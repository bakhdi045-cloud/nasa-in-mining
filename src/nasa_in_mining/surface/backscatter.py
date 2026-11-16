"""Backscatter change from NISAR GCOV gamma-0 (linear power), with explicit per-pixel quality reasons.

Conventions (frozen in the protocol, see docs/SURFACE_STUDY.md):
- the native 10 m samples are averaged to the 20 m analysis grid in linear power, never in dB;
- delta_db = 10 * log10(gamma0_after / gamma0_before), defined only where both values are finite and > 0 and both
  dates are observed for the same polarisation;
- a spatial aggregate (zone) is 10 * log10(mean(after) / mean(before)) over the common observed cells, i.e. the
  mean is taken in linear power before the conversion to dB;
- a missing value is a reason code, never a zero and never "no change".
"""
from __future__ import annotations

import numpy as np

# Bit field of the reasons a sample/cell is not usable. 0 = observed. A pixel can carry several bits.
REASONS = {
    "outside_acquisition": 1,        # mask == 255: outside the acquisition extent (product fill value)
    "not_fully_focused": 2,          # mask == 0: at least one averaged radar sample partially focused or invalid
    "instrument_anomaly": 4,         # inputDataExceptionMask != 0 (documented: 2 = LSAR qFSP-H1 sample slip)
    "invalid_value": 8,              # non finite or <= 0 power where the mask declares the sample valid
    "near_noise_floor": 16,          # power below `margin` x the product's noise-equivalent backscatter
    "insufficient_subpixel_coverage": 32,   # fewer valid 10 m samples than required inside the 20 m cell
    "date_not_available": 64,        # the date is not part of the analysed grid (missing granule or crop)
}
SAMPLE_BITS = (REASONS["outside_acquisition"] | REASONS["not_fully_focused"] | REASONS["instrument_anomaly"]
               | REASONS["invalid_value"])


def reason_names(bits: int) -> list[str]:
    return [k for k, v in REASONS.items() if bits & v]


def sample_reasons(power: np.ndarray, mask: np.ndarray, exception: np.ndarray | None, validity_bit: int | None = None) -> np.ndarray:
    """Reason bits of each native sample (outside / not focused / anomaly / invalid value).

    `exception` is the product's inputDataExceptionMask. Its low byte holds the exception codes (0 = none, 2 = LSAR
    qFSP-H1 sample slip). In products whose layer description says it "also includes the validity mask bits" (CRID
    P05036), bits 8-15 are per-polarisation validity flags, set when the data are fully focused (256 HH, 512 HV):
    they are not anomalies. `validity_bit` is the bit of the polarisation analysed; a cleared bit means partially
    focused or missing data.
    """
    bits = np.zeros(power.shape, dtype="uint16")
    outside = mask == 255
    bits[outside] |= REASONS["outside_acquisition"]
    bits[mask == 0] |= REASONS["not_fully_focused"]
    if exception is not None:
        exc = exception.astype("uint32")
        bits[((exc & 0xFF) != 0) & ~outside] |= REASONS["instrument_anomaly"]
        if validity_bit is not None:
            bits[((exc & validity_bit) == 0) & ~outside] |= REASONS["not_fully_focused"]
    bad = ~(np.isfinite(power) & (power > 0)) & ~outside & (mask != 0)
    bits[bad] |= REASONS["invalid_value"]
    return bits


def block_reduce(a: np.ndarray, k: int, how: str = "sum") -> np.ndarray:
    h, w = a.shape
    if h % k or w % k:
        raise ValueError(f"shape {a.shape} is not a multiple of {k}")
    b = a.reshape(h // k, k, w // k, k)
    return b.sum(axis=(1, 3)) if how == "sum" else b.max(axis=(1, 3))


def aggregate_power(power: np.ndarray, bits: np.ndarray, k: int = 2, min_valid_fraction: float = 0.75):
    """Linear-power mean over the valid native samples of each k x k cell.

    Returns (cell_power float32 [NaN where unusable], cell_bits uint16, n_valid int8).
    Cell bits are 0 when the cell holds at least `min_valid_fraction` valid samples; otherwise they are the union of
    the reasons of its invalid samples, plus `insufficient_subpixel_coverage` when some samples were valid but too few.
    """
    ok = (bits & SAMPLE_BITS) == 0
    p = np.where(ok, power.astype("float64"), 0.0)
    n = block_reduce(ok.astype("int32"), k)
    total = block_reduce(p, k)
    cell_bits = np.zeros(n.shape, dtype="uint16")
    union = np.zeros(n.shape, dtype="uint16")
    for bit in REASONS.values():
        if bit & SAMPLE_BITS:
            union |= np.where(block_reduce(((bits & bit) != 0).astype("int32"), k) > 0, bit, 0).astype("uint16")
    need = int(np.ceil(min_valid_fraction * k * k))
    enough = n >= need
    cell_bits[~enough] = union[~enough]
    cell_bits[(~enough) & (n > 0)] |= REASONS["insufficient_subpixel_coverage"]
    out = np.full(n.shape, np.nan, dtype="float32")
    out[enough] = (total[enough] / n[enough]).astype("float32")
    return out, cell_bits, n.astype("int8")


def mark_noise(power: np.ndarray, bits: np.ndarray, noise_floor: np.ndarray | None, margin: float) -> np.ndarray:
    """Add `near_noise_floor` where the cell power is below margin x noise-equivalent backscatter (NEBS)."""
    out = bits.copy()
    if noise_floor is None:
        return out
    with np.errstate(invalid="ignore"):
        low = np.isfinite(power) & np.isfinite(noise_floor) & (power < margin * noise_floor)
    out[low] |= REASONS["near_noise_floor"]
    return out


def delta_db(before: np.ndarray, after: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """10 log10(after / before) where valid and both positive and finite, NaN elsewhere."""
    ok = valid & np.isfinite(before) & np.isfinite(after) & (before > 0) & (after > 0)
    out = np.full(before.shape, np.nan, dtype="float32")
    with np.errstate(invalid="ignore", divide="ignore"):
        out[ok] = (10.0 * np.log10(after[ok].astype("float64") / before[ok].astype("float64"))).astype("float32")
    return out


def zone_delta_db(before: np.ndarray, after: np.ndarray, valid: np.ndarray, zone: np.ndarray) -> dict:
    """Zone aggregate computed on linear power before the dB conversion, plus descriptive per-cell quantiles."""
    sel = zone & valid & np.isfinite(before) & np.isfinite(after) & (before > 0) & (after > 0)
    n = int(sel.sum())
    if n == 0:
        return {"n": 0, "aggregate_db": None, "median_cell_db": None, "p05_db": None, "p95_db": None}
    agg = 10.0 * np.log10(float(after[sel].astype("float64").mean()) / float(before[sel].astype("float64").mean()))
    cell = 10.0 * np.log10(after[sel].astype("float64") / before[sel].astype("float64"))
    p05, med, p95 = np.quantile(cell, [0.05, 0.5, 0.95])
    return {"n": n, "aggregate_db": float(agg), "median_cell_db": float(med), "p05_db": float(p05), "p95_db": float(p95)}


def expected_speckle_sigma_db(n_looks: float) -> float:
    """Standard deviation in dB of the ratio of two independent fully developed speckle estimates of `n_looks`
    looks each: 10 / ln(10) * sqrt(2 / n_looks) (delta method). An optimistic reference, not a threshold."""
    return float(10.0 / np.log(10.0) * np.sqrt(2.0 / n_looks))
