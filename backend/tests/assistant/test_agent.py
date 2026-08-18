import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from app.assistant.agent import (
    DocAgentDeps,
    DocumentCopilotAgent,
    read_chunk,
    read_surrounding_chunks,
    search_filings,
)
from app.assistant.outputs import SourcePassage
from app.chat.messages import TurnMessage
from app.grounding.validator import GroundingError

CHUNK_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
CHUNK_B = uuid.UUID("22222222-2222-2222-2222-222222222222")
DOCUMENT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _passage(chunk_id: uuid.UUID) -> SourcePassage:
    return SourcePassage(
        chunk_id=chunk_id,
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
    def __init__(self, passages=()):
        self.passages = list(passages)
        self.queries = []

    async def retrieve(self, query):
        self.queries.append(query)
        return self.passages


def _agent(model: TestModel, retriever: FakeRetriever) -> DocumentCopilotAgent:
    return DocumentCopilotAgent(retriever=retriever, model=model)


def _ctx(deps: DocAgentDeps) -> RunContext[DocAgentDeps]:
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


async def _generate(
    agent: DocumentCopilotAgent, passages: list[SourcePassage]
):
    conversation = [TurnMessage(role="user", content="What is the risk?")]
    return await agent.generate(conversation, passages)


@pytest.mark.asyncio
async def test_generate_resolves_citations_and_returns_evidence():
    model = TestModel(
        call_tools=[],
        custom_output_args={"answer": "Grounded.", "citations": [CHUNK_A]},
    )
    agent = _agent(model, FakeRetriever())
    passage = _passage(CHUNK_A)

    answer, evidence = await _generate(agent, [passage])

    assert answer.answer == "Grounded."
    assert len(answer.citations) == 1
    citation = answer.citations[0]
    assert citation.chunk_id == CHUNK_A
    assert citation.ticker == "NVDA"
    assert citation.excerpt == passage.text
    assert [p.chunk_id for p in evidence] == [CHUNK_A]


@pytest.mark.asyncio
async def test_generate_rejects_citation_for_unretrieved_chunk():
    model = TestModel(
        call_tools=[],
        custom_output_args={"answer": "Bad.", "citations": [CHUNK_B]},
    )
    agent = _agent(model, FakeRetriever())

    with pytest.raises(GroundingError, match="was not retrieved"):
        await _generate(agent, [_passage(CHUNK_A)])


@pytest.mark.asyncio
async def test_generate_rejects_answer_without_citations():
    model = TestModel(call_tools=[], custom_output_args={"answer": "No cites."})
    agent = _agent(model, FakeRetriever())

    with pytest.raises(GroundingError, match="no citations"):
        await _generate(agent, [_passage(CHUNK_A)])


@pytest.mark.asyncio
async def test_generate_rejects_refusal_that_cites():
    model = TestModel(
        call_tools=[],
        custom_output_args={
            "answer": "I can't answer.",
            "citations": [CHUNK_A],
            "insufficient_evidence": True,
        },
    )
    agent = _agent(model, FakeRetriever())

    with pytest.raises(GroundingError, match="declines but still cites"):
        await _generate(agent, [_passage(CHUNK_A)])


@pytest.mark.asyncio
async def test_generate_allows_refusal_without_citations():
    model = TestModel(
        call_tools=[],
        custom_output_args={
            "answer": "Not in the corpus.",
            "insufficient_evidence": True,
        },
    )
    agent = _agent(model, FakeRetriever())

    answer, evidence = await _generate(agent, [_passage(CHUNK_A)])

    assert answer.insufficient_evidence is True
    assert answer.citations == ()
    assert [p.chunk_id for p in evidence] == [CHUNK_A]


@pytest.mark.asyncio
async def test_generate_uses_last_user_message_with_history():
    model = TestModel(
        call_tools=[],
        custom_output_args={"answer": "Grounded.", "citations": [CHUNK_A]},
    )
    retriever = FakeRetriever()
    agent = _agent(model, retriever)
    conversation = [
        TurnMessage(role="user", content="prior question"),
        TurnMessage(role="assistant", content="prior answer"),
        TurnMessage(role="user", content="current question"),
    ]

    answer, evidence = await agent.generate(conversation, [_passage(CHUNK_A)])

    assert answer.citations[0].chunk_id == CHUNK_A
    assert [p.chunk_id for p in evidence] == [CHUNK_A]


@pytest.mark.asyncio
async def test_search_filings_tool_appends_evidence():
    retriever = FakeRetriever([_passage(CHUNK_A)])
    deps = DocAgentDeps(retriever=retriever)

    out = await search_filings(_ctx(deps), "data center revenue", top_k=1)

    assert retriever.queries == ["data center revenue"]
    assert [p.chunk_id for p in deps.evidence] == [CHUNK_A]
    assert "11111111-1111-1111-1111-111111111111" in out


@pytest.mark.asyncio
async def test_read_chunk_tool_appends_passage():
    deps = DocAgentDeps(retriever=FakeRetriever())
    with patch("app.assistant.agent.fetch_chunk", AsyncMock(return_value=_passage(CHUNK_A))):
        out = await read_chunk(_ctx(deps), CHUNK_A)

    assert [p.chunk_id for p in deps.evidence] == [CHUNK_A]
    assert "Risk Factors" in out


@pytest.mark.asyncio
async def test_read_chunk_tool_returns_not_found():
    deps = DocAgentDeps(retriever=FakeRetriever())
    with patch("app.assistant.agent.fetch_chunk", AsyncMock(return_value=None)):
        out = await read_chunk(_ctx(deps), CHUNK_A)

    assert out == f"Chunk {CHUNK_A} not found."
    assert deps.evidence == []


@pytest.mark.asyncio
async def test_read_surrounding_chunks_tool_appends_passages():
    deps = DocAgentDeps(retriever=FakeRetriever())
    with patch(
        "app.assistant.agent.fetch_surrounding",
        AsyncMock(return_value=[_passage(CHUNK_A), _passage(CHUNK_B)]),
    ):
        out = await read_surrounding_chunks(_ctx(deps), CHUNK_A, window=1)

    assert [p.chunk_id for p in deps.evidence] == [CHUNK_A, CHUNK_B]
    assert "11111111-1111-1111-1111-111111111111" in out


@pytest.mark.asyncio
async def test_read_surrounding_chunks_tool_rejects_large_window():
    deps = DocAgentDeps(retriever=FakeRetriever())
    with patch("app.assistant.agent.fetch_surrounding", AsyncMock()) as fetch:
        out = await read_surrounding_chunks(_ctx(deps), CHUNK_A, window=10)

    assert out == "Error: window must be between 0 and 5."
    fetch.assert_not_awaited()
    assert deps.evidence == []