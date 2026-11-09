"""Local browser workspace. Secrets stay on the server; runs use the real n8n webhook."""

import asyncio
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from heatbrief.api import Review
from heatbrief.assistant import CATALOG, ChatInput, assistant_mode, reply
from heatbrief.errors import HeatBriefError
from heatbrief.models import BriefingRequest
from heatbrief.pdf_report import make_pdf
from heatbrief.store import Store
from heatbrief.workspace_jobs import JobStore

ROOT = Path(__file__).resolve().parents[2]


def project_dir():
    return Path(os.getenv("HEATBRIEF_PROJECT_DIR", str(ROOT)))


def data_dir():
    path = Path(os.getenv("HEATBRIEF_DATA_DIR", "data"))
    return path if path.is_absolute() else project_dir() / path


def local_config():
    path = project_dir() / ".automation/local-config.json"
    if not path.exists():
        raise HeatBriefError("automation_unavailable", "Start the local automation first", 503)
    return json.loads(path.read_text(encoding="utf-8"))


def history_summary(result):
    request = result["request"]
    return {
        "request_id": result["request_id"],
        "question": request["question"],
        "client_name": request["client_name"],
        "date": request["date"],
        "time": request["time"],
        "timezone": request["timezone"],
        "sites": len(request["locations"]),
        "status": result["status"],
        "lowest_c": result["comparison"]["lowest_c"],
        "mock": result["comparison"]["mock"],
    }


def execution_record(request_id, workflow_id):
    path = project_dir() / ".automation/state/.n8n/database.sqlite"
    if not path.exists():
        return None
    try:
        db = sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True, timeout=1)
        try:
            row = db.execute(
                "SELECT e.id,e.status FROM execution_entity e JOIN execution_data d "
                "ON e.id=d.executionId WHERE e.workflowId=? AND instr(d.data,?)>0 "
                "ORDER BY e.id DESC LIMIT 1",
                (workflow_id, request_id),
            ).fetchone()
        finally:
            db.close()
        return {"id": str(row[0]), "status": row[1]} if row else None
    except sqlite3.Error:
        return None


async def execute_run(request, app):
    jobs = JobStore(data_dir())
    started = time.monotonic()
    try:
        config = local_config()
        jobs.update_job(request.request_id, state="running", event="Processing in n8n")
        async with httpx.AsyncClient(timeout=70, trust_env=False) as client:
            response = await client.post(
                "http://localhost:5678/webhook/heatbrief",
                headers={"X-HeatBrief-Webhook-Key": config["webhook_key"]},
                json=request.model_dump(mode="json"),
            )
        if response.status_code >= 400:
            try:
                error = response.json()
            except ValueError:
                error = {}
            raise HeatBriefError(
                error.get("error", "automation_error"),
                error.get("message", "The n8n workflow did not complete"),
                response.status_code,
            )
        body = response.json()
        saved = Store(data_dir()).get(request.request_id)
        if (
            body.get("request_id") != request.request_id
            or body.get("report_markdown") != saved["report_markdown"]
        ):
            raise HeatBriefError(
                "evidence_mismatch", "Workflow evidence does not match the saved report", 502
            )
        saved["replayed"] = body.get("replayed", False)
        jobs.update_job(request.request_id, event="Report and follow-up saved")
        execution = None
        for _ in range(12):
            execution = execution_record(request.request_id, config["workflow_id"])
            if execution and execution["status"] == "success":
                break
            await asyncio.sleep(0.2)
        jobs.update_job(
            request.request_id,
            state="completed",
            event="Review already recorded" if saved.get("review") else "Ready for human review",
            result=saved,
            execution_id=execution["id"] if execution else None,
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )
    except asyncio.CancelledError:
        jobs.update_job(
            request.request_id,
            state="failed",
            event="Run interrupted",
            error={
                "error": "interrupted",
                "message": "This run was interrupted. Retry the request.",
            },
        )
        raise
    except Exception as exc:
        if isinstance(exc, HeatBriefError):
            error = {"error": exc.code, "message": str(exc)}
        else:
            error = {
                "error": "automation_unavailable",
                "message": "Cannot complete the workflow. Check that local automation is running.",
            }
        jobs.update_job(
            request.request_id,
            state="failed",
            event="Request needs attention",
            error=error,
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )


