# /// script
# requires-python = ">=3.12"
# ///
"""Convert downloaded SEC HTML filings to Markdown with Docling.

Run with the backend venv (docling is a dev dependency there):

    source backend/.venv/bin/activate
    python data/convert.py

Writes one .md per source .htm/.html under data/markdown/, preserving the
data/downloads/ year folder layout and emitting a parallel manifest.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from docling.document_converter import DocumentConverter

log = logging.getLogger("convert")

DATA_DIR = Path(__file__).resolve().parent
SOURCE_DIR = DATA_DIR / "downloads"
OUTPUT_DIR = DATA_DIR / "markdown"
SOURCE_MANIFEST = SOURCE_DIR / "manifest.json"
OUTPUT_MANIFEST = OUTPUT_DIR / "manifest.json"
HTML_SUFFIXES = {".htm", ".html"}


def find_html_files() -> list[Path]:
    return sorted(
        p
        for p in SOURCE_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in HTML_SUFFIXES
    )


def source_manifest() -> dict:
    if not SOURCE_MANIFEST.exists():
        return {"filings": []}
    return json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))


def source_metadata() -> dict[str, dict]:
    return {
        filing["local_path"]: filing for filing in source_manifest().get("filings", [])
    }


def convert_filings() -> dict:
    converter = DocumentConverter()
    metadata = source_metadata()
    html_files = find_html_files()
    failures = []

    for source in html_files:
        rel = source.relative_to(SOURCE_DIR)
        out_path = OUTPUT_DIR / rel.with_suffix(".md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = converter.convert(source)
            out_path.write_text(
                result.document.export_to_markdown(), encoding="utf-8"
            )
        except Exception:
            failures.append(str(rel))
            log.exception("Failed to convert %s", rel)
            continue
        log.info("Converted %s -> %s", rel, out_path.relative_to(DATA_DIR))

    filings = []
    for rel, source in ((p.relative_to(SOURCE_DIR), p) for p in html_files):
        if str(rel) in metadata:
            filing = dict(metadata[str(rel)])
        else:
            filing = {"local_path": str(rel)}
        filing["source_path"] = filing["local_path"]
        filing["local_path"] = str(rel.with_suffix(".md"))
        filings.append(filing)

    manifest = {
        "source": "docling markdown conversion",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "converted_count": len(html_files) - len(failures),
        "failed_count": len(failures),
        "filings": filings,
    }
    OUTPUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    manifest = convert_filings()
    print(
        f"Converted {manifest['converted_count']} filing(s) to {OUTPUT_DIR} "
        f"({manifest['failed_count']} failed)"
    )
    print(f"Manifest: {OUTPUT_MANIFEST}")
