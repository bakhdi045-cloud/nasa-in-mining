/* Generated from contract/mining_case.schema.json by `npm run contract`. Do not edit. */

export type SchemaVersion = "2.0";
export type CaseId = string;
export type RunId = string;
export type DataNature = "real" | "synthetic";
export type PresentationLevelKey = string;
export type QuestionKey = string;
export type UserKey = string;
export type Id = string;
export type Name = string;
export type Country = string;
export type Commodity = string;
export type Operator = string | null;
/**
 * @minItems 2
 * @maxItems 2
 */
export type Centroid = [unknown, unknown];
export type DescriptionKey = string;
export type Id1 = string;
export type Role = "study_perimeter" | "control_ring" | "mapped_mining_outside_perimeter" | "exclusion";
export type AreaKm2 = number | null;
export type Source = string;
export type SourceDate = string | null;
export type License = string;
export type Attribution = string;
export type Nature = string | null;
export type Zones = Zone[];
export type Id2 = string;
export type Label = string;
export type Source1 = string;
export type SourceDate1 = string | null;
export type AreaKm21 = number;
export type UsedAs = "main" | "sensitivity" | "context";
export type Note = string;
export type PerimeterVersions = PerimeterVersion[];
export type ZonesUrl = string;
export type PairId = string;
export type GranuleId = string;
export type Collection = string;
export type Crid = string;
export type Maturity = string;
export type GeometryId = string;
export type Direction = "ascending" | "descending";
export type Track = number;
export type Frame = number;
export type ReferenceTime = string;
export type SecondaryTime = string;
export type SpanDays = number;
export type ProductVersion = string | null;
export type ProductSpecificationVersion = string | null;
export type SoftwareVersion = string | null;
export type ProcessingDatetime = string | null;
export type Doi = string | null;
export type SourceUrl = string;
export type BytesTransferred = number | null;
export type Name1 = string;
export type Sha256 = string;
export type SpacingM = number[] | null;
export type Units = string | null;
export type Layers = LayerFile[];
export type Ok = boolean;
export type Reasons = string[];
export type Acquisitions = Acquisition[];
export type ItemId = string;
export type Datetime = string;
export type Platform = string | null;
export type ProcessingBaseline = string | null;
export type CloudCoverPctTile = number | null;
export type ClearFractionStudy = number;
export type ClearFractionControl = number;
export type DoubtfulFractionStudy = number;
export type Usable = boolean;
export type Reason = string | null;
export type OpticalScenes = OpticalScene[];
export type Id3 = string;
export type Version = string;
export type ObservableKey = string;
export type Id4 = string;
export type LabelKey = string;
export type Description = string;
export type Pixels = number;
export type AreaKm22 = number;
export type Controls = ControlDef[];
export type MainProfile = string;
export type ReusedModules = string[];
export type Steps = string[];
export type BlockSizeJustification = string;
export type PairId1 = string;
export type GeometryId1 = string;
export type Direction1 = "ascending" | "descending";
export type ReferenceDate = string;
export type SecondaryDate = string;
export type SpanDays1 = number;
export type Status = "ok" | "rejected_coherence_qc" | "insufficient_control" | "incompatible_grid";
export type Reasons1 = string[];
export type ZoneId = string;
export type ZoneAreaKm2 = number;
export type Value = number | null;
export type Unit = string;
export type Status1 = "measured" | "not_measured" | "unavailable" | "not_applicable";
export type Kind = "not_estimated" | "block_bootstrap_interval" | "empirical_sigma";
export type Low = number | null;
export type High = number | null;
export type Value1 = number | null;
export type Level = number | null;
export type Method1 = string | null;
export type BlockM = number | null;
export type NBlocks = number | null;
export type BlockSizeSensitivity = {
  [k: string]: number[];
} | null;
export type Reason1 = string | null;
export type Zones1 = ZoneMetrics[];
export type Id5 = string;
export type ControlId = string;
export type Quantile = number;
export type ExceedsControl = boolean | null;
export type Profiles = Profile[];
export type NClusters = number | null;
export type Id6 = number;
export type AreaKm23 = number;
/**
 * @minItems 2
 * @maxItems 2
 */
