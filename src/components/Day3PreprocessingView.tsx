import React, { useState } from 'react';
import { Check, ExternalLink, Play, RefreshCw, SlidersHorizontal, X } from 'lucide-react';
import { PreprocessingAblationChart } from './Day3And4Charts';
import { MarkdownViewer } from './MarkdownViewer';
import { SpectralReflectanceChart } from './SpectralCharts';
import type {
  Day3DatasetPreprocessing,
  Day3PreprocessingPayload,
  PreprocessingConfigDto,
  SpectralCurve,
} from '../types/day1';

interface Day3PreprocessingViewProps {
  prepPayload: Day3PreprocessingPayload | null;
  prepLoading: boolean;
  prepRunning: boolean;
  source: 'primary' | 'synthetic';
  onChangeSource: (src: 'primary' | 'synthetic') => void;
  onRunPreprocessing: (config?: Partial<PreprocessingConfigDto>) => void;
  completedBlocks: number[];
  onToggleBlock: (blockId: number) => void;
  noteMarkdown: string;
  onOpenDoc: (key: string) => void;
}

const DAY3_SCHEDULE = [
  { id: 1, title: 'Drop Bad Edges & Water Bands', time: '45 min' },
  { id: 2, title: 'Clip & Sanitize Reflectance', time: '45 min' },
  { id: 3, title: 'Savitzky-Golay Smoothing', time: '1 h' },
  { id: 4, title: 'SNV & Train-Fit MSC', time: '1 h' },
  { id: 5, title: 'First-Derivative Spectra', time: '45 min' },
  { id: 6, title: 'Raw vs. Processed Plots', time: '1 h' },
  { id: 7, title: 'src/preprocessing.py Pipeline', time: '75 min' },
];

