"""Rule-based keyword extraction for the full-text search leg.

`extract_keywords` turns a free-form user query into a small set of content
terms for `to_tsquery`, so a verbose question ("How many employees did
Microsoft have in 2023?") becomes `employees | microsoft | 2023` instead of a
wide AND over every token. Pure logic, no I/O and no LLM: deterministic and
free, so it runs on every query without touching the network.

Terms are sanitized to `[a-z0-9]` (via the tokenizer), so joining them with
``|`` is safe for `to_tsquery` — there is no operator-injection surface.
"""

from __future__ import annotations

import re

# Query-word stopwords. Kept deliberately small and focused on question phrasing;
# domain words like "revenue" or "risk" are meaningful and must survive.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "in",
        "into",
        "is",
        "it",
        "its",
        "many",
        "much",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "them",
        "there",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "would",
    }
)

_TOKEN = re.compile(r"[a-z0-9]+")


def extract_keywords(query: str, *, max_terms: int = 5) -> list[str]:
    """Return up to ``max_terms`` content terms from ``query``, best first.

    Lowercases and tokenizes on non-alphanumeric boundaries, drops stopwords,
    tokens shorter than three characters, and pure numbers (4-digit years are
    kept — they matter in filing queries). Deduped, order-preserving. Returns
    ``[]`` when nothing meaningful survives.
    """
    seen: set[str] = set()
    terms: list[str] = []
    for token in _TOKEN.findall(query.lower()):
        if token in seen or token in _STOPWORDS:
            continue
        if len(token) < 3:
            continue
        if token.isdigit() and len(token) != 4:
            continue
        seen.add(token)
        terms.append(token)
        if len(terms) == max_terms:
            break
    return terms