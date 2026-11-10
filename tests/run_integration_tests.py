import asyncio
import io
import sys
import os
import numpy as np
import httpx

sys.path.append(os.path.abspath("TerraSpectra-Hyperspectral-Crop-Disease-Forecasting/backend"))
from app.main import app

async def run_tests():
    print("Testing TerraSpectra Endpoints via ASGITransport...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("✓ Health Check Passed:", res.json()["platform"])

        # 2. Benchmark Hypercube
        res = await client.get("/api/research/sample-hypercube")
        assert res.status_code == 200, f"Sample hypercube failed: {res.text}"
        data = res.json()
        assert len(data["spectral_curve"]) > 10
        assert "indices" in data
        assert "stress" in data
        assert "explainability" in data
        print("✓ Benchmark Sample Hypercube Endpoint Passed:", data["sample_name"])

        # 3. 7-Day Disease Risk Forecast
        res = await client.get("/api/forecasting/disease-risk?crop_type=Wheat&stress_score=0.45&lat=16.705&lon=74.243")
        assert res.status_code == 200, f"Forecast failed: {res.text}"
        fc = res.json()["disease_forecast"]
        assert fc["forecast_horizon_days"] == 7
        assert len(fc["trajectory"]) == 7
        print("✓ 7-Day Disease Risk Forecast Passed: Peak Risk Day", fc["peak_risk_day"])

        # 4. Research Analytics Dashboard
        res = await client.get("/api/research/analytics")
        assert res.status_code == 200, f"Research analytics failed: {res.text}"
        an = res.json()
        assert "model_performance" in an
        print("✓ Research Analytics Endpoint Passed. Model Accuracy:", an["model_performance"]["accuracy"])

        # 5. Hyperspectral Ingestion (Valid 60-band cube)
        cube = np.random.uniform(0.05, 0.75, (15, 15, 60)).astype(np.float32)
        bio = io.BytesIO()
        np.save(bio, cube)
        bio.seek(0)
        files = {"file": ("test_wheat_cube.npy", bio.getvalue(), "application/octet-stream")}
        res = await client.post("/api/hyperspectral/upload-and-analyze", files=files, data={"crop_type": "Wheat (Triticum aestivum)"})
        assert res.status_code == 200, f"Upload analysis failed: {res.text}"
        up_res = res.json()
        assert up_res["metadata"]["bands_count"] == 60
        assert "spectral_indices" in up_res
        print("✓ Valid 60-Band Hypercube Upload & Analysis Passed. Diagnosed:", up_res["diagnosis"]["predicted_condition"])

        # 6. Reject RGB (3-band) image
        rgb_cube = np.random.uniform(0, 255, (15, 15, 3)).astype(np.uint8)
        bio = io.BytesIO()
        np.save(bio, rgb_cube)
        bio.seek(0)
        files = {"file": ("fake_rgb_cube.npy", bio.getvalue(), "application/octet-stream")}
        res = await client.post("/api/hyperspectral/upload-and-analyze", files=files)
        assert res.status_code == 422
        assert "Insufficient spectral bands" in res.json()["detail"]
        print("✓ RGB 3-Band Rejection Guard Passed:", res.json()["detail"])

    print("\nALL 6 ENDPOINT INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())

