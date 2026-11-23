from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime


class HyperspectralMetadataSchema(BaseModel):
    """Schema for ingested hyperspectral cube metadata."""
    filename: str
    format: str
    dimensions: Tuple[int, int, int] = Field(..., description="(Height, Width, Spectral Bands)")
    bands_count: int
    wavelengths: List[float]
    wavelength_units: str = "nm"
    data_type: str = "float32"
    byte_order: int = 0
    file_size_bytes: int
    is_valid_hyperspectral: bool
    summary: str
    crs: Optional[str] = "EPSG:4326"
    spatial_resolution_m: Optional[float] = 30.0


class NarrowbandIndicesSchema(BaseModel):
    """Schema for computed scientific narrowband spectral vegetation indices."""
    NDVI: float = Field(..., ge=-1.0, le=1.0, description="Normalized Difference Vegetation Index (800nm vs 670nm)")
    NDRE: float = Field(..., ge=-1.0, le=1.0, description="Normalized Difference Red Edge (800nm vs 720nm)")
    PRI: float = Field(..., ge=-1.0, le=1.0, description="Photochemical Reflectance Index (531nm vs 570nm)")
    PSRI: float = Field(..., ge=-2.0, le=2.0, description="Plant Senescence Reflectance Index (680nm, 500nm, 750nm)")
    WBI: float = Field(..., ge=0.0, le=5.0, description="Water Band Index (900nm vs 970nm)")
    MCARI: float = Field(..., ge=-2.0, le=5.0, description="Modified Chlorophyll Absorption in Reflectance Index")


class PCAComponentSchema(BaseModel):
    """Schema for PCA dimensionality reduction component."""
    pc_index: int
    variance_ratio: float
    eigenvalue: Optional[float] = 1.0
    loadings: List[float]


class PCAResultSchema(BaseModel):
    """Schema for PCA spectral projection output."""
    explained_variance_ratio: List[float]
    total_explained_variance: float
    components: List[PCAComponentSchema]
    sample_scatter: List[Dict[str, float]]


class DiseaseClassificationSchema(BaseModel):
    """Schema for crop pathology classification inference."""
    predicted_condition: str
    is_healthy: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: str = Field(..., description="NORMAL, LOW, MODERATE, CRITICAL")
    probabilities: Dict[str, float]


class EarlyStressSchema(BaseModel):
    """Schema for pre-symptomatic crop physiological stress assessment."""
    composite_stress_score: float = Field(..., ge=0.0, le=1.0)
    stress_level: str
    moisture_deficit_pct: float
    chlorophyll_breakdown_pct: float
    photosynthetic_depression_pct: float
    actionable_guidance: str


class SpectralAttributionPoint(BaseModel):
    """Schema for individual wavelength XAI attribution."""
    band_index: int
    wavelength: float
    shap_value: float
    direction: str = Field(..., description="contributing or dampening")


class ExplainabilitySchema(BaseModel):
    """Schema for model explainability output."""
    predicted_condition: str
    top_influential_wavelengths: List[SpectralAttributionPoint]
    explainability_summary: str


class FullAnalysisResponse(BaseModel):
    """Full scientific response schema for hyperspectral cube upload & analysis."""
    analysis_id: int
    metadata: HyperspectralMetadataSchema
    spectral_indices: NarrowbandIndicesSchema
    spectral_curve: List[Dict[str, float]]
    preprocessing_comparison: Optional[List[Dict[str, float]]] = None
    snr_db: Optional[float] = None
    pca_analysis: PCAResultSchema
    diagnosis: DiseaseClassificationSchema
    early_stress: EarlyStressSchema
    explainability: ExplainabilitySchema
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DiseaseRiskForecastRequest(BaseModel):
    """Request schema for epidemiological 7-day risk forecasting."""
    crop_type: str = "Wheat (Triticum aestivum)"
    stress_score: float = Field(default=0.45, ge=0.0, le=1.0)
    lat: float = 16.7050
    lon: float = 74.2433
    historical_spectral_trend: Optional[List[float]] = None


class DailyForecastItem(BaseModel):
    """Schema for single-day disease forecast projection."""
    day_index: int
    date: str
    projected_risk: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    temperature_c: float
    humidity_pct: float
    rainfall_mm: float
    favorable_pathogens: List[str]


class DiseaseForecastResponse(BaseModel):
    """Response schema for multi-day disease risk trajectory."""
    crop_type: str
    current_stress_score: float
    seven_day_trajectory: List[DailyForecastItem]
    peak_risk_day: int
    overall_recommendation: str


if __name__ == "__main__":
    # Self-test validation
    sample_indices = NarrowbandIndicesSchema(
        NDVI=0.78, NDRE=0.45, PRI=0.02, PSRI=-0.05, WBI=1.05, MCARI=0.35
    )
    print("Hyperspectral Pydantic Schemas initialized successfully:")
    print(f"Sample NDVI: {sample_indices.NDVI}, WBI: {sample_indices.WBI}")
