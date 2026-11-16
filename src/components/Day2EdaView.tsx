import React, { useState } from 'react';
import { Check, ExternalLink, Play, RefreshCw, X } from 'lucide-react';
import { DifferenceSpectrumChart, OutlierHistogramChart } from './Day2Charts';
import { MarkdownViewer } from './MarkdownViewer';
import {
  SpectralReflectanceChart,
  TemporalTrajectoryChart,
} from './SpectralCharts';
import type { Day2DatasetEda, Day2EdaPayload, SpectralCurve, TemporalPoint } from '../types/day1';

interface Day2EdaViewProps {
  edaPayload: Day2EdaPayload | null;
  edaLoading: boolean;
  edaRunning: boolean;
  edaSource: 'primary' | 'synthetic';
  onChangeSource: (src: 'primary' | 'synthetic') => void;
  onRunEda: () => void;
  completedBlocks: number[];
  onToggleBlock: (blockId: number) => void;
  dataSummaryMarkdown: string;
  onOpenDoc: (key: string) => void;
}

const DAY2_SCHEDULE = [
  { id: 1, title: 'Unified Loader (src/data.py)', time: '1 h' },
  { id: 2, title: 'Sanity Checks & Axis Audit', time: '45 min' },
  { id: 3, title: 'Class Balance & Grouping Keys', time: '45 min' },
  { id: 4, title: 'Mean Spectra & Variance Bands', time: '1 h' },
  { id: 5, title: 'Difference Spectrum & Red Edge', time: '1 h' },
  { id: 6, title: 'Clean Notebook & Data Summary', time: '1 h' },
];

