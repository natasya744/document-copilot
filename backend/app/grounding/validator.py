"""Grounding enforcement — the trust contract.

An assistant answer may only cite passages that were retrieved for the current
request. An answer without citations is only acceptable when it explicitly
declines for insufficient evidence, and a declining answer must not cite
anything. Display metadata is re-derived from the retrieved passage, never from
the model, so a citation cannot carry fabricated company/filing/page details.

Pure logic, no I/O: the contract is unit-tested without a database or LLM.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage


class GroundingError(Exception):
    """Raised when an answer fails the grounding contract.

    The orchestrator converts this into a streamed error event; nothing is
    persisted.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def validate_grounding(
    answer: GroundedAnswer, retrieved: Sequence[SourcePassage]
) -> GroundedAnswer:
    """Enforce the citation contract and return a normalized answer.

    The returned answer's citations are rebuilt from ``retrieved`` so display
    fields and excerpts come from the passages, not from the model.
    """
    passages_by_chunk = {passage.chunk_id: passage for passage in retrieved}

    if answer.insufficient_evidence:
        if answer.citations:
            raise GroundingError("Answer declines but still cites sources")
        return answer

    if not answer.citations:
        raise GroundingError("Answer has no citations")

    for citation in answer.citations:
        if citation.chunk_id not in passages_by_chunk:
            raise GroundingError("Answer cites a passage that was not retrieved")

    normalized = tuple(
        Citation.from_passage(passages_by_chunk[citation.chunk_id])
        for citation in answer.citations
    )
    return replace(answer, citations=normalized)