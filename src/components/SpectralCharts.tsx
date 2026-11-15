import React, { useState } from 'react';
import type { SpectralCurve, TemporalPoint } from '../types/day1';

const SERIES_COLORS = [
  { stroke: '#0F766E', fill: '#0F766E', dash: undefined },
  { stroke: '#D97706', fill: '#D97706', dash: '6 4' },
  { stroke: '#0284C7', fill: '#0284C7', dash: '3 3' },
  { stroke: '#DC2626', fill: '#DC2626', dash: '8 3 2 3' },
];

interface SpectralReflectanceChartProps {
  curves: SpectralCurve[];
}

export const SpectralReflectanceChart: React.FC<SpectralReflectanceChartProps> = ({ curves }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [showBands, setShowBands] = useState(true);

  if (!curves || curves.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center border border-slate-200 rounded-lg bg-slate-50 text-sm text-slate-500">
        No spectral bands available for the selected dataset.
      </div>
    );
  }

  const width = 760;
  const height = 310;
  const pad = { top: 24, right: 24, bottom: 42, left: 52 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const wavelengths = curves[0].points.map((p) => p.wavelengthNm);
  const minWl = Math.min(...wavelengths);
  const maxWl = Math.max(...wavelengths);

  const allValues = curves.flatMap((c) =>
    c.points.map((p) => (showBands ? p.mean + p.std : p.mean))
  );
  const yMax = Math.max(20, Math.ceil(Math.max(...allValues) / 10) * 10);
  const yMin = 0;

  const xScale = (wl: number) =>
    pad.left + ((wl - minWl) / Math.max(1, maxWl - minWl)) * plotW;
  const yScale = (val: number) =>
    pad.top + plotH - ((val - yMin) / Math.max(1, yMax - yMin)) * plotH;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(yMin + t * (yMax - yMin)));
  const xTicks = wavelengths.filter((_, idx) =>
    wavelengths.length > 14 ? idx % 4 === 0 || idx === wavelengths.length - 1 : true
  );

  const activeIdx = hoveredIdx !== null ? hoveredIdx : Math.floor(wavelengths.length * 0.65);
  const activeWl = wavelengths[activeIdx];
  const redEdgeStart = xScale(Math.max(minWl, 680));
  const redEdgeEnd = xScale(Math.min(maxWl, 750));

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Mean Leaf &amp; Canopy Spectral Signature
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Reflectance (%) across {minWl}–{maxWl} nm · Red-edge transition shaded at 680–750 nm
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setShowBands((prev) => !prev)}
            className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
          >
            {showBands ? 'Hide ±1 SD Band' : 'Show ±1 SD Band'}
          </button>
        </div>
      </div>

      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none cursor-crosshair"
          onMouseLeave={() => setHoveredIdx(null)}
        >
          {/* Red-edge highlight band */}
          {redEdgeEnd > redEdgeStart && (
            <rect
              x={redEdgeStart}
              y={pad.top}
              width={redEdgeEnd - redEdgeStart}
              height={plotH}
              fill="#0F766E"
              fillOpacity={0.05}
            />
          )}

          {/* Horizontal Grid & Y Axis */}
          {yTicks.map((tick) => {
            const y = yScale(tick);
            return (
              <g key={tick}>
                <line
                  x1={pad.left}
                  x2={width - pad.right}
                  y1={y}
                  y2={y}
                  stroke="#E2E8F0"
                  strokeWidth={1}
                />
                <text
                  x={pad.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="fill-slate-500 text-[10px] font-mono tabular-nums"
                >
                  {tick}%
                </text>
              </g>
            );
          })}

          {/* X Axis Ticks */}
          {xTicks.map((wl) => {
            const x = xScale(wl);
            return (
              <g key={wl}>
                <line
                  x1={x}
                  x2={x}
                  y1={pad.top + plotH}
                  y2={pad.top + plotH + 4}
                  stroke="#94A3B8"
                  strokeWidth={1}
                />
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

          {/* ±1 SD Envelopes */}
          {showBands &&
            curves.map((curve, cIdx) => {
              const color = SERIES_COLORS[cIdx % SERIES_COLORS.length];
              const upper = curve.points
                .map((p) => `${xScale(p.wavelengthNm)},${yScale(p.mean + p.std)}`)
                .join(' ');
              const lower = [...curve.points]
                .reverse()
                .map((p) => `${xScale(p.wavelengthNm)},${yScale(Math.max(0, p.mean - p.std))}`)
                .join(' ');
              return (
                <polygon
                  key={`band-${curve.label}`}
                  points={`${upper} ${lower}`}
                  fill={color.fill}
                  fillOpacity={0.1}
                />
              );
            })}

          {/* Mean Curves */}
          {curves.map((curve, cIdx) => {
            const color = SERIES_COLORS[cIdx % SERIES_COLORS.length];
            const pathD = curve.points
              .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.wavelengthNm)} ${yScale(p.mean)}`)
              .join(' ');
            const activePt = curve.points[activeIdx];
            return (
              <g key={curve.label}>
                <path
                  d={pathD}
                  fill="none"
                  stroke={color.stroke}
                  strokeWidth={2.25}
                  strokeDasharray={color.dash}
                />
                {activePt && (
                  <circle
                    cx={xScale(activePt.wavelengthNm)}
                    cy={yScale(activePt.mean)}
                    r={4}
                    fill={color.stroke}
                    stroke="#FFFFFF"
                    strokeWidth={1.5}
                  />
                )}
              </g>
            );
          })}

          {/* Active Hairline */}
          {activeWl !== undefined && (
            <line
              x1={xScale(activeWl)}
              x2={xScale(activeWl)}
              y1={pad.top}
              y2={pad.top + plotH}
              stroke="#475569"
              strokeWidth={1}
              strokeDasharray="3 3"
            />
          )}

          {/* Hover capture columns */}
          {wavelengths.map((wl, idx) => {
            const x = xScale(wl);
            const sliceW = plotW / Math.max(1, wavelengths.length - 1);
            return (
              <rect
                key={`hit-${wl}`}
                x={x - sliceW / 2}
                y={pad.top}
                width={sliceW}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setHoveredIdx(idx)}
              />
            );
          })}
        </svg>

        {/* Legend & Crosshair Readout */}
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex flex-wrap items-center gap-5">
            {curves.map((curve, idx) => {
              const color = SERIES_COLORS[idx % SERIES_COLORS.length];
              return (
                <div key={curve.label} className="flex items-center gap-2">
                  <span
                    className="inline-block w-4 h-0.5"
                    style={{
                      backgroundColor: color.stroke,
                      borderBottom: color.dash ? `2px dashed ${color.stroke}` : undefined,
                    }}
                  />
                  <span className="font-medium text-slate-800">{curve.label}</span>
                  <span className="text-slate-400 font-mono tabular-nums">
                    (n={curve.samples})
                  </span>
                </div>
              );
            })}
          </div>

          {activeWl !== undefined && (
            <div className="flex flex-wrap items-center gap-3 font-mono tabular-nums text-slate-700 bg-slate-50 px-3 py-1.5 rounded border border-slate-200">
              <span className="font-semibold text-slate-900">{activeWl} nm</span>
              {curves.map((c, idx) => {
                const pt = c.points[activeIdx];
                if (!pt) return null;
                const color = SERIES_COLORS[idx % SERIES_COLORS.length];
                return (
                  <span key={c.label} style={{ color: color.stroke }}>
                    {pt.mean.toFixed(2)}% ±{pt.std.toFixed(1)}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface TemporalTrajectoryChartProps {
  trajectory: TemporalPoint[];
  labels: string[];
}

export const TemporalTrajectoryChart: React.FC<TemporalTrajectoryChartProps> = ({
  trajectory,
  labels,
}) => {
  const [hoveredDateIdx, setHoveredDateIdx] = useState<number | null>(null);

  if (!trajectory || trajectory.length === 0 || labels.length === 0) {
    return null;
  }

  const width = 760;
  const height = 240;
  const pad = { top: 20, right: 24, bottom: 38, left: 52 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const vals = trajectory.flatMap((t) => labels.map((l) => t.series[l]).filter((v) => v !== undefined));
  const minVal = Math.max(0, Math.floor((Math.min(...vals) - 0.05) * 20) / 20);
  const maxVal = Math.min(1, Math.ceil((Math.max(...vals) + 0.05) * 20) / 20);

  const xScale = (idx: number) =>
    pad.left + (idx / Math.max(1, trajectory.length - 1)) * plotW;
  const yScale = (v: number) =>
    pad.top + plotH - ((v - minVal) / Math.max(0.01, maxVal - minVal)) * plotH;

  const yTicks = [0, 0.5, 1].map((t) => minVal + t * (maxVal - minVal));
  const activeIdx = hoveredDateIdx !== null ? hoveredDateIdx : trajectory.length - 1;
  const activePoint = trajectory[activeIdx];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Temporal NDVI Trajectory Across Acquisition Dates
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Normalized Difference Vegetation Index (780 nm / 670 nm) supporting Day 6 temporal forecast
          </p>
        </div>
        {activePoint && (
          <div className="flex items-center gap-3 font-mono tabular-nums text-xs bg-slate-50 px-3 py-1.5 rounded border border-slate-200">
            <span className="font-semibold text-slate-900">{activePoint.date}</span>
            {labels.map((label, idx) => {
              const val = activePoint.series[label];
              if (val === undefined) return null;
              const color = SERIES_COLORS[idx % SERIES_COLORS.length];
              return (
                <span key={label} style={{ color: color.stroke }}>
                  {val.toFixed(3)}
                </span>
              );
            })}
          </div>
        )}
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto select-none cursor-crosshair"
        onMouseLeave={() => setHoveredDateIdx(null)}
      >
        {yTicks.map((tick) => {
          const y = yScale(tick);
          return (
            <g key={tick}>
              <line
                x1={pad.left}
                x2={width - pad.right}
                y1={y}
                y2={y}
                stroke="#E2E8F0"
                strokeWidth={1}
              />
              <text
                x={pad.left - 8}
                y={y + 4}
                textAnchor="end"
                className="fill-slate-500 text-[10px] font-mono tabular-nums"
              >
                {tick.toFixed(2)}
              </text>
            </g>
          );
        })}

        {trajectory.map((pt, idx) => {
          const showLabel =
            trajectory.length <= 8 ||
            idx === 0 ||
            idx === trajectory.length - 1 ||
            idx % Math.ceil(trajectory.length / 6) === 0;
          if (!showLabel) return null;
          return (
            <text
              key={pt.date}
              x={xScale(idx)}
              y={height - 12}
              textAnchor="middle"
              className="fill-slate-500 text-[10px] font-mono tabular-nums"
            >
              {pt.date}
            </text>
          );
        })}

        {labels.map((label, lIdx) => {
          const color = SERIES_COLORS[lIdx % SERIES_COLORS.length];
          const pts = trajectory
            .map((t, idx) => (t.series[label] !== undefined ? { idx, val: t.series[label] } : null))
            .filter((x): x is { idx: number; val: number } => x !== null);
          if (pts.length === 0) return null;
          const d = pts
            .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.idx)} ${yScale(p.val)}`)
            .join(' ');
          const activeV = activePoint?.series[label];
          return (
            <g key={label}>
              <path
                d={d}
                fill="none"
                stroke={color.stroke}
                strokeWidth={2}
                strokeDasharray={color.dash}
              />
              {activeV !== undefined && (
                <circle
                  cx={xScale(activeIdx)}
                  cy={yScale(activeV)}
                  r={3.5}
                  fill={color.stroke}
                  stroke="#FFFFFF"
                  strokeWidth={1.5}
                />
              )}
            </g>
          );
        })}

        <line
          x1={xScale(activeIdx)}
          x2={xScale(activeIdx)}
          y1={pad.top}
          y2={pad.top + plotH}
          stroke="#475569"
          strokeWidth={1}
          strokeDasharray="3 3"
        />

        {trajectory.map((pt, idx) => {
          const sliceW = plotW / Math.max(1, trajectory.length - 1);
          return (
            <rect
              key={`t-hit-${pt.date}`}
              x={xScale(idx) - sliceW / 2}
              y={pad.top}
              width={sliceW}
              height={plotH}
              fill="transparent"
              onMouseEnter={() => setHoveredDateIdx(idx)}
            />
          );
        })}
      </svg>
    </div>
  );
};
