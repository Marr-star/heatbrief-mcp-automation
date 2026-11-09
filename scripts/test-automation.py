"""Exercise the actual n8n webhook, including replay and handled failures."""

import json
import sqlite3
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    config_file = ROOT / ".automation/local-config.json"
    if not config_file.exists():
        raise RuntimeError("Start automation first: uv run python scripts/start-automation.py")
    config = json.loads(config_file.read_text())
    local_env = dotenv_values(ROOT / ".env")
    token = local_env["HEATBRIEF_API_TOKEN"]
    webhook = "http://localhost:5678/webhook/heatbrief"
    headers = {"X-HeatBrief-Webhook-Key": config["webhook_key"]}
    request = json.loads((ROOT / "examples/request.json").read_text())
    request["request_id"] = "automation-" + uuid.uuid4().hex[:12]
    checks = []
    with httpx.Client(timeout=75, trust_env=False) as client:
        unauthorized = client.post(webhook, json=request)
        assert unauthorized.status_code in (401, 403), "Webhook must require its own credential"
        checks.append("Webhook authentication rejects missing credentials")

        created = client.post(webhook, headers=headers, json=request)
        assert created.status_code == 200, f"Webhook returned {created.status_code}: {created.text}"
        result = created.json()
        assert result["request_id"] == request["request_id"]
        assert result["status"] == "draft_pending_review"
        assert result["review_required"] is True
        assert result["comparison"]["lowest_locations"] == ["Tempe Riverside"]
        assert result["comparison"]["lowest_c"] == 34.1
        assert "Mock data" in result["report_markdown"]
        checks.append("Real n8n execution returns the saved mock report and review packet")

        saved = client.get(
            "http://127.0.0.1:8000/briefings/" + request["request_id"],
            headers={"Authorization": "Bearer " + token},
        )
        assert saved.status_code == 200
        assert saved.json()["report_markdown"] == result["report_markdown"]
        checks.append("n8n response matches the persisted HeatBrief report")

        replay = client.post(webhook, headers=headers, json=request)
        assert replay.status_code == 200 and replay.json()["replayed"] is True
        assert replay.json()["follow_up_draft"] == result["follow_up_draft"]
        checks.append("Duplicate webhook reuses the original report and unsent follow-up")

        changed = {**request, "question": "Changed question using the same request ID"}
        conflict = client.post(webhook, headers=headers, json=changed)
        assert conflict.status_code == 409 and conflict.json()["error"] == "idempotency_conflict"
        checks.append("Changed content with the same ID returns 409 through n8n")

        missing = {**request, "request_id": request["request_id"] + "-missing"}
        missing.pop("timezone")
        invalid = client.post(webhook, headers=headers, json=missing)
        assert invalid.status_code == 422 and invalid.json()["error"] == "invalid_request"
        checks.append("Missing timezone returns a useful 422 through n8n")

        unsupported = {
            **request,
            "request_id": request["request_id"] + "-date",
            "date": "2030-01-01",
        }
        unavailable = client.post(webhook, headers=headers, json=unsupported)
        assert unavailable.status_code == 422 and unavailable.json()["error"] == "unsupported_date"
        checks.append("Unsupported date returns an explicit limitation through n8n")

    data_dir = Path(local_env.get("HEATBRIEF_DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    with sqlite3.connect(data_dir / "heatbrief.sqlite3") as db:
        count = db.execute(
            "SELECT COUNT(*) FROM briefings WHERE request_id=?", (request["request_id"],)
        ).fetchone()[0]
    assert count == 1, "Expected exactly one stored briefing after duplicate requests"
    checks.append("SQLite contains exactly one briefing for the repeated request")
    output = ROOT / "reports" / request["request_id"]
    output.mkdir(parents=True, exist_ok=True)
    (output / "briefing.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output / "report.md").write_text(result["report_markdown"], encoding="utf-8")
    (output / "follow-up.txt").write_text(result["follow_up_draft"], encoding="utf-8")
    summary = {
        "automation": "passed",
        "request_id": request["request_id"],
        "checks": checks,
        "lowest_c": 34.1,
        "mock": True,
        "output": str(output),
    }
    (output / "automation-checks.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, OSError, httpx.HTTPError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
