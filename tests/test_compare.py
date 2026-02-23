from pathlib import Path

from ai_etl import cli
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


def test_diff_writes_judge_report(tmp_path, monkeypatch):
    rulebook = tmp_path / "judge.yaml"
    expected = tmp_path / "expected.yaml"
    actual = tmp_path / "actual.yaml"

    rulebook.write_text("name: judge\n", encoding="utf-8")
    expected.write_text("value: 1\n", encoding="utf-8")
    actual.write_text("value: 2\n", encoding="utf-8")

    class StubClient:
        def __init__(self, base_url: str, model: str) -> None:
            self.base_url = base_url
            self.model = model

        def chat(self, messages, **kwargs):
            return "judge:\n  overall_pass: true\n  score: 1.0\n  mismatches: []\n"

    monkeypatch.setattr(cli, "OllamaClient", StubClient)

    out_dir = tmp_path / "out"
    cli.diff(
        expected=expected,
        actual=actual,
        rulebook=rulebook,
        prompt=Path("prompts/stage_d_judge.yaml"),
        out_dir=out_dir,
        model=None,
        temperature=None,
        top_p=None,
        max_tokens=None,
        seed=None,
        verbose=False,
    )

    run_dirs = [path for path in out_dir.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    report_path = run_dirs[0] / "judge_report.yaml"
    assert report_path.exists()
    assert "overall_pass" in report_path.read_text(encoding="utf-8")
