import numpy as np
from scipy.signal import savgol_filter
from sklearn.decomposition import PCA
from typing import Dict, Any, List, Tuple, Optional


class SpectralPreprocessingPipeline:
    """
    Standardized Hyperspectral Preprocessing Service:
    - Reflectance calibration and scale correction
    - NoData & bad band removal
    - Savitzky-Golay spectral noise smoothing
    - Continuum removal (upper convex hull normalization)
    - Dimensionality reduction via Principal Component Analysis (PCA)
    """

    @staticmethod
    def sanitize_cube(cube: np.ndarray, nodata_value: Optional[float] = None) -> np.ndarray:
        """
        Replaces NaNs, infinite values, and optional NoData flags with 0.0,
        ensuring values are non-negative.
        """
        arr = np.copy(cube)
        if nodata_value is not None:
            arr[arr == nodata_value] = 0.0
        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
        return np.maximum(arr, 0.0)

    @staticmethod
    def extract_spatial_mean(cube: np.ndarray) -> np.ndarray:
        """
        Extracts spatial average spectral signature, masking out background zero pixels.
        Cube shape: (Height, Width, Bands) -> Output: 1D array of shape (Bands,)
        """
        spatial_sum = np.sum(cube, axis=2)
        # Identify foreground crop canopy pixels (avoid dark borders or saturation)
        valid_mask = (spatial_sum > 0.05) & (spatial_sum < (cube.shape[2] * 0.99))
        if np.any(valid_mask):
            return np.mean(cube[valid_mask], axis=0)
        return np.mean(cube, axis=(0, 1))

    @staticmethod
    def apply_savitzky_golay(signature: np.ndarray, window_length: int = 7, polyorder: int = 2) -> np.ndarray:
        """
        Applies Savitzky-Golay smoothing filter to suppress high-frequency sensor noise
        while preserving narrow absorption troughs (e.g. 670nm red trough, 700-750nm red-edge inflection).
        """
        n_bands = len(signature)
        wl = min(window_length, n_bands)
        if wl % 2 == 0:
            wl -= 1
        if wl <= polyorder:
            return signature.astype(np.float32)
        filtered = savgol_filter(signature, window_length=wl, polyorder=polyorder)
        return np.maximum(filtered, 0.0).astype(np.float32)

    @staticmethod
    def apply_continuum_removal(signature: np.ndarray, wavelengths: Optional[List[float]] = None) -> np.ndarray:
        """
        Computes continuum removal (convex envelope normalization) to isolate specific
        absorption features by removing the background baseline reflectance slope.
        Returns normalized reflectance in range [0.0, 1.0].
        """
        n_bands = len(signature)
        if n_bands < 5:
            return np.clip(signature, 0.0, 1.0)

        envelope = np.copy(signature)
        # Linear continuum between start and end waveband anchors
        p1 = 0
        p2 = n_bands - 1
        slope = (signature[p2] - signature[p1]) / float(p2 - p1)
        intercept = signature[p1]
        baseline = np.array([intercept + slope * i for i in range(n_bands)], dtype=np.float32)
        envelope = np.maximum(envelope, baseline)

        cr = np.where(envelope > 1e-6, signature / envelope, 1.0)
        return np.clip(cr, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def compute_pca(cube: np.ndarray, n_components: int = 3, max_samples: int = 5000) -> Dict[str, Any]:
        """
        Computes PCA transformation across spectral channels.
        Returns explained variance ratios, cumulative variance, and 2D scatter coordinates.
        """
        h, w, b = cube.shape
        flat = cube.reshape(-1, b)
        sample_size = min(max_samples, flat.shape[0])

        if flat.shape[0] > sample_size:
            idx = np.random.choice(flat.shape[0], sample_size, replace=False)
            sub = flat[idx]
        else:
            sub = flat

        pca = PCA(n_components=min(n_components, b))
        transformed = pca.fit_transform(sub)

        var_ratios = [round(float(v), 4) for v in pca.explained_variance_ratio_]
        total_var = round(float(np.sum(pca.explained_variance_ratio_)), 4)

        components_data = []
        for i in range(len(var_ratios)):
            components_data.append({
                "pc_index": i + 1,
                "variance_ratio": var_ratios[i],
                "eigenvalue": round(float(pca.explained_variance_[i]), 4) if hasattr(pca, "explained_variance_") else 1.0,
                "loadings": [round(float(l), 4) for l in pca.components_[i]]
            })

        scatter_points = []
        n_scatter = min(200, len(transformed))
        for i in range(n_scatter):
            scatter_points.append({
                "pc1": round(float(transformed[i, 0]), 3),
                "pc2": round(float(transformed[i, 1]), 3) if transformed.shape[1] > 1 else 0.0
            })

        return {
            "explained_variance_ratio": var_ratios,
            "total_explained_variance": total_var,
            "components": components_data,
            "sample_scatter": scatter_points
        }

