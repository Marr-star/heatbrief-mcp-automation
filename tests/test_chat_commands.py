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


@pytest.mark.parametrize(
    "message",
    [
        "i want the evidence",
        "Show the evidence",
        "Show the sources",
        "Where did these readings come from?",
        "Send me the proof",
        "What is the evidence?",
    ],
)
async def test_evidence_request_returns_saved_records_without_new_measurements(chat_store, message):
    store, saved = chat_store
    changed_draft = Draft(date="2026-07-15", time="15:37", timezone="Africa/Cairo")
    answer = await reply(
        ChatInput(message=message, briefing_id=saved["request_id"], draft=changed_draft), store
    )
    assert answer["action"] == "answer"
    assert answer["view"] == "evidence"
    assert "2025-09-20" in answer["message"]
    assert "Mock data" in answer["message"]
    assert "\nCoordinates:" in answer["message"]
    for row in saved["measurements"]:
        assert row["source_id"] in answer["message"]
        assert row["source"] in answer["message"]
        assert row["observed_at"] in answer["message"]
        assert str(row["latitude"]) in answer["message"]
        assert str(row["longitude"]) in answer["message"]


async def test_evidence_without_selected_report_does_not_invent_records(chat_store):
    answer = await reply(ChatInput(message="I want the evidence"), chat_store[0])
    assert answer["action"] == "answer"
    assert "no saved comparison selected" in answer["message"]
    assert "view" not in answer
    assert "mock-20250920" not in answer["message"]


async def test_evidence_definition_still_explains_the_term(chat_store):
    store, saved = chat_store
    answer = await reply(
        ChatInput(message="What does evidence mean?", briefing_id=saved["request_id"]), store
    )
    assert "Evidence is the source record" in answer["message"]
    assert "view" not in answer


async def test_missing_source_metadata_is_labeled_unavailable(chat_store):
    store, saved = chat_store
    row = saved["measurements"][0]
    row.pop("source_id")
    row.pop("observed_at")
    store.complete(saved["request_id"], saved)
    answer = await reply(
        ChatInput(message="Show the sources", briefing_id=saved["request_id"]), store
    )
    assert "Evidence ID: Unavailable" in answer["message"]
    assert "Observed: Not recorded" in answer["message"]


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Just Tempe and Scottsdale.", ["Tempe Riverside", "Scottsdale Courtyard"]),
        ("Tempe and Scottsdale please", ["Tempe Riverside", "Scottsdale Courtyard"]),
        ("Remove Scottsdale", ["Phoenix Civic Plaza", "Tempe Riverside"]),
        ("Use only Civic Plaza and Riverside", ["Phoenix Civic Plaza", "Tempe Riverside"]),
    ],
)
async def test_contextual_site_refinements_preserve_time_and_run(chat_store, message, expected):
    store, saved = chat_store
    draft = Draft.model_validate({key: saved["request"][key] for key in Draft.model_fields})
    answer = await reply(
        ChatInput(message=message, draft=draft, briefing_id=saved["request_id"]), store
    )
    assert answer["action"] == "run"
    assert [site["name"] for site in answer["draft"]["locations"]] == expected
    assert answer["draft"]["date"] == draft.date
    assert answer["draft"]["time"] == draft.time
    assert answer["draft"]["timezone"] == draft.timezone


def test_site_aliases_do_not_change_selection_for_timezone_or_result_questions():
    draft = Draft(
        locations=[
            {"name": "Tempe Riverside", "latitude": 33.4255, "longitude": -111.94},
            {"name": "Scottsdale Courtyard", "latitude": 33.4942, "longitude": -111.9261},
        ]
    )
    assert extract_explicit("Make it 5pm Phoenix time", draft).locations == draft.locations
    assert (
        extract_explicit("Why is Tempe Riverside the lowest?", draft).locations == draft.locations
    )
    expanded = extract_explicit("Add Phoenix", draft)
    assert len(expanded.locations) == 3
    assert len({site.name for site in expanded.locations}) == 3


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Which one is hotter?", "Scottsdale Courtyard has the highest temperature"),
        ("Which is warmer?", "Scottsdale Courtyard has the highest temperature"),
        ("And which is cooler?", "Tempe Riverside has the lowest temperature"),
        ("Which one is colder?", "Tempe Riverside has the lowest temperature"),
    ],
)
async def test_comparative_followups_answer_from_saved_evidence(chat_store, message, expected):
    store, saved = chat_store
    draft = Draft.model_validate({key: saved["request"][key] for key in Draft.model_fields})
    answer = await reply(
        ChatInput(message=message, draft=draft, briefing_id=saved["request_id"]), store
    )
    assert answer["action"] == "answer"
    assert expected in answer["message"]
    assert answer["draft"]["locations"] == draft.model_dump()["locations"]
    assert "2025-09-20" in answer["message"]


