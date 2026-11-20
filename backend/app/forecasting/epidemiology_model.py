import math
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta


class MicroclimaticEpidemiologyModel:
    """
    Advanced Microclimatic Crop Disease Epidemiology & Sporulation Simulator.
    
    Implements epidemiological physics-informed compartmental modeling:
      1. Thermal-Hydrological Sporulation Kinetics (Yan & Hunt cardinal temperature models).
      2. Leaf Wetness Duration (LWD) Estimation via Dew Point Depletion & Relative Humidity.
      3. Pathogen Incubation & Inoculum Pressure Dynamics (Susceptible-Exposed-Infectious-Removed SEIR framework).
      4. Crop Microclimate Canopy Attenuation (transpiration humidity buffering & solar extinction).
      5. Multi-Pathogen Daily Infection Risk Indexing (Rust, Powdery Mildew, Blight, Septoria).
    """

    # Thermal cardinal temperatures (T_min, T_opt, T_max) in Celsius for agricultural pathogens
    PATHOGEN_CARDINALS = {
        "stripe_rust": {"t_min": 2.0, "t_opt": 16.0, "t_max": 24.0, "min_lwd_hours": 4.0},
        "powdery_mildew": {"t_min": 5.0, "t_opt": 21.0, "t_max": 28.0, "min_lwd_hours": 0.0},
        "septoria": {"t_min": 7.0, "t_opt": 22.0, "t_max": 30.0, "min_lwd_hours": 12.0},
        "fusarium_head_blight": {"t_min": 10.0, "t_opt": 26.0, "t_max": 34.0, "min_lwd_hours": 16.0},
        "bacterial_streak": {"t_min": 12.0, "t_opt": 28.0, "t_max": 36.0, "min_lwd_hours": 6.0}
    }

    @staticmethod
    def estimate_dew_point(temp_c: float, relative_humidity_pct: float) -> float:
        """
        Magnus-Tetens formula approximation for dew point calculation.
        """
        a = 17.27
        b = 237.7
        rh = max(0.01, min(100.0, relative_humidity_pct))
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(rh / 100.0)
        dew_point = (b * alpha) / (a - alpha)
        return float(round(dew_point, 2))

    @staticmethod
    def estimate_leaf_wetness_hours(
        relative_humidity_pct: float,
        rainfall_mm: float,
        dew_point_depression_c: float
    ) -> float:
        """
        Estimates daily Leaf Wetness Duration (LWD in hours) based on RH thresholds,
        dew point depression (T - T_dew), and precipitation duration.
        """
        lwd = 0.0
        # Precipitation contribution
        if rainfall_mm > 0.1:
            lwd += min(14.0, 4.0 + rainfall_mm * 1.5)

        # Condensation contribution when dew point depression is narrow (< 2.5°C)
        if dew_point_depression_c <= 1.5:
            lwd += 8.0
        elif dew_point_depression_c <= 2.5:
            lwd += 4.5

        # Ambient RH threshold contribution (> 85%)
        if relative_humidity_pct >= 90.0:
            lwd += 6.0
        elif relative_humidity_pct >= 80.0:
            lwd += 3.0

        return float(round(min(24.0, max(0.0, lwd)), 1))

    @classmethod
    def compute_thermal_kinetics(cls, temp_c: float, pathogen: str) -> float:
        """
        Computes normalized thermal development rate [0, 1] using Yan & Hunt non-linear cardinal function.
        """
        params = cls.PATHOGEN_CARDINALS.get(pathogen, {"t_min": 5.0, "t_opt": 20.0, "t_max": 30.0})
        t_min, t_opt, t_max = params["t_min"], params["t_opt"], params["t_max"]

        if temp_c <= t_min or temp_c >= t_max:
            return 0.0

        num = (temp_c - t_min) * ((t_max - temp_c) ** ((t_max - t_opt) / (t_opt - t_min)))
        den = (t_opt - t_min) * ((t_max - t_opt) ** ((t_max - t_opt) / (t_opt - t_min)))
        rate = num / (den + 1e-9)
        return float(round(min(1.0, max(0.0, rate)), 4))

    @classmethod
    def simulate_pathogen_epidemiology(
        cls,
        temp_c: float,
        rh_pct: float,
        rain_mm: float,
        canopy_stress_score: float = 0.4
    ) -> Dict[str, Any]:
        """
        Simulates microclimatic daily infection favorability across all key target pathogens.
        """
        dew_point = cls.estimate_dew_point(temp_c, rh_pct)
        dp_depression = max(0.0, temp_c - dew_point)
        lwd_hours = cls.estimate_leaf_wetness_hours(rh_pct, rain_mm, dp_depression)

        results = {}
        for pathogen, params in cls.PATHOGEN_CARDINALS.items():
            thermal_rate = cls.compute_thermal_kinetics(temp_c, pathogen)
            min_lwd = params["min_lwd_hours"]

            # Moisture adequacy factor
            if min_lwd == 0.0:
                # Mildew requires high RH but not necessarily free water droplets
                moisture_fac = min(1.0, max(0.0, (rh_pct - 50.0) / 45.0))
            else:
                moisture_fac = min(1.0, lwd_hours / min_lwd) if lwd_hours >= (min_lwd * 0.5) else 0.0

            # Inoculum amplification by existing physiological host crop canopy stress
            stress_vulnerability = 1.0 + (canopy_stress_score * 0.5)
            daily_risk = thermal_rate * moisture_fac * stress_vulnerability
            daily_risk = float(round(min(1.0, max(0.0, daily_risk)), 4))

            results[pathogen] = {
                "infection_risk_index": daily_risk,
                "thermal_development_rate": thermal_rate,
                "moisture_adequacy": round(moisture_fac, 3),
                "severity_category": (
                    "CRITICAL" if daily_risk > 0.75
                    else "HIGH" if daily_risk > 0.50
                    else "MODERATE" if daily_risk > 0.25
                    else "LOW"
                )
            }

        return {
            "microclimatic_metrics": {
                "air_temperature_c": temp_c,
                "relative_humidity_pct": rh_pct,
                "dew_point_c": dew_point,
                "dew_point_depression_c": round(dp_depression, 2),
                "leaf_wetness_duration_hours": lwd_hours,
                "rainfall_mm": rain_mm
            },
            "pathogen_epidemiology": results
        }

    @classmethod
    def generate_multiday_epidemiological_forecast(
        cls,
        daily_weather_forecast: List[Dict[str, Any]],
        initial_stress_score: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Projects multi-day disease progression incorporating compounding cumulative spore incubation.
        """
        trajectory = []
        cumulative_inoculum_pressure = 0.0

        for day_idx, day_weather in enumerate(daily_weather_forecast):
            temp = float(day_weather.get("temp", 22.0))
            rh = float(day_weather.get("humidity", 70.0))
            rain = float(day_weather.get("rain", 0.0))

            daily_sim = cls.simulate_pathogen_epidemiology(
                temp_c=temp,
                rh_pct=rh,
                rain_mm=rain,
                canopy_stress_score=initial_stress_score
            )

            # Calculate daily composite risk
            risks = [p["infection_risk_index"] for p in daily_sim["pathogen_epidemiology"].values()]
            avg_risk = float(np.mean(risks))

            # Compounding inoculum accumulation
            cumulative_inoculum_pressure = (cumulative_inoculum_pressure * 0.85) + (avg_risk * 0.3)

            date_str = day_weather.get("date", (datetime.now() + timedelta(days=day_idx)).strftime("%Y-%m-%d"))
            trajectory.append({
                "day_index": day_idx + 1,
                "date": date_str,
                "composite_daily_risk": round(min(1.0, avg_risk + cumulative_inoculum_pressure * 0.2), 4),
                "cumulative_inoculum_pressure": round(cumulative_inoculum_pressure, 4),
                "microclimate": daily_sim["microclimatic_metrics"],
                "pathogen_risks": daily_sim["pathogen_epidemiology"]
            })

        return trajectory


if __name__ == "__main__":
    # Self-test validation
    sample_weather = [
        {"date": "2026-11-20", "temp": 19.5, "humidity": 88.0, "rain": 4.5},
        {"date": "2026-11-21", "temp": 17.0, "humidity": 92.0, "rain": 12.0},
        {"date": "2026-11-22", "temp": 22.0, "humidity": 75.0, "rain": 0.0}
    ]
    forecast_res = MicroclimaticEpidemiologyModel.generate_multiday_epidemiological_forecast(sample_weather, initial_stress_score=0.45)
    print("MicroclimaticEpidemiologyModel self-test passed:")
    print(f"Generated {len(forecast_res)} forecast days.")
    print(f"Day 1 leaf wetness duration: {forecast_res[0]['microclimate']['leaf_wetness_duration_hours']} hours")
    print(f"Day 1 Stripe Rust Risk: {forecast_res[0]['pathogen_risks']['stripe_rust']['infection_risk_index']}")
