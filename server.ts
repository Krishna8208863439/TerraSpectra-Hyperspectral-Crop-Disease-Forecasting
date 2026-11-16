import express from 'express';
import { execFile } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const ROOT_DIR = process.cwd();
const PORT = Number(process.env.PORT || 3000);

const DOC_FILES: Record<string, { label: string; relPath: string }> = {
  project_brief: { label: 'One-Page Project Brief', relPath: 'docs/project_brief.md' },
  data_summary: { label: 'Day 2 Data Summary', relPath: 'docs/data_summary.md' },
  dataset_note: { label: 'Dataset Decision Note', relPath: 'docs/dataset_note.md' },
  mentor_message: { label: 'Mentor Scope Message', relPath: 'docs/mentor_message.md' },
  readme: { label: 'Repository README', relPath: 'README.md' },
  data_loader: { label: 'Day 2 Loader (src/data.py)', relPath: 'src/data.py' },
  requirements: { label: 'Python Requirements', relPath: 'requirements.txt' },
  verify_env: { label: 'Env Verification Script', relPath: 'src/pipeline/verify_env.py' },
};

const STATE_FILE = path.join(ROOT_DIR, 'reports', 'day1_state.json');

interface Day1State {
  mentorMessaged: boolean;
  scopeConfirmed: boolean;
  mentorReplyStatus: 'awaiting' | 'confirmed' | 'auto_fallback';
  progressCadence: 'daily_slack' | 'daily_github' | 'midweek_sync';
  selectedDataset: 'primary_zenodo' | 'synthetic_fallback';
  completedBlocks: number[];
  day2CompletedBlocks: number[];
  updatedAt: string;
}

const DEFAULT_STATE: Day1State = {
  mentorMessaged: true,
  scopeConfirmed: true,
  mentorReplyStatus: 'awaiting',
  progressCadence: 'daily_slack',
  selectedDataset: 'primary_zenodo',
  completedBlocks: [1, 2, 3, 4, 5, 6],
  day2CompletedBlocks: [1, 2, 3, 4, 5, 6],
  updatedAt: new Date().toISOString(),
};

function readDay1State(): Day1State {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const raw = fs.readFileSync(STATE_FILE, 'utf-8');
      return { ...DEFAULT_STATE, ...JSON.parse(raw) };
    }
  } catch {
    // Fall back to default state if corrupted
  }
  return DEFAULT_STATE;
}

function writeDay1State(nextState: Day1State): Day1State {
  fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
  const payload = { ...nextState, updatedAt: new Date().toISOString() };
  fs.writeFileSync(STATE_FILE, JSON.stringify(payload, null, 2), 'utf-8');
  return payload;
}

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      inQuotes = !inQuotes;
    } else if (ch === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  result.push(current.trim());
  return result;
}

function parseCsvFile(filePath: string): { headers: string[]; rows: Record<string, string>[] } {
  const raw = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, '');
  const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };
  const headers = parseCsvLine(lines[0]);
  const rows: Record<string, string>[] = [];
  for (let i = 1; i < lines.length; i += 1) {
    const cols = parseCsvLine(lines[i]);
    const row: Record<string, string> = {};
    for (let j = 0; j < headers.length; j += 1) {
      row[headers[j]] = cols[j] ?? '';
    }
    rows.push(row);
  }
  return { headers, rows };
}

