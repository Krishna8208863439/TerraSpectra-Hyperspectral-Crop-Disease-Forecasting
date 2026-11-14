# 🛰️ TerraSpectra — Hyperspectral Crop Disease Forecasting

An AI-powered system using **hyperspectral imaging** and **machine learning** to detect and forecast crop diseases days before visible symptoms appear.

---

## 🔬 Why TerraSpectra?

Standard RGB vision detects diseases **after** damage is visible. TerraSpectra analyzes **400nm–1000nm spectral bands** to catch biochemical stress **days earlier**.

---

## 🚀 Features

- 📡 **Hyperspectral Ingestion** — Supports ENVI (.hdr/.raw), GeoTIFF, and NumPy (.npy) formats
- 📊 **Spectral Indices** — NDVI, NDRE, PRI, WBI, PSRI, MCARI with PCA reduction
- 🤖 **ML Disease Classifier** — Random Forest + SVM ensemble for 6 crop pathologies
- 🌱 **Early Stress Detection** — Pre-symptomatic moisture deficit and chlorophyll breakdown
- 📅 **7-Day Risk Forecast** — Spectral trends + Open-Meteo microclimatic data
- 🧠 **Explainable AI (XAI)** — SHAP band-wise attribution per prediction
- 📈 **Research Dashboard** — F1-score, confusion matrix, persistent SQLite storage

---

## 🦠 Detectable Diseases

| Disease | Pathogen |
|---|---|
| Stripe Rust | *Puccinia striiformis* |
| Powdery Mildew | *Blumeria graminis* |
| Septoria Leaf Blotch | *Zymoseptoria tritici* |
| Fusarium Head Blight | *Fusarium graminearum* |
| Bacterial Leaf Streak | *Xanthomonas translucens* |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, PyTorch, Scikit-learn, NumPy, SciPy |
| Frontend | React 18, Vite, Lucide Icons |
| Storage | SQLite / PostgreSQL |
| Deploy | Docker, Docker Compose |

---

## 📦 Quick Start

```bash
# 1. Clone
git clone https://github.com/Krishna8208863439/TerraSpectra-Hyperspectral-Crop-Disease-Forecasting.git
cd TerraSpectra-Hyperspectral-Crop-Disease-Forecasting

# 2. Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev

# 4. Docker (all-in-one)
docker-compose up --build
```

---

## 📁 Project Structure

```
TerraSpectra/
├── backend/        # FastAPI ML engine
├── frontend/       # React + Vite dashboard
├── datasets/       # Hyperspectral training data
├── docker/         # Container configs
└── nginx/          # Reverse proxy
```

---

## 🧪 Testing

```bash
python -m unittest tests/test_scientific_engine.py
python tests/run_integration_tests.py
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

> Built for precision agriculture and early crop disease intervention 🌾🛰️
