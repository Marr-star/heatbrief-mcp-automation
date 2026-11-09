# Run the actual automation locally

The project can start its own isolated n8n instance, attach the required credentials, and publish a local copy of the exported workflow. It keeps the runtime, database, credentials and logs inside the ignored `.automation` directory. The original export remains portable and inactive.

## Start and test

In VS Code, choose **Terminal → Run Task → HeatBrief: start automation**. Wait for `"automation": "ready"`, then choose **Terminal → Run Task → HeatBrief: test automation**.

Equivalent commands from the project directory:

```powershell
uv run python scripts/start-automation.py
uv run python scripts/test-automation.py
```

The first start installs n8n 2.46.6 if necessary and requires Node.js 24+. Subsequent starts reuse the installed runtime. The API and n8n run in the background, listening on loopback. Their logs are under `.automation/logs`.

## Inspect in n8n

Open http://localhost:5678/workflow/heatbriefDemo001. For this isolated local demo, open `.automation/local-login.txt` in VS Code and use the login details there. This is a local account, not an n8n Cloud or FortyGuard account. Select **Executions** to inspect the real node inputs and outputs.

## What the test checks

1. Missing webhook credentials are rejected.
2. A valid request runs the actual Webhook → HTTP Request → Code → Respond to Webhook graph.
3. The returned report matches the report saved by HeatBrief.
4. Repeating the request replays the same report and follow-up.
5. Reusing the ID with changed content returns 409.
6. Omitting timezone returns 422 with clarification.
7. An unsupported date returns 422 with a limitation.
8. SQLite contains exactly one briefing for the repeated request.

Each test run uses a new request ID and writes its report, follow-up, JSON result and check summary under the printed `reports/automation-...` directory. The status stays `draft_pending_review`; the test does not approve or send anything.

The n8n instance receives only the webhook credential and HeatBrief automation token. The separate human-review token stays outside n8n. All readings remain fictional mock data. Live FortyGuard integration remains gated.
