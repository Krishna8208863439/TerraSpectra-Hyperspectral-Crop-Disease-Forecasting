import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query, status

from app.services.hyperspectral_loader import HyperspectralCubeLoader
from app.services.spectral_preprocessing import SpectralPreprocessingPipeline
from app.services.spectral_analysis import SpectralAnalysisService
from app.services.spectral_anomaly_detector import SpectralAnomalyDetector
from app.explainability.xai_engine import ExplainableAIEngine
from app.inference.disease_classifier import HyperspectralDiseaseClassifier
from app.forecasting.crop_stress_engine import EarlyCropStressEngine
from app.forecasting.epidemiology_model import MicroclimaticEpidemiologyModel
from app.services.weather_service import EnvironmentalIntelligenceService
from app.geospatial.zonal_statistics import SpatialZonalStatisticsEngine
from app.database import db

router = APIRouter(prefix="/api/v2", tags=["TerraSpectra V2 Scientific API"])

# Classifier singleton instance
classifier = HyperspectralDiseaseClassifier()


@router.post(
    "/hyperspectral/ingest-cube",
    summary="Ingest multi-band hyperspectral cube and execute end-to-end diagnostic inference",
    status_code=status.HTTP_200_OK
)
async def ingest_hyperspectral_cube_v2(
    file: UploadFile = File(..., description="Hyperspectral data file (.npy, .hdr, .raw, .tif)"),
    header_file: Optional[UploadFile] = File(None, description="Optional ENVI ASCII header (.hdr)"),
    crop_type: str = Form("Wheat (Triticum aestivum)", description="Target agricultural crop specimen")
):
    """
    Modular V2 ingestion endpoint:
      1. Parses and validates cube dimensions (ensuring >= 10 contiguous spectral bands).
      2. Performs Savitzky-Golay noise filtering and continuum removal.
      3. Computes 6 narrowband vegetation indices (NDVI, NDRE, PRI, PSRI, WBI, MCARI).
      4. Detects unsupervised spectral anomalies (Reed-Xiaoli RX and Red-Edge Position shifts).
      5. Runs deep learning disease classification and pre-symptomatic stress assessment.
      6. Generates SHAP band attribution explanations and persists record to database.
    """
    contents = await file.read()
    filename = file.filename
    header_bytes = await header_file.read() if header_file else None
    header_name = header_file.filename if header_file else None

    try:
        # Ingest cube
        cube, meta = HyperspectralCubeLoader.load_hyperspectral_cube(
            primary_bytes=contents,
            primary_filename=filename,
            secondary_bytes=header_bytes,
            secondary_filename=header_name
        )

        # Spectral processing and narrowband indices
        profile = SpectralAnalysisService.extract_full_profile(cube, meta.wavelengths)
        pca_res = SpectralPreprocessingPipeline.compute_pca(cube, n_components=3)

        filtered_sig = profile["filtered_signature"]
        indices = profile["indices"]

        # Anomaly detection & biomarkers
        anomaly_res = SpectralAnomalyDetector.analyze_cube_anomalies(cube, meta.wavelengths)

        # Pathology diagnosis
        diagnosis = classifier.predict(filtered_sig, meta.wavelengths)

        # Pre-symptomatic early stress
        stress = EarlyCropStressEngine.analyze_stress_indicators(filtered_sig, meta.wavelengths, indices)

        # Explainability
        xai = ExplainableAIEngine.compute_band_importance(
            filtered_sig,
            meta.wavelengths,
            diagnosis["predicted_condition"],
            classifier.rf_model
        )

        # Persist to database
        record_id = db.save_analysis(
            dataset_name=meta.filename,
            crop_type=crop_type,
            condition=diagnosis["predicted_condition"],
            confidence=diagnosis["confidence"],
            is_healthy=diagnosis["is_healthy"],
            severity=diagnosis["severity"],
            stress_score=stress["composite_stress_score"],
            indices=indices,
            xai_summary=xai["explainability_summary"]
        )

        return {
            "analysis_id": record_id,
            "status": "success",
            "metadata": meta.dict(),
            "spectral_indices": indices,
            "spectral_curve": [
                {"wavelength": pt["wavelength"], "reflectance": pt["filtered_reflectance"]}
                for pt in profile["chart_points"]
            ],
            "preprocessing_comparison": profile["chart_points"],
            "snr_db": profile["snr_db"],
            "spectral_anomalies": anomaly_res,
            "pca_analysis": pca_res,
            "diagnosis": diagnosis,
            "early_stress": stress,
            "explainability": xai
        }

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {str(e)}")


@router.get(
    "/epidemiology/forecast-7day",
    summary="Simulate 7-day multi-pathogen infection trajectory coupled with microclimatic forecast"
)
async def get_epidemiological_forecast_v2(
    crop_type: str = Query("Wheat (Triticum aestivum)"),
    stress_score: float = Query(0.42, ge=0.0, le=1.0),
    lat: float = Query(16.7050),
    lon: float = Query(74.2433)
):
    """
    Couples weather telemetry with thermal development kinetics (Yan & Hunt model)
    and leaf wetness duration (LWD) estimations.
    """
    weather = await EnvironmentalIntelligenceService.get_microclimate_forecast(lat, lon)
    daily_weather = weather.get("daily_forecast", [])
    
    trajectory = MicroclimaticEpidemiologyModel.generate_multiday_epidemiological_forecast(
        daily_weather_forecast=daily_weather,
        initial_stress_score=stress_score
    )

    return {
        "crop_type": crop_type,
        "location": {"latitude": lat, "longitude": lon},
        "initial_canopy_stress_score": stress_score,
        "epidemiological_trajectory": trajectory
    }


@router.get(
    "/geospatial/zonal-management-prescription",
    summary="Retrieve field parcel management zones with variable rate spray prescriptions"
)
def get_zonal_prescription_geojson_v2(
    min_lon: float = Query(74.2150),
    min_lat: float = Query(16.6850),
    max_lon: float = Query(74.2550),
    max_lat: float = Query(16.7250),
    grid_dim: int = Query(10, ge=4, le=24),
    base_stress: float = Query(0.45, ge=0.0, le=1.0)
):
    """
    Computes spatial autocorrelation (Local Moran's I) to delineate disease clusters (High-High hotspots)
    and outputs GeoJSON FeatureCollection with prescription dosages (L/Ha).
    """
    bounds = (min_lon, min_lat, max_lon, max_lat)
    return SpatialZonalStatisticsEngine.generate_management_zones_geojson(
        bounds=bounds,
        grid_dim=grid_dim,
        base_stress=base_stress
    )


if __name__ == "__main__":
    print("TerraSpectra V2 Scientific APIRouter initialized successfully.")
    print(f"Prefix: {router.prefix}, Registered routes: {[route.path for route in router.routes]}")
