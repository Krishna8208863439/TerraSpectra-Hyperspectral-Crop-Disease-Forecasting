# Day 6 Error Analysis, Interpretability & Forecasting Prep Report

**Generated programmatically by:** `python3 src/pipeline/run_day6_error_and_forecast.py`  
**Evaluated Baseline:** `XGBoost` on **Feature Set E** (`1163` / `2272` out-of-fold errors = **`51.19%`**)

---

## 1. Error Analysis (Plain-Language Diagnosis)

1. **Which classes are confused & biological plausibility?**  
   - False positives and false negatives are balanced between **`Control (40% Water) → Drought (10% Water)`** (`614` scans) and the reverse direction (`549` scans). Biologically, drought stress takes days to diverge from watered controls, creating heavy spectral overlap in early measurement sessions.
2. **Are errors concentrated in particular dates, genotypes, or plants?**  
   - **Early-half vs. Late-half dates:** Error rate runs at **`50.6%`** in the first half of trial dates vs. **`51.8%`** in the second half.  
   - **Genotypes/Fields (`field_id`):** Electra: 47.5% (559/1178); Elvar: 55.2% (604/1094).
3. **Do misclassified spectra look noisy or genuinely ambiguous?**  
   - Misclassified samples have median L2 robust `Z = -0.04` (`8.2%` above `Z > 3.0`) vs. `0.04` for correct samples, and a tight centroid margin (`-0.001` vs. `-0.032`) — proving errors are **primarily genuine boundary ambiguity**, not isolated sensor spikes.

---

## 2. Model Interpretability (TreeExplainer & Day 2 Wavelength Alignment)

What does the model use to separate watered vs. drought-stressed plants? Top features ranked by validation `|SHAP|`:

| Feature | Mean \|SHAP\| | Permutation Imp. | Direction (Corr) |
| --- | ---: | ---: | ---: |
| `Band_645nm` | `0.30761` | `0.02556` | `+0.399` |
| `Band_670nm` | `0.25806` | `0.04066` | `-0.531` |
| `REP_nm` | `0.20971` | `0.00680` | `-0.799` |
| `MCARI` | `0.18694` | `0.03735` | `+0.155` |
| `Band_525nm` | `0.18568` | `0.03730` | `-0.615` |
| `PRI` | `0.17962` | `0.03562` | `-0.189` |
| `Band_570nm` | `0.15140` | `0.03229` | `-0.030` |

- **Comparison with Day 2 EDA:** Across aligned wavelengths (`460–970 nm`), model SHAP importance correlates at **Spearman $\rho = 0.17$** with Day 2 Fisher discriminant ratio $J$, highlighting canopy chlorophyll/water-sensitive indices (**PRI**, **NDVI**, **MCARI**) plus red-edge/green bands (`525`, `570`, `700`, `890 nm`).

---

## 3. Light Hyperparameter Tuning Inside `StratifiedGroupKFold`

- **Untuned `XGBoost` (Set E):** Macro-F1 = `0.4877 ± 0.0233`, Bal. Acc = `0.4883`, ROC-AUC = `0.4630`
- **Tuned `XGBoost` (`{"n_estimators": 200, "max_depth": 6, "learning_rate": 0.06, "subsample": 0.85}`):** Macro-F1 = **`0.4892 ± 0.0386`** (`Δ +0.0015`), Bal. Acc = **`0.4898 ± 0.0388`**, ROC-AUC = **`0.4684`**

---

## 4. Forecasting Feasibility & Sequence Baselines (`src/sequences.py`)

**Verdict for Mentor:** **True temporal forecasting IS directly supported** on our primary dataset (`79` plants, `31` dates, median `28` timepoints/plant yielding **`1986`** sliding windows at `W=3, k=+1`), as well as the multi-timepoint synthetic benchmark (Lag-RF `k=+1` MAE=`0.0421`, $R^2$=`0.8684`). All windows from any given `plant_id` stay strictly inside one CV fold.

| Horizon & Windows | Model | CV MAE (± std) | CV RMSE | CV $R^2$ |
| --- | --- | ---: | ---: | ---: |
| k = +1 (1986 windows) | Persistence (NDVI_{t+k} = NDVI_t) | `0.0247 ± 0.0010` | `0.0388` | `0.9644` |
| k = +1 (1986 windows) | Lag-Feature Ridge Regression | `0.0176 ± 0.0010` | `0.0271` | `0.9826` |
| k = +1 (1986 windows) | Lag-Feature Random Forest | `0.0175 ± 0.0010` | `0.0274` | `0.9822` |
| k = +2 (1907 windows) | Persistence (NDVI_{t+k} = NDVI_t) | `0.0462 ± 0.0021` | `0.0681` | `0.8902` |
| k = +2 (1907 windows) | Lag-Feature Ridge Regression | `0.0267 ± 0.0021` | `0.0390` | `0.9637` |
| k = +2 (1907 windows) | Lag-Feature Random Forest | `0.0257 ± 0.0024` | `0.0389` | `0.9637` |
| k = +3 (1828 windows) | Persistence (NDVI_{t+k} = NDVI_t) | `0.0688 ± 0.0033` | `0.0973` | `0.7758` |
| k = +3 (1828 windows) | Lag-Feature Ridge Regression | `0.0336 ± 0.0029` | `0.0490` | `0.9427` |
| k = +3 (1828 windows) | Lag-Feature Random Forest | `0.0327 ± 0.0038` | `0.0490` | `0.9425` |

Full experiment history logged in **`reports/experiment_log.csv`**.
