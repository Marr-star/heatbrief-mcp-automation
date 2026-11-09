# Two-minute demonstration

Open `docs/demo.html` locally for self-contained playback. The companion `docs/assets/demo.cast` is an asciicast terminal recording; `docs/assets/demo-transcript.txt` is its readable transcript. This is a scripted recording of actual executed CLI commands and output, not a recording of a coding-assistant UI or n8n instance.

| Time | Demonstration |
|---|---|
| 0:00 | Explain the use case and visible mock-data scope |
| 0:08 | Discover `env_params` over MCP and retrieve a fictional measurement |
| 0:25 | Compare three points and save the client briefing |
| 0:45 | Inspect the evidence-backed report and limitations |
| 1:10 | Repeat the request and show the saved-result replay |
| 1:30 | Show a missing-timezone validation failure |
| 1:46 | Hand off for human review and state external integration limits |

To re-record: `uv run python scripts/record-demo.py`. It takes approximately 120 seconds and creates an isolated, ignored request-history database. It makes no live API calls, uses fictional client details and sends no messages.

For a later live presentation: configure the coding assistant using `docs/agent-setup.md`, import the n8n workflow, verify a complete execution, then record the visible UI. Keep the mock label until FortyGuard access and the actual measurement schema are tested.
