import os
import io
import numpy as np
import pytest
import httpx
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from app.main import app

@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "TerraSpectra"
        assert data["status"] == "online"

@pytest.mark.asyncio
async def test_sample_hypercube_benchmark_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/research/sample-hypercube")
        assert response.status_code == 200
        data = response.json()
        assert "spectral_curve" in data
        assert "diagnosis" in data
        assert "indices" in data
        assert "stress" in data
        assert "explainability" in data
        assert len(data["spectral_curve"]) > 10

@pytest.mark.asyncio
async def test_disease_risk_forecast_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/forecasting/disease-risk?crop_type=Wheat&stress_score=0.45&lat=16.705&lon=74.243")
        assert response.status_code == 200
        data = response.json()
        assert "disease_forecast" in data
        assert data["disease_forecast"]["forecast_horizon_days"] == 7
        assert len(data["disease_forecast"]["trajectory"]) == 7

@pytest.mark.asyncio
async def test_research_dashboard_analytics_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/research/analytics")
        assert response.status_code == 200
        data = response.json()
        assert "model_performance" in data
        assert "accuracy" in data["model_performance"]
        assert "confusion_matrix" in data["model_performance"]

@pytest.mark.asyncio
async def test_hyperspectral_upload_valid_cube():
    cube = np.random.uniform(0.05, 0.75, (20, 20, 60)).astype(np.float32)
    bio = io.BytesIO()
    np.save(bio, cube)
    bio.seek(0)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("test_wheat_cube.npy", bio.getvalue(), "application/octet-stream")}
        data = {"crop_type": "Wheat (Triticum aestivum)"}

        response = await client.post("/api/hyperspectral/upload-and-analyze", files=files, data=data)
        assert response.status_code == 200
        res = response.json()
        assert res["metadata"]["bands_count"] == 60
        assert "spectral_indices" in res
        assert "diagnosis" in res
        assert "early_stress" in res
        assert "explainability" in res

@pytest.mark.asyncio
async def test_hyperspectral_upload_rejects_insufficient_bands():
    rgb_cube = np.random.uniform(0, 255, (20, 20, 3)).astype(np.uint8)
    bio = io.BytesIO()
    np.save(bio, rgb_cube)
    bio.seek(0)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("fake_rgb_cube.npy", bio.getvalue(), "application/octet-stream")}
        response = await client.post("/api/hyperspectral/upload-and-analyze", files=files)
        assert response.status_code == 422
        assert "Insufficient spectral bands" in response.json()["detail"]
