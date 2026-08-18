"""Upsert converted SEC Markdown filings into `source_documents`.

Reads data/markdown/manifest.json (produced by data/convert.py), loads each
filing's markdown content, and writes rows to `source_documents` via the
service-role Supabase client. Idempotent: rows are keyed by `accession_number`
(unique) and updated in place rather than duplicated on re-runs.

Run with the backend venv:

    python backend/ingest/ingest_source_documents.py
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from app.database.supabase import get_admin_client

log = logging.getLogger("ingest_source_documents")

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "markdown" / "manifest.json"
MARKDOWN_DIR = REPO_ROOT / "data" / "markdown"

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def filing_rows(manifest: dict) -> list[dict]:
    rows = []
    for filing in manifest["filings"]:
        rows.append(
            {
                "ticker": filing["ticker"],
                "company_name": COMPANY_NAMES[filing["ticker"]],
                "filing_type": filing["form"],
                "filing_date": filing["filing_date"],
                "year": int(filing["local_path"].split("/", 1)[0]),
                "accession_number": filing["accession_number"],
                "source_url": filing["source_url"],
                "markdown_content": (
                    MARKDOWN_DIR / filing["local_path"]
                ).read_text(encoding="utf-8"),
                "metadata": {
                    "cik": filing["cik"],
                    "report_date": filing["report_date"],
                    "primary_document": filing["primary_document"],
                    "source_path": filing["source_path"],
                },
            }
        )
    return rows


def existing_accession_numbers(client, rows: list[dict]) -> set[str]:
    accs = [row["accession_number"] for row in rows]
    result = (
        client.table("source_documents")
        .select("accession_number")
        .in_("accession_number", accs)
        .execute()
    )
    return {row["accession_number"] for row in result.data}


def ingest() -> None:
    client = get_admin_client()
    rows = filing_rows(load_manifest())
    existing = existing_accession_numbers(client, rows)

    inserted = 0
    for row in rows:
        if row["accession_number"] in existing:
            client.table("source_documents").update(row).eq(
                "accession_number", row["accession_number"]
            ).execute()
            log.info("Updated %s (%s)", row["accession_number"], row["ticker"])
        else:
            client.table("source_documents").insert(
                {**row, "id": str(uuid.uuid4())}
            ).execute()
            inserted += 1
            log.info("Inserted %s (%s)", row["accession_number"], row["ticker"])

    print(
        f"Ingested {len(rows)} source document(s) "
        f"({len(rows) - inserted} updated, {inserted} inserted)"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ingest()
