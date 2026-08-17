import uuid
from datetime import date

import pytest

from app.assistant.outputs import Citation
from app.chat.messages import (
    ChatInputError,
    TurnMessage,
    UIMessage,
    from_ui_message,
    from_ui_messages,
    to_ui_message_json,
)


def _ui_message(*, role: str = "user", text: str = "hello", parts: list[dict] | None = None) -> UIMessage:
    return UIMessage(
        id="msg-1",
        role=role,
        parts=parts if parts is not None else [{"type": "text", "text": text}],
    )


def test_from_ui_message_extracts_role_and_text():
    message = from_ui_message(_ui_message(role="user", text="hello"))
    assert message == TurnMessage(role="user", content="hello")


def test_from_ui_message_concatenates_text_parts():
    message = from_ui_message(
        _ui_message(parts=[{"type": "text", "text": "foo "}, {"type": "text", "text": "bar"}])
    )
    assert message == TurnMessage(role="user", content="foo bar")


def test_from_ui_message_ignores_non_text_parts():
    message = from_ui_message(
        _ui_message(parts=[{"type": "text", "text": "hi"}, {"type": "data-citations", "data": {}}])
    )
    assert message.content == "hi"


def test_from_ui_message_rejects_unsupported_role():
    with pytest.raises(ChatInputError):
        from_ui_message(_ui_message(role="system"))


def test_from_ui_message_rejects_empty_content():
    with pytest.raises(ChatInputError):
        from_ui_message(_ui_message(text=""))


def test_from_ui_messages_preserves_order():
    messages = from_ui_messages(
        [_ui_message(role="user", text="q"), _ui_message(role="assistant", text="a")]
    )
    assert messages == [
        TurnMessage(role="user", content="q"),
        TurnMessage(role="assistant", content="a"),
    ]


def test_to_ui_message_json_without_citations():
    payload = to_ui_message_json(role="assistant", content="answer")
    assert payload == {
        "role": "assistant",
        "parts": [{"type": "text", "text": "answer"}],
    }


def test_to_ui_message_json_with_citations():
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
    payload = to_ui_message_json(role="assistant", content="answer", citations=[citation])
    parts = payload["parts"]
    assert parts[0] == {"type": "text", "text": "answer"}
    assert parts[1]["type"] == "data-citations"
    assert parts[1]["data"]["citations"] == [citation.to_dict()]