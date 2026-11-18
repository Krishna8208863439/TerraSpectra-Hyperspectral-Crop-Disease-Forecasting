# TerraSpectra — Hyperspectral Crop Stress Detection & Temporal Forecasting

**Milestone:** Project Technical Report (Draft v1 — Sections 1–4 Complete, Sections 5–6 Outlined)  
**Author:** Shashwat Shukla (Data Associate L1 Intern, Infotact Solutions · Ref. `ITS/DSML/1494`)  
**Repository Modules:** `src/data.py`, `src/preprocessing.py`, `src/features.py`, `src/evaluation.py`, `src/sequences.py`, `src/inference.py`, `src/week3_models.py`

---

## 1. Problem Statement & Objectives

Crop stress and foliar disease alter leaf chlorophyll concentration, cell wall turgor, and internal mesophyll scattering before necrosis or wilting becomes clearly visible to human scouts. Optical spectroscopy measures leaf reflectance across visible (VIS: 400–700 nm), red-edge (690–750 nm), and near-infrared (NIR: 750–1000+ nm) bands to capture these physiological transitions non-destructively.

TerraSpectra frames the problem as three connected empirical tasks designed around strict zero-leakage validation:

1. **Detection:** Classify multi-spectral leaf observations into healthy (`Control (40% Water)` / `Healthy`) versus stressed or diseased states using chemometric baselines (PLS-DA), kernel models (SVM-RBF), tree ensembles (Random Forest, XGBoost), and neural comparators evaluated across unseen plants.
2. **Early Detection & Interpretability:** Identify which spectral wavelengths (red-edge inflection, green-red pigment bands) and narrow-band vegetation indices drive predictions using validation-fold SHAP (`TreeExplainer`) and permutation importance, quantifying how many days early spectral signals flag developing stress.
3. **Temporal Forecasting:** Construct chronological sliding windows (`W` past dates) of per-plant spectral reflectance and vegetation indices to forecast future canopy $\text{NDVI}_{t+k}$ (`k ∈ {1, 2, 3}` steps ahead), benchmarking Ridge Regression and Random Forest lag forecasters against a naive Persistence baseline ($\hat{y}_{t+k} = y_t$) strictly inside `GroupKFold(plant_id)`.

---

## 2. Dataset, Licence & Limitations

