"""Local, credential-free configuration, independent of the NASA_SAR checkout.

MINING_* settings take precedence. NISAR_* aliases keep existing data workflows
usable. Environment variables must be set before importing processing modules.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


def setting(name: str, default: str) -> str:
    return os.environ.get(f"MINING_{name}", os.environ.get(f"NISAR_{name}", default))


DATA_DIR = Path(setting("DATA", str(Path.cwd() / "data"))).expanduser().resolve()
CACHE_DIR = Path(setting("CACHE", str(Path.cwd() / ".cache" / "nasa-in-mining"))).expanduser().resolve()
# 'aux' is a reserved Windows device name, so use 'auxiliary'.
AUX_DIR = Path(setting("AUX", str(DATA_DIR / "auxiliary"))).expanduser().resolve()
OFFLINE = setting("OFFLINE", "1") == "1"

WAVELENGTH_M = 0.2384  # Fallback only; recipes/wavelength.py reads each product's frequency.
LOS_SIGN = float(setting("LOS_SIGN", "1"))
if LOS_SIGN not in (-1.0, 1.0):
    raise ValueError("MINING_LOS_SIGN must be +1 or -1")
LOS_SIGN_VERIFIED = setting("LOS_SIGN_VERIFIED", "0") == "1"
SIGN_BASIS = (
    "documented GUNW convention: positive phase = away from sensor; "
    "displacement = -lambda/(4*pi)*phase; positive LOS = toward satellite"
    if LOS_SIGN > 0 else "opposite of the documented GUNW convention; MINING_LOS_SIGN=-1"
)
COHERENCE_MIN = 0.3
POINT_RADIUS_M = 1000
MIN_RATE_DAYS = 365
SM_UNCERTAINTY = 0.028
CRID_MATURITY = {"P05023": "provisional", "P05036": "validated"}

# No Morocco-specific gap is silently imposed on a new mining location.
DATA_GAPS = json.loads(setting("DATA_GAPS", "[]"))
if not isinstance(DATA_GAPS, list):
    raise ValueError("MINING_DATA_GAPS must be a JSON list of [YYYYMMDD, YYYYMMDD] pairs")
for gap in DATA_GAPS:
    if not isinstance(gap, list) or len(gap) != 2:
        raise ValueError("each data gap must be a pair of dates")
    for stamp in gap:
        datetime.strptime(stamp, "%Y%m%d")
    if gap[0] >= gap[1]:
        raise ValueError("a data gap must end after it starts")
