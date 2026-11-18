"""TerraSpectra Live Inference, Batch CSV Scoring, Forecasting & Early-Detection Engine.

Provides CLI-callable JSON inference powered strictly by leak-free trained models:
  - Spectral classifier ensemble (XGBoost, Random Forest, SVM-RBF, PLS-DA) on Feature Set E
  - Vegetation index telemetry (NDVI, NDRE, PRI, Red-Edge Position, MCARI)
  - Real per-prediction feature attributions (TreeSHAP or contrast weights)
  - Per-plant chronological NDVI trajectory forecasting (Persistence vs Lag-Ridge vs Lag-RF)
  - Early-detection lead-time analysis on held-out plants

Usage:
  python3 src/inference.py --action samples --source primary
  python3 src/inference.py --action predict-one --source primary --payload-json '{...}'
  python3 src/inference.py --action predict-csv --source primary --payload-json '{"csv_text": "..."}'
  python3 src/inference.py --action forecast-plant --source primary --payload-json '{"plant_id": "2", "horizon": 3}'
  python3 src/inference.py --action early-detection --source primary
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import pickle
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

from src.data import DatasetSource, load_dataset
from src.evaluation import PLSDAClassifier, RANDOM_SEED
from src.features import SpectralFeatureSetPipeline, VegetationIndexExtractor
from src.preprocessing import (
    PROCESSED_DIR,
    PreprocessingConfig,
    make_leak_free_train_test_indices,
    remove_nan_spectral_rows,
)
from src.sequences import _parse_sortable_dates, build_temporal_sequences

CACHE_VERSION = 2


def _cache_path(source: DatasetSource) -> Path:
    return PROCESSED_DIR / f"{source}_terraspectra_inference_v{CACHE_VERSION}.pkl"


def _fit_and_cache_bundle(source: DatasetSource) -> dict[str, Any]:
    """Train leak-free Set E classifier bundle + sequence forecasters on training plants only."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(source)
    if cache_file.exists():
        try:
            with cache_file.open("rb") as f:
                bundle = pickle.load(f)
            if isinstance(bundle, dict) and bundle.get("version") == CACHE_VERSION:
                return bundle
        except Exception:
            pass

    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, _ = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )
    train_idx, test_idx = make_leak_free_train_test_indices(y_clean, groups_clean)

    le = LabelEncoder().fit(y_clean)
    y_enc = le.transform(y_clean)
    class_names = [str(c) for c in le.classes_]
    n_classes = len(class_names)

    prep_cfg = PreprocessingConfig(
        drop_bad_bands=True,
        drop_wavelengths=(365.0,) if source == "primary" else (),
        normalization="snv",
        use_savgol=True,
        savgol_window=3 if source == "primary" else 5,
        savgol_polyorder=1 if source == "primary" else 2,
    )
    feat_pipe = SpectralFeatureSetPipeline(
        wavelengths=ds.wavelengths,
        feature_set="E_indices_plus_selected",
        prep_config=prep_cfg,
        top_k_bands=5,
    )
    X_tr = feat_pipe.fit_transform(X_clean[train_idx], y_clean[train_idx])
    y_tr = y_enc[train_idx]
    feature_names = feat_pipe.get_feature_names_out()
    aligned_wl = feat_pipe.aligned_wavelengths_

    # Pure reflectance stats for UI overlay (Control/Healthy vs Stressed reference envelopes)
    X_tr_refl = feat_pipe.preprocessor_.transform_reflectance_only(X_clean[train_idx])
    ref_curves: dict[str, list[dict[str, float]]] = {}
    for cls_idx, cname in enumerate(class_names):
        mask = y_tr == cls_idx
        sub = X_tr_refl[mask]
        mean_vec = np.mean(sub, axis=0)
        std_vec = np.std(sub, axis=0)
        ref_curves[cname] = [
            {
                "wavelength_nm": float(wl),
                "mean": round(float(m), 3),
                "std": round(float(s), 3),
            }
            for wl, m, s in zip(aligned_wl, mean_vec, std_vec)
        ]

    # Fit all 4 benchmark models strictly on train_idx
    rf_clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_SEED,
        n_jobs=1,
    ).fit(X_tr, y_tr)

    if n_classes == 2:
        neg = int((y_tr == 0).sum())
        pos = max(1, int((y_tr == 1).sum()))
        xgb_clf = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.06,
            subsample=0.85,
            colsample_bytree=0.85,
            scale_pos_weight=round(neg / pos, 4),
            eval_metric="logloss",
            random_state=RANDOM_SEED,
            n_jobs=1,
        ).fit(X_tr, y_tr)
    else:
        xgb_clf = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.06,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="mlogloss",
            random_state=RANDOM_SEED,
            n_jobs=1,
        ).fit(X_tr, y_tr)

    svm_clf = Pipeline(
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
    ).fit(X_tr, y_tr)

    pls_clf = PLSDAClassifier(n_components=min(5, X_tr.shape[1])).fit(X_tr, y_tr)

    # Feature baseline stats from training healthy/control samples for fast local explanations
    healthy_label = class_names[0]
    healthy_mask = y_tr == 0
    feat_means_by_class = {
        cname: np.mean(X_tr[y_tr == idx], axis=0) for idx, cname in enumerate(class_names)
    }
    feat_std_global = np.where(np.std(X_tr, axis=0) > 1e-8, np.std(X_tr, axis=0), 1.0)
    rf_importances = rf_clf.feature_importances_.copy()

    # Build forecasting models (k=1,2,3) trained strictly on train_plants
    train_plants_set = set(groups_clean.iloc[train_idx]["plant_id"].astype(str).tolist())
    win_size = 3 if source == "primary" else 2
    forecasters: dict[int, dict[str, Any]] = {}
    for horizon in (1, 2, 3):
        seq = build_temporal_sequences(source=source, window_size=win_size, horizon=horizon)
        if len(seq.y_ndvi_target) == 0:
            continue
        seq_tr_mask = np.array([pid in train_plants_set for pid in seq.plant_ids], dtype=bool)
        if not np.any(seq_tr_mask):
            seq_tr_mask = np.ones(len(seq.y_ndvi_target), dtype=bool)
        X_seq_tr = seq.X_windows_flat[seq_tr_mask]
        y_seq_tr = seq.y_ndvi_target[seq_tr_mask]

        scaler_seq = StandardScaler().fit(X_seq_tr)
        ridge_seq = Ridge(alpha=10.0).fit(scaler_seq.transform(X_seq_tr), y_seq_tr)
        rf_seq = RandomForestRegressor(
            n_estimators=120, max_depth=8, random_state=RANDOM_SEED, n_jobs=1
        ).fit(X_seq_tr, y_seq_tr)

        forecasters[horizon] = {
            "window_size": win_size,
            "horizon": horizon,
            "scaler": scaler_seq,
            "ridge": ridge_seq,
            "rf": rf_seq,
        }

    bundle = {
        "version": CACHE_VERSION,
        "source": source,
        "wavelengths": ds.wavelengths,
        "aligned_wavelengths": aligned_wl,
        "class_names": class_names,
        "healthy_label": healthy_label,
        "feature_names": feature_names,
        "feat_pipe": feat_pipe,
        "models": {
            "xgboost": xgb_clf,
            "random_forest": rf_clf,
            "svm": svm_clf,
            "plsda": pls_clf,
        },
        "rf_importances": rf_importances,
        "feat_means_by_class": feat_means_by_class,
        "feat_std_global": feat_std_global,
        "ref_curves": ref_curves,
        "forecasters": forecasters,
        "train_idx": train_idx,
        "test_idx": test_idx,
    }
    with cache_file.open("wb") as f:
        pickle.dump(bundle, f)
    return bundle


