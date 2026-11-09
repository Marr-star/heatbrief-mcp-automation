import json
from datetime import timedelta
from pathlib import Path

import pytest

from heatbrief.demo import DEMO_END, DEMO_START, parse_demo_timestamp, validate_demo_time
from heatbrief.errors import HeatBriefError
from heatbrief.mock_mcp import env_params
from heatbrief.models import BriefingRequest
from heatbrief.providers import provider_session
from heatbrief.service import build_briefing
from heatbrief.store import Store


@pytest.mark.parametrize(
    "day,clock,zone",
    [
        ("2025-01-01", "00:00", "America/Phoenix"),
        ("2025-09-09", "14:00", "America/Phoenix"),
        ("2026-07-15", "15:37", "America/Phoenix"),
        ("2026-11-09", "18:45", "Africa/Cairo"),
        ("2027-12-31", "23:59", "America/Phoenix"),
        ("2025-01-01", "07:00", "UTC"),
        ("2028-01-01", "06:59", "UTC"),
    ],
)
def test_inclusive_window_and_generated_measurement(day, clock, zone):
    request = json.loads(Path("examples/request.json").read_text())
    request.update(date=day, time=clock, timezone=zone)
    value = BriefingRequest.model_validate(request)
    validate_demo_time(value)
    reading = env_params(
        33.4484,
        -112.074,
        {
            "start_date": day,
            "start_time": clock,
            "timezone": zone,
            "filter_type": 1,
        },
    )
    assert reading["observed_at"] == value.timestamp.isoformat()
    assert reading["mock"] is True
    assert "generated, not observations" in reading["source"]


@pytest.mark.parametrize(
    "day,clock,zone",
    [
        ("2024-12-31", "23:59", "America/Phoenix"),
        ("2028-01-01", "00:00", "America/Phoenix"),
        ("2025-01-01", "06:59", "UTC"),
        ("2028-01-01", "07:00", "UTC"),
        ("2025-03-09", "02:30", "America/New_York"),
        ("2025-11-02", "01:30", "America/New_York"),
    ],
)
def test_outside_window_and_ambiguous_times_are_not_generated(day, clock, zone):
    with pytest.raises(ValueError, match="unsupported_date"):
        parse_demo_timestamp(
            {
                "start_date": day,
                "start_time": clock,
                "timezone": zone,
                "filter_type": 1,
            }
        )


def test_every_calendar_date_has_stable_distinct_source_records():
    records, temperatures = set(), set()
    for offset in range((DEMO_END.date() - DEMO_START.date()).days + 1):
        day = DEMO_START.date() + timedelta(days=offset)
        reading = env_params(
            33.4484,
            -112.074,
            {
                "start_date": day.isoformat(),
                "start_time": "08:37",
                "filter_type": 1,
            },
        )
        records.add(reading["source_id"])
        temperatures.add(reading["temperature"])
    assert len(records) == 1095
    assert len(temperatures) > 100
    first = env_params(
        33.4484,
        -112.074,
        {
            "start_date": "2026-07-15",
            "start_time": "15:37",
            "filter_type": 1,
        },
    )
    assert first == env_params(
        33.4484,
        -112.074,
        {
            "start_date": "2026-07-15",
            "start_time": "15:37",
            "filter_type": 1,
        },
    )


def test_daytime_variation_and_minute_evidence_are_real_scenarios():
    values = [
        env_params(
            33.4255,
            -111.94,
            {
                "start_date": "2026-07-15",
                "start_time": clock,
                "filter_type": 1,
            },
        )
        for clock in ("08:00", "15:00", "15:01", "23:30")
    ]
    assert values[1]["temperature"] > values[0]["temperature"]
    assert values[1]["temperature"] > values[3]["temperature"]
    assert values[1]["source_id"] != values[2]["source_id"]


async def test_new_dates_through_real_mcp_keep_timestamps_and_replay(tmp_path):
    payload = json.loads(Path("examples/request.json").read_text())
    store = Store(tmp_path)
    async with provider_session("mock") as provider:
        for index, (day, clock, zone) in enumerate(
            [
                ("2025-09-09", "14:00", "America/Phoenix"),
                ("2026-07-15", "15:37", "America/Phoenix"),
                ("2026-11-09", "18:45", "Africa/Cairo"),
            ]
        ):
            request = BriefingRequest.model_validate(
                {
                    **payload,
                    "request_id": f"expanded-{index}",
                    "date": day,
                    "time": clock,
                    "timezone": zone,
                }
            )
            result = await build_briefing(request, provider, store)
            assert result["comparison"]["incomplete"] is False
            assert len(result["measurements"]) == 3
            assert all(
                row["observed_at"] == request.timestamp.isoformat()
                for row in result["measurements"]
            )
            assert all("mock-v2-" in row["source_id"] for row in result["measurements"])
            replay = await build_briefing(request, provider, store)
            assert replay["replayed"] is True
            assert replay["report_markdown"] == result["report_markdown"]


def test_boundary_validation_uses_instants_across_timezones():
    payload = json.loads(Path("examples/request.json").read_text())
    request = BriefingRequest.model_validate(
        {**payload, "date": "2025-01-01", "time": "06:59", "timezone": "UTC"}
    )
    with pytest.raises(HeatBriefError, match="inclusive"):
        validate_demo_time(request)
