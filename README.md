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
```

---

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
```

---

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
