"""CLI with lazy scientific imports: help/capabilities need only Python."""
from __future__ import annotations

import argparse
from importlib import metadata
import json
import math
import os
from pathlib import Path
import sys

RECIPES = ("surface-change", "displacement", "timeseries", "flood", "vegetation-loss", "offsets", "soil-moisture")


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    return value


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Standalone NISAR mining processing; no data download is automatic.")
    p.add_argument("--version", action="version", version="nasa-in-mining 0.2.0")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities", help="list the extracted processing capabilities")
    sub.add_parser("doctor", help="report installed runtime dependencies")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data", type=Path)
    common.add_argument("--cache", type=Path)
    common.add_argument("--output", type=Path, help="also write the JSON response to this file")
    modes = common.add_mutually_exclusive_group()
    modes.add_argument("--offline", action="store_true")
    modes.add_argument("--online", action="store_true", help="permit optional DEM/source network access")
    cat = sub.add_parser("catalog", parents=[common], help="index local products marked _DONE")
    cat.add_argument("--level", choices=("GUNW", "GCOV", "GOFF", "SME2"))
    a = sub.add_parser("analyze", parents=[common], help="run an extracted point/circle recipe")
    a.add_argument("--recipe", required=True, choices=RECIPES)
    a.add_argument("--lat", required=True, type=float)
    a.add_argument("--lon", required=True, type=float)
    a.add_argument("--event", help="optional UTC timestamp or calendar date; a date means the whole day")
    roi = sub.add_parser("summarize", parents=[common], help="sample a raster within a supplied WGS84 mining polygon")
    roi.add_argument("--raster", type=Path, required=True)
    roi.add_argument("--roi", type=Path, required=True)
    roi.add_argument("--unit", required=True)
    roi.add_argument("--threshold", type=float)
    roi.add_argument("--absolute", action="store_true")
    run = sub.add_parser("case-run", parents=[common], help="run the polygon mining-case pipeline (precomputed results)")
    run.add_argument("--case", type=Path, required=True, help="case folder holding case_config.json and zones")
    run.add_argument("--out", type=Path, help="output folder (default: <case>/output)")
    sch = sub.add_parser("contract-schema", help="write the MiningCase JSON schema")
    sch.add_argument("--out", type=Path, required=True)
    srv = sub.add_parser("serve", help="serve recorded cases and the web interface (offline capable)")
    srv.add_argument("--cases", type=Path, default=Path("cases"))
    srv.add_argument("--web", type=Path, default=Path("web") / "dist")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8000)
    return p


def main(argv: list[str] | None = None) -> int:
    # JSON is written as UTF-8 even on a Windows console using a legacy code page (e.g. cp1252).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower().replace("-", "") != "utf8":
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    args = _parser().parse_args(argv)
    for option, env in (("data", "MINING_DATA"), ("cache", "MINING_CACHE")):
        if getattr(args, option, None) is not None:
            os.environ[env] = str(getattr(args, option).resolve())
    if getattr(args, "online", False) or getattr(args, "offline", False):
        os.environ["MINING_OFFLINE"] = "0" if args.online else "1"
    exit_code = 0
    try:
        if args.command == "capabilities":
            result = {"project": "nasa-in-mining", "version": "0.2.0", "recipes": RECIPES,
                      "helpers": ["catalog", "raster", "quality", "uncertainty", "corrections", "wavelength",
                                  "decomposition", "exposure", "polygon_statistics"],
                      "limits": ["No ore discovery, grade, production or rupture prediction.",
                                 "Point/circle recipes do not describe a whole mine polygon.",
                                 "Real-site validation and a verified mining boundary are still required."]}
        elif args.command == "doctor":
            versions = {}
            for name in ("numpy", "scipy", "rasterio", "pyproj", "h5py", "matplotlib", "pillow", "requests"):
                try:
                    versions[name] = metadata.version(name)
                except metadata.PackageNotFoundError:
                    versions[name] = None
            result = {"status": "ok" if all(versions.values()) else "missing_dependencies", "versions": versions}
            exit_code = 0 if all(versions.values()) else 1
        elif args.command == "catalog":
            from . import catalog
            result = [p.summary() for p in catalog.refresh() if not args.level or p.level == args.level]
        elif args.command == "analyze":
            from .analysis import analyze_point
            result = analyze_point(args.recipe, args.lat, args.lon, args.event)
            exit_code = 0 if result["status"] == "ok" else 2
        elif args.command == "case-run":
            from .mining import pipeline
            data = args.data or Path(os.environ.get("MINING_DATA", "data"))
            case = pipeline.run(args.case, data, args.out)
            result = {"case_id": case.case_id, "processing_status": case.processing.status,
                      "pairs": len(case.pairs), "pairs_ok": sum(1 for p in case.pairs if p.status == "ok"),
                      "validation": {v.observable: v.level for v in case.validation},
                      "output": str(args.out or args.case / "output")}
            exit_code = 0 if case.processing.status in ("complete", "partial") else 2
        elif args.command == "contract-schema":
            from .mining.contract import MiningCase
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(MiningCase.model_json_schema(), indent=1) + "\n", encoding="utf-8")
            result = {"written": str(args.out)}
        elif args.command == "serve":
            import uvicorn
            from .api import create_app
            uvicorn.run(create_app(args.cases, args.web), host=args.host, port=args.port)
            return 0
        else:
            from .roi import summarize_raster
            result = summarize_raster(args.raster, args.roi, args.unit, args.threshold, args.absolute)
            exit_code = 0 if result["status"] == "ok" else 2
        body = json.dumps(json_safe(result), ensure_ascii=False, allow_nan=False, indent=2)
        if getattr(args, "output", None):
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(body + "\n", encoding="utf-8")
        print(body)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": type(exc).__name__, "message": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1
    return exit_code
