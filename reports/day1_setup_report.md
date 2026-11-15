# Day 1 Setup & Verification Report

**Date:** Monday, 16 November  
**Goal:** Remove every blocker for the rest of the week (agreed scope, working repo, verified Python stack, licensed dataset decision).

## 1. Python Environment Verification (`src/pipeline/verify_env.py`)

- **Runtime:** Python 3.10.12 (`/usr/bin/python3`)
- **Verified Imports:**
  - `numpy`: `2.2.6`
  - `pandas`: `2.3.3`
  - `scikit-learn`: `1.7.2`
  - `xgboost`: `3.2.0`
  - `matplotlib`: `3.10.9`
  - `spectral`: `0.26`

## 2. Dataset Selection Verification (`src/pipeline/dataset_loader.py`)

- **Primary Dataset:** Zenodo Record `22755812` (`CC-BY-4.0`)
  - `data/raw/Multispectral_Reflectance.csv`: `2,285` rows × `37` columns
  - `data/raw/experimental_design.csv`: `79` plants × `5` columns (`41` Control `40% Water`, `38` Drought `10% Water`; `5` rows in reflectance table lack matching design metadata and are flagged for Day 2 cleaning)
  - Acquisition Dates: `31` distinct dates (`07-08-21` to `08-12-21`)
- **Companion Synthetic Benchmark:** `data/raw/synthetic_leaf_disease_spectra_v1.csv` (`120` rows × `69` columns, `400–1000 nm`, `SYNTHETIC_CONTROLLED_STRESS`)
- **Carry-Forward Grouping Keys:** `Plant_ID`, `Pot_Number`, `date`, `TimeStamp`
