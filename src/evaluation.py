"""Day 5 Block 1 & 4: Leak-Free StratifiedGroupKFold Splitter & Evaluation Harness.

Provides:
  - Fixed RANDOM_SEED = 42 and reproducible StratifiedGroupKFold(n_splits=5) grouped by plant_id
  - Persistent split index manifest saved to data/processed/day5_cv_splits.json
  - Out-of-fold & per-fold metrics: Balanced Accuracy, Macro-F1, Per-Class Precision/Recall,
    ROC-AUC, and aggregated Confusion Matrix
  - Leakage comparison helper contrasting StratifiedGroupKFold vs. naive random StratifiedKFold
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Callable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.preprocessing import LabelEncoder

RANDOM_SEED = 42
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


class PLSDAClassifier(BaseEstimator, ClassifierMixin):
    """Partial Least Squares Discriminant Analysis wrapper for binary & multi-class spectra."""

    def __init__(self, n_components: int = 5, scale: bool = True) -> None:
        self.n_components = n_components
        self.scale = scale

    def fit(self, X: np.ndarray, y: np.ndarray) -> "PLSDAClassifier":
        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y)
        self.classes_ = np.unique(y_arr)
        n_classes = len(self.classes_)
        self._is_binary = n_classes == 2

        Y_dummy = np.zeros((len(y_arr), n_classes), dtype=float)
        for i, cls in enumerate(self.classes_):
            Y_dummy[:, i] = (y_arr == cls).astype(float)

        max_comp = max(1, min(int(self.n_components), X_arr.shape[1], X_arr.shape[0] - 1))
        self.effective_components_ = max_comp
        self.pls_ = PLSRegression(n_components=max_comp, scale=self.scale)
        self.pls_.fit(X_arr, Y_dummy)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        raw_scores = self.pls_.predict(np.asarray(X, dtype=float))
        if raw_scores.ndim == 1:
            raw_scores = raw_scores[:, None]
        # Temperature-calibrated softmax over PLS dummy response projections
        shifted = raw_scores - np.max(raw_scores, axis=1, keepdims=True)
        exp_s = np.exp(np.clip(shifted * 2.0, -30.0, 30.0))
        probs = exp_s / np.sum(exp_s, axis=1, keepdims=True)
        return probs

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return self.classes_[np.argmax(probs, axis=1)]


def build_and_save_grouped_splits(
    y: np.ndarray,
    group_ids: pd.DataFrame,
    source: str,
    group_col: str = "plant_id",
    n_splits: int = 5,
    save: bool = True,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], dict]:
    """Create reproducible StratifiedGroupKFold folds and persist indices cleanly."""
    groups = group_ids[group_col].to_numpy()
    unique_groups = int(pd.Series(groups).nunique())
    splits = min(n_splits, max(2, unique_groups))
    sgkf = StratifiedGroupKFold(n_splits=splits, shuffle=True, random_state=RANDOM_SEED)

    folds: list[tuple[np.ndarray, np.ndarray]] = []
    fold_records: list[dict] = []
    for fold_id, (tr_idx, va_idx) in enumerate(sgkf.split(np.zeros(len(y)), y, groups=groups)):
        folds.append((tr_idx, va_idx))
        tr_plants = set(groups[tr_idx].tolist())
        va_plants = set(groups[va_idx].tolist())
        overlap = tr_plants.intersection(va_plants)
        fold_records.append(
            {
                "fold": fold_id,
                "train_n": int(len(tr_idx)),
                "val_n": int(len(va_idx)),
                "train_groups": len(tr_plants),
                "val_groups": len(va_plants),
                "group_overlap": len(overlap),
                "val_indices": [int(i) for i in va_idx],
            }
        )

    manifest = {
        "source": source,
        "random_seed": RANDOM_SEED,
        "cv_strategy": f"StratifiedGroupKFold(n_splits={splits}, shuffle=True, random_state={RANDOM_SEED})",
        "group_column": group_col,
        "total_clean_samples": int(len(y)),
        "unique_groups": unique_groups,
        "folds": fold_records,
    }
    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        out_path = PROCESSED_DIR / f"{source}_day5_cv_splits.json"
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return folds, manifest


def build_naive_random_splits(
    y: np.ndarray,
    n_splits: int = 5,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Leakage demonstration splitter: random sample split ignoring plant/plot grouping."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_SEED)
    return [(tr_idx, va_idx) for tr_idx, va_idx in skf.split(np.zeros(len(y)), y)]


def evaluate_cv_folds(
    X: np.ndarray,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    pipeline_factory: Callable[[], object],
) -> dict:
    """Evaluate a leak-free pipeline factory across all folds, returning mean ± std metrics,
    per-class precision/recall, aggregated confusion matrix, and out-of-fold predictions.
    """
    le = LabelEncoder().fit(y)
    y_enc = le.transform(y)
    class_names = [str(c) for c in le.classes_]
    n_classes = len(class_names)

    fold_bacc: list[float] = []
    fold_mf1: list[float] = []
    fold_auc: list[float] = []

    oof_pred = np.full(len(y_enc), -1, dtype=int)
    oof_proba = np.zeros((len(y_enc), n_classes), dtype=float)

    for tr_idx, va_idx in folds:
        pipe = pipeline_factory()
        pipe.fit(X[tr_idx], y_enc[tr_idx])
        pred = np.asarray(pipe.predict(X[va_idx]), dtype=int)
        oof_pred[va_idx] = pred

        if hasattr(pipe, "predict_proba"):
            proba = np.asarray(pipe.predict_proba(X[va_idx]), dtype=float)
        else:
            proba = np.eye(n_classes, dtype=float)[pred]
        oof_proba[va_idx] = proba

        fold_bacc.append(float(balanced_accuracy_score(y_enc[va_idx], pred)))
        fold_mf1.append(float(f1_score(y_enc[va_idx], pred, average="macro")))
        try:
            if n_classes == 2:
                fold_auc.append(float(roc_auc_score(y_enc[va_idx], proba[:, 1])))
            else:
                fold_auc.append(
                    float(roc_auc_score(y_enc[va_idx], proba, multi_class="ovr", average="macro"))
                )
        except ValueError:
            pass

    cm = confusion_matrix(y_enc, oof_pred, labels=list(range(n_classes)))
    cls_report = classification_report(
        y_enc,
        oof_pred,
        labels=list(range(n_classes)),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    per_class = [
        {
            "class_name": cname,
            "precision": round(float(cls_report[cname]["precision"]), 4),
            "recall": round(float(cls_report[cname]["recall"]), 4),
            "f1": round(float(cls_report[cname]["f1-score"]), 4),
            "support": int(cls_report[cname]["support"]),
        }
        for cname in class_names
    ]

    oof_bacc = float(balanced_accuracy_score(y_enc, oof_pred))
    oof_mf1 = float(f1_score(y_enc, oof_pred, average="macro"))
    try:
        oof_auc = (
            float(roc_auc_score(y_enc, oof_proba[:, 1]))
            if n_classes == 2
            else float(roc_auc_score(y_enc, oof_proba, multi_class="ovr", average="macro"))
        )
    except ValueError:
        oof_auc = float(np.mean(fold_auc)) if fold_auc else 0.0

    return {
        "class_names": class_names,
        "balanced_acc_mean": round(float(np.mean(fold_bacc)), 4),
        "balanced_acc_std": round(float(np.std(fold_bacc, ddof=1) if len(fold_bacc) > 1 else 0.0), 4),
        "macro_f1_mean": round(float(np.mean(fold_mf1)), 4),
        "macro_f1_std": round(float(np.std(fold_mf1, ddof=1) if len(fold_mf1) > 1 else 0.0), 4),
        "roc_auc_mean": round(float(np.mean(fold_auc)) if fold_auc else 0.0, 4),
        "roc_auc_std": round(float(np.std(fold_auc, ddof=1) if len(fold_auc) > 1 else 0.0), 4),
        "oof_balanced_acc": round(oof_bacc, 4),
        "oof_macro_f1": round(oof_mf1, 4),
        "oof_roc_auc": round(oof_auc, 4),
        "fold_scores": {
            "balanced_acc": [round(x, 4) for x in fold_bacc],
            "macro_f1": [round(x, 4) for x in fold_mf1],
            "roc_auc": [round(x, 4) for x in fold_auc],
        },
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "oof_pred_indices": oof_pred.tolist(),
        "oof_true_indices": y_enc.tolist(),
        "oof_proba": oof_proba.tolist(),
    }
