"""Day 5 Runner: Baseline Models (RF, XGBoost, SVM, PLS-DA) & Leak-Free Evaluation.

Usage:
  python3 src/pipeline/run_day5_baselines.py
  python3 src/pipeline/run_day5_baselines.py --group-col plant_id
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

from src.data import DatasetSource, load_dataset
from src.evaluation import (
    PLSDAClassifier,
    RANDOM_SEED,
    build_and_save_grouped_splits,
    build_naive_random_splits,
    evaluate_cv_folds,
)
from src.features import FEATURE_SET_LABELS, FeatureSetName, SpectralFeatureSetPipeline
from src.preprocessing import PreprocessingConfig, remove_nan_spectral_rows

REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = ROOT_DIR / "docs"
EXPERIMENT_LOG_PATH = REPORTS_DIR / "experiment_log.csv"


def _make_model_estimator(model_key: str, y_enc: np.ndarray):
    n_classes = int(len(np.unique(y_enc)))
    if model_key == "random_forest":
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            n_jobs=1,
        )
    if model_key == "xgboost":
        if n_classes == 2:
            neg = int((y_enc == 0).sum())
            pos = max(1, int((y_enc == 1).sum()))
            spw = round(neg / pos, 4)
            return XGBClassifier(
                n_estimators=180,
                max_depth=5,
                learning_rate=0.06,
                subsample=0.85,
                colsample_bytree=0.85,
                scale_pos_weight=spw,
                eval_metric="logloss",
                random_state=RANDOM_SEED,
                n_jobs=1,
            )
        return XGBClassifier(
            n_estimators=180,
            max_depth=5,
            learning_rate=0.06,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="mlogloss",
            random_state=RANDOM_SEED,
            n_jobs=1,
        )
    if model_key == "svm":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "svc",
                    SVC(
                        C=2.0,
                        kernel="rbf",
                        gamma="scale",
                        probability=True,
                        class_weight="balanced",
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        )
    if model_key == "pls_da":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("plsda", PLSDAClassifier(n_components=5, scale=False)),
            ]
        )
    raise ValueError(f"Unknown model key: {model_key}")


MODEL_META = [
    ("random_forest", "Random Forest"),
    ("xgboost", "XGBoost"),
    ("svm", "SVM (RBF)"),
    ("pls_da", "PLS-DA"),
]


def _run_for_source(source: DatasetSource, group_col: str = "plant_id") -> dict:
    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, dropped_nan = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )

    folds, split_manifest = build_and_save_grouped_splits(
        y=y_clean,
        group_ids=groups_clean,
        source=source,
        group_col=group_col,
        n_splits=5,
        save=True,
    )
    naive_folds = build_naive_random_splits(y=y_clean, n_splits=5)

    drop_wl = (365.0,) if source == "primary" else ()
    prep_cfg = PreprocessingConfig(
        drop_bad_bands=True,
        drop_wavelengths=drop_wl,
        use_savgol=True,
        savgol_window=3 if source == "primary" else 5,
        savgol_polyorder=1 if source == "primary" else 2,
        normalization="snv",
        use_first_derivative=False,
    )

    _, counts = np.unique(y_clean, return_counts=True)
    y_dummy_enc = np.concatenate([np.full(c, i) for i, c in enumerate(counts)])

    # Block 2: Train all 4 baselines on Feature Set A (Preprocessed spectrum)
    set_a_results: list[dict] = []
    for model_key, model_label in MODEL_META:
        def factory_a(mk: str = model_key):
            return Pipeline(
                [
                    (
                        "features",
                        SpectralFeatureSetPipeline(
                            wavelengths=ds.wavelengths,
                            feature_set="A_full_spectrum",
                            prep_config=prep_cfg,
                            top_k_bands=5,
                        ),
                    ),
                    ("clf", _make_model_estimator(mk, y_dummy_enc)),
                ]
            )

        res = evaluate_cv_folds(X_clean, y_clean, folds, factory_a)
        set_a_results.append(
            {
                "model_key": model_key,
                "model_name": model_label,
                "feature_set_key": "A_full_spectrum",
                "feature_set_code": "A",
                "feature_set_desc": FEATURE_SET_LABELS["A_full_spectrum"][1],
                "split_scheme": f"StratifiedGroupKFold({group_col})",
                **res,
            }
        )

    best_set_a = max(set_a_results, key=lambda r: (r["macro_f1_mean"], r["roc_auc_mean"]))
    best_model_key = best_set_a["model_key"]
    best_model_name = best_set_a["model_name"]

    # Block 3: Repeat best baseline model across Feature Sets B, C, D, E
    feature_set_sweep: list[dict] = [best_set_a]
    for fkey in ("B_veg_indices", "C_pca", "D_selected_bands", "E_indices_plus_selected"):
        short_code = FEATURE_SET_LABELS[fkey][0].replace("Set ", "")

        def factory_fs(fk: FeatureSetName = fkey, mk: str = best_model_key):
            return Pipeline(
                [
                    (
                        "features",
                        SpectralFeatureSetPipeline(
                            wavelengths=ds.wavelengths,
                            feature_set=fk,
                            prep_config=prep_cfg,
                            top_k_bands=5,
                        ),
                    ),
                    ("clf", _make_model_estimator(mk, y_dummy_enc)),
                ]
            )

        res = evaluate_cv_folds(X_clean, y_clean, folds, factory_fs)
        feature_set_sweep.append(
            {
                "model_key": best_model_key,
                "model_name": best_model_name,
                "feature_set_key": fkey,
                "feature_set_code": short_code,
                "feature_set_desc": FEATURE_SET_LABELS[fkey][1],
                "split_scheme": f"StratifiedGroupKFold({group_col})",
                **res,
            }
        )

    # Identify overall best baseline (model + feature set) across all evaluated combinations
    all_runs = set_a_results + feature_set_sweep[1:]
    overall_best = max(all_runs, key=lambda r: (r["macro_f1_mean"], r["roc_auc_mean"]))

    # Block 5: Leakage Demonstration — run best model & feature set on naive random split
    best_fk: FeatureSetName = overall_best["feature_set_key"]
    best_mk: str = overall_best["model_key"]

    def factory_leak():
        return Pipeline(
            [
                (
                    "features",
                    SpectralFeatureSetPipeline(
                        wavelengths=ds.wavelengths,
                        feature_set=best_fk,
                        prep_config=prep_cfg,
                        top_k_bands=5,
                    ),
                ),
                ("clf", _make_model_estimator(best_mk, y_dummy_enc)),
            ]
        )

    leaky_res = evaluate_cv_folds(X_clean, y_clean, naive_folds, factory_leak)
    leakage_comparison = {
        "model_key": best_mk,
        "model_name": overall_best["model_name"],
        "feature_set_code": overall_best["feature_set_code"],
        "feature_set_key": best_fk,
        "grouped_balanced_acc": overall_best["balanced_acc_mean"],
        "grouped_balanced_acc_std": overall_best["balanced_acc_std"],
        "grouped_macro_f1": overall_best["macro_f1_mean"],
        "grouped_macro_f1_std": overall_best["macro_f1_std"],
        "grouped_roc_auc": overall_best["roc_auc_mean"],
        "naive_balanced_acc": leaky_res["balanced_acc_mean"],
        "naive_balanced_acc_std": leaky_res["balanced_acc_std"],
        "naive_macro_f1": leaky_res["macro_f1_mean"],
        "naive_macro_f1_std": leaky_res["macro_f1_std"],
        "naive_roc_auc": leaky_res["roc_auc_mean"],
        "inflation_balanced_acc": round(leaky_res["balanced_acc_mean"] - overall_best["balanced_acc_mean"], 4),
        "inflation_macro_f1": round(leaky_res["macro_f1_mean"] - overall_best["macro_f1_mean"], 4),
        "inflation_roc_auc": round(leaky_res["roc_auc_mean"] - overall_best["roc_auc_mean"], 4),
        "naive_confusion_matrix": leaky_res["confusion_matrix"],
    }

    return {
        "source": source,
        "random_seed": RANDOM_SEED,
        "group_col": group_col,
        "dropped_nan_rows": dropped_nan,
        "clean_samples": int(len(y_clean)),
        "split_manifest": split_manifest,
        "set_a_models": set_a_results,
        "best_model_feature_sets": feature_set_sweep,
        "overall_best": {k: v for k, v in overall_best.items() if k not in ("oof_pred_indices", "oof_true_indices", "oof_proba")},
        "leakage_demonstration": leakage_comparison,
    }


def _plot_day5_figures(primary_res: dict, synthetic_res: dict) -> list[str]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    # Figure 09: Set A 4-Model Confusion Matrices (Primary Zenodo) + Best Model Normalized CM
    fig, axes = plt.subplots(1, 4, figsize=(14.5, 3.8))
    fig.patch.set_facecolor("white")

    for ax, run in zip(axes, primary_res["set_a_models"]):
        cm = np.array(run["confusion_matrix"], dtype=float)
        row_sums = np.maximum(cm.sum(axis=1, keepdims=True), 1.0)
        cm_pct = cm / row_sums * 100.0
        ax.imshow(cm_pct, cmap="YlGnBu", vmin=0, vmax=100)
        short_classes = ["Control", "Drought"] if len(run["class_names"]) == 2 else [c[:8] for c in run["class_names"]]
        ax.set_xticks(range(len(short_classes)))
        ax.set_xticklabels(short_classes, fontsize=8.5)
        ax.set_yticks(range(len(short_classes)))
        ax.set_yticklabels(short_classes, fontsize=8.5)
        ax.set_xlabel("Predicted", fontsize=8.5)
        if ax is axes[0]:
            ax.set_ylabel("True", fontsize=8.5)
        ax.set_title(
            f"{run['model_name']} (Set A)\nF1={run['macro_f1_mean']:.3f} ± {run['macro_f1_std']:.3f}",
            fontsize=9.2,
            fontweight="bold",
        )
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                txt_color = "white" if cm_pct[i, j] > 55 else "#0F172A"
                ax.text(
                    j,
                    i,
                    f"{int(cm[i, j])}\n({cm_pct[i, j]:.1f}%)",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=txt_color,
                    fontweight="semibold",
                )

    fig.suptitle(
        "Day 5 Primary Leak-Free Out-of-Fold Confusion Matrices (Set A · 5-Fold StratifiedGroupKFold by plant_id)",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    p9 = FIGURES_DIR / "09_day5_confusion_matrices.png"
    fig.savefig(p9, dpi=160, bbox_inches="tight")
    plt.close(fig)
    paths.append(str(p9.relative_to(ROOT_DIR)))

    # Figure 10: Baseline Comparison Across Feature Sets A-E & The Leakage Gap Demonstration
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.7))
    fig.patch.set_facecolor("white")

    # Left: Best model Macro-F1 (+/- SD) across Feature Sets A-E on Primary
    fs_runs = primary_res["best_model_feature_sets"]
    x = np.arange(len(fs_runs))
    means = [r["macro_f1_mean"] for r in fs_runs]
    stds = [r["macro_f1_std"] for r in fs_runs]
    bacc = [r["balanced_acc_mean"] for r in fs_runs]
    w = 0.36
    ax1.bar(x - w / 2, means, w, yerr=stds, capsize=4, color="#0F766E", label="Macro-F1 (± fold SD)")
    ax1.bar(x + w / 2, bacc, w, color="#2563EB", alpha=0.82, label="Balanced Accuracy")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Set {r['feature_set_code']}" for r in fs_runs], fontsize=9)
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("5-Fold Grouped CV Score")
    ax1.set_title(
        f"Primary ({fs_runs[0]['model_name']}): Feature Sets A–E Comparison",
        fontsize=10.2,
        fontweight="bold",
    )
    ax1.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax1.legend(frameon=False, fontsize=8.5)
    for i, m in enumerate(means):
        ax1.text(i - w / 2, m + stds[i] + 0.02, f"{m:.3f}", ha="center", fontsize=8)

    # Right: The Leakage Demonstration (Primary & Synthetic Grouped vs Naive Random Split)
    leak_p = primary_res["leakage_demonstration"]
    leak_s = synthetic_res["leakage_demonstration"]
    cats = ["Primary Bal. Acc", "Primary Macro-F1", "Primary ROC-AUC", "Synthetic Macro-F1"]
    grouped_vals = [
        leak_p["grouped_balanced_acc"],
        leak_p["grouped_macro_f1"],
        leak_p["grouped_roc_auc"],
        leak_s["grouped_macro_f1"],
    ]
    naive_vals = [
        leak_p["naive_balanced_acc"],
        leak_p["naive_macro_f1"],
        leak_p["naive_roc_auc"],
        leak_s["naive_macro_f1"],
    ]
    xk = np.arange(len(cats))
    ax2.bar(xk - w / 2, grouped_vals, w, color="#0F766E", label="Grouped Split (plant_id, Honest)")
    ax2.bar(xk + w / 2, naive_vals, w, color="#DC2626", alpha=0.88, label="Naive Random Split (Leaky)")
    ax2.set_xticks(xk)
    ax2.set_xticklabels(cats, fontsize=8.5)
    ax2.set_ylim(0, 1.12)
    ax2.set_ylabel("Score")
    ax2.set_title(
        f"Leakage Demonstration ({leak_p['model_name']} · Set {leak_p['feature_set_code']})",
        fontsize=10.2,
        fontweight="bold",
    )
    ax2.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax2.legend(frameon=False, fontsize=8.5)
    for i, (g, n) in enumerate(zip(grouped_vals, naive_vals)):
        ax2.text(i + w / 2, n + 0.02, f"{n:.3f}\n(+{(n - g):.3f})", ha="center", fontsize=7.5, color="#B91C1C")

    fig.tight_layout()
    p10 = FIGURES_DIR / "10_day5_baseline_and_leakage_gap.png"
    fig.savefig(p10, dpi=160)
    plt.close(fig)
    paths.append(str(p10.relative_to(ROOT_DIR)))

    return paths


def _save_csv_and_experiment_log(primary_res: dict, synthetic_res: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for res in (primary_res, synthetic_res):
        seen = set()
        for r in res["set_a_models"] + res["best_model_feature_sets"]:
            key = (res["source"], r["model_key"], r["feature_set_code"], r["split_scheme"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "source": res["source"],
                    "model": r["model_name"],
                    "feature_set": r["feature_set_code"],
                    "split_scheme": r["split_scheme"],
                    "balanced_acc_mean": r["balanced_acc_mean"],
                    "balanced_acc_std": r["balanced_acc_std"],
                    "macro_f1_mean": r["macro_f1_mean"],
                    "macro_f1_std": r["macro_f1_std"],
                    "roc_auc_mean": r["roc_auc_mean"],
                    "roc_auc_std": r["roc_auc_std"],
                    "seed": res["random_seed"],
                }
            )
        leak = res["leakage_demonstration"]
        rows.append(
            {
                "source": res["source"],
                "model": f"{leak['model_name']} (LEAKY DEMO)",
                "feature_set": leak["feature_set_code"],
                "split_scheme": "Naive StratifiedKFold (LEAKY)",
                "balanced_acc_mean": leak["naive_balanced_acc"],
                "balanced_acc_std": leak["naive_balanced_acc_std"],
                "macro_f1_mean": leak["naive_macro_f1"],
                "macro_f1_std": leak["naive_macro_f1_std"],
                "roc_auc_mean": leak["naive_roc_auc"],
                "roc_auc_std": 0.0,
                "seed": res["random_seed"],
            }
        )

    df_out = pd.DataFrame(rows)
    df_out.to_csv(REPORTS_DIR / "day5_baseline_results.csv", index=False)

    # Seed Day 5 runs into experiment_log.csv cleanly
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_rows = []
    for idx, r in enumerate(rows):
        log_rows.append(
            {
                "run_id": f"day5_{idx + 1:02d}",
                "timestamp": ts,
                "day": "Day 5",
                "data_version": f"{r['source']}_v1",
                "preprocessing": "drop_365nm|clip_0_100|savgol|snv",
                "features": f"Set {r['feature_set']}",
                "model": r["model"],
                "parameters": f"seed={r['seed']}; {r['split_scheme']}",
                "cv_scheme": r["split_scheme"],
                "balanced_acc": f"{r['balanced_acc_mean']:.4f} ± {r['balanced_acc_std']:.4f}",
                "macro_f1": f"{r['macro_f1_mean']:.4f} ± {r['macro_f1_std']:.4f}",
                "roc_auc": f"{r['roc_auc_mean']:.4f}",
                "notes": "Baseline CV" if "LEAKY" not in r["split_scheme"] else "Naive random split leakage benchmark",
            }
        )
    with open(EXPERIMENT_LOG_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(log_rows[0].keys()))
        writer.writeheader()
        writer.writerows(log_rows)


def _write_baseline_note(primary_res: dict, synthetic_res: dict) -> None:
    set_a_rows = "\n".join(
        f"| {r['model_name']} | {r['feature_set_code']} | `{r['balanced_acc_mean']:.4f} ± {r['balanced_acc_std']:.4f}` | `{r['macro_f1_mean']:.4f} ± {r['macro_f1_std']:.4f}` | `{r['roc_auc_mean']:.4f} ± {r['roc_auc_std']:.4f}` |"
        for r in primary_res["set_a_models"]
    )
    sweep_rows = "\n".join(
        f"| {r['model_name']} | {r['feature_set_code']} ({r['feature_set_desc']}) | `{r['balanced_acc_mean']:.4f} ± {r['balanced_acc_std']:.4f}` | `{r['macro_f1_mean']:.4f} ± {r['macro_f1_std']:.4f}` | `{r['roc_auc_mean']:.4f} ± {r['roc_auc_std']:.4f}` |"
        for r in primary_res["best_model_feature_sets"][1:]
    )
    best = primary_res["overall_best"]
    leak_p = primary_res["leakage_demonstration"]
    leak_s = synthetic_res["leakage_demonstration"]

    note = f"""# Day 5 Baseline Models & Leak-Free Evaluation Report

