"""Day 4 Runner: Leak-Free Feature Engineering, Index Lookup, PCA, RF+MI Selection & Sets A–E.

Generates:
  - data/processed/{source}_feature_set_Set_A.npz ... Set_E.npz
  - reports/day4_features_metrics.json
  - reports/figures/07_pca_variance_and_band_importance.png
  - reports/figures/08_feature_sets_and_indices.png
  - docs/feature_engineering_note.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features import (
    FEATURE_SET_LABELS,
    build_and_save_feature_sets,
)
from src.preprocessing import PreprocessingConfig

REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = ROOT_DIR / "docs"

PALETTE = ["#0F766E", "#D97706", "#DC2626", "#2563EB"]


def _analyze_source(source: str, top_k_bands: int, normalization: str) -> dict:
    drop_wl = (365.0,) if source == "primary" else ()
    cfg = PreprocessingConfig(
        drop_bad_bands=True,
        drop_wavelengths=drop_wl,
        use_savgol=True,
        savgol_window=3 if source == "primary" else 5,
        savgol_polyorder=1 if source == "primary" else 2,
        normalization=normalization,  # type: ignore[arg-type]
        use_first_derivative=False,
    )
    res = build_and_save_feature_sets(
        source=source,  # type: ignore[arg-type]
        prep_config=cfg,
        top_k_bands=top_k_bands,
        pca_variance=0.99,
    )
    pipe = res["reference_pipe"]
    train_idx = res["train_idx"]
    X_train_raw = res["X_clean"][train_idx]
    y_train = res["y_clean"][train_idx]

    # 1. Index class distributions (training set sanity summary + sampled scatter stats)
    X_train_refl = pipe.preprocessor_.transform_reflectance_only(X_train_raw)
    X_idx = pipe.index_extractor_.transform(X_train_refl)
    idx_names = pipe.index_extractor_.get_feature_names_out()

    index_stats_by_class: list[dict] = []
    classes = list(np.unique(y_train))
    for col_i, idx_name in enumerate(idx_names):
        vals = X_idx[:, col_i]
        per_class = {}
        for cls in classes:
            sub = vals[y_train == cls]
            per_class[str(cls)] = {
                "mean": round(float(np.mean(sub)), 4),
                "std": round(float(np.std(sub)), 4),
                "median": round(float(np.median(sub)), 4),
                "q25": round(float(np.percentile(sub, 25)), 4),
                "q75": round(float(np.percentile(sub, 75)), 4),
            }
        index_stats_by_class.append({"index": idx_name, "classes": per_class})

    # 2. PCA explained variance (train-only fit)
    pca_red = pipe.pca_reducer_
    evr = pca_red.full_explained_variance_ratio_
    cum = pca_red.full_cumulative_variance_
    pca_components = [
        {
            "component": f"PC{i + 1}",
            "explained_variance_ratio": round(float(evr[i]), 4),
            "cumulative_variance": round(float(cum[i]), 4),
        }
        for i in range(min(len(evr), 12))
    ]

    # 3. RF Importance vs. Mutual Information band rankings (train-only fit)
    bs = pipe.band_selector_
    selected_set = set(float(w) for w in bs.selected_wavelengths_)
    band_rankings = []
    for wl, rf_imp, mi_val, comb in zip(
        bs.wavelengths,
        bs.rf_importances_,
        bs.mi_scores_,
        bs.combined_scores_,
    ):
        band_rankings.append(
            {
                "wavelength_nm": float(wl),
                "rf_importance": round(float(rf_imp), 5),
                "mutual_info": round(float(mi_val), 5),
                "consensus_score": round(float(comb), 4),
                "selected": float(wl) in selected_set,
            }
        )

    return {
        "source": source,
        "manifest": res["manifest"],
        "pca": {
            "selected_components": int(pca_red.n_components_),
            "variance_captured": round(float(cum[pca_red.n_components_ - 1]), 4),
            "components": pca_components,
        },
        "band_selection": {
            "top_k": int(len(bs.selected_wavelengths_)),
            "selected_wavelengths_nm": [float(w) for w in bs.selected_wavelengths_],
            "rankings": band_rankings,
        },
        "index_distributions": index_stats_by_class,
        "mcari_citation": "Daughtry et al. (2000), Remote Sensing of Environment 74(2):229-239",
    }


def _plot_day4_figures(primary_res: dict, synthetic_res: dict) -> list[str]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_paths: list[str] = []

    # Figure 07: Train-Only PCA Variance & RF vs Mutual Information Band Selection
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.4))
    fig.patch.set_facecolor("white")

    for row_idx, (res, label_prefix) in enumerate(
        [(primary_res, "Primary Zenodo (9 aligned bands)"), (synthetic_res, "Synthetic (61 bands)")]
    ):
        ax_pca = axes[row_idx, 0]
        comps = res["pca"]["components"]
        x = np.arange(len(comps))
        evr = [c["explained_variance_ratio"] * 100.0 for c in comps]
        cum = [c["cumulative_variance"] * 100.0 for c in comps]
        ax_pca.bar(x, evr, color="#0F766E", alpha=0.82, label="Individual Variance (%)")
        ax_pca.plot(x, cum, color="#D97706", marker="o", linewidth=2.0, label="Cumulative (%)")
        ax_pca.axhline(95.0, color="#64748B", linestyle=":", linewidth=1.0, label="95% Threshold")
        ax_pca.set_xticks(x)
        ax_pca.set_xticklabels([c["component"] for c in comps], fontsize=8)
        ax_pca.set_ylim(0, 108)
        ax_pca.set_ylabel("Explained Variance (%)")
        ax_pca.set_title(
            f"{label_prefix}: Train-Only PCA ({res['pca']['selected_components']} PCs = {res['pca']['variance_captured']*100:.1f}%)",
            fontsize=10,
            fontweight="bold",
        )
        ax_pca.grid(True, axis="y", linestyle="--", alpha=0.3)
        ax_pca.legend(frameon=False, fontsize=8, loc="center right")

        ax_imp = axes[row_idx, 1]
        rankings = res["band_selection"]["rankings"]
        wls = [r["wavelength_nm"] for r in rankings]
        rf_norm = np.array([r["rf_importance"] for r in rankings])
        rf_norm = rf_norm / max(1e-12, float(rf_norm.max()))
        mi_norm = np.array([r["mutual_info"] for r in rankings])
        mi_norm = mi_norm / max(1e-12, float(mi_norm.max()))
        if len(wls) <= 15:
            bw = 0.35
            xp = np.arange(len(wls))
            ax_imp.bar(xp - bw / 2, rf_norm, bw, color="#0F766E", label="Random Forest Importance (norm)")
            ax_imp.bar(xp + bw / 2, mi_norm, bw, color="#2563EB", label="Mutual Information (norm)")
            ax_imp.set_xticks(xp)
            ax_imp.set_xticklabels([f"{int(w)}" for w in wls], fontsize=8)
            for idx_b, r in enumerate(rankings):
                if r["selected"]:
                    ax_imp.text(idx_b, max(rf_norm[idx_b], mi_norm[idx_b]) + 0.04, "★", ha="center", color="#D97706", fontsize=10)
        else:
            ax_imp.plot(wls, rf_norm, color="#0F766E", linewidth=2.0, label="RF Importance (norm)")
            ax_imp.plot(wls, mi_norm, color="#2563EB", linewidth=1.8, linestyle="--", label="Mutual Info (norm)")
            for r in rankings:
                if r["selected"]:
                    ax_imp.axvline(r["wavelength_nm"], color="#D97706", alpha=0.45, linewidth=1.5)
        ax_imp.set_ylim(0, 1.18)
        ax_imp.set_xlabel("Wavelength (nm)")
        ax_imp.set_ylabel("Normalized Score (Train Only)")
        ax_imp.set_title(f"{label_prefix}: Band Selection (Top {res['band_selection']['top_k']} starred/highlighted)", fontsize=10, fontweight="bold")
        ax_imp.grid(True, linestyle="--", alpha=0.3)
        ax_imp.legend(frameon=False, fontsize=8)

    fig.suptitle("Day 4 Leak-Free Feature Reduction: Train-Only PCA & RF/MI Band Selection", fontsize=12, fontweight="bold", y=0.99)
    fig.tight_layout()
    p7 = FIGURES_DIR / "07_pca_variance_and_band_importance.png"
    fig.savefig(p7, dpi=160)
    plt.close(fig)
    fig_paths.append(str(p7.relative_to(ROOT_DIR)))

    # Figure 08: Vegetation Index Separability + Feature Sets A-E Comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 4.8))
    fig.patch.set_facecolor("white")

    # Left: Normalized Class Mean Vegetation Indices (Primary Zenodo)
    idx_items = primary_res["index_distributions"]
    idx_labels = [it["index"] for it in idx_items]
    classes = list(idx_items[0]["classes"].keys())
    xp = np.arange(len(idx_labels))
    w = 0.35
    for c_i, cls in enumerate(classes):
        means = []
        for it in idx_items:
            m_val = it["classes"][cls]["mean"]
            # Scale REP_nm (690..750) into [0..1] visually or standardize relative to class control
            if it["index"] == "REP_nm":
                means.append((m_val - 690.0) / 60.0)
            else:
                means.append(m_val)
        ax1.bar(xp + (c_i - 0.5) * w, means, w, color=PALETTE[c_i], label=cls)
    ax1.set_xticks(xp)
    ax1.set_xticklabels([f"{l}{'*' if l == 'REP_nm' else ''}" for l in idx_labels], fontsize=9)
    ax1.set_title("Primary Class Mean Vegetation Indices (*REP scaled (λ-690)/60)", fontsize=10.2, fontweight="bold")
    ax1.set_ylabel("Index Value")
    ax1.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax1.legend(frameon=False, fontsize=8.5)

    # Right: Feature Sets A–E Leak-Free CV Macro-F1 (Primary RF & Synthetic LR)
    sets_p = primary_res["manifest"]["feature_sets"]
    sets_s = synthetic_res["manifest"]["feature_sets"]
    set_codes = [s["code"] for s in sets_p]
    xs = np.arange(len(set_codes))
    ax2.bar(xs - w / 2, [s["cv_macro_f1_rf"] for s in sets_p], w, color="#0F766E", label="Primary RF (Plant-Grouped CV)")
    ax2.bar(xs + w / 2, [s["cv_macro_f1_lr"] for s in sets_s], w, color="#D97706", label="Synthetic LR (Plant-Grouped CV)")
    ax2.set_xticks(xs)
    ax2.set_xticklabels([f"{c}\n({p['n_features']}d / {s['n_features']}d)" for c, p, s in zip(set_codes, sets_p, sets_s)], fontsize=8.5)
    ax2.set_ylim(0, 1.08)
    ax2.set_ylabel("5-Fold StratifiedGroupKFold Macro-F1")
    ax2.set_title("Named Feature Sets A–E Performance (Inside-Fold Leak-Free)", fontsize=10.2, fontweight="bold")
    ax2.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax2.legend(frameon=False, fontsize=8.5)

    fig.tight_layout()
    p8 = FIGURES_DIR / "08_feature_sets_and_indices.png"
    fig.savefig(p8, dpi=160)
    plt.close(fig)
    fig_paths.append(str(p8.relative_to(ROOT_DIR)))

    return fig_paths


def _write_feature_engineering_note(primary_res: dict, synthetic_res: dict) -> None:
    p_sets = primary_res["manifest"]["feature_sets"]
    s_sets = synthetic_res["manifest"]["feature_sets"]

    match_rows = "\n".join(
        f"| `{m['index_name']}` | `{m['role']}` | `{m['requested_nm']:.0f} nm` | `{m['matched_nm']:.0f} nm` | `±{m['delta_nm']:.1f} nm` |"
        for m in primary_res["manifest"]["band_matches"]
    )
    set_rows = "\n".join(
        f"| **{p['code']}** | {p['description']} | `{p['n_features']}` | `{p['cv_macro_f1_lr']:.4f}` | `{p['cv_macro_f1_rf']:.4f}` | `{s['cv_macro_f1_lr']:.4f}` |"
        for p, s in zip(p_sets, s_sets)
    )

    note = f"""# Day 4 Feature Engineering Note — Indices, PCA, Band Selection & Sets A–E

