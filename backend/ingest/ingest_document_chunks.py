"""Chunk and embed source documents into `document_chunks`.

Reads every row from `source_documents` (populated by
`ingest_source_documents.py`), then for each:

1. Promotes SEC PART/ITEM lines to markdown headings and parses back into a
   DoclingDocument.
2. Builds the section tree with the hierarchical chunker.
3. Chunks with the hybrid chunker (token-aware, aligned to the embedding model).
4. Embeds the context-enriched chunk text with OpenAI.
5. Writes rows to `document_chunks` via the service-role client.

Idempotent: existing chunks for a document are deleted before re-insertion, so
re-runs converge without duplicate rows.

Run with the backend venv:

    python backend/ingest/ingest_document_chunks.py
"""
from __future__ import annotations

import logging
import uuid

from app.database.supabase import get_admin_client
from ingest.chunking import (
    build_hybrid_chunker,
    build_section_paths,
    build_tokenizer,
    chunk_document,
    markdown_to_document,
    promote_sec_headings,
)
from ingest.embeddings import Embedder

log = logging.getLogger("ingest_document_chunks")


def source_documents(client) -> list[dict]:
    result = (
        client.table("source_documents")
        .select("id, ticker, company_name, filing_type, filing_date, year, "
                "accession_number, markdown_content")
        .order("year", desc=False)
        .execute()
    )
    return result.data


def delete_existing_chunks(client, document_id: str) -> int:
    result = (
        client.table("document_chunks")
        .delete()
        .eq("document_id", document_id)
        .execute()
    )
    return len(result.data)


def chunk_rows(document: dict, chunks) -> list[dict]:
    metadata = {
        "ticker": document["ticker"],
        "company_name": document["company_name"],
        "filing_type": document["filing_type"],
        "filing_date": document["filing_date"],
        "year": document["year"],
        "accession_number": document["accession_number"],
    }
    rows = []
    for chunk in chunks:
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "document_id": document["id"],
                "chunk_index": chunk.index,
                "page": None,
                "section": chunk.section[:255] if chunk.section else None,
                "chunk_text": chunk.text,
                "token_count": chunk.token_count,
                "metadata": {
                    **metadata,
                    "section_path": chunk.section,
                    "headings": chunk.headings,
                    "doc_item_refs": chunk.doc_item_refs,
                },
            }
        )
    return rows


def ingest() -> None:
    client = get_admin_client()
    tokenizer = build_tokenizer()
    chunker = build_hybrid_chunker(tokenizer)
    embedder = Embedder()

    documents = source_documents(client)
    total_chunks = 0
    for document in documents:
        markdown = promote_sec_headings(document["markdown_content"])
        doc = markdown_to_document(markdown, document["accession_number"])
        section_paths = build_section_paths(doc)
        chunks = chunk_document(doc, chunker, section_paths)
        if not chunks:
            log.warning("No chunks for %s", document["accession_number"])
            continue

        rows = chunk_rows(document, chunks)
        embeddings = embedder.embed_texts([c.enriched_text for c in chunks])
        for row, embedding in zip(rows, embeddings, strict=True):
            row["embedding"] = embedding

        deleted = delete_existing_chunks(client, document["id"])
        for start in range(0, len(rows), 100):
            client.table("document_chunks").insert(rows[start : start + 100]).execute()

        total_chunks += len(rows)
        log.info(
            "Ingested %s %s (%s) — %d chunks (%d replaced)",
            document["ticker"],
            document["year"],
            document["accession_number"],
            len(rows),
            deleted,
        )

    print(
        f"Ingested chunks for {len(documents)} document(s): "
        f"{total_chunks} chunk(s) in document_chunks"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ingest()