**Generated programmatically by:** `python3 src/pipeline/run_day5_baselines.py`  
**Evaluation Harness:** `src/evaluation.py` (`StratifiedGroupKFold(n_splits=5, shuffle=True, random_state={RANDOM_SEED})` grouped by `{primary_res['group_col']}`)  
**Zero-Leakage Guarantee:** `0` plant overlap across every CV fold; scalers, MSC references, PCA, and RF/MI band selectors refit strictly inside each fold.

---

## 1. Primary Dataset Results Table — Feature Set A (Mean ± Std Across 5 Plant-Grouped Folds)

| Model | Feature Set | Balanced Accuracy | Macro-F1 | ROC-AUC |
| --- | :---: | ---: | ---: | ---: |
{set_a_rows}

---

## 2. Best Baseline Model ({primary_res['best_model_feature_sets'][0]['model_name']}) Across Feature Sets B–E

| Model | Feature Set | Balanced Accuracy | Macro-F1 | ROC-AUC |
| --- | --- | ---: | ---: | ---: |
{sweep_rows}

**Primary Best Baseline to Beat:** **`{best['model_name']}`** on **Feature Set {best['feature_set_code']}** — Macro-F1 **`{best['macro_f1_mean']:.4f} ± {best['macro_f1_std']:.4f}`**, Balanced Acc **`{best['balanced_acc_mean']:.4f} ± {best['balanced_acc_std']:.4f}`**, ROC-AUC **`{best['roc_auc_mean']:.4f}`**.

