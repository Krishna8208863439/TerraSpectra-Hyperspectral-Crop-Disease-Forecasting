import React, { useState } from 'react';
import { Check, ExternalLink, Lock, Play, RefreshCw, X } from 'lucide-react';
import { BandImportanceChart, PcaScreeChart } from './Day3And4Charts';
import { MarkdownViewer } from './MarkdownViewer';
import type { Day4DatasetFeatures, Day4FeaturesPayload } from '../types/day1';

interface Day4FeaturesViewProps {
  featuresPayload: Day4FeaturesPayload | null;
  featuresLoading: boolean;
  featuresRunning: boolean;
  source: 'primary' | 'synthetic';
  onChangeSource: (src: 'primary' | 'synthetic') => void;
  onRunFeatures: (params: { topK: number; normalization: 'none' | 'snv' | 'msc' }) => void;
  completedBlocks: number[];
  onToggleBlock: (blockId: number) => void;
  noteMarkdown: string;
  onOpenDoc: (key: string) => void;
}

const DAY4_SCHEDULE = [
  { id: 1, title: 'Nearest-Band Helper', time: '30 min' },
  { id: 2, title: 'NDVI, NDRE, PRI, REP, MCARI', time: '90 min' },
  { id: 3, title: 'Train-Only PCA & Variance', time: '1 h' },
  { id: 4, title: 'RF & Mutual Info Selection', time: '90 min' },
  { id: 5, title: 'Named Feature Sets A–E', time: '1 h' },
  { id: 6, title: 'Per-Class Sanity Plots', time: '1 h' },
];

