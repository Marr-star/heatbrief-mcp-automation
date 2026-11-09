import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_full_agent_mcp_round_trip(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "heatbrief.agent_mcp"],
        env={"HEATBRIEF_DATA_DIR": str(tmp_path), "HEATBRIEF_MODE": "mock"},
    )
    request = json.loads(Path("examples/request.json").read_text())
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {"create_briefing", "read_briefing"} == {tool.name for tool in tools.tools}
            created = await session.call_tool("create_briefing", {"request": request})
            assert not created.isError
            assert created.structuredContent["comparison"]["lowest_c"] == 34.1
            saved = await session.call_tool("read_briefing", {"request_id": request["request_id"]})
            assert (
                saved.structuredContent["follow_up_draft"]
                == created.structuredContent["follow_up_draft"]
            )
