import unittest
import numpy as np
import io
import os
import tifffile

from app.services.hyperspectral_loader import HyperspectralCubeLoader
from app.services.spectral_preprocessing import SpectralPreprocessingPipeline
from app.services.spectral_analysis import SpectralAnalysisService


class TestHyperspectralIngestionPipeline(unittest.TestCase):
    """
    Test suite for Hyperspectral Data Cube Ingestion, Preprocessing,
    and Spectral Analysis services.
    """

    def setUp(self):
        # 1. Generate synthetic 3D NumPy cube (64x64, 50 bands)
        self.h, self.w, self.b = 32, 32, 50
        self.mock_cube = np.random.uniform(0.1, 0.8, size=(self.h, self.w, self.b)).astype(np.float32)

        # 2. ENVI mock data
        self.envi_hdr = f"""ENVI
description = {{Synthetic Agricultural VNIR Cube}}
samples = {self.w}
lines = {self.h}
bands = {self.b}
header offset = 0
file type = ENVI Standard
data type = 4
interleave = bsq
byte order = 0
wavelength units = nm
"""
        self.envi_raw = self.mock_cube.transpose((2, 0, 1)).astype(np.float32).tobytes()

    def test_numpy_cube_ingestion(self):
        bio = io.BytesIO()
        np.save(bio, self.mock_cube)
        bio.seek(0)

        cube, meta = HyperspectralCubeLoader.load_numpy_cube(bio.read(), "test_cube.npy")
        self.assertEqual(cube.shape, (self.h, self.w, self.b))
        self.assertEqual(meta.bands_count, 50)
        self.assertTrue(meta.is_valid_hyperspectral)
        self.assertEqual(len(meta.wavelengths), 50)
        self.assertAlmostEqual(meta.wavelengths[0], 400.0, delta=1.0)
        self.assertAlmostEqual(meta.wavelengths[-1], 1000.0, delta=1.0)

    def test_rejection_of_rgb_three_band_image(self):
        rgb_cube = np.random.uniform(0, 1, size=(32, 32, 3)).astype(np.float32)
        bio = io.BytesIO()
        np.save(bio, rgb_cube)
        bio.seek(0)

        with self.assertRaises(ValueError) as ctx:
            HyperspectralCubeLoader.load_numpy_cube(bio.read(), "rgb_invalid.npy")
        self.assertIn("Insufficient spectral bands", str(ctx.exception))

    def test_envi_pair_ingestion(self):
        cube, meta = HyperspectralCubeLoader.load_envi_cube(self.envi_raw, self.envi_hdr, "wheat_envi.raw")
        self.assertEqual(cube.shape, (self.h, self.w, self.b))
        self.assertEqual(meta.bands_count, 50)
        self.assertIn("ENVI (BSQ)", meta.format)
        self.assertTrue(meta.is_valid_hyperspectral)

    def test_geotiff_multiband_ingestion(self):
        bio = io.BytesIO()
        tifffile.imwrite(bio, self.mock_cube)
        bio.seek(0)

        cube, meta = HyperspectralCubeLoader.load_geotiff_cube(bio.read(), "specimen_geotiff.tif")
        self.assertEqual(cube.shape, (self.h, self.w, self.b))
        self.assertEqual(meta.bands_count, 50)
        self.assertIn("GeoTIFF", meta.format)

    def test_spectral_preprocessing_savitzky_golay(self):
        noisy_sig = np.sin(np.linspace(0, np.pi, 50)) + np.random.normal(0, 0.05, 50)
        smoothed = SpectralPreprocessingPipeline.apply_savitzky_golay(noisy_sig, window_length=7, polyorder=2)
        self.assertEqual(len(smoothed), 50)
        self.assertTrue(np.all(smoothed >= 0.0))

    def test_continuum_removal(self):
        sig = np.sin(np.linspace(0.2, 0.8, 50))
        cr = SpectralPreprocessingPipeline.apply_continuum_removal(sig)
        self.assertEqual(len(cr), 50)
        self.assertTrue(np.all(cr <= 1.0001))
        self.assertTrue(np.all(cr >= 0.0))

    def test_pca_dimensionality_reduction(self):
        pca_res = SpectralPreprocessingPipeline.compute_pca(self.mock_cube, n_components=3)
        self.assertEqual(len(pca_res["explained_variance_ratio"]), 3)
        self.assertTrue(0.0 <= pca_res["total_explained_variance"] <= 1.0)
        self.assertTrue(len(pca_res["sample_scatter"]) > 0)

    def test_vegetation_indices_calculation(self):
        wavelengths = list(np.linspace(400.0, 1000.0, 50))
        sig = np.full(50, 0.4, dtype=np.float32)
        # Give higher reflectance at 800nm than 670nm to mimic vegetation
        idx_800 = int(np.argmin(np.abs(np.array(wavelengths) - 800.0)))
        idx_670 = int(np.argmin(np.abs(np.array(wavelengths) - 670.0)))
        sig[idx_800] = 0.8
        sig[idx_670] = 0.2

        indices = SpectralAnalysisService.compute_vegetation_indices(sig, wavelengths)
        self.assertIn("NDVI", indices)
        self.assertIn("NDRE", indices)
        self.assertIn("PRI", indices)
        self.assertIn("PSRI", indices)
        self.assertIn("WBI", indices)
        self.assertIn("MCARI", indices)
        self.assertGreater(indices["NDVI"], 0.5)


if __name__ == "__main__":
    unittest.main()

