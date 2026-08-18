from app.retrieval.fusion import reciprocal_rank_fusion


def test_empty_rankings_return_empty():
    assert reciprocal_rank_fusion([]) == []


def test_empty_lists_are_ignored():
    assert reciprocal_rank_fusion([[], ["a"]]) == [("a", 1.0 / 61)]


def test_single_ranking_preserves_order():
    assert reciprocal_rank_fusion([["a", "b"]]) == [
        ("a", 1.0 / 61),
        ("b", 1.0 / 62),
    ]


def test_later_rank_positions_score_lower():
    scores = dict(reciprocal_rank_fusion([["a", "b", "c"]]))
    assert scores["a"] > scores["b"] > scores["c"]


def test_chunk_in_both_rankings_accumulates():
    assert reciprocal_rank_fusion([["a", "b", "c"], ["a"]]) == [
        ("a", 2.0 / 61),
        ("b", 1.0 / 62),
        ("c", 1.0 / 63),
    ]


def test_disjoint_rankings_are_merged():
    result = reciprocal_rank_fusion([["a"], ["b"]])
    assert set(dict(result)) == {"a", "b"}
    assert all(abs(score - 1.0 / 61) < 1e-12 for _, score in result)


def test_custom_k_smooths_scores():
    scores = dict(reciprocal_rank_fusion([["a"]], k=10))
    assert abs(scores["a"] - 1.0 / 11) < 1e-12