export type Centroid1 = [unknown, unknown];
export type MedianCoherence = number;
export type PairsSameGeometryOverlapping = number | null;
export type PairsSameGeometryObserved = number | null;
export type RetainedAtLowerQuantile = boolean | null;
export type ClustersShown = Cluster[];
export type LayerIds = string[];
export type Mode = "strict" | "exploratory";
export type MaxGapDays = number;
export type Status2 = "ok" | "no_scene_pair" | "insufficient_overlap";
export type Reason2 = string | null;
export type BeforeItem = string | null;
export type BeforeDatetime = string | null;
export type AfterItem = string | null;
export type AfterDatetime = string | null;
export type GapDaysBefore = number | null;
export type GapDaysAfter = number | null;
export type RadarWindow = string[];
export type OpticalWindow = string[] | null;
export type Table = {
  [k: string]: number;
} | null;
export type SpectralHypotheses = {
  [k: string]: number;
} | null;
export type Optical = OpticalComparison[];
export type Pairs = PairResult[];
export type GeometryId2 = string;
export type Direction2 = string;
export type Track1 = number;
export type Frame1 = number;
export type Crid1 = string;
export type NPairs = number;
export type NPairsAnalysed = number;
export type GeometryId3 = string;
export type SpanDays2 = number;
export type PairIds = string[];
export type Gaps = string[][];
export type LayerId = string | null;
export type CountLayerId = string | null;
export type ObservedPairsMin = number | null;
export type ObservedPairsMax = number | null;
export type DisjointPairs = string[];
export type Recurrence = Recurrence1[];
export type Geometries = GeometrySummary[];
export type Status3 = "ok" | "unavailable";
export type Rule = string;
export type PairA = string;
export type PairB = string;
export type OverlapDays = number;
export type Matches = WindowMatch[];
export type Unmatched = string[];
export type Reason3 = string | null;
export type PairId2 = string;
export type Status4 = "computed" | "not_computed" | "insufficient_data";
export type PhaseQcOk = boolean;
export type Within3Sigma = boolean | null;
export type LayerId1 = string | null;
export type SignVerified = boolean;
export type Interpreted = false;
export type Reason4 = string | null;
export type Los = LosPair[];
export type Id7 = string;
export type Kind1 = "observation" | "derived" | "reference" | "basemap";
export type TitleKey = string;
export type Url = string;
export type Corners = number[][];
export type Kind2 = "continuous" | "categorical" | "rgb";
export type Unit1 = string | null;
export type Vmin = number | null;
export type Vmax = number | null;
export type Cmap = string | null;
export type Stops = string[] | null;
export type Levels = number | null;
export type Classes = {
  [k: string]: number[];
} | null;
export type ClassKeys = {
  [k: string]: string;
} | null;
export type DateStart = string | null;
export type DateEnd = string | null;
export type SourceIds = string[];
export type ResolutionM = number | null;
export type Export = string | null;
export type DisplayNoteKey = string | null;
export type Layers1 = Layer[];
export type Id8 = string;
export type Format = "csv" | "geojson" | "geotiff" | "json" | "markdown";
export type Path = string;
export type DescriptionKey1 = string;
export type Sha2561 = string;
export type Exports = Export1[];
export type Id9 = string;
export type Kind3 = "optical_imagery" | "map" | "land_cover" | "documentation";
export type Name2 = string;
export type Provider = string;
export type License1 = string;
export type Url1 = string;
export type Dates = string[];
export type SupportsKey = string;
export type CannotSupportKey = string;
export type References = Reference[];
export type Observable = string;
export type Level1 =
  | "not_computed"
  | "computed"
  | "internally_cross_checked"
  | "associated_with_independent_observation"
  | "independently_validated";
export type Criteria = string[];
export type EvidenceKeys = string[];
export type MissingKeys = string[];
export type Validation = ValidationItem[];
export type Id10 = string;
export type Kind4 = string;
export type Evidence = string[];
export type LimitKeys = string[];
export type Findings = Finding[];
export type Id11 = string;
/**
 * @minItems 2
 * @maxItems 2
 */
export type Centroid2 = [unknown, unknown];
export type AreaKm24 = number;
export type Zone1 = string;
export type Landcover = string | null;
export type Evidence1 = string[];
export type AlternativeKeys = string[];
export type ToCollectKeys = string[];
export type Dates1 = string[][];
export type Dossiers = Dossier[];
export type Id12 = string;
export type Kind5 = string;
export type Because = string[];
export type NextChecks = NextCheck[];
export type Limits = string[];
export type Status5 = "complete" | "partial" | "unavailable" | "failed";
export type Rule1 = string;
export type Name3 = string;
export type Required = boolean;
export type Status6 = "done" | "skipped" | "failed" | "unavailable" | "partial";
export type Message = string | null;
export type Steps1 = Step[];
export type Blockers = string[];
export type RunId1 = string;
export type CreatedUtc = string;
export type CodeCommit = string | null;
export type CodeDirty = boolean | null;
export type Python = string;
export type ConfigSha256 = string;
export type Path1 = string;
export type Sha2562 = string;
export type Role1 = string;
export type DeclaredSha256 = string | null;
export type Inputs = FileRecord[];
export type Outputs = FileRecord[];
export type DurationS = number;

