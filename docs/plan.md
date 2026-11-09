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
- Follow-up automation phase: n8n 2.46.6 imported, configured, published and tested locally. Eight webhook checks passed; five real execution records were saved.
- Web workspace phase: guided intake, map/comparison/evidence views, real run tracking, saved briefings, editable drafts, reviewer decisions and PDF export implemented locally. Includes an optional AI intake adapter, disabled until configured. Browser smoke run reached actual n8n execution 13; 47 local tests passed.
- Still unverified: live FortyGuard access/schema and coding-assistant UI use. The included recording demonstrates the mock CLI workflow; the later n8n runtime evidence is documented separately.

Mock tests do not count as live provider observations. Native n8n and assistant UI demos can be recorded after those integrations are configured.
