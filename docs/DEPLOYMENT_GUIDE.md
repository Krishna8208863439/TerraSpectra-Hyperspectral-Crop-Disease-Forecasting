# Quick Start & Deployment Guide: TerraSpectra

This document provides instructions for running, testing, and deploying **TerraSpectra-Hyperspectral-Crop-Disease-Forecasting**.

---

## 1. Running Locally

You have two execution modes available depending on whether you are running the unified production application or developing the frontend:

### Mode A: Unified Single-Port Application (Recommended)
This serves both the React scientific dashboard and the Python FastAPI backend from a single URL (`http://localhost:8000`).

```bash
cd TerraSpectra-Hyperspectral-Crop-Disease-Forecasting/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Technical Schema**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Mode B: Development Mode (with Live Hot-Reload)
Use this mode when you are modifying frontend UI code or styling.

1. **Start the FastAPI Backend**:
   ```bash
   cd TerraSpectra-Hyperspectral-Crop-Disease-Forecasting/backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start the React Vite Dev Server**:
   ```bash
   cd TerraSpectra-Hyperspectral-Crop-Disease-Forecasting/frontend
   npm run dev
   ```
- **Live Dev Dashboard**: [http://localhost:3000](http://localhost:3000) (Proxies `/api` to port 8000 automatically)

---

## 2. Testing the Pipeline with Sample Benchmark Hypercubes

TerraSpectra comes with pre-generated scientific benchmark hypercubes located in `ml/datasets/`:

| Specimen Dataset File | Format | Channels | Pathological Condition |
| :--- | :--- | :--- | :--- |
| `specimen_stripe_rust_100b.npy` | NumPy 3D Cube | 100 Bands (400-1000nm) | Stripe Rust (*Puccinia striiformis*) |
| `specimen_healthy_100b.npy` | NumPy 3D Cube | 100 Bands (400-1000nm) | Healthy Vegetative Canopy |
| `specimen_powdery_mildew_100b.npy` | NumPy 3D Cube | 100 Bands (400-1000nm) | Powdery Mildew (*Blumeria graminis*) |
| `specimen_septoria_leaf_blotch_100b.npy` | NumPy 3D Cube | 100 Bands (400-1000nm) | Septoria Leaf Blotch (*Zymoseptoria tritici*) |
| `specimen_fusarium_head_blight_100b.npy` | NumPy 3D Cube | 100 Bands (400-1000nm) | Fusarium Head Blight |
| `specimen_bacterial_leaf_streak_100b.npy` | NumPy 3D Cube | 100 Bands (400-1000nm) | Bacterial Leaf Streak |
| `wheat_canopy_healthy_vnir.hdr` / `.raw` | ENVI Standard | 100 Bands (400-1000nm) | Healthy Canopy (ENVI BSQ format) |
| `wheat_canopy_stripe_rust_vnir.hdr` / `.raw` | ENVI Standard | 100 Bands (400-1000nm) | Stripe Rust (ENVI BSQ format) |

### How to test:
1. Open [http://localhost:8000](http://localhost:8000) in your browser.
2. Click on the **Hyperspectral Upload** tab in the sidebar navigation.
3. Select any `.npy` file or drag an ENVI `.hdr` file from `ml/datasets/`.
4. Click **Execute Hyperspectral Spectral Analysis**.
5. The system will automatically compute the full continuous VNIR spectral curve, calculate 6 narrowband vegetation indices, classify the disease status, assess early pre-symptomatic stress, evaluate band-wise SHAP attributions, and calculate the 7-day microclimate risk forecast.

---

## 3. Running Automated Tests

Run the scientific test suite:
```bash
python -m unittest TerraSpectra-Hyperspectral-Crop-Disease-Forecasting/tests/test_scientific_engine.py
```

Generate new synthetic ENVI hypercubes:
```bash
python TerraSpectra-Hyperspectral-Crop-Disease-Forecasting/scripts/generate_envi_datasets.py
```

---

## 4. Containerized Deployment (Docker)

To deploy with Docker Compose:
```bash
cd TerraSpectra-Hyperspectral-Crop-Disease-Forecasting
docker-compose up --build -d
```
- **Backend Service**: `http://localhost:8000`
- **Frontend Nginx Container**: `http://localhost:3000`

---

## 5. Notes on Cloud / Production Hosting

- **PythonAnywhere Hosting Note**: The existing Smart Kisan deployment at `https://Krishna3114.pythonanywhere.com` remains completely untouched. Because PythonAnywhere WSGI has CPU and memory ceilings for heavy scientific array processing, the recommended hosting targets for TerraSpectra in production are:
  - Docker on AWS ECS / DigitalOcean / GCP Cloud Run.
  - Render / Railway using the provided `backend/Dockerfile` and `frontend/Dockerfile`.

