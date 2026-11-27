import os
import sys
import unittest
import numpy as np

# Ensure backend modules are on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.spectral_anomaly_detector import SpectralAnomalyDetector
from services.spectral_unmixing_engine import SpectralEndmemberUnmixingEngine
from forecasting.epidemiology_model import MicroclimaticEpidemiologyModel
from geospatial.zonal_statistics import SpatialZonalStatisticsEngine


class TestAdvancedScientificServices(unittest.TestCase):
    """
    Validation test suite for TerraSpectra's advanced scientific engines:
      1. Reed-Xiaoli (RX) Anomaly Detection & Red-Edge Biomarkers
      2. Vertex Component Analysis (VCA) & FCLS Spectral Unmixing
      3. Yan & Hunt Microclimatic Disease Epidemiology Model
      4. Spatial Zonal Statistics & Local Moran's I Hotspot Detection
    """

    def setUp(self):
        np.random.seed(42)
        self.h, self.w, self.b = 16, 16, 50
        self.mock_cube = np.random.uniform(0.1, 0.7, (self.h, self.w, self.b)).astype(np.float32)
        self.wavelengths = list(np.linspace(400.0, 1000.0, self.b))

    def test_reed_xiaoli_anomaly_detection(self):
        """Verify RX anomaly detector computes valid normalized Mahalanobis distances."""
        rx_map = SpectralAnomalyDetector.compute_rx_anomaly(self.mock_cube)
        self.assertEqual(rx_map.shape, (self.h, self.w))
        self.assertGreaterEqual(float(np.min(rx_map)), 0.0)
        self.assertLessEqual(float(np.max(rx_map)), 1.0)

    def test_spectral_biomarkers_extraction(self):
        """Verify extraction of Red-Edge Position (REP) and foliar water absorption depth."""
        mean_sig = np.mean(self.mock_cube, axis=(0, 1))
        biomarkers = SpectralAnomalyDetector.extract_biomarker_fingerprints(mean_sig, self.wavelengths)
        
        self.assertIn("red_edge_position_nm", biomarkers)
        self.assertIn("water_absorption_depth_970nm", biomarkers)
        self.assertIn("red_edge_status", biomarkers)
        self.assertTrue(680.0 <= biomarkers["red_edge_position_nm"] <= 760.0)

    def test_vca_endmember_extraction(self):
        """Verify Vertex Component Analysis extracts the requested number of pure endmembers."""
        num_em = 3
        endmembers, indices = SpectralEndmemberUnmixingEngine.extract_endmembers_vca(
            self.mock_cube, num_endmembers=num_em
        )
        self.assertEqual(endmembers.shape, (num_em, self.b))
        self.assertEqual(len(indices), num_em)

    def test_fcls_pixel_unmixing(self):
        """Verify FCLS unmixing satisfies Abundance Non-negativity and Sum-to-One constraints."""
        num_em = 4
        endmembers, _ = SpectralEndmemberUnmixingEngine.extract_endmembers_vca(
            self.mock_cube, num_endmembers=num_em
        )
        sample_pixel = self.mock_cube[0, 0]
        abundances = SpectralEndmemberUnmixingEngine.unmix_pixel_fcls(sample_pixel, endmembers)
        
        self.assertEqual(len(abundances), num_em)
        self.assertTrue(np.all(abundances >= 0.0), "Abundances must be non-negative")
        self.assertAlmostEqual(float(np.sum(abundances)), 1.0, places=4, msg="Abundances must sum to 1.0")

    def test_thermal_kinetics_epidemiology(self):
        """Verify Yan & Hunt cardinal development rates for crop pathogens."""
        # Stripe Rust optimal temperature is ~16C
        opt_rate = MicroclimaticEpidemiologyModel.compute_thermal_kinetics(16.0, "stripe_rust")
        cold_rate = MicroclimaticEpidemiologyModel.compute_thermal_kinetics(1.0, "stripe_rust")
        hot_rate = MicroclimaticEpidemiologyModel.compute_thermal_kinetics(26.0, "stripe_rust")
        
        self.assertGreater(opt_rate, 0.8)
        self.assertEqual(cold_rate, 0.0)
        self.assertEqual(hot_rate, 0.0)

    def test_multiday_epidemiological_forecast(self):
        """Verify multi-day forecast produces valid daily infection trajectory with leaf wetness hours."""
        sample_weather = [
            {"date": "2026-11-27", "temp": 18.0, "humidity": 85.0, "rain": 5.0},
            {"date": "2026-11-28", "temp": 20.0, "humidity": 75.0, "rain": 0.0}
        ]
        forecast = MicroclimaticEpidemiologyModel.generate_multiday_epidemiological_forecast(
            sample_weather, initial_stress_score=0.4
        )
        self.assertEqual(len(forecast), 2)
        self.assertIn("composite_daily_risk", forecast[0])
        self.assertIn("leaf_wetness_duration_hours", forecast[0]["microclimate"])
        self.assertTrue(0.0 <= forecast[0]["composite_daily_risk"] <= 1.0)

    def test_local_morans_i_hotspot_detection(self):
        """Verify spatial autocorrelation classifies cells into hotspots and coldspots."""
        grid = np.array([
            [0.8, 0.9, 0.85, 0.1, 0.1],
            [0.9, 0.95, 0.88, 0.12, 0.08],
            [0.85, 0.9, 0.8, 0.15, 0.1],
            [0.1, 0.12, 0.14, 0.05, 0.08],
            [0.08, 0.05, 0.09, 0.07, 0.06]
        ], dtype=np.float32)
        
        cluster_map, counts = SpatialZonalStatisticsEngine.compute_local_morans_i(grid)
        self.assertEqual(cluster_map.shape, grid.shape)
        self.assertGreater(counts["high_high_hotspot"], 0)
        self.assertGreater(counts["low_low_healthy"], 0)

    def test_management_zones_geojson_generation(self):
        """Verify GeoJSON FeatureCollection generation with variable rate prescription dosage."""
        bounds = (74.2150, 16.6850, 74.2550, 16.7250)
        geojson = SpatialZonalStatisticsEngine.generate_management_zones_geojson(bounds, grid_dim=4, base_stress=0.5)
        
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(len(geojson["features"]), 16)
        prop = geojson["features"][0]["properties"]
        self.assertIn("recommended_dosage_l_ha", prop)
        self.assertIn("priority", prop)


if __name__ == "__main__":
    unittest.main()
