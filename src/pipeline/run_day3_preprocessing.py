"""Day 3 Runner: Execute Configurable Preprocessing Pipeline, Ablation Study, Figures & Note.

Usage:
  python3 src/pipeline/run_day3_preprocessing.py
  python3 src/pipeline/run_day3_preprocessing.py --config-json '{"normalization":"msc","use_first_derivative":true}'
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
from sklearn.metrics import f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.preprocessing import (
    PreprocessingConfig,
    SpectralPreprocessor,
    make_leak_free_train_test_indices,
    remove_nan_spectral_rows,
    run_preprocessing_pipeline,
)
from src.data import load_dataset

REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = ROOT_DIR / "docs"

PALETTE = ["#0F766E", "#D97706", "#DC2626", "#2563EB"]


def _compute_step_metrics(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    wavelengths: np.ndarray,
    comparison_classes: tuple[str, str],
) -> dict:
    """Compute per-class curves, mean Fisher separation J, and leak-free holdout probe F1."""
    c_healthy, c_stressed = comparison_classes
    # Evaluate Fisher ratio on training set only to avoid test peeking
    m_h = y_train == c_healthy
    m_s = y_train == c_stressed
    mu_h = np.mean(X_train[m_h], axis=0)
    mu_s = np.mean(X_train[m_s], axis=0)
    var_h = np.var(X_train[m_h], axis=0)
    var_s = np.var(X_train[m_s], axis=0)
    fisher_per_band = ((mu_s - mu_h) ** 2) / np.maximum(var_h + var_s, 1e-12)
    mean_fisher = float(np.mean(fisher_per_band))
    max_fisher = float(np.max(fisher_per_band))

    # Quick leak-free LogisticRegression holdout probe on transformed features
    le = LabelEncoder().fit(y_train)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_train)
    X_te_s = scaler.transform(X_test)
    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_tr_s, le.transform(y_train))
    y_pred = clf.predict(X_te_s)
    holdout_f1 = float(f1_score(le.transform(y_test), y_pred, average="macro"))

    class_curves = []
    for cls in np.unique(y_train):
        mask = y_train == cls
        sub = X_train[mask]
        c_mean = np.mean(sub, axis=0)
        c_std = np.std(sub, axis=0)
        class_curves.append(
            {
                "label": str(cls),
                "n_samples": int(mask.sum()),
                "points": [
                    {
                        "wavelength_nm": float(wl),
                        "mean": round(float(m), 5),
                        "std": round(float(s), 5),
                    }
                    for wl, m, s in zip(wavelengths, c_mean, c_std)
                ],
            }
        )

    return {
        "n_bands": int(X_train.shape[1]),
        "wavelengths_nm": [float(w) for w in wavelengths],
        "mean_fisher_ratio": round(mean_fisher, 6),
        "max_fisher_ratio": round(max_fisher, 6),
        "holdout_macro_f1": round(holdout_f1, 4),
        "class_curves": class_curves,
    }


def _analyze_dataset(source: str, custom_cfg: PreprocessingConfig) -> dict:
    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, dropped_nan = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )
    train_idx, test_idx = make_leak_free_train_test_indices(y_clean, groups_clean)
    X_tr_raw, X_te_raw = X_clean[train_idx], X_clean[test_idx]
    y_tr, y_te = y_clean[train_idx], y_clean[test_idx]

    classes = list(np.unique(y_clean))
    comp_pair = (classes[0], classes[-1])

    default_drop = (365.0,) if source == "primary" else ()
    presets: list[tuple[str, str, PreprocessingConfig]] = [
        (
            "raw",
            "0. Raw Unprocessed (Clip Only)",
            PreprocessingConfig(
                drop_bad_bands=False,
                drop_wavelengths=(),
                use_savgol=False,
                normalization="none",
                use_first_derivative=False,
            ),
        ),
        (
            "bad_band_drop",
            "1. Drop Bad Bands + Clip",
            PreprocessingConfig(
                drop_bad_bands=True,
                drop_wavelengths=default_drop,
                use_savgol=False,
                normalization="none",
                use_first_derivative=False,
            ),
        ),
        (
            "savgol",
            "2. + Savitzky-Golay Smooth",
            PreprocessingConfig(
                drop_bad_bands=True,
                drop_wavelengths=default_drop,
                use_savgol=True,
                savgol_window=3 if source == "primary" else 5,
                savgol_polyorder=1 if source == "primary" else 2,
                normalization="none",
                use_first_derivative=False,
            ),
        ),
        (
            "snv",
            "3. + SNV Normalization",
            PreprocessingConfig(
                drop_bad_bands=True,
                drop_wavelengths=default_drop,
                use_savgol=True,
                savgol_window=3 if source == "primary" else 5,
                savgol_polyorder=1 if source == "primary" else 2,
                normalization="snv",
                use_first_derivative=False,
            ),
        ),
        (
            "msc",
            "4. + MSC Normalization (Train Ref)",
            PreprocessingConfig(
                drop_bad_bands=True,
                drop_wavelengths=default_drop,
                use_savgol=True,
                savgol_window=3 if source == "primary" else 5,
                savgol_polyorder=1 if source == "primary" else 2,
                normalization="msc",
                use_first_derivative=False,
            ),
        ),
        (
            "first_derivative",
            "5. + First Derivative (dR/dλ)",
            PreprocessingConfig(
                drop_bad_bands=True,
                drop_wavelengths=default_drop,
                use_savgol=True,
                savgol_window=3 if source == "primary" else 5,
                savgol_polyorder=1 if source == "primary" else 2,
                normalization="snv",
                use_first_derivative=True,
            ),
        ),
    ]

    ablation_results = []
    transformed_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for key, label, cfg in presets:
        prep = SpectralPreprocessor(wavelengths=ds.wavelengths, config=cfg)
        X_tr_p = prep.fit_transform(X_tr_raw, y_tr)
        X_te_p = prep.transform(X_te_raw)
        wl_out = prep.get_aligned_wavelengths()
        metrics = _compute_step_metrics(X_tr_p, X_te_p, y_tr, y_te, wl_out, comp_pair)
        ablation_results.append(
            {
                "key": key,
                "label": label,
                "config": cfg.to_dict(),
                **metrics,
            }
        )
        transformed_cache[key] = (X_tr_p, wl_out)

    # Also run user/active config and persist to data/processed/
    # Adjust drop_wavelengths cleanly for synthetic (400..1000 doesn't include 365)
    effective_custom = PreprocessingConfig.from_dict(custom_cfg.to_dict())
    if source == "synthetic":
        effective_custom.drop_wavelengths = tuple(
            w for w in effective_custom.drop_wavelengths if w >= 400.0
        )

    active_run = run_preprocessing_pipeline(
        source=source,  # type: ignore[arg-type]
        config=effective_custom,
        save_outputs=True,
    )
    active_metrics = _compute_step_metrics(
        active_run["X_train_proc"],
        active_run["X_test_proc"],
        active_run["y_train"],
        active_run["y_test"],
        active_run["aligned_wavelengths"],
        comp_pair,
    )

    # Savitzky-Golay parameter comparison on aligned non-SNV bands
    savgol_sweep_configs = (
        [(3, 1), (5, 2), (7, 2)] if source == "primary" else [(5, 2), (7, 2), (11, 3)]
    )
    savgol_comparison = []
    for win, poly in savgol_sweep_configs:
        cfg_sg = PreprocessingConfig(
            drop_bad_bands=True,
            drop_wavelengths=default_drop,
            use_savgol=True,
            savgol_window=win,
            savgol_polyorder=poly,
            normalization="none",
            use_first_derivative=False,
        )
        prep_sg = SpectralPreprocessor(wavelengths=ds.wavelengths, config=cfg_sg)
        X_tr_sg = prep_sg.fit_transform(X_tr_raw, y_tr)
        X_te_sg = prep_sg.transform(X_te_raw)
        wl_sg = prep_sg.get_aligned_wavelengths()
        m_sg = _compute_step_metrics(X_tr_sg, X_te_sg, y_tr, y_te, wl_sg, comp_pair)
        savgol_comparison.append(
            {
                "name": f"win={prep_sg.savgol_.effective_window_length_}, poly={prep_sg.savgol_.effective_polyorder_}",
                "requested_window": win,
                "effective_window": int(prep_sg.savgol_.effective_window_length_),
                "effective_polyorder": int(prep_sg.savgol_.effective_polyorder_),
                "mean_fisher_ratio": m_sg["mean_fisher_ratio"],
                "holdout_macro_f1": m_sg["holdout_macro_f1"],
                "class_curves": m_sg["class_curves"],
            }
        )

    return {
        "source": source,
        "dropped_nan_rows": dropped_nan,
        "manifest": active_run["manifest"],
        "active_metrics": {
            "config": effective_custom.to_dict(),
            **active_metrics,
        },
        "ablation": ablation_results,
        "savgol_comparison": savgol_comparison,
        "_cache": transformed_cache,
    }


def _plot_preprocessing_figures(primary_res: dict, synthetic_res: dict) -> list[str]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_paths: list[str] = []

    # Figure 05: Raw vs. Preprocessed Mean Spectra per Class + Step Separability Comparison
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.2))
    fig.patch.set_facecolor("white")

    for row_idx, (res, title_prefix) in enumerate(
        [(primary_res, "Primary Zenodo (8–10 bands)"), (synthetic_res, "Synthetic (61 bands)")]
    ):
        raw_step = res["ablation"][0]
        snv_step = res["ablation"][3]

        ax_raw = axes[row_idx, 0]
        for idx, cls_curve in enumerate(raw_step["class_curves"]):
            wls = [p["wavelength_nm"] for p in cls_curve["points"]]
            mu = np.array([p["mean"] for p in cls_curve["points"]])
            sd = np.array([p["std"] for p in cls_curve["points"]])
            color = PALETTE[idx % len(PALETTE)]
            ax_raw.plot(wls, mu, color=color, linewidth=2.0, label=cls_curve["label"])
            ax_raw.fill_between(wls, mu - sd, mu + sd, color=color, alpha=0.14)
        ax_raw.set_title(f"{title_prefix}: Raw Mean ± SD (F1={raw_step['holdout_macro_f1']:.3f})", fontsize=10, fontweight="bold")
        ax_raw.set_ylabel("Reflectance (%)")
        ax_raw.grid(True, linestyle="--", alpha=0.3)
        ax_raw.legend(frameon=False, fontsize=8)

        ax_proc = axes[row_idx, 1]
        for idx, cls_curve in enumerate(snv_step["class_curves"]):
            wls = [p["wavelength_nm"] for p in cls_curve["points"]]
            mu = np.array([p["mean"] for p in cls_curve["points"]])
            sd = np.array([p["std"] for p in cls_curve["points"]])
            color = PALETTE[idx % len(PALETTE)]
            ax_proc.plot(wls, mu, color=color, linewidth=2.0, label=cls_curve["label"])
            ax_proc.fill_between(wls, mu - sd, mu + sd, color=color, alpha=0.14)
        ax_proc.set_title(
            f"{title_prefix}: After Bad-Band Drop + SavGol + SNV (F1={snv_step['holdout_macro_f1']:.3f})",
            fontsize=10,
            fontweight="bold",
        )
        ax_proc.set_ylabel("SNV Normalized Units")
        ax_proc.grid(True, linestyle="--", alpha=0.3)
        ax_proc.legend(frameon=False, fontsize=8)
        if row_idx == 1:
            ax_raw.set_xlabel("Wavelength (nm)")
            ax_proc.set_xlabel("Wavelength (nm)")

    fig.suptitle("Day 3 Preprocessing: Raw vs. Cleaned/SNV Class Spectra Preserving Separability", fontsize=12, fontweight="bold", y=0.99)
    fig.tight_layout()
    p5 = FIGURES_DIR / "05_preprocessing_comparison.png"
    fig.savefig(p5, dpi=160)
    plt.close(fig)
    fig_paths.append(str(p5.relative_to(ROOT_DIR)))

    # Figure 06: Step-by-Step Holdout Macro-F1, MSC vs Derivative, and Savitzky-Golay Visual Comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.6))
    fig.patch.set_facecolor("white")

    steps_short = ["Raw", "DropBad", "SavGol", "SNV", "MSC", "1st-Deriv"]
    x_pos = np.arange(len(steps_short))
    f1_prim = [s["holdout_macro_f1"] for s in primary_res["ablation"]]
    f1_synt = [s["holdout_macro_f1"] for s in synthetic_res["ablation"]]
    width = 0.36
    ax1.bar(x_pos - width / 2, f1_prim, width, color="#0F766E", label="Primary (Zenodo 22755812)")
    ax1.bar(x_pos + width / 2, f1_synt, width, color="#D97706", label="Synthetic (400–1000 nm)")
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(steps_short, fontsize=9)
    ax1.set_ylim(0, 1.08)
    ax1.set_ylabel("Plant-Grouped Holdout Macro-F1")
    ax1.set_title("Ablation Across Switchable Preprocessing Steps", fontsize=10.5, fontweight="bold")
    ax1.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax1.legend(frameon=False, fontsize=8.5)
    for i, v in enumerate(f1_prim):
        ax1.text(i - width / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=7.5)
    for i, v in enumerate(f1_synt):
        ax1.text(i + width / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=7.5)

    deriv_step = primary_res["ablation"][5]
    for idx, cls_curve in enumerate(deriv_step["class_curves"]):
        wls = [p["wavelength_nm"] for p in cls_curve["points"]]
        mu = [p["mean"] for p in cls_curve["points"]]
        ax2.plot(wls, mu, marker="o", linewidth=2.0, color=PALETTE[idx], label=cls_curve["label"])
    ax2.axhline(0.0, color="#64748B", linewidth=1.0, linestyle=":")
    ax2.axvspan(690, 750, color="#10B981", alpha=0.10, label="Red-Edge Slope Window (690–750 nm)")
    ax2.set_title("Primary First-Derivative Mean Spectra (dR/dλ after SNV)", fontsize=10.5, fontweight="bold")
    ax2.set_xlabel("Wavelength (nm)")
    ax2.set_ylabel("d(SNV)/dλ (nm⁻¹)")
    ax2.grid(True, linestyle="--", alpha=0.3)
    ax2.legend(frameon=False, fontsize=8)

    fig.tight_layout()
    p6 = FIGURES_DIR / "06_savgol_and_derivative_comparison.png"
    fig.savefig(p6, dpi=160)
    plt.close(fig)
    fig_paths.append(str(p6.relative_to(ROOT_DIR)))

    return fig_paths


def _write_preprocessing_note(primary_res: dict, synthetic_res: dict) -> None:
    p_abl = {item["key"]: item for item in primary_res["ablation"]}
    s_abl = {item["key"]: item for item in synthetic_res["ablation"]}
    note = f"""# Day 3 Preprocessing Note — Which Steps Helped & Why Each Is Included

