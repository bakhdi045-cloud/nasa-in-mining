"""Reproducibly extract selected modules. The source tree is strictly read-only.

Run: python scripts/extract_upstream.py --source ../NASA_SAR [--dry-run]
Local edits to previously extracted modules are protected against overwrites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://github.com/AYmANTwill/NASA_SAR"
FILES = {
    "backend/catalog.py": "catalog.py",
    "backend/raster.py": "raster.py",
    "backend/quality.py": "quality.py",
    "backend/uncertainty.py": "uncertainty.py",
    "backend/palettes.json": "palettes.json",
    "backend/science/exposure.py": "exposure.py",
    **{f"backend/recipes/{name}.py": f"recipes/{name}.py" for name in (
        "__init__", "backscatter", "corrections", "damage", "decompose",
        "displacement", "offsets", "soil_moisture", "timeseries", "wavelength",
    )},
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def adapt(name: str, raw: bytes) -> bytes:
    if not name.endswith(".py"):
        return raw.replace(b"\r\n", b"\n")
    s = raw.decode("utf-8-sig").replace("\r\n", "\n")
    names = "config|catalog|raster|quality|uncertainty|recipes"
    s = re.sub(rf"(?m)^(\s*)from ({names})(\.[\w.]+)? import ",
               r"\1from nasa_in_mining.\2\3 import ", s)
    s = re.sub(r"(?m)^(\s*)import (raster|quality|config)\s*$",
               r"\1from nasa_in_mining import \2", s)
    if name.endswith("recipes/corrections.py"):
        s = s.replace("import numpy as np\n", "import numpy as np\nfrom nasa_in_mining.config import OFFLINE\n", 1)
        s = s.replace('os.environ.get("NISAR_OFFLINE", "0") == "1"', "OFFLINE")
        s = s.replace('os.environ.get("NISAR_OFFLINE")', "OFFLINE")
    if name.endswith("science/exposure.py"):
        s = re.sub(r"(?m)^AUX_DIR = .*\n", "from nasa_in_mining.config import AUX_DIR, OFFLINE\n", s)
        s = s.replace('os.environ.get("NISAR_OFFLINE") == "1"', "OFFLINE")
        s = s.replace('USER_AGENT = "nisar-pulse/1.0 (NASA Space Apps 2026)"',
                      'USER_AGENT = "nasa-in-mining/0.1 (derived from NISAR Pulse)"')
    return ("# Extracted from NISAR Pulse / NASA_SAR; see PROVENANCE.md and UPSTREAM.json.\n" + s).encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    source = args.source.resolve()
    if source == ROOT or source in ROOT.parents or ROOT in source.parents:
        ap.error("source and destination must be separate, non-nested repositories")
    revision = subprocess.check_output(
        ["git", "-c", f"safe.directory={source.as_posix()}", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    manifest_path = ROOT / "UPSTREAM.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    known = {r["destination"]: r["extracted_sha256"] for r in old.get("files", [])}
    records, writes = [], []
    for original, relative in FILES.items():
        path = source / original
        raw = path.read_bytes()
        out = adapt(original, raw)
        destination = f"src/nasa_in_mining/{relative}"
        target = ROOT / destination
        if target.exists() and target.read_bytes() != out:
            if known.get(destination) != sha(target.read_bytes()):
                ap.error(f"local modifications protected: {destination}")
        records.append({"source": original, "source_sha256": sha(raw),
                        "destination": destination, "extracted_sha256": sha(out)})
        writes.append((target, out, path, raw))
    if args.dry_run:
        print(json.dumps({"source_revision": revision, "files": len(records), "writes": False}))
        return 0
    for target, out, _, _ in writes:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(out)
    manifest = {"source_repository": SOURCE_URL, "source_revision": revision,
                "source_license": "No project/backend license found in the inspected source revision.",
                "adaptations": [
                    "Package-qualified imports and normalized extracted text line endings.",
                    "Independent configuration, no hard-coded Moroccan data gap or credentials.",
                    "Offline-by-default external helpers and Windows-compatible auxiliary cache path.",
                    "Exposure helper HTTP User-Agent identifies the new project.",
                ], "files": records}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for _, _, path, original in writes:
        if path.read_bytes() != original:
            raise RuntimeError(f"source changed during extraction: {path}; inspect concurrent work")
    print(f"Extracted {len(records)} files from {revision}; source bytes verified unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
