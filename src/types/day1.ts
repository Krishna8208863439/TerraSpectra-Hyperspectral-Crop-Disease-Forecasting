export interface PackageCheck {
  module: string;
  name: string;
  min_version: string;
  installed_version: string | null;
  status: 'ok' | 'missing';
  error: string | null;
}

export interface EnvVerifyResult {
  python_version: string;
  python_executable: string;
  platform: string;
  all_ok: boolean;
  packages: PackageCheck[];
  error?: string;
}

export interface RepoDirectory {
  path: string;
  purpose: string;
  exists: boolean;
  itemCount: number;
}

export interface RepoFile {
  path: string;
  exists: boolean;
  sizeBytes: number;
}

export interface RepoStatus {
  directories: RepoDirectory[];
  files: RepoFile[];
  git: {
    initialized: boolean;
    branch: string;
    dirtyCount: number;
    commits: Array<{ hash: string; message: string; date: string }>;
  };
}

export interface SpectralPoint {
  wavelengthNm: number;
  mean: number;
  std: number;
}

export interface SpectralCurve {
  label: string;
  samples: number;
  plants: number;
  points: SpectralPoint[];
}

export interface TemporalPoint {
  date: string;
  series: Record<string, number>;
}

export interface DatasetSummary {
  datasetId: 'primary_zenodo' | 'synthetic_fallback';
  title: string;
  source: string;
  licence: string;
  fallbackTier: string;
  limitationNote: string;
  files: string[];
  shape: { rows: number; columns: number };
  designShape: { rows: number; columns: number } | null;
  uniquePlants: number;
  uniquePots: number;
  uniqueDatesCount: number;
  dateRange: string;
  groupingColumns: Array<{ name: string; role: string; splitUsage: string }>;
  labelDistribution: Array<{ label: string; count: number }>;
  genotypeDistribution: Array<{ label: string; count: number }>;
  curves: SpectralCurve[];
  temporalTrajectory: TemporalPoint[];
  sampleRows: Array<{
    sampleId: string;
    plantId: string;
    potNumber: string;
    genotype: string;
    date: string;
    label: string;
    r670: number;
    r780: number;
    ndvi: number;
    ndre: number;
  }>;
}

export interface DocItem {
  key: string;
  label: string;
  relPath: string;
  content: string;
}

export interface Day1State {
  mentorMessaged: boolean;
  scopeConfirmed: boolean;
  mentorReplyStatus: 'awaiting' | 'confirmed' | 'auto_fallback';
  progressCadence: 'daily_slack' | 'daily_github' | 'midweek_sync';
  selectedDataset: 'primary_zenodo' | 'synthetic_fallback';
  completedBlocks: number[];
  day2CompletedBlocks?: number[];
  updatedAt: string;
}

export interface BandDiagnostic {
  band: string;
  wavelength_nm: number;
  region: string;
  healthy_mean: number;
  stressed_mean: number;
  diff_stressed_minus_healthy: number;
  fisher_ratio: number;
  cohens_d: number;
  cross_sample_cv: number;
  intra_noise_ratio: number | null;
  zero_or_neg_count: number;
  saturated_count: number;
  drop_candidate: boolean;
}

export interface BandDropCandidate {
  band: string;
  wavelength_nm: number;
  region: string;
  fisher_ratio: number;
  intra_noise_ratio: number | null;
  reason: string;
}

export interface OutlierSample {
  sample_id: string;
  plant_id: string;
  date: string;
  label: string;
  l2_distance: number;
  robust_z: number;
}

export interface Day2DatasetEda {
  source: 'primary' | 'synthetic';
  sanity: {
    raw_rows: number;
    labeled_rows: number;
    unmatched_metadata_rows: number;
    n_bands: number;
    dtype: string;
    missing_spectral_values: number;
    rows_with_missing_spectra: number;
    missing_label_values: number;
    duplicate_sample_ids: number;
    exact_duplicate_spectra: number;
    wavelength_min_nm: number;
    wavelength_max_nm: number;
    wavelength_spacings_nm: number[];
    reflectance_min: number;
    reflectance_max: number;
  };
  class_balance: Array<{
    label: string;
    count: number;
    percent: number;
    plants: number;
  }>;
  imbalance_ratio: number;
  grouping: {
    unique_plants: number;
    unique_plots: number;
    unique_fields: number;
    unique_dates: number;
    scans_per_plant_min: number;
    scans_per_plant_median: number;
    scans_per_plant_mean: number;
    scans_per_plant_max: number;
    recommended_split_column: string;
    temporal_split_column: string;
  };
  class_curves: Array<{
    label: string;
    n_samples: number;
    points: Array<{ wavelength_nm: number; mean: number; std: number }>;
  }>;
  comparison_pair: { healthy: string; stressed: string };
  band_diagnostics: BandDiagnostic[];
  top_discriminative_bands: BandDiagnostic[];
  bands_to_drop_day3: BandDropCandidate[];
  red_edge_slope_pct_per_nm: Record<string, number>;
  outliers: {
    method: string;
    median_l2_distance: number;
    mad_l2_distance: number;
    outlier_count: number;
    outlier_percent: number;
    top_outliers: OutlierSample[];
    z_scores_histogram: number[];
    z_hist_edges: number[];
  };
  temporal: {
    date_count: number;
    first_date: string;
    last_date: string;
    series: Array<{
      date: string;
      classes: Record<
        string,
        { n: number; ndvi_mean: number; ndre_mean: number; r700_mean: number; r780_mean: number }
      >;
    }>;
    early_vs_late_ndvi: Record<
      string,
      { early_ndvi: number; late_ndvi: number; delta_ndvi: number }
    >;
  };
}

export interface Day2EdaPayload {
  figures: string[];
  primary: Day2DatasetEda;
  synthetic: Day2DatasetEda;
}

