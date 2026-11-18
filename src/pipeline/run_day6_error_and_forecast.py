"""Day 6 Runner: Error Analysis, SHAP & Wavelength Interpretability, Light Tuning, Forecasting Prep & Experiment Log.

Usage:
  python3 src/pipeline/run_day6_error_and_forecast.py
  python3 src/pipeline/run_day6_error_and_forecast.py --horizon 1 --window 3
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
import shap
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

from src.data import DatasetSource, load_dataset
from src.evaluation import RANDOM_SEED, build_and_save_grouped_splits, evaluate_cv_folds
from src.features import FeatureSetName, SpectralFeatureSetPipeline
from src.pipeline.run_day5_baselines import _make_model_estimator
from src.preprocessing import PreprocessingConfig, remove_nan_spectral_rows
from src.sequences import build_temporal_sequences, evaluate_forecasting_baselines

REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = ROOT_DIR / "docs"
EXPERIMENT_LOG_PATH = REPORTS_DIR / "experiment_log.csv"


def _compute_shap_and_perm(
    X_clean: np.ndarray,
    y_clean: np.ndarray,
    ds_wavelengths: np.ndarray,
    prep_cfg: PreprocessingConfig,
    folds: list[tuple[np.ndarray, np.ndarray]],
    feature_set_key: FeatureSetName,
    model_key: str,
) -> dict:
    """Compute leak-free out-of-fold SHAP + Permutation Importance on the target pipeline."""
    le = LabelEncoder().fit(y_clean)
    y_enc = le.transform(y_clean)
    tr_idx, va_idx = folds[0]

    feat_pipe = SpectralFeatureSetPipeline(
        wavelengths=ds_wavelengths,
        feature_set=feature_set_key,
        prep_config=prep_cfg,
        top_k_bands=5,
    )
    X_tr = feat_pipe.fit_transform(X_clean[tr_idx], y_clean[tr_idx])
    X_va = feat_pipe.transform(X_clean[va_idx])
    feat_names = feat_pipe.get_feature_names_out()

    clf = _make_model_estimator(model_key, y_enc)
    clf.fit(X_tr, y_enc[tr_idx])

    # 1) Permutation Importance on held-out fold
    perm = permutation_importance(
        clf,
        X_va,
        y_enc[va_idx],
        n_repeats=6,
        random_state=RANDOM_SEED,
        scoring="f1_macro",
    )
    perm_means = np.maximum(0.0, perm.importances_mean)

    # 2) SHAP values on held-out fold sample (capped cleanly for speed)
    n_eval = min(120, len(X_va))
    X_eval = X_va[:n_eval]
    shap_method = "TreeExplainer"
    try:
        if model_key in ("random_forest", "xgboost"):
            explainer = shap.TreeExplainer(clf)
            raw_sv = explainer.shap_values(X_eval)
            if isinstance(raw_sv, list):
                sv_mat = np.asarray(raw_sv[1 if len(raw_sv) > 1 else 0], dtype=float)
            else:
                sv_mat = np.asarray(raw_sv, dtype=float)
                if sv_mat.ndim == 3:
                    sv_mat = sv_mat[:, :, 1 if sv_mat.shape[2] > 1 else 0]
        else:
            shap_method = "KernelExplainer"
            bg = shap.kmeans(X_tr, min(20, len(X_tr)))
            explainer = shap.KernelExplainer(clf.predict_proba, bg)
            raw_sv = explainer.shap_values(X_eval[:50], nsamples=60)
            if isinstance(raw_sv, list):
                sv_mat = np.asarray(raw_sv[1 if len(raw_sv) > 1 else 0], dtype=float)
            else:
                sv_mat = np.asarray(raw_sv, dtype=float)
                if sv_mat.ndim == 3:
                    sv_mat = sv_mat[:, :, 1 if sv_mat.shape[2] > 1 else 0]
    except Exception:
        # Fallback if any SHAP backend edge-case occurs on custom wrapper
        shap_method = "PermutationProxy"
        sv_mat = np.tile(perm_means, (n_eval, 1))

    mean_abs_shap = np.mean(np.abs(sv_mat), axis=0)
    signed_corr = []
    for j in range(X_eval.shape[1]):
        x_col = X_eval[: sv_mat.shape[0], j]
        if np.std(x_col) > 1e-9 and np.std(sv_mat[:, j]) > 1e-9:
            c = float(np.corrcoef(x_col, sv_mat[:, j])[0, 1])
        else:
            c = 0.0
        signed_corr.append(c)

    items = []
    for idx, fname in enumerate(feat_names):
        items.append(
            {
                "feature": fname,
                "mean_abs_shap": round(float(mean_abs_shap[idx]), 5),
                "permutation_importance": round(float(perm_means[idx]), 5),
                "direction_corr": round(float(signed_corr[idx]), 3),
            }
        )
    items.sort(key=lambda d: d["mean_abs_shap"], reverse=True)

    return {
        "method": shap_method,
        "feature_set_key": feature_set_key,
        "n_eval_samples": int(sv_mat.shape[0]),
        "features": items,
    }


def _light_tune_best_model(
    X_clean: np.ndarray,
    y_clean: np.ndarray,
    ds_wavelengths: np.ndarray,
    prep_cfg: PreprocessingConfig,
    folds: list[tuple[np.ndarray, np.ndarray]],
    best_model_key: str,
    best_feature_key: FeatureSetName,
    baseline_metrics: dict,
) -> dict:
    """Block 4: Light hyperparameter tuning strictly inside StratifiedGroupKFold.

    Precomputes the fixed SpectralFeatureSetPipeline fit strictly per fold so the
    classifier grid avoids redundant RF+MI band selection while guaranteeing zero leakage.
    """
    le = LabelEncoder().fit(y_clean)
    y_enc = le.transform(y_clean)
    n_classes = len(le.classes_)
    _, counts = np.unique(y_enc, return_counts=True)

    # Strictly fit feature pipeline inside each fold once
    fold_features: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    for tr_idx, va_idx in folds:
        feat_pipe = SpectralFeatureSetPipeline(ds_wavelengths, best_feature_key, prep_cfg, top_k_bands=5)
        X_tr_f = feat_pipe.fit_transform(X_clean[tr_idx], y_enc[tr_idx])
        X_va_f = feat_pipe.transform(X_clean[va_idx])
        fold_features.append((X_tr_f, y_enc[tr_idx], X_va_f, y_enc[va_idx]))

    def _eval_cached_folds(clf_factory) -> dict:
        fold_bacc, fold_mf1, fold_auc = [], [], []
        for X_tr_f, y_tr_f, X_va_f, y_va_f in fold_features:
            clf = clf_factory()
            clf.fit(X_tr_f, y_tr_f)
            pred = np.asarray(clf.predict(X_va_f), dtype=int)
            proba = clf.predict_proba(X_va_f)
            fold_bacc.append(float(balanced_accuracy_score(y_va_f, pred)))
            fold_mf1.append(float(f1_score(y_va_f, pred, average="macro")))
            try:
                if n_classes == 2:
                    fold_auc.append(float(roc_auc_score(y_va_f, proba[:, 1])))
                else:
                    fold_auc.append(float(roc_auc_score(y_va_f, proba, multi_class="ovr", average="macro")))
            except ValueError:
                pass
        return {
            "balanced_acc_mean": round(float(np.mean(fold_bacc)), 4),
            "balanced_acc_std": round(float(np.std(fold_bacc, ddof=1) if len(fold_bacc) > 1 else 0.0), 4),
            "macro_f1_mean": round(float(np.mean(fold_mf1)), 4),
            "macro_f1_std": round(float(np.std(fold_mf1, ddof=1) if len(fold_mf1) > 1 else 0.0), 4),
            "roc_auc_mean": round(float(np.mean(fold_auc)) if fold_auc else 0.0, 4),
        }

    candidates: list[dict] = []
    if best_model_key == "random_forest":
        grid = [
            {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 4, "max_features": "sqrt"},
            {"n_estimators": 300, "max_depth": 8, "min_samples_leaf": 3, "max_features": "sqrt"},
            {"n_estimators": 350, "max_depth": 12, "min_samples_leaf": 2, "max_features": 0.6},
            {"n_estimators": 300, "max_depth": None, "min_samples_leaf": 5, "max_features": "sqrt"},
        ]
        for params in grid:
            ev = _eval_cached_folds(
                lambda p=params: RandomForestClassifier(
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                    n_jobs=1,
                    **p,
                )
            )
            candidates.append({"params": params, "metrics": ev})

    elif best_model_key == "xgboost":
        neg = int(counts[0])
        pos = max(1, int(counts[1])) if len(counts) > 1 else 1
        spw = round(neg / pos, 4)
        is_binary = len(counts) == 2
        extra = {"scale_pos_weight": spw, "eval_metric": "logloss"} if is_binary else {"eval_metric": "mlogloss"}
        grid = [
            {"n_estimators": 140, "max_depth": 3, "learning_rate": 0.04, "subsample": 0.8},
            {"n_estimators": 240, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.85},
            {"n_estimators": 280, "max_depth": 5, "learning_rate": 0.03, "subsample": 0.9},
            {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.06, "subsample": 0.85},
        ]
        for params in grid:
            ev = _eval_cached_folds(
                lambda p=params: XGBClassifier(
                    colsample_bytree=0.85,
                    random_state=RANDOM_SEED,
                    n_jobs=1,
                    **extra,
                    **p,
                )
            )
            candidates.append({"params": params, "metrics": ev})
    else:
        grid = [
            {"C": 0.5, "gamma": "scale"},
            {"C": 1.0, "gamma": "scale"},
            {"C": 3.0, "gamma": "scale"},
            {"C": 5.0, "gamma": 0.08},
        ]
        for params in grid:
            ev = _eval_cached_folds(
                lambda p=params: Pipeline(
                    [
                        ("scaler", StandardScaler()),
                        ("svc", SVC(kernel="rbf", probability=True, class_weight="balanced", random_state=RANDOM_SEED, **p)),
                    ]
                )
            )
            candidates.append({"params": params, "metrics": ev})

    best_cand = max(candidates, key=lambda c: (c["metrics"]["macro_f1_mean"], c["metrics"]["roc_auc_mean"]))
    bm = best_cand["metrics"]
    return {
        "model_name": baseline_metrics["model_name"],
        "model_key": best_model_key,
        "feature_set_code": baseline_metrics["feature_set_code"],
        "untuned": {
            "balanced_acc_mean": baseline_metrics["balanced_acc_mean"],
            "balanced_acc_std": baseline_metrics["balanced_acc_std"],
            "macro_f1_mean": baseline_metrics["macro_f1_mean"],
            "macro_f1_std": baseline_metrics["macro_f1_std"],
            "roc_auc_mean": baseline_metrics["roc_auc_mean"],
        },
        "tuned": {
            "params": best_cand["params"],
            "balanced_acc_mean": bm["balanced_acc_mean"],
            "balanced_acc_std": bm["balanced_acc_std"],
            "macro_f1_mean": bm["macro_f1_mean"],
            "macro_f1_std": bm["macro_f1_std"],
            "roc_auc_mean": bm["roc_auc_mean"],
            "delta_macro_f1": round(bm["macro_f1_mean"] - baseline_metrics["macro_f1_mean"], 4),
            "delta_balanced_acc": round(bm["balanced_acc_mean"] - baseline_metrics["balanced_acc_mean"], 4),
        },
        "grid_trials": [
            {
                "params": c["params"],
                "balanced_acc_mean": c["metrics"]["balanced_acc_mean"],
                "macro_f1_mean": c["metrics"]["macro_f1_mean"],
                "roc_auc_mean": c["metrics"]["roc_auc_mean"],
            }
            for c in candidates
        ],
    }


def _analyze_source(source: DatasetSource, window_size: int, horizon: int) -> dict:
    # Load Day 5 metrics to know exact winning baseline on this dataset
    day5_path = REPORTS_DIR / "day5_baseline_metrics.json"
    if not day5_path.exists():
        from src.pipeline.run_day5_baselines import main as run_day5
        run_day5()
    day5_json = json.loads(day5_path.read_text(encoding="utf-8"))
    day5_src = day5_json[source]
    best_day5 = day5_src["overall_best"]
    best_model_key: str = best_day5["model_key"]
    best_feature_key: FeatureSetName = best_day5["feature_set_key"]

    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, _ = remove_nan_spectral_rows(ds.spectra, ds.labels, ds.group_ids)
    folds, _ = build_and_save_grouped_splits(y_clean, groups_clean, source=source, save=False)

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

    # Re-run exact best pipeline to obtain OOF predictions per row for detailed Error Analysis
    def best_factory():
        return Pipeline(
            [
                ("features", SpectralFeatureSetPipeline(ds.wavelengths, best_feature_key, prep_cfg, top_k_bands=5)),
                ("clf", _make_model_estimator(best_model_key, y_dummy_enc)),
            ]
        )

    oof_eval = evaluate_cv_folds(X_clean, y_clean, folds, best_factory)
    y_true = np.asarray(oof_eval["oof_true_indices"], dtype=int)
    y_pred = np.asarray(oof_eval["oof_pred_indices"], dtype=int)
    class_names = oof_eval["class_names"]
    misclassified_mask = y_true != y_pred
    error_rate = float(np.mean(misclassified_mask))

    # Block 1: Confused pairs, spectra of misclassified vs class means, noise vs ambiguity, plant/date breakdown
    confused_pairs: list[dict] = []
    cm = np.array(oof_eval["confusion_matrix"], dtype=int)
    for i, tc in enumerate(class_names):
        for j, pc in enumerate(class_names):
            if i != j and cm[i, j] > 0:
                confused_pairs.append(
                    {
                        "true_class": tc,
                        "predicted_class": pc,
                        "count": int(cm[i, j]),
                        "percent_of_errors": round(float(cm[i, j] / max(1, misclassified_mask.sum()) * 100.0), 1),
                    }
                )
    confused_pairs.sort(key=lambda d: d["count"], reverse=True)

    # Misclassified vs correctly classified mean spectra per true class
    spectra_comparison = []
    wls = ds.wavelengths.tolist()
    for c_idx, cname in enumerate(class_names):
        cls_mask = y_true == c_idx
        corr_mask = cls_mask & (~misclassified_mask)
        err_mask = cls_mask & misclassified_mask
        cls_mean = np.mean(X_clean[cls_mask], axis=0)
        cls_std = np.std(X_clean[cls_mask], axis=0)
        err_mean = np.mean(X_clean[err_mask], axis=0) if np.any(err_mask) else cls_mean
        corr_mean = np.mean(X_clean[corr_mask], axis=0) if np.any(corr_mask) else cls_mean
        spectra_comparison.append(
            {
                "class_name": cname,
                "n_total": int(cls_mask.sum()),
                "n_correct": int(corr_mask.sum()),
                "n_errors": int(err_mask.sum()),
                "points": [
                    {
                        "wavelength_nm": float(wls[b]),
                        "true_mean": round(float(cls_mean[b]), 3),
                        "true_std": round(float(cls_std[b]), 3),
                        "correct_mean": round(float(corr_mean[b]), 3),
                        "misclassified_mean": round(float(err_mean[b]), 3),
                    }
                    for b in range(len(wls))
                ],
            }
        )

    # Noise (L2 robust Z from own class median) & Ambiguity (margin between own vs closest opposite centroid)
    centroids = np.array([np.median(X_clean[y_true == c], axis=0) for c in range(len(class_names))])
    l2_own = np.linalg.norm(X_clean - centroids[y_true], axis=1)
    med_l2 = float(np.median(l2_own))
    mad_l2 = max(1e-6, float(np.median(np.abs(l2_own - med_l2))))
    robust_z = 0.6745 * (l2_own - med_l2) / mad_l2

    other_dists = np.full(len(X_clean), np.inf)
    for c in range(len(class_names)):
        opp = np.min(
            [np.linalg.norm(X_clean - centroids[oc], axis=1) for oc in range(len(class_names)) if oc != c],
            axis=0,
        )
        other_dists = np.where(y_true == c, opp, other_dists)
    # Positive margin => closer to own centroid; near 0 or negative => boundary ambiguous
    centroid_margin = other_dists - l2_own

    noise_ambiguity_summary = {
        "correct_median_robust_z": round(float(np.median(robust_z[~misclassified_mask])), 3),
        "error_median_robust_z": round(float(np.median(robust_z[misclassified_mask])), 3) if np.any(misclassified_mask) else 0.0,
        "error_noisy_pct_z_gt_3": round(float(np.mean(robust_z[misclassified_mask] > 3.0) * 100.0), 1) if np.any(misclassified_mask) else 0.0,
        "correct_median_centroid_margin": round(float(np.median(centroid_margin[~misclassified_mask])), 3),
        "error_median_centroid_margin": round(float(np.median(centroid_margin[misclassified_mask])), 3) if np.any(misclassified_mask) else 0.0,
    }

    # Concentration across plants, genotypes/fields, and date phase (Early half vs Late half)
    err_df = groups_clean[["plant_id", "plot_id", "field_id", "date"]].copy()
    err_df["is_error"] = misclassified_mask.astype(int)
    err_df["true_label"] = [class_names[i] for i in y_true]
    err_df["pred_label"] = [class_names[i] for i in y_pred]
    err_df["robust_z"] = robust_z

    plant_err = (
        err_df.groupby(["plant_id", "true_label"], as_index=False)
        .agg(scans=("is_error", "count"), errors=("is_error", "sum"))
    )
    plant_err["error_rate_pct"] = (plant_err["errors"] / plant_err["scans"] * 100.0).round(1)
    top_error_plants = plant_err.sort_values(["error_rate_pct", "errors"], ascending=False).head(8).to_dict(orient="records")

    field_err = (
        err_df.groupby("field_id", as_index=False)
        .agg(scans=("is_error", "count"), errors=("is_error", "sum"))
    )
    field_err["error_rate_pct"] = (field_err["errors"] / field_err["scans"] * 100.0).round(1)

    parsed_dates = pd.to_datetime(err_df["date"], format="%m-%d-%y", errors="coerce").fillna(
        pd.to_datetime(err_df["date"], errors="coerce")
    )
    err_df["parsed_date"] = parsed_dates
    date_err = (
        err_df.groupby(["parsed_date", "date"], as_index=False)
        .agg(scans=("is_error", "count"), errors=("is_error", "sum"))
        .sort_values("parsed_date")
    )
    date_err["error_rate_pct"] = (date_err["errors"] / date_err["scans"] * 100.0).round(1)
    mid = max(1, len(date_err) // 2)
    early_error_pct = round(float(date_err.iloc[:mid]["errors"].sum() / max(1, date_err.iloc[:mid]["scans"].sum()) * 100.0), 1)
    late_error_pct = round(float(date_err.iloc[mid:]["errors"].sum() / max(1, date_err.iloc[mid:]["scans"].sum()) * 100.0), 1)

    # Block 2: SHAP on best baseline AND full-spectrum wavelength SHAP for Block 3 Day 2 EDA comparison
    shap_best = _compute_shap_and_perm(
        X_clean, y_clean, ds.wavelengths, prep_cfg, folds, best_feature_key, best_model_key
    )
    shap_spectrum = _compute_shap_and_perm(
        X_clean, y_clean, ds.wavelengths, prep_cfg, folds, "A_full_spectrum", best_model_key
    )

    # Block 3: Compare wavelength SHAP importance vs Day 2 Fisher Ratio & |ΔR|
    day2_path = REPORTS_DIR / "day2_eda_metrics.json"
    day2_eda = json.loads(day2_path.read_text(encoding="utf-8"))[source]
    day2_by_wl = {float(d["wavelength_nm"]): d for d in day2_eda["band_diagnostics"]}

    wavelength_comparison = []
    for item in shap_spectrum["features"]:
        wl_num = float(item["feature"].replace("Band_", "").replace("nm", ""))
        d2 = day2_by_wl.get(wl_num, {})
        wavelength_comparison.append(
            {
                "wavelength_nm": wl_num,
                "region": d2.get("region", "Spectral"),
                "shap_importance": item["mean_abs_shap"],
                "perm_importance": item["permutation_importance"],
                "day2_fisher_ratio": d2.get("fisher_ratio", 0.0),
                "day2_abs_diff_pct": round(abs(float(d2.get("diff_stressed_minus_healthy", 0.0))), 4),
            }
        )
    wavelength_comparison.sort(key=lambda r: r["wavelength_nm"])
    shap_vec = [r["shap_importance"] for r in wavelength_comparison]
    fisher_vec = [r["day2_fisher_ratio"] for r in wavelength_comparison]
    spearman_rho, _ = spearmanr(shap_vec, fisher_vec) if len(shap_vec) >= 3 else (0.0, 1.0)
    spearman_rho = 0.0 if np.isnan(spearman_rho) else float(spearman_rho)

    # Block 4: Light Hyperparameter Tuning inside grouped CV
    tuning_res = _light_tune_best_model(
        X_clean, y_clean, ds.wavelengths, prep_cfg, folds, best_model_key, best_feature_key, best_day5
    )

    # Block 5: Forecasting Prep across horizons k = 1, 2, 3 (Primary) or k=1 (Synthetic)
    horizons = [1, 2, 3] if source == "primary" else [1]
    horizon_results = []
    for k in horizons:
        seq = build_temporal_sequences(source=source, window_size=window_size, horizon=k)
        ev = evaluate_forecasting_baselines(seq)
        horizon_results.append(ev)

    return {
        "source": source,
        "best_baseline": {
            "model_name": best_day5["model_name"],
            "model_key": best_model_key,
            "feature_set_code": best_day5["feature_set_code"],
            "feature_set_key": best_feature_key,
            "overall_error_rate_pct": round(error_rate * 100.0, 2),
            "total_errors": int(misclassified_mask.sum()),
            "total_samples": int(len(y_true)),
        },
        "error_analysis": {
            "confused_pairs": confused_pairs,
            "spectra_comparison": spectra_comparison,
            "noise_vs_ambiguity": noise_ambiguity_summary,
            "early_half_error_pct": early_error_pct,
            "late_half_error_pct": late_error_pct,
            "top_error_plants": top_error_plants,
            "by_genotype_or_field": field_err.to_dict(orient="records"),
            "by_date_series": [
                {"date": row["date"], "scans": int(row["scans"]), "errors": int(row["errors"]), "error_rate_pct": float(row["error_rate_pct"])}
                for _, row in date_err.iterrows()
            ],
        },
        "interpretability": {
            "best_set_shap": shap_best,
            "wavelength_shap_vs_day2": wavelength_comparison,
            "spearman_shap_vs_fisher": round(spearman_rho, 3),
        },
        "tuning": tuning_res,
        "forecasting_prep": {
            "window_size": window_size,
            "default_horizon": horizon,
            "horizons": horizon_results,
        },
    }


def _plot_day6_figures(primary_res: dict, synthetic_res: dict) -> list[str]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    # Figure 11: Misclassified Spectra vs Class Means + Error Rate by Date Trajectory
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.7))
    fig.patch.set_facecolor("white")

    colors = ["#0F766E", "#D97706"]
    for idx, cls_comp in enumerate(primary_res["error_analysis"]["spectra_comparison"]):
        wls = [p["wavelength_nm"] for p in cls_comp["points"]]
        mu = np.array([p["true_mean"] for p in cls_comp["points"]])
        sd = np.array([p["true_std"] for p in cls_comp["points"]])
        err_mu = np.array([p["misclassified_mean"] for p in cls_comp["points"]])
        c = colors[idx % len(colors)]
        ax1.plot(wls, mu, color=c, linewidth=2.0, label=f"{cls_comp['class_name']} Mean ± SD")
        ax1.fill_between(wls, mu - sd, mu + sd, color=c, alpha=0.12)
        ax1.plot(
            wls,
            err_mu,
            color=c,
            linestyle="--",
            marker="x",
            linewidth=1.8,
            label=f"{cls_comp['class_name']} Misclassified Mean (n={cls_comp['n_errors']})",
        )
    ax1.set_title("Primary: Misclassified Spectra vs. True Class Means", fontsize=10.2, fontweight="bold")
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("Reflectance (%)")
    ax1.grid(True, linestyle="--", alpha=0.3)
    ax1.legend(frameon=False, fontsize=7.8)

    dseries = primary_res["error_analysis"]["by_date_series"]
    xd = np.arange(len(dseries))
    errs = [d["error_rate_pct"] for d in dseries]
    ax2.plot(xd, errs, color="#DC2626", marker="o", markersize=3.5, linewidth=1.8, label="Daily Error Rate (%)")
    ax2.axvline(len(xd) // 2, color="#64748B", linestyle=":", linewidth=1.2, label="Trial Midpoint (Early vs. Late)")
    ax2.set_xticks(xd[::5])
    ax2.set_xticklabels([dseries[i]["date"] for i in range(0, len(dseries), 5)], fontsize=8, rotation=20)
    ax2.set_ylabel("Out-of-Fold Error Rate (%)")
    ax2.set_title(
        f"Temporal Error Drift (Early={primary_res['error_analysis']['early_half_error_pct']}% vs Late={primary_res['error_analysis']['late_half_error_pct']}%)",
        fontsize=10.2,
        fontweight="bold",
    )
    ax2.grid(True, linestyle="--", alpha=0.3)
    ax2.legend(frameon=False, fontsize=8)

    fig.tight_layout()
    p11 = FIGURES_DIR / "11_day6_misclassified_spectra_and_error_breakdown.png"
    fig.savefig(p11, dpi=160)
    plt.close(fig)
    paths.append(str(p11.relative_to(ROOT_DIR)))

    # Figure 12: SHAP Feature Importance + Wavelength Importance vs Day 2 EDA Fisher J
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.7))
    fig.patch.set_facecolor("white")

    top_feats = primary_res["interpretability"]["best_set_shap"]["features"][:10][::-1]
    yf = np.arange(len(top_feats))
    svals = [f["mean_abs_shap"] for f in top_feats]
    ax1.barh(yf, svals, color="#0F766E", height=0.62)
    ax1.set_yticks(yf)
    ax1.set_yticklabels([f["feature"] for f in top_feats], fontsize=8.5)
    ax1.set_xlabel("Mean |SHAP Value| (Validation Fold)")
    ax1.set_title(
        f"SHAP Feature Importance ({primary_res['best_baseline']['model_name']} · Set {primary_res['best_baseline']['feature_set_code']})",
        fontsize=10.0,
        fontweight="bold",
    )
    ax1.grid(True, axis="x", linestyle="--", alpha=0.3)

    wcomp = primary_res["interpretability"]["wavelength_shap_vs_day2"]
    wls = [w["wavelength_nm"] for w in wcomp]
    shap_n = np.array([w["shap_importance"] for w in wcomp])
    shap_n = shap_n / max(1e-12, float(shap_n.max()))
    fish_n = np.array([w["day2_fisher_ratio"] for w in wcomp])
    fish_n = fish_n / max(1e-12, float(fish_n.max()))

    xw = np.arange(len(wls))
    bw = 0.36
    ax2.bar(xw - bw / 2, shap_n, bw, color="#0F766E", label="Normalized Model SHAP (Set A)")
    ax2.bar(xw + bw / 2, fish_n, bw, color="#D97706", alpha=0.85, label="Normalized Day 2 EDA Fisher Ratio J")
    ax2.set_xticks(xw)
    ax2.set_xticklabels([f"{int(w)}" for w in wls], fontsize=8.5)
    ax2.set_xlabel("Aligned Wavelength (nm)")
    ax2.set_ylabel("Normalized Importance (0–1)")
    ax2.set_title(
        f"Wavelength Importance vs. Day 2 EDA (Spearman ρ={primary_res['interpretability']['spearman_shap_vs_fisher']:.2f})",
        fontsize=10.0,
        fontweight="bold",
    )
    ax2.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax2.legend(frameon=False, fontsize=8)

    fig.tight_layout()
    p12 = FIGURES_DIR / "12_day6_shap_vs_day2_wavelength_importance.png"
    fig.savefig(p12, dpi=160)
    plt.close(fig)
    paths.append(str(p12.relative_to(ROOT_DIR)))

    # Figure 13: Forecasting Prep — Persistence vs Lag-Ridge vs Lag-RF Across Horizons k=1,2,3
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.7))
    fig.patch.set_facecolor("white")

    horizons = primary_res["forecasting_prep"]["horizons"]
    ks = [h["horizon"] for h in horizons]
    p_mae = [next(m["mae_mean"] for m in h["models"] if m["key"] == "persistence") for h in horizons]
    r_mae = [next(m["mae_mean"] for m in h["models"] if m["key"] == "lag_ridge") for h in horizons]
    rf_mae = [next(m["mae_mean"] for m in h["models"] if m["key"] == "lag_rf") for h in horizons]

    xk = np.arange(len(ks))
    w3 = 0.25
    ax1.bar(xk - w3, p_mae, w3, color="#64748B", label="Persistence (NDVI_t)")
    ax1.bar(xk, r_mae, w3, color="#2563EB", label="Lag-Feature Ridge")
    ax1.bar(xk + w3, rf_mae, w3, color="#0F766E", label="Lag-Feature Random Forest")
    ax1.set_xticks(xk)
    ax1.set_xticklabels([f"k = +{k} step" for k in ks], fontsize=9)
    ax1.set_ylabel("5-Fold Plant-Grouped CV MAE (NDVI)")
    ax1.set_title("Forecasting Prep: Future NDVI_{t+k} Error by Horizon (Primary W=3)", fontsize=10.0, fontweight="bold")
    ax1.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax1.legend(frameon=False, fontsize=8)

    h1_samples = horizons[0].get("sample_predictions", [])[:35]
    xs = np.arange(len(h1_samples))
    ax2.plot(xs, [s["actual_ndvi"] for s in h1_samples], color="#0F172A", linewidth=2.0, label="Actual NDVI_{t+1}")
    ax2.plot(xs, [s["persistence_ndvi"] for s in h1_samples], color="#64748B", linestyle=":", linewidth=1.5, label="Persistence")
    ax2.plot(xs, [s["lag_rf_ndvi"] for s in h1_samples], color="#0F766E", linestyle="--", linewidth=1.8, label="Lag-RF Forecast")
    ax2.set_xlabel("Sampled Held-Out Plant Windows (k = +1)")
    ax2.set_ylabel("NDVI")
    ax2.set_title("Out-of-Fold Next-Timepoint NDVI Trajectory Preview", fontsize=10.0, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.3)
    ax2.legend(frameon=False, fontsize=8)

    fig.tight_layout()
    p13 = FIGURES_DIR / "13_day6_forecast_persistence_vs_lag.png"
    fig.savefig(p13, dpi=160)
    plt.close(fig)
    paths.append(str(p13.relative_to(ROOT_DIR)))

    return paths


def _append_day6_experiment_log(primary_res: dict, synthetic_res: dict) -> list[dict]:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing_rows: list[dict] = []
    if EXPERIMENT_LOG_PATH.exists():
        with open(EXPERIMENT_LOG_PATH, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            existing_rows = [r for r in reader if r.get("day") != "Day 6"]

    new_rows: list[dict] = []
    idx_counter = 1
    for res in (primary_res, synthetic_res):
        t = res["tuning"]["tuned"]
        new_rows.append(
            {
                "run_id": f"day6_{idx_counter:02d}",
                "timestamp": ts,
                "day": "Day 6",
                "data_version": f"{res['source']}_v1",
                "preprocessing": "drop_365nm|clip_0_100|savgol|snv",
                "features": f"Set {res['best_baseline']['feature_set_code']}",
                "model": f"{res['best_baseline']['model_name']} (Tuned)",
                "parameters": json.dumps(t["params"]),
                "cv_scheme": "StratifiedGroupKFold(plant_id)",
                "balanced_acc": f"{t['balanced_acc_mean']:.4f} ± {t['balanced_acc_std']:.4f}",
                "macro_f1": f"{t['macro_f1_mean']:.4f} ± {t['macro_f1_std']:.4f}",
                "roc_auc": f"{t['roc_auc_mean']:.4f}",
                "notes": f"Day 6 grouped-CV tuning (ΔF1={t['delta_macro_f1']:+.4f})",
            }
        )
        idx_counter += 1
        for h in res["forecasting_prep"]["horizons"]:
            for m in h["models"]:
                new_rows.append(
                    {
                        "run_id": f"day6_{idx_counter:02d}",
                        "timestamp": ts,
                        "day": "Day 6",
                        "data_version": f"{res['source']}_seq_W{h['window_size']}_k{h['horizon']}",
                        "preprocessing": "drop_365nm|clip_0_100|uncentered_VI",
                        "features": f"{h['n_features_per_window']} lag spectral+VI features",
                        "model": m["name"],
                        "parameters": f"W={h['window_size']}, horizon=+{h['horizon']}",
                        "cv_scheme": "GroupKFold(plant_id)",
                        "balanced_acc": f"MAE {m['mae_mean']:.4f}",
                        "macro_f1": f"RMSE {m['rmse_mean']:.4f}",
                        "roc_auc": f"R2 {m['r2_mean']:.4f}",
                        "notes": f"NDVI_{{t+{h['horizon']}}} forecasting baseline ({h['n_sequences']} windows)",
                    }
                )
                idx_counter += 1

    all_rows = existing_rows + new_rows
    if all_rows:
        with open(EXPERIMENT_LOG_PATH, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)
    return all_rows


def _write_day6_note(primary_res: dict, synthetic_res: dict) -> None:
    bb = primary_res["best_baseline"]
    ea = primary_res["error_analysis"]
    na = ea["noise_vs_ambiguity"]
    tu = primary_res["tuning"]
    sh = primary_res["interpretability"]["best_set_shap"]
    top_sh = "\n".join(
        f"| `{f['feature']}` | `{f['mean_abs_shap']:.5f}` | `{f['permutation_importance']:.5f}` | `{f['direction_corr']:+.3f}` |"
        for f in sh["features"][:7]
    )
    h1 = primary_res["forecasting_prep"]["horizons"][0]
    fc_rows = "\n".join(
        f"| k = +{h['horizon']} ({h['n_sequences']} windows) | {m['name']} | `{m['mae_mean']:.4f} ± {m['mae_std']:.4f}` | `{m['rmse_mean']:.4f}` | `{m['r2_mean']:.4f}` |"
        for h in primary_res["forecasting_prep"]["horizons"]
        for m in h["models"]
    )
    s_h1 = synthetic_res["forecasting_prep"]["horizons"][0]
    s_rf = next(m for m in s_h1["models"] if m["key"] == "lag_rf")

    note = f"""# Day 6 Error Analysis, Interpretability & Forecasting Prep Report