---

## 3. The Leakage Demonstration (Plant-Grouped vs. Naive Random Split)

Running **`{leak_p['model_name']}` (Set {leak_p['feature_set_code']})** with a naive random sample split (`StratifiedKFold`, ignoring `plant_id`) leaks replicate plant signatures across train and validation folds:

| Dataset | Grouped Balanced Acc | Naive Random Bal. Acc | Inflation Gap (Δ) | Grouped Macro-F1 | Naive Macro-F1 | F1 Inflation (Δ) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Primary (Zenodo 22755812)** | `{leak_p['grouped_balanced_acc']:.4f}` | `{leak_p['naive_balanced_acc']:.4f}` | **`+{leak_p['inflation_balanced_acc']:.4f}`** | `{leak_p['grouped_macro_f1']:.4f}` | `{leak_p['naive_macro_f1']:.4f}` | **`+{leak_p['inflation_macro_f1']:.4f}`** |
| **Synthetic (400–1000 nm)** | `{leak_s['grouped_balanced_acc']:.4f}` | `{leak_s['naive_balanced_acc']:.4f}` | `+{leak_s['inflation_balanced_acc']:.4f}` | `{leak_s['grouped_macro_f1']:.4f}` | `{leak_s['naive_macro_f1']:.4f}` | `+{leak_s['inflation_macro_f1']:.4f}` |

