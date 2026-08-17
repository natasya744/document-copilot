"""Temporary grounded-answer stubs for Phase 5 UI development.

Stand-ins for the Phase 3 retriever and Phase 4 PydanticAI agent until those
land. They produce a fixed, realistic grounded answer so the frontend
streaming, citation panel, and persistence paths can be exercised end-to-end
without a live OpenAI call or a populated retrieval index. The answer is
clearly labeled as a stub so nobody mistakes it for real analysis.
"""

from __future__ import annotations

import uuid
from datetime import date

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage

_REFUSAL_MARKERS = ("not in the filings", "outside the corpus")


def _passages() -> list[SourcePassage]:
    return [
        SourcePassage(
            chunk_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            document_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            chunk_index=0,
            ticker="NVDA",
            company_name="NVIDIA Corp",
            filing_type="10-K",
            filing_date=date(2025, 1, 31),
            year=2025,
            page="p. 10",
            section="Risk Factors",
            text="NVIDIA's operations are exposed to supply chain constraints, "
            "customer concentration, and geopolitical export-control changes.",
        ),
        SourcePassage(
            chunk_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            document_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            chunk_index=1,
            ticker="NVDA",
            company_name="NVIDIA Corp",
            filing_type="10-K",
            filing_date=date(2025, 1, 31),
            year=2025,
            page="p. 42",
            section="Management's Discussion",
            text="Data center revenue grew substantially during the fiscal year, "
            "driven by accelerated computing and AI infrastructure demand.",
        ),
    ]


class StubRetriever:
    """Returns the fixed stub passages regardless of the query."""

    async def retrieve(self, query: str) -> list[SourcePassage]:
        return _passages()


class StubAgent:
    """Returns a canned grounded answer citing the stub passages."""

    async def generate(
        self, conversation, passages: list[SourcePassage]
    ) -> GroundedAnswer:
        last_user = next(
            (m.content for m in reversed(conversation) if m.role == "user"),
            "",
        )
        if any(marker in last_user.lower() for marker in _REFUSAL_MARKERS):
            return GroundedAnswer(
                answer=(
                    "I can't answer that from the filings in the corpus. The "
                    "retrieved passages do not contain enough evidence to "
                    "support a grounded response."
                ),
                insufficient_evidence=True,
            )
        answer = (
            f'On "{last_user}", the most relevant discussion is in NVIDIA\'s '
            "FY2025 10-K. The Risk Factors section (p. 10) covers supply chain "
            "and customer concentration risks, and Management's Discussion "
            "(p. 42) reports strong data center revenue growth. Stub answer "
            "for UI development — the real retriever and agent will ground "
            "this in the actual corpus."
        )
        return GroundedAnswer(
            answer=answer,
            citations=tuple(Citation.from_passage(p) for p in passages),
        )