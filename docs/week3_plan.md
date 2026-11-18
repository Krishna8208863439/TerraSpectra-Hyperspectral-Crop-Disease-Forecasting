# Week 3 Implementation Plan (24 to 30 Nov)

**Goal:** Train and honestly compare deep spectral and temporal sequence models against the frozen Week 2 baselines (`XGBoost Set E` & `Lag-Feature Random Forest`), keeping every experiment logged cleanly in `reports/experiment_log.csv`.

---

## Execution Matrix

| Task | Specification & Contract | Comparator (Frozen Baseline) | Priority |
| --- | --- | --- | --- |
| **1D-CNN on Spectra** | 1D convolutions over aligned spectral band axis `(batch, 1, B)` with BatchNorm, GELU, AdaptiveAvgPool, dropout (`0.2`), cosine LR schedule, evaluated on exact `data/processed/*_day5_cv_splits.json` folds. | **Tuned XGBoost Set E** (`Macro-F1 0.4892 ± 0.0386` primary; `1.0000` synthetic) & Neural MLP (`src/week3_models.py`). | **Core** |
| **LSTM / GRU Forecaster** | 2-layer GRU (`hidden=48, dropout=0.2`) ingesting `W=3` windows `(B_vi + B_refl)` from `src/sequences.py` (`1,986` / `1,907` / `1,828` windows) to predict $\text{NDVI}_{t+k}$ & stress probability at $k \in \{1, 2, 3\}$ under `GroupKFold(plant_id)`. | **Persistence** (`k=+3` MAE `0.0688`, $R^2$ `0.7758`) & **Lag-Feature Random Forest** (`k=+3` MAE `0.0327`, $R^2$ `0.9425`). If GRU cannot beat Lag-RF, report honestly. | **Core** |
| **Light Tuning & Experiment Logging** | Constrained tuning inside `StratifiedGroupKFold` / `GroupKFold` (`learning_rate`, `dropout`, `weight_decay`); append every run (`week3_01+`) to `reports/experiment_log.csv`. | Previous best `day6_01` (`F1 0.4892`) & `day6_10` (`MAE 0.0327`). | **Core** |
| **Optional 3D-CNN** | Lightweight spectral-spatial patch 3D-CNN **only if** external ENVI/spatial image cubes become available and timeline has buffer. | N/A (Cut first per scope guard). | **Cut First if Behind** |

---

## Scope & Timeline Guardrail
- **Protect First:** Temporal forecasting comparison (`Persistence` vs `Lag-RF` vs `GRU`) and the live interactive TerraSpectra demo (spectrum CSV uploader + plant forecaster + early-detection lead-time readout).
- **Zero-Leakage Rule:** Every Week 3 model must consume identical plant-grouped CV indices (`primary_day5_cv_splits.json`) and never standardize/tune across held-out `plant_id` groups.
