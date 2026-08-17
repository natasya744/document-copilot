import json
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage
from app.chat.messages import TurnMessage
from app.chat.orchestrator import run_turn

THREAD_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CHUNK_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
ASSISTANT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _passage() -> SourcePassage:
    return SourcePassage(
        chunk_id=CHUNK_1,
        document_id=DOCUMENT_ID,
        chunk_index=0,
        ticker="NVDA",
        company_name="NVIDIA Corp",
        filing_type="10-K",
        filing_date=date(2025, 1, 31),
        year=2025,
        page="p. 10",
        section="Risk Factors",
        text="Retrieved passage text.",
    )


class FakeRetriever:
    def __init__(self, passages):
        self.passages = passages
        self.queries = []

    async def retrieve(self, query):
        self.queries.append(query)
        return self.passages


class FakeAgent:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    async def generate(self, conversation, passages):
        self.calls.append((conversation, passages))
        return self.answer


def _assistant_row():
    return {"id": str(ASSISTANT_ID), "sequence_number": 2}


async def _collect(async_gen):
    return [line async for line in async_gen]


def _events(lines):
    return [json.loads(line[len("data: ") :].strip()) for line in lines]


@pytest.mark.asyncio
async def test_happy_path_persists_user_assistant_and_citations():
    agent = FakeAgent(
        GroundedAnswer(answer="Grounded answer.", citations=(Citation.from_passage(_passage()),))
    )
    retriever = FakeRetriever([_passage()])
    create_message = AsyncMock(return_value=_assistant_row())
    create_citation = AsyncMock(return_value={})

    with (
        patch("app.chat.orchestrator.chats.create_message", create_message),
        patch("app.chat.orchestrator.chats.create_citation", create_citation),
    ):
        lines = await _collect(
            run_turn(
                client=None,
                thread_id=THREAD_ID,
                incoming=[TurnMessage(role="user", content="What is the risk?")],
                prior_messages=[],
                retriever=retriever,
                agent=agent,
            )
        )

    assert create_message.await_count == 2
    user_kwargs = create_message.await_args_list[0].kwargs
    assistant_kwargs = create_message.await_args_list[1].kwargs
    assert user_kwargs["role"] == "user"
    assert user_kwargs["content"] == "What is the risk?"
    assert user_kwargs["sequence_number"] == 1
    assert assistant_kwargs["role"] == "assistant"
    assert assistant_kwargs["content"] == "Grounded answer."
    assert assistant_kwargs["sequence_number"] == 2
    assert assistant_kwargs["message_json"]["parts"][0] == {
        "type": "text",
        "text": "Grounded answer.",
    }

    citation_kwargs = create_citation.await_args_list[0].kwargs
    assert citation_kwargs["message_id"] == ASSISTANT_ID
    assert citation_kwargs["chunk_id"] == CHUNK_1
    assert citation_kwargs["document_id"] == DOCUMENT_ID
    assert citation_kwargs["metadata_"]["ticker"] == "NVDA"

    events = _events(lines)
    assert events[0]["type"] == "start"
    assert events[0]["messageId"] == str(ASSISTANT_ID)
    assert events[-1]["type"] == "finish"
    deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    assert "".join(deltas) == "Grounded answer."


@pytest.mark.asyncio
async def test_prior_messages_continue_sequence_numbering():
    agent = FakeAgent(
        GroundedAnswer(answer="Grounded answer.", citations=(Citation.from_passage(_passage()),))
    )
    retriever = FakeRetriever([_passage()])
    create_message = AsyncMock(return_value=_assistant_row())
    prior = [
        {"role": "user", "content": "old q", "sequence_number": 1},
        {"role": "assistant", "content": "old a", "sequence_number": 2},
    ]

    with (
        patch("app.chat.orchestrator.chats.create_message", create_message),
        patch("app.chat.orchestrator.chats.create_citation", AsyncMock(return_value={})),
    ):
        await _collect(
            run_turn(
                client=None,
                thread_id=THREAD_ID,
                incoming=[TurnMessage(role="user", content="new q")],
                prior_messages=prior,
                retriever=retriever,
                agent=agent,
            )
        )

    sequences = [call.kwargs["sequence_number"] for call in create_message.await_args_list]
    assert sequences == [3, 4]
    assert [call.kwargs["role"] for call in create_message.await_args_list] == [
        "user",
        "assistant",
    ]


@pytest.mark.asyncio
async def test_regenerate_with_assistant_last_skips_user_persist():
    agent = FakeAgent(
        GroundedAnswer(answer="Regenerated answer.", citations=(Citation.from_passage(_passage()),))
    )
    retriever = FakeRetriever([_passage()])
    create_message = AsyncMock(return_value=_assistant_row())
    incoming = [
        TurnMessage(role="user", content="q"),
        TurnMessage(role="assistant", content="old a"),
    ]

    with (
        patch("app.chat.orchestrator.chats.create_message", create_message),
        patch("app.chat.orchestrator.chats.create_citation", AsyncMock(return_value={})),
    ):
        await _collect(
            run_turn(
                client=None,
                thread_id=THREAD_ID,
                incoming=incoming,
                prior_messages=[],
                retriever=retriever,
                agent=agent,
            )
        )

    assert create_message.await_count == 1
    assert create_message.await_args_list[0].kwargs["role"] == "assistant"


@pytest.mark.asyncio
async def test_grounding_failure_emits_error_and_persists_nothing():
    agent = FakeAgent(
        GroundedAnswer(answer="Bad answer.", citations=(Citation.from_passage(_passage()),))
    )
    retriever = FakeRetriever([])
    create_message = AsyncMock()
    create_citation = AsyncMock()

    with (
        patch("app.chat.orchestrator.chats.create_message", create_message),
        patch("app.chat.orchestrator.chats.create_citation", create_citation),
    ):
        lines = await _collect(
            run_turn(
                client=None,
                thread_id=THREAD_ID,
                incoming=[TurnMessage(role="user", content="q")],
                prior_messages=[],
                retriever=retriever,
                agent=agent,
            )
        )

    assert _events(lines) == [
        {"type": "error", "errorText": "Answer cites a passage that was not retrieved"}
    ]
    create_message.assert_not_awaited()
    create_citation.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_incoming_messages_emits_error():
    agent = FakeAgent(GroundedAnswer(answer="n/a"))
    retriever = FakeRetriever([])
    create_message = AsyncMock()

    with patch("app.chat.orchestrator.chats.create_message", create_message):
        lines = await _collect(
            run_turn(
                client=None,
                thread_id=THREAD_ID,
                incoming=[],
                prior_messages=[],
                retriever=retriever,
                agent=agent,
            )
        )

    assert _events(lines) == [{"type": "error", "errorText": "Request contains no messages"}]
    create_message.assert_not_awaited()