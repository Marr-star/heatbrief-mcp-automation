# Real n8n automation verification

Verified locally on **2026-11-09**: Windows, Node.js 24.19.0, n8n 2.46.6, HeatBrief Python 3.12.12. Mock temperature data only.

## Actual execution path

Authenticated POST `/webhook/heatbrief` → n8n Webhook → HTTP Request → HeatBrief API → real MCP stdio → Python comparison → SQLite report/draft → Code review packet → Respond to Webhook.

The exported workflow was imported using the n8n CLI, configured with two local Header Auth credentials, and published in an isolated loopback-only instance. The human review token was not imported into n8n.

## Results

Request ID: `automation-b40b8542d732`.

| Check | Observed result |
|---|---|
| Webhook authentication | Missing credential rejected |
| Complete request | 200; Tempe Riverside lowest at 34.1 °C; visible Mock data label |
| Persistence | n8n's returned report exactly matched the saved HeatBrief report |
| Duplicate webhook | 200; `replayed: true`; identical unsent follow-up |
| Same ID, changed content | 409; `idempotency_conflict` |
| Missing timezone | 422; `invalid_request` with clarification |
| Unsupported date | 422; `unsupported_date` |
| No duplicate briefing | Exactly one SQLite briefing row for the repeated ID |

n8n execution IDs **1–5** were inspected in its own database and each had `status=success` for workflow `heatbriefDemo001`. These represent the valid request, replay, conflict and two handled validation failures. A handled HTTP error is an expected workflow result, so the n8n execution itself succeeds.

Status remains `draft_pending_review`. No approval or outbound message was produced.

## Repeat it

Use VS Code's **HeatBrief: start automation** and **HeatBrief: test automation** tasks, or:

```powershell
uv run python scripts/start-automation.py
uv run python scripts/test-automation.py
```

Every test run uses a new ID and exports its own report, draft, JSON and check summary into the printed `reports/automation-...` directory. Inspect node data in the local n8n **Executions** view.

## Limits

This proves the local n8n-to-HeatBrief automation over mock MCP. It does not verify live FortyGuard data, a coding-assistant UI, cloud/container networking or email delivery. The older two-minute CLI recording predates this runtime test.
