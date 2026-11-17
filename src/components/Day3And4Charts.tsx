import React, { useState } from 'react';
import type { Day4DatasetFeatures, PreprocessingStepResult } from '../types/day1';

interface PreprocessingAblationChartProps {
  steps: PreprocessingStepResult[];
}

export const PreprocessingAblationChart: React.FC<PreprocessingAblationChartProps> = ({ steps }) => {
  const [metric, setMetric] = useState<'f1' | 'fisher'>('f1');
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!steps || steps.length === 0) return null;

  const width = 760;
  const height = 270;
  const pad = { top: 24, right: 24, bottom: 52, left: 56 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const values = steps.map((s) => (metric === 'f1' ? s.holdout_macro_f1 : s.mean_fisher_ratio));
  const maxVal =
    metric === 'f1'
      ? 1.05
      : Math.max(0.01, Math.max(...values) * 1.2);

  const slotW = plotW / steps.length;
  const barW = Math.min(48, slotW * 0.54);
  const yScale = (v: number) => pad.top + plotH - (v / maxVal) * plotH;
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map((t) => t * (metric === 'f1' ? 1.0 : maxVal));
  const activeStep = steps[hoveredIdx ?? steps.length - 1];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {metric === 'f1'
              ? 'Plant-Grouped Holdout Macro-F1 Across Preprocessing Steps'
              : 'Training-Split Mean Fisher Ratio (J) Across Preprocessing Steps'}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Every scaler &amp; MSC reference spectrum fitted strictly on training plants only
          </p>
        </div>

        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
          <button
            type="button"
            onClick={() => setMetric('f1')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              metric === 'f1' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Holdout Macro-F1
          </button>
          <button
            type="button"
            onClick={() => setMetric('fisher')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              metric === 'fisher' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Fisher Ratio (J)
          </button>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto select-none"
        onMouseLeave={() => setHoveredIdx(null)}
      >
        {yTicks.map((tick, idx) => {
          const y = yScale(tick);
          return (
            <g key={idx}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
              <text
                x={pad.left - 8}
                y={y + 4}
                textAnchor="end"
                className="fill-slate-500 text-[10px] font-mono tabular-nums"
              >
                {metric === 'f1' ? tick.toFixed(2) : tick.toFixed(4)}
              </text>
            </g>
          );
        })}

        {steps.map((step, idx) => {
          const val = metric === 'f1' ? step.holdout_macro_f1 : step.mean_fisher_ratio;
          const cx = pad.left + idx * slotW + slotW / 2;
          const yTop = yScale(val);
          const barH = Math.max(2, pad.top + plotH - yTop);
          const isHovered = hoveredIdx === idx;
          const shortName = step.label.replace(/^\d+\.\s*/, '').slice(0, 16);
          return (
            <g key={step.key} onMouseEnter={() => setHoveredIdx(idx)} className="cursor-pointer">
              <rect
                x={cx - barW / 2}
                y={yTop}
                width={barW}
                height={barH}
                rx={3}
                fill={idx === 0 ? '#64748B' : isHovered ? '#115E59' : '#0F766E'}
                fillOpacity={isHovered ? 1 : 0.86}
              />
              <text
                x={cx}
                y={yTop - 6}
                textAnchor="middle"
                className="fill-slate-700 text-[10px] font-mono tabular-nums font-medium"
              >
                {metric === 'f1' ? val.toFixed(3) : val.toFixed(4)}
              </text>
              <text
                x={cx}
                y={height - 18}
                textAnchor="middle"
                className="fill-slate-600 text-[10px] font-sans"
              >
                {shortName}
              </text>
            </g>
          );
        })}
      </svg>

      {activeStep && (
        <div className="mt-2 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs font-mono tabular-nums text-slate-600">
          <span className="font-sans font-semibold text-slate-900">{activeStep.label}</span>
          <div className="flex flex-wrap items-center gap-4">
            <span>Bands: {activeStep.n_bands}</span>
            <span>Mean J: {activeStep.mean_fisher_ratio.toFixed(5)}</span>
            <span className="text-teal-800 font-semibold">
              Holdout F1: {activeStep.holdout_macro_f1.toFixed(4)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

interface PcaScreeChartProps {
  pca: Day4DatasetFeatures['pca'];
}

export const PcaScreeChart: React.FC<PcaScreeChartProps> = ({ pca }) => {
  if (!pca || pca.components.length === 0) return null;

  const width = 580;
  const height = 270;
  const pad = { top: 24, right: 24, bottom: 42, left: 48 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const comps = pca.components;
  const slotW = plotW / comps.length;
  const barW = Math.min(34, slotW * 0.56);
  const yScale = (pct: number) => pad.top + plotH - (pct / 105) * plotH;

  const lineD = comps
    .map((c, idx) => {
      const cx = pad.left + idx * slotW + slotW / 2;
      const cy = yScale(c.cumulative_variance * 100);
      return `${idx === 0 ? 'M' : 'L'} ${cx} ${cy}`;
    })
    .join(' ');

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Train-Only PCA Explained Variance (Scree + Cumulative)
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {pca.selected_components} components capture {(pca.variance_captured * 100).toFixed(2)}% variance
          </p>
        </div>
        <span className="text-xs font-mono tabular-nums text-teal-800 font-medium whitespace-nowrap">
          Set C ({pca.selected_components} PCs)
        </span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
        {[0, 25, 50, 75, 100].map((pct) => {
          const y = yScale(pct);
          return (
            <g key={pct}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
              <text x={pad.left - 8} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono tabular-nums">
                {pct}%
              </text>
            </g>
          );
        })}

        <line
          x1={pad.left}
          x2={width - pad.right}
          y1={yScale(95)}
          y2={yScale(95)}
          stroke="#94A3B8"
          strokeDasharray="4 4"
          strokeWidth={1}
        />

        {comps.map((c, idx) => {
          const cx = pad.left + idx * slotW + slotW / 2;
          const pct = c.explained_variance_ratio * 100;
          const yTop = yScale(pct);
          const barH = Math.max(1, pad.top + plotH - yTop);
          return (
            <g key={c.component}>
              <rect
                x={cx - barW / 2}
                y={yTop}
                width={barW}
                height={barH}
                fill={idx < pca.selected_components ? '#0F766E' : '#CBD5E1'}
                fillOpacity={0.85}
                rx={2}
              />
              <text x={cx} y={height - 14} textAnchor="middle" className="fill-slate-600 text-[10px] font-mono">
                {c.component}
              </text>
            </g>
          );
        })}

        <path d={lineD} fill="none" stroke="#D97706" strokeWidth={2.2} />
        {comps.map((c, idx) => {
          const cx = pad.left + idx * slotW + slotW / 2;
          const cy = yScale(c.cumulative_variance * 100);
          return (
            <circle
              key={`pt-${c.component}`}
              cx={cx}
              cy={cy}
              r={3.5}
              fill="#D97706"
              stroke="#FFFFFF"
              strokeWidth={1.2}
            />
          );
        })}
      </svg>
    </div>
  );
};

interface BandImportanceChartProps {
  bandSelection: Day4DatasetFeatures['band_selection'];
}

export const BandImportanceChart: React.FC<BandImportanceChartProps> = ({ bandSelection }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const rankings = bandSelection?.rankings || [];
  if (rankings.length === 0) return null;

  const width = 580;
  const height = 270;
  const pad = { top: 24, right: 20, bottom: 42, left: 48 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxRf = Math.max(1e-6, ...rankings.map((r) => r.rf_importance));
  const maxMi = Math.max(1e-6, ...rankings.map((r) => r.mutual_info));
  const yScale = (v: number) => pad.top + plotH - v * plotH;

  const isDense = rankings.length > 18;
  const slotW = plotW / rankings.length;
  const activeRank = rankings[hoveredIdx ?? 0];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Train-Only Band Selection: RF Importance &amp; Mutual Information
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Top {bandSelection.top_k} consensus wavelengths: {bandSelection.selected_wavelengths_nm.join(', ')} nm
          </p>
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

        {isDense ? (
          <>
            <path
              d={rankings
                .map((r, i) => {
                  const x = pad.left + (i / (rankings.length - 1)) * plotW;
                  const y = yScale(r.rf_importance / maxRf);
                  return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                })
                .join(' ')}
              fill="none"
              stroke="#0F766E"
              strokeWidth={2}
            />
            <path
              d={rankings
                .map((r, i) => {
                  const x = pad.left + (i / (rankings.length - 1)) * plotW;
                  const y = yScale(r.mutual_info / maxMi);
                  return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                })
                .join(' ')}
              fill="none"
              stroke="#2563EB"
              strokeWidth={1.8}
              strokeDasharray="4 3"
            />
            {rankings.map((r, i) => {
              const x = pad.left + (i / (rankings.length - 1)) * plotW;
              return (
                <g key={r.wavelength_nm}>
                  {r.selected && (
                    <line x1={x} x2={x} y1={pad.top} y2={pad.top + plotH} stroke="#D97706" strokeOpacity={0.5} strokeWidth={2} />
                  )}
                  {i % 10 === 0 && (
                    <text x={x} y={height - 14} textAnchor="middle" className="fill-slate-500 text-[10px] font-mono">
                      {r.wavelength_nm}
                    </text>
                  )}
                  <rect
                    x={x - slotW / 2}
                    y={pad.top}
                    width={slotW}
                    height={plotH}
                    fill="transparent"
                    onMouseEnter={() => setHoveredIdx(i)}
                  />
                </g>
              );
            })}
          </>
        ) : (
          rankings.map((r, i) => {
            const cx = pad.left + i * slotW + slotW / 2;
            const bw = Math.min(18, slotW * 0.34);
            const yRf = yScale(r.rf_importance / maxRf);
            const yMi = yScale(r.mutual_info / maxMi);
            return (
              <g key={r.wavelength_nm} onMouseEnter={() => setHoveredIdx(i)} className="cursor-pointer">
                {r.selected && (
                  <rect
                    x={pad.left + i * slotW + 2}
                    y={pad.top}
                    width={slotW - 4}
                    height={plotH}
                    fill="#D97706"
                    fillOpacity={0.08}
                    rx={3}
                  />
                )}
                <rect x={cx - bw - 1} y={yRf} width={bw} height={Math.max(1, pad.top + plotH - yRf)} fill="#0F766E" rx={2} />
                <rect x={cx + 1} y={yMi} width={bw} height={Math.max(1, pad.top + plotH - yMi)} fill="#2563EB" rx={2} />
                <text
                  x={cx}
                  y={height - 14}
                  textAnchor="middle"
                  className={`text-[10px] font-mono ${r.selected ? 'fill-amber-700 font-bold' : 'fill-slate-500'}`}
                >
                  {r.wavelength_nm}
                </text>
              </g>
            );
          })
        )}
      </svg>

      <div className="mt-2 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-4 text-slate-600">
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-teal-700 mr-1.5 align-middle" />
            RF Importance
          </span>
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-blue-600 mr-1.5 align-middle" />
            Mutual Info
          </span>
        </div>
        {activeRank && (
          <div className="font-mono tabular-nums text-slate-700">
            {activeRank.wavelength_nm} nm · RF {activeRank.rf_importance.toFixed(4)} · MI {activeRank.mutual_info.toFixed(4)}
            {activeRank.selected ? ' · ★ Selected' : ''}
          </div>
        )}
      </div>
    </div>
  );
};