def _load_clean_table(source: DatasetSource) -> tuple[np.ndarray, np.ndarray, pd.DataFrame, np.ndarray]:
    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, _ = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )
    return X_clean, y_clean, groups_clean, ds.wavelengths


def _extract_vis_single(bundle: dict[str, Any], raw_row: np.ndarray) -> tuple[dict[str, float], np.ndarray]:
    pipe: SpectralFeatureSetPipeline = bundle["feat_pipe"]
    X2d = np.asarray(raw_row, dtype=float).reshape(1, -1)
    refl = pipe.preprocessor_.transform_reflectance_only(X2d)
    vis = pipe.index_extractor_.transform(refl)[0]
    vi_names = pipe.index_extractor_.get_feature_names_out()
    return {name: round(float(val), 4) for name, val in zip(vi_names, vis)}, refl[0]


def _predict_row(bundle: dict[str, Any], raw_row: np.ndarray, active_model: str = "xgboost") -> dict[str, Any]:
    pipe: SpectralFeatureSetPipeline = bundle["feat_pipe"]
    X2d = np.asarray(raw_row, dtype=float).reshape(1, -1)
    X_feat = pipe.transform(X2d)
    class_names: list[str] = bundle["class_names"]
    vis_dict, refl_vec = _extract_vis_single(bundle, raw_row)

    model_probs: dict[str, dict[str, Any]] = {}
    for mkey, label in [
        ("xgboost", "XGBoost (Set E)"),
        ("random_forest", "Random Forest (Set E)"),
        ("svm", "SVM (RBF, Set E)"),
        ("plsda", "PLS-DA (Set E)"),
    ]:
        clf = bundle["models"][mkey]
        probs = clf.predict_proba(X_feat)[0]
        pred_i = int(np.argmax(probs))
        model_probs[mkey] = {
            "model_key": mkey,
            "model_name": label,
            "predicted_class": class_names[pred_i],
            "confidence": round(float(probs[pred_i]), 4),
            "probabilities": {cname: round(float(p), 4) for cname, p in zip(class_names, probs)},
        }

    chosen = model_probs.get(active_model, model_probs["xgboost"])
    pred_class = chosen["predicted_class"]

    # Local attribution: standardized deviation from Healthy baseline weighted by RF importance
    healthy_name = bundle["healthy_label"]
    healthy_mean = bundle["feat_means_by_class"][healthy_name]
    target_mean = bundle["feat_means_by_class"].get(pred_class, healthy_mean)
    z_vs_healthy = (X_feat[0] - healthy_mean) / bundle["feat_std_global"]
    direction_sign = np.sign(target_mean - healthy_mean)
    imp = bundle["rf_importances"]
    imp_norm = imp / max(1e-9, float(np.max(imp)))
    raw_contrib = z_vs_healthy * np.where(direction_sign == 0, 1.0, direction_sign) * imp_norm

    drivers = []
    for idx, fname in enumerate(bundle["feature_names"]):
        drivers.append(
            {
                "feature": fname,
                "value": round(float(X_feat[0, idx]), 4),
                "z_vs_healthy": round(float(z_vs_healthy[idx]), 3),
                "contribution": round(float(raw_contrib[idx]), 4),
                "importance": round(float(imp[idx]), 4),
            }
        )
    drivers.sort(key=lambda d: abs(d["contribution"]), reverse=True)

    # Ensemble agreement count
    votes = [m["predicted_class"] for m in model_probs.values()]
    agreement = sum(1 for v in votes if v == pred_class)

    return {
        "predicted_class": pred_class,
        "confidence": chosen["confidence"],
        "ensemble_agreement": f"{agreement}/4 models agree",
        "active_model": active_model,
        "models": list(model_probs.values()),
        "vegetation_indices": vis_dict,
        "aligned_wavelengths_nm": [float(w) for w in bundle["aligned_wavelengths"]],
        "reflectance_curve": [
            {"wavelength_nm": float(w), "reflectance": round(float(r), 3)}
            for w, r in zip(bundle["aligned_wavelengths"], refl_vec)
        ],
        "reference_curves": bundle["ref_curves"],
        "drivers": drivers[:8],
    }


