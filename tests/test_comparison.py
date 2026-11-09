import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from heatbrief.errors import HeatBriefError
from heatbrief.models import BriefingRequest
from heatbrief.providers import provider_session
from heatbrief.service import build_briefing, compare
from heatbrief.store import Store


@pytest.fixture
def payload():
    return json.loads(Path("examples/request.json").read_text())


async def test_fixture_comparison_and_persistent_replay(payload, tmp_path):
    request = BriefingRequest.model_validate(payload)
    async with provider_session("mock") as provider:
        first = await build_briefing(request, provider, Store(tmp_path))
        second = await build_briefing(request, provider, Store(tmp_path))
    assert first["comparison"]["lowest_locations"] == ["Tempe Riverside"]
    assert first["comparison"]["spread_c"] == 2.6
    assert "Mock data" in first["report_markdown"]
    assert "HUMAN REVIEW REQUIRED" in first["follow_up_draft"]
    assert second["replayed"] is True
    assert first["report_markdown"] == second["report_markdown"]


@pytest.mark.parametrize("field,value", [("timezone", "Unknown/Zone"), ("time", "14:00Z")])
def test_invalid_timezone_and_time(payload, field, value):
    payload[field] = value
    with pytest.raises(ValidationError):
        BriefingRequest.model_validate(payload)


@pytest.mark.parametrize("date,time", [("2025-11-02", "01:30"), ("2025-03-09", "02:30")])
def test_dst_requires_clarification(payload, date, time):
    payload.update(date=date, time=time, timezone="America/New_York")
    with pytest.raises(ValidationError, match="ambiguous or nonexistent"):
        BriefingRequest.model_validate(payload)


async def test_missing_measurement_is_incomplete_and_not_zero(payload):
    class Provider:
        mode = "mock"

        async def measure(self, location, request):
            return {
                **location.model_dump(exclude={"name"}),
                "temperature": None if location.name == "Tempe Riverside" else 35,
                "unit": "C",
                "observed_at": request.timestamp,
                "source": "Mock data",
                "source_id": location.name,
                "mock": True,
            }

    result = await compare(BriefingRequest.model_validate(payload), Provider())
    assert result["comparison"]["incomplete"] is True
    assert len(result["comparison"]["ranking"]) == 2
    assert "Among available readings" in result["follow_up_draft"]


async def test_request_id_conflict(payload, tmp_path):
    store = Store(tmp_path)
    store.claim(BriefingRequest.model_validate(payload), "mock")
    payload["question"] = "A different business question for the same request ID"
    with pytest.raises(HeatBriefError, match="different content"):
        store.claim(BriefingRequest.model_validate(payload), "mock")
