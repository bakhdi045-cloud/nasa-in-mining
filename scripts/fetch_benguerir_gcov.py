"""Inventory NISAR GCOV over Benguerir (public CMR query, run at execution time) and crop gamma-0 layers.

1. CMR search (public, paginated): cases/benguerir-surface-study/inventory/<collection>.json (committed, small).
2. GCOV crops (Earthdata credential read locally by access.remote; never printed): data/GCOV/<granule>/.

A batch is a homogeneous set: same collection, CRID, track, frame and direction. Batches never mix.
    python scripts/fetch_benguerir_gcov.py --batch pilot_0816_0828          # the two granules of the integration pilot
    python scripts/fetch_benguerir_gcov.py --batch p05023_T044_A_F018       # the whole ascending P05023 series
    python scripts/fetch_benguerir_gcov.py --batch p05023_T023_D_F072       # the whole descending P05023 series
    python scripts/fetch_benguerir_gcov.py --batch p05036_T023_D_F072       # separate pilot (validated collection)
    python scripts/fetch_benguerir_gcov.py --inventory-only
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pyproj import Transformer  # noqa: E402
from shapely.geometry import shape  # noqa: E402
from shapely.ops import transform, unary_union  # noqa: E402

from nasa_in_mining.access import cmr, gcov_subset  # noqa: E402

CASE = ROOT / "cases" / "benguerir-surface-study"
V2_ZONES = ROOT / "cases" / "benguerir" / "zones.geojson"
EPSG, SNAP, MARGIN_M = 32629, 80.0, 400.0
COLLECTIONS = ["NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_GCOV_V1"]
NAME = re.compile(r"GCOV_(\d+)_(\d+)_([AD])_(\d+)_\w+_\w+_[AB]_(\d{8})T\d{6}_\d{8}T\d{6}_(P\d+)_")
BATCHES = {  # name: (collection, crid, track, direction, frame, dates or None)
    "pilot_0816_0828": ("NISAR_L2_GCOV_PROVISIONAL_V1", "P05023", 44, "A", 18, ("20260816", "20260828")),
    "p05023_T044_A_F018": ("NISAR_L2_GCOV_PROVISIONAL_V1", "P05023", 44, "A", 18, None),
    "p05023_T023_D_F072": ("NISAR_L2_GCOV_PROVISIONAL_V1", "P05023", 23, "D", 72, None),
    "p05036_T023_D_F072": ("NISAR_L2_GCOV_V1", "P05036", 23, "D", 72, None),
}


def window():
    fc = json.loads(V2_ZONES.read_text(encoding="utf-8"))
    geom = unary_union([shape(f["geometry"]) for f in fc["features"] if f["id"] in ("study", "control", "panels_outside")])
    fwd = Transformer.from_crs(4326, EPSG, always_xy=True).transform
    xmin, ymin, xmax, ymax = transform(fwd, geom).bounds
    snap = lambda v, f: f(v / SNAP) * SNAP  # noqa: E731
    return ((snap(xmin - MARGIN_M, math.floor), snap(ymin - MARGIN_M, math.floor),
             snap(xmax + MARGIN_M, math.ceil), snap(ymax + MARGIN_M, math.ceil)), geom.bounds)


def parse(granule_id: str):
    m = NAME.search(granule_id)
    return None if not m else {"cycle": int(m[1]), "track": int(m[2]), "direction": m[3], "frame": int(m[4]),
                               "date": m[5], "crid": m[6]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", choices=sorted(BATCHES))
    ap.add_argument("--inventory-only", action="store_true")
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    args = ap.parse_args()
    utm, wgs = window()
    inv = CASE / "inventory"
    inv.mkdir(parents=True, exist_ok=True)
    searched = datetime.now(timezone.utc).isoformat(timespec="seconds")
    found = {}
    for coll in COLLECTIONS:
        grans, completeness = cmr.search(coll, wgs, temporal="2026-06-01T00:00:00Z,2026-11-16T23:59:59Z")
        found[coll] = grans
        (inv / f"{coll}.json").write_text(json.dumps(
            {"collection": coll, "searched_utc": searched, "bbox_wgs84": wgs, "temporal": "2026-06-01/2026-11-16",
             "n": len(grans), "completeness": completeness,
             "note": "catalogue presence only; download, extraction and usable pixels are recorded separately",
             "granules": [g.to_dict() for g in grans]}, indent=1), encoding="utf-8", newline="\n")
        print(f"{coll}: {len(grans)} granules (complete={completeness['complete']})", flush=True)
    if args.inventory_only or not args.batch:
        return
    coll, crid, track, direction, frame, dates = BATCHES[args.batch]
    sel = []
    for g in found[coll]:
        p = parse(g.granule_id)
        if p and (p["crid"], p["track"], p["direction"], p["frame"]) == (crid, track, direction, frame) \
                and (dates is None or p["date"] in dates):
            sel.append(g)
    print(f"batch {args.batch}: {len(sel)} granules; crop window EPSG:{EPSG} {utm}", flush=True)
    log = []
    for g in sel:
        try:
            rec = gcov_subset.extract(g.data_url, g.granule_id, args.data, utm, EPSG)
            log.append({"granule_id": g.granule_id, "status": "extracted", "bytes_transferred": rec.get("bytes_transferred")})
            print("ok", g.granule_id, round((rec.get("bytes_transferred") or 0) / 1e6, 1), "MB", flush=True)
        except Exception as exc:   # recorded, never silently skipped
            log.append({"granule_id": g.granule_id, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            print("FAILED", g.granule_id, type(exc).__name__, exc, flush=True)
    (inv / f"gcov_extraction_log_{args.batch}.json").write_text(json.dumps(
        {"run_utc": searched, "batch": args.batch, "window_utm": utm, "epsg": EPSG, "items": log}, indent=1),
        encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
