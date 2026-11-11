import unittest
import numpy as np
import sys
import os

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.preprocessing.cube_parser import HyperspectralCubeParser
from app.preprocessing.spectral_engine import SpectralAnalysisEngine
from app.inference.disease_classifier import HyperspectralDiseaseClassifier
from app.forecasting.crop_stress_engine import EarlyCropStressEngine
from app.forecasting.forecasting_engine import CropDiseaseForecastingEngine
from app.explainability.xai_engine import ExplainableAIEngine

class TestTerraSpectraScientificEngine(unittest.TestCase):

    def setUp(self):
        self.classifier = HyperspectralDiseaseClassifier()
        self.wavelengths = np.linspace(400, 1000, 100).tolist()
        # Synthetic test cube: 10x10 pixels with 100 spectral bands
        self.cube = np.random.uniform(0.1, 0.7, (10, 10, 100)).astype(np.float32)

    def test_spectral_signature_extraction(self):
        sig = SpectralAnalysisEngine.extract_mean_spectral_signature(self.cube)
        self.assertEqual(len(sig), 100)
        self.assertTrue(np.all(sig >= 0.0) and np.all(sig <= 1.0))

    def test_narrowband_indices_computation(self):
        sig = SpectralAnalysisEngine.extract_mean_spectral_signature(self.cube)
        indices = SpectralAnalysisEngine.compute_spectral_indices(sig, self.wavelengths)
        for key in ["NDVI", "NDRE", "PRI", "PSRI", "WBI", "MCARI"]:
            self.assertIn(key, indices)
            self.assertIsInstance(indices[key], float)

    def test_disease_classification_inference(self):
        sig = SpectralAnalysisEngine.extract_mean_spectral_signature(self.cube)
        res = self.classifier.predict(sig, self.wavelengths)
        self.assertIn("predicted_condition", res)
        self.assertIn("confidence", res)
        self.assertIn(res["predicted_condition"], self.classifier.CLASSES)
        self.assertGreaterEqual(res["confidence"], 0.0)
        self.assertLessEqual(res["confidence"], 1.0)

    def test_early_crop_stress_analysis(self):
        sig = SpectralAnalysisEngine.extract_mean_spectral_signature(self.cube)
        indices = SpectralAnalysisEngine.compute_spectral_indices(sig, self.wavelengths)
        stress = EarlyCropStressEngine.analyze_stress_indicators(sig, self.wavelengths, indices)
        self.assertIn("composite_stress_score", stress)
        self.assertIn("stress_level", stress)
        self.assertTrue(0.0 <= stress["composite_stress_score"] <= 1.0)

    def test_forecasting_engine(self):
        forecast = CropDiseaseForecastingEngine.forecast_7_day_risk(
            crop_type="Wheat (Triticum aestivum)",
            current_stress_score=0.45,
            historical_spectral_trend=[0.35, 0.40, 0.45],
            weather_forecast_days=[]
        )
        self.assertEqual(forecast["forecast_horizon_days"], 7)
        self.assertEqual(len(forecast["trajectory"]), 7)
        self.assertIn("peak_risk_level", forecast)

    def test_xai_attribution(self):
        sig = SpectralAnalysisEngine.extract_mean_spectral_signature(self.cube)
        xai = ExplainableAIEngine.compute_band_importance(
            sig, self.wavelengths, "Stripe Rust", self.classifier.rf_model
        )
        self.assertIn("top_influential_wavelengths", xai)
        self.assertEqual(len(xai["top_influential_wavelengths"]), 10)
        self.assertIn("explainability_summary", xai)

if __name__ == "__main__":
    unittest.main()

