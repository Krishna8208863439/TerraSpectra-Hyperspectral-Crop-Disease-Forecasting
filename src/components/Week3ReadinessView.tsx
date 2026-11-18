import React from 'react';
import { Cpu, GitCompare, Layers, Lock, RefreshCw } from 'lucide-react';
import type { Day5BaselinesPayload, Week3ReadinessPayload } from '../types/day1';

interface Week3ReadinessViewProps {
  readiness: Week3ReadinessPayload | null;
  readinessLoading: boolean;
  baselinesPayload: Day5BaselinesPayload | null;
  source: 'primary' | 'synthetic';
  onChangeSource: (src: 'primary' | 'synthetic') => void;
  onRefresh: () => void;
}

export const Week3ReadinessView: React.FC<Week3ReadinessViewProps> = ({
  readiness,
  readinessLoading,
  baselinesPayload,
  source,
  onChangeSource,
  onRefresh,
}) => {
  if (readinessLoading && !readiness) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-sm text-slate-500">
        Running neural MLP benchmark &amp; Week 3 sequence contract (<code className="font-mono">src/week3_models.py</code>)...
      </div>
    );
  }

  const neuralRows = readiness?.benchmarks?.[source]?.neural_mlp_results || [];
  const activeBaseline = baselinesPayload ? baselinesPayload[source] : null;
  const bestClassical = activeBaseline?.overall_best;

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span>src/week3_models.py</span>
              <span aria-hidden="true">·</span>
              <span>Neural Comparator &amp; Week 3 Architecture Contracts</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Neural Spectral Comparator (MLP) &amp; Week 3 1D-CNN / GRU Specifications
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
              onClick={onRefresh}
              disabled={readinessLoading}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 disabled:opacity-60 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${readinessLoading ? 'animate-spin' : ''}`} />
              <span>{readinessLoading ? 'Evaluating MLP...' : 'Re-run Neural Benchmark'}</span>
            </button>
          </div>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-700">
            <Lock className="w-3.5 h-3.5 text-teal-800 shrink-0" />
            <span>
              <strong>Equal-Split Contract:</strong> Neural models train and evaluate strictly on the exact same frozen 5-fold <code className="font-mono">StratifiedGroupKFold(groups=plant_id)</code> splits as Random Forest, XGBoost, SVM, and PLS-DA.
            </span>
          </div>
          {bestClassical && (
            <span className="font-mono tabular-nums text-teal-800 font-semibold whitespace-nowrap">
              Classical Target to Beat: {bestClassical.model_name} (Set {bestClassical.feature_set_code}) · F1 {bestClassical.macro_f1_mean.toFixed(4)}
            </span>
          )}
        </div>
      </div>

      {/* Neural MLP vs Classical Benchmark Table */}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-teal-800" />
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Neural MLP (2-Layer 64→32) vs. Classical Grouped-CV Baselines
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Empirical test of feed-forward neural generalization before convolutional 1D-CNN band modeling
              </p>
            </div>
          </div>
          <span className="text-xs font-mono text-slate-500">
            5-Fold StratifiedGroupKFold ({source})
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                <th className="px-4 py-2.5 font-medium">Model Architecture</th>
                <th className="px-4 py-2.5 font-medium">Feature Set</th>
                <th className="px-4 py-2.5 font-medium text-right">Bal. Acc (± SD)</th>
                <th className="px-4 py-2.5 font-medium text-right">Macro-F1 (± SD)</th>
                <th className="px-4 py-2.5 font-medium text-right">ROC-AUC</th>
                <th className="px-4 py-2.5 font-medium text-right">Δ vs. Best Classical</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
              {bestClassical && (
                <tr className="bg-teal-50/40">
                  <td className="px-4 py-2.5 font-sans font-semibold text-teal-900">
                    {bestClassical.model_name} (Reference Winner)
                  </td>
                  <td className="px-4 py-2.5 text-slate-700">Set {bestClassical.feature_set_code}</td>
                  <td className="px-4 py-2.5 text-right font-semibold text-slate-900">
                    {bestClassical.balanced_acc_mean.toFixed(4)} ± {bestClassical.balanced_acc_std.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-bold text-teal-800">
                    {bestClassical.macro_f1_mean.toFixed(4)} ± {bestClassical.macro_f1_std.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-700">
                    {bestClassical.roc_auc_mean.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-semibold text-teal-800">0.0000</td>
                </tr>
              )}
              {neuralRows.map((row, idx) => {
                const delta = bestClassical ? row.macro_f1_mean - bestClassical.macro_f1_mean : 0;
                return (
                  <tr key={`${row.feature_set}-${idx}`} className="hover:bg-slate-50/70">
                    <td className="px-4 py-2.5 font-sans font-medium text-slate-900">{row.model_name}</td>
                    <td className="px-4 py-2.5 text-slate-700">{row.feature_set}</td>
                    <td className="px-4 py-2.5 text-right text-slate-700">
                      {row.balanced_acc_mean.toFixed(4)} ± {row.balanced_acc_std.toFixed(4)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-semibold text-slate-900">
                      {row.macro_f1_mean.toFixed(4)} ± {row.macro_f1_std.toFixed(4)}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-700">
                      {row.roc_auc_mean.toFixed(4)}
                    </td>
                    <td
                      className={`px-4 py-2.5 text-right font-semibold ${
                        delta >= 0 ? 'text-teal-800' : 'text-amber-700'
                      }`}
                    >
                      {delta >= 0 ? `+${delta.toFixed(4)}` : delta.toFixed(4)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Week 3 Architecture Specifications */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-teal-800" />
          <h3 className="text-sm font-semibold text-slate-900">
            Week 3 Deep Spectral &amp; Sequence Model Specifications
          </h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {(readiness?.architectures || []).map((arch) => (
            <div key={arch.id} className="bg-white border border-slate-200 rounded-lg p-5 space-y-3 flex flex-col justify-between">
              <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-xs font-mono text-teal-800 font-semibold">{arch.task}</div>
                    <h4 className="text-base font-bold text-slate-900 mt-0.5 flex items-center gap-1.5">
                      <Cpu className="w-4 h-4 text-slate-500 shrink-0" />
                      <span>{arch.name}</span>
                    </h4>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">{arch.architecture}</p>

                <div className="border border-slate-200 rounded-md divide-y divide-slate-100 text-xs font-mono">
                  <div className="px-3 py-2 flex justify-between gap-2">
                    <span className="font-sans text-slate-500">Primary Tensor</span>
                    <span className="text-slate-900 font-semibold">{arch.input_shape_primary}</span>
                  </div>
                  <div className="px-3 py-2 flex justify-between gap-2">
                    <span className="font-sans text-slate-500">Synthetic Tensor</span>
                    <span className="text-slate-900 font-semibold">{arch.input_shape_synthetic}</span>
                  </div>
                  <div className="px-3 py-2 flex justify-between gap-2">
                    <span className="font-sans text-slate-500">Param Budget</span>
                    <span className="text-slate-700">{arch.approx_params}</span>
                  </div>
                  <div className="px-3 py-2 flex justify-between gap-2">
                    <span className="font-sans text-slate-500">CV Protocol</span>
                    <span className="text-teal-800 text-right">{arch.cv_contract}</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between gap-2">
                <span>Comparator: <strong className="text-slate-700">{arch.comparator}</strong></span>
                <span className="font-mono text-teal-800">{arch.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