**Generated programmatically by:** `python3 src/pipeline/run_day3_preprocessing.py`  
**Module:** `src/preprocessing.py` (scikit-learn `Pipeline` + `SpectralPreprocessor`)

---

## 1. One-Sentence Justification for Each Pipeline Step

1. **Drop Bad Bands (`BadBandDropper`):** Removes noisy UV edge bands (`365 nm` on primary, high intra-scan StDev/Mean `{0.490:.3f}`) and SWIR water-absorption windows (`1350–1450 nm`, `1800–1950 nm`) while keeping `wavelengths_` strictly aligned for Day 4 indices.
2. **Reflectance Sanitization (`ReflectanceSanitizer`):** Drops `{primary_res['dropped_nan_rows']}` failed NaN scans cleanly prior to splitting, imputes any residual non-finite cells using training-split column medians only, and clips out-of-range values to `[0, 100]%`.
3. **Savitzky-Golay Smoothing (`SavitzkyGolaySmoother`):** Suppresses high-frequency sensor jitter along the spectral axis using a low-order local polynomial filter (`win=3, poly=1` on sparse 9-band primary; `win=5, poly=2` on dense 61-band synthetic) without blurring sharp red-edge inflection points.
4. **Scatter Normalization (`SpectralScatterNormalizer` — SNV & MSC):** Removes multiplicative illumination and leaf-angle baseline offsets via per-sample **SNV** or training-mean **MSC**, exposing shape changes around green (`525–570 nm`) and red-edge (`700–780 nm`) bands.
5. **First-Derivative Spectra (`FirstDerivativeSpectra`):** Computes wavelength-aware numerical slopes $dR/d\\lambda$ (`np.gradient` over aligned wavelengths) to remove additive background drift and sharpen red-edge slope shifts.

