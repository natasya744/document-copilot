from app.retrieval.keywords import extract_keywords


def test_extracts_content_terms_from_verbose_query():
    terms = extract_keywords("How many employees did Microsoft have in 2023?")
    assert terms == ["employees", "microsoft", "2023"]


def test_drops_stopwords_and_short_tokens():
    terms = extract_keywords("What is the risk of the data center business?")
    assert "the" not in terms
    assert "of" not in terms
    assert terms == ["risk", "data", "center", "business"]


def test_keeps_four_digit_years_drops_other_numbers():
    assert extract_keywords("revenue in 2023") == ["revenue", "2023"]
    assert extract_keywords("revenue 42 7") == ["revenue"]


def test_dedupes_terms():
    assert extract_keywords("revenue revenue growth growth") == ["revenue", "growth"]


def test_caps_at_max_terms():
    terms = extract_keywords(
        "How much did revenue grow in the cloud and data center segments last year?",
        max_terms=3,
    )
    assert len(terms) == 3


def test_returns_empty_for_all_stopwords():
    assert extract_keywords("How do we what?") == []