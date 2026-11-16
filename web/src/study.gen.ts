/* Generated from contract/surface_study.schema.json by `npm run contract`. Do not edit. */

export type SchemaVersion = "3.0";
export type StudyId = string;
export type RunId = string;
export type DataNature = "real" | "synthetic";
export type PresentationLevelKey = string;
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
export type Version = string;
export type FrozenUtc = string;
export type Status = string;
export type Sha256 = string;
export type HistoryNote = string;
export type PrimaryObservable = string;
export type State = "historical_map" | "draft_interpretation" | "remote_sensing_reviewed" | "operator_confirmed";
export type ReviewStatus = "pending_human_review" | "recorded";
export type Source = string;
export type SourceDate = string | null;
export type License = string | null;
export type AreaKm2 = number;
export type Value = number | null;
export type Unit = string;
export type Status1 = "measured" | "not_measured" | "unavailable" | "not_applicable";
export type Kind = "not_estimated" | "block_bootstrap_interval" | "empirical_sigma";
export type Low = number | null;
export type High = number | null;
export type Value1 = number | null;
export type Level = number | null;
export type Method = string | null;
export type BlockM = number | null;
export type NBlocks = number | null;
export type BlockSizeSensitivity = {
  [k: string]: number[];
} | null;
export type Reason = string | null;
export type LegalClaim = string;
export type Geojson = string;
export type ReviewFile = string;
export type Id2 = string;
export type Role = "study_perimeter" | "control_ring" | "mapped_mining_outside_perimeter" | "exclusion";
export type AreaKm21 = number | null;
export type Source1 = string;
export type SourceDate1 = string | null;
export type License1 = string;
export type Attribution = string;
export type Nature = string | null;
export type Zones = Zone[];
export type ZonesUrl = string;
export type AcquisitionId = string;
export type GranuleId = string;
export type Collection = string;
export type Maturity = "provisional" | "validated";
export type Crid = string;
export type GeometryId = string;
export type Direction = "ascending" | "descending";
export type Track = number;
export type Frame = number;
export type TimeUtc = string;
export type ProductVersion = string | null;
export type SpecificationVersion = string | null;
export type SoftwareVersion = string | null;
export type ProcessingDatetime = string | null;
export type Doi = string | null;
export type SourceUrl = string;
export type BytesTransferred = number | null;
export type Polarizations = string[];
export type NativeSpacingM = number;
export type AnalysisSpacingM = number;
export type ObservationMode = string | null;
export type NoiseCorrectionApplied = boolean | null;
export type RtcApplied = boolean | null;
export type Normalization = string | null;
export type HasInputDataException = boolean | null;
export type Status2 = "usable" | "rejected";
export type Reasons = string[];
export type CalibrationCaveatKeys = string[];
export type Acquisitions = GcovAcquisition[];
export type BatchId = string;
export type Role1 = "main" | "extension";
export type Collection1 = string;
export type Crid1 = string;
export type GeometryId1 = string;
export type Direction1 = "ascending" | "descending";
export type NAcquisitions = number;
export type NUsable = number;
export type NWindows = number;
export type NWindowsComputed = number;
export type Dates = string[];
export type Gaps = {
  [k: string]: unknown;
}[];
export type NoteKeys = string[];
export type Batches = BatchInfo[];
export type WindowId = string;
export type BatchId1 = string;
export type Role2 = "main" | "extension";
export type GeometryId2 = string;
export type Direction2 = "ascending" | "descending";
export type BeforeId = string;
export type AfterId = string;
export type BeforeDate = string;
export type AfterDate = string;
export type SpanDays = number;
export type Status3 = "computed" | "rejected";
export type Reasons1 = string[];
export type Pol = string;
export type Primary = boolean;
export type Status4 = "computed" | "unavailable" | "insufficient_coverage";
export type Reasons2 = string[];
export type ZoneId = string;
export type Zones1 = ZoneChange[];
export type Status5 = "ok" | "insufficient_baseline" | "not_applicable";
export type NPairs = number;
export type PairIds = string[];
export type Reason1 = string | null;
export type KSigma = number | null;
export type LayerIds = string[];
export type Pols = PolChange[];
export type QualityLayerId = string | null;
export type Mode = "strict" | "exploratory";
export type MaxGapDays = number;
export type Status6 = "ok" | "no_scene_pair" | "insufficient_overlap";
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
export type GunwContext = {
  [k: string]: unknown;
} | null;
export type DevelopmentWindow = boolean;
export type Windows = ChangeWindow[];
export type WindowId1 = string;
export type Pol1 = string;
export type ZoneId1 = string;
export type Quality = QualityRow[];
export type ItemId = string;
export type Datetime = string;
export type Platform = string | null;
export type ProcessingBaseline = string | null;
export type CloudCoverPctTile = number | null;
export type ClearFractionStudy = number;
export type ClearFractionControl = number;
export type DoubtfulFractionStudy = number;
export type Usable = boolean;
export type Reason3 = string | null;
export type OpticalScenes = OpticalScene[];
export type DerivedAtRead = boolean;
export type Mode1 = "strict" | "exploratory";
export type NRadarComparisons = number;
export type NAttempted = number;
export type NUniqueOpticalPairs = number;
export type NGroupsCiAbove1 = number;
export type GroupId = string;
export type BeforeItem1 = string;
export type AfterItem1 = string;
export type BeforeDatetime1 = string | null;
export type AfterDatetime1 = string | null;
export type PairIds1 = string[];
export type NCiAbove1 = number;
export type Groups = OpticalGroup[];
export type NoteKey = string;
export type Optical1 = OpticalEvidence[];
export type Id3 = string;
export type Kind1 = "field_observation" | "dated_imagery_annotation" | "operator_record" | "other";
export type Observable = string;
export type Source2 = string;
export type Reviewer = string | null;
export type ReviewerIndependent = boolean;
export type BlindToRadar = boolean;
export type Method1 = string | null;
export type Rights = string | null;
export type DateStart = string | null;
export type DateEnd = string | null;
export type GeometryRef = string | null;
export type NUnitsFlagged = number;
export type NUnitsUnflagged = number;
export type NUnitsIndeterminate = number;
export type NIndependentGroups = number;
export type SamplingProbabilitiesRecorded = boolean;
export type Evaluation = {
  [k: string]: boolean | number | string | null;
} | null;
export type Limits = string[];
export type References = ReferenceEvidence[];
export type Status7 = "awaiting_annotations" | "annotated_insufficient" | "evaluated";
export type UnitDefinition = string;
export type SamplingFile = string | null;
export type AnnotationTemplate = string | null;
export type NAnnotated = number;
export type NIndeterminate = number;
export type Evaluation1 = {
  [k: string]: unknown;
} | null;
export type Missing = string[];
export type Id4 = string;
export type Kind2 = "optical_imagery" | "map" | "land_cover" | "documentation";
export type Name1 = string;
export type Provider = string;
export type License2 = string;
export type Url = string;
export type Dates1 = string[];
export type SupportsKey = string;
export type CannotSupportKey = string;
export type ReferenceCatalogue = Reference[];
export type ZoneId2 = string;
export type LabelKey = string;
export type Centroid1 = [unknown, unknown] | null;
export type AreaKm22 = number | null;
export type RadarVariation = "measured" | "insufficient_baseline" | "unavailable";
export type OpticalVisibleChange =
  "corroborated_two_or_more_optical_pairs" | "one_optical_pair" | "not_elevated" | "not_observable" | "not_assessed";
