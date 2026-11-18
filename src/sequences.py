"""Day 6 Block 5: Temporal Sequence Construction & Leak-Free Forecasting Prep (`src/sequences.py`).

Builds chronological sliding-window sequences per plant across measurement dates:
  - Input window: past W timepoints ending at time t (spectral bands + NDVI, NDRE, PRI, REP, lags)
  - Targets at horizon t + k:
      1) Continuous future NDVI_{t+k} (and delta_NDVI = NDVI_{t+k} - NDVI_t)
      2) Binary/categorical stress label at t + k
  - Zero-leakage rule: every window carries its plant_id so StratifiedGroupKFold / GroupKFold
    keeps all windows from one plant strictly inside the same split.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from src.data import DatasetSource, load_dataset
from src.features import VegetationIndexExtractor
from src.preprocessing import BadBandDropper, ReflectanceSanitizer, remove_nan_spectral_rows


@dataclass
class TemporalSequenceDataset:
    source: DatasetSource
    window_size: int
    horizon: int
    X_windows_flat: np.ndarray
    X_windows_3d: np.ndarray
    feature_names: list[str]
    y_ndvi_target: np.ndarray
    y_ndvi_current: np.ndarray
    y_delta_ndvi: np.ndarray
    y_label_target: np.ndarray
    plant_ids: np.ndarray
    target_dates: np.ndarray
    n_plants_with_sequences: int
    unique_dates_count: int
    min_obs_per_plant: int
    median_obs_per_plant: float
    max_obs_per_plant: int


def _parse_sortable_dates(date_series: pd.Series) -> pd.Series:
    """Parse MM-DD-YY (Zenodo) or ISO YYYY-MM-DD (Synthetic) into sortable timestamps."""
    parsed = pd.to_datetime(date_series, format="%m-%d-%y", errors="coerce")
    if parsed.isna().any():
        fallback = pd.to_datetime(date_series, errors="coerce")
        parsed = parsed.fillna(fallback)
    return parsed


def build_temporal_sequences(
    source: DatasetSource = "primary",
    window_size: int = 3,
    horizon: int = 1,
) -> TemporalSequenceDataset:
    """Build per-plant sliding temporal windows predicting vegetation health at t + horizon."""
    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, _ = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )

    drop_wl = (365.0,) if source == "primary" else ()
    dropper = BadBandDropper(wavelengths=ds.wavelengths, drop_wavelengths=drop_wl, enabled=True).fit(X_clean)
    wl_aligned = dropper.get_aligned_wavelengths()
    sanitizer = ReflectanceSanitizer(clip_min=0.0, clip_max=100.0, enabled=True).fit(dropper.transform(X_clean))
    X_refl = sanitizer.transform(dropper.transform(X_clean))

    vi_ext = VegetationIndexExtractor(wavelengths=wl_aligned).fit(X_refl)
    X_vi = vi_ext.transform(X_refl)
    vi_names = vi_ext.get_feature_names_out()
    ndvi_col = vi_names.index("NDVI")

    meta_df = groups_clean.copy()
    meta_df["label"] = y_clean
    meta_df["parsed_date"] = _parse_sortable_dates(meta_df["date"])
    meta_df["orig_pos"] = np.arange(len(meta_df))

    # Aggregate replicate scans taken on the same plant + date to clean daily plant trajectories
    band_cols = [f"Band_{int(round(w))}nm" for w in wl_aligned]
    combined = pd.concat(
        [
            meta_df[["plant_id", "date", "parsed_date", "label"]].reset_index(drop=True),
            pd.DataFrame(X_refl, columns=band_cols),
            pd.DataFrame(X_vi, columns=vi_names),
        ],
        axis=1,
    )

    daily = (
        combined.groupby(["plant_id", "parsed_date", "date", "label"], as_index=False)[band_cols + vi_names]
        .mean()
        .sort_values(["plant_id", "parsed_date"])
        .reset_index(drop=True)
    )

    obs_counts = daily.groupby("plant_id").size()
    seq_cols = vi_names + band_cols

    windows_3d: list[np.ndarray] = []
    windows_flat: list[np.ndarray] = []
    y_ndvi_target: list[float] = []
    y_ndvi_current: list[float] = []
    y_delta_ndvi: list[float] = []
    y_label_target: list[str] = []
    seq_plants: list[str] = []
    seq_dates: list[str] = []

    # Feature names for flattened lag table + explicit temporal summary statistics
    flat_names: list[str] = []
    for lag_idx in range(window_size):
        lag_label = f"t-{window_size - 1 - lag_idx}" if lag_idx < window_size - 1 else "t"
        for col in seq_cols:
            flat_names.append(f"{col}_{lag_label}")
    flat_names.extend(["NDVI_slope_window", "NDRE_slope_window", "NDVI_rolling_mean"])

    ndre_col = vi_names.index("NDRE") if "NDRE" in vi_names else ndvi_col

    for plant_id, p_df in daily.groupby("plant_id", sort=False):
        p_df = p_df.sort_values("parsed_date").reset_index(drop=True)
        n_t = len(p_df)
        if n_t < window_size + horizon:
            continue

        arr_seq = p_df[seq_cols].to_numpy(dtype=float)
        ndvi_series = p_df["NDVI"].to_numpy(dtype=float)
        labels_series = p_df["label"].astype(str).to_numpy()
        dates_series = p_df["date"].astype(str).to_numpy()

        for end_t in range(window_size - 1, n_t - horizon):
            start_t = end_t - window_size + 1
            target_idx = end_t + horizon
            win_mat = arr_seq[start_t : end_t + 1, :]
            ndvi_slope = float(
                (win_mat[-1, ndvi_col] - win_mat[0, ndvi_col]) / max(1, window_size - 1)
            )
            ndre_slope = float(
                (win_mat[-1, ndre_col] - win_mat[0, ndre_col]) / max(1, window_size - 1)
            )
            ndvi_mean = float(np.mean(win_mat[:, ndvi_col]))
            flat_vec = np.concatenate(
                [win_mat.reshape(-1), np.array([ndvi_slope, ndre_slope, ndvi_mean], dtype=float)]
            )

            windows_3d.append(win_mat)
            windows_flat.append(flat_vec)
            y_ndvi_current.append(float(ndvi_series[end_t]))
            y_ndvi_target.append(float(ndvi_series[target_idx]))
            y_delta_ndvi.append(float(ndvi_series[target_idx] - ndvi_series[end_t]))
            y_label_target.append(labels_series[target_idx])
            seq_plants.append(str(plant_id))
            seq_dates.append(dates_series[target_idx])

    return TemporalSequenceDataset(
        source=source,
        window_size=window_size,
        horizon=horizon,
        X_windows_flat=np.asarray(windows_flat, dtype=float) if windows_flat else np.empty((0, len(flat_names))),
        X_windows_3d=np.asarray(windows_3d, dtype=float) if windows_3d else np.empty((0, window_size, len(seq_cols))),
        feature_names=flat_names,
        y_ndvi_target=np.asarray(y_ndvi_target, dtype=float),
        y_ndvi_current=np.asarray(y_ndvi_current, dtype=float),
        y_delta_ndvi=np.asarray(y_delta_ndvi, dtype=float),
        y_label_target=np.asarray(y_label_target, dtype=str),
        plant_ids=np.asarray(seq_plants, dtype=str),
        target_dates=np.asarray(seq_dates, dtype=str),
        n_plants_with_sequences=int(pd.Series(seq_plants).nunique()) if seq_plants else 0,
        unique_dates_count=int(daily["date"].nunique()),
        min_obs_per_plant=int(obs_counts.min()),
        median_obs_per_plant=float(obs_counts.median()),
        max_obs_per_plant=int(obs_counts.max()),
    )


def evaluate_forecasting_baselines(
    seq_ds: TemporalSequenceDataset,
    n_splits: int = 5,
) -> dict:
    """Evaluate persistence vs. lag-feature Ridge & Random Forest regressors inside plant-grouped CV."""
    if len(seq_ds.y_ndvi_target) == 0:
        return {
            "feasible": False,
            "reason": "Insufficient repeated timepoints per plant for requested window/horizon.",
            "n_sequences": 0,
        }

    unique_plants = int(pd.Series(seq_ds.plant_ids).nunique())
    splits = min(n_splits, max(2, unique_plants))
    gkf = GroupKFold(n_splits=splits)

    y_true = seq_ds.y_ndvi_target
    y_persist = seq_ds.y_ndvi_current
    X = seq_ds.X_windows_flat
    groups = seq_ds.plant_ids

    results: dict[str, dict] = {}
    oof_preds: dict[str, np.ndarray] = {
        "persistence": y_persist.copy(),
        "lag_ridge": np.zeros_like(y_true),
        "lag_rf": np.zeros_like(y_true),
    }

    fold_metrics: dict[str, dict[str, list[float]]] = {
        "persistence": {"mae": [], "rmse": [], "r2": []},
        "lag_ridge": {"mae": [], "rmse": [], "r2": []},
        "lag_rf": {"mae": [], "rmse": [], "r2": []},
    }

    for tr_idx, va_idx in gkf.split(X, y_true, groups=groups):
        # 1) Persistence baseline: NDVI_{t+k} = NDVI_t
        pred_p = y_persist[va_idx]
        fold_metrics["persistence"]["mae"].append(float(mean_absolute_error(y_true[va_idx], pred_p)))
        fold_metrics["persistence"]["rmse"].append(float(np.sqrt(mean_squared_error(y_true[va_idx], pred_p))))
        fold_metrics["persistence"]["r2"].append(float(r2_score(y_true[va_idx], pred_p)))

        # 2) Lag-feature Ridge Regression
        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X[tr_idx])
        X_va_s = scaler.transform(X[va_idx])
        ridge = Ridge(alpha=10.0)
        ridge.fit(X_tr_s, y_true[tr_idx])
        pred_r = np.clip(ridge.predict(X_va_s), -1.0, 1.0)
        oof_preds["lag_ridge"][va_idx] = pred_r
        fold_metrics["lag_ridge"]["mae"].append(float(mean_absolute_error(y_true[va_idx], pred_r)))
        fold_metrics["lag_ridge"]["rmse"].append(float(np.sqrt(mean_squared_error(y_true[va_idx], pred_r))))
        fold_metrics["lag_ridge"]["r2"].append(float(r2_score(y_true[va_idx], pred_r)))

        # 3) Lag-feature Random Forest Regressor
        rf = RandomForestRegressor(n_estimators=120, max_depth=8, random_state=42, n_jobs=1)
        rf.fit(X[tr_idx], y_true[tr_idx])
        pred_rf = np.clip(rf.predict(X[va_idx]), -1.0, 1.0)
        oof_preds["lag_rf"][va_idx] = pred_rf
        fold_metrics["lag_rf"]["mae"].append(float(mean_absolute_error(y_true[va_idx], pred_rf)))
        fold_metrics["lag_rf"]["rmse"].append(float(np.sqrt(mean_squared_error(y_true[va_idx], pred_rf))))
        fold_metrics["lag_rf"]["r2"].append(float(r2_score(y_true[va_idx], pred_rf)))

    labels_pretty = {
        "persistence": "Persistence (NDVI_{t+k} = NDVI_t)",
        "lag_ridge": "Lag-Feature Ridge Regression",
        "lag_rf": "Lag-Feature Random Forest",
    }
    models_summary = []
    for key in ("persistence", "lag_ridge", "lag_rf"):
        models_summary.append(
            {
                "key": key,
                "name": labels_pretty[key],
                "mae_mean": round(float(np.mean(fold_metrics[key]["mae"])), 5),
                "mae_std": round(float(np.std(fold_metrics[key]["mae"], ddof=1) if len(fold_metrics[key]["mae"]) > 1 else 0.0), 5),
                "rmse_mean": round(float(np.mean(fold_metrics[key]["rmse"])), 5),
                "rmse_std": round(float(np.std(fold_metrics[key]["rmse"], ddof=1) if len(fold_metrics[key]["rmse"]) > 1 else 0.0), 5),
                "r2_mean": round(float(np.mean(fold_metrics[key]["r2"])), 4),
                "r2_std": round(float(np.std(fold_metrics[key]["r2"], ddof=1) if len(fold_metrics[key]["r2"]) > 1 else 0.0), 4),
            }
        )

    # Sample trajectory pairs (up to 60 evenly spaced sequences) for UI chart
    step = max(1, len(y_true) // 60)
    sample_points = [
        {
            "plant_id": str(seq_ds.plant_ids[i]),
            "date": str(seq_ds.target_dates[i]),
            "actual_ndvi": round(float(y_true[i]), 4),
            "persistence_ndvi": round(float(oof_preds["persistence"][i]), 4),
            "lag_ridge_ndvi": round(float(oof_preds["lag_ridge"][i]), 4),
            "lag_rf_ndvi": round(float(oof_preds["lag_rf"][i]), 4),
        }
        for i in range(0, len(y_true), step)
    ]

    return {
        "feasible": True,
        "source": seq_ds.source,
        "window_size": seq_ds.window_size,
        "horizon": seq_ds.horizon,
        "n_sequences": int(len(y_true)),
        "n_features_per_window": int(X.shape[1]),
        "n_plants": seq_ds.n_plants_with_sequences,
        "unique_dates": seq_ds.unique_dates_count,
        "obs_per_plant": {
            "min": seq_ds.min_obs_per_plant,
            "median": seq_ds.median_obs_per_plant,
            "max": seq_ds.max_obs_per_plant,
        },
        "models": models_summary,
        "sample_predictions": sample_points,
    }


if __name__ == "__main__":
    for src in ("primary", "synthetic"):
        win = 3 if src == "primary" else 2
        seq = build_temporal_sequences(source=src, window_size=win, horizon=1)
        eval_res = evaluate_forecasting_baselines(seq)
        print(f"[{src}] sequences={eval_res.get('n_sequences')} plants={eval_res.get('n_plants')}")
        for m in eval_res.get("models", []):
            print(f"  {m['name']}: MAE={m['mae_mean']:.4f}, RMSE={m['rmse_mean']:.4f}, R2={m['r2_mean']:.4f}")