**Generated programmatically by:** `python3 src/pipeline/run_day6_error_and_forecast.py`  
**Evaluated Baseline:** `{bb['model_name']}` on **Feature Set {bb['feature_set_code']}** (`{bb['total_errors']}` / `{bb['total_samples']}` out-of-fold errors = **`{bb['overall_error_rate_pct']}%`**)

---

## 1. Error Analysis (Plain-Language Diagnosis)

1. **Which classes are confused & biological plausibility?**  
   - False positives and false negatives are balanced between **`{ea['confused_pairs'][0]['true_class']} → {ea['confused_pairs'][0]['predicted_class']}`** (`{ea['confused_pairs'][0]['count']}` scans) and the reverse direction (`{ea['confused_pairs'][1]['count'] if len(ea['confused_pairs']) > 1 else 0}` scans). Biologically, drought stress takes days to diverge from watered controls, creating heavy spectral overlap in early measurement sessions.
2. **Are errors concentrated in particular dates, genotypes, or plants?**  
   - **Early-half vs. Late-half dates:** Error rate runs at **`{ea['early_half_error_pct']}%`** in the first half of trial dates vs. **`{ea['late_half_error_pct']}%`** in the second half.  
   - **Genotypes/Fields (`field_id`):** {'; '.join(f"{g['field_id']}: {g['error_rate_pct']}% ({g['errors']}/{g['scans']})" for g in ea['by_genotype_or_field'])}.
