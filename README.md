# HeatBrief

An evidence-backed temperature analyst and client briefing workflow built with Python, MCP, SQLite and n8n.

**Current status: Phase 2 — working MCP comparison, evidence-backed reports and SQLite history. FortyGuard live integration is unverified.**

## Quick start

Install [uv](https://docs.astral.sh/uv/), then run from this folder:

```powershell
uv sync --locked
uv run heatbrief ping
uv run heatbrief compare examples/request.json
uv run heatbrief show demo-phoenix-001
uv run pytest
```

The ping command starts a real MCP stdio session, discovers `env_params` and calls a fictional fixture. The comparison writes `reports/demo-phoenix-001/report.md`, `follow-up.txt` and `briefing.json`. Repeat the request to replay the saved result. It makes no FortyGuard API requests and uses no credits.

The fixture's lowest temperature is **Tempe Riverside, 34.1 °C**, with a 2.6 °C spread. This supports a temperature comparison only. It does not establish safety. All follow-ups remain unsent drafts for human review.

`uv run heatbrief-agent-mcp` exposes `create_briefing` and `read_briefing` to an MCP client. The request includes explicit coordinates, local date/time and an IANA timezone. Python calculates the ranking; an attached assistant can explain the returned evidence.

See [the build plan](docs/plan.md) and [the integration notes](docs/integration.md).
