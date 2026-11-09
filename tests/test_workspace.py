import asyncio
import json
from copy import deepcopy
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

import heatbrief.workspace as workspace
from heatbrief.models import BriefingRequest
from heatbrief.pdf_report import make_pdf
from heatbrief.store import Store
from heatbrief.workspace_jobs import JobStore


@pytest.fixture
def saved_briefing():
    return json.loads(
        Path("examples/generated/demo-phoenix-001/briefing.json").read_text(encoding="utf-8")
    )


@pytest.fixture
async def workspace_client(tmp_path, monkeypatch, saved_briefing):
    monkeypatch.setenv("HEATBRIEF_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HEATBRIEF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HEATBRIEF_ASSISTANT_MODE", "guided")
    local = tmp_path / ".automation"
    local.mkdir()
    (local / "local-config.json").write_text(
        json.dumps(
            {
                "webhook_key": "private-webhook-test-key",
                "workflow_id": "test-workflow",
            }
        )
    )
    calls = []
    behavior = {"failure": False}

    async def backend(request):
        if request.method == "GET":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/webhook/heatbrief":
            assert request.headers["X-HeatBrief-Webhook-Key"] == "private-webhook-test-key"
            body = json.loads(request.content)
            calls.append(body)
            if behavior["failure"]:
                return httpx.Response(
                    422, json={"error": "unsupported_date", "message": "Unsupported mock date"}
                )
            store = Store(tmp_path / "data")
            original = store.claim(BriefingRequest.model_validate(body), "mock")
            if original:
                return httpx.Response(200, json={**original, "replayed": True})
            result = deepcopy(saved_briefing)
            result.update(request_id=body["request_id"], request=body, replayed=False)
            store.complete(body["request_id"], result)
            return httpx.Response(200, json=result)
        if request.url.path.endswith("/review"):
            if request.headers.get("Authorization") != "Bearer human-test-key":
                return httpx.Response(
                    401, json={"error": "unauthorized", "message": "Reviewer key not accepted"}
                )
            body = json.loads(request.content)
            return httpx.Response(
                200,
                json=Store(tmp_path / "data").review(
                    request.url.path.split("/")[2],
                    {**body, "reviewed_at": "2026-11-09T10:00:00Z"},
                ),
            )
        raise AssertionError("Unexpected outbound request")

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        workspace.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            **{**kwargs, "transport": httpx.MockTransport(backend)},
        ),
    )
    monkeypatch.setattr(
        workspace, "execution_record", lambda *_args: {"id": "42", "status": "success"}
    )
    app = workspace.create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client, calls, behavior, tmp_path
    await asyncio.gather(*app.state.tasks, return_exceptions=True)


async def session_headers(client):
    response = await client.get("/api/bootstrap")
    return {"X-HeatBrief-CSRF": response.json()["csrf"], "Origin": "http://testserver"}


async def wait_job(client, job_id):
    for _ in range(50):
        value = (await client.get("/api/runs/" + job_id)).json()
        if value["state"] in ("completed", "failed"):
            return value
        await asyncio.sleep(0.01)
    raise AssertionError("Job did not finish")


async def test_session_csrf_and_secret_boundaries(workspace_client):
    client, _calls, _behavior, _root = workspace_client
    assert (await client.get("/api/history")).status_code == 401
    response = await client.get("/api/bootstrap")
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "private-webhook-test-key" not in response.text
    assert "OPENAI_API_KEY" not in response.text
    headers = {"X-HeatBrief-CSRF": response.json()["csrf"]}
    assert (
        await client.post("/api/chat", json={"message": "Compare the three demo sites"})
    ).status_code == 403
    assert (
        await client.post(
            "/api/chat",
            headers={**headers, "Origin": "https://elsewhere.invalid"},
            json={"message": "Compare the three demo sites"},
        )
    ).status_code == 403
    second = (await client.get("/api/bootstrap")).json()
    assert second["csrf"] == headers["X-HeatBrief-CSRF"]


