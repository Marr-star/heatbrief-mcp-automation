import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from heatbrief.api import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HEATBRIEF_API_TOKEN", "automation-test-token")
    monkeypatch.setenv("HEATBRIEF_REVIEW_TOKEN", "human-test-token")
    monkeypatch.setenv("HEATBRIEF_MODE", "mock")
    return TestClient(app)


def test_auth_and_validation(client):
    assert client.get("/health").json()["mode"] == "mock"
    assert client.post("/briefings", json={}).status_code == 401
    response = client.post(
        "/briefings", json={}, headers={"Authorization": "Bearer automation-test-token"}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"
    assert any("timezone" in e["field"] for e in response.json()["details"])


def test_webhook_to_saved_report_and_human_review(client):
    request = json.loads(Path("examples/request.json").read_text())
    headers = {"Authorization": "Bearer automation-test-token"}
    created = client.post("/briefings", json=request, headers=headers)
    assert created.status_code == 200
    result = created.json()
    assert result["status"] == "draft_pending_review"
    assert result["comparison"]["lowest_c"] == 34.1
    replay = client.post("/briefings", json=request, headers=headers)
    assert replay.json()["replayed"] is True
    path = f"/briefings/{request['request_id']}"
    assert client.get(path, headers=headers).json()["report_markdown"] == result["report_markdown"]
    review = {"decision": "approve", "reviewer": "Demo reviewer"}
    assert client.post(path + "/review", json=review, headers=headers).status_code == 401
    approved = client.post(
        path + "/review", json=review, headers={"Authorization": "Bearer human-test-token"}
    )
    assert approved.json()["status"] == "approved_for_manual_send"
    assert "sent" not in approved.json()
    assert (
        client.post(
            path + "/review",
            json={**review, "decision": "reject"},
            headers={"Authorization": "Bearer human-test-token"},
        ).status_code
        == 409
    )