export type DocumentedCause = "none_documented";
export type CauseUndetermined = boolean;
export type AlternativeKeys = string[];
export type ToCollectKeys = string[];
export type WindowIds = string[];
export type Conclusions = ZoneConclusion[];
export type Id5 = string;
export type Kind3 = string;
export type Evidence = string[];
export type LimitKeys = string[];
export type Findings = Finding[];
export type Id6 = string;
export type Kind4 = "observation" | "derived" | "reference" | "basemap";
export type TitleKey = string;
export type Url1 = string;
export type Corners = number[][];
export type Kind5 = "continuous" | "categorical" | "rgb";
export type Unit1 = string | null;
export type Vmin = number | null;
export type Vmax = number | null;
export type Cmap = string | null;
export type Stops = string[] | null;
export type Levels = number | null;
export type Classes1 = {
  [k: string]: number[];
} | null;
export type ClassKeys = {
  [k: string]: string;
} | null;
export type DateStart1 = string | null;
export type DateEnd1 = string | null;
export type SourceIds = string[];
export type ResolutionM = number | null;
export type Export = string | null;
export type DisplayNoteKey = string | null;
export type Layers = Layer[];
export type Id7 = string;
export type Format = "csv" | "geojson" | "geotiff" | "json" | "markdown" | "html";
export type Path = string;
export type DescriptionKey1 = string;
export type Sha2561 = string;
export type Exports = Export1[];
export type Limits1 = string[];
export type ExternalSources = {
  [k: string]: string;
}[];
export type Status8 = "complete" | "partial" | "unavailable" | "failed";
export type Rule = string;
export type Name2 = string;
export type Required = boolean;
export type Status9 = "done" | "skipped" | "failed" | "unavailable" | "partial";
export type Message = string | null;
export type Steps = Step[];
export type Blockers = string[];
export type RunId1 = string;
export type CreatedUtc = string;
export type CodeCommit = string | null;
export type CodeDirty = boolean | null;
export type Python = string;
export type ConfigSha256 = string;
export type Path1 = string;
export type Sha2562 = string;
export type Role3 = string;
export type DeclaredSha256 = string | null;
export type Inputs = FileRecord[];
export type Outputs = FileRecord[];
export type DurationS = number;
export type V2Context = {
  [k: string]: unknown;
} | null;

