"""`SurfaceStudy` contract 3.0: backscatter-change study of the Benguerir mine (new method, separate from MiningCase 2.x).

Same conventions as the MiningCase contract: finite numbers, an absent value is null with a status and a reason,
processing state is separate from the level of evidence, references between objects must resolve. A reference
is only "effective" when it carries the structured fields listed in ReferenceEvidence.missing(); nothing here
can be turned into "validated" by a label.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from ..mining.contract import (EvidenceSummary, Export, Layer, Manifest, Measurement, OpticalComparison, OpticalScene,
                               Processing, Reference, ReferenceEvidence, Scalar, Site, Strict, Zone, absent, maybe,
                               measured)

STUDY_SCHEMA_VERSION = "3.0"

__all__ = ["SurfaceStudy", "STUDY_SCHEMA_VERSION", "absent", "maybe", "measured"]


class ProtocolInfo(Strict):
    id: str
    version: str
    frozen_utc: str
    status: str
    sha256: str
    history_note: str
    primary_observable: str
    parameters: dict[str, Any]


class BoundaryInfo(Strict):
    state: Literal["historical_map", "draft_interpretation", "remote_sensing_reviewed", "operator_confirmed"]
    review_status: Literal["pending_human_review", "recorded"]
    source: str
    source_date: str | None
    license: str | None
    area_km2: float
    position_uncertainty: Measurement
    classes: dict[str, str]
    automated_checks: dict[str, Any]
    needed_for_next_state: dict[str, list[str]]
    legal_claim: str
    geojson: str
    review_file: str


class GcovAcquisition(Strict):
    acquisition_id: str
    granule_id: str
    collection: str
    maturity: Literal["provisional", "validated"]
    crid: str
    geometry_id: str
    direction: Literal["ascending", "descending"]
    track: int
    frame: int
    time_utc: str
    product_version: str | None
    specification_version: str | None
    software_version: str | None
    processing_datetime: str | None
    doi: str | None
    source_url: str
    bytes_transferred: int | None
    polarizations: list[str]
    native_spacing_m: float
    analysis_spacing_m: float
    observation_mode: str | None
    noise_correction_applied: bool | None
    rtc_applied: bool | None
    normalization: str | None
    has_input_data_exception: bool | None
    median_looks: Measurement
    noise_floor_db: dict[str, Measurement]
    median_incidence_deg: Measurement
    observed_fraction_study: dict[str, Measurement]
    files: dict[str, str]
    status: Literal["usable", "rejected"]
    reasons: list[str]
    calibration_caveat_keys: list[str]


class ZoneChange(Strict):
    zone_id: str
    observed_fraction: Measurement
    aggregate_db: Measurement
    median_cell_db: Measurement
    p05_db: Measurement
    p95_db: Measurement


class BaselineState(Strict):
    status: Literal["ok", "insufficient_baseline", "not_applicable"]
    n_pairs: int
    pair_ids: list[str]
    reason: str | None = None
    centre_db: Measurement | None = None
    sigma_db: Measurement | None = None
    k_sigma: float | None = None
    calibration_rate: Measurement | None = None
    evaluation_rate: Measurement | None = None


class FlagSummary(Strict):
    study_fraction: Measurement
    control_fraction: Measurement
    ratio: Measurement
    study_flagged_area_km2: Measurement
    darker_area_km2: Measurement
    brighter_area_km2: Measurement
    ratio_block_sensitivity: dict[str, list[float] | None]


class PolChange(Strict):
    pol: str
    primary: bool
    status: Literal["computed", "unavailable", "insufficient_coverage"]
    reasons: list[str]
    zones: list[ZoneChange]
    study_minus_control_db: Measurement
    baseline: BaselineState
    flags: FlagSummary | None
    layer_ids: list[str]


class ChangeWindow(Strict):
    window_id: str
    batch_id: str
    role: Literal["main", "extension"]
    geometry_id: str
    direction: Literal["ascending", "descending"]
    before_id: str
    after_id: str
    before_date: str
    after_date: str
    span_days: int
    status: Literal["computed", "rejected"]
    reasons: list[str]
    pols: list[PolChange]
    quality_layer_id: str | None
    optical: list[OpticalComparison]
    gunw_context: dict[str, Any] | None = None
    development_window: bool = False


class BatchInfo(Strict):
    batch_id: str
    role: Literal["main", "extension"]
    collection: str
    crid: str
    geometry_id: str
    direction: Literal["ascending", "descending"]
    n_acquisitions: int
    n_usable: int
    n_windows: int
    n_windows_computed: int
    dates: list[str]
    gaps: list[dict[str, Any]]
    note_keys: list[str]


class QualityRow(Strict):
    window_id: str
    pol: str
    zone_id: str
    observed_fraction: Measurement
    reasons: dict[str, Measurement]


class ReferenceState(Strict):
    status: Literal["awaiting_annotations", "annotated_insufficient", "evaluated"]
    unit_definition: str
    sampling_file: str | None
    annotation_template: str | None
    n_units_sampled: dict[str, int]
    n_annotated: int
    n_indeterminate: int
    evaluation: dict[str, Any] | None
    missing: list[str]


class ZoneConclusion(Strict):
    zone_id: str
    label_key: str
    centroid: tuple[float, float] | None
    area_km2: float | None
    radar_variation: Literal["measured", "insufficient_baseline", "unavailable"]
    radar_params: dict[str, Scalar | list]
    optical_visible_change: Literal["corroborated_two_or_more_optical_pairs", "one_optical_pair", "not_elevated",
                                    "not_observable", "not_assessed"]
    optical_params: dict[str, Scalar | list]
    documented_cause: Literal["none_documented"] = "none_documented"
    cause_undetermined: bool = True
    alternative_keys: list[str]
    to_collect_keys: list[str]
    window_ids: list[str]


class Finding(Strict):
    id: str
    kind: str
    params: dict[str, Scalar | list]
    evidence: list[str]
    limit_keys: list[str] = Field(default_factory=list)


class SurfaceStudy(Strict):
    schema_version: Literal["3.0"] = STUDY_SCHEMA_VERSION
    study_id: str
    run_id: str
    data_nature: Literal["real", "synthetic"]
    presentation_level_key: str
    site: Site
    protocol: ProtocolInfo
    boundary: BoundaryInfo
    zones: list[Zone]
    zones_url: str
    acquisitions: list[GcovAcquisition]
    batches: list[BatchInfo]
    windows: list[ChangeWindow]
    quality: list[QualityRow]
    optical_scenes: list[OpticalScene]
    evidence: EvidenceSummary
    references: ReferenceState
    reference_catalogue: list[Reference]
    conclusions: list[ZoneConclusion]
    findings: list[Finding]
    layers: list[Layer]
    exports: list[Export]
    limits: list[str]
    external_sources: list[dict[str, str]]
    processing: Processing
    manifest: Manifest | None = None
    v2_context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _links(self):
        layers = {x.id for x in self.layers}
        acqs = {a.acquisition_id for a in self.acquisitions}
        if len(layers) != len(self.layers):
            raise ValueError("duplicate layer ids")
        wids = set()
        for w in self.windows:
            if w.window_id in wids:
                raise ValueError(f"duplicate window {w.window_id}")
            wids.add(w.window_id)
            if w.before_id not in acqs or w.after_id not in acqs:
                raise ValueError(f"window {w.window_id} refers to unknown acquisitions")
            for p in w.pols:
                for lid in p.layer_ids:
                    if lid not in layers:
                        raise ValueError(f"window {w.window_id} refers to unknown layer {lid}")
                if p.status == "computed" and p.baseline.status == "ok" and p.flags is None:
                    raise ValueError(f"{w.window_id}/{p.pol}: a baseline without flags")
                if p.status != "computed" and p.flags is not None:
                    raise ValueError(f"{w.window_id}/{p.pol}: flags on a window that was not computed")
            if w.quality_layer_id and w.quality_layer_id not in layers:
                raise ValueError(f"window {w.window_id} refers to unknown quality layer")
        for c in self.conclusions:
            if not set(c.window_ids) <= wids:
                raise ValueError(f"conclusion {c.zone_id} cites unknown windows")
        for g in self.evidence.optical:
            for grp in g.groups:
                if not set(grp.pair_ids) <= wids:
                    raise ValueError("an optical group cites unknown windows")
        eff = [r for r in self.evidence.references if r.effective()]
        if self.references.status == "evaluated" and not eff:
            raise ValueError("an evaluated reference state needs at least one effective structured reference")
        if self.boundary.state in ("remote_sensing_reviewed", "operator_confirmed") and self.boundary.review_status != "recorded":
            raise ValueError("a reviewed boundary needs a recorded review")
        if self.processing.status == "unavailable" and self.windows:
            raise ValueError("an unavailable study carries no window")
        return self
