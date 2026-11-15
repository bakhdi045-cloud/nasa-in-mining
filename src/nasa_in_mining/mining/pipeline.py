"""Reproducible mining-case pipeline (new module).

import -> checks -> analysis grid -> computation -> quality mask -> polygon statistics -> independent comparison
-> export, with a run manifest. Reuses the extracted catalog, quality, raster, roi, wavelength, displacement and
uncertainty modules where their assumptions hold; see docs/METHOD.md for each choice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from . import coherence_change as cc
from . import export
from .contract import (Acquisition, Cluster, CrossGeometry, Export, FileRecord, Finding, GeometrySummary, Layer,
                       LayerFile, Legend, LosPair, Manifest, Method, MiningCase, NextCheck, OpticalComparison,
                       OpticalScene, PairQuality, PairResult, Processing, Reference, Site, Step, Uncertainty,
                       ValidationItem, Zone, ZoneMetrics, absent, measured, unavailable_case)

METHOD_VERSION = "1.0.0"
REUSED = ["catalog.load/parse_name (product index, CRID, dates)", "quality.split (flat phase, median coherence)",
          "roi.summarize_raster (polygon statistics, cross-check)", "raster._colormap (palettes)",
          "recipes.displacement.los_cm_full (phase to LOS, masks)", "recipes.wavelength (product frequency)",
          "uncertainty.robust_sigma (control-zone noise)"]
FLAG_COLORS = {1: (0, 224, 255, 240), 255: (150, 150, 150, 110)}
GEOM_COLORS = {"ascending": "A", "descending": "D"}


# ----------------------------------------------------------------------------------------------- helpers
def _git(root: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
                                timeout=10).stdout.strip() or None
        # code and case inputs only: the outputs being written are not part of the code state
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "scripts", "pyproject.toml",
                                     ":(glob)cases/*/case_config.json", ":(glob)cases/*/zones.geojson"], cwd=root,
                                    capture_output=True, text=True, timeout=10).stdout.strip())
        return commit, dirty
    except Exception:
        return None, None


def _packages() -> dict:
    out = {}
    for name in ("numpy", "scipy", "rasterio", "pyproj", "h5py", "shapely", "pydantic", "matplotlib", "pillow"):
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def _date(stamp: str) -> str:
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"


def _m(value, unit, reason="not computed", status="unavailable", uncertainty=None):
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return absent(unit, reason, status)
    return measured(value, unit, uncertainty)


def _read(path: Path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        return arr, {"transform": src.transform, "crs": src.crs, "shape": arr.shape, "nodata": src.nodata}


def _same_grid(a: dict, b: dict) -> bool:
    return a["shape"] == b["shape"] and a["crs"] == b["crs"] and all(
        math.isclose(x, y, abs_tol=1e-6) for x, y in zip(tuple(a["transform"])[:6], tuple(b["transform"])[:6]))


def _rasterize(geom_wgs84, grid: dict, epsg: int) -> np.ndarray:
    from rasterio.warp import transform_geom
    if geom_wgs84 is None or geom_wgs84.is_empty:
        return np.zeros(grid["shape"], dtype=bool)
    g = transform_geom("EPSG:4326", f"EPSG:{epsg}", mapping(geom_wgs84))
    return geometry_mask([g], out_shape=grid["shape"], transform=grid["transform"], invert=True, all_touched=False)


def _lonlat(grid: dict, epsg: int, row: float, col: float) -> tuple[float, float]:
    from pyproj import Transformer
    x, y = grid["transform"] * (col + 0.5, row + 0.5)
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(x, y)
    return round(lon, 5), round(lat, 5)


# ----------------------------------------------------------------------------------------------- optical
def _optical_index(s2_dir: Path) -> list[dict]:
    out = []
    if not s2_dir.exists():
        return out
    for prov in sorted(s2_dir.glob("*/provenance.json")):
        rec = json.loads(prov.read_text(encoding="utf-8"))
        rec["stack"] = prov.parent / "stack.tif"
        rec["date"] = datetime.fromisoformat(rec["datetime"].replace("Z", "+00:00"))
        out.append(rec)
    return sorted(out, key=lambda r: r["date"])


def _bracket(scenes: list[dict], t0: datetime, t1: datetime, max_gap_days: float, min_valid: float):
    ok = [s for s in scenes if s["valid_fraction_window"] >= min_valid]
    before = [s for s in ok if s["date"] <= t0 and (t0 - s["date"]).total_seconds() / 86400 <= max_gap_days]
    after = [s for s in ok if s["date"] >= t1 and (s["date"] - t1).total_seconds() / 86400 <= max_gap_days]
    if not before or not after:
        return None, None
    return before[-1], after[0]


def _optical_change(b: dict, a: dict) -> tuple[np.ndarray, dict]:
    """Change magnitude (L2 norm over the 6 reflectance bands) and spectral diagnostics used to examine
    alternative explanations: dNDVI (vegetation), dMNDWI (green/SWIR1, wetting or drying), d brightness."""
    with rasterio.open(b["stack"]) as s0, rasterio.open(a["stack"]) as s1:
        x0, x1 = s0.read().astype("float32"), s1.read().astype("float32")
    ok = np.all(np.isfinite(x0), axis=0) & np.all(np.isfinite(x1), axis=0)
    d = np.sqrt(np.sum((x1 - x0) ** 2, axis=0))
    d[~ok] = np.nan
    # band order: blue, green, red, nir, swir16, swir22
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = lambda x: (x[3] - x[2]) / (x[3] + x[2])  # noqa: E731
        mndwi = lambda x: (x[1] - x[4]) / (x[1] + x[4])  # noqa: E731
        diag = {"d_ndvi": ndvi(x1) - ndvi(x0), "d_mndwi": mndwi(x1) - mndwi(x0),
                "d_brightness": x1.mean(axis=0) - x0.mean(axis=0)}
    for v in diag.values():
        v[~ok] = np.nan
    return d, diag


def _indicative_label(dn: float, dm: float, db: float) -> str:
    """Descriptive, heuristic reading of the dominant optical change (documented thresholds, not a cause)."""
    if not all(math.isfinite(v) for v in (dn, dm, db)):
        return "optical.undetermined"
    if abs(dm) >= 0.2 and abs(dm) >= 2 * abs(dn):
        return "optical.moisture_like"
    if abs(dn) >= 0.1:
        return "optical.vegetation_like"
    if abs(db) >= 0.03:
        return "optical.brightness_like"
    return "optical.weak"


# ----------------------------------------------------------------------------------------------- LOS
def _los(p, grid80: dict, zones80: dict, cfg: dict, quality_ok: bool):
    from ..recipes import displacement
    from ..uncertainty import robust_sigma
    from .. import config as legacy_config
    pid = p.id
    if cfg["coherence_min"] != legacy_config.COHERENCE_MIN:
        raise ValueError("los.coherence_min must equal the inherited COHERENCE_MIN used by displacement.los_cm_full")
    if not quality_ok:
        return None, LosPair(pair_id=pid, status="not_computed", reference="none",
                             control_sigma_cm=absent("cm", "pair rejected by quality control", "not_measured"),
                             study_median_cm=absent("cm", "pair rejected", "not_measured"),
                             study_p05_cm=absent("cm", "pair rejected", "not_measured"),
                             study_p95_cm=absent("cm", "pair rejected", "not_measured"),
                             study_coherent_fraction=absent("1", "pair rejected", "not_measured"),
                             area_beyond_3sigma_km2=absent("km2", "pair rejected", "not_measured"),
                             layer_id=None, sign_verified=legacy_config.LOS_SIGN_VERIFIED, reason="quality")
    disp, coh, prof, notes, report = displacement.los_cm_full(p, corrections=())
    ccomp = displacement._components_raster(p)
    control, study = zones80["control"], zones80["study"]
    ok_ctrl = np.isfinite(disp) & control
    reason = None
    if ccomp is not None and ok_ctrl.any():
        labels = ccomp[ok_ctrl]
        labels = labels[labels > 0]
        comp = int(np.bincount(labels.astype(np.int64)).argmax()) if labels.size else None
    else:
        comp = None
    if comp is not None:
        same = ccomp == comp
        disp = np.where(same, disp, np.nan)
        ok_ctrl = np.isfinite(disp) & control
    if ok_ctrl.sum() < cfg["min_control_pixels"]:
        reason = "too few coherent control pixels in the reference component"
    pix_km2 = abs(prof["transform"].a * prof["transform"].e) / 1e6
    if reason:
        na = lambda u: absent(u, reason, "not_measured")  # noqa: E731
        return None, LosPair(pair_id=pid, status="insufficient_data", reference="control ring median",
                             control_sigma_cm=na("cm"), study_median_cm=na("cm"), study_p05_cm=na("cm"),
                             study_p95_cm=na("cm"), study_coherent_fraction=na("1"), area_beyond_3sigma_km2=na("km2"),
                             layer_id=None, sign_verified=legacy_config.LOS_SIGN_VERIFIED, reason=reason)
    ref = float(np.median(disp[ok_ctrl]))
    disp = disp - ref
    sigma = robust_sigma(disp[ok_ctrl])
    inside = np.isfinite(disp) & study
    frac = inside.sum() / max(study.sum(), 1)
    sig = Uncertainty(kind="empirical_sigma", value=sigma, method="robust sigma (1.4826 MAD) of referenced LOS in "
                      "the control ring; includes residual troposphere and ionosphere; spatially correlated")
    vals = disp[inside]
    if vals.size < 50 or not math.isfinite(sigma):
        na = lambda u: absent(u, "too few coherent study pixels", "not_measured")  # noqa: E731
        return disp, LosPair(pair_id=pid, status="insufficient_data", reference="control ring median",
                             control_sigma_cm=_m(sigma, "cm"), study_median_cm=na("cm"), study_p05_cm=na("cm"),
                             study_p95_cm=na("cm"), study_coherent_fraction=measured(frac, "1"),
                             area_beyond_3sigma_km2=na("km2"), layer_id=None,
                             sign_verified=legacy_config.LOS_SIGN_VERIFIED, reason="too few coherent study pixels")
    beyond = inside & (np.abs(disp) > cfg["sigma_factor"] * sigma)
    return disp, LosPair(pair_id=pid, status="ok", reference="median of the control ring (same connected component)",
                         control_sigma_cm=measured(sigma, "cm"),
                         study_median_cm=measured(float(np.median(vals)), "cm", sig),
                         study_p05_cm=measured(float(np.percentile(vals, 5)), "cm", sig),
                         study_p95_cm=measured(float(np.percentile(vals, 95)), "cm", sig),
                         study_coherent_fraction=measured(float(frac), "1"),
                         area_beyond_3sigma_km2=measured(float(beyond.sum() * pix_km2), "km2"),
                         layer_id=f"los_{pid}", sign_verified=legacy_config.LOS_SIGN_VERIFIED)


def _index(catalog, data_dir: Path) -> list:
    """Index a data folder with the extracted catalogue, then restore its configured folder (no global side effect)."""
    previous = catalog.DATA_DIR
    try:
        catalog.DATA_DIR = data_dir
        return list(catalog.refresh())
    finally:
        catalog.DATA_DIR = previous
        catalog.load.cache_clear()


# ----------------------------------------------------------------------------------------------- main
def run(case_dir: Path, data_dir: Path, out_dir: Path | None = None, repo_root: Path | None = None) -> MiningCase:
    t_start = time.time()
    case_dir = Path(case_dir)
    out_dir = Path(out_dir or case_dir / "output")
    repo_root = Path(repo_root or case_dir.parents[1])
    cfg_path = case_dir / "case_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    epsg, mcfg, ocfg, lcfg = cfg["epsg"], cfg["method"], cfg["optical"], cfg["los"]
    steps: list[Step] = []
    inputs: list[FileRecord] = []

    # --- zones
    zfc = json.loads((case_dir / cfg["zones_file"]).read_text(encoding="utf-8"))
    zgeoms = {f["id"]: shape(f["geometry"]) for f in zfc["features"]}
    zprops = {f["id"]: f["properties"] for f in zfc["features"]}
    zones = [Zone(id=k, role=v["role"], area_km2=v.get("area_km2"), source=f"OpenStreetMap ({v.get('osm_type', 'derived')}"
                  f" {v.get('osm_id', '')})".replace(" )", ")"), source_date=v.get("osm_timestamp") or v.get("osm_base_timestamp"),
                  license=v["license"], attribution=v["attribution"], nature=v.get("nature")) for k, v in zprops.items()]
    inputs.append(FileRecord(path=str((case_dir / cfg["zones_file"]).relative_to(repo_root)).replace("\\", "/"),
                             sha256=export.sha256(case_dir / cfg["zones_file"]), role="zones"))
    site = Site(**cfg["site"])
    method = Method(id="control-relative-coherence-loss", version=METHOD_VERSION, reused_modules=REUSED,
                    parameters={**{f"method.{k}": v for k, v in mcfg.items()}, **{f"optical.{k}": v for k, v in ocfg.items()},
                                **{f"los.{k}": v for k, v in lcfg.items()}, "radar.coherence_layer": cfg["radar"]["coherence_layer"],
                                "radar.crid": cfg["radar"]["crid"]},
                    steps=["import", "checks", "grid", "flags", "quality_mask", "polygon_statistics",
                           "cross_geometry", "optical_comparison", "los", "export", "manifest"])
    references = [Reference(**r) for r in cfg["references"]]

    # --- catalogue (reuse the extracted index on this data folder)
    from .. import catalog, quality
    products = [p for p in _index(catalog, Path(data_dir)) if p.level == "GUNW" and p.crid == cfg["radar"]["crid"]]
    if not products:
        steps.append(Step(name="import", status="unavailable", message=f"no GUNW product in {data_dir}"))
        case = unavailable_case(cfg["case_id"], site, zones, "zones.geojson", method, references,
                                ["blocker.no_radar_products"], steps)
        out_dir.mkdir(parents=True, exist_ok=True)
        export.write_json(out_dir / "case.json", json.loads(case.model_dump_json()))
        return case
    steps.append(Step(name="import", status="done", message=f"{len(products)} GUNW products ({cfg['radar']['crid']})"))

    # --- quality (inherited gross rejection on the 80 m layers)
    good, rejected = quality.split(products)
    rej_by_id = {r["product"]: r for r in rejected}
    steps.append(Step(name="checks", status="done", message=f"{len(rejected)} pair(s) rejected by quality.split"))

    # --- analysis grid: 20 m coherence grid of the first product; every pair must match it exactly
    coh_name, mask_name = cfg["radar"]["coherence_layer"], cfg["radar"]["mask_layer"]
    _, grid = _read(products[0].folder / coh_name)
    pix_km2 = abs(grid["transform"].a * grid["transform"].e) / 1e6
    study_g, control_g = zgeoms["study"], zgeoms["control"]
    panels_g = zgeoms.get("panels_outside")
    zmask = {"study": _rasterize(study_g, grid, epsg), "control": _rasterize(control_g, grid, epsg),
             "panels_outside": _rasterize(panels_g, grid, epsg)}
    from shapely.ops import transform as stransform
    from pyproj import Transformer
    fwd = Transformer.from_crs(4326, epsg, always_xy=True).transform
    inv = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    study_m = stransform(fwd, study_g)
    band_inner = stransform(inv, study_m.buffer(2000)).intersection(control_g)
    zmask["control_1_2km"] = _rasterize(band_inner, grid, epsg)
    zmask["control_2_4km"] = zmask["control"] & ~zmask["control_1_2km"]
    steps.append(Step(name="grid", status="done", message=f"{grid['shape'][1]}x{grid['shape'][0]} px at "
                      f"{abs(grid['transform'].a):g} m, EPSG:{epsg}; zones rasterised by pixel centre"))
    study_geojson = out_dir / "exports" / "study_perimeter.geojson"
    export.write_json(study_geojson, {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": mapping(study_g), "properties": zprops["study"]}]})

    # --- optical scenes
    scenes = _optical_index(Path(data_dir) / ocfg["dir"])
    optical_scenes = [OpticalScene(item_id=s["item_id"], datetime=s["datetime"], platform=s.get("platform"),
                                   processing_baseline=s.get("processing_baseline"),
                                   cloud_cover_pct=s.get("cloud_cover_pct"),
                                   valid_fraction_window=s["valid_fraction_window"]) for s in scenes]

    layers: list[Layer] = []
    exports_: list[Export] = []
    outputs: list[FileRecord] = []
    acquisitions, pairs, los_pairs = [], [], []
    per_geom: dict[str, dict] = {}
    q, qs = mcfg["control_quantile"], mcfg["sensitivity_quantiles"]
    min_px = max(1, int(round(mcfg["min_cluster_km2"] / pix_km2)))
    los_maps = {}

    def add_layer(layer: Layer, path: Path):
        layers.append(layer)
        outputs.append(FileRecord(path=str(path.relative_to(out_dir)).replace("\\", "/"), sha256=export.sha256(path),
                                  role="layer"))

    for p in sorted(products, key=lambda x: (x.direction, x.ref)):
        prov = json.loads((p.folder / "provenance.json").read_text(encoding="utf-8"))
        ident, proc = prov.get("identification", {}), prov.get("processing", {})
        geom_id = f"{p.track:03d}{GEOM_COLORS[p.direction]}_F{p.frame:03d}"
        qrec = quality.check(p)
        acquisitions.append(Acquisition(
            pair_id=p.id, granule_id=p.name, collection=prov["source_url"].split("/")[4], crid=p.crid,
            maturity=p.maturity, geometry_id=geom_id, direction=p.direction, track=p.track, frame=p.frame,
            reference_time=ident.get("referenceZeroDopplerStartTime", p.ref), secondary_time=ident.get(
                "secondaryZeroDopplerStartTime", p.sec), span_days=p.span_days,
            product_version=ident.get("productVersion"), processing_datetime=ident.get("processingDateTime"),
            doi=ident.get("productDoi"), source_url=prov["source_url"], bytes_transferred=prov.get("bytes_transferred"),
            layers=[LayerFile(name=k, sha256=v["sha256"], spacing_m=v.get("spacing_m"), units=v.get("units"))
                    for k, v in prov["layers"].items()],
            looks={k: proc.get(k) for k in ("wrapped_azimuth_looks", "wrapped_range_looks", "unwrapped_azimuth_looks",
                                             "unwrapped_range_looks")},
            quality=PairQuality(ok=qrec["ok"], reasons=qrec["reasons"], phase_sigma_rad=qrec["phase_sigma_rad"],
                                coherence_median=qrec["coherence_median"])))
        for name, v in prov["layers"].items():
            inputs.append(FileRecord(path=f"data/GUNW/{p.name}/{name}", sha256=v["sha256"], role="nisar_crop"))
        g = per_geom.setdefault(geom_id, {"direction": p.direction, "track": p.track, "frame": p.frame, "crid": p.crid,
                                          "flags": [], "valids": [], "pair_ids": [], "n": 0, "n_used": 0})
        g["n"] += 1
        coh, cgrid = _read(p.folder / coh_name)
        mask, mgrid = _read(p.folder / mask_name)
        base = dict(pair_id=p.id, geometry_id=geom_id, reference_date=_date(p.ref), secondary_date=_date(p.sec),
                    span_days=p.span_days)
        empty = dict(threshold=absent("1", "not computed", "not_measured"), threshold_sensitivity={},
                     control_flag_rate=absent("1", "not computed", "not_measured"),
                     control_median_coherence=absent("1", "not computed", "not_measured"), zones=[],
                     study_flagged_area_sensitivity={}, n_clusters=None, clusters_shown=[], layer_ids=[], optical=None)
        if not (_same_grid(cgrid, grid) and _same_grid(mgrid, grid)):
            pairs.append(PairResult(**base, **empty, status="incompatible_grid",
                                    reason="coherence or mask grid differs from the analysis grid (no resampling done)"))
            continue
        if p.id in rej_by_id:
            pairs.append(PairResult(**base, **empty, status="rejected_quality",
                                    reason="; ".join(rej_by_id[p.id]["reasons"])))
            los_pairs.append(_los(p, None, None, lcfg, False)[1])
            continue
        coh = coh.astype("float32")
        valid = cc.mask_valid(mask) & np.isfinite(coh)
        main = cc.flag_pair(coh, valid, zmask["control"], q)
        if main["status"] != "ok":
            pairs.append(PairResult(**base, **empty, status="insufficient_control",
                                    reason=f"{main['control_valid_pixels']} valid control pixels"))
            continue
        flagged = main["flagged"]
        sens = {str(x): cc.flag_pair(coh, valid, zmask["control"], x) for x in qs}

        # flag raster (0 = observed, not flagged; 1 = flagged; 255 = not observed) and polygon cross-check with roi.py
        flag_u8 = np.where(valid, flagged.astype("uint8"), 255).astype("uint8")
        tif = out_dir / "rasters" / f"flags_{p.id}.tif"
        sha = export.write_geotiff(tif, flag_u8, grid["transform"], epsg, nodata=255,
                                   tags={"pair": p.id, "values": "0 observed not flagged; 1 flagged; 255 not observed",
                                         "threshold_coherence": main["threshold"], "control_quantile": q})
        exports_.append(Export(id=f"flags_{p.id}", format="geotiff", path=f"rasters/flags_{p.id}.tif",
                               description_key="export.flags_geotiff", sha256=sha))
        from ..roi import summarize_raster
        check = summarize_raster(tif, study_geojson, unit="flag (1 = below control quantile)", threshold=0.5)
        zm = {}
        for zid in ("study", "panels_outside", "control", "control_1_2km", "control_2_4km"):
            s = cc.zone_stats(flagged, valid, zmask[zid], coh, pix_km2)
            zm[zid] = s
        s = zm["study"]
        if not (math.isclose(check["valid_area_km2"], s["observable_area_km2"], rel_tol=1e-9, abs_tol=1e-9)
                and math.isclose(check["selected_area_km2"] or 0.0, s["flagged_area_km2"] or 0.0, rel_tol=1e-9, abs_tol=1e-9)):
            raise RuntimeError(f"{p.id}: polygon statistics disagree with roi.summarize_raster")

        def metrics(zid):
            s = zm[zid]
            reason = "zone not observed in this pair"
            return ZoneMetrics(zone_id=zid, zone_area_km2=s["zone_area_km2"],
                               observable_area_km2=measured(s["observable_area_km2"], "km2"),
                               observable_fraction=_m(s["observable_fraction"], "1", "empty zone"),
                               flagged_area_km2=_m(s["flagged_area_km2"], "km2", reason),
                               flagged_fraction_of_observable=_m(s["flagged_fraction_of_observable"], "1", reason),
                               median_coherence=_m(s["median_coherence"], "1", reason))
        sens_area = {k: _m(cc.zone_stats(v["flagged"], valid, zmask["study"], coh, pix_km2)["flagged_area_km2"], "km2")
                     for k, v in sens.items()}
        labels, clusters = cc.change_zones(flagged, zmask["study"], coh, min_px)
        shown = clusters[: mcfg["clusters_shown"]]
        gj = export.clusters_geojson(labels, shown, grid["transform"], epsg, {"pair_id": p.id})
        cl_path = out_dir / "clusters" / f"clusters_{p.id}.geojson"
        sha = export.write_json(cl_path, gj)
        exports_.append(Export(id=f"clusters_{p.id}", format="geojson", path=f"clusters/clusters_{p.id}.geojson",
                               description_key="export.clusters_geojson", sha256=sha))

        # layers
        lid_c, lid_f = f"coh_{p.id}", f"flags_{p.id}"
        png = out_dir / "layers" / f"{lid_c}.png"
        info = export.png_continuous(png, coh, grid["transform"], epsg, "magma", 0.0, 1.0)
        add_layer(Layer(id=lid_c, kind="observation", title_key="layer.coherence", params={"pair": p.id},
                        url=f"layers/{lid_c}.png", corners=info["corners"],
                        legend=Legend(kind="continuous", unit="1 (coherence)", vmin=0, vmax=1, cmap="magma", stops=info["stops"]),
                        date_start=_date(p.ref), date_end=_date(p.sec), source_ids=[p.id],
                        resolution_m=abs(grid["transform"].a)), png)
        png = out_dir / "layers" / f"{lid_f}.png"
        info = export.png_categorical(png, flag_u8, grid["transform"], epsg, FLAG_COLORS)
        add_layer(Layer(id=lid_f, kind="derived", title_key="layer.flags", params={"pair": p.id, "quantile": q},
                        url=f"layers/{lid_f}.png", corners=info["corners"],
                        legend=Legend(kind="categorical", classes=info["classes"],
                                      class_keys={"1": "legend.flagged", "255": "legend.not_observed"}),
                        date_start=_date(p.ref), date_end=_date(p.sec), source_ids=[p.id],
                        resolution_m=abs(grid["transform"].a), export=f"rasters/flags_{p.id}.tif"), png)
        layer_ids = [lid_c, lid_f]

        # optical comparison for the same window
        optical = None
        if scenes:
            t0 = datetime.fromisoformat(acquisitions[-1].reference_time[:19]).replace(tzinfo=timezone.utc)
            t1 = datetime.fromisoformat(acquisitions[-1].secondary_time[:19]).replace(tzinfo=timezone.utc)
            sb, sa = _bracket(scenes, t0, t1, ocfg["max_gap_days"], ocfg["min_valid_fraction"])
            na = lambda r: absent("1", r, "not_measured")  # noqa: E731
            if sb is None:
                optical = OpticalComparison(status="no_scene_pair", before_item=None, after_item=None, gap_days_before=None,
                                            gap_days_after=None, optical_threshold=na("no bracketing scenes"),
                                            lift=na("no bracketing scenes"), p_optical_given_radar=na("no bracketing scenes"),
                                            p_optical_given_not_radar=na("no bracketing scenes"),
                                            jaccard=na("no bracketing scenes"),
                                            reason=f"no clear Sentinel-2 scene within {ocfg['max_gap_days']} days on both sides")
            else:
                dopt, diag = _optical_change(sb, sa)
                ctrl = dopt[zmask["control"] & np.isfinite(dopt)]
                thr = float(np.quantile(ctrl, ocfg["quantile"])) if ctrl.size >= cc.MIN_CONTROL_PIXELS else None
                both = zmask["study"] & valid & np.isfinite(dopt)
                if thr is None or both.sum() < 100:
                    optical = OpticalComparison(status="insufficient_overlap", before_item=sb["item_id"], after_item=sa["item_id"],
                                                gap_days_before=(t0 - sb["date"]).total_seconds() / 86400,
                                                gap_days_after=(sa["date"] - t1).total_seconds() / 86400,
                                                optical_threshold=na("insufficient overlap"), lift=na("insufficient overlap"),
                                                p_optical_given_radar=na("insufficient overlap"),
                                                p_optical_given_not_radar=na("insufficient overlap"),
                                                jaccard=na("insufficient overlap"), reason="too few jointly valid pixels")
                else:
                    oflag = np.isfinite(dopt) & (dopt > thr)
                    lf = cc.lift(flagged, oflag, both)
                    optical = OpticalComparison(
                        status="ok", before_item=sb["item_id"], after_item=sa["item_id"],
                        gap_days_before=round((t0 - sb["date"]).total_seconds() / 86400, 2),
                        gap_days_after=round((sa["date"] - t1).total_seconds() / 86400, 2),
                        optical_threshold=measured(thr, "reflectance (L2 norm, 6 bands)"),
                        lift=_m(lf["lift"], "ratio", "no radar-flagged or no unflagged pixel", "not_measured"),
                        p_optical_given_radar=_m(lf["p_b_given_a"], "1", "no radar-flagged pixel", "not_measured"),
                        p_optical_given_not_radar=_m(lf["p_b_given_not_a"], "1", "no unflagged pixel", "not_measured"),
                        jaccard=_m(lf["jaccard"], "1", "empty union", "not_measured"),
                        control_median_d_ndvi=_m(float(np.nanmedian(diag["d_ndvi"][zmask["control"]])), "1"),
                        control_median_d_mndwi=_m(float(np.nanmedian(diag["d_mndwi"][zmask["control"]])), "1"))
                    for c in shown:
                        sel = (labels == c["id"]) & np.isfinite(dopt)
                        c["optical_change_fraction"] = float(oflag[sel].mean()) if sel.any() else None
                        if sel.any():
                            dn, dm, db = (float(np.nanmedian(diag[k][sel])) for k in ("d_ndvi", "d_mndwi", "d_brightness"))
                            c["optical_diagnostics"] = {"d_ndvi": dn, "d_mndwi": dm, "d_brightness": db,
                                                        "indicative_key": _indicative_label(dn, dm, db)}
                    lid_o = f"opt_{p.id}"
                    png = out_dir / "layers" / f"{lid_o}.png"
                    info = export.png_continuous(png, np.where(oflag, dopt, np.nan), grid["transform"], epsg,
                                                 "inferno", thr, max(thr * 3, thr + 0.05))
                    add_layer(Layer(id=lid_o, kind="reference", title_key="layer.optical_change",
                                    params={"pair": p.id, "before": sb["item_id"], "after": sa["item_id"]},
                                    url=f"layers/{lid_o}.png", corners=info["corners"],
                                    legend=Legend(kind="continuous", unit="reflectance change (L2 norm)", vmin=thr,
                                                  vmax=max(thr * 3, thr + 0.05), cmap="inferno", stops=info["stops"]),
                                    date_start=sb["datetime"][:10], date_end=sa["datetime"][:10],
                                    source_ids=[sb["item_id"], sa["item_id"]], resolution_m=20.0), png)
                    layer_ids.append(lid_o)

        pairs.append(PairResult(
            **base, status="ok",
            threshold=measured(main["threshold"], "1 (coherence)", Uncertainty(
                kind="sensitivity_range", low=min(v["threshold"] for v in sens.values()),
                high=max(v["threshold"] for v in sens.values()), method=f"control quantiles {qs}")),
            threshold_sensitivity={k: _m(v["threshold"], "1 (coherence)") for k, v in sens.items()},
            control_flag_rate=measured(main["control_flag_rate"], "1"),
            control_median_coherence=measured(main["control_median"], "1"),
            zones=[metrics(z) for z in ("study", "panels_outside", "control", "control_1_2km", "control_2_4km")],
            study_flagged_area_sensitivity=sens_area, n_clusters=len(clusters),
            clusters_shown=[Cluster(id=c["id"], area_km2=c["pixels"] * pix_km2,
                                    centroid=_lonlat(grid, epsg, c["row"], c["col"]),
                                    median_coherence=c["median_coherence"],
                                    optical_change_fraction=c.get("optical_change_fraction"),
                                    optical_diagnostics=c.get("optical_diagnostics")) for c in shown],
            layer_ids=layer_ids, optical=optical))
        g["n_used"] += 1
        if p.span_days == mcfg["recurrence_span_days"]:
            g["flags"].append(flagged)
            g["valids"].append(valid)
            g["pair_ids"].append(p.id)

        # LOS on the 80 m grid (complement)
        _, grid80 = _read(p.files["phase"])
        z80 = {"study": _rasterize(study_g, grid80, epsg), "control": _rasterize(control_g, grid80, epsg)}
        disp, lp = _los(p, grid80, z80, lcfg, True)
        if disp is not None and lp.status == "ok":
            lid = f"los_{p.id}"
            png = out_dir / "layers" / f"{lid}.png"
            lim = lcfg["display_limit_cm"]
            info = export.png_continuous(png, disp, grid80["transform"], epsg, "RdBu_r", -lim, lim)
            add_layer(Layer(id=lid, kind="derived", title_key="layer.los", params={"pair": p.id},
                            url=f"layers/{lid}.png", corners=info["corners"],
                            legend=Legend(kind="continuous", unit="cm (LOS, sign unverified)", vmin=-lim, vmax=lim,
                                          cmap="RdBu_r", stops=info["stops"]),
                            date_start=_date(p.ref), date_end=_date(p.sec), source_ids=[p.id], resolution_m=80.0), png)
            pairs[-1].layer_ids.append(lid)
        los_pairs.append(lp)
    steps.append(Step(name="flags", status="done", message=f"{sum(1 for p in pairs if p.status == 'ok')} pairs analysed"))
    steps.append(Step(name="polygon_statistics", status="done",
                      message="zone statistics cross-checked against roi.summarize_raster for every pair"))

    # --- recurrence per geometry and cross-geometry agreement
    geometries, rec_maps = [], {}
    for gid, g in sorted(per_geom.items()):
        if g["flags"]:
            frac, seen = cc.recurrence(g["flags"], g["valids"])
            rec_maps[gid] = frac
            lid = f"recurrence_{gid}"
            tif = out_dir / "rasters" / f"{lid}.tif"
            sha = export.write_geotiff(tif, frac, grid["transform"], epsg,
                                       tags={"values": "fraction of observed 12-day pairs flagged", "pairs": ",".join(g["pair_ids"])})
            exports_.append(Export(id=lid, format="geotiff", path=f"rasters/{lid}.tif",
                                   description_key="export.recurrence_geotiff", sha256=sha))
            png = out_dir / "layers" / f"{lid}.png"
            info = export.png_continuous(png, np.where(frac > 0, frac, np.nan), grid["transform"], epsg, "viridis", 0, 1)
            add_layer(Layer(id=lid, kind="derived", title_key="layer.recurrence", params={"geometry": gid, "n_pairs": len(g["flags"])},
                            url=f"layers/{lid}.png", corners=info["corners"],
                            legend=Legend(kind="continuous", unit="fraction of observed pairs", vmin=0, vmax=1, cmap="viridis", stops=info["stops"]),
                            date_start=_date(min(x.split("_")[3] for x in g["pair_ids"])),
                            date_end=_date(max(x.split("_")[4] for x in g["pair_ids"])), source_ids=g["pair_ids"],
                            resolution_m=abs(grid["transform"].a), export=f"rasters/{lid}.tif"), png)
            st = zmask["study"] & np.isfinite(frac)
            ever = float(((frac > 0) & st).sum() * pix_km2)
            half = float(((frac >= mcfg["frequent_threshold"]) & st).sum() * pix_km2)
        else:
            lid, ever, half = None, None, None
        geometries.append(GeometrySummary(geometry_id=gid, direction=g["direction"], track=g["track"], frame=g["frame"],
                                          crid=g["crid"], n_pairs=g["n"], n_pairs_used=g["n_used"],
                                          recurrence_pairs=g["pair_ids"], recurrence_layer_id=lid,
                                          study_area_flagged_ever_km2=_m(ever, "km2", "no usable 12-day pair"),
                                          study_area_flagged_half_or_more_km2=_m(half, "km2", "no usable 12-day pair")))
    if len(rec_maps) >= 2:
        (ga, fa), (gb, fb) = list(rec_maps.items())[:2]
        st = zmask["study"]
        rho = cc.spearman(fa[st], fb[st])
        dom = st & np.isfinite(fa) & np.isfinite(fb)
        lf = cc.lift(fa >= mcfg["frequent_threshold"], fb >= mcfg["frequent_threshold"], dom)
        cross = CrossGeometry(status="ok", spearman_recurrence_study=_m(rho, "1", "too few pixels", "not_measured"),
                              lift_frequent_change=_m(lf["lift"], "ratio", "no frequent change", "not_measured"),
                              jaccard_frequent_change=_m(lf["jaccard"], "1", "no frequent change", "not_measured"),
                              frequent_threshold=mcfg["frequent_threshold"])
    else:
        na = absent("1", "fewer than two geometries with usable pairs", "unavailable")
        cross = CrossGeometry(status="unavailable", spearman_recurrence_study=na, lift_frequent_change=na,
                              jaccard_frequent_change=na, frequent_threshold=mcfg["frequent_threshold"],
                              reason="fewer than two geometries with usable pairs")
    steps.append(Step(name="cross_geometry", status="done" if cross.status == "ok" else "unavailable"))

    # recurrence of each shown cluster in the other geometry
    for pr in pairs:
        other = [gid for gid in rec_maps if gid != pr.geometry_id]
        if not other:
            continue
        frac = rec_maps[other[0]]
        lab_path = out_dir / "clusters" / f"clusters_{pr.pair_id}.geojson"
        if not lab_path.exists():
            continue
        from rasterio.features import rasterize
        from rasterio.warp import transform_geom
        fc = json.loads(lab_path.read_text(encoding="utf-8"))
        for c in pr.clusters_shown:
            feats = [transform_geom("EPSG:4326", f"EPSG:{epsg}", f["geometry"]) for f in fc["features"]
                     if f["properties"]["id"] == c.id]
            if not feats:
                continue
            sel = rasterize([(g_, 1) for g_ in feats], out_shape=grid["shape"], transform=grid["transform"],
                            dtype="uint8").astype(bool) & np.isfinite(frac)
            c.recurrence_in_other_pairs = float(np.mean(frac[sel])) if sel.any() else None

    # --- basemaps (Sentinel-2 true colour, earliest and latest complete scenes)
    full = [s for s in scenes if s["valid_fraction_window"] >= 0.999]
    for tag, s in (("early", full[0] if full else None), ("late", full[-1] if full else None)):
        if s is None:
            continue
        with rasterio.open(s["stack"]) as src:
            rgb = src.read([3, 2, 1]).astype("float32")
            st_t = src.transform
        lid = f"s2_{tag}"
        png = out_dir / "layers" / f"{lid}.jpg"
        info = export.png_rgb(png, rgb, st_t, epsg)
        add_layer(Layer(id=lid, kind="basemap", title_key="layer.s2_true_colour", params={"item": s["item_id"]},
                        url=f"layers/{lid}.jpg", corners=info["corners"], legend=Legend(kind="rgb"),
                        date_start=s["datetime"][:10], date_end=s["datetime"][:10], source_ids=[s["item_id"]],
                        resolution_m=20.0), png)
    steps.append(Step(name="optical_comparison", status="done" if scenes else "unavailable",
                      message=f"{len(scenes)} Sentinel-2 scenes"))
    steps.append(Step(name="los", status="done", message="per-pair LOS referenced to the control ring; sign unverified"))

    # --- tables
    rows = []
    for pr in pairs:
        z = {m.zone_id: m for m in pr.zones}
        rows.append({"pair_id": pr.pair_id, "geometry": pr.geometry_id, "reference_date": pr.reference_date,
                     "secondary_date": pr.secondary_date, "span_days": pr.span_days, "status": pr.status,
                     "threshold_coherence": pr.threshold.value, "control_flag_rate": pr.control_flag_rate.value,
                     "study_observable_fraction": z["study"].observable_fraction.value if "study" in z else None,
                     "study_flagged_km2": z["study"].flagged_area_km2.value if "study" in z else None,
                     "study_flagged_fraction": z["study"].flagged_fraction_of_observable.value if "study" in z else None,
                     "inner_ring_flagged_fraction": z["control_1_2km"].flagged_fraction_of_observable.value if z else None,
                     "outer_ring_flagged_fraction": z["control_2_4km"].flagged_fraction_of_observable.value if z else None,
                     "optical_lift": pr.optical.lift.value if pr.optical else None, "reason": pr.reason})
    sha = export.write_csv(out_dir / "exports" / "pairs.csv", rows)
    exports_.append(Export(id="pairs_csv", format="csv", path="exports/pairs.csv", description_key="export.pairs_csv", sha256=sha))
    exports_.append(Export(id="study_geojson", format="geojson", path="exports/study_perimeter.geojson",
                           description_key="export.study_geojson", sha256=export.sha256(study_geojson)))

    # --- findings, validation, next checks (structured; texts are composed by the interface)
    findings, next_checks, validation = derive_findings(pairs, geometries, cross, los_pairs, mcfg)
    limits = ["limit.cause_not_identified", "limit.no_ore_volume_production", "limit.provisional_products",
              "limit.perimeter_2020_not_legal", "limit.control_not_proven_stable", "limit.threshold_is_selection",
              "limit.no_data_is_not_no_change", "limit.los_sign_unverified", "limit.optical_supports_location_only",
              "limit.twelve_day_window", "limit.no_field_truth"]
    processing = Processing(status="complete" if scenes else "partial", steps=steps,
                            blockers=[] if scenes else ["blocker.no_optical_reference"])
    commit, dirty = _git(repo_root)
    for f in sorted((out_dir / "rasters").glob("*.tif")) + sorted((out_dir / "clusters").glob("*.geojson")) + \
            sorted((out_dir / "exports").glob("*")):
        outputs.append(FileRecord(path=str(f.relative_to(out_dir)).replace("\\", "/"), sha256=export.sha256(f), role="export"))
    manifest = Manifest(run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        code_commit=commit, code_dirty=dirty, python=platform.python_version(), packages=_packages(),
                        config_sha256=export.sha256(cfg_path), inputs=inputs, outputs=outputs,
                        duration_s=round(time.time() - t_start, 1))
    case = MiningCase(case_id=cfg["case_id"], data_nature=cfg.get("data_nature", "real"),
                      question_key="question.coherence_change", user_key="user.monitoring_analyst", site=site,
                      zones=zones, zones_url="zones.geojson", acquisitions=acquisitions, optical_scenes=optical_scenes,
                      method=method, pairs=pairs, geometries=geometries, cross_geometry=cross, los=los_pairs,
                      layers=layers, exports=exports_, references=references, validation=validation,
                      findings=findings, next_checks=next_checks, limits=limits, processing=processing, manifest=manifest)
    export.write_json(out_dir / "case.json", json.loads(case.model_dump_json()))
    export.write_json(out_dir / "zones.geojson", zfc)
    return case


def derive_findings(pairs, geometries, cross, los_pairs, mcfg):
    """Findings only restate measured quantities; each next check cites the findings that motivate it."""
    ok = [p for p in pairs if p.status == "ok"]
    findings, checks = [], []

    def z(p, zid):
        return next((m for m in p.zones if m.zone_id == zid), None)

    if ok:
        ratios = []
        for p in ok:
            s = z(p, "study").flagged_fraction_of_observable.value
            c = p.control_flag_rate.value
            if s is not None and c:
                ratios.append((p.pair_id, s / c))
        above = [pid for pid, r in ratios if r > 1]
        findings.append(Finding(id="F1", kind="study_rate_vs_control",
                                params={"n_pairs": len(ok), "n_above": len(above),
                                        "median_ratio": float(np.median([r for _, r in ratios])) if ratios else None,
                                        "min_ratio": float(min(r for _, r in ratios)) if ratios else None,
                                        "max_ratio": float(max(r for _, r in ratios)) if ratios else None,
                                        "quantile": mcfg["control_quantile"]},
                                evidence=[p for p, _ in ratios]))
        inner = [z(p, "control_1_2km").flagged_fraction_of_observable.value for p in ok]
        outer = [z(p, "control_2_4km").flagged_fraction_of_observable.value for p in ok]
        pairs_io = [(a, b) for a, b in zip(inner, outer) if a is not None and b is not None]
        if pairs_io:
            findings.append(Finding(id="F2", kind="inner_vs_outer_ring",
                                    params={"median_inner": float(np.median([a for a, _ in pairs_io])),
                                            "median_outer": float(np.median([b for _, b in pairs_io])),
                                            "n_pairs": len(pairs_io)}, evidence=[p.pair_id for p in ok]))
        po = [(z(p, "study").flagged_fraction_of_observable.value, z(p, "panels_outside").flagged_fraction_of_observable.value)
              for p in ok if z(p, "panels_outside") is not None]
        po = [(a, b) for a, b in po if a is not None and b is not None]
        if po:
            findings.append(Finding(id="F9", kind="panels_outside_vs_study",
                                    params={"median_study": float(np.median([a for a, _ in po])),
                                            "median_panels_outside": float(np.median([b for _, b in po])),
                                            "n_pairs_panels_above_control": sum(1 for _, b in po if b > mcfg["control_quantile"]),
                                            "n_pairs": len(po)}, evidence=[p.pair_id for p in ok]))
        opt = [p for p in ok if p.optical and p.optical.status == "ok" and p.optical.lift.value is not None]
        if opt:
            lifts = [p.optical.lift.value for p in opt]
            findings.append(Finding(id="F3", kind="optical_association",
                                    params={"n_pairs": len(opt), "median_lift": float(np.median(lifts)),
                                            "min_lift": float(min(lifts)), "max_lift": float(max(lifts)),
                                            "n_lift_above_2": sum(1 for v in lifts if v > 2)},
                                    evidence=[p.pair_id for p in opt]))
        if cross.status == "ok":
            findings.append(Finding(id="F4", kind="cross_geometry",
                                    params={"spearman": cross.spearman_recurrence_study.value,
                                            "lift": cross.lift_frequent_change.value,
                                            "jaccard": cross.jaccard_frequent_change.value,
                                            "frequent_threshold": cross.frequent_threshold},
                                    evidence=[g.recurrence_layer_id for g in geometries if g.recurrence_layer_id]))
        # most recurrent clusters: shown clusters with a high recurrence in the other geometry
        cands = []
        for p in ok:
            for c in p.clusters_shown:
                if c.recurrence_in_other_pairs is not None:
                    cands.append((c.recurrence_in_other_pairs, c.area_km2, p, c))
        cands.sort(key=lambda t: (-t[0], -t[1]))
        seen, top = [], []
        for rec, area, p, c in cands:
            if any(abs(c.centroid[0] - s[0]) < 0.005 and abs(c.centroid[1] - s[1]) < 0.005 for s in seen):
                continue
            seen.append(c.centroid)
            top.append((rec, area, p, c))
            if len(top) == 3:
                break
        for i, (rec, area, p, c) in enumerate(top, start=1):
            fid = f"F5.{i}"
            findings.append(Finding(id=fid, kind="recurrent_cluster",
                                    params={"pair_id": p.pair_id, "cluster_id": c.id, "lon": c.centroid[0],
                                            "lat": c.centroid[1], "area_km2": area, "other_geometry_recurrence": rec,
                                            "optical_change_fraction": c.optical_change_fraction,
                                            "optical_indicative_key": (c.optical_diagnostics or {}).get("indicative_key"),
                                            "n_pairs_with_cluster_here": sum(
                                                1 for q in ok if any(abs(k.centroid[0] - c.centroid[0]) < 0.003
                                                                     and abs(k.centroid[1] - c.centroid[1]) < 0.003
                                                                     for k in q.clusters_shown)),
                                            "reference_date": p.reference_date, "secondary_date": p.secondary_date},
                                    evidence=[p.pair_id, f"clusters_{p.pair_id}"]))
            checks.append(NextCheck(id=f"N{i}", kind="inspect_location",
                                    params={"lon": c.centroid[0], "lat": c.centroid[1], "from": p.reference_date,
                                            "to": p.secondary_date}, because=[fid]))
    rejected = [p for p in pairs if p.status != "ok"]
    if rejected:
        findings.append(Finding(id="F6", kind="pairs_not_used",
                                params={"n": len(rejected), "reasons": sorted({p.status for p in rejected})},
                                evidence=[p.pair_id for p in rejected]))
    long_ = [p for p in ok if p.span_days != mcfg["recurrence_span_days"]]
    if long_:
        findings.append(Finding(id="F7", kind="long_span_pairs", params={"n": len(long_), "span_days": long_[0].span_days},
                                evidence=[p.pair_id for p in long_]))
    los_ok = [lp for lp in los_pairs if lp.status == "ok"]
    if los_ok:
        findings.append(Finding(id="F8", kind="los_summary",
                                params={"n_pairs": len(los_ok),
                                        "median_sigma_cm": float(np.median([lp.control_sigma_cm.value for lp in los_ok])),
                                        "max_abs_p95_cm": float(max(max(abs(lp.study_p05_cm.value), abs(lp.study_p95_cm.value))
                                                                    for lp in los_ok)),
                                        "sign_verified": los_ok[0].sign_verified},
                                evidence=[lp.pair_id for lp in los_ok]))
        checks.append(NextCheck(id="N_los", kind="verify_los_sign_and_amplitude", params={}, because=["F8"]))
    f2 = next((f for f in findings if f.id == "F2"), None)
    f9 = next((f for f in findings if f.id == "F9"), None)
    because = []
    if f2 and f2.params["median_outer"] and f2.params["median_inner"] > 2 * f2.params["median_outer"]:
        because.append("F2")
    if f9 and f9.params["median_panels_outside"] > mcfg["control_quantile"]:
        because.append("F9")
    if because:
        checks.append(NextCheck(id="N_perimeter", kind="update_perimeter", params={}, because=because))
    f3 = next((f for f in findings if f.id == "F3"), None)
    low_opt = [p.pair_id for p in ok if p.optical and p.optical.lift.value is not None and p.optical.lift.value < 1.5]
    if low_opt:
        checks.append(NextCheck(id="N_moisture", kind="check_moisture_or_rain", params={"pairs": low_opt}, because=["F3"]))
    checks.append(NextCheck(id="N_validated", kind="rerun_with_validated_products", params={"crid_expected": "P05036"},
                            because=["limit.provisional_products"]))

    # validation levels (kept separate from processing state)
    coh_level = "computed"
    evidence, missing = ["evidence.reproducible_run", "evidence.quality_control"], []
    if cross.status == "ok" and (cross.spearman_recurrence_study.value or 0) > 0.3:
        coh_level = "internally_consistent"
        evidence.append("evidence.cross_geometry")
    if f3 and f3.params["median_lift"] > 2:
        coh_level = "consistent_with_independent_source"
        evidence.append("evidence.optical_location")
    missing += ["missing.field_truth", "missing.validated_products"]
    validation = [ValidationItem(observable="coherence_change_location", level=coh_level, evidence_keys=evidence,
                                 missing_keys=missing),
                  ValidationItem(observable="los_displacement", level="computed" if los_ok else "not_computed",
                                 evidence_keys=["evidence.control_noise"] if los_ok else [],
                                 missing_keys=["missing.sign_check", "missing.gnss_or_levelling", "missing.iono_tropo_correction"]),
                  ValidationItem(observable="cause_of_change", level="not_computed", evidence_keys=[],
                                 missing_keys=["missing.field_truth", "missing.operations_calendar"])]
    return findings, checks, validation
