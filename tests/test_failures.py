import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from heatbrief.errors import HeatBriefError
from heatbrief.models import BriefingRequest
from heatbrief.providers import measure_with_retry, provider_session
from heatbrief.service import build_briefing, compare
from heatbrief.store import Store


@pytest.fixture
def request_payload():
    return json.loads(Path("examples/request.json").read_text())


class FakeProvider:
    mode = "mock"

    def __init__(self, transform=None, failure=None):
        self.calls = 0
        self.transform = transform or (lambda value, _location: value)
        self.failure = failure

    async def measure(self, location, request):
        self.calls += 1
        if self.failure:
            raise self.failure
        value = {
            **location.model_dump(exclude={"name"}),
            "temperature": 95,
            "unit": "F",
            "observed_at": request.timestamp,
            "source": "Mock data",
            "source_id": location.name,
            "mock": True,
        }
        return self.transform(value, location)


@pytest.mark.parametrize("field", ["timezone", "date", "time", "locations"])
def test_missing_fields_require_clarification(request_payload, field):
    request_payload.pop(field)
    with pytest.raises(ValidationError):
        BriefingRequest.model_validate(request_payload)


async def test_unit_conversion_and_ties(request_payload):
    result = await compare(BriefingRequest.model_validate(request_payload), FakeProvider())
    assert result["comparison"]["lowest_c"] == 35
    assert len(result["comparison"]["lowest_locations"]) == 3
    assert "tie" in result["follow_up_draft"]


@pytest.mark.parametrize(
    "changes",
    [
        {"temperature": float("nan")},
        {"unit": "K"},
        {"observed_at": "2025-09-20T14:00:00"},
        {"latitude": 0},
        {"observed_at": "2025-09-20T14:00:00Z"},
        {"mock": False},
    ],
)
async def test_untrusted_measurements_are_not_ranked(request_payload, changes):
    provider = FakeProvider(lambda value, _location: {**value, **changes})
    with pytest.raises(HeatBriefError):
        await compare(BriefingRequest.model_validate(request_payload), provider)


async def test_rate_limit_retries_then_recovers(request_payload):
    class Flaky(FakeProvider):
        async def measure(self, location, request):
            if self.calls < 2:
                self.calls += 1
                raise HeatBriefError("rate_limited", "Rate limit exceeded", 429)
            return await super().measure(location, request)

    provider = Flaky()
    request = BriefingRequest.model_validate(request_payload)
    result = await measure_with_retry(provider, request.locations[0], request, base_delay=0)
    assert result["temperature"] == 95
    assert provider.calls == 3


@pytest.mark.parametrize(
    "failure,expected",
    [
        (TimeoutError(), 3),
        (HeatBriefError("rate_limited", "Rate limited", 429), 3),
        (HeatBriefError("unauthorized", "Invalid credentials", 401), 1),
    ],
)
async def test_retry_limit_and_no_retry_for_bad_credentials(request_payload, failure, expected):
    provider = FakeProvider(failure=failure)
    request = BriefingRequest.model_validate(request_payload)
    with pytest.raises(HeatBriefError):
        await measure_with_retry(provider, request.locations[0], request, base_delay=0)
    assert provider.calls == expected


async def test_live_mode_fails_closed_without_credentials(monkeypatch):
    monkeypatch.delenv("FORTYGUARD_API_KEY", raising=False)
    monkeypatch.delenv("FORTYGUARD_MCP_URL", raising=False)
    with pytest.raises(HeatBriefError, match="FORTYGUARD_API_KEY"):
        async with provider_session("live"):
            pytest.fail("Must not enter a live provider without credentials")
    monkeypatch.setenv("FORTYGUARD_API_KEY", "fake-test-key")
    monkeypatch.setenv("FORTYGUARD_MCP_URL", "https://example.invalid/mcp")
    with pytest.raises(HeatBriefError, match="gated"):
        async with provider_session("live"):
            pytest.fail("Must not make unverified live calls")


async def test_unsupported_date_preserves_error_and_releases_claim(request_payload, tmp_path):
    request_payload["date"] = "2030-01-01"
    request = BriefingRequest.model_validate(request_payload)
    store = Store(tmp_path)
    with pytest.raises(HeatBriefError) as error:
        async with provider_session("mock") as provider:
            await build_briefing(request, provider, store)
    assert error.value.code == "unsupported_date"
    assert store.claim(request, "mock") is None


async def test_duplicate_while_processing_does_not_measure_twice(request_payload, tmp_path):
    started, finish = asyncio.Event(), asyncio.Event()

    class Paused(FakeProvider):
        async def measure(self, location, request):
            started.set()
            await finish.wait()
            return await super().measure(location, request)

    provider = Paused()
    request = BriefingRequest.model_validate(request_payload)
    store = Store(tmp_path)
    first = asyncio.create_task(build_briefing(request, provider, store))
    await started.wait()
    try:
        with pytest.raises(HeatBriefError) as error:
            await build_briefing(request, provider, Store(tmp_path))
        assert error.value.code == "request_in_progress"
    finally:
        finish.set()
        await first
    assert provider.calls == len(request.locations)


def test_expired_processing_claim_can_recover(request_payload, tmp_path):
    request = BriefingRequest.model_validate(request_payload)
    store = Store(tmp_path)
    store.claim(request, "mock")
    with store.connect() as db:
        db.execute("UPDATE briefings SET lease_expires=0")
    assert store.claim(request, "mock") is None
