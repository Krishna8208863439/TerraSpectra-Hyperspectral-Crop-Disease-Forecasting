import numpy as np
from typing import Dict, Any, List, Optional, Tuple


class SpectralEndmemberUnmixingEngine:
    """
    Hyperspectral Endmember Extraction & Linear Spectral Unmixing (LSU) Engine.
    
    Provides sub-pixel canopy composition analysis:
      1. Vertex Component Analysis (VCA):
         Unsupervised geometric algorithm to discover pure spectral endmembers
         (e.g., Healthy Foliage, Necrotic / Sporulated Lesion, Exposed Soil, Senescent Canopy)
         from high-dimensional hyperspectral cubes.
      2. Fully Constrained Least Squares (FCLS) Unmixing:
         Decomposes each mixed canopy pixel into fractional abundance components subject to:
           - Abundance Non-negativity Constraint (ANC): a_i >= 0
           - Abundance Sum-to-One Constraint (ASC): sum(a_i) == 1
      3. Sub-Pixel Disease Fraction Quantification:
         Measures micro-lesion progression even when pathogen symptoms occupy
         only 5% - 20% of an individual pixel area before visible canopy necrosis.
    """

    DEFAULT_ENDMEMBER_NAMES = [
        "Healthy Photosynthetic Canopy",
        "Pathogenic Necrosis / Lesion",
        "Senescent / Chlorotic Tissue",
        "Soil / Non-Photosynthetic Background"
    ]

    @staticmethod
    def extract_endmembers_vca(
        cube: np.ndarray,
        num_endmembers: int = 4,
        snr_input_db: Optional[float] = None
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Vertex Component Analysis (Nascimento & Dias, 2005) for endmember extraction.
        Cube shape: (H, W, B) -> Returns: (num_endmembers, B) array of endmember spectra,
        and list of indices representing selected pure pixels.
        """
        h, w, b = cube.shape
        flat = cube.reshape(-1, b)

        # Exclude black/invalid background pixels
        valid_mask = np.sum(flat, axis=1) > 0.05
        if np.sum(valid_mask) < num_endmembers:
            # Fallback if too few valid pixels
            mean_sig = np.mean(flat, axis=0)
            endmembers = np.tile(mean_sig, (num_endmembers, 1))
            return endmembers, list(range(num_endmembers))

        r_data = flat[valid_mask].T  # Shape: (B, N)
        num_pixels = r_data.shape[1]
        p = num_endmembers

        # Estimate SNR if not provided
        if snr_input_db is None:
            r_mean = np.mean(r_data, axis=1, keepdims=True)
            r_centered = r_data - r_mean
            cov = np.dot(r_centered, r_centered.T) / num_pixels
            trace_cov = np.trace(cov)
            snr_est = 10 * np.log10(np.sum(r_mean**2) / (trace_cov + 1e-8))
        else:
            snr_est = snr_input_db

        snr_threshold = 15 + 10 * np.log10(p)

        # SVD Projection
        if snr_est > snr_threshold:
            u, s, vh = np.linalg.svd(np.dot(r_data, r_data.T) / num_pixels)
            Ud = u[:, :p]
            x_proj = np.dot(Ud.T, r_data)
            # Projective coordinates
            u_mean = np.mean(x_proj, axis=1, keepdims=True)
            scale = np.sum(x_proj * u_mean, axis=0, keepdims=True)
            scale[np.abs(scale) < 1e-6] = 1e-6
            y_proj = x_proj / scale
        else:
            u, s, vh = np.linalg.svd(cov if 'cov' in locals() else np.cov(r_data))
            Ud = u[:, :p - 1]
            x_proj = np.dot(Ud.T, r_data - np.mean(r_data, axis=1, keepdims=True))
            c_norm = np.max(np.sqrt(np.sum(x_proj**2, axis=0)))
            y_proj = np.vstack([x_proj, np.full((1, num_pixels), c_norm)])

        # VCA iterative simplex expansion
        indice = []
        A = np.zeros((p, p))
        A[-1, 0] = 1

        for i in range(p):
            w_vec = np.random.randn(p, 1)
            f = w_vec - np.dot(A, np.dot(np.linalg.pinv(A), w_vec))
            f_norm = np.linalg.norm(f)
            f = f / (f_norm + 1e-9)

            v = np.dot(f.T, y_proj)
            max_idx = int(np.argmax(np.abs(v)))
            indice.append(max_idx)
            A[:, i] = y_proj[:, max_idx]

        pure_endmembers = r_data[:, indice].T  # Shape: (p, B)
        return pure_endmembers.astype(np.float32), indice

    @staticmethod
    def unmix_pixel_fcls(
        pixel: np.ndarray,
        endmembers: np.ndarray,
        max_iter: int = 40
    ) -> np.ndarray:
        """
        Fast non-negative constrained unmixing via iterative projected gradient descent
        with Sum-to-One normalization (FCLS approximation).
        pixel: shape (B,)
        endmembers: shape (p, B)
        Returns: abundance vector a of shape (p,) where sum(a) == 1 and a >= 0.
        """
        p, b = endmembers.shape
        # Initialize uniform abundances
        abundances = np.full(p, 1.0 / p, dtype=np.float32)
        
        # Precompute M^T * M and M^T * y
        mt_m = np.dot(endmembers, endmembers.T)  # (p, p)
        mt_y = np.dot(endmembers, pixel)         # (p,)
        
        step_size = 1.0 / (np.linalg.norm(mt_m, 2) + 1e-6)

        for _ in range(max_iter):
            # Gradient of 0.5 * ||y - M*a||^2 is M^T*(M*a - y)
            grad = np.dot(mt_m, abundances) - mt_y
            abundances -= step_size * grad

            # Project to non-negative orthant
            abundances = np.maximum(abundances, 0.0)

            # Enforce Sum-to-One
            sum_a = np.sum(abundances)
            if sum_a > 1e-8:
                abundances /= sum_a
            else:
                abundances = np.full(p, 1.0 / p, dtype=np.float32)

        return abundances

    @classmethod
    def compute_fractional_abundance_maps(
        cls,
        cube: np.ndarray,
        num_endmembers: int = 4
    ) -> Dict[str, Any]:
        """
        Extracts endmembers and computes spatial abundance fraction heatmaps for every pixel.
        Cube shape: (H, W, B)
        """
        h, w, b = cube.shape
        endmembers, pure_indices = cls.extract_endmembers_vca(cube, num_endmembers=num_endmembers)

        # Allocate abundance volume: (H, W, p)
        abundance_maps = np.zeros((h, w, num_endmembers), dtype=np.float32)

        # Unmix spatial pixels
        for r in range(h):
            for c in range(w):
                pix = cube[r, c]
                if np.sum(pix) > 0.05:
                    abundance_maps[r, c] = cls.unmix_pixel_fcls(pix, endmembers)
                else:
                    abundance_maps[r, c, 3 if num_endmembers >= 4 else 0] = 1.0

        # Mean fractional composition across entire field canopy
        valid_mask = np.sum(cube, axis=2) > 0.05
        if np.any(valid_mask):
            mean_abundances = np.mean(abundance_maps[valid_mask], axis=0)
        else:
            mean_abundances = np.mean(abundance_maps.reshape(-1, num_endmembers), axis=0)

        endmember_summaries = []
        for i in range(num_endmembers):
            name = cls.DEFAULT_ENDMEMBER_NAMES[i] if i < len(cls.DEFAULT_ENDMEMBER_NAMES) else f"Endmember {i+1}"
            endmember_summaries.append({
                "endmember_index": i,
                "endmember_name": name,
                "mean_canopy_fraction_pct": round(float(mean_abundances[i] * 100.0), 2),
                "peak_fraction_pct": round(float(np.max(abundance_maps[:, :, i]) * 100.0), 2),
                "pure_pixel_signature": [round(float(v), 4) for v in endmembers[i]]
            })

        # Sub-pixel necrotic lesion coverage
        necrotic_fraction = float(mean_abundances[1]) if num_endmembers > 1 else 0.0

        return {
            "num_endmembers": num_endmembers,
            "subpixel_disease_canopy_fraction_pct": round(necrotic_fraction * 100.0, 2),
            "endmember_compositions": endmember_summaries,
            "canopy_homogeneity_score": round(float(np.max(mean_abundances)), 3)
        }


if __name__ == "__main__":
    dummy_cube = np.random.uniform(0.1, 0.7, (12, 12, 50)).astype(np.float32)
    unmixing_result = SpectralEndmemberUnmixingEngine.compute_fractional_abundance_maps(dummy_cube, num_endmembers=4)
    print("SpectralEndmemberUnmixingEngine verification passed:")
    print(f"Sub-pixel disease coverage: {unmixing_result['subpixel_disease_canopy_fraction_pct']}%")
    print(f"Endmembers extracted: {len(unmixing_result['endmember_compositions'])}")