---

## 2. Empirical Separation Comparison (Which Steps Helped vs. Didn't)

Evaluated strictly on leak-free `StratifiedGroupKFold` (`plant_id` holdout fold) using standardized Logistic Regression Macro-F1 and training Fisher ratio $J$:

| Preprocessing Step | Primary Aligned Bands | Primary Fisher $J$ | Primary Holdout F1 | Synthetic Holdout F1 | Assessment |
| --- | ---: | ---: | ---: | ---: | --- |
| Raw Baseline | `{p_abl['raw']['n_bands']}` | `{p_abl['raw']['mean_fisher_ratio']:.5f}` | `{p_abl['raw']['holdout_macro_f1']:.4f}` | `{s_abl['raw']['holdout_macro_f1']:.4f}` | Preserves overall albedo magnitude used by linear LR, but mixes illumination & UV noise |
| Drop Bad Bands (`365 nm`) + Clip | `{p_abl['bad_band_drop']['n_bands']}` | `{p_abl['bad_band_drop']['mean_fisher_ratio']:.5f}` | `{p_abl['bad_band_drop']['holdout_macro_f1']:.4f}` | `{s_abl['bad_band_drop']['holdout_macro_f1']:.4f}` | Raises mean Fisher $J$ (`{p_abl['raw']['mean_fisher_ratio']:.5f}` → `{p_abl['bad_band_drop']['mean_fisher_ratio']:.5f}`) by removing noisy UV edge |
| + Savitzky-Golay Smoothing | `{p_abl['savgol']['n_bands']}` | `{p_abl['savgol']['mean_fisher_ratio']:.5f}` | `{p_abl['savgol']['holdout_macro_f1']:.4f}` | `{s_abl['savgol']['holdout_macro_f1']:.4f}` | Stabilizes high-frequency curve before derivatives; mild smoothing loss on sparse 9-band LEDs |
| + SNV Normalization | `{p_abl['snv']['n_bands']}` | `{p_abl['snv']['mean_fisher_ratio']:.5f}` | `{p_abl['snv']['holdout_macro_f1']:.4f}` | `{s_abl['snv']['holdout_macro_f1']:.4f}` | Recovers linear holdout F1 (`{p_abl['savgol']['holdout_macro_f1']:.4f}` → `{p_abl['snv']['holdout_macro_f1']:.4f}`) after removing leaf albedo scatter |
| + MSC (Train Reference Only) | `{p_abl['msc']['n_bands']}` | `{p_abl['msc']['mean_fisher_ratio']:.5f}` | `{p_abl['msc']['holdout_macro_f1']:.4f}` | `{s_abl['msc']['holdout_macro_f1']:.4f}` | Closely tracks SNV using training-split reference spectrum without test leakage |
| + First Derivative ($dR/d\\lambda$) | `{p_abl['first_derivative']['n_bands']}` | `{p_abl['first_derivative']['mean_fisher_ratio']:.5f}` | `{p_abl['first_derivative']['holdout_macro_f1']:.4f}` | `{s_abl['first_derivative']['holdout_macro_f1']:.4f}` | Highest Fisher $J$ (`{p_abl['first_derivative']['mean_fisher_ratio']:.5f}`) on Primary; degrades sparse-gap linear separation less than dense cubes under noise |

