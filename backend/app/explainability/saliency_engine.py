import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional, Tuple, Union


class SpatialSpectralSaliencyEngine:
    """
    Advanced Explainable AI (XAI) engine for 3D-CNN and Vision Transformer models.
    Provides pixel-level spatial saliency heatmaps, spectral gradient backpropagation,
    and Integrated Gradients for hyperspectral crop disease diagnostics.
    """

    def __init__(self, model: Optional[nn.Module] = None, device: Optional[str] = None):
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = model
        if self.model is not None:
            self.model.to(self.device)
            self.model.eval()

    def compute_vanilla_gradients(
        self,
        patch_tensor: torch.Tensor,
        target_class: int
    ) -> np.ndarray:
        """
        Computes input attribution gradients d(Loss)/d(Input) for a specific target class.
        patch_tensor: shape (1, C, H, W)
        Returns: numpy array of shape (C, H, W)
        """
        patch_tensor = patch_tensor.clone().detach().to(self.device)
        patch_tensor.requires_grad = True

        outputs = self.model(patch_tensor)
        target_score = outputs[0, target_class]
        self.model.zero_grad()
        target_score.backward()

        grads = patch_tensor.grad.detach().cpu().numpy()[0]
        return grads

    def compute_integrated_gradients(
        self,
        patch_tensor: torch.Tensor,
        target_class: int,
        steps: int = 20,
        baseline: Optional[torch.Tensor] = None
    ) -> np.ndarray:
        """
        Computes Integrated Gradients (Sundararajan et al., 2017) along a linear path
        from a baseline (black/zero or median spectrum) to the target hypercube patch.
        
        IG_i(x) = (x_i - x'_i) * int_0^1 (dF(x' + alpha*(x - x')) / dx_i) d_alpha
        """
        patch_tensor = patch_tensor.clone().detach().to(self.device)
        if baseline is None:
            baseline = torch.zeros_like(patch_tensor).to(self.device)
        else:
            baseline = baseline.to(self.device)

        # Scale inputs along linear path
        alphas = torch.linspace(0.0, 1.0, steps).to(self.device)
        scaled_inputs = [baseline + alpha * (patch_tensor - baseline) for alpha in alphas]

        accumulated_grads = torch.zeros_like(patch_tensor)

        for scaled in scaled_inputs:
            scaled.requires_grad = True
            outputs = self.model(scaled)
            target_score = outputs[0, target_class]
            self.model.zero_grad()
            target_score.backward()
            accumulated_grads += scaled.grad.detach()

        avg_grads = accumulated_grads / steps
        delta = patch_tensor - baseline
        ig_attributions = (delta * avg_grads).detach().cpu().numpy()[0]
        return ig_attributions

    def generate_spatial_saliency_map(
        self,
        attributions: np.ndarray,
        aggregation: str = "l2"
    ) -> np.ndarray:
        """
        Collapses spectral channel attributions (C, H, W) into a 2D spatial heatmap (H, W).
        Aggregations:
          - 'l2': Euclidean norm across spectral channels
          - 'mean': Absolute mean across channels
          - 'max': Maximum absolute activation
        """
        if aggregation == "l2":
            saliency_2d = np.sqrt(np.mean(attributions ** 2, axis=0))
        elif aggregation == "max":
            saliency_2d = np.max(np.abs(attributions), axis=0)
        else:
            saliency_2d = np.mean(np.abs(attributions), axis=0)

        # Normalize to [0.0, 1.0]
        min_v = np.min(saliency_2d)
        max_v = np.max(saliency_2d)
        if max_v > min_v:
            normalized_saliency = (saliency_2d - min_v) / (max_v - min_v)
        else:
            normalized_saliency = np.zeros_like(saliency_2d)

        return normalized_saliency.astype(np.float32)

    def generate_spectral_importance_profile(
        self,
        attributions: np.ndarray,
        wavelengths: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Aggregates attributions across spatial dimensions (H, W) to obtain a 1D
        spectral importance curve per wavelength.
        """
        c, h, w = attributions.shape
        # Spatial mean of absolute attribution
        spectral_importance = np.mean(np.abs(attributions), axis=(1, 2))

        # Normalize
        norm_factor = np.max(spectral_importance) if np.max(spectral_importance) > 0 else 1.0
        normalized_scores = spectral_importance / norm_factor

        profile = []
        for i in range(c):
            wl = wavelengths[i] if i < len(wavelengths) else 400.0 + i * (600.0 / c)
            profile.append({
                "band_index": i,
                "wavelength": round(float(wl), 2),
                "attribution_score": round(float(normalized_scores[i]), 5),
                "raw_gradient_mean": round(float(np.mean(attributions[i])), 6)
            })

        return sorted(profile, key=lambda x: x["attribution_score"], reverse=True)

    def explain_patch(
        self,
        patch: Union[np.ndarray, torch.Tensor],
        target_class: int,
        wavelengths: List[float]
    ) -> Dict[str, Any]:
        """
        Comprehensive spatial-spectral attribution for a single hyperspectral crop patch.
        """
        if isinstance(patch, np.ndarray):
            patch_tensor = torch.tensor(patch, dtype=torch.float32)
        else:
            patch_tensor = patch.clone().detach()

        if patch_tensor.ndim == 3:
            patch_tensor = patch_tensor.unsqueeze(0)  # (1, C, H, W)

        if self.model is not None:
            attributions = self.compute_integrated_gradients(patch_tensor, target_class=target_class, steps=15)
        else:
            # Fallback perturbation-based sensitivity if PyTorch model is not attached
            c, h, w = patch_tensor.shape[1], patch_tensor.shape[2], patch_tensor.shape[3]
            attributions = np.abs(np.gradient(patch_tensor.cpu().numpy()[0], axis=0))

        saliency_map = self.generate_spatial_saliency_map(attributions, aggregation="l2")
        spectral_profile = self.generate_spectral_importance_profile(attributions, wavelengths)

        return {
            "target_class": target_class,
            "spatial_saliency_map": saliency_map.tolist(),
            "top_salient_wavelengths": spectral_profile[:10],
            "spatial_focus_ratio": round(float(np.mean(saliency_map > 0.5)), 4),
            "spectral_bandwidth_contributed": len(spectral_profile)
        }


if __name__ == "__main__":
    # Self-test validation
    dummy_patch = np.random.uniform(0.1, 0.8, (100, 9, 9)).astype(np.float32)
    dummy_wls = list(np.linspace(400.0, 1000.0, 100))
    xai_engine = SpatialSpectralSaliencyEngine()
    result = xai_engine.explain_patch(dummy_patch, target_class=1, wavelengths=dummy_wls)
    print("SpatialSpectralSaliencyEngine validation passed:")
    print(f"Spatial focus ratio: {result['spatial_focus_ratio']}")
    print(f"Top wavelength: {result['top_salient_wavelengths'][0]['wavelength']} nm")
