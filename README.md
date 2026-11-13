# 🛰️ TerraSpectra — Hyperspectral Crop Disease Forecasting

An AI-powered agricultural intelligence system that uses **hyperspectral imaging** and **machine learning**
to detect, analyze, and forecast crop diseases at an early stage — enabling precision agriculture and smarter farming decisions.

---

## 🔬 What Makes TerraSpectra Different?

Standard crop vision systems rely on 3-channel RGB images and can only detect diseases **after** visible symptoms appear.
TerraSpectra analyzes **400nm–1000nm hyperspectral data** to catch biochemical stress signals **days before** any visible damage.

---

## 🚀 Core Features

| Module | Description |
|---|---|
| 📡 Hyperspectral Ingestion | Parses ENVI (.hdr/.raw), multi-band GeoTIFF, and NumPy 3D arrays (.npy) |
| 📊 Spectral Analysis Engine | NDVI, NDRE, PRI, WBI, PSRI, MCARI indices + PCA dimensionality reduction |
| 🤖 ML Disease Classifier | Random Forest + SVM ensemble detecting 6 crop pathologies |
| 🌱 Early Stress Detection | Pre-symptomatic moisture deficit & chlorophyll breakdown identification |
| 📅 7-Day Risk Forecasting | Epidemiological projection using spectral + Open-Meteo microclimatic data |
| 🧠 Explainable AI (XAI) | SHAP band-wise attribution identifying exact wavelengths driving predictions |
| 📈 Research Dashboard | Confusion matrix, precision, recall, F1-score with SQLite persistent storage |

---

## 🦠 Detectable Crop Diseases

- ✅ Healthy (No Pathogen Detected)
- 🟡 Stripe Rust — *Puccinia striiformis*
- ⚪ Powdery Mildew — *Blumeria graminis*
- 🟤 Septoria Leaf Blotch — *Zymoseptoria tritici*
- 🔴 Fusarium Head Blight
- 🟠 Bacterial Leaf Streak — *Xanthomonas translucens*

---

## 🛠️ Tech Stack

**Backend:** Python 3.12 · FastAPI · Uvicorn · NumPy · SciPy · Scikit-learn · PyTorch · Pydantic · HTTPX  
**Frontend:** React 18 · Vite · Lucide Icons · Scientific CSS Theme  
**Storage:** SQLite / PostgreSQL  
**Deployment:** Docker · Docker Compose  

---

## 📦 Getting Started

### Prerequisites
- Python 3.10+
- Node.js v18+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Krishna8208863439/TerraSpectra-Hyperspectral-Crop-Disease-Forecasting.git
cd TerraSpectra-Hyperspectral-Crop-Disease-Forecasting
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs available at: `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Web dashboard at: `http://localhost:3000`

### 4. Docker (Full Stack)
```bash
docker-compose up --build
```

---

## 🧪 Testing

```bash
# Unit tests for scientific processing engine
python -m unittest tests/test_scientific_engine.py

# API integration tests
python tests/run_integration_tests.py
```

---

## 📁 Project Structure

```
TerraSpectra/
├── backend/              # FastAPI Python AI & ML engine
│   ├── app/              # API routes and core logic
│   ├── models/           # ML classifiers (RF + SVM)
│   └── tests/            # Unit and integration tests
├── frontend/             # React + Vite dashboard
├── datasets/             # Hyperspectral training datasets
├── docker/               # Docker configs
└── nginx/                # Reverse proxy config
```

---

## 🌐 Deployment

Deploy to PythonAnywhere:
```bash
python deploy_all_to_pythonanywhere.py
```

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 🙌 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

> Built for precision agriculture and early crop disease intervention 🌾🛰️