**Generated programmatically by:** `python3 src/pipeline/run_day4_features.py`  
**Module:** `src/features.py` (all feature selection & PCA fitted strictly inside `StratifiedGroupKFold` / train split)

---

## 1. Vegetation Index Definitions & Wavelength Mapping

Using `find_nearest_band(wavelengths, target_nm)` on Day 3 aligned bands (`{primary_res['manifest']['aligned_wavelengths_nm']}` nm on primary):

- **NDVI:** $(R_{{\\text{{NIR}}}} - R_{{\\text{{Red}}}}) / (R_{{\\text{{NIR}}}} + R_{{\\text{{Red}}}})$ (nearest 800 nm & 670 nm)
- **NDRE:** $(R_{{\\text{{NIR}}}} - R_{{\\text{{RedEdge}}}}) / (R_{{\\text{{NIR}}}} + R_{{\\text{{RedEdge}}}})$ (nearest 800 nm & 720 nm)
- **PRI:** $(R_{{531}} - R_{{570}}) / (R_{{531}} + R_{{570}})$
- **Red-Edge Position (REP):** Peak wavelength of $dR/d\\lambda$ inside `690–750 nm` (interpolated via Guyot & Baret inflection estimator on sparse multispectral LEDs, direct derivative quadratic peak on dense 61-band cubes)
- **MCARI:** $\\left[(R_{{700}} - R_{{670}}) - 0.2\\,(R_{{700}} - R_{{550}})\\right] \\cdot (R_{{700}} / R_{{670}})$ — **Citation:** *Daughtry, C. S. T., Walthall, C. L., Kim, M. S., Brown de Colstoun, E., & McMurtrey, J. E. (2000). Estimating corn leaf chlorophyll concentration from leaf and canopy reflectance. Remote Sensing of Environment, 74(2), 229–239.*

