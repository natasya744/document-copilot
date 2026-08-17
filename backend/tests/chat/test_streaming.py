import json
import uuid
from datetime import date

from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.streaming import answer_events, error_event

MESSAGE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _answer(*, citations: bool = False) -> GroundedAnswer:
    citation = None
    if citations:
        citation = Citation(
            chunk_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            document_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            ticker="NVDA",
            company_name="NVIDIA Corp",
            filing_type="10-K",
            filing_date=date(2025, 1, 31),
            year=2025,
            page="p. 10",
            section="Risk Factors",
            excerpt="Passage text.",
        )
    return GroundedAnswer(answer="Hello world", citations=(citation,) if citation else ())


def _parse(events: list[str]) -> list[dict]:
    parsed = []
    for event in events:
        assert event.startswith("data: ")
        assert event.endswith("\n\n")
        parsed.append(json.loads(event[len("data: ") :].strip()))
    return parsed


def test_answer_events_match_ui_message_chunk_shape():
    events = _parse(list(answer_events(_answer(), MESSAGE_ID)))
    assert [event["type"] for event in events] == [
        "start",
        "text-start",
        "text-delta",
        "text-end",
        "finish",
    ]
    assert events[0]["messageId"] == MESSAGE_ID
    assert events[1]["id"] == events[2]["id"] == events[3]["id"]
    assert events[-1] == {"type": "finish", "finishReason": "stop"}


def test_answer_events_reassemble_text():
    events = _parse(list(answer_events(_answer(), MESSAGE_ID)))
    deltas = [event["delta"] for event in events if event["type"] == "text-delta"]
    assert "".join(deltas) == "Hello world"


def test_answer_events_with_citations_include_data_part():
    events = _parse(list(answer_events(_answer(citations=True), MESSAGE_ID)))
    citation_event = next(event for event in events if event["type"] == "data-citations")
    assert citation_event["id"] == "citations-0"
    assert citation_event["data"]["citations"][0]["ticker"] == "NVDA"


def test_answer_events_without_citations_skip_data_part():
    events = _parse(list(answer_events(_answer(), MESSAGE_ID)))
    assert all(event["type"] != "data-citations" for event in events)


def test_error_event_shape():
    event = error_event("Something went wrong")
    parsed = _parse([event])
    assert parsed == [{"type": "error", "errorText": "Something went wrong"}]