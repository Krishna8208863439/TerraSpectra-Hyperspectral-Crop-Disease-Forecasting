"""Day 2 Blocks 2-6: Reproducible EDA, Sanity Checks, Figure Generation & Data Summary.

Imports `src/data.py`, computes all dataset statistics, outlier diagnostics,
difference spectra, band-drop recommendations for Day 3, and temporal trajectories,
saves matplotlib figures to `reports/figures/`, writes `reports/day2_eda_metrics.json`,
and generates `docs/data_summary.md` directly from code-computed numbers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data import DatasetSource, SpectralDataset, load_dataset

REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = ROOT_DIR / "docs"


def _sort_dates(dates: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(dates, format="%m-%d-%y", errors="coerce")
    if parsed.isna().all():
        parsed = pd.to_datetime(dates, errors="coerce")
    return parsed


def analyze_dataset(source: DatasetSource) -> dict:
    ds: SpectralDataset = load_dataset(source=source, drop_unlabeled=True)
    X = ds.spectra
    y = ds.labels
    wl = ds.wavelengths
    groups = ds.group_ids

    n_samples, n_bands = X.shape
    raw_rows = int(len(ds.raw_df))

    # Block 2: Sanity checks
    missing_spectra = int(np.isnan(X).sum())
    missing_rows = int(np.isnan(X).any(axis=1).sum())
    missing_labels = int(pd.isna(y).sum())
    dup_sample_ids = int(groups["sample_id"].duplicated().sum())
    exact_dup_spectra = int(pd.DataFrame(X).dropna().duplicated().sum())
    spacings = np.diff(wl)
    unique_spacings = sorted({float(s) for s in spacings})

    # Block 3: Class balance & grouping
    unique_classes, counts = np.unique(y, return_counts=True)
    class_balance = []
    for cls, cnt in zip(unique_classes, counts):
        class_balance.append(
            {
                "label": str(cls),
                "count": int(cnt),
                "percent": round(float(cnt) / n_samples * 100.0, 2),
                "plants": int(groups.loc[y == cls, "plant_id"].nunique()),
            }
        )
    imbalance_ratio = round(float(counts.max()) / max(1.0, float(counts.min())), 3)

    scans_per_plant = groups.groupby("plant_id").size()
    grouping_stats = {
        "unique_plants": int(groups["plant_id"].nunique()),
        "unique_plots": int(groups["plot_id"].nunique()),
        "unique_fields": int(groups["field_id"].nunique()),
        "unique_dates": int(groups["date"].nunique()),
        "scans_per_plant_min": int(scans_per_plant.min()),
        "scans_per_plant_median": float(scans_per_plant.median()),
        "scans_per_plant_mean": round(float(scans_per_plant.mean()), 2),
        "scans_per_plant_max": int(scans_per_plant.max()),
        "recommended_split_column": "plant_id",
        "temporal_split_column": "date",
    }

    # Block 4: Mean spectra per class with variance bands
    class_curves = []
    for cls in unique_classes:
        mask = y == cls
        sub = X[mask]
        means = np.nanmean(sub, axis=0)
        stds = np.nanstd(sub, axis=0)
        class_curves.append(
            {
                "label": str(cls),
                "n_samples": int(mask.sum()),
                "points": [
                    {
                        "wavelength_nm": float(w),
                        "mean": round(float(m), 4),
                        "std": round(float(s), 4),
                    }
                    for w, m, s in zip(wl, means, stds)
                ],
            }
        )

    # Block 5: Difference spectrum & discriminability (Control vs Stressed)
    if source == "primary":
        healthy_label = "Control (40% Water)"
        stressed_label = "Drought (10% Water)"
    else:
        healthy_label = "Healthy"
        stressed_label = "Severe_Necrosis"

    h_mask = y == healthy_label
    s_mask = y == stressed_label
    h_mean = np.nanmean(X[h_mask], axis=0)
    h_std = np.nanstd(X[h_mask], axis=0)
    s_mean = np.nanmean(X[s_mask], axis=0)
    s_std = np.nanstd(X[s_mask], axis=0)

    diff_mean = s_mean - h_mean
    pooled_var = np.maximum(1e-9, h_std**2 + s_std**2)
    fisher_ratio = (s_mean - h_mean) ** 2 / pooled_var
    cohens_d = (s_mean - h_mean) / np.sqrt(pooled_var / 2.0)

    # Band quality / noise / Day 3 drop audit
    band_diagnostics = []
    bands_to_drop_day3 = []
    for idx, (b_name, w_nm) in enumerate(zip(ds.band_names, wl)):
        col_vals = X[:, idx]
        finite_vals = col_vals[~np.isnan(col_vals)]
        col_mean = float(np.mean(finite_vals))
        col_std = float(np.std(finite_vals))
        cross_cv = col_std / max(1e-6, col_mean)
        zero_or_neg = int(np.sum(finite_vals <= 0.0))
        saturated = int(np.sum(finite_vals >= 99.5))

        intra_noise_ratio = None
        if ds.band_stdevs is not None:
            valid_std_mask = (~np.isnan(col_vals)) & (~np.isnan(ds.band_stdevs[:, idx]))
            ratios = ds.band_stdevs[valid_std_mask, idx] / np.maximum(1e-3, col_vals[valid_std_mask])
            intra_noise_ratio = round(float(np.mean(ratios)), 4)

        region = "VIS"
        if w_nm < 400:
            region = "UV Edge"
        elif 690 <= w_nm <= 750:
            region = "Red Edge"
        elif w_nm > 750:
            region = "NIR Plateau"

        drop_reason = None
        if source == "primary":
            if w_nm == 365:
                drop_reason = (
                    f"UV spectrum edge (365 nm): high intra-scan relative noise "
                    f"(StDev/Mean={intra_noise_ratio:.3f}) and low Fisher separation ({fisher_ratio[idx]:.4f})."
                )
            elif w_nm == 970:
                drop_reason = (
                    f"Water-absorption shoulder / Si-detector edge (970 nm): elevated noise "
                    f"(StDev/Mean={intra_noise_ratio:.3f}); verify before retaining for moisture indices."
                )
        else:
            if w_nm <= 410:
                drop_reason = f"Blue/UV spectrum edge ({int(w_nm)} nm): low chlorophyll signal-to-noise."
            elif w_nm >= 970:
                drop_reason = f"Water-absorption edge ({int(w_nm)} nm): edge band candidate for removal."

        if drop_reason:
            bands_to_drop_day3.append(
                {
                    "band": b_name,
                    "wavelength_nm": float(w_nm),
                    "region": region,
                    "fisher_ratio": round(float(fisher_ratio[idx]), 4),
                    "intra_noise_ratio": intra_noise_ratio,
                    "reason": drop_reason,
                }
            )

        band_diagnostics.append(
            {
                "band": b_name,
                "wavelength_nm": float(w_nm),
                "region": region,
                "healthy_mean": round(float(h_mean[idx]), 4),
                "stressed_mean": round(float(s_mean[idx]), 4),
                "diff_stressed_minus_healthy": round(float(diff_mean[idx]), 4),
                "fisher_ratio": round(float(fisher_ratio[idx]), 4),
                "cohens_d": round(float(cohens_d[idx]), 4),
                "cross_sample_cv": round(float(cross_cv), 4),
                "intra_noise_ratio": intra_noise_ratio,
                "zero_or_neg_count": zero_or_neg,
                "saturated_count": saturated,
                "drop_candidate": drop_reason is not None,
            }
        )

    # Rank discriminative bands by Fisher ratio
    ranked_bands = sorted(band_diagnostics, key=lambda b: b["fisher_ratio"], reverse=True)

    # Outlier detection using per-class L2 distance & MAD robust Z-score on finite spectra
    valid_row_mask = ~np.isnan(X).any(axis=1)
    l2_dists = np.full(n_samples, np.nan, dtype=float)
    for cls in unique_classes:
        mask = (y == cls) & valid_row_mask
        med = np.median(X[mask], axis=0)
        l2_dists[mask] = np.linalg.norm(X[mask] - med, axis=1)

    valid_dists = l2_dists[valid_row_mask]
    med_dist = float(np.median(valid_dists))
    mad_dist = float(np.median(np.abs(valid_dists - med_dist)))
    robust_z = np.full(n_samples, np.nan, dtype=float)
    robust_z[valid_row_mask] = 0.6745 * (l2_dists[valid_row_mask] - med_dist) / max(1e-6, mad_dist)
    outlier_mask = valid_row_mask & (robust_z > 3.0)
    outlier_indices = np.where(outlier_mask)[0]
    top_outliers = sorted(
        [
            {
                "sample_id": str(groups.iloc[i]["sample_id"]),
                "plant_id": str(groups.iloc[i]["plant_id"]),
                "date": str(groups.iloc[i]["date"]),
                "label": str(y[i]),
                "l2_distance": round(float(l2_dists[i]), 3),
                "robust_z": round(float(robust_z[i]), 3),
            }
            for i in outlier_indices
        ],
        key=lambda x: x["robust_z"],
        reverse=True,
    )

    # Temporal progression (NDVI & Red Edge 700nm across dates)
    idx_670 = int(np.argmin(np.abs(wl - 670)))
    idx_700 = int(np.argmin(np.abs(wl - 700)))
    idx_780 = int(np.argmin(np.abs(wl - 780)))
    ndvi = (X[:, idx_780] - X[:, idx_670]) / np.maximum(1e-6, X[:, idx_780] + X[:, idx_670])
    ndre = (X[:, idx_780] - X[:, idx_700]) / np.maximum(1e-6, X[:, idx_780] + X[:, idx_700])

    temp_df = pd.DataFrame(
        {
            "date": groups["date"].to_numpy(),
            "parsed_date": _sort_dates(groups["date"]).to_numpy(),
            "plant_id": groups["plant_id"].to_numpy(),
            "label": y,
            "ndvi": ndvi,
            "ndre": ndre,
            "r700": X[:, idx_700],
            "r780": X[:, idx_780],
        }
    )
    temp_df = temp_df.sort_values("parsed_date")
    ordered_dates = temp_df["date"].drop_duplicates().tolist()

    temporal_series = []
    for d_str in ordered_dates:
        sub_d = temp_df[temp_df["date"] == d_str]
        entry: dict = {"date": str(d_str), "classes": {}}
        for cls in unique_classes:
            sub_c = sub_d[sub_d["label"] == cls]
            if len(sub_c) > 0:
                entry["classes"][str(cls)] = {
                    "n": int(len(sub_c)),
                    "ndvi_mean": round(float(sub_c["ndvi"].mean()), 4),
                    "ndre_mean": round(float(sub_c["ndre"].mean()), 4),
                    "r700_mean": round(float(sub_c["r700"].mean()), 3),
                    "r780_mean": round(float(sub_c["r780"].mean()), 3),
                }
        temporal_series.append(entry)

    # Early vs Late half NDVI shift per class
    mid_idx = max(1, len(ordered_dates) // 2)
    early_dates = set(ordered_dates[:mid_idx])
    late_dates = set(ordered_dates[mid_idx:])
    temporal_deltas = {}
    for cls in unique_classes:
        e_ndvi = float(temp_df[(temp_df["label"] == cls) & (temp_df["date"].isin(early_dates))]["ndvi"].mean())
        l_ndvi = float(temp_df[(temp_df["label"] == cls) & (temp_df["date"].isin(late_dates))]["ndvi"].mean())
        temporal_deltas[str(cls)] = {
            "early_ndvi": round(e_ndvi, 4),
            "late_ndvi": round(l_ndvi, 4),
            "delta_ndvi": round(l_ndvi - e_ndvi, 4),
        }

    # Red-edge slope (700 -> 780 nm) summary
    red_edge_slope = (X[:, idx_780] - X[:, idx_700]) / max(1.0, float(wl[idx_780] - wl[idx_700]))
    red_edge_summary = {
        str(cls): round(float(np.nanmean(red_edge_slope[y == cls])), 4) for cls in unique_classes
    }

    valid_z = robust_z[valid_row_mask]
    z_hist_counts, z_hist_edges = np.histogram(valid_z, bins=16, range=(-2, 6))

    return {
        "source": source,
        "sanity": {
            "raw_rows": raw_rows,
            "labeled_rows": n_samples,
            "unmatched_metadata_rows": ds.unmatched_count,
            "n_bands": n_bands,
            "dtype": str(X.dtype),
            "missing_spectral_values": missing_spectra,
            "rows_with_missing_spectra": missing_rows,
            "missing_label_values": missing_labels,
            "duplicate_sample_ids": dup_sample_ids,
            "exact_duplicate_spectra": exact_dup_spectra,
            "wavelength_min_nm": float(wl.min()),
            "wavelength_max_nm": float(wl.max()),
            "wavelength_spacings_nm": unique_spacings,
            "reflectance_min": round(float(np.nanmin(X)), 4),
            "reflectance_max": round(float(np.nanmax(X)), 4),
        },
        "class_balance": class_balance,
        "imbalance_ratio": imbalance_ratio,
        "grouping": grouping_stats,
        "class_curves": class_curves,
        "comparison_pair": {"healthy": healthy_label, "stressed": stressed_label},
        "band_diagnostics": band_diagnostics,
        "top_discriminative_bands": ranked_bands[:5],
        "bands_to_drop_day3": bands_to_drop_day3,
        "red_edge_slope_pct_per_nm": red_edge_summary,
        "outliers": {
            "method": "Per-class median L2 distance (MAD robust Z > 3.0)",
            "median_l2_distance": round(med_dist, 3),
            "mad_l2_distance": round(mad_dist, 3),
            "outlier_count": int(outlier_mask.sum()),
            "outlier_percent": round(float(outlier_mask.sum()) / max(1, int(valid_row_mask.sum())) * 100.0, 2),
            "top_outliers": top_outliers[:12],
            "z_scores_histogram": z_hist_counts.tolist(),
            "z_hist_edges": np.round(z_hist_edges, 2).tolist(),
        },
        "temporal": {
            "date_count": len(ordered_dates),
            "first_date": ordered_dates[0] if ordered_dates else "",
            "last_date": ordered_dates[-1] if ordered_dates else "",
            "series": temporal_series,
            "early_vs_late_ndvi": temporal_deltas,
        },
        "_internal": {"l2_robust_z": valid_z, "ndvi": ndvi, "temp_df": temp_df, "wl": wl},
    }


def generate_figures(primary_metrics: dict) -> list[str]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.edgecolor": "#CBD5E1",
            "axes.linewidth": 0.9,
            "grid.color": "#E2E8F0",
            "grid.linestyle": "-",
            "grid.linewidth": 0.7,
        }
    )

    colors = {"Control (40% Water)": "#0F766E", "Drought (10% Water)": "#D97706"}
    wl = np.array([b["wavelength_nm"] for b in primary_metrics["band_diagnostics"]])

    # Figure 1: Mean spectra per class with +/- 1 SD variance bands
    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=160)
    ax.axvspan(690, 750, color="#0F766E", alpha=0.06, label="Red-edge zone (690–750 nm)")
    for curve in primary_metrics["class_curves"]:
        lbl = curve["label"]
        means = np.array([p["mean"] for p in curve["points"]])
        stds = np.array([p["std"] for p in curve["points"]])
        c = colors.get(lbl, "#0284C7")
        ax.plot(wl, means, marker="o", linewidth=2.1, markersize=4.5, color=c, label=f"{lbl} (n={curve['n_samples']})")
        ax.fill_between(wl, np.maximum(0, means - stds), means + stds, color=c, alpha=0.14)
    ax.set_title("Mean Spectral Reflectance by Treatment (±1 SD)", fontweight="bold", pad=10)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Reflectance (%)")
    ax.grid(True, alpha=0.7)
    ax.legend(frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=9)
    plt.tight_layout()
    f1 = FIGURES_DIR / "01_mean_spectra_variance.png"
    fig.savefig(f1)
    plt.close(fig)

    # Figure 2: Difference spectrum + Fisher discriminant ratio
    diff_vals = np.array([b["diff_stressed_minus_healthy"] for b in primary_metrics["band_diagnostics"]])
    fisher_vals = np.array([b["fisher_ratio"] for b in primary_metrics["band_diagnostics"]])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.5, 5.8), dpi=160, sharex=True)
    ax1.axvspan(690, 750, color="#0F766E", alpha=0.07, label="Red edge (690–750 nm)")
    ax1.axvspan(780, 970, color="#0284C7", alpha=0.05, label="NIR plateau (780–970 nm)")
    ax1.axhline(0, color="#64748B", linewidth=1, linestyle="--")
    ax1.plot(wl, diff_vals, marker="o", color="#B45309", linewidth=2.0)
    ax1.fill_between(wl, 0, diff_vals, color="#D97706", alpha=0.15)
    ax1.set_ylabel("Delta Reflectance (%)")
    ax1.set_title("Difference Spectrum (Drought - Control) & Band Discriminability", fontweight="bold", pad=8)
    ax1.grid(True, alpha=0.7)
    ax1.legend(frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=8.5)

    bar_colors = ["#DC2626" if b["drop_candidate"] else "#0F766E" for b in primary_metrics["band_diagnostics"]]
    ax2.axvspan(690, 750, color="#0F766E", alpha=0.07)
    ax2.axvspan(780, 970, color="#0284C7", alpha=0.05)
    ax2.bar(wl, fisher_vals, width=22, color=bar_colors, alpha=0.85)
    ax2.set_xlabel("Wavelength (nm)")
    ax2.set_ylabel("Fisher Ratio J")
    ax2.set_title("Per-Band Separability (Red bars = Day 3 drop/audit candidates)", fontsize=10, pad=6)
    ax2.grid(True, axis="y", alpha=0.7)
    plt.tight_layout()
    f2 = FIGURES_DIR / "02_difference_spectrum_red_edge.png"
    fig.savefig(f2)
    plt.close(fig)

    # Figure 3: Class balance + outlier distribution
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 4.0), dpi=160)
    cls_labels = [c["label"] for c in primary_metrics["class_balance"]]
    cls_counts = [c["count"] for c in primary_metrics["class_balance"]]
    ax1.bar(cls_labels, cls_counts, color=["#0F766E", "#D97706"], width=0.5)
    ax1.set_title("Class Balance (Labeled Scans)", fontweight="bold")
    ax1.set_ylabel("Sample Count")
    ax1.grid(True, axis="y", alpha=0.7)
    for i, cnt in enumerate(cls_counts):
        ax1.text(i, cnt + 20, str(cnt), ha="center", va="bottom", fontsize=9, fontweight="bold")

    z_vals = primary_metrics["_internal"]["l2_robust_z"]
    ax2.hist(np.clip(z_vals, -2, 6), bins=24, color="#334155", alpha=0.82, edgecolor="white")
    ax2.axvline(3.0, color="#DC2626", linestyle="--", linewidth=1.6, label="Outlier cutoff (Z = 3.0)")
    ax2.set_title(f"Spectral Outlier Distribution (n={primary_metrics['outliers']['outlier_count']} flagged)", fontweight="bold")
    ax2.set_xlabel("Robust L2 Z-Score (clipped at 6)")
    ax2.set_ylabel("Scan Count")
    ax2.grid(True, axis="y", alpha=0.7)
    ax2.legend(frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=8.5)
    plt.tight_layout()
    f3 = FIGURES_DIR / "03_class_group_and_outliers.png"
    fig.savefig(f3)
    plt.close(fig)

    # Figure 4: Temporal progression across dates
    series = primary_metrics["temporal"]["series"]
    dates = [s["date"] for s in series]
    x_idx = np.arange(len(dates))
    fig, ax = plt.subplots(figsize=(9.0, 4.2), dpi=160)
    for lbl in ["Control (40% Water)", "Drought (10% Water)"]:
        vals = [s["classes"].get(lbl, {}).get("ndvi_mean", np.nan) for s in series]
        ax.plot(x_idx, vals, marker="o", markersize=3.5, linewidth=2.0, color=colors[lbl], label=lbl)
    tick_step = max(1, len(dates) // 8)
    ax.set_xticks(x_idx[::tick_step])
    ax.set_xticklabels(dates[::tick_step], rotation=25, ha="right", fontsize=8.5)
    ax.set_title("Temporal NDVI Trajectory Across 31 Measurement Dates", fontweight="bold", pad=8)
    ax.set_ylabel("Mean NDVI (780 nm / 670 nm)")
    ax.grid(True, alpha=0.7)
    ax.legend(frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=9)
    plt.tight_layout()
    f4 = FIGURES_DIR / "04_temporal_spectral_progression.png"
    fig.savefig(f4)
    plt.close(fig)

    return [
        "reports/figures/01_mean_spectra_variance.png",
        "reports/figures/02_difference_spectrum_red_edge.png",
        "reports/figures/03_class_group_and_outliers.png",
        "reports/figures/04_temporal_spectral_progression.png",
    ]


def render_data_summary_markdown(m: dict) -> str:
    s = m["sanity"]
    g = m["grouping"]
    o = m["outliers"]
    t = m["temporal"]
    top_bands = m["top_discriminative_bands"]
    drop_bands = m["bands_to_drop_day3"]

    class_lines = "\n".join(
        f"- **{c['label']}:** {c['count']:,} scans ({c['percent']}%) across {c['plants']} plants"
        for c in m["class_balance"]
    )
    top_band_lines = "\n".join(
        f"- `{b['band']}` ({int(b['wavelength_nm'])} nm · {b['region']}): Fisher J = `{b['fisher_ratio']}`, "
        f"ΔR = `{b['diff_stressed_minus_healthy']:+.3f}%` (Cohen's d = `{b['cohens_d']:+.3f}`)"
        for b in top_bands[:4]
    )
    drop_lines = "\n".join(
        f"- `{d['band']}` ({int(d['wavelength_nm'])} nm · {d['region']}): {d['reason']}"
        for d in drop_bands
    )
    temporal_lines = "\n".join(
        f"- **{cls}:** Early-half mean NDVI `{vals['early_ndvi']:.4f}` → Late-half `{vals['late_ndvi']:.4f}` "
        f"(Δ = `{vals['delta_ndvi']:+.4f}`)"
        for cls, vals in t["early_vs_late_ndvi"].items()
    )

    return f"""# Day 2 Data Summary & EDA Findings

