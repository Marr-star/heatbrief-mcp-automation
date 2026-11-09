# Integration boundary

Official documentation consulted on 2026-11-09:

- https://docs-api.fortyguard.com/docs/mcp-tools
- https://docs-api.fortyguard.com/docs/quickstart
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpClient/
- https://github.com/modelcontextprotocol/python-sdk

FortyGuard documents `env_params` with coordinates, `date_time`, a **reference** `temperature` and optional `analysis`. A reference temperature is input; it must never be presented as an independently retrieved reading. The exact authenticated MCP transport, account coverage, limits and response schema have not been tested here.

The mock uses that documented tool name and input concepts, with a HeatBrief-owned normalized response. It is **not** a verified copy of FortyGuard's wire schema. Its values are fictional and cover the three demo coordinates from 2025-01-01 00:00 through 2027-12-31 23:59 America/Phoenix inclusive, every minute. The mock-owned `date_time.timezone` field defaults to America/Phoenix; it is not claimed as a verified FortyGuard parameter. Generated readings use deterministic scenario rules, not observations or forecasts; the original sample values and evidence IDs remain stable. Unsupported requests return an explicit error.

The demo agent runs in an existing coding assistant through HeatBrief's MCP server; the assistant supplies the LLM reasoning. Python supplies all ranking and report facts. The automated baseline uses a deterministic explanation template and needs no LLM key.

Before enabling live comparison: obtain a development key, verify the endpoint and authentication with the provider, inspect tools/list, capture a sanitized real response, implement an explicit unit/time/source mapping, confirm reference-temperature provenance, and add live contract tests. No automatic fallback from live to mock is permitted.
