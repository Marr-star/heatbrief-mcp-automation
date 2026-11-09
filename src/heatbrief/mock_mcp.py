"""Fictional fixtures over the real MCP stdio transport; never live data."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HeatBrief MOCK temperature data")
FIXTURES = {
    (33.4484, -112.074): ("Phoenix Civic Plaza", 35.2),
    (33.4255, -111.94): ("Tempe Riverside", 34.1),
    (33.4942, -111.9261): ("Scottsdale Courtyard", 36.7),
}
FIXTURE_DATE_TIME = {"start_date": "2025-09-20", "start_time": "14:00", "filter_type": 1}


@mcp.tool()
def env_params(latitude: float, longitude: float, date_time: dict) -> dict:
    """MOCK DATA ONLY. Get a fictional point reading for the documented demo fixture.

    The normalized response is HeatBrief-owned, not a verified FortyGuard schema.
    Reference temperature is deliberately not accepted as a measured observation.
    """
    if date_time != FIXTURE_DATE_TIME:
        raise ValueError("unsupported_date: Mock supports only 2025-09-20 at 14:00 America/Phoenix")
    fixture = FIXTURES.get((latitude, longitude))
    if fixture is None:
        raise ValueError("unsupported_location: Use one of the three demo coordinates")
    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature": fixture[1],
        "unit": "C",
        "observed_at": "2025-09-20T14:00:00-07:00",
        "source": "HeatBrief fictional fixture — Mock data",
        "source_id": f"mock-20250920-{latitude}-{longitude}",
        "mock": True,
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