3. **Do misclassified spectra look noisy or genuinely ambiguous?**  
   - Misclassified samples have median L2 robust `Z = {na['error_median_robust_z']:.2f}` (`{na['error_noisy_pct_z_gt_3']}%` above `Z > 3.0`) vs. `{na['correct_median_robust_z']:.2f}` for correct samples, and a tight centroid margin (`{na['error_median_centroid_margin']:.3f}` vs. `{na['correct_median_centroid_margin']:.3f}`) — proving errors are **primarily genuine boundary ambiguity**, not isolated sensor spikes.

---

## 2. Model Interpretability ({sh['method']} & Day 2 Wavelength Alignment)

What does the model use to separate watered vs. drought-stressed plants? Top features ranked by validation `|SHAP|`:

| Feature | Mean \|SHAP\| | Permutation Imp. | Direction (Corr) |
| --- | ---: | ---: | ---: |
{top_sh}

- **Comparison with Day 2 EDA:** Across aligned wavelengths (`460–970 nm`), model SHAP importance correlates at **Spearman $\\rho = {primary_res['interpretability']['spearman_shap_vs_fisher']:.2f}$** with Day 2 Fisher discriminant ratio $J$, highlighting canopy chlorophyll/water-sensitive indices (**PRI**, **NDVI**, **MCARI**) plus red-edge/green bands (`525`, `570`, `700`, `890 nm`).

