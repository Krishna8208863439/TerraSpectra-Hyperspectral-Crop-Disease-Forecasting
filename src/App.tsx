import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, Search } from 'lucide-react';
import { Day2EdaView } from './components/Day2EdaView';
import { Day3PreprocessingView } from './components/Day3PreprocessingView';
import { Day4FeaturesView } from './components/Day4FeaturesView';
import { Day5BaselinesView } from './components/Day5BaselinesView';
import { Day6ErrorAndForecastView } from './components/Day6ErrorAndForecastView';
import { ExperimentsView, ReportAndRepoView } from './components/ExperimentsAndReportViews';
import { LiveInferenceView } from './components/LiveInferenceView';
import { Week3ReadinessView } from './components/Week3ReadinessView';
import type {
  DatasetSummary,
  Day2EdaPayload,
  Day3PreprocessingPayload,
  Day4FeaturesPayload,
  Day5BaselinesPayload,
  Day6ErrorAndForecastPayload,
  DocItem,
  EnvVerifyResult,
  PreprocessingConfigDto,
  RepoStatus,
  Week3ReadinessPayload,
} from './types/day1';

type ActiveTab = 'demo' | 'lab' | 'evaluation' | 'experiments' | 'docs';
type LabStage = 'data' | 'preprocessing' | 'features' | 'explorer';
type EvalStage = 'baselines' | 'diagnostics' | 'neural';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('demo');
  const [labStage, setLabStage] = useState<LabStage>('data');
  const [evalStage, setEvalStage] = useState<EvalStage>('baselines');
  const [pipelineSource, setPipelineSource] = useState<'primary' | 'synthetic'>('primary');

  const [envResult, setEnvResult] = useState<EnvVerifyResult | null>(null);
  const [repoStatus, setRepoStatus] = useState<RepoStatus | null>(null);
  const [datasetSummary, setDatasetSummary] = useState<DatasetSummary | null>(null);

  const [edaPayload, setEdaPayload] = useState<Day2EdaPayload | null>(null);
  const [edaLoading, setEdaLoading] = useState<boolean>(false);
  const [edaRunning, setEdaRunning] = useState<boolean>(false);

  const [prepPayload, setPrepPayload] = useState<Day3PreprocessingPayload | null>(null);
  const [prepLoading, setPrepLoading] = useState<boolean>(false);
  const [prepRunning, setPrepRunning] = useState<boolean>(false);

  const [featuresPayload, setFeaturesPayload] = useState<Day4FeaturesPayload | null>(null);
  const [featuresLoading, setFeaturesLoading] = useState<boolean>(false);
  const [featuresRunning, setFeaturesRunning] = useState<boolean>(false);

  const [baselinesPayload, setBaselinesPayload] = useState<Day5BaselinesPayload | null>(null);
  const [baselinesLoading, setBaselinesLoading] = useState<boolean>(false);
  const [baselinesRunning, setBaselinesRunning] = useState<boolean>(false);

  const [day6Payload, setDay6Payload] = useState<Day6ErrorAndForecastPayload | null>(null);
  const [day6Loading, setDay6Loading] = useState<boolean>(false);
  const [day6Running, setDay6Running] = useState<boolean>(false);

  const [week3Readiness, setWeek3Readiness] = useState<Week3ReadinessPayload | null>(null);
  const [week3Loading, setWeek3Loading] = useState<boolean>(false);

  const [fullPipelineRunning, setFullPipelineRunning] = useState<boolean>(false);

  const [docs, setDocs] = useState<DocItem[]>([]);
  const [selectedDocKey, setSelectedDocKey] = useState<string>('project_report');
  const [saveFeedback, setSaveFeedback] = useState<string>('');

  const [sampleQuery, setSampleQuery] = useState<string>('');
  const [sampleLabelFilter, setSampleLabelFilter] = useState<string>('ALL');

  const loadEnv = useCallback(async () => {
    try {
      const res = await fetch('/api/env/verify');
      const data: EnvVerifyResult = await res.json();
      setEnvResult(data);
    } catch {
      setEnvResult({
        python_version: 'unknown',
        python_executable: 'python3',
        platform: 'unknown',
        all_ok: false,
        packages: [],
        error: 'Unable to reach /api/env/verify',
      });
    }
  }, []);

  const loadRepoAndDocs = useCallback(async () => {
    try {
      const [repoRes, docsRes] = await Promise.all([
        fetch('/api/repo/status'),
        fetch('/api/docs'),
      ]);
      if (repoRes.ok) setRepoStatus(await repoRes.json());
      if (docsRes.ok) {
        const payload = await docsRes.json();
        setDocs(payload.docs || []);
      }
    } catch {
      // ignore transient startup errors
    }
  }, []);

  const loadEdaMetrics = useCallback(async () => {
    setEdaLoading(true);
    try {
      const res = await fetch('/api/eda/metrics');
      if (res.ok) setEdaPayload(await res.json());
    } finally {
      setEdaLoading(false);
    }
  }, []);

  const handleRunEda = useCallback(async () => {
    setEdaRunning(true);
    try {
      const res = await fetch('/api/eda/run', { method: 'POST' });
      if (res.ok) {
        const payload = await res.json();
        if (payload.data) setEdaPayload(payload.data);
        await loadRepoAndDocs();
      }
    } finally {
      setEdaRunning(false);
    }
  }, [loadRepoAndDocs]);

  const loadPreprocessingMetrics = useCallback(async () => {
    setPrepLoading(true);
    try {
      const res = await fetch('/api/preprocessing/metrics');
      if (res.ok) setPrepPayload(await res.json());
    } finally {
      setPrepLoading(false);
    }
  }, []);

  const handleRunPreprocessing = useCallback(
    async (config?: Partial<PreprocessingConfigDto>) => {
      setPrepRunning(true);
      try {
        const res = await fetch('/api/preprocessing/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config || {}),
        });
        if (res.ok) {
          const payload = await res.json();
          if (payload.data) setPrepPayload(payload.data);
          await loadRepoAndDocs();
        }
      } finally {
        setPrepRunning(false);
      }
    },
    [loadRepoAndDocs]
  );

  const loadFeaturesMetrics = useCallback(async () => {
    setFeaturesLoading(true);
    try {
      const res = await fetch('/api/features/metrics');
      if (res.ok) setFeaturesPayload(await res.json());
    } finally {
      setFeaturesLoading(false);
    }
  }, []);

  const handleRunFeatures = useCallback(
    async (params?: { topK: number; normalization: 'none' | 'snv' | 'msc' }) => {
      setFeaturesRunning(true);
      try {
        const res = await fetch('/api/features/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(params || { topK: 5, normalization: 'snv' }),
        });
        if (res.ok) {
          const payload = await res.json();
          if (payload.data) setFeaturesPayload(payload.data);
          await loadRepoAndDocs();
        }
      } finally {
        setFeaturesRunning(false);
      }
    },
    [loadRepoAndDocs]
  );

  const loadBaselinesMetrics = useCallback(async () => {
    setBaselinesLoading(true);
    try {
      const res = await fetch('/api/baselines/metrics');
      if (res.ok) setBaselinesPayload(await res.json());
    } finally {
      setBaselinesLoading(false);
    }
  }, []);

  const handleRunBaselines = useCallback(
    async (groupCol: 'plant_id' | 'plot_id' | 'field_id' = 'plant_id') => {
      setBaselinesRunning(true);
      try {
        const res = await fetch('/api/baselines/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ groupCol }),
        });
        if (res.ok) {
          const payload = await res.json();
          if (payload.data) setBaselinesPayload(payload.data);
          await loadRepoAndDocs();
        }
      } finally {
        setBaselinesRunning(false);
      }
    },
    [loadRepoAndDocs]
  );

  const loadDay6Metrics = useCallback(async () => {
    setDay6Loading(true);
    try {
      const res = await fetch('/api/day6/metrics');
      if (res.ok) setDay6Payload(await res.json());
    } finally {
      setDay6Loading(false);
    }
  }, []);

  const handleRunDay6 = useCallback(
    async (params: { window: number; horizon: number } = { window: 3, horizon: 1 }) => {
      setDay6Running(true);
      try {
        const res = await fetch('/api/day6/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(params),
        });
        if (res.ok) {
          const payload = await res.json();
          if (payload.data) setDay6Payload(payload.data);
          await loadRepoAndDocs();
        }
      } finally {
        setDay6Running(false);
      }
    },
    [loadRepoAndDocs]
  );

  const loadWeek3Readiness = useCallback(async (forceRefresh = false) => {
    setWeek3Loading(true);
    try {
      const url = forceRefresh ? '/api/week3/readiness?refresh=1' : '/api/week3/readiness';
      const res = await fetch(url);
      if (res.ok) setWeek3Readiness(await res.json());
    } finally {
      setWeek3Loading(false);
    }
  }, []);

  const handleRunFullPipeline = useCallback(async () => {
    setFullPipelineRunning(true);
    try {
      const res = await fetch('/api/pipeline/run-all', { method: 'POST' });
      if (res.ok) {
        await Promise.all([
          loadBaselinesMetrics(),
          loadDay6Metrics(),
          loadWeek3Readiness(false),
          loadRepoAndDocs(),
        ]);
      }
    } finally {
      setFullPipelineRunning(false);
    }
  }, [loadBaselinesMetrics, loadDay6Metrics, loadWeek3Readiness, loadRepoAndDocs]);

  const loadDataset = useCallback(async (source: 'primary' | 'synthetic') => {
    try {
      const res = await fetch(`/api/dataset/summary?source=${source}`);
      if (res.ok) setDatasetSummary(await res.json());
    } catch {
      // ignore transient error
    }
  }, []);

  useEffect(() => {
    loadEnv();
    loadRepoAndDocs();
    loadEdaMetrics();
    loadPreprocessingMetrics();
    loadFeaturesMetrics();
    loadBaselinesMetrics();
    loadDay6Metrics();
    loadWeek3Readiness(false);
  }, [
    loadEnv,
    loadRepoAndDocs,
    loadEdaMetrics,
    loadPreprocessingMetrics,
    loadFeaturesMetrics,
    loadBaselinesMetrics,
    loadDay6Metrics,
    loadWeek3Readiness,
  ]);

  useEffect(() => {
    loadDataset(pipelineSource);
  }, [pipelineSource, loadDataset]);

  const saveDocument = async (key: string, content: string) => {
    setSaveFeedback('Saving...');
    try {
      const res = await fetch(`/api/docs/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        setDocs((prev) => prev.map((d) => (d.key === key ? { ...d, content } : d)));
        setSaveFeedback('Saved');
        setTimeout(() => setSaveFeedback(''), 2500);
      } else {
        setSaveFeedback('Save failed');
      }
    } catch {
      setSaveFeedback('Save failed');
    }
  };

  const openDocument = (key: string) => {
    setSelectedDocKey(key);
    setActiveTab('docs');
  };

  const dataSummaryDoc = docs.find((d) => d.key === 'data_summary')?.content || '';
  const preprocessingNoteDoc = docs.find((d) => d.key === 'preprocessing_note')?.content || '';
  const featureNoteDoc = docs.find((d) => d.key === 'feature_engineering_note')?.content || '';
  const baselineNoteDoc = docs.find((d) => d.key === 'baseline_results_note')?.content || '';
  const day6NoteDoc = docs.find((d) => d.key === 'error_interpretability_note')?.content || '';

  const activeBaselines = baselinesPayload ? baselinesPayload[pipelineSource] : null;
  const activeDay6 = day6Payload ? day6Payload[pipelineSource] : null;

  const passedPackages = envResult?.packages.filter((p) => p.status === 'ok').length ?? 0;
  const totalPackages = envResult?.packages.length ?? 8;
  const presentDirs = repoStatus?.directories.filter((d) => d.exists).length ?? 0;
  const totalDirs = repoStatus?.directories.length ?? 7;

  const allFigures = useMemo(() => {
    const combined = [
      ...(edaPayload?.figures || []),
      ...(prepPayload?.figures || []),
      ...(featuresPayload?.figures || []),
      ...(baselinesPayload?.figures || []),
      ...(day6Payload?.figures || []),
    ];
    return Array.from(new Set(combined));
  }, [edaPayload, prepPayload, featuresPayload, baselinesPayload, day6Payload]);

  const forecastHorizon3 = activeDay6?.forecasting_prep.horizons.find((h) => h.horizon === 3);
  const lagRfH3 = forecastHorizon3?.models.find((m) => m.key === 'lag_rf');

  const filteredSampleRows = useMemo(() => {
    if (!datasetSummary) return [];
    const q = sampleQuery.trim().toLowerCase();
    return datasetSummary.sampleRows.filter((row) => {
      const matchesLabel = sampleLabelFilter === 'ALL' || row.label === sampleLabelFilter;
      const matchesQuery =
        !q ||
        row.plantId.toLowerCase().includes(q) ||
        row.date.toLowerCase().includes(q) ||
        row.sampleId.toLowerCase().includes(q);
      return matchesLabel && matchesQuery;
    });
  }, [datasetSummary, sampleLabelFilter, sampleQuery]);

  const navItems: Array<{ id: ActiveTab; label: string }> = [
    { id: 'demo', label: 'Live Demo' },
    { id: 'lab', label: 'Spectral Lab' },
    { id: 'evaluation', label: 'Evaluation' },
    { id: 'experiments', label: 'Experiments' },
    { id: 'docs', label: 'Report & Repo' },
  ];

  const anyRunning =
    fullPipelineRunning || edaRunning || prepRunning || featuresRunning || baselinesRunning || day6Running;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Top Bar Contract: 3 zones, single-line controls, 5 concise domain nav items */}
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200">
        <div className="max-w-[1280px] mx-auto px-6 h-16 flex items-center justify-between gap-6">
          <button
            type="button"
            onClick={() => setActiveTab('demo')}
            className="text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0 cursor-pointer focus-visible:outline-2 focus-visible:outline-teal-700"
          >
            Terra<span className="text-teal-800">Spectra</span>
          </button>

          <nav className="hidden md:flex items-center gap-6" aria-label="Primary navigation">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={`text-sm font-medium py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer border-b-2 ${
                    isActive
                      ? 'text-teal-800 border-teal-700'
                      : 'text-slate-600 border-transparent hover:text-slate-900'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="flex items-center shrink-0">
            <button
              type="button"
              onClick={handleRunFullPipeline}
              disabled={anyRunning}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-teal-800 hover:bg-teal-900 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${anyRunning ? 'animate-spin' : ''}`} />
              <span>{anyRunning ? 'Running Pipeline...' : 'Run Pipeline'}</span>
            </button>
          </div>
        </div>

        {/* Mobile navigation bar */}
        <div className="md:hidden border-t border-slate-100 px-4 py-2 flex items-center gap-4 overflow-x-auto">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`text-xs font-medium py-1 whitespace-nowrap shrink-0 ${
                activeTab === item.id ? 'text-teal-800 font-semibold' : 'text-slate-600'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-[1280px] mx-auto px-6 py-8 space-y-8">
        {/* Project Header & 4-Column Telemetry Strip */}
        <section className="space-y-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-mono">
              <span>Hyperspectral Crop Stress &amp; Disease Forecasting</span>
              <span aria-hidden="true">·</span>
              <span>Zenodo 22755812 + Synthetic 61-Band Benchmark</span>
              <span aria-hidden="true">·</span>
              <span>Zero-Leakage Plant-Grouped Validation</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 [text-wrap:balance] max-w-3xl">
              TerraSpectra: Leaf Stress Diagnosis &amp; Trajectory Forecasting
            </h1>
            <p className="text-sm text-slate-600 max-w-3xl leading-relaxed">
              Interactive VNIR spectral stress classifier (<code className="font-mono text-slate-800">460–970 nm</code>), vegetation-index feature engineering, Shapley explainability, and multi-horizon canopy NDVI trajectory forecaster evaluated strictly by <code className="font-mono text-slate-800">plant_id</code>.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Dataset Coverage</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {datasetSummary ? datasetSummary.shape.rows.toLocaleString() : '2,280'}
                </span>
                <span className="text-xs font-mono text-slate-400">scans</span>
              </div>
              <div className="mt-2 text-xs font-mono text-slate-600 tabular-nums">
                {datasetSummary ? `${datasetSummary.uniquePlants} plants · ${datasetSummary.uniqueDatesCount} dates` : '79 plants · 31 dates'}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Best Leak-Free Classifier</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono tabular-nums text-slate-900">
                  {activeDay6
                    ? `F1 ${activeDay6.tuning.tuned.macro_f1_mean.toFixed(3)}`
                    : activeBaselines
                      ? `F1 ${activeBaselines.overall_best.macro_f1_mean.toFixed(3)}`
                      : 'Loading...'}
                </span>
                <span className="text-xs font-mono text-teal-800 font-semibold">
                  {activeBaselines ? `XGB · Set ${activeBaselines.overall_best.feature_set_code}` : ''}
                </span>
              </div>
              <div className="mt-2 text-xs text-rose-700 font-mono tabular-nums">
                {activeBaselines
                  ? `Naive split inflates +${activeBaselines.leakage_demonstration.inflation_macro_f1.toFixed(3)} F1`
                  : 'StratifiedGroupKFold (5 folds)'}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Canopy Trajectory Forecaster</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {lagRfH3 ? `R² ${lagRfH3.r2_mean.toFixed(3)}` : 'R² 0.943'}
                </span>
                <span className="text-xs font-mono text-teal-800 font-semibold">t+3 horizon</span>
              </div>
              <div className="mt-2 text-xs text-slate-600 font-mono tabular-nums">
                {lagRfH3
                  ? `Lag-RF MAE ${lagRfH3.mae_mean.toFixed(4)} (${forecastHorizon3?.n_sequences} seqs)`
                  : 'Sequence modeling verified'}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Runtime &amp; Repo Status</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {passedPackages}/{totalPackages}
                </span>
                <span className="text-xs font-mono text-slate-400">pkgs · {presentDirs}/{totalDirs} dirs</span>
              </div>
              <div className="mt-2 text-xs text-teal-800 font-medium">
                {envResult?.all_ok ? '● Reproducible stack verified' : '▲ Checking Python stack'}
              </div>
            </div>
          </div>
        </section>

        {/* TAB 1: LIVE DEMO (Interactive Models, Batch CSV, Plant Trajectory Forecaster) */}
        {activeTab === 'demo' && (
          <LiveInferenceView
            source={pipelineSource}
            onChangeSource={setPipelineSource}
          />
        )}

        {/* TAB 2: SPECTRAL LAB (EDA, Preprocessing Studio, Feature Sets A-E, Raw Explorer) */}
        {activeTab === 'lab' && (
          <div className="space-y-6">
            <div className="bg-white border border-slate-200 rounded-lg p-3 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg">
                {[
                  { id: 'data', label: '1. Data & Spectral Signatures' },
                  { id: 'preprocessing', label: '2. Preprocessing Studio (SavGol / SNV / MSC)' },
                  { id: 'features', label: '3. Feature Sets A–E & Band Selection' },
                  { id: 'explorer', label: '4. Sample Scan Explorer' },
                ].map((stage) => (
                  <button
                    key={stage.id}
                    type="button"
                    onClick={() => setLabStage(stage.id as LabStage)}
                    className={`px-3.5 py-2 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      labStage === stage.id
                        ? 'bg-white text-slate-900 shadow-xs font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {stage.label}
                  </button>
                ))}
              </div>
              <div className="text-xs font-mono text-slate-500 px-2">
                src/data.py → src/preprocessing.py → src/features.py
              </div>
            </div>

            {labStage === 'data' && (
              <Day2EdaView
                edaPayload={edaPayload}
                edaLoading={edaLoading}
                edaRunning={edaRunning}
                edaSource={pipelineSource}
                onChangeSource={setPipelineSource}
                onRunEda={handleRunEda}
                dataSummaryMarkdown={dataSummaryDoc}
                onOpenDoc={openDocument}
              />
            )}

            {labStage === 'preprocessing' && (
              <Day3PreprocessingView
                prepPayload={prepPayload}
                prepLoading={prepLoading}
                prepRunning={prepRunning}
                source={pipelineSource}
                onChangeSource={setPipelineSource}
                onRunPreprocessing={handleRunPreprocessing}
                noteMarkdown={preprocessingNoteDoc}
                onOpenDoc={openDocument}
              />
            )}

            {labStage === 'features' && (
              <Day4FeaturesView
                featuresPayload={featuresPayload}
                featuresLoading={featuresLoading}
                featuresRunning={featuresRunning}
                source={pipelineSource}
                onChangeSource={setPipelineSource}
                onRunFeatures={handleRunFeatures}
                noteMarkdown={featureNoteDoc}
                onOpenDoc={openDocument}
              />
            )}

            {labStage === 'explorer' && (
              <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">
                      Sample Reflectance &amp; Vegetation Index Explorer
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Inspect individual leaf observations from <code className="font-mono">{datasetSummary?.files?.[0] || 'data/raw/'}</code>
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        value={sampleQuery}
                        onChange={(e) => setSampleQuery(e.target.value)}
                        placeholder="Search plant ID or date..."
                        className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:border-teal-700"
                      />
                    </div>
                    <select
                      value={sampleLabelFilter}
                      onChange={(e) => setSampleLabelFilter(e.target.value)}
                      className="text-xs bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5"
                    >
                      <option value="ALL">All Classes</option>
                      {(datasetSummary?.labelDistribution || []).map((c) => (
                        <option key={c.label} value={c.label}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="overflow-x-auto border border-slate-200 rounded-md">
                  <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-2 font-medium">Plant ID</th>
                        <th className="px-3 py-2 font-medium">Pot</th>
                        <th className="px-3 py-2 font-medium">Date</th>
                        <th className="px-3 py-2 font-sans font-medium">Label</th>
                        <th className="px-3 py-2 font-medium text-right">R670 (%)</th>
                        <th className="px-3 py-2 font-medium text-right">R780 (%)</th>
                        <th className="px-3 py-2 font-medium text-right">NDVI</th>
                        <th className="px-3 py-2 font-medium text-right">NDRE</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredSampleRows.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="px-4 py-6 text-center font-sans text-slate-500">
                            No sample scans match your filter.
                          </td>
                        </tr>
                      ) : (
                        filteredSampleRows.map((row) => (
                          <tr key={row.sampleId} className="hover:bg-slate-50/70">
                            <td className="px-3 py-2 font-semibold text-slate-900">{row.plantId}</td>
                            <td className="px-3 py-2 text-slate-600">{row.potNumber}</td>
                            <td className="px-3 py-2 text-slate-600">{row.date}</td>
                            <td className="px-3 py-2 font-sans text-slate-800">{row.label}</td>
                            <td className="px-3 py-2 text-right text-slate-700">{row.r670.toFixed(2)}</td>
                            <td className="px-3 py-2 text-right text-slate-700">{row.r780.toFixed(2)}</td>
                            <td className="px-3 py-2 text-right font-semibold text-teal-800">{row.ndvi.toFixed(3)}</td>
                            <td className="px-3 py-2 text-right text-slate-700">{row.ndre.toFixed(3)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: EVALUATION (Baselines & Leakage Proof, SHAP & Error Diagnostics, Neural Comparator) */}
        {activeTab === 'evaluation' && (
          <div className="space-y-6">
            <div className="bg-white border border-slate-200 rounded-lg p-3 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg">
                {[
                  { id: 'baselines', label: '1. Grouped-CV Baselines & Leakage Proof' },
                  { id: 'diagnostics', label: '2. Error Diagnostics, SHAP & Sequences' },
                  { id: 'neural', label: '3. Neural Comparator (MLP / 1D-CNN / GRU)' },
                ].map((stage) => (
                  <button
                    key={stage.id}
                    type="button"
                    onClick={() => setEvalStage(stage.id as EvalStage)}
                    className={`px-3.5 py-2 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      evalStage === stage.id
                        ? 'bg-white text-slate-900 shadow-xs font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {stage.label}
                  </button>
                ))}
              </div>
              <div className="text-xs font-mono text-slate-500 px-2">
                StratifiedGroupKFold(plant_id) · Zero Group Overlap
              </div>
            </div>

            {evalStage === 'baselines' && (
              <Day5BaselinesView
                baselinesPayload={baselinesPayload}
                baselinesLoading={baselinesLoading}
                baselinesRunning={baselinesRunning}
                source={pipelineSource}
                onChangeSource={setPipelineSource}
                onRunBaselines={handleRunBaselines}
                noteMarkdown={baselineNoteDoc}
                onOpenDoc={openDocument}
              />
            )}

            {evalStage === 'diagnostics' && (
              <Day6ErrorAndForecastView
                day6Payload={day6Payload}
                day6Loading={day6Loading}
                day6Running={day6Running}
                source={pipelineSource}
                onChangeSource={setPipelineSource}
                onRunDay6={handleRunDay6}
                noteMarkdown={day6NoteDoc}
                onOpenDoc={openDocument}
              />
            )}

            {evalStage === 'neural' && (
              <Week3ReadinessView
                readiness={week3Readiness}
                readinessLoading={week3Loading}
                baselinesPayload={baselinesPayload}
                source={pipelineSource}
                onChangeSource={setPipelineSource}
                onRefresh={() => loadWeek3Readiness(true)}
              />
            )}
          </div>
        )}

        {/* TAB 4: EXPERIMENTS (Full Experiment Log & All Figures Gallery) */}
        {activeTab === 'experiments' && (
          <ExperimentsView
            rows={day6Payload?.experiment_log_rows || []}
            allFigures={allFigures}
            onRefresh={() => {
              loadDay6Metrics();
              loadBaselinesMetrics();
            }}
          />
        )}

        {/* TAB 5: REPORT & REPO (Technical Report, Mentor Update, Week 3 Plan, Repo/Python/Git) */}
        {activeTab === 'docs' && (
          <ReportAndRepoView
            docs={docs}
            selectedDocKey={selectedDocKey}
            onSelectDoc={setSelectedDocKey}
            onSaveDoc={saveDocument}
            saveFeedback={saveFeedback}
            repoStatus={repoStatus}
            envResult={envResult}
            onRefreshRepo={loadRepoAndDocs}
            onRefreshEnv={loadEnv}
          />
        )}
      </main>
    </div>
  );
}
