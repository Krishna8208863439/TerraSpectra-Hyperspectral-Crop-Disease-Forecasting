import numpy as np
from typing import Dict, Any, List

class EarlyCropStressEngine:
    """
    Analyzes subtle pre-symptomatic spectral deviations before macroscopic lesion emergence.
    Distinguishes physiological stressors (water/nitrogen deficit) from pathogen infections.
    """

    @staticmethod
    def analyze_stress_indicators(signature: np.ndarray, wavelengths: List[float], indices: Dict[str, float]) -> Dict[str, Any]:
        """
        Computes early stress indicators:
        - Chlorophyll breakdown indicator (RedEdge shift)
        - Moisture deficit indicator (Water Band Index drop)
        - Photochemical efficiency depression (PRI drop)
        """
        ndvi = indices.get("NDVI", 0.7)
        ndre = indices.get("NDRE", 0.5)
        pri = indices.get("PRI", 0.0)
        psri = indices.get("PSRI", 0.0)
        wbi = indices.get("WBI", 1.0)

        # Baseline reference for optimal healthy canopy
        healthy_ndvi_ref = 0.82
        healthy_ndre_ref = 0.55
        healthy_wbi_ref = 1.15
        healthy_pri_ref = 0.05

        # Stress differentials
        water_stress_delta = max(0.0, healthy_wbi_ref - wbi)
        chloro_stress_delta = max(0.0, healthy_ndre_ref - ndre)
        photo_stress_delta = max(0.0, healthy_pri_ref - pri)

        # Overall composite stress score [0.0 = completely healthy, 1.0 = acute stress]
        stress_score = (
            0.35 * min(1.0, chloro_stress_delta / 0.35) +
            0.35 * min(1.0, water_stress_delta / 0.40) +
            0.20 * min(1.0, photo_stress_delta / 0.15) +
            0.10 * max(0.0, min(1.0, (psri + 0.1) / 0.4))
        )
        stress_score = round(float(np.clip(stress_score, 0.0, 1.0)), 3)

        # Determine dominant stress type
        if stress_score < 0.25:
            stress_level = "Nominal / Low Stress"
            dominant_factor = "None (Canopy is physiologically vigorous)"
            actionable_recommendation = "Maintain regular monitoring schedule. Canopy shows optimal cellular turgor and chlorophyll density."
        elif water_stress_delta > chloro_stress_delta and water_stress_delta > 0.15:
            stress_level = "Sub-Visual Moisture Deficit"
            dominant_factor = "Water Band Reflectance Attenuation (970nm dip)"
            actionable_recommendation = "Early irrigation intervention recommended. Hyperspectral signature indicates leaf cell water potential drop prior to visible wilting."
        elif chloro_stress_delta > 0.12:
            stress_level = "Early Chlorosis / Nitrogen Stress"
            dominant_factor = "Red Edge Slope Flattening (700-725nm)"
            actionable_recommendation = "Targeted foliar nitrogen assessment suggested. Red-edge inflection points indicate early chloroplast degradation."
        else:
            stress_level = "General Physiological Stress"
            dominant_factor = "Photochemical Index & Carotenoid Shift"
            actionable_recommendation = "Inspect field microclimate and soil salinity. Photosynthetic light-use efficiency is depressed."

        # Key diagnostic bands
        diagnostic_bands = [
            {"band": "531nm (PRI)", "importance": "High", "role": "Carotenoid/xanthophyll cycle regulation"},
            {"band": "705nm (RedEdge)", "importance": "Critical", "role": "Foliar chlorophyll absorption boundary"},
            {"band": "720nm (NDRE)", "importance": "Critical", "role": "Sub-canopy nitrogen & chlorophyll status"},
            {"band": "970nm (WBI)", "importance": "High", "role": "Foliar cellular water absorption"}
        ]

        return {
            "composite_stress_score": stress_score,
            "stress_level": stress_level,
            "dominant_stress_factor": dominant_factor,
            "water_stress_index": round(float(water_stress_delta), 3),
            "chlorophyll_stress_index": round(float(chloro_stress_delta), 3),
            "photochemical_depression_index": round(float(photo_stress_delta), 3),
            "actionable_recommendation": actionable_recommendation,
            "diagnostic_bands": diagnostic_bands,
            "distinction_note": "Important: Sub-visual crop stress reflects physiological depletion and must not be confused with confirmed fungal/bacterial infection diagnosis."
        }

