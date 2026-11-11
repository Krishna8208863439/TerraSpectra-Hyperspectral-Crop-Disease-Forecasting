# TerraSpectra: Hyperspectral Crop Intelligence & Disease Forecasting

An advanced scientific agricultural remote sensing platform designed to analyze contiguous hyperspectral data cubes (VNIR 400nm - 1000nm), extract diagnostic spectral reflectance signatures, detect pre-symptomatic crop physiological stress, classify foliar plant pathologies, and project 7-day disease risk through longitudinal multi-modal epidemiology.

---

## 1. Problem Statement & Research Motivation

Standard agricultural computer vision relies primarily on 3-channel RGB imagery (Red, Green, Blue). However, macroscopic symptoms (chlorosis, necrotic pustules, leaf wilting) only manifest after pathogens have established deep intracellular infections. 

**TerraSpectra** utilizes scientific hyperspectral imaging across narrow, contiguous spectral bands to:
- Detect biochemical and cellular changes (chlorophyll degradation, red-edge inflection shift, water absorption loss) days before visual symptom onset.
- Calculate narrowband physiological vegetation indices (NDVI, NDRE, PRI, PSRI, WBI, MCARI).
- Separate general abiotic stress (drought, nitrogen deficit) from confirmed biotic infections.
- Couple spectral trajectories with microclimatic variables (temperature, relative humidity, sporulation windows) for 7-day forward risk projections.

---

## 2. Core Architectural Modules

1. **Hyperspectral Data Ingestion**:
   - Parses ENVI (`.hdr` / `.raw`), multi-band GeoTIFF, and NumPy 3D arrays (`.npy`).
   - Validates spectral dimensions ($\ge 10$ contiguous bands).
   - Rejects 3-channel RGB imagery to maintain scientific validity.

2. **Spectral Analysis Engine**:
   - Continuous reflectance curve generation across VNIR (400-1000nm).
   - Savitzky-Golay noise filtering and continuum removal.
   - Narrowband indices:
     - **NDVI**: Overall green biomass $(R_{800} - R_{670}) / (R_{800} + R_{670})$.
     - **NDRE**: Red-edge chlorophyll sensitivity $(R_{800} - R_{720}) / (R_{800} + R_{720})$.
     - **PRI**: Photochemical reflectance and light-use efficiency $(R_{531} - R_{570}) / (R_{531} + R_{570})$.
     - **WBI**: Foliar cellular hydration ratio $(R_{900} / R_{970})$.
     - **PSRI**: Plant senescence index $(R_{680} - R_{500}) / R_{750}$.
     - **MCARI**: Modified chlorophyll absorption in reflectance.
   - Principal Component Analysis (PCA) dimensionality reduction.

3. **Machine Learning Disease Classification**:
   - Dual-model ensemble: 100-tree Random Forest + RBF Support Vector Classifier.
   - Multi-class diagnostic spectrum:
     - *Healthy (No Pathogen Detected)*
     - *Stripe Rust (Puccinia striiformis)*
     - *Powdery Mildew (Blumeria graminis)*
     - *Septoria Leaf Blotch (Zymoseptoria tritici)*
     - *Fusarium Head Blight*
     - *Bacterial Leaf Streak (Xanthomonas translucens)*
   - Full probability distribution and ensemble agreement verification.

4. **Early Crop Stress Identification**:
   - Sub-visual stress indicators quantifying moisture deficit and chlorophyll breakdown before lesion emergence.
   - Explicit scientific demarcation between physiological stress and fungal/bacterial infection.

5. **7-Day Epidemiological Disease Forecasting**:
   - Integrates spectral degradation trajectory with microclimatic sporulation favorability from Open-Meteo.
   - Computes daily risk projections with expanding confidence bounds $[CI_{lower}, CI_{upper}]$.

6. **Explainable AI (XAI)**:
   - Band-wise Shapley (SHAP) attributions identifying exact nanometer wavelengths driving predictions.
   - Biological domain breakdowns across Blue Absorption, Red Trough, Red Edge, and NIR Plateau.

7. **Research Analytics Dashboard**:
   - Experimental confusion matrix, precision, recall, and weighted F1-score tracking.
   - SQLite persistent storage for research runs.

---

## 3. Technology Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, NumPy, SciPy, Scikit-learn, PyTorch, Pydantic, HTTPX.
- **Frontend**: React 18, Vite, Lucide Icons, Modern Scientific CSS Theme.
- **Storage**: SQLite / PostgreSQL.
- **Deployment**: Docker, Docker Compose.

---

## 4. Getting Started

### Backend Execution
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation: `http://localhost:8000/docs`

### Frontend Execution
```bash
cd frontend
npm install
npm run dev
```
Web dashboard: `http://localhost:3000`

### Docker Deployment
```bash
docker-compose up --build
```

---

## 5. Verification & Testing

Run unit tests for the scientific processing engine:
```bash
python -m unittest tests/test_scientific_engine.py
```

Run API endpoint tests:
```bash
python tests/run_integration_tests.py
```

