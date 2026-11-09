# MCP integration feedback

## Observation scope

No FortyGuard server has been accessed. These are local mock/SDK observations and questions for later live verification, not reported FortyGuard bugs.

## Local observation 1: structured tool output

- **Steps to reproduce:** expose a tool returning a bare `dict` using the installed Python FastMCP SDK and inspect its `CallToolResult`.
- **Expected:** a machine-readable result that clients can reliably parse.
- **Actual:** the initial bare return annotation produced text content without `structuredContent` in the analyst round-trip test.
- **Improvement applied:** explicit `dict[str, Any]` return annotations with `structured_output=True`; both mock and analyst tools now return structured content. The data client also supports JSON text responses.
- **Evidence:** local SDK regression test; not a provider observation.

## Local observation 2: task-group exception wrapping

- **Steps to reproduce:** request an unsupported mock date through an MCP client managed by AnyIO task groups.
- **Expected:** an actionable `unsupported_date` error reaches the caller.
- **Actual:** a domain exception propagated through the session context as a nested exception group, obscuring the original failure type.
- **Improvement applied:** preserve a single leaf failure when closing the MCP session; ambiguous multi-error connection failures become an explicit connection error.
- **Evidence:** unsupported-date regression test; not a provider observation.

## Live verification questions

1. What is the official MCP URL, supported transport and exact authentication header?
2. What tools and coordinate/date ranges are enabled for this development account?
3. `env_params` takes a reference `temperature`. Which tool supplies an independently retrieved comparable point temperature, with timestamp, units and provenance?
4. What are the exact response schemas and missing-data conventions? Is `tools/list` sufficient to discover all input constraints?
5. How are rate limits and asynchronous activity identifiers communicated? Which retry intervals are recommended?

For every later live finding, record sanitized steps, expected and actual behavior, account capability context, an activity ID where appropriate, and a proposed improvement. Never record API keys or temporary signed URLs.
