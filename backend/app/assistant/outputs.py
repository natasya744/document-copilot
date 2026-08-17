"""Shared types for the grounded-answer pipeline.

These are the contract between retrieval, the assistant agent, grounding
validation, streaming, and persistence. They are deliberately pure — no I/O —
so every stage is unit-testable without a database or LLM.

The agent is trusted only for *which* retrieved chunks it cites. Display
metadata and excerpts are re-derived from the retrieved passage by
`app/grounding/validator.py`, so nothing in a citation is fabricated.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SourcePassage:
    """One retrieved chunk with the document metadata needed for display."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    ticker: str
    company_name: str
    filing_type: str
    filing_date: date
    year: int
    page: str | None
    section: str | None
    text: str


@dataclass(frozen=True)
class Citation:
    """A reference to a retrieved passage, fully resolved for display."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    ticker: str
    company_name: str
    filing_type: str
    filing_date: date
    year: int
    page: str | None
    section: str | None
    excerpt: str

    @classmethod
    def from_passage(cls, passage: SourcePassage, *, excerpt: str | None = None) -> Citation:
        """Build a citation from a passage, using the passage text as the excerpt."""
        return cls(
            chunk_id=passage.chunk_id,
            document_id=passage.document_id,
            ticker=passage.ticker,
            company_name=passage.company_name,
            filing_type=passage.filing_type,
            filing_date=passage.filing_date,
            year=passage.year,
            page=passage.page,
            section=passage.section,
            excerpt=passage.text if excerpt is None else excerpt,
        )

    def to_dict(self) -> dict:
        """Wire shape (camelCase) sent to the frontend in the stream."""
        return {
            "chunkId": str(self.chunk_id),
            "documentId": str(self.document_id),
            "ticker": self.ticker,
            "companyName": self.company_name,
            "filingType": self.filing_type,
            "filingDate": self.filing_date.isoformat(),
            "year": self.year,
            "page": self.page,
            "section": self.section,
            "excerpt": self.excerpt,
        }

    def display_metadata(self) -> dict:
        """Display fields stored in the ``message_citations.metadata`` JSONB."""
        return {
            "ticker": self.ticker,
            "companyName": self.company_name,
            "filingType": self.filing_type,
            "filingDate": self.filing_date.isoformat(),
            "year": self.year,
            "page": self.page,
            "section": self.section,
        }


@dataclass(frozen=True)
class GroundedAnswer:
    """An answer plus the citations it relies on.

    ``insufficient_evidence`` marks a refusal: the answer states the corpus
    does not support an answer, so it must carry no citations.
    """

    answer: str
    citations: tuple[Citation, ...] = ()
    insufficient_evidence: bool = False