export interface MiningCase {
  schema_version?: SchemaVersion;
  case_id: CaseId;
  run_id: RunId;
  data_nature: DataNature;
  presentation_level_key: PresentationLevelKey;
  question_key: QuestionKey;
  user_key: UserKey;
  site: Site;
  zones: Zones;
  perimeter_versions: PerimeterVersions;
  zones_url: ZonesUrl;
  acquisitions: Acquisitions;
  optical_scenes: OpticalScenes;
  optical_search: OpticalSearch;
  method: Method;
  pairs: Pairs;
  geometries: Geometries;
  cross_geometry: CrossGeometry;
  los: Los;
  layers: Layers1;
  exports: Exports;
  references: References;
  validation: Validation;
  findings: Findings;
  dossiers: Dossiers;
  next_checks: NextChecks;
  limits: Limits;
  processing: Processing;
  manifest: Manifest | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Site".
 */
export interface Site {
  id: Id;
  name: Name;
  country: Country;
  commodity: Commodity;
  operator?: Operator;
  centroid: Centroid;
  description_key: DescriptionKey;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Zone".
 */
export interface Zone {
  id: Id1;
  role: Role;
  area_km2: AreaKm2;
  source: Source;
  source_date: SourceDate;
  license: License;
  attribution: Attribution;
  nature?: Nature;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "PerimeterVersion".
 */
export interface PerimeterVersion {
  id: Id2;
  label: Label;
  source: Source1;
  source_date: SourceDate1;
  area_km2: AreaKm21;
  used_as: UsedAs;
  note: Note;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Acquisition".
 */
export interface Acquisition {
  pair_id: PairId;
  granule_id: GranuleId;
  collection: Collection;
  crid: Crid;
  maturity: Maturity;
  geometry_id: GeometryId;
  direction: Direction;
  track: Track;
  frame: Frame;
  reference_time: ReferenceTime;
  secondary_time: SecondaryTime;
  span_days: SpanDays;
  product_version: ProductVersion;
  product_specification_version: ProductSpecificationVersion;
  software_version: SoftwareVersion;
  processing_datetime: ProcessingDatetime;
  doi: Doi;
  source_url: SourceUrl;
  bytes_transferred: BytesTransferred;
  layers: Layers;
  looks: Looks;
  coherence_qc: QualityCheck;
  phase_qc: QualityCheck;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "LayerFile".
 */
export interface LayerFile {
  name: Name1;
  sha256: Sha256;
  spacing_m?: SpacingM;
  units?: Units;
}
export interface Looks {
  [k: string]: number | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "QualityCheck".
 */
export interface QualityCheck {
  ok: Ok;
  reasons: Reasons;
  metrics: Metrics;
}
export interface Metrics {
  [k: string]: boolean | number | string | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "OpticalScene".
 */
export interface OpticalScene {
  item_id: ItemId;
  datetime: Datetime;
  platform: Platform;
  processing_baseline: ProcessingBaseline;
  cloud_cover_pct_tile: CloudCoverPctTile;
  clear_fraction_study: ClearFractionStudy;
  clear_fraction_control: ClearFractionControl;
  doubtful_fraction_study: DoubtfulFractionStudy;
  usable: Usable;
  reason?: Reason;
}
export interface OpticalSearch {
  [k: string]: boolean | number | string | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Method".
 */
export interface Method {
  id: Id3;
  version: Version;
  observable_key: ObservableKey;
  parameters: Parameters;
  controls: Controls;
  main_profile: MainProfile;
  reused_modules: ReusedModules;
  steps: Steps;
  autocorrelation: Autocorrelation;
  block_size_justification: BlockSizeJustification;
}
export interface Parameters {
  [k: string]: boolean | number | string | unknown[] | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "ControlDef".
 */
export interface ControlDef {
  id: Id4;
  label_key: LabelKey;
  description: Description;
  pixels: Pixels;
  area_km2: AreaKm22;
  landcover_share: LandcoverShare;
}
export interface LandcoverShare {
  [k: string]: number;
}
export interface Autocorrelation {
  [k: string]: number | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "PairResult".
 */
export interface PairResult {
  pair_id: PairId1;
  geometry_id: GeometryId1;
  direction: Direction1;
  reference_date: ReferenceDate;
  secondary_date: SecondaryDate;
  span_days: SpanDays1;
  status: Status;
  reasons: Reasons1;
  main: ZoneMetrics | null;
  zones: Zones1;
  profiles: Profiles;
  statistical: Measurement;
  perimeter_sensitivity: PerimeterSensitivity;
  zone_stability: ZoneStability;
  n_clusters: NClusters;
  clusters_shown: ClustersShown;
  layer_ids: LayerIds;
  optical: Optical;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "ZoneMetrics".
 */
export interface ZoneMetrics {
  zone_id: ZoneId;
  zone_area_km2: ZoneAreaKm2;
  observable_area_km2: Measurement;
  observable_fraction: Measurement;
  flagged_area_km2: Measurement;
  flagged_fraction: Measurement;
  median_coherence: Measurement;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Measurement".
 */
export interface Measurement {
  value: Value;
  unit: Unit;
  status: Status1;
  uncertainty?: Uncertainty | null;
  reason?: Reason1;
}
/**
 * Statistical uncertainty of one measured value.
 *
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Uncertainty".
 */
export interface Uncertainty {
  kind: Kind;
  low?: Low;
  high?: High;
  value?: Value1;
  level?: Level;
  method?: Method1;
  block_m?: BlockM;
  n_blocks?: NBlocks;
  block_size_sensitivity?: BlockSizeSensitivity;
}
/**
 * Result of one (control, quantile) profile for one pair.
 *
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Profile".
 */
export interface Profile {
  id: Id5;
  control_id: ControlId;
  quantile: Quantile;
  threshold: Measurement;
  calibration_rate: Measurement;
  evaluation_rate: Measurement;
  study_flagged_area_km2: Measurement;
  study_flagged_fraction: Measurement;
  ratio_to_evaluation_rate: Measurement;
  exceeds_control: ExceedsControl;
}
export interface PerimeterSensitivity {
  [k: string]: Measurement;
}
export interface ZoneStability {
  [k: string]: Measurement;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Cluster".
 */
export interface Cluster {
  id: Id6;
  area_km2: AreaKm23;
  centroid: Centroid1;
  median_coherence: MedianCoherence;
  pairs_same_geometry_overlapping?: PairsSameGeometryOverlapping;
  pairs_same_geometry_observed?: PairsSameGeometryObserved;
  retained_at_lower_quantile?: RetainedAtLowerQuantile;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "OpticalComparison".
 */
export interface OpticalComparison {
  mode: Mode;
  max_gap_days: MaxGapDays;
  status: Status2;
  reason?: Reason2;
  before_item?: BeforeItem;
  before_datetime?: BeforeDatetime;
  after_item?: AfterItem;
  after_datetime?: AfterDatetime;
  gap_days_before?: GapDaysBefore;
  gap_days_after?: GapDaysAfter;
  radar_window: RadarWindow;
  optical_window?: OpticalWindow;
  joint_observable_fraction: Measurement;
  optical_threshold: Measurement;
  table?: Table;
  p_optical_given_radar: Measurement;
  p_optical_given_not_radar: Measurement;
  association_ratio: Measurement;
  jaccard: Measurement;
  share_of_optical_change_in_radar_flags: Measurement;
  ratio_with_unclassified_scl: Measurement;
  control_median_d_mndwi: Measurement;
  spectral_hypotheses?: SpectralHypotheses;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "GeometrySummary".
 */
export interface GeometrySummary {
  geometry_id: GeometryId2;
  direction: Direction2;
  track: Track1;
  frame: Frame1;
  crid: Crid1;
  n_pairs: NPairs;
  n_pairs_analysed: NPairsAnalysed;
  recurrence: Recurrence;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Recurrence".
 */
export interface Recurrence1 {
  geometry_id: GeometryId3;
  span_days: SpanDays2;
  pair_ids: PairIds;
  gaps: Gaps;
  layer_id: LayerId;
  count_layer_id: CountLayerId;
  observed_pairs_min: ObservedPairsMin;
  observed_pairs_max: ObservedPairsMax;
  flagged_ever_km2: Measurement;
  flagged_half_or_more_km2: Measurement;
  disjoint_pairs: DisjointPairs;
  flagged_half_or_more_disjoint_km2: Measurement;
  jaccard_adjacent_pairs: Measurement;
  jaccard_pairs_two_apart: Measurement;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "CrossGeometry".
 */
export interface CrossGeometry {
  status: Status3;
  rule: Rule;
  matches: Matches;
  unmatched: Unmatched;
  median_jaccard: Measurement;
  reason?: Reason3;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "WindowMatch".
 */
export interface WindowMatch {
  pair_a: PairA;
  pair_b: PairB;
  overlap_days: OverlapDays;
  table: Table1;
  association_ratio: Measurement;
  jaccard: Measurement;
  p_b_given_a: Measurement;
}
export interface Table1 {
  [k: string]: number;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "LosPair".
 */
export interface LosPair {
  pair_id: PairId2;
  status: Status4;
  phase_qc_ok: PhaseQcOk;
  control_sigma_cm: Measurement;
  study_p05_cm: Measurement;
  study_p95_cm: Measurement;
  within_3sigma: Within3Sigma;
  layer_id: LayerId1;
  sign_verified: SignVerified;
  interpreted?: Interpreted;
  reason?: Reason4;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Layer".
 */
export interface Layer {
  id: Id7;
  kind: Kind1;
  title_key: TitleKey;
  params?: Params;
  url: Url;
  corners: Corners;
  legend: Legend;
  date_start?: DateStart;
  date_end?: DateEnd;
  source_ids?: SourceIds;
  resolution_m?: ResolutionM;
  export?: Export;
  display_note_key?: DisplayNoteKey;
}
export interface Params {
  [k: string]: boolean | number | string | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Legend".
 */
export interface Legend {
  kind: Kind2;
  unit?: Unit1;
  vmin?: Vmin;
  vmax?: Vmax;
  cmap?: Cmap;
  stops?: Stops;
  levels?: Levels;
  classes?: Classes;
  class_keys?: ClassKeys;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Export".
 */
export interface Export1 {
  id: Id8;
  format: Format;
  path: Path;
  description_key: DescriptionKey1;
  sha256: Sha2561;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Reference".
 */
export interface Reference {
  id: Id9;
  kind: Kind3;
  name: Name2;
  provider: Provider;
  license: License1;
  url: Url1;
  dates?: Dates;
  supports_key: SupportsKey;
  cannot_support_key: CannotSupportKey;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "ValidationItem".
 */
export interface ValidationItem {
  observable: Observable;
  level: Level1;
  criteria: Criteria;
  evidence_keys: EvidenceKeys;
  missing_keys: MissingKeys;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Finding".
 */
export interface Finding {
  id: Id10;
  kind: Kind4;
  params: Params1;
  evidence: Evidence;
  limit_keys?: LimitKeys;
}
export interface Params1 {
  [k: string]: boolean | number | string | unknown[] | null;
}
/**
 * Verification sheet for one zone: what was observed, what supports it, what else could explain it.
 *
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Dossier".
 */
export interface Dossier {
  id: Id11;
  centroid: Centroid2;
  area_km2: AreaKm24;
  zone: Zone1;
  landcover: Landcover;
  observation: Observation;
  evidence: Evidence1;
  alternative_keys: AlternativeKeys;
  to_collect_keys: ToCollectKeys;
  dates: Dates1;
}
export interface Observation {
  [k: string]: boolean | number | string | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "NextCheck".
 */
export interface NextCheck {
  id: Id12;
  kind: Kind5;
  params: Params2;
  because: Because;
}
export interface Params2 {
  [k: string]: boolean | number | string | unknown[] | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Processing".
 */
export interface Processing {
  status: Status5;
  rule: Rule1;
  steps: Steps1;
  blockers?: Blockers;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Step".
 */
export interface Step {
  name: Name3;
  required: Required;
  status: Status6;
  message?: Message;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "Manifest".
 */
export interface Manifest {
  run_id: RunId1;
  created_utc: CreatedUtc;
  code_commit: CodeCommit;
  code_dirty: CodeDirty;
  python: Python;
  packages: Packages;
  config_sha256: ConfigSha256;
  inputs: Inputs;
  outputs: Outputs;
  duration_s: DurationS;
}
export interface Packages {
  [k: string]: string | null;
}
/**
 * This interface was referenced by `MiningCase`'s JSON-Schema
 * via the `definition` "FileRecord".
 */
export interface FileRecord {
  path: Path1;
  sha256: Sha2562;
  role: Role1;
  declared_sha256?: DeclaredSha256;
}