async def test_workflow_job_persistence_and_replay(workspace_client):
    client, calls, _behavior, root = workspace_client
    headers = await session_headers(client)
    payload = json.loads(Path("examples/request.json").read_text())
    payload["request_id"] = "workspace-job-test"
    started = await client.post("/api/runs", headers=headers, json=payload)
    assert started.status_code == 202
    complete = await wait_job(client, payload["request_id"])
    assert complete["state"] == "completed"
    assert complete["execution_id"] == "42"
    assert complete["result"]["comparison"]["lowest_c"] == 34.1
    assert len(complete["events"]) == 4
    assert JobStore(root / "data").get_job(payload["request_id"])["state"] == "completed"
    await client.post("/api/runs", headers=headers, json=payload)
    replay = await wait_job(client, payload["request_id"])
    assert replay["result"]["replayed"] is True
    assert len(calls) == 2
    changed = {**payload, "question": "A changed question needs a different request ID"}
    assert (await client.post("/api/runs", headers=headers, json=changed)).status_code == 409


async def test_workflow_failure_is_visible_and_does_not_invent_report(workspace_client):
    client, _calls, behavior, _root = workspace_client
    headers = await session_headers(client)
    behavior["failure"] = True
    payload = json.loads(Path("examples/request.json").read_text())
    payload.update(request_id="unsupported-workspace", date="2030-01-01")
    await client.post("/api/runs", headers=headers, json=payload)
    failed = await wait_job(client, payload["request_id"])
    assert failed["state"] == "failed"
    assert failed["error"]["error"] == "unsupported_date"
    assert failed["result"] is None


async def test_draft_edits_and_human_review_are_separate(workspace_client, saved_briefing):
    client, _calls, _behavior, root = workspace_client
    headers = await session_headers(client)
    store = Store(root / "data")
    store.claim(BriefingRequest.model_validate(saved_briefing["request"]), "mock")
    store.complete(saved_briefing["request_id"], saved_briefing)
    path = "/api/briefings/" + saved_briefing["request_id"]
    edited = await client.post(
        path + "/draft", headers=headers, json={"content": "Reviewed client draft"}
    )
    assert edited.json()["follow_up_draft"] == "Reviewed client draft"
    assert edited.json()["report_markdown"] == saved_briefing["report_markdown"]
    exported = await client.get(path + "/pdf")
    exported_text = " ".join(
        page.extract_text() for page in PdfReader(BytesIO(exported.content)).pages
    )
    assert "Reviewed client draft" in exported_text
    review = {"decision": "approve", "reviewer": "Demo reviewer"}
    assert (await client.post(path + "/review", headers=headers, json=review)).status_code == 401
    assert (
        await client.post(
            path + "/review",
            headers={**headers, "Authorization": "Bearer automation-test-key"},
            json=review,
        )
    ).status_code == 401
    approved = await client.post(
        path + "/review", headers={**headers, "Authorization": "Bearer human-test-key"}, json=review
    )
    assert approved.json()["status"] == "approved_for_manual_send"
    assert (
        await client.post(path + "/draft", headers=headers, json={"content": "Late edit"})
    ).status_code == 409


def test_pdf_contains_mock_label_temperature_and_provenance(saved_briefing):
    content = make_pdf(saved_briefing)
    assert content.startswith(b"%PDF")
    reader = PdfReader(BytesIO(content))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert "MOCK DATA" in text
    assert "34.1" in text
    assert "mock-20250920-33.4255--111.94" in text
    assert "Temperature alone" in text


def test_interrupted_jobs_are_recoverable(tmp_path, saved_briefing):
    jobs = JobStore(tmp_path)
    request = BriefingRequest.model_validate(saved_briefing["request"])
    jobs.create_job(request)
    jobs.update_job(request.request_id, state="running")
    jobs.recover_interrupted()
    assert jobs.get_job(request.request_id)["error"]["error"] == "interrupted"
