"""Verify the real HTTP -> MCP -> SQLite -> response -> review flow."""

import json
import os
import sys
import uuid
from pathlib import Path

import httpx

base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
payload = json.loads((Path(__file__).resolve().parents[1] / "examples/request.json").read_text())
payload["request_id"] = "http-smoke-" + uuid.uuid4().hex[:10]
headers = {"Authorization": f"Bearer {os.environ['HEATBRIEF_API_TOKEN']}"}
with httpx.Client(base_url=base_url, timeout=70, trust_env=False) as client:
    assert client.get("/health").json()["mode"] == "mock"
    assert client.post("/briefings", json=payload).status_code == 401
    result = client.post("/briefings", headers=headers, json=payload)
    result.raise_for_status()
    body = result.json()
    assert body["comparison"]["lowest_locations"] == ["Tempe Riverside"]
    assert "Mock data" in body["report_markdown"]
    assert client.post("/briefings", headers=headers, json=payload).json()["replayed"] is True
    path = f"/briefings/{payload['request_id']}"
    assert client.get(path, headers=headers).json()["report_markdown"] == body["report_markdown"]
    invalid = {**payload, "request_id": "invalid-" + uuid.uuid4().hex[:8]}
    invalid.pop("timezone")
    assert client.post("/briefings", headers=headers, json=invalid).status_code == 422
    review = {"decision": "approve", "reviewer": "Fictional HTTP smoke reviewer"}
    assert client.post(path + "/review", headers=headers, json=review).status_code == 401
    if os.getenv("HEATBRIEF_REVIEW_TOKEN"):
        approved = client.post(path + "/review", json=review, headers={
            "Authorization": f"Bearer {os.environ['HEATBRIEF_REVIEW_TOKEN']}",
        })
        assert approved.json()["status"] == "approved_for_manual_send"
    print(json.dumps({"http_flow": "passed", "request_id": payload["request_id"],
                      "lowest_c": body["comparison"]["lowest_c"], "mock": True}))
