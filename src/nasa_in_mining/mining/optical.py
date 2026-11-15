"""Sentinel-2 comparison for one radar pair (v2): scene usability measured in the zones, strict (<= 3 days) and
exploratory (<= 8 days) brackets, 2 x 2 tables with absolute and conditional proportions, block-bootstrap interval.

Sentinel-2 is a second sensor observing the same place at nearby dates. It is not ground truth: an association
between radar flags and optical change says that both sensors saw a change in the same place, not that a mining
detection is correct.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np
import rasterio

from . import stats
from .contract import OpticalComparison, absent, maybe, measured, Uncertainty

SCL_CLEAR = (4, 5, 6)
SCL_DOUBTFUL = (7,)
HYPOTHESES = ("hypothesis.moisture", "hypothesis.vegetation", "hypothesis.brightness", "hypothesis.weak")


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")[:25]).astimezone(timezone.utc)


def index(s2_dir: Path, zones: dict, hasher, min_clear_study: float, min_clear_control: float) -> list[dict]:
    """All read scenes with their clear fractions in the study and control zones (SCL measured in the zones)."""
    out = []
    if not s2_dir.exists():
        return out
    for prov in sorted(s2_dir.glob("*/provenance.json")):
        folder = prov.parent
        if folder.name.endswith(".partial"):
            continue
        rec = json.loads(hasher(prov, role="s2_provenance").read_text(encoding="utf-8"))
        if "files" not in rec:
            continue
        scl_path = hasher(folder / "scl.tif", role="s2_scl", declared=rec["files"].get("scl.tif"))
        with rasterio.open(scl_path) as src:
            scl = src.read(1)
        clear = np.isin(scl, SCL_CLEAR)
        doubt = np.isin(scl, SCL_DOUBTFUL)
        cs = float(clear[zones["study"]].mean())
        cc = float(clear[zones["control"]].mean())
        ds = float(doubt[zones["study"]].mean())
        usable = cs >= min_clear_study and cc >= min_clear_control
        reason = None if usable else (f"clear fraction {cs:.2f} in the study perimeter and {cc:.2f} in the control "
                                      f"(required {min_clear_study:.2f} / {min_clear_control:.2f})")
        out.append({**rec, "stack": folder / "stack.tif", "scl_array": scl, "clear": clear, "doubtful": doubt,
                    "date": _dt(rec["datetime"]), "clear_study": cs, "clear_control": cc, "doubtful_study": ds,
                    "usable": usable, "reason": reason})
    return sorted(out, key=lambda r: r["date"])


def bracket(scenes: list[dict], t0: datetime, t1: datetime, max_gap: float):
    before = [s for s in scenes if s["usable"] and s["date"] <= t0 and (t0 - s["date"]).total_seconds() / 86400 <= max_gap]
    after = [s for s in scenes if s["usable"] and s["date"] >= t1 and (s["date"] - t1).total_seconds() / 86400 <= max_gap]
    return (before[-1] if before else None), (after[0] if after else None)


def explain_missing(scenes: list[dict], t0: datetime, t1: datetime, max_gap: float) -> str:
    """Explicit reason why no bracket exists (nearest scenes and why they were not usable)."""
    parts = []
    for side, cond in (("before", lambda s: s["date"] <= t0), ("after", lambda s: s["date"] >= t1)):
        cands = [s for s in scenes if cond(s)]
        cands.sort(key=lambda s: abs((s["date"] - (t0 if side == "before" else t1)).total_seconds()))
        inside = [s for s in cands if abs((s["date"] - (t0 if side == "before" else t1)).total_seconds()) / 86400 <= max_gap]
        if any(s["usable"] for s in inside):
            continue
        if inside:
            parts.append(f"{side}: {len(inside)} scene(s) within {max_gap:g} d, none usable "
                         f"({'; '.join(s['datetime'][:10] + ' ' + s['reason'] for s in inside[:3])})")
        else:
            near = next((s for s in cands if s["usable"]), None)
            gap = None if near is None else abs((near["date"] - (t0 if side == "before" else t1)).total_seconds()) / 86400
            parts.append(f"{side}: no scene within {max_gap:g} d; nearest usable scene "
                         + ("none" if near is None else f"{near['datetime'][:10]} ({gap:.1f} d)"))
    return " | ".join(parts) or "no bracketing scene"


def _read_stack(scene: dict, hasher) -> np.ndarray:
    path = hasher(scene["stack"], role="s2_stack", declared=scene["files"].get("stack.tif"))
    with rasterio.open(path) as src:
        return src.read().astype("float32")


def _indices(x: np.ndarray) -> dict[str, np.ndarray]:
    with np.errstate(invalid="ignore", divide="ignore"):
        return {"ndvi": (x[3] - x[2]) / (x[3] + x[2]), "mndwi": (x[1] - x[4]) / (x[1] + x[4]), "bright": x.mean(axis=0)}


def hypothesis_labels(d_ndvi, d_mndwi, d_bright) -> np.ndarray:
    """Per-pixel spectral hypothesis index into HYPOTHESES (documented thresholds; descriptive, not calibrated)."""
    lab = np.full(d_ndvi.shape, 3, dtype="uint8")
    lab[np.abs(d_bright) >= 0.03] = 2
    lab[np.abs(d_ndvi) >= 0.1] = 1
    lab[(np.abs(d_mndwi) >= 0.2) & (np.abs(d_mndwi) >= 2 * np.abs(d_ndvi))] = 0
    return lab


def compare(mode: str, max_gap: float, scenes: list[dict], t0: datetime, t1: datetime, radar_flags: np.ndarray,
            radar_valid: np.ndarray, zones: dict, calib: np.ndarray, ids: np.ndarray, cfg: dict, hasher, seed: int):
    """Returns (OpticalComparison, extras or None)."""
    window = [t0.isoformat(timespec="minutes"), t1.isoformat(timespec="minutes")]
    na = lambda unit, r: absent(unit, r, "not_measured")  # noqa: E731
    sb, sa = bracket(scenes, t0, t1, max_gap)

    def empty(status, reason, **kw):
        return OpticalComparison(mode=mode, max_gap_days=max_gap, status=status, reason=reason, radar_window=window,
                                 joint_observable_fraction=na("fraction", reason), optical_threshold=na("reflectance", reason),
                                 p_optical_given_radar=na("fraction", reason), p_optical_given_not_radar=na("fraction", reason),
                                 association_ratio=na("ratio", reason), jaccard=na("fraction", reason),
                                 share_of_optical_change_in_radar_flags=na("fraction", reason),
                                 ratio_with_unclassified_scl=na("ratio", reason),
                                 control_median_d_mndwi=na("1", reason), **kw), None

    if sb is None or sa is None:
        return empty("no_scene_pair", explain_missing(scenes, t0, t1, max_gap))
    gaps = dict(before_item=sb["item_id"], before_datetime=sb["datetime"], after_item=sa["item_id"],
                after_datetime=sa["datetime"], gap_days_before=round((t0 - sb["date"]).total_seconds() / 86400, 2),
                gap_days_after=round((sa["date"] - t1).total_seconds() / 86400, 2),
                optical_window=[sb["datetime"][:16], sa["datetime"][:16]])
    x0, x1 = _read_stack(sb, hasher), _read_stack(sa, hasher)
    finite = np.all(np.isfinite(x0), axis=0) & np.all(np.isfinite(x1), axis=0)
    clear_main = sb["clear"] & sa["clear"] & finite
    clear_loose = (sb["clear"] | sb["doubtful"]) & (sa["clear"] | sa["doubtful"]) & finite
    d = np.sqrt(np.sum((x1 - x0) ** 2, axis=0))
    study, control = zones["study"], zones["control"]
    joint = study & radar_valid & clear_main
    jfrac = float(joint.sum() / max(study.sum(), 1))
    ctrl = d[control & calib & clear_main]
    if jfrac < cfg["min_joint_fraction"] or ctrl.size < 2000:
        return empty("insufficient_overlap", f"joint radar/optical observable fraction {jfrac:.2f} of the perimeter "
                     f"(required {cfg['min_joint_fraction']}) or too few clear control pixels ({ctrl.size})", **gaps)
    thr = float(np.quantile(ctrl, cfg["quantile"]))
    oflag = clear_main & (d > thr)
    t = stats.contingency(radar_flags, oflag, joint)
    ci = stats.bootstrap_association(radar_flags, oflag, joint, ids, seed=seed)
    loose_joint = study & radar_valid & clear_loose
    ctrl_l = d[control & calib & clear_loose]
    thr_l = float(np.quantile(ctrl_l, cfg["quantile"]))
    t_l = stats.contingency(radar_flags, clear_loose & (d > thr_l), loose_joint)
    i0, i1 = _indices(x0), _indices(x1)
    dn, dm, db = i1["ndvi"] - i0["ndvi"], i1["mndwi"] - i0["mndwi"], i1["bright"] - i0["bright"]
    both = radar_flags & oflag & joint
    labels = hypothesis_labels(dn, dm, db)
    hyp = {HYPOTHESES[i]: int((labels[both] == i).sum()) for i in range(4)}
    unc = (Uncertainty(kind="block_bootstrap_interval", low=ci["low"], high=ci["high"], level=0.95, block_m=cfg["block_m"],
                       n_blocks=ci["n_blocks"], method="percentile interval, resampling square blocks of the perimeter")
           if ci["status"] == "ok" else Uncertainty(kind="not_estimated", method=f"block bootstrap {ci['status']} "
                                                    f"({ci.get('n_blocks')} blocks)"))
    comp = OpticalComparison(
        mode=mode, max_gap_days=max_gap, status="ok", radar_window=window, **gaps,
        joint_observable_fraction=measured(jfrac, "fraction"),
        optical_threshold=measured(thr, "reflectance (L2 norm, 6 bands)"),
        table={k: t[k] for k in ("n11", "n10", "n01", "n00")},
        p_optical_given_radar=maybe(t["p_b_given_a"], "fraction", "no radar-flagged pixel in the joint domain"),
        p_optical_given_not_radar=maybe(t["p_b_given_not_a"], "fraction", "no unflagged pixel"),
        association_ratio=maybe(t["ratio"], "ratio", "undefined (zero optical change outside radar flags)",
                                uncertainty=unc if t["ratio"] is not None else None),
        jaccard=maybe(t["jaccard"], "fraction", "empty union"),
        share_of_optical_change_in_radar_flags=maybe(t["share_of_b_explained_by_a"], "fraction", "no optical change"),
        ratio_with_unclassified_scl=maybe(t_l["ratio"], "ratio", "undefined"),
        control_median_d_mndwi=maybe(float(np.nanmedian(dm[control & clear_main])), "1", "no clear control pixel"),
        spectral_hypotheses=hyp)
    return comp, {"d": d, "oflag": oflag, "joint": joint, "d_ndvi": dn, "d_mndwi": dm, "d_bright": db,
                  "labels": labels, "before": sb, "after": sa, "x0": x0, "x1": x1, "threshold": thr}


def dominant_hypothesis(labels: np.ndarray, sel: np.ndarray) -> str | None:
    if not sel.any():
        return None
    counts = np.bincount(labels[sel], minlength=4)
    return HYPOTHESES[int(counts.argmax())]


def finite_or_none(v):
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else v
