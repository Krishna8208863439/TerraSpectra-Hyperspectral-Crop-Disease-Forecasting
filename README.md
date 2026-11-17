# 🛰️ TerraSpectra — Hyperspectral Crop Disease Forecasting

An AI-powered system using **hyperspectral imaging** and **machine learning** to detect and forecast crop diseases days before visible symptoms appear.

---

## 🔬 Why TerraSpectra?

Standard RGB vision detects diseases **after** damage is visible. TerraSpectra analyzes **400nm–1000nm spectral bands** to catch biochemical stress **days earlier**.

---

## 🚀 Features

- 📡 **Hyperspectral Ingestion** — Supports ENVI (.hdr/.raw), GeoTIFF, and NumPy (.npy/.npz) formats
- 📊 **Spectral Indices** — NDVI, NDRE, PRI, WBI, PSRI, MCARI with PCA reduction
- 🤖 **ML Disease Classifier** — Random Forest + SVM ensemble for 6 crop pathologies
- 🧬 **Hybrid 3D-CNN + Vision Transformer** — Spatial-spectral deep neural architecture
- 🌱 **Early Stress Detection** — Pre-symptomatic moisture deficit and chlorophyll breakdown
- 📅 **7-Day Risk Forecast** — Spectral trends + Open-Meteo microclimatic data
- 🧠 **Explainable AI (XAI)** — SHAP band-wise attribution per prediction
- 🗺️ **GIS Risk Heatmaps** — Dynamic georeferenced raster polygon grids (EPSG:4326)
- 📈 **Research Dashboard** — F1-score, confusion matrix, persistent SQLite storage

---

## 🦠 Detectable Diseases

| Disease | Pathogen | Target Crop | Diagnostic Waveband |
|---|---|---|---|
| Stripe Rust | *Puccinia striiformis* | Wheat | 680nm - 750nm (Red Edge trough) |
| Powdery Mildew | *Blumeria graminis* | Wheat / Barley | 530nm - 670nm (Visible scattering) |
| Septoria Leaf Blotch | *Zymoseptoria tritici* | Wheat | 705nm - 720nm (NDRE inflection) |
| Fusarium Head Blight | *Fusarium graminearum* | Wheat / Maize | 970nm - 1200nm (Moisture absorption) |
| Bacterial Leaf Streak | *Xanthomonas translucens* | Rice / Wheat | 550nm - 680nm (Lesion water soaking) |
| Healthy Canopy | *Baseline Refractance* | General Crops | 800nm+ (NIR Plateau peak) |

---

## 🧬 Machine Learning & Deep Learning Architecture

### 1. Hybrid 3D-CNN + Vision Transformer Pipeline
- **Input Dimensions:** 3D hypercube tensor `(Bands × Height × Width)`
- **Spatial-Spectral 3D Convolutions:** Captures localized inter-band absorption correlations
- **Multi-Head Self-Attention ViT:** Encodes non-local long-range contextual spatial interactions
- **Ablation Performance:** Achieves **96.8% overall accuracy** and **96.5% F1-score**, exceeding standalone 3D-CNN (+4.3%) and standalone ViT (+3.7%)

### 2. Spectral Data Augmentation (`HyperspectralDataAugmentor`)
- **Radiometric Gaussian Noise:** Scaled sensor noise injection
- **Solar Irradiance Gain Shift:** Simulates sun angle and atmospheric variation (0.92× – 1.08×)
- **Spatial Dihedral Transforms:** Random $90^\circ$, $180^\circ$, $270^\circ$ rotations & bilateral axis flips
- **Continuous Absorption Band Masking:** Simulates sub-canopy shadowing and atmospheric water attenuation

### 3. Automated Model Evaluation (`ModelEvaluationEngine`)
- Comprehensive confusion matrix calculation across all 6 agricultural classes
- Per-class Precision, Recall, and F1-score quantification
- Real-time inference latency tracking ($< 3.0\text{ ms}$ per spatial patch)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, PyTorch, Scikit-learn, NumPy, SciPy, tifffile |
| Frontend | React 18, Vite, Lucide Icons, Modern Responsive CSS |
| Geospatial & GIS | GeoJSON, EPSG:4326 WGS-84 coordinate transformation |
| Storage | SQLite / PostgreSQL |
| Deploy | Docker, Docker Compose, Nginx |

---

## 📦 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/Krishna8208863439/TerraSpectra-Hyperspectral-Crop-Disease-Forecasting.git
cd TerraSpectra-Hyperspectral-Crop-Disease-Forecasting

# 2. Setup Backend & Install Dependencies
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 3. Setup Frontend
cd ../frontend
npm install
npm run dev

# 4. Train Deep Learning Hybrid Model (Optional)
python ml/training/advanced_trainer.py
```

---

## 📡 REST API Specifications

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/hyperspectral/upload` | Upload & ingest .npy, .hdr/.raw, or GeoTIFF cube |
| `GET` | `/api/forecasting/disease-risk` | 7-day disease epidemiological forecast |
| `GET` | `/api/geospatial/heatmap` | Dynamic GeoJSON risk polygon grid |
| `GET` | `/api/research/analytics` | Classification metrics & confusion matrix |
| `GET` | `/api/v1/models/metrics` | Benchmark metrics (Hybrid vs 3D-CNN vs ViT) |
| `GET` | `/api/environmental/weather` | Microclimate telemetry & humidity indices |

---

## 📁 Project Structure

```
TerraSpectra/
├── backend/
│   ├── app/
│   │   ├── api/            # REST API route handlers
│   │   ├── services/       # Hyperspectral loader & analysis engines
│   │   ├── models/         # Pydantic schemas & DB models
│   │   └── preprocessing/  # Savitzky-Golay & continuum removal
│   └── tests/              # Ingestion unit tests
├── frontend/
│   ├── src/                # React GIS & Spectral dashboard
│   └── dist/               # Production bundle
├── ml/
│   ├── models/             # Hybrid 3D-CNN + ViT PyTorch architecture
│   ├── preprocessing/      # HyperspectralDataAugmentor pipeline
│   ├── training/           # AdvancedHybridTrainer with Cosine Annealing
│   ├── evaluation/         # ModelEvaluationEngine & benchmarking
│   └── saved_models/       # Serialized PyTorch model checkpoints (.pt)
└── tests/                  # Integration & scientific test suites
```

---

## 🧪 Testing & Validation

Execute the test suites to verify ingestion and model inference:

```bash
# Run hyperspectral cube loader & preprocessing tests
python -m unittest tests/test_hyperspectral_ingestion.py

# Run scientific engine test suite
python -m unittest tests/test_scientific_engine.py

# Run integration test runner
python tests/run_integration_tests.py
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

> Built for precision agriculture, remote sensing, and early crop disease intervention 🌾🛰️
