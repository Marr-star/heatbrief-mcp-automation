"""Fictional samples and synthetic scenarios over MCP stdio; never live data."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from heatbrief.demo import DEMO_ZONE, REFERENCE, parse_demo_timestamp, synthetic_temperature

mcp = FastMCP("HeatBrief MOCK temperature data")
FIXTURES = {
    (33.4484, -112.074): ("Phoenix Civic Plaza", 35.2),
    (33.4255, -111.94): ("Tempe Riverside", 34.1),
    (33.4942, -111.9261): ("Scottsdale Courtyard", 36.7),
}
FIXTURE_DATE_TIME = {"start_date": "2025-09-20", "start_time": "14:00", "filter_type": 1}


@mcp.tool(structured_output=True)
def env_params(latitude: float, longitude: float, date_time: dict) -> dict[str, Any]:
    """MOCK ONLY. Fictional readings for three sites, 2025-01-01 00:00 through
    2027-12-31 23:59 America/Phoenix inclusive, at any minute. date_time accepts
    start_date YYYY-MM-DD, start_time HH:MM, filter_type 1 and optional IANA timezone
    (default America/Phoenix). Values are deterministic synthetic scenarios, never
    actual observations or forecasts. The original example keeps its fixed values.
    The normalized response is HeatBrief-owned, not a verified FortyGuard schema.
    """
    stamp = parse_demo_timestamp(date_time)
    coordinates = (latitude, longitude)
    fixture = FIXTURES.get(coordinates)
    if fixture is None:
        raise ValueError("unsupported_location: Use one of the three demo coordinates")
    original = stamp == REFERENCE
    source_id = (
        f"mock-20250920-{latitude}-{longitude}"
        if original
        else f"mock-v2-{stamp.astimezone(DEMO_ZONE):%Y%m%dT%H%M}-{latitude}-{longitude}"
    )
    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature": fixture[1]
        if original
        else synthetic_temperature(fixture[1], stamp, coordinates),
        "unit": "C",
        "observed_at": stamp.isoformat(),
        "source": "HeatBrief fictional fixture — Mock data"
        if original
        else "HeatBrief synthetic demo v2 — generated, not observations",
        "source_id": source_id,
        "mock": True,
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
