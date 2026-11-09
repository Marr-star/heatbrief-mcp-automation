# Build phases

Each completed phase gets a separate commit and push to GitHub.

1. **Foundation + MCP:** Python project, explicit mock fixture, one successful MCP tool call.
2. **Comparison + evidence:** input validation, deterministic ranking, report, draft follow-up, SQLite history and deduplication.
3. **Automation:** authenticated local API and importable n8n webhook workflow with human review.
4. **Reliability:** failure matrix, bounded retries, regression tests, CI, setup and troubleshooting.
5. **Demo + handoff:** sample artifacts, example prompts, demo walkthrough and integration feedback.

## Delivery status

- Phases 1–4 implemented, locally verified, committed and pushed separately. Phase 4 CI passed on Windows and Ubuntu.
- Phase 5 includes sample artifacts, preview, prompts, setup guides and a two-minute scripted terminal recording of actual CLI requests.
- Still unverified: live FortyGuard access and schema, coding-assistant UI use, and n8n runtime import/execution. The included recording demonstrates the tested mock CLI workflow.

Mock tests do not count as live provider observations. Native n8n and assistant UI demos can be recorded after those integrations are configured.