function summarizePrimaryDataset() {
  const designPath = path.join(ROOT_DIR, 'data', 'raw', 'experimental_design.csv');
  const spectraPath = path.join(ROOT_DIR, 'data', 'raw', 'Multispectral_Reflectance.csv');
  const design = parseCsvFile(designPath);
  const spectra = parseCsvFile(spectraPath);

  const designMap = new Map<string, Record<string, string>>();
  for (const row of design.rows) {
    designMap.set(row.Plant_ID, row);
  }

  const bands = [
    { col: 'Mean_365', nm: 365 },
    { col: 'Mean_460', nm: 460 },
    { col: 'Mean_525', nm: 525 },
    { col: 'Mean_570', nm: 570 },
    { col: 'Mean_645', nm: 645 },
    { col: 'Mean_670', nm: 670 },
    { col: 'Mean_700', nm: 700 },
    { col: 'Mean_780', nm: 780 },
    { col: 'Mean_890', nm: 890 },
    { col: 'Mean_970', nm: 970 },
  ];

  const plantSet = new Set<string>();
  const potSet = new Set<string>();
  const dateSet = new Set<string>();
  const labelCounts: Record<string, number> = {};
  const genotypeCounts: Record<string, number> = {};

  const groupAgg = new Map<
    string,
    { n: number; plants: Set<string>; sums: number[]; sqSums: number[] }
  >();
  const dateAgg = new Map<string, Map<string, { sumNdvi: number; sumRedEdge: number; n: number }>>();

  const sampleRows: Array<Record<string, string | number>> = [];

  for (const row of spectra.rows) {
    const plantId = row.Plant_ID || 'Unknown';
    const meta = designMap.get(plantId);
    const treatment = meta?.Treatment || 'Unmatched_Metadata';
    const genotype = meta?.Genotype || 'Unknown';
    const pot = meta?.Pot_Number || '-';
    const date = row.date || 'Unknown';

    plantSet.add(plantId);
    if (pot !== '-') potSet.add(pot);
    dateSet.add(date);

    labelCounts[treatment] = (labelCounts[treatment] || 0) + 1;
    genotypeCounts[genotype] = (genotypeCounts[genotype] || 0) + 1;

    if (!groupAgg.has(treatment)) {
      groupAgg.set(treatment, {
        n: 0,
        plants: new Set(),
        sums: new Array(bands.length).fill(0),
        sqSums: new Array(bands.length).fill(0),
      });
    }
    const agg = groupAgg.get(treatment)!;
    agg.n += 1;
    agg.plants.add(plantId);

    for (let b = 0; b < bands.length; b += 1) {
      const val = Number.parseFloat(row[bands[b].col] || '0');
      if (!Number.isNaN(val)) {
        agg.sums[b] += val;
        agg.sqSums[b] += val * val;
      }
    }

    const r670 = Number.parseFloat(row.Mean_670 || '0');
    const r700 = Number.parseFloat(row.Mean_700 || '0');
    const r780 = Number.parseFloat(row.Mean_780 || '0');
    const ndvi = r780 + r670 > 0 ? (r780 - r670) / (r780 + r670) : 0;
    const ndre = r780 + r700 > 0 ? (r780 - r700) / (r780 + r700) : 0;

    if (treatment !== 'Unmatched_Metadata' && date !== 'Unknown') {
      if (!dateAgg.has(date)) dateAgg.set(date, new Map());
      const dm = dateAgg.get(date)!;
      if (!dm.has(treatment)) dm.set(treatment, { sumNdvi: 0, sumRedEdge: 0, n: 0 });
      const dEntry = dm.get(treatment)!;
      dEntry.sumNdvi += ndvi;
      dEntry.sumRedEdge += ndre;
      dEntry.n += 1;
    }

    if (sampleRows.length < 18 && meta) {
      sampleRows.push({
        sampleId: row.Sample_ID,
        plantId,
        potNumber: pot,
        genotype,
        date,
        label: treatment,
        r670: Number(r670.toFixed(2)),
        r780: Number(r780.toFixed(2)),
        ndvi: Number(ndvi.toFixed(3)),
        ndre: Number(ndre.toFixed(3)),
      });
    }
  }

  const curves = Array.from(groupAgg.entries())
    .filter(([k]) => k !== 'Unmatched_Metadata')
    .map(([label, agg]) => ({
      label,
      samples: agg.n,
      plants: agg.plants.size,
      points: bands.map((b, idx) => {
        const mean = agg.sums[idx] / Math.max(1, agg.n);
        const variance = Math.max(0, agg.sqSums[idx] / Math.max(1, agg.n) - mean * mean);
        return {
          wavelengthNm: b.nm,
          mean: Number(mean.toFixed(3)),
          std: Number(Math.sqrt(variance).toFixed(3)),
        };
      }),
    }));

  const sortedDates = Array.from(dateSet).sort((a, b) => {
    const [am, ad, ay] = a.split('-').map(Number);
    const [bm, bd, by] = b.split('-').map(Number);
    return new Date(2000 + ay, am - 1, ad).getTime() - new Date(2000 + by, bm - 1, bd).getTime();
  });

  const temporalTrajectory = sortedDates.map((date) => {
    const dm = dateAgg.get(date);
    const series: Record<string, number> = {};
    if (dm) {
      for (const [label, entry] of dm.entries()) {
        series[label] = Number((entry.sumNdvi / Math.max(1, entry.n)).toFixed(4));
      }
    }
    return { date, series };
  });

  return {
    datasetId: 'primary_zenodo',
    title: 'Plant Phenotyping and Environmental Stress Dataset',
    source: 'Zenodo DOI 10.5281/zenodo.22755812',
    licence: 'CC-BY-4.0',
    fallbackTier: 'Tier 1 (Leaf/Plant Spectral CSV)',
    limitationNote:
      'Abiotic drought/water-stress phenotyping (Control 40% Water vs. Drought 10% Water) rather than pathogen inoculation.',
    files: ['data/raw/Multispectral_Reflectance.csv', 'data/raw/experimental_design.csv'],
    shape: { rows: spectra.rows.length, columns: spectra.headers.length },
    designShape: { rows: design.rows.length, columns: design.headers.length },
    uniquePlants: plantSet.size,
    uniquePots: potSet.size,
    uniqueDatesCount: sortedDates.length,
    dateRange: sortedDates.length > 0 ? `${sortedDates[0]} to ${sortedDates[sortedDates.length - 1]}` : '-',
    groupingColumns: [
      { name: 'Plant_ID', role: 'Biological plant unit', splitUsage: 'Primary StratifiedGroupKFold key' },
      { name: 'Pot_Number', role: 'Physical pot / plot ID', splitUsage: 'Spatial container check' },
      { name: 'date', role: 'Acquisition calendar date', splitUsage: 'Chronological forecast split' },
      { name: 'TimeStamp', role: 'Exact scan session timestamp', splitUsage: 'Replicate deduplication' },
    ],
    labelDistribution: Object.entries(labelCounts).map(([label, count]) => ({ label, count })),
    genotypeDistribution: Object.entries(genotypeCounts).map(([label, count]) => ({ label, count })),
    curves,
    temporalTrajectory,
    sampleRows,
  };
}

