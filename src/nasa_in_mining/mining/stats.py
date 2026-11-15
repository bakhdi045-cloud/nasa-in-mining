"""Spatial statistics for v2: calibration/evaluation split of controls, block bootstrap, autocorrelation,
contingency tables, overlap-based zone matching and date-window pairing (new module).

Pixels are spatially dependent: no interval here treats them as independent observations. Intervals come from
resampling square blocks; their sensitivity to the block size is reported by the pipeline.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np

from .coherence_change import MIN_CONTROL_PIXELS


def checkerboard(shape: tuple[int, int], block_px: int) -> np.ndarray:
    """True = calibration blocks, False = evaluation blocks (alternating squares of block_px pixels)."""
    rows = np.arange(shape[0]) // block_px
    cols = np.arange(shape[1]) // block_px
    return ((rows[:, None] + cols[None, :]) % 2) == 0


def threshold_split(coh: np.ndarray, valid: np.ndarray, control: np.ndarray, calib: np.ndarray,
                    quantile: float) -> dict:
    """Threshold from the calibration part of a control; flag rate measured on its held-out evaluation part.
    The calibration rate is close to the quantile by construction and is not evidence of anything."""
    if not 0 < quantile < 0.5:
        raise ValueError("the control quantile must be in (0, 0.5)")
    ok = valid & np.isfinite(coh)
    cal = coh[ok & control & calib]
    ev = coh[ok & control & ~calib]
    if cal.size < MIN_CONTROL_PIXELS or ev.size < MIN_CONTROL_PIXELS:
        return {"status": "insufficient_control", "threshold": None, "calibration_pixels": int(cal.size),
                "evaluation_pixels": int(ev.size)}
    thr = float(np.quantile(cal, quantile))
    return {"status": "ok", "threshold": thr, "calibration_pixels": int(cal.size), "evaluation_pixels": int(ev.size),
            "calibration_rate": float((cal < thr).mean()), "evaluation_rate": float((ev < thr).mean()),
            "flagged": ok & (coh < thr), "valid": ok}


def block_ids(shape: tuple[int, int], block_px: int) -> np.ndarray:
    r = np.arange(shape[0]) // block_px
    c = np.arange(shape[1]) // block_px
    return (r[:, None] * (int(c.max()) + 1) + c[None, :]).astype("int64")


def block_counts(flag: np.ndarray, valid: np.ndarray, zone: np.ndarray, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(flagged count, valid count) for each block holding valid pixels of the zone."""
    sel = zone & valid
    if not sel.any():
        return np.zeros(0), np.zeros(0)
    _, inv = np.unique(ids[sel], return_inverse=True)
    n = np.bincount(inv).astype(float)
    k = np.bincount(inv, weights=flag[sel].astype(float))
    return k, n