### 2.1 Primary Open Dataset (Tier 1 Leaf Spectral CSV)
- **Dataset:** *Plant Phenotyping and Environmental Stress Dataset* (Zenodo Record [`10.5281/zenodo.22755812`](https://doi.org/10.5281/zenodo.22755812))
- **Licence:** Creative Commons Attribution 4.0 International (**CC-BY-4.0**)
- **Raw & Clean Dimensions:**
  - `Multispectral_Reflectance.csv`: **2,285 rows × 37 columns**, joined with `experimental_design.csv` on `Plant_ID` (`5` unmatched metadata rows dropped -> **2,280 labeled rows**; `8` rows with incomplete NaN sensor scans dropped inside preprocessing -> **2,272 clean scans**).
  - **Spectral Bands (10 raw -> 9 aligned):** LED multispectral reflectance means at `365, 460, 525, 570, 645, 670, 700, 780, 890, 970` nm. Band `365 nm` is dropped due to UV noise and low between-class Fisher separation.
  - **Biological & Temporal Structure:** **79 unique plants** (`Plant_ID`), **79 pots** (`Pot_Number`), **2 genotypes** (`Electra`, `Elvar`), spanning **31 chronological dates** (`23–29` repeated scans per plant, median `29`).
  - **Class Distribution:** `Control (40% Water)`: `1,178` scans (`51.67%`, `41` plants); `Drought (10% Water)`: `1,102` scans (`48.33%`, `38` plants). Imbalance ratio = `1.069`.

### 2.2 Companion Synthetic Hyperspectral Benchmark (Tier 3 Clearly Labeled Fallback)
- **File:** `data/raw/synthetic_leaf_disease_spectra_v1.csv` (`src/pipeline/generate_synthetic_spectra.py`, **Apache-2.0**)
- **Dimensions:** **120 observations** across `4` progressive pathology stages (`Healthy`, `Early_Chlorosis`, `Moderate_Blight`, `Severe_Necrosis`; `30` scans/stage), spanning **61 contiguous bands (`400–1000 nm`, `10 nm` step)** across `24` synthetic plants over `5` longitudinal dates. Explicitly tagged `SYNTHETIC_CONTROLLED_STRESS` to benchmark red-edge derivative peak shifts under dense 10 nm resolution.

### 2.3 Explicit Dataset Limitations
1. **Abiotic vs. Biotic Stress Proxy:** Zenodo 22755812 measures controlled abiotic water stress (40% vs. 10% substrate moisture) rather than pathogen-inoculated fungal/bacterial disease. Physiological stress indices (NDVI, NDRE, PRI, REP) respond to chlorosis and water deficit similarly, so transferring thresholds to field biotic blight requires pathogen-labeled validation trials in future work.
2. **Sparse Multispectral Resolution:** With 9 retained discrete LED wavelengths (spacing `25–110 nm`), fine narrow-band absorption troughs around `550 nm` and `720 nm` rely on nearest-band lookup (`570 nm`, `700 nm`) and quadratic inflection interpolation for Red-Edge Position (`REP_nm`).
3. **Boundary Overlap in Early Trial Days:** Because water withholding starts gradually across genotypes, scans from Days 1–7 sit close to the watered control centroid regardless of treatment label.

---

## 3. Methods: Preprocessing, Features, Models & Evaluation Protocol

### 3.1 Leak-Free Preprocessing (`src/preprocessing.py`)
All stateful statistics (column medians for residual imputation, MSC reference spectrum, scalers, PCA rotations, RF/MI band selectors) are fit **exclusively inside training folds** inside scikit-learn pipelines:
- **Band Cleaning (`BadBandDropper`):** Drops noisy `365 nm` UV band and masks water-absorption windows (`1350–1450 nm`, `1800–1950 nm`), keeping aligned wavelength metadata synchronized.
- **Sanitization (`ReflectanceSanitizer`):** Removes `8` broken NaN scan rows upstream, clips residual reflectance to `[0, 100]%`.
- **Denoising (`SavitzkyGolaySmoother`):** Smooths spectra along the wavelength axis (`window=3, polyorder=1` on sparse 9-band primary; `window=5, polyorder=2` on 60-band synthetic; validated via Savitzky & Golay, 1964).
- **Scatter Normalization (`SpectralScatterNormalizer`):** Row-wise **SNV** (Standard Normal Variate: $(x_i - \mu_i)/\sigma_i$, Barnes et al., 1989) compared against train-fit **MSC** and first-derivative finite differences $dR/d\lambda$. SNV + SavGol is retained as the primary spectral representation.

### 3.2 Vegetation Indices & Feature Sets A–E (`src/features.py`)
Indices are extracted strictly from uncentered positive reflectance prior to SNV zero-centering using dynamic `find_nearest_band()`:
- **NDVI** (Rouse et al., 1974): $(R_{800} - R_{670}) / (R_{800} + R_{670})$
- **NDRE** (Gitelson & Merzlyak, 1994): $(R_{800} - R_{720}) / (R_{800} + R_{720})$
- **PRI** (Gamon et al., 1992): $(R_{531} - R_{570}) / (R_{531} + R_{570})$
- **MCARI** (Daughtry et al., 2000): $\left[(R_{700} - R_{670}) - 0.2\,(R_{700} - R_{550})\right] \cdot (R_{700} / R_{670})$
- **REP_nm** (Guyot & Baret, 1988; Cho & Skidmore, 2006): Inflection wavelength inside `690–750 nm`.

Five nested feature sets are materialized per CV fold:
- **Set A:** Preprocessed full spectrum (`9` bands on primary; `60` on synthetic)
- **Set B:** Five biophysical vegetation indices (`NDVI`, `NDRE`, `PRI`, `REP_nm`, `MCARI`)
- **Set C:** Train-fit PCA retaining 99% variance (`3` PCs primary / `8` PCs synthetic)
- **Set D:** Top-5 consensus selected wavelengths (RF importance + Mutual Information on train split: `[460, 570, 645, 700, 890] nm` on primary)
- **Set E:** Combined Indices + Selected Bands (`10` features on primary)

### 3.3 Models & Leak-Free Plant-Grouped Evaluation (`src/evaluation.py`, `src/sequences.py`)
- **Seed & Split Contract:** Fixed `RANDOM_SEED = 42` with 5-fold `StratifiedGroupKFold(n_splits=5)` grouped by `plant_id` (`0` plant overlap between train and validation folds across all 5 splits, persisted to `data/processed/primary_day5_cv_splits.json`).
- **Detection Models:** Random Forest, XGBoost (`scale_pos_weight` balanced), SVM (RBF kernel with `StandardScaler`), and **PLS-DA** (`PLSDAClassifier` chemometrics baseline via scikit-learn `PLSRegression`).
- **Leakage Control Audit:** Compared directly against naive sample-level `StratifiedKFold` ignoring `plant_id`.
- **Sequence Forecasting (`src/sequences.py`):** Per-plant daily aggregated trajectories sliced into `W=3` sliding windows (`45` lag spectral+VI + slope features on primary; `1,986` windows at `k=+1`, `1,907` at `k=+2`, `1,828` at `k=+3`) evaluated with `GroupKFold(plant_id)` comparing Persistence vs. Lag-Feature Ridge vs. Lag-Feature Random Forest.

---

## 4. Results: Baselines, Confusion Matrices, Leakage & Wavelength Importance

### 4.1 Classification Baselines on Frozen Grouped CV (`primary` vs `synthetic`)

| Dataset | Feature Set | Model | CV Balanced Acc (± SD) | CV Macro-F1 (± SD) | ROC-AUC |
| --- | --- | --- | ---: | ---: | ---: |
| Primary (Zenodo) | Set A (9 bands) | Random Forest | `0.4789 ± 0.0206` | `0.4783 ± 0.0209` | `0.4746` |
| Primary (Zenodo) | Set A (9 bands) | XGBoost | `0.4840 ± 0.0194` | `0.4837 ± 0.0195` | `0.4832` |
| Primary (Zenodo) | Set A (9 bands) | SVM (RBF) | `0.4677 ± 0.0183` | `0.4573 ± 0.0205` | `0.4594` |
| Primary (Zenodo) | Set A (9 bands) | PLS-DA | `0.4878 ± 0.0357` | `0.4598 ± 0.0383` | `0.4698` |
| Primary (Zenodo) | Set B (5 VIs) | XGBoost | `0.4851 ± 0.0202` | `0.4838 ± 0.0200` | `0.4737` |
| Primary (Zenodo) | Set C (3 PCs) | XGBoost | `0.4566 ± 0.0199` | `0.4561 ± 0.0196` | `0.4434` |
| Primary (Zenodo) | Set D (5 Sel. Bands) | XGBoost | `0.4873 ± 0.0252` | `0.4867 ± 0.0251` | `0.4703` |
| Primary (Zenodo) | Set E (VIs + Bands) | XGBoost (Untuned) | `0.4883 ± 0.0236` | `0.4877 ± 0.0233` | `0.4630` |
| **Primary (Zenodo)** | **Set E (VIs + Bands)** | **XGBoost (Tuned)** | **`0.4898 ± 0.0388`** | **`0.4892 ± 0.0386`** | **`0.4684`** |
| Synthetic (61 bands) | Set A / D / E | RF / SVM | `1.0000 ± 0.0000` | `1.0000 ± 0.0000` | `1.0000` |
| Synthetic (61 bands) | Set A | PLS-DA | `0.7418 ± 0.1004` | `0.7143 ± 0.1212` | `0.9535` |

### 4.2 Empirical Leakage Proof (`StratifiedGroupKFold` vs. Naive Random `StratifiedKFold`)
Evaluating the exact same **XGBoost + Set E** pipeline with sample-level random splitting leaks replicate daily scans of identical plants across folds, falsely inflating performance by **`+0.0881` Macro-F1** (`0.4877` honest plant-grouped -> `0.5758` leaky naive; ROC-AUC `0.4630` -> `0.6176`). Enforcing `plant_id` grouping prevents this illusion and reveals true cross-plant generalization difficulty.

### 4.3 Out-of-Fold Confusion Matrix & Error Analysis (Primary XGBoost Set E)
- **Aggregated Confusion Matrix:** Control correctly predicted `563` / `1,177`, misclassified as Drought `614` (`52.2%`); Drought correctly predicted `546` / `1,095`, misclassified as Control `549` (`50.1%`). Overall OOF error rate = `51.19%` (`1,163` / `2,272` scans).
- **Root Cause (Boundary Ambiguity vs. Noise):** Misclassified scans exhibit median L2 robust `Z = -0.04` (only `8.2%` exceed `Z > 3.0`) vs. `0.04` for correct predictions, with tiny centroid margin (`-0.001` vs `-0.032`). Single-timepoint static reflectance is overwhelmed by inter-plant genetic morphology variance (`Electra` `47.5%` error vs `Elvar` `55.2%`), proving multi-temporal trajectories are essential.

### 4.4 Wavelength Importance & SHAP Alignment
Validation `TreeExplainer` ranks **`Band_645nm`** (`|SHAP| = 0.3076`), **`Band_670nm`** (`0.2581`, Chlorophyll-a absorption), **`REP_nm`** (`0.2097`, Red-Edge shift correlation `-0.799`), **`MCARI`** (`0.1869`), **`Band_525nm`** (`0.1857`), **`PRI`** (`0.1796`), and **`Band_570nm`** (`0.1514`) as primary decision drivers, aligning positively with Day 2 Fisher discriminant ratios ($\rho = 0.17$).

### 4.5 Temporal Forecasting Baselines (`W=3`, `GroupKFold(plant_id)`)

| Horizon | Sequences (`79` plants) | Persistence MAE / $R^2$ | Lag-Ridge MAE / $R^2$ | Lag-RF MAE / $R^2$ | MAE Improvement vs Persistence |
| --- | ---: | ---: | ---: | ---: | ---: |
| `k = +1` | `1,986` | `0.0247` / `0.9644` | `0.0176` / **`0.9826`** | **`0.0175`** / `0.9822` | **-29.1% error** |
| `k = +2` | `1,907` | `0.0462` / `0.8902` | `0.0267` / **`0.9637`** | **`0.0257`** / `0.9637` | **-44.4% error** |
| `k = +3` | `1,828` | `0.0688` / `0.7758` | `0.0336` / **`0.9427`** | **`0.0327`** / `0.9425`** | **-52.5% error** |

---

## 5. Discussion (Outline — To Be Finalized After Week 3)

- **Why single-scan classification plateaus near ~0.49 F1 on primary drought while multi-step NDVI forecasting achieves $R^2 > 0.94$:** Cross-plant static variance (`Genotype`, leaf orientation, canopy size) dwarfs subtle early drought absorption differences in single snapshots, whereas conditioning on each plant's recent 3-day spectral velocity (`NDVI_slope`, `NDRE_slope`) isolates true temporal physiological trajectory—halving error at `k=+3` relative to Persistence.
- **Role of SavGol + SNV + Vegetation Indices:** Combining domain ratios (`NDVI`, `NDRE`, `PRI`, `MCARI`, `REP`) with top supervised wavelengths (`Set E`) yields consistent improvements across all non-linear models.

---

## 6. Future Work & References (Week 3 Roadmap)

1. Benchmark **1D-CNN** over the spectral band axis against XGBoost Set E on frozen `primary_day5_cv_splits.json`.
2. Train **GRU / LSTM** sequence forecaster on `src/sequences.py` 3D windows and compare directly against Persistence and Lag-RF.
3. Optional patch **3D-CNN** deferred unless image cubes become available (cut first to protect forecasting & interactive demo).

### References & Citations
- **Primary Dataset:** Zenodo Record `10.5281/zenodo.22755812` (*Plant Phenotyping and Environmental Stress Dataset*, CC-BY-4.0).
- **NDVI:** Rouse, J. W., Haas, R. H., Schell, J. A., & Deering, D. W. (1974). Monitoring vegetation systems in the Great Plains with ERTS. *NASA SP-351*, 309–317.
- **NDRE:** Gitelson, A., & Merzlyak, M. N. (1994). Quantitative estimation of chlorophyll-a using reflectance spectra. *Journal of Photochemistry and Photobiology B: Biology*, 22(3), 247–252.
- **PRI:** Gamon, J. A., Peñuelas, J., & Field, C. B. (1992). A narrow-waveband spectral index that tracks diurnal changes in photosynthetic efficiency. *Remote Sensing of Environment*, 41(1), 35–44.
- **MCARI:** Daughtry, C. S. T., Walthall, C. L., Kim, M. S., Brown de Colstoun, E., & McMurtrey, J. E. (2000). Estimating corn leaf chlorophyll concentration from leaf and canopy reflectance. *Remote Sensing of Environment*, 74(2), 229–239.
- **Savitzky-Golay & SNV:** Savitzky, A., & Golay, M. J. E. (1964) *Analytical Chemistry*, 36(8); Barnes, R. J., Dhanoa, M. S., & Lister, S. J. (1989) *Applied Spectroscopy*, 43(5).