### Nearest-Band Lookup Table (Primary Zenodo Aligned Spectra)

| Index | Role | Requested | Matched Band | Delta |
| --- | --- | ---: | ---: | ---: |
{match_rows}

---

## 2. Leak-Free Dimensionality Reduction & Band Selection (Train Only)

- **PCA (`PCASpectralReducer`):** Standardizes and fits PCA strictly on `X_train`. Captures **`{primary_res['pca']['variance_captured']*100:.2f}%`** variance in **`{primary_res['pca']['selected_components']}` PCs** on Primary and **`{synthetic_res['pca']['variance_captured']*100:.2f}%`** variance in **`{synthetic_res['pca']['selected_components']}` PCs** on Synthetic.
- **Selected Bands (`SupervisedBandSelector`):** Consensus ranking (normalized Random Forest importance + Mutual Information fitted inside train fold only). Top selected Primary wavelengths: **`{primary_res['band_selection']['selected_wavelengths_nm']}` nm**.

---

## 3. Feature Sets A–E Comparison (5-Fold `StratifiedGroupKFold` by `plant_id`)

| Feature Set | Contents | Primary Dim | Primary LR F1 | Primary RF F1 | Synthetic LR F1 |
| --- | --- | ---: | ---: | ---: | ---: |
{set_rows}

Saved `.npz` feature sets for Day 5 modeling reside in `data/processed/` (`*_feature_set_Set_A.npz` through `Set_E.npz`).
"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "feature_engineering_note.md").write_text(note, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Day 4 Feature Engineering Pipeline")
    parser.add_argument("--top-k", type=int, default=5, help="Top-k bands for Set D/E")
    parser.add_argument("--normalization", type=str, default="snv", choices=["none", "snv", "msc"])
    args = parser.parse_args()

    primary_res = _analyze_source("primary", top_k_bands=args.top_k, normalization=args.normalization)
    synthetic_res = _analyze_source("synthetic", top_k_bands=args.top_k, normalization=args.normalization)
    figures = _plot_day4_figures(primary_res, synthetic_res)
    _write_feature_engineering_note(primary_res, synthetic_res)

    payload = {
        "figures": figures,
        "primary": primary_res,
        "synthetic": synthetic_res,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_DIR / "day4_features_metrics.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Day 4 Feature Engineering complete: {out_json} & {DOCS_DIR / 'feature_engineering_note.md'}")
    print(f"Generated {len(figures)} figures in {FIGURES_DIR}")


if __name__ == "__main__":
    main()
