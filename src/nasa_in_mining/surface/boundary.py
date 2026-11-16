"""Boundary dossier: what the study perimeter is, what supports it, and what is still waiting for a human review.

The perimeter used so far is the OpenStreetMap quarry polygon (way 638354631, last edited 2020). Its validity as a
geometry is not a verification of the mine boundary. This module writes `boundary.geojson` and
`boundary_review.json`, computes automated consistency checks (area, overlap, land cover, optical contrast across
the edge) and records the review states. It never marks a boundary reviewed or operator-confirmed: those states
need a person and their evidence, and stay `pending` until they are filled in `boundary_review_input.json`.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from scipy import ndimage
from shapely.geometry import mapping, shape

STATES = ("historical_map", "draft_interpretation", "remote_sensing_reviewed", "operator_confirmed")
CLASSES = ("study_extent", "installations", "visible_excavations", "waste_dumps", "ponds_basins")


def _mask(geom, grid_shape, transform, epsg):
    g = transform_geom("EPSG:4326", f"EPSG:{epsg}", mapping(geom))
    return geometry_mask([g], out_shape=grid_shape, transform=transform, invert=True)


def automated_checks(zones_fc: dict, wc_path: Path | None, s2_stack: Path | None, epsg: int = 32629) -> dict:
    """Consistency checks that need no reviewer. They describe the polygon; they do not validate it."""
    feats = {f["id"]: shape(f["geometry"]) for f in zones_fc["features"]}
    study = feats["study"]
    out: dict = {"geometry_valid": bool(study.is_valid), "n_parts": len(getattr(study, "geoms", [study]))}
    ref = None
    for p in (wc_path, s2_stack):
        if p and p.exists():
            ref = p
            break
    if ref is None:
        return {**out, "raster_checks": "unavailable: no local raster on the analysis grid"}
    with rasterio.open(ref) as src:
        shape_, tr = (src.height, src.width), src.transform
    pix_km2 = abs(tr.a * tr.e) / 1e6
    inside = _mask(study, shape_, tr, epsg)
    out["area_km2_rasterised"] = round(float(inside.sum() * pix_km2), 3)
    out["raster_grid_m"] = abs(tr.a)
    band_out = ndimage.binary_dilation(inside, iterations=int(round(300 / abs(tr.a)))) & ~inside
    band_in = inside & ~ndimage.binary_erosion(inside, iterations=int(round(300 / abs(tr.a))))
    out["edge_band_m"] = 300
    if wc_path and wc_path.exists():
        with rasterio.open(wc_path) as src:
            wc = src.read(1)
        from ..access.worldcover import CLASSES as WC

        def share(m):
            if not m.any():
                return {}
            v, c = np.unique(wc[m], return_counts=True)
            return {WC.get(int(a), str(int(a))): round(float(b) / m.sum(), 3) for a, b in zip(v, c) if b / m.sum() >= 0.01}
        out["landcover_2021_share"] = {"inside": share(inside), "outside_band_300m": share(band_out)}
    if s2_stack and s2_stack.exists():
        with rasterio.open(s2_stack) as src:
            x = src.read().astype("float32")
        bright = np.nanmean(x, axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            ndvi = (x[3] - x[2]) / (x[3] + x[2])
        med = lambda a, m: None if not (m & np.isfinite(a)).any() else round(float(np.nanmedian(a[m & np.isfinite(a)])), 4)  # noqa: E731
        out["optical_contrast_across_edge"] = {
            "scene": s2_stack.parent.name, "brightness_inner_band": med(bright, band_in),
            "brightness_outer_band": med(bright, band_out), "ndvi_inner_band": med(ndvi, band_in),
            "ndvi_outer_band": med(ndvi, band_out),
            "reading": "descriptive values of the 300 m bands on either side of the edge; "
                       "they do not locate the operational limit and do not verify the outline"}
    if "panels_outside" in feats:
        pan = feats["panels_outside"]
        out["panels_outside_osm_2020_km2"] = round(float(_mask(pan, shape_, tr, epsg).sum() * pix_km2), 3)
    return out


def build(zones_path: Path, out_dir: Path, wc_path: Path | None, s2_stack: Path | None, review_input: Path | None,
          epsg: int = 32629) -> dict:
    fc = json.loads(zones_path.read_text(encoding="utf-8"))
    study_f = next(f for f in fc["features"] if f["id"] == "study")
    props = study_f["properties"]
    checks = automated_checks(fc, wc_path, s2_stack, epsg)
    human = {}
    if review_input and review_input.exists():
        human = json.loads(review_input.read_text(encoding="utf-8"))
    state = human.get("state", "historical_map")
    if state not in STATES:
        raise ValueError(f"unknown boundary state {state}")
    if state in ("remote_sensing_reviewed", "operator_confirmed"):
        need = ("reviewer", "review_date", "imagery_date", "imagery_source", "evidence") if state == "remote_sensing_reviewed" \
            else ("operator_contact_role", "confirmation_date", "evidence")
        missing = [k for k in need if not human.get(k)]
        if missing:
            raise ValueError(f"state {state} is recorded only with {need}; missing {missing}")
    out_dir.mkdir(parents=True, exist_ok=True)
    feature = {"type": "Feature", "id": "study_extent", "geometry": study_f["geometry"],
               "properties": {"class": "study_extent", "state": state, "source": "OpenStreetMap way 638354631 v3",
                              "source_date": props.get("osm_timestamp"), "license": props.get("license"),
                              "area_km2": props.get("area_km2"), "crs": "EPSG:4326",
                              "nature": "mapped extent of quarry land use; not a mining concession or legal boundary"}}
    boundary = {"type": "FeatureCollection", "features": [feature]}
    (out_dir / "boundary.geojson").write_text(json.dumps(boundary, indent=1), encoding="utf-8", newline="\n")
    review = {
        "site": "OCP Benguerir (Gantour site; OCP states a Living Lab with UM6P at Benguerir)",
        "operator": "OCP Group",
        "documentary_source": {"name": "OpenStreetMap way 638354631 (landuse=quarry), version 3", "date": props.get("osm_timestamp"),
                               "license": props.get("license"), "crs": "EPSG:4326",
                               "operator_source": "https://www.ocpgroup.ma/fr/nos-activites/operations-industrielles"},
        "state": state, "state_scale": list(STATES),
        "review": {"status": "recorded" if state != "historical_map" and human else "pending_human_review",
                   "imagery_date": human.get("imagery_date"), "review_date": human.get("review_date"),
                   "reviewer": human.get("reviewer"), "evidence": human.get("evidence"),
                   "operator_confirmation": human.get("operator_contact_role") and {
                       "role": human.get("operator_contact_role"), "date": human.get("confirmation_date")} or None},
        "position_uncertainty_m": None,
        "position_uncertainty_note": "not estimated: it requires a review on dated imagery; the study uses +/- one 20 m pixel only as a sensitivity",
        "classes": {c: ("historical_map" if c == "study_extent" else "not_identified") for c in CLASSES},
        "class_note": "installations, excavations, dumps and basins are not separated: no reviewed source identifies them; the OSM industrial parcels (2020) are kept as a context layer with unconfirmed semantics",
        "comparison_with_osm_2020": {"overlap": "identical: the perimeter in use is the OSM 2020 polygon", "area_km2": props.get("area_km2")},
        "automated_checks": checks,
        "automated_checks_note": "descriptive; a valid geometry or a surface contrast is not a verification of the boundary",
        "legal_claim": "none: not a concession, a permit area or an operating limit",
        "controls": {"definition": "ring 1-4 km outside the perimeter with built-up and industrial exclusions (OSM 2020, 100 m buffer); defined before results",
                     "comparability_checked": ["land cover (WorldCover 2021) shares per control"],
                     "comparability_not_checked": ["slope", "soil", "land use history", "irrigation"],
                     "not_assumed_stable": True},
        "context_zone": "rings 1-2 km and 2-4 km are kept as context and comparators; 1-4 km is an analysis convention, not an influence boundary",
        "needed_for_next_state": {
            "remote_sensing_reviewed": ["need.contemporary_imagery", "need.reviewer", "need.digitised_limits"],
            "operator_confirmed": ["need.operator_written_confirmation"]}}
    (out_dir / "boundary_review.json").write_text(json.dumps(review, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    return review
