"""Day 1 Fallback #3: Synthetic Leaf Spectral Disease Generator (Clearly Labeled Synthetic).

Provides a reproducible synthetic leaf-level hyperspectral dataset (400-1000 nm, 10 nm step)
with controlled chlorophyll degradation, red-edge blue-shift, and NIR mesophyll drop
across multi-day plant observations. Used strictly when real data is unavailable or for
unit-testing leak-free Plant_ID / Plot_ID / Date splits.
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT_DIR / "data" / "raw" / "synthetic_leaf_disease_spectra_v1.csv"

WAVELENGTHS = list(range(400, 1001, 10))
STAGES = ["Healthy", "Early_Chlorosis", "Moderate_Blight", "Severe_Necrosis"]


def _gaussian(x: float, mu: float, sigma: float, amp: float) -> float:
    return amp * math.exp(-0.5 * ((x - mu) / sigma) ** 2)


def simulate_leaf_spectrum(stage: str, day_idx: int, rng: random.Random) -> list[float]:
    severity_map = {
        "Healthy": 0.05 + 0.01 * day_idx,
        "Early_Chlorosis": 0.25 + 0.04 * day_idx,
        "Moderate_Blight": 0.55 + 0.05 * day_idx,
        "Severe_Necrosis": 0.85 + 0.03 * day_idx,
    }
    sev = min(1.0, max(0.0, severity_map[stage]))
    plant_bias = rng.gauss(0.0, 0.012)

    values: list[float] = []
    for wl in WAVELENGTHS:
        # Base healthy leaf reflectance: green peak (~550nm), red absorption (~670nm), NIR plateau (~760-950nm)
        green_peak = _gaussian(wl, 552.0, 32.0, 0.14 - 0.03 * sev)
        red_chlorophyll_absorption = -_gaussian(wl, 672.0, 26.0, 0.12 * (1.0 - 0.72 * sev))
        # Red-edge inflection shifts blueward under stress (720 -> 702 nm)
        red_edge_center = 722.0 - 18.0 * sev
        nir_plateau = (0.48 - 0.17 * sev) / (1.0 + math.exp(-(wl - red_edge_center) / 14.0))
        vis_baseline = 0.04 + 0.08 * sev * max(0.0, (wl - 450.0) / 250.0) if wl < 710 else 0.04
        water_dip_970 = -_gaussian(wl, 970.0, 22.0, 0.035 * (1.0 - 0.4 * sev))

        reflectance = vis_baseline + green_peak + red_chlorophyll_absorption + nir_plateau + water_dip_970
        reflectance += plant_bias + rng.gauss(0.0, 0.005)
        values.append(round(max(0.01, min(0.85, reflectance)), 5))
    return values


def generate_csv(seed: int = 42) -> Path:
    rng = random.Random(seed)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    band_headers = [f"band_{wl}nm" for wl in WAVELENGTHS]
    headers = [
        "sample_id",
        "plant_id",
        "plot_id",
        "field_id",
        "acquisition_date",
        "day_index",
        "disease_label",
        "data_origin",
        *band_headers,
    ]

    dates = ["2026-11-02", "2026-11-05", "2026-11-08", "2026-11-11", "2026-11-14"]
    rows: list[list[str | int | float]] = []

    sample_counter = 1
    for field_idx in range(1, 3):
        field_id = f"FIELD_{field_idx:02d}"
        for plot_idx in range(1, 4):
            plot_id = f"F{field_idx}_PLOT_{plot_idx:02d}"
            for plant_local in range(1, 5):
                plant_id = f"PLANT_{field_idx}_{plot_idx}_{plant_local:02d}"
                base_stage_idx = (plant_local + plot_idx) % 4
                for d_idx, acq_date in enumerate(dates):
                    # Progressive stress trajectory across dates for stressed plants
                    if base_stage_idx == 0:
                        stage = "Healthy"
                    else:
                        prog_idx = min(3, base_stage_idx + (1 if d_idx >= 3 and base_stage_idx < 3 else 0))
                        stage = STAGES[prog_idx]
                    spectrum = simulate_leaf_spectrum(stage, d_idx, rng)
                    rows.append(
                        [
                            f"SYN_{sample_counter:04d}",
                            plant_id,
                            plot_id,
                            field_id,
                            acq_date,
                            d_idx,
                            stage,
                            "SYNTHETIC_CONTROLLED_STRESS",
                            *spectrum,
                        ]
                    )
                    sample_counter += 1

    with OUT_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)

    return OUT_PATH


if __name__ == "__main__":
    path = generate_csv()
    print(f"Generated synthetic dataset at {path}")
