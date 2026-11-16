"""Read-only audit of the published study; writes only the requested evidence file.

No credentials are read. Optional CMR queries use public catalogue metadata only.
An intact local manifest is not independent verification of the source measurements.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def check_files(records: list[dict], base: Path) -> dict:
    missing, changed = [], []
    for row in records:
        p = base / row["path"]
        if not p.is_file():
            missing.append(row["path"])
        elif digest(p) != row["sha256"]:
            changed.append(row["path"])
    return {"declared": len(records), "missing": missing, "changed": changed,
            "matching": len(records) - len(missing) - len(changed)}


def local_audit() -> dict:
    from nasa_in_mining.mining.contract import MiningCase
    from nasa_in_mining.mining.pipeline import verify_run
    import numpy as np
    import rasterio
    from shapely.geometry import shape
    from shapely.ops import transform
    from pyproj import Transformer

    output = ROOT / "cases/benguerir/output"
    case = json.loads((output / "case.json").read_text(encoding="utf-8"))
    model = MiningCase.model_validate(case)
    refs = git("for-each-ref", "--format=%(refname:short)|%(objectname)", "refs/heads", "refs/remotes").splitlines()
    strict = []
    groups: dict[tuple, list] = defaultdict(list)
    for pair in case["pairs"]:
        for o in pair["optical"]:
            if o["mode"] == "strict" and o["status"] == "ok":
                row = {"pair_id": pair["pair_id"], "before": o["before_item"], "after": o["after_item"],
                       "jaccard": o["jaccard"]["value"], "ratio": o["association_ratio"]["value"],
                       "interval": o["association_ratio"].get("uncertainty"), "table": o["table"]}
                strict.append(row)
                groups[(row["before"], row["after"])].append(row["pair_id"])
    upstream = json.loads((ROOT / "UPSTREAM.json").read_text(encoding="utf-8"))
    upstream_checks = check_files([{"path": r["destination"], "sha256": r["extracted_sha256"]}
                                   for r in upstream["files"]], ROOT)
    zonefc = json.loads((ROOT / "cases/benguerir/zones.geojson").read_text(encoding="utf-8"))
    fwd = Transformer.from_crs(4326, 32629, always_xy=True).transform
    geometry = [{"id": f.get("id") or f["properties"].get("id"),
                 "valid": shape(f["geometry"]).is_valid,
                 "area_km2": transform(fwd, shape(f["geometry"])).area / 1e6}
                for f in zonefc["features"]]
    raster_checks = []
    for ex in case["exports"]:
        if ex["format"] == "geotiff":
            with rasterio.open(output / ex["path"]) as src:
                values = src.read(1)
                observed = src.read_masks(1).astype(bool) & np.isfinite(values)
                finite_values = values[observed]
                raster_checks.append({"path": ex["path"], "crs": str(src.crs), "shape": list(src.shape),
                                      "spacing": list(src.res),
                                      "nodata": "NaN" if src.nodata is not None and np.isnan(src.nodata) else src.nodata,
                                      "valid_pixels": int(observed.sum()),
                                      "range": [float(finite_values.min()), float(finite_values.max())] if finite_values.size else None,
                                      "tags": src.tags()})
    inventories = []
    for path in sorted((ROOT / "cases/benguerir/inventory").glob("NISAR*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        inventories.append({k: d.get(k) for k in ("collection", "searched_utc", "bbox_wgs84", "n", "completeness")})
    main = case["method"]["main_profile"]
    summaries = []
    for days in (12, 24):
        pairs = [p for p in case["pairs"] if p["status"] == "ok" and p["span_days"] == days]
        profiles = [next(x for x in p["profiles"] if x["id"] == main) for p in pairs]
        ratios = [p["ratio_to_evaluation_rate"]["value"] for p in profiles]
        ci_above = sum(((p["ratio_to_evaluation_rate"].get("uncertainty") or {}).get("low") or 0) > 1 for p in profiles)
        sensitivity = []
        for q in (0.005, 0.01, 0.05):
            pr = [x for p in pairs for x in p["profiles"] if x["id"] == f"ring@{q}"]
            rr = [x["ratio_to_evaluation_rate"]["value"] for x in pr]
            sensitivity.append({"quantile": q, "n": len(rr), "n_above_1": sum(r > 1 for r in rr),
                                "median_ratio": float(np.median(rr)) if rr else None})
        summaries.append({"span_days": days, "n": len(pairs), "ratio_min": min(ratios, default=None),
                          "ratio_median": float(np.median(ratios)) if ratios else None,
                          "ratio_max": max(ratios, default=None), "interval_above_1": ci_above,
                          "threshold_sensitivity": sensitivity})
    return {"audited_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_head": git("rev-parse", "HEAD"), "git_branch": git("branch", "--show-current"),
            "refs": refs, "tracked_files": len(git("ls-files").splitlines()),
            "scope": "OCP Benguerir only; confirmed by user on 2026-11-16",
            "case_id": case["case_id"], "published_run": case["run_id"],
            "published_code": case["manifest"]["code_commit"],
            "case_json_sha256": digest(output / "case.json"),
            "contract_and_output_problems": verify_run(output, model),
            "input_integrity": check_files(case["manifest"]["inputs"], ROOT),
            "input_roles": dict(Counter(x["role"] for x in case["manifest"]["inputs"])),
            "output_integrity": check_files(case["manifest"]["outputs"], output),
            "upstream_integrity": upstream_checks,
            "pair_status": dict(Counter(p["status"] for p in case["pairs"])),
            "maturities": dict(Counter(p["maturity"] for p in case["acquisitions"])),
            "pair_summaries": summaries, "strict_optical_comparisons": strict,
            "distinct_optical_pairs": [{"before": a, "after": b, "radar_comparisons": ps}
                                       for (a, b), ps in groups.items()],
            "validation": case["validation"], "geometry": geometry,
            "optical_scenes_read": len(case["optical_scenes"]),
            "optical_scenes_usable": sum(s["usable"] for s in case["optical_scenes"]),
            "published_layers": [{"id": x["id"], "kind": x["kind"], "url": x["url"]} for x in case["layers"]],
            "raster_exports": raster_checks, "recorded_inventories": inventories,
            "limitations": ["Hashes establish local integrity, not independent source authenticity or field validation.",
                            "Recorded inventories are dated snapshots, not live availability.",
                            "No new scientific result is published by this audit."]}


def live_catalogue() -> dict:
    from nasa_in_mining.access.cmr import search
    inv = json.loads((ROOT / "cases/benguerir/inventory/NISAR_L2_GUNW_PROVISIONAL_V1.json").read_text(encoding="utf-8"))
    bbox = tuple(inv["bbox_wgs84"])
    collections = ["NISAR_L2_GUNW_PROVISIONAL_V1", "NISAR_L2_GUNW_V1",
                   "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_GCOV_V1", "OPERA_L2_RTC-S1_V1"]
    temporal = "2026-06-01T00:00:00Z,2026-11-16T23:59:59Z"

    def query(name):
        try:
            granules, complete = search(name, bbox, temporal=temporal)
            return {"collection": name, "status": "ok", "count": len(granules), "completeness": complete,
                    "granules": [g.to_dict() for g in granules] if name.startswith("NISAR") else
                                [g.to_dict() for g in granules[:3]],
                    "note": "Metadata only; footprint intersection is not pixel-level usable coverage. "
                            "OPERA sample is limited to three entries; data_url may be null because the NISAR "
                            "catalogue adapter selects HDF5 links, not OPERA GeoTIFFs."}
        except Exception as exc:
            return {"collection": name, "status": "error", "error_type": type(exc).__name__, "error": str(exc)}
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(query, collections))
    return {"queried_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "endpoint": "https://cmr.earthdata.nasa.gov/search/granules.json", "bbox_wgs84": bbox,
            "temporal": temporal, "results": results}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalogue", action="store_true", help="query public CMR metadata instead of local files")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = live_catalogue() if args.catalogue else local_audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Evidence written: {args.out}")
    if args.catalogue:
        print(json.dumps([{k: r.get(k) for k in ("collection", "status", "count", "error")}
                          for r in data["results"]]))
        if any(r["status"] != "ok" for r in data["results"]):
            raise SystemExit(1)
    else:
        print(json.dumps({k: data[k] for k in ("input_integrity", "output_integrity", "upstream_integrity", "pair_status")}))
        if data["contract_and_output_problems"] or any(data[k]["missing"] or data[k]["changed"]
                for k in ("input_integrity", "output_integrity", "upstream_integrity")):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
