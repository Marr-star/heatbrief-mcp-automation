# HeatBrief web workspace

Run the interface locally with the existing Python, SQLite and n8n automation.

```powershell
uv sync --locked
uv run python scripts/start-workspace.py
```

Open http://127.0.0.1:8001, or use VS Code's **Terminal → Run Task → HeatBrief: open web workspace**. The launcher installs missing frontend dependencies, builds changed frontend source, starts/reuses the automation, and launches the workspace on loopback. Requires Node.js 24+.

## Use it

1. Choose **Try the demo sites**, review the named sites/date/time/timezone, then select **Run comparison**.
2. Follow actual workflow events. The completed run links to its real n8n execution when the local execution record is available.
3. Explore the location map and temperature cards. The map shows site positions, not an interpolated temperature heatmap.
4. Open **Evidence** for timestamps, units, coordinates, source records and limitations. Download Markdown or a PDF briefing.
5. Open **Client briefing**, edit the follow-up and save it. Approval/rejection requires the separate reviewer key from your local `.env` (`HEATBRIEF_REVIEW_TOKEN`). The key is entered only for that review request and is not saved by the frontend. Approval records a decision for manual sending.
6. Use **Saved briefings** to revisit reports. **Replay saved request** runs the same request through n8n and reuses its stored result.

The **Clarify a request** example intentionally omits date/time/timezone so you can see the assistant ask for missing details. Unsupported dates, times and timezones are blocked before starting a workflow. Choose **Use demo date and time** to explicitly apply the supported sample time while keeping your other request details. All demo temperatures are fictional.

## Guided and optional AI intake

Guided mode works immediately without a model account. It extracts explicit dates/times/timezones and named demo sites, leaves missing fields unresolved, and validates completed requests. It is labeled **Guided demo assistant** in the interface.

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
