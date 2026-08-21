"""Smoke test for the full grounded-chat pipeline.

Runs the real retrieval + PydanticAI agent + grounding validation against the
configured Supabase DB and OpenAI, then prints the generated answer with its
citations — the same path the chat API uses, minus message persistence. Not a
unit test — it hits network + DB + LLM.

Usage (from ``backend/``):

    uv run python scripts/smoke_chat.py "How many employees did Microsoft have in 2023?"

Run without a query to enter an interactive prompt that keeps asking questions:

    uv run python scripts/smoke_chat.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time

from app.chat.messages import TurnMessage
from app.chat.orchestrator import _best_relevance, default_agent, default_retriever
from app.config import settings
from app.grounding.validator import validate_grounding

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("smoke_chat")

SAMPLE_QUERIES = [
    "How many employees did Microsoft have in 2023?",
    "What are NVIDIA's main risk factors?",
    "How much revenue did NVIDIA report in the latest fiscal year?",
    "What did Microsoft say about its cloud and AI services?",
    "What legal proceedings is NVIDIA involved in?",
]


def _snippet(text: str, width: int = 160) -> str:
    return text.replace("\n", " ")[:width]


def _print_citation(i: int, citation) -> None:
    print(f"\n[{i + 1}] {citation.company_name} ({citation.ticker}) — {citation.filing_type} {citation.filing_date or citation.year}")
    print(f"    chunk_id={citation.chunk_id} page={citation.page} section={citation.section}")
    print(f"    {_snippet(citation.excerpt)}")


async def _answer(query: str) -> int:
    logger.info("Query: %s", query)
    retriever = default_retriever()
    agent = default_agent(retriever)

    start = time.perf_counter()
    passages = await retriever.retrieve(query)
    logger.info(
        "Retrieved %d passage(s) in %.2fs",
        len(passages),
        time.perf_counter() - start,
    )
    best = _best_relevance(passages)
    logger.info("Best relevance: %s", f"{best:.4f}" if best is not None else "n/a")
    if best is not None and best < settings.min_relevance_score:
        logger.warning(
            "Relevance %.4f below min %.4f — refusing without an LLM call",
            best,
            settings.min_relevance_score,
        )
        print("Insufficient evidence to answer (relevance too low).")
        print(f"Best relevance: {best:.4f} vs min {settings.min_relevance_score}")
        return 1

    start = time.perf_counter()
    logger.info("Generating answer via agent (model=%s)…", settings.openai_chat_model)
    answer, evidence = await agent.generate(
        [TurnMessage(role="user", content=query)], passages
    )
    logger.info(
        "Agent returned in %.2fs — %d evidence passage(s)",
        time.perf_counter() - start,
        len(evidence),
    )

    start = time.perf_counter()
    answer = validate_grounding(answer, evidence)
    logger.info(
        "Grounding validated in %.2fs — %d citation(s)",
        time.perf_counter() - start,
        len(answer.citations),
    )

    print(f"\nANSWER\n------\n{answer.answer}\n")

    if answer.insufficient_evidence:
        print("(Assistant declined: no citable evidence found.)")
    elif answer.citations:
        print(f"SOURCES ({len(answer.citations)})\n-------")
        for i, citation in enumerate(answer.citations):
            _print_citation(i, citation)
    return 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="question to answer")
    args = parser.parse_args()

    if args.query:
        return await _answer(args.query)

    print("Interactive mode — type a question, or 'q' to quit (Ctrl+C works too).\n")
    print("Sample questions to get started:")
    for q in SAMPLE_QUERIES:
        print(f"  • {q}")
    print()
    while True:
        try:
            query = input("> ").strip()
            if not query:
                continue
            if query.lower() in ("q", "quit", "exit"):
                return 0
            await _answer(query)
        except KeyboardInterrupt:
            print("\nQuit.")
            return 0
        except EOFError:
            print()
            return 0
        except Exception as exc:  # noqa: BLE001 — keep the interactive session alive
            print(f"Question failed ({type(exc).__name__}): {exc}")
            print("Try another question, or 'q' to quit.")
        print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(0)