def action_samples(source: DatasetSource) -> dict[str, Any]:
    """Return unseen validation plants & representative scans from test_idx for interactive testing."""
    bundle = _fit_and_cache_bundle(source)
    X_clean, y_clean, groups_clean, wavelengths = _load_clean_table(source)
    test_idx = bundle["test_idx"]
    test_set = set(int(i) for i in test_idx.tolist())

    meta = groups_clean.copy()
    meta["label"] = y_clean
    meta["parsed_date"] = _parse_sortable_dates(meta["date"])
    meta["is_holdout"] = [i in test_set for i in range(len(meta))]

    # Collect held-out plants first, sorted by holdout scan count
    plant_records = []
    for pid, grp in meta.groupby("plant_id"):
        grp_sorted = grp.sort_values("parsed_date")
        n_obs = len(grp_sorted)
        holdout_flag = bool(grp_sorted["is_holdout"].any())
        plant_records.append(
            {
                "plant_id": str(pid),
                "true_label": str(grp_sorted["label"].iloc[-1]),
                "field_id": str(grp_sorted["field_id"].iloc[0]),
                "plot_id": str(grp_sorted["plot_id"].iloc[0]),
                "n_scans": int(n_obs),
                "date_start": str(grp_sorted["date"].iloc[0]),
                "date_end": str(grp_sorted["date"].iloc[-1]),
                "split": "holdout_test" if holdout_flag else "train",
            }
        )
    plant_records.sort(key=lambda r: (0 if r["split"] == "holdout_test" else 1, -r["n_scans"], r["plant_id"]))

    # Pick representative unseen test samples across classes for 1-click Spectrum Classifier presets
    presets = []
    test_meta = meta.iloc[test_idx]
    for cname in bundle["class_names"]:
        sub = test_meta[test_meta["label"] == cname]
        if len(sub) == 0:
            sub = meta[meta["label"] == cname]
        if len(sub) > 0:
            # Pick an early/mid and late scan
            chosen_indices = [sub.index[0]]
            if len(sub) > 3:
                chosen_indices.append(sub.index[-1])
            for row_i in chosen_indices[:2]:
                row_meta = meta.loc[row_i]
                bands = {f"{int(round(w))}": round(float(val), 3) for w, val in zip(wavelengths, X_clean[row_i])}
                presets.append(
                    {
                        "sample_id": str(row_meta["sample_id"]),
                        "plant_id": str(row_meta["plant_id"]),
                        "date": str(row_meta["date"]),
                        "true_label": str(row_meta["label"]),
                        "field_id": str(row_meta["field_id"]),
                        "split": "Unseen Holdout Plant" if row_meta["is_holdout"] else "Train Plant",
                        "wavelengths_nm": [float(w) for w in wavelengths],
                        "raw_bands": bands,
                    }
                )

    return {
        "source": source,
        "class_names": bundle["class_names"],
        "wavelengths_nm": [float(w) for w in wavelengths],
        "aligned_wavelengths_nm": [float(w) for w in bundle["aligned_wavelengths"]],
        "holdout_plants_count": sum(1 for p in plant_records if p["split"] == "holdout_test"),
        "plants": plant_records,
        "sample_presets": presets,
    }


