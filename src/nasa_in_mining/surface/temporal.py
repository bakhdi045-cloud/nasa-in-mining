"""Temporal reference of backscatter change: residual of a pair against pairs that share none of its acquisitions.

A single pair gives a descriptive map of change, not an estimate of the usual state: without enough homogeneous,
non-overlapping pairs the answer is `insufficient_baseline` (never zero, never "stable").
Homogeneous = same collection, CRID, track, frame, direction, polarisation and span.
"""
from __future__ import annotations

import numpy as np

from ..mining import stats

ROBUST = 1.4826   # MAD to sigma for a Gaussian


def disjoint_baseline(target: tuple[str, str], candidates: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Pairs of `candidates` (reference, secondary acquisition ids) that share no acquisition with the target."""
    return [c for c in candidates if c != target and not (set(c) & set(target))]


def baseline_median(stack: list[np.ndarray], min_pairs_per_cell: int) -> np.ndarray:
    """Per-cell median over the baseline pairs, NaN where fewer than `min_pairs_per_cell` pairs observed the cell."""
    a = np.stack(stack).astype("float64")
    n = np.isfinite(a).sum(axis=0)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(a, axis=0)
    med[n < min_pairs_per_cell] = np.nan
    return med.astype("float32")


def robust_sigma(values: np.ndarray) -> float | None:
    v = values[np.isfinite(values)]
    if v.size < 100:
        return None
    return float(ROBUST * np.median(np.abs(v - np.median(v))))


def flag_residual(delta: np.ndarray, baseline: np.ndarray, control: np.ndarray, calib: np.ndarray, k: float,
                  min_control_cells: int = 500) -> dict:
    """Flag cells whose change departs from the baseline by more than k robust sigmas of the control residuals.

    sigma and centre come from the calibration half of the control only; the flag rate of the held-out evaluation
    half is what the study is compared with. `direction`: -1 darker than the baseline expectation, +1 brighter.
    """
    resid = delta.astype("float64") - baseline.astype("float64")
    ok = np.isfinite(resid)
    cal = resid[ok & control & calib]
    ev_n = int((ok & control & ~calib).sum())
    if cal.size < min_control_cells or ev_n < min_control_cells:
        return {"status": "insufficient_control", "calibration_cells": int(cal.size), "evaluation_cells": ev_n}
    centre = float(np.median(cal))
    sigma = robust_sigma(cal)
    if not sigma:
        return {"status": "insufficient_control", "calibration_cells": int(cal.size), "evaluation_cells": ev_n}
    z = (resid - centre) / sigma
    flagged = ok & (np.abs(np.nan_to_num(z)) > k)
    direction = np.zeros(delta.shape, dtype="int8")
    direction[flagged & (z < 0)] = -1
    direction[flagged & (z > 0)] = 1
    return {"status": "ok", "residual": resid.astype("float32"), "z": z.astype("float32"), "flagged": flagged,
            "valid": ok, "direction": direction, "centre_db": centre, "sigma_db": sigma,
            "calibration_cells": int(cal.size), "evaluation_cells": ev_n,
            "calibration_rate": float(flagged[ok & control & calib].mean()),
            "evaluation_rate": float(flagged[ok & control & ~calib].mean())}


def rate_ratio(flagged: np.ndarray, valid: np.ndarray, study: np.ndarray, control_eval: np.ndarray,
               ids: np.ndarray, seed: int) -> dict:
    """Flag fraction in the study and in the held-out control, their ratio and block-bootstrap intervals."""
    k1, n1 = stats.block_counts(flagged, valid, study, ids)
    k2, n2 = stats.block_counts(flagged, valid, control_eval, ids)
    s, c = int((flagged & valid & study).sum()), int((valid & study).sum())
    s2, c2 = int((flagged & valid & control_eval).sum()), int((valid & control_eval).sum())
    f1 = s / c if c else None
    f2 = s2 / c2 if c2 else None
    boot = stats.bootstrap_ratio(k1, n1, k2, n2, seed=seed) if c and c2 else {"status": "empty"}
    return {"study_flagged": s, "study_valid": c, "control_flagged": s2, "control_valid": c2, "study_fraction": f1,
            "control_fraction": f2, "ratio": (f1 / f2) if (f1 is not None and f2) else None, "bootstrap": boot}
