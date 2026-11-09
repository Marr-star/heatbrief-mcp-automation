# Setup and troubleshooting

## Python or command not found

Install uv from https://docs.astral.sh/uv/getting-started/installation/. Open a new terminal, run `uv sync --locked`, and use commands prefixed with `uv run`. Python 3.12 is selected by `.python-version`; uv can install it if needed. Node.js 22+ is used only for workflow JavaScript checks.

## Validation requests clarification

Use `examples/request.json`. Supply a local date, HH:MM time, IANA timezone and two to ten explicitly named coordinates. Avoid duplicate coordinates/names. DST gaps and repeated local hours require another unambiguous time. HeatBrief does not silently geocode names or assume a timezone.

## Unsupported mock date or coordinate

The synthetic demo covers the three example points from 2025-01-01 at 00:00 through 2027-12-31 at 23:59 America/Phoenix, inclusive, every minute. Choose a date/time example or any instant inside that window. Other locations and out-of-window instants are unsupported. A valid IANA timezone is required; DST gaps and repeated hours need another unambiguous local time. Generated values are fictional scenarios, not observations or forecasts. An incomplete result compares available points only and names missing evidence.

## Credentials and live mode

Live comparison remains gated even when a key and URL are supplied. Follow `docs/integration.md` to verify the official connection and schema before implementing the live adapter. Never label reference temperature input as a retrieved reading. Never paste credentials into requests or commit `.env`.

## API returns 401 or 503

Copy `.env.example` to `.env`, replace both token placeholders with different local random values, and start using `scripts/run-api.ps1` so `.env` is loaded. HTTP requires `Authorization: Bearer <HEATBRIEF_API_TOKEN>`. Review requires the separate `HEATBRIEF_REVIEW_TOKEN`. An unset or placeholder token produces 503; an incorrect token produces 401.

CLI/MCP processes read process environment variables; they do not automatically load `.env`. Default mock mode needs no key. The API launch script explicitly loads `.env`.

## Repeated ID / request in progress

Identical payloads and provider mode replay one stored report. Changed content requires a new ID. Concurrent in-flight duplicates return 409. Failed requests release their claim. If a process was killed, wait at most 90 seconds for its processing lease to expire, then retry the same request. There is a 60-second comparison budget, 15-second per-call timeout and up to three transient attempts.

## n8n cannot reach the bridge

Check `/health` from the n8n host. Docker containers do not share the host's loopback. Set the HTTP node URL for your deployment's internal network. n8n Cloud cannot directly call a localhost service. See `docs/n8n-setup.md`. Keep the workflow inactive until its credentials and URL are configured.

## MCP client does not connect

First run `uv run heatbrief ping`. MCP protocol traffic uses stdout; logs go to stderr. Ensure the client runs `uv run --directory <absolute-project-folder> heatbrief-agent-mcp`. The analyst MCP server itself starts a child mock MCP server using the same Python interpreter. Restart the client after configuration changes.
