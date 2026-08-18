import uuid
from datetime import date

import pytest

from app.retrieval.retriever import HybridRetriever

CHUNK_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
CHUNK_B = uuid.UUID("22222222-2222-2222-2222-222222222222")
CHUNK_C = uuid.UUID("33333333-3333-3333-3333-333333333333")
DOCUMENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _row(chunk_id, *, page="p. 10", section="Risk Factors"):
    return {
        "chunk_id": chunk_id,
        "document_id": DOCUMENT_ID,
        "chunk_index": 0,
        "page": page,
        "section": section,
        "chunk_text": f"Passage text for {chunk_id}.",
        "ticker": "NVDA",
        "company_name": "NVIDIA Corp",
        "filing_type": "10-K",
        "filing_date": date(2025, 1, 31),
        "year": 2025,
    }


class RecordingQueries:
    """Async stand-ins for the real query functions; records their arguments."""

    def __init__(self, semantic_rows, keyword_rows):
        self.semantic_rows = semantic_rows
        self.keyword_rows = keyword_rows
        self.semantic_calls = []
        self.keyword_calls = []

    async def semantic(self, conn, embedding, k):
        self.semantic_calls.append({"embedding": embedding, "k": k})
        return self.semantic_rows

    async def keyword(self, conn, query, k):
        self.keyword_calls.append({"query": query, "k": k})
        return self.keyword_rows


async def _fake_embed(text):
    return [0.1, 0.2, 0.3]


def _retriever(queries, **kwargs):
    return HybridRetriever(
        embed=_fake_embed,
        semantic_fn=queries.semantic,
        keyword_fn=queries.keyword,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_retrieve_fuses_rankings_in_rrf_order():
    queries = RecordingQueries(
        semantic_rows=[_row(CHUNK_A), _row(CHUNK_B)],
        keyword_rows=[_row(CHUNK_B), _row(CHUNK_C)],
    )
    passages = await _retriever(queries).retrieve("query text")

    # RRF: A 1/61; B 1/61 + 1/62; C 1/62  →  order B, A, C, deduped.
    assert [p.chunk_id for p in passages] == [CHUNK_B, CHUNK_A, CHUNK_C]
    assert passages[0].text == f"Passage text for {CHUNK_B}."
    assert len(passages) == 3


@pytest.mark.asyncio
async def test_retrieve_truncates_to_top_k():
    queries = RecordingQueries(
        semantic_rows=[_row(CHUNK_A), _row(CHUNK_B)],
        keyword_rows=[_row(CHUNK_B), _row(CHUNK_C)],
    )
    passages = await _retriever(queries, top_k=1).retrieve("query text")

    assert [p.chunk_id for p in passages] == [CHUNK_B]


@pytest.mark.asyncio
async def test_retrieve_returns_empty_when_no_results():
    queries = RecordingQueries(semantic_rows=[], keyword_rows=[])
    passages = await _retriever(queries).retrieve("query text")

    assert passages == []


@pytest.mark.asyncio
async def test_embedding_and_query_are_forwarded_to_queries():
    queries = RecordingQueries(
        semantic_rows=[_row(CHUNK_A)],
        keyword_rows=[_row(CHUNK_B)],
    )
    await _retriever(queries, candidate_k=12).retrieve("some query")

    assert queries.semantic_calls == [{"embedding": [0.1, 0.2, 0.3], "k": 12}]
    assert queries.keyword_calls == [{"query": "some query", "k": 12}]


@pytest.mark.asyncio
async def test_passage_carries_full_document_metadata():
    queries = RecordingQueries(
        semantic_rows=[_row(CHUNK_A, page=None, section="Management's Discussion")],
        keyword_rows=[],
    )
    passages = await _retriever(queries).retrieve("query text")

    passage = passages[0]
    assert passage.chunk_id == CHUNK_A
    assert passage.document_id == DOCUMENT_ID
    assert passage.ticker == "NVDA"
    assert passage.company_name == "NVIDIA Corp"
    assert passage.filing_type == "10-K"
    assert passage.filing_date == date(2025, 1, 31)
    assert passage.year == 2025
    assert passage.page is None
    assert passage.section == "Management's Discussion"
    assert passage.text == f"Passage text for {CHUNK_A}."