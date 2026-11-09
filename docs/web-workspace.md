# HeatBrief web workspace

Run the interface locally with the existing Python, SQLite and n8n automation.

```powershell
uv sync --locked
uv run python scripts/start-workspace.py
```

Open http://127.0.0.1:8001, or use VS Code's **Terminal → Run Task → HeatBrief: open web workspace**. The launcher installs missing frontend dependencies, builds changed frontend source, starts/reuses the automation, and launches the workspace on loopback. Requires Node.js 24+.

## Use it

1. Type **Compare all demo sites on July 17, 2026 at noon Cairo time**. The comparison starts directly from chat. If details are missing, reply with them in chat; the pending request runs once complete. **Run the demo** selects and runs the original example. The form and **Run comparison** remain optional alternatives.
2. Follow actual workflow events. The completed run links to its real n8n execution when the local execution record is available.
3. Chat returns both extremes and the spread. Ask **Which is highest?**, **Which is lowest?**, **What is the average?**, **Show the ranking**, or **What does spread mean?** without starting another run. The cards mark both highest and lowest readings; a highest-specific question leads the finding with the maximum. The map shows positions, not an interpolated heatmap.
4. Open **Evidence** for timestamps, units, coordinates, source records and limitations. Download Markdown or a PDF briefing.
5. Open **Client briefing**, edit the follow-up and save it. Approval/rejection requires the separate reviewer key from your local `.env` (`HEATBRIEF_REVIEW_TOKEN`). The key is entered only for that review request and is not saved by the frontend. Approval records a decision for manual sending.
6. Use **Saved briefings** to revisit reports. **Replay saved request** runs the same request through n8n and reuses its stored result.

Chat asks for missing details automatically. Reply with those details in the conversation to continue the pending comparison.

## Demo window and examples

The supported window is **January 1, 2025 at 00:00 through December 31, 2027 at 23:59, America/Phoenix**, including both endpoints. Every minute inside it is supported: 1,095 dates and 1,576,800 time slots per site. It is a window of allowed individual comparison times; each comparison uses the single instant you select.

In **Request details**, choose a **Date and time example** (winter morning, spring noon, summer afternoon, autumn evening, late night or the original example), or enter any date and minute in the window. The timezone is applied before checking the bounds; equivalent instants in another IANA timezone work. Invalid dates, DST gaps/repeated hours and out-of-window instants require correction before a workflow starts.

The three sites receive deterministic synthetic values with seasonal, daytime and per-day variation. Repeating a point/time gives the same value. These rules are fictional scenarios, not a Phoenix climate model, historical observations or a forecast. Generated evidence uses a `mock-v2-` identifier containing its canonical date and minute. The original September 20, 2025 14:00 example keeps its fixed values and IDs, and saved briefings are replayed without recalculation.

Additional CLI requests: `examples/request-winter-morning.json` and `examples/request-summer-afternoon.json`. All demo temperatures remain fictional.

## Guided and optional AI intake

Guided mode works immediately without a model account. It handles explicit comparison commands and follow-up result questions, including dates written as ISO dates, full/abbreviated English month names or day-month-year, 12/24-hour times, noon/midnight, and today/tomorrow in the specified timezone (Africa/Cairo when no timezone has yet been supplied). Missing date/time/timezone or ambiguous locations require a chat clarification; exact named sites or **all demo sites** identify the catalog locations.

Each chat message has its own ID, so repeating the same HTTP message cannot enqueue a duplicate successful comparison. An explicit **just prepare; don't run** keeps the request prepared until **run it**. Questions about a saved result use that result's timestamps and source records; they do not claim new measurements. Highest ties, negative values and unit conversion are handled by Python. Older saved comparisons derive their maximum from the stored ranking without rewriting their original reports.

This is a bounded guided assistant for these commands and results, labeled **Guided demo assistant**. An optional configured model can help intake; the server validates every action. Neither mode can approve a draft or send an email from chat.

To opt into AI intake, configure these locally in `.env` and restart the workspace:

```dotenv
HEATBRIEF_ASSISTANT_MODE=openai
OPENAI_API_KEY=your-local-key
HEATBRIEF_LLM_MODEL=a-model-available-to-your-account
```

This explicitly enables an external OpenAI API request containing the question and request draft. Model availability and API billing depend on your account. The adapter uses the Responses API with structured output and `store=false`; the model helps with intake, while explicit time/location fields and Python calculations remain authoritative. A model is never given reviewer or sending tools. See [official structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

The OpenAI adapter is covered with a simulated HTTP contract test; no live model call was performed during this build because no key/model was configured.

## Architecture and local access

- React/TypeScript + Vite provides the interface. Leaflet displays browser-requested OpenStreetMap tiles with attribution. Map tiles require internet; site markers remain available when the base layer fails. See [Leaflet](https://leafletjs.com/examples/quick-start/) and [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/).
- The separate FastAPI workspace on port 8001 serves the built interface and owns the same-origin browser API.
- Its server calls the existing authenticated n8n webhook. Secrets never appear in the frontend bundle or bootstrap response.
- SQLite stores run events/results and briefing history. An interrupted run can be retried; the underlying request ID prevents duplicate briefings.
- Browser writes require a local session and CSRF header; cross-origin writes are rejected. Reviewer credentials remain separate from automation credentials.
- This is a single-owner local workspace. It has not been deployed online and is not a multi-user hosted service. Hosted deployment needs its own authentication, durable shared storage and network-access design.

If you restart the server while a browser tab is open, reload the page to establish a fresh session. Logs are under `.automation/logs/workspace.log`.