export const Day3PreprocessingView: React.FC<Day3PreprocessingViewProps> = ({
  prepPayload,
  prepLoading,
  prepRunning,
  source,
  onChangeSource,
  onRunPreprocessing,
  completedBlocks,
  onToggleBlock,
  noteMarkdown,
  onOpenDoc,
}) => {
  const [subSection, setSubSection] = useState<'ablation' | 'spectra' | 'figures' | 'note'>('ablation');
  const [lightboxFigure, setLightboxFigure] = useState<string | null>(null);

  const [dropUv365, setDropUv365] = useState<boolean>(true);
  const [dropNir970, setDropNir970] = useState<boolean>(false);
  const [useSavgol, setUseSavgol] = useState<boolean>(true);
  const [savgolWindow, setSavgolWindow] = useState<number>(3);
  const [normalization, setNormalization] = useState<'none' | 'snv' | 'msc'>('snv');
  const [useDerivative, setUseDerivative] = useState<boolean>(false);

  const activeData: Day3DatasetPreprocessing | null = prepPayload
    ? source === 'synthetic'
      ? prepPayload.synthetic
      : prepPayload.primary
    : null;

  const handleApplyCustom = () => {
    const dropList: number[] = [];
    if (dropUv365) dropList.push(365.0);
    if (dropNir970) dropList.push(970.0);
    onRunPreprocessing({
      drop_bad_bands: dropList.length > 0,
      drop_wavelengths: dropList,
      drop_water_bands: true,
      use_savgol: useSavgol,
      savgol_window: savgolWindow,
      savgol_polyorder: savgolWindow >= 5 ? 2 : 1,
      normalization,
      use_first_derivative: useDerivative,
    });
  };

  if (prepLoading && !activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-sm text-slate-500">
        Executing Python preprocessing pipeline (<code className="font-mono">src/preprocessing.py</code>)...
      </div>
    );
  }

  if (!activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-8 flex flex-col items-center justify-center gap-4 text-center">
        <div className="text-sm font-medium text-slate-800">
          Day 3 preprocessing metrics have not been generated yet.
        </div>
        <button
          type="button"
          onClick={() => onRunPreprocessing()}
          disabled={prepRunning}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 cursor-pointer"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run Day 3 Preprocessing Pipeline</span>
        </button>
      </div>
    );
  }

  const rawStep = activeData.ablation[0];
  const rawCurves: SpectralCurve[] = (rawStep?.class_curves || []).map((c) => ({
    label: c.label,
    samples: c.n_samples,
    plants: 0,
    points: (c.points.length > 20 ? c.points.filter((_, i) => i % 2 === 0) : c.points).map((p) => ({
      wavelengthNm: p.wavelength_nm,
      mean: p.mean,
      std: p.std,
    })),
  }));

  const activeCurves: SpectralCurve[] = (activeData.active_metrics?.class_curves || []).map((c) => ({
    label: c.label,
    samples: c.n_samples,
    plants: 0,
    points: (c.points.length > 20 ? c.points.filter((_, i) => i % 2 === 0) : c.points).map((p) => ({
      wavelengthNm: p.wavelength_nm,
      mean: p.mean,
      std: p.std,
    })),
  }));

  return (
    <div className="space-y-6">
      {/* Header & Schedule Strip */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span>Day 3</span>
              <span aria-hidden="true">·</span>
              <span>Wed 18 Nov</span>
              <span aria-hidden="true">·</span>
              <span>Preprocessing &amp; Spectral Transforms</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Leak-Free Spectral Cleaning, Savitzky-Golay, SNV/MSC &amp; Derivatives
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

            <button
              type="button"
              onClick={handleApplyCustom}
              disabled={prepRunning}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 disabled:opacity-60 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${prepRunning ? 'animate-spin' : ''}`} />
              <span>{prepRunning ? 'Running Pipeline...' : 'Apply & Rerun Pipeline'}</span>
            </button>
          </div>
        </div>

        {/* 7-block Schedule Tracker */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 pt-4 border-t border-slate-100">
          {DAY3_SCHEDULE.map((blk) => {
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

        {/* Interactive Switchable Config Controls */}
        <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 font-semibold text-slate-800">
              <SlidersHorizontal className="w-3.5 h-3.5 text-teal-800" />
              <span>Switchable Pipeline Flags (<code className="font-mono">PreprocessingConfig</code>)</span>
            </div>
            <div className="font-mono tabular-nums text-slate-600">
              Train/Test: {activeData.manifest.train_rows}/{activeData.manifest.test_rows} rows ({activeData.manifest.train_plants}/{activeData.manifest.test_plants} plants) · Output: <span className="text-teal-800">{activeData.manifest.output_npz}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
            <label className="flex items-center gap-2 bg-white border border-slate-200 rounded px-3 py-2 cursor-pointer">
              <input
                type="checkbox"
                checked={dropUv365}
                onChange={(e) => setDropUv365(e.target.checked)}
                className="accent-teal-700"
              />
              <span>Drop 365 nm UV Edge</span>
            </label>

            <label className="flex items-center gap-2 bg-white border border-slate-200 rounded px-3 py-2 cursor-pointer">
              <input
                type="checkbox"
                checked={dropNir970}
                onChange={(e) => setDropNir970(e.target.checked)}
                className="accent-teal-700"
              />
              <span>Drop 970 nm NIR Edge</span>
            </label>

            <div className="flex items-center justify-between gap-2 bg-white border border-slate-200 rounded px-3 py-1.5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useSavgol}
                  onChange={(e) => setUseSavgol(e.target.checked)}
                  className="accent-teal-700"
                />
                <span>SavGol Win</span>
              </label>
              <select
                value={savgolWindow}
                disabled={!useSavgol}
                onChange={(e) => setSavgolWindow(Number(e.target.value))}
                className="font-mono text-xs border border-slate-200 rounded px-1.5 py-0.5 bg-white disabled:opacity-50"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={7}>7</option>
              </select>
            </div>

            <div className="flex items-center justify-between gap-2 bg-white border border-slate-200 rounded px-3 py-1.5">
              <span className="text-slate-600">Scatter Norm</span>
              <select
                value={normalization}
                onChange={(e) => setNormalization(e.target.value as 'none' | 'snv' | 'msc')}
                className="font-mono text-xs border border-slate-200 rounded px-1.5 py-0.5 bg-white"
              >
                <option value="snv">SNV</option>
                <option value="msc">MSC (Train)</option>
                <option value="none">None</option>
              </select>
            </div>

            <label className="flex items-center gap-2 bg-white border border-slate-200 rounded px-3 py-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useDerivative}
                onChange={(e) => setUseDerivative(e.target.checked)}
                className="accent-teal-700"
              />
              <span>1st Derivative (dR/dλ)</span>
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-600">
            <span className="font-sans font-medium text-slate-700">Aligned Wavelengths Carried to Day 4 ({activeData.manifest.wavelengths_out_nm.length}):</span>
            <span>{activeData.manifest.wavelengths_out_nm.join(' · ')} nm</span>
            {activeData.manifest.dropped_wavelengths_nm.length > 0 && (
              <span className="text-rose-700">
                (Dropped: {activeData.manifest.dropped_wavelengths_nm.join(', ')} nm)
              </span>
            )}
          </div>
        </div>

        {/* Sub-section segmented bar */}
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg w-fit">
          {[
            { id: 'ablation', label: '1. Step Ablation & Fisher' },
            { id: 'spectra', label: '2. Raw vs. Processed Spectra' },
            { id: 'figures', label: '3. Saved Figures (2)' },
            { id: 'note', label: '4. Preprocessing Note' },
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

      {/* SECTION 1: ABLATION & STEP COMPARISON */}
      {subSection === 'ablation' && (
        <div className="space-y-6">
          <PreprocessingAblationChart steps={activeData.ablation} />

          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-slate-900">
                Step-by-Step Class Separation &amp; Leak-Free Holdout Benchmark
              </h3>
              <span className="text-xs font-mono text-teal-800">
                Active Config F1: {activeData.active_metrics.holdout_macro_f1.toFixed(4)} · Mean J: {activeData.active_metrics.mean_fisher_ratio.toFixed(5)}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-4 py-2.5 font-medium">Pipeline Stage</th>
                    <th className="px-4 py-2.5 font-medium text-right">Aligned Bands</th>
                    <th className="px-4 py-2.5 font-medium text-right">Mean Fisher J</th>
                    <th className="px-4 py-2.5 font-medium text-right">Peak Fisher J</th>
                    <th className="px-4 py-2.5 font-medium text-right">Holdout Macro-F1</th>
                    <th className="px-4 py-2.5 font-medium">Preprocessing Flags</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                  {activeData.ablation.map((step) => (
                    <tr key={step.key} className="hover:bg-slate-50/70">
                      <td className="px-4 py-2.5 font-sans font-medium text-slate-900">{step.label}</td>
                      <td className="px-4 py-2.5 text-right text-slate-700">{step.n_bands}</td>
                      <td className="px-4 py-2.5 text-right text-slate-700">{step.mean_fisher_ratio.toFixed(5)}</td>
                      <td className="px-4 py-2.5 text-right text-slate-700">{step.max_fisher_ratio.toFixed(5)}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-teal-800">{step.holdout_macro_f1.toFixed(4)}</td>
                      <td className="px-4 py-2.5 font-sans text-slate-600">
                        {step.config.drop_bad_bands ? 'DropBad ' : ''}
                        {step.config.use_savgol ? `SavGol(${step.config.savgol_window},${step.config.savgol_polyorder}) ` : ''}
                        {step.config.normalization !== 'none' ? step.config.normalization.toUpperCase() + ' ' : ''}
                        {step.config.use_first_derivative ? '1stDeriv' : ''}
                        {!step.config.drop_bad_bands && !step.config.use_savgol && step.config.normalization === 'none' && !step.config.use_first_derivative ? 'Clip only' : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: RAW VS PROCESSED SPECTRA + SAVGOL SWEEP */}
      {subSection === 'spectra' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="space-y-2">
              <div className="text-xs font-mono text-slate-500">
                Before Preprocessing · Raw {rawStep?.n_bands} bands
              </div>
              <SpectralReflectanceChart curves={rawCurves} />
            </div>
            <div className="space-y-2">
              <div className="text-xs font-mono text-teal-800 font-medium">
                After Active Pipeline · {activeData.active_metrics.n_bands} aligned bands ({normalization.toUpperCase()} {useDerivative ? '+ dR/dλ' : ''})
              </div>
              <SpectralReflectanceChart curves={activeCurves} />
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">
              Block 3 Savitzky-Golay Smoothing Window &amp; Polynomial Sweep
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {activeData.savgol_comparison.map((sg) => (
                <div key={sg.name} className="border border-slate-200 rounded-md p-3.5 space-y-1.5">
                  <div className="text-xs font-mono font-semibold text-slate-900">{sg.name}</div>
                  <div className="text-xs text-slate-500">
                    Requested win={sg.requested_window} → Clamped win={sg.effective_window}
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono tabular-nums pt-1 border-t border-slate-100">
                    <span className="text-slate-600">Fisher J: {sg.mean_fisher_ratio.toFixed(5)}</span>
                    <span className="text-teal-800 font-semibold">F1: {sg.holdout_macro_f1.toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: SAVED FIGURES */}
      {subSection === 'figures' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {(prepPayload?.figures || []).map((figRel) => {
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
                    src={`/api/figures/${filename}?t=${activeData.active_metrics.holdout_macro_f1}`}
                    alt={title}
                    className="w-full h-auto rounded border border-slate-200 bg-white"
                  />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* SECTION 4: PREPROCESSING NOTE */}
      {subSection === 'note' && (
        <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <div className="text-xs font-mono text-slate-500">docs/preprocessing_note.md</div>
              <h3 className="text-base font-semibold text-slate-900 mt-0.5">
                Day 3 Preprocessing Findings &amp; Step Justifications
              </h3>
            </div>
            <button
              type="button"
              onClick={() => onOpenDoc('preprocessing_note')}
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
              src={`/api/figures/${lightboxFigure}?t=${activeData.active_metrics.holdout_macro_f1}`}
              alt={lightboxFigure}
              className="w-full h-auto max-h-[80vh] object-contain mx-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
};
