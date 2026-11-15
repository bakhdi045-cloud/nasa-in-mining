"""`MiningCase` contract shared by the pipeline, the API and the web interface (new module).

Conventions kept explicit by validators:
- a value that is absent is `null` with a `status` other than "measured" and a `reason`;
- a measured zero is a real observation (`status: "measured"`, `value: 0`);
- `uncertainty: null` means "not estimated or not provided"; an uncertainty of 0 must say how it was obtained;
- processing state (did the computation run?) is separate from validation level (what supports the result?).
User-facing sentences are composed by the interface from structured fields, so displayed numbers are the
numbers of this file.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Uncertainty(Strict):
    kind: Literal["not_estimated", "sensitivity_range", "empirical_sigma", "not_applicable"]
    value: float | None = None
    low: float | None = None
    high: float | None = None
    method: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "empirical_sigma" and (self.value is None or self.method is None):
            raise ValueError("an empirical sigma needs a value and a method")
        if self.kind == "sensitivity_range" and (self.low is None or self.high is None or self.method is None):
            raise ValueError("a sensitivity range needs low, high and a method")
        if self.kind in ("not_estimated", "not_applicable") and any(v is not None for v in (self.value, self.low, self.high)):
            raise ValueError("a non-estimated uncertainty carries no number")
        return self


class Measurement(Strict):
    value: float | None
    unit: str
    status: Literal["measured", "not_measured", "unavailable", "not_applicable"]
    uncertainty: Uncertainty | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.status == "measured" and self.value is None:
            raise ValueError("a measured value cannot be null")
        if self.status != "measured" and self.value is not None:
            raise ValueError("only a measured value carries a number")
        if self.value is None and not self.reason:
            raise ValueError("an absent value needs a reason")
        return self


def measured(value: float, unit: str, uncertainty: Uncertainty | None = None) -> Measurement:
    return Measurement(value=float(value), unit=unit, status="measured", uncertainty=uncertainty)


def absent(unit: str, reason: str, status: str = "unavailable") -> Measurement:
    return Measurement(value=None, unit=unit, status=status, reason=reason)


class Site(Strict):
    id: str
    name: str
    country: str
    commodity: str
    operator: str | None = None
    centroid: tuple[float, float]           # lon, lat
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


class LayerFile(Strict):
    name: str
    sha256: str
    spacing_m: list[float] | None = None
    units: str | None = None


class PairQuality(Strict):
    ok: bool
    reasons: list[str]
    phase_sigma_rad: float | None
    coherence_median: float | None


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
    processing_datetime: str | None
    doi: str | None
    source_url: str
    bytes_transferred: int | None
    layers: list[LayerFile]
    looks: dict[str, int | None]
    quality: PairQuality


class OpticalScene(Strict):
    item_id: str
    datetime: str
    platform: str | None
    processing_baseline: str | None
    cloud_cover_pct: float | None
    valid_fraction_window: float


class Method(Strict):
    id: str
    version: str
    parameters: dict[str, float | int | str | bool | list | None]
    reused_modules: list[str]
    steps: list[str]


class ZoneMetrics(Strict):
    zone_id: str
    zone_area_km2: float
    observable_area_km2: Measurement
    observable_fraction: Measurement
    flagged_area_km2: Measurement
    flagged_fraction_of_observable: Measurement
    median_coherence: Measurement


class Cluster(Strict):
    id: int
    area_km2: float
    centroid: tuple[float, float]
    median_coherence: float
    recurrence_in_other_pairs: float | None = None
    optical_change_fraction: float | None = None
    optical_diagnostics: dict[str, float | str | None] | None = None


class OpticalComparison(Strict):
    status: Literal["ok", "no_scene_pair", "insufficient_overlap"]
    before_item: str | None
    after_item: str | None
    gap_days_before: float | None
    gap_days_after: float | None
    optical_threshold: Measurement
    lift: Measurement
    p_optical_given_radar: Measurement
    p_optical_given_not_radar: Measurement
    jaccard: Measurement
    control_median_d_ndvi: Measurement | None = None
    control_median_d_mndwi: Measurement | None = None
    reason: str | None = None


class PairResult(Strict):
    pair_id: str
    geometry_id: str
    reference_date: str
    secondary_date: str
    span_days: int
    status: Literal["ok", "rejected_quality", "insufficient_control", "incompatible_grid"]
    reason: str | None = None
    threshold: Measurement
    threshold_sensitivity: dict[str, Measurement]
    control_flag_rate: Measurement
    control_median_coherence: Measurement
    zones: list[ZoneMetrics]
    study_flagged_area_sensitivity: dict[str, Measurement]
    n_clusters: int | None
    clusters_shown: list[Cluster]
    layer_ids: list[str]
    optical: OpticalComparison | None


class GeometrySummary(Strict):
    geometry_id: str
    direction: str
    track: int
    frame: int
    crid: str
    n_pairs: int
    n_pairs_used: int
    recurrence_pairs: list[str]
    recurrence_layer_id: str | None
    study_area_flagged_ever_km2: Measurement
    study_area_flagged_half_or_more_km2: Measurement


class CrossGeometry(Strict):
    status: Literal["ok", "unavailable"]
    spearman_recurrence_study: Measurement
    lift_frequent_change: Measurement
    jaccard_frequent_change: Measurement
    frequent_threshold: float
    reason: str | None = None


class LosPair(Strict):
    pair_id: str
    status: Literal["ok", "insufficient_data", "not_computed"]
    reference: str
    control_sigma_cm: Measurement
    study_median_cm: Measurement
    study_p05_cm: Measurement
    study_p95_cm: Measurement
    study_coherent_fraction: Measurement
    area_beyond_3sigma_km2: Measurement
    layer_id: str | None
    sign_verified: bool
    reason: str | None = None


class Legend(Strict):
    kind: Literal["continuous", "categorical", "rgb"]
    unit: str | None = None
    vmin: float | None = None
    vmax: float | None = None
    cmap: str | None = None
    stops: list[str] | None = None
    classes: dict[str, list[int]] | None = None
    class_keys: dict[str, str] | None = None


class Layer(Strict):
    id: str
    kind: Literal["observation", "derived", "reference", "basemap", "zones"]
    title_key: str
    params: dict[str, str | int | float | None] = Field(default_factory=dict)
    url: str
    corners: list[list[float]] | None = None
    legend: Legend | None = None
    date_start: str | None = None
    date_end: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    resolution_m: float | None = None
    export: str | None = None


class Reference(Strict):
    id: str
    kind: Literal["optical_imagery", "map", "documentation"]
    name: str
    provider: str
    license: str
    url: str
    dates: list[str] = Field(default_factory=list)
    supports_key: str
    cannot_support_key: str


class ValidationItem(Strict):
    observable: str
    level: Literal["not_computed", "computed", "internally_consistent", "consistent_with_independent_source",
                   "independently_validated"]
    evidence_keys: list[str]
    missing_keys: list[str]


class Finding(Strict):
    id: str
    kind: str
    params: dict[str, bool | float | int | str | None | list]
    evidence: list[str]


class NextCheck(Strict):
    id: str
    kind: str
    params: dict[str, bool | float | int | str | None | list]
    because: list[str]


class Step(Strict):
    name: str
    status: Literal["done", "skipped", "failed", "unavailable"]
    message: str | None = None


class Processing(Strict):
    status: Literal["complete", "partial", "unavailable", "failed"]
    steps: list[Step]
    blockers: list[str] = Field(default_factory=list)


class FileRecord(Strict):
    path: str
    sha256: str
    role: str | None = None


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


class Export(Strict):
    id: str
    format: Literal["csv", "geojson", "geotiff", "json"]
    path: str
    description_key: str
    sha256: str


class MiningCase(Strict):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    case_id: str
    data_nature: Literal["real", "synthetic"]
    question_key: str
    user_key: str
    site: Site
    zones: list[Zone]
    zones_url: str
    acquisitions: list[Acquisition]
    optical_scenes: list[OpticalScene]
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
    next_checks: list[NextCheck]
    limits: list[str]
    processing: Processing
    manifest: Manifest | None

    @model_validator(mode="after")
    def _links(self):
        layer_ids = {layer.id for layer in self.layers}
        pair_ids = {a.pair_id for a in self.acquisitions}
        for p in self.pairs:
            if p.pair_id not in pair_ids:
                raise ValueError(f"result {p.pair_id} has no acquisition record")
            missing = [lid for lid in p.layer_ids if lid not in layer_ids]
            if missing:
                raise ValueError(f"result {p.pair_id} refers to unknown layers {missing}")
        return self


def unavailable_case(case_id: str, site: Site, zones: list[Zone], zones_url: str, method: Method,
                     references: list[Reference], blockers: list[str], steps: list[Step],
                     data_nature: str = "real") -> MiningCase:
    """A complete, valid case that states that no observation could be made (never 'no change')."""
    na = absent("1", "no observation could be made", "unavailable")
    return MiningCase(case_id=case_id, data_nature=data_nature, question_key="question.coherence_change",
                      user_key="user.monitoring_analyst", site=site, zones=zones, zones_url=zones_url,
                      acquisitions=[], optical_scenes=[], method=method, pairs=[], geometries=[],
                      cross_geometry=CrossGeometry(status="unavailable", spearman_recurrence_study=na,
                                                   lift_frequent_change=na, jaccard_frequent_change=na,
                                                   frequent_threshold=0.5, reason="no radar pair available"),
                      los=[], layers=[], exports=[], references=references,
                      validation=[ValidationItem(observable="coherence_change", level="not_computed",
                                                 evidence_keys=[], missing_keys=["missing.radar_products"])],
                      findings=[], next_checks=[], limits=["limit.no_data_is_not_no_change"],
                      processing=Processing(status="unavailable", steps=steps, blockers=blockers), manifest=None)