@pytest.mark.parametrize("message", ["Actually make it 5pm", "Just Tempe and Scottsdale"])
async def test_refined_request_description_matches_current_details(chat_store, message):
    store, saved = chat_store
    draft = Draft.model_validate({key: saved["request"][key] for key in Draft.model_fields})
    draft.question = "Compare all three demo locations on September 20, 2025 at 2 pm Phoenix time"
    answer = await reply(
        ChatInput(message=message, draft=draft, briefing_id=saved["request_id"]), store
    )
    assert answer["action"] == "run"
    request = answer["draft"]
    assert request["date"] in request["question"]
    assert request["time"] in request["question"]
    assert request["timezone"] in request["question"]
    assert "2 pm" not in request["question"]
    assert "all three" not in request["question"]
    for site in request["locations"]:
        assert site["name"] in request["question"]


async def test_prepared_time_change_is_coherent_when_run_later(chat_store):
    store, saved = chat_store
    draft = Draft.model_validate({key: saved["request"][key] for key in Draft.model_fields})
    prepared = await reply(ChatInput(message="Just prepare; make it 5pm", draft=draft), store)
    assert prepared["action"] == "prepare"
    assert "17:00" in prepared["draft"]["question"]
    run = await reply(
        ChatInput(
            message="Run it",
            draft=Draft.model_validate(prepared["draft"]),
            pending_action="prepare",
        ),
        store,
    )
    assert run["action"] == "run"
    assert "17:00" in run["draft"]["question"]


async def test_just_tell_me_is_a_question_not_a_selection_change(chat_store):
    store, saved = chat_store
    draft = Draft.model_validate({key: saved["request"][key] for key in Draft.model_fields})
    answer = await reply(
        ChatInput(
            message="Just tell me why Tempe Riverside is the lowest",
            draft=draft,
            briefing_id=saved["request_id"],
        ),
        store,
    )
    assert answer["action"] == "answer"
    assert answer["draft"]["locations"] == draft.model_dump()["locations"]


@pytest.mark.parametrize(
    "message,expected",
    [
        ("hello", "Hi! I compare temperatures"),
        ("Thanks!", "You're welcome"),
        ("never mind", "Nothing is running"),
    ],
)
async def test_small_talk_gets_a_human_reply_not_a_field_checklist(chat_store, message, expected):
    answer = await reply(ChatInput(message=message), chat_store[0])
    assert answer["action"] == "answer"
    assert expected in answer["message"]
    assert "business question" not in answer["message"]


async def test_cancel_clears_a_pending_run(chat_store):
    answer = await reply(ChatInput(message="cancel", pending_action="run"), chat_store[0])
    assert answer["pending_action"] == "none"
    assert "cancelled" in answer["message"]


async def test_city_names_are_explained_and_exact_site_reply_runs(chat_store):
    store = chat_store[0]
    first = await reply(
        ChatInput(message="compare tempe and scottsdale on july 4 2026 at 3 pm phoenix time"),
        store,
    )
    assert first["action"] == "clarify"
    assert "city names" in first["message"]
    assert "Tempe Riverside and Scottsdale Courtyard" in first["suggestions"]
    second = await reply(
        ChatInput(
            message=first["suggestions"][0],
            draft=Draft.model_validate(first["draft"]),
            pending_action=first["pending_action"],
        ),
        store,
    )
    assert second["action"] == "run"
    assert [site["name"] for site in second["draft"]["locations"]] == [
        "Tempe Riverside",
        "Scottsdale Courtyard",
    ]


