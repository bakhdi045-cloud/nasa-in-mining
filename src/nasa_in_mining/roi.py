"""New mining adapter: explicit polygon sampling, without attributing its signal to mining.

GeoJSON is WGS84. Pixel centres define membership. Area is projected grid area
for metric/other linear projected CRSs, and geodesic row area for north-up
geographic degree grids. A threshold describes a selection, not a confidence.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from pyproj import CRS
from rasterio.features import geometry_mask, is_valid_geom
from rasterio.warp import transform_geom

from . import raster


def load_polygons(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if "crs" in data:
        raise ValueError("provide RFC 7946 GeoJSON in WGS84 without a legacy crs member")
    if data.get("type") == "FeatureCollection":
        geoms = [f.get("geometry") for f in data.get("features", [])]
    elif data.get("type") == "Feature":
        geoms = [data.get("geometry")]
    else:
        geoms = [data]
    if not geoms:
        raise ValueError("the ROI has no polygon")
    for geom in geoms:
        if not geom or geom.get("type") not in ("Polygon", "MultiPolygon") or not is_valid_geom(geom):
            raise ValueError("all ROI geometries must be Polygon or MultiPolygon")
        polygons = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for polygon in polygons:
            for ring in polygon:
                if len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError("polygon rings must be closed with at least four positions")
                for position in ring:
                    x, y = position[:2]
                    if not (isinstance(x, (int, float)) and isinstance(y, (int, float))
                            and math.isfinite(x) and math.isfinite(y) and -180 <= x <= 180 and -90 <= y <= 90):
                        raise ValueError("ROI coordinates must be finite WGS84 longitude/latitude")
                if max(p[0] for p in ring) - min(p[0] for p in ring) > 180:
                    raise ValueError("split an ROI crossing the antimeridian before sampling")
    return geoms


def _area_km2(mask: np.ndarray, prof: dict) -> tuple[float, str]:
    crs = CRS.from_user_input(prof["crs"])
    t = prof["transform"]
    if crs.is_projected:
        factors = [a.unit_conversion_factor for a in crs.axis_info[:2]]
        if len(factors) != 2 or not all(math.isfinite(f) and f > 0 for f in factors):
            raise ValueError("the raster CRS has no usable linear units")
        area = abs(t.a * t.e - t.b * t.d) * factors[0] * factors[1]
        return float(mask.sum() * area / 1e6), "projected_grid_area"
    if not crs.is_geographic or t.b != 0 or t.d != 0:
        raise ValueError("reproject this raster to a projected CRS for area statistics")
    if any(not math.isclose(a.unit_conversion_factor, math.pi / 180) for a in crs.axis_info[:2]):
        raise ValueError("geographic area sampling requires degree coordinates")
    geod = crs.get_geod()
    areas = []
    for row in range(mask.shape[0]):
        corners = [t * p for p in ((0, row), (1, row), (1, row + 1), (0, row + 1))]
        if any(not -90 <= lat <= 90 for _, lat in corners):
            raise ValueError("the raster extends outside valid latitude coordinates")
        area, _ = geod.polygon_area_perimeter(*zip(*corners))
        areas.append(abs(area))
    return float(np.dot(np.asarray(areas), mask.sum(axis=1)) / 1e6), "geodesic_pixel_area"


def summarize_raster(path: str | Path, roi: str | Path, unit: str,
                     threshold: float | None = None, absolute: bool = False) -> dict:
    if not unit.strip():
        raise ValueError("the input signal unit must be provided")
    if threshold is not None and (not math.isfinite(threshold) or (absolute and threshold < 0)):
        raise ValueError("provide a finite threshold (nonnegative for absolute selection)")
    arr, prof = raster.read(path)
    if not prof["crs"]:
        raise ValueError("the input raster has no CRS")
    geoms = [transform_geom("EPSG:4326", prof["crs"], g) for g in load_polygons(roi)]
    inside = geometry_mask(geoms, out_shape=arr.shape, transform=prof["transform"], invert=True, all_touched=False)
    valid = inside & np.isfinite(arr)
    sampled, method = _area_km2(inside, prof)
    valid_area, _ = _area_km2(valid, prof)
    n, nv = int(inside.sum()), int(valid.sum())
    stats, selected = None, None
    if nv:
        values = arr[valid]
        stats = {"min": float(values.min()), "median": float(np.median(values)),
                 "mean": float(values.mean()), "max": float(values.max())}
        if threshold is not None:
            test = np.abs(arr) if absolute else arr
            selected, _ = _area_km2(valid & (test > threshold), prof)
    return {"status": "ok" if nv else "no_data" if n else "no_sampled_pixels",
            "raster": str(Path(path)), "roi": str(Path(roi)), "unit": unit, "unit_source": "user_supplied",
            "sampling": "pixel_centres", "area_method": method, "inside_pixels": n, "valid_pixels": nv,
            "valid_fraction": nv / n if n else None, "sampled_area_km2": sampled,
            "valid_area_km2": valid_area, "statistics": stats, "selected_area_km2": selected,
            "threshold": threshold, "selection": "absolute_value > threshold" if absolute else "value > threshold",
            "uncertainty": None,
            "limits": ["No classification uncertainty estimated; selected area is not verified mining activity.",
                       "Polygon membership uses pixel centres; a subpixel or out-of-frame ROI may have no samples.",
                       "Projected area inherits the distortion of the input CRS; choose an appropriate area CRS."]}