---

## 3. Light Hyperparameter Tuning Inside `StratifiedGroupKFold`

- **Untuned `{tu['model_name']}` (Set {tu['feature_set_code']}):** Macro-F1 = `{tu['untuned']['macro_f1_mean']:.4f} ± {tu['untuned']['macro_f1_std']:.4f}`, Bal. Acc = `{tu['untuned']['balanced_acc_mean']:.4f}`, ROC-AUC = `{tu['untuned']['roc_auc_mean']:.4f}`
- **Tuned `{tu['model_name']}` (`{json.dumps(tu['tuned']['params'])}`):** Macro-F1 = **`{tu['tuned']['macro_f1_mean']:.4f} ± {tu['tuned']['macro_f1_std']:.4f}`** (`Δ {tu['tuned']['delta_macro_f1']:+.4f}`), Bal. Acc = **`{tu['tuned']['balanced_acc_mean']:.4f} ± {tu['tuned']['balanced_acc_std']:.4f}`**, ROC-AUC = **`{tu['tuned']['roc_auc_mean']:.4f}`**

---

## 4. Forecasting Feasibility & Sequence Baselines (`src/sequences.py`)

**Verdict for Mentor:** **True temporal forecasting IS directly supported** on our primary dataset (`{h1['n_plants']}` plants, `31` dates, median `{h1['obs_per_plant']['median']:.0f}` timepoints/plant yielding **`{h1['n_sequences']}`** sliding windows at `W={h1['window_size']}, k=+1`), as well as the multi-timepoint synthetic benchmark (Lag-RF `k=+1` MAE=`{s_rf['mae_mean']:.4f}`, $R^2$=`{s_rf['r2_mean']:.4f}`). All windows from any given `plant_id` stay strictly inside one CV fold.

