# Dataset Decision & Metadata Note (Day 1 — Blocks 4 & 5)

**Document:** `docs/dataset_note.md` · **Date:** Monday, 16 November · **Decision Status:** Locked for Day 2 EDA

---

## 1. Repository Search Log (Block 4)

We evaluated open spectral crop/plant stress and disease datasets across all four target portals specified in the Day 1 plan:

| Source Portal | Candidate Evaluated | Licence | Format & Size | Labels & Temporal Structure | Assessment |
| --- | --- | --- | --- | --- | --- |
| **Zenodo** (Selected Primary) | *Plant Phenotyping and Environmental Stress Dataset* (DOI: `10.5281/zenodo.22755812`) | **CC-BY-4.0** (Permissive) | Tabular CSV (`Multispectral_Reflectance.csv` + `experimental_design.csv`, ~1.4 MB) | `Treatment` (Control vs. Drought levels), `Genotype`, repeated `date` scans per `Plant_ID` | **Selected (Fallback Rank 1 variant):** Ready-to-load CSV leaf/plant spectra with explicit plant & date keys. |
| **Zenodo** (Secondary Option) | *Multi-Temporal Field Spectroscopy of Apple Leaf Reflectance* (DOI: `10.5281/zenodo.22143346`) | **CC-BY-4.0** | Preprocessed `.txt` zip (13 MB), 350–2500 nm, 1,110 spectra across 37 days | Vitality time-series across 6 leaves, 5 positions/leaf (single cultivar) | Strong temporal resolution, but lacks multi-class stress/disease treatments. |
| **Kaggle** | *Hyperspectral Crop Disease / Indian Pines Benchmark Mirrors* | CC0 / Dataset-specific | `.mat` / `.npy` / `.csv` (requires Kaggle CLI auth) | Land-cover crop classes (Indian Pines) or image-only Leaf datasets | Land-cover cubes lack leaf-level temporal disease progression; auth adds Day 1 friction. |
| **Mendeley Data** | *Leaf Spectral Reflectance for Crop Stress / Nutrient Deficiency* | CC-BY-4.0 | `.xlsx` / `.csv` | Cultivar & nutrient/water treatment labels | Viable secondary backup if additional crop species are needed on Day 3. |
| **IEEE DataPort** | *Hyperspectral Plant Disease Benchmarks* | Subscription / Mixed | `.hdr` / `.raw` ENVI cubes (multi-GB) | Pixel-level disease annotations | Too heavy for Day 1 baseline; requires `spectral` ENVI parsing and high bandwidth. |

---

## 2. Selected Primary Dataset Card

- **Source:** Zenodo Record `22755812` — *Plant Phenotyping and Environmental Stress Dataset* (`data/raw/Multispectral_Reflectance.csv` & `data/raw/experimental_design.csv`)
- **Licence:** `CC-BY-4.0` (Attribution required; commercial and academic reuse permitted)
- **Fallback Tier & Limitation Statement:** Tier 1 leaf/plant-level CSV spectral dataset. **Explicit Limitation:** Labels represent controlled abiotic water/drought stress treatments rather than pathogen-specific fungal/bacterial disease inoculation. Downstream reports will state this clearly when interpreting stress signatures.
- **Shape & Wavelength Grid:**
  - `experimental_design.csv`: Plant-level metadata table (`Plant_ID`, `Pot_Number`, `GxT_Code`, `Genotype`, `Treatment`)
  - `Multispectral_Reflectance.csv`: Multi-temporal scan table with 10 nominal spectral mean bands (`Mean_365`, `Mean_460`, `Mean_525`, `Mean_570`, `Mean_645`, `Mean_670`, `Mean_700`, `Mean_780`, `Mean_890`, `Mean_970` nm), 5 UV/longpass band ratios, and per-band standard deviations (`StDev_*`).
- **Companion Synthetic Benchmark (Fallback Tier 3 — Clearly Labeled Synthetic):**
  - `data/raw/synthetic_leaf_disease_spectra_v1.csv` (120 samples × 61 hyperspectral bands from 400–1000 nm at 10 nm resolution, generated via `src/pipeline/generate_synthetic_spectra.py`).
  - Explicitly tagged `data_origin = SYNTHETIC_CONTROLLED_STRESS` with 4 progressive disease classes (`Healthy`, `Early_Chlorosis`, `Moderate_Blight`, `Severe_Necrosis`) for unit-testing hyperspectral red-edge baselines and multi-class disease pipelines.

---

## 3. Grouping Columns (Carry Forward to Day 2 & Day 5)

To guarantee **leak-free splits** on Day 5 (`GroupKFold`, `StratifiedGroupKFold`, and forward temporal holdouts), never split rows randomly. Always group or split along these identifiers:

| Column | Role | Leakage Risk if Ignored | Day 2 / Day 5 Action |
| --- | --- | --- | --- |
| `Plant_ID` (`plant_id`) | Biological plant unit | High — repeated scans of the same plant appear in both train and test folds | Primary `groups` key for `StratifiedGroupKFold` |
| `Pot_Number` (`plot_id` / `field_id`) | Spatial container / plot | Medium — micro-environment & genotype correlation | Secondary spatial group audit |
| `date` / `TimeStamp` (`acquisition_date`) | Temporal acquisition stamp | High — future scans leaking into past forecast models | Chronological cutoff for temporal forecasting |
| `Spectre_Number` / `Sample_ID` | Technical scan replicate | High — replicate shots from the same imaging session | Aggregate or keep grouped by `(Plant_ID, date)` |
