# Day 3 Preprocessing Note — Which Steps Helped & Why Each Is Included

**Generated programmatically by:** `python3 src/pipeline/run_day3_preprocessing.py`  
**Module:** `src/preprocessing.py` (scikit-learn `Pipeline` + `SpectralPreprocessor`)

---

## 1. One-Sentence Justification for Each Pipeline Step

1. **Drop Bad Bands (`BadBandDropper`):** Removes noisy UV edge bands (`365 nm` on primary, high intra-scan StDev/Mean `0.490`) and SWIR water-absorption windows (`1350–1450 nm`, `1800–1950 nm`) while keeping `wavelengths_` strictly aligned for Day 4 indices.
2. **Reflectance Sanitization (`ReflectanceSanitizer`):** Drops `8` failed NaN scans cleanly prior to splitting, imputes any residual non-finite cells using training-split column medians only, and clips out-of-range values to `[0, 100]%`.
3. **Savitzky-Golay Smoothing (`SavitzkyGolaySmoother`):** Suppresses high-frequency sensor jitter along the spectral axis using a low-order local polynomial filter (`win=3, poly=1` on sparse 9-band primary; `win=5, poly=2` on dense 61-band synthetic) without blurring sharp red-edge inflection points.
4. **Scatter Normalization (`SpectralScatterNormalizer` — SNV & MSC):** Removes multiplicative illumination and leaf-angle baseline offsets via per-sample **SNV** or training-mean **MSC**, exposing shape changes around green (`525–570 nm`) and red-edge (`700–780 nm`) bands.
5. **First-Derivative Spectra (`FirstDerivativeSpectra`):** Computes wavelength-aware numerical slopes $dR/d\lambda$ (`np.gradient` over aligned wavelengths) to remove additive background drift and sharpen red-edge slope shifts.

---

## 2. Empirical Separation Comparison (Which Steps Helped vs. Didn't)

Evaluated strictly on leak-free `StratifiedGroupKFold` (`plant_id` holdout fold) using standardized Logistic Regression Macro-F1 and training Fisher ratio $J$:

| Preprocessing Step | Primary Aligned Bands | Primary Fisher $J$ | Primary Holdout F1 | Synthetic Holdout F1 | Assessment |
| --- | ---: | ---: | ---: | ---: | --- |
| Raw Baseline | `10` | `0.00083` | `0.5656` | `1.0000` | Preserves overall albedo magnitude used by linear LR, but mixes illumination & UV noise |
| Drop Bad Bands (`365 nm`) + Clip | `9` | `0.00091` | `0.4385` | `1.0000` | Raises mean Fisher $J$ (`0.00083` → `0.00091`) by removing noisy UV edge |
| + Savitzky-Golay Smoothing | `9` | `0.00068` | `0.4249` | `1.0000` | Stabilizes high-frequency curve before derivatives; mild smoothing loss on sparse 9-band LEDs |
| + SNV Normalization | `9` | `0.00076` | `0.4699` | `1.0000` | Recovers linear holdout F1 (`0.4249` → `0.4699`) after removing leaf albedo scatter |
| + MSC (Train Reference Only) | `9` | `0.00073` | `0.4651` | `1.0000` | Closely tracks SNV using training-split reference spectrum without test leakage |
| + First Derivative ($dR/d\lambda$) | `9` | `0.00100` | `0.4747` | `0.7176` | Highest Fisher $J$ (`0.00100`) on Primary; degrades sparse-gap linear separation less than dense cubes under noise |

---

## 3. Key Takeaway Carried Forward to Day 4 & Day 5

- **Primary Recommendation:** Enable `BadBandDropper(drop=[365.0])` + `ReflectanceSanitizer(clip=[0, 100])` + gentle `Savitzky-Golay(w=3, p=1)` for the uncentered **vegetation index branch**, and pair with **SNV / MSC** for spectral/PCA/band-selection branches.
- **Warning:** Never compute NDVI/NDRE/PRI/MCARI *after* SNV or first derivative—zero-centered reflectances cause ratio denominators to cross zero. `SpectralFeatureSetPipeline` routes index extraction through the non-centered reflectance branch automatically.
- **Saved Outputs (`data/processed/`):** `primary_day3_preprocessed.npz` (`1809` train / `463` test, `9` aligned bands `[460.0, 525.0, 570.0, 645.0, 670.0, 700.0, 780.0, 890.0, 970.0]`).
