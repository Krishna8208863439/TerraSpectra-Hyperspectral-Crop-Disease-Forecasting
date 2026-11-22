import os
from typing import List, Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class PlatformSettings(BaseSettings):
    """
    Enterprise-grade system configuration for TerraSpectra Hyperspectral AI Engine.
    Handles environment variables, scientific processing thresholds, ML hyperparameters,
    and storage paths.
    """

    # Application Metadata
    APP_NAME: str = "TerraSpectra"
    APP_VERSION: str = "2.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")

    # Networking & CORS
    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000"
    ]

    # Database & Storage
    DATABASE_URL: str = Field(
        default="sqlite:///./backend/app/database/terraspectra.db",
        env="DATABASE_URL"
    )
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    SAVED_MODELS_DIR: str = os.path.join(BASE_DIR, "ml", "saved_models")
    UPLOAD_TEMP_DIR: str = os.path.join(BASE_DIR, "uploads")

    # Hyperspectral Ingestion & Processing Thresholds
    MIN_HYPERSPECTRAL_BANDS: int = 10
    STANDARD_VNIR_START_NM: float = 400.0
    STANDARD_VNIR_END_NM: float = 1000.0
    SAVGOL_WINDOW_LENGTH: int = 7
    SAVGOL_POLYORDER: int = 2
    PCA_N_COMPONENTS: int = 3
    MAX_PIXELS_FOR_PCA_SAMPLE: int = 5000

    # Narrowband Index Calibration Benchmarks
    HEALTHY_NDVI_THRESHOLD: float = 0.65
    EARLY_STRESS_NDRE_THRESHOLD: float = 0.35
    CAROTENOID_PRI_STRESS_THRESHOLD: float = -0.05
    FOLIAR_WATER_WBI_STRESS_THRESHOLD: float = 0.95

    # ML Inference Settings
    DEFAULT_TORCH_DEVICE: str = "cpu"
    MODEL_CHECKPOINT_NAME: str = "hybrid_3dcnn_vit.pt"
    INFERENCE_BATCH_SIZE: int = 16
    MAX_SPATIAL_PATCH_SIZE: int = 9

    # Epidemiological Simulation Parameters
    DEFAULT_FORECAST_HORIZON_DAYS: int = 7
    STRESS_INOCULUM_AMPLIFICATION: float = 0.50
    INOCULUM_PERSISTENCE_DECAY: float = 0.85

    # Geospatial Default Bounds (Kolhapur / Western Ghats Agricultural Basin)
    DEFAULT_GIS_BOUNDS: Dict[str, float] = {
        "min_lon": 74.2150,
        "min_lat": 16.6850,
        "max_lon": 74.2550,
        "max_lat": 16.7250
    }
    DEFAULT_CRS: str = "EPSG:4326"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


# Global singleton instance
settings = PlatformSettings()


if __name__ == "__main__":
    print(f"TerraSpectra Settings Initialized:")
    print(f"App: {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    print(f"DB URL: {settings.DATABASE_URL}")
    print(f"VNIR Spectral Range: {settings.STANDARD_VNIR_START_NM} - {settings.STANDARD_VNIR_END_NM} nm")
    print(f"Healthy NDVI Threshold: {settings.HEALTHY_NDVI_THRESHOLD}")