def bootstrap_ratio(k1, n1, k2=None, n2=None, reps: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    """Block bootstrap of sum(k1)/sum(n1) and, when given, of its ratio to sum(k2)/sum(n2)."""
    rng = np.random.default_rng(seed)
    out: dict = {"n_blocks": int(len(n1)), "n_blocks_reference": None if n2 is None else int(len(n2))}
    if len(n1) < 5 or (n2 is not None and len(n2) < 5):
        return {**out, "status": "too_few_blocks"}
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    i1 = rng.integers(0, len(n1), size=(reps, len(n1)))
    f1 = k1[i1].sum(1) / np.maximum(n1[i1].sum(1), 1)
    out.update(status="ok", fraction_low=float(np.quantile(f1, lo)), fraction_high=float(np.quantile(f1, hi)))
    if n2 is not None:
        i2 = rng.integers(0, len(n2), size=(reps, len(n2)))
        f2 = k2[i2].sum(1) / np.maximum(n2[i2].sum(1), 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = f1 / f2
        r = r[np.isfinite(r)]
        if r.size < 0.9 * reps:
            out["ratio_status"] = "reference_rate_often_zero"
        else:
            out.update(ratio_status="ok", ratio_low=float(np.quantile(r, lo)), ratio_high=float(np.quantile(r, hi)))
    return out


def contingency(a: np.ndarray, b: np.ndarray, domain: np.ndarray) -> dict:
    """2 x 2 table of two boolean maps inside a domain, with absolute and conditional proportions."""
    a, b = a & domain, b & domain
    n11 = int((a & b).sum())
    n10 = int((a & ~b).sum())
    n01 = int((~a & b & domain).sum())
    n00 = int((domain & ~a & ~b).sum())
    na, nn, union = n11 + n10, n01 + n00, n11 + n10 + n01
    p_ba = n11 / na if na else None
    p_bn = n01 / nn if nn else None
    return {"n11": n11, "n10": n10, "n01": n01, "n00": n00, "n": na + nn,
            "p_b_given_a": p_ba, "p_b_given_not_a": p_bn,
            "ratio": (p_ba / p_bn) if (p_ba is not None and p_bn) else None,
            "jaccard": (n11 / union) if union else None,
            "share_of_b_explained_by_a": (n11 / (n11 + n01)) if (n11 + n01) else None}


def bootstrap_association(a: np.ndarray, b: np.ndarray, domain: np.ndarray, ids: np.ndarray, reps: int = 2000,
                          seed: int = 0, level: float = 0.95) -> dict:
    """Block bootstrap interval of P(b|a) / P(b|not a) inside the domain."""
    if not domain.any():
        return {"status": "empty", "n_blocks": 0}
    _, inv = np.unique(ids[domain], return_inverse=True)
    nb = int(inv.max()) + 1
    if nb < 5:
        return {"status": "too_few_blocks", "n_blocks": nb}
    aa, bb = a[domain], b[domain]
    c = [np.bincount(inv, weights=w.astype(float), minlength=nb) for w in (aa & bb, aa & ~bb, ~aa & bb, ~aa & ~bb)]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nb, size=(reps, nb))
    s11, s10, s01, s00 = (x[idx].sum(1) for x in c)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = (s11 / (s11 + s10)) / (s01 / (s01 + s00))
    r = r[np.isfinite(r)]
    if r.size < 0.9 * reps:
        return {"status": "unstable", "n_blocks": nb}
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    return {"status": "ok", "n_blocks": nb, "low": float(np.quantile(r, lo)), "high": float(np.quantile(r, hi))}


def autocorrelation(field: np.ndarray, mask: np.ndarray, lags_px: list[int]) -> dict[int, float | None]:
    """Correlation of a field with itself shifted by each lag (rows and columns), on pixel pairs inside the mask."""
    x = field.astype(float)
    out: dict[int, float | None] = {}
    for lag in lags_px:
        va, vb = [], []
        for a, b, ma, mb in ((x[:, :-lag], x[:, lag:], mask[:, :-lag], mask[:, lag:]),
                             (x[:-lag, :], x[lag:, :], mask[:-lag, :], mask[lag:, :])):
            m = ma & mb
            va.append(a[m])
            vb.append(b[m])
        a1, b1 = np.concatenate(va), np.concatenate(vb)
        out[lag] = None if a1.size < 100 or a1.std() == 0 or b1.std() == 0 else float(np.corrcoef(a1, b1)[0, 1])
    return out


def overlap_match(a: np.ndarray, b_labels: np.ndarray, min_overlap: float = 0.5) -> list[int]:
    """Labels of zones in b_labels whose overlap with the pixel set a is at least min_overlap of the smaller one.
    A neighbouring zone without enough shared pixels is not the same zone."""
    hit = b_labels[a]
    hit = hit[hit > 0]
    if hit.size == 0:
        return []
    labs, cnt = np.unique(hit, return_counts=True)
    sizes = np.bincount(b_labels.ravel())[labs]
    na = int(a.sum())
    return [int(lab) for lab, c, s in zip(labs, cnt, sizes) if c / min(na, s) >= min_overlap]


def overlap_days(a: tuple[str, str], b: tuple[str, str]) -> float:
    """Overlap in days of two time windows given as ISO strings."""
    p = lambda s: datetime.fromisoformat(s[:19])  # noqa: E731
    start, end = max(p(a[0]), p(b[0])), min(p(a[1]), p(b[1]))
    return max(0.0, (end - start).total_seconds() / 86400)
