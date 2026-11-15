"""Reproducible mining-case pipeline, v2.

import -> integrity -> coherence QC (separate from phase QC) -> analysis grid -> controls (calibration/evaluation
split, several documented controls) -> low-coherence flags for 3 quantiles -> polygon statistics (cross-checked
with roi.summarize_raster) -> block-bootstrap intervals -> perimeter / threshold / control sensitivity ->
recurrence (12-day pairs, gaps visible) -> window-matched orbit comparison -> Sentinel-2 strict and exploratory
comparison -> verification sheets -> export -> manifest -> verification -> publication.

Every run is written to cases/<case>/runs/<run_id>/ and published to cases/<case>/output/ only after it passed
verification; nothing from a previous run is reused. See docs/METHOD.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from scipy import ndimage
from shapely.geometry import mapping, shape

from . import coherence_change as cc
from . import export, optical, stats
from .contract import (Acquisition, ControlDef, CrossGeometry, Export, FileRecord, GeometrySummary, Layer, LayerFile,
                       Legend, LosPair, Manifest, Method, MiningCase, OpticalScene, PairResult, PerimeterVersion,
                       Processing, Profile, QualityCheck, Recurrence, Reference, Site, Step, Uncertainty, WindowMatch,
                       Zone, ZoneMetrics, Cluster, Dossier, absent, maybe, measured)
from .findings import derive

METHOD_VERSION = "2.0.0"
REUSED = ["catalog.load/parse_name (product index, CRID, dates)", "quality.check (phase QC, LOS only)",
          "roi.summarize_raster (polygon statistics cross-check)", "raster._colormap (palettes)",
          "recipes.displacement.los_cm_full (phase to LOS, masks)", "recipes.wavelength (product frequency)",
          "uncertainty.robust_sigma (control noise)"]
FLAG_COLORS = {1: (0, 224, 255, 240), 255: (150, 150, 150, 110)}
MASK_PHRASES = ("Bits 0-7 represent subswath encoding", "Bits 8-15 represent bitwise anomaly flags")
GEOM_LETTER = {"ascending": "A", "descending": "D"}


class PipelineError(RuntimeError):
    pass


# ----------------------------------------------------------------------------------------------- inputs log
class InputLog:
    """Hashes every file the run actually reads and compares it with the fingerprint declared by its provenance."""

    def __init__(self, repo_root: Path):
        self.root = repo_root
        self.records: dict[str, FileRecord] = {}

    def __call__(self, path: Path, role: str, declared: str | None = None) -> Path:
        path = Path(path)
        key = str(path.resolve())
        if key not in self.records:
            h = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                rel = str(path.resolve().relative_to(self.root.resolve())).replace("\\", "/")
            except ValueError:
                rel = str(path)
            if declared and declared != h:
                raise PipelineError(f"{rel}: content differs from its declared fingerprint (corrupt or modified)")
            self.records[key] = FileRecord(path=rel, sha256=h, role=role, declared_sha256=declared)
        return path

    def list(self) -> list[FileRecord]:
        return sorted(self.records.values(), key=lambda r: r.path)


def _git(root: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
                                timeout=10).stdout.strip() or None
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


def _seed(text: str) -> int:
    """Stable seed (Python's hash() is randomised per process and would break reproducibility)."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def _date(stamp: str) -> str:
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"


def _same_grid(a, b) -> bool:
    return a["shape"] == b["shape"] and a["crs"] == b["crs"] and all(
        math.isclose(x, y, abs_tol=1e-6) for x, y in zip(tuple(a["transform"])[:6], tuple(b["transform"])[:6]))


def _read(path: Path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        return arr, {"transform": src.transform, "crs": src.crs, "shape": arr.shape}


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


def _index(catalog, data_dir: Path) -> list:
    previous = catalog.DATA_DIR
    try:
        catalog.DATA_DIR = data_dir
        return list(catalog.refresh())
    finally:
        catalog.DATA_DIR = previous
        catalog.load.cache_clear()


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")[:26]).replace(tzinfo=timezone.utc)


def _unc_bootstrap(b: dict, block_m: float, key_low="fraction_low", key_high="fraction_high", sens=None) -> Uncertainty:
    if b.get("status") != "ok" or key_low not in b:
        return Uncertainty(kind="not_estimated", method=f"block bootstrap not possible ({b.get('status', b.get('ratio_status'))}, "
                                                        f"{b.get('n_blocks')} blocks)")
    return Uncertainty(kind="block_bootstrap_interval", low=b[key_low], high=b[key_high], level=0.95, block_m=block_m,
                       n_blocks=b["n_blocks"], method="percentile interval from 2000 resamplings of square blocks",
                       block_size_sensitivity=sens)


# ----------------------------------------------------------------------------------------------- run
def run(case_dir: Path, data_dir: Path, repo_root: Path | None = None, publish: bool = True,
        run_id: str | None = None) -> MiningCase:
    t_start = time.time()
    case_dir = Path(case_dir)
    repo_root = Path(repo_root or case_dir.parents[1])
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging = case_dir / "runs" / run_id
    if staging.exists():
        raise PipelineError(f"run directory {staging} already exists: a run never reuses old files")
    staging.mkdir(parents=True)
    log = InputLog(repo_root)
    cfg_path = log(case_dir / "case_config.json", role="config")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    epsg, mcfg, ocfg, lcfg = cfg["epsg"], cfg["method"], cfg["optical"], cfg["los"]
    quantiles, main_q = mcfg["quantiles"], mcfg["main_quantile"]
    main_profile = f"ring@{main_q}"
    block_m, block_sizes = mcfg["block_m"], mcfg["block_sizes_m"]
    steps: list[Step] = []
    ex: list[Export] = []

    zpath = log(case_dir / cfg["zones_file"], role="zones")
    zfc = json.loads(zpath.read_text(encoding="utf-8"))
    zgeoms = {f["id"]: shape(f["geometry"]) for f in zfc["features"]}
    zprops = {f["id"]: f["properties"] for f in zfc["features"]}
    zones = [Zone(id=k, role=v["role"], area_km2=v.get("area_km2"),
                  source=f"OpenStreetMap ({v.get('osm_type', 'derived')} {v.get('osm_id', '')})".replace(" )", ")"),
                  source_date=v.get("osm_timestamp") or v.get("osm_base_timestamp"), license=v["license"],
                  attribution=v["attribution"], nature=v.get("nature")) for k, v in zprops.items()]
    site = Site(**cfg["site"])
    references = [Reference(**r) for r in cfg["references"]]

    from .. import catalog, quality
    products = [p for p in _index(catalog, Path(data_dir)) if p.level == "GUNW" and p.crid == cfg["radar"]["crid"]]
    coh_name, mask_name = cfg["radar"]["coherence_layer"], cfg["radar"]["mask_layer"]
    if not products:
        return _unavailable(case_dir, staging, cfg, site, zones, zfc, references, log, t_start, run_id, repo_root, publish)
    steps.append(Step(name="import", required=True, status="done", message=f"{len(products)} GUNW ({cfg['radar']['crid']})"))

    # ---------------------------------------------------------------- integrity of every crop
    provs = {}
    for p in products:
        from ..access.nisar_subset import verify
        okv, why = verify(p.folder)
        if not okv:
            raise PipelineError(f"{p.name}: {why}")
        prov = json.loads(log(p.folder / "provenance.json", role="nisar_provenance").read_text(encoding="utf-8"))
        provs[p.id] = prov
        desc = prov["layers"][mask_name].get("description") or ""
        if not all(ph in desc for ph in MASK_PHRASES):
            raise PipelineError(f"{p.name}: mask semantics differ from the decoded layout; update the decoder first")
    steps.append(Step(name="integrity", required=True, status="done",
                      message="files hashed at read time and compared with their declared fingerprints; mask layout "
                              "checked against each product's own description"))

    # ---------------------------------------------------------------- grid and zones
    first = products[0]
    _, grid = _read(log(first.folder / coh_name, role="nisar_coherence", declared=provs[first.id]["layers"][coh_name]["sha256"]))
    pix_km2 = abs(grid["transform"].a * grid["transform"].e) / 1e6
    px_m = abs(grid["transform"].a)
    from shapely.ops import transform as stransform
    from pyproj import Transformer
    fwd = Transformer.from_crs(4326, epsg, always_xy=True).transform
    inv = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    study_g, control_g, panels_g = zgeoms["study"], zgeoms["control"], zgeoms.get("panels_outside")
    study_m = stransform(fwd, study_g)
    Z = {"study": _rasterize(study_g, grid, epsg), "control": _rasterize(control_g, grid, epsg),
         "panels_outside": _rasterize(panels_g, grid, epsg)}
    Z["control_1_2km"] = _rasterize(stransform(inv, study_m.buffer(2000)).intersection(control_g), grid, epsg)
    Z["control_2_4km"] = Z["control"] & ~Z["control_1_2km"]
    Z["study_eroded"] = ndimage.binary_erosion(Z["study"])
    Z["study_dilated"] = ndimage.binary_dilation(Z["study"]) & ~Z["control"]
    Z["study_plus_panels"] = Z["study"] | Z["panels_outside"]

    wc_path = Path(data_dir) / "worldcover" / "worldcover.tif"
    landcover = None
    if wc_path.exists():
        wc_prov = json.loads(log(wc_path.parent / "provenance.json", role="worldcover_provenance").read_text(encoding="utf-8"))
        landcover, wgrid = _read(log(wc_path, role="worldcover", declared=wc_prov["files"]["worldcover.tif"]))
        if not _same_grid(wgrid, grid):
            raise PipelineError("WorldCover is not on the analysis grid")
    from ..access.worldcover import CLASSES

    def lc_share(mask):
        if landcover is None or not mask.any():
            return {}
        v, c = np.unique(landcover[mask], return_counts=True)
        return {CLASSES.get(int(a), str(int(a))): round(float(b) / mask.sum(), 4) for a, b in zip(v, c) if b / mask.sum() >= 0.01}

    controls = {"ring": Z["control"], "ring_outer": Z["control_2_4km"]}
    control_desc = {"ring": "control.ring", "ring_outer": "control.ring_outer"}
    if landcover is not None:
        controls["ring_bare"] = Z["control"] & (landcover == 60)
        controls["ring_crop"] = Z["control"] & (landcover == 40)
        control_desc.update(ring_bare="control.ring_bare", ring_crop="control.ring_crop")
    controls = {k: v for k, v in controls.items() if v.sum() >= 4 * cc.MIN_CONTROL_PIXELS}
    calib = stats.checkerboard(grid["shape"], int(round(mcfg["calibration_block_m"] / px_m)))
    ids = {b: stats.block_ids(grid["shape"], int(round(b / px_m))) for b in block_sizes}
    steps.append(Step(name="grid_and_controls", required=True, status="done",
                      message=f"{grid['shape'][1]}x{grid['shape'][0]} px at {px_m:g} m; controls: {', '.join(controls)}"))

    perimeter_versions = [
        PerimeterVersion(id="osm_v3_2020", label="OSM way 638354631 v3", source="OpenStreetMap",
                         source_date=zprops["study"].get("osm_timestamp"), area_km2=float(Z["study"].sum() * pix_km2),
                         used_as="main", note="mapped quarry land use; not a concession"),
        PerimeterVersion(id="eroded_1px", label="perimeter minus one 20 m pixel", source="derived",
                         source_date=None, area_km2=float(Z["study_eroded"].sum() * pix_km2), used_as="sensitivity",
                         note="boundary placement uncertainty"),
        PerimeterVersion(id="dilated_1px", label="perimeter plus one 20 m pixel", source="derived", source_date=None,
                         area_km2=float(Z["study_dilated"].sum() * pix_km2), used_as="sensitivity",
                         note="boundary placement uncertainty"),
        PerimeterVersion(id="with_panels_2020", label="perimeter + OSM parcels 2020", source="OpenStreetMap",
                         source_date=zprops.get("panels_outside", {}).get("osm_base_timestamp"),
                         area_km2=float(Z["study_plus_panels"].sum() * pix_km2), used_as="sensitivity",
                         note="parcels semantics unconfirmed; not enlarged to fit the flags")]

    # ---------------------------------------------------------------- optical scenes (coverage measured in the zones)
    scenes = optical.index(Path(data_dir) / ocfg["dir"], Z, log, ocfg["min_clear_study"], ocfg["min_clear_control"])
    optical_scenes = [OpticalScene(item_id=s["item_id"], datetime=s["datetime"], platform=s.get("platform"),
                                   processing_baseline=s.get("processing_baseline"),
                                   cloud_cover_pct_tile=s.get("cloud_cover_pct_tile"),
                                   clear_fraction_study=round(s["clear_study"], 4),
                                   clear_fraction_control=round(s["clear_control"], 4),
                                   doubtful_fraction_study=round(s["doubtful_study"], 4), usable=s["usable"],
                                   reason=s["reason"]) for s in scenes]
    search_rec = {}
    inv_s2 = case_dir / "inventory" / "sentinel2.json"
    if inv_s2.exists():
        r = json.loads(log(inv_s2, role="inventory").read_text(encoding="utf-8"))
        search_rec = {"searched_utc": r.get("searched_utc"), "catalogue": r.get("catalogue"), "tile": r.get("tile"),
                      "complete": (r.get("completeness") or {}).get("complete"),
                      "number_matched": (r.get("completeness") or {}).get("number_matched"),
                      "n_tile": (r.get("completeness") or {}).get("n_tile"), "dn_convention": r.get("dn_convention")}

    layers: list[Layer] = []
    out_dir = staging

    def add_layer(layer: Layer):
        layers.append(layer)

    # ---------------------------------------------------------------- per pair
    acquisitions, pairs, los_pairs = [], [], []
    keep = {}           # pair_id -> arrays kept for recurrence / matching
    for p in sorted(products, key=lambda x: (x.direction, x.ref)):
        prov = provs[p.id]
        ident, proc = prov.get("identification", {}), prov.get("processing", {})
        gid = f"{p.track:03d}{GEOM_LETTER[p.direction]}_F{p.frame:03d}"
        coh_path = log(p.folder / coh_name, role="nisar_coherence", declared=prov["layers"][coh_name]["sha256"])
        mask_path = log(p.folder / mask_name, role="nisar_mask", declared=prov["layers"][mask_name]["sha256"])
        for name in ("unwrappedInterferogram_HH_unwrappedPhase.tif", "unwrappedInterferogram_HH_coherenceMagnitude.tif",
                     "unwrappedInterferogram_HH_connectedComponents.tif"):
            log(p.folder / name, role="nisar_80m", declared=prov["layers"][name]["sha256"])
        log(p.folder / "radar_geometry.npz", role="radar_geometry", declared=prov["files"]["radar_geometry.npz"])
        coh, cgrid = _read(coh_path)
        mask, mgrid = _read(mask_path)
        grid_ok = _same_grid(cgrid, grid) and _same_grid(mgrid, grid)
        if not grid_ok:                       # never resampled: compared on the analysis grid or not at all
            coh = np.full(grid["shape"], np.nan, "float32")
            mask = np.zeros(grid["shape"], "uint32")
        coh = coh.astype("float32")
        base_valid = cc.mask_valid(mask) & np.isfinite(coh)
        anomaly = cc.anomaly_flags(mask) & base_valid
        valid = base_valid & ~anomaly
        analysed = Z["study"] | Z["control"]
        vfrac = float(valid[analysed].mean())
        med = float(np.median(coh[valid & analysed])) if (valid & analysed).any() else None
        low = mask.astype("int64") & 0xFF
        sec_bad = float(((low % 10) == 0)[analysed].mean())
        ref_bad = float((((low // 10) % 10) == 0)[analysed].mean())
        water = float((((low // 100) % 10) != 0)[analysed].mean())
        all_coh = coh[analysed & np.isfinite(coh)]
        reasons = []
        if ref_bad >= 0.5:
            reasons.append(f"product mask: reference acquisition ({_date(p.ref)}) marked invalid on {ref_bad:.0%} of the analysed zones")
        if sec_bad >= 0.5:
            reasons.append(f"product mask: secondary acquisition ({_date(p.sec)}) marked invalid on {sec_bad:.0%} of the analysed zones")
        if vfrac < mcfg["min_valid_fraction"] and not reasons:
            reasons.append(f"valid fraction {vfrac:.2f} below {mcfg['min_valid_fraction']} in the analysed zones")
        if med is not None and med < mcfg["min_median_coherence"]:
            reasons.append(f"median coherence {med:.2f} below {mcfg['min_median_coherence']} in the analysed zones")
        coh_qc = QualityCheck(ok=not reasons, reasons=reasons,
                              metrics={"median_coherence_zones": None if med is None else round(med, 4),
                                       "median_coherence_unmasked": None if not all_coh.size else round(float(np.median(all_coh)), 4),
                                       "valid_fraction_zones": round(vfrac, 4), "reference_invalid_fraction": round(ref_bad, 4),
                                       "secondary_invalid_fraction": round(sec_bad, 4), "water_fraction": round(water, 4),
                                       "anomaly_pixels_zones": int(anomaly[analysed].sum())})
        q = quality.check(p)
        phase_qc = QualityCheck(ok=q["ok"], reasons=q["reasons"],
                                metrics={"phase_sigma_rad": q["phase_sigma_rad"], "coherence_median_80m": q["coherence_median"]})
        acquisitions.append(Acquisition(
            pair_id=p.id, granule_id=p.name, collection=prov["source_url"].split("/")[4], crid=p.crid, maturity=p.maturity,
            geometry_id=gid, direction=p.direction, track=p.track, frame=p.frame,
            reference_time=ident.get("referenceZeroDopplerStartTime", p.ref), secondary_time=ident.get("secondaryZeroDopplerStartTime", p.sec),
            span_days=p.span_days, product_version=ident.get("productVersion"),
            product_specification_version=ident.get("productSpecificationVersion"), software_version=proc.get("software_version"),
            processing_datetime=ident.get("processingDateTime"), doi=ident.get("productDoi"), source_url=prov["source_url"],
            bytes_transferred=prov.get("bytes_transferred"),
            layers=[LayerFile(name=k, sha256=v["sha256"], spacing_m=v.get("spacing_m"), units=v.get("units")) for k, v in prov["layers"].items()],
            looks={k: proc.get(k) for k in ("wrapped_azimuth_looks", "wrapped_range_looks", "unwrapped_azimuth_looks", "unwrapped_range_looks")},
            coherence_qc=coh_qc, phase_qc=phase_qc))
        acq = acquisitions[-1]
        base = dict(pair_id=p.id, geometry_id=gid, direction=p.direction, reference_date=_date(p.ref),
                    secondary_date=_date(p.sec), span_days=p.span_days)
        empty = dict(main=None, zones=[], profiles=[], statistical=absent("fraction", "pair not analysed", "not_measured"),
                     perimeter_sensitivity={}, zone_stability={}, n_clusters=None, clusters_shown=[], layer_ids=[], optical=[])
        if not grid_ok:
            pairs.append(PairResult(**base, **empty, status="incompatible_grid",
                                    reasons=["coherence or mask grid differs from the analysis grid (no resampling)"]))
            los_pairs.append(_los_not(p.id, phase_qc.ok, "incompatible grid"))
            continue
        if not coh_qc.ok:
            pairs.append(PairResult(**base, **empty, status="rejected_coherence_qc", reasons=coh_qc.reasons))
            los_pairs.append(_los_not(p.id, phase_qc.ok, "pair rejected by the coherence QC"))
            continue

        # profiles
        profiles, flags_by = [], {}
        for cname, cmask in controls.items():
            for qv in quantiles:
                r = stats.threshold_split(coh, valid, cmask, calib, qv)
                pid = f"{cname}@{qv}"
                if r["status"] != "ok":
                    continue
                flags_by[pid] = r["flagged"]
                s = cc.zone_stats(r["flagged"], valid, Z["study"], coh, pix_km2)
                ratio = (s["flagged_fraction_of_observable"] / r["evaluation_rate"]) if r["evaluation_rate"] else None
                profiles.append(Profile(
                    id=pid, control_id=cname, quantile=qv, threshold=measured(r["threshold"], "coherence"),
                    calibration_rate=measured(r["calibration_rate"], "fraction"),
                    evaluation_rate=measured(r["evaluation_rate"], "fraction"),
                    study_flagged_area_km2=measured(s["flagged_area_km2"], "km2"),
                    study_flagged_fraction=measured(s["flagged_fraction_of_observable"], "fraction"),
                    ratio_to_evaluation_rate=maybe(ratio, "ratio", "zero flag rate in the evaluation part of the control"),
                    exceeds_control=bool(s["flagged_fraction_of_observable"] > r["evaluation_rate"])))
        if main_profile not in flags_by:
            pairs.append(PairResult(**base, **empty, status="insufficient_control",
                                    reasons=["too few valid pixels in the calibration or evaluation part of the ring control"]))
            continue
        flagged = flags_by[main_profile]
        mainp = next(x for x in profiles if x.id == main_profile)
        evalmask = Z["control"] & ~calib

        # block bootstrap of the perimeter fraction and of the ratio to the evaluation rate, block-size sensitivity
        boots = {}
        for b in block_sizes:
            k1, n1 = stats.block_counts(flagged, valid, Z["study"], ids[b])
            k2, n2 = stats.block_counts(flagged, valid, evalmask, ids[b])
            boots[b] = stats.bootstrap_ratio(k1, n1, k2, n2, seed=_seed(p.id))
        sens_f = {f"{int(b)} m": [boots[b]["fraction_low"], boots[b]["fraction_high"]] for b in block_sizes if boots[b].get("status") == "ok"}
        sens_r = {f"{int(b)} m": [boots[b]["ratio_low"], boots[b]["ratio_high"]] for b in block_sizes if boots[b].get("ratio_status") == "ok"}
        statistical = measured(mainp.study_flagged_fraction.value, "fraction", _unc_bootstrap(boots[block_m], block_m, sens=sens_f))
        rb = boots[block_m]
        mainp = mainp.model_copy(update={"ratio_to_evaluation_rate": maybe(
            mainp.ratio_to_evaluation_rate.value, "ratio", "zero flag rate in the evaluation part",
            uncertainty=(_unc_bootstrap(rb, block_m, "ratio_low", "ratio_high", sens_r)
                         if mainp.ratio_to_evaluation_rate.value is not None and rb.get("ratio_status") == "ok"
                         else Uncertainty(kind="not_estimated", method=f"ratio interval {rb.get('ratio_status', rb.get('status'))}")
                         if mainp.ratio_to_evaluation_rate.value is not None else None))})
        profiles = [mainp if x.id == main_profile else x for x in profiles]

        # zone metrics, cross-check with the existing polygon module
        zm = {}
        for zid in ("study", "panels_outside", "control", "control_1_2km", "control_2_4km"):
            zm[zid] = cc.zone_stats(flagged, valid, Z[zid], coh, pix_km2)
        flag_u8 = np.where(valid, flagged.astype("uint8"), 255).astype("uint8")
        tif = out_dir / "rasters" / f"flags_{p.id}.tif"
        export.write_geotiff(tif, flag_u8, grid["transform"], epsg, nodata=255,
                             tags={"pair": p.id, "values": "0 observed not flagged; 1 low coherence relative to control; "
                                   "255 not observed (product mask, water, anomaly)", "threshold": mainp.threshold.value,
                                   "profile": main_profile})
        ex.append(Export(id=f"flags_{p.id}", format="geotiff", path=f"rasters/flags_{p.id}.tif",
                         description_key="export.flags_geotiff", sha256=export.sha256(tif)))
        study_geo = out_dir / "exports" / "study_perimeter.geojson"
        if not study_geo.exists():
            export.write_json(study_geo, {"type": "FeatureCollection", "features": [
                {"type": "Feature", "geometry": mapping(study_g), "properties": zprops["study"]}]})
        from ..roi import summarize_raster
        chk = summarize_raster(tif, study_geo, unit="flag", threshold=0.5)
        s = zm["study"]
        if not (math.isclose(chk["valid_area_km2"], s["observable_area_km2"], rel_tol=1e-9, abs_tol=1e-9)
                and math.isclose(chk["selected_area_km2"] or 0.0, s["flagged_area_km2"] or 0.0, rel_tol=1e-9, abs_tol=1e-9)):
            raise PipelineError(f"{p.id}: polygon statistics disagree with roi.summarize_raster")

        def metrics(zid):
            s = zm[zid]
            why = "zone not observed in this pair" if s["zone_pixels"] else "empty zone"
            return ZoneMetrics(zone_id=zid, zone_area_km2=s["zone_area_km2"],
                               observable_area_km2=measured(s["observable_area_km2"], "km2"),
                               observable_fraction=maybe(s["observable_fraction"], "fraction", "empty zone"),
                               flagged_area_km2=maybe(s["flagged_area_km2"], "km2", why),
                               flagged_fraction=maybe(s["flagged_fraction_of_observable"], "fraction", why),
                               median_coherence=maybe(s["median_coherence"], "coherence", why))
        zone_list = [metrics(z) for z in zm]

        # perimeter sensitivity
        per = {}
        for vid, m in (("eroded_1px", Z["study_eroded"]), ("dilated_1px", Z["study_dilated"]), ("with_panels_2020", Z["study_plus_panels"])):
            sv = cc.zone_stats(flagged, valid, m, coh, pix_km2)
            per[f"{vid}:area"] = maybe(sv["flagged_area_km2"], "km2", "not observed")
            per[f"{vid}:fraction"] = maybe(sv["flagged_fraction_of_observable"], "fraction", "not observed")

        # clusters and their stability across quantiles
        min_px = max(1, int(round(mcfg["min_cluster_km2"] / pix_km2)))
        labels, clusters = cc.change_zones(flagged, Z["study"], coh, min_px)
        low_flags = flags_by.get(f"ring@{min(quantiles)}")
        stab = {}
        for qv in quantiles:
            if qv == main_q or f"ring@{qv}" not in flags_by:
                continue
            t = stats.contingency(flagged, flags_by[f"ring@{qv}"], Z["study"] & valid)
            stab[f"jaccard_vs_q{qv}"] = maybe(t["jaccard"], "fraction", "empty union")
        if "ring_bare@" + str(main_q) in flags_by:
            t = stats.contingency(flagged, flags_by[f"ring_bare@{main_q}"], Z["study"] & valid)
            stab["jaccard_vs_ring_bare"] = maybe(t["jaccard"], "fraction", "empty union")
        if clusters and low_flags is not None:
            kept = sum(1 for c in clusters if low_flags[labels == c["id"]].mean() >= 0.5)
            stab["clusters_retained_at_lowest_quantile"] = measured(kept / len(clusters), "fraction")
        shown = clusters[: mcfg["clusters_shown"]]
        gj = export.clusters_geojson(labels, shown, grid["transform"], epsg, {"pair_id": p.id})
        sha = export.write_json(out_dir / "clusters" / f"clusters_{p.id}.geojson", gj)
        ex.append(Export(id=f"clusters_{p.id}", format="geojson", path=f"clusters/clusters_{p.id}.geojson",
                         description_key="export.clusters_geojson", sha256=sha))

        # layers
        lid_c, lid_f = f"coh_{p.id}", f"flags_{p.id}"
        info = export.png_continuous(out_dir / "layers" / f"{lid_c}.png", coh, grid["transform"], epsg, "magma", 0.0, 1.0,
                                     levels=mcfg["coherence_preview_levels"])
        add_layer(Layer(id=lid_c, kind="observation", title_key="layer.coherence", params={"pair": p.id},
                        url=f"layers/{lid_c}.png", corners=info["corners"],
                        legend=Legend(kind="continuous", unit="coherence (0-1)", vmin=0, vmax=1, cmap="magma",
                                      stops=info["stops"], levels=info["levels"]),
                        date_start=_date(p.ref), date_end=_date(p.sec), source_ids=[p.id], resolution_m=px_m,
                        display_note_key="layer.note.quantized"))
        info = export.png_categorical(out_dir / "layers" / f"{lid_f}.png", flag_u8, grid["transform"], epsg, FLAG_COLORS)
        add_layer(Layer(id=lid_f, kind="derived", title_key="layer.flags", params={"pair": p.id, "profile": main_profile},
                        url=f"layers/{lid_f}.png", corners=info["corners"],
                        legend=Legend(kind="categorical", classes=info["classes"],
                                      class_keys={"1": "legend.flagged", "255": "legend.not_observed"}),
                        date_start=_date(p.ref), date_end=_date(p.sec), source_ids=[p.id], resolution_m=px_m,
                        export=f"rasters/flags_{p.id}.tif"))
        layer_ids = [lid_c, lid_f]

        # optical comparisons: strict and exploratory, kept apart
        t0, t1 = _dt(acq.reference_time), _dt(acq.secondary_time)
        comps = []
        for mode, gap in (("strict", ocfg["strict_gap_days"]), ("exploratory", ocfg["exploratory_gap_days"])):
            comp, extra = optical.compare(mode, gap, scenes, t0, t1, flagged, valid, Z, calib, ids[block_m],
                                          {**ocfg, "block_m": block_m}, log, seed=_seed(p.id + mode))
            comps.append(comp)
            if extra is not None and mode == "strict":
                keep.setdefault(p.id, {})["optical"] = extra
                lid_o = f"opt_{p.id}"
                vmax = max(extra["threshold"] * 3, extra["threshold"] + 0.05)
                info = export.png_continuous(out_dir / "layers" / f"{lid_o}.png", np.where(extra["oflag"], extra["d"], np.nan),
                                             grid["transform"], epsg, "inferno", extra["threshold"], vmax)
                add_layer(Layer(id=lid_o, kind="reference", title_key="layer.optical_change",
                                params={"pair": p.id, "before": comp.before_item, "after": comp.after_item},
                                url=f"layers/{lid_o}.png", corners=info["corners"],
                                legend=Legend(kind="continuous", unit="reflectance change (L2 norm)", vmin=extra["threshold"],
                                              vmax=vmax, cmap="inferno", stops=info["stops"], levels=info["levels"]),
                                date_start=comp.before_datetime[:10], date_end=comp.after_datetime[:10],
                                source_ids=[comp.before_item, comp.after_item], resolution_m=px_m))
                layer_ids.append(lid_o)
                for tag, sc, xx in (("before", extra["before"], extra["x0"]), ("after", extra["after"], extra["x1"])):
                    lid = f"s2{tag}_{p.id}"
                    with rasterio.open(sc["stack"]) as src:
                        st_t = src.transform
                    info = export.png_rgb(out_dir / "layers" / f"{lid}.jpg", xx[[2, 1, 0]], st_t, epsg)
                    add_layer(Layer(id=lid, kind="basemap", title_key=f"layer.s2_{tag}", params={"item": sc["item_id"], "pair": p.id},
                                    url=f"layers/{lid}.jpg", corners=info["corners"], legend=Legend(kind="rgb"),
                                    date_start=sc["datetime"][:10], date_end=sc["datetime"][:10],
                                    source_ids=[sc["item_id"]], resolution_m=px_m))
                    layer_ids.append(lid)

        pairs.append(PairResult(
            **base, status="ok", reasons=[], main=metrics("study"), zones=zone_list, profiles=profiles,
            statistical=statistical, perimeter_sensitivity=per, zone_stability=stab, n_clusters=len(clusters),
            clusters_shown=[Cluster(id=c["id"], area_km2=c["pixels"] * pix_km2, centroid=_lonlat(grid, epsg, c["row"], c["col"]),
                                    median_coherence=c["median_coherence"],
                                    retained_at_lower_quantile=None if low_flags is None else bool(low_flags[labels == c["id"]].mean() >= 0.5))
                            for c in shown],
            layer_ids=layer_ids, optical=comps))
        keep.setdefault(p.id, {}).update(flagged=flagged, valid=valid, labels=labels, gid=gid, span=p.span_days,
                                         ref=acq.reference_time, sec=acq.secondary_time)

        # LOS (reported, not interpreted)
        lp, disp, grid80 = _los(p, phase_qc.ok, study_g, control_g, epsg, lcfg)
        if disp is not None:
            lid = f"los_{p.id}"
            lim = lcfg["display_limit_cm"]
            info = export.png_continuous(out_dir / "layers" / f"{lid}.png", disp, grid80["transform"], epsg, "RdBu_r", -lim, lim)
            add_layer(Layer(id=lid, kind="derived", title_key="layer.los", params={"pair": p.id}, url=f"layers/{lid}.png",
                            corners=info["corners"], legend=Legend(kind="continuous", unit="cm (LOS, sign unverified)",
                                                                   vmin=-lim, vmax=lim, cmap="RdBu_r", stops=info["stops"],
                                                                   levels=info["levels"]),
                            date_start=_date(p.ref), date_end=_date(p.sec), source_ids=[p.id], resolution_m=80.0,
                            display_note_key="layer.note.los_not_interpreted"))
            pairs[-1].layer_ids.append(lid)
        los_pairs.append(lp)

    n_ok = sum(1 for x in pairs if x.status == "ok")
    steps.append(Step(name="coherence_qc", required=True, status="done",
                      message=f"{n_ok} of {len(pairs)} pairs pass the coherence QC"))
    steps.append(Step(name="low_coherence_flags", required=True, status="done" if n_ok else "failed",
                      message=f"{len(controls)} controls x {len(quantiles)} quantiles"))
    steps.append(Step(name="polygon_statistics", required=True, status="done" if n_ok else "failed",
                      message="cross-checked with roi.summarize_raster for every analysed pair"))

    # ---------------------------------------------------------------- recurrence (same span only, gaps visible)
    geometries, recurrences = [], []
    span12 = mcfg["recurrence_span_days"]
    for gid in sorted({a.geometry_id for a in acquisitions}):
        gacq = [a for a in acquisitions if a.geometry_id == gid]
        gpairs = [x for x in pairs if x.geometry_id == gid]
        chain = sorted([x for x in gpairs if x.status == "ok" and x.span_days == span12], key=lambda x: x.reference_date)
        recs = []
        if chain:
            fl = [keep[x.pair_id]["flagged"] for x in chain]
            va = [keep[x.pair_id]["valid"] for x in chain]
            frac, seen = cc.recurrence(fl, va)
            lid, lidn = f"recurrence_{gid}_{span12}d", f"observed_{gid}_{span12}d"
            sha = export.write_geotiff(out_dir / "rasters" / f"{lid}.tif", frac, grid["transform"], epsg,
                                       tags={"values": f"fraction of observed {span12}-day pairs flagged", "pairs": ",".join(x.pair_id for x in chain)})
            ex.append(Export(id=lid, format="geotiff", path=f"rasters/{lid}.tif", description_key="export.recurrence_geotiff", sha256=sha))
            sha = export.write_geotiff(out_dir / "rasters" / f"{lidn}.tif", seen.astype("uint8"), grid["transform"], epsg, nodata=0,
                                       tags={"values": f"number of observed {span12}-day pairs"})
            ex.append(Export(id=lidn, format="geotiff", path=f"rasters/{lidn}.tif", description_key="export.observed_geotiff", sha256=sha))
            info = export.png_continuous(out_dir / "layers" / f"{lid}.png", np.where(frac > 0, frac, np.nan), grid["transform"], epsg, "viridis", 0, 1)
            add_layer(Layer(id=lid, kind="derived", title_key="layer.recurrence", params={"geometry": gid, "n_pairs": len(chain), "span_days": span12},
                            url=f"layers/{lid}.png", corners=info["corners"],
                            legend=Legend(kind="continuous", unit="fraction of observed pairs", vmin=0, vmax=1, cmap="viridis",
                                          stops=info["stops"], levels=info["levels"]),
                            date_start=chain[0].reference_date, date_end=chain[-1].secondary_date, source_ids=[x.pair_id for x in chain],
                            resolution_m=px_m, export=f"rasters/{lid}.tif"))
            info = export.png_continuous(out_dir / "layers" / f"{lidn}.png", np.where(seen > 0, seen, np.nan).astype("float32"),
                                         grid["transform"], epsg, "cividis", 0, len(chain))
            add_layer(Layer(id=lidn, kind="derived", title_key="layer.observed_count", params={"geometry": gid, "n_pairs": len(chain)},
                            url=f"layers/{lidn}.png", corners=info["corners"],
                            legend=Legend(kind="continuous", unit="observed pairs", vmin=0, vmax=len(chain), cmap="cividis",
                                          stops=info["stops"], levels=info["levels"]),
                            date_start=chain[0].reference_date, date_end=chain[-1].secondary_date,
                            source_ids=[x.pair_id for x in chain], resolution_m=px_m, export=f"rasters/{lidn}.tif"))
            st = Z["study"]
            gaps = []
            allp = sorted(gpairs, key=lambda x: x.reference_date)
            for a_, b_ in zip(chain, chain[1:]):
                if a_.secondary_date != b_.reference_date:
                    gaps.append([a_.secondary_date, b_.reference_date])
            for x in allp:
                if x.status != "ok" or x.span_days != span12:
                    gaps.append([x.reference_date, x.secondary_date])
            gaps = sorted({tuple(g) for g in gaps})
            disjoint, last = [], None
            for x in chain:
                if last is None or x.reference_date > last:
                    disjoint.append(x)
                    last = x.secondary_date
            fd, vd = [keep[x.pair_id]["flagged"] for x in disjoint], [keep[x.pair_id]["valid"] for x in disjoint]
            frac_d, seen_d = cc.recurrence(fd, vd)
            adj = [stats.contingency(fl[i], fl[i + 1], st & va[i] & va[i + 1])["jaccard"] for i in range(len(chain) - 1)
                   if chain[i].secondary_date == chain[i + 1].reference_date]
            two = [stats.contingency(fl[i], fl[i + 2], st & va[i] & va[i + 2])["jaccard"] for i in range(len(chain) - 2)]
            ms = seen[st]
            recs.append(Recurrence(
                geometry_id=gid, span_days=span12, pair_ids=[x.pair_id for x in chain], gaps=[list(g) for g in gaps],
                layer_id=lid, count_layer_id=lidn, observed_pairs_min=int(ms.min()), observed_pairs_max=int(ms.max()),
                flagged_ever_km2=measured(float(((frac > 0) & st).sum() * pix_km2), "km2"),
                flagged_half_or_more_km2=measured(float(((frac >= 0.5) & st & (seen >= mcfg["min_observed_pairs"])).sum() * pix_km2), "km2"),
                disjoint_pairs=[x.pair_id for x in disjoint],
                flagged_half_or_more_disjoint_km2=measured(float(((frac_d >= 0.5) & st & (seen_d >= 2)).sum() * pix_km2), "km2"),
                jaccard_adjacent_pairs=maybe(float(np.median([a for a in adj if a is not None])) if adj else None, "fraction", "no adjacent pairs"),
                jaccard_pairs_two_apart=maybe(float(np.median([a for a in two if a is not None])) if two else None, "fraction", "fewer than 3 pairs")))
            keep[f"rec_{gid}"] = {"frac": frac, "seen": seen}
            # overlap-based zone repetition for the shown clusters
            for x in chain:
                lab = keep[x.pair_id]["labels"]
                upd = []
                for c in x.clusters_shown:
                    sel = lab == c.id
                    others = [y for y in chain if y.pair_id != x.pair_id]
                    obs = [y for y in others if keep[y.pair_id]["valid"][sel].mean() >= 0.5]
                    hits = sum(1 for y in obs if stats.overlap_match(sel, keep[y.pair_id]["labels"], mcfg["zone_overlap_min"]))
                    upd.append(c.model_copy(update={"pairs_same_geometry_overlapping": hits, "pairs_same_geometry_observed": len(obs)}))
                x.clusters_shown[:] = upd
        recurrences += recs
        geometries.append(GeometrySummary(geometry_id=gid, direction=gacq[0].direction, track=gacq[0].track, frame=gacq[0].frame,
                                          crid=gacq[0].crid, n_pairs=len(gpairs), n_pairs_analysed=sum(1 for x in gpairs if x.status == "ok"),
                                          recurrence=recs))
    steps.append(Step(name="recurrence", required=False, status="done" if recurrences else "unavailable"))

    # ---------------------------------------------------------------- window-matched orbit comparison
    cross = _cross(pairs, acquisitions, keep, Z, ids[block_m], mcfg)
    steps.append(Step(name="cross_geometry", required=False, status="done" if cross.status == "ok" else "unavailable",
                      message=cross.rule))
    n_strict = sum(1 for x in pairs for c in x.optical if c.mode == "strict" and c.status == "ok")
    steps.append(Step(name="optical_strict", required=False, status="done" if n_strict else "unavailable",
                      message=f"{n_strict} strict comparisons; {sum(1 for s in scenes if s['usable'])} usable of {len(scenes)} scenes"))

    # ---------------------------------------------------------------- basemaps with their real dates
    usable_full = [s for s in scenes if s["clear_study"] >= 0.999 and s["clear_control"] >= 0.99]
    for tag, s in (("early", usable_full[0] if usable_full else None), ("late", usable_full[-1] if usable_full else None)):
        if s is None:
            continue
        with rasterio.open(s["stack"]) as src:
            rgb, st_t = src.read([3, 2, 1]).astype("float32"), src.transform
        info = export.png_rgb(out_dir / "layers" / f"s2_{tag}.jpg", rgb, st_t, epsg)
        add_layer(Layer(id=f"s2_{tag}", kind="basemap", title_key="layer.s2_true_colour", params={"item": s["item_id"]},
                        url=f"layers/s2_{tag}.jpg", corners=info["corners"], legend=Legend(kind="rgb"),
                        date_start=s["datetime"][:10], date_end=s["datetime"][:10], source_ids=[s["item_id"]], resolution_m=px_m))

    # ---------------------------------------------------------------- verification sheets
    dossiers = _dossiers(pairs, keep, recurrences, Z, landcover, grid, epsg, pix_km2, mcfg, out_dir, ex)

    # ---------------------------------------------------------------- findings, evidence levels, next checks
    findings, validation, checks = derive({"pairs": pairs, "cross": cross, "los": los_pairs, "recurrence": recurrences,
                                           "dossiers": dossiers, "scenes": optical_scenes, "controls": list(controls)},
                                          {**mcfg, "main_profile": main_profile})

    # ---------------------------------------------------------------- tables
    _tables(pairs, cross, out_dir, ex, main_profile)
    export.write_json(out_dir / "zones.geojson", zfc)
    ex.append(Export(id="study_geojson", format="geojson", path="exports/study_perimeter.geojson",
                     description_key="export.study_geojson", sha256=export.sha256(out_dir / "exports" / "study_perimeter.geojson")))

    required_ok = all(s.status == "done" for s in steps if s.required)
    optional_missing = [s.name for s in steps if not s.required and s.status != "done"]
    status = "failed" if not required_ok else ("partial" if optional_missing or n_ok < len(pairs) else "complete")
    processing = Processing(status=status, steps=steps,
                            rule="failed if a required step failed; partial if an optional step is unavailable or a "
                                 "pair could not be analysed; complete otherwise",
                            blockers=[f"blocker.step_unavailable:{n}" for n in optional_missing])
    method = Method(id="low-coherence-relative-to-control", version=METHOD_VERSION,
                    observable_key="observable.low_coherence_relative_to_control",
                    parameters={**{f"method.{k}": v for k, v in mcfg.items()}, **{f"optical.{k}": v for k, v in ocfg.items()},
                                **{f"los.{k}": v for k, v in lcfg.items()}, "radar.coherence_layer": coh_name, "radar.crid": cfg["radar"]["crid"]},
                    controls=[ControlDef(id=k, label_key=control_desc[k], description=k, pixels=int(v.sum()),
                                         area_km2=float(v.sum() * pix_km2), landcover_share=lc_share(v)) for k, v in controls.items()]
                    + [ControlDef(id="study", label_key="control.study_reference", description="study perimeter (for comparison)",
                                  pixels=int(Z["study"].sum()), area_km2=float(Z["study"].sum() * pix_km2), landcover_share=lc_share(Z["study"]))],
                    main_profile=main_profile, reused_modules=REUSED,
                    steps=[s.name for s in steps] + ["export", "manifest", "verification", "publication"],
                    autocorrelation=_autocorr(pairs, keep, controls["ring"], px_m),
                    block_size_justification=mcfg["block_justification"])
    limits = ["limit.observable_is_relative", "limit.coherence_contributions", "limit.cause_not_identified",
              "limit.no_ore_volume_production", "limit.provisional_products", "limit.perimeter_2020_not_legal",
              "limit.control_not_proven_stable", "limit.threshold_is_selection", "limit.no_data_is_not_no_change",
              "limit.optical_is_cross_sensor", "limit.spectral_hypotheses", "limit.los_not_interpreted",
              "limit.window_length", "limit.no_field_truth"]
    case_kw = dict(case_id=cfg["case_id"], run_id=run_id, data_nature=cfg.get("data_nature", "real"),
                   presentation_level_key="presentation.exploratory", question_key="question.low_coherence",
                   user_key="user.monitoring_analyst", site=site, zones=zones, perimeter_versions=perimeter_versions,
                   zones_url="zones.geojson", acquisitions=acquisitions, optical_scenes=optical_scenes,
                   optical_search=search_rec, method=method, pairs=pairs, geometries=geometries, cross_geometry=cross,
                   los=los_pairs, layers=layers, exports=ex, references=references, validation=validation,
                   findings=findings, dossiers=dossiers, next_checks=checks, limits=limits, processing=processing)
    return _finish(case_kw, staging, case_dir, cfg_path, log, t_start, run_id, repo_root, publish)


# ----------------------------------------------------------------------------------------------- helpers
def _los_not(pid: str, phase_ok: bool, reason: str) -> LosPair:
    na = lambda u: absent(u, reason, "not_measured")  # noqa: E731
    from .. import config as legacy
    return LosPair(pair_id=pid, status="not_computed", phase_qc_ok=phase_ok, control_sigma_cm=na("cm"), study_p05_cm=na("cm"),
                   study_p95_cm=na("cm"), within_3sigma=None, layer_id=None, sign_verified=legacy.LOS_SIGN_VERIFIED, reason=reason)


def _los(p, phase_ok: bool, study_g, control_g, epsg: int, cfg: dict):
    """LOS on the 80 m grid referenced to the control ring; reported only, never interpreted."""
    from ..recipes import displacement
    from ..uncertainty import robust_sigma
    from .. import config as legacy
    if not phase_ok:
        return _los_not(p.id, False, "phase QC failed (flat phase or low median coherence)"), None, None
    if cfg["coherence_min"] != legacy.COHERENCE_MIN:
        raise PipelineError("los.coherence_min must equal the inherited COHERENCE_MIN")
    disp, _, prof, _, _ = displacement.los_cm_full(p, corrections=())
    grid80 = {"transform": prof["transform"], "crs": prof["crs"], "shape": disp.shape}
    study, control = _rasterize(study_g, grid80, epsg), _rasterize(control_g, grid80, epsg)
    comp = displacement._components_raster(p)
    okc = np.isfinite(disp) & control
    if comp is not None and okc.any():
        lab = comp[okc]
        lab = lab[lab > 0]
        if lab.size:
            disp = np.where(comp == int(np.bincount(lab.astype(np.int64)).argmax()), disp, np.nan)
    okc = np.isfinite(disp) & control
    if okc.sum() < cfg["min_control_pixels"]:
        return _los_not(p.id, True, "too few coherent control pixels in the reference component"), None, None
    disp = disp - float(np.median(disp[okc]))
    sigma = robust_sigma(disp[okc])
    vals = disp[np.isfinite(disp) & study]
    if vals.size < 50 or not math.isfinite(sigma):
        return _los_not(p.id, True, "too few coherent perimeter pixels"), None, None
    p05, p95 = float(np.percentile(vals, 5)), float(np.percentile(vals, 95))
    return LosPair(pair_id=p.id, status="computed", phase_qc_ok=True,
                   control_sigma_cm=measured(sigma, "cm", Uncertainty(kind="not_estimated", method="sigma of the control; spatially correlated noise")),
                   study_p05_cm=measured(p05, "cm"), study_p95_cm=measured(p95, "cm"),
                   within_3sigma=bool(max(abs(p05), abs(p95)) <= 3 * sigma), layer_id=f"los_{p.id}",
                   sign_verified=legacy.LOS_SIGN_VERIFIED), disp, grid80


def _cross(pairs, acquisitions, keep, Z, ids, mcfg) -> CrossGeometry:
    rule = (f"one-to-one matching of {mcfg['recurrence_span_days']}-day pairs of different orbits by largest window "
            f"overlap, at least {mcfg['min_overlap_days']} days; compared on perimeter pixels valid in both")
    ok = [x for x in pairs if x.status == "ok" and x.span_days == mcfg["recurrence_span_days"]]
    acq = {a.pair_id: a for a in acquisitions}
    geoms = sorted({x.geometry_id for x in ok})
    na = lambda r: absent("fraction", r, "unavailable")  # noqa: E731
    if len(geoms) < 2:
        return CrossGeometry(status="unavailable", rule=rule, matches=[], unmatched=[x.pair_id for x in ok],
                             median_jaccard=na("fewer than two geometries"), reason="fewer than two geometries")
    A = [x for x in ok if x.geometry_id == geoms[0]]
    B = [x for x in ok if x.geometry_id == geoms[1]]
    cand = []
    for a in A:
        for b in B:
            o = stats.overlap_days((acq[a.pair_id].reference_time, acq[a.pair_id].secondary_time),
                                   (acq[b.pair_id].reference_time, acq[b.pair_id].secondary_time))
            if o >= mcfg["min_overlap_days"]:
                cand.append((o, a, b))
    used_a, used_b, matches = set(), set(), []
    for o, a, b in sorted(cand, key=lambda t: -t[0]):
        if a.pair_id in used_a or b.pair_id in used_b:
            continue
        used_a.add(a.pair_id)
        used_b.add(b.pair_id)
        fa, fb = keep[a.pair_id]["flagged"], keep[b.pair_id]["flagged"]
        dom = Z["study"] & keep[a.pair_id]["valid"] & keep[b.pair_id]["valid"]
        t = stats.contingency(fa, fb, dom)
        ci = stats.bootstrap_association(fa, fb, dom, ids, seed=_seed(a.pair_id + b.pair_id))
        unc = (Uncertainty(kind="block_bootstrap_interval", low=ci["low"], high=ci["high"], level=0.95, block_m=mcfg["block_m"],
                           n_blocks=ci["n_blocks"], method="percentile interval, square blocks of the perimeter")
               if ci["status"] == "ok" else Uncertainty(kind="not_estimated", method=f"bootstrap {ci['status']}"))
        matches.append(WindowMatch(pair_a=a.pair_id, pair_b=b.pair_id, overlap_days=round(o, 2),
                                   table={k: t[k] for k in ("n11", "n10", "n01", "n00")},
                                   association_ratio=maybe(t["ratio"], "ratio", "undefined", uncertainty=unc if t["ratio"] is not None else None),
                                   jaccard=maybe(t["jaccard"], "fraction", "empty union"),
                                   p_b_given_a=maybe(t["p_b_given_a"], "fraction", "no flag in the first pair")))
    matches.sort(key=lambda m: acq[m.pair_a].reference_time)
    unmatched = [x.pair_id for x in ok if x.pair_id not in used_a | used_b]
    jac = [m.jaccard.value for m in matches if m.jaccard.value is not None]
    return CrossGeometry(status="ok" if matches else "unavailable", rule=rule, matches=matches, unmatched=unmatched,
                         median_jaccard=maybe(float(np.median(jac)) if jac else None, "fraction", "no matched window"),
                         reason=None if matches else "no pair of windows overlaps enough")


def _autocorr(pairs, keep, ring, px_m) -> dict:
    """Median autocorrelation of the flag indicator in the control ring at several lags, over analysed 12-day pairs."""
    lags_m = [20, 100, 250, 500, 1000, 2000]
    lags = [max(1, int(round(m / px_m))) for m in lags_m]
    vals = {m: [] for m in lags_m}
    for x in pairs:
        if x.status != "ok":
            continue
        k = keep[x.pair_id]
        ac = stats.autocorrelation(k["flagged"], ring & k["valid"], lags)
        for m, lag in zip(lags_m, lags):
            if ac[lag] is not None:
                vals[m].append(ac[lag])
    return {f"{m} m": (float(np.median(v)) if v else None) for m, v in vals.items()}


def _dossiers(pairs, keep, recurrences, Z, landcover, grid, epsg, pix_km2, mcfg, out_dir, ex) -> list[Dossier]:
    """Zones flagged in at least half of the observed 12-day pairs in BOTH orbits (>= min observed pairs each)."""
    recs = [r for r in recurrences if f"rec_{r.geometry_id}" in keep]
    if len(recs) < 2:
        return []
    from ..access.worldcover import CLASSES
    m = np.ones(Z["study"].shape, bool)
    for r in recs:
        k = keep[f"rec_{r.geometry_id}"]
        m &= (k["frac"] >= 0.5) & (k["seen"] >= mcfg["min_observed_pairs"])
    m &= Z["study"] | Z["panels_outside"]
    lab, n = ndimage.label(m, structure=np.ones((3, 3), bool))
    min_px = max(1, int(round(mcfg["min_cluster_km2"] / pix_km2)))
    sizes = ndimage.sum_labels(np.ones_like(lab), lab, index=np.arange(1, n + 1)) if n else []
    order = sorted([i + 1 for i in range(n) if sizes[i] >= min_px], key=lambda i: -sizes[i - 1])[: mcfg["max_dossiers"]]
    out, labmap = [], np.zeros(lab.shape, "int32")
    ok = [x for x in pairs if x.status == "ok"]
    for j, li in enumerate(order, start=1):
        sel = lab == li
        labmap[sel] = j
        rows, cols = np.nonzero(sel)
        per_geom, dates, evidence = {}, [], []
        for r in recs:
            flagged_in = []
            for pid in r.pair_ids:
                k = keep[pid]
                if k["valid"][sel].mean() >= 0.5 and k["flagged"][sel & k["valid"]].mean() >= 0.5:
                    flagged_in.append(pid)
            per_geom[r.geometry_id] = (len(flagged_in), len(r.pair_ids))
            evidence += flagged_in
            dates += [[next(x.reference_date for x in ok if x.pair_id == pid), next(x.secondary_date for x in ok if x.pair_id == pid)] for pid in flagged_in]
        opt_hits, hyps = [], {}
        for x in ok:
            o = keep.get(x.pair_id, {}).get("optical")
            if o is None:
                continue
            j_ = sel & o["joint"]
            if j_.sum() < 0.5 * sel.sum():
                continue
            opt_hits.append(float(o["oflag"][j_].mean()))
            h = optical.dominant_hypothesis(o["labels"], j_ & keep[x.pair_id]["flagged"] & o["oflag"])
            if h:
                hyps[h] = hyps.get(h, 0) + 1
        lc = None
        if landcover is not None:
            v, c = np.unique(landcover[sel], return_counts=True)
            lc = CLASSES.get(int(v[c.argmax()]), str(int(v[c.argmax()])))
        alts = ["alt.surface_works", "alt.coherence_contributions"]
        if hyps.get("hypothesis.moisture"):
            alts.append("alt.moisture")
        if hyps.get("hypothesis.vegetation"):
            alts.append("alt.vegetation")
        alts.append("alt.acquisition_effect")
        zone = "study" if Z["study"][sel].mean() >= 0.5 else "panels_outside"
        obs = {f"flagged_pairs_{g}": v[0] for g, v in per_geom.items()}
        obs.update({f"observed_pairs_{g}": v[1] for g, v in per_geom.items()})
        obs.update(strict_optical_comparisons=len(opt_hits),
                   median_optical_change_share=float(np.median(opt_hits)) if opt_hits else None,
                   spectral_hypotheses=", ".join(f"{k}:{v}" for k, v in sorted(hyps.items())) or None)
        out.append(Dossier(id=f"Z{j}", centroid=_lonlat(grid, epsg, rows.mean(), cols.mean()), area_km2=float(sel.sum() * pix_km2),
                           zone=zone, landcover=lc, observation=obs, evidence=sorted(set(evidence)), alternative_keys=alts,
                           to_collect_keys=["collect.vhr_images", "collect.operations_log", "collect.field_visit", "collect.rainfall"],
                           dates=dates))
    if out:
        gj = export.clusters_geojson(labmap, [{"id": d_.id and int(d_.id[1:]), **{"dossier": d_.id, "area_km2": d_.area_km2}} for d_ in out],
                                     grid["transform"], epsg)
        sha = export.write_json(out_dir / "exports" / "verification_zones.geojson", gj)
        ex.append(Export(id="dossiers_geojson", format="geojson", path="exports/verification_zones.geojson",
                         description_key="export.dossiers_geojson", sha256=sha))
        lines = ["# Fiches de vérification — zones signalées dans au moins la moitié des paires des deux orbites", "",
                 "Ces fiches décrivent des observations radar et optiques. Elles ne diagnostiquent ni une cause ni un danger.", ""]
        for d_ in out:
            lines += [f"## {d_.id} — {d_.area_km2:.3f} km², {d_.centroid[1]:.5f} N, {abs(d_.centroid[0]):.5f} O",
                      f"- Zone : {d_.zone} ; occupation du sol WorldCover 2021 : {d_.landcover}",
                      *[f"- {k} : {v}" for k, v in d_.observation.items()],
                      f"- Fenêtres signalées : {', '.join(a + '→' + b for a, b in d_.dates)}",
                      f"- Hypothèses alternatives : {', '.join(d_.alternative_keys)}",
                      f"- À recueillir : {', '.join(d_.to_collect_keys)}", ""]
        p = out_dir / "exports" / "verification_sheets.md"
        p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        ex.append(Export(id="dossiers_md", format="markdown", path="exports/verification_sheets.md",
                         description_key="export.dossiers_md", sha256=export.sha256(p)))
    return out


def _tables(pairs, cross, out_dir, ex, main_profile):
    rows, prow, orow = [], [], []
    for x in pairs:
        m = next((pr for pr in x.profiles if pr.id == main_profile), None)
        u = x.statistical.uncertainty
        rows.append({"pair_id": x.pair_id, "geometry": x.geometry_id, "reference_date": x.reference_date,
                     "secondary_date": x.secondary_date, "span_days": x.span_days, "status": x.status, "reasons": "; ".join(x.reasons),
                     "threshold": m.threshold.value if m else None, "evaluation_rate": m.evaluation_rate.value if m else None,
                     "study_flagged_km2": m.study_flagged_area_km2.value if m else None,
                     "study_flagged_fraction": m.study_flagged_fraction.value if m else None,
                     "fraction_ci_low": u.low if u and u.kind == "block_bootstrap_interval" else None,
                     "fraction_ci_high": u.high if u and u.kind == "block_bootstrap_interval" else None,
                     "ratio": m.ratio_to_evaluation_rate.value if m else None})
        for pr in x.profiles:
            prow.append({"pair_id": x.pair_id, "span_days": x.span_days, "profile": pr.id, "threshold": pr.threshold.value,
                         "calibration_rate": pr.calibration_rate.value, "evaluation_rate": pr.evaluation_rate.value,
                         "study_flagged_km2": pr.study_flagged_area_km2.value, "study_flagged_fraction": pr.study_flagged_fraction.value,
                         "ratio": pr.ratio_to_evaluation_rate.value, "exceeds_control": pr.exceeds_control})
        for c in x.optical:
            u = c.association_ratio.uncertainty
            orow.append({"pair_id": x.pair_id, "mode": c.mode, "status": c.status, "reason": c.reason, "before": c.before_datetime,
                         "after": c.after_datetime, "gap_before_days": c.gap_days_before, "gap_after_days": c.gap_days_after,
                         **(c.table or {}), "p_opt_given_radar": c.p_optical_given_radar.value,
                         "p_opt_given_not_radar": c.p_optical_given_not_radar.value, "ratio": c.association_ratio.value,
                         "ratio_ci_low": u.low if u and u.kind == "block_bootstrap_interval" else None,
                         "ratio_ci_high": u.high if u and u.kind == "block_bootstrap_interval" else None,
                         "jaccard": c.jaccard.value, "joint_fraction": c.joint_observable_fraction.value})
    for name, data, key in (("pairs.csv", rows, "pairs_csv"), ("profiles.csv", prow, "profiles_csv"), ("optical.csv", orow, "optical_csv")):
        sha = export.write_csv(out_dir / "exports" / name, data)
        ex.append(Export(id=key, format="csv", path=f"exports/{name}", description_key=f"export.{key}", sha256=sha))
    crow = [{"pair_a": m.pair_a, "pair_b": m.pair_b, "overlap_days": m.overlap_days, **m.table, "ratio": m.association_ratio.value,
             "jaccard": m.jaccard.value, "p_b_given_a": m.p_b_given_a.value} for m in cross.matches]
    sha = export.write_csv(out_dir / "exports" / "cross_geometry.csv", crow)
    ex.append(Export(id="cross_csv", format="csv", path="exports/cross_geometry.csv", description_key="export.cross_csv", sha256=sha))


def referenced_files(case: MiningCase) -> list[str]:
    return sorted({lay.url for lay in case.layers} | {e.path for e in case.exports} | {case.zones_url})


def verify_run(folder: Path, case: MiningCase) -> list[str]:
    """Problems that forbid publication: unreadable contract, missing or altered referenced files."""
    problems = []
    for rel in referenced_files(case):
        if not (folder / rel).is_file():
            problems.append(f"missing file {rel}")
    if case.manifest:
        for o in case.manifest.outputs:
            f = folder / o.path
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != o.sha256:
                problems.append(f"output {o.path} differs from the manifest")
    try:
        MiningCase.model_validate_json((folder / "case.json").read_text(encoding="utf-8"))
    except Exception as exc:          # noqa: BLE001
        problems.append(f"case.json does not satisfy the contract: {exc}")
    return problems


def _finish(case_kw, staging, case_dir, cfg_path, log, t_start, run_id, repo_root, publish) -> MiningCase:
    outputs = [FileRecord(path=str(f.relative_to(staging)).replace("\\", "/"), sha256=export.sha256(f), role="output")
               for f in sorted(staging.rglob("*")) if f.is_file() and f.name != "case.json"]
    commit, dirty = _git(repo_root)
    case_kw["manifest"] = Manifest(run_id=run_id, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                   code_commit=commit, code_dirty=dirty, python=platform.python_version(), packages=_packages(),
                                   config_sha256=export.sha256(cfg_path), inputs=log.list(), outputs=outputs,
                                   duration_s=round(time.time() - t_start, 1))
    case = MiningCase(**case_kw)
    export.write_json(staging / "case.json", json.loads(case.model_dump_json()))
    problems = verify_run(staging, case)
    if problems:
        (staging / "VERIFICATION_FAILED.txt").write_text("\n".join(problems), encoding="utf-8")
        raise PipelineError(f"run {run_id} failed verification: {problems[:5]}")
    (staging / "VERIFIED").write_text(run_id, encoding="utf-8")
    if publish:
        target, tmp, old = case_dir / "output", case_dir / "output.publishing", case_dir / "output.previous"
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(old, ignore_errors=True)
        shutil.copytree(staging, tmp)
        if target.exists():
            os.replace(target, old)
        os.replace(tmp, target)
        shutil.rmtree(old, ignore_errors=True)
    return case


def _unavailable(case_dir, staging, cfg, site, zones, zfc, references, log, t_start, run_id, repo_root, publish) -> MiningCase:
    from .contract import ValidationItem
    na = absent("fraction", "no radar observation", "unavailable")
    export.write_json(staging / "zones.geojson", zfc)
    case_kw = dict(case_id=cfg["case_id"], run_id=run_id, data_nature=cfg.get("data_nature", "real"),
                   presentation_level_key="presentation.exploratory", question_key="question.low_coherence",
                   user_key="user.monitoring_analyst", site=site, zones=zones, perimeter_versions=[], zones_url="zones.geojson",
                   acquisitions=[], optical_scenes=[], optical_search={},
                   method=Method(id="low-coherence-relative-to-control", version=METHOD_VERSION,
                                 observable_key="observable.low_coherence_relative_to_control", parameters={}, controls=[],
                                 main_profile="ring@0.01", reused_modules=REUSED, steps=["import"], autocorrelation={},
                                 block_size_justification=""),
                   pairs=[], geometries=[], cross_geometry=CrossGeometry(status="unavailable", rule="", matches=[], unmatched=[],
                                                                       median_jaccard=na, reason="no radar pair"),
                   los=[], layers=[], exports=[], references=references,
                   validation=[ValidationItem(observable="low_coherence_location", level="not_computed", criteria=[],
                                              evidence_keys=[], missing_keys=["missing.radar_products"])],
                   findings=[], dossiers=[], next_checks=[], limits=["limit.no_data_is_not_no_change"],
                   processing=Processing(status="unavailable", rule="no radar product", blockers=["blocker.no_radar_products"],
                                         steps=[Step(name="import", required=True, status="unavailable", message="no GUNW product")]))
    return _finish(case_kw, staging, case_dir, case_dir / "case_config.json", log, t_start, run_id, repo_root, publish)
