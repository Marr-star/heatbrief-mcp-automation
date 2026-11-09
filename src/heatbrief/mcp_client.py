import json
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

from heatbrief.errors import HeatBriefError


@asynccontextmanager
async def mock_session():
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "heatbrief.mock_mcp"])
    try:
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    except BaseExceptionGroup as group:
        # AnyIO task groups wrap exceptions raised inside the yielded context.
        # Preserve one domain failure so unsupported requests stay actionable.
        leaves = []

        def flatten(error):
            if isinstance(error, BaseExceptionGroup):
                for nested in error.exceptions:
                    flatten(nested)
            else:
                leaves.append(error)

        flatten(group)
        if len(leaves) == 1:
            raise leaves[0] from None
        raise HeatBriefError(
            "mcp_connection_error", "MCP session failed; retry the request", 502
        ) from None


async def call_env_params(session, arguments: dict) -> dict:
    try:
        result = await session.call_tool("env_params", arguments)
    except McpError as exc:
        raise HeatBriefError("mcp_connection_error", "MCP tool call failed", 502) from exc
    if result.isError:
        message = " ".join(c.text for c in result.content if c.type == "text")
        code = next(
            (code for code in ("unsupported_date", "unsupported_location") if code in message),
            "tool_error",
        )
        raise HeatBriefError(code, message, 502 if code == "tool_error" else 422)
    if result.structuredContent is not None:
        return result.structuredContent
    text = next((c.text for c in result.content if c.type == "text"), None)
    if text is None:
        raise HeatBriefError("invalid_response", "MCP returned no structured measurement", 502)
    return json.loads(text)