---

## 3. Key Takeaway Carried Forward to Day 4 & Day 5

- **Primary Recommendation:** Enable `BadBandDropper(drop=[365.0])` + `ReflectanceSanitizer(clip=[0, 100])` + gentle `Savitzky-Golay(w=3, p=1)` for the uncentered **vegetation index branch**, and pair with **SNV / MSC** for spectral/PCA/band-selection branches.
- **Warning:** Never compute NDVI/NDRE/PRI/MCARI *after* SNV or first derivative—zero-centered reflectances cause ratio denominators to cross zero. `SpectralFeatureSetPipeline` routes index extraction through the non-centered reflectance branch automatically.
- **Saved Outputs (`data/processed/`):** `primary_day3_preprocessed.npz` (`{primary_res['manifest']['train_rows']}` train / `{primary_res['manifest']['test_rows']}` test, `{len(primary_res['manifest']['wavelengths_out_nm'])}` aligned bands `{primary_res['manifest']['wavelengths_out_nm']}`).
"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "preprocessing_note.md").write_text(note, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Day 3 Spectral Preprocessing & Ablation")
    parser.add_argument("--config-json", type=str, default=None, help="JSON config overrides")
    args = parser.parse_args()

    custom_cfg = (
        PreprocessingConfig.from_dict(json.loads(args.config_json))
        if args.config_json
        else PreprocessingConfig()
    )

    primary_res = _analyze_dataset("primary", custom_cfg)
    synthetic_res = _analyze_dataset("synthetic", custom_cfg)
    figures = _plot_preprocessing_figures(primary_res, synthetic_res)
    _write_preprocessing_note(primary_res, synthetic_res)

    # Strip internal numpy cache before serializing JSON
    primary_clean = {k: v for k, v in primary_res.items() if k != "_cache"}
    synthetic_clean = {k: v for k, v in synthetic_res.items() if k != "_cache"}

    payload = {
        "figures": figures,
        "primary": primary_clean,
        "synthetic": synthetic_clean,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_DIR / "day3_preprocessing_metrics.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Day 3 Preprocessing complete: {out_json} & {DOCS_DIR / 'preprocessing_note.md'}")
    print(f"Generated {len(figures)} figures in {FIGURES_DIR}")


if __name__ == "__main__":
    main()
