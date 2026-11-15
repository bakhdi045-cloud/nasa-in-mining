// TypeScript view of the MiningCase contract (src/nasa_in_mining/mining/contract.py, schema 1.0).
// contract/mining_case.schema.json is the authoritative schema; tests check that the recorded case satisfies both.

export type Status = "measured" | "not_measured" | "unavailable" | "not_applicable";

export interface Uncertainty {
  kind: "not_estimated" | "sensitivity_range" | "empirical_sigma" | "not_applicable";
  value?: number | null;
  low?: number | null;
  high?: number | null;
  method?: string | null;
}

export interface Measurement {
  value: number | null;
  unit: string;
  status: Status;
  uncertainty?: Uncertainty | null;
  reason?: string | null;
}

export interface Site {
  id: string;
  name: string;
  country: string;
  commodity: string;
  operator?: string | null;
  centroid: [number, number];
  description_key: string;
}

export interface Zone {
  id: string;
  role: "study_perimeter" | "control_ring" | "mapped_mining_outside_perimeter" | "exclusion";
  area_km2: number | null;
  source: string;
  source_date: string | null;
  license: string;
  attribution: string;
  nature?: string | null;
}

export interface Acquisition {
  pair_id: string;
  granule_id: string;
  collection: string;
  crid: string;
  maturity: string;
  geometry_id: string;
  direction: "ascending" | "descending";
  track: number;
  frame: number;
  reference_time: string;
  secondary_time: string;
  span_days: number;
  product_version: string | null;
  processing_datetime: string | null;
  doi: string | null;
  source_url: string;
  bytes_transferred: number | null;
  layers: { name: string; sha256: string; spacing_m?: number[] | null; units?: string | null }[];
  looks: Record<string, number | null>;
  quality: { ok: boolean; reasons: string[]; phase_sigma_rad: number | null; coherence_median: number | null };
}

export interface OpticalScene {
  item_id: string;
  datetime: string;
  platform: string | null;
  processing_baseline: string | null;
  cloud_cover_pct: number | null;
  valid_fraction_window: number;
}

export interface ZoneMetrics {
  zone_id: string;
  zone_area_km2: number;
  observable_area_km2: Measurement;
  observable_fraction: Measurement;
  flagged_area_km2: Measurement;
  flagged_fraction_of_observable: Measurement;
  median_coherence: Measurement;
}

export interface Cluster {
  id: number;
  area_km2: number;
  centroid: [number, number];
  median_coherence: number;
  recurrence_in_other_pairs?: number | null;
  optical_change_fraction?: number | null;
  optical_diagnostics?: Record<string, number | string | null> | null;
}

export interface OpticalComparison {
  status: "ok" | "no_scene_pair" | "insufficient_overlap";
  before_item: string | null;
  after_item: string | null;
  gap_days_before: number | null;
  gap_days_after: number | null;
  optical_threshold: Measurement;
  lift: Measurement;
  p_optical_given_radar: Measurement;
  p_optical_given_not_radar: Measurement;
  jaccard: Measurement;
  control_median_d_ndvi?: Measurement | null;
  control_median_d_mndwi?: Measurement | null;
  reason?: string | null;
}

export interface PairResult {
  pair_id: string;
  geometry_id: string;
  reference_date: string;
  secondary_date: string;
  span_days: number;
  status: "ok" | "rejected_quality" | "insufficient_control" | "incompatible_grid";
  reason?: string | null;
  threshold: Measurement;
  threshold_sensitivity: Record<string, Measurement>;
  control_flag_rate: Measurement;
  control_median_coherence: Measurement;
  zones: ZoneMetrics[];
  study_flagged_area_sensitivity: Record<string, Measurement>;
  n_clusters: number | null;
  clusters_shown: Cluster[];
  layer_ids: string[];
  optical: OpticalComparison | null;
}

export interface GeometrySummary {
  geometry_id: string;
  direction: string;
  track: number;
  frame: number;
  crid: string;
  n_pairs: number;
  n_pairs_used: number;
  recurrence_pairs: string[];
  recurrence_layer_id: string | null;
  study_area_flagged_ever_km2: Measurement;
  study_area_flagged_half_or_more_km2: Measurement;
}

export interface CrossGeometry {
  status: "ok" | "unavailable";
  spearman_recurrence_study: Measurement;
  lift_frequent_change: Measurement;
  jaccard_frequent_change: Measurement;
  frequent_threshold: number;
  reason?: string | null;
}

