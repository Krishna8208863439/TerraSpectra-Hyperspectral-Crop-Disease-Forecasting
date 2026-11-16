# Day 2 Data Summary & EDA Findings

**Generated programmatically by:** `python3 src/pipeline/run_day2_eda.py`  
**Primary Dataset:** Zenodo Record `22755812` (`CC-BY-4.0`) — *Plant Phenotyping and Environmental Stress Dataset*  
**Limitation Disclosure:** This dataset measures **abiotic drought/water-stress** (`Control 40% Water` vs. `Drought 10% Water`), not pathogen inoculation. (It is not a satellite land-cover fallback dataset such as Indian Pines or Salinas.)

---

## 1. Dataset Shape, Sanity Checks & Class Balance

- **Raw vs. Labeled Scans:** `2,285` raw rows in `Multispectral_Reflectance.csv`; `5` rows (`PlantId_78`) lack matching entries in `experimental_design.csv` and are excluded by `src/data.py`, leaving **`2,280` labeled samples × `10` spectral bands** (`dtype: float64`).
- **Data Integrity:** `80` missing spectral values across `8` failed-scan rows (must be dropped on Day 3), `0` duplicate `Sample_ID`s, and `0` exact duplicate spectral vectors. Reflectance spans `0.76%` to `35.48%`.
- **Wavelength Axis:** `365 nm` to `970 nm` with non-uniform multispectral spacings (`[25.0, 30.0, 45.0, 65.0, 75.0, 80.0, 95.0, 110.0]` nm).
- **Class Balance (Imbalance Ratio `1.069:1`):**
- **Control (40% Water):** 1,178 scans (51.67%) across 41 plants
- **Drought (10% Water):** 1,102 scans (48.33%) across 38 plants

---

## 2. Grouping Structure (Day 5 Leak-Free Split Key)

- **Biological & Spatial Keys:** `79` unique plants (`plant_id`), `79` pots (`plot_id`), `2` genotypes (`field_id`), and `31` acquisition dates (`date`).
- **Repeated Scans per Plant:** min `23`, median `29.0`, mean `28.86`, max `29`.
- **Split Decision:** Group all cross-validation folds by **`plant_id`** (`StratifiedGroupKFold`) and order temporal forecasts chronologically by **`date`**.

---

## 3. Discriminative Wavelengths, Outliers & Bands to Drop on Day 3

- **Most Discriminative Bands (Red Edge & NIR Plateau):**
- `Mean_525` (525 nm · VIS): Fisher J = `0.0013`, ΔR = `+0.199%` (Cohen's d = `+0.051`)
- `Mean_570` (570 nm · VIS): Fisher J = `0.0012`, ΔR = `+0.208%` (Cohen's d = `+0.048`)
- `Mean_780` (780 nm · NIR Plateau): Fisher J = `0.0009`, ΔR = `+0.230%` (Cohen's d = `+0.042`)
- `Mean_645` (645 nm · VIS): Fisher J = `0.0007`, ΔR = `+0.288%` (Cohen's d = `+0.039`)
- **Red-Edge Slope (`700 → 780 nm`):** Control `0.1641%/nm` vs. Drought `0.1641%/nm`.
- **Outlier Spectra:** Using per-class median L2 distance (`median = 10.927`, `MAD = 5.152`), **`172` scans (`7.57%`)** exceed `robust Z > 3.0` and will be inspected/winsorized on Day 3.
- **Bands Flagged to Drop or Isolate on Day 3:**
- `Mean_365` (365 nm · UV Edge): UV spectrum edge (365 nm): high intra-scan relative noise (StDev/Mean=0.490) and low Fisher separation (0.0002).
- `Mean_970` (970 nm · NIR Plateau): Water-absorption shoulder / Si-detector edge (970 nm): elevated noise (StDev/Mean=0.405); verify before retaining for moisture indices.

---

## 4. Temporal Spectral Progression (07-08-21 to 08-12-21)

- **Control (40% Water):** Early-half mean NDVI `0.7788` → Late-half `0.4775` (Δ = `-0.3013`)
- **Drought (10% Water):** Early-half mean NDVI `0.7805` → Late-half `0.4748` (Δ = `-0.3056`)

Saved figures in `reports/figures/`: `01_mean_spectra_variance.png`, `02_difference_spectrum_red_edge.png`, `03_class_group_and_outliers.png`, and `04_temporal_spectral_progression.png`.
