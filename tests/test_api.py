import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from heatbrief.api import app


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HEATBRIEF_API_TOKEN", "automation-test-token")
    monkeypatch.setenv("HEATBRIEF_REVIEW_TOKEN", "human-test-token")
    monkeypatch.setenv("HEATBRIEF_MODE", "mock")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_auth_and_validation(client):
    assert (await client.get("/health")).json()["mode"] == "mock"
    assert (await client.post("/briefings", json={})).status_code == 401
    response = await client.post(
        "/briefings", json={}, headers={"Authorization": "Bearer automation-test-token"}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"
    assert any("timezone" in e["field"] for e in response.json()["details"])


async def test_webhook_to_saved_report_and_human_review(client):
    request = json.loads(Path("examples/request.json").read_text())
    headers = {"Authorization": "Bearer automation-test-token"}
    created = await client.post("/briefings", json=request, headers=headers)
    assert created.status_code == 200
    result = created.json()
    assert result["status"] == "draft_pending_review"
    assert result["comparison"]["lowest_c"] == 34.1
    replay = await client.post("/briefings", json=request, headers=headers)
    assert replay.json()["replayed"] is True
    path = f"/briefings/{request['request_id']}"
    assert (await client.get(path, headers=headers)).json()["report_markdown"] == result[
        "report_markdown"
    ]
    review = {"decision": "approve", "reviewer": "Demo reviewer"}
    assert (await client.post(path + "/review", json=review, headers=headers)).status_code == 401
    approved = await client.post(
        path + "/review", json=review, headers={"Authorization": "Bearer human-test-token"}
    )
    assert approved.json()["status"] == "approved_for_manual_send"
    assert "sent" not in approved.json()
    assert (
        await client.post(
            path + "/review",
            json={**review, "decision": "reject"},
            headers={"Authorization": "Bearer human-test-token"},
        )
    ).status_code == 409


async def test_unsupported_date_returns_actionable_http_error(client):
    request = json.loads(Path("examples/request.json").read_text())
    request["date"] = "2030-01-01"
    response = await client.post(
        "/briefings", json=request, headers={"Authorization": "Bearer automation-test-token"}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "unsupported_date"


async def test_duplicate_content_conflict(client):
    request = json.loads(Path("examples/request.json").read_text())
    headers = {"Authorization": "Bearer automation-test-token"}
    assert (await client.post("/briefings", json=request, headers=headers)).status_code == 200
    request["question"] = "A changed question requires a different ID"
    response = await client.post("/briefings", json=request, headers=headers)
    assert response.status_code == 409
    assert response.json()["error"] == "idempotency_conflict"


async def test_unconfigured_and_live_gates(client, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_API_TOKEN", "replace-with-a-random-local-token")
    assert (await client.post("/briefings", json={})).status_code == 503
    monkeypatch.setenv("HEATBRIEF_API_TOKEN", "automation-test-token")
    monkeypatch.setenv("HEATBRIEF_MODE", "live")
    monkeypatch.delenv("FORTYGUARD_API_KEY", raising=False)
    request = json.loads(Path("examples/request.json").read_text())
    response = await client.post(
        "/briefings", json=request, headers={"Authorization": "Bearer automation-test-token"}
    )
    assert response.status_code == 503
    assert response.json()["error"] == "missing_credentials"


async def test_same_review_token_cannot_bypass_human_separation(client, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_REVIEW_TOKEN", "automation-test-token")
    response = await client.post(
        "/briefings/demo/review",
        json={
            "decision": "approve",
            "reviewer": "Fictional reviewer",
        },
        headers={"Authorization": "Bearer automation-test-token"},
    )
    assert response.status_code == 503
