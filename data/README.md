# Data Directory (`data/`)

- `raw/Multispectral_Reflectance.csv` — 2,285 multi-temporal spectral reflectance observations (Zenodo DOI `10.5281/zenodo.22755812`, `CC-BY-4.0`).
- `raw/experimental_design.csv` — 79 plant metadata rows (`Plant_ID`, `Pot_Number`, `GxT_Code`, `Genotype`, `Treatment`: 41 Control / 38 Drought).
- `raw/synthetic_leaf_disease_spectra_v1.csv` — 120 synthetic leaf spectra (400–1000 nm, 61 bands) clearly labeled `SYNTHETIC_CONTROLLED_STRESS` for Fallback Tier 3 smoke testing.
- `processed/` — Reserved for Day 2+ cleaned tables, feature matrices, and leak-free `StratifiedGroupKFold` split indices.
