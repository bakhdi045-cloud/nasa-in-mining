"""Sentinel-2 L2A (Copernicus) window reads from the public Earth Search STAC catalogue (new module, v2).

Used as an independent, dated optical observation for the *location* of surface change. It is a cross-sensor
comparison, not ground truth, and validates neither a radar coherence value nor a line-of-sight displacement.

Radiometry (verified 2026-11-15, see docs/DATA_SOURCES.md): Earth Search COG pixel values equal the original ESA
DN minus 1000 for processing baselines >= 04.00 (pixel-by-pixel comparison with Planetary Computer, which keeps the
ESA DN). The BOA offset is therefore already applied: reflectance = DN / 10000. The item's raster:bands offset
(-0.1) is NOT applied a second time. v1 applied it (all reflectances shifted by -0.1).

Masks: the scene classification (SCL) is stored next to the reflectance stack and applied by the analysis with
recorded parameters (main: clear = vegetation 4, not-vegetated 5, water 6; doubtful = unclassified 7; excluded:
0 no data, 1 saturated/defective, 2 dark area/shadow, 3 cloud shadow, 8-10 clouds and cirrus, 11 snow).
"Contains modified Copernicus Sentinel data 2026" (Copernicus open licence).
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import from_bounds
import requests

from .remote import USER_AGENT

STAC = "https://earth-search.aws.element84.com/v1/search"
BANDS = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "swir16": "B11", "swir22": "B12"}
SCL_CLEAR = (4, 5, 6)
SCL_DOUBTFUL = (7,)
SCL_EXCLUDED = (0, 1, 2, 3, 8, 9, 10, 11)
QUANTIFICATION = 10000.0
DN_CONVENTION = "earth-search-v1: BOA offset pre-applied in pixel values; reflectance = DN / 10000"
READER_VERSION = "2"
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "AWS_NO_SIGN_REQUEST": "YES",
            "GDAL_HTTP_USERAGENT": USER_AGENT, "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif"}


def search(bbox_wgs84, start: str, end: str, max_cloud: float | None = None, tile: str | None = None,
           page_limit: int = 100) -> tuple[list[dict], dict]:
    """All items, following STAC 'next' links; deduplicated by id. Returns (items, completeness record)."""
    body: dict = {"collections": ["sentinel-2-l2a"], "bbox": list(bbox_wgs84), "datetime": f"{start}/{end}",
                  "limit": page_limit}
    if max_cloud is not None:
        body["query"] = {"eo:cloud_cover": {"lt": max_cloud}}
    url, method, items, pages, matched = STAC, "POST", {}, 0, None
    while url:
        r = requests.request(method, url, json=body if method == "POST" else None,
                             headers={"User-Agent": USER_AGENT}, timeout=90)
        r.raise_for_status()
        page = r.json()
        pages += 1
        matched = page.get("numberMatched", matched)
        for it in page.get("features", []):
            items.setdefault(it["id"], it)
        nxt = next((link for link in page.get("links", []) if link.get("rel") == "next"), None)
        if not nxt or not page.get("features"):
            break
        url, method = nxt["href"], nxt.get("method", "GET")
        if method == "POST":
            body = {**body, **nxt.get("body", {})} if nxt.get("merge") else nxt.get("body", body)
        if pages > 200:
            raise RuntimeError("STAC pagination did not terminate")
    out = sorted(items.values(), key=lambda i: i["properties"]["datetime"])
    n_all = len(out)
    if tile:
        out = [i for i in out if i["properties"].get("grid:code") == f"MGRS-{tile}"]
    record = {"pages": pages, "number_matched": matched, "n_received_unique": n_all,
              "complete": (matched is None) or (matched == n_all), "n_tile": len(out), "tile": tile}
    if matched is not None and matched != n_all:
        raise RuntimeError(f"STAC search incomplete: {n_all} unique items for {matched} matched")
    return out, record


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_key(item_id: str, bounds_utm, epsg: int, res: float) -> dict:
    return {"item_id": item_id, "bounds_utm": [float(v) for v in bounds_utm], "epsg": int(epsg), "res_m": float(res),
            "bands": list(BANDS.values()), "dn_convention": DN_CONVENTION, "reader_version": READER_VERSION}


def cached(out_dir: Path, key: dict) -> dict | None:
    """Provenance of a complete, unmodified cached read with the same parameters, else None."""
    prov = out_dir / "provenance.json"
    if not prov.exists():
        return None
    try:
        rec = json.loads(prov.read_text(encoding="utf-8"))
        if rec.get("cache_key") != key:
            return None
        for name, digest in rec["files"].items():
            if not (out_dir / name).exists() or _sha(out_dir / name) != digest:
                return None
        return rec
    except (OSError, ValueError, KeyError):
        return None


def read_item(item: dict, bounds_utm, epsg: int, out_root: Path, res: float = 20.0) -> dict:
    """Write reflectance (6 bands, float32, NaN = no data) and SCL (uint8) on the grid bounds_utm at res metres."""
    out_dir = Path(out_root) / item["id"]
    key = cache_key(item["id"], bounds_utm, epsg, res)
    hit = cached(out_dir, key)
    if hit:
        return hit
    if item["properties"].get("proj:epsg") != epsg:
        raise ValueError(f"{item['id']}: tile EPSG differs from the analysis grid")
    xmin, ymin, xmax, ymax = bounds_utm
    w, h = int(round((xmax - xmin) / res)), int(round((ymax - ymin) / res))
    stack = np.full((len(BANDS), h, w), np.nan, dtype="float32")
    hrefs = {}
    with rasterio.Env(**GDAL_ENV):
        a = item["assets"]["scl"]
        hrefs["scl"] = a["href"]
        with rasterio.open(a["href"]) as src:
            if src.res[0] != res:
                raise ValueError("SCL is expected at 20 m")
            scl = src.read(1, window=from_bounds(xmin, ymin, xmax, ymax, src.transform), out_shape=(h, w),
                           resampling=Resampling.nearest, boundless=True, fill_value=0).astype("uint8")
        for i, name in enumerate(BANDS):
            a = item["assets"][name]
            hrefs[name] = a["href"]
            nodata = (a.get("raster:bands") or [{}])[0].get("nodata", 0)
            with rasterio.open(a["href"]) as src:
                fine = src.res[0] < res
                dn = src.read(1, window=from_bounds(xmin, ymin, xmax, ymax, src.transform), out_shape=(h, w),
                              resampling=Resampling.average if fine else Resampling.nearest,
                              boundless=True, fill_value=nodata).astype("float32")
                if fine:   # an average must not mix no-data pixels: mark any 20 m cell touching no data
                    raw = src.read(1, window=from_bounds(xmin, ymin, xmax, ymax, src.transform), boundless=True,
                                   fill_value=nodata, out_shape=(h * 2, w * 2))
                    holes = (raw == nodata).reshape(h, 2, w, 2).any(axis=(1, 3))
                else:
                    holes = dn == nodata
            refl = dn / QUANTIFICATION
            refl[holes] = np.nan
            stack[i] = refl
    tmp = out_dir.with_name(out_dir.name + ".partial")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    profile = dict(driver="GTiff", width=w, height=h, crs=f"EPSG:{epsg}", transform=from_origin(xmin, ymax, res, res),
                   compress="deflate")
    with rasterio.open(tmp / "stack.tif", "w", count=len(BANDS), dtype="float32", nodata=np.nan, **profile) as dst:
        dst.write(stack)
        dst.descriptions = tuple(BANDS)
    with rasterio.open(tmp / "scl.tif", "w", count=1, dtype="uint8", nodata=0, **profile) as dst:
        dst.write(scl, 1)
    p = item["properties"]
    rec = {"item_id": item["id"], "datetime": p["datetime"], "platform": p.get("platform"),
           "processing_baseline": p.get("s2:processing_baseline"), "product_uri": p.get("s2:product_uri"),
           "cloud_cover_pct_tile": p.get("eo:cloud_cover"), "tile": p.get("grid:code"),
           "earthsearch_boa_offset_applied": p.get("earthsearch:boa_offset_applied"),
           "declared_raster_bands": {k: (item["assets"][k].get("raster:bands") or [{}])[0] for k in BANDS},
           "dn_convention": DN_CONVENTION, "hrefs": hrefs, "resolution_m": res,
           "resampling": "10 m bands: 2x2 mean (cells touching no data set to NaN); 20 m bands and SCL copied",
           "scl_window_counts": {str(int(k)): int(v) for k, v in zip(*np.unique(scl, return_counts=True))},
           "read_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cache_key": key,
           "license": "Copernicus Sentinel data terms (free, full and open)",
           "attribution": "Contains modified Copernicus Sentinel data 2026",
           "files": {"stack.tif": _sha(tmp / "stack.tif"), "scl.tif": _sha(tmp / "scl.tif")}}
    (tmp / "provenance.json").write_text(json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
    shutil.rmtree(out_dir, ignore_errors=True)
    os.replace(tmp, out_dir)       # published only once complete
    return rec
