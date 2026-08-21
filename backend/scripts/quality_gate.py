"""CLI for the quality gate (Phase 6).

Runs the ten client-brief questions plus out-of-corpus refusal probes through
the real pipeline and prints a pass/fail report. Exits non-zero when any brief
question or probe fails its checks.

Usage (from ``backend/``):

    uv run python scripts/quality_gate.py                 # full gate
    uv run python scripts/quality_gate.py --question 3    # one brief question
    uv run python scripts/quality_gate.py --report /tmp/gate.md
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.quality_gate import (
    BRIEF_QUESTIONS,
    REFUSAL_PROBES,
    QuestionResult,
    evaluate,
    render_report,
    run_question,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)


async def _run_one(index: int) -> list[QuestionResult]:
    if not 1 <= index <= len(BRIEF_QUESTIONS):
        raise SystemExit(f"Question index must be 1..{len(BRIEF_QUESTIONS)}")
    result = await run_question(BRIEF_QUESTIONS[index - 1], index=index)
    evaluate(result)
    return [result]


def _write_report(path: str, report: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(report)


async def _run_all_with_progress() -> list[QuestionResult]:
    """Run every question, printing a one-line marker as each one finishes."""
    results: list[QuestionResult] = []
    total = len(BRIEF_QUESTIONS) + len(REFUSAL_PROBES)
    for index, question in enumerate(BRIEF_QUESTIONS, start=1):
        result = await run_question(question, index=index)
        evaluate(result)
        results.append(result)
        print(f"  [{len(results)}/{total}] Q{index}: {result.elapsed_s:.1f}s")
    for question in REFUSAL_PROBES:
        result = await run_question(question)
        evaluate(result)
        results.append(result)
        print(f"  [{len(results)}/{total}] probe: {result.elapsed_s:.1f}s")
    return results


async def _run(args: argparse.Namespace) -> list[QuestionResult]:
    results = (
        await _run_one(args.question)
        if args.question
        else await _run_all_with_progress()
    )
    return results


def main() -> int:
    args = _parser().parse_args()
    try:
        results = asyncio.run(_run(args))
    except KeyboardInterrupt:
        raise SystemExit(130)
    report = render_report(results)
    print(report)
    if args.report:
        _write_report(args.report, report)
        print(f"\nWrote report to {args.report}")
    return 0 if all(result.all_passed for result in results) else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", type=int, help="run only one brief question (1-10)")
    parser.add_argument("--report", help="also write the report to this file")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())