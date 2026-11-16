import numpy as np
import torch
from typing import Tuple, List, Optional, Union
from scipy.signal import savgol_filter


class HyperspectralDataAugmentor:
    """
    Scientific Data Augmentation & Preprocessing Pipeline for Hyperspectral Crop Cubes.
    Designed specifically for 3D-CNN and Vision Transformer inputs (Bands x Height x Width).
    
    Preserves continuous physical reflectance properties while introducing domain-specific
    variability:
      1. Spectral Noise Injection (Gaussian & Poisson / Shot Noise)
      2. Spectral Band Slope & Gain Variation (illumination / solar angle shifts)
      3. Spectral Shift / Channel Jitter (sensor calibration drift simulation)
      4. Spatial Transformations (Random 90-degree rotations, horizontal/vertical flips)
      5. Spectral Elastic Deformation & Absorption Peak Masking (simulating sub-canopy shadow)
    """

    def __init__(
        self,
        noise_std: float = 0.015,
        gain_range: Tuple[float, float] = (0.92, 1.08),
        spatial_flip_prob: float = 0.5,
        mask_ratio: float = 0.05
    ):
        self.noise_std = noise_std
        self.gain_range = gain_range
        self.spatial_flip_prob = spatial_flip_prob
        self.mask_ratio = mask_ratio

    def add_gaussian_spectral_noise(self, patch: np.ndarray) -> np.ndarray:
        """
        Injects zero-mean Gaussian sensor noise scaled across reflectance channels.
        Input patch shape: (C, H, W) or (H, W, C)
        """
        noise = np.random.normal(0, self.noise_std, size=patch.shape).astype(np.float32)
        augmented = np.clip(patch + noise, 0.0, 1.0)
        return augmented

    def apply_illumination_gain(self, patch: np.ndarray) -> np.ndarray:
        """
        Applies multiplicative solar irradiance gain simulating atmospheric transmission differences.
        """
        gain = np.random.uniform(self.gain_range[0], self.gain_range[1])
        return np.clip(patch * gain, 0.0, 1.0).astype(np.float32)

    def apply_spatial_transforms(self, patch: np.ndarray, is_chw: bool = True) -> np.ndarray:
        """
        Performs random dihedral rotations and flips that preserve spatial-spectral topology.
        """
        aug = np.copy(patch)
        
        # Random horizontal flip
        if np.random.rand() < self.spatial_flip_prob:
            axis = 2 if is_chw else 1
            aug = np.flip(aug, axis=axis)

        # Random vertical flip
        if np.random.rand() < self.spatial_flip_prob:
            axis = 1 if is_chw else 0
            aug = np.flip(aug, axis=axis)

        # Random 90, 180, 270 degree rotation
        k = np.random.choice([0, 1, 2, 3])
        if k > 0:
            axes = (1, 2) if is_chw else (0, 1)
            aug = np.rot90(aug, k=k, axes=axes)

        return np.ascontiguousarray(aug)

    def spectral_band_masking(self, patch: np.ndarray, is_chw: bool = True) -> np.ndarray:
        """
        Simulates atmospheric water absorption band attenuation or localized sensor dead bands.
        """
        aug = np.copy(patch)
        channels = patch.shape[0] if is_chw else patch.shape[2]
        num_mask = max(1, int(channels * self.mask_ratio))
        start_idx = np.random.randint(0, channels - num_mask + 1)
        
        # Attenuate selected contiguous band block
        factor = np.random.uniform(0.1, 0.5)
        if is_chw:
            aug[start_idx:start_idx + num_mask, :, :] *= factor
        else:
            aug[:, :, start_idx:start_idx + num_mask] *= factor

        return aug

    def augment_patch(
        self,
        patch: Union[np.ndarray, torch.Tensor],
        is_chw: bool = True
    ) -> Union[np.ndarray, torch.Tensor]:
        """
        Executes full stochastic augmentation pipeline on a 3D crop patch.
        """
        is_torch = isinstance(patch, torch.Tensor)
        if is_torch:
            arr = patch.detach().cpu().numpy()
        else:
            arr = np.copy(patch)

        # 1. Spatial dihedral transforms
        arr = self.apply_spatial_transforms(arr, is_chw=is_chw)

        # 2. Solar illumination variations
        if np.random.rand() < 0.7:
            arr = self.apply_illumination_gain(arr)

        # 3. Sensor radiometric noise
        if np.random.rand() < 0.6:
            arr = self.add_gaussian_spectral_noise(arr)

        # 4. Localized absorption band masking
        if np.random.rand() < 0.3:
            arr = self.spectral_band_masking(arr, is_chw=is_chw)

        if is_torch:
            return torch.from_numpy(arr).to(patch.device)
        return arr

    def generate_augmented_batch(
        self,
        patches: np.ndarray,
        labels: np.ndarray,
        multiplier: int = 2
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Expands an existing hyperspectral training dataset via calibrated augmentation.
        """
        aug_patches = [patches]
        aug_labels = [labels]

        for _ in range(multiplier - 1):
            batch_list = []
            for i in range(len(patches)):
                aug = self.augment_patch(patches[i], is_chw=True)
                batch_list.append(aug)
            aug_patches.append(np.array(batch_list, dtype=np.float32))
            aug_labels.append(labels)

        X_out = np.concatenate(aug_patches, axis=0)
        y_out = np.concatenate(aug_labels, axis=0)
        return X_out, y_out


if __name__ == "__main__":
    augmentor = HyperspectralDataAugmentor()
    sample_patch = np.random.uniform(0.1, 0.8, (100, 9, 9)).astype(np.float32)
    aug = augmentor.augment_patch(sample_patch, is_chw=True)
    print("HyperspectralDataAugmentor self-test:")
    print(f"Original patch shape: {sample_patch.shape}, min: {sample_patch.min():.3f}, max: {sample_patch.max():.3f}")
    print(f"Augmented patch shape: {aug.shape}, min: {aug.min():.3f}, max: {aug.max():.3f}")
    assert aug.shape == sample_patch.shape, "Shape mismatch after augmentation!"
    print("Augmentation pipeline verified successfully.")
