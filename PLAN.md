# TerraSpectra: Project Master Plan & Architectural Roadmap

## 1. Executive Summary & Scientific Purpose

**TerraSpectra** is an advanced scientific agricultural remote sensing platform designed to transition agricultural plant pathology from reactive post-symptomatic inspection (standard 3-channel RGB computer vision) to pre-symptomatic, bio-physiologically grounded spectral intelligence.

By analyzing contiguous hyperspectral data cubes across the Visible and Near-Infrared spectrum (VNIR: 400nm – 1000nm), TerraSpectra:
- Identifies subtle foliar cellular breakdown and chlorophyll degradation days before visible lesions appear.
- Separates general abiotic stress (moisture deficit, nitrogen deficiency) from confirmed pathogen infections.
- Couples longitudinal spectral deterioration rates with microclimatic variables (temperature, relative humidity, leaf wetness, rainfall) to project a 7-day epidemiological disease risk trajectory.
- Employs Explainable AI (SHAP-approximated spectral attribution) to highlight the exact biological wavelengths driving diagnostic decisions.

---

## 2. Core Architectural System Diagram

```
+-----------------------------------------------------------------------------------+
|                            HYPERSPECTRAL INGESTION                                |
|  - ENVI Cubes (.hdr / .raw)                                                       |
|  - NumPy Hypercubes (.npy) [Height x Width x Bands] (Bands >= 10)                 |
|  - Calibrated VNIR (400 - 1000 nm)                                                |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                           SPECTRAL ANALYSIS ENGINE                                |
|  - Spatial Mean Spectral Signature Extraction                                    |
|  - Savitzky-Golay Denoising (Polynomial Order 2, Window 7)                        |
|  - Continuum Removal (Convex Hull Normalization)                                  |
|  - Narrowband Physiological Vegetation Indices:                                    |
|      * NDVI (800nm vs 670nm)  * NDRE (800nm vs 720nm)                             |
|      * PRI  (531nm vs 570nm)  * WBI  (900nm vs 970nm)                             |
|      * PSRI (680nm/500nm/750nm) * MCARI (705nm/670nm/570nm)                       |
|  - PCA Dimensionality Reduction & Loading Attributions                            |
+------------------------------------------+----------------------------------------+
                                           |
         +---------------------------------+--------------------------------+
         |                                 |                                |
         v                                 v                                v
+------------------+             +--------------------+            +-----------------+
| ML CLASSIFIER    |             | EARLY STRESS       |            | EXPLAINABLE AI  |
| - 100-Tree RF    |             | - Water Deficit    |            | - Band-wise     |
| - RBF SVM        |             | - Chlorosis Drop   |            |   SHAP Scores   |
| - 6 Target       |             | - Photochemical    |            | - Biological    |
|   Pathologies    |             |   Depression       |            |   Domain Map    |
+--------+---------+             +---------+----------+            +--------+--------+
         |                                 |                                |
         +---------------------------------+--------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                     7-DAY EPIDEMIOLOGICAL FORECASTING ENGINE                      |
|  - Longitudinal Spectral Vulnerability Slope                                      |
|  - Open-Meteo Microclimate Telemetry (Temp, RH %, Precipitation)                  |
|  - Pathogen-Specific Sporulation Favorability (Rust, Mildew, Blight)               |
|  - Expanding Horizon Confidence Intervals [CI_lower, CI_upper]                    |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                     PRESENTATION & PERSISTENCE SERVICES                           |
|  - SQLite Research Database (Scans, Predictions, Statistics)                      |
|  - Geospatial Heatmap Engine (Deck.gl / Mapbox GeoJSON Risk Grid)                 |
|  - Tabular Scientific Export (CSV agronomic reports)                              |
|  - React 18 Scientific Dashboard (Single-Port or Dev Mode)                        |
+-----------------------------------------------------------------------------------+
```

---

## 3. Current Implementation Status

