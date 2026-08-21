"""Reciprocal Rank Fusion for hybrid retrieval.

Fuses ranked lists of document-chunk ids by rank position rather than raw
score, so the unbounded full-text ranking and cosine similarity can be combined
on equal footing:

    rrf_score(d) = sum over each retriever r of 1 / (k + rank_r(d))

``k`` is a smoothing constant, conventionally 60 (Cormack et al., SIGIR 2009).
Pure logic, no I/O: fully unit-testable without a database.
"""

from __future__ import annotations

from collections import defaultdict

from app.config import settings


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = settings.retrieval_rrf_k
) -> list[tuple[str, float]]:
    """Fuse ranked lists of chunk ids into one score-ordered list.

    Each ranking is ordered best-first. A chunk appearing in multiple rankings
    accumulates a contribution from each; chunks are emitted in descending
    fused score with no duplicates.
    """
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: -item[1])