import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  FileText,
  FolderGit2,
  Play,
  RefreshCw,
  Save,
  Search,
} from 'lucide-react';
import { Day2EdaView } from './components/Day2EdaView';
import { Day3PreprocessingView } from './components/Day3PreprocessingView';
import { Day4FeaturesView } from './components/Day4FeaturesView';
import { MarkdownViewer } from './components/MarkdownViewer';
import type {
  DatasetSummary,
  Day1State,
  Day2EdaPayload,
  Day3PreprocessingPayload,
  Day4FeaturesPayload,
  DocItem,
  EnvVerifyResult,
  PreprocessingConfigDto,
  RepoStatus,
} from './types/day1';

type ActiveTab = 'overview' | 'day1' | 'day2' | 'day3' | 'day4' | 'brief';

interface ScheduleBlock {
  id: number;
  title: string;
  task: string;
  timeBudget: string;
  deliverable: string;
}

const SCHEDULE_BLOCKS: ScheduleBlock[] = [
  {
    id: 1,
    title: 'Mentor Scope & Cadence Check-In',
    task: 'Confirm scope (detection baseline + simple temporal forecast), ask whether a dataset is provided, and confirm progress update cadence.',
    timeBudget: '30 min',
    deliverable: 'docs/mentor_message.md',
  },
  {
    id: 2,
    title: 'Repository Structure & Git Initialization',
    task: 'Create the Git repo with data/, notebooks/, src/, reports/, app/, docs/, README.md, and requirements.txt.',
    timeBudget: '45 min',
    deliverable: 'README.md + folder tree',
  },
  {
    id: 3,
    title: 'Python Environment & Core Stack Setup',
    task: 'Set up Python environment and verify imports for NumPy, pandas, scikit-learn, XGBoost, matplotlib, and spectral.',
    timeBudget: '45 min',
    deliverable: 'src/pipeline/verify_env.py',
  },
  {
    id: 4,
    title: 'Open Spectral Portal Search & Audit',
    task: 'Search Kaggle, Zenodo, Mendeley Data, and IEEE DataPort; audit licence, format, labels, and temporal structure.',
    timeBudget: '2 h',
    deliverable: 'Portal audit matrix',
  },
  {
    id: 5,
    title: 'Fallback Order Selection & Decision Log',
    task: 'Select dataset using the Day 1 fallback hierarchy, document limitations, and note plant/plot/date grouping keys.',
    timeBudget: '30 min',
    deliverable: 'docs/dataset_note.md',
  },
  {
    id: 6,
    title: 'One-Page Project Brief',
    task: 'Write a concise project brief covering problem framing, data summary, leak-free validation, and success metrics.',
    timeBudget: '45 min',
    deliverable: 'docs/project_brief.md',
  },
];

const PORTAL_SEARCH_MATRIX = [
  {
    portal: 'Zenodo (Selected)',
    candidate: 'Plant Phenotyping & Environmental Stress Dataset (DOI: 10.5281/zenodo.22755812)',
    licence: 'CC-BY-4.0',
    format: 'CSV (2,285 rows × 37 cols)',
    labels: 'Control (40% Water) · Drought (10% Water) · Genotype',
    verdict: 'Selected Tier 1 CSV',
  },
  {
    portal: 'Zenodo (Secondary)',
    candidate: 'Multi-Temporal Apple Leaf Reflectance (DOI: 10.5281/zenodo.22143346)',
    licence: 'CC-BY-4.0',
    format: 'Preprocessed TXT zip (1,110 scans, 350–2500 nm)',
    labels: '37-day tree vitality sequence (single cultivar)',
    verdict: 'Backup temporal benchmark',
  },
  {
    portal: 'Kaggle',
    candidate: 'Indian Pines / Salinas Hyperspectral & Leaf Image Mirrors',
    licence: 'CC0 / Mixed',
    format: '.mat / .npy / JPEG',
    labels: '16 land-cover classes (not crop disease)',
    verdict: 'Tier 2 fallback only',
  },
  {
    portal: 'Mendeley Data',
    candidate: 'Leaf Spectral Reflectance for Crop Stress & Nutrient Deficiency',
    licence: 'CC-BY-4.0',
    format: '.xlsx / .csv',
    labels: 'Cultivar & nutrient/water treatments',
    verdict: 'Optional Day 3 expansion',
  },
  {
    portal: 'IEEE DataPort',
    candidate: 'Hyperspectral Plant Disease Cubes',
    licence: 'Subscription / Mixed',
    format: 'ENVI .hdr / .raw (multi-GB)',
    labels: 'Pixel-level disease masks',
    verdict: 'Deferred (bandwidth & licence)',
  },
];

