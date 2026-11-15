"""Polygon-scale coherence-change analysis relative to a control zone (new module).

For one GUNW pair on the analysis grid:
    valid     = finite coherence AND product mask valid (both RSLC subswaths present, not water)
    threshold = q-quantile of the valid control-zone coherence of the SAME pair
    flagged   = valid AND coherence < threshold
By construction about q of the control pixels are flagged; the study-zone rate is compared with it. The threshold
adapts to scene-wide decorrelation (moisture, season) seen by the control zone. It is a selection rule with a
stated control flag rate, not a probability that a pixel was excavated.

The functions are pure (arrays in, dicts out) so that they can be tested on synthetic grids.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

MIN_CONTROL_PIXELS = 2000


def mask_valid(mask: np.ndarray, fill: int = 255) -> np.ndarray:
    """NISAR GUNW mask, bits 0-7 = decimal digits [water][reference subswath][secondary subswath].
    Valid when both subswath digits are non-zero and the water digit is 0. Anomaly bits (8-23) are reported
    separately and do not invalidate a pixel here."""
    m = mask.astype("int64")
    low = m & 0xFF
    sec, ref, water = low % 10, (low // 10) % 10, (low // 100) % 10
    return (m != fill) & (sec > 0) & (ref > 0) & (water == 0)


def anomaly_flags(mask: np.ndarray) -> np.ndarray:
    m = mask.astype("int64")
    return ((m >> 8) & 0xFFFF) != 0


def flag_pair(coh: np.ndarray, valid: np.ndarray, control: np.ndarray, quantile: float) -> dict:
    if not 0 < quantile < 0.5:
        raise ValueError("the control quantile must be in (0, 0.5)")
    if coh.shape != valid.shape or coh.shape != control.shape:
        raise ValueError("coherence, validity and control grids differ")
    ok = valid & np.isfinite(coh)
    ctrl = coh[ok & control]
    if ctrl.size < MIN_CONTROL_PIXELS:
        return {"status": "insufficient_control", "threshold": None, "flagged": None,
                "control_valid_pixels": int(ctrl.size)}
    thr = float(np.quantile(ctrl, quantile))
    flagged = ok & (coh < thr)
    return {"status": "ok", "threshold": thr, "flagged": flagged, "valid": ok,
            "control_valid_pixels": int(ctrl.size),
            "control_flag_rate": float((ctrl < thr).mean()),
            "control_median": float(np.median(ctrl))}


def zone_stats(flagged: np.ndarray | None, valid: np.ndarray, zone: np.ndarray, coh: np.ndarray,
               pixel_km2: float) -> dict:
    """Area statistics inside one zone. Unobserved pixels stay unobserved (never counted as unchanged)."""
    n_zone = int(zone.sum())
    obs = valid & zone
    n_obs = int(obs.sum())
    out = {"zone_pixels": n_zone, "zone_area_km2": n_zone * pixel_km2, "observable_pixels": n_obs,
           "observable_area_km2": n_obs * pixel_km2,
           "observable_fraction": (n_obs / n_zone) if n_zone else None,
           "flagged_area_km2": None, "flagged_fraction_of_observable": None, "median_coherence": None}
    if n_obs:
        out["median_coherence"] = float(np.median(coh[obs]))
    if flagged is not None and n_obs:
        nf = int((flagged & zone).sum())
        out["flagged_area_km2"] = nf * pixel_km2
        out["flagged_fraction_of_observable"] = nf / n_obs
    return out


def change_zones(flagged: np.ndarray, zone: np.ndarray, coh: np.ndarray, min_pixels: int) -> tuple[np.ndarray, list[dict]]:
    """Connected clusters (8-connectivity) of flagged pixels inside the zone, at least min_pixels large."""
    lab, n = ndimage.label(flagged & zone, structure=np.ones((3, 3), dtype=bool))
    if n == 0:
        return np.zeros(flagged.shape, dtype="int32"), []
    sizes = ndimage.sum_labels(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    keep = np.nonzero(sizes >= min_pixels)[0] + 1
    out = np.zeros(flagged.shape, dtype="int32")
    clusters = []
    for new_id, old in enumerate(sorted(keep, key=lambda k: -sizes[k - 1]), start=1):
        sel = lab == old
        out[sel] = new_id
        rows, cols = np.nonzero(sel)
        clusters.append({"id": new_id, "pixels": int(sel.sum()), "row": float(rows.mean()), "col": float(cols.mean()),
                         "median_coherence": float(np.median(coh[sel]))})
    return out, clusters


def recurrence(flags: list[np.ndarray], valids: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """(fraction of observed pairs in which each pixel is flagged, number of observed pairs). NaN if never observed."""
    if not flags:
        raise ValueError("no pair to combine")
    count = np.zeros(flags[0].shape, dtype="int32")
    seen = np.zeros(flags[0].shape, dtype="int32")
    for f, v in zip(flags, valids):
        count += (f & v)
        seen += v
    frac = np.where(seen > 0, count / np.maximum(seen, 1), np.nan).astype("float32")
    return frac, seen


def lift(a: np.ndarray, b: np.ndarray, domain: np.ndarray) -> dict:
    """Spatial association of two boolean maps inside a domain: P(b | a) / P(b | not a), and Jaccard index."""
    a, b = a & domain, b & domain
    na, nn = int(a.sum()), int((domain & ~a).sum())
    p_ba = (int((a & b).sum()) / na) if na else None
    p_bn = (int((b & ~a & domain).sum()) / nn) if nn else None
    union = int((a | b).sum())
    out = {"n_a": na, "n_b": int(b.sum()), "n_both": int((a & b).sum()), "p_b_given_a": p_ba,
           "p_b_given_not_a": p_bn, "lift": None, "jaccard": (int((a & b).sum()) / union) if union else None}
    if p_ba is not None and p_bn:
        out["lift"] = p_ba / p_bn
    return out


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 30:
        return None
    from scipy.stats import spearmanr
    r = spearmanr(x[ok], y[ok]).statistic
    return None if not math.isfinite(r) else float(r)
