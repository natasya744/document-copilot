"""Quality gate vs the client brief.

Runs the ten example analyst questions plus out-of-corpus refusal probes
through the real pipeline (hybrid retrieval → grounded-answer agent → grounding
validation) and evaluates each result against the trust contract: answers must
be cited with filing + location, cross-year/cross-company questions must span
the corpus, and out-of-corpus questions must refuse instead of inventing.

This is a live harness — it hits the DB, OpenAI, and the LLM. It is not part of
the fast unit suite; the thin pytest wrapper lives behind
``@pytest.mark.integration`` and the CLI lives in ``backend/scripts/quality_gate.py``.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage
from app.chat.messages import TurnMessage
from app.chat.orchestrator import default_agent, default_retriever
from app.config import settings
from app.grounding.validator import validate_grounding

# The ten example analyst questions from docs/client-brief.md, verbatim.
BRIEF_QUESTIONS: list[str] = [
    "Across Apple's 2021-2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change, and which category appears to have contributed most to any mix shift?",
    "For Amazon, compare AWS operating income and margin against North America and International from 2021-2025. In which years did AWS appear to fund losses or weaker profitability elsewhere?",
    "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business from fiscal 2021 through fiscal 2025?",
    "Across Microsoft's 2021-2025 filings, what changed in the way the company describes Azure, AI infrastructure, and cloud capacity constraints?",
    "For Alphabet, how did Google Search, YouTube ads, Google Network, subscriptions/platforms/devices, and Google Cloud revenue trends differ across the available 10-Ks?",
    "Which of the five companies added, removed, or materially changed risk-factor language related to AI, cloud infrastructure, export controls, supply chain concentration, or regulation between 2021 and 2025?",
    "For Apple and NVIDIA, what do the filings say about supplier concentration or dependence on third-party manufacturing, and did the wording become more or less urgent over time?",
    "Compare capital expenditures and purchase commitments for Microsoft, Alphabet, Amazon, and NVIDIA. What do the filings imply about the scale and timing of AI/cloud infrastructure investment?",
    "For each company, summarize the most important geographic revenue exposures disclosed in the latest 10-K, then identify any year-over-year changes that could matter to an analyst.",
    "If an analyst asks whether the filings prove that generative AI improved margins for any of these companies, what evidence exists in the corpus, and where should the bot refuse to infer beyond the filings?",
]

# Out-of-corpus / beyond-corpus probes: the bot must refuse, not invent.
REFUSAL_PROBES: list[str] = [
    "What is the current stock price of Apple and should I buy shares?",
    "How much revenue did AMD report in its most recent quarter?",
    "What did analysts write about NVIDIA this week?",
    "What are the latest earnings estimates for Tesla?",
]

# Brief questions that ask for year-over-year trends and must span the corpus.
CROSS_YEAR_INDEXES = {1, 2, 3, 4, 5, 8}
# Brief questions that compare multiple companies and must span tickers.
CROSS_COMPANY_INDEXES = {6, 7}

# Phrases that mark an answer as declining to infer beyond the filings.
_HEDGE_PATTERNS = (
    r"\bdoes not provide evidence\b",
    r"\bno evidence\b",
    r"\bdoes not support\b",
    r"\bcannot (determine|be determined|establish)\b",
    r"\binsufficient\b",
    r"\bnot supported by the filings\b",
    r"\bthe filings do not\b",
    r"\bthe corpus does not\b",
    r"\bdo not prove\b",
    r"\bdoes not prove\b",
    r"\bunable to\b",
    r"\bbeyond the filings\b",
    r"\bcannot be inferred\b",
)
_HEDGE_RE = re.compile("|".join(_HEDGE_PATTERNS), re.IGNORECASE)


@dataclass
class Check:
    """One automated gate check for a single question."""

    name: str
    passed: bool
    detail: str = ""
    # Warnings (e.g. a known corpus gap) surface in the report but do not fail
    # the gate.
    is_warning: bool = False


@dataclass
class QuestionResult:
    """A question run through the pipeline plus its gate evaluation."""

    index: int | None
    question: str
    answer: GroundedAnswer
    evidence: list[SourcePassage]
    checks: list[Check] = field(default_factory=list)
    error: str | None = None
    elapsed_s: float = 0.0

    @property
    def all_passed(self) -> bool:
        return all(
            check.passed for check in self.checks if not check.is_warning
        )


def _best_relevance(passages: list[SourcePassage]) -> float | None:
    scored = [passage.score for passage in passages if passage.score is not None]
    return max(scored) if scored else None


def _hedged(text: str) -> list[str]:
    return list(dict.fromkeys(_HEDGE_RE.findall(text)))


def _distinct_years(citations: tuple[Citation, ...]) -> list[int]:
    return sorted({citation.year for citation in citations})


def _distinct_tickers(citations: tuple[Citation, ...]) -> list[str]:
    return sorted({citation.ticker for citation in citations})


async def run_question(query: str, *, index: int | None = None) -> QuestionResult:
    """Run one question through the full pipeline and return the gated result."""
    start = time.perf_counter()
    retriever = default_retriever()
    agent = default_agent(retriever)

    try:
        passages = await retriever.retrieve(query)
        best = _best_relevance(passages)
        if best is not None and best < settings.min_relevance_score:
            answer = GroundedAnswer(
                answer="Insufficient evidence to answer (relevance too low).",
                insufficient_evidence=True,
            )
            evidence = []
        else:
            answer, evidence = await agent.generate(
                [TurnMessage(role="user", content=query)], passages
            )
            answer = validate_grounding(answer, evidence)
    except Exception as exc:  # noqa: BLE001 — the harness reports, never crashes
        return QuestionResult(
            index=index,
            question=query,
            answer=GroundedAnswer(answer=""),
            evidence=[],
            error=f"{type(exc).__name__}: {exc}",
            elapsed_s=time.perf_counter() - start,
        )

    return QuestionResult(
        index=index,
        question=query,
        answer=answer,
        evidence=evidence,
        elapsed_s=time.perf_counter() - start,
    )


def evaluate(result: QuestionResult) -> None:
    """Populate ``result.checks`` from the pipeline output and brief rules."""
    answer = result.answer
    citations = answer.citations
    is_refusal = answer.insufficient_evidence
    hedges = _hedged(answer.answer)

    if result.error:
        result.checks.append(
            Check("ran_without_error", False, f"pipeline failed: {result.error}")
        )
        return

    result.checks.append(
        Check("ran_without_error", True, f"in {result.elapsed_s:.1f}s")
    )

    result.checks.append(
        Check(
            "cited_or_refused",
            bool(citations) or is_refusal,
            f"{len(citations)} citation(s)"
            + ("; explicit refusal" if is_refusal else "")
            + ("; no citations and no refusal" if not citations and not is_refusal else ""),
        )
    )

    if citations:
        missing_section = [
            c.ticker for c in citations if not c.section
        ]
        result.checks.append(
            Check(
                "citations_have_section",
                not missing_section,
                f"{len(citations) - len(missing_section)}/{len(citations)} cite a section",
            )
        )
        if all(not c.page for c in citations):
            result.checks.append(
                Check(
                    "citations_have_page",
                    False,
                    "no chunk carries page metadata (known corpus gap — "
                    "section-level location for the pilot)",
                    is_warning=True,
                )
            )
        else:
            result.checks.append(
                Check("citations_have_page", True, "page metadata present")
            )
    else:
        result.checks.append(
            Check("citations_have_section", is_refusal, "no citations (refusal)")
        )
        result.checks.append(
            Check("citations_have_page", is_refusal, "no citations (refusal)")
        )

    if result.index in CROSS_YEAR_INDEXES:
        years = _distinct_years(citations)
        result.checks.append(
            Check(
                "spans_years",
                len(years) >= 2,
                f"{len(years)} distinct year(s): {', '.join(map(str, years)) or 'none'}",
            )
        )
    if result.index in CROSS_COMPANY_INDEXES:
        tickers = _distinct_tickers(citations)
        result.checks.append(
            Check(
                "spans_companies",
                len(tickers) >= 2,
                f"{len(tickers)} distinct ticker(s): {', '.join(tickers) or 'none'}",
            )
        )

    # Q10 and every out-of-corpus probe must decline to go beyond the filings.
    if result.index == 10 or result.index is None:
        result.checks.append(
            Check(
                "refuses_beyond_corpus",
                is_refusal or bool(hedges),
                "explicit refusal"
                if is_refusal
                else f"hedge markers: {', '.join(hedges) or 'none found'}",
            )
        )

    if result.index is None and citations:
        result.checks.append(
            Check(
                "refusal_has_no_citations",
                False,
                "out-of-corpus probe answered with citations instead of refusing",
            )
        )


async def run_all() -> list[QuestionResult]:
    """Run the brief questions and the refusal probes, evaluated."""
    results: list[QuestionResult] = []
    for index, question in enumerate(BRIEF_QUESTIONS, start=1):
        result = await run_question(question, index=index)
        evaluate(result)
        results.append(result)
    for question in REFUSAL_PROBES:
        result = await run_question(question)
        evaluate(result)
        results.append(result)
    return results


def _citation_line(citation: Citation) -> str:
    location = citation.section or citation.page or "no location"
    return (
        f"    [{citation.ticker}] {citation.company_name} — {citation.filing_type} "
        f"{citation.year}-{citation.filing_date} · {location}"
    )


def render_report(results: list[QuestionResult]) -> str:
    """Render the gate report as text for the CLI / report file."""
    brief = [r for r in results if r.index is not None]
    probes = [r for r in results if r.index is None]
    lines = ["# Document Copilot — quality gate vs client brief", ""]
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M %Z')}")
    lines.append(
        f"Corpus: {len(brief) + len(probes)} questions · "
        f"{sum(1 for r in brief if r.all_passed)}/{len(brief)} brief passed · "
        f"{sum(1 for r in probes if r.all_passed)}/{len(probes)} probes refused cleanly"
    )
    lines.append("")

    for result in brief + probes:
        label = f"Q{result.index}" if result.index is not None else "PROBE"
        status = "PASS" if result.all_passed else "FAIL"
        lines.append(f"## {label} — {status}")
        lines.append(f"**{result.question}**")
        lines.append(f"({result.elapsed_s:.1f}s)")
        if result.error:
            lines.append(f"ERROR: {result.error}")
        for check in result.checks:
            mark = "PASS" if check.passed else ("WARN" if check.is_warning else "FAIL")
            lines.append(f"- [{mark}] {check.name}: {check.detail}")
        if result.answer.answer:
            snippet = " ".join(result.answer.answer.split())
            lines.append(f"- Answer: {snippet[:220]}{'…' if len(snippet) > 220 else ''}")
        if result.answer.citations:
            lines.append("- Sources:")
            for citation in result.answer.citations:
                lines.append(_citation_line(citation))
        lines.append("")

    passed_brief = sum(1 for r in brief if r.all_passed)
    passed_probes = sum(1 for r in probes if r.all_passed)
    lines.append("## Summary")
    lines.append(f"- Brief questions passed: {passed_brief}/{len(brief)}")
    lines.append(f"- Refusal probes passed: {passed_probes}/{len(probes)}")
    lines.append("- Page metadata: absent corpus-wide (section-level citations for the pilot)")
    lines.append("")
    return "\n".join(lines)