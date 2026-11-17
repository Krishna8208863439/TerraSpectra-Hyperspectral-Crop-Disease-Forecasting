# SpectralCrop — Hyperspectral Crop Stress Detection & Temporal Forecasting

Day 1 Setup, Day 2 EDA, Day 3 Spectral Preprocessing & Day 4 Feature Engineering Repository.

## Project Scope

1. **Detection Baseline:** Classify leaf/plant spectral reflectance observations into healthy vs. stressed/diseased states using tabular spectral features and vegetation indices (`scikit-learn`, `XGBoost`).
2. **Simple Temporal Forecast:** Forecast next-timestep vegetation index / stress trajectory ($\Delta\text{NDVI}_{t+1}$) across repeated measurement dates.
3. **Interactive Workbench:** Web console (`server.ts` + React `src/`) to execute live Python verification, Day 2 EDA (`src/data.py`), switchable Day 3 spectral preprocessing (`src/preprocessing.py`), and leak-free Day 4 feature sets A–E (`src/features.py`).

---

## Repository Structure

```text
.
├── app/                      # Web application architecture notes & integration docs
├── data/
│   ├── raw/                  # Immutable Zenodo CC-BY-4.0 CSVs + clearly labeled synthetic fallback CSV
│   └── processed/            # Saved Day 3 preprocessed splits & Day 4 Feature Sets A–E (.npz + manifests)
├── docs/
│   ├── project_brief.md          # Day 1 one-page project brief
│   ├── dataset_note.md           # Day 1 dataset source, licence, labels, and grouping columns
│   ├── mentor_message.md         # Day 1 mentor scope confirmation & cadence message
│   ├── data_summary.md           # Day 2 code-generated data summary & band-drop audit
│   ├── preprocessing_note.md     # Day 3 preprocessing step justifications & separation findings
│   └── feature_engineering_note.md # Day 4 index mapping, MCARI ref, PCA & Feature Sets A–E report
├── notebooks/
│   ├── 01_day1_env_and_data_check.ipynb  # Day 1 environment & sanity-check notebook
│   ├── 01_eda.ipynb                      # Day 2 reproducible EDA notebook
│   ├── 02_preprocessing.ipynb            # Day 3 before/after spectral transform notebook
│   └── 03_features.ipynb                 # Day 4 indices, train-only PCA & RF/MI notebook
├── reports/
│   ├── day2_eda_metrics.json             # Structured JSON EDA metrics
│   ├── day3_preprocessing_metrics.json   # Structured JSON preprocessing ablation metrics
│   ├── day4_features_metrics.json        # Structured JSON PCA, RF/MI & Sets A–E metrics
│   └── figures/                          # Figures 01–04 (Day 2), 05–06 (Day 3), 07–08 (Day 4)
├── src/
│   ├── data.py                           # Day 2 unified loader (spectra, labels, wavelengths, group_ids)
│   ├── preprocessing.py                  # Day 3 scikit-learn Pipeline transformers & config
│   ├── features.py                       # Day 4 nearest-band, VIs, train-only PCA, RF+MI, Sets A–E
│   └── pipeline/
│       ├── verify_env.py                 # Core Python library import verification
│       ├── dataset_loader.py             # CSV loader & spectral summary inspector
│       ├── run_day2_eda.py               # Reproducible Day 2 EDA runner
│       ├── run_day3_preprocessing.py     # Reproducible Day 3 ablation & figure runner
│       ├── run_day4_features.py          # Reproducible Day 4 Feature Sets A–E runner
│       └── generate_synthetic_spectra.py # Synthetic controlled-stress spectra generator
├── README.md
└── requirements.txt
```

---

## Quickstart & Pipeline Execution (Days 1–4)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 src/pipeline/verify_env.py
python3 src/data.py
python3 src/pipeline/run_day2_eda.py
python3 src/pipeline/run_day3_preprocessing.py
python3 src/pipeline/run_day4_features.py

npm install
npm run dev
```

---

## Carry-Forward to Day 5 Modeling

- **Leak-Free Grouping Keys:** Group CV folds by `plant_id` (`StratifiedGroupKFold`) and order temporal forecasts chronologically by `date`.
- **Day 3 Aligned Wavelengths:** `[460, 525, 570, 645, 670, 700, 780, 890, 970] nm` (`Mean_365` dropped, 8 failed NaN rows removed prior to splitting).
- **Day 4 Named Feature Sets (`data/processed/`):** `Set A` (full spectrum) through `Set E` (VIs + train-selected bands) stored ready for Day 5 baseline & XGBoost comparisons.

## Pushing to GitHub

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```
