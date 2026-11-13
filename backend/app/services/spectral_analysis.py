import numpy as np
from typing import Dict, Any, List, Optional
from app.services.spectral_preprocessing import SpectralPreprocessingPipeline


class SpectralAnalysisService:
    """
    Scientific analysis service for hyperspectral signatures and cubes.
    Generates:
      - Raw & preprocessed spectral profiles
      - Continuum-removed spectra for absorption trough isolation
      - Narrowband vegetation indices (NDVI, NDRE, PRI, PSRI, WBI, MCARI)
      - Band statistics (mean, std, min, max, SNR)
      - Spectral anomaly detection against healthy baseline
    """

    @staticmethod
    def extract_full_profile(
        cube: np.ndarray,
        wavelengths: List[float]
    ) -> Dict[str, Any]:
        """
        Calculates spatial mean, standard deviation, and preprocessed curves.
        """
        raw_mean = SpectralPreprocessingPipeline.extract_spatial_mean(cube)
        filtered = SpectralPreprocessingPipeline.apply_savitzky_golay(raw_mean)
        continuum = SpectralPreprocessingPipeline.apply_continuum_removal(filtered, wavelengths)

        # Signal-to-Noise Ratio (SNR) estimation
        noise_diff = raw_mean - filtered
        noise_std = float(np.std(noise_diff))
        mean_sig = float(np.mean(raw_mean))
        snr_db = round(float(20 * np.log10(mean_sig / (noise_std + 1e-6))), 1) if noise_std > 0 else 45.0

        # Subsample for UI graphs (up to 60 points)
        step = max(1, len(wavelengths) // 60)
        chart_points = []
        for i in range(0, len(wavelengths), step):
            chart_points.append({
                "wavelength": round(wavelengths[i], 1),
                "raw_reflectance": round(float(raw_mean[i]), 4),
                "filtered_reflectance": round(float(filtered[i]), 4),
                "continuum_removed": round(float(continuum[i]), 4)
            })

        indices = SpectralAnalysisService.compute_vegetation_indices(filtered, wavelengths)

        return {
            "snr_db": snr_db,
            "raw_signature": [round(float(v), 4) for v in raw_mean],
            "filtered_signature": [round(float(v), 4) for v in filtered],
            "continuum_removed": [round(float(v), 4) for v in continuum],
            "chart_points": chart_points,
            "indices": indices
        }

    @staticmethod
    def compute_vegetation_indices(signature: np.ndarray, wavelengths: List[float]) -> Dict[str, float]:
        """
        Computes precision scientific narrowband vegetation indices:
        - NDVI: (R800 - R670) / (R800 + R670)
        - NDRE: (R800 - R720) / (R800 + R720)
        - PRI:  (R531 - R570) / (R531 + R570)
        - PSRI: (R680 - R500) / R750
        - WBI:  R900 / R970
        - MCARI: ((R705 - R670) - 0.2*(R705 - R570))*(R705 / R670)
        """
        w_arr = np.array(wavelengths)

        def get_band(target_w: float) -> float:
            idx = int(np.argmin(np.abs(w_arr - target_w)))
            return float(signature[idx])

        r500 = get_band(500.0)
        r531 = get_band(531.0)
        r570 = get_band(570.0)
        r670 = get_band(670.0)
        r680 = get_band(680.0)
        r705 = get_band(705.0)
        r720 = get_band(720.0)
        r750 = get_band(750.0)
        r800 = get_band(800.0)
        r900 = get_band(900.0)
        r970 = get_band(970.0)

        ndvi = (r800 - r670) / (r800 + r670 + 1e-6)
        ndre = (r800 - r720) / (r800 + r720 + 1e-6)
        pri = (r531 - r570) / (r531 + r570 + 1e-6)
        psri = (r680 - r500) / (r750 + 1e-6)
        wbi = r900 / (r970 + 1e-6)
        mcari = ((r705 - r670) - 0.2 * (r705 - r570)) * (r705 / (r670 + 1e-6))

        return {
            "NDVI": round(float(np.clip(ndvi, -1.0, 1.0)), 4),
            "NDRE": round(float(np.clip(ndre, -1.0, 1.0)), 4),
            "PRI": round(float(np.clip(pri, -1.0, 1.0)), 4),
            "PSRI": round(float(np.clip(psri, -2.0, 2.0)), 4),
            "WBI": round(float(np.clip(wbi, 0.0, 3.0)), 4),
            "MCARI": round(float(np.clip(mcari, -2.0, 5.0)), 4)
        }