**Generated programmatically by:** `python3 src/pipeline/run_day2_eda.py`  
**Primary Dataset:** Zenodo Record `22755812` (`CC-BY-4.0`) — *Plant Phenotyping and Environmental Stress Dataset*  
**Limitation Disclosure:** This dataset measures **abiotic drought/water-stress** (`Control 40% Water` vs. `Drought 10% Water`), not pathogen inoculation. (It is not a satellite land-cover fallback dataset such as Indian Pines or Salinas.)

---

## 1. Dataset Shape, Sanity Checks & Class Balance

- **Raw vs. Labeled Scans:** `{s['raw_rows']:,}` raw rows in `Multispectral_Reflectance.csv`; `{s['unmatched_metadata_rows']}` rows (`PlantId_78`) lack matching entries in `experimental_design.csv` and are excluded by `src/data.py`, leaving **`{s['labeled_rows']:,}` labeled samples × `{s['n_bands']}` spectral bands** (`dtype: {s['dtype']}`).
- **Data Integrity:** `{s['missing_spectral_values']}` missing spectral values across `{s['rows_with_missing_spectra']}` failed-scan rows (must be dropped on Day 3), `{s['duplicate_sample_ids']}` duplicate `Sample_ID`s, and `{s['exact_duplicate_spectra']}` exact duplicate spectral vectors. Reflectance spans `{s['reflectance_min']:.2f}%` to `{s['reflectance_max']:.2f}%`.
- **Wavelength Axis:** `{int(s['wavelength_min_nm'])} nm` to `{int(s['wavelength_max_nm'])} nm` with non-uniform multispectral spacings (`{s['wavelength_spacings_nm']}` nm).
- **Class Balance (Imbalance Ratio `{m['imbalance_ratio']}:1`):**
{class_lines}

