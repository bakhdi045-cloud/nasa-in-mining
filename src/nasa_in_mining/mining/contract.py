"""`MiningCase` contract v2, shared by the pipeline, the API and the web interface.

Conventions enforced by validators:
- every number is finite; a fraction (unit "fraction") lies in [0, 1];
- an absent value is `null` with a status other than "measured" and a reason; a measured zero is an observation;
- `uncertainty: null` means "not estimated"; an estimated uncertainty states its kind and method, and an interval
  has low <= high; statistical uncertainty, threshold sensitivity, control sensitivity and perimeter uncertainty
  are separate objects;
- processing state (did a step run?) is separate from the evidence level (what supports a statement?);
- references between objects (pairs, layers, exports, findings, zones) must resolve.
User-facing sentences are composed by the interface from structured fields: a displayed number is a number of
this file.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "2.0"
Scalar = bool | int | float | str | None


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _finite(v):
    if isinstance(v, float) and not math.isfinite(v):
        raise ValueError("numbers must be finite")
    return v


class Uncertainty(Strict):
    """Statistical uncertainty of one measured value."""
    kind: Literal["not_estimated", "block_bootstrap_interval", "empirical_sigma"]
    low: float | None = None
    high: float | None = None
    value: float | None = None
    level: float | None = None
    method: str | None = None
    block_m: float | None = None
    n_blocks: int | None = None
    block_size_sensitivity: dict[str, list[float]] | None = None

    @field_validator("low", "high", "value", "level", "block_m")
    @classmethod
    def _finite_numbers(cls, v):
        return _finite(v)

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "not_estimated":
            if any(x is not None for x in (self.low, self.high, self.value)):
                raise ValueError("a non-estimated uncertainty carries no number")
            if not self.method:
                raise ValueError("say why the uncertainty is not estimated")
        if self.kind == "block_bootstrap_interval":
            if self.low is None or self.high is None or self.low > self.high or not self.method or not self.block_m:
                raise ValueError("a bootstrap interval needs low <= high, a block size and a method")
        if self.kind == "empirical_sigma" and (self.value is None or self.value < 0 or not self.method):
            raise ValueError("an empirical sigma needs a non-negative value and a method")
        return self


class Measurement(Strict):
    value: float | None
    unit: str
    status: Literal["measured", "not_measured", "unavailable", "not_applicable"]
    uncertainty: Uncertainty | None = None
    reason: str | None = None

    @field_validator("value")
    @classmethod
    def _finite_value(cls, v):
        return _finite(v)

    @model_validator(mode="after")
    def _check(self):
        if self.status == "measured" and self.value is None:
            raise ValueError("a measured value cannot be null")
        if self.status != "measured" and (self.value is not None or self.uncertainty is not None):
            raise ValueError("only a measured value carries a number or an uncertainty")
        if self.value is None and not self.reason:
            raise ValueError("an absent value needs a reason")
        if self.unit == "fraction" and self.value is not None and not 0 <= self.value <= 1:
            raise ValueError(f"a fraction must lie in [0, 1], got {self.value}")
        if self.unit in ("km2", "count", "pixels") and self.value is not None and self.value < 0:
            raise ValueError("an area or a count cannot be negative")
        return self


def measured(value: float, unit: str, uncertainty: Uncertainty | None = None) -> Measurement:
    return Measurement(value=float(value), unit=unit, status="measured", uncertainty=uncertainty)


def absent(unit: str, reason: str, status: str = "unavailable") -> Measurement:
    return Measurement(value=None, unit=unit, status=status, reason=reason)


def maybe(value, unit: str, reason: str, status: str = "not_measured", uncertainty: Uncertainty | None = None) -> Measurement:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return absent(unit, reason, status)
    return measured(value, unit, uncertainty)


class Site(Strict):
    id: str
    name: str
    country: str
    commodity: str
    operator: str | None = None
    centroid: tuple[float, float]
    description_key: str


class Zone(Strict):
    id: str
    role: Literal["study_perimeter", "control_ring", "mapped_mining_outside_perimeter", "exclusion"]
    area_km2: float | None
    source: str
    source_date: str | None
    license: str
    attribution: str
    nature: str | None = None


class PerimeterVersion(Strict):
    id: str
    label: str
    source: str
    source_date: str | None
    area_km2: float
    used_as: Literal["main", "sensitivity", "context"]
    note: str


class LayerFile(Strict):
    name: str
    sha256: str
    spacing_m: list[float] | None = None
    units: str | None = None


class QualityCheck(Strict):
    ok: bool
    reasons: list[str]
    metrics: dict[str, Scalar]


class Acquisition(Strict):
    pair_id: str
    granule_id: str
    collection: str
    crid: str
    maturity: str
    geometry_id: str
    direction: Literal["ascending", "descending"]
    track: int
    frame: int
    reference_time: str
    secondary_time: str
    span_days: int
    product_version: str | None
    product_specification_version: str | None
    software_version: str | None
    processing_datetime: str | None
    doi: str | None
    source_url: str
    bytes_transferred: int | None
    layers: list[LayerFile]
    looks: dict[str, int | None]
    coherence_qc: QualityCheck
    phase_qc: QualityCheck


class OpticalScene(Strict):
    item_id: str
    datetime: str
    platform: str | None
    processing_baseline: str | None
    cloud_cover_pct_tile: float | None
    clear_fraction_study: float
    clear_fraction_control: float
    doubtful_fraction_study: float
    usable: bool
    reason: str | None = None


class ControlDef(Strict):
    id: str
    label_key: str
    description: str
    pixels: int
    area_km2: float
    landcover_share: dict[str, float]


class Method(Strict):
    id: str
    version: str
    observable_key: str
    parameters: dict[str, Scalar | list]
    controls: list[ControlDef]
    main_profile: str
    reused_modules: list[str]
    steps: list[str]
    autocorrelation: dict[str, float | None]
    block_size_justification: str


class ZoneMetrics(Strict):
    zone_id: str
    zone_area_km2: float
    observable_area_km2: Measurement
    observable_fraction: Measurement
    flagged_area_km2: Measurement
    flagged_fraction: Measurement
    median_coherence: Measurement


class Profile(Strict):
    """Result of one (control, quantile) profile for one pair."""
    id: str
    control_id: str
    quantile: float
    threshold: Measurement
    calibration_rate: Measurement
    evaluation_rate: Measurement
    study_flagged_area_km2: Measurement
    study_flagged_fraction: Measurement
    ratio_to_evaluation_rate: Measurement
    exceeds_control: bool | None


class Cluster(Strict):
    id: int
    area_km2: float
    centroid: tuple[float, float]
    median_coherence: float
    pairs_same_geometry_overlapping: int | None = None
    pairs_same_geometry_observed: int | None = None
    retained_at_lower_quantile: bool | None = None


class OpticalComparison(Strict):
    mode: Literal["strict", "exploratory"]
    max_gap_days: float
    status: Literal["ok", "no_scene_pair", "insufficient_overlap"]
    reason: str | None = None
    before_item: str | None = None
    before_datetime: str | None = None
    after_item: str | None = None
    after_datetime: str | None = None
    gap_days_before: float | None = None
    gap_days_after: float | None = None
    radar_window: list[str]
    optical_window: list[str] | None = None
    joint_observable_fraction: Measurement
    optical_threshold: Measurement
    table: dict[str, int] | None = None
    p_optical_given_radar: Measurement
    p_optical_given_not_radar: Measurement
    association_ratio: Measurement
    jaccard: Measurement
    share_of_optical_change_in_radar_flags: Measurement
    ratio_with_unclassified_scl: Measurement
    control_median_d_mndwi: Measurement
    spectral_hypotheses: dict[str, int] | None = None


class PairResult(Strict):
    pair_id: str
    geometry_id: str
    direction: Literal["ascending", "descending"]
    reference_date: str
    secondary_date: str
    span_days: int
    status: Literal["ok", "rejected_coherence_qc", "insufficient_control", "incompatible_grid"]
    reasons: list[str]
    main: ZoneMetrics | None
    zones: list[ZoneMetrics]
    profiles: list[Profile]
    statistical: Measurement
    perimeter_sensitivity: dict[str, Measurement]
    zone_stability: dict[str, Measurement]
    n_clusters: int | None
    clusters_shown: list[Cluster]
    layer_ids: list[str]
    optical: list[OpticalComparison]

    @model_validator(mode="after")
    def _states(self):
        if self.status == "ok" and (self.main is None or self.main.flagged_area_km2.status != "measured"):
            raise ValueError(f"{self.pair_id}: an analysed pair must carry measured perimeter values")
        if self.status != "ok" and (self.main is not None or self.profiles or not self.reasons):
            raise ValueError(f"{self.pair_id}: a pair that was not analysed carries no values and states why")
        return self


class Recurrence(Strict):
    geometry_id: str
    span_days: int
    pair_ids: list[str]
    gaps: list[list[str]]
    layer_id: str | None
    count_layer_id: str | None
    observed_pairs_min: int | None
    observed_pairs_max: int | None
    flagged_ever_km2: Measurement
    flagged_half_or_more_km2: Measurement
    disjoint_pairs: list[str]
    flagged_half_or_more_disjoint_km2: Measurement
    jaccard_adjacent_pairs: Measurement
    jaccard_pairs_two_apart: Measurement


class GeometrySummary(Strict):
    geometry_id: str
    direction: str
    track: int
    frame: int
    crid: str
    n_pairs: int
    n_pairs_analysed: int
    recurrence: list[Recurrence]


class WindowMatch(Strict):
    pair_a: str
    pair_b: str
    overlap_days: float
    table: dict[str, int]
    association_ratio: Measurement
    jaccard: Measurement
    p_b_given_a: Measurement


class CrossGeometry(Strict):
    status: Literal["ok", "unavailable"]
    rule: str
    matches: list[WindowMatch]
    unmatched: list[str]
    median_jaccard: Measurement
    reason: str | None = None


class LosPair(Strict):
    pair_id: str
    status: Literal["computed", "not_computed", "insufficient_data"]
    phase_qc_ok: bool
    control_sigma_cm: Measurement
    study_p05_cm: Measurement
    study_p95_cm: Measurement
    within_3sigma: bool | None
    layer_id: str | None
    sign_verified: bool
    interpreted: Literal[False] = False
    reason: str | None = None


class Legend(Strict):
    kind: Literal["continuous", "categorical", "rgb"]
    unit: str | None = None
    vmin: float | None = None
    vmax: float | None = None
    cmap: str | None = None
    stops: list[str] | None = None
    levels: int | None = None
    classes: dict[str, list[int]] | None = None
    class_keys: dict[str, str] | None = None


class Layer(Strict):
    id: str
    kind: Literal["observation", "derived", "reference", "basemap"]
    title_key: str
    params: dict[str, Scalar] = Field(default_factory=dict)
    url: str
    corners: list[list[float]]
    legend: Legend
    date_start: str | None = None
    date_end: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    resolution_m: float | None = None
    export: str | None = None
    display_note_key: str | None = None


class Reference(Strict):
    id: str
    kind: Literal["optical_imagery", "map", "land_cover", "documentation"]
    name: str
    provider: str
    license: str
    url: str
    dates: list[str] = Field(default_factory=list)
    supports_key: str
    cannot_support_key: str


class ValidationItem(Strict):
    observable: str
    level: Literal["not_computed", "computed", "internally_cross_checked", "associated_with_independent_observation",
                   "independently_validated"]
    criteria: list[str]
    evidence_keys: list[str]
    missing_keys: list[str]


class Finding(Strict):
    id: str
    kind: str
    params: dict[str, Scalar | list]
    evidence: list[str]
    limit_keys: list[str] = Field(default_factory=list)


class Dossier(Strict):
    """Verification sheet for one zone: what was observed, what supports it, what else could explain it."""
    id: str
    centroid: tuple[float, float]
    area_km2: float
    zone: str
    landcover: str | None
    observation: dict[str, Scalar]
    evidence: list[str]
    alternative_keys: list[str]
    to_collect_keys: list[str]
    dates: list[list[str]]


class NextCheck(Strict):
    id: str
    kind: str
    params: dict[str, Scalar | list]
    because: list[str]


class Step(Strict):
    name: str
    required: bool
    status: Literal["done", "skipped", "failed", "unavailable", "partial"]
    message: str | None = None


class Processing(Strict):
    status: Literal["complete", "partial", "unavailable", "failed"]
    rule: str
    steps: list[Step]
    blockers: list[str] = Field(default_factory=list)


class FileRecord(Strict):
    path: str
    sha256: str
    role: str
    declared_sha256: str | None = None


class Manifest(Strict):
    run_id: str
    created_utc: str
    code_commit: str | None
    code_dirty: bool | None
    python: str
    packages: dict[str, str | None]
    config_sha256: str
    inputs: list[FileRecord]
    outputs: list[FileRecord]
    duration_s: float

    @model_validator(mode="after")
    def _integrity(self):
        bad = [f.path for f in self.inputs if f.declared_sha256 and f.declared_sha256 != f.sha256]
        if bad:
            raise ValueError(f"inputs differ from their declared fingerprints: {bad[:3]}")
        return self


class Export(Strict):
    id: str
    format: Literal["csv", "geojson", "geotiff", "json", "markdown"]
    path: str
    description_key: str
    sha256: str


class MiningCase(Strict):
    schema_version: Literal["2.0"] = SCHEMA_VERSION
    case_id: str
    run_id: str
    data_nature: Literal["real", "synthetic"]
    presentation_level_key: str
    question_key: str
    user_key: str
    site: Site
    zones: list[Zone]
    perimeter_versions: list[PerimeterVersion]
    zones_url: str
    acquisitions: list[Acquisition]
    optical_scenes: list[OpticalScene]
    optical_search: dict[str, Scalar]
    method: Method
    pairs: list[PairResult]
    geometries: list[GeometrySummary]
    cross_geometry: CrossGeometry
    los: list[LosPair]
    layers: list[Layer]
    exports: list[Export]
    references: list[Reference]
    validation: list[ValidationItem]
    findings: list[Finding]
    dossiers: list[Dossier]
    next_checks: list[NextCheck]
    limits: list[str]
    processing: Processing
    manifest: Manifest | None

    @model_validator(mode="after")
    def _links(self):
        layers = {x.id for x in self.layers}
        pairs = {a.pair_id for a in self.acquisitions}
        findings = {f.id for f in self.findings}
        dossiers = {d.id for d in self.dossiers}
        if len(layers) != len(self.layers):
            raise ValueError("duplicate layer ids")
        for p in self.pairs:
            if p.pair_id not in pairs:
                raise ValueError(f"result {p.pair_id} has no acquisition record")
            missing = [lid for lid in p.layer_ids if lid not in layers]
            if missing:
                raise ValueError(f"result {p.pair_id} refers to unknown layers {missing}")
        for g in self.geometries:
            for r in g.recurrence:
                for lid in (r.layer_id, r.count_layer_id):
                    if lid and lid not in layers:
                        raise ValueError(f"recurrence refers to unknown layer {lid}")
                if not set(r.pair_ids) <= pairs:
                    raise ValueError("recurrence refers to unknown pairs")
        for m in self.cross_geometry.matches:
            if m.pair_a not in pairs or m.pair_b not in pairs:
                raise ValueError("a window match refers to unknown pairs")
        known = pairs | layers | findings | dossiers | {e.id for e in self.exports}
        for f in self.findings:
            unknown = [e for e in f.evidence if e not in known]
            if unknown:
                raise ValueError(f"finding {f.id} cites unknown evidence {unknown}")
        for c in self.next_checks:
            unknown = [b for b in c.because if b not in findings and b not in dossiers and not b.startswith("limit.")]
            if unknown:
                raise ValueError(f"next check {c.id} cites unknown findings {unknown}")
        if self.processing.status == "unavailable" and self.pairs:
            raise ValueError("an unavailable case carries no pair result")
        for v in self.validation:
            if v.level == "independently_validated" and "evidence.field_truth" not in v.evidence_keys:
                raise ValueError("independent validation requires recorded field truth")
        return self