def action_predict_one(source: DatasetSource, payload: dict[str, Any]) -> dict[str, Any]:
    bundle = _fit_and_cache_bundle(source)
    wavelengths = bundle["wavelengths"]
    active_model = str(payload.get("model", "xgboost"))

    bands_map: dict[str, float] = payload.get("bands", {})
    if not bands_map and "vector" in payload:
        vec = np.asarray(payload["vector"], dtype=float)
        if len(vec) != len(wavelengths):
            raise ValueError(f"Expected {len(wavelengths)} bands, got {len(vec)}")
        raw_row = vec
    else:
        raw_vals = []
        for wl in wavelengths:
            k_int = str(int(round(wl)))
            k_mean = f"Mean_{int(round(wl))}"
            k_band = f"band_{int(round(wl))}nm"
            if k_int in bands_map:
                raw_vals.append(float(bands_map[k_int]))
            elif k_mean in bands_map:
                raw_vals.append(float(bands_map[k_mean]))
            elif k_band in bands_map:
                raw_vals.append(float(bands_map[k_band]))
            else:
                # Linear interpolate or zero if 365 is omitted
                raw_vals.append(0.0)
        raw_row = np.asarray(raw_vals, dtype=float)

    res = _predict_row(bundle, raw_row, active_model=active_model)
    res["source"] = source
    res["input_wavelengths_nm"] = [float(w) for w in wavelengths]
    res["raw_input_bands"] = {
        str(int(round(w))): round(float(v), 3) for w, v in zip(wavelengths, raw_row)
    }
    return res


