"""Inventory NISAR products over the Benguerir case and crop the GUNW layers to the study window.

1. CMR search (public): writes cases/benguerir/inventory/<collection>.json (committed, small).
2. GUNW crops (Earthdata credential required, read locally from EARTHDATA_TOKEN, .earthdata_token or netrc):
   writes data/GUNW/<granule>/ (git-ignored). Only the window bytes are transferred.

Run: python scripts/fetch_benguerir_nisar.py [--inventory-only] [--limit N]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pyproj import Transformer  # noqa: E402
from shapely.geometry import shape  # noqa: E402
from shapely.ops import transform, unary_union  # noqa: E402

from nasa_in_mining.access import cmr, nisar_subset  # noqa: E402

CASE = ROOT / "cases" / "benguerir"
EPSG, SNAP, MARGIN_M = 32629, 80.0, 400.0
COLLECTIONS = ["NISAR_L2_GUNW_V1", "NISAR_L2_GUNW_PROVISIONAL_V1", "NISAR_L2_GCOV_V1", "NISAR_L2_GCOV_PROVISIONAL_V1",
               "NISAR_L2_GOFF_V1", "NISAR_L2_GOFF_PROVISIONAL_V1", "NISAR_L3_SME2_PROVISIONAL_V1"]


def window() -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    fc = json.loads((CASE / "zones.geojson").read_text(encoding="utf-8"))
    geom = unary_union([shape(f["geometry"]) for f in fc["features"] if f["id"] in ("study", "control", "panels_outside")])
    fwd = Transformer.from_crs(4326, EPSG, always_xy=True).transform
    xmin, ymin, xmax, ymax = transform(fwd, geom).bounds
    snap = lambda v, f: f(v / SNAP) * SNAP  # noqa: E731
    utm = (snap(xmin - MARGIN_M, math.floor), snap(ymin - MARGIN_M, math.floor),
           snap(xmax + MARGIN_M, math.ceil), snap(ymax + MARGIN_M, math.ceil))
    return utm, geom.bounds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory-only", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    args = ap.parse_args()
    utm, wgs = window()
    inv_dir = CASE / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    searched = datetime.now(timezone.utc).isoformat(timespec="seconds")
    gunw = []
    for coll in COLLECTIONS:
        grans = cmr.search(coll, wgs)
        (inv_dir / f"{coll}.json").write_text(json.dumps(
            {"collection": coll, "searched_utc": searched, "bbox_wgs84": wgs, "n": len(grans),
             "note": "catalogue presence only; download and usability are recorded separately",
             "granules": [g.to_dict() for g in grans]}, indent=1), encoding="utf-8", newline="\n")
        print(f"{coll}: {len(grans)} granules", flush=True)
        if coll.startswith("NISAR_L2_GUNW"):
            gunw += grans
    if args.inventory_only:
        return
    print("crop window EPSG:%d %s" % (EPSG, utm), flush=True)
    log = []
    for g in gunw[: args.limit] if args.limit else gunw:
        try:
            rec = nisar_subset.extract(g.data_url, g.granule_id, args.data, utm, EPSG)
            log.append({"granule_id": g.granule_id, "status": "extracted",
                        "bytes_transferred": rec.get("bytes_transferred")})
            print("ok", g.granule_id, round((rec.get("bytes_transferred") or 0) / 1e6, 1), "MB", flush=True)
        except Exception as exc:  # recorded, never silently skipped
            log.append({"granule_id": g.granule_id, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            print("FAILED", g.granule_id, type(exc).__name__, exc, flush=True)
    (inv_dir / "gunw_extraction_log.json").write_text(json.dumps(
        {"run_utc": searched, "window_utm": utm, "epsg": EPSG, "items": log}, indent=1), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
