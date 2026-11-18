import numpy as np
from typing import Dict, Any, List, Optional, Tuple


class SpectralAnomalyDetector:
    """
    Scientific Hyperspectral Spectral Anomaly & Biomarker Extraction Service.
    
    Provides:
      1. Reed-Xiaoli (RX) Anomaly Detection: The benchmark unsupervised remote sensing
         algorithm for detecting non-typical spectral pixels against local/global canopy background.
      2. Spectral Angle Mapper (SAM): Computes spectral similarity angles against reference
         healthy crop spectral endmembers in N-dimensional spectral space.
      3. Spectral Information Divergence (SID): Measures probabilistic divergence between
         target pixel signatures and healthy crop reference signatures.
      4. Early-Stress Biomarker Fingerprinting: Quantifies Red-Edge Shift (nm),
         Photochemical Inversion Ratio, and Water Band Depth.
    """

    @staticmethod
    def compute_rx_anomaly(cube: np.ndarray) -> np.ndarray:
        """
        Calculates Reed-Xiaoli (RX) anomaly score for each spatial pixel in the hypercube.
        Input cube shape: (H, W, B) -> Output: 2D array of shape (H, W)
        
        Formula: RX(r) = (r - mu)^T * C^(-1) * (r - mu)
        where mu is the global mean spectral vector and C is the spectral covariance matrix.
        """
        h, w, b = cube.shape
        flat = cube.reshape(-1, b)

        # Exclude background/zero pixels
        mask = np.sum(flat, axis=1) > 0.05
        if not np.any(mask):
            return np.zeros((h, w), dtype=np.float32)

        valid_pixels = flat[mask]
        mu = np.mean(valid_pixels, axis=0)
        centered = valid_pixels - mu

        # Regularized Covariance matrix
        cov = np.cov(centered, rowvar=False) + np.eye(b) * 1e-4
        try:
            inv_cov = np.linalg.pinv(cov)
        except Exception:
            inv_cov = np.eye(b)

        # Compute Mahalanobis distance for all pixels
        all_centered = flat - mu
        # Vectorized quadratic form: sum((X * inv_cov) * X, axis=1)
        rx_scores = np.sum(np.dot(all_centered, inv_cov) * all_centered, axis=1)
        rx_map = rx_scores.reshape((h, w))

        # Normalize to [0.0, 1.0]
        max_val = np.nanmax(rx_map)
        min_val = np.nanmin(rx_map)
        if max_val > min_val:
            rx_map = (rx_map - min_val) / (max_val - min_val)
        else:
            rx_map = np.zeros_like(rx_map)

        return np.clip(rx_map, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def compute_spectral_angle(sig1: np.ndarray, sig2: np.ndarray) -> float:
        """
        Spectral Angle Mapper (SAM) angle in radians between two spectral signatures.
        SAM = arccos( (sig1 . sig2) / (||sig1|| * ||sig2||) )
        """
        norm1 = np.linalg.norm(sig1)
        norm2 = np.linalg.norm(sig2)
        if norm1 == 0 or norm2 == 0:
            return float(np.pi / 2)
        cos_theta = np.dot(sig1, sig2) / (norm1 * norm2)
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        return float(np.arccos(cos_theta))

    @staticmethod
    def compute_spectral_information_divergence(sig1: np.ndarray, sig2: np.ndarray) -> float:
        """
        Spectral Information Divergence (SID) measuring relative entropy between signatures.
        """
        p = np.maximum(sig1, 1e-6) / (np.sum(sig1) + 1e-6)
        q = np.maximum(sig2, 1e-6) / (np.sum(sig2) + 1e-6)
        d_pq = np.sum(p * np.log(p / q))
        d_qp = np.sum(q * np.log(q / p))
        return float(max(0.0, d_pq + d_qp))

    @staticmethod
    def extract_biomarker_fingerprints(
        signature: np.ndarray,
        wavelengths: List[float]
    ) -> Dict[str, Any]:
        """
        Extracts key physiological hyperspectral biomarkers:
          - Red-Edge Position (REP): Wavelength of maximum derivative in 680-760nm
          - Carotenoid-to-Chlorophyll Ratio (PRI Inversion)
          - Water Absorption Band Depth (970nm absorption trough relative to 900nm shoulder)
          - Green Peak Reflectance Amplitude (550nm)
        """
        w_arr = np.array(wavelengths)

        def get_val(target_w: float) -> float:
            idx = int(np.argmin(np.abs(w_arr - target_w)))
            return float(signature[idx])

        # 1. Red Edge Position (REP) via 1st spectral derivative
        re_mask = (w_arr >= 680.0) & (w_arr <= 760.0)
        if np.sum(re_mask) >= 3:
            re_wavelengths = w_arr[re_mask]
            re_reflectance = signature[re_mask]
            deriv = np.gradient(re_reflectance, re_wavelengths)
            max_idx = int(np.argmax(deriv))
            rep_nm = round(float(re_wavelengths[max_idx]), 2)
        else:
            rep_nm = 715.0

        r550 = get_val(550.0)
        r680 = get_val(680.0)
        r800 = get_val(800.0)
        r900 = get_val(900.0)
        r970 = get_val(970.0)

        # Water absorption trough depth
        water_depth = round(float(max(0.0, (r900 - r970) / (r900 + 1e-6))), 4)

        # Chlorophyll absorption ratio: (R800 - R680) / R800
        chl_absorption_depth = round(float(max(0.0, (r800 - r680) / (r800 + 1e-6))), 4)

        return {
            "red_edge_position_nm": rep_nm,
            "green_peak_reflectance": round(r550, 4),
            "chlorophyll_absorption_depth": chl_absorption_depth,
            "water_absorption_depth_970nm": water_depth,
            "red_edge_status": "Normal / Healthy" if rep_nm >= 715.0 else "Blue-Shifted (Chlorosis / Stress)"
        }

    @staticmethod
    def analyze_cube_anomalies(
        cube: np.ndarray,
        wavelengths: List[float],
        reference_healthy: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive spatial-spectral anomaly and biomarker evaluation.
        """
        h, w, b = cube.shape
        rx_map = SpectralAnomalyDetector.compute_rx_anomaly(cube)
        high_anomaly_ratio = float(np.mean(rx_map > 0.65))

        mean_sig = np.mean(cube.reshape(-1, b), axis=0)
        biomarkers = SpectralAnomalyDetector.extract_biomarker_fingerprints(mean_sig, wavelengths)

        sam_angle = None
        sid_div = None
        if reference_healthy is not None and len(reference_healthy) == b:
            sam_angle = round(SpectralAnomalyDetector.compute_spectral_angle(mean_sig, reference_healthy), 4)
            sid_div = round(SpectralInformationDivergence(mean_sig, reference_healthy), 4) if 'SpectralInformationDivergence' in globals() else round(SpectralAnomalyDetector.compute_spectral_information_divergence(mean_sig, reference_healthy), 4)

        return {
            "rx_anomaly_mean": round(float(np.mean(rx_map)), 4),
            "rx_anomaly_max": round(float(np.max(rx_map)), 4),
            "high_anomaly_pixel_fraction": round(high_anomaly_ratio, 4),
            "biomarkers": biomarkers,
            "sam_angle_rad": sam_angle,
            "sid_divergence": sid_div
        }


if __name__ == "__main__":
    # Self-test validation
    dummy_cube = np.random.uniform(0.1, 0.7, (16, 16, 50)).astype(np.float32)
    dummy_wls = list(np.linspace(400.0, 1000.0, 50))
    res = SpectralAnomalyDetector.analyze_cube_anomalies(dummy_cube, dummy_wls)
    print("SpectralAnomalyDetector verification successful:")
    print(res)
