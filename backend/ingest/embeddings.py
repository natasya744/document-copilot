"""OpenAI embeddings for document chunks.

Uses the configured ``text-embedding-3-small`` model with an explicit
dimensions argument so the vector always matches the ``vector(1536)`` column.
Requests are batched to stay well under the API's per-call input limit.
"""
from __future__ import annotations

from openai import OpenAI

from app.config import settings

BATCH_SIZE = 128


class Embedder:
    """Sync OpenAI embeddings client bound to the configured model."""

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model
        self._dimensions = settings.openai_embedding_dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            response = self._client.embeddings.create(
                model=self._model,
                input=batch,
                dimensions=self._dimensions,
            )
            vectors.extend(item.embedding for item in response.data)
        return vectors

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]