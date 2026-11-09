# HeatBrief

An evidence-backed temperature analyst and client briefing workflow built with Python, MCP, SQLite and n8n.

**Current status: Phase 1 — a working, explicitly labeled mock MCP server. FortyGuard live integration is unverified.**

## Quick start

Install [uv](https://docs.astral.sh/uv/), then run from this folder:

```powershell
uv sync --locked
uv run heatbrief ping
uv run pytest
```

The ping command starts a real MCP stdio session, discovers the `env_params` tool and calls it against a fixed fictional fixture. It makes no FortyGuard API requests and uses no credits.

See [the build plan](docs/plan.md) and [the integration notes](docs/integration.md).
