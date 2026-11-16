"""Write boundary.geojson and boundary_review.json for the surface study (run: python scripts/build_boundary_dossier.py)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_in_mining.surface import boundary  # noqa: E402

CASE = ROOT / "cases" / "benguerir-surface-study"
review = boundary.build(CASE / "zones.geojson", CASE / "boundary", ROOT / "data" / "worldcover" / "worldcover.tif",
                        ROOT / "data" / "S2" / "S2B_29SPR_20260828_0_L2A" / "stack.tif",
                        CASE / "boundary" / "boundary_review_input.json")
print(json.dumps({k: review[k] for k in ("state", "review")}, indent=1))
print(json.dumps(review["automated_checks"], indent=1))
