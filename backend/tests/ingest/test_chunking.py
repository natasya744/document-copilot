from ingest.chunking import (
    build_section_paths,
    chunk_document,
    markdown_to_document,
    promote_sec_headings,
)

_MD = """# PART I

# ITEM 1. BUSINESS

NVIDIA pioneered accelerated computing to help solve the most challenging
computational problems.

# ITEM 1A. RISK FACTORS

Our business is subject to many risks.

| Metric | Value |
| ------ | ----- |
| A      | 1     |
| B      | 2     |
"""


def _document():
    return markdown_to_document(_MD, "test.md")


def test_promote_sec_headings_marks_part_and_item_lines():
    promoted = promote_sec_headings(_MD)
    assert "# PART I" in promoted
    assert "# ITEM 1. BUSINESS" in promoted
    assert "# ITEM 1A. RISK FACTORS" in promoted


def test_promote_sec_headings_leaves_inline_references_alone():
    md = "Refer to Item 1A. Risk Factors for more.\n"
    assert promote_sec_headings(md) == md


def test_markdown_to_document_parses_headings():
    doc = _document()
    headings = [i.text for i, _ in doc.iterate_items() if i.label.value == "title"]
    assert "PART I" in headings
    assert "ITEM 1A. RISK FACTORS" in headings


def test_build_section_paths_maps_items_to_sections():
    doc = _document()
    paths = build_section_paths(doc)
    assert paths
    assert any("ITEM 1A. RISK FACTORS" in path for path in paths.values())


def test_chunk_document_with_real_chunker():
    from ingest.chunking import build_hybrid_chunker, build_tokenizer

    doc = _document()
    paths = build_section_paths(doc)
    chunker = build_hybrid_chunker(build_tokenizer())
    chunks = chunk_document(doc, chunker, paths)

    assert chunks
    assert all(c.token_count > 0 for c in chunks)
    sections = {c.section for c in chunks if c.section}
    assert any("BUSINESS" in s for s in sections)
    assert any("RISK FACTORS" in s for s in sections)