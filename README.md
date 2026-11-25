<div align="center">

# 🌿 TerraSpectra

### Hyperspectral Crop Stress Detection & Temporal Forecasting

*Leak-free spectral machine learning: from raw leaf reflectance to explainable stress detection and multi-horizon canopy forecasts.*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Node](https://img.shields.io/badge/Node.js-18%2B-339933)
![Validation](https://img.shields.io/badge/CV-StratifiedGroupKFold(plant__id)-orange)
![Data](https://img.shields.io/badge/Data-CC--BY--4.0-green)
![Synthetic](https://img.shields.io/badge/Synthetic-Apache--2.0-green)
![Status](https://img.shields.io/badge/Status-Week%203%20in%20progress-yellow)

</div>

---

## Table of Contents

- [Why TerraSpectra](#-why-terraspectra)
- [At a Glance](#-at-a-glance)
- [Key Results](#-key-results)
- [Quick Start](#-quick-start)
- [Data Sources](#-data-sources)
- [Methodology](#-methodology)
- [Vegetation Indices](#-vegetation-indices)
- [Evaluation Protocol](#-evaluation-protocol)
- [Installation](#-installation)
- [Running the Full Pipeline](#-running-the-full-pipeline)
- [Web Application](#-web-application)
- [Repository Structure](#-repository-structure)
- [Limitations](#-limitations)
- [Risks & Mitigations](#-risks--mitigations)
- [Roadmap](#-roadmap)
- [Reproducibility](#-reproducibility)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Glossary](#-glossary)
- [Contributing](#-contributing)
- [Citation](#-citation)
- [License](#-license)

---

## 🎯 Why TerraSpectra

Spectral datasets usually contain **many repeated scans of the same plant**. If those replicates land in both the training and validation sets, models memorise plants instead of learning stress signatures, and reported accuracy looks better than it really is.

TerraSpectra is built around one rule: **no information from a validation plant may ever reach training.** Every split is grouped by `Plant_ID`, and every transform (PCA, feature selection, scaling) is fit on training folds only. On top of that honest foundation it provides:

- **Detection:** classify leaf stress from reflectance spectra.
- **Explanation:** show which wavelengths and indices drive predictions, and how early stress is caught.
- **Forecasting:** predict future canopy NDVI per plant.
- **A live workbench** for scoring spectra and CSV batches.

---

## 📌 At a Glance

| | |
|---|---|
| **Core principle** | Zero leakage: grouped splits on `Plant_ID`, fit-on-train-only transforms |
| **Primary data** | 79 plants · 2 genotypes · 31 dates · 10 bands (365–970 nm) · 2,272 clean scans |
| **Classifiers** | Random Forest, XGBoost, SVM (RBF), PLS-DA, Neural MLP |
| **Forecasters** | Persistence baseline, Lag-Feature Ridge, Lag-Feature Random Forest |
| **Indices** | NDVI, NDRE, PRI, MCARI, Red-Edge Position |
| **Interpretability** | Validation-fold SHAP (`TreeExplainer`) and early-detection lead time |
| **Interface** | Express + Node web workbench backed by cached Python models |

| Task | What it does | Core modules |
|---|---|---|
| **1. Detection & Diagnosis** | Preprocess spectra, extract indices, benchmark classifiers in grouped CV | `preprocessing.py`, `features.py`, `evaluation.py` |
| **2. Interpretability & Early Detection** | Rank wavelengths/indices with SHAP, measure lead time on holdout plants, serve live scoring | `inference.py` |
| **3. Temporal Forecasting** | Sliding windows (`W = 3`) forecasting NDVI<sub>t+k</sub>, `k ∈ {1, 2, 3}` | `sequences.py` |

---

## 📊 Key Results

### 🔒 Leakage changes the story
For **XGBoost on Feature Set E (Macro-F1)**:

| Split strategy | Macro-F1 |
| --- | :---: |
| `StratifiedGroupKFold(plant_id)`, honest | **0.4877** |
| Naive random split, leaky | 0.5758 |
| **Inflation from leakage** | **+0.0881** |

> **Takeaway:** ignoring plant identity inflates performance by roughly 9 F1 points. Every headline number in this project uses the grouped figure.

### 📈 Forecasting beats Persistence at every horizon
Setup: `W = 3`, 1,828–1,986 sequences depending on horizon. At `k = +3`:

| Model | MAE ↓ | R² ↑ |
| --- | :---: | :---: |
| Persistence baseline (ŷ<sub>t+k</sub> = y<sub>t</sub>) | 0.0688 | 0.7758 |
| **Lag-Feature Random Forest** | **0.0327** | **0.9425** |
| **MAE reduction** | **52.5%** | |

> **Reading the results:** classifying drought stress from 10 bands is hard once leakage is removed (Macro-F1 ≈ 0.49), while short-horizon NDVI forecasting is far more tractable.

---

## 🚀 Quick Start

```bash
# 1. Environment
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt

# 2. Put the Zenodo CSVs in data/raw/, then verify and run a core stage
python3 src/pipeline/verify_env.py
python3 src/pipeline/run_day5_baselines.py      # grouped-CV baselines + leakage audit

# 3. Build the model cache and launch the app
python3 src/inference.py --action warm-cache
npm install && npm run dev                      # http://localhost:3000
```

> Stages feed each other. For a clean first run, use the [full ordered pipeline](#-running-the-full-pipeline).

---

## 🗂 Data Sources

| Dataset | Origin | Licence | Scope & Limitations |
| --- | --- | --- | --- |
| **Primary Multi-Temporal Plant Spectra**<br>`data/raw/Multispectral_Reflectance.csv` + `experimental_design.csv` | Zenodo [`10.5281/zenodo.22755812`](https://doi.org/10.5281/zenodo.22755812), *Plant Phenotyping and Environmental Stress Dataset* | **CC-BY-4.0** | 2,285 rows (2,272 clean valid scans), 79 plants (`Plant_ID`), 2 genotypes, 31 dates, 10 bands (365–970 nm). Labels are **abiotic water/drought stress** (`Control 40%` vs `Drought 10%`), **not** pathogen inoculation. |
| **Companion Synthetic Benchmark**<br>`data/raw/synthetic_leaf_disease_spectra_v1.csv` | Local generator: `src/pipeline/generate_synthetic_spectra.py` | **Apache-2.0** | 120 scans × 61 bands (400–1000 nm, 10 nm step), 4 stages (`Healthy`, `Early_Chlorosis`, `Moderate_Blight`, `Severe_Necrosis`), 5 dates. Tagged `SYNTHETIC_CONTROLLED_STRESS`. |

Files in `data/raw/` are **immutable**. Please cite the Zenodo record if you reuse the data.

---

## 🔬 Methodology

```mermaid
flowchart LR
    A[Raw spectra<br/>Zenodo + Synthetic] --> B[Preprocessing<br/>BadBand · SG · SNV/MSC]
    B --> C[Vegetation indices]
    C --> D[Feature Sets A–E<br/>train-only PCA · RF+MI]
    D --> E[Grouped CV<br/>StratifiedGroupKFold]
    E --> F[Models<br/>RF · XGB · SVM · PLS-DA · MLP]
    F --> G[SHAP & lead-time]
    B --> H[Sequences W=3]
    H --> I[Forecasters<br/>Persistence · Ridge · RF]
    F --> J[Cached inference bundle]
    I --> J
    J --> K[Web workbench]
```

### Preprocessing (`src/preprocessing.py`)

| Step | Purpose |
| --- | --- |
| `BadBandDropper` | Drops the noisy 365 nm UV band |
| `ReflectanceSanitizer` | Cleans invalid reflectance values |
| Savitzky–Golay | Denoises spectra |
| SNV / MSC | Scatter normalization |
| First derivative | Emphasises spectral shape over absolute level |

### Features (`src/features.py`)
Uncentered vegetation indices plus **Feature Sets A–E**, built with train-only PCA and RF + mutual-information (MI) selection.

### Models

| Task | Models |
| --- | --- |
| Classification | Random Forest · XGBoost · SVM (RBF) · PLS-DA (`PLSDAClassifier`) · Neural MLP |
| Forecasting | Persistence · Lag-Feature Ridge · Lag-Feature Random Forest |
| Planned (Week 3) | 1D-CNN · GRU / LSTM · *(optional)* 3D-CNN |

### Zero-Leakage Guarantees

| Guarantee | How it is enforced |
| --- | --- |
| Plant-level separation | All splits keyed on `Plant_ID` |
| Fit-on-train-only | PCA, RF + MI selection and scalers fit inside each training fold |
| Frozen folds | CV splits saved in `data/processed/*.json`, shared by all models |
| Chronological forecasting | Windows respect time order; `GroupKFold(plant_id)` |
| Explicit audit | Stage 5 quantifies the naive-vs-grouped gap |

---

## 🌱 Vegetation Indices

Standard literature definitions are shown below. The exact band choices for the 10-band dataset (nearest available band to each wavelength) are implemented in `src/features.py`.

| Index | Common formula | Sensitive to |
| --- | --- | --- |
| **NDVI** | (NIR − Red) / (NIR + Red) | Canopy greenness / biomass |
| **NDRE** | (NIR − RedEdge) / (NIR + RedEdge) | Chlorophyll content, early stress |
| **PRI** | (R531 − R570) / (R531 + R570) | Xanthophyll cycle, light-use efficiency |
| **MCARI** | [(R700 − R670) − 0.2 (R700 − R550)] × (R700 / R670) | Chlorophyll absorption |
| **REP** | Wavelength of steepest red-edge slope (~680–750 nm) | Chlorophyll status (red-edge shift) |

---

## 🧪 Evaluation Protocol

| Item | Setting |
| --- | --- |
| Classification CV | Frozen 5-fold `StratifiedGroupKFold(plant_id)` |
| Forecasting CV | `GroupKFold(plant_id)` |
| Classification metric | Macro-F1 from out-of-fold (OOF) predictions |
| Forecasting metrics | MAE and R², compared against Persistence |
| Early detection | Lead time measured on unseen holdout plants |
| Interpretability | SHAP on validation folds only |
| Comparison rule | All models evaluated on identical saved folds |

---

## ⚙️ Installation

**Prerequisites:** Python 3.10+ and Node.js 18+ with npm (recommended minimums; adjust to your tested environment).

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Tech stack:** Python · NumPy · pandas · scikit-learn · XGBoost · PyTorch · `spectral` / `rasterio` / `h5py` · matplotlib / plotly · SHAP · Node.js + Express.

---

## 🔁 Running the Full Pipeline

```bash
# Stage 0: Verify core Python stack imports
python3 src/pipeline/verify_env.py

# Stage 1: Inspect dataset shapes, wavelengths & Plant_ID grouping keys
python3 src/data.py

# Stage 2: Exploratory Data Analysis → Figures 01–04
python3 src/pipeline/run_day2_eda.py

# Stage 3: Leak-free preprocessing → Figures 05–06
python3 src/pipeline/run_day3_preprocessing.py

# Stage 4: Vegetation indices, train-only PCA / RF+MI Sets A–E → Figures 07–08
python3 src/pipeline/run_day4_features.py

# Stage 5: Grouped-CV baselines + leakage audit → Figures 09–10
python3 src/pipeline/run_day5_baselines.py

# Stage 6: Error analysis, SHAP alignment, tuning, forecasting → Figures 11–13
python3 src/pipeline/run_day6_error_and_forecast.py

# Stage 7: Neural comparator, Week 3 readiness & inference model cache
python3 src/week3_models.py
python3 src/inference.py --action warm-cache
```

| Stage | Script | Produces |
| :---: | --- | --- |
| 0 | `verify_env.py` | Environment check |
| 1 | `data.py` | Dataset summary |
| 2 | `run_day2_eda.py` | Figures 01–04 |
| 3 | `run_day3_preprocessing.py` | Preprocessed matrices, Figures 05–06 |
| 4 | `run_day4_features.py` | Sets A–E, Figures 07–08 |
| 5 | `run_day5_baselines.py` | Baseline table, leakage audit, Figures 09–10 |
| 6 | `run_day6_error_and_forecast.py` | Error / SHAP / forecast results, Figures 11–13 |
| 7 | `week3_models.py`, `inference.py` | MLP comparator, cached inference bundle |

### Outputs

| Location | Contents |
| --- | --- |
| `reports/day*_metrics.json` | Structured per-stage metrics |
| `reports/day5_baseline_results.csv` | Baseline results table |
| `reports/experiment_log.csv` | Reproducible experiment tracker |
| `reports/figures/` | Publication PNG charts (01–13) |
| `data/processed/` | Preprocessed matrices, Sets A–E (`.npz`), CV splits (`.json`), cached inference bundle |

---

## 🖥 Web Application

```mermaid
flowchart LR
    U[Browser<br/>localhost:3000] --> S[server.ts<br/>Express API]
    S --> P[src/inference.py]
    P --> C[(Cached inference bundle<br/>data/processed/)]
```

```bash
python3 src/inference.py --action warm-cache   # build the model cache first
npm install
npm run dev
# Open http://localhost:3000
```

| Capability | Description |
| --- | --- |
| Live spectrum classification | Score a single spectrum in real time |
| Batch CSV scoring | Score many scans from a CSV |
| NDVI forecasting | Forecast future canopy NDVI from a plant's recent scans |
| Early-detection lead time | See how far ahead stress is flagged |

---

## 📁 Repository Structure

```text
.
├── data/
│   ├── raw/                  # Immutable Zenodo CC-BY-4.0 CSVs + synthetic fallback CSV
│   └── processed/            # Preprocessed matrices, Sets A–E (.npz), CV splits (.json), inference bundle
├── docs/
│   ├── project_report.md     # Draft technical report (Sections 1–4 complete, 5–6 outlined + citations)
│   ├── weekly_mentor_update.md  # Milestone summary & Week 3 confirmation request
│   ├── week3_plan.md         # Week 3 1D-CNN, GRU/LSTM & light tuning roadmap
│   ├── project_brief.md      # Scope & metrics framing
│   ├── dataset_note.md       # Portal audit & metadata decision log
│   └── ...                   # Per-stage technical notes
├── notebooks/                # Reproducible EDA, preprocessing, feature, baseline & error notebooks
├── reports/
│   ├── day*_metrics.json
│   ├── day5_baseline_results.csv
│   ├── experiment_log.csv
│   └── figures/              # PNG charts (01–13)
├── src/
│   ├── data.py               # Unified loader (Primary Zenodo + Synthetic)
│   ├── preprocessing.py      # BadBandDropper, ReflectanceSanitizer, SavitzkyGolay, SNV/MSC, 1st derivative
│   ├── features.py           # NDVI, NDRE, PRI, REP, MCARI, train-only PCA, RF+MI selection, Sets A–E
│   ├── evaluation.py         # StratifiedGroupKFold harness, PLSDAClassifier, OOF metrics
│   ├── sequences.py          # Sliding windows & Persistence/Ridge/RF forecasters
│   ├── inference.py          # Live classifier, CSV scorer, forecaster & lead-time engine
│   ├── week3_models.py       # Neural MLP comparator & 1D-CNN / GRU specifications
│   └── pipeline/             # CLI-runnable stage scripts
├── server.ts                 # Express API bridge to Python models
├── README.md
└── requirements.txt
```

| Document | Purpose |
| --- | --- |
| `docs/project_report.md` | Full technical report draft |
| `docs/project_brief.md` | Scope, goals and metric framing |
| `docs/dataset_note.md` | Dataset audit and metadata decisions |
| `docs/week3_plan.md` | Deep-learning roadmap |
| `docs/weekly_mentor_update.md` | Progress summary for mentor review |

---

## ⚠️ Limitations

- **Abiotic, not biotic stress:** primary labels are water/drought stress. Do **not** read results as pathogen or disease detection on real crops.
- **Synthetic data is not field data:** it validates the pipeline and dense-band behavior only.
- **Coarse spectral resolution:** 10 bands (365–970 nm) limit fine red-edge and derivative features.
- **Modest honest accuracy:** grouped Macro-F1 ≈ 0.49 (XGBoost, Set E) reflects a hard task once leakage is removed.
- **Small cohort:** 79 plants and 2 genotypes limit claims about other species and environments.

---

## 🛡 Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| No suitable dataset | Decide by end of Week 1; use the documented fallback instead of waiting |
| Curse of dimensionality | Band selection or PCA (train-only), strong regularization, cross-validation |
| Data leakage | Group-based splits on `Plant_ID` plus an explicit leakage audit |
| Time overrun | Treat the 3D-CNN as optional; a solid baseline, working demo and clear report beat an unfinished deep model |
| Plagiarism / attribution | Original code and text; cite every dataset and paper used |

---

## 🗺 Roadmap

| Status | Milestone |
| :---: | --- |
| ✅ | Leak-free preprocessing and feature pipeline |
| ✅ | Grouped-CV baselines (RF, XGBoost, SVM, PLS-DA) and leakage audit |
| ✅ | SHAP interpretability and early-detection lead time |
| ✅ | Multi-horizon forecasting (Persistence / Ridge / RF) |
| ✅ | Neural MLP comparator and live inference app |
| ⬜ | 1D-CNN and GRU / LSTM models (`docs/week3_plan.md`) |
| ⬜ | Light hyperparameter tuning across models |
| ⬜ | Finish report Sections 5–6 |
| ⬜ | *(Optional)* 3D-CNN on hyperspectral cubes |

---

## 🔁 Reproducibility

- [x] Frozen CV folds saved to `data/processed/`
- [x] Preprocessing, PCA and selection fit on training folds only
- [x] Per-stage metrics in `reports/day*_metrics.json`
- [x] Experiment tracker in `reports/experiment_log.csv`
- [x] Immutable raw data
- [ ] Pin random seeds and dependency versions in `requirements.txt` (confirm)

---

## 🩺 Troubleshooting

| Problem | Likely fix |
| --- | --- |
| `ModuleNotFoundError` | Activate `.venv`, re-run `pip install -r requirements.txt`, check with `verify_env.py` |
| Web app shows no predictions | Run `python3 src/inference.py --action warm-cache` first |
| Missing data file errors | Confirm both Zenodo CSVs are in `data/raw/` with exact filenames |
| Port 3000 already in use | Stop the other process or change the port in `server.ts` |
| A later stage fails | Run earlier stages first; each stage's outputs feed the next |

---

## ❓ FAQ

**Why is Macro-F1 only ~0.49?**
The evaluation is honest: plants never cross folds and the data has only 10 bands. The naive split's 0.5758 is inflated by leakage.

**Is this disease detection?**
No. The real data captures drought stress. The synthetic benchmark simulates disease stages but is not real.

**Why compare against Persistence?**
It is a strong, simple time-series baseline. Cutting MAE by 52.5% at `k = +3` shows the lag features add real signal.

**Why group by `Plant_ID`?**
Repeated scans of one plant are highly correlated. Grouping prevents the model from being rewarded for recognising a plant it has already seen.

---

## 📖 Glossary

| Term | Meaning |
| --- | --- |
| **Leakage** | Information from validation data influencing training, inflating metrics |
| **Grouped CV** | Cross-validation where all samples of one group (plant) stay in the same fold |
| **OOF** | Out-of-fold: predictions made on data a model did not train on |
| **Macro-F1** | F1 averaged equally across classes |
| **SNV / MSC** | Standard Normal Variate / Multiplicative Scatter Correction |
| **SG filter** | Savitzky–Golay smoothing filter |
| **SHAP** | Shapley-value-based feature attribution |
| **PLS-DA** | Partial Least Squares Discriminant Analysis |
| **REP** | Red-Edge Position |
| **Persistence** | Baseline that predicts the future equals the latest observation |
| **Lead time** | How much earlier stress is detected than a reference point |

---

## 🤝 Contributing

1. Fork and create a feature branch.
2. Keep all splits grouped by `Plant_ID`; fit every transform on training data only.
3. Log new experiments in `reports/experiment_log.csv`.
4. Open a pull request describing the change and its effect on grouped-CV metrics.

---

## 📚 Citation

Please cite the source dataset:

> *Plant Phenotyping and Environmental Stress Dataset.* Zenodo. https://doi.org/10.5281/zenodo.22755812 (CC-BY-4.0)

```bibtex
@dataset{terraspectra_source,
  title     = {Plant Phenotyping and Environmental Stress Dataset},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22755812},
  license   = {CC-BY-4.0}
}
```

*Add the original authors and year from the Zenodo record before publishing.*

---

## 📄 License

- **Code:** add your chosen license (e.g., MIT or Apache-2.0) and a `LICENSE` file.
- **Primary dataset:** CC-BY-4.0 (attribution required).
- **Synthetic benchmark:** Apache-2.0.
