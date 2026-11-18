import React, { useState } from 'react';
import type {
  Day5DatasetBaselines,
  Day5ModelRun,
  Day6DatasetAnalysis,
} from '../types/day1';

interface BaselineComparisonChartProps {
  data: Day5DatasetBaselines;
}

export const BaselineComparisonChart: React.FC<BaselineComparisonChartProps> = ({ data }) => {
  const [viewMode, setViewMode] = useState<'set_a' | 'feature_sets'>('set_a');
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const runs: Day5ModelRun[] =
    viewMode === 'set_a' ? data.set_a_models : data.best_model_feature_sets;

  if (!runs || runs.length === 0) return null;

  const width = 620;
  const height = 270;
  const pad = { top: 24, right: 20, bottom: 52, left: 48 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const yScale = (v: number) => pad.top + plotH - Math.min(1.05, Math.max(0, v)) / 1.05 * plotH;
  const slotW = plotW / runs.length;
  const barW = Math.min(34, slotW * 0.34);
  const activeRun = runs[hoveredIdx ?? 0];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {viewMode === 'set_a'
              ? 'Feature Set A: 4 Baseline Models (5-Fold Plant-Grouped CV)'
              : `${data.best_model_feature_sets[0]?.model_name || 'Best Model'}: Feature Sets A–E Sweep`}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Bars show mean across 5 folds; whiskers indicate ±1 fold SD on Macro-F1
          </p>
        </div>

        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
          <button
            type="button"
            onClick={() => {
              setViewMode('set_a');
              setHoveredIdx(null);
            }}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              viewMode === 'set_a' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            4 Models (Set A)
          </button>
          <button
            type="button"
            onClick={() => {
              setViewMode('feature_sets');
              setHoveredIdx(null);
            }}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              viewMode === 'feature_sets' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Sets A–E Sweep
          </button>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto select-none"
        onMouseLeave={() => setHoveredIdx(null)}
      >
        {[0, 0.25, 0.5, 0.75, 1.0].map((v) => {
          const y = yScale(v);
          return (
            <g key={v}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
              <text x={pad.left - 8} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono tabular-nums">
                {v.toFixed(2)}
              </text>
            </g>
          );
        })}

        {runs.map((run, i) => {
          const cx = pad.left + i * slotW + slotW / 2;
          const yF1 = yScale(run.macro_f1_mean);
          const yBacc = yScale(run.balanced_acc_mean);
          const yTopSd = yScale(run.macro_f1_mean + run.macro_f1_std);
          const yBotSd = yScale(Math.max(0, run.macro_f1_mean - run.macro_f1_std));
          const isBest =
            run.model_key === data.overall_best.model_key &&
            run.feature_set_code === data.overall_best.feature_set_code;
          const xLabel = viewMode === 'set_a' ? run.model_name : `Set ${run.feature_set_code}`;

          return (
            <g
              key={`${run.model_key}-${run.feature_set_code}`}
              onMouseEnter={() => setHoveredIdx(i)}
              className="cursor-pointer"
            >
              <rect
                x={cx - barW - 2}
                y={yF1}
                width={barW}
                height={Math.max(1, pad.top + plotH - yF1)}
                fill={isBest ? '#115E59' : '#0F766E'}
                fillOpacity={hoveredIdx === i ? 1 : 0.88}
                rx={2}
              />
              <line x1={cx - barW / 2 - 2} x2={cx - barW / 2 - 2} y1={yTopSd} y2={yBotSd} stroke="#0F172A" strokeWidth={1.3} />
              <line x1={cx - barW / 2 - 6} x2={cx - barW / 2 + 2} y1={yTopSd} y2={yTopSd} stroke="#0F172A" strokeWidth={1.3} />
              <line x1={cx - barW / 2 - 6} x2={cx - barW / 2 + 2} y1={yBotSd} y2={yBotSd} stroke="#0F172A" strokeWidth={1.3} />

              <rect
                x={cx + 2}
                y={yBacc}
                width={barW}
                height={Math.max(1, pad.top + plotH - yBacc)}
                fill="#2563EB"
                fillOpacity={hoveredIdx === i ? 0.95 : 0.78}
                rx={2}
              />

              <text
                x={cx - barW / 2 - 2}
                y={Math.max(12, yTopSd - 5)}
                textAnchor="middle"
                className="fill-slate-800 text-[9.5px] font-mono tabular-nums font-semibold"
              >
                {run.macro_f1_mean.toFixed(3)}
              </text>
              <text
                x={cx}
                y={height - 16}
                textAnchor="middle"
                className={`text-[10.5px] font-sans ${isBest ? 'fill-teal-800 font-bold' : 'fill-slate-600'}`}
              >
                {xLabel}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-2 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-4 text-slate-600">
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-teal-700 mr-1.5 align-middle" />
            Macro-F1 (± SD)
          </span>
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-blue-600 mr-1.5 align-middle" />
            Balanced Acc
          </span>
        </div>
        {activeRun && (
          <div className="font-mono tabular-nums text-slate-700">
            {activeRun.model_name} (Set {activeRun.feature_set_code}) · F1 {activeRun.macro_f1_mean.toFixed(4)} ± {activeRun.macro_f1_std.toFixed(4)} · AUC {activeRun.roc_auc_mean.toFixed(4)}
          </div>
        )}
      </div>
    </div>
  );
};

interface LeakageInflationChartProps {
  primary: Day5DatasetBaselines;
  synthetic: Day5DatasetBaselines;
}

export const LeakageInflationChart: React.FC<LeakageInflationChartProps> = ({
  primary,
  synthetic,
}) => {
  const lp = primary.leakage_demonstration;
  const ls = synthetic.leakage_demonstration;
  const items = [
    { label: 'Primary Bal. Acc', grouped: lp.grouped_balanced_acc, naive: lp.naive_balanced_acc },
    { label: 'Primary Macro-F1', grouped: lp.grouped_macro_f1, naive: lp.naive_macro_f1 },
    { label: 'Primary ROC-AUC', grouped: lp.grouped_roc_auc, naive: lp.naive_roc_auc },
    { label: 'Synthetic Macro-F1', grouped: ls.grouped_macro_f1, naive: ls.naive_macro_f1 },
  ];

  const width = 560;
  const height = 260;
  const pad = { top: 28, right: 20, bottom: 48, left: 48 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const yScale = (v: number) => pad.top + plotH - Math.min(1.08, Math.max(0, v)) / 1.08 * plotH;
  const slotW = plotW / items.length;
  const barW = Math.min(34, slotW * 0.32);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-slate-900">
          Leakage Inflation: Plant-Grouped vs. Naive Random Split
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Naive random CV mixes scans from identical plants across train &amp; validation folds
        </p>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
        {[0, 0.25, 0.5, 0.75, 1.0].map((v) => {
          const y = yScale(v);
          return (
            <g key={v}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
              <text x={pad.left - 8} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono tabular-nums">
                {v.toFixed(2)}
              </text>
            </g>
          );
        })}

        {items.map((item, i) => {
          const cx = pad.left + i * slotW + slotW / 2;
          const yG = yScale(item.grouped);
          const yN = yScale(item.naive);
          const delta = item.naive - item.grouped;
          return (
            <g key={item.label}>
              <rect
                x={cx - barW - 2}
                y={yG}
                width={barW}
                height={Math.max(1, pad.top + plotH - yG)}
                fill="#0F766E"
                rx={2}
              />
              <rect
                x={cx + 2}
                y={yN}
                width={barW}
                height={Math.max(1, pad.top + plotH - yN)}
                fill="#DC2626"
                fillOpacity={0.88}
                rx={2}
              />
              <text
                x={cx - barW / 2 - 2}
                y={yG - 5}
                textAnchor="middle"
                className="fill-teal-900 text-[9.5px] font-mono tabular-nums"
              >
                {item.grouped.toFixed(3)}
              </text>
              <text
                x={cx + barW / 2 + 2}
                y={Math.max(12, yN - 5)}
                textAnchor="middle"
                className="fill-rose-700 text-[9.5px] font-mono tabular-nums font-bold"
              >
                {item.naive.toFixed(3)} ({delta >= 0 ? `+${delta.toFixed(3)}` : delta.toFixed(3)})
              </text>
              <text x={cx} y={height - 16} textAnchor="middle" className="fill-slate-600 text-[10px] font-sans">
                {item.label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-2 pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-5 text-xs text-slate-600">
        <span>
          <span className="inline-block w-2.5 h-2.5 bg-teal-700 mr-1.5 align-middle" />
          StratifiedGroupKFold (Honest)
        </span>
        <span>
          <span className="inline-block w-2.5 h-2.5 bg-red-600 mr-1.5 align-middle" />
          Naive StratifiedKFold (Leaky)
        </span>
      </div>
    </div>
  );
};

interface ConfusionMatrixGridProps {
  title: string;
  classNames: string[];
  matrix: number[][];
  accent?: 'teal' | 'rose';
}

export const ConfusionMatrixGrid: React.FC<ConfusionMatrixGridProps> = ({
  title,
  classNames,
  matrix,
  accent = 'teal',
}) => {
  if (!matrix || matrix.length === 0) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
      <div className="text-xs font-semibold text-slate-900">{title}</div>
      <div className="overflow-x-auto">
        <table className="w-full text-center border-collapse text-xs font-mono tabular-nums">
          <thead>
            <tr className="text-slate-500">
              <th className="p-2 text-left font-sans font-medium">True \ Pred</th>
              {classNames.map((cn) => (
                <th key={cn} className="p-2 font-sans font-medium truncate max-w-[110px]" title={cn}>
                  {cn.replace(/\s*\(.*?\)/g, '')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => {
              const rowSum = Math.max(1, row.reduce((a, b) => a + b, 0));
              return (
                <tr key={classNames[i] || i} className="border-t border-slate-100">
                  <td className="p-2 text-left font-sans font-medium text-slate-800 whitespace-nowrap">
                    {(classNames[i] || `Class ${i}`).replace(/\s*\(.*?\)/g, '')}
                  </td>
                  {row.map((val, j) => {
                    const pct = (val / rowSum) * 100;
                    const isDiag = i === j;
                    const bgClass = isDiag
                      ? accent === 'rose'
                        ? pct > 70
                          ? 'bg-rose-700 text-white'
                          : 'bg-rose-100 text-rose-900'
                        : pct > 65
                          ? 'bg-teal-800 text-white'
                          : 'bg-teal-100 text-teal-900'
                      : 'bg-slate-50 text-slate-700';
                    return (
                      <td key={j} className={`p-2 border border-white rounded ${bgClass}`}>
                        <div className="font-bold">{val}</div>
                        <div className="text-[10px] opacity-85">{pct.toFixed(1)}%</div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface MisclassifiedSpectraChartProps {
  errorAnalysis: Day6DatasetAnalysis['error_analysis'];
}

export const MisclassifiedSpectraChart: React.FC<MisclassifiedSpectraChartProps> = ({
  errorAnalysis,
}) => {
  const comps = errorAnalysis.spectra_comparison;
  const dateSeries = errorAnalysis.by_date_series;
  if (!comps || comps.length === 0) return null;

  const w = 560;
  const h = 260;
  const pad = { top: 20, right: 18, bottom: 40, left: 46 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;

  const allPts = comps.flatMap((c) => c.points);
  const wls = comps[0].points.map((p) => p.wavelength_nm);
  const minWl = Math.min(...wls);
  const maxWl = Math.max(...wls);
  const minR = Math.min(0, ...allPts.map((p) => Math.min(p.true_mean - p.true_std, p.misclassified_mean)));
  const maxR = Math.max(10, ...allPts.map((p) => Math.max(p.true_mean + p.true_std, p.misclassified_mean))) * 1.06;

  const xScale = (wl: number) => pad.left + ((wl - minWl) / Math.max(1, maxWl - minWl)) * pw;
  const yScale = (val: number) => pad.top + ph - ((val - minR) / Math.max(1e-6, maxR - minR)) * ph;

  const palette = ['#0F766E', '#D97706', '#2563EB', '#DC2626'];

  // Right chart: Daily error rate trajectory
  const maxErr = Math.max(20, ...dateSeries.map((d) => d.error_rate_pct)) * 1.1;
  const xDateScale = (idx: number) =>
    pad.left + (idx / Math.max(1, dateSeries.length - 1)) * pw;
  const yErrScale = (pct: number) => pad.top + ph - (pct / maxErr) * ph;
  const midIdx = Math.floor(dateSeries.length / 2);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-slate-900">
            Misclassified Spectra vs. True Class Mean ± SD
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Dashed curves trace misclassified out-of-fold spectra sitting right inside opposing class envelopes
          </p>
        </div>
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto select-none">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const val = minR + t * (maxR - minR);
            const y = yScale(val);
            return (
              <g key={t}>
                <line x1={pad.left} x2={w - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
                <text x={pad.left - 6} y={y + 3} textAnchor="end" className="fill-slate-500 text-[10px] font-mono">
                  {val.toFixed(0)}
                </text>
              </g>
            );
          })}

          {comps.slice(0, 4).map((cls, cIdx) => {
            const color = palette[cIdx % palette.length];
            const pts = cls.points;
            const meanPath = pts
              .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.wavelength_nm)} ${yScale(p.true_mean)}`)
              .join(' ');
            const errPath = pts
              .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.wavelength_nm)} ${yScale(p.misclassified_mean)}`)
              .join(' ');
            const upper = pts.map((p) => `${xScale(p.wavelength_nm)},${yScale(p.true_mean + p.true_std)}`).join(' ');
            const lower = [...pts]
              .reverse()
              .map((p) => `${xScale(p.wavelength_nm)},${yScale(p.true_mean - p.true_std)}`)
              .join(' ');

            return (
              <g key={cls.class_name}>
                <polygon points={`${upper} ${lower}`} fill={color} fillOpacity={0.09} />
                <path d={meanPath} fill="none" stroke={color} strokeWidth={2.0} />
                <path d={errPath} fill="none" stroke={color} strokeWidth={1.8} strokeDasharray="5 3" />
              </g>
            );
          })}

          {wls
            .filter((_, idx) => wls.length <= 12 || idx % Math.ceil(wls.length / 8) === 0)
            .map((wl) => (
              <text
                key={wl}
                x={xScale(wl)}
                y={h - 14}
                textAnchor="middle"
                className="fill-slate-500 text-[10px] font-mono"
              >
                {wl}
              </text>
            ))}
        </svg>

        <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-4 text-xs text-slate-600">
          {comps.slice(0, 4).map((cls, cIdx) => (
            <span key={cls.class_name} className="inline-flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-0.5"
                style={{ backgroundColor: palette[cIdx % palette.length] }}
              />
              <span>
                {cls.class_name.replace(/\s*\(.*?\)/g, '')} (err {cls.n_errors}/{cls.n_total})
              </span>
            </span>
          ))}
          <span className="font-mono text-slate-400">Solid: Class Mean · Dashed: Errors</span>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="mb-2 flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Temporal Error Rate Drift Across Acquisition Dates
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Early half error: <strong className="font-mono">{errorAnalysis.early_half_error_pct}%</strong> vs. Late half: <strong className="font-mono">{errorAnalysis.late_half_error_pct}%</strong>
            </p>
          </div>
        </div>
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto select-none">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const pct = t * maxErr;
            const y = yErrScale(pct);
            return (
              <g key={t}>
                <line x1={pad.left} x2={w - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
                <text x={pad.left - 6} y={y + 3} textAnchor="end" className="fill-slate-500 text-[10px] font-mono">
                  {pct.toFixed(0)}%
                </text>
              </g>
            );
          })}
          <line
            x1={xDateScale(midIdx)}
            x2={xDateScale(midIdx)}
            y1={pad.top}
            y2={pad.top + ph}
            stroke="#64748B"
            strokeDasharray="4 4"
            strokeWidth={1.2}
          />
          <path
            d={dateSeries
              .map((d, i) => `${i === 0 ? 'M' : 'L'} ${xDateScale(i)} ${yErrScale(d.error_rate_pct)}`)
              .join(' ')}
            fill="none"
            stroke="#DC2626"
            strokeWidth={2}
          />
          {dateSeries.map((d, i) => (
            <g key={d.date}>
              <circle cx={xDateScale(i)} cy={yErrScale(d.error_rate_pct)} r={2.8} fill="#DC2626" />
              {(i === 0 || i === dateSeries.length - 1 || i % Math.max(1, Math.floor(dateSeries.length / 5)) === 0) && (
                <text x={xDateScale(i)} y={h - 14} textAnchor="middle" className="fill-slate-500 text-[9.5px] font-mono">
                  {d.date}
                </text>
              )}
            </g>
          ))}
        </svg>
        <div className="mt-2 pt-2 border-t border-slate-100 text-xs text-slate-600 flex justify-between">
          <span>Vertical rule marks trial midpoint ({dateSeries[midIdx]?.date || 'mid'})</span>
          <span className="font-mono text-slate-500">{dateSeries.length} dates tracked</span>
        </div>
      </div>
    </div>
  );
};

interface ShapVsDay2ChartProps {
  interpretability: Day6DatasetAnalysis['interpretability'];
  modelLabel: string;
}

export const ShapVsDay2Chart: React.FC<ShapVsDay2ChartProps> = ({
  interpretability,
  modelLabel,
}) => {
  const topShap = interpretability.best_set_shap.features.slice(0, 10);
  const wls = interpretability.wavelength_shap_vs_day2;

  const maxShap = Math.max(1e-6, ...topShap.map((f) => f.mean_abs_shap));
  const maxWlShap = Math.max(1e-6, ...wls.map((w) => w.shap_importance));
  const maxWlFish = Math.max(1e-6, ...wls.map((w) => w.day2_fisher_ratio));

  const svgW = 560;
  const svgH = 270;
  const pad = { top: 22, right: 18, bottom: 42, left: 44 };
  const pw = svgW - pad.left - pad.right;
  const ph = svgH - pad.top - pad.bottom;
  const slotW = pw / Math.max(1, wls.length);
  const bw = Math.min(18, slotW * 0.34);
  const yScale = (v: number) => pad.top + ph - v * ph;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Top Validation Features by |SHAP| ({interpretability.best_set_shap.method})
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {modelLabel} evaluated on {interpretability.best_set_shap.n_eval_samples} held-out plant scans
          </p>
        </div>

        <div className="space-y-2">
          {topShap.map((item) => {
            const pct = (item.mean_abs_shap / maxShap) * 100;
            return (
              <div key={item.feature} className="text-xs space-y-1">
                <div className="flex items-center justify-between font-mono tabular-nums">
                  <span className="font-semibold text-slate-800">{item.feature}</span>
                  <span className="text-slate-600">
                    |SHAP| {item.mean_abs_shap.toFixed(4)} · Perm {item.permutation_importance.toFixed(4)}
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded overflow-hidden">
                  <div className="h-full bg-teal-700 rounded" style={{ width: `${Math.max(3, pct)}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Wavelength SHAP vs. Day 2 EDA Fisher Discriminant J
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Normalized wavelength importance across aligned spectrum
            </p>
          </div>
          <span className="text-xs font-mono font-semibold text-teal-800 whitespace-nowrap">
            Spearman ρ = {interpretability.spearman_shap_vs_fisher.toFixed(2)}
          </span>
        </div>

        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full h-auto select-none">
          {[0, 0.25, 0.5, 0.75, 1].map((v) => {
            const y = yScale(v);
            return (
              <g key={v}>
                <line x1={pad.left} x2={svgW - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
                <text x={pad.left - 6} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono">
                  {v.toFixed(2)}
                </text>
              </g>
            );
          })}

          {wls.length > 18 ? (
            <>
              <path
                d={wls
                  .map(
                    (w, i) =>
                      `${i === 0 ? 'M' : 'L'} ${pad.left + (i / (wls.length - 1)) * pw} ${yScale(w.shap_importance / maxWlShap)}`
                  )
                  .join(' ')}
                fill="none"
                stroke="#0F766E"
                strokeWidth={2.0}
              />
              <path
                d={wls
                  .map(
                    (w, i) =>
                      `${i === 0 ? 'M' : 'L'} ${pad.left + (i / (wls.length - 1)) * pw} ${yScale(w.day2_fisher_ratio / maxWlFish)}`
                  )
                  .join(' ')}
                fill="none"
                stroke="#D97706"
                strokeWidth={1.8}
                strokeDasharray="4 3"
              />
              {wls
                .filter((_, i) => i % 10 === 0)
                .map((w) => {
                  const idx = wls.indexOf(w);
                  return (
                    <text
                      key={w.wavelength_nm}
                      x={pad.left + (idx / (wls.length - 1)) * pw}
                      y={svgH - 14}
                      textAnchor="middle"
                      className="fill-slate-500 text-[10px] font-mono"
                    >
                      {w.wavelength_nm}
                    </text>
                  );
                })}
            </>
          ) : (
            wls.map((w, i) => {
              const cx = pad.left + i * slotW + slotW / 2;
              const yS = yScale(w.shap_importance / maxWlShap);
              const yF = yScale(w.day2_fisher_ratio / maxWlFish);
              return (
                <g key={w.wavelength_nm}>
                  <rect x={cx - bw - 1} y={yS} width={bw} height={Math.max(1, pad.top + ph - yS)} fill="#0F766E" rx={2} />
                  <rect x={cx + 1} y={yF} width={bw} height={Math.max(1, pad.top + ph - yF)} fill="#D97706" rx={2} />
                  <text x={cx} y={svgH - 14} textAnchor="middle" className="fill-slate-600 text-[10px] font-mono">
                    {w.wavelength_nm}
                  </text>
                </g>
              );
            })
          )}
        </svg>

        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center gap-5 text-xs text-slate-600">
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-teal-700 mr-1.5 align-middle" />
            Model |SHAP| (Set A)
          </span>
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-amber-600 mr-1.5 align-middle" />
            Day 2 EDA Fisher J
          </span>
        </div>
      </div>
    </div>
  );
};

interface ForecastHorizonChartProps {
  horizons: Day6DatasetAnalysis['forecasting_prep']['horizons'];
}

export const ForecastHorizonChart: React.FC<ForecastHorizonChartProps> = ({ horizons }) => {
  const valid = horizons.filter((h) => h.feasible);
  if (valid.length === 0) return null;

  const h1 = valid[0];
  const pts = h1.sample_predictions.slice(0, 35);

  const w = 560;
  const h = 250;
  const pad = { top: 20, right: 18, bottom: 40, left: 48 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;

  const allMaes = valid.flatMap((hr) => hr.models.map((m) => m.mae_mean));
  const maxMae = Math.max(0.01, Math.max(...allMaes) * 1.2);
  const slotW = pw / valid.length;
  const bw = Math.min(26, slotW * 0.24);
  const yMae = (v: number) => pad.top + ph - (v / maxMae) * ph;

  // Trajectory right panel
  const allNdvi = pts.flatMap((p) => [p.actual_ndvi, p.persistence_ndvi, p.lag_rf_ndvi]);
  const minN = Math.min(...allNdvi) - 0.02;
  const maxN = Math.max(...allNdvi) + 0.02;
  const xPt = (i: number) => pad.left + (i / Math.max(1, pts.length - 1)) * pw;
  const yPt = (v: number) => pad.top + ph - ((v - minN) / Math.max(1e-4, maxN - minN)) * ph;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-slate-900">
            Forecast Error (CV MAE) by Horizon k: Persistence vs. Lag Models
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Lower MAE is better · evaluated with GroupKFold(plant_id)
          </p>
        </div>
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto select-none">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const val = t * maxMae;
            const y = yMae(val);
            return (
              <g key={t}>
                <line x1={pad.left} x2={w - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
                <text x={pad.left - 6} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono">
                  {val.toFixed(3)}
                </text>
              </g>
            );
          })}
          {valid.map((hr, i) => {
            const cx = pad.left + i * slotW + slotW / 2;
            const mp = hr.models.find((m) => m.key === 'persistence')!;
            const mr = hr.models.find((m) => m.key === 'lag_ridge')!;
            const mrf = hr.models.find((m) => m.key === 'lag_rf')!;
            return (
              <g key={hr.horizon}>
                <rect x={cx - bw * 1.5 - 2} y={yMae(mp.mae_mean)} width={bw} height={Math.max(1, pad.top + ph - yMae(mp.mae_mean))} fill="#64748B" rx={2} />
                <rect x={cx - bw * 0.5} y={yMae(mr.mae_mean)} width={bw} height={Math.max(1, pad.top + ph - yMae(mr.mae_mean))} fill="#2563EB" rx={2} />
                <rect x={cx + bw * 0.5 + 2} y={yMae(mrf.mae_mean)} width={bw} height={Math.max(1, pad.top + ph - yMae(mrf.mae_mean))} fill="#0F766E" rx={2} />
                <text x={cx} y={h - 14} textAnchor="middle" className="fill-slate-700 text-[10.5px] font-mono">
                  k = +{hr.horizon} step
                </text>
              </g>
            );
          })}
        </svg>
        <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-4 text-xs text-slate-600">
          <span><span className="inline-block w-2.5 h-2.5 bg-slate-500 mr-1.5 align-middle" />Persistence</span>
          <span><span className="inline-block w-2.5 h-2.5 bg-blue-600 mr-1.5 align-middle" />Lag-Ridge</span>
          <span><span className="inline-block w-2.5 h-2.5 bg-teal-700 mr-1.5 align-middle" />Lag-RF</span>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-slate-900">
            Out-of-Fold Next-Timepoint NDVI Trajectory Preview (k = +{h1.horizon})
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Sampled windows from held-out plants comparing Actual vs. Persistence vs. Lag-RF
          </p>
        </div>
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto select-none">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const val = minN + t * (maxN - minN);
            const y = yPt(val);
            return (
              <g key={t}>
                <line x1={pad.left} x2={w - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
                <text x={pad.left - 6} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono">
                  {val.toFixed(2)}
                </text>
              </g>
            );
          })}
          <path
            d={pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xPt(i)} ${yPt(p.actual_ndvi)}`).join(' ')}
            fill="none"
            stroke="#0F172A"
            strokeWidth={2}
          />
          <path
            d={pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xPt(i)} ${yPt(p.persistence_ndvi)}`).join(' ')}
            fill="none"
            stroke="#64748B"
            strokeWidth={1.4}
            strokeDasharray="3 3"
          />
          <path
            d={pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xPt(i)} ${yPt(p.lag_rf_ndvi)}`).join(' ')}
            fill="none"
            stroke="#0F766E"
            strokeWidth={1.8}
            strokeDasharray="6 3"
          />
          <text x={w / 2} y={h - 14} textAnchor="middle" className="fill-slate-500 text-[10px] font-mono">
            Held-out chronological plant windows ({pts.length} shown)
          </text>
        </svg>
        <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-4 text-xs text-slate-600">
          <span><span className="inline-block w-3 h-0.5 bg-slate-900 mr-1.5 align-middle" />Actual NDVI</span>
          <span><span className="inline-block w-3 h-0.5 bg-slate-500 mr-1.5 align-middle" />Persistence</span>
          <span><span className="inline-block w-3 h-0.5 bg-teal-700 mr-1.5 align-middle" />Lag-RF Forecast</span>
        </div>
      </div>
    </div>
  );
};
