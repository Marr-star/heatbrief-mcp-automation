import json
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from heatbrief.errors import HeatBriefError


@asynccontextmanager
async def mock_session():
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "heatbrief.mock_mcp"])
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_env_params(session, arguments: dict) -> dict:
    result = await session.call_tool("env_params", arguments)
    if result.isError:
        message = " ".join(c.text for c in result.content if c.type == "text")
        code = "unsupported_date" if "unsupported_date" in message else "unsupported_location"
        raise HeatBriefError(code, message)
    if result.structuredContent is not None:
        return result.structuredContent
    text = next((c.text for c in result.content if c.type == "text"), None)
    if text is None:
        raise HeatBriefError("invalid_response", "MCP returned no structured measurement", 502)
    return json.loads(text)
