"""Chunking for SEC 10-K filings using Docling's chunkers.

Two chunkers work together:

- ``HybridChunker`` produces the retrieval chunks. It is token-aware (aligned
  to the embedding model's tokenizer) and structure-aware, so tables can be
  split with repeated headers while staying inside the embedding window.
- ``HierarchicalChunker`` produces one chunk per document element. Its heading
  paths form the section tree; each hybrid chunk is tagged with the deepest
  section path that covers its content.

SEC filings use styled ``<div>``s instead of semantic headings, so the markdown
we ingest has no ``#`` markers. ``promote_sec_headings`` rewrites the
standalone ``PART X`` / ``ITEM n. ...`` lines as markdown headings so both
chunkers can recover the section structure.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import tiktoken
from docling.chunking import HierarchicalChunker, HybridChunker
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.serializer.markdown import (
    MarkdownParams,
    MarkdownTableSerializer,
)
from docling_core.types.doc import DoclingDocument

from app.config import settings

_SEC_HEADER_RE = re.compile(r"(PART [IVX]+|ITEM \d+[A-Z]?\. .+)", re.IGNORECASE)

_DOCUMENT_CONVERTER = DocumentConverter(allowed_formats=[InputFormat.MD])


class MarkdownTableSerializerProvider(ChunkingSerializerProvider):
    """Chunk tables as compact markdown instead of docling's flat cell dump.

    SEC HTML tables store every merged cell expanded across many columns, so
    the default table serializer emits lines of ``, = . , = .`` noise that an
    LLM cannot parse. Rendering tables as markdown keeps them readable.
    """

    def get_serializer(self, doc):
        return ChunkingDocSerializer(
            doc=doc,
            table_serializer=MarkdownTableSerializer(),
            params=MarkdownParams(compact_tables=True),
        )


def promote_sec_headings(markdown: str) -> str:
    """Rewrite standalone SEC ``PART X`` / ``ITEM n.`` lines as ``#`` headings."""
    lines = []
    for line in markdown.split("\n"):
        stripped = line.strip()
        if _SEC_HEADER_RE.fullmatch(stripped):
            lines.append(f"# {stripped}")
        else:
            lines.append(line)
    return "\n".join(lines)


def _collapse_duplicate_cells(line: str) -> str:
    """Drop adjacent duplicate cells in one markdown table row.

    Docling's HTML conversion expands a single logical cell (e.g. ``Revenue``)
    across as many columns as the merged region spans. Collapsing adjacent
    identical cells restores the readable table while preserving every unique
    value. No-op on rows with distinct cells.
    """
    cells = line.strip().split("|")
    out = [cells[0]]
    for cell in cells[1:]:
        if out and out[-1] == cell:
            continue
        out.append(cell)
    return "|".join(out)


def normalize_tables(markdown: str) -> str:
    """Collapse duplicated cells across all markdown table rows."""
    return "\n".join(
        _collapse_duplicate_cells(line) if line.lstrip().startswith("|") else line
        for line in markdown.split("\n")
    )


def prepare_markdown(markdown: str) -> str:
    """Full markdown prep before Docling parsing: sections + table cleanup."""
    return normalize_tables(promote_sec_headings(markdown))


def markdown_to_document(markdown: str, filename: str) -> DoclingDocument:
    """Parse promoted markdown back into a DoclingDocument."""
    stream = DocumentStream(
        name=filename if filename.endswith(".md") else f"{filename}.md",
        stream=io.BytesIO(markdown.encode("utf-8")),
    )
    return _DOCUMENT_CONVERTER.convert(source=stream).document


def build_tokenizer() -> OpenAITokenizer:
    """Tokenizer matching the configured OpenAI embedding model."""
    return OpenAITokenizer(
        tokenizer=tiktoken.encoding_for_model(settings.openai_embedding_model),
        max_tokens=settings.openai_embedding_max_tokens,
    )


def build_hybrid_chunker(tokenizer: OpenAITokenizer) -> HybridChunker:
    return HybridChunker(
        tokenizer=tokenizer,
        serializer_provider=MarkdownTableSerializerProvider(),
    )


def build_section_paths(doc: DoclingDocument) -> dict[str, str]:
    """Map each doc-item self_ref to its deepest heading path.

    Uses the hierarchical chunker: every element becomes one chunk whose
    ``meta.headings`` is the path of section headings leading to it.
    """
    section_by_item: dict[str, str] = {}
    for chunk in HierarchicalChunker().chunk(dl_doc=doc):
        path = " / ".join(chunk.meta.headings or [])
        if not path:
            continue
        for item in chunk.meta.doc_items:
            section_by_item[item.self_ref] = path
    return section_by_item


def _deepest_section(paths: list[str]) -> str | None:
    """Pick the deepest (longest) non-empty heading path among candidates."""
    return max((p for p in paths if p), key=len, default=None)


@dataclass
class Chunk:
    index: int
    text: str
    enriched_text: str
    section: str | None
    headings: list[str] = field(default_factory=list)
    doc_item_refs: list[str] = field(default_factory=list)
    token_count: int = 0


def chunk_document(
    doc: DoclingDocument,
    chunker: HybridChunker,
    section_paths: dict[str, str],
) -> list[Chunk]:
    """Chunk a document, resolving each chunk's section from the section tree."""
    chunks: list[Chunk] = []
    for index, chunk in enumerate(chunker.chunk(dl_doc=doc)):
        refs = [item.self_ref for item in chunk.meta.doc_items]
        paths = [section_paths[ref] for ref in refs if ref in section_paths]
        enriched_text = chunker.contextualize(chunk=chunk)
        chunks.append(
            Chunk(
                index=index,
                text=chunk.text,
                enriched_text=enriched_text,
                section=_deepest_section(paths),
                headings=list(chunk.meta.headings or []),
                doc_item_refs=refs,
                token_count=chunker.tokenizer.count_tokens(enriched_text),
            )
        )
    return chunks