---

## 4. Interpretation & Week 3 Baseline Benchmark

- Naive random sample splitting artificially inflates Primary Macro-F1 by **`+{leak_p['inflation_macro_f1']:.4f}`** (`{leak_p['grouped_macro_f1']:.4f} → {leak_p['naive_macro_f1']:.4f}`), proving why cross-validation must isolate whole plants (`plant_id`) rather than mixing repeated daily scans of the same plant across splits.
- Under honest plant-grouped validation, raw-spectrum single-timepoint static separation across the full 31-day trial sits around `{best['macro_f1_mean']:.4f}` Macro-F1 because early trial dates have nearly identical water-stress spectra (analyzed in detail on Day 6).
- **Target to Beat in Week 3 / Day 6:** Tuned `{best['model_name']}` and temporal lag/sequence models evaluated strictly on the same `plant_id` folds (`data/processed/primary_day5_cv_splits.json`).
"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "baseline_results_note.md").write_text(note, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Day 5 Leak-Free Baselines & Leakage Benchmark")
    parser.add_argument("--group-col", type=str, default="plant_id", choices=["plant_id", "plot_id", "field_id"])
    args = parser.parse_args()

    primary_res = _run_for_source("primary", group_col=args.group_col)
    synthetic_res = _run_for_source("synthetic", group_col="plant_id")
    figures = _plot_day5_figures(primary_res, synthetic_res)
    _save_csv_and_experiment_log(primary_res, synthetic_res)
    _write_baseline_note(primary_res, synthetic_res)

    # Strip large OOF arrays before writing UI JSON payload (Day 6 consumes OOF directly)
    def _clean_for_json(res: dict) -> dict:
        out = dict(res)
        for k in ("set_a_models", "best_model_feature_sets"):
            out[k] = [
                {kk: vv for kk, vv in item.items() if kk not in ("oof_pred_indices", "oof_true_indices", "oof_proba")}
                for item in res[k]
            ]
        return out

    payload = {
        "figures": figures,
        "csv_path": "reports/day5_baseline_results.csv",
        "primary": _clean_for_json(primary_res),
        "synthetic": _clean_for_json(synthetic_res),
    }
    out_json = REPORTS_DIR / "day5_baseline_metrics.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Day 5 Baselines complete: {out_json} & {REPORTS_DIR / 'day5_baseline_results.csv'}")
    print(f"Best Primary: {primary_res['overall_best']['model_name']} (Set {primary_res['overall_best']['feature_set_code']}) F1={primary_res['overall_best']['macro_f1_mean']:.4f} vs Leaky Naive F1={primary_res['leakage_demonstration']['naive_macro_f1']:.4f}")


if __name__ == "__main__":
    main()
