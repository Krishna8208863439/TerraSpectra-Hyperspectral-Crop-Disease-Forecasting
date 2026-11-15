"""Day 1 Dataset Loader & Metadata Summary Utility.

Supports loading the primary Zenodo multi-temporal plant spectral dataset
(data/raw/Multispectral_Reflectance.csv + data/raw/experimental_design.csv)
and inspecting shape, label distribution, and leak-free grouping columns.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"

SPECTRAL_BAND_COLS = [
    "Mean_365",
    "Mean_460",
    "Mean_525",
    "Mean_570",
    "Mean_645",
    "Mean_670",
    "Mean_700",
    "Mean_780",
    "Mean_890",
    "Mean_970",
]


def load_primary_dataset() -> pd.DataFrame:
    design_path = RAW_DIR / "experimental_design.csv"
    spectra_path = RAW_DIR / "Multispectral_Reflectance.csv"
    if not design_path.exists() or not spectra_path.exists():
        raise FileNotFoundError("Primary Zenodo CSV files not found in data/raw/")

    design = pd.read_csv(design_path)
    spectra = pd.read_csv(spectra_path)
    df = spectra.merge(design, on="Plant_ID", how="left")
    return df


def summarize_dataset() -> dict:
    df = load_primary_dataset()
    wavelengths = [int(c.split("_")[1]) for c in SPECTRAL_BAND_COLS]
    label_counts = df["Treatment"].fillna("Unknown").value_counts().to_dict()
    genotype_counts = df["Genotype"].fillna("Unknown").value_counts().to_dict()

    curves = {}
    for treatment, grp in df.groupby("Treatment"):
        means = grp[SPECTRAL_BAND_COLS].mean().round(4).to_dict()
        stds = grp[SPECTRAL_BAND_COLS].std().round(4).to_dict()
        curves[str(treatment)] = {
            "n_samples": int(len(grp)),
            "n_plants": int(grp["Plant_ID"].nunique()),
            "points": [
                {
                    "wavelength_nm": int(col.split("_")[1]),
                    "band": col,
                    "mean": float(means[col]),
                    "std": float(stds[col]),
                }
                for col in SPECTRAL_BAND_COLS
            ],
        }

    return {
        "source": "Zenodo Record 22755812 (CC-BY-4.0)",
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "wavelengths_nm": wavelengths,
        "unique_plants": int(df["Plant_ID"].nunique()),
        "unique_pots": int(df["Pot_Number"].nunique()) if "Pot_Number" in df.columns else 0,
        "unique_dates": sorted([str(d) for d in df["date"].dropna().unique()]),
        "grouping_columns": ["Plant_ID", "Pot_Number", "date", "TimeStamp"],
        "label_counts": {str(k): int(v) for k, v in label_counts.items()},
        "genotype_counts": {str(k): int(v) for k, v in genotype_counts.items()},
        "curves": curves,
    }


if __name__ == "__main__":
    summary = summarize_dataset()
    if "--json" in sys.argv:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Dataset shape: ({summary['rows']}, {summary['columns']})")
        print(f"Unique plants: {summary['unique_plants']} | Dates: {len(summary['unique_dates'])}")
        print("Labels:", summary["label_counts"])
        print("Grouping columns:", summary["grouping_columns"])