const FALLBACK_TIERS = [
  {
    tier: 'Tier 1 — Primary Target',
    title: 'Hyperspectral or spectral-signature crop stress/disease dataset (leaf/plant CSV)',
    status: 'Selected: Zenodo Record 22755812 (CC-BY-4.0)',
    detail:
      '2,285 multi-temporal spectral scans across 31 dates and 80 plant IDs. Explicit limitation: measures abiotic drought stress rather than biotic pathogen inoculation.',
  },
  {
    tier: 'Tier 2 — Pipeline Fallback',
    title: 'Indian Pines or Salinas benchmark cubes',
    status: 'Evaluated · Not needed',
    detail:
      'Useful for ENVI / spectral library spatial pipeline validation, but represents satellite land-cover classes rather than leaf disease progression.',
  },
  {
    tier: 'Tier 3 — Synthetic Fallback',
    title: 'Simulated leaf spectra with controlled stress effects',
    status: 'Ready companion benchmark (synthetic_leaf_disease_spectra_v1.csv)',
    detail:
      '120 synthetic spectra (400–1000 nm, 61 bands) across 4 disease stages (Healthy to Severe Necrosis), clearly labeled SYNTHETIC_CONTROLLED_STRESS.',
  },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('day3');
  const [workspaceSub, setWorkspaceSub] = useState<'docs' | 'repo'>('docs');
  const [activeBlockId, setActiveBlockId] = useState<number>(1);
  const [datasetSource, setDatasetSource] = useState<'primary' | 'synthetic'>('primary');
  const [edaSource, setEdaSource] = useState<'primary' | 'synthetic'>('primary');
  const [pipelineSource, setPipelineSource] = useState<'primary' | 'synthetic'>('primary');

  const [envResult, setEnvResult] = useState<EnvVerifyResult | null>(null);
  const [envLoading, setEnvLoading] = useState<boolean>(false);

  const [repoStatus, setRepoStatus] = useState<RepoStatus | null>(null);
  const [datasetSummary, setDatasetSummary] = useState<DatasetSummary | null>(null);
  const [datasetLoading, setDatasetLoading] = useState<boolean>(false);

  const [edaPayload, setEdaPayload] = useState<Day2EdaPayload | null>(null);
  const [edaLoading, setEdaLoading] = useState<boolean>(false);
  const [edaRunning, setEdaRunning] = useState<boolean>(false);

  const [prepPayload, setPrepPayload] = useState<Day3PreprocessingPayload | null>(null);
  const [prepLoading, setPrepLoading] = useState<boolean>(false);
  const [prepRunning, setPrepRunning] = useState<boolean>(false);

  const [featuresPayload, setFeaturesPayload] = useState<Day4FeaturesPayload | null>(null);
  const [featuresLoading, setFeaturesLoading] = useState<boolean>(false);
  const [featuresRunning, setFeaturesRunning] = useState<boolean>(false);

  const [docs, setDocs] = useState<DocItem[]>([]);
  const [selectedDocKey, setSelectedDocKey] = useState<string>('preprocessing_note');
  const [docEditMode, setDocEditMode] = useState<boolean>(false);
  const [docDraft, setDocDraft] = useState<string>('');
  const [saveFeedback, setSaveFeedback] = useState<string>('');

  const [day1State, setDay1State] = useState<Day1State | null>(null);
  const [mentorDraft, setMentorDraft] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<string>('');

  const [sampleQuery, setSampleQuery] = useState<string>('');
  const [sampleLabelFilter, setSampleLabelFilter] = useState<string>('ALL');

  const loadEnv = useCallback(async () => {
    setEnvLoading(true);
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
    } finally {
      setEnvLoading(false);
    }
  }, []);

  const loadRepoAndDocs = useCallback(async () => {
    try {
      const [repoRes, docsRes, stateRes] = await Promise.all([
        fetch('/api/repo/status'),
        fetch('/api/docs'),
        fetch('/api/day1/state'),
      ]);
      if (repoRes.ok) setRepoStatus(await repoRes.json());
      if (docsRes.ok) {
        const payload = await docsRes.json();
        setDocs(payload.docs || []);
        const mentorDoc = (payload.docs || []).find((d: DocItem) => d.key === 'mentor_message');
        if (mentorDoc) setMentorDraft(mentorDoc.content);
      }
      if (stateRes.ok) setDay1State(await stateRes.json());
    } catch {
      // ignore transient startup errors
    }
  }, []);

  const loadEdaMetrics = useCallback(async () => {
    setEdaLoading(true);
    try {
      const res = await fetch('/api/eda/metrics');
      if (res.ok) {
        setEdaPayload(await res.json());
      }
    } finally {
      setEdaLoading(false);
    }
  }, []);

  const handleRunDay2Eda = useCallback(async () => {
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

  const handleRunDay3Preprocessing = useCallback(
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

  const handleRunDay4Features = useCallback(
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

  const handleRunHeaderCta = useCallback(async () => {
    if (activeTab === 'day2') {
      await handleRunDay2Eda();
    } else if (activeTab === 'day4') {
      await handleRunDay4Features({ topK: 5, normalization: 'snv' });
    } else {
      await handleRunDay3Preprocessing();
    }
  }, [activeTab, handleRunDay2Eda, handleRunDay3Preprocessing, handleRunDay4Features]);

  const loadDataset = useCallback(async (source: 'primary' | 'synthetic') => {
    setDatasetLoading(true);
    try {
      const res = await fetch(`/api/dataset/summary?source=${source}`);
      if (res.ok) {
        setDatasetSummary(await res.json());
      }
    } finally {
      setDatasetLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEnv();
    loadRepoAndDocs();
    loadEdaMetrics();
    loadPreprocessingMetrics();
    loadFeaturesMetrics();
  }, [loadEnv, loadRepoAndDocs, loadEdaMetrics, loadPreprocessingMetrics, loadFeaturesMetrics]);

  useEffect(() => {
    loadDataset(datasetSource);
  }, [datasetSource, loadDataset]);

  useEffect(() => {
    const activeDoc = docs.find((d) => d.key === selectedDocKey);
    if (activeDoc) {
      setDocDraft(activeDoc.content);
    }
  }, [selectedDocKey, docs]);

  const updateDay1State = async (patch: Partial<Day1State>) => {
    if (!day1State) return;
    const optimistic = { ...day1State, ...patch };
    setDay1State(optimistic);
    try {
      const res = await fetch('/api/day1/state', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(optimistic),
      });
      if (res.ok) {
        setDay1State(await res.json());
      }
    } catch {
      // keep optimistic
    }
  };

  const toggleBlockComplete = (blockId: number) => {
    if (!day1State) return;
    const exists = day1State.completedBlocks.includes(blockId);
    const next = exists
      ? day1State.completedBlocks.filter((id) => id !== blockId)
      : [...day1State.completedBlocks, blockId].sort((a, b) => a - b);
    updateDay1State({ completedBlocks: next });
  };

  const toggleDay2Block = (blockId: number) => {
    if (!day1State) return;
    const current = day1State.day2CompletedBlocks ?? [1, 2, 3, 4, 5, 6];
    const exists = current.includes(blockId);
    const next = exists
      ? current.filter((id) => id !== blockId)
      : [...current, blockId].sort((a, b) => a - b);
    updateDay1State({ day2CompletedBlocks: next });
  };

  const toggleDay3Block = (blockId: number) => {
    if (!day1State) return;
    const current = day1State.day3CompletedBlocks ?? [1, 2, 3, 4, 5, 6, 7];
    const exists = current.includes(blockId);
    const next = exists
      ? current.filter((id) => id !== blockId)
      : [...current, blockId].sort((a, b) => a - b);
    updateDay1State({ day3CompletedBlocks: next });
  };

  const toggleDay4Block = (blockId: number) => {
    if (!day1State) return;
    const current = day1State.day4CompletedBlocks ?? [1, 2, 3, 4, 5, 6];
    const exists = current.includes(blockId);
    const next = exists
      ? current.filter((id) => id !== blockId)
      : [...current, blockId].sort((a, b) => a - b);
    updateDay1State({ day4CompletedBlocks: next });
  };

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
        setSaveFeedback('Saved to workspace');
        setTimeout(() => setSaveFeedback(''), 2500);
      } else {
        setSaveFeedback('Save failed');
      }
    } catch {
      setSaveFeedback('Save failed');
    }
  };

  const handleCopyText = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(''), 2000);
    } catch {
      // clipboard fallback
    }
  };

  const handleDownloadFile = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const completedCount = day1State?.completedBlocks.length ?? 0;
  const day2CompletedBlocks = day1State?.day2CompletedBlocks ?? [1, 2, 3, 4, 5, 6];
  const day3CompletedBlocks = day1State?.day3CompletedBlocks ?? [1, 2, 3, 4, 5, 6, 7];
  const day4CompletedBlocks = day1State?.day4CompletedBlocks ?? [1, 2, 3, 4, 5, 6];
  const passedPackages = envResult?.packages.filter((p) => p.status === 'ok').length ?? 0;
  const totalPackages = envResult?.packages.length ?? 6;
  const presentDirs = repoStatus?.directories.filter((d) => d.exists).length ?? 0;
  const totalDirs = repoStatus?.directories.length ?? 8;

  const activeDoc = docs.find((d) => d.key === selectedDocKey);
  const dataSummaryDoc = docs.find((d) => d.key === 'data_summary')?.content || '';
  const preprocessingNoteDoc = docs.find((d) => d.key === 'preprocessing_note')?.content || '';
  const featureNoteDoc = docs.find((d) => d.key === 'feature_engineering_note')?.content || '';
  const isDocEditable =
    selectedDocKey === 'project_brief' ||
    selectedDocKey === 'data_summary' ||
    selectedDocKey === 'preprocessing_note' ||
    selectedDocKey === 'feature_engineering_note' ||
    selectedDocKey === 'dataset_note' ||
    selectedDocKey === 'mentor_message' ||
    selectedDocKey === 'readme';

  const filteredSampleRows = useMemo(() => {
    if (!datasetSummary) return [];
    return datasetSummary.sampleRows.filter((row) => {
      const matchesLabel = sampleLabelFilter === 'ALL' || row.label === sampleLabelFilter;
      const q = sampleQuery.trim().toLowerCase();
      const matchesQuery =
        !q ||
        row.plantId.toLowerCase().includes(q) ||
        row.date.toLowerCase().includes(q) ||
        row.sampleId.toLowerCase().includes(q);
      return matchesLabel && matchesQuery;
    });
  }, [datasetSummary, sampleLabelFilter, sampleQuery]);

  const navItems: Array<{ id: ActiveTab; label: string }> = [
    { id: 'overview', label: 'Overview' },
    { id: 'day1', label: 'Day 1' },
    { id: 'day2', label: 'Day 2 EDA' },
    { id: 'day3', label: 'Day 3 Prep' },
    { id: 'day4', label: 'Day 4 Features' },
    { id: 'brief', label: 'Docs & Repo' },
  ];

  const activeEda = edaPayload
    ? edaSource === 'synthetic'
      ? edaPayload.synthetic
      : edaPayload.primary
    : null;

  const activePrep = prepPayload
    ? pipelineSource === 'synthetic'
      ? prepPayload.synthetic
      : prepPayload.primary
    : null;

  const activeFeatures = featuresPayload
    ? pipelineSource === 'synthetic'
      ? featuresPayload.synthetic
      : featuresPayload.primary
    : null;

  const bestFeatureSet = activeFeatures
    ? [...activeFeatures.manifest.feature_sets].sort(
        (a, b) => Math.max(b.cv_macro_f1_lr, b.cv_macro_f1_rf) - Math.max(a.cv_macro_f1_lr, a.cv_macro_f1_rf)
      )[0]
    : null;

  const headerRunning = edaRunning || prepRunning || featuresRunning;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Top Bar Contract: 3 zones, gap-8, single-line controls */}
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200">
        <div className="max-w-[1280px] mx-auto px-6 h-16 flex items-center justify-between gap-8">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className="text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0 cursor-pointer focus-visible:outline-2 focus-visible:outline-teal-700"
          >
            SpectralCrop
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
              onClick={handleRunHeaderCta}
              disabled={headerRunning}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-teal-800 hover:bg-teal-900 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${headerRunning ? 'animate-spin' : ''}`} />
              <span>
                {headerRunning
                  ? 'Running...'
                  : activeTab === 'day2'
                    ? 'Run Day 2 EDA'
                    : activeTab === 'day4'
                      ? 'Run Day 4 Features'
                      : 'Run Day 3 Prep'}
              </span>
            </button>
          </div>
        </div>

        {/* Mobile navigation fallback */}
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
        {/* Hero Header & 4-Column KPI Strip */}
        <section className="space-y-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-mono">
              <span>Day 1 – Day 4</span>
              <span aria-hidden="true">·</span>
              <span>Mon 16 Nov – Thu 19 Nov</span>
              <span aria-hidden="true">·</span>
              <span>EDA, Preprocessing &amp; Leak-Free Feature Sets A–E</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 [text-wrap:balance] max-w-3xl">
              Crop Stress Detection &amp; Temporal Forecast Workbench
            </h1>
            <p className="text-sm text-slate-600 max-w-2xl leading-relaxed">
              Execute modular scikit-learn spectral preprocessing (<code className="font-mono text-slate-800">src/preprocessing.py</code>)
              and build leak-free vegetation index, PCA, and RF/MI Feature Sets A–E (<code className="font-mono text-slate-800">src/features.py</code>).
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Pipeline Progress</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                  Day 1–4
                </span>
                <span className="text-xs font-mono text-slate-400">
                  {completedCount + day2CompletedBlocks.length + day3CompletedBlocks.length + day4CompletedBlocks.length} / 25 blocks
                </span>
              </div>
              <div className="mt-2 text-xs text-teal-800 font-medium">
                ● Ready for Day 5 Baseline &amp; XGBoost
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Day 3 Aligned Bands</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {activePrep ? activePrep.manifest.wavelengths_out_nm.length : 9} bands
                </span>
                <span className="text-xs font-mono text-slate-400">
                  ({activePrep ? activePrep.manifest.train_rows : 1815} tr / {activePrep ? activePrep.manifest.test_rows : 457} te)
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-600 font-mono tabular-nums">
                {activePrep
                  ? `Dropped ${activePrep.manifest.dropped_wavelengths_nm.join(', ') || 'none'} nm · ${activePrep.dropped_nan_rows} NaN rows`
                  : 'Loading preprocessing...'}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Day 4 Best Feature Set</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {bestFeatureSet ? bestFeatureSet.code : 'Set E'}
                </span>
                <span className="text-xs font-mono text-teal-800 font-semibold">
                  {bestFeatureSet
                    ? `F1 ${Math.max(bestFeatureSet.cv_macro_f1_lr, bestFeatureSet.cv_macro_f1_rf).toFixed(3)}`
                    : 'Computing CV...'}
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-600 font-mono tabular-nums">
                {bestFeatureSet
                  ? `${bestFeatureSet.n_features} features · Plant-Grouped CV`
                  : 'Auditing sets A–E...'}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-500">Stack &amp; Repository</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                  {passedPackages} / {totalPackages}
                </span>
                <span className="text-xs font-mono text-slate-400">
                  {presentDirs}/{totalDirs} dirs
                </span>
              </div>
              <div className="mt-2 text-xs text-teal-800 font-medium">
                {envResult?.all_ok ? '● Stack & Git verified' : '▲ Verify Python stack'}
              </div>
            </div>
          </div>
        </section>

        {/* OVERVIEW VIEW */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left column: Done-When Criteria + Schedule Table */}
            <div className="lg:col-span-7 space-y-6">
              <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
                <div className="flex items-center justify-between gap-4">
                  <h2 className="text-base font-semibold text-slate-900">
                    Day 1 – Day 4 Done-When Verification
                  </h2>
                  <span className="text-xs font-mono text-slate-500">
                    Ready for Day 5 Modeling
                  </span>
                </div>

                <div className="divide-y divide-slate-100">
                  <div className="py-3 flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        1. Day 1 Environment, Git Repo &amp; Dataset Scope Locked
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Zenodo 22755812 + Synthetic fallback verified via{' '}
                        <code className="font-mono text-slate-700">verify_env.py</code>.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('day1')}
                      className="text-xs font-medium text-teal-800 hover:underline whitespace-nowrap shrink-0 cursor-pointer"
                    >
                      ● Open Day 1
                    </button>
                  </div>

                  <div className="py-3 flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        2. Day 2 Data Loading &amp; Spectral EDA ({activeEda ? activeEda.sanity.labeled_rows : 2280} scans)
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        <code className="font-mono text-slate-700">src/data.py</code>, 4 EDA figures, outlier audit &amp; <code className="font-mono text-slate-700">docs/data_summary.md</code>.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('day2')}
                      className="text-xs font-medium text-teal-800 hover:underline whitespace-nowrap shrink-0 cursor-pointer"
                    >
                      ● Open Day 2 EDA
                    </button>
                  </div>

                  <div className="py-3 flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        3. Day 3 Preprocessing Pipeline (SavGol, SNV, MSC, 1st Deriv)
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Leak-free <code className="font-mono text-slate-700">src/preprocessing.py</code> &amp; <code className="font-mono text-slate-700">notebooks/02_preprocessing.ipynb</code> with aligned wavelengths.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('day3')}
                      className="text-xs font-medium text-teal-800 hover:underline whitespace-nowrap shrink-0 cursor-pointer"
                    >
                      ● Open Day 3 Prep
                    </button>
                  </div>

                  <div className="py-3 flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        4. Day 4 Feature Sets A–E, VIs &amp; Train-Only PCA / RF+MI Selection
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        <code className="font-mono text-slate-700">src/features.py</code>, MCARI (Daughtry et al. 2000), &amp; saved `.npz` sets in <code className="font-mono text-slate-700">data/processed/</code>.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('day4')}
                      className="text-xs font-medium text-teal-800 hover:underline whitespace-nowrap shrink-0 cursor-pointer"
                    >
                      ● Open Day 4 Features
                    </button>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-200 bg-slate-50 -mx-5 -mb-5 px-5 py-3.5 rounded-b-lg">
                  <div className="text-xs font-semibold text-slate-800">
                    Carry Forward to Day 3 &amp; Day 5 Leak-Free Splits
                  </div>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    Group CV folds by <code className="font-mono text-slate-800">plant_id</code>{' '}
                    (79 plants) and order forecasts by{' '}
                    <code className="font-mono text-slate-800">date</code> (31 dates). Drop 8
                    failed-scan NaN rows and audit edge bands{' '}
                    <code className="font-mono text-slate-800">Mean_365</code> &amp;{' '}
                    <code className="font-mono text-slate-800">Mean_970</code> on Day 3.
                  </p>
                </div>
              </div>

              {/* Compact 6-block summary table */}
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
                  <h2 className="text-base font-semibold text-slate-900">Day 1 Schedule</h2>
                  <button
                    type="button"
                    onClick={() => setActiveTab('day1')}
                    className="text-xs font-medium text-teal-800 hover:underline cursor-pointer"
                  >
                    Open Interactive Blocks
                  </button>
                </div>
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-4 py-2.5 font-medium w-16">Block</th>
                      <th className="px-4 py-2.5 font-medium">Task</th>
                      <th className="px-4 py-2.5 font-medium text-right w-20">Time</th>
                      <th className="px-4 py-2.5 font-medium text-right w-24">State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {SCHEDULE_BLOCKS.map((block) => {
                      const done = day1State?.completedBlocks.includes(block.id) ?? false;
                      return (
                        <tr
                          key={block.id}
                          onClick={() => {
                            setActiveTab('day1');
                            setActiveBlockId(block.id);
                          }}
                          className="hover:bg-slate-50 cursor-pointer transition-colors"
                        >
                          <td className="px-4 py-3 font-mono tabular-nums font-semibold text-slate-700">
                            0{block.id}
                          </td>
                          <td className="px-4 py-3 text-slate-800">
                            <div className="font-medium">{block.title}</div>
                            <div className="text-slate-500 mt-0.5 line-clamp-1">{block.task}</div>
                          </td>
                          <td className="px-4 py-3 font-mono tabular-nums text-right text-slate-600 whitespace-nowrap">
                            {block.timeBudget}
                          </td>
                          <td
                            className={`px-4 py-3 text-right font-medium whitespace-nowrap ${
                              done ? 'text-teal-800' : 'text-slate-500'
                            }`}
                          >
                            {done ? '● Done' : '○ Open'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right column: Live Python Environment + Repo Snapshot */}
            <div className="lg:col-span-5 space-y-6">
              <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">
                      Python Environment Audit
                    </h2>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">
                      {envResult?.python_executable || '/usr/bin/python3'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={loadEnv}
                    className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer whitespace-nowrap"
                  >
                    Re-run Test
                  </button>
                </div>

                <div className="border border-slate-200 rounded-md overflow-hidden">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-2 font-medium">Library</th>
                        <th className="px-3 py-2 font-medium text-right">Installed</th>
                        <th className="px-3 py-2 font-medium text-right">Import</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                      {(envResult?.packages || []).map((pkg) => (
                        <tr key={pkg.module}>
                          <td className="px-3 py-2 text-slate-800 font-sans font-medium">
                            {pkg.name}
                          </td>
                          <td className="px-3 py-2 text-right text-slate-600">
                            {pkg.installed_version || '—'}
                          </td>
                          <td
                            className={`px-3 py-2 text-right font-sans font-medium ${
                              pkg.status === 'ok' ? 'text-teal-800' : 'text-rose-700'
                            }`}
                          >
                            {pkg.status === 'ok' ? 'PASS' : 'FAIL'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-slate-900">
                    Dataset &amp; Output Files
                  </h2>
                  <button
                    type="button"
                    onClick={() => setActiveTab('brief')}
                    className="text-xs font-medium text-teal-800 hover:underline cursor-pointer"
                  >
                    Edit Brief &amp; Notes
                  </button>
                </div>
                <div className="space-y-2 text-xs">
                  {(repoStatus?.files || []).slice(0, 9).map((f) => (
                    <div
                      key={f.path}
                      className="flex items-center justify-between py-1.5 border-b border-slate-100 last:border-b-0"
                    >
                      <span className="font-mono text-slate-700 truncate pr-3">{f.path}</span>
                      <span className="font-mono tabular-nums text-slate-500 whitespace-nowrap">
                        {f.exists ? formatBytes(f.sizeBytes) : 'Missing'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* DAY 1 SCHEDULE VIEW */}
        {activeTab === 'day1' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left block list */}
            <aside className="lg:col-span-4 bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
              {SCHEDULE_BLOCKS.map((block) => {
                const isSelected = activeBlockId === block.id;
                const isDone = day1State?.completedBlocks.includes(block.id) ?? false;
                return (
                  <button
                    key={block.id}
                    type="button"
                    onClick={() => setActiveBlockId(block.id)}
                    className={`w-full text-left p-4 transition-colors cursor-pointer flex items-start justify-between gap-3 ${
                      isSelected ? 'bg-slate-50' : 'hover:bg-slate-50/60'
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                        <span>Block 0{block.id}</span>
                        <span aria-hidden="true">·</span>
                        <span className="tabular-nums">{block.timeBudget}</span>
                      </div>
                      <div
                        className={`text-sm font-semibold mt-1 ${
                          isSelected ? 'text-teal-800' : 'text-slate-900'
                        }`}
                      >
                        {block.title}
                      </div>
                    </div>
                    <span
                      className={`text-xs font-medium whitespace-nowrap shrink-0 mt-0.5 ${
                        isDone ? 'text-teal-800' : 'text-slate-400'
                      }`}
                    >
                      {isDone ? '● Done' : '○ Open'}
                    </span>
                  </button>
                );
              })}
            </aside>

            {/* Right active block detail & workspace */}
            <div className="lg:col-span-8 bg-white border border-slate-200 rounded-lg p-6 space-y-6">
              {(() => {
                const currentBlock =
                  SCHEDULE_BLOCKS.find((b) => b.id === activeBlockId) || SCHEDULE_BLOCKS[0];
                const isDone = day1State?.completedBlocks.includes(currentBlock.id) ?? false;
                return (
                  <>
                    <div className="flex flex-wrap items-start justify-between gap-4 pb-4 border-b border-slate-200">
                      <div>
                        <div className="text-xs font-mono text-slate-500">
                          Block 0{currentBlock.id} · {currentBlock.timeBudget} · Deliverable:{' '}
                          {currentBlock.deliverable}
                        </div>
                        <h2 className="text-xl font-bold text-slate-900 mt-1">
                          {currentBlock.title}
                        </h2>
                        <p className="text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
                          {currentBlock.task}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => toggleBlockComplete(currentBlock.id)}
                        className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg border transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                          isDone
                            ? 'bg-teal-800 text-white border-teal-800 hover:bg-teal-900'
                            : 'bg-white text-slate-800 border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>{isDone ? 'Completed' : 'Mark Complete'}</span>
                      </button>
                    </div>

                    {/* Block 1 Workspace */}
                    {currentBlock.id === 1 && (
                      <div className="space-y-5">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1.5">
                              Mentor Reply Status
                            </label>
                            <select
                              value={day1State?.mentorReplyStatus || 'awaiting'}
                              onChange={(e) =>
                                updateDay1State({
                                  mentorReplyStatus: e.target.value as Day1State['mentorReplyStatus'],
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-md focus:outline-none focus:border-teal-700"
                            >
                              <option value="awaiting">Awaiting mentor reply (Tuesday cutoff)</option>
                              <option value="confirmed">Scope &amp; cadence confirmed</option>
                              <option value="auto_fallback">Proceeding with selected Zenodo option</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1.5">
                              Preferred Update Cadence
                            </label>
                            <select
                              value={day1State?.progressCadence || 'daily_slack'}
                              onChange={(e) =>
                                updateDay1State({
                                  progressCadence: e.target.value as Day1State['progressCadence'],
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-md focus:outline-none focus:border-teal-700"
                            >
                              <option value="daily_slack">Daily end-of-day Slack summary</option>
                              <option value="daily_github">Daily GitHub commit &amp; PR notes</option>
                              <option value="midweek_sync">Mid-week sync + Friday review</option>
                            </select>
                          </div>
                        </div>

                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <label className="text-xs font-medium text-slate-700">
                              Mentor Message &amp; Scope Log (docs/mentor_message.md)
                            </label>
                            <div className="flex items-center gap-2">
                              {saveFeedback && (
                                <span className="text-xs text-teal-800 font-medium">
                                  {saveFeedback}
                                </span>
                              )}
                              <button
                                type="button"
                                onClick={() => handleCopyText('mentor', mentorDraft)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer"
                              >
                                <Copy className="w-3.5 h-3.5" />
                                <span>{copiedKey === 'mentor' ? 'Copied' : 'Copy'}</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => saveDocument('mentor_message', mentorDraft)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-teal-800 text-white rounded-md hover:bg-teal-900 cursor-pointer"
                              >
                                <Save className="w-3.5 h-3.5" />
                                <span>Save</span>
                              </button>
                            </div>
                          </div>
                          <textarea
                            rows={14}
                            value={mentorDraft}
                            onChange={(e) => setMentorDraft(e.target.value)}
                            className="w-full p-3 text-xs font-mono leading-relaxed bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:border-teal-700"
                          />
                        </div>
                      </div>
                    )}

                    {/* Block 2 Workspace */}
                    {currentBlock.id === 2 && (
                      <div className="space-y-4">
                        <p className="text-xs text-slate-600">
                          Live filesystem check against the Day 1 required repository layout.
                        </p>
                        <div className="border border-slate-200 rounded-md overflow-hidden">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                                <th className="px-3 py-2 font-medium">Directory</th>
                                <th className="px-3 py-2 font-medium">Purpose</th>
                                <th className="px-3 py-2 font-medium text-right">Items</th>
                                <th className="px-3 py-2 font-medium text-right">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {(repoStatus?.directories || []).map((dir) => (
                                <tr key={dir.path}>
                                  <td className="px-3 py-2 font-mono text-slate-900">{dir.path}/</td>
                                  <td className="px-3 py-2 text-slate-600">{dir.purpose}</td>
                                  <td className="px-3 py-2 font-mono tabular-nums text-right text-slate-600">
                                    {dir.itemCount}
                                  </td>
                                  <td
                                    className={`px-3 py-2 text-right font-medium ${
                                      dir.exists ? 'text-teal-800' : 'text-rose-700'
                                    }`}
                                  >
                                    {dir.exists ? 'PASS' : 'MISSING'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Block 3 Workspace */}
                    {currentBlock.id === 3 && (
                      <div className="space-y-4">
                        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 border border-slate-200 rounded-md p-3">
                          <code className="text-xs font-mono text-slate-800">
                            python3 src/pipeline/verify_env.py
                          </code>
                          <button
                            type="button"
                            onClick={loadEnv}
                            disabled={envLoading}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-teal-800 text-white rounded-md hover:bg-teal-900 cursor-pointer"
                          >
                            <Play className="w-3.5 h-3.5" />
                            <span>{envLoading ? 'Running...' : 'Execute Import Test'}</span>
                          </button>
                        </div>

                        <div className="border border-slate-200 rounded-md overflow-hidden">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                                <th className="px-3 py-2 font-medium">Package</th>
                                <th className="px-3 py-2 font-medium">Module</th>
                                <th className="px-3 py-2 font-medium text-right">Min Spec</th>
                                <th className="px-3 py-2 font-medium text-right">Installed</th>
                                <th className="px-3 py-2 font-medium text-right">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                              {(envResult?.packages || []).map((pkg) => (
                                <tr key={pkg.module}>
                                  <td className="px-3 py-2 font-sans font-medium text-slate-900">
                                    {pkg.name}
                                  </td>
                                  <td className="px-3 py-2 text-slate-600">{pkg.module}</td>
                                  <td className="px-3 py-2 text-right text-slate-500">
                                    &ge;{pkg.min_version}
                                  </td>
                                  <td className="px-3 py-2 text-right text-slate-800">
                                    {pkg.installed_version || '—'}
                                  </td>
                                  <td
                                    className={`px-3 py-2 text-right font-sans font-medium ${
                                      pkg.status === 'ok' ? 'text-teal-800' : 'text-rose-700'
                                    }`}
                                  >
                                    {pkg.status === 'ok' ? 'PASS' : 'FAIL'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Block 4 Workspace */}
                    {currentBlock.id === 4 && (
                      <div className="space-y-4">
                        <p className="text-xs text-slate-600">
                          Candidate spectral repositories audited across Kaggle, Zenodo, Mendeley
                          Data, and IEEE DataPort for licence, format, and temporal grouping keys.
                        </p>
                        <div className="border border-slate-200 rounded-md overflow-x-auto">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                                <th className="px-3 py-2.5 font-medium">Portal</th>
                                <th className="px-3 py-2.5 font-medium">Candidate Dataset</th>
                                <th className="px-3 py-2.5 font-medium">Licence</th>
                                <th className="px-3 py-2.5 font-medium">Format &amp; Labels</th>
                                <th className="px-3 py-2.5 font-medium">Verdict</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {PORTAL_SEARCH_MATRIX.map((row) => (
                                <tr key={row.portal} className="align-top">
                                  <td className="px-3 py-2.5 font-semibold text-slate-900 whitespace-nowrap">
                                    {row.portal}
                                  </td>
                                  <td className="px-3 py-2.5 text-slate-700">{row.candidate}</td>
                                  <td className="px-3 py-2.5 font-mono text-slate-700 whitespace-nowrap">
                                    {row.licence}
                                  </td>
                                  <td className="px-3 py-2.5 text-slate-600">
                                    <div>{row.format}</div>
                                    <div className="text-slate-500 mt-0.5">{row.labels}</div>
                                  </td>
                                  <td className="px-3 py-2.5 font-medium text-teal-800 whitespace-nowrap">
                                    {row.verdict}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Block 5 Workspace */}
                    {currentBlock.id === 5 && (
                      <div className="space-y-4">
                        <p className="text-xs text-slate-600">
                          Dataset selection follows the Day 1 fallback order. Both the primary Zenodo
                          CSV and companion synthetic benchmark are downloaded and ready in{' '}
                          <code className="font-mono">data/raw/</code>.
                        </p>
                        <div className="space-y-3">
                          {FALLBACK_TIERS.map((item) => (
                            <div
                              key={item.tier}
                              className="p-4 border border-slate-200 rounded-lg bg-slate-50/50 space-y-1.5"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                                <span className="font-mono font-semibold text-slate-700">
                                  {item.tier}
                                </span>
                                <span className="font-medium text-teal-800">{item.status}</span>
                              </div>
                              <div className="text-sm font-semibold text-slate-900">
                                {item.title}
                              </div>
                              <p className="text-xs text-slate-600 leading-relaxed">{item.detail}</p>
                            </div>
                          ))}
                        </div>
                        <div className="flex items-center gap-3 pt-2">
                          <button
                            type="button"
                            onClick={() => setActiveTab('day2')}
                            className="px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 cursor-pointer"
                          >
                            Open Day 2 Spectral EDA
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Block 6 Workspace */}
                    {currentBlock.id === 6 && (
                      <div className="space-y-4">
                        <p className="text-xs text-slate-600">
                          The one-page project brief is stored at{' '}
                          <code className="font-mono">docs/project_brief.md</code> and covers
                          problem framing, dataset characteristics, leak-free split strategy, and
                          success metrics.
                        </p>
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedDocKey('project_brief');
                              setActiveTab('brief');
                            }}
                            className="px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 cursor-pointer"
                          >
                            View &amp; Edit Project Brief
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedDocKey('dataset_note');
                              setActiveTab('brief');
                            }}
                            className="px-4 py-2 text-xs font-medium border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 cursor-pointer"
                          >
                            View Dataset Note
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        )}

        {/* DAY 2 DATA LOADING & EDA VIEW */}
        {activeTab === 'day2' && (
          <div className="space-y-8">
            <Day2EdaView
              edaPayload={edaPayload}
              edaLoading={edaLoading}
              edaRunning={edaRunning}
              edaSource={edaSource}
              onChangeSource={setEdaSource}
              onRunEda={handleRunDay2Eda}
              completedBlocks={day2CompletedBlocks}
              onToggleBlock={toggleDay2Block}
              dataSummaryMarkdown={dataSummaryDoc}
              onOpenDoc={(key) => {
                setSelectedDocKey(key);
                setDocEditMode(false);
                setWorkspaceSub('docs');
                setActiveTab('brief');
              }}
            />

            {/* Dataset Scan Records Table */}
            {datasetSummary && (
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      Sample Scan Records &amp; Computed Indices ({datasetSource === 'synthetic' ? 'Synthetic' : 'Zenodo Primary'})
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Interactive preview of matched plant observations with Red (670 nm), NIR (780 nm), NDVI, and NDRE
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
                      <button
                        type="button"
                        onClick={() => setDatasetSource('primary')}
                        className={`px-2.5 py-1 text-xs font-medium rounded-md cursor-pointer ${
                          datasetSource === 'primary' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                        }`}
                      >
                        Primary
                      </button>
                      <button
                        type="button"
                        onClick={() => setDatasetSource('synthetic')}
                        className={`px-2.5 py-1 text-xs font-medium rounded-md cursor-pointer ${
                          datasetSource === 'synthetic' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                        }`}
                      >
                        Synthetic
                      </button>
                    </div>
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        value={sampleQuery}
                        onChange={(e) => setSampleQuery(e.target.value)}
                        placeholder="Filter Plant ID or date..."
                        className="pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-teal-700"
                      />
                    </div>
                    <select
                      value={sampleLabelFilter}
                      onChange={(e) => setSampleLabelFilter(e.target.value)}
                      className="px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-teal-700"
                    >
                      <option value="ALL">All Labels</option>
                      {datasetSummary.curves.map((c) => (
                        <option key={c.label} value={c.label}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-2.5 font-medium">Plant ID</th>
                        <th className="px-3 py-2.5 font-medium">Pot / Plot</th>
                        <th className="px-3 py-2.5 font-medium">Date</th>
                        <th className="px-3 py-2.5 font-medium">Label</th>
                        <th className="px-3 py-2.5 font-medium text-right">R670 (%)</th>
                        <th className="px-3 py-2.5 font-medium text-right">R780 (%)</th>
                        <th className="px-3 py-2.5 font-medium text-right">NDVI</th>
                        <th className="px-3 py-2.5 font-medium text-right">NDRE</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                      {filteredSampleRows.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="px-4 py-6 text-center text-slate-500 font-sans">
                            No matching sample rows for the current filter.
                          </td>
                        </tr>
                      ) : (
                        filteredSampleRows.map((row) => (
                          <tr key={row.sampleId} className="hover:bg-slate-50/70">
                            <td className="px-3 py-2 font-semibold text-slate-900">
                              {row.plantId}
                            </td>
                            <td className="px-3 py-2 text-slate-600">{row.potNumber}</td>
                            <td className="px-3 py-2 text-slate-600">{row.date}</td>
                            <td className="px-3 py-2 font-sans text-slate-800">{row.label}</td>
                            <td className="px-3 py-2 text-right text-slate-700">
                              {row.r670.toFixed(2)}
                            </td>
                            <td className="px-3 py-2 text-right text-slate-700">
                              {row.r780.toFixed(2)}
                            </td>
                            <td className="px-3 py-2 text-right font-semibold text-teal-800">
                              {row.ndvi.toFixed(3)}
                            </td>
                            <td className="px-3 py-2 text-right text-slate-700">
                              {row.ndre.toFixed(3)}
                            </td>
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

        {/* DAY 3 PREPROCESSING & SPECTRAL TRANSFORMS VIEW */}
        {activeTab === 'day3' && (
          <Day3PreprocessingView
            prepPayload={prepPayload}
            prepLoading={prepLoading}
            prepRunning={prepRunning}
            source={pipelineSource}
            onChangeSource={setPipelineSource}
            onRunPreprocessing={handleRunDay3Preprocessing}
            completedBlocks={day3CompletedBlocks}
            onToggleBlock={toggleDay3Block}
            noteMarkdown={preprocessingNoteDoc}
            onOpenDoc={(key) => {
              setSelectedDocKey(key);
              setDocEditMode(false);
              setWorkspaceSub('docs');
              setActiveTab('brief');
            }}
          />
        )}

        {/* DAY 4 FEATURE ENGINEERING VIEW */}
        {activeTab === 'day4' && (
          <Day4FeaturesView
            featuresPayload={featuresPayload}
            featuresLoading={featuresLoading}
            featuresRunning={featuresRunning}
            source={pipelineSource}
            onChangeSource={setPipelineSource}
            onRunFeatures={handleRunDay4Features}
            completedBlocks={day4CompletedBlocks}
            onToggleBlock={toggleDay4Block}
            noteMarkdown={featureNoteDoc}
            onOpenDoc={(key) => {
              setSelectedDocKey(key);
              setDocEditMode(false);
              setWorkspaceSub('docs');
              setActiveTab('brief');
            }}
          />
        )}

        {/* DOCS & REPOSITORY UNIFIED VIEW */}
        {activeTab === 'brief' && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 bg-white border border-slate-200 rounded-lg px-5 py-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  Project Documentation, Scripts &amp; Repository Manifest
                </h2>
                <p className="text-xs text-slate-500">
                  Inspect/edit markdown notes, review Python source modules, and audit Git commit status
                </p>
              </div>
              <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
                <button
                  type="button"
                  onClick={() => setWorkspaceSub('docs')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer ${
                    workspaceSub === 'docs' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  Documentation &amp; Code ({docs.length})
                </button>
                <button
                  type="button"
                  onClick={() => setWorkspaceSub('repo')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer ${
                    workspaceSub === 'repo' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  Repository &amp; Git ({repoStatus?.files.filter((f) => f.exists).length ?? 0}/{repoStatus?.files.length ?? 0})
                </button>
              </div>
            </div>

            {workspaceSub === 'docs' && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <aside className="lg:col-span-3 bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
              {docs.map((doc) => (
                <button
                  key={doc.key}
                  type="button"
                  onClick={() => {
                    setSelectedDocKey(doc.key);
                    setDocEditMode(false);
                  }}
                  className={`w-full text-left p-3.5 transition-colors cursor-pointer ${
                    selectedDocKey === doc.key ? 'bg-slate-50' : 'hover:bg-slate-50/60'
                  }`}
                >
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                    <FileText className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{doc.relPath}</span>
                  </div>
                  <div
                    className={`text-sm font-medium mt-1 ${
                      selectedDocKey === doc.key ? 'text-teal-800' : 'text-slate-900'
                    }`}
                  >
                    {doc.label}
                  </div>
                </button>
              ))}
            </aside>

            <div className="lg:col-span-9 bg-white border border-slate-200 rounded-lg p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
                <div>
                  <div className="text-xs font-mono text-slate-500">{activeDoc?.relPath}</div>
                  <h2 className="text-lg font-bold text-slate-900 mt-0.5">{activeDoc?.label}</h2>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {saveFeedback && (
                    <span className="text-xs font-medium text-teal-800 mr-2">{saveFeedback}</span>
                  )}
                  <button
                    type="button"
                    onClick={() =>
                      activeDoc &&
                      handleDownloadFile(
                        activeDoc.relPath.split('/').pop() || `${activeDoc.key}.md`,
                        docDraft
                      )
                    }
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer whitespace-nowrap"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </button>

                  {isDocEditable && (
                    <button
                      type="button"
                      onClick={() => setDocEditMode((prev) => !prev)}
                      className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer whitespace-nowrap"
                    >
                      {docEditMode ? 'Preview Rendered' : 'Edit Source'}
                    </button>
                  )}

                  {isDocEditable && docEditMode && (
                    <button
                      type="button"
                      onClick={() => saveDocument(selectedDocKey, docDraft)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-teal-800 text-white rounded-md hover:bg-teal-900 cursor-pointer whitespace-nowrap"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>Save to Disk</span>
                    </button>
                  )}
                </div>
              </div>

              {docEditMode ? (
                <textarea
                  rows={24}
                  value={docDraft}
                  onChange={(e) => setDocDraft(e.target.value)}
                  className="w-full p-4 text-xs font-mono leading-relaxed bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:border-teal-700"
                />
              ) : (
                <MarkdownViewer content={activeDoc?.content || ''} />
              )}
            </div>
            </div>
            )}

            {workspaceSub === 'repo' && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-7 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">
                  Repository Artifact Manifest
                </h2>
                <button
                  type="button"
                  onClick={loadRepoAndDocs}
                  className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer"
                >
                  Refresh Tree
                </button>
              </div>
              <div className="border border-slate-200 rounded-md overflow-hidden">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-3 py-2 font-medium">File Path</th>
                      <th className="px-3 py-2 font-medium text-right">Size</th>
                      <th className="px-3 py-2 font-medium text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                    {(repoStatus?.files || []).map((f) => (
                      <tr key={f.path}>
                        <td className="px-3 py-2 text-slate-800">{f.path}</td>
                        <td className="px-3 py-2 text-right text-slate-500">
                          {f.exists ? formatBytes(f.sizeBytes) : '—'}
                        </td>
                        <td
                          className={`px-3 py-2 text-right font-sans font-medium ${
                            f.exists ? 'text-teal-800' : 'text-rose-700'
                          }`}
                        >
                          {f.exists ? 'Present' : 'Missing'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="lg:col-span-5 space-y-6">
              <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <FolderGit2 className="w-4 h-4 text-teal-800" />
                  <h2 className="text-base font-semibold text-slate-900">Git Repository Status</h2>
                </div>
                <div className="text-xs space-y-2">
                  <div className="flex justify-between py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">Initialized</span>
                    <span className="font-mono font-medium text-slate-900">
                      {repoStatus?.git.initialized ? 'Yes' : 'No'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">Active Branch</span>
                    <span className="font-mono font-medium text-slate-900">
                      {repoStatus?.git.branch || '—'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-slate-500">Uncommitted Files</span>
                    <span className="font-mono tabular-nums font-medium text-slate-900">
                      {repoStatus?.git.dirtyCount ?? 0}
                    </span>
                  </div>
                </div>

                {repoStatus?.git.commits && repoStatus.git.commits.length > 0 && (
                  <div className="pt-2 border-t border-slate-200 space-y-2">
                    <div className="text-xs font-medium text-slate-700">Recent Commits</div>
                    {repoStatus.git.commits.map((c) => (
                      <div key={c.hash} className="text-xs flex items-start gap-2.5">
                        <code className="font-mono text-teal-800 shrink-0">{c.hash}</code>
                        <span className="text-slate-700 flex-1">{c.message}</span>
                        <span className="font-mono text-slate-400 shrink-0">{c.date}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
                <h2 className="text-base font-semibold text-slate-900">GitHub Remote Push Guide</h2>
                <pre className="p-3 bg-slate-900 text-slate-100 rounded-md text-xs font-mono overflow-x-auto leading-relaxed">
{`git remote add origin <YOUR_GITHUB_URL>
git branch -M main
git push -u origin main`}
                </pre>
              </div>
            </div>
          </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
