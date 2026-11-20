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

export interface SampleScanRow {
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
  spectrum: Array<{ wavelengthNm: number; reflectance: number }>;
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
  sampleRows: SampleScanRow[];
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
  day3CompletedBlocks?: number[];
  day4CompletedBlocks?: number[];
  day5CompletedBlocks?: number[];
  day6CompletedBlocks?: number[];
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

export interface PreprocessingConfigDto {
  drop_bad_bands: boolean;
  drop_wavelengths: number[];
  drop_water_bands: boolean;
  clip_min: number;
  clip_max: number;
  scale_mode: 'none' | 'unit_0_1' | 'standard';
  use_savgol: boolean;
  savgol_window: number;
  savgol_polyorder: number;
  normalization: 'none' | 'snv' | 'msc';
  use_first_derivative: boolean;
}

export interface PreprocessingStepResult {
  key: string;
  label: string;
  config: PreprocessingConfigDto;
  n_bands: number;
  wavelengths_nm: number[];
  mean_fisher_ratio: number;
  max_fisher_ratio: number;
  holdout_macro_f1: number;
  class_curves: Array<{
    label: string;
    n_samples: number;
    points: Array<{ wavelength_nm: number; mean: number; std: number }>;
  }>;
}

export interface Day3DatasetPreprocessing {
  source: 'primary' | 'synthetic';
  dropped_nan_rows: number;
  manifest: {
    source: string;
    config: PreprocessingConfigDto;
    raw_labeled_rows: number;
    dropped_nan_rows: number;
    clean_rows: number;
    train_rows: number;
    test_rows: number;
    train_plants: number;
    test_plants: number;
    wavelengths_in_nm: number[];
    wavelengths_out_nm: number[];
    dropped_wavelengths_nm: number[];
    effective_savgol_window: number;
    effective_savgol_polyorder: number;
    output_npz: string;
  };
  active_metrics: Omit<PreprocessingStepResult, 'key' | 'label'>;
  ablation: PreprocessingStepResult[];
  savgol_comparison: Array<{
    name: string;
    requested_window: number;
    effective_window: number;
    effective_polyorder: number;
    mean_fisher_ratio: number;
    holdout_macro_f1: number;
    class_curves: PreprocessingStepResult['class_curves'];
  }>;
}

export interface Day3PreprocessingPayload {
  figures: string[];
  primary: Day3DatasetPreprocessing;
  synthetic: Day3DatasetPreprocessing;
}

export interface FeatureSetEntry {
  key: string;
  code: string;
  description: string;
  n_features: number;
  feature_names: string[];
  train_shape: [number, number];
  test_shape: [number, number];
  cv_macro_f1_lr: number;
  cv_macro_f1_rf: number;
  cv_roc_auc_lr: number | null;
  saved_path: string;
}

export interface BandMatchEntry {
  index_name: string;
  role: string;
  requested_nm: number;
  band_index: number;
  matched_nm: number;
  delta_nm: number;
  within_tolerance: boolean;
}

export interface Day4DatasetFeatures {
  source: 'primary' | 'synthetic';
  manifest: {
    source: string;
    dropped_nan_rows: number;
    aligned_wavelengths_nm: number[];
    band_matches: BandMatchEntry[];
    skipped_indices: Array<{ index: string; reason: string }>;
    feature_sets: FeatureSetEntry[];
  };
  pca: {
    selected_components: number;
    variance_captured: number;
    components: Array<{
      component: string;
      explained_variance_ratio: number;
      cumulative_variance: number;
    }>;
  };
  band_selection: {
    top_k: number;
    selected_wavelengths_nm: number[];
    rankings: Array<{
      wavelength_nm: number;
      rf_importance: number;
      mutual_info: number;
      consensus_score: number;
      selected: boolean;
    }>;
  };
  index_distributions: Array<{
    index: string;
    classes: Record<
      string,
      { mean: number; std: number; median: number; q25: number; q75: number }
    >;
  }>;
  mcari_citation: string;
}

export interface Day4FeaturesPayload {
  figures: string[];
  primary: Day4DatasetFeatures;
  synthetic: Day4DatasetFeatures;
}

export interface Day5ModelRun {
  model_key: string;
  model_name: string;
  feature_set_key: string;
  feature_set_code: string;
  feature_set_desc: string;
  split_scheme: string;
  class_names: string[];
  balanced_acc_mean: number;
  balanced_acc_std: number;
  macro_f1_mean: number;
  macro_f1_std: number;
  roc_auc_mean: number;
  roc_auc_std: number;
  oof_balanced_acc: number;
  oof_macro_f1: number;
  oof_roc_auc: number;
  fold_scores: {
    balanced_acc: number[];
    macro_f1: number[];
    roc_auc: number[];
  };
  per_class: Array<{
    class_name: string;
    precision: number;
    recall: number;
    f1: number;
    support: number;
  }>;
  confusion_matrix: number[][];
}

export interface Day5LeakageDemo {
  model_key: string;
  model_name: string;
  feature_set_code: string;
  feature_set_key: string;
  grouped_balanced_acc: number;
  grouped_balanced_acc_std: number;
  grouped_macro_f1: number;
  grouped_macro_f1_std: number;
  grouped_roc_auc: number;
  naive_balanced_acc: number;
  naive_balanced_acc_std: number;
  naive_macro_f1: number;
  naive_macro_f1_std: number;
  naive_roc_auc: number;
  inflation_balanced_acc: number;
  inflation_macro_f1: number;
  inflation_roc_auc: number;
  naive_confusion_matrix: number[][];
}

export interface Day5DatasetBaselines {
  source: 'primary' | 'synthetic';
  random_seed: number;
  group_col: string;
  dropped_nan_rows: number;
  clean_samples: number;
  split_manifest: {
    source: string;
    random_seed: number;
    cv_strategy: string;
    group_column: string;
    total_clean_samples: number;
    unique_groups: number;
    folds: Array<{
      fold: number;
      train_n: number;
      val_n: number;
      train_groups: number;
      val_groups: number;
      group_overlap: number;
    }>;
  };
  set_a_models: Day5ModelRun[];
  best_model_feature_sets: Day5ModelRun[];
  overall_best: Day5ModelRun;
  leakage_demonstration: Day5LeakageDemo;
}

export interface Day5BaselinesPayload {
  figures: string[];
  csv_path: string;
  primary: Day5DatasetBaselines;
  synthetic: Day5DatasetBaselines;
}

export interface ExperimentLogRow {
  run_id: string;
  timestamp: string;
  day: string;
  data_version: string;
  preprocessing: string;
  features: string;
  model: string;
  parameters: string;
  cv_scheme: string;
  balanced_acc: string;
  macro_f1: string;
  roc_auc: string;
  notes: string;
}

export interface Day6DatasetAnalysis {
  source: 'primary' | 'synthetic';
  best_baseline: {
    model_name: string;
    model_key: string;
    feature_set_code: string;
    feature_set_key: string;
    overall_error_rate_pct: number;
    total_errors: number;
    total_samples: number;
  };
  error_analysis: {
    confused_pairs: Array<{
      true_class: string;
      predicted_class: string;
      count: number;
      percent_of_errors: number;
    }>;
    spectra_comparison: Array<{
      class_name: string;
      n_total: number;
      n_correct: number;
      n_errors: number;
      points: Array<{
        wavelength_nm: number;
        true_mean: number;
        true_std: number;
        correct_mean: number;
        misclassified_mean: number;
      }>;
    }>;
    noise_vs_ambiguity: {
      correct_median_robust_z: number;
      error_median_robust_z: number;
      error_noisy_pct_z_gt_3: number;
      correct_median_centroid_margin: number;
      error_median_centroid_margin: number;
    };
    early_half_error_pct: number;
    late_half_error_pct: number;
    top_error_plants: Array<{
      plant_id: string;
      true_label: string;
      scans: number;
      errors: number;
      error_rate_pct: number;
    }>;
    by_genotype_or_field: Array<{
      field_id: string;
      scans: number;
      errors: number;
      error_rate_pct: number;
    }>;
    by_date_series: Array<{
      date: string;
      scans: number;
      errors: number;
      error_rate_pct: number;
    }>;
  };
  interpretability: {
    best_set_shap: {
      method: string;
      feature_set_key: string;
      n_eval_samples: number;
      features: Array<{
        feature: string;
        mean_abs_shap: number;
        permutation_importance: number;
        direction_corr: number;
      }>;
    };
    wavelength_shap_vs_day2: Array<{
      wavelength_nm: number;
      region: string;
      shap_importance: number;
      perm_importance: number;
      day2_fisher_ratio: number;
      day2_abs_diff_pct: number;
    }>;
    spearman_shap_vs_fisher: number;
  };
  tuning: {
    model_name: string;
    model_key: string;
    feature_set_code: string;
    untuned: {
      balanced_acc_mean: number;
      balanced_acc_std: number;
      macro_f1_mean: number;
      macro_f1_std: number;
      roc_auc_mean: number;
    };
    tuned: {
      params: Record<string, unknown>;
      balanced_acc_mean: number;
      balanced_acc_std: number;
      macro_f1_mean: number;
      macro_f1_std: number;
      roc_auc_mean: number;
      delta_macro_f1: number;
      delta_balanced_acc: number;
    };
    grid_trials: Array<{
      params: Record<string, unknown>;
      balanced_acc_mean: number;
      macro_f1_mean: number;
      roc_auc_mean: number;
    }>;
  };
  forecasting_prep: {
    window_size: number;
    default_horizon: number;
    horizons: Array<{
      feasible: boolean;
      source: string;
      window_size: number;
      horizon: number;
      n_sequences: number;
      n_features_per_window: number;
      n_plants: number;
      unique_dates: number;
      obs_per_plant: { min: number; median: number; max: number };
      models: Array<{
        key: string;
        name: string;
        mae_mean: number;
        mae_std: number;
        rmse_mean: number;
        rmse_std: number;
        r2_mean: number;
        r2_std: number;
      }>;
      sample_predictions: Array<{
        plant_id: string;
        date: string;
        actual_ndvi: number;
        persistence_ndvi: number;
        lag_ridge_ndvi: number;
        lag_rf_ndvi: number;
      }>;
    }>;
  };
}

export interface Day6ErrorAndForecastPayload {
  figures: string[];
  experiment_log_path: string;
  experiment_log_rows: ExperimentLogRow[];
  primary: Day6DatasetAnalysis;
  synthetic: Day6DatasetAnalysis;
}

export interface InferenceSamplePreset {
  sample_id: string;
  plant_id: string;
  date: string;
  true_label: string;
  field_id: string;
  split: string;
  wavelengths_nm: number[];
  raw_bands: Record<string, number>;
}

export interface InferencePlantRecord {
  plant_id: string;
  true_label: string;
  field_id: string;
  plot_id: string;
  n_scans: number;
  date_start: string;
  date_end: string;
  split: 'holdout_test' | 'train';
}

export interface InferenceSamplesPayload {
  source: 'primary' | 'synthetic';
  class_names: string[];
  wavelengths_nm: number[];
  aligned_wavelengths_nm: number[];
  holdout_plants_count: number;
  plants: InferencePlantRecord[];
  sample_presets: InferenceSamplePreset[];
}

export interface ModelPredictionVote {
  model_key: string;
  model_name: string;
  predicted_class: string;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface SpectrumPredictionResult {
  source: 'primary' | 'synthetic';
  predicted_class: string;
  confidence: number;
  ensemble_agreement: string;
  active_model: string;
  models: ModelPredictionVote[];
  vegetation_indices: Record<string, number>;
  aligned_wavelengths_nm: number[];
  reflectance_curve: Array<{ wavelength_nm: number; reflectance: number }>;
  reference_curves: Record<string, Array<{ wavelength_nm: number; mean: number; std: number }>>;
  drivers: Array<{
    feature: string;
    value: number;
    z_vs_healthy: number;
    contribution: number;
    importance: number;
  }>;
  input_wavelengths_nm: number[];
  raw_input_bands: Record<string, number>;
}

export interface CsvBatchPredictionResult {
  source: 'primary' | 'synthetic';
  model: string;
  rows_scored: number;
  total_rows_in_csv: number;
  labeled_accuracy: number | null;
  class_counts: Record<string, number>;
  mean_reflectance_curve: Array<{ wavelength_nm: number; reflectance: number }>;
  reference_curves: Record<string, Array<{ wavelength_nm: number; mean: number; std: number }>>;
  rows: Array<{
    row_index: number;
    sample_id: string;
    plant_id: string;
    date: string;
    true_label: string | null;
    predicted_class: string;
    confidence: number;
    is_correct: boolean | null;
    ndvi: number;
    ndre: number;
    rep_nm: number;
    probabilities: Record<string, number>;
  }>;
}

export interface PlantForecastResult {
  source: 'primary' | 'synthetic';
  plant_id: string;
  true_label: string;
  field_id: string;
  plot_id: string;
  split: string;
  window_size: number;
  horizon: number;
  n_timepoints: number;
  trial_duration_days: number;
  first_spectral_flag_day: number | null;
  first_ndvi_divergence_day: number | null;
  lead_time_vs_end_days: number | null;
  history: Array<{
    step: number;
    day_offset: number;
    date: string;
    actual_ndvi: number;
    healthy_cohort_ndvi: number;
    ndre: number;
    pri: number;
    rep_nm: number;
    stress_prob: number;
    lag_rf_backtest: number | null;
    lag_ridge_backtest: number | null;
  }>;
  future: Array<{
    horizon: number;
    day_offset: number;
    date: string;
    persistence_ndvi: number;
    lag_ridge_ndvi: number;
    lag_rf_ndvi: number;
    delta_from_current: number;
  }>;
}

export interface EarlyDetectionSummary {
  source: 'primary' | 'synthetic';
  holdout_scans: number;
  holdout_stressed_plants: number;
  trial_span_days: number;
  first_classifier_detection_day: number | null;
  first_ndvi_divergence_day: number | null;
  median_plant_lead_days_before_end: number;
  pct_stressed_plants_detected_early: number;
  daily_curve: Array<{
    day_num: number;
    date: string;
    healthy_ndvi: number;
    stressed_ndvi: number;
    healthy_stress_prob: number;
    stressed_stress_prob: number;
    ndvi_separation_d: number;
  }>;
}

export interface Week3ReadinessPayload {
  architectures: Array<{
    id: string;
    name: string;
    task: string;
    input_shape_primary: string;
    input_shape_synthetic: string;
    architecture: string;
    approx_params: string;
    cv_contract: string;
    comparator: string;
    status: string;
  }>;
  benchmarks: Record<
    'primary' | 'synthetic',
    {
      source: string;
      neural_mlp_results: Array<{
        model_name: string;
        feature_set: string;
        balanced_acc_mean: number;
        balanced_acc_std: number;
        macro_f1_mean: number;
        macro_f1_std: number;
        roc_auc_mean: number;
      }>;
    }
  >;
}


