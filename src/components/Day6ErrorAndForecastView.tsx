import React, { useState } from 'react';
import {
  ExternalLink,
  Lock,
  Play,
  RefreshCw,
  Sliders,
  TrendingUp,
  X,
} from 'lucide-react';
import {
  ForecastHorizonChart,
  MisclassifiedSpectraChart,
  ShapVsDay2Chart,
} from './Day5And6Charts';
import { MarkdownViewer } from './MarkdownViewer';
import type { Day6DatasetAnalysis, Day6ErrorAndForecastPayload } from '../types/day1';

interface Day6ErrorAndForecastViewProps {
  day6Payload: Day6ErrorAndForecastPayload | null;
  day6Loading: boolean;
  day6Running: boolean;
  source: 'primary' | 'synthetic';
  onChangeSource: (src: 'primary' | 'synthetic') => void;
  onRunDay6: (params: { window: number; horizon: number }) => void;
  noteMarkdown: string;
  onOpenDoc: (key: string) => void;
}

export const Day6ErrorAndForecastView: React.FC<Day6ErrorAndForecastViewProps> = ({
  day6Payload,
  day6Loading,
  day6Running,
  source,
  onChangeSource,
  onRunDay6,
  noteMarkdown,
  onOpenDoc,
}) => {
  const [subSection, setSubSection] = useState<
    'errors' | 'shap' | 'tuning_forecast' | 'exp_log' | 'figures_note'
  >('errors');
  const [windowSize, setWindowSize] = useState<number>(3);
  const [horizon, setHorizon] = useState<number>(1);
  const [logFilter, setLogFilter] = useState<'ALL' | 'Day 5' | 'Day 6'>('ALL');
  const [lightboxFigure, setLightboxFigure] = useState<string | null>(null);

  const activeData: Day6DatasetAnalysis | null = day6Payload
    ? source === 'synthetic'
      ? day6Payload.synthetic
      : day6Payload.primary
    : null;

  if (day6Loading && !activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-sm text-slate-500">
        Computing SHAP explanations, error diagnostics, grouped-CV grid search, and temporal sequences (<code className="font-mono">src/sequences.py</code>)...
      </div>
    );
  }

  if (!activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-8 flex flex-col items-center justify-center gap-4 text-center">
        <div className="text-sm font-medium text-slate-800">
          Day 6 error analysis, SHAP &amp; forecasting results have not been generated yet.
        </div>
        <button
          type="button"
          onClick={() => onRunDay6({ window: windowSize, horizon })}
          disabled={day6Running}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 cursor-pointer"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run Day 6 Analysis</span>
        </button>
      </div>
    );
  }

  const bb = activeData.best_baseline;
  const ea = activeData.error_analysis;
  const na = ea.noise_vs_ambiguity;
  const tu = activeData.tuning;
  const h1 = activeData.forecasting_prep.horizons[0];
  const filteredLog = (day6Payload?.experiment_log_rows || []).filter(
    (r) => logFilter === 'ALL' || r.day === logFilter
  );

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span>src/sequences.py &amp; SHAP</span>
              <span aria-hidden="true">·</span>
              <span>Error Analysis, Interpretability &amp; Multi-Step Forecasting</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Out-of-Fold Errors, SHAP Alignment, Grouped Tuning &amp; Temporal Sequences
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
              <span className="text-slate-600">Window W</span>
              <select
                value={windowSize}
                onChange={(e) => setWindowSize(Number(e.target.value))}
                className="font-mono bg-white border border-slate-200 rounded px-1.5 py-0.5"
              >
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
                <option value={5}>5</option>
              </select>
              <span className="text-slate-600">Horizon k</span>
              <select
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
                className="font-mono bg-white border border-slate-200 rounded px-1.5 py-0.5"
              >
                <option value={1}>+1</option>
                <option value={2}>+2</option>
                <option value={3}>+3</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => onRunDay6({ window: windowSize, horizon })}
              disabled={day6Running}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 disabled:opacity-60 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${day6Running ? 'animate-spin' : ''}`} />
              <span>{day6Running ? 'Updating Diagnostics...' : 'Rerun Diagnostics & Sequences'}</span>
            </button>
          </div>
        </div>

        {/* Leak-free Guarantee & Forecasting Feasibility Verdict Strip */}
        <div className="bg-slate-50 border border-slate-200 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-700">
            <Lock className="w-3.5 h-3.5 text-teal-800 shrink-0" />
            <span>
              <strong>Sequence Verdict:</strong> True multi-timepoint forecasting IS supported (
              <code className="font-mono">{h1?.n_sequences ?? 0}</code> windows across{' '}
              <code className="font-mono">{h1?.n_plants ?? 0}</code> plants; all plant windows kept strictly within one <code className="font-mono">GroupKFold</code>).
            </span>
          </div>
          <span className="font-mono tabular-nums text-teal-800 font-semibold whitespace-nowrap">
            Tuned {tu.model_name}: F1 {tu.tuned.macro_f1_mean.toFixed(4)} ({tu.tuned.delta_macro_f1 >= 0 ? `+${tu.tuned.delta_macro_f1.toFixed(4)}` : tu.tuned.delta_macro_f1.toFixed(4)})
          </span>
        </div>

        {/* Sub-section segmented bar */}
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg w-fit">
          {[
            { id: 'errors', label: '1. Error Analysis' },
            { id: 'shap', label: '2. SHAP & Wavelengths' },
            { id: 'tuning_forecast', label: '3. Tuning & Forecasting' },
            { id: 'exp_log', label: `4. Experiment Log (${day6Payload?.experiment_log_rows.length || 0})` },
            { id: 'figures_note', label: '5. Figures (3) & Report' },
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

      {/* SECTION 1: ERROR ANALYSIS */}
      {subSection === 'errors' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs text-slate-500">Out-of-Fold Error Rate</div>
              <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 mt-1">
                {bb.overall_error_rate_pct.toFixed(2)}%
              </div>
              <div className="text-xs font-mono text-slate-500 mt-1">
                {bb.total_errors} errors / {bb.total_samples} scans ({bb.model_name} Set {bb.feature_set_code})
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs text-slate-500">Noise vs. Boundary Ambiguity</div>
              <div className="text-xl font-bold font-mono tabular-nums text-teal-800 mt-1">
                Z={na.error_median_robust_z.toFixed(2)} vs {na.correct_median_robust_z.toFixed(2)}
              </div>
              <div className="text-xs text-slate-600 mt-1">
                Only <strong className="font-mono">{na.error_noisy_pct_z_gt_3}%</strong> errors &gt;3Z · Margin <strong className="font-mono">{na.error_median_centroid_margin.toFixed(2)}</strong> vs <strong className="font-mono">{na.correct_median_centroid_margin.toFixed(2)}</strong>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs text-slate-500">Temporal Early vs. Late Errors</div>
              <div className="text-xl font-bold font-mono tabular-nums text-slate-900 mt-1">
                {ea.early_half_error_pct}% → {ea.late_half_error_pct}%
              </div>
              <div className="text-xs text-slate-600 mt-1">
                First half vs. second half of chronological dates
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs text-slate-500">Top Confused Pair</div>
              <div className="text-sm font-bold text-slate-900 mt-1 leading-snug">
                {ea.confused_pairs[0]
                  ? `${ea.confused_pairs[0].true_class.replace(/\s*\(.*?\)/g, '')} → ${ea.confused_pairs[0].predicted_class.replace(/\s*\(.*?\)/g, '')}`
                  : 'None'}
              </div>
              <div className="text-xs font-mono text-slate-500 mt-1">
                {ea.confused_pairs[0]
                  ? `${ea.confused_pairs[0].count} scans (${ea.confused_pairs[0].percent_of_errors}% of all errors)`
                  : '0 misclassifications'}
              </div>
            </div>
          </div>

          <MisclassifiedSpectraChart errorAnalysis={ea} />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-5 bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200">
                <h3 className="text-sm font-semibold text-slate-900">
                  Confused Pairs &amp; Genotype/Field Error Breakdown
                </h3>
              </div>
              <div className="p-4 space-y-4">
                <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-2.5 py-1.5 font-sans font-medium">True → Predicted</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">Count</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {ea.confused_pairs.slice(0, 6).map((cp, idx) => (
                      <tr key={idx}>
                        <td className="px-2.5 py-1.5 font-sans text-slate-800">
                          {cp.true_class} → {cp.predicted_class}
                        </td>
                        <td className="px-2.5 py-1.5 text-right font-semibold">{cp.count}</td>
                        <td className="px-2.5 py-1.5 text-right text-slate-500">{cp.percent_of_errors}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <table className="w-full text-left border-collapse text-xs font-mono tabular-nums border-t border-slate-200">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-2.5 py-1.5 font-sans font-medium">Genotype / Field Block</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">Errors / Scans</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">Error %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {ea.by_genotype_or_field.map((gf) => (
                      <tr key={gf.field_id}>
                        <td className="px-2.5 py-1.5 font-sans font-medium text-slate-800">{gf.field_id}</td>
                        <td className="px-2.5 py-1.5 text-right text-slate-600">{gf.errors} / {gf.scans}</td>
                        <td className="px-2.5 py-1.5 text-right font-semibold text-rose-700">{gf.error_rate_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="lg:col-span-7 bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">
                  Highest-Error Individual Plants (<code className="font-mono">plant_id</code> Concentration)
                </h3>
                <span className="text-xs font-mono text-slate-500">Top 8 plants</span>
              </div>
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-4 py-2 font-medium">Plant ID</th>
                    <th className="px-4 py-2 font-sans font-medium">True Class</th>
                    <th className="px-4 py-2 font-medium text-right">Errors</th>
                    <th className="px-4 py-2 font-medium text-right">Total Scans</th>
                    <th className="px-4 py-2 font-medium text-right">Error Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ea.top_error_plants.map((p) => (
                    <tr key={p.plant_id}>
                      <td className="px-4 py-2 font-semibold text-slate-900">{p.plant_id}</td>
                      <td className="px-4 py-2 font-sans text-slate-700">{p.true_label}</td>
                      <td className="px-4 py-2 text-right font-semibold text-rose-700">{p.errors}</td>
                      <td className="px-4 py-2 text-right text-slate-600">{p.scans}</td>
                      <td className="px-4 py-2 text-right font-semibold text-slate-900">{p.error_rate_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: SHAP & WAVELENGTHS */}
      {subSection === 'shap' && (
        <div className="space-y-6">
          <ShapVsDay2Chart
            interpretability={activeData.interpretability}
            modelLabel={`${bb.model_name} · Set ${bb.feature_set_code}`}
          />

          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Validation SHAP &amp; Permutation Importance Table
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Computed strictly on held-out fold validation data ({activeData.interpretability.best_set_shap.method})
                </p>
              </div>
              <span className="text-xs font-mono text-teal-800">
                Wavelength ρ vs Day 2 Fisher J: {activeData.interpretability.spearman_shap_vs_fisher.toFixed(3)}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-4 py-2.5 font-medium">Rank</th>
                    <th className="px-4 py-2.5 font-sans font-medium">Feature</th>
                    <th className="px-4 py-2.5 font-medium text-right">Mean |SHAP|</th>
                    <th className="px-4 py-2.5 font-medium text-right">Permutation Imp. (F1)</th>
                    <th className="px-4 py-2.5 font-medium text-right">SHAP Direction Corr</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {activeData.interpretability.best_set_shap.features.map((f, idx) => (
                    <tr key={f.feature}>
                      <td className="px-4 py-2 text-slate-500">#{idx + 1}</td>
                      <td className="px-4 py-2 font-semibold text-slate-900">{f.feature}</td>
                      <td className="px-4 py-2 text-right font-semibold text-teal-800">{f.mean_abs_shap.toFixed(5)}</td>
                      <td className="px-4 py-2 text-right text-slate-700">{f.permutation_importance.toFixed(5)}</td>
                      <td
                        className={`px-4 py-2 text-right font-semibold ${
                          f.direction_corr >= 0 ? 'text-teal-800' : 'text-amber-700'
                        }`}
                      >
                        {f.direction_corr >= 0 ? `+${f.direction_corr.toFixed(3)}` : f.direction_corr.toFixed(3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: TUNING & FORECASTING */}
      {subSection === 'tuning_forecast' && (
        <div className="space-y-6">
          {/* Block 4: Light Hyperparameter Tuning */}
          <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-teal-800" />
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Hyperparameter Tuning Inside StratifiedGroupKFold ({tu.model_name} · Set {tu.feature_set_code})
                  </h3>
                  <p className="text-xs text-slate-500">
                    Winning params: <code className="font-mono text-slate-700">{JSON.stringify(tu.tuned.params)}</code>
                  </p>
                </div>
              </div>
              <span className="font-mono tabular-nums text-xs font-semibold text-teal-800">
                Δ Macro-F1: {tu.tuned.delta_macro_f1 >= 0 ? `+${tu.tuned.delta_macro_f1.toFixed(4)}` : tu.tuned.delta_macro_f1.toFixed(4)}
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums border border-slate-200 rounded">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-3 py-2 font-sans font-medium">Variant</th>
                    <th className="px-3 py-2 font-medium text-right">Balanced Acc</th>
                    <th className="px-3 py-2 font-medium text-right">Macro-F1</th>
                    <th className="px-3 py-2 font-medium text-right">ROC-AUC</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="px-3 py-2.5 font-sans font-medium text-slate-700">Day 5 Untuned</td>
                    <td className="px-3 py-2.5 text-right">{tu.untuned.balanced_acc_mean.toFixed(4)} ± {tu.untuned.balanced_acc_std.toFixed(4)}</td>
                    <td className="px-3 py-2.5 text-right">{tu.untuned.macro_f1_mean.toFixed(4)} ± {tu.untuned.macro_f1_std.toFixed(4)}</td>
                    <td className="px-3 py-2.5 text-right">{tu.untuned.roc_auc_mean.toFixed(4)}</td>
                  </tr>
                  <tr className="bg-teal-50/40">
                    <td className="px-3 py-2.5 font-sans font-semibold text-teal-900">Day 6 Grid-Tuned ★</td>
                    <td className="px-3 py-2.5 text-right font-semibold">{tu.tuned.balanced_acc_mean.toFixed(4)} ± {tu.tuned.balanced_acc_std.toFixed(4)}</td>
                    <td className="px-3 py-2.5 text-right font-bold text-teal-800">{tu.tuned.macro_f1_mean.toFixed(4)} ± {tu.tuned.macro_f1_std.toFixed(4)}</td>
                    <td className="px-3 py-2.5 text-right font-semibold">{tu.tuned.roc_auc_mean.toFixed(4)}</td>
                  </tr>
                </tbody>
              </table>

              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums border border-slate-200 rounded">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-3 py-2 font-sans font-medium">Grid Candidate Params</th>
                    <th className="px-3 py-2 font-medium text-right">Bal. Acc</th>
                    <th className="px-3 py-2 font-medium text-right">Macro-F1</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tu.grid_trials.map((gt, idx) => (
                    <tr key={idx}>
                      <td className="px-3 py-1.5 text-[11px] text-slate-600 truncate max-w-[260px]">
                        {JSON.stringify(gt.params)}
                      </td>
                      <td className="px-3 py-1.5 text-right">{gt.balanced_acc_mean.toFixed(4)}</td>
                      <td className="px-3 py-1.5 text-right font-semibold text-slate-800">{gt.macro_f1_mean.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Block 5: Forecasting Prep */}
          <ForecastHorizonChart horizons={activeData.forecasting_prep.horizons} />

          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-teal-800" />
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Temporal Sequence Forecasting Baselines (<code className="font-mono">src/sequences.py</code>)
                  </h3>
                  <p className="text-xs text-slate-500">
                    Predicting future canopy <code className="font-mono">NDVI_{'{t+k}'}</code> from W={activeData.forecasting_prep.window_size} prior spectral scans inside <code className="font-mono">GroupKFold(plant_id)</code>
                  </p>
                </div>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-4 py-2.5 font-medium">Horizon (Windows)</th>
                    <th className="px-4 py-2.5 font-sans font-medium">Forecaster</th>
                    <th className="px-4 py-2.5 font-medium text-right">CV MAE (± SD)</th>
                    <th className="px-4 py-2.5 font-medium text-right">CV RMSE (± SD)</th>
                    <th className="px-4 py-2.5 font-medium text-right">CV R²</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {activeData.forecasting_prep.horizons
                    .filter((hr) => hr.feasible)
                    .flatMap((hr) =>
                      hr.models.map((m) => (
                        <tr key={`${hr.horizon}-${m.key}`} className={m.key === 'lag_rf' ? 'bg-teal-50/30' : ''}>
                          <td className="px-4 py-2 text-slate-800 font-semibold">
                            k = +{hr.horizon} ({hr.n_sequences} seqs)
                          </td>
                          <td className="px-4 py-2 font-sans text-slate-800">{m.name}</td>
                          <td className="px-4 py-2 text-right font-semibold text-teal-800">
                            {m.mae_mean.toFixed(5)} ± {m.mae_std.toFixed(5)}
                          </td>
                          <td className="px-4 py-2 text-right text-slate-600">
                            {m.rmse_mean.toFixed(5)} ± {m.rmse_std.toFixed(5)}
                          </td>
                          <td className="px-4 py-2 text-right text-slate-800">{m.r2_mean.toFixed(4)}</td>
                        </tr>
                      ))
                    )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 4: EXPERIMENT LOG */}
      {subSection === 'exp_log' && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Reproducible Experiment Log (<code className="font-mono">reports/experiment_log.csv</code>)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every classification &amp; forecasting run logged with data version, preprocessing, features, parameters, and CV metrics
              </p>
            </div>
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
              {(['ALL', 'Day 5', 'Day 6'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setLogFilter(f)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md cursor-pointer ${
                    logFilter === f ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="px-3 py-2 font-medium">Run ID</th>
                  <th className="px-3 py-2 font-medium">Day</th>
                  <th className="px-3 py-2 font-medium">Data</th>
                  <th className="px-3 py-2 font-sans font-medium">Model</th>
                  <th className="px-3 py-2 font-medium">Features</th>
                  <th className="px-3 py-2 font-medium">CV Scheme</th>
                  <th className="px-3 py-2 font-medium text-right">Primary Metric 1</th>
                  <th className="px-3 py-2 font-medium text-right">Primary Metric 2</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredLog.map((r) => (
                  <tr key={r.run_id} className={r.cv_scheme.includes('LEAKY') ? 'bg-rose-50/50' : ''}>
                    <td className="px-3 py-2 font-semibold text-slate-800">{r.run_id}</td>
                    <td className="px-3 py-2 text-slate-600">{r.day}</td>
                    <td className="px-3 py-2 text-slate-600">{r.data_version}</td>
                    <td className="px-3 py-2 font-sans font-medium text-slate-900">{r.model}</td>
                    <td className="px-3 py-2 text-slate-600">{r.features}</td>
                    <td className="px-3 py-2 text-[11px] text-slate-500">{r.cv_scheme}</td>
                    <td className="px-3 py-2 text-right font-semibold text-teal-800">{r.macro_f1}</td>
                    <td className="px-3 py-2 text-right text-slate-600">{r.balanced_acc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SECTION 5: FIGURES & REPORT */}
      {subSection === 'figures_note' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {(day6Payload?.figures || []).map((figRel) => {
              const filename = figRel.split('/').pop() || figRel;
              const title = filename.replace(/^\d+_/, '').replace('.png', '').replace(/_/g, ' ');
              return (
                <div key={figRel} className="bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                    <div className="min-w-0 pr-2">
                      <div className="text-[11px] font-mono text-slate-500 truncate">{figRel}</div>
                      <div className="text-xs font-semibold text-slate-900 capitalize mt-0.5 truncate">{title}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setLightboxFigure(filename)}
                      className="text-xs font-medium text-teal-800 hover:underline shrink-0 cursor-pointer"
                    >
                      Expand
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLightboxFigure(filename)}
                    className="p-2.5 bg-slate-50/60 hover:bg-slate-100/70 transition-colors cursor-zoom-in"
                  >
                    <img
                      src={`/api/figures/${filename}?w=${windowSize}&k=${horizon}`}
                      alt={title}
                      className="w-full h-auto rounded border border-slate-200 bg-white"
                    />
                  </button>
                </div>
              );
            })}
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <div className="text-xs font-mono text-slate-500">docs/error_interpretability_note.md</div>
                <h3 className="text-base font-semibold text-slate-900 mt-0.5">
                  Day 6 Error Analysis, Interpretability &amp; Forecasting Readiness Report
                </h3>
              </div>
              <button
                type="button"
                onClick={() => onOpenDoc('error_interpretability_note')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Edit in Docs</span>
              </button>
            </div>
            <MarkdownViewer content={noteMarkdown} />
          </div>
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
              src={`/api/figures/${lightboxFigure}?w=${windowSize}&k=${horizon}`}
              alt={lightboxFigure}
              className="w-full h-auto max-h-[80vh] object-contain mx-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
};
