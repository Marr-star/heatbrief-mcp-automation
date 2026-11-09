import json
from datetime import date
from pathlib import Path

import pytest

from heatbrief.assistant import ChatInput, Draft, extract_explicit, reply
from heatbrief.models import BriefingRequest
from heatbrief.reporting import narrative
from heatbrief.service import compare
from heatbrief.store import Store


@pytest.fixture
def chat_store(tmp_path, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_ASSISTANT_MODE", "guided")
    result = json.loads(Path("examples/generated/demo-phoenix-001/briefing.json").read_text())
    store = Store(tmp_path)
    store.claim(BriefingRequest.model_validate(result["request"]), "mock")
    store.complete(result["request_id"], result)
    return store, result


async def test_complete_text_requests_a_run_without_a_confirmation_button(chat_store):
    store, _ = chat_store
    answer = await reply(
        ChatInput(message="Compare all demo sites on July 15, 2026 at 3:37pm Phoenix time"), store
    )
    assert answer["action"] == "run"
    assert answer["ready"] is True
    assert answer["draft"]["time"] == "15:37"
    assert len(answer["draft"]["locations"]) == 3
    assert "select Run" not in answer["message"]


async def test_missing_details_can_be_completed_entirely_in_chat(chat_store):
    store, _ = chat_store
    first = await reply(ChatInput(message="Compare all three sites"), store)
    assert first["action"] == "clarify"
    assert first["pending_action"] == "run"
    second = await reply(
        ChatInput(
            message="15 July 2026 at 3:37pm",
            draft=Draft.model_validate(first["draft"]),
            pending_action=first["pending_action"],
        ),
        store,
    )
    assert second["missing_fields"] == ["timezone"]
    third = await reply(
        ChatInput(
            message="Phoenix time",
            draft=Draft.model_validate(second["draft"]),
            pending_action=second["pending_action"],
        ),
        store,
    )
    assert third["action"] == "run"
    assert third["draft"]["date"] == "2026-07-15"


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Which is highest?", "Scottsdale Courtyard has the highest temperature at 36.7"),
        ("And the lowest?", "Tempe Riverside has the lowest temperature at 34.1"),
        ("What is the average?", "35.3 °C"),
        ("Show the ranking", "From coolest to warmest"),
    ],
)
async def test_followup_answers_use_legacy_saved_evidence_without_a_run(
    chat_store, question, expected
):
    store, saved = chat_store
    assert "highest_c" not in saved["comparison"]
    answer = await reply(ChatInput(message=question, briefing_id=saved["request_id"]), store)
    assert answer["action"] == "answer"
    assert expected in answer["message"]
    assert "2025-09-20" in answer["message"]


async def test_prepare_only_remains_draft_until_explicit_run(chat_store):
    store, saved = chat_store
    draft = Draft.model_validate({key: saved["request"][key] for key in Draft.model_fields})
    first = await reply(ChatInput(message="Just prepare this; don't run", draft=draft), store)
    assert first["action"] == "prepare"
    followup = await reply(
        ChatInput(
            message="Make it 6pm",
            draft=Draft.model_validate(first["draft"]),
            pending_action="prepare",
        ),
        store,
    )
    assert followup["action"] == "prepare"
    final = await reply(
        ChatInput(
            message="Run it",
            draft=Draft.model_validate(followup["draft"]),
            pending_action="prepare",
        ),
        store,
    )
    assert final["action"] == "run"
    assert final["draft"]["time"] == "18:00"


@pytest.mark.parametrize(
    "message,expected",
    [
        ("What does spread mean?", "highest returned temperature minus the lowest"),
        ("What is n8n?", "workflow engine"),
        ("What does mock mean?", "fictional"),
        ("Approve and email this report", "separate reviewer"),
    ],
)
async def test_explanations_and_unsupported_actions_never_request_comparison(
    chat_store, message, expected
):
    store, _ = chat_store
    answer = await reply(ChatInput(message=message), store)
    assert answer["action"] == "answer"
    assert expected in answer["message"]


async def test_explicit_demo_command_selects_and_runs_the_documented_example(chat_store):
    answer = await reply(ChatInput(message="run the demo"), chat_store[0])
    assert answer["action"] == "run"
    assert answer["draft"]["date"] == "2025-09-20"


def test_relative_dates_noon_and_midnight_use_an_explicit_reference():
    today = date(2026, 11, 9)
    draft = extract_explicit("Compare all sites tomorrow at noon Cairo time", Draft(), today)
    assert draft.date == "2026-11-10"
    assert draft.time == "12:00"
    assert draft.timezone == "Africa/Cairo"
    midnight = extract_explicit("Today at midnight", Draft(), today)
    assert midnight.date == "2026-11-09"
    assert midnight.time == "00:00"


async def test_highest_uses_converted_values_ties_and_negative_temperatures():
    payload = json.loads(Path("examples/request.json").read_text())
    request = BriefingRequest.model_validate(payload)

    class Provider:
        mode = "mock"

        async def measure(self, site, requested):
            first = site.name == "Phoenix Civic Plaza"
            return {
                **site.model_dump(exclude={"name"}),
                "temperature": -40 if first else -10,
                "unit": "F" if first else "C",
                "observed_at": requested.timestamp,
                "source": "Mock",
                "source_id": site.name,
                "mock": True,
            }

    result = await compare(request, Provider())
    assert result["comparison"]["highest_c"] == -10
    assert result["comparison"]["highest_locations"] == ["Scottsdale Courtyard", "Tempe Riverside"]
    assert result["comparison"]["lowest_c"] == -40
    assert result["comparison"]["spread_c"] == 30
    assert "tie for the highest temperature at -10.0" in narrative(result["comparison"])
    assert "highest temperature" in result["report_markdown"]
    assert "highest temperature" in result["follow_up_draft"]


async def test_unknown_term_question_is_not_misread_as_a_mean_temperature_query(chat_store):
    store, saved = chat_store
    answer = await reply(
        ChatInput(message="What does foobar mean?", briefing_id=saved["request_id"]), store
    )
    assert answer["action"] == "answer"
    assert "do not have an explanation" in answer["message"]
    assert "The average" not in answer["message"]


async def test_guided_mode_has_an_honest_explanation(chat_store):
    answer = await reply(ChatInput(message="What does guided mean?"), chat_store[0])
    assert answer["action"] == "answer"
    assert "without a general-purpose language model enabled" in answer["message"]
