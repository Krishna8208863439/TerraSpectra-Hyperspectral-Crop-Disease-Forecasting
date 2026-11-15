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
  updatedAt: string;
}
