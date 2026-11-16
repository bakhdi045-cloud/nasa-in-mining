"""Light read-only API over recorded mining cases (v2).

GET /api/health                                   -> service status and contract version
GET /api/cases                                    -> cases with their published run and other verified local runs
GET /api/cases/{case_id}[?run=<run_id>]           -> the validated MiningCase JSON (published run by default)
GET|HEAD /api/cases/{case_id}/files/{path}[?run=] -> a layer, export or zones file of that run (path confined)
GET /api/studies, /api/studies/{study_id}[?run=], /api/studies/{study_id}/files/{path} -> the surface-change study (contract 3.0)
A run is listed only if its folder holds a VERIFIED marker written by the pipeline after verification. The web
interface is served from MINING_WEB_DIST when it exists. No computation is triggered and no external resource is
needed: the API works offline on recorded results. Errors are JSON: {"error": <code>, "message": <text>}.
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
from .mining.evidence import with_evidence
from .surface.contract import STUDY_SCHEMA_VERSION, SurfaceStudy

mimetypes.add_type("text/javascript", ".mjs")   # module workers need a JavaScript MIME type
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/geo+json", ".geojson")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _read_id(folder: Path, name: str = "case.json", key: str = "case_id") -> tuple[str | None, str | None]:
    try:
        d = json.loads((folder / name).read_text(encoding="utf-8"))
        return d.get(key), d.get("run_id")
    except (OSError, json.JSONDecodeError):
        return None, None


def index(root: Path, name: str = "case.json", key: str = "case_id") -> dict[str, dict]:
    """{case_id: {"published": run_id, "runs": {run_id: folder}}}; `name`/`key` select cases (case.json) or studies."""
    out: dict[str, dict] = {}
    for case_dir in sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []:
        pub = case_dir / "output"
        if (pub / name).exists():
            cid, rid = _read_id(pub, name, key)
            if cid:
                e = out.setdefault(cid, {"published": None, "runs": {}})
                e["published"] = rid or "published"
                e["runs"][e["published"]] = pub
        for run in sorted((case_dir / "runs").glob("*")) if (case_dir / "runs").exists() else []:
            if (run / "VERIFIED").exists() and (run / name).exists():
                cid, rid = _read_id(run, name, key)
                if cid and rid:
                    out.setdefault(cid, {"published": None, "runs": {}})["runs"].setdefault(rid, run)
    return out


def create_app(cases_root: str | Path | None = None, web_dist: str | Path | None = None) -> FastAPI:
    root = Path(cases_root or os.environ.get("MINING_CASES", Path.cwd() / "cases")).resolve()
    dist = Path(web_dist or os.environ.get("MINING_WEB_DIST", Path.cwd() / "web" / "dist")).resolve()
    app = FastAPI(title="NASA in Mining API", version="0.3.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(GZipMiddleware, minimum_size=2048)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content={"error": exc.code, "message": exc.message})

    def folder(case_id: str, run: str | None) -> Path:
        idx = index(root)
        if case_id not in idx:
            raise ApiError(404, "case_not_found", f"no recorded case '{case_id}' under {root.name}/")
        rid = run or idx[case_id]["published"]
        if rid not in idx[case_id]["runs"]:
            raise ApiError(404, "run_not_found", f"no verified run '{run}' for case '{case_id}'")
        return idx[case_id]["runs"][rid]

    def load(case_id: str, run: str | None) -> MiningCase:
        f = folder(case_id, run)
        try:
            return with_evidence(MiningCase.model_validate(json.loads((f / "case.json").read_text(encoding="utf-8"))))
        except json.JSONDecodeError as exc:
            raise ApiError(500, "case_unreadable", f"case.json is not valid JSON: {exc.msg}") from exc
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(x) for x in first["loc"])
            raise ApiError(500, "contract_violation", f"case.json does not satisfy the MiningCase contract "
                                                      f"{SCHEMA_VERSION} at '{where}': {first['msg']}") from exc

    def study_folder(study_id: str, run: str | None) -> Path:
        idx = index(root, "study.json", "study_id")
        if study_id not in idx:
            raise ApiError(404, "study_not_found", f"no recorded study '{study_id}' under {root.name}/")
        rid = run or idx[study_id]["published"]
        if rid not in idx[study_id]["runs"]:
            raise ApiError(404, "run_not_found", f"no verified run '{run}' for study '{study_id}'")
        return idx[study_id]["runs"][rid]

    def load_study(study_id: str, run: str | None) -> SurfaceStudy:
        f = study_folder(study_id, run)
        try:
            return SurfaceStudy.model_validate(json.loads((f / "study.json").read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise ApiError(500, "study_unreadable", f"study.json is not valid JSON: {exc.msg}") from exc
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(x) for x in first["loc"])
            raise ApiError(500, "contract_violation", f"study.json does not satisfy the SurfaceStudy contract "
                                                      f"{STUDY_SCHEMA_VERSION} at '{where}': {first['msg']}") from exc

    @app.get("/api/health")
    def health():
        return {"status": "ok", "schema_version": SCHEMA_VERSION, "study_schema_version": STUDY_SCHEMA_VERSION,
                "cases": sorted(index(root)), "studies": sorted(index(root, "study.json", "study_id")), "web": dist.exists()}

    @app.get("/api/studies")
    def studies():
        out = []
        for sid, e in sorted(index(root, "study.json", "study_id").items()):
            item = {"study_id": sid, "published_run": e["published"], "runs": sorted(e["runs"], reverse=True)}
            try:
                st = load_study(sid, None)
                item.update(site=st.site.name, data_nature=st.data_nature, processing_status=st.processing.status,
                            boundary_state=st.boundary.state, reference_status=st.references.status,
                            n_windows=len(st.windows))
            except ApiError as exc:
                item.update(error=exc.code, message=exc.message)
            out.append(item)
        return out

    @app.get("/api/studies/{study_id}")
    def study(study_id: str, run: str | None = None):
        return JSONResponse(json.loads(load_study(study_id, run).model_dump_json()))

    @app.api_route("/api/studies/{study_id}/files/{path:path}", methods=["GET", "HEAD"])
    def study_file(study_id: str, path: str, run: str | None = None):
        base = study_folder(study_id, run).resolve()
        target = (base / path).resolve()
        if base not in target.parents or not target.is_file():
            raise ApiError(404, "file_not_found", f"no file '{path}' in study '{study_id}'")
        return FileResponse(target)

    @app.get("/api/cases")
    def cases():
        out = []
        for cid, e in sorted(index(root).items()):
            item = {"case_id": cid, "published_run": e["published"], "runs": sorted(e["runs"], reverse=True)}
            try:
                c = load(cid, None)
                item.update(site=c.site.name, data_nature=c.data_nature, processing_status=c.processing.status,
                            validation={v.observable: v.level for v in c.validation}, n_pairs=len(c.pairs))
            except ApiError as exc:
                item.update(error=exc.code, message=exc.message)
            out.append(item)
        return out

    @app.get("/api/cases/{case_id}")
    def case(case_id: str, run: str | None = None):
        return JSONResponse(json.loads(load(case_id, run).model_dump_json()))

    @app.api_route("/api/cases/{case_id}/files/{path:path}", methods=["GET", "HEAD"])
    def case_file(case_id: str, path: str, run: str | None = None):
        base = folder(case_id, run).resolve()
        target = (base / path).resolve()
        if base not in target.parents or not target.is_file():
            raise ApiError(404, "file_not_found", f"no file '{path}' in case '{case_id}'")
        return FileResponse(target)

    if dist.exists():
        if (dist / "assets").exists():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full:path}")
        def spa(full: str):
            if full.startswith("api/"):
                raise ApiError(404, "not_found", f"unknown API route '/{full}'")
            candidate = (dist / full).resolve()
            if full and dist in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})   # always pick up a rebuilt interface

    return app


app = create_app()
