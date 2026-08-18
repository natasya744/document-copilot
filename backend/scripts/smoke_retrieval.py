"""Smoke test for the live hybrid retriever.

Runs the real ``HybridRetriever`` against the configured Supabase DB and OpenAI
embeddings and prints the top passages, so a human can eyeball whether retrieval
actually works. Not a unit test — it hits network + DB.

Usage (from ``backend/``):

    uv run python scripts/smoke_retrieval.py "revenue growth in 2023"
"""

from __future__ import annotations

import argparse
import asyncio

from app.retrieval.retriever import HybridRetriever


def _snippet(text: str, width: int = 220) -> str:
    return text.replace("\n", " ")[:width]


def _print_passage(i: int, p) -> None:
    score = f"{p.score:.4f}" if p.score is not None else "n/a"
    print(f"\n[{i + 1}] score={score}")
    print(f"    {p.company_name} ({p.ticker}) — {p.filing_type} {p.filing_date or p.year}")
    print(f"    chunk_id={p.chunk_id} page={p.page} section={p.section}")
    print(f"    {_snippet(p.text)}")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="question to retrieve passages for")
    parser.add_argument("--top-k", type=int, default=5, help="passages to print")
    args = parser.parse_args()

    retriever = HybridRetriever()
    passages = await retriever.retrieve(args.query)

    if not passages:
        print("No passages retrieved.")
        return 1

    print(f"Retrieved {len(passages)} passage(s) for: {args.query}")
    for i, passage in enumerate(passages[: args.top_k]):
        _print_passage(i, passage)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
