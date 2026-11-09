import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from heatbrief.errors import HeatBriefError
from heatbrief.mcp_client import call_env_params, mock_session
from heatbrief.mock_mcp import FIXTURE_DATE_TIME
from heatbrief.models import BriefingRequest
from heatbrief.providers import provider_session
from heatbrief.service import build_briefing
from heatbrief.store import Store


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


async def run_compare(args):
    request = BriefingRequest.model_validate_json(Path(args.request).read_text(encoding="utf-8"))
    async with provider_session(args.mode) as provider:
        result = await build_briefing(request, provider, Store(args.data_dir))
    output = Path(args.out) / request.request_id
    output.mkdir(parents=True, exist_ok=True)
    (output / "briefing.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output / "report.md").write_text(result["report_markdown"], encoding="utf-8")
    (output / "follow-up.txt").write_text(result["follow_up_draft"], encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "replayed": result["replayed"],
                "comparison": result["comparison"],
                "output": str(output),
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description="HeatBrief temperature analyst")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ping", help="Discover and call the mock MCP tool")
    compare_parser = commands.add_parser("compare", help="Create a report and follow-up draft")
    compare_parser.add_argument("request", help="JSON request file")
    compare_parser.add_argument("--mode", choices=["mock", "live"], default=None)
    compare_parser.add_argument("--out", default="reports")
    compare_parser.add_argument("--data-dir", default=os.getenv("HEATBRIEF_DATA_DIR", "data"))
    show_parser = commands.add_parser("show", help="Read a completed briefing")
    show_parser.add_argument("request_id")
    show_parser.add_argument("--data-dir", default=os.getenv("HEATBRIEF_DATA_DIR", "data"))
    args = parser.parse_args()
    try:
        if args.command == "ping":
            asyncio.run(ping())
        elif args.command == "compare":
            asyncio.run(run_compare(args))
        else:
            print(json.dumps(Store(args.data_dir).get(args.request_id), indent=2))
    except (HeatBriefError, ValidationError, OSError, ValueError, TimeoutError) as exc:
        print(
            json.dumps({"error": getattr(exc, "code", "invalid_request"), "message": str(exc)}),
            file=sys.stderr,
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
