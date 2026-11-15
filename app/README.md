# App Directory (`app/`)

This directory holds application integration documentation and entry points for the SpectralCrop interactive Day 1 workbench and downstream detection + temporal forecasting UI.

## Runtime Architecture

- **Backend Server (`../server.ts`)**: Express server running on port `3000` with `vite.middlewares` mounted in development. Exposes `/api/*` endpoints for:
  - `/api/repo/status`: Audits repository folder structure (`data/`, `notebooks/`, `src/`, `reports/`, `app/`, `docs/`), Git commit state, and Day 1 deliverable checklist.
  - `/api/env/verify`: Executes `python3 src/pipeline/verify_env.py` in real time to verify Python version and test imports for `numpy`, `pandas`, `sklearn`, `xgboost`, `matplotlib`, and `spectral`.
  - `/api/docs` & `/api/docs/:name`: Reads and saves `docs/project_brief.md`, `docs/dataset_note.md`, `docs/mentor_message.md`, and `README.md`.
  - `/api/dataset/summary`: Parses the selected spectral dataset in `data/raw/` to return actual shape, label distribution, wavelength grid, mean reflectance curves per class, and grouping columns (`plant_id`, `leaf_id`, `plot_id`, `date`) required for Day 2 EDA and Day 5 leak-free splits.
- **Frontend Workbench (`../src/`)**: React + TypeScript + Tailwind CSS interactive console for verifying environment checks, reviewing dataset candidates across Kaggle/Zenodo/Mendeley/IEEE DataPort, inspecting spectral curves, and editing/exporting Day 1 artifacts.
