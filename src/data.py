"""Day 2 Block 1: Unified Spectral Dataset Loader (`src/data.py`).

Returns spectra, labels, wavelengths, and group IDs for downstream sanity checks,
EDA, preprocessing, and leak-free cross-validation splits.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"

PRIMARY_BAND_COLS = [
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

PRIMARY_STDEV_COLS = [
    "StDev_365",
    "StDev_460",
    "StDev_525",
    "StDev_570",
    "StDev_645",
    "StDev_670",
    "StDev_700",
    "StDev_780",
    "StDev_890",
    "StDev_970",
]

DatasetSource = Literal["primary", "synthetic"]


@dataclass
class SpectralDataset:
    source: DatasetSource
    spectra: np.ndarray
    labels: np.ndarray
    wavelengths: np.ndarray
    group_ids: pd.DataFrame
    band_names: list[str]
    band_stdevs: np.ndarray | None
    raw_df: pd.DataFrame
    unmatched_count: int


def load_dataset(
    source: DatasetSource = "primary",
    drop_unlabeled: bool = True,
) -> SpectralDataset:
    """Load spectral matrix, labels, wavelengths, and grouping identifiers."""
    if source == "primary":
        design_path = RAW_DIR / "experimental_design.csv"
        spectra_path = RAW_DIR / "Multispectral_Reflectance.csv"
        if not design_path.exists() or not spectra_path.exists():
            raise FileNotFoundError("Primary Zenodo CSV files missing from data/raw/")

        design_df = pd.read_csv(design_path)
        spectra_df = pd.read_csv(spectra_path)
        merged = spectra_df.merge(design_df, on="Plant_ID", how="left")

        unmatched_mask = merged["Treatment"].isna()
        unmatched_count = int(unmatched_mask.sum())

        df = merged.loc[~unmatched_mask].copy() if drop_unlabeled else merged.copy()
        if not drop_unlabeled:
            df["Treatment"] = df["Treatment"].fillna("Unmatched_Metadata")

        wavelengths = np.array([int(col.split("_")[1]) for col in PRIMARY_BAND_COLS], dtype=float)
        spectra = df[PRIMARY_BAND_COLS].to_numpy(dtype=float)
        band_stdevs = df[PRIMARY_STDEV_COLS].to_numpy(dtype=float)
        labels = df["Treatment"].astype(str).to_numpy()

        group_ids = pd.DataFrame(
            {
                "sample_id": df["Sample_ID"].astype(str),
                "plant_id": df["Plant_ID"].astype(str),
                "plot_id": df["Pot_Number"].fillna(-1).astype(str),
                "field_id": df["Genotype"].fillna("Unknown").astype(str),
                "date": df["date"].astype(str),
                "timestamp": df["TimeStamp"].astype(str),
            },
            index=df.index,
        )

        return SpectralDataset(
            source="primary",
            spectra=spectra,
            labels=labels,
            wavelengths=wavelengths,
            group_ids=group_ids,
            band_names=list(PRIMARY_BAND_COLS),
            band_stdevs=band_stdevs,
            raw_df=merged,
            unmatched_count=unmatched_count,
        )

    if source == "synthetic":
        synth_path = RAW_DIR / "synthetic_leaf_disease_spectra_v1.csv"
        if not synth_path.exists():
            raise FileNotFoundError("Synthetic dataset CSV missing from data/raw/")

        df = pd.read_csv(synth_path)
        band_cols = [c for c in df.columns if c.startswith("band_") and c.endswith("nm")]
        wavelengths = np.array(
            [int(c.replace("band_", "").replace("nm", "")) for c in band_cols],
            dtype=float,
        )
        # Convert fractional reflectance [0..1] to percent [0..100] for consistent scale
        spectra = df[band_cols].to_numpy(dtype=float) * 100.0
        labels = df["disease_label"].astype(str).to_numpy()
        group_ids = pd.DataFrame(
            {
                "sample_id": df["sample_id"].astype(str),
                "plant_id": df["plant_id"].astype(str),
                "plot_id": df["plot_id"].astype(str),
                "field_id": df["field_id"].astype(str),
                "date": df["acquisition_date"].astype(str),
                "timestamp": df["acquisition_date"].astype(str),
            },
            index=df.index,
        )

        return SpectralDataset(
            source="synthetic",
            spectra=spectra,
            labels=labels,
            wavelengths=wavelengths,
            group_ids=group_ids,
            band_names=band_cols,
            band_stdevs=None,
            raw_df=df,
            unmatched_count=0,
        )

    raise ValueError(f"Unsupported dataset source: {source}")


def load_spectra(
    source: DatasetSource = "primary",
    drop_unlabeled: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    """Convenience tuple loader returning (spectra, labels, wavelengths, group_ids)."""
    ds = load_dataset(source=source, drop_unlabeled=drop_unlabeled)
    return ds.spectra, ds.labels, ds.wavelengths, ds.group_ids


if __name__ == "__main__":
    spectra, labels, wavelengths, group_ids = load_spectra("primary")
    print(f"Primary spectra shape: {spectra.shape}")
    print(f"Wavelengths (nm): {wavelengths.tolist()}")
    print(f"Unique labels: {np.unique(labels, return_counts=True)}")
    print(f"Group columns: {list(group_ids.columns)} | Unique plants: {group_ids['plant_id'].nunique()}")