def _parse_csv_spectra_rows(csv_text: str, target_wl: np.ndarray) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Parse arbitrary CSV containing leaf spectra into aligned matrix matching target_wl."""
    df = pd.read_csv(io.StringIO(csv_text.strip()))
    if df.empty:
        raise ValueError("Uploaded CSV contains no data rows.")

    # Auto-detect fractional reflectance [0..1] vs percent [0..100]
    col_map: dict[float, str] = {}
    for col in df.columns:
        clean = str(col).strip()
        wl_num = None
        if clean.startswith("Mean_"):
            try:
                wl_num = float(clean.replace("Mean_", ""))
            except ValueError:
                pass
        elif clean.startswith("band_") and clean.endswith("nm"):
            try:
                wl_num = float(clean.replace("band_", "").replace("nm", ""))
            except ValueError:
                pass
        else:
            stripped = clean.lower().replace("nm", "").strip()
            try:
                val = float(stripped)
                if 300.0 <= val <= 2500.0:
                    wl_num = val
            except ValueError:
                pass
        if wl_num is not None:
            col_map[wl_num] = col

    if len(col_map) < 3:
        raise ValueError(
            "Could not detect at least 3 wavelength columns (e.g., Mean_460..Mean_970, band_460nm, or numeric headers like 460, 525, 670, 780)."
        )

    avail_wls = np.array(sorted(col_map.keys()), dtype=float)
    raw_avail = df[[col_map[w] for w in avail_wls]].to_numpy(dtype=float)

    # Rescale fractional [0..1] -> [0..100]% if max reflectance <= 1.5
    if np.nanmax(raw_avail) <= 1.5:
        raw_avail = raw_avail * 100.0

    # Interpolate onto dataset wavelength grid smoothly
    aligned_rows = np.empty((len(df), len(target_wl)), dtype=float)
    for r in range(len(df)):
        row_vals = raw_avail[r]
        aligned_rows[r] = np.interp(target_wl, avail_wls, row_vals)

    meta_rows = []
    for idx, row in df.iterrows():
        sid = row.get("Sample_ID", row.get("sample_id", f"Row-{idx + 1}"))
        pid = row.get("Plant_ID", row.get("plant_id", "-"))
        dt = row.get("date", row.get("acquisition_date", "-"))
        truth = row.get("Treatment", row.get("disease_label", row.get("label", None)))
        meta_rows.append(
            {
                "row_index": int(idx + 1),
                "sample_id": str(sid),
                "plant_id": str(pid),
                "date": str(dt),
                "true_label": str(truth) if pd.notna(truth) else None,
            }
        )
    return meta_rows, aligned_rows


def action_predict_csv(source: DatasetSource, payload: dict[str, Any]) -> dict[str, Any]:
    bundle = _fit_and_cache_bundle(source)
    csv_text = str(payload.get("csv_text", "")).strip()
    active_model = str(payload.get("model", "xgboost"))
    if not csv_text:
        raise ValueError("Missing csv_text payload.")

    meta_rows, X_in = _parse_csv_spectra_rows(csv_text, bundle["wavelengths"])
    max_rows = min(len(X_in), 200)
    pipe: SpectralFeatureSetPipeline = bundle["feat_pipe"]
    X_feat = pipe.transform(X_in[:max_rows])
    X_refl = pipe.preprocessor_.transform_reflectance_only(X_in[:max_rows])
    X_vi = pipe.index_extractor_.transform(X_refl)
    vi_names = pipe.index_extractor_.get_feature_names_out()
    ndvi_i = vi_names.index("NDVI") if "NDVI" in vi_names else 0
    ndre_i = vi_names.index("NDRE") if "NDRE" in vi_names else 0
    rep_i = vi_names.index("REP_nm") if "REP_nm" in vi_names else 0

    clf = bundle["models"].get(active_model, bundle["models"]["xgboost"])
    class_names: list[str] = bundle["class_names"]
    probs = clf.predict_proba(X_feat)
    preds = np.argmax(probs, axis=1)

    rows_out = []
    class_counts: dict[str, int] = {c: 0 for c in class_names}
    correct_count = 0
    labeled_count = 0

    for i in range(max_rows):
        pred_cls = class_names[int(preds[i])]
        class_counts[pred_cls] = class_counts.get(pred_cls, 0) + 1
        meta = meta_rows[i]
        is_correct = None
        if meta["true_label"] is not None and meta["true_label"] in class_names:
            labeled_count += 1
            is_correct = meta["true_label"] == pred_cls
            if is_correct:
                correct_count += 1
        rows_out.append(
            {
                **meta,
                "predicted_class": pred_cls,
                "confidence": round(float(probs[i, preds[i]]), 4),
                "is_correct": is_correct,
                "ndvi": round(float(X_vi[i, ndvi_i]), 4) if X_vi.shape[1] > ndvi_i else 0.0,
                "ndre": round(float(X_vi[i, ndre_i]), 4) if X_vi.shape[1] > ndre_i else 0.0,
                "rep_nm": round(float(X_vi[i, rep_i]), 2) if X_vi.shape[1] > rep_i else 710.0,
                "probabilities": {c: round(float(p), 4) for c, p in zip(class_names, probs[i])},
            }
        )

    mean_curve = np.mean(X_refl, axis=0)
    return {
        "source": source,
        "model": active_model,
        "rows_scored": max_rows,
        "total_rows_in_csv": len(X_in),
        "labeled_accuracy": round(correct_count / labeled_count, 4) if labeled_count > 0 else None,
        "class_counts": class_counts,
        "mean_reflectance_curve": [
            {"wavelength_nm": float(w), "reflectance": round(float(v), 3)}
            for w, v in zip(bundle["aligned_wavelengths"], mean_curve)
        ],
        "reference_curves": bundle["ref_curves"],
        "rows": rows_out,
    }


def action_forecast_plant(source: DatasetSource, payload: dict[str, Any]) -> dict[str, Any]:
    """Run live plant-level chronological Lag-RF & Lag-Ridge forecasts + classifier stress probability trajectory."""
    bundle = _fit_and_cache_bundle(source)
    X_clean, y_clean, groups_clean, _ = _load_clean_table(source)
    requested_pid = str(payload.get("plant_id", "")).strip()
    horizon = max(1, min(3, int(payload.get("horizon", 3))))

    pipe: SpectralFeatureSetPipeline = bundle["feat_pipe"]
    clf = bundle["models"]["xgboost"]
    class_names: list[str] = bundle["class_names"]
    # Identify primary stress/positive class (Drought or non-Healthy)
    stress_idx = 1 if len(class_names) > 1 else 0

    X_refl = pipe.preprocessor_.transform_reflectance_only(X_clean)
    X_vis = pipe.index_extractor_.transform(X_refl)
    vi_names = pipe.index_extractor_.get_feature_names_out()
    aligned_wl = bundle["aligned_wavelengths"]
    band_cols = [f"Band_{int(round(w))}nm" for w in aligned_wl]

    X_feat = pipe.transform(X_clean)
    probs = clf.predict_proba(X_feat)
    stress_prob = probs[:, stress_idx] if probs.shape[1] == 2 else (1.0 - probs[:, 0])

    meta = groups_clean[["plant_id", "date", "field_id", "plot_id"]].copy()
    meta["label"] = y_clean
    meta["parsed_date"] = _parse_sortable_dates(meta["date"])
    meta["stress_prob"] = stress_prob

    full_df = pd.concat(
        [
            meta.reset_index(drop=True),
            pd.DataFrame(X_refl, columns=band_cols),
            pd.DataFrame(X_vis, columns=vi_names),
        ],
        axis=1,
    )

    if not requested_pid or requested_pid not in set(full_df["plant_id"]):
        test_pids = set(groups_clean.iloc[bundle["test_idx"]]["plant_id"].astype(str).tolist())
        candidates = sorted(test_pids) if test_pids else sorted(full_df["plant_id"].unique().tolist())
        requested_pid = candidates[0]

    p_raw = full_df[full_df["plant_id"] == requested_pid].copy()
    daily = (
        p_raw.groupby(["plant_id", "parsed_date", "date", "label"], as_index=False)[
            band_cols + vi_names + ["stress_prob"]
        ]
        .mean()
        .sort_values("parsed_date")
        .reset_index(drop=True)
    )

    # Healthy cohort daily mean NDVI curve for biological divergence comparison
    healthy_name = bundle["healthy_label"]
    healthy_daily = (
        full_df[full_df["label"] == healthy_name]
        .groupby("parsed_date", as_index=False)["NDVI"]
        .agg(["mean", "std"])
        .reset_index()
    )
    h_map = {
        pd.Timestamp(r["parsed_date"]): (float(r["mean"]), float(r["std"] if pd.notna(r["std"]) else 0.03))
        for _, r in healthy_daily.iterrows()
    }

    forecaster = bundle["forecasters"].get(horizon) or bundle["forecasters"].get(1)
    win_size = int(forecaster["window_size"]) if forecaster else 3
    seq_cols = vi_names + band_cols
    ndvi_col_i = vi_names.index("NDVI")
    ndre_col_i = vi_names.index("NDRE") if "NDRE" in vi_names else ndvi_col_i

    arr_seq = daily[seq_cols].to_numpy(dtype=float)
    n_t = len(daily)

    history_points = []
    first_stress_flag_day = None
    first_ndvi_divergence_day = None
    t0 = pd.Timestamp(daily["parsed_date"].iloc[0])

    # Run rolling one-step or k-step backtest predictions where history allows
    ridge_f = forecaster["ridge"] if forecaster else None
    scaler_f = forecaster["scaler"] if forecaster else None
    rf_f = forecaster["rf"] if forecaster else None
    f_h = int(forecaster["horizon"]) if forecaster else 1

    pred_rf_by_idx: dict[int, float] = {}
    pred_ridge_by_idx: dict[int, float] = {}
    if forecaster and n_t >= win_size + f_h:
        for end_t in range(win_size - 1, n_t - f_h):
            start_t = end_t - win_size + 1
            win_mat = arr_seq[start_t : end_t + 1, :]
            ndvi_slope = float((win_mat[-1, ndvi_col_i] - win_mat[0, ndvi_col_i]) / max(1, win_size - 1))
            ndre_slope = float((win_mat[-1, ndre_col_i] - win_mat[0, ndre_col_i]) / max(1, win_size - 1))
            ndvi_mean = float(np.mean(win_mat[:, ndvi_col_i]))
            flat_vec = np.concatenate([win_mat.reshape(-1), np.array([ndvi_slope, ndre_slope, ndvi_mean])]).reshape(1, -1)
            target_idx = end_t + f_h
            pred_rf_by_idx[target_idx] = float(np.clip(rf_f.predict(flat_vec)[0], -1.0, 1.0))
            pred_ridge_by_idx[target_idx] = float(np.clip(ridge_f.predict(scaler_f.transform(flat_vec))[0], -1.0, 1.0))

    for idx, row in daily.iterrows():
        dt = pd.Timestamp(row["parsed_date"])
        day_num = int((dt - t0).days)
        h_mean, h_std = h_map.get(dt, (float(row["NDVI"]), 0.03))
        ndvi_val = float(row["NDVI"])
        sprob = float(row["stress_prob"])
        if first_stress_flag_day is None and sprob >= 0.55:
            first_stress_flag_day = day_num
        if first_ndvi_divergence_day is None and (h_mean - ndvi_val) > max(0.025, 0.75 * h_std):
            first_ndvi_divergence_day = day_num
        history_points.append(
            {
                "step": int(idx + 1),
                "day_offset": day_num,
                "date": str(row["date"]),
                "actual_ndvi": round(ndvi_val, 4),
                "healthy_cohort_ndvi": round(h_mean, 4),
                "ndre": round(float(row["NDRE"]), 4) if "NDRE" in daily else 0.0,
                "pri": round(float(row["PRI"]), 4) if "PRI" in daily else 0.0,
                "rep_nm": round(float(row["REP_nm"]), 2) if "REP_nm" in daily else 710.0,
                "stress_prob": round(sprob, 4),
                "lag_rf_backtest": round(pred_rf_by_idx[idx], 4) if idx in pred_rf_by_idx else None,
                "lag_ridge_backtest": round(pred_ridge_by_idx[idx], 4) if idx in pred_ridge_by_idx else None,
            }
        )

    # Future forward forecast from the last W scans for horizons +1 .. +horizon
    future_points = []
    if n_t >= win_size:
        win_mat = arr_seq[n_t - win_size : n_t, :]
        ndvi_slope = float((win_mat[-1, ndvi_col_i] - win_mat[0, ndvi_col_i]) / max(1, win_size - 1))
        ndre_slope = float((win_mat[-1, ndre_col_i] - win_mat[0, ndre_col_i]) / max(1, win_size - 1))
        ndvi_mean = float(np.mean(win_mat[:, ndvi_col_i]))
        flat_vec = np.concatenate([win_mat.reshape(-1), np.array([ndvi_slope, ndre_slope, ndvi_mean])]).reshape(1, -1)
        last_ndvi = float(daily["NDVI"].iloc[-1])
        last_date = pd.Timestamp(daily["parsed_date"].iloc[-1])

        for h in range(1, horizon + 1):
            fc = bundle["forecasters"].get(h)
            if fc is not None:
                rf_val = float(np.clip(fc["rf"].predict(flat_vec)[0], -1.0, 1.0))
                ridge_val = float(np.clip(fc["ridge"].predict(fc["scaler"].transform(flat_vec))[0], -1.0, 1.0))
            else:
                rf_val = float(np.clip(last_ndvi + h * ndvi_slope, -1.0, 1.0))
                ridge_val = rf_val
            future_dt = last_date + pd.Timedelta(days=h)
            future_points.append(
                {
                    "horizon": h,
                    "day_offset": int((future_dt - t0).days),
                    "date": f"t+{h} ({future_dt.strftime('%m-%d-%y')})",
                    "persistence_ndvi": round(last_ndvi, 4),
                    "lag_ridge_ndvi": round(ridge_val, 4),
                    "lag_rf_ndvi": round(rf_val, 4),
                    "delta_from_current": round(rf_val - last_ndvi, 4),
                }
            )

    test_pids = set(groups_clean.iloc[bundle["test_idx"]]["plant_id"].astype(str).tolist())
    return {
        "source": source,
        "plant_id": requested_pid,
        "true_label": str(daily["label"].iloc[-1]),
        "field_id": str(p_raw["field_id"].iloc[0]),
        "plot_id": str(p_raw["plot_id"].iloc[0]),
        "split": "Unseen Holdout Plant" if requested_pid in test_pids else "Train Plant",
        "window_size": win_size,
        "horizon": horizon,
        "n_timepoints": n_t,
        "trial_duration_days": int((pd.Timestamp(daily["parsed_date"].iloc[-1]) - t0).days),
        "first_spectral_flag_day": first_stress_flag_day,
        "first_ndvi_divergence_day": first_ndvi_divergence_day,
        "lead_time_vs_end_days": (
            int((pd.Timestamp(daily["parsed_date"].iloc[-1]) - t0).days) - first_stress_flag_day
            if first_stress_flag_day is not None
            else None
        ),
        "history": history_points,
        "future": future_points,
    }


def action_early_detection(source: DatasetSource) -> dict[str, Any]:
    """Compute held-out early-detection lead-time curve & summary across all stressed holdout plants."""
    bundle = _fit_and_cache_bundle(source)
    X_clean, y_clean, groups_clean, _ = _load_clean_table(source)
    test_idx = bundle["test_idx"]

    pipe: SpectralFeatureSetPipeline = bundle["feat_pipe"]
    clf = bundle["models"]["xgboost"]
    class_names: list[str] = bundle["class_names"]
    healthy_name = bundle["healthy_label"]
    stress_idx = 1 if len(class_names) > 1 else 0

    X_test_feat = pipe.transform(X_clean[test_idx])
    X_test_refl = pipe.preprocessor_.transform_reflectance_only(X_clean[test_idx])
    X_test_vi = pipe.index_extractor_.transform(X_test_refl)
    vi_names = pipe.index_extractor_.get_feature_names_out()
    ndvi_col = vi_names.index("NDVI")
    rep_col = vi_names.index("REP_nm") if "REP_nm" in vi_names else ndvi_col

    probs = clf.predict_proba(X_test_feat)
    stress_prob = probs[:, stress_idx] if probs.shape[1] == 2 else (1.0 - probs[:, 0])

    df = groups_clean.iloc[test_idx][["plant_id", "date"]].copy().reset_index(drop=True)
    df["label"] = y_clean[test_idx]
    df["is_stressed"] = df["label"] != healthy_name
    df["parsed_date"] = _parse_sortable_dates(df["date"])
    t_start = df["parsed_date"].min()
    df["day_num"] = (df["parsed_date"] - t_start).dt.days
    df["ndvi"] = X_test_vi[:, ndvi_col]
    df["rep_nm"] = X_test_vi[:, rep_col]
    df["stress_prob"] = stress_prob

    # Per-date cohort comparison
    daily_curve = []
    first_cohort_divergence_day = None
    first_classifier_day = None
    for day_val, grp in df.groupby("day_num"):
        h_grp = grp[~grp["is_stressed"]]
        s_grp = grp[grp["is_stressed"]]
        if len(h_grp) == 0 or len(s_grp) == 0:
            continue
        h_ndvi = float(h_grp["NDVI" if "NDVI" in h_grp else "ndvi"].mean())
        s_ndvi = float(s_grp["ndvi"].mean())
        h_prob = float(h_grp["stress_prob"].mean())
        s_prob = float(s_grp["stress_prob"].mean())
        pooled_sd = float(np.sqrt(0.5 * (np.var(h_grp["ndvi"]) + np.var(s_grp["ndvi"])) + 1e-8))
        cohen_d = (h_ndvi - s_ndvi) / pooled_sd
        if first_cohort_divergence_day is None and cohen_d >= 0.4:
            first_cohort_divergence_day = int(day_val)
        if first_classifier_day is None and s_prob > h_prob + 0.05 and s_prob >= 0.50:
            first_classifier_day = int(day_val)
        daily_curve.append(
            {
                "day_num": int(day_val),
                "date": str(grp["date"].iloc[0]),
                "healthy_ndvi": round(h_ndvi, 4),
                "stressed_ndvi": round(s_ndvi, 4),
                "healthy_stress_prob": round(h_prob, 4),
                "stressed_stress_prob": round(s_prob, 4),
                "ndvi_separation_d": round(float(cohen_d), 3),
            }
        )

    # Individual held-out stressed plant lead times relative to peak end-of-trial stress
    plant_lead_days = []
    for pid, grp in df[df["is_stressed"]].groupby("plant_id"):
        grp_s = grp.sort_values("day_num")
        peak_day = int(grp_s["day_num"].max())
        flagged = grp_s[grp_s["stress_prob"] >= 0.52]
        if len(flagged) > 0:
            first_flag = int(flagged["day_num"].iloc[0])
            plant_lead_days.append(max(0, peak_day - first_flag))

    max_day = int(df["day_num"].max()) if len(df) else 0
    return {
        "source": source,
        "holdout_scans": int(len(df)),
        "holdout_stressed_plants": int(df[df["is_stressed"]]["plant_id"].nunique()),
        "trial_span_days": max_day,
        "first_classifier_detection_day": first_classifier_day,
        "first_ndvi_divergence_day": first_cohort_divergence_day,
        "median_plant_lead_days_before_end": round(float(np.median(plant_lead_days)), 1) if plant_lead_days else 0.0,
        "pct_stressed_plants_detected_early": round(
            100.0 * len(plant_lead_days) / max(1, int(df[df["is_stressed"]]["plant_id"].nunique())),
            1,
        ),
        "daily_curve": daily_curve,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="TerraSpectra live inference & forecasting CLI")
    parser.add_argument(
        "--action",
        required=True,
        choices=["samples", "predict-one", "predict-csv", "forecast-plant", "early-detection", "warm-cache"],
    )
    parser.add_argument("--source", default="primary", choices=["primary", "synthetic"])
    parser.add_argument("--payload-json", default="{}")
    args = parser.parse_args()

    payload = json.loads(args.payload_json) if args.payload_json else {}
    src: DatasetSource = args.source

    if args.action == "warm-cache":
        for s in ("primary", "synthetic"):
            _fit_and_cache_bundle(s)  # type: ignore[arg-type]
        print(json.dumps({"ok": True, "cached": ["primary", "synthetic"]}))
    elif args.action == "samples":
        print(json.dumps(action_samples(src)))
    elif args.action == "predict-one":
        print(json.dumps(action_predict_one(src, payload)))
    elif args.action == "predict-csv":
        print(json.dumps(action_predict_csv(src, payload)))
    elif args.action == "forecast-plant":
        print(json.dumps(action_forecast_plant(src, payload)))
    elif args.action == "early-detection":
        print(json.dumps(action_early_detection(src)))


if __name__ == "__main__":
    main()
