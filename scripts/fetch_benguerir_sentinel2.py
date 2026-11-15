"""Read Sentinel-2 L2A windows (tile 29SPR) over the Benguerir study window. Public data, no credential.

Writes data/S2/<item>/stack.tif + provenance.json (git-ignored) and cases/benguerir/inventory/sentinel2.json.
Run: python scripts/fetch_benguerir_sentinel2.py
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_benguerir_nisar import EPSG, window  # noqa: E402
from nasa_in_mining.access import sentinel2  # noqa: E402

# v2: no tile cloud filter. Every scene of the period is read; clear coverage is measured later in each zone.
START, END, MAX_CLOUD, TILE = "2026-06-01T00:00:00Z", "2026-11-15T00:00:00Z", None, "29SPR"


def main() -> None:
    utm, wgs = window()
    items, completeness = sentinel2.search(wgs, START, END, MAX_CLOUD, TILE)
    print("search:", completeness, flush=True)
    from nasa_in_mining.access import worldcover
    wc = worldcover.read(utm, EPSG, ROOT / "data" / "worldcover")
    print("worldcover:", wc["class_counts"], flush=True)
    log = []
    for it in items:
        try:
            rec = sentinel2.read_item(it, utm, EPSG, ROOT / "data" / "S2")
            log.append({"item_id": it["id"], "status": "read", "datetime": rec["datetime"],
                        "scl_window_counts": rec["scl_window_counts"],
                        "processing_baseline": rec["processing_baseline"],
                        "cloud_cover_pct_tile": rec["cloud_cover_pct_tile"]})
            print("ok", it["id"], flush=True)
        except Exception as exc:
            log.append({"item_id": it["id"], "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            print("FAILED", it["id"], exc, flush=True)
    out = ROOT / "cases" / "benguerir" / "inventory" / "sentinel2.json"
    out.write_text(json.dumps({"catalogue": sentinel2.STAC, "collection": "sentinel-2-l2a", "tile": TILE,
                               "searched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "period": [START, END], "max_cloud_pct_tile": MAX_CLOUD, "window_utm": utm,
                               "completeness": completeness, "dn_convention": sentinel2.DN_CONVENTION,
                               "items": log}, indent=1), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
