import React, { useMemo, useState } from 'react';
import { Eye, EyeOff, LineChart, X } from 'lucide-react';
import type { SampleScanRow, SpectralCurve } from '../types/day1';

const TRACE_COLORS = [
  '#0F766E', // Deep Teal
  '#BE123C', // Crimson Rose
  '#D97706', // Amber
  '#0284C7', // Sky Blue
  '#6D28D9', // Violet
  '#334155', // Slate
];

const BAND_ANNOTATIONS: Record<number, string> = {
  460: 'Blue Chl-b Absorption',
  525: 'Green Reference',
  570: 'Yellow-Green Peak',
  645: 'Red Pigment Shoulder',
  670: 'Chl-a Absorption Well',
  700: 'Red-Edge Inflection',
  780: 'NIR Cell-Wall Shoulder',
  890: 'NIR Canopy Plateau',
  970: 'Leaf Water Trough',
};

function describeWavelength(nm: number): string {
  const exact = BAND_ANNOTATIONS[Math.round(nm)];
  if (exact) return exact;
  if (nm < 500) return 'Blue Absorption Band';
  if (nm < 600) return 'Green Reflectance Peak';
  if (nm < 685) return 'Chlorophyll Absorption';
  if (nm <= 750) return 'Red-Edge Transition';
  if (nm < 920) return 'NIR Mesophyll Plateau';
  return 'Water Absorption Shoulder';
}

interface SampleScanProfileChartProps {
  selectedRows: SampleScanRow[];
  referenceCurves?: SpectralCurve[];
  onRemoveRow: (sampleId: string) => void;
  onClearAll: () => void;
}

