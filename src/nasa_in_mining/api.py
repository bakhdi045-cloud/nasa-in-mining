"""Light read-only API over precomputed mining cases (new module).

GET /api/health                       -> service status and contract version
GET /api/cases                        -> list of available cases (id, site, status, validation)
GET /api/cases/{case_id}              -> the validated MiningCase JSON
GET /api/cases/{case_id}/files/{path} -> a layer, export or zones file of that case (path confined to the case)
The web interface is served from MINING_WEB_DIST when it exists. No computation is triggered by a request and no
external resource is required: the API works offline on recorded results.
Errors are JSON: {"error": <code>, "message": <text>}.
"""
from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .mining.contract import SCHEMA_VERSION, MiningCase


mimetypes.add_type("text/javascript", ".mjs")   # module workers need a JavaScript MIME type (Windows registry may lack it)
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/geo+json", ".geojson")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _case_dirs(root: Path) -> dict[str, Path]:
    out = {}
    for case_json in sorted(root.glob("*/output/case.json")):
        try:
            cid = json.loads(case_json.read_text(encoding="utf-8")).get("case_id")
        except (OSError, json.JSONDecodeError):
            continue
        if cid:
            out[cid] = case_json.parent
    return out


def create_app(cases_root: str | Path | None = None, web_dist: str | Path | None = None) -> FastAPI:
    root = Path(cases_root or os.environ.get("MINING_CASES", Path.cwd() / "cases")).resolve()
    dist = Path(web_dist or os.environ.get("MINING_WEB_DIST", Path.cwd() / "web" / "dist")).resolve()
    app = FastAPI(title="NASA in Mining API", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(GZipMiddleware, minimum_size=2048)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content={"error": exc.code, "message": exc.message})

    def load(case_id: str) -> tuple[MiningCase, Path]:
        dirs = _case_dirs(root)
        if case_id not in dirs:
            raise ApiError(404, "case_not_found", f"no recorded case '{case_id}' under {root.name}/")
        try:
            data = json.loads((dirs[case_id] / "case.json").read_text(encoding="utf-8"))
            return MiningCase.model_validate(data), dirs[case_id]
        except json.JSONDecodeError as exc:
            raise ApiError(500, "case_unreadable", f"case.json is not valid JSON: {exc.msg}") from exc
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(x) for x in first["loc"])
            raise ApiError(500, "contract_violation", f"case.json does not satisfy the MiningCase contract at "
                                                      f"'{where}': {first['msg']}") from exc

    @app.get("/api/health")
    def health():
        return {"status": "ok", "schema_version": SCHEMA_VERSION, "cases": sorted(_case_dirs(root)),
                "web": dist.exists()}

    @app.get("/api/cases")
    def cases():
        out = []
        for cid in sorted(_case_dirs(root)):
            try:
                case, _ = load(cid)
            except ApiError as exc:
                out.append({"case_id": cid, "error": exc.code, "message": exc.message})
                continue
            out.append({"case_id": case.case_id, "site": case.site.name, "data_nature": case.data_nature,
                        "processing_status": case.processing.status,
                        "validation": {v.observable: v.level for v in case.validation},
                        "n_pairs": len(case.pairs)})
        return out

    @app.get("/api/cases/{case_id}")
    def case(case_id: str):
        c, _ = load(case_id)
        return JSONResponse(json.loads(c.model_dump_json()))

    @app.api_route("/api/cases/{case_id}/files/{path:path}", methods=["GET", "HEAD"])
    def case_file(case_id: str, path: str):
        _, folder = load(case_id)
        target = (folder / path).resolve()
        if folder not in target.parents or not target.is_file():
            raise ApiError(404, "file_not_found", f"no file '{path}' in case '{case_id}'")
        return FileResponse(target)

    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets") if (dist / "assets").exists() else None

        @app.get("/{full:path}")
        def spa(full: str):
            if full.startswith("api/"):
                raise ApiError(404, "not_found", f"unknown API route '/{full}'")
            candidate = (dist / full).resolve()
            if full and dist in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
