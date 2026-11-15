"""Study zones of a mining case: sourced perimeter, documented exclusions and control ring (new module).

The control ring is a geometric construction, not a "stable" certificate: it represents surrounding land observed
with the same acquisitions, season and geometry, from which built-up, military, industrial and other quarry areas
mapped in OpenStreetMap are removed. Distances are computed in the metric CRS of the radar grid.
"""
from __future__ import annotations

import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

EXCLUDED_LANDUSE = {"residential", "industrial", "commercial", "construction", "retail", "railway", "landfill",
                    "brownfield", "military", "quarry"}


def _proj(epsg: int):
    fwd = Transformer.from_crs(4326, epsg, always_xy=True).transform
    inv = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    return fwd, inv


def osm_way_polygon(element: dict):
    from shapely.geometry import Polygon
    coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
    if coords[0] != coords[-1]:
        return None
    return Polygon(coords)


def osm_relation_polygon(element: dict):
    """Outer/inner multipolygon from Overpass `out geom` members; open outer ways are joined with polygonize."""
    from shapely.geometry import LineString
    from shapely.ops import polygonize
    outer, inner = [], []
    for m in element.get("members", []):
        if m.get("type") != "way" or not m.get("geometry"):
            continue
        line = LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
        (inner if m.get("role") == "inner" else outer).append(line)
    polys = list(polygonize(unary_union(outer))) if outer else []
    if not polys:
        return None
    geom = unary_union(polys)
    if inner:
        holes = list(polygonize(unary_union(inner)))
        if holes:
            geom = geom.difference(unary_union(holes))
    return geom


def exclusion_features(osm: dict, study_osm_id: int) -> list[dict]:
    """Mapped areas that must not serve as control terrain (everything but the study way itself)."""
    out = []
    for e in osm.get("elements", []):
        tags = e.get("tags", {})
        kind = tags.get("landuse")
        if not (kind in EXCLUDED_LANDUSE or tags.get("amenity") == "university" or tags.get("aeroway")
                or tags.get("man_made") or tags.get("natural") == "water"):
            continue
        if e["type"] == "way" and e["id"] == study_osm_id:
            continue
        geom = osm_way_polygon(e) if e["type"] == "way" else osm_relation_polygon(e)
        if geom is None or geom.is_empty or not geom.is_valid:
            continue
        out.append({"type": "Feature", "geometry": mapping(geom),
                    "properties": {"osm_type": e["type"], "osm_id": e["id"], "osm_version": e.get("version"),
                                   "osm_timestamp": e.get("timestamp"),
                                   "class": kind or tags.get("amenity") or tags.get("aeroway") or tags.get("man_made")
                                   or tags.get("natural"), "name": tags.get("name")}})
    return out


def control_ring(study_wgs84, exclusions_wgs84: list, epsg: int, inner_m: float, outer_m: float,
                 exclusion_buffer_m: float = 100.0):
    """Ring between inner_m and outer_m from the study perimeter, minus buffered exclusions (WGS84 output)."""
    fwd, inv = _proj(epsg)
    study = transform(fwd, study_wgs84)
    ring = study.buffer(outer_m).difference(study.buffer(inner_m))
    if exclusions_wgs84:
        excl = unary_union([transform(fwd, g).buffer(exclusion_buffer_m) for g in exclusions_wgs84])
        ring = ring.difference(excl)
    return transform(inv, ring), ring.area / 1e6


def area_km2(geom_wgs84, epsg: int) -> float:
    fwd, _ = _proj(epsg)
    return transform(fwd, geom_wgs84).area / 1e6


def load_feature_collection(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["features"] if data.get("type") == "FeatureCollection" else [data]


def geometry_of(path: str | Path):
    return unary_union([shape(f["geometry"]) for f in load_feature_collection(path)])