function summarizeSyntheticDataset() {
  const synthPath = path.join(ROOT_DIR, 'data', 'raw', 'synthetic_leaf_disease_spectra_v1.csv');
  const synth = parseCsvFile(synthPath);
  const bandCols = synth.headers.filter((h) => h.startsWith('band_') && h.endsWith('nm'));
  const wavelengths = bandCols.map((c) => Number.parseInt(c.replace('band_', '').replace('nm', ''), 10));

  const plantSet = new Set<string>();
  const plotSet = new Set<string>();
  const dateSet = new Set<string>();
  const labelCounts: Record<string, number> = {};
  const groupAgg = new Map<
    string,
    { n: number; plants: Set<string>; sums: number[]; sqSums: number[] }
  >();
  const dateAgg = new Map<string, Map<string, { sumNdvi: number; n: number }>>();
  const sampleRows: Array<Record<string, string | number>> = [];

  for (const row of synth.rows) {
    const label = row.disease_label || 'Unknown';
    const plantId = row.plant_id || 'Unknown';
    const plotId = row.plot_id || 'Unknown';
    const date = row.acquisition_date || 'Unknown';

    plantSet.add(plantId);
    plotSet.add(plotId);
    dateSet.add(date);
    labelCounts[label] = (labelCounts[label] || 0) + 1;

    if (!groupAgg.has(label)) {
      groupAgg.set(label, {
        n: 0,
        plants: new Set(),
        sums: new Array(bandCols.length).fill(0),
        sqSums: new Array(bandCols.length).fill(0),
      });
    }
    const agg = groupAgg.get(label)!;
    agg.n += 1;
    agg.plants.add(plantId);
    for (let b = 0; b < bandCols.length; b += 1) {
      const val = Number.parseFloat(row[bandCols[b]] || '0') * 100;
      agg.sums[b] += val;
      agg.sqSums[b] += val * val;
    }

    const r670 = Number.parseFloat(row.band_670nm || '0') * 100;
    const r700 = Number.parseFloat(row.band_700nm || '0') * 100;
    const r780 = Number.parseFloat(row.band_780nm || '0') * 100;
    const ndvi = r780 + r670 > 0 ? (r780 - r670) / (r780 + r670) : 0;
    const ndre = r780 + r700 > 0 ? (r780 - r700) / (r780 + r700) : 0;

    if (!dateAgg.has(date)) dateAgg.set(date, new Map());
    const dm = dateAgg.get(date)!;
    if (!dm.has(label)) dm.set(label, { sumNdvi: 0, n: 0 });
    const dEntry = dm.get(label)!;
    dEntry.sumNdvi += ndvi;
    dEntry.n += 1;

    if (sampleRows.length < 18) {
      sampleRows.push({
        sampleId: row.sample_id,
        plantId,
        potNumber: plotId,
        genotype: row.field_id,
        date,
        label,
        r670: Number(r670.toFixed(2)),
        r780: Number(r780.toFixed(2)),
        ndvi: Number(ndvi.toFixed(3)),
        ndre: Number(ndre.toFixed(3)),
      });
    }
  }

  const curves = Array.from(groupAgg.entries()).map(([label, agg]) => ({
    label,
    samples: agg.n,
    plants: agg.plants.size,
    points: bandCols
      .map((_c, idx) => {
        const mean = agg.sums[idx] / Math.max(1, agg.n);
        const variance = Math.max(0, agg.sqSums[idx] / Math.max(1, agg.n) - mean * mean);
        return {
          wavelengthNm: wavelengths[idx],
          mean: Number(mean.toFixed(3)),
          std: Number(Math.sqrt(variance).toFixed(3)),
        };
      })
      .filter((_pt, i) => i % 2 === 0),
  }));

  const sortedDates = Array.from(dateSet).sort();
  const temporalTrajectory = sortedDates.map((date) => {
    const dm = dateAgg.get(date);
    const series: Record<string, number> = {};
    if (dm) {
      for (const [label, entry] of dm.entries()) {
        series[label] = Number((entry.sumNdvi / Math.max(1, entry.n)).toFixed(4));
      }
    }
    return { date, series };
  });

  return {
    datasetId: 'synthetic_fallback',
    title: 'Synthetic Leaf Spectral Disease Benchmark (400–1000 nm)',
    source: 'Local Generator (src/pipeline/generate_synthetic_spectra.py)',
    licence: 'Apache-2.0 (Synthetic)',
    fallbackTier: 'Tier 3 (Clearly Labeled Synthetic)',
    limitationNote:
      'SYNTHETIC DATA: Simulated PROSPECT-inspired chlorophyll & red-edge shift effects for leak-free pipeline testing only.',
    files: ['data/raw/synthetic_leaf_disease_spectra_v1.csv'],
    shape: { rows: synth.rows.length, columns: synth.headers.length },
    designShape: null,
    uniquePlants: plantSet.size,
    uniquePots: plotSet.size,
    uniqueDatesCount: sortedDates.length,
    dateRange: sortedDates.length > 0 ? `${sortedDates[0]} to ${sortedDates[sortedDates.length - 1]}` : '-',
    groupingColumns: [
      { name: 'plant_id', role: 'Biological plant unit', splitUsage: 'Primary StratifiedGroupKFold key' },
      { name: 'plot_id', role: 'Plot container identifier', splitUsage: 'Spatial block holdout' },
      { name: 'field_id', role: 'Field block identifier', splitUsage: 'Cross-field generalization test' },
      { name: 'acquisition_date', role: 'Measurement date', splitUsage: 'Chronological forecast split' },
    ],
    labelDistribution: Object.entries(labelCounts).map(([label, count]) => ({ label, count })),
    genotypeDistribution: [],
    curves,
    temporalTrajectory,
    sampleRows,
  };
}