export interface LosPair {
  pair_id: string;
  status: "ok" | "insufficient_data" | "not_computed";
  reference: string;
  control_sigma_cm: Measurement;
  study_median_cm: Measurement;
  study_p05_cm: Measurement;
  study_p95_cm: Measurement;
  study_coherent_fraction: Measurement;
  area_beyond_3sigma_km2: Measurement;
  layer_id: string | null;
  sign_verified: boolean;
  reason?: string | null;
}

export interface Legend {
  kind: "continuous" | "categorical" | "rgb";
  unit?: string | null;
  vmin?: number | null;
  vmax?: number | null;
  cmap?: string | null;
  stops?: string[] | null;
  classes?: Record<string, number[]> | null;
  class_keys?: Record<string, string> | null;
}

export interface Layer {
  id: string;
  kind: "observation" | "derived" | "reference" | "basemap" | "zones";
  title_key: string;
  params: Record<string, string | number | null>;
  url: string;
  corners?: number[][] | null;
  legend?: Legend | null;
  date_start?: string | null;
  date_end?: string | null;
  source_ids: string[];
  resolution_m?: number | null;
  export?: string | null;
}

export interface Reference {
  id: string;
  kind: "optical_imagery" | "map" | "documentation";
  name: string;
  provider: string;
  license: string;
  url: string;
  dates: string[];
  supports_key: string;
  cannot_support_key: string;
}

export type ValidationLevel =
  | "not_computed"
  | "computed"
  | "internally_consistent"
  | "consistent_with_independent_source"
  | "independently_validated";

export interface ValidationItem {
  observable: string;
  level: ValidationLevel;
  evidence_keys: string[];
  missing_keys: string[];
}

export type Params = Record<string, boolean | number | string | null | unknown[]>;

export interface Finding {
  id: string;
  kind: string;
  params: Params;
  evidence: string[];
}

export interface NextCheck {
  id: string;
  kind: string;
  params: Params;
  because: string[];
}

export interface Manifest {
  run_id: string;
  created_utc: string;
  code_commit: string | null;
  code_dirty: boolean | null;
  python: string;
  packages: Record<string, string | null>;
  config_sha256: string;
  inputs: { path: string; sha256: string; role?: string | null }[];
  outputs: { path: string; sha256: string; role?: string | null }[];
  duration_s: number;
}

export interface Export {
  id: string;
  format: "csv" | "geojson" | "geotiff" | "json";
  path: string;
  description_key: string;
  sha256: string;
}

export interface MiningCase {
  schema_version: "1.0";
  case_id: string;
  data_nature: "real" | "synthetic";
  question_key: string;
  user_key: string;
  site: Site;
  zones: Zone[];
  zones_url: string;
  acquisitions: Acquisition[];
  optical_scenes: OpticalScene[];
  method: { id: string; version: string; parameters: Record<string, unknown>; reused_modules: string[]; steps: string[] };
  pairs: PairResult[];
  geometries: GeometrySummary[];
  cross_geometry: CrossGeometry;
  los: LosPair[];
  layers: Layer[];
  exports: Export[];
  references: Reference[];
  validation: ValidationItem[];
  findings: Finding[];
  next_checks: NextCheck[];
  limits: string[];
  processing: {
    status: "complete" | "partial" | "unavailable" | "failed";
    steps: { name: string; status: string; message?: string | null }[];
    blockers: string[];
  };
  manifest: Manifest | null;
}

export interface ApiErrorBody {
  error: string;
  message: string;
}

/** Minimal runtime check so that an incompatible file produces an explicit error instead of a broken page. */
export function assertMiningCase(data: unknown): asserts data is MiningCase {
  const d = data as Partial<MiningCase> | null;
  const missing: string[] = [];
  if (!d || typeof d !== "object") throw new Error("the case is not a JSON object");
  if (d.schema_version !== "1.0") throw new Error(`unsupported schema_version ${String(d.schema_version)} (expected 1.0)`);
  for (const key of ["case_id", "site", "zones", "pairs", "layers", "validation", "processing", "limits"] as const) {
    if (d[key] === undefined) missing.push(key);
  }
  if (missing.length) throw new Error(`the case misses required fields: ${missing.join(", ")}`);
}
