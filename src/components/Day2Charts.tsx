import React, { useState } from 'react';
import type { BandDiagnostic } from '../types/day1';

interface DifferenceSpectrumChartProps {
  diagnostics: BandDiagnostic[];
  comparisonPair: { healthy: string; stressed: string };
}

export const DifferenceSpectrumChart: React.FC<DifferenceSpectrumChartProps> = ({
  diagnostics,
  comparisonPair,
}) => {
  const [mode, setMode] = useState<'diff' | 'fisher'>('diff');
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!diagnostics || diagnostics.length === 0) {
    return null;
  }

  const width = 760;
  const height = 310;
  const pad = { top: 24, right: 24, bottom: 42, left: 56 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const wavelengths = diagnostics.map((d) => d.wavelength_nm);
  const minWl = Math.min(...wavelengths);
  const maxWl = Math.max(...wavelengths);

  const values = diagnostics.map((d) =>
    mode === 'diff' ? d.diff_stressed_minus_healthy : d.fisher_ratio
  );
  const minVal = mode === 'diff' ? Math.min(0, Math.floor(Math.min(...values) * 1.15)) : 0;
  const maxVal =
    mode === 'diff'
      ? Math.max(0.5, Math.ceil(Math.max(...values, 0.5) * 1.15))
      : Math.max(0.05, Math.max(...values) * 1.18);

  const xScale = (wl: number) =>
    pad.left + ((wl - minWl) / Math.max(1, maxWl - minWl)) * plotW;
  const yScale = (v: number) =>
    pad.top + plotH - ((v - minVal) / Math.max(1e-6, maxVal - minVal)) * plotH;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => minVal + t * (maxVal - minVal));
  const xTicks = wavelengths.filter((_, idx) =>
    wavelengths.length > 14 ? idx % 4 === 0 || idx === wavelengths.length - 1 : true
  );

  const redEdgeStart = xScale(Math.max(minWl, 690));
  const redEdgeEnd = xScale(Math.min(maxWl, 750));
  const nirStart = xScale(Math.max(minWl, 780));
  const nirEnd = xScale(Math.min(maxWl, 970));

  const activeIdx = hoveredIdx !== null ? hoveredIdx : Math.floor(diagnostics.length * 0.7);
  const activeBand = diagnostics[activeIdx] || diagnostics[0];

  const zeroY = yScale(0);
  const pathD = diagnostics
    .map((d, i) => {
      const val = mode === 'diff' ? d.diff_stressed_minus_healthy : d.fisher_ratio;
      return `${i === 0 ? 'M' : 'L'} ${xScale(d.wavelength_nm)} ${yScale(val)}`;
    })
    .join(' ');

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {mode === 'diff'
              ? `Difference Spectrum (${comparisonPair.stressed} − ${comparisonPair.healthy})`
              : 'Per-Band Fisher Discriminant Ratio (Separability)'}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Red edge (690–750 nm) &amp; NIR plateau (780–970 nm) shaded · Red markers = Day 3 audit bands
          </p>
        </div>

        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
          <button
            type="button"
            onClick={() => setMode('diff')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              mode === 'diff' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            ΔR (%)
          </button>
          <button
            type="button"
            onClick={() => setMode('fisher')}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              mode === 'fisher' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Fisher Ratio
          </button>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto select-none cursor-crosshair"
        onMouseLeave={() => setHoveredIdx(null)}
      >
        {/* Shaded diagnostic regions */}
        {redEdgeEnd > redEdgeStart && (
          <rect
            x={redEdgeStart}
            y={pad.top}
            width={redEdgeEnd - redEdgeStart}
            height={plotH}
            fill="#0F766E"
            fillOpacity={0.07}
          />
        )}
        {nirEnd > nirStart && (
          <rect
            x={nirStart}
            y={pad.top}
            width={nirEnd - nirStart}
            height={plotH}
            fill="#0284C7"
            fillOpacity={0.05}
          />
        )}

        {/* Gridlines */}
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
                {mode === 'diff' ? tick.toFixed(1) : tick.toFixed(3)}
              </text>
            </g>
          );
        })}

        {mode === 'diff' && minVal <= 0 && maxVal >= 0 && (
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={zeroY}
            y2={zeroY}
            stroke="#64748B"
            strokeWidth={1.1}
            strokeDasharray="4 4"
          />
        )}

        {xTicks.map((wl) => {
          const x = xScale(wl);
          return (
            <g key={wl}>
              <line x1={x} x2={x} y1={pad.top + plotH} y2={pad.top + plotH + 4} stroke="#94A3B8" strokeWidth={1} />
              <text
                x={x}
                y={height - 14}
                textAnchor="middle"
                className="fill-slate-500 text-[10px] font-mono tabular-nums"
              >
                {wl}
              </text>
            </g>
          );
        })}

        <text
          x={pad.left + plotW / 2}
          y={height - 1}
          textAnchor="middle"
          className="fill-slate-400 text-[10px] font-mono"
        >
          Wavelength (nm)
        </text>

        {mode === 'diff' ? (
          <>
            <path d={pathD} fill="none" stroke="#B45309" strokeWidth={2.25} />
            {diagnostics.map((d) => (
              <circle
                key={d.band}
                cx={xScale(d.wavelength_nm)}
                cy={yScale(d.diff_stressed_minus_healthy)}
                r={d.drop_candidate ? 4.5 : 3.5}
                fill={d.drop_candidate ? '#DC2626' : '#B45309'}
                stroke="#FFFFFF"
                strokeWidth={1.2}
              />
            ))}
          </>
        ) : (
          diagnostics.map((d) => {
            const x = xScale(d.wavelength_nm);
            const barW = Math.max(6, Math.min(24, plotW / diagnostics.length - 4));
            const yTop = yScale(d.fisher_ratio);
            return (
              <rect
                key={d.band}
                x={x - barW / 2}
                y={yTop}
                width={barW}
                height={Math.max(1, pad.top + plotH - yTop)}
                fill={d.drop_candidate ? '#DC2626' : '#0F766E'}
                fillOpacity={0.85}
                rx={2}
              />
            );
          })
        )}

        {/* Active Crosshair */}
        <line
          x1={xScale(activeBand.wavelength_nm)}
          x2={xScale(activeBand.wavelength_nm)}
          y1={pad.top}
          y2={pad.top + plotH}
          stroke="#475569"
          strokeWidth={1}
          strokeDasharray="3 3"
        />

        {diagnostics.map((d, idx) => {
          const sliceW = plotW / Math.max(1, diagnostics.length - 1);
          return (
            <rect
              key={`hit-${d.band}`}
              x={xScale(d.wavelength_nm) - sliceW / 2}
              y={pad.top}
              width={sliceW}
              height={plotH}
              fill="transparent"
              onMouseEnter={() => setHoveredIdx(idx)}
            />
          );
        })}
      </svg>

      <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-4 text-slate-600">
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-teal-700/20 border border-teal-700/40 mr-1.5 align-middle" />
            Red Edge (690–750 nm)
          </span>
          <span>
            <span className="inline-block w-2.5 h-2.5 bg-sky-600/15 border border-sky-600/40 mr-1.5 align-middle" />
            NIR Plateau (780–970 nm)
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3 font-mono tabular-nums bg-slate-50 px-3 py-1.5 rounded border border-slate-200 text-slate-700">
          <span className="font-semibold text-slate-900">
            {activeBand.wavelength_nm} nm ({activeBand.region})
          </span>
          <span>ΔR: {activeBand.diff_stressed_minus_healthy >= 0 ? '+' : ''}{activeBand.diff_stressed_minus_healthy.toFixed(2)}%</span>
          <span>J: {activeBand.fisher_ratio.toFixed(4)}</span>
          <span>d: {activeBand.cohens_d.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
};

