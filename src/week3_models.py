"""Day 7 & Week 3 Spectral Architecture Benchmark & Readiness (`src/week3_models.py`).

Implements:
  1. Week 3 Neural Comparator (`MLPClassifier` multi-layer spectral network) benchmarked on the
     exact frozen plant-grouped splits (`data/processed/*_day5_cv_splits.json`) against Day 5–6
     RF, XGBoost, SVM, and PLS-DA baselines.
  2. Documented architecture specifications (`Spectral1DCNN` & `TemporalStressGRU`) with exact
     input tensor dimensions, parameter counts, training hyperparameters, and early-stopping protocol
     for Week 3 execution (24 to 30 Nov).

Usage:
  python3 src/week3_models.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data import DatasetSource, load_dataset
from src.evaluation import RANDOM_SEED, build_and_save_grouped_splits, evaluate_cv_folds
from src.features import SpectralFeatureSetPipeline
from src.preprocessing import PreprocessingConfig, remove_nan_spectral_rows

REPORTS_DIR = ROOT_DIR / "reports"


def get_week3_architecture_specs(
    n_bands_primary: int = 9,
    n_bands_synthetic: int = 60,
    n_seq_features: int = 14,
    window_size: int = 3,
) -> list[dict[str, Any]]:
    """Return structured Week 3 model specifications with exact tensor shapes & parameter budgets."""
    return [
        {
            "id": "spectral_1d_cnn",
            "name": "Spectral 1D-CNN Classifier",
            "task": "Leaf Stress / Disease Detection",
            "input_shape_primary": f"(batch, 1, {n_bands_primary} bands)",
            "input_shape_synthetic": f"(batch, 1, {n_bands_synthetic} bands)",
            "architecture": "Conv1d(1->32, k=3) -> BN -> GELU -> Conv1d(32->64, k=3) -> AdaptiveAvgPool1d -> Linear(64->2/4)",
            "approx_params": "~11,400 parameters",
            "cv_contract": "Evaluated on frozen data/processed/primary_day5_cv_splits.json (5-fold StratifiedGroupKFold by plant_id)",
            "comparator": "XGBoost Tuned Set E (Macro-F1 0.4892 primary / 1.0000 synthetic)",
            "status": "Architecture Spec + MLP Comparator Verified",
        },
        {
            "id": "temporal_stress_gru",
            "name": "Temporal Stress GRU Forecaster",
            "task": "Multi-Horizon Canopy NDVI & Stress Trajectory Forecasting (t+1..t+3)",
            "input_shape_primary": f"(batch, W={window_size} steps, {n_seq_features} VI+band channels)",
            "input_shape_synthetic": "(batch, W=2 steps, 65 VI+band channels)",
            "architecture": "GRU(input_dim->48, num_layers=2, dropout=0.2) -> LayerNorm -> Linear(48->horizon)",
            "approx_params": "~23,800 parameters",
            "cv_contract": "GroupKFold(n_splits=5, groups=plant_id) via src/sequences.py windows",
            "comparator": "Lag-Feature Random Forest (k=+1 MAE 0.0175, R² 0.9822; k=+3 MAE 0.0327, R² 0.9425)",
            "status": "Sequence Tensors Ready (1,986 W=3 windows)",
        },
        {
            "id": "optional_3d_cnn",
            "name": "Optional Patch 3D-CNN (Cube-Only Extension)",
            "task": "Spatial-Spectral Leaf Lesion Classification",
            "input_shape_primary": "Deferred (Zenodo primary dataset is leaf-mean CSV without raw pixel cubes)",
            "input_shape_synthetic": "Cut first per Week 3 scope guard if timeline is tight",
            "architecture": "Conv3d(1->16, k=(3,3,3)) -> MaxPool3d -> GlobalAvgPool3d -> Linear",
            "approx_params": "~42,000 parameters",
            "cv_contract": "Spatial block holdout across plots/fields",
            "comparator": "Patch 1D-CNN baseline",
            "status": "Optional / First to Cut",
        },
    ]


def benchmark_neural_spectral_baseline(source: DatasetSource = "primary") -> dict[str, Any]:
    """Benchmark a lightweight regularized Neural MLP on Set A & Set E inside identical grouped CV splits."""
    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, _ = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )
    folds, _manifest = build_and_save_grouped_splits(
        y=y_clean,
        group_ids=groups_clean,
        source=source,
        group_col="plant_id",
        n_splits=5,
        save=False,
    )

    prep_cfg = PreprocessingConfig(
        drop_bad_bands=True,
        drop_wavelengths=(365.0,) if source == "primary" else (),
        normalization="snv",
        use_savgol=True,
        savgol_window=3 if source == "primary" else 5,
        savgol_polyorder=1 if source == "primary" else 2,
    )

    # Materialize Set E per fold strictly inside train fold
    fold_results = {}
    for fkey, label in [
        ("A_full_spectrum", "Neural MLP (Set A Spectrum)"),
        ("E_indices_plus_selected", "Neural MLP (Set E Indices+Bands)"),
    ]:
        # Precompute transformed fold features once without leakage across fold boundaries
        bacc_list, mf1_list, auc_list = [], [], []
        from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
        from sklearn.preprocessing import LabelEncoder

        le = LabelEncoder().fit(y_clean)
        y_enc = le.transform(y_clean)
        n_cls = len(le.classes_)

        for tr_i, va_i in folds:
            feat_pipe = SpectralFeatureSetPipeline(
                wavelengths=ds.wavelengths,
                feature_set=fkey,  # type: ignore[arg-type]
                prep_config=prep_cfg,
                top_k_bands=5,
            )
            X_tr = feat_pipe.fit_transform(X_clean[tr_i], y_clean[tr_i])
            X_va = feat_pipe.transform(X_clean[va_i])

            clf = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "mlp",
                        MLPClassifier(
                            hidden_layer_sizes=(64, 32),
                            activation="relu",
                            alpha=0.1,
                            max_iter=350,
                            early_stopping=True,
                            random_state=RANDOM_SEED,
                        ),
                    ),
                ]
            )
            clf.fit(X_tr, y_enc[tr_i])
            pred = clf.predict(X_va)
            proba = clf.predict_proba(X_va)
            bacc_list.append(float(balanced_accuracy_score(y_enc[va_i], pred)))
            mf1_list.append(float(f1_score(y_enc[va_i], pred, average="macro")))
            try:
                if n_cls == 2:
                    auc_list.append(float(roc_auc_score(y_enc[va_i], proba[:, 1])))
                else:
                    auc_list.append(float(roc_auc_score(y_enc[va_i], proba, multi_class="ovr", average="macro")))
            except ValueError:
                pass

        fold_results[fkey] = {
            "model_name": label,
            "feature_set": fkey,
            "balanced_acc_mean": round(float(np.mean(bacc_list)), 4),
            "balanced_acc_std": round(float(np.std(bacc_list, ddof=1)), 4),
            "macro_f1_mean": round(float(np.mean(mf1_list)), 4),
            "macro_f1_std": round(float(np.std(mf1_list, ddof=1)), 4),
            "roc_auc_mean": round(float(np.mean(auc_list)) if auc_list else 0.0, 4),
        }

    return {"source": source, "neural_mlp_results": list(fold_results.values())}


def run_week3_readiness_audit() -> dict[str, Any]:
    """Generate Week 3 readiness benchmark & architecture payload for reports/day7_consolidation.json."""
    specs = get_week3_architecture_specs()
    primary_mlp = benchmark_neural_spectral_baseline("primary")
    synthetic_mlp = benchmark_neural_spectral_baseline("synthetic")
    payload = {
        "architectures": specs,
        "benchmarks": {
            "primary": primary_mlp,
            "synthetic": synthetic_mlp,
        },
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / "day7_week3_readiness.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    res = run_week3_readiness_audit()
    for src_key in ("primary", "synthetic"):
        print(f"=== Week 3 Neural MLP Benchmark ({src_key}) ===")
        for item in res["benchmarks"][src_key]["neural_mlp_results"]:
            print(
                f"  {item['model_name']}: BalAcc={item['balanced_acc_mean']:.4f}, "
                f"MacroF1={item['macro_f1_mean']:.4f}, AUC={item['roc_auc_mean']:.4f}"
            )
