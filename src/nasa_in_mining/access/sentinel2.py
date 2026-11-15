"""Sentinel-2 L2A (Copernicus) window reads from the public Earth Search STAC catalogue (new module).

Used as an independent, dated optical reference for the *location* of surface change. It does not validate a
radar coherence value or a line-of-sight displacement. Reflectance = DN * scale + offset, taken from each item's
raster:bands metadata (processing baselines >= 04.00 carry the -0.1 BOA offset).
Data: "Contains modified Copernicus Sentinel data [2026]" (Copernicus open licence).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import from_bounds
import requests

from .remote import USER_AGENT

STAC = "https://earth-search.aws.element84.com/v1/search"
BANDS = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "swir16": "B11", "swir22": "B12"}
# SCL classes kept as valid surface observations: 2 dark area, 4 vegetation, 5 not vegetated, 6 water, 7 unclassified
SCL_VALID = (2, 4, 5, 6, 7)
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "AWS_NO_SIGN_REQUEST": "YES",
            "GDAL_HTTP_USERAGENT": USER_AGENT, "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif"}


def search(bbox_wgs84, start: str, end: str, max_cloud: float = 10.0, tile: str | None = None) -> list[dict]:
    body = {"collections": ["sentinel-2-l2a"], "bbox": list(bbox_wgs84), "datetime": f"{start}/{end}",
            "limit": 200, "query": {"eo:cloud_cover": {"lt": max_cloud}}}
    r = requests.post(STAC, json=body, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    items = r.json()["features"]
    if tile:
        items = [i for i in items if i["properties"].get("grid:code") == f"MGRS-{tile}"]
    return sorted(items, key=lambda i: i["properties"]["datetime"])


def read_item(item: dict, bounds_utm, epsg: int, out_dir: Path, res: float = 20.0) -> dict:
    """Write a 20 m reflectance stack (6 bands, float32, NaN outside valid SCL) aligned on bounds_utm."""
    out_dir = Path(out_dir) / item["id"]
    done = out_dir / "stack.tif"
    if done.exists():
        return json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    if item["properties"].get("proj:epsg") != epsg:
        raise ValueError(f"{item['id']}: tile EPSG differs from the analysis grid")
    xmin, ymin, xmax, ymax = bounds_utm
    w, h = int(round((xmax - xmin) / res)), int(round((ymax - ymin) / res))
    stack = np.full((len(BANDS), h, w), np.nan, dtype="float32")
    scaling = {}
    with rasterio.Env(**GDAL_ENV):
        a = item["assets"]["scl"]
        with rasterio.open(a["href"]) as src:
            scl = src.read(1, window=from_bounds(xmin, ymin, xmax, ymax, src.transform), out_shape=(h, w),
                           resampling=Resampling.nearest, boundless=True, fill_value=0)
        valid = np.isin(scl, SCL_VALID)
        for i, name in enumerate(BANDS):
            a = item["assets"][name]
            rb = (a.get("raster:bands") or [{}])[0]
            scale, offset, nodata = rb.get("scale", 1e-4), rb.get("offset", 0.0), rb.get("nodata", 0)
            scaling[name] = {"scale": scale, "offset": offset, "nodata": nodata, "href": a["href"]}
            with rasterio.open(a["href"]) as src:
                dn = src.read(1, window=from_bounds(xmin, ymin, xmax, ymax, src.transform), out_shape=(h, w),
                              resampling=Resampling.average if src.res[0] < res else Resampling.nearest,
                              boundless=True, fill_value=nodata).astype("float32")
            refl = dn * scale + offset
            refl[(dn == nodata) | ~valid] = np.nan
            stack[i] = refl
    out_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(done, "w", driver="GTiff", width=w, height=h, count=len(BANDS), dtype="float32",
                       crs=f"EPSG:{epsg}", transform=from_origin(xmin, ymax, res, res), nodata=np.nan,
                       compress="deflate") as dst:
        dst.write(stack)
        dst.descriptions = tuple(BANDS)
    p = item["properties"]
    rec = {"item_id": item["id"], "datetime": p["datetime"], "platform": p.get("platform"),
           "processing_baseline": p.get("s2:processing_baseline"), "product_uri": p.get("s2:product_uri"),
           "cloud_cover_pct": p.get("eo:cloud_cover"), "tile": p.get("grid:code"),
           "valid_fraction_window": float(valid.mean()), "bands": scaling, "resolution_m": res,
           "resampling": "average of 10 m pixels to 20 m; 20 m bands copied on the aligned grid",
           "scl_valid_classes": list(SCL_VALID), "read_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "license": "Copernicus Sentinel data terms (free, full and open)",
           "attribution": "Contains modified Copernicus Sentinel data 2026"}
    (out_dir / "provenance.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec
