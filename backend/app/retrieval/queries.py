"""Raw SQL retrieval queries over `document_chunks`.

Two bounded queries run independently and are fused in Python by Reciprocal
Rank Fusion (see ``app/retrieval/fusion.py``):

- ``semantic_search`` — pgvector cosine similarity over ``embedding`` (HNSW).
- ``keyword_search`` — Postgres full-text search over the generated
  ``search_vector`` (GIN), ranked with ``ts_rank``.

Both JOIN ``source_documents`` so every row carries the display metadata
needed to build a ``SourcePassage`` without a second fetch. They are pure SQL:
the caller owns the connection and the retriever owns the query embedding.

The ``fetch_*`` helpers additionally own the engine connection; they back the
agent's ``read_chunk`` / ``read_surrounding_chunks`` tools.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.assistant.outputs import SourcePassage
from app.config import settings
from app.database.engine import get_engine
from app.retrieval.keywords import extract_keywords

_COLUMNS = """
        c.id AS chunk_id,
        c.document_id,
        c.chunk_index,
        c.page,
        c.section,
        c.chunk_text,
        d.ticker,
        d.company_name,
        d.filing_type,
        d.filing_date,
        d.year
"""

_FROM_JOIN = """
    FROM document_chunks c
    JOIN source_documents d ON d.id = c.document_id
"""

_SELECT = "SELECT" + _COLUMNS + _FROM_JOIN


async def _rows(conn: AsyncConnection, sql: str, params: dict) -> list[dict]:
    result = await conn.execute(text(sql), params)
    return [dict(row) for row in result.mappings().all()]


def row_to_passage(row: dict) -> SourcePassage:
    """Map a query row (already joined to ``source_documents``) to a passage."""
    distance = row.get("distance")
    return SourcePassage(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        chunk_index=row["chunk_index"],
        ticker=row["ticker"],
        company_name=row["company_name"],
        filing_type=row["filing_type"],
        filing_date=row["filing_date"],
        year=row["year"],
        page=row["page"],
        section=row["section"],
        text=row["chunk_text"],
        score=1 - distance if distance is not None else None,
    )


async def chunk_with_context(
    conn: AsyncConnection, chunk_id: uuid.UUID
) -> dict | None:
    """Return one chunk with document metadata, or ``None`` when absent."""
    rows = await _rows(conn, _SELECT + " WHERE c.id = :chunk_id", {"chunk_id": chunk_id})
    return rows[0] if rows else None


async def surrounding_chunks(
    conn: AsyncConnection, chunk_id: uuid.UUID, window: int = 2
) -> list[dict]:
    """Return up to ``window`` chunks before and after ``chunk_id`` in its document.

    Ordered by chunk index. Returns ``[]`` when the chunk does not exist.
    """
    anchor = await _rows(
        conn,
        "SELECT document_id, chunk_index FROM document_chunks WHERE id = :chunk_id",
        {"chunk_id": chunk_id},
    )
    if not anchor:
        return []
    rows = await _rows(
        conn,
        _SELECT
        + """
            WHERE c.document_id = :document_id
              AND c.chunk_index BETWEEN :low AND :high
            ORDER BY c.chunk_index
        """,
        {
            "document_id": anchor[0]["document_id"],
            "low": anchor[0]["chunk_index"] - window,
            "high": anchor[0]["chunk_index"] + window,
        },
    )
    return rows


async def fetch_chunk(chunk_id: uuid.UUID) -> SourcePassage | None:
    """Fetch one chunk as a passage, or ``None`` when it does not exist."""
    async with get_engine().connect() as conn:
        row = await chunk_with_context(conn, chunk_id)
    return row_to_passage(row) if row else None


async def fetch_surrounding(
    chunk_id: uuid.UUID, window: int = 2
) -> list[SourcePassage]:
    """Fetch the passages surrounding ``chunk_id`` in its document."""
    async with get_engine().connect() as conn:
        rows = await surrounding_chunks(conn, chunk_id, window)
    return [row_to_passage(row) for row in rows]


async def semantic_search(
    conn: AsyncConnection, query_embedding: list[float], k: int
) -> list[dict]:
    """Top-``k`` chunks by cosine similarity to ``query_embedding``.

    ``query_embedding`` is passed as the ``"[0.1, 0.2, ...]"`` string form; the
    explicit ``::vector`` cast makes the coercion to the HNSW column type
    unambiguous.
    """
    sql = (
        "SELECT"
        + _COLUMNS
        + """
        , c.embedding <=> CAST(:query_embedding AS vector) AS distance
        """
        + _FROM_JOIN
        + """
        ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :k
    """
    )
    return await _rows(
        conn,
        sql,
        {
            "query_embedding": "[" + ",".join(f"{v:.8f}" for v in query_embedding) + "]",
            "k": k,
        },
    )


async def keyword_search(conn: AsyncConnection, query: str, k: int) -> list[dict]:
    """Top-``k`` chunks by full-text rank against ``query``.

    ``extract_keywords`` narrows the user query to meaningful content terms
    (see ``app/retrieval/keywords.py``); they are OR-combined with
    ``to_tsquery`` for recall, since the semantic leg already covers precision.
    ``'english'`` matches the config used to generate ``search_vector``. When
    nothing meaningful survives extraction, falls back to ``plainto_tsquery``
    over the raw query.
    """
    terms = extract_keywords(query, max_terms=settings.retrieval_keyword_max_terms)
    if terms:
        sql = _SELECT + """
            , ts_rank(c.search_vector, to_tsquery('english', :query)) AS rank
            WHERE c.search_vector @@ to_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :k
        """
        return await _rows(conn, sql, {"query": "|".join(terms), "k": k})
    sql = _SELECT + """
        , ts_rank(c.search_vector, plainto_tsquery('english', :query)) AS rank
        WHERE c.search_vector @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :k
    """
    return await _rows(conn, sql, {"query": query, "k": k})