export const Day2EdaView: React.FC<Day2EdaViewProps> = ({
  edaPayload,
  edaLoading,
  edaRunning,
  edaSource,
  onChangeSource,
  onRunEda,
  completedBlocks,
  onToggleBlock,
  dataSummaryMarkdown,
  onOpenDoc,
}) => {
  const [subSection, setSubSection] = useState<'diagnostics' | 'spectral' | 'outliers' | 'figures' | 'summary'>('diagnostics');
  const [lightboxFigure, setLightboxFigure] = useState<string | null>(null);
  const [showAllBands, setShowAllBands] = useState<boolean>(false);

  const activeData: Day2DatasetEda | null = edaPayload
    ? edaSource === 'synthetic'
      ? edaPayload.synthetic
      : edaPayload.primary
    : null;

  if (edaLoading && !activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-sm text-slate-500">
        Running Python Day 2 EDA via <code className="font-mono">src/pipeline/run_day2_eda.py</code>...
      </div>
    );
  }

  if (!activeData) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-8 flex flex-col items-center justify-center gap-4 text-center">
        <div className="text-sm font-medium text-slate-800">
          Day 2 EDA metrics have not been generated yet.
        </div>
        <button
          type="button"
          onClick={onRunEda}
          disabled={edaRunning}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 cursor-pointer"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run Day 2 EDA Script</span>
        </button>
      </div>
    );
  }

  const curvesForChart: SpectralCurve[] = activeData.class_curves.map((c) => ({
    label: c.label,
    samples: c.n_samples,
    plants: 0,
    points: (activeData.band_diagnostics.length > 20
      ? c.points.filter((_, i) => i % 2 === 0)
      : c.points
    ).map((p) => ({
      wavelengthNm: p.wavelength_nm,
      mean: p.mean,
      std: p.std,
    })),
  }));

  const trajectoryForChart: TemporalPoint[] = activeData.temporal.series.map((pt) => {
    const series: Record<string, number> = {};
    for (const [cls, stats] of Object.entries(pt.classes)) {
      series[cls] = stats.ndvi_mean;
    }
    return { date: pt.date, series };
  });

  const displayedDiagnostics =
    activeData.band_diagnostics.length > 16 && !showAllBands
      ? activeData.band_diagnostics.filter((_, idx) => idx % 5 === 0 || activeData.band_diagnostics[idx].drop_candidate)
      : activeData.band_diagnostics;

  return (
    <div className="space-y-6">
      {/* Control & Schedule Strip */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span>Day 2</span>
              <span aria-hidden="true">·</span>
              <span>Tue 17 Nov</span>
              <span aria-hidden="true">·</span>
              <span>Data Loading &amp; EDA</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Spectral Sanity Checks, Discriminability &amp; Band Audit
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
              <button
                type="button"
                onClick={() => onChangeSource('primary')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  edaSource === 'primary' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                }`}
              >
                Primary (Zenodo 22755812)
              </button>
              <button
                type="button"
                onClick={() => onChangeSource('synthetic')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  edaSource === 'synthetic' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                }`}
              >
                Synthetic (400–1000 nm)
              </button>
            </div>

            <button
              type="button"
              onClick={onRunEda}
              disabled={edaRunning}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded-lg hover:bg-teal-900 disabled:opacity-60 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${edaRunning ? 'animate-spin' : ''}`} />
              <span>{edaRunning ? 'Running Python EDA...' : 'Rerun Python EDA'}</span>
            </button>
          </div>
        </div>

        {/* Interactive Day 2 6-block checklist strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-4 border-t border-slate-100">
          {DAY2_SCHEDULE.map((blk) => {
            const done = completedBlocks.includes(blk.id);
            return (
              <button
                key={blk.id}
                type="button"
                onClick={() => onToggleBlock(blk.id)}
                className={`text-left p-2.5 rounded-md border transition-colors cursor-pointer ${
                  done
                    ? 'bg-slate-50 border-slate-200 text-slate-900'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
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

        {/* Sub-section segmented bar */}
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg w-fit">
          {[
            { id: 'diagnostics', label: '1. Sanity & Grouping' },
            { id: 'spectral', label: '2. Spectra & Red Edge' },
            { id: 'outliers', label: '3. Outliers & Drop List' },
            { id: 'figures', label: '4. Saved Figures (4)' },
            { id: 'summary', label: '5. Data Summary' },
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

      {/* SECTION 1: SANITY CHECKS, CLASS BALANCE & GROUPING */}
      {subSection === 'diagnostics' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">
                Block 2 Sanity Checks (<code className="font-mono text-xs">src/data.py</code>)
              </h3>
              <span className="text-xs font-mono text-teal-800 font-medium">
                ● Verified from Python output
              </span>
            </div>

            <div className="border border-slate-200 rounded-md overflow-hidden">
              <table className="w-full text-left border-collapse text-xs">
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="px-3.5 py-2.5 text-slate-500">Raw vs. Labeled Matrix Shape</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right text-slate-900 font-medium">
                      {activeData.sanity.raw_rows.toLocaleString()} raw →{' '}
                      {activeData.sanity.labeled_rows.toLocaleString()} × {activeData.sanity.n_bands} ({activeData.sanity.dtype})
                    </td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2.5 text-slate-500">Unmatched Metadata Rows</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right text-amber-700 font-medium">
                      {activeData.sanity.unmatched_metadata_rows}{' '}
                      {activeData.sanity.unmatched_metadata_rows > 0 ? '(PlantId_78 excluded)' : '(none)'}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2.5 text-slate-500">Missing Values (Spectra / Labels)</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right text-teal-800 font-medium">
                      {activeData.sanity.missing_spectral_values} / {activeData.sanity.missing_label_values}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2.5 text-slate-500">Duplicates (Sample_ID / Exact Spectra)</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right text-slate-900">
                      {activeData.sanity.duplicate_sample_ids} / {activeData.sanity.exact_duplicate_spectra}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2.5 text-slate-500">Wavelength Axis Range</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right text-slate-900">
                      {activeData.sanity.wavelength_min_nm}–{activeData.sanity.wavelength_max_nm} nm
                    </td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2.5 text-slate-500">Band Spacing (Δλ)</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right text-slate-700">
                      {activeData.sanity.wavelength_spacings_nm.join(', ')} nm
                    </td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2.5 text-slate-500">Reflectance Value Bounds</td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right text-slate-900">
                      {activeData.sanity.reflectance_min.toFixed(2)}% to {activeData.sanity.reflectance_max.toFixed(2)}%
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">Block 3 Class Balance</h3>
                <span className="text-xs font-mono tabular-nums text-slate-500">
                  Ratio {activeData.imbalance_ratio}:1
                </span>
              </div>
              <div className="space-y-3">
                {activeData.class_balance.map((cls) => (
                  <div key={cls.label} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-800">{cls.label}</span>
                      <span className="font-mono tabular-nums text-slate-600">
                        {cls.count.toLocaleString()} ({cls.percent}%) · {cls.plants} plants
                      </span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-teal-700 rounded-full" style={{ width: `${cls.percent}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
              <h3 className="text-sm font-semibold text-slate-900">
                Grouping Hierarchy &amp; Split Key
              </h3>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
                  <div className="text-slate-500">Unique Plants</div>
                  <div className="text-lg font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                    {activeData.grouping.unique_plants}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
                  <div className="text-slate-500">Unique Dates</div>
                  <div className="text-lg font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                    {activeData.grouping.unique_dates}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
                  <div className="text-slate-500">Pots / Genotypes</div>
                  <div className="text-sm font-bold font-mono tabular-nums text-slate-900 mt-1">
                    {activeData.grouping.unique_plots} pots · {activeData.grouping.unique_fields} fields
                  </div>
                </div>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
                  <div className="text-slate-500">Scans / Plant</div>
                  <div className="text-sm font-bold font-mono tabular-nums text-slate-900 mt-1">
                    {activeData.grouping.scans_per_plant_min}–{activeData.grouping.scans_per_plant_max} (med {activeData.grouping.scans_per_plant_median})
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-600 pt-1">
                Primary leak-free CV key:{' '}
                <code className="font-mono font-semibold text-teal-800">
                  {activeData.grouping.recommended_split_column}
                </code>{' '}
                · Temporal holdout key:{' '}
                <code className="font-mono font-semibold text-teal-800">
                  {activeData.grouping.temporal_split_column}
                </code>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: MEAN SPECTRA, DIFFERENCE SPECTRUM & RED EDGE */}
      {subSection === 'spectral' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <SpectralReflectanceChart curves={curvesForChart} />
            <DifferenceSpectrumChart
              diagnostics={activeData.band_diagnostics}
              comparisonPair={activeData.comparison_pair}
            />
          </div>

          {/* Temporal Progression */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-8">
              <TemporalTrajectoryChart
                trajectory={trajectoryForChart}
                labels={activeData.class_curves.map((c) => c.label)}
              />
            </div>
            <div className="lg:col-span-4 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
              <h3 className="text-sm font-semibold text-slate-900">
                Red-Edge Slope &amp; Temporal Shift
              </h3>
              <div className="space-y-2.5 text-xs">
                <div className="text-slate-500 font-medium">Red-Edge Slope (700 → 780 nm)</div>
                {Object.entries(activeData.red_edge_slope_pct_per_nm).map(([cls, slope]) => (
                  <div key={cls} className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-700">{cls}</span>
                    <span className="font-mono tabular-nums font-semibold text-slate-900">
                      {slope.toFixed(4)} %/nm
                    </span>
                  </div>
                ))}
              </div>
              <div className="space-y-2 text-xs pt-2">
                <div className="text-slate-500 font-medium">
                  Early vs. Late Date NDVI ({activeData.temporal.first_date} → {activeData.temporal.last_date})
                </div>
                {Object.entries(activeData.temporal.early_vs_late_ndvi).map(([cls, stats]) => (
                  <div key={cls} className="p-2.5 bg-slate-50 border border-slate-200 rounded-md">
                    <div className="font-medium text-slate-800">{cls}</div>
                    <div className="font-mono tabular-nums text-slate-600 mt-1">
                      {stats.early_ndvi.toFixed(3)} → {stats.late_ndvi.toFixed(3)} (
                      <span className={stats.delta_ndvi < 0 ? 'text-amber-700' : 'text-teal-800'}>
                        {stats.delta_ndvi >= 0 ? '+' : ''}
                        {stats.delta_ndvi.toFixed(4)}
                      </span>
                      )
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Per-Band Discriminability Table */}
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Per-Band Discriminability &amp; Noise Diagnostics
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Sorted along wavelength axis · Highlights discriminative Red-Edge / NIR bands and Day 3 drop candidates
                </p>
              </div>
              {activeData.band_diagnostics.length > 16 && (
                <button
                  type="button"
                  onClick={() => setShowAllBands((p) => !p)}
                  className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer"
                >
                  {showAllBands ? 'Show Sampled Bands' : `Show All ${activeData.band_diagnostics.length} Bands`}
                </button>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-3 py-2.5 font-medium">Band</th>
                    <th className="px-3 py-2.5 font-medium">Region</th>
                    <th className="px-3 py-2.5 font-medium text-right">Healthy</th>
                    <th className="px-3 py-2.5 font-medium text-right">Stressed</th>
                    <th className="px-3 py-2.5 font-medium text-right">ΔR (%)</th>
                    <th className="px-3 py-2.5 font-medium text-right">Fisher J</th>
                    <th className="px-3 py-2.5 font-medium text-right">Cohen d</th>
                    <th className="px-3 py-2.5 font-medium text-right">Intra Noise</th>
                    <th className="px-3 py-2.5 font-medium text-right">Day 3 Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                  {displayedDiagnostics.map((b) => (
                    <tr key={b.band} className={b.drop_candidate ? 'bg-rose-50/40' : 'hover:bg-slate-50/60'}>
                      <td className="px-3 py-2 font-semibold text-slate-900">{b.band}</td>
                      <td className="px-3 py-2 font-sans text-slate-600">{b.region}</td>
                      <td className="px-3 py-2 text-right text-slate-700">{b.healthy_mean.toFixed(2)}%</td>
                      <td className="px-3 py-2 text-right text-slate-700">{b.stressed_mean.toFixed(2)}%</td>
                      <td className="px-3 py-2 text-right text-slate-800">
                        {b.diff_stressed_minus_healthy >= 0 ? '+' : ''}
                        {b.diff_stressed_minus_healthy.toFixed(2)}%
                      </td>
                      <td className="px-3 py-2 text-right font-semibold text-teal-800">
                        {b.fisher_ratio.toFixed(4)}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-700">
                        {b.cohens_d >= 0 ? '+' : ''}
                        {b.cohens_d.toFixed(3)}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-600">
                        {b.intra_noise_ratio !== null ? b.intra_noise_ratio.toFixed(3) : b.cross_sample_cv.toFixed(3)}
                      </td>
                      <td
                        className={`px-3 py-2 text-right font-sans font-medium ${
                          b.drop_candidate ? 'text-rose-700' : 'text-teal-800'
                        }`}
                      >
                        {b.drop_candidate ? '▲ Drop / Audit' : 'Keep'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: OUTLIER SPECTRA & DAY 3 BAND DROP LIST */}
      {subSection === 'outliers' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-6 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Done-When #3: Bands Flagged to Drop on Day 3
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Spectrum edge bands and water-absorption shoulder channels identified for Day 3 ablation
                </p>
              </div>
              <div className="space-y-3">
                {activeData.bands_to_drop_day3.map((d) => (
                  <div key={d.band} className="p-3.5 bg-slate-50 border border-slate-200 rounded-md space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono font-semibold text-rose-700">
                        {d.band} ({d.wavelength_nm} nm · {d.region})
                      </span>
                      <span className="font-mono tabular-nums text-slate-500">
                        Fisher J = {d.fisher_ratio.toFixed(4)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{d.reason}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:col-span-6">
              <OutlierHistogramChart
                counts={activeData.outliers.z_scores_histogram}
                edges={activeData.outliers.z_hist_edges}
                outlierCount={activeData.outliers.outlier_count}
              />
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Flagged Outlier Spectra (Top {activeData.outliers.top_outliers.length} of{' '}
                  {activeData.outliers.outlier_count})
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {activeData.outliers.method} · Median L2 = {activeData.outliers.median_l2_distance} · MAD ={' '}
                  {activeData.outliers.mad_l2_distance}
                </p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="px-3 py-2.5 font-medium">Sample ID</th>
                    <th className="px-3 py-2.5 font-medium">Plant ID</th>
                    <th className="px-3 py-2.5 font-medium">Date</th>
                    <th className="px-3 py-2.5 font-medium">Label</th>
                    <th className="px-3 py-2.5 font-medium text-right">L2 Distance</th>
                    <th className="px-3 py-2.5 font-medium text-right">Robust Z</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                  {activeData.outliers.top_outliers.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-6 text-center text-slate-500 font-sans">
                        No spectral scans exceed the robust Z &gt; 3.0 threshold.
                      </td>
                    </tr>
                  ) : (
                    activeData.outliers.top_outliers.map((out) => (
                      <tr key={out.sample_id} className="hover:bg-slate-50/70">
                        <td className="px-3 py-2 text-slate-800">{out.sample_id}</td>
                        <td className="px-3 py-2 font-semibold text-slate-900">{out.plant_id}</td>
                        <td className="px-3 py-2 text-slate-600">{out.date}</td>
                        <td className="px-3 py-2 font-sans text-slate-700">{out.label}</td>
                        <td className="px-3 py-2 text-right text-slate-700">{out.l2_distance.toFixed(2)}</td>
                        <td className="px-3 py-2 text-right font-semibold text-rose-700">
                          {out.robust_z.toFixed(2)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 4: SAVED MATPLOTLIB FIGURES */}
      {subSection === 'figures' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-600">
              High-DPI figures generated directly by Matplotlib into{' '}
              <code className="font-mono">reports/figures/</code>. Click any figure to inspect full size.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {(edaPayload?.figures || []).map((figPath) => {
              const filename = figPath.split('/').pop() || figPath;
              const imgUrl = `/api/figures/${filename}?t=${encodeURIComponent(filename)}`;
              return (
                <div
                  key={figPath}
                  className="bg-white border border-slate-200 rounded-lg overflow-hidden"
                >
                  <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2">
                    <span className="text-xs font-mono font-medium text-slate-800 truncate">
                      {figPath}
                    </span>
                    <button
                      type="button"
                      onClick={() => setLightboxFigure(imgUrl)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-teal-800 hover:underline shrink-0 cursor-pointer"
                    >
                      <span>Expand</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLightboxFigure(imgUrl)}
                    className="block w-full bg-white p-3 cursor-pointer"
                  >
                    <img
                      src={imgUrl}
                      alt={filename}
                      referrerPolicy="no-referrer"
                      className="w-full h-auto object-contain rounded"
                    />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SECTION 5: HALF-PAGE DATA SUMMARY */}
      {subSection === 'summary' && (
        <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <div className="text-xs font-mono text-slate-500">docs/data_summary.md</div>
              <h3 className="text-base font-bold text-slate-900 mt-0.5">
                Reproducible Half-Page Data Summary
              </h3>
            </div>
            <button
              type="button"
              onClick={() => onOpenDoc('data_summary')}
              className="px-3.5 py-2 text-xs font-medium border border-slate-300 rounded-md hover:bg-slate-50 text-slate-800 cursor-pointer"
            >
              Open in Docs Editor
            </button>
          </div>
          <MarkdownViewer content={dataSummaryMarkdown} />
        </div>
      )}

      {/* Lightbox Modal for Matplotlib Figures */}
      {lightboxFigure && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/75 flex items-center justify-center p-6"
          onClick={() => setLightboxFigure(null)}
        >
          <div
            className="bg-white rounded-lg max-w-4xl w-full p-4 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-700">
                {lightboxFigure.split('?')[0]}
              </span>
              <button
                type="button"
                onClick={() => setLightboxFigure(null)}
                className="p-1.5 text-slate-500 hover:text-slate-900 rounded cursor-pointer"
                aria-label="Close figure preview"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <img
              src={lightboxFigure}
              alt="Expanded EDA figure"
              referrerPolicy="no-referrer"
              className="w-full h-auto rounded border border-slate-100"
            />
          </div>
        </div>
      )}
    </div>
  );
};
