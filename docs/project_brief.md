# Project Brief: Spectral Crop Stress Detection & Temporal Forecasting

**Document:** `docs/project_brief.md` · **Date:** Monday, 16 November · **Milestone:** Day 1 Setup & Data Decision

---

## 1. Problem Statement

Crop disease and physiological plant stress alter leaf pigmentation, cellular mesophyll structure, and water content before visible symptoms become severe to the naked eye. High-resolution optical reflectance spectroscopy captures these biochemical shifts across visible (VIS: 400–700 nm), red-edge (700–750 nm), and near-infrared (NIR: 750–1000+ nm) bands.

This project builds a reproducible, leak-free machine learning pipeline with two connected deliverables:
1. **Detection Baseline:** Classify plant/leaf spectral observations into healthy vs. stressed/diseased states using spectral bands and domain vegetation indices (NDVI, Red-Edge NDRE, PRI, GNDVI).
2. **Simple Temporal Forecast:** Predict next-timestep spectral health trajectories (e.g., $\Delta\text{NDVI}_{t+1}$ or stress-class transition probability) from multi-temporal plant histories.

---

## 2. Data Summary & Split Integrity

- **Selected Primary Dataset:** Open-access multi-temporal plant spectral reflectance CSV dataset (`data/raw/Multispectral_Reflectance.csv` joined with `data/raw/experimental_design.csv`, Zenodo DOI `10.5281/zenodo.22755812`, Licence: `CC-BY-4.0`), plus documented fallback evaluation across Kaggle, Zenodo, Mendeley Data, and IEEE DataPort.
- **Spectral Coverage:** Leaf/canopy reflectance bands spanning 365 nm to 970 nm (`Mean_365` through `Mean_970` plus UV/blue-green ratios and band standard deviations).
- **Grouping & Leakage Prevention (Carry Forward to Day 2 & Day 5):** Multiple spectral scans are recorded per `Plant_ID` across repeated dates (`date`, `TimeStamp`). Random row-level splitting would leak plant identity across train and test folds. All downstream evaluations will strictly use `GroupKFold` / `StratifiedGroupKFold` grouped by `Plant_ID` (and temporal holdouts ordered by `date`).

---

## 3. Success Metrics

| Task | Primary Metric | Secondary Metric | Baseline Target / Sanity Bar |
| --- | --- | --- | --- |
| **Detection Baseline** (Binary / Multi-class) | **Macro F1-Score** (accounts for class balance) | **ROC-AUC** & Per-Class Recall | Beat majority-class & single-index (NDVI threshold) baseline under plant-grouped CV |
| **Temporal Forecast** (Next-date index / state) | **MAE & RMSE** on $\text{NDVI}_{t+1}$ (or Red-Edge slope) | **Directional Accuracy** / Forecast $R^2$ | Beat persistence baseline ($\hat{y}_{t+1} = y_t$) across held-out plants |
| **Engineering & Reproducibility** | Zero plant/date leakage across splits | End-to-end deterministic run from `src/` | Reproducible `verify_env.py` + documented dataset note |

---

## 4. Scope Boundaries & Risks

- **In Scope:** Tabular spectral feature engineering, regularized linear & tree-based baselines (`LogisticRegression`, `RandomForest`, `XGBoost`), plant-grouped validation, and simple lag-based temporal forecasting.
- **Out of Scope (Week 1):** Raw 3D hypercube deep CNNs, custom hardware calibration, or multi-season domain transfer without external field trials.
- **Key Limitation Note:** Where abiotic stress (e.g., controlled drought/water-stress phenotyping) stands in for pathogen-specific labels, this limitation is explicitly flagged in `docs/dataset_note.md` and model cards.
