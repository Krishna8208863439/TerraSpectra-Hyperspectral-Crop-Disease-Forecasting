<<<<<<< Updated upstream
# 🌾 TerraSpectra: Hyperspectral Crop Disease Forecasting

> Early detection and forecasting of crop disease using hyperspectral imaging and machine learning.

![Status](https://img.shields.io/badge/status-in%20progress-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Domain](https://img.shields.io/badge/domain-Data%20Science%20%26%20ML-green)

---

## 📌 Project Information

| Field | Details |
|---|---|
| **Project Name** | TerraSpectra: Hyperspectral Crop Disease Forecasting |
| **Organization** | Infotact Solutions |
| **Intern** | Shashwat Shukla |
| **Role** | Data Associate L1 Intern |
| **Domain** | Data Science & Machine Learning |
| **Internship Duration** | 3 Months |
| **Project Duration** | 1 Month (10/11/2026 – 10/12/2026) |
| **Mentor** | _TBD_ |

---

## 📖 Overview

Crop diseases often change a plant's physiology (chlorophyll content, water content, cell structure) **before** symptoms are visible to the human eye. Hyperspectral imaging captures reflectance across hundreds of narrow spectral bands, which makes it possible to pick up these early signals.

**TerraSpectra** aims to build a machine learning pipeline that:

1. Ingests hyperspectral crop data,
2. Extracts informative spectral (and spatial) features,
3. Detects and classifies disease stress, and
4. Forecasts disease progression / risk over time.

---

## 🎯 Objectives

- Gain practical exposure to a real-world Data Science & ML workflow.
- Analyze hyperspectral data and understand its structure (spatial × spectral cube).
- Build and compare ML/DL models for crop disease detection and forecasting.
- Evaluate model performance rigorously and document findings to industry standards.

---

## 🧭 Scope of Work

- [ ] Understand project requirements and objectives
- [ ] Collect and preprocess relevant datasets
- [ ] Perform Exploratory Data Analysis (EDA)
- [ ] Design, develop and evaluate ML models
- [ ] Document methodology, findings and outcomes
- [ ] Maintain version control and code documentation
- [ ] Submit periodic progress updates to the mentor
- [ ] Complete the project within the stipulated timeline

---

## 🗓️ Suggested 4-Week Plan

| Week | Focus | Key Outputs |
|---|---|---|
| **1** | Problem understanding, literature review, dataset identification, environment setup | Dataset shortlist, project repo, EDA plan |
| **2** | Data loading, preprocessing, EDA | Cleaned data, spectral plots, band/feature analysis |
| **3** | Feature engineering, baseline + advanced models, forecasting experiments | Trained models, experiment log |
| **4** | Evaluation, documentation, report, PPT, demo | Final report, presentation, demo |

---

## 🔬 Proposed Methodology

### 1. Data
- Hyperspectral images / spectral signatures of crops (healthy vs diseased, ideally with time-series).
- Dataset to be confirmed with the mentor. Public hyperspectral benchmarks (e.g., Indian Pines, Salinas) can be used to prototype the pipeline before moving to disease-specific data.

### 2. Preprocessing
- Radiometric / reflectance calibration (if raw data)
- Noise and bad-band removal
- Smoothing (e.g., Savitzky–Golay), normalization / standardization
- Handling missing values and class imbalance

### 3. Feature Engineering
- Dimensionality reduction: PCA, band selection
- Vegetation indices: NDVI, red-edge indices, PRI, etc.
- Spatial features / patch extraction for CNN models
- Temporal features for forecasting

### 4. Modeling
| Stage | Candidate Models |
|---|---|
| Baselines | Logistic Regression, Random Forest, SVM, XGBoost |
| Deep learning | 1D-CNN (spectral), 2D/3D-CNN (spectral-spatial) |
| Forecasting | LSTM / GRU, Temporal models on index time-series |

### 5. Evaluation
- Classification: Accuracy, Precision, Recall, F1-score, Confusion Matrix, ROC-AUC
- Forecasting: MAE, RMSE, R²
- Cross-validation and a strictly held-out test set (avoid spatial leakage between train/test pixels)

---

## 📁 Repository Structure

```
terraspectra/
├── data/
│   ├── raw/                # Original data (never modified, not committed)
│   ├── interim/            # Intermediate data
│   └── processed/          # Model-ready data
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── 03_modeling.ipynb
│   └── 04_forecasting.ipynb
├── src/
│   ├── data_loader.py
│   ├── preprocessing.py
│   ├── features.py
│   ├── models.py
│   ├── train.py
│   ├── evaluate.py
│   └── utils.py
├── models/                 # Saved model artifacts
├── reports/
│   ├── figures/
│   ├── project_report.pdf
│   └── presentation.pptx
├── docs/                   # Project documentation
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
=======
# SpectralCrop — Hyperspectral Crop Stress Detection & Temporal Forecasting

Day 1 Setup, Scope Confirmation, Environment Verification, and Dataset Decision Repository.

## Project Scope

1. **Detection Baseline:** Classify leaf/plant spectral reflectance observations into healthy vs. stressed/diseased states using tabular spectral features and vegetation indices (`scikit-learn`, `XGBoost`).
2. **Simple Temporal Forecast:** Forecast next-timestep vegetation index / stress trajectory ($\Delta\text{NDVI}_{t+1}$) across repeated measurement dates.
3. **Interactive Workbench:** Web console (`server.ts` + React `src/`) to audit repository structure, execute live Python stack verification, inspect spectral curves, and edit Day 1 documentation.

---

## Repository Structure

```text
.
├── app/                      # Web application architecture notes & integration docs
├── data/
│   ├── raw/                  # Downloaded Zenodo CC-BY-4.0 CSVs + clearly labeled synthetic fallback CSV
│   └── processed/            # Output directory for Day 2+ cleaned tables & split manifests
├── docs/
│   ├── project_brief.md      # One-page project brief: problem, data, success metrics
│   ├── dataset_note.md       # Dataset source, licence, shape, labels, and grouping columns
│   └── mentor_message.md     # Block 1 mentor scope confirmation & cadence message
├── notebooks/
│   └── 01_day1_env_and_data_check.ipynb  # Day 1 environment & spectral sanity-check notebook
├── reports/                  # Generated evaluation figures and metrics reports
├── src/
│   └── pipeline/
│       ├── verify_env.py                 # Core Python library import verification script
│       ├── dataset_loader.py             # CSV loader & spectral summary inspector
│       └── generate_synthetic_spectra.py # Fallback #3 synthetic controlled-stress spectra generator
├── README.md
└── requirements.txt
>>>>>>> Stashed changes
```

---

<<<<<<< Updated upstream
## ⚙️ Getting Started

### Prerequisites
- Python 3.10+
- Git

### Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd terraspectra

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Suggested `requirements.txt`

```
numpy
pandas
scipy
scikit-learn
xgboost
matplotlib
seaborn
spectral
rasterio
scikit-image
torch
tensorflow
jupyter
tqdm
```

> Pick **either** `torch` or `tensorflow` for deep learning to keep the environment light.

### Run

```bash
# Launch notebooks
jupyter notebook

# Train a model (once src/train.py is ready)
python src/train.py --config configs/baseline.yaml

# Evaluate
python src/evaluate.py --model models/best_model.pkl
=======
## Quickstart & Environment Verification (Block 3)

### 1. Python Stack Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Verify All Core Library Imports

```bash
python3 src/pipeline/verify_env.py
```

Required packages verified: `numpy`, `pandas`, `scikit-learn`, `xgboost`, `matplotlib`, `spectral`.

### 3. Inspect Dataset & Launch Interactive Workbench

```bash
python3 src/pipeline/dataset_loader.py
npm install
npm run dev
>>>>>>> Stashed changes
```

---

<<<<<<< Updated upstream
## 📦 Deliverables

- [ ] Source Code
- [ ] Project Documentation
- [ ] Project Report
- [ ] Presentation (PPT)
- [ ] Model Evaluation Results
- [ ] Final Project Demonstration

---

## 📊 Results

_To be updated as experiments are completed._

| Model | Accuracy | F1-score | Notes |
|---|---|---|---|
| Random Forest (baseline) | – | – | – |
| SVM | – | – | – |
| 1D-CNN | – | – | – |
| 3D-CNN | – | – | – |

---

## ✅ Best Practices Followed

- Meaningful, frequent Git commits (feature branches + clear messages)
- Reproducibility: fixed random seeds, pinned dependencies
- Clear docstrings and comments in code
- Experiments logged with parameters and metrics
- Weekly progress updates shared with the mentor

---

## ⚠️ Confidentiality & Originality

- This project is part of an internship at Infotact Solutions. **Do not disclose or publish confidential company information or data** to any third party.
- Check with your mentor before making this repository public.
- All submitted work must be original and free from plagiarism. Cite all datasets, papers and external code used.

---

## 📚 References

_Add papers, datasets and tools here as you go._

- 

---

## 📝 License

_To be decided with the organization/mentor._

---

## 🙋 Contact

**Shashwat Shukla** – Data Associate L1 Intern, Infotact Solutions
=======
## Day 1 Carry-Forward to Day 2 & Day 5

- **Leak-Free Grouping Keys:** `Plant_ID`, `Pot_Number`, `date`, `TimeStamp` (and `plant_id`, `plot_id`, `field_id`, `acquisition_date` in the synthetic benchmark).
- **Rule:** All Day 5 cross-validation must group by `Plant_ID` (`StratifiedGroupKFold`) and respect chronological `date` ordering for temporal forecasts.

## Pushing to GitHub

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```
>>>>>>> Stashed changes
