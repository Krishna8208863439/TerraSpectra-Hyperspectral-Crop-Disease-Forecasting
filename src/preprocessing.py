"""Day 3 (Wed 18 Nov): Reusable, Leak-Free Spectral Preprocessing Pipeline.

Implements scikit-learn compatible transformers with switchable config flags:
  - Block 1: BadBandDropper (drop UV/IR noisy edges & water-absorption bands, keeping wavelengths aligned)
  - Block 2: ReflectanceSanitizer (train-fit NaN median imputation, clipping, optional scaling)
  - Block 3: SavitzkyGolaySmoother (noise reduction with adaptive odd window & polynomial order)
  - Block 4: SpectralScatterNormalizer (SNV and train-fit MSC multiplicative scatter correction)
  - Block 5: FirstDerivativeSpectra (wavelength-aware first-derivative reflectance dR/dlambda)
  - Block 7: SpectralPreprocessor & one-call run_preprocessing_pipeline() saving to data/processed/

Design rule: Anything that learns from data (imputation medians, scalers, MSC reference spectrum)
is fitted ONLY on the training split inside fit(). Raw data in data/raw/ stays untouched.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import sys
from typing import Literal

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data import DatasetSource, SpectralDataset, load_dataset

PROCESSED_DIR = ROOT_DIR / "data" / "processed"

WATER_ABSORPTION_RANGES: tuple[tuple[float, float], ...] = (
    (1350.0, 1450.0),
    (1800.0, 1950.0),
)


@dataclass
class PreprocessingConfig:
    """Switchable preprocessing flags for Day 3 exploration & Day 5 model ablation."""

    drop_bad_bands: bool = True
    drop_wavelengths: tuple[float, ...] = (365.0,)
    drop_water_bands: bool = True
    clip_min: float = 0.0
    clip_max: float = 100.0
    scale_mode: Literal["none", "unit_0_1", "standard"] = "none"
    use_savgol: bool = True
    savgol_window: int = 3
    savgol_polyorder: int = 1
    normalization: Literal["none", "snv", "msc"] = "snv"
    use_first_derivative: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["drop_wavelengths"] = list(self.drop_wavelengths)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PreprocessingConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        if "drop_wavelengths" in filtered and filtered["drop_wavelengths"] is not None:
            filtered["drop_wavelengths"] = tuple(float(w) for w in filtered["drop_wavelengths"])
        return cls(**filtered)


def remove_nan_spectral_rows(
    spectra: np.ndarray,
    labels: np.ndarray,
    group_ids: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame, int]:
    """Filter out completely/partially missing spectral rows before CV splitting.

    Does not touch test labels/targets or learn statistics; strictly removes broken sensor scans.
    """
    X = np.asarray(spectra, dtype=float)
    valid_mask = np.isfinite(X).all(axis=1)
    dropped_count = int((~valid_mask).sum())
    if dropped_count == 0:
        return X, np.asarray(labels), group_ids.reset_index(drop=True), 0
    return (
        X[valid_mask],
        np.asarray(labels)[valid_mask],
        group_ids.loc[valid_mask].reset_index(drop=True),
        dropped_count,
    )


class BadBandDropper(BaseEstimator, TransformerMixin):
    """Block 1: Drop noisy spectral edges & water-absorption bands while aligning wavelengths."""

    def __init__(
        self,
        wavelengths: np.ndarray | list[float],
        drop_wavelengths: tuple[float, ...] = (365.0,),
        drop_water_bands: bool = True,
        water_band_ranges: tuple[tuple[float, float], ...] = WATER_ABSORPTION_RANGES,
        tolerance_nm: float = 2.0,
        enabled: bool = True,
    ) -> None:
        self.wavelengths = np.asarray(wavelengths, dtype=float)
        self.drop_wavelengths = tuple(float(w) for w in drop_wavelengths)
        self.drop_water_bands = drop_water_bands
        self.water_band_ranges = water_band_ranges
        self.tolerance_nm = tolerance_nm
        self.enabled = enabled

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "BadBandDropper":
        wl = np.asarray(self.wavelengths, dtype=float)
        if not self.enabled:
            self.keep_mask_ = np.ones(len(wl), dtype=bool)
        else:
            drop_mask = np.zeros(len(wl), dtype=bool)
            for target in self.drop_wavelengths:
                drop_mask |= np.abs(wl - target) <= self.tolerance_nm
            if self.drop_water_bands:
                for lo, hi in self.water_band_ranges:
                    drop_mask |= (wl >= lo) & (wl <= hi)
            self.keep_mask_ = ~drop_mask

        if not np.any(self.keep_mask_):
            raise ValueError("BadBandDropper would remove all bands; check drop_wavelengths config.")

        self.wavelengths_out_ = wl[self.keep_mask_].copy()
        self.dropped_wavelengths_ = wl[~self.keep_mask_].copy()
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_arr = np.asarray(X, dtype=float)
        return X_arr[:, self.keep_mask_]

    def get_aligned_wavelengths(self) -> np.ndarray:
        return self.wavelengths_out_.copy()


class ReflectanceSanitizer(BaseEstimator, TransformerMixin):
    """Block 2: Impute residual non-finite entries using train medians, clip range, and scale."""

    def __init__(
        self,
        clip_min: float = 0.0,
        clip_max: float = 100.0,
        scale_mode: Literal["none", "unit_0_1", "standard"] = "none",
        enabled: bool = True,
    ) -> None:
        self.clip_min = clip_min
        self.clip_max = clip_max
        self.scale_mode = scale_mode
        self.enabled = enabled

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "ReflectanceSanitizer":
        X_arr = np.asarray(X, dtype=float).copy()
        self.col_medians_ = np.nanmedian(X_arr, axis=0)
        self.col_medians_ = np.where(np.isfinite(self.col_medians_), self.col_medians_, 0.0)
        X_clean = self._impute_and_clip(X_arr)
        self.scaler_: StandardScaler | None = None
        if self.enabled and self.scale_mode == "standard":
            self.scaler_ = StandardScaler()
            self.scaler_.fit(X_clean)
        return self

    def _impute_and_clip(self, X_arr: np.ndarray) -> np.ndarray:
        out = np.asarray(X_arr, dtype=float).copy()
        bad_mask = ~np.isfinite(out)
        if np.any(bad_mask):
            row_idx, col_idx = np.where(bad_mask)
            out[row_idx, col_idx] = self.col_medians_[col_idx]
        if self.enabled:
            out = np.clip(out, self.clip_min, self.clip_max)
        return out

    def transform(self, X: np.ndarray) -> np.ndarray:
        out = self._impute_and_clip(np.asarray(X, dtype=float))
        if not self.enabled:
            return out
        if self.scale_mode == "unit_0_1":
            denom = self.clip_max if self.clip_max > 0 else 100.0
            return out / denom
        if self.scale_mode == "standard" and self.scaler_ is not None:
            return self.scaler_.transform(out)
        return out


class SavitzkyGolaySmoother(BaseEstimator, TransformerMixin):
    """Block 3: Savitzky-Golay spectral denoising along the wavelength axis."""

    def __init__(
        self,
        window_length: int = 5,
        polyorder: int = 2,
        deriv: int = 0,
        mode: str = "interp",
        enabled: bool = True,
    ) -> None:
        self.window_length = window_length
        self.polyorder = polyorder
        self.deriv = deriv
        self.mode = mode
        self.enabled = enabled

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "SavitzkyGolaySmoother":
        n_bands = X.shape[1]
        win = max(3, int(self.window_length))
        if win % 2 == 0:
            win += 1
        if win > n_bands:
            win = n_bands if n_bands % 2 == 1 else max(3, n_bands - 1)
        poly = min(int(self.polyorder), max(1, win - 2))
        self.effective_window_length_ = win
        self.effective_polyorder_ = poly
        self.can_apply_ = n_bands >= 3 and win >= 3 and poly < win
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_arr = np.asarray(X, dtype=float)
        if not self.enabled or not self.can_apply_:
            return X_arr.copy()
        return savgol_filter(
            X_arr,
            window_length=self.effective_window_length_,
            polyorder=self.effective_polyorder_,
            deriv=self.deriv,
            axis=1,
            mode=self.mode,
        )


class SpectralScatterNormalizer(BaseEstimator, TransformerMixin):
    """Block 4: SNV (row-wise scatter removal) and MSC (train-fit reference scatter correction)."""

    def __init__(
        self,
        method: Literal["none", "snv", "msc"] = "snv",
        eps: float = 1e-8,
        enabled: bool = True,
    ) -> None:
        self.method = method
        self.eps = eps
        self.enabled = enabled

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "SpectralScatterNormalizer":
        X_arr = np.asarray(X, dtype=float)
        # Fitted strictly on training split so MSC never leaks validation/test spectra
        self.reference_spectrum_ = np.mean(X_arr, axis=0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_arr = np.asarray(X, dtype=float)
        if not self.enabled or self.method == "none":
            return X_arr.copy()

        if self.method == "snv":
            means = np.mean(X_arr, axis=1, keepdims=True)
            stds = np.std(X_arr, axis=1, keepdims=True)
            stds = np.where(stds < self.eps, 1.0, stds)
            return (X_arr - means) / stds

        if self.method == "msc":
            ref = self.reference_spectrum_
            ref_mean = float(np.mean(ref))
            ref_centered = ref - ref_mean
            denom = float(np.dot(ref_centered, ref_centered))
            if denom < self.eps:
                return X_arr.copy()

            x_means = np.mean(X_arr, axis=1, keepdims=True)
            x_centered = X_arr - x_means
            slopes = (x_centered @ ref_centered) / denom
            slopes = np.where(np.abs(slopes) < self.eps, 1.0, slopes)
            intercepts = x_means[:, 0] - slopes * ref_mean
            return (X_arr - intercepts[:, None]) / slopes[:, None]

        raise ValueError(f"Unsupported scatter normalization method: {self.method}")


class FirstDerivativeSpectra(BaseEstimator, TransformerMixin):
    """Block 5: Wavelength-aware first-derivative reflectance dR/dlambda."""

    def __init__(
        self,
        wavelengths: np.ndarray | list[float] | None = None,
        use_wavelength_spacing: bool = True,
        enabled: bool = False,
    ) -> None:
        self.wavelengths = None if wavelengths is None else np.asarray(wavelengths, dtype=float)
        self.use_wavelength_spacing = use_wavelength_spacing
        self.enabled = enabled

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "FirstDerivativeSpectra":
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_arr = np.asarray(X, dtype=float)
        if not self.enabled:
            return X_arr.copy()
        if (
            self.use_wavelength_spacing
            and self.wavelengths is not None
            and len(self.wavelengths) == X_arr.shape[1]
        ):
            return np.gradient(X_arr, self.wavelengths, axis=1)
        return np.gradient(X_arr, axis=1)


class SpectralPreprocessor(BaseEstimator, TransformerMixin):
    """Block 7: Configurable end-to-end scikit-learn Pipeline wrapper keeping wavelengths aligned."""

    def __init__(
        self,
        wavelengths: np.ndarray | list[float],
        config: PreprocessingConfig | None = None,
    ) -> None:
        self.wavelengths = np.asarray(wavelengths, dtype=float)
        self.config = config or PreprocessingConfig()

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "SpectralPreprocessor":
        cfg = self.config
        self.band_dropper_ = BadBandDropper(
            wavelengths=self.wavelengths,
            drop_wavelengths=cfg.drop_wavelengths,
            drop_water_bands=cfg.drop_water_bands,
            enabled=cfg.drop_bad_bands,
        )
        self.band_dropper_.fit(X, y)
        aligned_wl = self.band_dropper_.get_aligned_wavelengths()

        self.sanitizer_ = ReflectanceSanitizer(
            clip_min=cfg.clip_min,
            clip_max=cfg.clip_max,
            scale_mode=cfg.scale_mode,
            enabled=True,
        )
        self.savgol_ = SavitzkyGolaySmoother(
            window_length=cfg.savgol_window,
            polyorder=cfg.savgol_polyorder,
            enabled=cfg.use_savgol,
        )
        self.scatter_norm_ = SpectralScatterNormalizer(
            method=cfg.normalization,
            enabled=cfg.normalization != "none",
        )
        self.derivative_ = FirstDerivativeSpectra(
            wavelengths=aligned_wl,
            use_wavelength_spacing=True,
            enabled=cfg.use_first_derivative,
        )

        self.pipeline_ = Pipeline(
            steps=[
                ("drop_bad_bands", self.band_dropper_),
                ("sanitize_reflectance", self.sanitizer_),
                ("savgol_smooth", self.savgol_),
                ("scatter_norm", self.scatter_norm_),
                ("first_derivative", self.derivative_),
            ]
        )
        self.pipeline_.fit(X, y)
        self.wavelengths_out_ = aligned_wl
        self.dropped_wavelengths_ = self.band_dropper_.dropped_wavelengths_.copy()
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return self.pipeline_.transform(X)

    def transform_reflectance_only(self, X: np.ndarray) -> np.ndarray:
        """Transform up through Savitzky-Golay smoothing WITHOUT zero-centering SNV or derivative.

        Used by Day 4 vegetation indices (NDVI/NDRE/PRI/MCARI) so ratios remain well-conditioned.
        """
        Xt = self.band_dropper_.transform(X)
        Xt = self.sanitizer_.transform(Xt)
        Xt = self.savgol_.transform(Xt)
        return Xt

    def get_aligned_wavelengths(self) -> np.ndarray:
        return self.wavelengths_out_.copy()


def make_leak_free_train_test_indices(
    labels: np.ndarray,
    group_ids: pd.DataFrame,
    n_splits: int = 5,
    test_fold: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic StratifiedGroupKFold split grouped by plant_id to eliminate plant leakage."""
    plants = group_ids["plant_id"].to_numpy()
    unique_plants = pd.Series(plants).nunique()
    splits = min(n_splits, max(2, unique_plants))
    sgkf = StratifiedGroupKFold(n_splits=splits)
    folds = list(sgkf.split(np.zeros(len(labels)), labels, groups=plants))
    fold_idx = test_fold % len(folds)
    return folds[fold_idx]


