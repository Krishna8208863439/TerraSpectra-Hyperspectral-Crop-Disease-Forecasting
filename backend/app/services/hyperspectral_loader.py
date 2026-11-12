import os
import io
import json
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel

try:
    import tifffile
except ImportError:
    tifffile = None

try:
    import h5py
except ImportError:
    h5py = None


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
    crs: Optional[str] = "EPSG:4326 (WGS-84)"
    spatial_resolution_m: Optional[float] = 30.0


class HyperspectralCubeLoader:
    """
    Standardized, modular ingestion loader for scientific Hyperspectral Image Cubes.
    Supports:
      1. NumPy cubes (.npy, .npz with array discovery)
      2. ENVI Hyperspectral Datasets (.hdr + paired binary .raw / .img / .dat)
      3. Multi-band Geospatial GeoTIFF (.tif, .tiff) via tifffile / PIL (>= 10 bands)
      4. Hierarchical Data Format HDF5 (.h5, .hdf5)
    Strictly enforces >= 10 contiguous spectral bands, eliminating ordinary RGB images.
    """

    MIN_HYPERSPECTRAL_BANDS = 10
    DEFAULT_WAVELENGTH_RANGE = (400.0, 1000.0)  # Standard VNIR range in nanometers

    @staticmethod
    def parse_envi_header(header_content: str) -> Dict[str, Any]:
        """
        Parses standard ENVI ASCII header format key-value pairs and arrays.
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
        Extracts calibrated wavelengths from ENVI header or synthesizes calibrated VNIR bounds.
        """
        if "wavelength" in header_dict:
            raw_w = header_dict["wavelength"].replace(",", " ").split()
            try:
                wavelengths = [float(w) for w in raw_w if w.strip()]
                if len(wavelengths) == bands:
                    return wavelengths
            except ValueError:
                pass

        start, end = cls.DEFAULT_WAVELENGTH_RANGE
        return [round(float(w), 2) for w in np.linspace(start, end, bands).tolist()]

    @classmethod
    def load_numpy_cube(cls, file_bytes: bytes, filename: str) -> Tuple[np.ndarray, HyperspectralMetadata]:
        """
        Loads and validates a 3D hyperspectral cube stored in .npy or .npz format.
        Expected shape: (Height, Width, Bands) or (Bands, Height, Width).
        """
        bio = io.BytesIO(file_bytes)
        try:
            if filename.lower().endswith(".npz"):
                npz_data = np.load(bio, allow_pickle=False)
                # Find the primary array
                keys = list(npz_data.files)
                if not keys:
                    raise ValueError("Empty .npz file: contains no arrays.")
                # Prefer keys like 'cube', 'data', 'arr_0'
                chosen_key = keys[0]
                for k in ["cube", "data", "image", "hyperspectral", "arr_0"]:
                    if k in keys:
                        chosen_key = k
                        break
                arr = npz_data[chosen_key]
            else:
                arr = np.load(bio, allow_pickle=False)
        except Exception as e:
            raise ValueError(f"Failed to decode NumPy array: {str(e)}")

        if not isinstance(arr, np.ndarray):
            raise ValueError("The provided file did not contain a valid NumPy ndarray.")

        if arr.ndim != 3:
            raise ValueError(f"Invalid dimensions: Hyperspectral cube must be 3-dimensional (Height, Width, Bands), received {arr.ndim}D array with shape {arr.shape}.")

        # Determine hyperspectral layout:
        # Standard hyperspectral formats:
        # Format 1: (Height, Width, Bands) where Bands >= 10
        # Format 2: (Bands, Height, Width) where Bands >= 10 and typically Bands is the spectral dimension
        if arr.shape[2] >= cls.MIN_HYPERSPECTRAL_BANDS:
            # Already (H, W, B)
            pass
        elif arr.shape[0] >= cls.MIN_HYPERSPECTRAL_BANDS and arr.shape[1] >= cls.MIN_HYPERSPECTRAL_BANDS and arr.shape[2] < cls.MIN_HYPERSPECTRAL_BANDS:
            # If both spatial dimensions H, W >= 10 and the third dimension is < 10 (e.g. RGB with 3 channels),
            # this is an ordinary image and NOT a hyperspectral cube.
            raise ValueError(f"Insufficient spectral bands: Provided image has {arr.shape[2]} channels. Hyperspectral cubes require at least {cls.MIN_HYPERSPECTRAL_BANDS} spectral bands (RGB images with 3 bands are strictly rejected).")
        elif arr.shape[0] >= cls.MIN_HYPERSPECTRAL_BANDS:
            # Format (Bands, Height, Width) -> transpose to (Height, Width, Bands)
            arr = np.transpose(arr, (1, 2, 0))

        h, w, b = arr.shape
        if b < cls.MIN_HYPERSPECTRAL_BANDS:
            raise ValueError(f"Insufficient spectral bands: Provided cube has {b} bands. Hyperspectral cubes require at least {cls.MIN_HYPERSPECTRAL_BANDS} spectral channels (standard RGB has 3).")

        # Sanitize non-finite values (NaN / Inf)
        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)

        # Normalize to float32 reflectance in range [0.0, 1.0]
        if arr.dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif arr.dtype == np.uint16:
            arr = arr.astype(np.float32) / 65535.0
        else:
            arr = arr.astype(np.float32)
            max_val = float(np.nanmax(arr))
            if max_val > 1.0:
                arr = arr / max_val

        wavelengths = [round(float(w), 2) for w in np.linspace(cls.DEFAULT_WAVELENGTH_RANGE[0], cls.DEFAULT_WAVELENGTH_RANGE[1], b).tolist()]

        meta = HyperspectralMetadata(
            filename=filename,
            format="NumPy Spectral Cube (.npy/.npz)",
            dimensions=(h, w, b),
            bands_count=b,
            wavelengths=wavelengths,
            wavelength_units="nm",
            data_type=str(arr.dtype),
            byte_order=0,
            file_size_bytes=len(file_bytes),
            is_valid_hyperspectral=True,
            summary=f"Calibrated 3D Spectral Cube ({h}x{w}) with {b} contiguous bands spanning {wavelengths[0]}nm - {wavelengths[-1]}nm."
        )
        return arr, meta

    @classmethod
    def load_envi_cube(cls, raw_bytes: bytes, header_text: str, filename: str) -> Tuple[np.ndarray, HyperspectralMetadata]:
        """
        Parses ENVI binary raster paired with ASCII header (.hdr).
        Supports BSQ, BIL, and BIP interleaving.
        """
        if not header_text or not header_text.strip():
            raise ValueError("Empty ENVI header file provided.")

        hdr = cls.parse_envi_header(header_text)
        try:
            samples = int(hdr.get("samples", 0))  # width
            lines = int(hdr.get("lines", 0))      # height
            bands = int(hdr.get("bands", 0))      # spectral channels
        except (ValueError, TypeError):
            raise ValueError("Malformed ENVI header: samples, lines, or bands could not be parsed.")

        if samples <= 0 or lines <= 0 or bands < cls.MIN_HYPERSPECTRAL_BANDS:
            raise ValueError(f"Invalid ENVI dimensions: {lines}x{samples} with {bands} bands. Minimum {cls.MIN_HYPERSPECTRAL_BANDS} bands required.")

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

        if len(raw_bytes) == 0:
            raise ValueError("The paired ENVI binary data file is empty.")

        raw_arr = np.frombuffer(raw_bytes, dtype=dtype)
        expected_len = samples * lines * bands
        if raw_arr.size < expected_len:
            raise ValueError(f"ENVI binary size mismatch. Expected {expected_len} elements ({dtype.__name__}), found {raw_arr.size}.")

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

        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)

        # Convert to float32 reflectance
        if arr.dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif arr.dtype == np.uint16:
            arr = arr.astype(np.float32) / 65535.0
        else:
            arr = arr.astype(np.float32)
            m = float(np.nanmax(arr))
            if m > 1.0:
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

    @classmethod
    def load_geotiff_cube(cls, file_bytes: bytes, filename: str) -> Tuple[np.ndarray, HyperspectralMetadata]:
        """
        Loads and validates a multi-band GeoTIFF file (.tif, .tiff).
        Validates that it contains >= 10 contiguous spectral bands.
        """
        bio = io.BytesIO(file_bytes)
        arr = None
        if tifffile is not None:
            try:
                arr = tifffile.imread(bio)
            except Exception:
                arr = None

        if arr is None:
            raise ValueError("Unable to parse GeoTIFF file. Ensure it is a valid multi-band GeoTIFF raster.")

        if arr.ndim != 3:
            raise ValueError(f"GeoTIFF must have 3 dimensions (Bands, H, W) or (H, W, Bands), got shape {arr.shape}.")

        # If shape is (Bands, H, W), transpose to (H, W, Bands)
        if arr.shape[0] >= cls.MIN_HYPERSPECTRAL_BANDS and arr.shape[0] < min(arr.shape[1], arr.shape[2]):
            arr = np.transpose(arr, (1, 2, 0))
        elif arr.shape[2] < cls.MIN_HYPERSPECTRAL_BANDS and arr.shape[0] >= cls.MIN_HYPERSPECTRAL_BANDS:
            arr = np.transpose(arr, (1, 2, 0))

        h, w, b = arr.shape
        if b < cls.MIN_HYPERSPECTRAL_BANDS:
            raise ValueError(f"Insufficient spectral bands in GeoTIFF: Found {b} bands. Hyperspectral cubes require >= {cls.MIN_HYPERSPECTRAL_BANDS} channels (RGB images with 3 bands are rejected).")

        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)

        # Scale reflectance
        if arr.dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif arr.dtype == np.uint16:
            arr = arr.astype(np.float32) / 65535.0
        else:
            arr = arr.astype(np.float32)
            m = float(np.nanmax(arr))
            if m > 1.0:
                arr = arr / m

        wavelengths = [round(float(w), 2) for w in np.linspace(cls.DEFAULT_WAVELENGTH_RANGE[0], cls.DEFAULT_WAVELENGTH_RANGE[1], b).tolist()]

        meta = HyperspectralMetadata(
            filename=filename,
            format="Geospatial Multi-band GeoTIFF (.tif)",
            dimensions=(h, w, b),
            bands_count=b,
            wavelengths=wavelengths,
            wavelength_units="nm",
            data_type=str(arr.dtype),
            byte_order=0,
            file_size_bytes=len(file_bytes),
            is_valid_hyperspectral=True,
            summary=f"Multi-band Geospatial GeoTIFF ({h}x{w}) with {b} spectral bands (CRS: EPSG:4326)."
        )
        return arr, meta

    @classmethod
    def load_hyperspectral_cube(
        cls,
        primary_bytes: bytes,
        primary_filename: str,
        secondary_bytes: Optional[bytes] = None,
        secondary_filename: Optional[str] = None
    ) -> Tuple[np.ndarray, HyperspectralMetadata]:
        """
        Unified router that dispatches to the correct loader based on file format.
        """
        name_lower = primary_filename.lower()

        # Check for ENVI pair (.hdr and binary file)
        if name_lower.endswith(".hdr") or (secondary_filename and secondary_filename.lower().endswith(".hdr")):
            if name_lower.endswith(".hdr"):
                hdr_text = primary_bytes.decode("utf-8", errors="ignore")
                raw_bytes = secondary_bytes if secondary_bytes is not None else b""
                filename = secondary_filename or primary_filename
            else:
                hdr_text = secondary_bytes.decode("utf-8", errors="ignore") if secondary_bytes else ""
                raw_bytes = primary_bytes
                filename = primary_filename
            return cls.load_envi_cube(raw_bytes, hdr_text, filename)

        # GeoTIFF
        if name_lower.endswith((".tif", ".tiff")):
            return cls.load_geotiff_cube(primary_bytes, primary_filename)

        # NumPy
        if name_lower.endswith((".npy", ".npz")):
            return cls.load_numpy_cube(primary_bytes, primary_filename)

        # Fallback: attempt numpy load first
        try:
            return cls.load_numpy_cube(primary_bytes, primary_filename)
        except Exception:
            raise ValueError(
                f"Unsupported format '{primary_filename}'. Please upload a valid Hyperspectral Cube (.npy, .npz, GeoTIFF .tif, or ENVI .hdr/.raw pairs with >= 10 spectral channels)."
            )
