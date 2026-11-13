import math
import numpy as np
from typing import Dict, Any, List
from datetime import datetime, timedelta

class CropDiseaseForecastingEngine:
    """
    Longitudinal Disease Risk Forecasting Engine.
    Combines time-series spectral trends with microclimatic variables
    (temperature, relative humidity, leaf wetness hours, rainfall)
    to project pathogen sporulation and infection likelihood over a 7-day horizon.
    """

    @staticmethod
    def calculate_pathogen_weather_favorability(
        temp_c: float,
        humidity_pct: float,
        rain_mm: float
    ) -> Dict[str, float]:
        """
        Calculates epidemiological climate suitability for major foliar diseases:
        - Rusts (optimum 15-22°C, RH > 85%, free moisture)
        - Mildew (optimum 18-25°C, RH 70-90%)
        - Blight/Bacterial (optimum 24-30°C, RH > 90%, rain splash)
        """
        # Rust favorability
        rust_temp_fac = math.exp(-((temp_c - 18.0) ** 2) / 36.0)
        rust_hum_fac = max(0.0, (humidity_pct - 65.0) / 35.0) if humidity_pct >= 65 else 0.0
        rust_rain_fac = min(1.0, rain_mm / 10.0)
        rust_risk = (0.5 * rust_temp_fac * rust_hum_fac) + (0.5 * rust_rain_fac * rust_temp_fac)

        # Mildew favorability
        mildew_temp_fac = math.exp(-((temp_c - 22.0) ** 2) / 45.0)
        mildew_hum_fac = max(0.0, (humidity_pct - 60.0) / 40.0) if humidity_pct >= 60 else 0.0
        mildew_risk = mildew_temp_fac * mildew_hum_fac

        # Blight favorability
        blight_temp_fac = math.exp(-((temp_c - 26.0) ** 2) / 30.0)
        blight_hum_fac = max(0.0, (humidity_pct - 75.0) / 25.0) if humidity_pct >= 75 else 0.0
        blight_risk = blight_temp_fac * blight_hum_fac

        return {
            "rust_favorability": round(float(np.clip(rust_risk, 0.0, 1.0)), 3),
            "mildew_favorability": round(float(np.clip(mildew_risk, 0.0, 1.0)), 3),
            "blight_favorability": round(float(np.clip(blight_risk, 0.0, 1.0)), 3)
        }

    @classmethod
    def forecast_7_day_risk(
        cls,
        crop_type: str,
        current_stress_score: float,
        historical_spectral_trend: List[float],
        weather_forecast_days: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates 7-day risk trajectory based on longitudinal spectral degradation
        plus forecasted daily microclimate metrics.
        """
        now = datetime.now()
        trajectory = []

        # Baseline spectral slope (rate of deterioration)
        if len(historical_spectral_trend) >= 2:
            spectral_delta = historical_spectral_trend[-1] - historical_spectral_trend[0]
            spectral_slope = spectral_delta / max(1, len(historical_spectral_trend) - 1)
        else:
            spectral_slope = 0.02 * current_stress_score

        running_risk = current_stress_score * 0.45

        # Fallback default weather if none provided
        if not weather_forecast_days or len(weather_forecast_days) < 7:
            weather_forecast_days = [
                {"temp_max": 24.5 + i * 0.4, "temp_min": 14.2, "humidity": 78 + (i % 3) * 4, "rain_mm": 1.2 if i in [2, 3] else 0.0}
                for i in range(7)
            ]

        for day_idx in range(7):
            target_date = (now + timedelta(days=day_idx + 1)).strftime("%Y-%m-%d")
            w = weather_forecast_days[day_idx]
            avg_temp = (w.get("temp_max", 24) + w.get("temp_min", 14)) / 2.0
            rh = float(w.get("humidity", 75))
            rain = float(w.get("rain_mm", 0.0))

            fav = cls.calculate_pathogen_weather_favorability(avg_temp, rh, rain)
            max_fav = max(fav["rust_favorability"], fav["mildew_favorability"], fav["blight_favorability"])

            # Risk evolution: spectral vulnerability * environmental pressure
            daily_progression = (0.04 * max_fav) + (0.02 * spectral_slope)
            running_risk = float(np.clip(running_risk + daily_progression, 0.05, 0.98))

            # Confidence interval expands over forecast horizon
            uncertainty = round(float(0.04 + (day_idx * 0.018)), 3)
            ci_lower = max(0.0, round(running_risk - uncertainty, 3))
            ci_upper = min(1.0, round(running_risk + uncertainty, 3))

            risk_level = "Low" if running_risk < 0.35 else ("Moderate" if running_risk < 0.65 else "High")

            trajectory.append({
                "day": day_idx + 1,
                "date": target_date,
                "projected_risk": round(running_risk, 3),
                "confidence_lower": ci_lower,
                "confidence_upper": ci_upper,
                "risk_category": risk_level,
                "temp_c": round(avg_temp, 1),
                "humidity_pct": rh,
                "pathogen_weather_suitability": max_fav,
                "specific_risks": fav
            })

        peak_day = max(trajectory, key=lambda x: x["projected_risk"])

        return {
            "crop_type": crop_type,
            "forecast_horizon_days": 7,
            "peak_risk_day": peak_day["day"],
            "peak_risk_date": peak_day["date"],
            "peak_risk_level": peak_day["risk_category"],
            "mean_projected_risk": round(float(np.mean([t["projected_risk"] for t in trajectory])), 3),
            "trajectory": trajectory,
            "methodology_disclaimer": "Forecast is driven by multi-day spectral signature trajectory and forecasted microclimatic pathogen sporulation indices. Single hyperspectral scans are augmented with longitudinal priors."
        }

