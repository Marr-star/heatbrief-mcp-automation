import pytest

from heatbrief.errors import HeatBriefError
from heatbrief.mcp_client import call_env_params, mock_session
from heatbrief.mock_mcp import FIXTURE_DATE_TIME


async def test_real_stdio_discovery_and_call():
    async with mock_session() as session:
        tools = await session.list_tools()
        assert "env_params" in [t.name for t in tools.tools]
        value = await call_env_params(
            session,
            {
                "latitude": 33.4484,
                "longitude": -112.074,
                "date_time": FIXTURE_DATE_TIME,
            },
        )
    assert value["mock"] is True
    assert value["temperature"] == 35.2
    assert value["unit"] == "C"


async def test_unsupported_location_is_explicit():
    async with mock_session() as session:
        with pytest.raises(HeatBriefError, match="unsupported_location"):
            await call_env_params(
                session,
                {
                    "latitude": 0,
                    "longitude": 0,
                    "date_time": FIXTURE_DATE_TIME,
                },
            )
