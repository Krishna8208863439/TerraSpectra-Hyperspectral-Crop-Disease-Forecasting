import os
import io
import json
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel

class HyperspectralMetadata(BaseModel):
    filename: str
    format: str
    dimensions: Tuple[int, int, int]  # (height, width, bands)
    bands_count: int
    wavelengths: List[float]
    wavelength_units: str = "nm"
    data_type: str
    byte_order: int = 0
    file_size_bytes: int
    is_valid_hyperspectral: bool
    summary: str

class HyperspectralCubeParser:
    """
    Parser for scientific Hyperspectral Image Cubes.
    Supports ENVI format (.hdr + binary raw/img/dat), NumPy cubes (.npy), and multi-band arrays.
    Validates dimensional constraints ensuring true spectral hypercubes (>= 10 bands).
    """

    MIN_HYPERSPECTRAL_BANDS = 10
    DEFAULT_WAVELENGTH_RANGE = (400.0, 1000.0)  # VNIR range in nm

    @staticmethod
    def parse_envi_header(header_content: str) -> Dict[str, Any]:
        """
        Parses standard ENVI ASCII header format.
        """
        lines = header_content.splitlines()
        header_data = {}
        in_multiline = False
        current_key = None
        multiline_buffer = []

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith(";") or line_str == "ENVI":
                continue

            if in_multiline:
                if "}" in line_str:
                    multiline_buffer.append(line_str.replace("}", "").strip())
                    header_data[current_key] = " ".join(multiline_buffer)
                    in_multiline = False
                    current_key = None
                    multiline_buffer = []
                else:
                    multiline_buffer.append(line_str.rstrip(","))
                continue

            if "=" in line_str:
                parts = line_str.split("=", 1)
                key = parts[0].strip().lower()
                val = parts[1].strip()

                if "{" in val and "}" not in val:
                    in_multiline = True
                    current_key = key
                    multiline_buffer.append(val.replace("{", "").strip())
                elif "{" in val and "}" in val:
                    header_data[key] = val.replace("{", "").replace("}", "").strip()
                else:
                    header_data[key] = val

        return header_data

    @classmethod
    def extract_wavelengths(cls, header_dict: Dict[str, Any], bands: int) -> List[float]:
        """
        Extracts or calibrates wavelengths from ENVI header or synthesizes calibrated VNIR bounds.
        """
        if "wavelength" in header_dict:
            raw_w = header_dict["wavelength"].replace(",", " ").split()
            try:
                wavelengths = [float(w) for w in raw_w if w.strip()]
                if len(wavelengths) == bands:
                    return wavelengths
            except ValueError:
                pass

        # If wavelengths not explicitly specified in header, generate calibrated contiguous linear bands
        start, end = cls.DEFAULT_WAVELENGTH_RANGE
        return [round(w, 2) for w in np.linspace(start, end, bands).tolist()]

    @classmethod
    def load_numpy_cube(cls, file_bytes: bytes, filename: str) -> Tuple[np.ndarray, HyperspectralMetadata]:
        """
        Loads and validates a 3D hyperspectral cube stored in .npy format.
        Expected shape: (Height, Width, Bands) or (Bands, Height, Width).
        """
        bio = io.BytesIO(file_bytes)
        arr = np.load(bio)

        if arr.ndim != 3:
            raise ValueError(f"Invalid dimensions: Hyperspectral cube must be 3-dimensional (H, W, Bands), got {arr.ndim}D array.")

        # Transpose if bands are in the first dimension (B, H, W) -> (H, W, B)
        if arr.shape[0] > arr.shape[2] and arr.shape[0] >= cls.MIN_HYPERSPECTRAL_BANDS:
            arr = np.transpose(arr, (1, 2, 0))

        h, w, b = arr.shape
        if b < cls.MIN_HYPERSPECTRAL_BANDS:
            raise ValueError(f"Insufficient spectral bands: Provided image has {b} bands. Hyperspectral cubes require at least {cls.MIN_HYPERSPECTRAL_BANDS} spectral bands (RGB has 3).")

        # Normalize to float32 reflectance in range [0.0, 1.0] if in uint16 or uint8
        if arr.dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif arr.dtype == np.uint16:
            arr = arr.astype(np.float32) / 65535.0
        else:
            arr = arr.astype(np.float32)
            # Clip potential outliers if normalized reflectance
            if np.nanmax(arr) > 1.0:
                max_val = np.nanmax(arr)
                if max_val > 0:
                    arr = arr / max_val

        wavelengths = [round(w, 2) for w in np.linspace(cls.DEFAULT_WAVELENGTH_RANGE[0], cls.DEFAULT_WAVELENGTH_RANGE[1], b).tolist()]

        meta = HyperspectralMetadata(
            filename=filename,
            format="NumPy Spectral Cube (.npy)",
            dimensions=(h, w, b),
            bands_count=b,
            wavelengths=wavelengths,
            wavelength_units="nm",
            data_type=str(arr.dtype),
            byte_order=0,
            file_size_bytes=len(file_bytes),
            is_valid_hyperspectral=True,
            summary=f"Calibrated 3D Spectral Cube with {b} contiguous bands spanning {wavelengths[0]}nm - {wavelengths[-1]}nm."
        )
        return arr, meta

    @classmethod
    def load_envi_cube(cls, raw_bytes: bytes, header_text: str, filename: str) -> Tuple[np.ndarray, HyperspectralMetadata]:
        """
        Parses ENVI binary data paired with header configuration.
        """
        hdr = cls.parse_envi_header(header_text)
        samples = int(hdr.get("samples", 0))  # width
        lines = int(hdr.get("lines", 0))      # height
        bands = int(hdr.get("bands", 0))      # spectral channels

        if samples <= 0 or lines <= 0 or bands < cls.MIN_HYPERSPECTRAL_BANDS:
            raise ValueError(f"Invalid ENVI dimensions: {lines}x{samples} with {bands} bands. Minimum {cls.MIN_HYPERSPECTRAL_BANDS} bands required.")

        # Data type mapping according to ENVI specification
        dtype_map = {
            "1": np.uint8,
            "2": np.int16,
            "3": np.int32,
            "4": np.float32,
            "5": np.float64,
            "12": np.uint16,
        }
        dt_code = str(hdr.get("data type", "4"))
        dtype = dtype_map.get(dt_code, np.float32)
        interleave = hdr.get("interleave", "bsq").lower()

        raw_arr = np.frombuffer(raw_bytes, dtype=dtype)
        expected_len = samples * lines * bands
        if raw_arr.size < expected_len:
            raise ValueError(f"ENVI file size mismatch. Expected {expected_len} elements, found {raw_arr.size}.")

        raw_arr = raw_arr[:expected_len]

        if interleave == "bsq":  # Band sequential (bands, lines, samples)
            arr = raw_arr.reshape((bands, lines, samples))
            arr = np.transpose(arr, (1, 2, 0))
        elif interleave == "bil":  # Band interleaved by line (lines, bands, samples)
            arr = raw_arr.reshape((lines, bands, samples))
            arr = np.transpose(arr, (0, 2, 1))
        elif interleave == "bip":  # Band interleaved by pixel (lines, samples, bands)
            arr = raw_arr.reshape((lines, samples, bands))
        else:
            arr = raw_arr.reshape((lines, samples, bands))

        # Convert to float32 reflectance
        if arr.dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif arr.dtype == np.uint16:
            arr = arr.astype(np.float32) / 65535.0
        else:
            arr = arr.astype(np.float32)
            if np.nanmax(arr) > 1.0:
                m = np.nanmax(arr)
                if m > 0:
                    arr = arr / m

        wavelengths = cls.extract_wavelengths(hdr, bands)

        meta = HyperspectralMetadata(
            filename=filename,
            format=f"ENVI ({interleave.upper()})",
            dimensions=(lines, samples, bands),
            bands_count=bands,
            wavelengths=wavelengths,
            wavelength_units=hdr.get("wavelength units", "nm"),
            data_type=str(arr.dtype),
            byte_order=int(hdr.get("byte order", 0)),
            file_size_bytes=len(raw_bytes),
            is_valid_hyperspectral=True,
            summary=f"ENVI Spectral Cube ({lines}x{samples}) with {bands} spectral channels ({interleave.upper()})."
        )
        return arr, meta