export interface SurfaceStudy {
  schema_version?: SchemaVersion;
  study_id: StudyId;
  run_id: RunId;
  data_nature: DataNature;
  presentation_level_key: PresentationLevelKey;
  site: Site;
  protocol: ProtocolInfo;
  boundary: BoundaryInfo;
  zones: Zones;
  zones_url: ZonesUrl;
  acquisitions: Acquisitions;
  batches: Batches;
  windows: Windows;
  quality: Quality;
  optical_scenes: OpticalScenes;
  evidence: EvidenceSummary;
  references: ReferenceState;
  reference_catalogue: ReferenceCatalogue;
  conclusions: Conclusions;
  findings: Findings;
  layers: Layers;
  exports: Exports;
  limits: Limits1;
  external_sources: ExternalSources;
  processing: Processing;
  manifest?: Manifest | null;
  v2_context?: V2Context;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
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
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "ProtocolInfo".
 */
export interface ProtocolInfo {
  id: Id1;
  version: Version;
  frozen_utc: FrozenUtc;
  status: Status;
  sha256: Sha256;
  history_note: HistoryNote;
  primary_observable: PrimaryObservable;
  parameters: Parameters;
}
export interface Parameters {
  [k: string]: unknown;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "BoundaryInfo".
 */
export interface BoundaryInfo {
  state: State;
  review_status: ReviewStatus;
  source: Source;
  source_date: SourceDate;
  license: License;
  area_km2: AreaKm2;
  position_uncertainty: Measurement;
  classes: Classes;
  automated_checks: AutomatedChecks;
  needed_for_next_state: NeededForNextState;
  legal_claim: LegalClaim;
  geojson: Geojson;
  review_file: ReviewFile;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Measurement".
 */
export interface Measurement {
  value: Value;
  unit: Unit;
  status: Status1;
  uncertainty?: Uncertainty | null;
  reason?: Reason;
}
/**
 * Statistical uncertainty of one measured value.
 *
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Uncertainty".
 */
export interface Uncertainty {
  kind: Kind;
  low?: Low;
  high?: High;
  value?: Value1;
  level?: Level;
  method?: Method;
  block_m?: BlockM;
  n_blocks?: NBlocks;
  block_size_sensitivity?: BlockSizeSensitivity;
}
export interface Classes {
  [k: string]: string;
}
export interface AutomatedChecks {
  [k: string]: unknown;
}
export interface NeededForNextState {
  [k: string]: string[];
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Zone".
 */
export interface Zone {
  id: Id2;
  role: Role;
  area_km2: AreaKm21;
  source: Source1;
  source_date: SourceDate1;
  license: License1;
  attribution: Attribution;
  nature?: Nature;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "GcovAcquisition".
 */
export interface GcovAcquisition {
  acquisition_id: AcquisitionId;
  granule_id: GranuleId;
  collection: Collection;
  maturity: Maturity;
  crid: Crid;
  geometry_id: GeometryId;
  direction: Direction;
  track: Track;
  frame: Frame;
  time_utc: TimeUtc;
  product_version: ProductVersion;
  specification_version: SpecificationVersion;
  software_version: SoftwareVersion;
  processing_datetime: ProcessingDatetime;
  doi: Doi;
  source_url: SourceUrl;
  bytes_transferred: BytesTransferred;
  polarizations: Polarizations;
  native_spacing_m: NativeSpacingM;
  analysis_spacing_m: AnalysisSpacingM;
  observation_mode: ObservationMode;
  noise_correction_applied: NoiseCorrectionApplied;
  rtc_applied: RtcApplied;
  normalization: Normalization;
  has_input_data_exception: HasInputDataException;
  median_looks: Measurement;
  noise_floor_db: NoiseFloorDb;
  median_incidence_deg: Measurement;
  observed_fraction_study: ObservedFractionStudy;
  files: Files;
  status: Status2;
  reasons: Reasons;
  calibration_caveat_keys: CalibrationCaveatKeys;
}
export interface NoiseFloorDb {
  [k: string]: Measurement;
}
export interface ObservedFractionStudy {
  [k: string]: Measurement;
}
export interface Files {
  [k: string]: string;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "BatchInfo".
 */
export interface BatchInfo {
  batch_id: BatchId;
  role: Role1;
  collection: Collection1;
  crid: Crid1;
  geometry_id: GeometryId1;
  direction: Direction1;
  n_acquisitions: NAcquisitions;
  n_usable: NUsable;
  n_windows: NWindows;
  n_windows_computed: NWindowsComputed;
  dates: Dates;
  gaps: Gaps;
  note_keys: NoteKeys;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "ChangeWindow".
 */
export interface ChangeWindow {
  window_id: WindowId;
  batch_id: BatchId1;
  role: Role2;
  geometry_id: GeometryId2;
  direction: Direction2;
  before_id: BeforeId;
  after_id: AfterId;
  before_date: BeforeDate;
  after_date: AfterDate;
  span_days: SpanDays;
  status: Status3;
  reasons: Reasons1;
  pols: Pols;
  quality_layer_id: QualityLayerId;
  optical: Optical;
  gunw_context?: GunwContext;
  development_window?: DevelopmentWindow;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "PolChange".
 */
export interface PolChange {
  pol: Pol;
  primary: Primary;
  status: Status4;
  reasons: Reasons2;
  zones: Zones1;
  study_minus_control_db: Measurement;
  baseline: BaselineState;
  flags: FlagSummary | null;
  layer_ids: LayerIds;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "ZoneChange".
 */
export interface ZoneChange {
  zone_id: ZoneId;
  observed_fraction: Measurement;
  aggregate_db: Measurement;
  median_cell_db: Measurement;
  p05_db: Measurement;
  p95_db: Measurement;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "BaselineState".
 */
export interface BaselineState {
  status: Status5;
  n_pairs: NPairs;
  pair_ids: PairIds;
  reason?: Reason1;
  centre_db?: Measurement | null;
  sigma_db?: Measurement | null;
  k_sigma?: KSigma;
  calibration_rate?: Measurement | null;
  evaluation_rate?: Measurement | null;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "FlagSummary".
 */
export interface FlagSummary {
  study_fraction: Measurement;
  control_fraction: Measurement;
  ratio: Measurement;
  study_flagged_area_km2: Measurement;
  darker_area_km2: Measurement;
  brighter_area_km2: Measurement;
  ratio_block_sensitivity: RatioBlockSensitivity;
}
export interface RatioBlockSensitivity {
  [k: string]: number[] | null;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "OpticalComparison".
 */
export interface OpticalComparison {
  mode: Mode;
  max_gap_days: MaxGapDays;
  status: Status6;
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
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "QualityRow".
 */
export interface QualityRow {
  window_id: WindowId1;
  pol: Pol1;
  zone_id: ZoneId1;
  observed_fraction: Measurement;
  reasons: Reasons3;
}
export interface Reasons3 {
  [k: string]: Measurement;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
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
  reason?: Reason3;
}
/**
 * Counts of independent supports, derived from the recorded comparisons (never typed by hand).
 *
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "EvidenceSummary".
 */
export interface EvidenceSummary {
  derived_at_read?: DerivedAtRead;
  optical?: Optical1;
  references?: References;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "OpticalEvidence".
 */
export interface OpticalEvidence {
  mode: Mode1;
  n_radar_comparisons: NRadarComparisons;
  n_attempted: NAttempted;
  n_unique_optical_pairs: NUniqueOpticalPairs;
  n_groups_ci_above_1: NGroupsCiAbove1;
  groups: Groups;
  note_key?: NoteKey;
}
/**
 * Radar comparisons that rely on the same pair of optical scenes: one temporal reference, not several.
 *
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "OpticalGroup".
 */
export interface OpticalGroup {
  group_id: GroupId;
  before_item: BeforeItem1;
  after_item: AfterItem1;
  before_datetime?: BeforeDatetime1;
  after_datetime?: AfterDatetime1;
  pair_ids: PairIds1;
  n_ci_above_1: NCiAbove1;
}
/**
 * A structured independent reference (field observation or dated, geolocated annotation).
 *
 * A text marker is not a reference: `effective()` states what a reference must carry before it can support the
 * level `independently_validated`. Every field is recorded; none is inferred.
 *
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "ReferenceEvidence".
 */
export interface ReferenceEvidence {
  id: Id3;
  kind: Kind1;
  observable: Observable;
  source: Source2;
  reviewer?: Reviewer;
  reviewer_independent?: ReviewerIndependent;
  blind_to_radar?: BlindToRadar;
  method?: Method1;
  rights?: Rights;
  date_start?: DateStart;
  date_end?: DateEnd;
  geometry_ref?: GeometryRef;
  n_units_flagged?: NUnitsFlagged;
  n_units_unflagged?: NUnitsUnflagged;
  n_units_indeterminate?: NUnitsIndeterminate;
  n_independent_groups?: NIndependentGroups;
  sampling_probabilities_recorded?: SamplingProbabilitiesRecorded;
  evaluation?: Evaluation;
  limits?: Limits;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "ReferenceState".
 */
export interface ReferenceState {
  status: Status7;
  unit_definition: UnitDefinition;
  sampling_file: SamplingFile;
  annotation_template: AnnotationTemplate;
  n_units_sampled: NUnitsSampled;
  n_annotated: NAnnotated;
  n_indeterminate: NIndeterminate;
  evaluation: Evaluation1;
  missing: Missing;
}
export interface NUnitsSampled {
  [k: string]: number;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Reference".
 */
export interface Reference {
  id: Id4;
  kind: Kind2;
  name: Name1;
  provider: Provider;
  license: License2;
  url: Url;
  dates?: Dates1;
  supports_key: SupportsKey;
  cannot_support_key: CannotSupportKey;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "ZoneConclusion".
 */
export interface ZoneConclusion {
  zone_id: ZoneId2;
  label_key: LabelKey;
  centroid: Centroid1;
  area_km2: AreaKm22;
  radar_variation: RadarVariation;
  radar_params: RadarParams;
  optical_visible_change: OpticalVisibleChange;
  optical_params: OpticalParams;
  documented_cause?: DocumentedCause;
  cause_undetermined?: CauseUndetermined;
  alternative_keys: AlternativeKeys;
  to_collect_keys: ToCollectKeys;
  window_ids: WindowIds;
}
export interface RadarParams {
  [k: string]: boolean | number | string | unknown[] | null;
}
export interface OpticalParams {
  [k: string]: boolean | number | string | unknown[] | null;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Finding".
 */
export interface Finding {
  id: Id5;
  kind: Kind3;
  params: Params;
  evidence: Evidence;
  limit_keys?: LimitKeys;
}
export interface Params {
  [k: string]: boolean | number | string | unknown[] | null;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Layer".
 */
export interface Layer {
  id: Id6;
  kind: Kind4;
  title_key: TitleKey;
  params?: Params1;
  url: Url1;
  corners: Corners;
  legend: Legend;
  date_start?: DateStart1;
  date_end?: DateEnd1;
  source_ids?: SourceIds;
  resolution_m?: ResolutionM;
  export?: Export;
  display_note_key?: DisplayNoteKey;
}
export interface Params1 {
  [k: string]: boolean | number | string | null;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Legend".
 */
export interface Legend {
  kind: Kind5;
  unit?: Unit1;
  vmin?: Vmin;
  vmax?: Vmax;
  cmap?: Cmap;
  stops?: Stops;
  levels?: Levels;
  classes?: Classes1;
  class_keys?: ClassKeys;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Export".
 */
export interface Export1 {
  id: Id7;
  format: Format;
  path: Path;
  description_key: DescriptionKey1;
  sha256: Sha2561;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Processing".
 */
export interface Processing {
  status: Status8;
  rule: Rule;
  steps: Steps;
  blockers?: Blockers;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "Step".
 */
export interface Step {
  name: Name2;
  required: Required;
  status: Status9;
  message?: Message;
}
/**
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
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
 * This interface was referenced by `SurfaceStudy`'s JSON-Schema
 * via the `definition` "FileRecord".
 */
export interface FileRecord {
  path: Path1;
  sha256: Sha2562;
  role: Role3;
  declared_sha256?: DeclaredSha256;
}
