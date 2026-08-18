"""Hybrid retriever: query → ranked ``SourcePassage`` list.

Runs the pgvector and full-text queries independently, fuses the two ranked
lists with Reciprocal Rank Fusion, and re-derives the top passages with the
document metadata already joined in by ``app/retrieval/queries.py``.

Implements the ``Retriever`` Protocol from ``app/chat/orchestrator.py``, so the
existing turn lifecycle (and later the PydanticAI agent's ``search_filings``
tool) can consume it unchanged. Query functions and the embedder are injected
so the unit tests never touch the engine or OpenAI.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncConnection

from app.assistant.outputs import SourcePassage
from app.database.engine import get_engine
from app.retrieval.embedding import embed_query
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import keyword_search, row_to_passage, semantic_search

CANDIDATE_K = 50
TOP_K = 10

EmbedFunc = Callable[[str], Awaitable[list[float]]]
SemanticFunc = Callable[[AsyncConnection, list[float], int], Awaitable[list[dict]]]
KeywordFunc = Callable[[AsyncConnection, str, int], Awaitable[list[dict]]]


class HybridRetriever:
    """Embeds a query, searches semantically and by keyword, fuses by RRF."""

    def __init__(
        self,
        *,
        candidate_k: int = CANDIDATE_K,
        top_k: int = TOP_K,
        embed: EmbedFunc = embed_query,
        semantic_fn: SemanticFunc = semantic_search,
        keyword_fn: KeywordFunc = keyword_search,
    ) -> None:
        self._candidate_k = candidate_k
        self._top_k = top_k
        self._embed = embed
        self._semantic = semantic_fn
        self._keyword = keyword_fn

    async def retrieve(self, query: str) -> list[SourcePassage]:
        """Return up to ``top_k`` source passages ranked by RRF."""
        query_embedding = await self._embed(query)
        async with get_engine().connect() as conn:
            semantic = await self._semantic(conn, query_embedding, self._candidate_k)
            keyword = await self._keyword(conn, query, self._candidate_k)

        fused = reciprocal_rank_fusion(
            [
                [row["chunk_id"] for row in semantic],
                [row["chunk_id"] for row in keyword],
            ]
        )
        rows_by_chunk = {row["chunk_id"]: row for row in (*semantic, *keyword)}
        return [
            row_to_passage(rows_by_chunk[chunk_id])
            for chunk_id, _ in fused[: self._top_k]
        ]