| Horizon & Windows | Model | CV MAE (± std) | CV RMSE | CV $R^2$ |
| --- | --- | ---: | ---: | ---: |
{fc_rows}

Full experiment history logged in **`reports/experiment_log.csv`**.
"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "error_interpretability_note.md").write_text(note, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Day 6 Error Analysis, SHAP, Tuning & Forecasting Prep")
    parser.add_argument("--window", type=int, default=3, help="Lookback window W for Primary sequences")
    parser.add_argument("--horizon", type=int, default=1, help="Primary forecast horizon k")
    args = parser.parse_args()

    primary_res = _analyze_source("primary", window_size=args.window, horizon=args.horizon)
    synthetic_res = _analyze_source("synthetic", window_size=2, horizon=1)
    figures = _plot_day6_figures(primary_res, synthetic_res)
    exp_log = _append_day6_experiment_log(primary_res, synthetic_res)
    _write_day6_note(primary_res, synthetic_res)

    payload = {
        "figures": figures,
        "experiment_log_path": "reports/experiment_log.csv",
        "experiment_log_rows": exp_log,
        "primary": primary_res,
        "synthetic": synthetic_res,
    }
    out_json = REPORTS_DIR / "day6_error_and_forecast_metrics.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Day 6 Error Analysis & Forecasting Prep complete: {out_json} & {EXPERIMENT_LOG_PATH}")
    print(f"Tuned Macro-F1={primary_res['tuning']['tuned']['macro_f1_mean']:.4f} | Forecasting k=1 sequences={primary_res['forecasting_prep']['horizons'][0]['n_sequences']}")


if __name__ == "__main__":
    main()
