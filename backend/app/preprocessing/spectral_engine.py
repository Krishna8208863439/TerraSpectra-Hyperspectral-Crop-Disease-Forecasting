import numpy as np
from scipy.signal import savgol_filter
from sklearn.decomposition import PCA
from typing import Dict, Any, List, Tuple

class SpectralAnalysisEngine:
    """
    Scientific processing engine for Hyperspectral cubes and signatures.
    Includes Savitzky-Golay filtering, Continuum Removal, PCA, Band slicing,
    and calculation of Narrowband Spectral Vegetation Indices.
    """

    @staticmethod
    def extract_mean_spectral_signature(cube: np.ndarray) -> np.ndarray:
        """
        Calculates spatial mean spectral signature across all pixels.
        Input cube: (H, W, B) -> Output: 1D array of length B.
        """
        # Exclude background zero-value or saturated pixels
        spatial_sum = np.sum(cube, axis=2)
        valid_mask = (spatial_sum > 0.05) & (spatial_sum < (cube.shape[2] * 0.98))
        if np.any(valid_mask):
            return np.mean(cube[valid_mask], axis=0)
        return np.mean(cube, axis=(0, 1))

    @staticmethod
    def apply_savitzky_golay(signature: np.ndarray, window_length: int = 7, polyorder: int = 2) -> np.ndarray:
        """
        Applies Savitzky-Golay smoothing filter to remove sensor noise while preserving absorption peaks.
        """
        wl = min(window_length, len(signature))
        if wl % 2 == 0:
            wl -= 1
        if wl <= polyorder:
            return signature
        return savgol_filter(signature, window_length=wl, polyorder=polyorder)

    @staticmethod
    def continuum_removal(signature: np.ndarray, wavelengths: List[float]) -> np.ndarray:
        """
        Performs continuum removal (convex hull normalization) to isolate specific chlorophyll absorption bands.
        """
        n_bands = len(signature)
        if n_bands < 5:
            return signature

        # Simplified upper convex envelope
        envelope = np.copy(signature)
        p1 = 0
        p2 = n_bands - 1
        slope = (signature[p2] - signature[p1]) / (p2 - p1)
        intercept = signature[p1]
        baseline = np.array([intercept + slope * i for i in range(n_bands)])
        envelope = np.maximum(envelope, baseline)

        cr = np.where(envelope > 1e-6, signature / envelope, 1.0)
        return np.clip(cr, 0.0, 1.0)

    @staticmethod
    def compute_spectral_indices(signature: np.ndarray, wavelengths: List[float]) -> Dict[str, float]:
        """
        Computes precision scientific narrowband indices based on key wavelengths:
        - NDVI (Normalized Difference Vegetation Index) ~ 800nm & 670nm
        - NDRE (Red Edge NDVI) ~ 790nm & 720nm (early stress marker)
        - PRI (Photochemical Reflectance Index) ~ 531nm & 570nm (carotenoid/photosynthetic efficiency)
        - PSRI (Plant Senescence Reflectance Index) ~ 680nm, 500nm & 750nm
        - WBI (Water Band Index) ~ 900nm & 970nm (foliar water status)
        """
        w_arr = np.array(wavelengths)
        def get_band_val(target_w: float) -> float:
            idx = int(np.argmin(np.abs(w_arr - target_w)))
            return float(signature[idx])

        r500 = get_band_val(500.0)
        r531 = get_band_val(531.0)
        r570 = get_band_val(570.0)
        r670 = get_band_val(670.0)
        r680 = get_band_val(680.0)
        r705 = get_band_val(705.0)
        r720 = get_band_val(720.0)
        r750 = get_band_val(750.0)
        r800 = get_band_val(800.0)
        r900 = get_band_val(900.0)
        r970 = get_band_val(970.0)

        # Standard NDVI: (R800 - R670) / (R800 + R670)
        ndvi = (r800 - r670) / (r800 + r670 + 1e-6)
        # RedEdge NDVI (NDRE): Sensitive to early chlorophyll changes before canopy browning
        ndre = (r800 - r720) / (r800 + r720 + 1e-6)
        # Photochemical Reflectance Index: (R531 - R570) / (R531 + R570)
        pri = (r531 - r570) / (r531 + r570 + 1e-6)
        # Plant Senescence Reflectance Index: (R680 - R500) / R750
        psri = (r680 - r500) / (r750 + 1e-6)
        # Water Band Index: R900 / R970
        wbi = r900 / (r970 + 1e-6)
        # Modified Chlorophyll Absorption in Reflectance Index (MCARI)
        mcari = ((r705 - r670) - 0.2 * (r705 - r570)) * (r705 / (r670 + 1e-6))

        return {
            "NDVI": round(float(np.clip(ndvi, -1.0, 1.0)), 4),
            "NDRE": round(float(np.clip(ndre, -1.0, 1.0)), 4),
            "PRI": round(float(np.clip(pri, -1.0, 1.0)), 4),
            "PSRI": round(float(np.clip(psri, -2.0, 2.0)), 4),
            "WBI": round(float(np.clip(wbi, 0.0, 3.0)), 4),
            "MCARI": round(float(np.clip(mcari, -2.0, 5.0)), 4)
        }

    @staticmethod
    def compute_pca_projection(cube: np.ndarray, n_components: int = 3) -> Dict[str, Any]:
        """
        Projects high-dimensional cube onto top principal components.
        """
        h, w, b = cube.shape
        flat = cube.reshape(-1, b)
        # Subsample if large for responsive interactive analysis
        sample_size = min(5000, flat.shape[0])
        idx = np.random.choice(flat.shape[0], sample_size, replace=False)
        sub_samples = flat[idx]

        pca = PCA(n_components=n_components)
        transformed = pca.fit_transform(sub_samples)

        return {
            "explained_variance_ratio": [round(float(v), 4) for v in pca.explained_variance_ratio_],
            "total_explained_variance": round(float(np.sum(pca.explained_variance_ratio_)), 4),
            "components": [
                {
                    "pc_index": i + 1,
                    "variance_ratio": round(float(pca.explained_variance_ratio_[i]), 4),
                    "loadings": [round(float(l), 4) for l in pca.components_[i]]
                }
                for i in range(n_components)
            ],
            "sample_scatter": [
                {"pc1": round(float(transformed[i, 0]), 3), "pc2": round(float(transformed[i, 1]), 3)}
                for i in range(min(200, len(transformed)))
            ]
        }

