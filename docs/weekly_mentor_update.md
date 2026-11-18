# Weekly Progress Update — Mentor Summary (Week 2 Consolidation)

**To:** Project Mentor · Infotact Solutions (Ref. `ITS/DSML/1494`)  
**From:** Shashwat Shukla, Data Associate L1 Intern  
**Project:** TerraSpectra — Hyperspectral Crop Stress Detection & Temporal Forecasting

---

- **Done:**
  - Selected & audited primary open dataset (**Zenodo `10.5281/zenodo.22755812`, CC-BY-4.0**; `2,280` labeled leaf scans across `79` plants and `31` dates) alongside a `61`-band synthetic red-edge disease progression benchmark (`400–1000 nm`).
  - Completed full EDA (`src/data.py`), leak-free preprocessing pipeline (`src/preprocessing.py`: bad-band drop `365 nm`, clipping, Savitzky-Golay smoothing, SNV/MSC/1st-derivative), and train-only feature engineering (`src/features.py`: NDVI, NDRE, PRI, MCARI, Red-Edge Position, PCA, RF+MI band selection, Sets A–E).
  - Benchmarked 4 baselines (RF, XGBoost, SVM-RBF, PLS-DA) under strict 5-fold `StratifiedGroupKFold(plant_id)`, ran SHAP/permutation error diagnostics, performed grouped hyperparameter tuning, and built sliding-window sequence forecasting baselines (`src/sequences.py`).
- **Key Result:**
  - **Temporal Forecasting (Headline Result):** On `1,986` (`k=+1`) to `1,828` (`k=+3`) plant-grouped sliding windows (`W=3`), **Lag-Feature Random Forest** cuts canopy NDVI forecast error by **52.5%** at horizon `k=+3` (**MAE `0.0327`**, **$R^2 = 0.9425$**) compared to Persistence (`MAE 0.0688`, `R^2 = 0.7758`).
  - **Static Leaf Classification & Leakage Proof:** Best leak-free baseline is **Tuned XGBoost on Set E** (**Macro-F1 `0.4892 ± 0.0386`**, synthetic Macro-F1 **`1.0000`**). Critically, running naive random `StratifiedKFold` instead of plant-grouped CV falsely inflates F1 by **`+0.0881`** (`0.4877 → 0.5758`), proving why `plant_id` grouping is mandatory.
- **Issues / Dataset Limitations:**
  - Primary Zenodo labels reflect abiotic drought stress (`Control 40%` vs `Drought 10%` water) rather than pathogen inoculation, and across discrete LED bands early-stage single-scan overlap leaves static CV F1 near `0.49` across unseen plants.
  - Because repeated daily measurements (`23–29` scans/plant) ARE present, temporal forecasting is **not blocked** and clearly captures diverging stress trajectories.
- **Next Week (Week 3: 24 to 30 Nov):**
  - Train and benchmark a **1D-CNN** over the spectral band axis against XGBoost Set E on the exact frozen `primary_day5_cv_splits.json` splits.
  - Train an **LSTM / GRU sequence forecaster** on `src/sequences.py` 3D windows and compare head-to-head against Persistence and Lag-Feature Random Forest/Boosting (`t+1, t+2, t+3`).
  - Maintain `reports/experiment_log.csv` with light grouped tuning and expand the interactive live inference demo.
- **Need from You:**
  - Please confirm if any pathogen-inoculated multi-temporal leaf cube dataset is available internally; otherwise we will evaluate Week 3 deep/temporal models on the frozen Zenodo `22755812` + `61`-band synthetic benchmarks and note the abiotic drought proxy clearly in the final report & PPT.