@pytest.mark.parametrize(
    "message,zone",
    [
        ("at 3pm pacific time", "America/Los_Angeles"),
        ("at 3pm MST", "America/Phoenix"),
        ("at 3pm Arizona time", "America/Phoenix"),
        ("at 3pm eastern", "America/New_York"),
        ("at 3pm america/phoenix", "America/Phoenix"),
    ],
)
def test_common_timezone_names(message, zone):
    assert (
        extract_explicit("Compare all demo sites on 2026-07-04 " + message, Draft()).timezone
        == zone
    )


def test_slash_like_words_are_not_timezones():
    draft = extract_explicit("Compare all demo sites and/or more on 2026-07-04", Draft())
    assert draft.timezone == ""


def test_iana_timezone_does_not_select_phoenix_civic_plaza():
    draft = Draft(
        locations=[site for site in extract_explicit("all demo sites", Draft()).locations]
    )
    changed = extract_explicit(
        "Compare Tempe Riverside and Scottsdale Courtyard at 5pm America/Phoenix", draft
    )
    assert [site.name for site in changed.locations] == ["Tempe Riverside", "Scottsdale Courtyard"]


@pytest.mark.parametrize(
    "text,expected",
    [("17/07/2026", "2026-07-17"), ("7/17/2026", "2026-07-17"), ("2026/07/04", "2026-07-04")],
)
def test_unambiguous_numeric_dates(text, expected):
    assert extract_explicit("Compare all demo sites on " + text, Draft()).date == expected


async def test_ambiguous_numeric_date_asks_which_one(chat_store):
    answer = await reply(
        ChatInput(message="Compare all demo sites on 07/04/2026 at 3pm Phoenix time"),
        chat_store[0],
    )
    assert answer["action"] == "clarify"
    assert answer["suggestions"] == ["July 4, 2026", "April 7, 2026"]


async def test_invalid_inputs_get_plain_explanations(chat_store):
    store = chat_store[0]
    clock = await reply(
        ChatInput(message="Compare all demo sites on 2026-07-04 at 25:00 Phoenix time"), store
    )
    assert "25:00 is not a valid time" in clock["message"]
    day = await reply(
        ChatInput(message="Compare all demo sites on February 30, 2026 at noon Phoenix time"),
        store,
    )
    assert "not a real calendar date" in day["message"]


def test_part_of_day_never_reuses_an_out_of_period_time():
    morning = Draft(time="08:00", date="2026-07-04", timezone="America/Phoenix")
    assert extract_explicit("same sites tomorrow afternoon", morning).time == ""
    afternoon = Draft(time="14:00", date="2026-07-04", timezone="America/Phoenix")
    assert extract_explicit("same sites tomorrow afternoon", afternoon).time == "14:00"


@pytest.mark.parametrize(
    "message,expected",
    [
        ("How hot was Tempe?", "Tempe Riverside read 34.1 °C, the lowest"),
        ("What was the temperature at Scottsdale?", "Scottsdale Courtyard read 36.7 °C"),
        ("Which is hotter, Tempe or Phoenix?", "Phoenix Civic Plaza is warmer"),
        ("Which is cooler, Phoenix or Scottsdale?", "Phoenix Civic Plaza is cooler"),
        ("What's the spread?", "The spread is 2.6 °C"),
        ("Show it in Fahrenheit", "°F"),
        ("Why is Scottsdale the hottest?", "can't say why"),
    ],
)
async def test_site_specific_followups_use_saved_readings(chat_store, message, expected):
    store, saved = chat_store
    draft = Draft.model_validate({key: saved["request"][key] for key in Draft.model_fields})
    answer = await reply(
        ChatInput(message=message, draft=draft, briefing_id=saved["request_id"]), store
    )
    assert answer["action"] == "answer"
    assert expected in answer["message"]
    assert answer["draft"]["locations"] == draft.model_dump()["locations"]
