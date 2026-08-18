"""Async OpenAI query embedding for retrieval.

The request path must not block on network I/O, so this mirrors
``ingest/embeddings.py`` (which is sync for the one-off scripts) with an
``AsyncOpenAI`` client bound to the same configured model and dimensions.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


async def embed_query(text: str) -> list[float]:
    """Embed a single query with the configured model (1536-dim)."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await _client.embeddings.create(
        model=settings.openai_embedding_model,
        input=[text],
        dimensions=settings.openai_embedding_dimensions,
    )
    return response.data[0].embedding
