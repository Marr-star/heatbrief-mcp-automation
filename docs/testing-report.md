# Verification report

Local environment: Windows, Python 3.12.12. Mock fixtures only. Commands: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `node scripts/check-workflow.cjs`.

Local result on 2026-11-09: **35 tests passed**, lint passed, formatting passed, workflow graph/JavaScript checks passed. A real local HTTP smoke run also passed.

The two-minute scripted terminal recording contains actual successful MCP/CLI commands, a saved-result replay and a missing-timezone failure. Its embedded offline player's playback JavaScript passed a local harness check; visual browser playback was not tested.

| Scenario | Observed result | Evidence type |
|---|---|---|
| Complete request | Tempe Riverside ranks lowest at 34.1 °C; spread 2.6 °C | Real MCP stdio + API tests |
| Missing fields / timezone | Validation asks for the missing fields; no fabricated inputs | Model + API tests |
| Ambiguous location / duplicated point | Explicit coordinates and unique locations required | Validation |
| DST gap / repeated local hour | Request rejected with clarification | Model tests |
| Unsupported date / location | Actionable mock error; no invented measurement | Mock MCP tests |
| Missing live credentials | `missing_credentials`; no request sent | Local live-mode gate test |
| Configured but unverified live mode | `live_integration_unverified`; no mock fallback | Local gate test |
| Invalid credentials | One attempt; no transient retry | Injected provider test, not FortyGuard |
| Rate limit / timeout | At most three attempts, then explicit failure | Injected provider tests |
| Missing measurement | Incomplete report; missing value is never treated as zero | Injected provider test |
| Wrong unit / NaN / mismatched point or time | Evidence rejected before ranking | Injected provider tests |
| Fahrenheit / tied temperatures | Conversion to Celsius and all tied locations preserved | Calculation tests |
| Repeated or concurrent request | Saved result reused; active request gets 409; changed content gets 409 | SQLite tests |
| Crash leaves a processing claim | Expired 90-second lease can be reclaimed | SQLite test |
| Human review | Automation token cannot approve; separate reviewer can approve; conflicting review gets 409 | API tests |
| Real HTTP flow | Authenticated POST → real mock MCP → SQLite → report → replay → human review | Local Uvicorn + HTTP smoke script |
| n8n graph and review JavaScript | Connections resolve; success/replay/error packets behave as expected | Static graph + JS harness |

## Limits

- No successful FortyGuard call, coverage check, API-key authentication, access-denied response or provider rate-limit observation is claimed.
- The n8n export has not yet been imported or executed in an n8n runtime.
- No coding-assistant MCP UI session has been tested. The same MCP server is exercised with the official Python SDK.
- The first GitHub CI run passed on Windows and Ubuntu: [run 42574927443](https://github.com/Marr-star/heatbrief-mcp-automation/actions/runs/42574927443), commit `4b54ced`. Later commits trigger their own checks.
- There is no outbound email transport. Human approval records a decision for manual sending.
