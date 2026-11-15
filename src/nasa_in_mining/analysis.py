"""Small point-analysis facade over the extracted recipes.

These are point/circle analyses, not an automatic mining footprint classifier.
Polygon statistics are deliberately separate in roi.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math

from . import catalog, config, quality
from .recipes import backscatter, damage, displacement, offsets, soil_moisture, timeseries

LEVELS = {
    "surface-change": "GUNW", "displacement": "GUNW", "timeseries": "GUNW",
    "flood": "GCOV", "vegetation-loss": "GCOV", "offsets": "GOFF", "soil-moisture": "SME2",
}


def event_stamp(value: str | None) -> tuple[str | None, str]:
    if not value:
        return None, "exact"
    if len(value) == 8 and value.isdigit():
        dt = datetime.strptime(value, "%Y%m%d")
        return dt.strftime("%Y%m%dT000000"), "day"
    if len(value) == 10:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%Y%m%dT000000"), "day"
    if len(value) == 15 and value[8] == "T":
        return datetime.strptime(value, "%Y%m%dT%H%M%S").strftime("%Y%m%dT%H%M%S"), "exact"
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("an event time must specify its timezone, for example 2026-01-20T12:00:00Z")
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S"), "exact"


def _check_metric_grid(label, crs_value, t) -> None:
    from pyproj import CRS
    crs = CRS.from_user_input(crs_value) if crs_value else None
    units_ok = crs and crs.is_projected and len(crs.axis_info) >= 2 and all(
        math.isclose(a.unit_conversion_factor, 1.0) for a in crs.axis_info[:2]
    )
    if not units_ok or t.b != 0 or t.d != 0 or not math.isclose(abs(t.a), abs(t.e)):
        raise ValueError(f"{label}: point recipes require a north-up square metre grid; reproject first")


def _require_metric_grid(products) -> None:
    """Legacy circle recipes assume square, north-up pixels measured in metres."""
    import rasterio
    for p in products:
        key = catalog.MAIN_LAYER.get(p.level)
        if key is None:
            continue
        with rasterio.open(p.files[key]) as src:
            _check_metric_grid(p.id, src.crs, src.transform)


def analyze_point(recipe: str, lat: float, lon: float, event: str | None = None) -> dict:
    if recipe not in LEVELS:
        raise ValueError(f"unknown recipe: {recipe}")
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude/longitude are out of range")
    stamp, precision = event_stamp(event)
    products = catalog.find(lat, lon, LEVELS[recipe])
    out = {"recipe": recipe, "location": {"lat": lat, "lon": lon},
           "products": [p.summary() for p in products], "result": None,
           "validation": "not_independently_validated", "limits": [
               "Surface change is not proof of extraction, damage, mineral grade or extracted volume.",
               "Inherited thresholds require validation for the chosen mining site.",
           ]}
    if not products:
        return {**out, "status": "no_coverage", "reason": f"no {LEVELS[recipe]} product covers this point"}
    _require_metric_grid(products)
    rejected = []
    if recipe in ("displacement", "timeseries"):
        products, rejected = quality.split(products)
        if not products:
            return {**out, "status": "insufficient_data", "reason": "all pairs rejected by quality control",
                    "rejected_pairs": rejected}
    if recipe == "surface-change":
        result = damage.analyze(products, lat, lon, stamp, precision)
        out["scope"] = {"kind": "circle", "radius_m": damage.RADIUS_M}
    elif recipe == "displacement":
        result = displacement.analyze(products[0], lat, lon)
        if result.get("los_cm") is None:
            result = {**result, "error": "no valid displacement at this point"}
        out["scope"] = {"kind": "point_window", "radius_m": config.POINT_RADIUS_M}
    elif recipe == "timeseries":
        result = timeseries.point_series(products, lat, lon)
        if not result:
            result = {"error": "no connected series with valid observations"}
        out["scope"] = {"kind": "point_window", "radius_m": config.POINT_RADIUS_M}
    elif recipe in ("flood", "vegetation-loss"):
        result = backscatter.analyze(products, lat, lon, "flood" if recipe == "flood" else "deforestation",
                                     stamp[:8] if stamp else None)
        out["limits"].append("Backscatter classifications and their thresholds are heuristic, not site-validated.")
    elif recipe == "offsets":
        result = offsets.analyze(products, lat, lon)
        out["limits"].append("GOFF offsets are not a prediction of slope failure.")
    else:
        # Check the SME2 grid too, before its metric-window calculations.
        _, prof, _ = soil_moisture._read(products[0])
        _check_metric_grid(products[0].id, prof["crs"], prof["transform"])
        result = soil_moisture.analyze(products, lat, lon)
        out["limits"].append("Soil moisture is not a measurement of tailings pore pressure or water chemistry.")
    if recipe in ("displacement", "timeseries"):
        out["los_sign_verified"] = config.LOS_SIGN_VERIFIED
        if not config.LOS_SIGN_VERIFIED:
            out["limits"].append("LOS direction follows a documented convention, not a verified local sign test.")
    failed = isinstance(result, dict) and bool(result.get("error"))
    return {**out, "status": "insufficient_data" if failed else "ok", "result": result,
            "rejected_pairs": rejected}
