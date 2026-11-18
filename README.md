# TerraSpectra — Hyperspectral Crop Stress Detection & Temporal Forecasting

End-to-end reproducible machine learning pipeline and interactive spectral workbench for crop leaf stress detection, biophysical vegetation-index extraction, plant-grouped validation, SHAP interpretability, and chronological multi-horizon canopy forecasting.

---

## Project Summary

TerraSpectra solves three connected crop phenotyping & spectral modeling tasks under strict zero-leakage guarantees:

1. **Detection & Diagnosis (`src/preprocessing.py`, `src/features.py`, `src/evaluation.py`):** Preprocesses raw leaf reflectance spectra (`BadBandDropper` dropping UV noise at 365 nm, Savitzky-Golay denoising, SNV/MSC scatter normalization), extracts uncentered domain vegetation indices (**NDVI, NDRE, PRI, MCARI, Red-Edge Position**), and benchmarks Random Forest, XGBoost, SVM (RBF), PLS-DA, and Neural MLP inside frozen 5-fold `StratifiedGroupKFold(plant_id)`.
2. **Interpretability & Early Detection (`src/inference.py`):** Ranks spectral wavelengths and indices via validation-fold `TreeExplainer` SHAP values, measures early-detection lead time on unseen holdout plants, and powers real-time spectrum classification and batch CSV scoring.
3. **Temporal Trajectory Forecasting (`src/sequences.py`):** Aggregates longitudinal scans per plant into sliding windows (`W=3` prior dates) to forecast future canopy $\text{NDVI}_{t+k}$ (`k ∈ {1, 2, 3}`) using Lag-Feature Ridge and Lag-Feature Random Forest vs. a Persistence baseline ($\hat{y}_{t+k} = y_t$) strictly inside `GroupKFold(plant_id)`.

---

## Data Sources & Licences

| Dataset | Source / Origin | Licence | Scope & Explicit Limitations |
| --- | --- | --- | --- |
| **Primary Multi-Temporal Plant Spectra** (`data/raw/Multispectral_Reflectance.csv` + `experimental_design.csv`) | Zenodo Record [`10.5281/zenodo.22755812`](https://doi.org/10.5281/zenodo.22755812) (*Plant Phenotyping and Environmental Stress Dataset*) | **CC-BY-4.0** | `2,285` total rows (`2,272` clean valid scans) across `79` plants (`Plant_ID`), `2` genotypes, `31` dates, and `10` multispectral bands (`365–970 nm`). **Limitation:** Labels capture controlled abiotic water/drought stress (`Control 40%` vs `Drought 10%`) rather than biotic pathogen inoculation. |
| **Companion Synthetic Benchmark** (`data/raw/synthetic_leaf_disease_spectra_v1.csv`) | Local Generator (`src/pipeline/generate_synthetic_spectra.py`) | **Apache-2.0** | `120` scans × `61` dense bands (`400–1000 nm`, `10 nm` step) across `4` disease stages (`Healthy`, `Early_Chlorosis`, `Moderate_Blight`, `Severe_Necrosis`) and `5` dates. Clearly tagged `SYNTHETIC_CONTROLLED_STRESS`. |

---

## Setup & Reproducible Pipeline Execution (From Scratch)

### 1. Python Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Verify Stack & Run Every Stage in Order
```bash
# Stage 0: Verify core Python stack imports
python3 src/pipeline/verify_env.py

# Stage 1: Inspect unified dataset shapes, wavelengths & Plant_ID grouping keys
python3 src/data.py

# Stage 2: Exploratory Data Analysis & Figures 01–04
python3 src/pipeline/run_day2_eda.py

# Stage 3: Leak-free Preprocessing Pipeline & Figures 05–06
python3 src/pipeline/run_day3_preprocessing.py

# Stage 4: Vegetation Indices, Train-Only PCA / RF+MI Sets A–E & Figures 07–08
python3 src/pipeline/run_day4_features.py

# Stage 5: Grouped-CV Baselines (RF, XGBoost, SVM, PLS-DA), Leakage Audit & Figures 09–10
python3 src/pipeline/run_day5_baselines.py

# Stage 6: Error Analysis, SHAP Alignment, Tuning, Temporal Forecasting & Figures 11–13
python3 src/pipeline/run_day6_error_and_forecast.py

# Stage 7: Neural Comparator, Week 3 Readiness & Live Inference Model Cache
python3 src/week3_models.py
python3 src/inference.py --action warm-cache
```

### 3. Launch Interactive TerraSpectra Web Application
```bash
npm install
npm run dev
# Open http://localhost:3000
```

---

## Key Verified Results

- **Leakage Demonstration (`StratifiedGroupKFold` vs. Naive Random Split):** Naive row-level splits leak replicate scans of identical plants across folds, falsely inflating XGBoost Set E Macro-F1 by **`+0.0881`** (`0.4877` grouped vs `0.5758` naive).
- **Multi-Horizon Temporal Forecasting (`W=3`, `1,828–1,986` sequences):** Lag-Feature Random Forest outperforms naive Persistence at every horizon, cutting `k=+3` MAE by **52.5%** (`0.0327` vs `0.0688`, $R^2 = 0.9425$ vs `0.7758`).

---

## Repository Structure

```text
.
├── data/
│   ├── raw/                  # Immutable Zenodo CC-BY-4.0 CSVs + synthetic fallback CSV
│   └── processed/            # Preprocessed matrices, Sets A–E (.npz), CV splits (.json) & cached inference bundle
├── docs/
│   ├── project_report.md     # Draft technical report (Sections 1–4 complete, 5–6 outlined + citations)
│   ├── weekly_mentor_update.md # Concise milestone summary & Week 3 confirmation request
│   ├── week3_plan.md         # Week 3 1D-CNN, GRU/LSTM & light tuning roadmap
│   ├── project_brief.md      # Scope & metrics framing
│   ├── dataset_note.md       # Portal audit & metadata decision log
│   └── ...                   # Per-stage technical notes (data summary, preprocessing, features, baselines, error)
├── notebooks/                # Reproducible EDA, preprocessing, feature, baseline & error analysis notebooks
├── reports/
│   ├── day*_metrics.json     # Structured JSON stage outputs
│   ├── day5_baseline_results.csv # Clean baseline results table
│   ├── experiment_log.csv    # Reproducible experiment tracker
│   └── figures/              # Publication PNG charts (01–13)
├── src/
│   ├── data.py               # Unified dataset loader (Primary Zenodo + Synthetic)
│   ├── preprocessing.py      # BadBandDropper, ReflectanceSanitizer, SavitzkyGolay, SNV/MSC, 1st Deriv
│   ├── features.py           # NDVI, NDRE, PRI, REP, MCARI, train-only PCA, RF+MI selection, Sets A–E
│   ├── evaluation.py         # StratifiedGroupKFold harness, PLSDAClassifier, OOF metrics
│   ├── sequences.py          # Chronological plant sliding windows & Persistence/Ridge/RF forecasters
│   ├── inference.py          # Live spectrum classifier, CSV batch scorer, forecaster & lead-time engine
│   ├── week3_models.py       # Neural MLP comparator & 1D-CNN / GRU architecture specifications
│   └── pipeline/             # CLI runnable stage scripts
├── server.ts                 # Express API bridge to live Python models & artifacts
├── README.md
└── requirements.txt
```