interface OutlierHistogramChartProps {
  counts: number[];
  edges: number[];
  outlierCount: number;
}

export const OutlierHistogramChart: React.FC<OutlierHistogramChartProps> = ({
  counts,
  edges,
  outlierCount,
}) => {
  if (!counts || counts.length === 0) return null;

  const width = 520;
  const height = 210;
  const pad = { top: 20, right: 18, bottom: 36, left: 42 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxCount = Math.max(1, ...counts);
  const minEdge = edges[0] ?? -2;
  const maxEdge = edges[edges.length - 1] ?? 6;
  const cutoffX = pad.left + ((3.0 - minEdge) / Math.max(1, maxEdge - minEdge)) * plotW;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Spectral L2 Distance Robust Z-Score
          </h3>
          <p className="text-xs text-slate-500">
            {outlierCount} scans exceed robust Z &gt; 3.0 threshold
          </p>
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
        {[0, 0.5, 1].map((t) => {
          const val = Math.round(t * maxCount);
          const y = pad.top + plotH - t * plotH;
          return (
            <g key={t}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="#E2E8F0" strokeWidth={1} />
              <text x={pad.left - 6} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] font-mono tabular-nums">
                {val}
              </text>
            </g>
          );
        })}

        {counts.map((c, idx) => {
          const barW = plotW / counts.length;
          const x = pad.left + idx * barW;
          const barH = (c / maxCount) * plotH;
          const edgeMid = ((edges[idx] ?? 0) + (edges[idx + 1] ?? 0)) / 2;
          return (
            <rect
              key={idx}
              x={x + 1}
              y={pad.top + plotH - barH}
              width={Math.max(2, barW - 2)}
              height={barH}
              fill={edgeMid >= 3.0 ? '#DC2626' : '#334155'}
              fillOpacity={0.85}
            />
          );
        })}

        <line
          x1={cutoffX}
          x2={cutoffX}
          y1={pad.top}
          y2={pad.top + plotH}
          stroke="#DC2626"
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />
        <text x={cutoffX + 4} y={pad.top + 12} className="fill-rose-700 text-[10px] font-mono font-semibold">
          Z = 3.0
        </text>

        {[-2, 0, 2, 3, 4, 6].map((tick) => {
          const x = pad.left + ((tick - minEdge) / Math.max(1, maxEdge - minEdge)) * plotW;
          return (
            <text
              key={tick}
              x={x}
              y={height - 12}
              textAnchor="middle"
              className="fill-slate-500 text-[10px] font-mono tabular-nums"
            >
              {tick}
            </text>
          );
        })}
      </svg>
    </div>
  );
};
