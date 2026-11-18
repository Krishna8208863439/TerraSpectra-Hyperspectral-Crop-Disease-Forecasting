import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  FileSpreadsheet,
  GitBranch,
  Play,
  RefreshCw,
  Sliders,
  TrendingUp,
  Upload,
} from 'lucide-react';
import type {
  CsvBatchPredictionResult,
  EarlyDetectionSummary,
  InferenceSamplesPayload,
  PlantForecastResult,
  SpectrumPredictionResult,
} from '../types/day1';

interface LiveInferenceViewProps {
  source: 'primary' | 'synthetic';
  onChangeSource: (src: 'primary' | 'synthetic') => void;
}

const SAMPLE_CSV_PRIMARY = `Sample_ID,Plant_ID,date,Mean_365,Mean_460,Mean_525,Mean_570,Mean_645,Mean_670,Mean_700,Mean_780,Mean_890,Mean_970
Scan_Healthy_A,P_Test_01,03-22-19,3.8,3.5,6.9,6.4,6.8,4.6,7.9,22.4,22.1,19.8
Scan_Drought_Early,P_Test_02,03-26-19,4.1,4.2,7.1,7.3,8.9,6.5,8.4,19.2,18.9,17.2
Scan_Drought_Late,P_Test_03,04-02-19,4.3,4.9,7.6,8.2,10.8,8.4,9.5,17.1,16.8,15.3`;

const BAND_ROLE_MAP: Record<number, string> = {
  365: 'UV (dropped)',
  460: 'Blue Chl-b',
  525: 'Green PRI-ref',
  570: 'Yellow-Green',
  645: 'Red Pigment',
  670: 'Chl-a Absorp',
  700: 'Red-Edge Inflect',
  780: 'NIR Shoulder',
  890: 'NIR Plateau',
  970: 'Water Trough',
};

