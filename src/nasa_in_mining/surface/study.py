"""Surface-change study pipeline (NISAR GCOV gamma-0 change), separate from the v2 coherence pipeline.

GCOV crops -> per-date quality bits (reasons per pixel) -> 20 m linear-power cells -> delta in dB per consecutive
pair -> zone statistics -> temporal reference from disjoint pairs (or `insufficient_baseline`) -> flags relative
to a held-out control -> Sentinel-2 comparison counted per distinct optical pair -> zone conclusions ->
reference sampling frame and blind annotation packet -> layers, exports, report, manifest, verification.

Every run is written to cases/<case>/runs/<run_id>/ and published to output/ only after verification.
See docs/SURFACE_STUDY.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time

import numpy as np
import rasterio
from affine import Affine
from scipy import ndimage

from ..access import gcov_subset
from ..mining import coherence_change as cc
from ..mining import evidence as ev
from ..mining import export, optical, stats
from ..mining.contract import (Export, FileRecord, Layer, Legend, Manifest, OpticalScene, Processing, Reference, Site,
                               Step, Uncertainty, Zone, EvidenceSummary)
from ..mining.pipeline import InputLog, PipelineError, _git, _packages, _rasterize, _seed, _lonlat, _same_grid
from . import backscatter as bs
from . import boundary as boundary_mod
from . import references as refs
from . import temporal
from .contract import (BaselineState, BatchInfo, BoundaryInfo, ChangeWindow, Finding, FlagSummary, GcovAcquisition,
                       PolChange, ProtocolInfo, QualityRow, ReferenceState, SurfaceStudy, ZoneChange, ZoneConclusion,
                       absent, maybe, measured)

STUDY_VERSION = "3.0.0"
POLS = ("HH", "HV")
GEOM_LETTER = {"ascending": "A", "descending": "D"}
DIRECTION = {"Ascending": "ascending", "Descending": "descending"}
FLAG_COLORS = {1: (49, 130, 189, 235), 2: (230, 120, 20, 235), 255: (150, 150, 150, 110)}
QUALITY_ORDER = ["outside_acquisition", "not_fully_focused", "instrument_anomaly", "invalid_value", "near_noise_floor",
                 "insufficient_subpixel_coverage", "date_not_available"]
QUALITY_COLORS = {1: (90, 90, 90, 200), 2: (160, 60, 160, 220), 3: (220, 40, 40, 230), 4: (240, 190, 40, 230),
                  5: (60, 160, 220, 200), 6: (120, 200, 120, 200), 7: (0, 0, 0, 230)}
GAP_DOCUMENTED = ("2026-07-27", "2026-08-10")      # ASF known issues: no data collected by the platform
ZONE_LABELS = {"study": "zone.study", "control_1_2km": "zone.ring_inner", "control_2_4km": "zone.ring_outer",
               "panels_outside": "zone.panels", "Z1": "zone.z1"}


def _date(stamp: str) -> str:
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")[:26]).replace(tzinfo=timezone.utc)


def _m(v, unit, reason, status="not_measured", unc=None):
    return maybe(None if v is None else float(v), unit, reason, status, unc)


# ----------------------------------------------------------------------------------------------- acquisitions
class Acq:
    """One GCOV acquisition on the 20 m analysis grid: cell power and reason bits for each polarisation."""

    def __init__(self, folder: Path, prov: dict):
        self.folder, self.prov = folder, prov
        ident = prov["identification"]
        self.track, self.frame = int(ident["trackNumber"]), int(ident["frameNumber"])
        self.direction = DIRECTION[ident["orbitPassDirection"]]
        self.time = ident["zeroDopplerStartTime"]
        self.date = self.time[:10]
        self.crid = ident["compositeReleaseId"]
        self.geometry_id = f"{self.track:03d}{GEOM_LETTER[self.direction]}_F{self.frame:03d}"
        self.acq_id = f"{self.geometry_id}_{self.date.replace('-', '')}"
        self.collection = prov["source_url"].split("/")[-3]
        self.power: dict[str, np.ndarray] = {}
        self.bits: dict[str, np.ndarray] = {}
        self.status, self.reasons = "usable", []
        self.looks = self.incidence = None
        self.noise_db: dict[str, float | None] = {}
        self.obs_study: dict[str, float] = {}


def _sample_coarse(path: Path, grid_t: Affine, shape, log: InputLog, declared: str):
    with rasterio.open(log(path, role="gcov_calibration", declared=declared)) as src:
        a, tr = src.read(1).astype("float32"), src.transform
    rows, cols = np.mgrid[0:shape[0], 0:shape[1]]
    x = grid_t.c + (cols + 0.5) * grid_t.a
    y = grid_t.f + (rows + 0.5) * grid_t.e
    ci = np.clip(np.floor((x - tr.c) / tr.a).astype(int), 0, a.shape[1] - 1)
    ri = np.clip(np.floor((y - tr.f) / tr.e).astype(int), 0, a.shape[0] - 1)
    return a[ri, ci]


def load_acquisition(folder: Path, prov: dict, log: InputLog, grid: dict | None, cfg_q: dict) -> tuple[Acq, dict]:
    a = Acq(folder, prov)
    files = prov["files"]

    def read(name):
        with rasterio.open(log(folder / name, role="gcov", declared=files[name])) as src:
            return src.read(1), src.transform, src.crs
    mask, tr10, crs = read("mask.tif")
    exc, _, _ = read("inputDataExceptionMask.tif")
    looks, _, _ = read("numberOfLooks.tif")
    sx = abs(tr10.a)
    g = {"transform": Affine(sx * 2, 0, tr10.c, 0, -sx * 2, tr10.f), "crs": crs, "shape": (mask.shape[0] // 2, mask.shape[1] // 2)}
    if grid is not None and not _same_grid(grid, g):
        a.status, a.reasons = "rejected", ["incompatible_grid"]
        return a, g
    cells = (mask.shape[0] // 2, mask.shape[1] // 2)
    inc = _sample_coarse(folder / "incidenceAngle.tif", g["transform"], cells, log, files["incidenceAngle.tif"]) \
        if "incidenceAngle.tif" in files else None
    a.incidence = inc
    a.looks = block = bs.block_reduce(looks.astype("float64"), 2) / 4.0
    desc = ((prov.get("layers") or {}).get("inputDataExceptionMask.tif") or {}).get("description") or ""
    has_validity_bits = "validity mask bits" in desc          # documented per product, never assumed
    for pol in prov["polarizations"]:
        power, _, _ = read(f"{pol}{pol}.tif")
        vbit = {"HH": 256, "HV": 512}.get(pol) if has_validity_bits else None
        sample_bits = bs.sample_reasons(power, mask, exc, vbit)
        cell, cbits, _ = bs.aggregate_power(power, sample_bits, 2, cfg_q["min_valid_subpixel_fraction"])
        nname = f"noiseEquivalentBackscatter_{pol}.tif"
        nebs = _sample_coarse(folder / nname, g["transform"], cells, log, files[nname]) if nname in files else None
        a.power[pol] = cell
        a.bits[pol] = bs.mark_noise(cell, cbits, nebs, cfg_q["noise_margin_linear"])
        a.noise_db[pol] = nebs
    return a, g


# ----------------------------------------------------------------------------------------------- helpers
def _zones(case_dir: Path, cfg: dict, grid: dict, log: InputLog, extra_geoms: dict | None = None):
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform as stransform
    epsg = cfg["epsg"]
    zpath = log(case_dir / cfg["zones_file"], role="zones")
    zfc = json.loads(zpath.read_text(encoding="utf-8"))
    zg = {f["id"]: shape(f["geometry"]) for f in zfc["features"]}
    zp = {f["id"]: f["properties"] for f in zfc["features"]}
    fwd = Transformer.from_crs(4326, epsg, always_xy=True).transform
    inv = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    study_m = stransform(fwd, zg["study"])
    Z = {"study": _rasterize(zg["study"], grid, epsg), "control": _rasterize(zg["control"], grid, epsg),
         "panels_outside": _rasterize(zg.get("panels_outside"), grid, epsg)}
    Z["control_1_2km"] = _rasterize(stransform(inv, study_m.buffer(2000)).intersection(zg["control"]), grid, epsg)
    Z["control_2_4km"] = Z["control"] & ~Z["control_1_2km"]
    for k, g in (extra_geoms or {}).items():
        Z[k] = _rasterize(g, grid, epsg)
    zones = [Zone(id=k, role=v["role"], area_km2=v.get("area_km2"),
                  source=f"OpenStreetMap ({v.get('osm_type', 'derived')} {v.get('osm_id', '')})".replace(" )", ")"),
                  source_date=v.get("osm_timestamp") or v.get("osm_base_timestamp"), license=v["license"],
                  attribution=v["attribution"], nature=v.get("nature")) for k, v in zp.items()]
    return Z, zones, zfc


def _bit_fractions(bits: np.ndarray, zone: np.ndarray) -> dict[str, float]:
    n = max(int(zone.sum()), 1)
    return {name: float(((bits[zone] & v) != 0).sum() / n) for name, v in bs.REASONS.items()}


def _quality_class(bits: np.ndarray) -> np.ndarray:
    out = np.zeros(bits.shape, dtype="float32")
    for i, name in reversed(list(enumerate(QUALITY_ORDER, 1))):
        out[(bits & bs.REASONS[name]) != 0] = i
    return out


def _flag_codes(res: dict) -> np.ndarray:
    out = np.zeros(res["flagged"].shape, dtype="uint8")
    out[res["direction"] == -1] = 1
    out[res["direction"] == 1] = 2
    out[~res["valid"]] = 255
    return out


def _ci_unc(b: dict, block_m: float, key="ratio") -> Uncertainty:
    if b.get("status") == "ok" and f"{key}_low" in b and b.get("ratio_status") == "ok":
        return Uncertainty(kind="block_bootstrap_interval", low=b[f"{key}_low"], high=b[f"{key}_high"], level=0.95,
                           block_m=block_m, n_blocks=b["n_blocks"],
                           method="percentile interval from 2000 resamplings of square blocks; conditional on the protocol")
    return Uncertainty(kind="not_estimated", method=f"block bootstrap not possible ({b.get('status')}/{b.get('ratio_status')})")


# ----------------------------------------------------------------------------------------------- run
def run(case_dir: Path, data_dir: Path, repo_root: Path | None = None, publish: bool = True,
        run_id: str | None = None) -> SurfaceStudy:
    t_start = time.time()
    case_dir, data_dir = Path(case_dir), Path(data_dir)
    repo_root = Path(repo_root or case_dir.parents[1])
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging = case_dir / "runs" / run_id
    if staging.exists():
        raise PipelineError(f"run directory {staging} already exists: a run never reuses old files")
    staging.mkdir(parents=True)
    log = InputLog(repo_root)
    cfg_path = log(case_dir / "study_config.json", role="config")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    proto_path = log(case_dir / cfg["protocol_file"], role="protocol")
    proto = json.loads(proto_path.read_text(encoding="utf-8"))
    pf, pq, pb, pc = proto["flagging"], proto["quality"], proto["baseline"], proto["coverage"]
    epsg, ocfg = cfg["epsg"], cfg["optical"]
    steps: list[Step] = []
    layers: list[Layer] = []
    exports: list[Export] = []
    out_dir = staging

    # ------------------------------------------------------------------ index GCOV crops (integrity checked)
    gdir = data_dir / cfg["gcov_dir"]
    provs = []
    for prov_file in sorted(gdir.glob("*/provenance.json")) if gdir.exists() else []:
        folder = prov_file.parent
        ok, why = gcov_subset.verify(folder)
        if not ok:
            raise PipelineError(f"{folder.name}: {why}")
        provs.append((folder, json.loads(log(prov_file, role="gcov_provenance").read_text(encoding="utf-8"))))
    if not provs:
        raise PipelineError("no GCOV crop found: run scripts/fetch_benguerir_gcov.py first")
    steps.append(Step(name="import", required=True, status="done",
                      message=f"{len(provs)} GCOV crops, hashed at read time and compared with their provenance"))

    grid, acqs = None, {}
    for folder, prov in provs:
        a, g = load_acquisition(folder, prov, log, grid, pq)
        grid = grid or g
        acqs[a.acq_id] = a
    px_m = abs(grid["transform"].a)
    pix_km2 = px_m * px_m / 1e6
    shape = grid["shape"]

    # ------------------------------------------------------------------ zones and extra geometries (Z1)
    from shapely.geometry import shape as sshape
    extra = {}
    vz = cfg.get("v2_verification_zones")
    if vz and (repo_root / vz).exists():
        fc = json.loads(log(repo_root / vz, role="v2_verification_zones").read_text(encoding="utf-8"))
        for f in fc["features"]:
            if f["properties"].get("dossier") == "Z1":
                extra["Z1"] = sshape(f["geometry"])
    Z, zones, zfc = _zones(case_dir, cfg, grid, log, extra)
    calib = stats.checkerboard(shape, int(round(pf["calibration_block_m"] / px_m)))
    ids = {b: stats.block_ids(shape, int(round(b / px_m))) for b in pf["bootstrap_block_sizes_m"]}
    block_m = pf["bootstrap_block_m"]
    ctrl_cal, ctrl_eval = Z["control"] & calib, Z["control"] & ~calib
    steps.append(Step(name="grid_and_zones", required=True, status="done",
                      message=f"{shape[1]}x{shape[0]} cells at {px_m:g} m; native 10 m samples averaged in linear power"))

    # ------------------------------------------------------------------ per-acquisition quality
    for a in acqs.values():
        for pol in POLS:
            if pol not in a.bits:
                continue
            a.obs_study[pol] = float((a.bits[pol][Z["study"]] == 0).mean())
        if a.status == "usable" and a.obs_study.get("HH", 0.0) < pc["min_observed_fraction_study"]:
            a.status = "rejected"
            frac = _bit_fractions(a.bits["HH"], Z["study"])
            a.reasons = [k for k, v in sorted(frac.items(), key=lambda kv: -kv[1]) if v > 0.05] or ["insufficient_coverage"]
    # ------------------------------------------------------------------ batches and windows
    batches, windows_raw = [], []
    by_batch: dict[str, list[Acq]] = {}
    for b in cfg["batches"]:
        members = sorted((a for a in acqs.values() if (a.collection, a.crid, a.track, a.frame, a.direction) ==
                          (b["collection"], b["crid"], b["track"], b["frame"], b["direction"])), key=lambda x: x.time)
        by_batch[b["id"]] = members
    for b in cfg["batches"]:
        mem = by_batch[b["id"]]
        gaps = []
        for x, y in zip(mem, mem[1:]):
            span = round((_dt(y.time) - _dt(x.time)).total_seconds() / 86400)   # acquisitions are 12 d minus a second apart
            if span > 14:
                overlap = x.date <= GAP_DOCUMENTED[1] and y.date >= GAP_DOCUMENTED[0]
                gaps.append({"between": [x.date, y.date], "span_days": span, "documented_instrument_gap": overlap,
                             "note": "no acquisition in the catalogue between these dates; not interpolated"})
            windows_raw.append((b, x, y, span))
        batches.append((b, mem, gaps))

    # ------------------------------------------------------------------ deltas, descriptive statistics, quality
    W: dict[str, dict] = {}
    quality_rows: list[QualityRow] = []
    for b, x, y, span in windows_raw:
        wid = f"GCOV_{x.geometry_id}_{x.date.replace('-', '')}_{y.date.replace('-', '')}_{b['crid']}"
        rec = {"id": wid, "batch": b, "x": x, "y": y, "span": span, "pols": {}, "reasons": []}
        rec["status"] = "computed"
        for a in (x, y):
            if a.status != "usable":
                rec["status"] = "rejected"
                rec["reasons"] += [f"{a.acq_id}:{r}" for r in a.reasons]
        for pol in POLS:
            if pol not in x.power or pol not in y.power:
                continue
            if rec["status"] == "rejected":
                bits = x.bits[pol] | y.bits[pol]
                for a in (x, y):
                    if a.status != "usable":
                        bits = bits | np.where(a.bits[pol] == 0, bs.REASONS["date_not_available"], 0).astype("uint16")
                rec["pols"][pol] = {"bits": bits, "delta": None, "valid": np.zeros(shape, bool)}
                continue
            bits = x.bits[pol] | y.bits[pol]
            delta = bs.delta_db(x.power[pol], y.power[pol], bits == 0)
            rec["pols"][pol] = {"bits": bits, "delta": delta, "valid": np.isfinite(delta)}
        W[wid] = rec

    # ------------------------------------------------------------------ temporal reference and flags
    for wid, rec in W.items():
        b = rec["batch"]
        for pol, p in rec["pols"].items():
            p["flags"], p["baseline"] = None, BaselineState(status="not_applicable", n_pairs=0, pair_ids=[],
                                                             reason="window not computed")
            if rec["status"] != "computed":
                continue
            cands = {w2: r2 for w2, r2 in W.items() if r2["batch"]["id"] == b["id"] and r2["span"] == rec["span"]
                     and r2["status"] == "computed" and pol in r2["pols"] and r2["pols"][pol]["delta"] is not None}
            key = lambda r: (r["x"].acq_id, r["y"].acq_id)  # noqa: E731
            disjoint = temporal.disjoint_baseline(key(rec), [key(r) for r in cands.values()])
            base_ids = [w2 for w2, r2 in cands.items() if key(r2) in disjoint]
            obs_s = float(p["valid"][Z["study"]].mean())
            p["obs_study"] = obs_s
            if obs_s < pc["min_observed_fraction_study"] or int((p["valid"] & Z["control"]).sum()) < pc["min_control_cells"]:
                p["status"] = "insufficient_coverage"
                p["baseline"] = BaselineState(status="not_applicable", n_pairs=0, pair_ids=[], reason="insufficient observed coverage")
                continue
            p["status"] = "computed"
            if len(base_ids) < pb["min_disjoint_pairs"]:
                p["baseline"] = BaselineState(
                    status="insufficient_baseline", n_pairs=len(base_ids), pair_ids=base_ids,
                    reason=f"{len(base_ids)} homogeneous {rec['span']}-day pair(s) sharing no acquisition "
                           f"(required {pb['min_disjoint_pairs']})")
                continue
            base = temporal.baseline_median([W[w2]["pols"][pol]["delta"] for w2 in base_ids], pb["min_pairs_per_cell"])
            res = temporal.flag_residual(p["delta"], base, Z["control"], calib, pf["k_sigma"], pc["min_control_cells"])
            if res["status"] != "ok":
                p["baseline"] = BaselineState(status="insufficient_baseline", n_pairs=len(base_ids), pair_ids=base_ids,
                                              reason=f"control too small for the residual spread ({res['calibration_cells']} / "
                                                     f"{res['evaluation_cells']} cells)")
                continue
            p["res"] = res
            p["baseline"] = BaselineState(
                status="ok", n_pairs=len(base_ids), pair_ids=base_ids, centre_db=measured(res["centre_db"], "dB"),
                sigma_db=measured(res["sigma_db"], "dB"), k_sigma=pf["k_sigma"],
                calibration_rate=measured(res["calibration_rate"], "fraction"),
                evaluation_rate=measured(res["evaluation_rate"], "fraction"))
            rr = temporal.rate_ratio(res["flagged"], res["valid"], Z["study"], ctrl_eval, ids[block_m], _seed(wid + pol))
            sens = {}
            for bm in pf["bootstrap_block_sizes_m"]:
                bb = temporal.rate_ratio(res["flagged"], res["valid"], Z["study"], ctrl_eval, ids[bm], _seed(wid + pol))["bootstrap"]
                sens[str(int(bm))] = [bb["ratio_low"], bb["ratio_high"]] if bb.get("ratio_status") == "ok" else None
            p["rate"] = rr
            nd = int(((res["direction"] == -1) & Z["study"]).sum())
            nb = int(((res["direction"] == 1) & Z["study"]).sum())
            p["flags"] = FlagSummary(
                study_fraction=measured(rr["study_fraction"], "fraction") if rr["study_fraction"] is not None else absent("fraction", "no observed study cell"),
                control_fraction=measured(rr["control_fraction"], "fraction") if rr["control_fraction"] is not None else absent("fraction", "no observed control cell"),
                ratio=maybe(rr["ratio"], "ratio", "the control flag rate is zero or the interval is unstable",
                            uncertainty=_ci_unc(rr["bootstrap"], block_m) if rr["ratio"] is not None else None),
                study_flagged_area_km2=measured(rr["study_flagged"] * pix_km2, "km2"),
                darker_area_km2=measured(nd * pix_km2, "km2"), brighter_area_km2=measured(nb * pix_km2, "km2"),
                ratio_block_sensitivity=sens)
    steps.append(Step(name="change_and_baseline", required=True, status="done",
                      message=f"{len(W)} consecutive windows; temporal reference from disjoint homogeneous pairs only"))

    # ------------------------------------------------------------------ optical (Sentinel-2) per window
    scenes = optical.index(data_dir / ocfg["dir"], Z, log, ocfg["min_clear_study"], ocfg["min_clear_control"])
    optical_scenes = [OpticalScene(item_id=s["item_id"], datetime=s["datetime"], platform=s.get("platform"),
                                   processing_baseline=s.get("processing_baseline"),
                                   cloud_cover_pct_tile=s.get("cloud_cover_pct_tile"),
                                   clear_fraction_study=round(s["clear_study"], 4),
                                   clear_fraction_control=round(s["clear_control"], 4),
                                   doubtful_fraction_study=round(s["doubtful_study"], 4), usable=s["usable"],
                                   reason=s["reason"]) for s in scenes]
    opt_extra: dict[str, dict] = {}
    opt_comps: dict[str, list] = {}
    for wid, rec in W.items():
        p = rec["pols"].get("HH")
        opt_comps[wid] = []
        if not p or p.get("flags") is None:
            continue
        res = p["res"]
        t0, t1 = _dt(rec["x"].time), _dt(rec["y"].time)
        for mode, gap in (("strict", ocfg["strict_gap_days"]), ("exploratory", ocfg["exploratory_gap_days"])):
            comp, ex_ = optical.compare(mode, gap, scenes, t0, t1, res["flagged"], res["valid"], Z, calib, ids[block_m],
                                        {**ocfg, "block_m": block_m}, log, seed=_seed(wid + mode))
            opt_comps[wid].append(comp)
            if ex_ is not None:
                opt_extra[f"{wid}|{mode}"] = ex_
    steps.append(Step(name="optical", required=False, status="done",
                      message=f"{len(scenes)} Sentinel-2 scenes read, {sum(1 for s in scenes if s['usable'])} usable"))

    # ------------------------------------------------------------------ verification zones (Z1 + recurring cells)
    recur = np.zeros(shape, dtype=bool)
    for geom in sorted({r["x"].geometry_id for r in W.values()}):
        n_obs = np.zeros(shape, int)
        n_flag = np.zeros(shape, int)
        for rec in W.values():
            p = rec["pols"].get("HH")
            if rec["x"].geometry_id == geom and rec["span"] == 12 and p and p.get("flags") is not None:
                n_obs += p["res"]["valid"]
                n_flag += p["res"]["flagged"]
        recur |= (n_obs >= 3) & (n_flag * 2 >= n_obs) & Z["study"]
    labels, nl = ndimage.label(recur, structure=np.ones((3, 3)))
    sizes = ndimage.sum(recur, labels, range(1, nl + 1)) if nl else []
    order = [i + 1 for i in np.argsort(sizes)[::-1] if sizes[i] >= cfg["min_zone_cluster_cells"]][: cfg["zones_new_max"]]
    zone_masks = {zid: Z[zid] for zid in ("study", "control_1_2km", "control_2_4km", "panels_outside") if zid in Z}
    if "Z1" in Z:
        zone_masks["Z1"] = Z["Z1"]
    new_ids = []
    for n, lab in enumerate(order, 1):
        zone_masks[f"N{n}"] = labels == lab
        new_ids.append(f"N{n}")

    def centroid(mask):
        r, c = ndimage.center_of_mass(mask)
        return _lonlat(grid, epsg, r, c)

    dev = {(d, a, b2) for d, a, b2 in cfg["development_windows"]}
    dev_wids = {wid for wid, r in W.items() if (r["x"].direction, r["x"].date, r["y"].date) in dev}
    conclusions = _conclusions(zone_masks, W, opt_extra, Z, ctrl_eval, cfg, pix_km2, centroid, calib, dev_wids)

    # ------------------------------------------------------------------ layers and rasters
    study_cells = Z["study"]
    win_models: list[ChangeWindow] = []
    for wid, rec in W.items():
        x, y, b = rec["x"], rec["y"], rec["batch"]
        pol_models, qlid = [], None
        for pol, p in rec["pols"].items():
            lids = []
            tags = {"window": wid, "pol": pol, "formula": "10*log10(gamma0_after/gamma0_before)", "units": "dB"}
            if p["delta"] is not None and pol == "HH":       # HV change is reported in the tables and its quality layer; no HV delta raster
                enc = np.full(p["delta"].shape, -32768, dtype="int16")          # 0.05 dB steps (<= 0.025 dB rounding), far below the ~1 dB noise
                fin = np.isfinite(p["delta"])
                enc[fin] = np.clip(np.round(p["delta"][fin] / 0.05), -32767, 32767).astype("int16")
                sha = export.write_geotiff(out_dir / "rasters" / f"delta_db_{pol}_{wid}.tif", enc, grid["transform"], epsg, nodata=-32768,
                                           tags={**tags, "encoding": "int16 = round(dB / 0.05); nodata -32768 = not observed; scale 0.05"}, scale=0.05)
                exports.append(Export(id=f"delta_{pol}_{wid}", format="geotiff", path=f"rasters/delta_db_{pol}_{wid}.tif",
                                      description_key="export.delta_geotiff", sha256=sha))
            sha = export.write_geotiff(out_dir / "rasters" / f"quality_{pol}_{wid}.tif", p["bits"].astype("uint16"), grid["transform"], epsg,
                                       nodata=None, tags={"window": wid, "pol": pol, "bits": json.dumps(bs.REASONS)})
            exports.append(Export(id=f"quality_{pol}_{wid}", format="geotiff", path=f"rasters/quality_{pol}_{wid}.tif",
                                  description_key="export.quality_geotiff", sha256=sha))
            if pol == "HH":
                qid = f"quality_{wid}"
                info = export.png_categorical(out_dir / "layers" / f"{qid}.png", _quality_class(p["bits"]), grid["transform"], epsg, QUALITY_COLORS)
                layers.append(Layer(id=qid, kind="derived", title_key="layer.quality", params={"window": wid, "pol": pol},
                                    url=f"layers/{qid}.png", corners=info["corners"],
                                    legend=Legend(kind="categorical", classes=info["classes"],
                                                  class_keys={str(i): f"quality.{n}" for i, n in enumerate(QUALITY_ORDER, 1)}),
                                    date_start=x.date, date_end=y.date, source_ids=[x.acq_id, y.acq_id], resolution_m=px_m,
                                    export=f"rasters/quality_{pol}_{wid}.tif"))
                qlid = qid
                if p["delta"] is not None:
                    did = f"delta_{pol}_{wid}"
                    info = export.png_continuous(out_dir / "layers" / f"{did}.png", p["delta"], grid["transform"], epsg, "RdBu_r", -4.0, 4.0)
                    layers.append(Layer(id=did, kind="observation", title_key="layer.delta_db", params={"window": wid, "pol": pol},
                                        url=f"layers/{did}.png", corners=info["corners"],
                                        legend=Legend(kind="continuous", unit="dB (gamma-0 HH, after / before)", vmin=-4.0, vmax=4.0,
                                                      cmap="RdBu_r", stops=info["stops"], levels=info["levels"]),
                                        date_start=x.date, date_end=y.date, source_ids=[x.acq_id, y.acq_id], resolution_m=px_m,
                                        export=f"rasters/delta_db_{pol}_{wid}.tif", display_note_key="layer.note.delta"))
                    lids.append(did)
                if p.get("res") is not None:
                    fid = f"flags_{pol}_{wid}"
                    codes = _flag_codes(p["res"])
                    sha = export.write_geotiff(out_dir / "rasters" / f"flags_{pol}_{wid}.tif", codes, grid["transform"], epsg, nodata=None,
                                               tags={"classes": "0 not flagged, 1 darker than expected, 2 brighter than expected, 255 not observed"})
                    exports.append(Export(id=fid, format="geotiff", path=f"rasters/flags_{pol}_{wid}.tif",
                                          description_key="export.flags_geotiff", sha256=sha))
                    info = export.png_categorical(out_dir / "layers" / f"{fid}.png", codes, grid["transform"], epsg, FLAG_COLORS)
                    layers.append(Layer(id=fid, kind="derived", title_key="layer.flags_temporal", params={"window": wid, "pol": pol, "k_sigma": pf["k_sigma"]},
                                        url=f"layers/{fid}.png", corners=info["corners"],
                                        legend=Legend(kind="categorical", classes=info["classes"],
                                                      class_keys={"1": "legend.darker", "2": "legend.brighter", "255": "legend.not_observed"}),
                                        date_start=x.date, date_end=y.date, source_ids=[x.acq_id, y.acq_id], resolution_m=px_m,
                                        export=f"rasters/flags_{pol}_{wid}.tif"))
                    lids.append(fid)
            # zone statistics
            zl = []
            ctrl_agg = None
            for zid in ["control", *zone_masks]:                 # all zones of the conclusions, plus the whole control
                zm = Z["control"] if zid == "control" else zone_masks[zid]
                stt = bs.zone_delta_db(x.power[pol], y.power[pol], p["valid"], zm) if p["delta"] is not None else None
                of = float(p["valid"][zm].mean()) if zm.any() else None
                if zid == "control" and stt and stt["aggregate_db"] is not None:
                    ctrl_agg = stt["aggregate_db"]
                if zid == "control":
                    continue
                zl.append(ZoneChange(
                    zone_id=zid, observed_fraction=_m(of, "fraction", "empty zone"),
                    aggregate_db=_m(stt and stt["aggregate_db"], "dB", "no observed cell" if p["delta"] is not None else "window rejected"),
                    median_cell_db=_m(stt and stt["median_cell_db"], "dB", "no observed cell"),
                    p05_db=_m(stt and stt["p05_db"], "dB", "no observed cell"), p95_db=_m(stt and stt["p95_db"], "dB", "no observed cell")))
                p.setdefault("zstats", {})[zid] = stt
            study_agg = (p.get("zstats", {}).get("study") or {}).get("aggregate_db")
            smc = (study_agg - ctrl_agg) if (study_agg is not None and ctrl_agg is not None) else None
            p["study_minus_control"] = smc
            for zid in ("study", "control"):
                quality_rows.append(QualityRow(window_id=wid, pol=pol, zone_id=zid,
                                               observed_fraction=measured(float((p["bits"][Z[zid]] == 0).mean()), "fraction"),
                                               reasons={k: measured(v, "fraction") for k, v in _bit_fractions(p["bits"], Z[zid]).items()}))
            pol_models.append(PolChange(
                pol=pol, primary=(pol == "HH"), status="computed" if (rec["status"] == "computed" and p.get("status") == "computed") else (
                    "insufficient_coverage" if p.get("status") == "insufficient_coverage" else "unavailable"),
                reasons=rec["reasons"] if rec["status"] != "computed" else ([] if p.get("status") == "computed" else ["insufficient observed coverage"]),
                zones=zl, study_minus_control_db=_m(smc, "dB", "window not computed" if p["delta"] is None else "no observed cell"),
                baseline=p["baseline"], flags=p.get("flags"), layer_ids=lids))
        rec["quality_layer_id"] = qlid
        rec["pol_models"] = pol_models
    # Sentinel-2 layers (shared per scene) and optical change layers
    done_rgb = set()
    for key, ex_ in opt_extra.items():
        wid, mode = key.split("|")
        if mode != "strict":
            continue
        comp = next(c for c in opt_comps[wid] if c.mode == "strict")
        lid_o = f"opt_{wid}"
        vmax = max(ex_["threshold"] * 3, ex_["threshold"] + 0.05)
        info = export.png_continuous(out_dir / "layers" / f"{lid_o}.png", np.where(ex_["oflag"], ex_["d"], np.nan),
                                     grid["transform"], epsg, "inferno", ex_["threshold"], vmax)
        layers.append(Layer(id=lid_o, kind="reference", title_key="layer.optical_change", params={"window": wid, "before": comp.before_item, "after": comp.after_item},
                            url=f"layers/{lid_o}.png", corners=info["corners"],
                            legend=Legend(kind="continuous", unit="reflectance change (L2 norm)", vmin=ex_["threshold"], vmax=vmax, cmap="inferno",
                                          stops=info["stops"], levels=info["levels"]),
                            date_start=comp.before_datetime[:10], date_end=comp.after_datetime[:10],
                            source_ids=[comp.before_item, comp.after_item], resolution_m=px_m))
        for tag, sc, xx in (("before", ex_["before"], ex_["x0"]), ("after", ex_["after"], ex_["x1"])):
            lid = f"s2rgb_{sc['item_id']}"
            if lid in done_rgb:
                continue
            done_rgb.add(lid)
            with rasterio.open(sc["stack"]) as src:
                st_t = src.transform
            info = export.png_rgb(out_dir / "layers" / f"{lid}.jpg", xx[[2, 1, 0]], st_t, epsg)
            layers.append(Layer(id=lid, kind="basemap", title_key="layer.s2_rgb", params={"item": sc["item_id"]},
                                url=f"layers/{lid}.jpg", corners=info["corners"], legend=Legend(kind="rgb"),
                                date_start=sc["datetime"][:10], date_end=sc["datetime"][:10], source_ids=[sc["item_id"]], resolution_m=px_m))
    # recurrence layer and verification zones
    exports_zones = _verification_zones(out_dir, zone_masks, conclusions, grid, epsg, exports, centroid, pix_km2)

    # ------------------------------------------------------------------ contract assembly
    v2_ctx = _v2_context(repo_root, cfg, log)
    windows = []
    for wid, rec in W.items():
        x, y, b = rec["x"], rec["y"], rec["batch"]
        gctx = None
        if v2_ctx:
            gctx = v2_ctx["pairs"].get((x.geometry_id, x.date, y.date))
        windows.append(ChangeWindow(
            window_id=wid, batch_id=b["id"], role=b["role"], geometry_id=x.geometry_id, direction=x.direction, before_id=x.acq_id,
            after_id=y.acq_id, before_date=x.date, after_date=y.date, span_days=rec["span"], status=rec["status"],
            reasons=rec["reasons"], pols=rec["pol_models"], quality_layer_id=rec["quality_layer_id"], optical=opt_comps.get(wid, []),
            gunw_context=gctx, development_window=(x.direction, x.date, y.date) in dev))
    optical_ev = [ev.group_comparisons(mode, [(w.window_id, c) for w in windows for c in w.optical if c.mode == mode])
                  for mode in ("strict", "exploratory")]
    ref_state, sampling_exports = _references(case_dir, cfg, W, opt_extra, opt_comps, Z, grid, epsg, out_dir, ctrl_eval, log, repo_root)
    exports += sampling_exports
    acq_models = [_acq_model(a, cfg) for a in sorted(acqs.values(), key=lambda a: (a.geometry_id, a.time))]
    findings = _findings(windows, optical_ev, acq_models, ref_state)
    bi = []
    for b, mem, gaps in batches:
        ws = [w for w in windows if w.batch_id == b["id"]]
        bi.append(BatchInfo(batch_id=b["id"], role=b["role"], collection=b["collection"], crid=b["crid"],
                            geometry_id=f"{b['track']:03d}{GEOM_LETTER[b['direction']]}_F{b['frame']:03d}", direction=b["direction"],
                            n_acquisitions=len(mem), n_usable=sum(1 for a in mem if a.status == "usable"), n_windows=len(ws),
                            n_windows_computed=sum(1 for w in ws if w.status == "computed"), dates=[a.date for a in mem], gaps=gaps,
                            note_keys=["batch.homogeneous", "batch.provisional" if b["collection"].endswith("PROVISIONAL_V1") else "batch.validated_collection"]))
    # boundary dossier
    bdir = out_dir / "boundary"
    review = boundary_mod.build(case_dir / "zones.geojson", bdir, data_dir / "worldcover" / "worldcover.tif",
                                data_dir / "S2" / "S2B_29SPR_20260828_0_L2A" / "stack.tif",
                                case_dir / cfg["boundary_dir"] / "boundary_review_input.json", epsg)
    for f in ("boundary.geojson", "boundary_review.json"):
        exports.append(Export(id=f"boundary_{f.split('.')[0]}", format="geojson" if f.endswith("geojson") else "json",
                              path=f"boundary/{f}", description_key="export.boundary", sha256=export.sha256(bdir / f)))
    boundary = BoundaryInfo(
        state=review["state"], review_status=review["review"]["status"], source=review["documentary_source"]["name"],
        source_date=review["documentary_source"]["date"], license=review["documentary_source"]["license"],
        area_km2=float(review["comparison_with_osm_2020"]["area_km2"]),
        position_uncertainty=absent("m", review["position_uncertainty_note"], "not_measured"), classes=review["classes"],
        automated_checks=review["automated_checks"], needed_for_next_state=review["needed_for_next_state"],
        legal_claim=review["legal_claim"], geojson="boundary/boundary.geojson", review_file="boundary/boundary_review.json")
    export.write_json(out_dir / "zones.geojson", zfc)
    # CSV exports
    rows = []
    for w in windows:
        for p in w.pols:
            rows.append({"window_id": w.window_id, "batch": w.batch_id, "role": w.role, "direction": w.direction, "before": w.before_date,
                         "after": w.after_date, "span_days": w.span_days, "window_status": w.status, "pol": p.pol,
                         "pol_status": p.status, "baseline_status": p.baseline.status, "baseline_pairs": p.baseline.n_pairs,
                         "study_minus_control_db": p.study_minus_control_db.value,
                         "study_aggregate_db": next((z.aggregate_db.value for z in p.zones if z.zone_id == "study"), None),
                         "study_observed_fraction": next((z.observed_fraction.value for z in p.zones if z.zone_id == "study"), None),
                         "flag_ratio": p.flags.ratio.value if p.flags else None,
                         "study_flag_fraction": p.flags.study_fraction.value if p.flags else None,
                         "control_flag_fraction": p.flags.control_fraction.value if p.flags else None,
                         "development_window": w.development_window})
    for name, data, key in (("windows.csv", rows, "windows_csv"),
                            ("quality_reasons.csv", [{"window_id": q.window_id, "pol": q.pol, "zone": q.zone_id,
                                                      "observed_fraction": q.observed_fraction.value,
                                                      **{k: v.value for k, v in q.reasons.items()}} for q in quality_rows], "quality_csv"),
                            ("acquisitions.csv", [{k: v for k, v in a.model_dump().items() if k in
                                                   ("acquisition_id", "granule_id", "collection", "crid", "geometry_id", "time_utc", "status", "reasons")}
                                                  for a in acq_models], "acquisitions_csv"),
                            ("optical_groups.csv", [{"mode": e.mode, "group": g.group_id, "before": g.before_item, "after": g.after_item,
                                                     "windows": ";".join(g.pair_ids), "n_ci_above_1": g.n_ci_above_1}
                                                    for e in optical_ev for g in e.groups], "optical_groups_csv")):
        exports.append(Export(id=key, format="csv", path=f"exports/{name}", description_key=f"export.{key}", sha256=export.write_csv(out_dir / "exports" / name, data)))
    limits = ["limit.gcov_provisional", "limit.calibration_before_2026_11_12", "limit.no_noise_correction", "limit.effective_resolution",
              "limit.perimeter_historical", "limit.no_independent_reference", "limit.optical_dependency", "limit.not_attribution",
              "limit.development_windows", "limit.interval_conditional", "limit.p05036_separate", "limit.instrument_gap",
              "limit.no_data_is_not_no_change", "limit.not_ore_or_hazard"]
    processing = Processing(status="complete", rule="complete when GCOV crops are verified and at least one window is computed; "
                            "the independent reference and the boundary review are reported separately as pending", steps=steps,
                            blockers=[] if any(w.status == "computed" for w in windows) else ["blocker.no_window_computed"])
    study = dict(study_id=cfg["study_id"], run_id=run_id, data_nature=cfg["data_nature"], presentation_level_key="presentation.exploratory_surface",
                 site=Site(**cfg["site"]), protocol=ProtocolInfo(
                     id=proto["protocol_id"], version=proto["version"], frozen_utc=proto["frozen_utc"], status=proto["status"],
                     sha256=export.sha256(proto_path), history_note=proto["history_note"], primary_observable=proto["observable"]["primary"]["id"],
                     parameters={"k_sigma": pf["k_sigma"], "noise_margin_linear": pq["noise_margin_linear"],
                                 "min_disjoint_pairs": pb["min_disjoint_pairs"], "bootstrap_block_m": block_m,
                                 "min_valid_subpixel_fraction": pq["min_valid_subpixel_fraction"]}),
                 boundary=boundary, zones=zones, zones_url="zones.geojson", acquisitions=acq_models, batches=bi, windows=windows,
                 quality=quality_rows, optical_scenes=optical_scenes, evidence=EvidenceSummary(optical=optical_ev, references=ref_state["effective"]),
                 references=ref_state["state"], reference_catalogue=[Reference(**r) for r in cfg["references"]], conclusions=conclusions,
                 findings=findings, layers=layers, exports=exports, limits=limits, external_sources=cfg["external_sources"],
                 processing=processing, v2_context=None if not v2_ctx else {k: v for k, v in v2_ctx.items() if k != "pairs"})
    return _finish(study, staging, case_dir, cfg_path, log, t_start, run_id, repo_root, publish)


# ----------------------------------------------------------------------------------------------- pieces
def _acq_model(a: Acq, cfg: dict) -> GcovAcquisition:
    prov, ident, proc = a.prov, a.prov["identification"], a.prov["processing"]
    inc = float(np.nanmedian(a.incidence)) if a.incidence is not None else None
    nd = {}
    for pol, nebs in a.noise_db.items():
        nd[pol] = _m(None if nebs is None else 10 * math.log10(float(np.nanmedian(nebs))), "dB", "no noise-equivalent backscatter in the crop")
    caveats = ["caveat.no_noise_correction"] if str(proc.get("noise_correction_applied")) == "False" else []
    if a.date < "2026-11-12":
        caveats.append("caveat.calibration_before_2026_11_12")
    if a.collection.endswith("PROVISIONAL_V1"):
        caveats.append("caveat.provisional")
    modes = ident.get("listOfObservationModes")
    return GcovAcquisition(
        acquisition_id=a.acq_id, granule_id=prov["granule_id"], collection=a.collection,
        maturity="provisional" if a.collection.endswith("PROVISIONAL_V1") else "validated", crid=a.crid, geometry_id=a.geometry_id,
        direction=a.direction, track=a.track, frame=a.frame, time_utc=a.time, product_version=ident.get("productVersion"),
        specification_version=ident.get("productSpecificationVersion"), software_version=proc.get("software_version"),
        processing_datetime=ident.get("processingDateTime"), doi=ident.get("productDoi"), source_url=prov["source_url"],
        bytes_transferred=prov.get("bytes_transferred"), polarizations=prov["polarizations"], native_spacing_m=prov["native_spacing_m"][0],
        analysis_spacing_m=20.0, observation_mode=", ".join(modes) if isinstance(modes, list) else modes,
        noise_correction_applied=None if proc.get("noise_correction_applied") is None else str(proc["noise_correction_applied"]) == "True",
        rtc_applied=None if proc.get("rtc_applied") is None else str(proc["rtc_applied"]) == "True",
        normalization=proc.get("normalization"),
        has_input_data_exception=None if ident.get("hasInputDataException") is None else bool(ident["hasInputDataException"]),
        median_looks=_m(None if a.looks is None else float(np.nanmedian(a.looks)), "count", "no numberOfLooks layer"),
        noise_floor_db=nd, median_incidence_deg=_m(inc, "degrees", "no incidence angle in the crop"),
        observed_fraction_study={k: measured(v, "fraction") for k, v in a.obs_study.items()},
        files=prov["files"], status=a.status, reasons=a.reasons, calibration_caveat_keys=caveats)


def _conclusions(zone_masks, W, opt_extra, Z, ctrl_eval, cfg, pix_km2, centroid, calib, dev_wids) -> list[ZoneConclusion]:
    out = []
    ratio_min, cells_min = cfg["elevated_ratio"], cfg["elevated_min_cells"]
    for zid, zm in zone_masks.items():
        if not zm.any():
            continue
        n_win = n_el = 0
        fr, smc_l, dark = [], [], []
        wids, desc = [], []
        for wid, rec in W.items():
            p = rec["pols"].get("HH")
            if not p or p.get("delta") is None or rec["span"] != 12:
                continue
            of = float(p["valid"][zm].mean())
            if of < 0.5:
                continue
            ctrl = (p.get("zstats") or {}).get("study")
            st = bs.zone_delta_db(rec["x"].power["HH"], rec["y"].power["HH"], p["valid"], zm)
            cg = bs.zone_delta_db(rec["x"].power["HH"], rec["y"].power["HH"], p["valid"], Z["control"])
            if st["aggregate_db"] is not None and cg["aggregate_db"] is not None:
                desc.append(st["aggregate_db"] - cg["aggregate_db"])
            if p.get("res") is None:
                continue
            res = p["res"]
            n_win += 1
            wids.append(wid)
            n_f = int((res["flagged"] & res["valid"] & zm).sum())
            n_v = int((res["valid"] & zm).sum())
            f = n_f / n_v if n_v else 0.0
            fr.append(f)
            r_c = p["rate"]["control_fraction"] or 0.0
            if n_f >= cells_min and f >= ratio_min * max(r_c, 1e-6):
                n_el += 1
            if n_f:
                dark.append(float(((res["direction"] == -1) & zm).sum() / n_f))
        if n_win:
            status = "measured"
        elif desc:
            status = "insufficient_baseline"
        else:
            status = "unavailable"
        radar_params = {"n_windows_with_baseline": n_win, "n_windows_elevated": n_el,
                        "median_flagged_fraction": float(np.median(fr)) if fr else None,
                        "median_darker_share_of_flags": float(np.median(dark)) if dark else None,
                        "median_study_minus_control_db": float(np.median(desc)) if desc else None,
                        "n_windows_descriptive": len(desc),
                        "selection": ("recurrence_of_the_same_flags" if zid.startswith("N") else "v2_coherence_recurrence" if zid == "Z1" else "perimeter_definition"),
                        "elevated_rule": f"flagged fraction >= {ratio_min} x control rate and >= {cells_min} cells"}
        # optical, per distinct optical pair
        pairs: dict[tuple[str, str], list[bool]] = {}
        pair_outside_dev: dict[tuple[str, str], bool] = {}
        for key, ex_ in opt_extra.items():
            wid, mode = key.split("|")
            if mode != "strict":
                continue
            clear = ex_["before"]["clear"] & ex_["after"]["clear"]
            sel = zm & clear
            ctrl_sel = Z["control"] & calib & clear
            if sel.sum() < 25 or ctrl_sel.sum() < 500:
                pairs.setdefault((ex_["before"]["item_id"], ex_["after"]["item_id"]), []).append(None)
                continue
            n_f = int((ex_["oflag"] & sel).sum())
            rate, rc = n_f / sel.sum(), float((ex_["oflag"] & ctrl_sel).sum() / ctrl_sel.sum())
            pk = (ex_["before"]["item_id"], ex_["after"]["item_id"])
            pairs.setdefault(pk, []).append(bool(n_f >= cells_min and rate >= ratio_min * max(rc, 1e-6)))
            pair_outside_dev[pk] = pair_outside_dev.get(pk, False) or wid not in dev_wids
        judged = {k: [v for v in vs if v is not None] for k, vs in pairs.items()}
        judged = {k: v for k, v in judged.items() if v}
        n_pairs = len(judged)
        n_pairs_el = sum(1 for v in judged.values() if any(v))
        n_el_outside_dev = sum(1 for k, v in judged.items() if any(v) and pair_outside_dev.get(k))
        optical_state = ("not_assessed" if not pairs else
                         "not_observable" if not judged else
                         "corroborated_two_or_more_optical_pairs" if n_pairs_el >= 2 else
                         "one_optical_pair" if n_pairs_el == 1 else "not_elevated")
        out.append(ZoneConclusion(
            zone_id=zid, label_key=ZONE_LABELS.get(zid, "zone.candidate"), centroid=centroid(zm), area_km2=round(float(zm.sum() * pix_km2), 3),
            radar_variation=status, radar_params=radar_params, optical_visible_change=optical_state,
            optical_params={"n_distinct_optical_pairs_assessed": n_pairs, "n_distinct_optical_pairs_elevated": n_pairs_el,
                            "n_elevated_pairs_with_a_window_outside_development": n_el_outside_dev,
                            "optical_pairs": [list(k) for k in judged]},
            alternative_keys=["alt.moisture", "alt.vegetation_or_crop", "alt.surface_roughness", "alt.operations", "alt.instrument"],
            to_collect_keys=["collect.dated_imagery", "collect.operations_calendar", "collect.rain_irrigation", "collect.site_observation"],
            window_ids=wids))
    return out


def _verification_zones(out_dir, zone_masks, conclusions, grid, epsg, exports, centroid, pix_km2):
    from rasterio.features import shapes
    from rasterio.warp import transform_geom
    feats = []
    for c in conclusions:
        if c.zone_id.startswith("N") or c.zone_id == "Z1":
            m = zone_masks[c.zone_id].astype("uint8")
            for geom, v in shapes(m, mask=m > 0, transform=grid["transform"], connectivity=8):
                feats.append({"type": "Feature", "id": c.zone_id, "geometry": transform_geom(f"EPSG:{epsg}", "EPSG:4326", geom, precision=6),
                              "properties": {"id": c.zone_id, "area_km2": c.area_km2, "radar_variation": c.radar_variation,
                                             "optical_visible_change": c.optical_visible_change, "cause": "undetermined"}})
    sha = export.write_json(out_dir / "exports" / "verification_zones.geojson", {"type": "FeatureCollection", "features": feats})
    exports.append(Export(id="verification_zones", format="geojson", path="exports/verification_zones.geojson",
                          description_key="export.verification_zones", sha256=sha))
    return None


def _v2_context(repo_root: Path, cfg: dict, log: InputLog):
    p = repo_root / cfg["v2_case"]
    if not p.exists():
        return None
    case = json.loads(log(p, role="v2_case").read_text(encoding="utf-8"))
    pairs = {}
    main = next((m["main_profile"] for m in [case["method"]]), "ring@0.01")
    for pr in case["pairs"]:
        if pr["status"] != "ok":
            continue
        prof = next((x for x in pr["profiles"] if x["id"] == main), None)
        if prof is None:
            continue
        ratio = prof["ratio_to_evaluation_rate"]
        u = ratio.get("uncertainty") or {}
        pairs[(pr["geometry_id"], pr["reference_date"], pr["secondary_date"])] = {
            "v2_pair_id": pr["pair_id"], "ratio": ratio["value"], "ci_low": u.get("low"), "ci_high": u.get("high"),
            "exceeds_control": prof["exceeds_control"], "observable": "low coherence relative to a control (GUNW, 20 m)"}
    return {"case_id": case["case_id"], "run_id": case["run_id"], "schema_version": case["schema_version"],
            "note": "GUNW low-coherence result kept as context; a different observable, never renamed surface change",
            "pairs": pairs}


def _references(case_dir, cfg, W, opt_extra, opt_comps, Z, grid, epsg, out_dir, ctrl_eval, log, repo_root):
    """Sampling frame, blind annotation packet and, if a person has filled annotations, the evaluation."""
    from PIL import Image
    from pyproj import Transformer
    exports = []
    frames = {}
    chips_src = {}
    for wid, rec in W.items():
        p = rec["pols"].get("HH")
        if not p or p.get("res") is None:
            continue
        pick = None
        for mode in ("strict", "exploratory"):
            if f"{wid}|{mode}" in opt_extra:
                pick = (mode, opt_extra[f"{wid}|{mode}"])
                break
        if pick is None:
            continue
        mode, ex_ = pick
        clear = ex_["before"]["clear"] & ex_["after"]["clear"]
        fr = refs.frame(p["res"]["flagged"] & clear, p["res"]["valid"] & clear, Z["study"], Z["control"])
        fr["_group"] = f"{ex_['before']['item_id']}|{ex_['after']['item_id']}"
        frames[wid] = fr
        chips_src[wid] = (mode, ex_)
    units, counts = refs.draw(frames, cfg["reference_per_stratum"], cfg["sampling_seed"]) if frames else ([], {})
    tr = grid["transform"]
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    k = refs.UNIT_CELLS
    analyst, blind, rows = [], [], []
    for u in units:
        r0, c0 = u["block_row"] * k, u["block_col"] * k
        x0, y0 = tr.c + c0 * tr.a, tr.f + r0 * tr.e
        x1, y1 = x0 + k * tr.a, y0 + k * tr.e
        ring = [list(to_ll(x, y)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))]
        mode, ex_ = chips_src[u["window_id"]]
        geom = {"type": "Polygon", "coordinates": [[[round(a, 6), round(b, 6)] for a, b in ring]]}
        uid = u["unit_id"]
        safe = uid.replace(":", "_")
        for tag, stk in (("before", ex_["x0"]), ("after", ex_["x1"])):
            h = 10
            rr0, rr1, cc0, cc1 = max(r0 + k // 2 - h, 0), r0 + k // 2 + h + 1, max(c0 + k // 2 - h, 0), c0 + k // 2 + h + 1
            rgb = np.clip((np.moveaxis(stk[[2, 1, 0], rr0:rr1, cc0:cc1], 0, -1) - 0.03) / 0.47, 0, 1)
            img = Image.fromarray((np.nan_to_num(rgb) * 255).astype("uint8"), "RGB").resize((rgb.shape[1] * 6, rgb.shape[0] * 6), Image.NEAREST)
            (out_dir / "annotation" / "chips").mkdir(parents=True, exist_ok=True)
            img.save(out_dir / "annotation" / "chips" / f"{safe}_{tag}.png", optimize=True)
        analyst.append({**u, "geometry": geom, "optical_mode": mode})
        blind.append({"type": "Feature", "id": uid, "geometry": geom,
                      "properties": {"unit_id": uid, "optical_before": ex_["before"]["datetime"][:10], "optical_after": ex_["after"]["datetime"][:10],
                                     "chip_before": f"annotation/chips/{safe}_before.png", "chip_after": f"annotation/chips/{safe}_after.png"}})
        rows.append({"unit_id": uid, "label": "", "source": "", "annotator": "", "blind_to_radar": "", "annotated_utc": "", "notes": ""})
    seed_info = {"seed": cfg["sampling_seed"], "per_stratum_target": cfg["reference_per_stratum"], "unit_cells": k,
                 "unit_size_m": k * abs(tr.a), "strata_counts": counts, "n_units": len(units),
                 "note": "analyst file: it carries the strata (radar status). Annotators receive only units_for_annotators.geojson, the chips and the template."}
    export.write_json(out_dir / "annotation" / "sampling_frame.json", {**seed_info, "units": [{k_: v for k_, v in a.items() if k_ != "geometry"} for a in analyst]})
    export.write_json(out_dir / "annotation" / "units_for_annotators.geojson", {"type": "FeatureCollection", "features": blind})
    export.write_csv(out_dir / "annotation" / "annotation_template.csv", rows)
    (out_dir / "annotation" / "README.md").write_text(
        "# Blind annotation packet\n\nFor each unit (60 m x 60 m) look at the `before` and `after` chips (Sentinel-2 true colour, 10 m native) "
        "and fill `annotation_template.csv`: `label` in {change_visible, no_change_visible, indeterminate}; `source` = human; `annotator`; "
        "`blind_to_radar` = true only if you did not see any radar product; `annotated_utc`. Add `annotation_meta.json` (reference_id, reviewer, "
        "reviewer_independent, method, rights, source, date_start, date_end, geometry_ref). Put both files in `cases/<case>/annotations/` and re-run. "
        "Proposals made by an agent or an algorithm must use source = agent / automated: they are counted but never support a validation.\n",
        encoding="utf-8", newline="\n")
    for name, fmt, key in (("sampling_frame.json", "json", "reference_sampling"), ("units_for_annotators.geojson", "geojson", "reference_units"),
                           ("annotation_template.csv", "csv", "reference_template"), ("README.md", "markdown", "reference_readme")):
        exports.append(Export(id=key, format=fmt, path=f"annotation/{name}", description_key=f"export.{key}", sha256=export.sha256(out_dir / "annotation" / name)))
    # evaluation only from a file filled by a person
    ann_dir = case_dir / cfg["annotation_dir"]
    n_ann, eval_res, effective, missing = 0, None, [], []
    if (ann_dir / "annotations.csv").exists() and (ann_dir / "annotation_meta.json").exists():
        import csv
        with open(log(ann_dir / "annotations.csv", role="annotations"), encoding="utf-8", newline="") as f:
            ann = [{**r, "blind_to_radar": str(r.get("blind_to_radar", "")).lower() == "true"} for r in csv.DictReader(f)
                   if r.get("label")]
        meta = json.loads(log(ann_dir / "annotation_meta.json", role="annotation_meta").read_text(encoding="utf-8"))
        n_ann = len(ann)
        eval_res = refs.evaluate(analyst, ann, seed=cfg["sampling_seed"])
        missing = eval_res.get("missing", [])
        meta.setdefault("geometry_ref", "annotation/units_for_annotators.geojson")
        re_ = refs.to_reference_evidence(eval_res, meta, analyst, "visible_surface_change_at_flagged_cells")
        if re_ is not None:
            effective.append(re_)
            missing = re_.missing()
    else:
        missing = ["annotations_filled_by_an_independent_person", "annotation_meta"]
    status = "awaiting_annotations" if n_ann == 0 else ("evaluated" if effective and effective[0].effective() else "annotated_insufficient")
    state = ReferenceState(
        status=status, unit_definition=f"{k} x {k} analysis cells ({k * abs(tr.a):g} m), drawn from a recorded seed, stratified by radar status",
        sampling_file="annotation/sampling_frame.json", annotation_template="annotation/annotation_template.csv",
        n_units_sampled={s: counts.get(s, {}).get("sampled", 0) for s in refs.STRATA} if counts else {}, n_annotated=n_ann,
        n_indeterminate=0 if not eval_res else eval_res.get("n_indeterminate", 0),
        evaluation=None if not eval_res else {k_: v for k_, v in eval_res.items() if k_ in ("status", "metrics", "intervals", "n_groups", "ignored", "indeterminate_rate", "scope")},
        missing=missing)
    return {"state": state, "effective": effective}, exports


def _findings(windows, optical_ev, acqs, ref_state) -> list[Finding]:
    f = []
    comp = [w for w in windows if w.status == "computed"]
    f.append(Finding(id="F_windows", kind="windows", params={"n_windows": len(windows), "n_computed": len(comp),
                                                              "n_rejected": len(windows) - len(comp)}, evidence=[w.window_id for w in windows]))
    for direction in ("ascending", "descending"):
        sel = [w for w in comp if w.direction == direction and w.role == "main" and w.span_days == 12]
        vals = [p.study_minus_control_db.value for w in sel for p in w.pols if p.pol == "HH" and p.study_minus_control_db.value is not None]
        if vals:
            f.append(Finding(id=f"F_delta_{direction}", kind="study_minus_control_db",
                             params={"direction": direction, "n_windows": len(vals), "median_db": float(np.median(vals)),
                                     "min_db": float(min(vals)), "max_db": float(max(vals)), "pol": "HH"},
                             evidence=[w.window_id for w in sel], limit_keys=["limit.calibration_before_2026_11_12"]))
    flagged = [(w, p) for w in comp for p in w.pols if p.pol == "HH" and p.flags is not None and w.span_days == 12 and w.role == "main"]
    if flagged:
        ratios = [p.flags.ratio.value for _, p in flagged if p.flags.ratio.value is not None]
        n_ci = sum(1 for _, p in flagged if p.flags.ratio.uncertainty and p.flags.ratio.uncertainty.kind == "block_bootstrap_interval"
                   and (p.flags.ratio.uncertainty.low or 0) > 1)
        f.append(Finding(id="F_flags_hh", kind="temporal_flags",
                         params={"n_windows": len(flagged), "median_ratio": float(np.median(ratios)) if ratios else None,
                                 "min_ratio": min(ratios) if ratios else None, "max_ratio": max(ratios) if ratios else None,
                                 "n_ci_above_1": n_ci, "k_sigma": 3.0},
                         evidence=[w.window_id for w, _ in flagged], limit_keys=["limit.interval_conditional"]))
    nobase = [w for w in comp for p in w.pols if p.pol == "HH" and p.baseline.status == "insufficient_baseline"]
    if nobase:
        f.append(Finding(id="F_insufficient_baseline", kind="insufficient_baseline", params={"n_windows": len(nobase)},
                         evidence=[w.window_id for w in nobase], limit_keys=["limit.no_data_is_not_no_change"]))
    hv_cov = [p.zones[0].observed_fraction.value for w in comp for p in w.pols if p.pol == "HV" and p.zones and p.zones[0].observed_fraction.value is not None]
    if hv_cov:
        f.append(Finding(id="F_hv_coverage", kind="hv_noise", params={"median_observed_fraction_study": float(np.median(hv_cov)), "n_windows": len(hv_cov)},
                         evidence=[], limit_keys=["limit.no_noise_correction"]))
    rej = [a for a in acqs if a.status == "rejected"]
    f.append(Finding(id="F_dates", kind="dates", params={"n_acquisitions": len(acqs), "n_rejected": len(rej),
                                                         "rejected": [a.acquisition_id for a in rej]}, evidence=[]))
    for e in optical_ev:
        f.append(Finding(id=f"F_optical_{e.mode}", kind="optical_dependency",
                         params={"mode": e.mode, "n_radar_comparisons": e.n_radar_comparisons, "n_unique_optical_pairs": e.n_unique_optical_pairs,
                                 "n_groups_ci_above_1": e.n_groups_ci_above_1}, evidence=[],
                         limit_keys=["limit.optical_dependency"]))
    f.append(Finding(id="F_reference", kind="reference_state", params={"status": ref_state["state"].status, "n_annotated": ref_state["state"].n_annotated,
                                                                       "missing": ref_state["state"].missing}, evidence=[],
                     limit_keys=["limit.no_independent_reference"]))
    return f


def verify_run(folder: Path, study: SurfaceStudy) -> list[str]:
    problems = []
    refs_ = {l.url for l in study.layers} | {e.path for e in study.exports} | {study.zones_url}
    for rel in sorted(refs_):
        if not (folder / rel).is_file():
            problems.append(f"missing file {rel}")
    if study.manifest:
        for o in study.manifest.outputs:
            f = folder / o.path
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != o.sha256:
                problems.append(f"output {o.path} differs from the manifest")
    try:
        SurfaceStudy.model_validate_json((folder / "study.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"study.json does not satisfy the contract: {exc}")
    return problems


def _finish(study_kw, staging, case_dir, cfg_path, log, t_start, run_id, repo_root, publish) -> SurfaceStudy:
    from . import report
    study = SurfaceStudy(**study_kw)
    # report is a derived output of the validated study: written before the manifest hashes the outputs
    rep = report.write(staging, study)
    study_kw["exports"] = study_kw["exports"] + [Export(id="report_html", format="html", path=rep, description_key="export.report_html",
                                                       sha256=export.sha256(staging / rep))]
    outputs = [FileRecord(path=str(f.relative_to(staging)).replace("\\", "/"), sha256=export.sha256(f), role="output")
               for f in sorted(staging.rglob("*")) if f.is_file() and f.name != "study.json"]
    commit, dirty = _git(repo_root)
    study_kw["manifest"] = Manifest(run_id=run_id, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), code_commit=commit,
                                    code_dirty=dirty, python=__import__("platform").python_version(), packages=_packages(),
                                    config_sha256=export.sha256(cfg_path), inputs=log.list(), outputs=outputs, duration_s=round(time.time() - t_start, 1))
    study = SurfaceStudy(**study_kw)
    export.write_json(staging / "study.json", json.loads(study.model_dump_json()))
    problems = verify_run(staging, study)
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
    return study
