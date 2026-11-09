import json

import httpx

from heatbrief.assistant import CATALOG, ChatInput, Draft, extract_explicit, model_intake, reply
from heatbrief.store import Store


def test_explicit_intake_keeps_missing_fields_missing():
    draft = extract_explicit("Compare the three demo sites for our event", Draft())
    assert len(draft.locations) == 3
    assert draft.timezone == ""
    assert draft.date == ""
    assert draft.time == ""


def test_date_time_and_exact_timezone():
    draft = extract_explicit(
        "Compare the three demo sites on September 20, 2025 at 2pm America/Phoenix", Draft()
    )
    assert draft.date == "2025-09-20"
    assert draft.time == "14:00"
    assert draft.timezone == "America/Phoenix"


async def test_ambiguous_city_names_require_named_sites(tmp_path, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_ASSISTANT_MODE", "guided")
    response = await reply(
        ChatInput(message="Compare Phoenix and Tempe for a site visit"), Store(tmp_path)
    )
    assert response["draft"]["locations"] == []
    assert response["ready"] is False
    assert "named locations" in " ".join(response["missing_fields"])


async def test_guided_ready_request_and_safety_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_ASSISTANT_MODE", "guided")
    response = await reply(
        ChatInput(
            message=(
                "Compare the three demo sites on 2025-09-20 at 14:00 America/Phoenix for our visit"
            )
        ),
        Store(tmp_path),
    )
    assert response["ready"] is True
    assert response["mode"] == "guided"
    safety = await reply(ChatInput(message="Is it safe to work outdoors?"), Store(tmp_path))
    assert "cannot establish" in safety["message"]


async def test_openai_connector_uses_structured_output_without_storing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("HEATBRIEF_LLM_MODEL", "test-model")

    async def provider(request):
        payload = json.loads(request.content)
        assert payload["store"] is False
        assert payload["text"]["format"]["strict"] is True
        assert payload["text"]["format"]["schema"]["additionalProperties"] is False
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "message": "What date and timezone?",
                                        "question": "Compare the three demo sites for a visit",
                                        "client_name": None,
                                    }
                                ),
                            }
                        ],
                    }
                ]
            },
        )

    result = await model_intake("Compare the demo sites", Draft(), httpx.MockTransport(provider))
    assert result.client_name is None
    assert "timezone" in result.message


async def test_complete_form_respects_dst_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("HEATBRIEF_ASSISTANT_MODE", "guided")
    response = await reply(
        ChatInput(
            message="Prepare the briefing",
            draft=Draft(
                question="Compare the three sites for our visit",
                locations=CATALOG,
                date="2025-11-02",
                time="01:30",
                timezone="America/New_York",
            ),
        ),
        Store(tmp_path),
    )
    assert response["ready"] is False
    assert any("ambiguous" in error for error in response["validation_errors"])