export const LiveInferenceView: React.FC<LiveInferenceViewProps> = ({
  source,
  onChangeSource,
}) => {
  const [subMode, setSubMode] = useState<'classifier' | 'csv' | 'forecaster'>('classifier');
  const [samples, setSamples] = useState<InferenceSamplesPayload | null>(null);
  const [samplesLoading, setSamplesLoading] = useState<boolean>(false);

  // Single-spectrum interactive state
  const [activeModel, setActiveModel] = useState<'xgboost' | 'random_forest' | 'svm' | 'plsda'>('xgboost');
  const [bandValues, setBandValues] = useState<Record<string, number>>({});
  const [selectedPresetLabel, setSelectedPresetLabel] = useState<string>('');
  const [predResult, setPredResult] = useState<SpectrumPredictionResult | null>(null);
  const [predLoading, setPredLoading] = useState<boolean>(false);
  const [hoverBandIdx, setHoverBandIdx] = useState<number | null>(null);

  // CSV batch scoring state
  const [csvText, setCsvText] = useState<string>(SAMPLE_CSV_PRIMARY);
  const [csvResult, setCsvResult] = useState<CsvBatchPredictionResult | null>(null);
  const [csvLoading, setCsvLoading] = useState<boolean>(false);
  const [csvError, setCsvError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Plant trajectory forecaster & early-detection state
  const [selectedPlantId, setSelectedPlantId] = useState<string>('');
  const [horizon, setHorizon] = useState<1 | 2 | 3>(3);
  const [plantForecast, setPlantForecast] = useState<PlantForecastResult | null>(null);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);
  const [earlySummary, setEarlySummary] = useState<EarlyDetectionSummary | null>(null);
  const [hoverStepIdx, setHoverStepIdx] = useState<number | null>(null);

  const runSinglePrediction = useCallback(
    async (bands: Record<string, number>, model: string, src: 'primary' | 'synthetic') => {
      if (Object.keys(bands).length === 0) return;
      setPredLoading(true);
      try {
        const res = await fetch('/api/predict/spectrum', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: src, bands, model }),
        });
        if (res.ok) {
          setPredResult(await res.json());
        }
      } finally {
        setPredLoading(false);
      }
    },
    []
  );

  const runPlantForecast = useCallback(
    async (plantId: string, k: number, src: 'primary' | 'synthetic') => {
      setForecastLoading(true);
      try {
        const res = await fetch('/api/predict/forecast', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: src, plant_id: plantId, horizon: k }),
        });
        if (res.ok) {
          const data: PlantForecastResult = await res.json();
          setPlantForecast(data);
          if (!plantId && data.plant_id) setSelectedPlantId(data.plant_id);
        }
      } finally {
        setForecastLoading(false);
      }
    },
    []
  );

  // Load unseen samples & early detection whenever dataset source switches
  useEffect(() => {
    let cancelled = false;
    setSamplesLoading(true);
    Promise.all([
      fetch(`/api/predict/samples?source=${source}`).then((r) => (r.ok ? r.json() : null)),
      fetch(`/api/early-detection?source=${source}`).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([sampData, edData]: [InferenceSamplesPayload | null, EarlyDetectionSummary | null]) => {
        if (cancelled) return;
        setSamples(sampData);
        setEarlySummary(edData);
        if (sampData && sampData.sample_presets.length > 0) {
          const firstPreset = sampData.sample_presets[0];
          setBandValues(firstPreset.raw_bands);
          setSelectedPresetLabel(`${firstPreset.sample_id} · ${firstPreset.true_label} (${firstPreset.date})`);
          runSinglePrediction(firstPreset.raw_bands, activeModel, source);
        }
        if (sampData && sampData.plants.length > 0) {
          const firstStressedHoldout =
            sampData.plants.find((p) => p.split === 'holdout_test' && p.true_label !== sampData.class_names[0]) ||
            sampData.plants[0];
          setSelectedPlantId(firstStressedHoldout.plant_id);
          runPlantForecast(firstStressedHoldout.plant_id, horizon, source);
        }
      })
      .finally(() => {
        if (!cancelled) setSamplesLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [source]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectPreset = (presetIndex: number) => {
    if (!samples) return;
    const preset = samples.sample_presets[presetIndex];
    if (!preset) return;
    setBandValues(preset.raw_bands);
    setSelectedPresetLabel(`${preset.sample_id} · ${preset.true_label} (${preset.date})`);
    runSinglePrediction(preset.raw_bands, activeModel, source);
  };

  const handleModelChange = (nextModel: 'xgboost' | 'random_forest' | 'svm' | 'plsda') => {
    setActiveModel(nextModel);
    if (Object.keys(bandValues).length > 0) {
      runSinglePrediction(bandValues, nextModel, source);
    }
  };

  const handleApplyStressShift = (intensity: 'healthy' | 'stressed') => {
    if (!samples) return;
    const next = { ...bandValues };
    for (const wl of samples.wavelengths_nm) {
      const key = String(Math.round(wl));
      const base = next[key] ?? 10;
      if (intensity === 'stressed') {
        // Biological stress: higher red reflectance (chlorophyll loss), lower NIR shoulder/plateau
        if (wl >= 620 && wl <= 705) next[key] = Number(Math.min(45, base * 1.28).toFixed(2));
        else if (wl >= 750) next[key] = Number(Math.max(5, base * 0.86).toFixed(2));
      } else {
        // Healthy turgid leaf: deeper Chl absorption @ 670nm, stronger NIR @ 780-890nm
        if (wl >= 620 && wl <= 705) next[key] = Number(Math.max(2, base * 0.78).toFixed(2));
        else if (wl >= 750) next[key] = Number(Math.min(55, base * 1.15).toFixed(2));
      }
    }
    setSelectedPresetLabel(intensity === 'stressed' ? 'Custom Perturbed (Stress Simulation)' : 'Custom Perturbed (Healthy Leaf)');
    setBandValues(next);
    runSinglePrediction(next, activeModel, source);
  };

  const handleRunCsvBatch = async () => {
    setCsvLoading(true);
    setCsvError('');
    try {
      const res = await fetch('/api/predict/csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, csv_text: csvText, model: activeModel }),
      });
      const data = await res.json();
      if (!res.ok) {
        setCsvError(data.error || 'CSV scoring failed');
      } else {
        setCsvResult(data);
      }
    } catch {
      setCsvError('Network error while running CSV inference');
    } finally {
      setCsvLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setCsvText(reader.result);
      }
    };
    reader.readAsText(file);
  };

  const sliderWavelengths = useMemo(() => {
    if (!samples) return [];
    const list = samples.aligned_wavelengths_nm;
    // For synthetic 60-band data, expose 10 key diagnostic wavelengths along the curve
    if (list.length > 14) {
      const picks = [460, 520, 550, 570, 640, 670, 700, 720, 780, 890, 970];
      return list.filter((w) => picks.includes(Math.round(w)));
    }
    return list;
  }, [samples]);

  // Helper SVG coordinates for Spectrum Classifier Plot
  const spectrumChartGeom = useMemo(() => {
    if (!predResult || predResult.reflectance_curve.length === 0) return null;
    const w = 680;
    const h = 250;
    const padL = 46;
    const padR = 20;
    const padT = 18;
    const padB = 34;

    const pts = predResult.reflectance_curve;
    const allWls = pts.map((p) => p.wavelength_nm);
    const minWl = Math.min(...allWls);
    const maxWl = Math.max(...allWls);

    const refKeys = Object.keys(predResult.reference_curves);
    const allY = pts.map((p) => p.reflectance);
    for (const k of refKeys) {
      for (const r of predResult.reference_curves[k]) {
        allY.push(r.mean + r.std, Math.max(0, r.mean - r.std));
      }
    }
    const maxY = Math.max(30, Math.ceil(Math.max(...allY) / 5) * 5);

    const xOf = (wl: number) =>
      padL + ((wl - minWl) / Math.max(1, maxWl - minWl)) * (w - padL - padR);
    const yOf = (val: number) =>
      h - padB - (Math.max(0, Math.min(maxY, val)) / maxY) * (h - padT - padB);

    return { w, h, padL, padR, padT, padB, minWl, maxWl, maxY, xOf, yOf, pts, refKeys };
  }, [predResult]);

  // Helper SVG coordinates for Plant Trajectory Forecaster Plot
  const forecastChartGeom = useMemo(() => {
    if (!plantForecast || plantForecast.history.length === 0) return null;
    const w = 700;
    const h = 255;
    const padL = 48;
    const padR = 22;
    const padT = 20;
    const padB = 36;

    const combinedDays = [
      ...plantForecast.history.map((p) => p.day_offset),
      ...plantForecast.future.map((p) => p.day_offset),
    ];
    const minD = Math.min(...combinedDays);
    const maxD = Math.max(...combinedDays, minD + 1);

    const allVals = [
      ...plantForecast.history.map((p) => p.actual_ndvi),
      ...plantForecast.history.map((p) => p.healthy_cohort_ndvi),
      ...plantForecast.future.map((p) => p.lag_rf_ndvi),
      ...plantForecast.future.map((p) => p.persistence_ndvi),
    ];
    const minV = Math.max(-0.2, Math.floor((Math.min(...allVals) - 0.05) * 20) / 20);
    const maxV = Math.min(1.0, Math.ceil((Math.max(...allVals) + 0.05) * 20) / 20);

    const xOf = (d: number) => padL + ((d - minD) / Math.max(1, maxD - minD)) * (w - padL - padR);
    const yOf = (v: number) =>
      h - padB - ((v - minV) / Math.max(0.05, maxV - minV)) * (h - padT - padB);

    return { w, h, padL, padR, padT, padB, minD, maxD, minV, maxV, xOf, yOf };
  }, [plantForecast]);

  const isStressPredicted =
    predResult &&
    samples &&
    predResult.predicted_class !== samples.class_names[0];

  return (
    <div className="space-y-6">
      {/* Control Ribbon: Mode Selector + Dataset Switcher */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg">
          {[
            { id: 'classifier', label: '1. Live Spectrum Classifier', icon: Activity },
            { id: 'csv', label: '2. Batch CSV Upload Scorer', icon: FileSpreadsheet },
            { id: 'forecaster', label: '3. Trajectory Forecaster & Early Detection', icon: TrendingUp },
          ].map((item) => {
            const Icon = item.icon;
            const active = subMode === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSubMode(item.id as typeof subMode)}
                className={`inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  active ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${active ? 'text-teal-700' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
            <button
              type="button"
              onClick={() => onChangeSource('primary')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                source === 'primary' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
              }`}
            >
              Zenodo Field Drought (10 bands)
            </button>
            <button
              type="button"
              onClick={() => onChangeSource('synthetic')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                source === 'synthetic' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
              }`}
            >
              Disease Hyperspectral (61 bands)
            </button>
          </div>
        </div>
      </div>

      {/* MODE 1: LIVE INTERACTIVE SPECTRUM CLASSIFIER */}
      {subMode === 'classifier' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Control Column */}
          <div className="lg:col-span-4 bg-white border border-slate-200 rounded-lg p-5 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-teal-700" />
                  <span>Leaf Spectrometer Input</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Unseen holdout plant scans or custom band calibration
                </p>
              </div>
              {samplesLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin text-teal-700" />}
            </div>

            {/* Unseen Holdout Sample Presets */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">
                Load Held-Out Validation Plant Scan
              </label>
              <select
                value={selectedPresetLabel}
                onChange={(e) => {
                  const idx = Number(e.target.selectedIndex);
                  handleSelectPreset(idx);
                }}
                className="w-full text-xs font-mono bg-slate-50 border border-slate-200 rounded-md px-2.5 py-2 text-slate-800"
              >
                {(samples?.sample_presets || []).map((p) => {
                  const labelText = `${p.sample_id} · ${p.true_label} (${p.date})`;
                  return (
                    <option key={p.sample_id} value={labelText}>
                      {labelText}
                    </option>
                  );
                })}
              </select>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => handleApplyStressShift('healthy')}
                  className="px-2.5 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 rounded hover:bg-emerald-100 cursor-pointer"
                >
                  Simulate Healthy Leaf
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyStressShift('stressed')}
                  className="px-2.5 py-1.5 text-xs font-medium bg-rose-50 text-rose-800 border border-rose-200 rounded hover:bg-rose-100 cursor-pointer"
                >
                  Simulate Stressed Leaf
                </button>
              </div>
            </div>

            {/* Model Selection */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-700">
                Active Classifier (Trained on Set E)
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {[
                  { id: 'xgboost', name: 'XGBoost' },
                  { id: 'random_forest', name: 'Random Forest' },
                  { id: 'svm', name: 'SVM (RBF)' },
                  { id: 'plsda', name: 'PLS-DA' },
                ].map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => handleModelChange(m.id as typeof activeModel)}
                    className={`px-2.5 py-1.5 text-xs font-medium rounded border text-left transition-colors cursor-pointer ${
                      activeModel === m.id
                        ? 'bg-teal-800 text-white border-teal-800'
                        : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {m.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Spectral Wavelength Sliders */}
            <div className="space-y-2.5 pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">Reflectance Calibration (%)</span>
                <span className="font-mono text-slate-400">SavGol + SNV</span>
              </div>
              <div className="space-y-2 max-h-[310px] overflow-y-auto pr-1">
                {sliderWavelengths.map((wl) => {
                  const key = String(Math.round(wl));
                  const val = bandValues[key] ?? 10;
                  return (
                    <div key={key} className="space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-mono font-semibold text-slate-800">
                          {key} nm{' '}
                          <span className="font-sans font-normal text-slate-400">
                            {BAND_ROLE_MAP[Math.round(wl)] || ''}
                          </span>
                        </span>
                        <span className="font-mono tabular-nums text-teal-800 font-semibold">
                          {val.toFixed(1)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min={0.5}
                        max={65}
                        step={0.2}
                        value={val}
                        onChange={(e) =>
                          setBandValues((prev) => ({
                            ...prev,
                            [key]: Number(e.target.value),
                          }))
                        }
                        className="w-full h-1.5 accent-teal-700 cursor-pointer"
                      />
                    </div>
                  );
                })}
              </div>

              <button
                type="button"
                onClick={() => runSinglePrediction(bandValues, activeModel, source)}
                disabled={predLoading}
                className="w-full mt-2 inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold text-white bg-teal-800 hover:bg-teal-900 disabled:opacity-60 rounded-lg transition-colors cursor-pointer"
              >
                <Play className="w-3.5 h-3.5" />
                <span>{predLoading ? 'Running Python Inference...' : 'Run Live Spectral Prediction'}</span>
              </button>
            </div>
          </div>

          {/* Right Viewport: Diagnosis, Spectral Curve, 4-Model Ensemble & SHAP Drivers */}
          <div className="lg:col-span-8 space-y-6">
            {/* Diagnosis & Biophysical Indices Strip */}
            <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
                    Real-Time Spectral Classification · {predResult?.active_model.toUpperCase() || 'XGBOOST'}
                  </div>
                  <div className="mt-1 flex items-baseline gap-3">
                    <span
                      className={`text-2xl font-bold tracking-tight ${
                        isStressPredicted ? 'text-rose-700' : 'text-teal-800'
                      }`}
                    >
                      {predResult
                        ? `${isStressPredicted ? '▲' : '●'} ${predResult.predicted_class}`
                        : 'Initializing Model...'}
                    </span>
                    {predResult && (
                      <span className="text-xs font-mono tabular-nums text-slate-500">
                        Confidence: <strong className="text-slate-900">{(predResult.confidence * 100).toFixed(1)}%</strong> ·{' '}
                        {predResult.ensemble_agreement}
                      </span>
                    )}
                  </div>
                </div>

                {predResult && (
                  <div className="grid grid-cols-5 gap-2 text-center bg-slate-50 border border-slate-200 rounded-md px-3 py-2">
                    {Object.entries(predResult.vegetation_indices).map(([k, v]) => (
                      <div key={k} className="px-1.5">
                        <div className="text-[10px] font-mono text-slate-500">{k}</div>
                        <div className="text-xs font-mono font-bold tabular-nums text-slate-900 mt-0.5">
                          {k === 'REP_nm' ? `${v.toFixed(1)}` : v.toFixed(3)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Interactive Spectral Curve Chart */}
              {spectrumChartGeom && predResult && (
                <div className="border-t border-slate-100 pt-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2 text-xs">
                    <span className="font-semibold text-slate-800">
                      Sample Reflectance Signature vs. Training Class Envelopes (690–750 nm Red-Edge Shaded)
                    </span>
                    <div className="flex items-center gap-4 font-mono text-[11px]">
                      <span className="text-slate-900 font-semibold">— Active Input</span>
                      <span className="text-teal-700">- - {spectrumChartGeom.refKeys[0]}</span>
                      {spectrumChartGeom.refKeys[1] && (
                        <span className="text-rose-700">- - {spectrumChartGeom.refKeys[1]}</span>
                      )}
                    </div>
                  </div>

                  <div className="relative">
                    <svg
                      viewBox={`0 0 ${spectrumChartGeom.w} ${spectrumChartGeom.h}`}
                      className="w-full h-auto cursor-crosshair select-none"
                      onMouseLeave={() => setHoverBandIdx(null)}
                    >
                      {/* Red-Edge window highlight */}
                      <rect
                        x={spectrumChartGeom.xOf(Math.max(spectrumChartGeom.minWl, 690))}
                        y={spectrumChartGeom.padT}
                        width={Math.max(
                          6,
                          spectrumChartGeom.xOf(Math.min(spectrumChartGeom.maxWl, 750)) -
                            spectrumChartGeom.xOf(Math.max(spectrumChartGeom.minWl, 690))
                        )}
                        height={spectrumChartGeom.h - spectrumChartGeom.padT - spectrumChartGeom.padB}
                        fill="#0f766e"
                        fillOpacity={0.07}
                      />

                      {/* Y Grid Lines */}
                      {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
                        const val = frac * spectrumChartGeom.maxY;
                        const y = spectrumChartGeom.yOf(val);
                        return (
                          <g key={frac}>
                            <line
                              x1={spectrumChartGeom.padL}
                              x2={spectrumChartGeom.w - spectrumChartGeom.padR}
                              y1={y}
                              y2={y}
                              stroke="#e2e8f0"
                              strokeDasharray="2 3"
                            />
                            <text
                              x={spectrumChartGeom.padL - 8}
                              y={y + 3}
                              textAnchor="end"
                              className="fill-slate-400 text-[10px] font-mono"
                            >
                              {val.toFixed(0)}%
                            </text>
                          </g>
                        );
                      })}

                      {/* Class Reference Curves */}
                      {spectrumChartGeom.refKeys.slice(0, 2).map((cname, cIdx) => {
                        const rPts = predResult.reference_curves[cname] || [];
                        const pathD = rPts
                          .map(
                            (p, idx) =>
                              `${idx === 0 ? 'M' : 'L'}${spectrumChartGeom.xOf(p.wavelength_nm).toFixed(1)},${spectrumChartGeom.yOf(p.mean).toFixed(1)}`
                          )
                          .join(' ');
                        const stroke = cIdx === 0 ? '#0f766e' : '#be123c';
                        return (
                          <path
                            key={cname}
                            d={pathD}
                            fill="none"
                            stroke={stroke}
                            strokeWidth={1.75}
                            strokeDasharray="5 4"
                            opacity={0.85}
                          />
                        );
                      })}

                      {/* Active Input Spectrum */}
                      <path
                        d={spectrumChartGeom.pts
                          .map(
                            (p, idx) =>
                              `${idx === 0 ? 'M' : 'L'}${spectrumChartGeom.xOf(p.wavelength_nm).toFixed(1)},${spectrumChartGeom.yOf(p.reflectance).toFixed(1)}`
                          )
                          .join(' ')}
                        fill="none"
                        stroke="#0f172a"
                        strokeWidth={2.5}
                      />

                      {/* Interactive Hover Nodes */}
                      {spectrumChartGeom.pts.map((p, idx) => {
                        const cx = spectrumChartGeom.xOf(p.wavelength_nm);
                        const cy = spectrumChartGeom.yOf(p.reflectance);
                        const active = hoverBandIdx === idx;
                        return (
                          <g key={p.wavelength_nm} onMouseEnter={() => setHoverBandIdx(idx)}>
                            {active && (
                              <line
                                x1={cx}
                                x2={cx}
                                y1={spectrumChartGeom.padT}
                                y2={spectrumChartGeom.h - spectrumChartGeom.padB}
                                stroke="#0f766e"
                                strokeWidth={1}
                              />
                            )}
                            <circle
                              cx={cx}
                              cy={cy}
                              r={active ? 5 : 3}
                              fill={active ? '#0f766e' : '#0f172a'}
                              stroke="#ffffff"
                              strokeWidth={1.2}
                            />
                            {(spectrumChartGeom.pts.length <= 12 || idx % 6 === 0) && (
                              <text
                                x={cx}
                                y={spectrumChartGeom.h - 10}
                                textAnchor="middle"
                                className="fill-slate-500 text-[10px] font-mono"
                              >
                                {Math.round(p.wavelength_nm)}
                              </text>
                            )}
                          </g>
                        );
                      })}
                    </svg>

                    {hoverBandIdx !== null && spectrumChartGeom.pts[hoverBandIdx] && (
                      <div className="mt-1 text-xs font-mono text-slate-700 bg-slate-50 border border-slate-200 rounded px-3 py-1 inline-flex items-center gap-3">
                        <span>
                          λ = <strong>{spectrumChartGeom.pts[hoverBandIdx].wavelength_nm} nm</strong>
                        </span>
                        <span>
                          Reflectance = <strong>{spectrumChartGeom.pts[hoverBandIdx].reflectance.toFixed(2)}%</strong>
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* 4-Model Probability Matrix + Local Attribution Drivers */}
            {predResult && (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                <div className="md:col-span-6 bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-200">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      4-Model Ensemble Consensus (Set E)
                    </h3>
                  </div>
                  <div className="p-4 space-y-3">
                    {predResult.models.map((m) => {
                      const clsKeys = Object.keys(m.probabilities);
                      const primaryStressProb = m.probabilities[clsKeys[1] || clsKeys[0]] ?? m.confidence;
                      return (
                        <div key={m.model_key} className="space-y-1 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-slate-800">{m.model_name}</span>
                            <span className="font-mono tabular-nums font-semibold text-slate-900">
                              {m.predicted_class} ({(m.confidence * 100).toFixed(1)}%)
                            </span>
                          </div>
                          <div className="w-full h-2 bg-slate-100 rounded overflow-hidden flex">
                            <div
                              className="bg-teal-700 h-full"
                              style={{ width: `${(m.probabilities[clsKeys[0]] ?? 0) * 100}%` }}
                            />
                            <div
                              className="bg-rose-600 h-full"
                              style={{ width: `${Math.max(0, 1 - (m.probabilities[clsKeys[0]] ?? 0)) * 100}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] font-mono text-slate-400">
                            <span>{clsKeys[0]}: {((m.probabilities[clsKeys[0]] ?? 0) * 100).toFixed(0)}%</span>
                            <span>{clsKeys[1] || 'Stressed'}: {(primaryStressProb * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="md:col-span-6 bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Local Wavelength &amp; Index Drivers
                    </h3>
                    <span className="text-[11px] font-mono text-slate-400">z vs Healthy</span>
                  </div>
                  <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-2 font-sans font-medium">Feature</th>
                        <th className="px-3 py-2 text-right font-medium">Value</th>
                        <th className="px-3 py-2 text-right font-medium">z-shift</th>
                        <th className="px-3 py-2 text-right font-medium">Impact</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {predResult.drivers.slice(0, 6).map((d) => (
                        <tr key={d.feature}>
                          <td className="px-3 py-2 font-semibold text-slate-800">{d.feature}</td>
                          <td className="px-3 py-2 text-right text-slate-600">{d.value.toFixed(3)}</td>
                          <td className="px-3 py-2 text-right text-slate-500">
                            {d.z_vs_healthy >= 0 ? `+${d.z_vs_healthy.toFixed(2)}` : d.z_vs_healthy.toFixed(2)}
                          </td>
                          <td
                            className={`px-3 py-2 text-right font-semibold ${
                              d.contribution >= 0 ? 'text-rose-700' : 'text-teal-700'
                            }`}
                          >
                            {d.contribution >= 0 ? `+${d.contribution.toFixed(3)}` : d.contribution.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODE 2: BATCH CSV SPECTRUM UPLOADER */}
      {subMode === 'csv' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-5 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Upload or Paste Spectral CSV</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Auto-detects <code className="font-mono">Mean_*</code>, <code className="font-mono">band_*nm</code>, or numeric λ headers
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer"
              >
                <Upload className="w-3.5 h-3.5 text-teal-700" />
                <span>Choose .CSV</span>
              </button>
            </div>

            <textarea
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              rows={9}
              className="w-full font-mono text-[11px] leading-relaxed bg-slate-50 border border-slate-200 rounded-md p-3 text-slate-800 focus:outline-none focus:border-teal-700"
              placeholder="Paste spectral reflectance CSV rows here..."
            />

            {csvError && (
              <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded px-3 py-2">
                {csvError}
              </div>
            )}

            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setCsvText(SAMPLE_CSV_PRIMARY)}
                className="text-xs text-slate-500 hover:text-slate-900 underline cursor-pointer"
              >
                Load Sample Scans
              </button>
              <button
                type="button"
                onClick={handleRunCsvBatch}
                disabled={csvLoading}
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-teal-800 hover:bg-teal-900 disabled:opacity-60 rounded-lg cursor-pointer"
              >
                <Play className="w-3.5 h-3.5" />
                <span>{csvLoading ? 'Scoring Batch...' : 'Score Uploaded CSV'}</span>
              </button>
            </div>
          </div>

          <div className="lg:col-span-7 bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Batch Inference &amp; Vegetation Index Readout</h3>
                <p className="text-xs text-slate-500">
                  Preprocesses every row via SavGol + SNV + Feature Set E without data leakage
                </p>
              </div>
              {csvResult && (
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span>Scored: <strong>{csvResult.rows_scored}</strong></span>
                  {Object.entries(csvResult.class_counts).map(([c, n]) => (
                    <span key={c} className="text-teal-800 font-semibold">
                      {c.split(' ')[0]}: {n}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {!csvResult ? (
              <div className="p-10 text-center text-xs text-slate-500">
                Click <strong>Score Uploaded CSV</strong> to run batch SavGol + Set E classification &amp; index profiling on your spectral CSV rows.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-3 py-2 font-medium">#</th>
                      <th className="px-3 py-2 font-sans font-medium">Sample</th>
                      <th className="px-3 py-2 font-sans font-medium">Prediction</th>
                      <th className="px-3 py-2 text-right font-medium">Conf.</th>
                      <th className="px-3 py-2 text-right font-medium">NDVI</th>
                      <th className="px-3 py-2 text-right font-medium">NDRE</th>
                      <th className="px-3 py-2 text-right font-medium">REP (nm)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {csvResult.rows.map((r) => {
                      const stressed = samples && r.predicted_class !== samples.class_names[0];
                      return (
                        <tr key={r.row_index}>
                          <td className="px-3 py-2 text-slate-400">{r.row_index}</td>
                          <td className="px-3 py-2 font-sans font-medium text-slate-800">{r.sample_id}</td>
                          <td className={`px-3 py-2 font-sans font-semibold ${stressed ? 'text-rose-700' : 'text-teal-800'}`}>
                            {r.predicted_class}
                          </td>
                          <td className="px-3 py-2 text-right">{(r.confidence * 100).toFixed(1)}%</td>
                          <td className="px-3 py-2 text-right">{r.ndvi.toFixed(3)}</td>
                          <td className="px-3 py-2 text-right">{r.ndre.toFixed(3)}</td>
                          <td className="px-3 py-2 text-right">{r.rep_nm.toFixed(1)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODE 3: PLANT TRAJECTORY FORECASTER & EARLY DETECTION */}
      {subMode === 'forecaster' && (
        <div className="space-y-6">
          {/* Top Summary Strip */}
          {earlySummary && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="text-xs text-slate-500">Median Early-Detection Lead Time</div>
                <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-teal-800">
                  {earlySummary.median_plant_lead_days_before_end} days
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Before final trial peak across holdout plants
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="text-xs text-slate-500">Holdout Stress Flag Rate</div>
                <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {earlySummary.pct_stressed_plants_detected_early}%
                </div>
                <div className="text-xs font-mono text-slate-500 mt-1">
                  Across {earlySummary.holdout_stressed_plants} unseen stressed plants
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="text-xs text-slate-500">First Classifier Separation</div>
                <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {earlySummary.first_classifier_detection_day !== null
                    ? `Day +${earlySummary.first_classifier_detection_day}`
                    : 'Gradual'}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {earlySummary.first_ndvi_divergence_day !== null
                    ? `Cohort NDVI diverges Day +${earlySummary.first_ndvi_divergence_day}`
                    : 'Tracked continuously'}
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="text-xs text-slate-500">Active Forecaster Horizon</div>
                <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-amber-700">
                  t + {horizon} steps
                </div>
                <div className="text-xs font-mono text-slate-500 mt-1">
                  Lag-RF vs. Lag-Ridge vs. Persistence
                </div>
              </div>
            </div>
          )}

          {/* Interactive Plant Trajectory Explorer */}
          <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-teal-700" />
                  <span>Per-Plant Chronological Canopy Forecast Simulator</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Select an unseen validation plant to inspect observed NDVI, healthy cohort curve, backtest accuracy, and forward <code className="font-mono">t+1..t+{horizon}</code> forecast
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-600 font-medium">Plant ID</span>
                  <select
                    value={selectedPlantId}
                    onChange={(e) => {
                      const nextPid = e.target.value;
                      setSelectedPlantId(nextPid);
                      runPlantForecast(nextPid, horizon, source);
                    }}
                    className="font-mono text-xs bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-900"
                  >
                    {(samples?.plants || []).map((p) => (
                      <option key={p.plant_id} value={p.plant_id}>
                        {p.plant_id} · {p.true_label.split(' ')[0]} ({p.split === 'holdout_test' ? 'Unseen Test' : 'Train'}, {p.n_scans}d)
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-md">
                  {[1, 2, 3].map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => {
                        const hk = k as 1 | 2 | 3;
                        setHorizon(hk);
                        if (selectedPlantId) runPlantForecast(selectedPlantId, hk, source);
                      }}
                      className={`px-2.5 py-1 text-xs font-mono font-semibold rounded cursor-pointer ${
                        horizon === k ? 'bg-white text-teal-800 shadow-xs' : 'text-slate-600'
                      }`}
                    >
                      k=+{k}
                    </button>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() => runPlantForecast(selectedPlantId, horizon, source)}
                  disabled={forecastLoading}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-teal-800 hover:bg-teal-900 rounded-md cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${forecastLoading ? 'animate-spin' : ''}`} />
                  <span>Forecast</span>
                </button>
              </div>
            </div>

            {plantForecast && forecastChartGeom && (
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
                <div className="xl:col-span-8 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div className="font-mono text-slate-700">
                      <strong>Plant {plantForecast.plant_id}</strong> ({plantForecast.true_label} · {plantForecast.split} · Field {plantForecast.field_id})
                    </div>
                    <div className="flex items-center gap-4 font-mono text-[11px]">
                      <span className="text-slate-900 font-semibold">— Observed NDVI</span>
                      <span className="text-slate-400">- - Healthy Mean</span>
                      <span className="text-amber-700 font-semibold">● Lag-RF Forecast (t+1..t+{horizon})</span>
                    </div>
                  </div>

                  <svg
                    viewBox={`0 0 ${forecastChartGeom.w} ${forecastChartGeom.h}`}
                    className="w-full h-auto cursor-crosshair select-none"
                    onMouseLeave={() => setHoverStepIdx(null)}
                  >
                    {/* Y grid lines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((f) => {
                      const v = forecastChartGeom.minV + f * (forecastChartGeom.maxV - forecastChartGeom.minV);
                      const y = forecastChartGeom.yOf(v);
                      return (
                        <g key={f}>
                          <line
                            x1={forecastChartGeom.padL}
                            x2={forecastChartGeom.w - forecastChartGeom.padR}
                            y1={y}
                            y2={y}
                            stroke="#e2e8f0"
                            strokeDasharray="2 3"
                          />
                          <text
                            x={forecastChartGeom.padL - 8}
                            y={y + 3}
                            textAnchor="end"
                            className="fill-slate-400 text-[10px] font-mono"
                          >
                            {v.toFixed(2)}
                          </text>
                        </g>
                      );
                    })}

                    {/* Healthy cohort reference curve */}
                    <path
                      d={plantForecast.history
                        .map(
                          (p, idx) =>
                            `${idx === 0 ? 'M' : 'L'}${forecastChartGeom.xOf(p.day_offset).toFixed(1)},${forecastChartGeom.yOf(p.healthy_cohort_ndvi).toFixed(1)}`
                        )
                        .join(' ')}
                      fill="none"
                      stroke="#94a3b8"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                    />

                    {/* Backtest Lag-RF curve */}
                    <path
                      d={plantForecast.history
                        .filter((p) => p.lag_rf_backtest !== null)
                        .map(
                          (p, idx) =>
                            `${idx === 0 ? 'M' : 'L'}${forecastChartGeom.xOf(p.day_offset).toFixed(1)},${forecastChartGeom.yOf(p.lag_rf_backtest as number).toFixed(1)}`
                        )
                        .join(' ')}
                      fill="none"
                      stroke="#0f766e"
                      strokeWidth={1.6}
                      strokeDasharray="2 2"
                    />

                    {/* Actual plant NDVI curve */}
                    <path
                      d={plantForecast.history
                        .map(
                          (p, idx) =>
                            `${idx === 0 ? 'M' : 'L'}${forecastChartGeom.xOf(p.day_offset).toFixed(1)},${forecastChartGeom.yOf(p.actual_ndvi).toFixed(1)}`
                        )
                        .join(' ')}
                      fill="none"
                      stroke="#0f172a"
                      strokeWidth={2.2}
                    />

                    {/* Forward Future Horizon line */}
                    {plantForecast.future.length > 0 && (
                      <path
                        d={[
                          plantForecast.history[plantForecast.history.length - 1],
                          ...plantForecast.future,
                        ]
                          .map((pt, idx) => {
                            const val = 'actual_ndvi' in pt ? pt.actual_ndvi : pt.lag_rf_ndvi;
                            return `${idx === 0 ? 'M' : 'L'}${forecastChartGeom.xOf(pt.day_offset).toFixed(1)},${forecastChartGeom.yOf(val).toFixed(1)}`;
                          })
                          .join(' ')}
                        fill="none"
                        stroke="#d97706"
                        strokeWidth={2.5}
                      />
                    )}

                    {/* History Hover Nodes */}
                    {plantForecast.history.map((p, idx) => (
                      <g key={p.step} onMouseEnter={() => setHoverStepIdx(idx)}>
                        <circle
                          cx={forecastChartGeom.xOf(p.day_offset)}
                          cy={forecastChartGeom.yOf(p.actual_ndvi)}
                          r={hoverStepIdx === idx ? 5 : 2.8}
                          fill={p.stress_prob >= 0.55 ? '#dc2626' : '#0f172a'}
                        />
                        {idx % Math.max(1, Math.floor(plantForecast.history.length / 6)) === 0 && (
                          <text
                            x={forecastChartGeom.xOf(p.day_offset)}
                            y={forecastChartGeom.h - 10}
                            textAnchor="middle"
                            className="fill-slate-400 text-[10px] font-mono"
                          >
                            D+{p.day_offset}
                          </text>
                        )}
                      </g>
                    ))}

                    {/* Future Horizon Points */}
                    {plantForecast.future.map((f) => (
                      <g key={f.horizon}>
                        <circle
                          cx={forecastChartGeom.xOf(f.day_offset)}
                          cy={forecastChartGeom.yOf(f.lag_rf_ndvi)}
                          r={4.5}
                          fill="#d97706"
                          stroke="#ffffff"
                          strokeWidth={1.5}
                        />
                      </g>
                    ))}
                  </svg>

                  {hoverStepIdx !== null && plantForecast.history[hoverStepIdx] && (
                    <div className="text-xs font-mono text-slate-700 bg-slate-50 border border-slate-200 rounded px-3 py-1.5 flex flex-wrap items-center gap-4">
                      <span>Date: <strong>{plantForecast.history[hoverStepIdx].date}</strong> (Day +{plantForecast.history[hoverStepIdx].day_offset})</span>
                      <span>Actual NDVI: <strong>{plantForecast.history[hoverStepIdx].actual_ndvi.toFixed(4)}</strong></span>
                      <span>P(Stress): <strong className={plantForecast.history[hoverStepIdx].stress_prob >= 0.55 ? 'text-rose-700' : 'text-teal-800'}>{(plantForecast.history[hoverStepIdx].stress_prob * 100).toFixed(1)}%</strong></span>
                      <span>REP: <strong>{plantForecast.history[hoverStepIdx].rep_nm.toFixed(1)} nm</strong></span>
                    </div>
                  )}
                </div>

                <div className="xl:col-span-4 space-y-4">
                  <div className="bg-slate-50 border border-slate-200 rounded-md p-4 space-y-2 text-xs">
                    <div className="font-semibold text-slate-900">Early-Detection &amp; Horizon Summary</div>
                    <div className="flex justify-between font-mono pt-1">
                      <span className="font-sans text-slate-600">Trial Span</span>
                      <span className="font-semibold">{plantForecast.trial_duration_days} days ({plantForecast.n_timepoints} scans)</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="font-sans text-slate-600">First Spectral Flag (p ≥ 0.55)</span>
                      <span className="font-semibold text-rose-700">
                        {plantForecast.first_spectral_flag_day !== null ? `Day +${plantForecast.first_spectral_flag_day}` : 'Not flagged'}
                      </span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="font-sans text-slate-600">Lead Time Before End</span>
                      <span className="font-semibold text-teal-800">
                        {plantForecast.lead_time_vs_end_days !== null ? `${plantForecast.lead_time_vs_end_days} days` : '-'}
                      </span>
                    </div>
                  </div>

                  <div className="border border-slate-200 rounded-md overflow-hidden">
                    <div className="px-3.5 py-2.5 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-800">
                      Forward Multi-Step Forecast Table
                    </div>
                    <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500">
                          <th className="px-3 py-1.5 font-medium">Step</th>
                          <th className="px-3 py-1.5 text-right font-medium">Lag-RF</th>
                          <th className="px-3 py-1.5 text-right font-medium">Ridge</th>
                          <th className="px-3 py-1.5 text-right font-medium">Persist</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {plantForecast.future.map((f) => (
                          <tr key={f.horizon}>
                            <td className="px-3 py-2 font-semibold text-amber-700">t+{f.horizon}</td>
                            <td className="px-3 py-2 text-right font-bold text-slate-900">{f.lag_rf_ndvi.toFixed(4)}</td>
                            <td className="px-3 py-2 text-right text-slate-600">{f.lag_ridge_ndvi.toFixed(4)}</td>
                            <td className="px-3 py-2 text-right text-slate-400">{f.persistence_ndvi.toFixed(4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
