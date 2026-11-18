import React, { useState } from 'react';
import {
  AlertTriangle,
  ExternalLink,
  Lock,
  Play,
  RefreshCw,
  ShieldCheck,
  X,
} from 'lucide-react';
import {
  BaselineComparisonChart,
  ConfusionMatrixGrid,
  LeakageInflationChart,
} from './Day5And6Charts';
import { MarkdownViewer } from './MarkdownViewer';
import type { Day5BaselinesPayload, Day5DatasetBaselines } from '../types/day1';

interface Day5BaselinesViewProps {
  baselinesPayload: Day5BaselinesPayload | null;
  baselinesLoading: boolean;
  baselinesRunning: boolean;
  source: 'primary' | 'synthetic';
  onChangeSource: (src: 'primary' | 'synthetic') => void;
  onRunBaselines: (groupCol: 'plant_id' | 'plot_id' | 'field_id') => void;
  noteMarkdown: string;
  onOpenDoc: (key: string) => void;
}

export const Day5BaselinesView: React.FC<Day5BaselinesViewProps> = ({
  baselinesPayload,
  baselinesLoading,
  baselinesRunning,
  source,
  onChangeSource,
  onRunBaselines,
  noteMarkdown,
  onOpenDoc,
}) => {
  const [subSection, setSubSection] = useState<'models' | 'leakage' | 'figures' | 'report'>('models');
  const [groupCol, setGroupCol] = useState<'plant_id' | 'plot_id' | 'field_id'>('plant_id');
  const [lightboxFigure, setLightboxFigure] = useState<string | null>(null);

  const activeData: Day5DatasetBaselines | null = baselinesPayload
    ? source === 'synthetic'
      ? baselinesPayload.synthetic
      : baselinesPayload.primary
    : null;

  if (baselinesLoading && !activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-sm text-slate-500">
        Executing leak-free 5-fold baseline evaluation (<code className="font-mono">src/evaluation.py</code>)...
      </div>
    );
  }

  if (!activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-8 flex flex-col items-center justify-center gap-4 text-center">
        <div className="text-sm font-medium text-slate-800">
          Day 5 baseline evaluation results have not been generated yet.
        </div>
        <button
          type="button"
          onClick={() => onRunBaselines(groupCol)}
          disabled={baselinesRunning}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 cursor-pointer"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run Day 5 Baselines</span>
        </button>
      </div>
    );
  }

  const best = activeData.overall_best;
  const leak = activeData.leakage_demonstration;
  const maxOverlap = Math.max(0, ...activeData.split_manifest.folds.map((f) => f.group_overlap));

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span>src/evaluation.py</span>
              <span aria-hidden="true">·</span>
              <span>StratifiedGroupKFold &amp; Leakage Audit</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Random Forest, XGBoost, SVM &amp; PLS-DA Across Feature Sets A–E
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
              <span className="text-slate-600">Group Key</span>
              <select
                value={groupCol}
                onChange={(e) => setGroupCol(e.target.value as 'plant_id' | 'plot_id' | 'field_id')}
                className="font-mono bg-white border border-slate-200 rounded px-1.5 py-0.5"
              >
                <option value="plant_id">plant_id</option>
                <option value="plot_id">plot_id</option>
                <option value="field_id">field_id</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => onRunBaselines(groupCol)}
              disabled={baselinesRunning}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 disabled:opacity-60 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${baselinesRunning ? 'animate-spin' : ''}`} />
              <span>{baselinesRunning ? 'Training CV...' : 'Rerun Grouped CV'}</span>
            </button>
          </div>
        </div>

        {/* Leak-free guarantee & Winner Strip */}
        <div className="bg-slate-50 border border-slate-200 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-700">
            <Lock className="w-3.5 h-3.5 text-teal-800 shrink-0" />
            <span>
              <strong>CV Protocol:</strong>{' '}
              <code className="font-mono">{activeData.split_manifest.cv_strategy}</code> grouped by{' '}
              <code className="font-mono">{activeData.split_manifest.group_column}</code> · Max group overlap:{' '}
              <strong className="font-mono text-teal-800">{maxOverlap}</strong> · Seed{' '}
              <code className="font-mono">{activeData.random_seed}</code>
            </span>
          </div>
          <span className="font-mono tabular-nums text-teal-800 font-semibold whitespace-nowrap">
            Best Baseline: {best.model_name} (Set {best.feature_set_code}) · F1 {best.macro_f1_mean.toFixed(4)} ± {best.macro_f1_std.toFixed(4)}
          </span>
        </div>

        {/* Sub-section segmented bar */}
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg w-fit">
          {[
            { id: 'models', label: '1. Baselines & Feature Sets A–E' },
            { id: 'leakage', label: '2. Leakage Demonstration' },
            { id: 'figures', label: '3. Confusion & Leakage Plots (2)' },
            { id: 'report', label: '4. Baseline Report & CSV' },
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

      {/* SECTION 1: BASELINE MODELS & FEATURE SETS A-E */}
      {subSection === 'models' && (
        <div className="space-y-6">
          {/* Top KPI Winner + Leakage Warning Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Best Model to Beat</span>
                <ShieldCheck className="w-4 h-4 text-teal-800" />
              </div>
              <div className="text-lg font-bold text-slate-900 mt-1">
                {best.model_name} · Set {best.feature_set_code}
              </div>
              <div className="text-xs font-mono tabular-nums text-teal-800 mt-1">
                Macro-F1 {best.macro_f1_mean.toFixed(4)} ± {best.macro_f1_std.toFixed(4)} · Bal. Acc {best.balanced_acc_mean.toFixed(4)}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-xs text-slate-500">ROC-AUC (5-Fold Plant-Grouped)</div>
              <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 mt-1">
                {best.roc_auc_mean.toFixed(4)}
                <span className="text-xs font-normal text-slate-400 ml-2">
                  ± {best.roc_auc_std.toFixed(4)}
                </span>
              </div>
              <div className="text-xs text-slate-600 mt-1 font-mono">
                {activeData.clean_samples} clean scans · {activeData.split_manifest.unique_groups} groups
              </div>
            </div>

            <div className="bg-white border border-rose-200 rounded-lg p-4">
              <div className="flex items-center justify-between text-xs text-rose-700 font-medium">
                <span>Naive Split Leakage Gap</span>
                <AlertTriangle className="w-4 h-4 text-rose-600" />
              </div>
              <div className="text-2xl font-bold font-mono tabular-nums text-rose-700 mt-1">
                {leak.inflation_macro_f1 >= 0 ? `+${leak.inflation_macro_f1.toFixed(4)}` : leak.inflation_macro_f1.toFixed(4)} F1
              </div>
              <div className="text-xs text-slate-600 mt-1 font-mono tabular-nums">
                Grouped {leak.grouped_macro_f1.toFixed(4)} → Leaky {leak.naive_macro_f1.toFixed(4)}
              </div>
            </div>
          </div>

          {/* Interactive Chart + Confusion Matrix */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            <div className="xl:col-span-7">
              <BaselineComparisonChart data={activeData} />
            </div>
            <div className="xl:col-span-5 space-y-4">
              <ConfusionMatrixGrid
                title={`Out-of-Fold Confusion Matrix (${best.model_name} · Set ${best.feature_set_code})`}
                classNames={best.class_names}
                matrix={best.confusion_matrix}
              />
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="text-xs font-semibold text-slate-900 mb-2">
                  Per-Class Precision, Recall &amp; F1 (OOF)
                </div>
                <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-2.5 py-1.5 font-sans font-medium">Class</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">Prec</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">Recall</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">F1</th>
                      <th className="px-2.5 py-1.5 font-medium text-right">N</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {best.per_class.map((pc) => (
                      <tr key={pc.class_name}>
                        <td className="px-2.5 py-1.5 font-sans font-medium text-slate-800">{pc.class_name}</td>
                        <td className="px-2.5 py-1.5 text-right">{pc.precision.toFixed(4)}</td>
                        <td className="px-2.5 py-1.5 text-right">{pc.recall.toFixed(4)}</td>
                        <td className="px-2.5 py-1.5 text-right font-semibold text-teal-800">{pc.f1.toFixed(4)}</td>
                        <td className="px-2.5 py-1.5 text-right text-slate-500">{pc.support}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Table 1: Block 2 — 4 Models on Feature Set A */}
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Four Baseline Models on Feature Set A (Mean ± Std Over 5 Folds)
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  All models trained strictly on identical grouped splits ({activeData.split_manifest.group_column})
                </p>
              </div>
              <span className="text-xs font-mono text-slate-500">Set A: Preprocessed Spectrum</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-4 py-2.5 font-medium">Model</th>
                    <th className="px-4 py-2.5 font-medium text-right">Balanced Acc (± SD)</th>
                    <th className="px-4 py-2.5 font-medium text-right">Macro-F1 (± SD)</th>
                    <th className="px-4 py-2.5 font-medium text-right">ROC-AUC (± SD)</th>
                    <th className="px-4 py-2.5 font-medium text-right">OOF Macro-F1</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                  {activeData.set_a_models.map((r) => {
                    const isBestA =
                      r.model_key === activeData.best_model_feature_sets[0]?.model_key;
                    return (
                      <tr key={r.model_key} className={isBestA ? 'bg-teal-50/40' : ''}>
                        <td className="px-4 py-2.5 font-sans font-semibold text-slate-900">
                          {r.model_name} {isBestA && <span className="text-teal-800 ml-1">★</span>}
                        </td>
                        <td className="px-4 py-2.5 text-right text-slate-700">
                          {r.balanced_acc_mean.toFixed(4)} ± {r.balanced_acc_std.toFixed(4)}
                        </td>
                        <td className="px-4 py-2.5 text-right font-semibold text-teal-800">
                          {r.macro_f1_mean.toFixed(4)} ± {r.macro_f1_std.toFixed(4)}
                        </td>
                        <td className="px-4 py-2.5 text-right text-slate-700">
                          {r.roc_auc_mean.toFixed(4)} ± {r.roc_auc_std.toFixed(4)}
                        </td>
                        <td className="px-4 py-2.5 text-right text-slate-500">
                          {r.oof_macro_f1.toFixed(4)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Table 2: Block 3 — Best Model Across Feature Sets A-E + Fold Split Manifest */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-7 bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-200">
                <h3 className="text-sm font-semibold text-slate-900">
                  {activeData.best_model_feature_sets[0]?.model_name} Across Feature Sets A–E
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="px-4 py-2 font-medium">Set</th>
                      <th className="px-4 py-2 font-medium text-right">Bal. Acc (± SD)</th>
                      <th className="px-4 py-2 font-medium text-right">Macro-F1 (± SD)</th>
                      <th className="px-4 py-2 font-medium text-right">ROC-AUC</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                    {activeData.best_model_feature_sets.map((r) => {
                      const isWinner = r.feature_set_code === best.feature_set_code;
                      return (
                        <tr key={r.feature_set_key} className={isWinner ? 'bg-amber-50/50' : ''}>
                          <td className="px-4 py-2 font-sans">
                            <span className="font-mono font-semibold text-slate-900">Set {r.feature_set_code}</span>
                            {isWinner && <span className="text-teal-800 ml-1">★</span>}
                            <div className="text-[11px] text-slate-500">{r.feature_set_desc}</div>
                          </td>
                          <td className="px-4 py-2 text-right text-slate-700">
                            {r.balanced_acc_mean.toFixed(4)} ± {r.balanced_acc_std.toFixed(4)}
                          </td>
                          <td className="px-4 py-2 text-right font-semibold text-teal-800">
                            {r.macro_f1_mean.toFixed(4)} ± {r.macro_f1_std.toFixed(4)}
                          </td>
                          <td className="px-4 py-2 text-right text-slate-600">{r.roc_auc_mean.toFixed(4)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="lg:col-span-5 bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-200">
                <h3 className="text-sm font-semibold text-slate-900">
                  Fold Leak-Free Split Audit ({activeData.split_manifest.group_column})
                </h3>
                <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                  Saved: data/processed/{activeData.source}_day5_cv_splits.json
                </p>
              </div>
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-3 py-2 font-medium">Fold</th>
                    <th className="px-3 py-2 font-medium text-right">Train N (Grp)</th>
                    <th className="px-3 py-2 font-medium text-right">Val N (Grp)</th>
                    <th className="px-3 py-2 font-medium text-right">Overlap</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {activeData.split_manifest.folds.map((f) => (
                    <tr key={f.fold}>
                      <td className="px-3 py-2 font-semibold text-slate-800">Fold {f.fold + 1}</td>
                      <td className="px-3 py-2 text-right text-slate-600">
                        {f.train_n} ({f.train_groups})
                      </td>
                      <td className="px-3 py-2 text-right text-slate-600">
                        {f.val_n} ({f.val_groups})
                      </td>
                      <td className="px-3 py-2 text-right font-semibold text-teal-800">
                        {f.group_overlap}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: LEAKAGE DEMONSTRATION */}
      {subSection === 'leakage' && baselinesPayload && (
        <div className="space-y-6">
          <div className="bg-white border border-rose-200 rounded-lg p-5 space-y-3">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Empirical Leakage Proof: Why Naive Random Splits Overstate Accuracy
                </h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  Re-running <strong>{leak.model_name} (Set {leak.feature_set_code})</strong> with a standard random <code className="font-mono">StratifiedKFold</code> (ignoring <code className="font-mono">plant_id</code>) leaks replicate daily scans of the exact same physical plants between training and test folds, artificially inflating Macro-F1 by <strong className="font-mono text-rose-700">{leak.inflation_macro_f1 >= 0 ? `+${leak.inflation_macro_f1.toFixed(4)}` : leak.inflation_macro_f1.toFixed(4)}</strong> and Balanced Accuracy by <strong className="font-mono text-rose-700">{leak.inflation_balanced_acc >= 0 ? `+${leak.inflation_balanced_acc.toFixed(4)}` : leak.inflation_balanced_acc.toFixed(4)}</strong>.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            <div className="xl:col-span-7">
              <LeakageInflationChart
                primary={baselinesPayload.primary}
                synthetic={baselinesPayload.synthetic}
              />
            </div>
            <div className="xl:col-span-5 space-y-4">
              <ConfusionMatrixGrid
                title={`Naive Random Split CM (${leak.model_name} · Set ${leak.feature_set_code})`}
                classNames={best.class_names}
                matrix={leak.naive_confusion_matrix}
                accent="rose"
              />
              <div className="bg-white border border-slate-200 rounded-lg p-4 text-xs space-y-2 font-mono tabular-nums">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="font-sans text-slate-600">Honest Grouped Balanced Acc</span>
                  <span className="font-semibold text-teal-800">{leak.grouped_balanced_acc.toFixed(4)} ± {leak.grouped_balanced_acc_std.toFixed(4)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="font-sans text-slate-600">Leaky Naive Balanced Acc</span>
                  <span className="font-semibold text-rose-700">{leak.naive_balanced_acc.toFixed(4)} ± {leak.naive_balanced_acc_std.toFixed(4)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="font-sans text-slate-600">Honest Grouped ROC-AUC</span>
                  <span className="font-semibold text-teal-800">{leak.grouped_roc_auc.toFixed(4)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="font-sans text-slate-600">Leaky Naive ROC-AUC</span>
                  <span className="font-semibold text-rose-700">{leak.naive_roc_auc.toFixed(4)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: SAVED FIGURES */}
      {subSection === 'figures' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {(baselinesPayload?.figures || []).map((figRel) => {
            const filename = figRel.split('/').pop() || figRel;
            const title = filename.replace(/^\d+_/, '').replace('.png', '').replace(/_/g, ' ');
            return (
              <div key={figRel} className="bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col">
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
                    src={`/api/figures/${filename}?g=${groupCol}`}
                    alt={title}
                    className="w-full h-auto rounded border border-slate-200 bg-white"
                  />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* SECTION 4: REPORT & CSV */}
      {subSection === 'report' && (
        <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <div className="text-xs font-mono text-slate-500">
                docs/baseline_results_note.md · {baselinesPayload?.csv_path}
              </div>
              <h3 className="text-base font-semibold text-slate-900 mt-0.5">
                Day 5 Baseline Evaluation Report
              </h3>
            </div>
            <button
              type="button"
              onClick={() => onOpenDoc('baseline_results_note')}
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
              src={`/api/figures/${lightboxFigure}?g=${groupCol}`}
              alt={lightboxFigure}
              className="w-full h-auto max-h-[80vh] object-contain mx-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
};
