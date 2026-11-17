"""Day 4 (Thu 19 Nov): Leak-Free Feature Engineering & Named Feature Sets A–E.

Implements:
  - Block 1: Nearest-wavelength band lookup helper (`find_nearest_band`)
  - Block 2: Vegetation indices (`NDVI`, `NDRE`, `PRI`, `Red-edge position`, `MCARI`)
             MCARI definition per Daughtry et al. (2000), Remote Sensing of Environment 74(2):229-239:
             MCARI = ((R700 - R670) - 0.2 * (R700 - R550)) * (R700 / R670)
  - Block 3: PCA reducer fitted strictly on training data (`PCASpectralReducer`)
  - Block 4: Random Forest importance + Mutual Information band selection fitted strictly
             on training splits / inside StratifiedGroupKFold (`SupervisedBandSelector`)
  - Block 5: Named Feature Sets A to E integrated inside the Day 3 preprocessing pipeline
             and persisted cleanly to data/processed/

Watch out rule: NEVER select bands or fit PCA on the full dataset before splitting.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Literal

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from src.data import DatasetSource, load_dataset
from src.preprocessing import (
    PROCESSED_DIR,
    PreprocessingConfig,
    SpectralPreprocessor,
    make_leak_free_train_test_indices,
    remove_nan_spectral_rows,
)


@dataclass
class NearestBandMatch:
    requested_nm: float
    band_index: int
    matched_nm: float
    delta_nm: float
    within_tolerance: bool


def find_nearest_band(
    wavelengths: np.ndarray | list[float],
    target_nm: float,
    max_delta_nm: float | None = 30.0,
) -> NearestBandMatch:
    """Block 1: Return the index and exact wavelength of the band nearest to target_nm."""
    wl = np.asarray(wavelengths, dtype=float)
    if wl.size == 0:
        raise ValueError("Wavelength array is empty.")
    idx = int(np.argmin(np.abs(wl - float(target_nm))))
    matched = float(wl[idx])
    delta = abs(matched - float(target_nm))
    within = True if max_delta_nm is None else delta <= float(max_delta_nm)
    return NearestBandMatch(
        requested_nm=float(target_nm),
        band_index=idx,
        matched_nm=matched,
        delta_nm=round(delta, 2),
        within_tolerance=within,
    )


def _compute_red_edge_position(X: np.ndarray, wavelengths: np.ndarray) -> np.ndarray:
    """Compute Red-Edge Position (nm) where first derivative dR/dlambda peaks inside 690–750 nm.

    If at least 3 bands lie inside [680, 760] nm (e.g. hyperspectral/synthetic cubes), uses the
    exact discrete derivative argmax with local parabolic refinement inside [690, 750] nm.
    If the sensor is multispectral with sparse bands straddling the red edge (e.g. 670, 700, 780 nm),
    uses Guyot & Baret / 3-point quadratic derivative interpolation constrained to [690, 750] nm
    so REP tracks red-edge inflection shift smoothly per observation.
    """
    wl = np.asarray(wavelengths, dtype=float)
    re_mask = (wl >= 690.0) & (wl <= 750.0)
    dense_re_indices = np.where(re_mask)[0]

    # Case 1: Multiple bands inside [690, 750] nm -> direct max of first derivative
    if len(dense_re_indices) >= 3:
        d1 = np.gradient(X, wl, axis=1)
        sub_d1 = d1[:, dense_re_indices]
        local_arg = np.argmax(sub_d1, axis=1)
        rep = np.empty(X.shape[0], dtype=float)
        for i, pos in enumerate(local_arg):
            g_idx = dense_re_indices[pos]
            if 0 < g_idx < len(wl) - 1:
                y0, y1, y2 = d1[i, g_idx - 1], d1[i, g_idx], d1[i, g_idx + 1]
                denom = (y0 - 2.0 * y1 + y2)
                if abs(denom) > 1e-12:
                    shift = 0.5 * (y0 - y2) / denom
                    shift = float(np.clip(shift, -0.5, 0.5))
                    step = 0.5 * (wl[g_idx + 1] - wl[g_idx - 1])
                    rep[i] = np.clip(wl[g_idx] + shift * step, 690.0, 750.0)
                    continue
            rep[i] = wl[g_idx]
        return rep

    # Case 2: Sparse multispectral red-edge (e.g., 645, 670, 700, 780 nm)
    b670 = find_nearest_band(wl, 670.0, max_delta_nm=40.0).band_index
    b700 = find_nearest_band(wl, 700.0, max_delta_nm=40.0).band_index
    b780 = find_nearest_band(wl, 780.0, max_delta_nm=40.0).band_index
    b740 = find_nearest_band(wl, 740.0, max_delta_nm=45.0).band_index

    r670 = X[:, b670]
    r700 = X[:, b700]
    r740 = X[:, b740]
    r780 = X[:, b780]

    # Cho & Skidmore / Guyot-Baret inflection estimator bounded inside 690–750 nm:
    # Inflection reflectance R_re = (R670 + R780) / 2 -> linearly interpolated across [700, 740/780]
    r_re = 0.5 * (r670 + r780)
    span_hi = np.where(np.abs(r780 - r700) > 1e-6, r780 - r700, 1e-6)
    wl_hi = wl[b780]
    if b740 != b780 and abs(wl[b740] - wl[b700]) > 5.0:
        span_hi = np.where(np.abs(r740 - r700) > 1e-6, r740 - r700, 1e-6)
        wl_hi = wl[b740]

    raw_rep = wl[b700] + (wl_hi - wl[b700]) * ((r_re - r700) / span_hi)
    return np.clip(raw_rep, 690.0, 750.0)


class VegetationIndexExtractor(BaseEstimator, TransformerMixin):
    """Block 2: Compute NDVI, NDRE, PRI, Red-edge position, and MCARI (Daughtry et al. 2000).

    Requires positive/uncentered reflectance aligned with `wavelengths`.
    Skips and documents any index whose spectral range is missing.
    """

    def __init__(self, wavelengths: np.ndarray | list[float], eps: float = 1e-6) -> None:
        self.wavelengths = np.asarray(wavelengths, dtype=float)
        self.eps = eps

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "VegetationIndexExtractor":
        wl = np.asarray(self.wavelengths, dtype=float)
        self.matches_: dict[str, dict[str, NearestBandMatch]] = {}
        self.feature_names_: list[str] = []
        self.skipped_indices_: list[dict[str, str]] = []

        # 1. NDVI: (R800 - R670) / (R800 + R670)
        m_nir = find_nearest_band(wl, 800.0, max_delta_nm=35.0)
        m_red = find_nearest_band(wl, 670.0, max_delta_nm=25.0)
        if m_nir.within_tolerance and m_red.within_tolerance:
            self.matches_["NDVI"] = {"NIR_800": m_nir, "Red_670": m_red}
            self.feature_names_.append("NDVI")
        else:
            self.skipped_indices_.append(
                {"index": "NDVI", "reason": "Missing 800 nm NIR or 670 nm Red coverage"}
            )

        # 2. NDRE: (R800 - R720) / (R800 + R720)
        m_re = find_nearest_band(wl, 720.0, max_delta_nm=25.0)
        if m_nir.within_tolerance and m_re.within_tolerance:
            self.matches_["NDRE"] = {"NIR_800": m_nir, "RedEdge_720": m_re}
            self.feature_names_.append("NDRE")
        else:
            self.skipped_indices_.append(
                {"index": "NDRE", "reason": "Missing 800 nm NIR or 720 nm Red-Edge coverage"}
            )

        # 3. PRI: (R531 - R570) / (R531 + R570)
        m_531 = find_nearest_band(wl, 531.0, max_delta_nm=15.0)
        m_570 = find_nearest_band(wl, 570.0, max_delta_nm=15.0)
        if m_531.within_tolerance and m_570.within_tolerance:
            self.matches_["PRI"] = {"R531": m_531, "R570": m_570}
            self.feature_names_.append("PRI")
        else:
            self.skipped_indices_.append(
                {"index": "PRI", "reason": "Missing 531 nm or 570 nm visible bands"}
            )

        # 4. Red-Edge Position (nm inside 690-750 nm)
        has_red_edge_window = bool(np.any((wl >= 670.0) & (wl <= 780.0)))
        if has_red_edge_window and len(wl) >= 3:
            self.feature_names_.append("REP_nm")
            self.matches_["REP_nm"] = {
                "Red_670": m_red,
                "RedEdge_700": find_nearest_band(wl, 700.0, max_delta_nm=25.0),
                "NIR_780": find_nearest_band(wl, 780.0, max_delta_nm=35.0),
            }
        else:
            self.skipped_indices_.append(
                {"index": "REP_nm", "reason": "Insufficient bands in 690–750 nm range"}
            )

        # 5. MCARI (Daughtry et al. 2000): ((R700 - R670) - 0.2*(R700 - R550)) * (R700 / R670)
        m_700 = find_nearest_band(wl, 700.0, max_delta_nm=20.0)
        m_550 = find_nearest_band(wl, 550.0, max_delta_nm=25.0)
        if m_700.within_tolerance and m_red.within_tolerance and m_550.within_tolerance:
            self.matches_["MCARI"] = {"R700": m_700, "R670": m_red, "R550": m_550}
            self.feature_names_.append("MCARI")
        else:
            self.skipped_indices_.append(
                {"index": "MCARI", "reason": "Missing 550, 670, or 700 nm bands"}
            )

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_arr = np.asarray(X, dtype=float)
        cols: list[np.ndarray] = []

        if "NDVI" in self.feature_names_:
            nir = X_arr[:, self.matches_["NDVI"]["NIR_800"].band_index]
            red = X_arr[:, self.matches_["NDVI"]["Red_670"].band_index]
            denom = np.where(np.abs(nir + red) > self.eps, nir + red, self.eps)
            cols.append((nir - red) / denom)

        if "NDRE" in self.feature_names_:
            nir = X_arr[:, self.matches_["NDRE"]["NIR_800"].band_index]
            re = X_arr[:, self.matches_["NDRE"]["RedEdge_720"].band_index]
            denom = np.where(np.abs(nir + re) > self.eps, nir + re, self.eps)
            cols.append((nir - re) / denom)

        if "PRI" in self.feature_names_:
            r531 = X_arr[:, self.matches_["PRI"]["R531"].band_index]
            r570 = X_arr[:, self.matches_["PRI"]["R570"].band_index]
            denom = np.where(np.abs(r531 + r570) > self.eps, r531 + r570, self.eps)
            cols.append((r531 - r570) / denom)

        if "REP_nm" in self.feature_names_:
            cols.append(_compute_red_edge_position(X_arr, self.wavelengths))

        if "MCARI" in self.feature_names_:
            r700 = X_arr[:, self.matches_["MCARI"]["R700"].band_index]
            r670 = X_arr[:, self.matches_["MCARI"]["R670"].band_index]
            r550 = X_arr[:, self.matches_["MCARI"]["R550"].band_index]
            safe_r670 = np.where(np.abs(r670) > self.eps, r670, self.eps)
            mcari = ((r700 - r670) - 0.2 * (r700 - r550)) * (r700 / safe_r670)
            cols.append(mcari)

        if not cols:
            return np.empty((X_arr.shape[0], 0), dtype=float)
        return np.column_stack(cols)

    def get_feature_names_out(self) -> list[str]:
        return list(self.feature_names_)


class PCASpectralReducer(BaseEstimator, TransformerMixin):
    """Block 3: Fit StandardScaler + PCA strictly on training data to prevent leakage."""

    def __init__(self, n_components: int | float = 0.99, max_components: int = 8) -> None:
        self.n_components = n_components
        self.max_components = max_components

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "PCASpectralReducer":
        self.scaler_ = StandardScaler()
        Xs = self.scaler_.fit_transform(X)
        # Fit full PCA first so explained variance curve covers every component
        full_pca = PCA(random_state=42)
        full_pca.fit(Xs)
        self.full_explained_variance_ratio_ = full_pca.explained_variance_ratio_.copy()
        self.full_cumulative_variance_ = np.cumsum(full_pca.explained_variance_ratio_).copy()

        if isinstance(self.n_components, float) and 0.0 < self.n_components < 1.0:
            k = int(np.searchsorted(self.full_cumulative_variance_, self.n_components) + 1)
            k = max(2, min(k, min(self.max_components, X.shape[1])))
        else:
            k = max(1, min(int(self.n_components), min(self.max_components, X.shape[1])))

        self.pca_ = PCA(n_components=k, random_state=42)
        self.pca_.fit(Xs)
        self.n_components_ = k
        self.feature_names_ = [f"PC{i + 1}" for i in range(k)]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return self.pca_.transform(self.scaler_.transform(X))

    def get_feature_names_out(self) -> list[str]:
        return list(self.feature_names_)


class SupervisedBandSelector(BaseEstimator, TransformerMixin):
    """Block 4: Select top-k bands using RF importance + Mutual Information on training split only."""

    def __init__(
        self,
        wavelengths: np.ndarray | list[float],
        top_k: int = 5,
        mode: Literal["consensus", "rf", "mi"] = "consensus",
        random_state: int = 42,
    ) -> None:
        self.wavelengths = np.asarray(wavelengths, dtype=float)
        self.top_k = top_k
        self.mode = mode
        self.random_state = random_state

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SupervisedBandSelector":
        y_enc = LabelEncoder().fit_transform(np.asarray(y))
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            random_state=self.random_state,
            n_jobs=1,
        )
        rf.fit(X, y_enc)
        self.rf_importances_ = rf.feature_importances_.copy()

        mi = mutual_info_classif(X, y_enc, random_state=self.random_state)
        self.mi_scores_ = mi.copy()

        rf_norm = self.rf_importances_ / max(1e-12, float(np.max(self.rf_importances_)))
        mi_norm = self.mi_scores_ / max(1e-12, float(np.max(self.mi_scores_)))

        if self.mode == "rf":
            score = rf_norm
        elif self.mode == "mi":
            score = mi_norm
        else:
            score = 0.5 * (rf_norm + mi_norm)

        self.combined_scores_ = score
        k = min(int(self.top_k), X.shape[1])
        top_unsorted = np.argsort(score)[::-1][:k]
        self.selected_indices_ = np.sort(top_unsorted)
        self.selected_wavelengths_ = self.wavelengths[self.selected_indices_].copy()
        self.feature_names_ = [f"Band_{int(round(w))}nm" for w in self.selected_wavelengths_]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(X, dtype=float)[:, self.selected_indices_]

    def get_feature_names_out(self) -> list[str]:
        return list(self.feature_names_)


FeatureSetName = Literal[
    "A_full_spectrum",
    "B_veg_indices",
    "C_pca",
    "D_selected_bands",
    "E_indices_plus_selected",
]


class SpectralFeatureSetPipeline(BaseEstimator, TransformerMixin):
    """Unified Day 3 Preprocessing + Day 4 Feature Engineering Pipeline for Sets A–E.

    Fits all preprocessing statistics (clipping medians, MSC reference, PCA, RF/MI selection)
    strictly on X_train, y_train so test/validation folds never leak.
    """

    def __init__(
        self,
        wavelengths: np.ndarray | list[float],
        feature_set: FeatureSetName = "E_indices_plus_selected",
        prep_config: PreprocessingConfig | None = None,
        pca_variance: float = 0.99,
        top_k_bands: int = 5,
    ) -> None:
        self.wavelengths = np.asarray(wavelengths, dtype=float)
        self.feature_set = feature_set
        self.prep_config = prep_config or PreprocessingConfig()
        self.pca_variance = pca_variance
        self.top_k_bands = top_k_bands

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SpectralFeatureSetPipeline":
        self.preprocessor_ = SpectralPreprocessor(
            wavelengths=self.wavelengths,
            config=self.prep_config,
        )
        X_spec_proc = self.preprocessor_.fit_transform(X, y)
        X_refl = self.preprocessor_.transform_reflectance_only(X)
        aligned_wl = self.preprocessor_.get_aligned_wavelengths()
        self.aligned_wavelengths_ = aligned_wl

        # Build transformers strictly on training split
        self.index_extractor_ = VegetationIndexExtractor(wavelengths=aligned_wl).fit(X_refl, y)
        self.pca_reducer_ = PCASpectralReducer(n_components=self.pca_variance).fit(X_spec_proc, y)
        self.band_selector_ = SupervisedBandSelector(
            wavelengths=aligned_wl,
            top_k=min(self.top_k_bands, X_spec_proc.shape[1]),
            mode="consensus",
        ).fit(X_spec_proc, y)

        if self.feature_set == "A_full_spectrum":
            self.feature_names_ = [f"Band_{int(round(w))}nm" for w in aligned_wl]
        elif self.feature_set == "B_veg_indices":
            self.feature_names_ = self.index_extractor_.get_feature_names_out()
        elif self.feature_set == "C_pca":
            self.feature_names_ = self.pca_reducer_.get_feature_names_out()
        elif self.feature_set == "D_selected_bands":
            self.feature_names_ = self.band_selector_.get_feature_names_out()
        elif self.feature_set == "E_indices_plus_selected":
            self.feature_names_ = (
                self.index_extractor_.get_feature_names_out()
                + self.band_selector_.get_feature_names_out()
            )
        else:
            raise ValueError(f"Unknown feature_set: {self.feature_set}")

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_spec_proc = self.preprocessor_.transform(X)
        if self.feature_set == "A_full_spectrum":
            return X_spec_proc
        if self.feature_set == "B_veg_indices":
            return self.index_extractor_.transform(self.preprocessor_.transform_reflectance_only(X))
        if self.feature_set == "C_pca":
            return self.pca_reducer_.transform(X_spec_proc)
        if self.feature_set == "D_selected_bands":
            return self.band_selector_.transform(X_spec_proc)
        if self.feature_set == "E_indices_plus_selected":
            X_idx = self.index_extractor_.transform(self.preprocessor_.transform_reflectance_only(X))
            X_sel = self.band_selector_.transform(X_spec_proc)
            return np.hstack([X_idx, X_sel])
        raise ValueError(f"Unknown feature_set: {self.feature_set}")

    def get_feature_names_out(self) -> list[str]:
        return list(self.feature_names_)


FEATURE_SET_LABELS: dict[FeatureSetName, tuple[str, str]] = {
    "A_full_spectrum": ("Set A", "Preprocessed full spectrum"),
    "B_veg_indices": ("Set B", "Vegetation indices only (NDVI, NDRE, PRI, REP, MCARI)"),
    "C_pca": ("Set C", "PCA components (fit on train split only)"),
    "D_selected_bands": ("Set D", "Selected bands (RF importance + Mutual Info on train only)"),
    "E_indices_plus_selected": ("Set E", "Indices plus selected bands"),
}


def build_and_save_feature_sets(
    source: DatasetSource = "primary",
    prep_config: PreprocessingConfig | None = None,
    top_k_bands: int = 5,
    pca_variance: float = 0.99,
) -> dict:
    """Build Feature Sets A–E using strictly leak-free train-only fit, evaluate with StratifiedGroupKFold,
    and persist processed arrays to data/processed/.
    """
    cfg = prep_config or PreprocessingConfig()
    ds = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, dropped_nan = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )
    train_idx, test_idx = make_leak_free_train_test_indices(y_clean, groups_clean)
    X_train_raw, X_test_raw = X_clean[train_idx], X_clean[test_idx]
    y_train, y_test = y_clean[train_idx], y_clean[test_idx]

    # Single leak-free cross-validation evaluation inside StratifiedGroupKFold (grouped by plant_id)
    plants = groups_clean["plant_id"].to_numpy()
    sgkf = StratifiedGroupKFold(n_splits=min(5, max(2, pd.Series(plants).nunique())))
    le = LabelEncoder().fit(y_clean)
    y_enc = le.transform(y_clean)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    feature_sets_summary: list[dict] = []
    reference_pipe: SpectralFeatureSetPipeline | None = None

    for set_key, (short_code, desc) in FEATURE_SET_LABELS.items():
        # 1) Fit strictly on holdout train_idx & save train/test split matrices
        pipe = SpectralFeatureSetPipeline(
            wavelengths=ds.wavelengths,
            feature_set=set_key,
            prep_config=cfg,
            pca_variance=pca_variance,
            top_k_bands=top_k_bands,
        )
        X_train_feat = pipe.fit_transform(X_train_raw, y_train)
        X_test_feat = pipe.transform(X_test_raw)
        feat_names = pipe.get_feature_names_out()
        if set_key == "E_indices_plus_selected":
            reference_pipe = pipe

        out_path = PROCESSED_DIR / f"{source}_feature_set_{short_code.replace(' ', '_')}.npz"
        np.savez(
            out_path,
            X_train=X_train_feat,
            X_test=X_test_feat,
            y_train=y_train,
            y_test=y_test,
            feature_names=np.array(feat_names, dtype=object),
            aligned_wavelengths=pipe.aligned_wavelengths_,
        )

        # 2) Leak-free StratifiedGroupKFold CV inside-fold benchmark (sanity comparison)
        fold_f1_lr: list[float] = []
        fold_auc_lr: list[float] = []
        fold_f1_rf: list[float] = []
        for tr_i, va_i in sgkf.split(X_clean, y_enc, groups=plants):
            fold_pipe = SpectralFeatureSetPipeline(
                wavelengths=ds.wavelengths,
                feature_set=set_key,
                prep_config=cfg,
                pca_variance=pca_variance,
                top_k_bands=top_k_bands,
            )
            X_tr_f = fold_pipe.fit_transform(X_clean[tr_i], y_clean[tr_i])
            X_va_f = fold_pipe.transform(X_clean[va_i])
            scaler = StandardScaler()
            X_tr_s = scaler.fit_transform(X_tr_f)
            X_va_s = scaler.transform(X_va_f)

            clf_lr = LogisticRegression(max_iter=1000, random_state=42)
            clf_lr.fit(X_tr_s, y_enc[tr_i])
            pred_lr = clf_lr.predict(X_va_s)
            fold_f1_lr.append(float(f1_score(y_enc[va_i], pred_lr, average="macro")))
            if len(le.classes_) == 2:
                prob_lr = clf_lr.predict_proba(X_va_s)[:, 1]
                fold_auc_lr.append(float(roc_auc_score(y_enc[va_i], prob_lr)))

            clf_rf = RandomForestClassifier(n_estimators=120, max_depth=8, random_state=42, n_jobs=1)
            clf_rf.fit(X_tr_f, y_enc[tr_i])
            pred_rf = clf_rf.predict(X_va_f)
            fold_f1_rf.append(float(f1_score(y_enc[va_i], pred_rf, average="macro")))

        feature_sets_summary.append(
            {
                "key": set_key,
                "code": short_code,
                "description": desc,
                "n_features": int(X_train_feat.shape[1]),
                "feature_names": feat_names,
                "train_shape": [int(X_train_feat.shape[0]), int(X_train_feat.shape[1])],
                "test_shape": [int(X_test_feat.shape[0]), int(X_test_feat.shape[1])],
                "cv_macro_f1_lr": round(float(np.mean(fold_f1_lr)), 4),
                "cv_macro_f1_rf": round(float(np.mean(fold_f1_rf)), 4),
                "cv_roc_auc_lr": round(float(np.mean(fold_auc_lr)), 4) if fold_auc_lr else None,
                "saved_path": str(out_path.relative_to(ROOT_DIR)),
            }
        )

    assert reference_pipe is not None
    # Export index lookup matches cleanly
    band_matches: list[dict] = []
    for idx_name, refs in reference_pipe.index_extractor_.matches_.items():
        for role, m in refs.items():
            band_matches.append(
                {
                    "index_name": idx_name,
                    "role": role,
                    **asdict(m),
                }
            )

    manifest = {
        "source": source,
        "dropped_nan_rows": dropped_nan,
        "aligned_wavelengths_nm": [float(w) for w in reference_pipe.aligned_wavelengths_],
        "band_matches": band_matches,
        "skipped_indices": reference_pipe.index_extractor_.skipped_indices_,
        "feature_sets": feature_sets_summary,
    }
    (PROCESSED_DIR / f"{source}_day4_feature_sets.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return {
        "dataset": ds,
        "X_clean": X_clean,
        "y_clean": y_clean,
        "groups_clean": groups_clean,
        "train_idx": train_idx,
        "test_idx": test_idx,
        "reference_pipe": reference_pipe,
        "manifest": manifest,
    }


if __name__ == "__main__":
    for src in ("primary", "synthetic"):
        res = build_and_save_feature_sets(source=src)
        print(f"=== {src.upper()} FEATURE SETS A-E (Leak-Free Plant-Grouped CV) ===")
        for item in res["manifest"]["feature_sets"]:
            print(
                f"  {item['code']} ({item['n_features']} feats): "
                f"LR F1={item['cv_macro_f1_lr']:.4f} | RF F1={item['cv_macro_f1_rf']:.4f} "
                f"| saved -> {item['saved_path']}"
            )
