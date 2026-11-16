"""Inventory OPERA RTC-S1 (NASA/JPL product derived from ESA/Copernicus Sentinel-1, C-band) over the Benguerir study.

Public CMR query at execution time, metadata only: nothing is downloaded or analysed. Granules are deduplicated by
(burst id, sensing date, processing version) so that versions and bursts are not counted as acquisitions; the study
and control coverage of each acquisition date is the union of its burst footprints. C-band results are never
subtracted from L-band NISAR values.

Run: python scripts/inventory_opera.py     -> cases/benguerir-surface-study/inventory/OPERA_L2_RTC-S1_V1_dedup.json
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shapely.geometry import Polygon, shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from nasa_in_mining.access import cmr  # noqa: E402

CASE = ROOT / "cases" / "benguerir-surface-study"
NAME = re.compile(r"OPERA_L2_RTC-S1_(T\d+-\d+-IW\d)_(\d{8})T\d{6}Z_\d{8}T\d{6}Z_(S1[ABC])_30_v(\d+\.\d+)")


def poly(g) -> Polygon | None:
    for entry in g.footprint or []:
        ring = entry[0] if isinstance(entry, list) else entry        # CMR: one list of rings per polygon
        v = [float(x) for x in ring.split()]
        pts = [(v[i + 1], v[i]) for i in range(0, len(v), 2)]   # CMR gives lat lon pairs
        return Polygon(pts)
    return None


def main() -> None:
    zones = json.loads((CASE / "zones.geojson").read_text(encoding="utf-8"))
    study = shape(next(f for f in zones["features"] if f["id"] == "study")["geometry"])
    control = shape(next(f for f in zones["features"] if f["id"] == "control")["geometry"])
    bbox = unary_union([study, control]).bounds
    grans, completeness = cmr.search("OPERA_L2_RTC-S1_V1", bbox, temporal="2026-06-01T00:00:00Z,2026-11-16T23:59:59Z")
    seen, versions, parsed = {}, set(), []
    for g in grans:
        m = NAME.search(g.granule_id)
        if not m:
            continue
        burst, day, sat, ver = m.groups()
        versions.add(ver)
        key = (burst, day)
        keep = seen.get(key)
        if keep is None or ver > keep[1]:
            seen[key] = (g, ver, sat)
        parsed.append(burst)
    by_day: dict[str, list] = {}
    for (burst, day), (g, ver, sat) in seen.items():
        by_day.setdefault(day, []).append((burst, g, sat))
    rows = []
    for day, items in sorted(by_day.items()):
        polys = [p for _, g, _ in items if (p := poly(g)) is not None]
        u = unary_union(polys) if polys else None
        rows.append({"date": f"{day[:4]}-{day[4:6]}-{day[6:]}", "n_bursts": len(items), "platforms": sorted({s for _, _, s in items}),
                     "study_covered_fraction": None if u is None else round(float(u.intersection(study).area / study.area), 3),
                     "control_covered_fraction": None if u is None else round(float(u.intersection(control).area / control.area), 3)})
    out = {"collection": "OPERA_L2_RTC-S1_V1", "searched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "bbox_wgs84": bbox, "temporal": "2026-06-01/2026-11-16", "completeness": completeness, "n_granules": len(grans),
           "n_unique_burst_dates": len(seen), "n_acquisition_dates": len(rows), "processing_versions": sorted(versions),
           "dates": rows, "status": "metadata_only",
           "origin": "NASA/JPL OPERA product derived from ESA/Copernicus Sentinel-1 C-band SAR; not a NASA instrument",
           "rule": "deduplicated by (burst, sensing date) keeping the highest processing version; coverage = union of burst footprints; "
                   "C-band is compared with C-band only and never subtracted from L-band NISAR values",
           "note": "footprint coverage does not guarantee valid pixels; no file was downloaded"}
    path = CASE / "inventory" / "OPERA_L2_RTC-S1_V1_dedup.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in ("n_granules", "n_unique_burst_dates", "n_acquisition_dates", "processing_versions")}))


if __name__ == "__main__":
    main()
