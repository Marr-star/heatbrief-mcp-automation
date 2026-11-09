# Verification report

Local environment: Windows, Python 3.12.12. Mock fixtures only. Commands: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `node scripts/check-workflow.cjs`.

Latest local result on 2026-11-09: **118 Python tests and 9 frontend tests passed**, with lint, formatting and the React/TypeScript production build passing. Earlier phases also verified the workflow graph/JavaScript, local HTTP and real n8n runtime.

Web workspace phase: **47 tests passed** locally. The React/TypeScript production build passed. Browser checks covered the desktop two-panel layout, narrow-screen panels, missing-field clarification, a real n8n comparison (execution **13**, request `web-5ba6dd8644f4413688`), source evidence, a saved draft edit, PDF download and rejection of an invalid reviewer key. The two-page exported PDF was rendered and visually inspected for readability, provenance and mock labels. Optional AI intake was checked with a simulated provider response; no live model key was configured.

Demo-time recovery regression: **53 tests passed**, with lint, formatting and frontend build passing. Unsupported dates, times and timezones are rejected before a workspace job or webhook call is created. The assistant keeps the requested fields and explains the fixture limits. Browser verification recovered the September 9 selection with **Use demo date and time**, then completed the corrected request in real n8n execution **17**.

Expanded demo window: **2025-01-01 00:00 through 2027-12-31 23:59 America/Phoenix, inclusive**, every minute. Tests cover all 1,095 calendar dates, inclusive endpoints, out-of-window instants, DST gaps/repeated hours, timezone conversion, reproducible generated readings, distinct timestamp evidence IDs, original-example compatibility and real MCP replay. Browser checks verified presets and a blocked out-of-window request. Actual n8n executions **18** (2026-07-15 15:37 America/Phoenix) and **19** (2026-11-09 18:45 Africa/Cairo) completed with three generated readings each. Follow-up chat from a saved briefing was also verified after normalizing its draft fields.

Chat execution and highest-temperature phase: complete text requests now enqueue the actual n8n workflow directly; missing fields are collected across messages, while explicit preparation remains non-executing. Repeating the same message ID does not enqueue a duplicate completed run. Follow-up highest/lowest/average/ranking and terminology answers use saved evidence without a new job. Highest values and all ties use converted Celsius measurements, with regression coverage for negative temperatures and older saved comparisons lacking maximum fields. Browser execution **26** completed from two chat messages without any form selections or Run-comparison click; it returned lowest 36.5 °C and highest 41.4 °C and answered highest/spread follow-ups. A fresh one-message hottest request completed as execution **27** (2026-07-17 12:00 Africa/Cairo), led the finding with the maximum and displayed both extremes. A two-page PDF from execution 26 was rendered and visually checked; PDF, Markdown and the unsent draft included both extremes.

Evidence-request regression: the exact phrase **i want the evidence**, along with source/proof variants, now returns the selected saved briefing’s temperatures, coordinates, timestamps, original units, source names and evidence IDs. It opens the Evidence view with source records expanded. Tests cover preservation of the saved timestamp even when the form draft has changed, missing metadata, no selected briefing, definition questions and no outgoing workflow call. Browser verification reproduced the phrase against the saved original example (execution **28**) and displayed all three source IDs in chat and Evidence without a new comparison.

Customer-style browser walkthrough: found and fixed contextual site narrowing, unrecognized comparative wording, stale request descriptions after refinements, and a PDF page-break issue. Verified actual runs **29–33**, saved-draft edits, history search/restore, evidence, browser PDF download, invalid-date rejection and conversational recovery. See [the full walkthrough](human-walkthrough.md) for exact prompts, observations and limits.

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
| Real n8n runtime | Eight automation checks passed; five execution records have success status | n8n 2.46.6 + actual webhook requests + SQLite evidence |

## Limits

- No successful FortyGuard call, coverage check, API-key authentication, access-denied response or provider rate-limit observation is claimed.
- n8n runtime import, publication and execution are verified locally. Hosted/container deployments still need their own networking and credential checks. See [the runtime test report](automation-test-report.md).
- No coding-assistant MCP UI session has been tested. The same MCP server is exercised with the official Python SDK.
- The first GitHub CI run passed on Windows and Ubuntu: [run 42574927443](https://github.com/Marr-star/heatbrief-mcp-automation/actions/runs/42574927443), commit `4b54ced`. Later commits trigger their own checks.
- There is no outbound email transport. Human approval records a decision for manual sending.
