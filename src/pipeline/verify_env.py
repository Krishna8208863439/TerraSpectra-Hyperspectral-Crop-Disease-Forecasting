"""Day 1 Block 3: Environment & Core Stack Import Verification.

Verifies that Python and every required package in requirements.txt
(NumPy, pandas, scikit-learn, XGBoost, matplotlib, spectral) can be imported cleanly.
Outputs either a human-readable report or structured JSON (--json).
"""

from __future__ import annotations

import importlib
import json
import platform
import sys
from pathlib import Path

REQUIRED_PACKAGES = [
    ("numpy", "NumPy", "1.26.0"),
    ("pandas", "pandas", "2.2.0"),
    ("sklearn", "scikit-learn", "1.5.0"),
    ("xgboost", "XGBoost", "2.1.0"),
    ("matplotlib", "matplotlib", "3.9.0"),
    ("spectral", "spectral (SPy)", "0.23.1"),
]


def check_environment() -> dict:
    results = []
    all_ok = True

    for module_name, display_name, min_version in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(module_name)
            version = getattr(mod, "__version__", "unknown")
            results.append(
                {
                    "module": module_name,
                    "name": display_name,
                    "min_version": min_version,
                    "installed_version": version,
                    "status": "ok",
                    "error": None,
                }
            )
        except Exception as exc:
            all_ok = False
            results.append(
                {
                    "module": module_name,
                    "name": display_name,
                    "min_version": min_version,
                    "installed_version": None,
                    "status": "missing",
                    "error": str(exc),
                }
            )

    return {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "all_ok": all_ok,
        "packages": results,
    }


def main() -> int:
    report = check_environment()
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        print(f"Python {report['python_version']} ({report['python_executable']})")
        print("-" * 60)
        for pkg in report["packages"]:
            status_label = "PASS" if pkg["status"] == "ok" else "FAIL"
            ver = pkg["installed_version"] or pkg["error"]
            print(f"[{status_label}] {pkg['name']:<16} {ver}")
        print("-" * 60)
        print("Environment status:", "ALL IMPORTS SUCCEEDED" if report["all_ok"] else "MISSING PACKAGES")

    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
