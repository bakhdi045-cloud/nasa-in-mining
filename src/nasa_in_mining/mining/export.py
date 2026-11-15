"""Exports for a mining case: GeoTIFF, Web-Mercator PNG overlays, GeoJSON clusters, CSV (new module).

PNG overlays are reprojected to EPSG:3857 so that a web map (MapLibre image source) places them exactly with
their four corner coordinates. Categorical layers use nearest-neighbour; continuous layers use nearest too, so
that displayed pixels keep measured values (no smoothing). Transparent = not observed.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_geom

from .. import raster as legacy_raster


def write_geotiff(path: Path, arr: np.ndarray, transform, epsg: int, nodata=None, tags: dict | None = None) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if nodata is None and arr.dtype.kind == "f":
        nodata = np.nan
    with rasterio.open(path, "w", driver="GTiff", width=arr.shape[-1], height=arr.shape[-2],
                       count=1 if arr.ndim == 2 else arr.shape[0], dtype=arr.dtype, crs=f"EPSG:{epsg}",
                       transform=transform, nodata=nodata, compress="deflate", predictor=2 if arr.dtype.kind in "iu" else 1) as dst:
        dst.write(arr if arr.ndim == 3 else arr[None])
        if tags:
            dst.update_tags(**{k: str(v) for k, v in tags.items()})
    return sha256(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_mercator(arr: np.ndarray, transform, epsg: int, resampling=Resampling.nearest):
    h, w = arr.shape[-2:]
    bounds = rasterio.transform.array_bounds(h, w, transform)
    dst_t, dw, dh = calculate_default_transform(f"EPSG:{epsg}", "EPSG:3857", w, h, *bounds)
    bands = arr if arr.ndim == 3 else arr[None]
    dst = np.full((bands.shape[0], dh, dw), np.nan, dtype="float32")
    for i in range(bands.shape[0]):
        reproject(bands[i].astype("float32"), dst[i], src_transform=transform, src_crs=f"EPSG:{epsg}",
                  dst_transform=dst_t, dst_crs="EPSG:3857", resampling=resampling, src_nodata=np.nan, dst_nodata=np.nan)
    west, north = dst_t * (0, 0)
    east, south = dst_t * (dw, dh)
    from pyproj import Transformer
    inv = Transformer.from_crs(3857, 4326, always_xy=True)
    (lon_w, lon_e), (lat_s, lat_n) = inv.transform([west, east], [south, north])
    corners = [[lon_w, lat_n], [lon_e, lat_n], [lon_e, lat_s], [lon_w, lat_s]]   # MapLibre order: TL, TR, BR, BL
    return dst if arr.ndim == 3 else dst[0], corners


def png_continuous(path: Path, arr: np.ndarray, transform, epsg: int, cmap: str, vmin: float, vmax: float,
                   alpha: int = 220) -> dict:
    from PIL import Image
    merc, corners = _to_mercator(arr, transform, epsg)
    # Indexed PNG: 254 colour levels between vmin and vmax (values outside are clipped), index 255 = no data.
    levels = 254
    norm = np.clip((merc - vmin) / (vmax - vmin + 1e-12), 0, 1)
    idx = np.where(np.isfinite(merc), np.round(np.nan_to_num(norm) * (levels - 1)), 255).astype("uint8")
    lut = (legacy_raster._colormap(cmap)(np.linspace(0, 1, levels))[:, :3] * 255).astype("uint8")
    palette = np.zeros((256, 3), dtype="uint8")
    palette[:levels] = lut
    img = Image.fromarray(idx, "P")
    img.putpalette(palette.ravel().tolist())
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True, transparency=bytes([alpha] * levels + [0, 0]))
    stops = ["#%02x%02x%02x" % tuple(int(v) for v in lut[i]) for i in np.linspace(0, levels - 1, 9).astype(int)]
    return {"corners": corners, "vmin": vmin, "vmax": vmax, "cmap": cmap, "levels": levels, "stops": stops,
            "sha256": sha256(path)}


def png_categorical(path: Path, arr: np.ndarray, transform, epsg: int, colors: dict[int, tuple]) -> dict:
    """arr: integer classes (NaN or a class absent from colors = transparent)."""
    from PIL import Image
    merc, corners = _to_mercator(arr.astype("float32"), transform, epsg)
    idx = np.zeros(merc.shape, dtype="uint8")              # index 0 = transparent
    palette, alpha = [0, 0, 0], [0]
    for i, (value, rgba_value) in enumerate(colors.items(), start=1):
        idx[merc == value] = i
        palette += list(rgba_value[:3])
        alpha.append(rgba_value[3])
    img = Image.fromarray(idx, "P")
    img.putpalette(palette + [0] * (768 - len(palette)))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True, transparency=bytes(alpha))
    return {"corners": corners, "classes": {str(k): list(v) for k, v in colors.items()}, "sha256": sha256(path)}


def png_rgb(path: Path, rgb: np.ndarray, transform, epsg: int, lo: float = 0.03, hi: float = 0.50,
            gamma: float = 1.0) -> dict:
    """True-colour basemap from reflectance bands (3, h, w)."""
    from PIL import Image
    merc, corners = _to_mercator(rgb, transform, epsg)
    img = np.clip((merc - lo) / (hi - lo), 0, 1) ** gamma
    out = np.zeros(merc.shape[1:] + (4,), dtype="uint8")
    out[..., :3] = (np.nan_to_num(np.moveaxis(img, 0, -1)) * 255).astype("uint8")
    out[..., 3] = np.where(np.all(np.isfinite(merc), axis=0), 255, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in (".jpg", ".jpeg"):            # basemap without transparency: compact JPEG
        Image.fromarray(out[..., :3], "RGB").save(path, quality=88, optimize=True)
    else:
        Image.fromarray(out, "RGBA").save(path, optimize=True)
    return {"corners": corners, "stretch": [lo, hi], "gamma": gamma, "sha256": sha256(path)}


def clusters_geojson(labels: np.ndarray, clusters: list[dict], transform, epsg: int, extra: dict | None = None) -> dict:
    """Vector outlines (WGS84) of labelled clusters; the polygons follow pixel edges."""
    feats = []
    by_id = {c["id"]: c for c in clusters}
    for geom, value in shapes(labels.astype("int32"), mask=labels > 0, transform=transform, connectivity=8):
        cid = int(value)
        if cid not in by_id:
            continue
        g = transform_geom(f"EPSG:{epsg}", "EPSG:4326", geom, precision=6)
        feats.append({"type": "Feature", "geometry": g, "properties": {**by_id[cid], **(extra or {})}})
    return {"type": "FeatureCollection", "features": feats}


def write_csv(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="", encoding="utf-8") as f:     # LF line ends: hashes match a Git checkout
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})
    return sha256(path)


def write_json(path: Path, data) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, allow_nan=False), encoding="utf-8", newline="\n")
    return sha256(path)