export const SampleScanProfileChart: React.FC<SampleScanProfileChartProps> = ({
  selectedRows,
  referenceCurves = [],
  onRemoveRow,
  onClearAll,
}) => {
  const [hoveredWl, setHoveredWl] = useState<number | null>(null);
  const [showClassEnvelope, setShowClassEnvelope] = useState<boolean>(true);

  const chartData = useMemo(() => {
    const minWl = 460;
    const maxWl = 970;

    // Collect distinct wavelengths across selected rows (fallback to reference curves if empty)
    const rawWls =
      selectedRows.length > 0
        ? selectedRows[0].spectrum.map((pt) => pt.wavelengthNm)
        : (referenceCurves[0]?.points || [])
            .map((p) => p.wavelengthNm)
            .filter((wl) => wl >= minWl && wl <= maxWl);

    const wavelengths = Array.from(new Set(rawWls))
      .filter((wl) => wl >= minWl && wl <= maxWl)
      .sort((a, b) => a - b);

    const filteredRefs = referenceCurves.map((c) => ({
      ...c,
      points: c.points.filter((p) => p.wavelengthNm >= minWl && p.wavelengthNm <= maxWl),
    }));

    const allReflectances: number[] = [];
    for (const row of selectedRows) {
      for (const pt of row.spectrum) {
        if (pt.wavelengthNm >= minWl && pt.wavelengthNm <= maxWl) {
          allReflectances.push(pt.reflectance);
        }
      }
    }
    if (showClassEnvelope) {
      for (const ref of filteredRefs) {
        for (const pt of ref.points) {
          allReflectances.push(pt.mean);
        }
      }
    }

    const rawMax = allReflectances.length > 0 ? Math.max(...allReflectances) : 30;
    const yMax = Math.max(25, Math.ceil((rawMax * 1.1) / 5) * 5);

    return { minWl, maxWl, wavelengths, filteredRefs, yMax };
  }, [selectedRows, referenceCurves, showClassEnvelope]);

  if (selectedRows.length === 0) {
    return (
      <div className="bg-slate-50 border border-dashed border-slate-300 rounded-lg p-6 text-center space-y-1.5">
        <div className="inline-flex items-center justify-center gap-2 text-xs font-semibold text-slate-700">
          <LineChart className="w-4 h-4 text-teal-800" />
          <span>Interactive Spectral Profile (460–970 nm)</span>
        </div>
        <p className="text-xs text-slate-500 max-w-xl mx-auto">
          Click any scan row in the table below to plot its leaf reflectance signature across 460–970 nm. Click multiple rows to overlay and compare up to 6 scans side by side.
        </p>
      </div>
    );
  }

  const width = 820;
  const height = 280;
  const pad = { top: 22, right: 24, bottom: 42, left: 52 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const { minWl, maxWl, wavelengths, filteredRefs, yMax } = chartData;

  const xScale = (wl: number) =>
    pad.left + ((wl - minWl) / Math.max(1, maxWl - minWl)) * plotW;
  const yScale = (val: number) =>
    pad.top + plotH - (Math.max(0, Math.min(yMax, val)) / Math.max(1, yMax)) * plotH;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(t * yMax));
  const xTicks =
    wavelengths.length > 14
      ? [460, 520, 570, 645, 670, 700, 780, 840, 900, 970]
      : wavelengths;

  const activeWl =
    hoveredWl !== null
      ? hoveredWl
      : wavelengths.includes(700)
        ? 700
        : wavelengths[Math.floor(wavelengths.length * 0.5)] ?? 670;

  const nearestValue = (pts: Array<{ wavelengthNm: number; reflectance: number }>, targetWl: number) => {
    if (pts.length === 0) return null;
    let best = pts[0];
    let bestDist = Math.abs(pts[0].wavelengthNm - targetWl);
    for (let i = 1; i < pts.length; i += 1) {
      const dist = Math.abs(pts[i].wavelengthNm - targetWl);
      if (dist < bestDist) {
        best = pts[i];
        bestDist = dist;
      }
    }
    return best;
  };

  return (
    <div className="bg-slate-50/70 border border-slate-200 rounded-lg p-4 space-y-3">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
            <span>460–970 nm VNIR Profile</span>
            <span aria-hidden="true">·</span>
            <span>{selectedRows.length} {selectedRows.length === 1 ? 'scan' : 'scans'} selected</span>
          </div>
          <h3 className="text-sm font-semibold text-slate-900 mt-0.5">
            Selected Sample Spectral Reflectance Curves
          </h3>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {filteredRefs.length > 0 && (
            <button
              type="button"
              onClick={() => setShowClassEnvelope((p) => !p)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white border border-slate-200 rounded-md text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              {showClassEnvelope ? <Eye className="w-3.5 h-3.5 text-teal-800" /> : <EyeOff className="w-3.5 h-3.5 text-slate-400" />}
              <span>{showClassEnvelope ? 'Class Means: On' : 'Class Means: Off'}</span>
            </button>
          )}
          <button
            type="button"
            onClick={onClearAll}
            className="px-3 py-1.5 text-xs font-medium bg-white border border-slate-200 rounded-md text-slate-600 hover:text-rose-700 hover:border-rose-200 cursor-pointer"
          >
            Clear Selection
          </button>
        </div>
      </div>

      {/* Interactive SVG Line Chart (460-970 nm) */}
      <div className="bg-white border border-slate-200 rounded-md p-3">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none cursor-crosshair"
          onMouseLeave={() => setHoveredWl(null)}
        >
          {/* Chl-a Absorption window (645-680 nm) */}
          <rect
            x={xScale(645)}
            y={pad.top}
            width={xScale(680) - xScale(645)}
            height={plotH}
            fill="#D97706"
            fillOpacity={0.05}
          />
          {/* Red-Edge transition window (690-750 nm) */}
          <rect
            x={xScale(690)}
            y={pad.top}
            width={xScale(750) - xScale(690)}
            height={plotH}
            fill="#0F766E"
            fillOpacity={0.06}
          />

          <text
            x={(xScale(690) + xScale(750)) / 2}
            y={pad.top + 12}
            textAnchor="middle"
            className="fill-teal-800/70 text-[9px] font-mono"
          >
            Red Edge
          </text>

          {/* Y Grid Lines & Labels */}
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
                  y={y + 3.5}
                  textAnchor="end"
                  className="fill-slate-500 text-[10px] font-mono tabular-nums"
                >
                  {tick}%
                </text>
              </g>
            );
          })}

          {/* X Axis Ticks (460-970 nm) */}
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
            Wavelength (nm) · 460–970 nm
          </text>

          {/* Reference Class Mean Curves (dashed subtle overlay) */}
          {showClassEnvelope &&
            filteredRefs.map((ref, idx) => {
              if (ref.points.length === 0) return null;
              const d = ref.points
                .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.wavelengthNm)} ${yScale(p.mean)}`)
                .join(' ');
              const refStroke = idx === 0 ? '#94A3B8' : '#CBD5E1';
              return (
                <path
                  key={`ref-${ref.label}`}
                  d={d}
                  fill="none"
                  stroke={refStroke}
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                />
              );
            })}

          {/* Selected Scan Row Lines */}
          {selectedRows.map((row, idx) => {
            const color = TRACE_COLORS[idx % TRACE_COLORS.length];
            const pts = row.spectrum.filter(
              (pt) => pt.wavelengthNm >= minWl && pt.wavelengthNm <= maxWl
            );
            if (pts.length === 0) return null;
            const pathD = pts
              .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.wavelengthNm)} ${yScale(p.reflectance)}`)
              .join(' ');
            const activePt = nearestValue(pts, activeWl);

            return (
              <g key={row.sampleId}>
                <path
                  d={pathD}
                  fill="none"
                  stroke={color}
                  strokeWidth={2.4}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
                {pts.length <= 14 &&
                  pts.map((p) => (
                    <circle
                      key={p.wavelengthNm}
                      cx={xScale(p.wavelengthNm)}
                      cy={yScale(p.reflectance)}
                      r={Math.abs(p.wavelengthNm - activeWl) < 1 ? 5 : 3}
                      fill={color}
                      stroke="#FFFFFF"
                      strokeWidth={1.5}
                    />
                  ))}
                {pts.length > 14 && activePt && (
                  <circle
                    cx={xScale(activePt.wavelengthNm)}
                    cy={yScale(activePt.reflectance)}
                    r={4.5}
                    fill={color}
                    stroke="#FFFFFF"
                    strokeWidth={1.5}
                  />
                )}
              </g>
            );
          })}

          {/* Active Hairline */}
          <line
            x1={xScale(activeWl)}
            x2={xScale(activeWl)}
            y1={pad.top}
            y2={pad.top + plotH}
            stroke="#475569"
            strokeWidth={1}
            strokeDasharray="3 3"
          />

          {/* Hover Capture Columns */}
          {wavelengths.map((wl) => {
            const x = xScale(wl);
            const sliceW = plotW / Math.max(1, wavelengths.length - 1);
            return (
              <rect
                key={`hover-${wl}`}
                x={x - sliceW / 2}
                y={pad.top}
                width={sliceW}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setHoveredWl(wl)}
              />
            );
          })}
        </svg>

        {/* Crosshair Readout + Selected Series Legend */}
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            {selectedRows.map((row, idx) => {
              const color = TRACE_COLORS[idx % TRACE_COLORS.length];
              return (
                <div
                  key={row.sampleId}
                  className="inline-flex items-center gap-2 bg-slate-50 border border-slate-200 rounded px-2.5 py-1"
                >
                  <span
                    className="w-2.5 h-2.5 rounded-xs shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <span className="font-mono font-semibold text-slate-800">{row.plantId}</span>
                  <span className="font-mono text-slate-500">{row.date}</span>
                  <span className="text-slate-600">({row.label.split(' ')[0]})</span>
                  <span className="font-mono text-teal-800 font-semibold">NDVI {row.ndvi.toFixed(3)}</span>
                  <button
                    type="button"
                    onClick={() => onRemoveRow(row.sampleId)}
                    className="text-slate-400 hover:text-rose-700 cursor-pointer ml-0.5"
                    aria-label={`Remove ${row.plantId} from chart`}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center gap-3 font-mono tabular-nums text-slate-700 bg-slate-50 px-3 py-1.5 rounded border border-slate-200">
            <span className="font-semibold text-slate-900">
              {activeWl} nm{' '}
              <span className="font-sans font-normal text-slate-500">
                ({describeWavelength(activeWl)})
              </span>
            </span>
            {selectedRows.map((row, idx) => {
              const color = TRACE_COLORS[idx % TRACE_COLORS.length];
              const pt = nearestValue(row.spectrum, activeWl);
              if (!pt) return null;
              return (
                <span key={row.sampleId} className="font-semibold" style={{ color }}>
                  {row.plantId}: {pt.reflectance.toFixed(2)}%
                </span>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
