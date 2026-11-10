import numpy as np
import os
from typing import Generator, Tuple, Dict, Any, List

class LargeRasterTilingEngine:
    """
    Memory-efficient chunked raster processing for large hyperspectral scenes.
    Slices large multi-gigabyte spatial-spectral cubes into overlapping spatial tiles,
    runs batch inference without Out-Of-Memory (OOM) errors, and reconstructs the full-scene risk map.
    """

    def __init__(self, tile_size: int = 64, overlap: int = 8, batch_size: int = 4):
        self.tile_size = tile_size
        self.overlap = overlap
        self.batch_size = batch_size
        self.stride = tile_size - overlap

    def generate_spatial_tiles(self, cube: np.ndarray) -> Generator[Tuple[int, int, np.ndarray], None, None]:
        """
        Yields (top_y, left_x, tile_cube) where tile_cube has shape (tile_size, tile_size, Bands).
        Pads edges symmetrically if spatial bounds are not divisible by stride.
        """
        h, w, b = cube.shape
        pad_h = (self.stride - (h % self.stride)) % self.stride
        pad_w = (self.stride - (w % self.stride)) % self.stride

        if pad_h > 0 or pad_w > 0:
            padded_cube = np.pad(cube, ((0, pad_h), (0, pad_w), (0, 0)), mode='reflect')
        else:
            padded_cube = cube

        p_h, p_w, _ = padded_cube.shape

        for y in range(0, p_h - self.tile_size + 1, self.stride):
            for x in range(0, p_w - self.tile_size + 1, self.stride):
                tile = padded_cube[y:y + self.tile_size, x:x + self.tile_size, :]
                yield (y, x, tile)

    def reconstruct_scene_risk(
        self,
        original_shape: Tuple[int, int],
        tile_predictions: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Blends overlapping tile inferences using distance-weighted averaging
        to prevent seam artifacts across spatial boundaries.
        """
        orig_h, orig_w = original_shape
        accum_risk = np.zeros((orig_h + self.tile_size, orig_w + self.tile_size), dtype=np.float32)
        weight_mask = np.zeros((orig_h + self.tile_size, orig_w + self.tile_size), dtype=np.float32)

        # 2D linear blending window
        window_1d = np.hanning(self.tile_size)
        window_2d = np.outer(window_1d, window_1d)

        for item in tile_predictions:
            y, x = item["y"], item["x"]
            risk_tile = item["risk_map"]  # (tile_size, tile_size)
            accum_risk[y:y + self.tile_size, x:x + self.tile_size] += risk_tile * window_2d
            weight_mask[y:y + self.tile_size, x:x + self.tile_size] += window_2d

        # Normalize overlapping blends
        weight_mask = np.maximum(weight_mask, 1e-5)
        blended_scene = accum_risk[:orig_h, :orig_w] / weight_mask[:orig_h, :orig_w]
        return np.clip(blended_scene, 0.0, 1.0)
