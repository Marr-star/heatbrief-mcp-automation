import argparse
import asyncio
import json

from heatbrief.mcp_client import call_env_params, mock_session
from heatbrief.mock_mcp import FIXTURE_DATE_TIME


async def ping():
    async with mock_session() as session:
        tools = await session.list_tools()
        result = await call_env_params(
            session,
            {
                "latitude": 33.4484,
                "longitude": -112.074,
                "date_time": FIXTURE_DATE_TIME,
            },
        )
    print(json.dumps({"tools": [t.name for t in tools.tools], "measurement": result}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="HeatBrief temperature analyst")
    parser.add_argument("command", choices=["ping"])
    parser.parse_args()
    asyncio.run(ping())


if __name__ == "__main__":
    main()