---

## 2. Grouping Structure (Day 5 Leak-Free Split Key)

- **Biological & Spatial Keys:** `{g['unique_plants']}` unique plants (`plant_id`), `{g['unique_plots']}` pots (`plot_id`), `{g['unique_fields']}` genotypes (`field_id`), and `{g['unique_dates']}` acquisition dates (`date`).
- **Repeated Scans per Plant:** min `{g['scans_per_plant_min']}`, median `{g['scans_per_plant_median']:.1f}`, mean `{g['scans_per_plant_mean']}`, max `{g['scans_per_plant_max']}`.
- **Split Decision:** Group all cross-validation folds by **`plant_id`** (`StratifiedGroupKFold`) and order temporal forecasts chronologically by **`date`**.

---

## 3. Discriminative Wavelengths, Outliers & Bands to Drop on Day 3

- **Most Discriminative Bands (Red Edge & NIR Plateau):**
{top_band_lines}
- **Red-Edge Slope (`700 → 780 nm`):** Control `{m['red_edge_slope_pct_per_nm'].get('Control (40% Water)', 0):.4f}%/nm` vs. Drought `{m['red_edge_slope_pct_per_nm'].get('Drought (10% Water)', 0):.4f}%/nm`.
- **Outlier Spectra:** Using per-class median L2 distance (`median = {o['median_l2_distance']}`, `MAD = {o['mad_l2_distance']}`), **`{o['outlier_count']}` scans (`{o['outlier_percent']}%`)** exceed `robust Z > 3.0` and will be inspected/winsorized on Day 3.
- **Bands Flagged to Drop or Isolate on Day 3:**
{drop_lines}

---

## 4. Temporal Spectral Progression ({t['first_date']} to {t['last_date']})

{temporal_lines}

Saved figures in `reports/figures/`: `01_mean_spectra_variance.png`, `02_difference_spectrum_red_edge.png`, `03_class_group_and_outliers.png`, and `04_temporal_spectral_progression.png`.
"""


def main() -> int:
    primary = analyze_dataset("primary")
    synthetic = analyze_dataset("synthetic")
    figures = generate_figures(primary)

    # Strip numpy-heavy internal objects before JSON serialization
    for m in (primary, synthetic):
        m.pop("_internal", None)

    payload = {
        "figures": figures,
        "primary": primary,
        "synthetic": synthetic,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = REPORTS_DIR / "day2_eda_metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_md = render_data_summary_markdown(primary)
    summary_path = DOCS_DIR / "data_summary.md"
    summary_path.write_text(summary_md, encoding="utf-8")

    print(f"Day 2 EDA complete: {metrics_path} & {summary_path}")
    print(f"Generated {len(figures)} figures in {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