| Component | Status | Description |
| :--- | :--- | :--- |
| **Data Ingestion Engine** | Completed | Robust ENVI (`.hdr`/`.raw`) and NumPy (`.npy`) cube parser with >= 10 band validation and dimensional safety guards. |
| **Spectral Engine** | Completed | Full implementation of Savitzky-Golay, continuum removal, PCA, and 6 narrowband vegetation indices. |
| **ML Classification Ensemble** | Completed | Dual Random Forest + RBF Support Vector Classifier with 6 foliar conditions, calibrated on VNIR profiles. |
| **Model Persistence & Cache** | Completed | Automatic model artifact caching (`saved_ensemble.joblib`), reducing inference cold starts from 3.7s to 0.26s. |
| **Early Stress Analysis** | Completed | Quantitative distinction between sub-visual abiotic stressors and confirmed foliar infections. |
| **7-Day Risk Forecasting** | Completed | Multi-modal coupling of spectral deterioration slope with agro-meteorological favorability models. |
| **Explainable AI (XAI)** | Completed | Band-wise Shapley feature attribution mapping to 6 biological spectral domains. |
| **Geospatial Risk Heatmap** | Completed | Georeferenced GeoJSON polygon generator for interactive Deck.gl / Mapbox risk overlays. |
| **Research Database & API** | Completed | SQLite persistent logging with FastAPI endpoints, OpenAPI documentation, and CSV report export. |
| **Deep Learning Hybrid** | Model Trained | PyTorch 3D-CNN + Vision Transformer (`Hybrid3DCNN_ViT`) architecture with saved weights in `ml/saved_models/`. |
| **Scientific Frontend** | Built | Interactive React 18 single-page dashboard with real-time charts, index dials, and XAI inspector. |
| **Automated Test Suite** | Verified | Scientific engine unit tests passing 100% in 0.26s with dynamic cross-environment path resolution. |

---

## 4. Phase-Wise Roadmap for Future Milestones

### Phase 1: Stabilization, Packaging & CI/CD (Immediate)
- [x] Fix hardcoded repository paths across test suites to ensure portable cross-platform execution.
- [x] Add root endpoint (`/`) alias to health check for direct API verification.
- [x] Implement automatic ML model serialization caching (`saved_ensemble.joblib`) for ultra-fast startup.
- [ ] Add pre-build npm script to compile `frontend/dist` automatically during Docker and production startup.
- [ ] Implement GitHub Actions CI pipeline running unit tests on Python 3.10, 3.11, and 3.12.

### Phase 2: Deep Learning Integration & Batch GPU Acceleration
- [ ] Connect the pre-trained `Hybrid3DCNN_ViT` PyTorch model (`hybrid_3dcnn_vit.pt`) into the active FastAPI inference pipeline alongside the RF/SVM ensemble.
- [ ] Support sub-patch spatial sampling $(9 \times 9)$ across high-resolution hypercubes for spatial lesion localization.
- [ ] Add ONNX Runtime export for low-latency CPU and edge deployment.

### Phase 3: Satellite & Airborne Multispectral Sensor Ingestion
- [ ] Expand cube parser to support GeoTIFF / Cloud-Optimized GeoTIFF (COG) formats.
- [ ] Add sensor-specific band calibration profiles for Sentinel-2 MSI, Landsat 8/9 OLI, PRISMA, and EnMAP.
- [ ] Include automated atmospheric correction and surface reflectance scaling.

### Phase 4: Pathogen Library & Agronomic Extension
- [ ] Extend diagnostic taxonomy beyond wheat to include maize (Northern Corn Leaf Blight, Grey Leaf Spot), rice (Blast, Bacterial Blight), and soybean (Rust).
- [ ] Integrate chemical and biological treatment recommendation protocols tied to severity levels.
- [ ] Enable multi-temporal repeat scan comparison for field progression monitoring over 14-30 day flight windows.

### Phase 5: Field Pilot & Edge Deployment
- [ ] Package lightweight inference container for drone-mounted edge compute payloads (NVIDIA Jetson / Raspberry Pi).
- [ ] Connect live weather telemetry caching with offline fallback synchronization.
- [ ] Conduct field validation trials with agronomic partner institutions.

---

## 5. Testing & Validation Protocol

To verify platform functionality, run:

1. **Scientific Processing Unit Tests**:
   ```bash
   python -m unittest tests/test_scientific_engine.py
   ```
2. **Synthetic Data Generation**:
   ```bash
   python scripts/generate_envi_datasets.py
   ```
3. **Interactive API Verification**:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   Navigate to `http://localhost:8000/docs` to test endpoints via Swagger UI.

