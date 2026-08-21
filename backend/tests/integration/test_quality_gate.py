"""Integration gate vs the client brief (Phase 6).

Runs the ten example analyst questions plus the out-of-corpus refusal probes
through the real pipeline and asserts the trust contract holds. This is a live
test: it needs working Supabase + OpenAI credentials and takes minutes to run.

Run explicitly with:

    uv run pytest tests/integration -m integration -q
"""

from __future__ import annotations

import pytest

from app.quality_gate import (
    BRIEF_QUESTIONS,
    CROSS_COMPANY_INDEXES,
    CROSS_YEAR_INDEXES,
    REFUSAL_PROBES,
    QuestionResult,
    evaluate,
    run_question,
)

pytestmark = pytest.mark.integration


async def _run_brief() -> list[QuestionResult]:
    results = []
    for index, question in enumerate(BRIEF_QUESTIONS, start=1):
        result = await run_question(question, index=index)
        evaluate(result)
        results.append(result)
    return results


async def _run_probes() -> list[QuestionResult]:
    results = []
    for question in REFUSAL_PROBES:
        result = await run_question(question)
        evaluate(result)
        results.append(result)
    return results


def _check(result: QuestionResult, name: str):
    return next(c for c in result.checks if c.name == name)


async def test_brief_questions_pass_the_gate():
    results = await _run_brief()
    assert len(results) == len(BRIEF_QUESTIONS)

    failures = [
        (r.index, r.question, [(c.name, c.detail) for c in r.checks if not c.passed])
        for r in results
        if not r.all_passed
    ]
    assert not failures, f"{len(failures)} brief question(s) failed: {failures}"


async def test_brief_questions_never_errored():
    results = await _run_brief()
    errored = [r.index for r in results if r.error]
    assert not errored, f"pipeline errors on: {errored}"


async def test_cross_year_questions_span_at_least_two_years():
    results = await _run_brief()
    for index in CROSS_YEAR_INDEXES:
        assert _check(results[index - 1], "spans_years").passed, (
            f"Q{index} should cite multiple filing years"
        )


async def test_cross_company_questions_span_multiple_tickers():
    results = await _run_brief()
    for index in CROSS_COMPANY_INDEXES:
        assert _check(results[index - 1], "spans_companies").passed, (
            f"Q{index} should cite multiple companies"
        )


async def test_beyond_filings_question_refuses_causal_inference():
    results = await _run_brief()
    assert _check(results[9], "refuses_beyond_corpus").passed, (
        "Q10 must refuse to infer beyond the filings"
    )


async def test_out_of_corpus_probes_refuse():
    results = await _run_probes()
    assert len(results) == len(REFUSAL_PROBES)
    failed = [
        (r.question, [(c.name, c.detail) for c in r.checks if not c.passed])
        for r in results
        if not r.all_passed
    ]
    assert not failed, f"probe(s) did not refuse cleanly: {failed}"