def run_preprocessing_pipeline(
    source: DatasetSource = "primary",
    config: PreprocessingConfig | None = None,
    save_outputs: bool = True,
) -> dict:
    """Done-when criterion: Run end to end from raw data with one function call.

    Loads raw data via src/data.py, removes broken NaN scans, splits cleanly by plant_id,
    fits preprocessing ONLY on training data, transforms train & test without leakage,
    and saves processed arrays + aligned wavelengths to data/processed/.
    """
    cfg = config or PreprocessingConfig()
    ds: SpectralDataset = load_dataset(source=source, drop_unlabeled=True)
    X_clean, y_clean, groups_clean, dropped_nan_rows = remove_nan_spectral_rows(
        ds.spectra, ds.labels, ds.group_ids
    )

    train_idx, test_idx = make_leak_free_train_test_indices(y_clean, groups_clean)
    X_train_raw, X_test_raw = X_clean[train_idx], X_clean[test_idx]
    y_train, y_test = y_clean[train_idx], y_clean[test_idx]

    preprocessor = SpectralPreprocessor(wavelengths=ds.wavelengths, config=cfg)
    X_train_proc = preprocessor.fit_transform(X_train_raw, y_train)
    X_test_proc = preprocessor.transform(X_test_raw)
    aligned_wl = preprocessor.get_aligned_wavelengths()

    if save_outputs:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        out_npz = PROCESSED_DIR / f"{source}_day3_preprocessed.npz"
        np.savez(
            out_npz,
            X_train=X_train_proc,
            X_test=X_test_proc,
            y_train=y_train,
            y_test=y_test,
            wavelengths=aligned_wl,
            train_idx=train_idx,
            test_idx=test_idx,
        )
        manifest = {
            "source": source,
            "config": cfg.to_dict(),
            "raw_labeled_rows": int(len(ds.labels)),
            "dropped_nan_rows": dropped_nan_rows,
            "clean_rows": int(len(y_clean)),
            "train_rows": int(len(train_idx)),
            "test_rows": int(len(test_idx)),
            "train_plants": int(groups_clean.iloc[train_idx]["plant_id"].nunique()),
            "test_plants": int(groups_clean.iloc[test_idx]["plant_id"].nunique()),
            "wavelengths_in_nm": [float(w) for w in ds.wavelengths],
            "wavelengths_out_nm": [float(w) for w in aligned_wl],
            "dropped_wavelengths_nm": [float(w) for w in preprocessor.dropped_wavelengths_],
            "effective_savgol_window": int(preprocessor.savgol_.effective_window_length_),
            "effective_savgol_polyorder": int(preprocessor.savgol_.effective_polyorder_),
            "output_npz": str(out_npz.relative_to(ROOT_DIR)),
        }
        (PROCESSED_DIR / f"{source}_day3_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    else:
        manifest = {
            "source": source,
            "config": cfg.to_dict(),
            "clean_rows": int(len(y_clean)),
            "train_rows": int(len(train_idx)),
            "test_rows": int(len(test_idx)),
            "wavelengths_out_nm": [float(w) for w in aligned_wl],
            "dropped_wavelengths_nm": [float(w) for w in preprocessor.dropped_wavelengths_],
        }

    return {
        "dataset": ds,
        "preprocessor": preprocessor,
        "X_clean_raw": X_clean,
        "y_clean": y_clean,
        "groups_clean": groups_clean,
        "train_idx": train_idx,
        "test_idx": test_idx,
        "X_train_proc": X_train_proc,
        "X_test_proc": X_test_proc,
        "y_train": y_train,
        "y_test": y_test,
        "aligned_wavelengths": aligned_wl,
        "manifest": manifest,
    }


if __name__ == "__main__":
    for src in ("primary", "synthetic"):
        res = run_preprocessing_pipeline(source=src, save_outputs=True)
        m = res["manifest"]
        print(
            f"[{src}] train={m['train_rows']} test={m['test_rows']} "
            f"| bands {len(m['wavelengths_in_nm'])} -> {len(m['wavelengths_out_nm'])} "
            f"| dropped={m['dropped_wavelengths_nm']} | saved={m['output_npz']}"
        )
