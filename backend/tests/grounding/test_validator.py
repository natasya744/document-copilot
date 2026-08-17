import uuid
from datetime import date

import pytest

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage
from app.grounding.validator import GroundingError, validate_grounding

CHUNK_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
CHUNK_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
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


def _citation(chunk_id: uuid.UUID) -> Citation:
    return Citation.from_passage(_passage(chunk_id))


def test_citation_mapping_to_retrieved_passage_normalizes_display_fields():
    answer = GroundedAnswer(
        answer="Some answer.",
        citations=(Citation(chunk_id=CHUNK_1, document_id=uuid.uuid4(), ticker="", company_name="", filing_type="", filing_date=date(1970, 1, 1), year=0, page=None, section=None, excerpt="ignored"),),
    )
    result = validate_grounding(answer, [_passage(CHUNK_1)])
    assert result.answer == "Some answer."
    assert len(result.citations) == 1
    citation = result.citations[0]
    assert citation.chunk_id == CHUNK_1
    assert citation.document_id == DOCUMENT_ID
    assert citation.ticker == "NVDA"
    assert citation.company_name == "NVIDIA Corp"
    assert citation.filing_date == date(2025, 1, 31)
    assert citation.year == 2025
    assert citation.page == "p. 10"
    assert citation.section == "Risk Factors"
    assert citation.excerpt == "Retrieved passage text."


def test_citation_for_unretrieved_chunk_is_rejected():
    answer = GroundedAnswer(answer="Some answer.", citations=(_citation(CHUNK_1),))
    with pytest.raises(GroundingError):
        validate_grounding(answer, [_passage(CHUNK_2)])


def test_answer_without_citations_is_rejected():
    with pytest.raises(GroundingError):
        validate_grounding(GroundedAnswer(answer="Some answer."), [_passage(CHUNK_1)])


def test_insufficient_evidence_without_citations_is_allowed():
    result = validate_grounding(
        GroundedAnswer(answer="Not enough evidence.", insufficient_evidence=True),
        [_passage(CHUNK_1)],
    )
    assert result.insufficient_evidence is True
    assert result.citations == ()


def test_insufficient_evidence_with_citations_is_rejected():
    with pytest.raises(GroundingError):
        validate_grounding(
            GroundedAnswer(
                answer="Not enough evidence.",
                citations=(_citation(CHUNK_1),),
                insufficient_evidence=True,
            ),
            [_passage(CHUNK_1)],
        )