def create_app():
    @asynccontextmanager
    async def lifespan(application):
        JobStore(data_dir()).recover_interrupted()
        yield
        for task in application.state.tasks:
            task.cancel()
        await asyncio.gather(*application.state.tasks, return_exceptions=True)

    app = FastAPI(title="HeatBrief workspace", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.sessions = {}
    app.state.tasks = set()
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )

    @app.middleware("http")
    async def response_security(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https://tile.openstreetmap.org; "
            "connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    @app.exception_handler(HeatBriefError)
    async def domain_error(_request, exc):
        return JSONResponse(
            status_code=exc.status, content={"error": exc.code, "message": str(exc)}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_request",
                "message": "Check the request details",
                "details": [
                    {"field": ".".join(map(str, item["loc"])), "message": item["msg"]}
                    for item in exc.errors()
                ],
            },
        )

    def session(request: Request):
        entry = app.state.sessions.get(request.cookies.get("heatbrief_session", ""))
        if not entry or entry["expires"] < time.time():
            raise HeatBriefError("session_expired", "Reload the workspace to continue", 401)
        return entry

    def mutation(request: Request, x_heatbrief_csrf: str | None = Header(default=None)):
        entry = session(request)
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
            raise HeatBriefError("forbidden", "This request must come from the workspace", 403)
        if not x_heatbrief_csrf or not hmac.compare_digest(entry["csrf"], x_heatbrief_csrf):
            raise HeatBriefError("forbidden", "Reload the workspace before continuing", 403)

    @app.get("/api/bootstrap")
    async def bootstrap(request: Request, response: Response):
        app.state.sessions = {
            key: value
            for key, value in app.state.sessions.items()
            if value["expires"] > time.time()
        }
        cookie = request.cookies.get("heatbrief_session", "")
        if cookie in app.state.sessions:
            csrf = app.state.sessions[cookie]["csrf"]
        else:
            csrf, cookie = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            app.state.sessions[cookie] = {"csrf": csrf, "expires": time.time() + 24 * 3600}
        response.set_cookie(
            "heatbrief_session", cookie, httponly=True, samesite="strict", max_age=24 * 3600
        )
        response.headers["Cache-Control"] = "no-store"

        async def alive(client, url):
            try:
                return (await client.get(url, timeout=2)).status_code == 200
            except httpx.HTTPError:
                return False

        async with httpx.AsyncClient(trust_env=False) as client:
            api_ok, n8n_ok = await asyncio.gather(
                alive(client, "http://127.0.0.1:8000/health"),
                alive(client, "http://localhost:5678/healthz"),
            )
        recent = Store(data_dir()).recent()
        latest_run = JobStore(data_dir()).latest_job()
        if (
            latest_run
            and latest_run["state"] == "completed"
            and (not recent or latest_run["id"] != recent[0]["request_id"])
        ):
            latest_run = None
        return {
            "csrf": csrf,
            "assistant_mode": assistant_mode(),
            "data_mode": "mock",
            "automation_connected": api_ok and n8n_ok,
            "catalog": CATALOG,
            "history": [history_summary(item) for item in recent],
            "latest": recent[0] if recent else None,
            "latest_run": latest_run,
            "fixture": {"date": "2025-09-20", "time": "14:00", "timezone": "America/Phoenix"},
            "workflow_url": "http://localhost:5678/workflow/heatbriefDemo001",
        }

    @app.get("/api/history", dependencies=[Depends(session)])
    def history():
        return [history_summary(item) for item in Store(data_dir()).recent()]

    @app.get("/api/status")
    def status():
        return {"status": "ok", "service": "heatbrief-workspace", "version": "0.2.0"}

    @app.get("/api/briefings/{request_id}", dependencies=[Depends(session)])
    def briefing(request_id: str):
        return Store(data_dir()).get(request_id)

    @app.post("/api/chat", dependencies=[Depends(mutation)])
    async def chat(message: ChatInput):
        return await reply(message, Store(data_dir()))

    @app.post("/api/runs", status_code=202, dependencies=[Depends(mutation)])
    async def run(request: BriefingRequest):
        jobs = JobStore(data_dir())
        try:
            previous = jobs.get_job(request.request_id)
            if previous["request"] != request.model_dump(mode="json"):
                raise HeatBriefError(
                    "idempotency_conflict", "Use a new request ID for changed content", 409
                )
            if previous["state"] in ("queued", "running"):
                return previous
        except HeatBriefError as exc:
            if exc.code != "not_found":
                raise
        local_config()
        job = jobs.create_job(request)
        task = asyncio.create_task(execute_run(request, app))
        app.state.tasks.add(task)
        task.add_done_callback(app.state.tasks.discard)
        return job

    @app.get("/api/runs/{job_id}", dependencies=[Depends(session)])
    def run_status(job_id: str):
        return JobStore(data_dir()).get_job(job_id)

    class DraftEdit(BaseModel):
        model_config = ConfigDict(extra="forbid")
        content: str = Field(min_length=1, max_length=20000)

    @app.post("/api/briefings/{request_id}/draft", dependencies=[Depends(mutation)])
    def edit_draft(request_id: str, edit: DraftEdit):
        return Store(data_dir()).edit_draft(request_id, edit.content)

    @app.post("/api/briefings/{request_id}/review", dependencies=[Depends(mutation)])
    async def review(
        request_id: str, decision: Review, authorization: Annotated[str | None, Header()] = None
    ):
        if not authorization:
            raise HeatBriefError("unauthorized", "Enter the reviewer key to record a decision", 401)
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            response = await client.post(
                f"http://127.0.0.1:8000/briefings/{request_id}/review",
                headers={"Authorization": authorization},
                json=decision.model_dump(),
            )
        if response.status_code >= 400:
            error = response.json()
            raise HeatBriefError(
                error.get("error", "review_failed"),
                error.get("message", "Review could not be recorded"),
                response.status_code,
            )
        return response.json()

    @app.get("/api/briefings/{request_id}/pdf", dependencies=[Depends(session)])
    def pdf(request_id: str):
        result = Store(data_dir()).get(request_id)
        return Response(
            make_pdf(result),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="heatbrief-{request_id}.pdf"',
                "Cache-Control": "no-store",
            },
        )

    build = ROOT / "web/dist"
    app.mount("/assets", StaticFiles(directory=build / "assets", check_dir=False), name="assets")

    @app.get("/{path:path}")
    def index(path: str):
        if path.startswith("api/"):
            raise HeatBriefError("not_found", "Endpoint not found", 404)
        if path == "favicon.svg":
            return FileResponse(ROOT / "web/public/favicon.svg", media_type="image/svg+xml")
        if not (build / "index.html").exists():
            raise HeatBriefError(
                "not_built", "Build the web workspace with npm run build in web", 503
            )
        return FileResponse(build / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
