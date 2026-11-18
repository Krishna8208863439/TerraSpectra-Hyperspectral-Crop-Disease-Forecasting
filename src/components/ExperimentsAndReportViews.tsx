import React, { useMemo, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FolderGit2,
  Image as ImageIcon,
  RefreshCw,
  Save,
  Search,
  Table,
  X,
} from 'lucide-react';
import { MarkdownViewer } from './MarkdownViewer';
import type {
  DocItem,
  EnvVerifyResult,
  ExperimentLogRow,
  RepoStatus,
} from '../types/day1';

interface ExperimentsViewProps {
  rows: ExperimentLogRow[];
  allFigures: string[];
  onRefresh: () => void;
}

export const ExperimentsView: React.FC<ExperimentsViewProps> = ({
  rows,
  allFigures,
  onRefresh,
}) => {
  const [subMode, setSubMode] = useState<'ledger' | 'gallery'>('ledger');
  const [search, setSearch] = useState<string>('');
  const [splitFilter, setSplitFilter] = useState<'ALL' | 'HONEST' | 'LEAKY' | 'FORECAST'>('ALL');
  const [dataFilter, setDataFilter] = useState<'ALL' | 'primary' | 'synthetic'>('ALL');
  const [lightboxFigure, setLightboxFigure] = useState<string | null>(null);

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((r) => {
      const matchesData = dataFilter === 'ALL' || r.data_version.toLowerCase().includes(dataFilter);
      const isLeaky = r.cv_scheme.toUpperCase().includes('LEAKY');
      const isForecast = r.cv_scheme.toLowerCase().includes('seq') || r.model.toLowerCase().includes('lag') || r.model.toLowerCase().includes('persistence');
      const matchesSplit =
        splitFilter === 'ALL' ||
        (splitFilter === 'LEAKY' && isLeaky) ||
        (splitFilter === 'FORECAST' && isForecast) ||
        (splitFilter === 'HONEST' && !isLeaky && !isForecast);
      const matchesSearch =
        !q ||
        r.model.toLowerCase().includes(q) ||
        r.features.toLowerCase().includes(q) ||
        r.run_id.toLowerCase().includes(q) ||
        r.notes.toLowerCase().includes(q);
      return matchesData && matchesSplit && matchesSearch;
    });
  }, [rows, search, splitFilter, dataFilter]);

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span>reports/experiment_log.csv</span>
              <span aria-hidden="true">·</span>
              <span>reports/figures/ ({allFigures.length} figures)</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Experiment Ledger &amp; Publication Figure Archive
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
              <button
                type="button"
                onClick={() => setSubMode('ledger')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer ${
                  subMode === 'ledger' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>Experiment Runs ({rows.length})</span>
              </button>
              <button
                type="button"
                onClick={() => setSubMode('gallery')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer ${
                  subMode === 'gallery' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                }`}
              >
                <ImageIcon className="w-3.5 h-3.5" />
                <span>All Figures ({allFigures.length})</span>
              </button>
            </div>

            <button
              type="button"
              onClick={onRefresh}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {subMode === 'ledger' && (
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
            <div className="relative flex-1 min-w-[220px] max-w-md">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter by model, feature set, run ID, or notes..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:border-teal-700"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-md">
                {(['ALL', 'primary', 'synthetic'] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDataFilter(d)}
                    className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer ${
                      dataFilter === d ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                    }`}
                  >
                    {d === 'ALL' ? 'All Datasets' : d === 'primary' ? 'Primary' : 'Synthetic'}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-md">
                {(['ALL', 'HONEST', 'FORECAST', 'LEAKY'] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSplitFilter(s)}
                    className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer ${
                      splitFilter === s ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {subMode === 'ledger' && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="px-3.5 py-2.5 font-medium">Run ID</th>
                  <th className="px-3.5 py-2.5 font-medium">Dataset</th>
                  <th className="px-3.5 py-2.5 font-sans font-medium">Model</th>
                  <th className="px-3.5 py-2.5 font-medium">Features</th>
                  <th className="px-3.5 py-2.5 font-medium">CV Scheme</th>
                  <th className="px-3.5 py-2.5 font-medium text-right">Macro-F1 / MAE</th>
                  <th className="px-3.5 py-2.5 font-medium text-right">Bal.Acc / R²</th>
                  <th className="px-3.5 py-2.5 font-medium text-right">ROC-AUC</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center font-sans text-slate-500">
                      No matching experiment runs found.
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((r) => {
                    const isLeaky = r.cv_scheme.toUpperCase().includes('LEAKY');
                    return (
                      <tr key={r.run_id} className={isLeaky ? 'bg-rose-50/50' : 'hover:bg-slate-50/70'}>
                        <td className="px-3.5 py-2 font-semibold text-slate-800">{r.run_id}</td>
                        <td className="px-3.5 py-2 text-slate-600">{r.data_version}</td>
                        <td className="px-3.5 py-2 font-sans font-medium text-slate-900">{r.model}</td>
                        <td className="px-3.5 py-2 text-slate-600">{r.features}</td>
                        <td className={`px-3.5 py-2 text-[11px] ${isLeaky ? 'text-rose-700 font-semibold' : 'text-slate-500'}`}>
                          {r.cv_scheme}
                        </td>
                        <td className={`px-3.5 py-2 text-right font-semibold ${isLeaky ? 'text-rose-700' : 'text-teal-800'}`}>
                          {r.macro_f1}
                        </td>
                        <td className="px-3.5 py-2 text-right text-slate-700">{r.balanced_acc}</td>
                        <td className="px-3.5 py-2 text-right text-slate-500">{r.roc_auc}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {subMode === 'gallery' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {allFigures.map((figRel) => {
            const filename = figRel.split('/').pop() || figRel;
            const title = filename.replace(/^\d+_/, '').replace('.png', '').replace(/_/g, ' ');
            return (
              <div key={figRel} className="bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col">
                <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[11px] font-mono text-slate-500 truncate">{figRel}</div>
                    <div className="text-xs font-semibold text-slate-900 capitalize mt-0.5 truncate">{title}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLightboxFigure(filename)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-teal-800 hover:underline shrink-0 cursor-pointer"
                  >
                    <span>Expand</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setLightboxFigure(filename)}
                  className="p-2.5 bg-slate-50/60 hover:bg-slate-100/70 transition-colors cursor-zoom-in flex-1 flex items-center"
                >
                  <img
                    src={`/api/figures/${filename}`}
                    alt={title}
                    className="w-full h-auto rounded border border-slate-200 bg-white"
                  />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {lightboxFigure && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/75 flex items-center justify-center p-6"
          onClick={() => setLightboxFigure(null)}
        >
          <div
            className="bg-white rounded-lg max-w-5xl w-full p-4 space-y-3 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <span className="text-xs font-mono text-slate-600">reports/figures/{lightboxFigure}</span>
              <button
                type="button"
                onClick={() => setLightboxFigure(null)}
                className="p-1 text-slate-500 hover:text-slate-900 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <img
              src={`/api/figures/${lightboxFigure}`}
              alt={lightboxFigure}
              className="w-full h-auto max-h-[80vh] object-contain mx-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
};

interface ReportAndRepoViewProps {
  docs: DocItem[];
  selectedDocKey: string;
  onSelectDoc: (key: string) => void;
  onSaveDoc: (key: string, content: string) => Promise<void>;
  saveFeedback: string;
  repoStatus: RepoStatus | null;
  envResult: EnvVerifyResult | null;
  onRefreshRepo: () => void;
  onRefreshEnv: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

const EDITABLE_DOC_KEYS = new Set([
  'project_report',
  'weekly_mentor_update',
  'week3_plan',
  'project_brief',
  'data_summary',
  'preprocessing_note',
  'feature_engineering_note',
  'baseline_results_note',
  'error_interpretability_note',
  'dataset_note',
  'mentor_message',
  'readme',
]);

export const ReportAndRepoView: React.FC<ReportAndRepoViewProps> = ({
  docs,
  selectedDocKey,
  onSelectDoc,
  onSaveDoc,
  saveFeedback,
  repoStatus,
  envResult,
  onRefreshRepo,
  onRefreshEnv,
}) => {
  const [subMode, setSubMode] = useState<'docs' | 'repo'>('docs');
  const [docEditMode, setDocEditMode] = useState<boolean>(false);
  const [docDraft, setDocDraft] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<string>('');

  const activeDoc = docs.find((d) => d.key === selectedDocKey) || docs[0];
  const currentContent = docEditMode ? docDraft : activeDoc?.content || '';
  const isEditable = activeDoc ? EDITABLE_DOC_KEYS.has(activeDoc.key) : false;

  const handleSelect = (doc: DocItem) => {
    onSelectDoc(doc.key);
    setDocEditMode(false);
    setDocDraft(doc.content);
  };

  const handleToggleEdit = () => {
    if (!docEditMode && activeDoc) {
      setDocDraft(activeDoc.content);
    }
    setDocEditMode((prev) => !prev);
  };

  const handleCopy = async () => {
    if (!activeDoc) return;
    try {
      await navigator.clipboard.writeText(currentContent);
      setCopiedKey(activeDoc.key);
      setTimeout(() => setCopiedKey(''), 2000);
    } catch {
      // clipboard fallback
    }
  };

  const handleDownload = () => {
    if (!activeDoc) return;
    const filename = activeDoc.relPath.split('/').pop() || `${activeDoc.key}.md`;
    const blob = new Blob([currentContent], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white border border-slate-200 rounded-lg px-5 py-3.5">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Technical Report, Week 3 Roadmap &amp; Repository Manifest
          </h2>
          <p className="text-xs text-slate-500">
            Read, edit, copy, and export scientific reports, mentor updates, source code modules, and Git history
          </p>
        </div>
        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
          <button
            type="button"
            onClick={() => setSubMode('docs')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer ${
              subMode === 'docs' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Reports &amp; Source ({docs.length})
          </button>
          <button
            type="button"
            onClick={() => setSubMode('repo')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer ${
              subMode === 'repo' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Repo, Python Stack &amp; Git ({repoStatus?.files.filter((f) => f.exists).length ?? 0}/{repoStatus?.files.length ?? 0})
          </button>
        </div>
      </div>

      {subMode === 'docs' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <aside className="lg:col-span-3 bg-white border border-slate-200 rounded-lg divide-y divide-slate-100 max-h-[720px] overflow-y-auto">
            {docs.map((doc) => {
              const isSelected = (activeDoc?.key || '') === doc.key;
              return (
                <button
                  key={doc.key}
                  type="button"
                  onClick={() => handleSelect(doc)}
                  className={`w-full text-left p-3.5 transition-colors cursor-pointer ${
                    isSelected ? 'bg-slate-50' : 'hover:bg-slate-50/60'
                  }`}
                >
                  <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
                    <FileText className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{doc.relPath}</span>
                  </div>
                  <div
                    className={`text-xs font-semibold mt-1 ${
                      isSelected ? 'text-teal-800' : 'text-slate-900'
                    }`}
                  >
                    {doc.label}
                  </div>
                </button>
              );
            })}
          </aside>

          <div className="lg:col-span-9 bg-white border border-slate-200 rounded-lg p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <div className="text-xs font-mono text-slate-500">{activeDoc?.relPath}</div>
                <h2 className="text-lg font-bold text-slate-900 mt-0.5">{activeDoc?.label}</h2>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {saveFeedback && (
                  <span className="text-xs font-medium text-teal-800 mr-1">{saveFeedback}</span>
                )}
                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer whitespace-nowrap"
                >
                  {copiedKey === activeDoc?.key ? (
                    <Check className="w-3.5 h-3.5 text-teal-700" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                  <span>{copiedKey === activeDoc?.key ? 'Copied' : 'Copy'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleDownload}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer whitespace-nowrap"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </button>

                {isEditable && (
                  <button
                    type="button"
                    onClick={handleToggleEdit}
                    className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer whitespace-nowrap"
                  >
                    {docEditMode ? 'Preview Rendered' : 'Edit Source'}
                  </button>
                )}

                {isEditable && docEditMode && activeDoc && (
                  <button
                    type="button"
                    onClick={() => onSaveDoc(activeDoc.key, docDraft)}
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
                rows={26}
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

      {subMode === 'repo' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">
                Repository Artifact Manifest
              </h2>
              <button
                type="button"
                onClick={onRefreshRepo}
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
            {/* Live Python Environment Verification */}
            <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Python Runtime Stack</h2>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    {envResult?.python_executable || '/usr/bin/python3'} · Py {envResult?.python_version || '3.11'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onRefreshEnv}
                  className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 text-slate-700 cursor-pointer whitespace-nowrap"
                >
                  Verify Stack
                </button>
              </div>
              <div className="border border-slate-200 rounded-md divide-y divide-slate-100 text-xs font-mono tabular-nums">
                {(envResult?.packages || []).map((pkg) => (
                  <div key={pkg.name} className="px-3 py-2 flex items-center justify-between">
                    <span className="font-semibold text-slate-800">{pkg.name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-slate-500">{pkg.installed_version || '—'}</span>
                      <span className={pkg.status === 'ok' ? 'text-teal-800 font-semibold' : 'text-rose-700 font-semibold'}>
                        {pkg.status === 'ok' ? 'PASS' : 'FAIL'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Git Repository Status */}
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
          </div>
        </div>
      )}
    </div>
  );
};
