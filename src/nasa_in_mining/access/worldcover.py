"""ESA WorldCover 10 m 2021 v200 land cover on the analysis grid (new in v2).

Used only to build control zones whose land cover resembles each other (bare/sparse vegetation, cropland,
grassland). WorldCover 2021 predates the radar period by five years and has its own errors; it is a documented
stratification aid, not a map of the mine. Licence: CC BY 4.0, "© ESA WorldCover project 2021 / Contains modified
Copernicus Sentinel data (2021) processed by ESA WorldCover consortium".
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N30W009_Map.tif"
CLASSES = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up",
           60: "bare / sparse vegetation", 70: "snow and ice", 80: "permanent water", 90: "herbaceous wetland",
           95: "mangroves", 100: "moss and lichen"}


def read(bounds_utm, epsg: int, out_dir: Path, res: float = 20.0) -> dict:
    """Mode-resample WorldCover to the grid; writes worldcover.tif + provenance.json."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    xmin, ymin, xmax, ymax = bounds_utm
    w, h = int(round((xmax - xmin) / res)), int(round((ymax - ymin) / res))
    dst_t = from_origin(xmin, ymax, res, res)
    out = np.zeros((h, w), dtype="uint8")
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", AWS_NO_SIGN_REQUEST="YES"):
        with rasterio.open(URL) as src:
            from rasterio.warp import transform_bounds
            from rasterio.windows import from_bounds
            b = transform_bounds(f"EPSG:{epsg}", src.crs, xmin, ymin, xmax, ymax, densify_pts=21)
            win = from_bounds(b[0] - 0.002, b[1] - 0.002, b[2] + 0.002, b[3] + 0.002, src.transform)
            arr = src.read(1, window=win)
            reproject(arr, out, src_transform=src.window_transform(win), src_crs=src.crs, dst_transform=dst_t,
                      dst_crs=f"EPSG:{epsg}", resampling=Resampling.mode, src_nodata=0, dst_nodata=0)
    path = out_dir / "worldcover.tif"
    with rasterio.open(path, "w", driver="GTiff", width=w, height=h, count=1, dtype="uint8", crs=f"EPSG:{epsg}",
                       transform=dst_t, nodata=0, compress="deflate") as dst:
        dst.write(out, 1)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    vals, counts = np.unique(out, return_counts=True)
    rec = {"source": URL, "product": "ESA WorldCover 10 m 2021 v200", "resampling": "mode to 20 m",
           "read_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "bounds_utm": list(bounds_utm),
           "epsg": epsg, "class_counts": {CLASSES.get(int(v), str(int(v))): int(c) for v, c in zip(vals, counts)},
           "license": "CC BY 4.0", "attribution": "© ESA WorldCover project 2021", "files": {"worldcover.tif": sha}}
    (out_dir / "provenance.json").write_text(json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
    return rec
