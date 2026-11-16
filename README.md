# SpectralCrop — Hyperspectral Crop Stress Detection & Temporal Forecasting

Day 1 Setup & Day 2 Data Loading / Exploratory Data Analysis Repository.

## Project Scope

1. **Detection Baseline:** Classify leaf/plant spectral reflectance observations into healthy vs. stressed/diseased states using tabular spectral features and vegetation indices (`scikit-learn`, `XGBoost`).
2. **Simple Temporal Forecast:** Forecast next-timestep vegetation index / stress trajectory ($\Delta\text{NDVI}_{t+1}$) across repeated measurement dates.
3. **Interactive Workbench:** Web console (`server.ts` + React `src/`) to audit repository structure, execute live Python stack verification, run reproducible Day 2 EDA (`src/data.py`, `src/pipeline/run_day2_eda.py`), inspect interactive spectral/difference/outlier/temporal charts, view saved PNG figures, and edit project documentation.

---

## Repository Structure

```text
.
├── app/                      # Web application architecture notes & integration docs
├── data/
│   ├── raw/                  # Downloaded Zenodo CC-BY-4.0 CSVs + clearly labeled synthetic fallback CSV
│   └── processed/            # Output directory for Day 3+ cleaned tables & split manifests
├── docs/
│   ├── project_brief.md      # Day 1 one-page project brief: problem, data, success metrics
│   ├── dataset_note.md       # Day 1 dataset source, licence, shape, labels, and grouping columns
│   ├── mentor_message.md     # Day 1 mentor scope confirmation & cadence message
│   └── data_summary.md       # Day 2 code-generated data summary & Day 3 band drop/audit plan
├── notebooks/
│   ├── 01_day1_env_and_data_check.ipynb  # Day 1 environment & spectral sanity-check notebook
│   └── 01_eda.ipynb                      # Day 2 reproducible EDA notebook
├── reports/
│   ├── day2_eda_metrics.json             # Structured JSON EDA metrics computed from src/data.py
│   └── figures/
│       ├── 01_mean_spectra_variance.png        # Class mean spectra ± 1 SD bands
│       ├── 02_difference_spectrum_red_edge.png # ΔR, Fisher ratio, Red-Edge & NIR windows
│       ├── 03_class_group_and_outliers.png     # Class/plant balance & robust Z > 3 outliers
│       └── 04_temporal_spectral_progression.png# NDVI / NDRE progression across 31 dates
├── src/
│   ├── data.py                           # Unified loader returning spectra, labels, wavelengths, group_ids
│   └── pipeline/
│       ├── verify_env.py                 # Core Python library import verification script
│       ├── dataset_loader.py             # CSV loader & spectral summary inspector
│       ├── run_day2_eda.py               # Reproducible Day 2 EDA, figure & docs/data_summary.md generator
│       └── generate_synthetic_spectra.py # Fallback #3 synthetic controlled-stress spectra generator
├── README.md
└── requirements.txt
```

---

## Quickstart & Environment Verification

### 1. Python Stack Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Verify All Core Library Imports (Day 1)

```bash
python3 src/pipeline/verify_env.py
```

Required packages verified: `numpy`, `pandas`, `scikit-learn`, `xgboost`, `matplotlib`, `spectral`.

### 3. Run Day 2 Loader & Reproducible EDA Pipeline

```bash
python3 src/data.py
python3 src/pipeline/run_day2_eda.py
npm install
npm run dev
```

`run_day2_eda.py` programmatically computes all shape, NaN/duplicate, grouping, Fisher separability, outlier, temporal, and band-drop diagnostics directly from `src/data.py` and regenerates `reports/day2_eda_metrics.json`, `reports/figures/*.png`, and `docs/data_summary.md`.

---

## Carry-Forward to Day 3 & Day 5

- **Leak-Free Grouping Keys:** `plant_id` (79 plants), `plot_id` (79 pots), `field_id` (2 genotypes), and `date` (31 dates `07-08-21` to `08-12-21`).
- **Rule:** All Day 5 cross-validation must group by `plant_id` (`StratifiedGroupKFold`) and respect chronological `date` ordering for temporal forecasts.
- **Day 3 Cleaning & Band Drop List:** Drop the 8 failed-scan rows containing `NaN` spectra and audit noisy edge bands `Mean_365` (365 nm) and `Mean_970` (970 nm).

## Pushing to GitHub

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```