export const Day4FeaturesView: React.FC<Day4FeaturesViewProps> = ({
  featuresPayload,
  featuresLoading,
  featuresRunning,
  source,
  onChangeSource,
  onRunFeatures,
  completedBlocks,
  onToggleBlock,
  noteMarkdown,
  onOpenDoc,
}) => {
  const [subSection, setSubSection] = useState<'sets' | 'pca_bands' | 'figures' | 'note'>('sets');
  const [lightboxFigure, setLightboxFigure] = useState<string | null>(null);
  const [topK, setTopK] = useState<number>(5);
  const [normalization, setNormalization] = useState<'none' | 'snv' | 'msc'>('snv');

  const activeData: Day4DatasetFeatures | null = featuresPayload
    ? source === 'synthetic'
      ? featuresPayload.synthetic
      : featuresPayload.primary
    : null;

  if (featuresLoading && !activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-sm text-slate-500">
        Executing Python feature engineering pipeline (<code className="font-mono">src/features.py</code>)...
      </div>
    );
  }

  if (!activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-8 flex flex-col items-center justify-center gap-4 text-center">
        <div className="text-sm font-medium text-slate-800">
          Day 4 Feature Sets A–E have not been generated yet.
        </div>
        <button
          type="button"
          onClick={() => onRunFeatures({ topK, normalization })}
          disabled={featuresRunning}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 cursor-pointer"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Build Feature Sets A–E</span>
        </button>
      </div>
    );
  }

  const bestSet = [...activeData.manifest.feature_sets].sort(
    (a, b) => Math.max(b.cv_macro_f1_lr, b.cv_macro_f1_rf) - Math.max(a.cv_macro_f1_lr, a.cv_macro_f1_rf)
  )[0];

  const classNames = Object.keys(activeData.index_distributions[0]?.classes || {});

  return (
    <div className="space-y-6">
      {/* Header & Schedule Strip */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span>Day 4</span>
              <span aria-hidden="true">·</span>
              <span>Thu 19 Nov</span>
              <span aria-hidden="true">·</span>
              <span>Feature Engineering</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Vegetation Indices, Train-Only PCA, RF/MI Selection &amp; Sets A–E
            </h2>
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
                Primary (Zenodo)
              </button>
              <button
                type="button"
                onClick={() => onChangeSource('synthetic')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  source === 'synthetic' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                }`}
              >
                Synthetic (61 bands)
              </button>
            </div>

            <div className="flex items-center gap-2 text-xs bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5">
              <span className="text-slate-600">Top-K</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="font-mono bg-white border border-slate-200 rounded px-1.5 py-0.5"
              >
                <option value={3}>3</option>
                <option value={4}>4</option>
                <option value={5}>5</option>
                <option value={6}>6</option>
                <option value={8}>8</option>
              </select>
              <span className="text-slate-600">Norm</span>
              <select
                value={normalization}
                onChange={(e) => setNormalization(e.target.value as 'none' | 'snv' | 'msc')}
                className="font-mono bg-white border border-slate-200 rounded px-1.5 py-0.5"
              >
                <option value="snv">SNV</option>
                <option value="msc">MSC</option>
                <option value="none">None</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => onRunFeatures({ topK, normalization })}
              disabled={featuresRunning}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 disabled:opacity-60 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${featuresRunning ? 'animate-spin' : ''}`} />
              <span>{featuresRunning ? 'Building Sets A–E...' : 'Rebuild Feature Sets'}</span>
            </button>
          </div>
        </div>

        {/* 6-block Schedule Tracker */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-4 border-t border-slate-100">
          {DAY4_SCHEDULE.map((blk) => {
            const done = completedBlocks.includes(blk.id);
            return (
              <button
                key={blk.id}
                type="button"
                onClick={() => onToggleBlock(blk.id)}
                className={`text-left p-2.5 rounded-md border transition-colors cursor-pointer ${
                  done ? 'bg-slate-50 border-slate-200 text-slate-900' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>B0{blk.id} · {blk.time}</span>
                  <span className={done ? 'text-teal-800 font-semibold' : 'text-slate-400'}>
                    {done ? <Check className="w-3.5 h-3.5 inline" /> : '○'}
                  </span>
                </div>
                <div className="text-xs font-medium mt-1 truncate">{blk.title}</div>
              </button>
            );
          })}
        </div>

        {/* Leak-free guarantee strip */}
        <div className="bg-slate-50 border border-slate-200 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-700">
            <Lock className="w-3.5 h-3.5 text-teal-800 shrink-0" />
            <span>
              <strong>Zero-Leakage Guarantee:</strong> <code className="font-mono">SpectralFeatureSetPipeline</code> fits PCA &amp; RF/MI band selection strictly inside 5-fold <code className="font-mono">StratifiedGroupKFold(groups=plant_id)</code>; indices compute on uncentered SavGol reflectance.
            </span>
          </div>
          {bestSet && (
            <span className="font-mono tabular-nums text-teal-800 font-semibold whitespace-nowrap">
              Top Set: {bestSet.code} ({bestSet.n_features} dims · F1 {Math.max(bestSet.cv_macro_f1_lr, bestSet.cv_macro_f1_rf).toFixed(4)})
            </span>
          )}
        </div>

        {/* Sub-section segmented bar */}
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg w-fit">
          {[
            { id: 'sets', label: '1. Feature Sets A–E & Indices' },
            { id: 'pca_bands', label: '2. PCA & Band Selection' },
            { id: 'figures', label: '3. Saved Figures (2)' },
            { id: 'note', label: '4. Feature Engineering Note' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSubSection(tab.id as typeof subSection)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                subSection === tab.id ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* SECTION 1: FEATURE SETS A-E + VEGETATION INDICES */}
      {subSection === 'sets' && (
        <div className="space-y-6">
          {/* Feature Sets A to E Table */}
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Named Feature Sets A–E (Inside-Fold Leak-Free CV Comparison)
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Persisted to <code className="font-mono">data/processed/</code> for Day 5 baseline &amp; XGBoost comparison
                </p>
              </div>
              <span className="text-xs font-mono text-slate-500">
                5-Fold StratifiedGroupKFold (plant_id)
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-4 py-2.5 font-medium">Set</th>
                    <th className="px-4 py-2.5 font-medium">Contents</th>
                    <th className="px-4 py-2.5 font-medium text-right">Dims</th>
                    <th className="px-4 py-2.5 font-medium text-right">LR Macro-F1</th>
                    <th className="px-4 py-2.5 font-medium text-right">RF Macro-F1</th>
                    <th className="px-4 py-2.5 font-medium text-right">LR ROC-AUC</th>
                    <th className="px-4 py-2.5 font-medium">Saved Artifact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                  {activeData.manifest.feature_sets.map((fs) => {
                    const isBest = bestSet && fs.code === bestSet.code;
                    return (
                      <tr key={fs.key} className={isBest ? 'bg-teal-50/40' : 'hover:bg-slate-50/70'}>
                        <td className="px-4 py-2.5 font-semibold text-slate-900 whitespace-nowrap">
                          {fs.code} {isBest && <span className="text-teal-800 ml-1">★</span>}
                        </td>
                        <td className="px-4 py-2.5 font-sans text-slate-700">
                          <div>{fs.description}</div>
                          <div className="text-[11px] font-mono text-slate-400 mt-0.5 truncate max-w-md">
                            {fs.feature_names.slice(0, 6).join(', ')}
                            {fs.feature_names.length > 6 ? `, +${fs.feature_names.length - 6} more` : ''}
                          </div>
                        </td>
                        <td className="px-4 py-2.5 text-right text-slate-700">{fs.n_features}</td>
                        <td className="px-4 py-2.5 text-right font-semibold text-teal-800">
                          {fs.cv_macro_f1_lr.toFixed(4)}
                        </td>
                        <td className="px-4 py-2.5 text-right font-semibold text-slate-800">
                          {fs.cv_macro_f1_rf.toFixed(4)}
                        </td>
                        <td className="px-4 py-2.5 text-right text-slate-600">
                          {fs.cv_roc_auc_lr !== null ? fs.cv_roc_auc_lr.toFixed(4) : '—'}
                        </td>
                        <td className="px-4 py-2.5 text-[11px] text-slate-500">{fs.saved_path}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Nearest-Wavelength Lookup Table + MCARI Citation */}
            <div className="lg:col-span-6 bg-white border border-slate-200 rounded-lg p-5 space-y-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Block 1 &amp; 2 Nearest-Band Wavelength Mapping
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Aligned wavelengths: <code className="font-mono">{activeData.manifest.aligned_wavelengths_nm.join(', ')} nm</code>
                </p>
              </div>
              <div className="border border-slate-200 rounded-md overflow-hidden">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-3 py-2 font-medium">Index</th>
                      <th className="px-3 py-2 font-medium">Role</th>
                      <th className="px-3 py-2 font-medium text-right">Target</th>
                      <th className="px-3 py-2 font-medium text-right">Matched</th>
                      <th className="px-3 py-2 font-medium text-right">|Δλ|</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                    {activeData.manifest.band_matches.map((bm, i) => (
                      <tr key={`${bm.index_name}-${bm.role}-${i}`}>
                        <td className="px-3 py-2 font-semibold text-slate-900">{bm.index_name}</td>
                        <td className="px-3 py-2 text-slate-600">{bm.role}</td>
                        <td className="px-3 py-2 text-right text-slate-500">{bm.requested_nm} nm</td>
                        <td className="px-3 py-2 text-right text-teal-800 font-semibold">{bm.matched_nm} nm</td>
                        <td className="px-3 py-2 text-right text-slate-600">±{bm.delta_nm} nm</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded p-3 leading-relaxed">
                <strong>MCARI Citation:</strong> {activeData.mcari_citation}. Formula: <code className="font-mono text-slate-800">((R700 − R670) − 0.2*(R700 − R550)) * (R700 / R670)</code>.
              </div>
            </div>

            {/* Per-Class Index Sanity Distributions */}
            <div className="lg:col-span-6 bg-white border border-slate-200 rounded-lg p-5 space-y-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Block 6 Sanity Check: Index Distributions per Class (Train Split)
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Mean ± SD across training observations before Day 5 modeling
                </p>
              </div>
              <div className="border border-slate-200 rounded-md overflow-hidden">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-3 py-2 font-medium">Index</th>
                      {classNames.map((cn) => (
                        <th key={cn} className="px-3 py-2 font-medium text-right">{cn}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                    {activeData.index_distributions.map((row) => (
                      <tr key={row.index}>
                        <td className="px-3 py-2.5 font-semibold text-slate-900">{row.index}</td>
                        {classNames.map((cn) => {
                          const stat = row.classes[cn];
                          return (
                            <td key={cn} className="px-3 py-2.5 text-right text-slate-700">
                              {stat ? `${stat.mean.toFixed(3)} ± ${stat.std.toFixed(3)}` : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: PCA & BAND SELECTION */}
      {subSection === 'pca_bands' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <PcaScreeChart pca={activeData.pca} />
            <BandImportanceChart bandSelection={activeData.band_selection} />
          </div>

          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">
                Train-Only Band Ranking: Random Forest Importance &amp; Mutual Information
              </h3>
              <span className="text-xs font-mono text-teal-800">
                Set D Selected ({activeData.band_selection.top_k} bands)
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-4 py-2 font-medium">Wavelength</th>
                    <th className="px-4 py-2 font-medium text-right">RF Importance</th>
                    <th className="px-4 py-2 font-medium text-right">Mutual Info</th>
                    <th className="px-4 py-2 font-medium text-right">Consensus Score</th>
                    <th className="px-4 py-2 font-medium text-right">Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                  {activeData.band_selection.rankings
                    .filter((_, idx) => activeData.band_selection.rankings.length <= 20 || idx % 3 === 0 || _.selected)
                    .map((r) => (
                      <tr key={r.wavelength_nm} className={r.selected ? 'bg-amber-50/50' : ''}>
                        <td className="px-4 py-2 font-semibold text-slate-900">{r.wavelength_nm} nm</td>
                        <td className="px-4 py-2 text-right text-slate-700">{r.rf_importance.toFixed(5)}</td>
                        <td className="px-4 py-2 text-right text-slate-700">{r.mutual_info.toFixed(5)}</td>
                        <td className="px-4 py-2 text-right font-semibold text-slate-900">{r.consensus_score.toFixed(4)}</td>
                        <td className="px-4 py-2 text-right font-sans">
                          {r.selected ? (
                            <span className="text-teal-800 font-semibold">★ Selected (Set D/E)</span>
                          ) : (
                            <span className="text-slate-400">Omitted</span>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: SAVED FIGURES */}
      {subSection === 'figures' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {(featuresPayload?.figures || []).map((figRel) => {
            const filename = figRel.split('/').pop() || figRel;
            const title = filename.replace(/^\d+_/, '').replace('.png', '').replace(/_/g, ' ');
            return (
              <div
                key={figRel}
                className="bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col"
              >
                <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-mono text-slate-500">{figRel}</div>
                    <div className="text-sm font-semibold text-slate-900 capitalize mt-0.5">{title}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLightboxFigure(filename)}
                    className="text-xs font-medium text-teal-800 hover:underline cursor-pointer"
                  >
                    Expand
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setLightboxFigure(filename)}
                  className="p-3 bg-slate-50/60 hover:bg-slate-100/70 transition-colors cursor-zoom-in"
                >
                  <img
                    src={`/api/figures/${filename}?t=${topK}-${normalization}`}
                    alt={title}
                    className="w-full h-auto rounded border border-slate-200 bg-white"
                  />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* SECTION 4: FEATURE ENGINEERING NOTE */}
      {subSection === 'note' && (
        <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <div className="text-xs font-mono text-slate-500">docs/feature_engineering_note.md</div>
              <h3 className="text-base font-semibold text-slate-900 mt-0.5">
                Day 4 Feature Engineering Report &amp; MCARI Reference
              </h3>
            </div>
            <button
              type="button"
              onClick={() => onOpenDoc('feature_engineering_note')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Edit in Docs</span>
            </button>
          </div>
          <MarkdownViewer content={noteMarkdown} />
        </div>
      )}

      {/* Lightbox Modal */}
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
              src={`/api/figures/${lightboxFigure}?t=${topK}-${normalization}`}
              alt={lightboxFigure}
              className="w-full h-auto max-h-[80vh] object-contain mx-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
};
