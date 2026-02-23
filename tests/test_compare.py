from ai_etl.compare import compare_texts


def test_compare_texts_basic_metrics():
    expected = "alpha\nbeta\n"
    actual = "alpha\ngamma\n"
    result = compare_texts(expected, actual)

    summary = result["summary"]
    assert summary["expected_lines"] == 2
    assert summary["actual_lines"] == 2
    assert summary["expected_tokens"] == 2
    assert summary["actual_tokens"] == 2
    assert 0.0 <= summary["char_similarity"] <= 1.0
    assert "diff_unified" in result
    assert "-beta" in result["diff_unified"]
    assert "+gamma" in result["diff_unified"]
