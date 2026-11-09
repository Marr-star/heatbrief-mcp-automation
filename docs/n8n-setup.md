# Automated client briefing

The exported workflow uses **Webhook → HeatBrief HTTP bridge → human review packet → response**. Inside the bridge, Python validates the request, calls the mock MCP over stdio, ranks measurements, generates the report and unsent draft, and saves them to SQLite. This keeps calculation and idempotency logic in one place. It does not claim a native FortyGuard MCP connection from n8n.

## Start the bridge

```powershell
Copy-Item .env.example .env
# Edit .env: use different random values for HEATBRIEF_API_TOKEN and HEATBRIEF_REVIEW_TOKEN.
.\scripts\run-api.ps1
```

API documentation: http://127.0.0.1:8000/docs. Health: http://127.0.0.1:8000/health.

## Import and configure n8n

1. Import `workflows/client-briefing.json` into a local n8n instance. It is inactive by default.
2. Create a **Header Auth** credential for the inbound Webhook: header name `X-HeatBrief-Webhook-Key`, with a random value. Attach it to `Receive briefing request`.
3. Create a separate **Header Auth** credential for `Create and save briefing`: header name `Authorization`, value `Bearer <HEATBRIEF_API_TOKEN from .env>`. Do not add the review token to n8n.
4. If n8n runs on the same host, keep `http://127.0.0.1:8000/briefings`. A container's loopback is its own container; use a shared internal network and a suitable bridge hostname there. n8n Cloud cannot reach this local service without an explicitly configured secure deployment.
5. Click **Listen for test event**, then POST `examples/request.json` to the displayed test URL with the webhook credential header. Inspect the result and saved report.
6. Submit the same JSON again: `replayed` becomes true and no second report or follow-up is created. Change the request content without changing its ID: the API returns `409`.

The HTTP node returns the API's status and JSON through Respond to Webhook, including validation errors. Its request timeout is 70 seconds; the comparison has a 60 second limit. A transport failure before an HTTP response can still cause an n8n execution error; inspect Executions and retry with the same ID.

## Human review

The workflow returns an unsent follow-up and a `review_required` field. A human reads the evidence, report and draft. To record approval or rejection, call `POST /briefings/{request_id}/review` with `{"decision":"approve","reviewer":"Demo reviewer"}` and `Authorization: Bearer <HEATBRIEF_REVIEW_TOKEN>`. An automation token cannot approve a briefing. Approval marks it `approved_for_manual_send`; there is no email-sending node or sending endpoint.

## Verification scope

The bridge and MCP round trip are exercised by automated tests. The workflow JSON and review-packet JavaScript are checked locally. Import and execution inside a real n8n instance remain **unverified** until an instance is configured. Do not describe static checks as a successful n8n run.

Native MCP Client alternative: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpClient/. Configure it only after verifying the actual FortyGuard endpoint, transport, authentication and response schema. The working demo deliberately uses the tested local bridge.
