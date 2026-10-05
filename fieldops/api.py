import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .agent import diagnose, execute
from .fixtures import SCENARIOS, make_fixture
from .models import Approval, CreateIncident
from .report import delivery_bundle
from .sandbox import sandbox_router
from .store import Conflict, Store, digest


def public_item(item: dict) -> dict:
    # Internal fault injector settings are not part of the agent/UI observation surface.
    result = {key: value for key, value in item.items() if key != "upstream"}
    result["plan_hash"] = digest(item["plan"]) if item["plan"] else None
    return result


def create_app(store: Store | None = None, serve_ui: bool = True) -> FastAPI:
    store = store or Store(os.getenv("FIELDOPS_DB", "data/fieldops.db"))
    app = FastAPI(title="FieldOps Agent", version="0.1.0")
    app.state.store = store
    app.include_router(sandbox_router(store))

    @app.exception_handler(KeyError)
    async def missing(_, __):
        return Response('"工单不存在"', status_code=404, media_type="application/json")

    @app.exception_handler(Conflict)
    async def conflict(_, exc):
        return Response('"' + str(exc) + '"', status_code=409, media_type="application/json")

    @app.get("/api/scenarios")
    def scenarios():
        return [{"id": key, "title": value[0], "ticket": value[1]} for key, value in SCENARIOS.items()]

    @app.get("/api/meta")
    def meta():
        return {
            "llm_configured": all(
                os.getenv(key)
                for key in ("FIELDOPS_MODEL_BASE_URL", "FIELDOPS_MODEL_API_KEY", "FIELDOPS_MODEL_NAME")
            ),
            "scope": "synthetic-local-http-sandbox",
            "version": "0.1.0",
        }

    @app.post("/api/incidents", status_code=201)
    def create(request: CreateIncident):
        try:
            fixture = make_fixture(request.scenario, request.seed)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if request.ticket:
            fixture["ticket"] = request.ticket
        return public_item(store.create(fixture, request.mode))

    @app.get("/api/incidents")
    def list_incidents():
        return [public_item(item) for item in store.list()]

    @app.get("/api/incidents/{incident_id}")
    def get(incident_id: str):
        return public_item(store.get(incident_id))

    @app.post("/api/incidents/{incident_id}/diagnose")
    async def run_diagnosis(incident_id: str):
        try:
            return public_item(await diagnose(app, store, incident_id))
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(422, "诊断未完成：检查模型配置、工具参数或响应格式；未修改部署") from exc

    @app.post("/api/incidents/{incident_id}/approve")
    def approve(incident_id: str, request: Approval):
        return public_item(store.approve(incident_id, request.plan_hash, request.revision))

    @app.post("/api/incidents/{incident_id}/execute")
    async def run_repair(incident_id: str):
        return public_item(await execute(store, incident_id))

    @app.get("/api/incidents/{incident_id}/bundle")
    def bundle(incident_id: str):
        return Response(
            delivery_bundle(store.get(incident_id)),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="fieldops-{incident_id}.zip"'},
        )

    @app.get("/api/benchmark")
    def benchmark():
        result = Path(__file__).resolve().parent.parent / "evaluation/results/summary.json"
        if not result.exists():
            return {"status": "not_run"}
        return FileResponse(result, media_type="application/json")

    dist = Path(__file__).resolve().parent.parent / "web/dist"
    if serve_ui and (dist / "assets").is_dir() and (dist / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

    return app
