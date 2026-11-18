# SpectralCrop — Hyperspectral Crop Stress Detection & Temporal Forecasting

Day 1–6 End-to-End Spectral Machine Learning Workbench: Setup, EDA, Spectral Preprocessing, Feature Engineering, Leak-Free Baseline Modeling, SHAP Interpretability, Tuning & Temporal Sequence Forecasting Prep.

## Project Scope

1. **Detection Baseline:** Classify leaf/plant spectral reflectance observations into healthy vs. stressed/diseased states using Random Forest, XGBoost, SVM (RBF), and PLS-DA inside leak-free plant-grouped 5-fold CV (`StratifiedGroupKFold`).
2. **Temporal Forecast Prep (`src/sequences.py`):** Construct chronological per-plant sliding spectral + VI windows (`W` steps → horizon `k ∈ {1,2,3}`) and benchmark Persistence vs. Lag-Feature Ridge vs. Lag-Feature Random Forest inside `GroupKFold(plant_id)`.
3. **Interactive Workbench:** Web console (`server.ts` + React `src/`) to execute live Python verification, Day 2 EDA (`src/data.py`), switchable Day 3 spectral preprocessing (`src/preprocessing.py`), leak-free Day 4 feature sets A–E (`src/features.py`), Day 5 baseline & leakage evaluation (`src/evaluation.py`), and Day 6 error analysis, SHAP alignment, tuning, experiment logging & sequence forecasting.

---

## Repository Structure

```text
.
├── app/                      # Web application architecture notes & integration docs
├── data/
│   ├── raw/                  # Immutable Zenodo CC-BY-4.0 CSVs + clearly labeled synthetic fallback CSV
│   └── processed/            # Day 3 preprocessed splits, Day 4 Feature Sets A–E (.npz), Day 5 CV splits (.json)
├── docs/
│   ├── project_brief.md            # Day 1 one-page project brief
│   ├── dataset_note.md             # Day 1 dataset source, licence, labels, and grouping columns
│   ├── mentor_message.md           # Day 1 mentor scope confirmation & cadence message
│   ├── data_summary.md             # Day 2 code-generated data summary & band-drop audit
│   ├── preprocessing_note.md       # Day 3 preprocessing step justifications & separation findings
│   ├── feature_engineering_note.md # Day 4 index mapping, MCARI ref, PCA & Feature Sets A–E report
│   ├── baseline_results_note.md    # Day 5 grouped CV baseline tables & leakage inflation proof
│   └── error_interpretability_note.md # Day 6 OOF error diagnosis, SHAP vs Day 2 ρ, tuning & forecast verdict
├── notebooks/
│   ├── 01_day1_env_and_data_check.ipynb  # Day 1 environment & sanity-check notebook
│   ├── 01_eda.ipynb                      # Day 2 reproducible EDA notebook
│   ├── 02_preprocessing.ipynb            # Day 3 before/after spectral transform notebook
│   ├── 03_features.ipynb                 # Day 4 indices, train-only PCA & RF/MI notebook
│   ├── 04_baselines.ipynb                # Day 5 4-model Set A + Sets B-E sweep + leakage demo
│   └── 05_error_analysis.ipynb           # Day 6 OOF errors, SHAP, grouped tuning & sequences
├── reports/
│   ├── day2_eda_metrics.json             # Structured JSON EDA metrics
│   ├── day3_preprocessing_metrics.json   # Structured JSON preprocessing ablation metrics
│   ├── day4_features_metrics.json        # Structured JSON PCA, RF/MI & Sets A–E metrics
│   ├── day5_baseline_metrics.json        # Structured JSON Day 5 CV metrics & leakage benchmark
│   ├── day5_baseline_results.csv         # Clean Day 5 tabular results CSV
│   ├── day6_error_and_forecast_metrics.json # Day 6 OOF errors, SHAP, tuning & forecasting JSON
│   ├── experiment_log.csv                # Full reproducible Day 5–6 experiment ledger
│   └── figures/                          # Figures 01–04 (Day 2), 05–06 (Day 3), 07–08 (Day 4), 09–10 (Day 5), 11–13 (Day 6)
├── src/
│   ├── data.py                           # Day 2 unified loader (spectra, labels, wavelengths, group_ids)
│   ├── preprocessing.py                  # Day 3 scikit-learn Pipeline transformers & config
│   ├── features.py                       # Day 4 nearest-band, VIs, train-only PCA, RF+MI, Sets A–E
│   ├── evaluation.py                     # Day 5 StratifiedGroupKFold harness, PLSDAClassifier & OOF aggregator
│   ├── sequences.py                      # Day 6 chronological sliding-window sequence & lag forecasters
│   └── pipeline/
│       ├── verify_env.py                 # Core Python library import verification
│       ├── dataset_loader.py             # CSV loader & spectral summary inspector
│       ├── run_day2_eda.py               # Reproducible Day 2 EDA runner
│       ├── run_day3_preprocessing.py     # Reproducible Day 3 ablation & figure runner
│       ├── run_day4_features.py          # Reproducible Day 4 Feature Sets A–E runner
│       ├── run_day5_baselines.py         # Reproducible Day 5 baseline & leakage demo runner
│       ├── run_day6_error_and_forecast.py # Reproducible Day 6 error, SHAP, tuning & forecast runner
│       └── generate_synthetic_spectra.py # Synthetic controlled-stress spectra generator
├── README.md
└── requirements.txt
```

---

## Quickstart & Pipeline Execution (Days 1–6)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 src/pipeline/verify_env.py
python3 src/data.py
python3 src/pipeline/run_day2_eda.py
python3 src/pipeline/run_day3_preprocessing.py
python3 src/pipeline/run_day4_features.py
python3 src/pipeline/run_day5_baselines.py
python3 src/pipeline/run_day6_error_and_forecast.py

npm install
npm run dev
```

## Pushing to GitHub

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```
