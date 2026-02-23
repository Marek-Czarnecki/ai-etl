from pathlib import Path

from ai_etl.yamlutil import dump_yaml, load_yaml_text


def test_benchmark_manifest_roundtrip(tmp_path: Path) -> None:
    manifest = {
        "pack": "examples/benchmark_pack_01",
        "created_at": "2024-01-01T00:00:00Z",
        "stage_a": {
            "run_dir": "out/benchmarks/20240101-000000/stage_a/20240101-000001",
            "actual": "out/benchmarks/20240101-000000/stage_a/20240101-000001/actual_output.yaml",
        },
        "stage_b": {
            "run_dir": "out/benchmarks/20240101-000000/stage_b/20240101-000002",
            "actual": "out/benchmarks/20240101-000000/stage_b/20240101-000002/actual_output.yaml",
        },
        "stage_c": {
            "run_dir": "out/benchmarks/20240101-000000/stage_c/20240101-000003",
            "validation_report": "out/benchmarks/20240101-000000/stage_c/20240101-000003/validation_report.yaml",
        },
        "stage_d": {
            "run_dir": "out/benchmarks/20240101-000000/stage_d/20240101-000004",
            "judge_report": "out/benchmarks/20240101-000000/stage_d/20240101-000004/judge_report.yaml",
        },
        "status": "PASS",
        "notes": [],
    }

    manifest_path = tmp_path / "benchmark_manifest.yaml"
    manifest_path.write_text(dump_yaml(manifest), encoding="utf-8")

    loaded = load_yaml_text(manifest_path.read_text(encoding="utf-8"))

    assert loaded["pack"]
    assert loaded["created_at"]
    assert loaded["stage_a"]["run_dir"]
    assert loaded["stage_a"]["actual"]
    assert loaded["stage_b"]["run_dir"]
    assert loaded["stage_b"]["actual"]
    assert loaded["stage_c"]["run_dir"]
    assert loaded["stage_c"]["validation_report"]
    assert loaded["stage_d"]["run_dir"]
    assert loaded["stage_d"]["judge_report"]
    assert loaded["status"] in {"PASS", "FAIL"}
    assert "notes" in loaded