async function createServer() {
  const app = express();
  app.use(express.json({ limit: '2mb' }));

  app.get('/api/health', (_req, res) => {
    res.json({ ok: true });
  });

  app.get('/api/day1/state', (_req, res) => {
    res.json(readDay1State());
  });

  app.put('/api/day1/state', (req, res) => {
    const current = readDay1State();
    const updated = writeDay1State({ ...current, ...req.body });
    res.json(updated);
  });

  app.get('/api/repo/status', async (_req, res) => {
    const expectedDirs = [
      { path: 'data', purpose: 'Raw downloaded CSVs & processed split outputs' },
      { path: 'data/raw', purpose: 'Immutable source spectral files' },
      { path: 'data/processed', purpose: 'Day 2+ cleaned feature matrices' },
      { path: 'notebooks', purpose: 'Exploratory & verification Jupyter notebooks' },
      { path: 'src/pipeline', purpose: 'Modular Python scripts for env, loading, and modeling' },
      { path: 'reports', purpose: 'Evaluation figures, metrics, and setup logs' },
      { path: 'app', purpose: 'Interactive workbench documentation & API notes' },
      { path: 'docs', purpose: 'Project brief, dataset decision note, and mentor log' },
    ];

    const expectedFiles = [
      'README.md',
      'requirements.txt',
      'docs/project_brief.md',
      'docs/dataset_note.md',
      'docs/data_summary.md',
      'docs/mentor_message.md',
      'src/data.py',
      'src/pipeline/verify_env.py',
      'src/pipeline/run_day2_eda.py',
      'notebooks/01_day1_env_and_data_check.ipynb',
      'notebooks/01_eda.ipynb',
      'reports/figures/01_mean_spectra_variance.png',
      'reports/figures/02_difference_spectrum_red_edge.png',
      'reports/figures/03_class_group_and_outliers.png',
      'reports/figures/04_temporal_spectral_progression.png',
      'data/raw/Multispectral_Reflectance.csv',
      'data/raw/experimental_design.csv',
      'data/raw/synthetic_leaf_disease_spectra_v1.csv',
    ];

    const directories = expectedDirs.map((d) => {
      const full = path.join(ROOT_DIR, d.path);
      const exists = fs.existsSync(full) && fs.statSync(full).isDirectory();
      const itemCount = exists ? fs.readdirSync(full).length : 0;
      return { ...d, exists, itemCount };
    });

    const files = expectedFiles.map((relPath) => {
      const full = path.join(ROOT_DIR, relPath);
      const exists = fs.existsSync(full);
      const sizeBytes = exists ? fs.statSync(full).size : 0;
      return { path: relPath, exists, sizeBytes };
    });

    let gitInitialized = false;
    let gitBranch = '';
    let gitCommits: Array<{ hash: string; message: string; date: string }> = [];
    let gitDirtyCount = 0;

    try {
      await execFileAsync('git', ['rev-parse', '--is-inside-work-tree'], { cwd: ROOT_DIR });
      gitInitialized = true;
      const { stdout: branchOut } = await execFileAsync('git', ['rev-parse', '--abbrev-ref', 'HEAD'], {
        cwd: ROOT_DIR,
      });
      gitBranch = branchOut.trim();
      const { stdout: statusOut } = await execFileAsync('git', ['status', '--short'], { cwd: ROOT_DIR });
      gitDirtyCount = statusOut
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean).length;
      const { stdout: logOut } = await execFileAsync(
        'git',
        ['log', '-n', '5', '--pretty=format:%h|%s|%cs'],
        { cwd: ROOT_DIR }
      );
      gitCommits = logOut
        .split('\n')
        .filter(Boolean)
        .map((line) => {
          const [hash, message, date] = line.split('|');
          return { hash, message, date };
        });
    } catch {
      gitInitialized = false;
    }

    res.json({
      directories,
      files,
      git: {
        initialized: gitInitialized,
        branch: gitBranch,
        dirtyCount: gitDirtyCount,
        commits: gitCommits,
      },
    });
  });

  app.get('/api/env/verify', async (_req, res) => {
    try {
      const { stdout } = await execFileAsync('python3', ['src/pipeline/verify_env.py', '--json'], {
        cwd: ROOT_DIR,
        timeout: 15000,
      });
      res.json(JSON.parse(stdout));
    } catch (err: unknown) {
      const execErr = err as { stdout?: string; stderr?: string; message?: string };
      if (execErr.stdout) {
        try {
          res.json(JSON.parse(execErr.stdout));
          return;
        } catch {
          // fall through
        }
      }
      res.status(500).json({
        all_ok: false,
        error: execErr.stderr || execErr.message || 'Failed to execute verify_env.py',
        packages: [],
      });
    }
  });

  app.get('/api/docs', (_req, res) => {
    const docs = Object.entries(DOC_FILES).map(([key, meta]) => {
      const full = path.join(ROOT_DIR, meta.relPath);
      const content = fs.existsSync(full) ? fs.readFileSync(full, 'utf-8') : '';
      return { key, label: meta.label, relPath: meta.relPath, content };
    });
    res.json({ docs });
  });

  app.put('/api/docs/:key', (req, res) => {
    const key = req.params.key;
    const meta = DOC_FILES[key];
    if (!meta) {
      res.status(404).json({ error: 'Unknown document key' });
      return;
    }
    if (
      key !== 'project_brief' &&
      key !== 'data_summary' &&
      key !== 'dataset_note' &&
      key !== 'mentor_message' &&
      key !== 'readme'
    ) {
      res.status(403).json({ error: 'Document is read-only in workbench' });
      return;
    }
    const content = typeof req.body?.content === 'string' ? req.body.content : null;
    if (content === null) {
      res.status(400).json({ error: 'Missing content string' });
      return;
    }
    const full = path.join(ROOT_DIR, meta.relPath);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, content, 'utf-8');
    res.json({ ok: true, key, relPath: meta.relPath, content });
  });

  app.get('/api/dataset/summary', (req, res) => {
    const source = req.query.source === 'synthetic' ? 'synthetic' : 'primary';
    try {
      const summary = source === 'synthetic' ? summarizeSyntheticDataset() : summarizePrimaryDataset();
      res.json(summary);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to parse dataset';
      res.status(500).json({ error: message });
    }
  });

  app.get('/api/eda/metrics', async (_req, res) => {
    const metricsPath = path.join(ROOT_DIR, 'reports', 'day2_eda_metrics.json');
    try {
      if (!fs.existsSync(metricsPath)) {
        await execFileAsync('python3', ['src/pipeline/run_day2_eda.py'], {
          cwd: ROOT_DIR,
          timeout: 30000,
        });
      }
      const raw = fs.readFileSync(metricsPath, 'utf-8');
      res.json(JSON.parse(raw));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load Day 2 EDA metrics';
      res.status(500).json({ error: message });
    }
  });

  app.post('/api/eda/run', async (_req, res) => {
    try {
      const { stdout } = await execFileAsync('python3', ['src/pipeline/run_day2_eda.py'], {
        cwd: ROOT_DIR,
        timeout: 30000,
      });
      const metricsPath = path.join(ROOT_DIR, 'reports', 'day2_eda_metrics.json');
      const raw = fs.readFileSync(metricsPath, 'utf-8');
      res.json({ ok: true, log: stdout, data: JSON.parse(raw) });
    } catch (err: unknown) {
      const execErr = err as { stderr?: string; message?: string };
      res.status(500).json({ error: execErr.stderr || execErr.message || 'EDA run failed' });
    }
  });

  app.get('/api/figures/:filename', (req, res) => {
    const filename = path.basename(req.params.filename);
    const full = path.join(ROOT_DIR, 'reports', 'figures', filename);
    if (!filename.endsWith('.png') || !fs.existsSync(full)) {
      res.status(404).json({ error: 'Figure not found' });
      return;
    }
    res.sendFile(full);
  });

  if (process.env.NODE_ENV !== 'production') {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distDir = path.join(ROOT_DIR, 'dist');
    app.use(express.static(distDir));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distDir, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`SpectralCrop Day 1 server listening on http://localhost:${PORT}`);
  });
}

createServer().catch((err) => {
  console.error(err);
  process.exit(1);
});
