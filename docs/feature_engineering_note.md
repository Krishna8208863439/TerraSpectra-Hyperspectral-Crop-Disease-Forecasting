# Day 4 Feature Engineering Note — Indices, PCA, Band Selection & Sets A–E

**Generated programmatically by:** `python3 src/pipeline/run_day4_features.py`  
**Module:** `src/features.py` (all feature selection & PCA fitted strictly inside `StratifiedGroupKFold` / train split)

---

## 1. Vegetation Index Definitions & Wavelength Mapping

Using `find_nearest_band(wavelengths, target_nm)` on Day 3 aligned bands (`[460.0, 525.0, 570.0, 645.0, 670.0, 700.0, 780.0, 890.0, 970.0]` nm on primary):

- **NDVI:** $(R_{\text{NIR}} - R_{\text{Red}}) / (R_{\text{NIR}} + R_{\text{Red}})$ (nearest 800 nm & 670 nm)
- **NDRE:** $(R_{\text{NIR}} - R_{\text{RedEdge}}) / (R_{\text{NIR}} + R_{\text{RedEdge}})$ (nearest 800 nm & 720 nm)
- **PRI:** $(R_{531} - R_{570}) / (R_{531} + R_{570})$
- **Red-Edge Position (REP):** Peak wavelength of $dR/d\lambda$ inside `690–750 nm` (interpolated via Guyot & Baret inflection estimator on sparse multispectral LEDs, direct derivative quadratic peak on dense 61-band cubes)
- **MCARI:** $\left[(R_{700} - R_{670}) - 0.2\,(R_{700} - R_{550})\right] \cdot (R_{700} / R_{670})$ — **Citation:** *Daughtry, C. S. T., Walthall, C. L., Kim, M. S., Brown de Colstoun, E., & McMurtrey, J. E. (2000). Estimating corn leaf chlorophyll concentration from leaf and canopy reflectance. Remote Sensing of Environment, 74(2), 229–239.*

### Nearest-Band Lookup Table (Primary Zenodo Aligned Spectra)

| Index | Role | Requested | Matched Band | Delta |
| --- | --- | ---: | ---: | ---: |
| `NDVI` | `NIR_800` | `800 nm` | `780 nm` | `±20.0 nm` |
| `NDVI` | `Red_670` | `670 nm` | `670 nm` | `±0.0 nm` |
| `NDRE` | `NIR_800` | `800 nm` | `780 nm` | `±20.0 nm` |
| `NDRE` | `RedEdge_720` | `720 nm` | `700 nm` | `±20.0 nm` |
| `PRI` | `R531` | `531 nm` | `525 nm` | `±6.0 nm` |
| `PRI` | `R570` | `570 nm` | `570 nm` | `±0.0 nm` |
| `REP_nm` | `Red_670` | `670 nm` | `670 nm` | `±0.0 nm` |
| `REP_nm` | `RedEdge_700` | `700 nm` | `700 nm` | `±0.0 nm` |
| `REP_nm` | `NIR_780` | `780 nm` | `780 nm` | `±0.0 nm` |
| `MCARI` | `R700` | `700 nm` | `700 nm` | `±0.0 nm` |
| `MCARI` | `R670` | `670 nm` | `670 nm` | `±0.0 nm` |
| `MCARI` | `R550` | `550 nm` | `570 nm` | `±20.0 nm` |

---

## 2. Leak-Free Dimensionality Reduction & Band Selection (Train Only)

- **PCA (`PCASpectralReducer`):** Standardizes and fits PCA strictly on `X_train`. Captures **`99.30%`** variance in **`3` PCs** on Primary and **`86.99%`** variance in **`8` PCs** on Synthetic.
- **Selected Bands (`SupervisedBandSelector`):** Consensus ranking (normalized Random Forest importance + Mutual Information fitted inside train fold only). Top selected Primary wavelengths: **`[460.0, 570.0, 645.0, 700.0, 890.0]` nm**.

---

## 3. Feature Sets A–E Comparison (5-Fold `StratifiedGroupKFold` by `plant_id`)

| Feature Set | Contents | Primary Dim | Primary LR F1 | Primary RF F1 | Synthetic LR F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| **Set A** | Preprocessed full spectrum | `9` | `0.4425` | `0.4828` | `0.9718` |
| **Set B** | Vegetation indices only (NDVI, NDRE, PRI, REP, MCARI) | `5` | `0.4341` | `0.4847` | `0.9163` |
| **Set C** | PCA components (fit on train split only) | `3` | `0.4498` | `0.4563` | `0.8332` |
| **Set D** | Selected bands (RF importance + Mutual Info on train only) | `5` | `0.4120` | `0.4894` | `1.0000` |
| **Set E** | Indices plus selected bands | `10` | `0.4398` | `0.4945` | `0.9601` |

Saved `.npz` feature sets for Day 5 modeling reside in `data/processed/` (`*_feature_set_Set_A.npz` through `Set_E.npz`).
