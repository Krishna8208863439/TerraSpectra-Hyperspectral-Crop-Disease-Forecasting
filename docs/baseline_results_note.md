# Day 5 Baseline Models & Leak-Free Evaluation Report

**Generated programmatically by:** `python3 src/pipeline/run_day5_baselines.py`  
**Evaluation Harness:** `src/evaluation.py` (`StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)` grouped by `plant_id`)  
**Zero-Leakage Guarantee:** `0` plant overlap across every CV fold; scalers, MSC references, PCA, and RF/MI band selectors refit strictly inside each fold.

---

## 1. Primary Dataset Results Table — Feature Set A (Mean ± Std Across 5 Plant-Grouped Folds)

| Model | Feature Set | Balanced Accuracy | Macro-F1 | ROC-AUC |
| --- | :---: | ---: | ---: | ---: |
| Random Forest | A | `0.4789 ± 0.0206` | `0.4783 ± 0.0209` | `0.4746 ± 0.0284` |
| XGBoost | A | `0.4840 ± 0.0194` | `0.4837 ± 0.0195` | `0.4832 ± 0.0225` |
| SVM (RBF) | A | `0.4677 ± 0.0183` | `0.4573 ± 0.0205` | `0.4594 ± 0.0368` |
| PLS-DA | A | `0.4878 ± 0.0357` | `0.4598 ± 0.0383` | `0.4698 ± 0.0351` |

---

## 2. Best Baseline Model (XGBoost) Across Feature Sets B–E

| Model | Feature Set | Balanced Accuracy | Macro-F1 | ROC-AUC |
| --- | --- | ---: | ---: | ---: |
| XGBoost | B (Vegetation indices only (NDVI, NDRE, PRI, REP, MCARI)) | `0.4851 ± 0.0202` | `0.4838 ± 0.0200` | `0.4737 ± 0.0215` |
| XGBoost | C (PCA components (fit on train split only)) | `0.4566 ± 0.0199` | `0.4561 ± 0.0196` | `0.4434 ± 0.0388` |
| XGBoost | D (Selected bands (RF importance + Mutual Info on train only)) | `0.4873 ± 0.0252` | `0.4867 ± 0.0251` | `0.4703 ± 0.0301` |
| XGBoost | E (Indices plus selected bands) | `0.4883 ± 0.0236` | `0.4877 ± 0.0233` | `0.4630 ± 0.0318` |

**Primary Best Baseline to Beat:** **`XGBoost`** on **Feature Set E** — Macro-F1 **`0.4877 ± 0.0233`**, Balanced Acc **`0.4883 ± 0.0236`**, ROC-AUC **`0.4630`**.

---

## 3. The Leakage Demonstration (Plant-Grouped vs. Naive Random Split)

Running **`XGBoost` (Set E)** with a naive random sample split (`StratifiedKFold`, ignoring `plant_id`) leaks replicate plant signatures across train and validation folds:

| Dataset | Grouped Balanced Acc | Naive Random Bal. Acc | Inflation Gap (Δ) | Grouped Macro-F1 | Naive Macro-F1 | F1 Inflation (Δ) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Primary (Zenodo 22755812)** | `0.4883` | `0.5760` | **`+0.0877`** | `0.4877` | `0.5758` | **`+0.0881`** |
| **Synthetic (400–1000 nm)** | `1.0000` | `1.0000` | `+0.0000` | `1.0000` | `1.0000` | `+0.0000` |

---

## 4. Interpretation & Week 3 Baseline Benchmark

- Naive random sample splitting artificially inflates Primary Macro-F1 by **`+0.0881`** (`0.4877 → 0.5758`), proving why cross-validation must isolate whole plants (`plant_id`) rather than mixing repeated daily scans of the same plant across splits.
- Under honest plant-grouped validation, raw-spectrum single-timepoint static separation across the full 31-day trial sits around `0.4877` Macro-F1 because early trial dates have nearly identical water-stress spectra (analyzed in detail on Day 6).
- **Target to Beat in Week 3 / Day 6:** Tuned `XGBoost` and temporal lag/sequence models evaluated strictly on the same `plant_id` folds (`data/processed/primary_day5_cv_splits.json`).
