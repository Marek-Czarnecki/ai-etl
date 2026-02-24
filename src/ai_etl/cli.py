"""CLI entrypoint for AI ETL."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
import typer

from ai_etl.config import load_config
from ai_etl.io import copy_file, gather_example_files, read_text, sha256_text, write_text
from ai_etl.llm_ollama import OllamaClient, check_ollama
from ai_etl.models import RunMeta, RunParams
from ai_etl.prompts import load_prompt, render_user
from ai_etl.propose import build_patch_prompt, prepare_patch_artifacts
from ai_etl.store_chroma import store_run
from ai_etl.yamlutil import dump_yaml, dump_yaml_path, load_yaml_path

app = typer.Typer(add_completion=False)
logger = logging.getLogger(__name__)


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not (stripped.startswith("```") and stripped.endswith("```")):
        return text
    lines = stripped.splitlines()
    if len(lines) < 2:
        return text
    if not (lines[0].startswith("```") and lines[-1].startswith("```")):
        return text
    return "\n".join(lines[1:-1]).strip()


def _quote_reason_values(text: str) -> str:
    lines = text.splitlines()
    updated = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped.startswith("reason:"):
            updated.append(line)
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if not value or value[0] in ("'", '"'):
            updated.append(line)
            continue
        if ":" not in value:
            updated.append(line)
            continue
        escaped = value.replace('"', '\\"')
        updated.append(f'{key}: "{escaped}"')
    return "\n".join(updated)


def _normalize_flags_doc(obj: object) -> object:
    if not isinstance(obj, dict):
        return obj
    if "flags" not in obj or not isinstance(obj["flags"], list):
        return obj
    normalized = dict(obj)
    flags = []
    severity_counts = {"High": 0, "Medium": 0, "Low": 0}
    transaction_ids = set()
    for item in obj["flags"]:
        if not isinstance(item, dict):
            flags.append(item)
            continue
        flag = dict(item)
        flag.pop("reason", None)
        tx_id = flag.get("transaction_id")
        if isinstance(tx_id, str) and tx_id:
            transaction_ids.add(tx_id)
        severity = flag.get("severity")
        if isinstance(severity, str) and severity in severity_counts:
            severity_counts[severity] += 1
        evidence = flag.get("evidence")
        if isinstance(evidence, dict):
            evidence_copy = dict(evidence)
            for key in ("transactions_in_window", "matched_keywords"):
                values = evidence_copy.get(key)
                if isinstance(values, list):
                    try:
                        evidence_copy[key] = sorted(values)
                    except TypeError:
                        evidence_copy[key] = values
            flag["evidence"] = evidence_copy
        flags.append(flag)
    def _flag_key(item: object) -> tuple:
        if not isinstance(item, dict):
            return ("", "")
        return (
            str(item.get("transaction_id", "")),
            str(item.get("requirement_id", "")),
        )
    normalized["flags"] = sorted(flags, key=_flag_key)
    summary = normalized.get("summary")
    normalized["summary"] = {
        "total_transactions": None,
        "flagged_transactions": len(transaction_ids),
        "flagged_by_severity": severity_counts,
    }
    return normalized


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def _check_chroma(chroma_url: str) -> tuple[bool, str]:
    base = chroma_url.rstrip("/")
    candidates = [
        f"{base}/api/v1/heartbeat",
        f"{base}/api/v2/heartbeat",
        f"{base}/api/heartbeat",
        f"{base}/api/v1/health",
        f"{base}/api/health",
    ]
    for url in candidates:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return True, "ok"
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
    return False, last_error


def _run_once(
    rulebook: Path,
    input_path: Optional[Path],
    examples: List[Path],
    expected: Optional[Path],
    actual_path: Optional[Path],
    prompt_path: Path,
    output_name: str,
    schema_text: str,
    model: Optional[str],
    temperature: Optional[float],
    top_p: Optional[float],
    max_tokens: Optional[int],
    seed: Optional[int],
    out_dir: Path,
    store_chroma_flag: bool,
    collection: str,
    verbose: bool,
) -> Path:
    _setup_logging(verbose)
    cfg = load_config()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = timestamp
    run_dir = out_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)

    rulebook_text = read_text(rulebook)
    input_text = read_text(input_path) if input_path is not None else ""
    expected_text = read_text(expected) if expected is not None else ""
    actual_input_text = read_text(actual_path) if actual_path is not None else ""

    rulebook_suffix = rulebook.suffix or ".yaml"
    rulebook_copy = run_dir / f"rulebook{rulebook_suffix}"
    copy_file(rulebook, rulebook_copy)

    input_copy = None
    if input_path is not None:
        input_suffix = input_path.suffix or ".yaml"
        input_copy = run_dir / f"input{input_suffix}"
        copy_file(input_path, input_copy)

    expected_copy = None
    if expected is not None:
        expected_suffix = expected.suffix or ".yaml"
        expected_copy = run_dir / f"expected{expected_suffix}"
        copy_file(expected, expected_copy)

    actual_input_copy = None
    if actual_path is not None:
        actual_suffix = actual_path.suffix or ".yaml"
        actual_input_copy = run_dir / f"actual_input{actual_suffix}"
        copy_file(actual_path, actual_input_copy)

    example_files = gather_example_files(examples or [])
    example_blocks = []
    for ex_path in example_files:
        ex_text = read_text(ex_path)
        example_blocks.append(f"### {ex_path.name}\n{ex_text}")

    examples_text = "\n\n".join(example_blocks)

    prompt = load_prompt(prompt_path)
    user_generate = render_user(
        prompt["user_template"],
        rulebook=rulebook_text,
        input_text=input_text,
        examples_text=examples_text,
        schema_text=schema_text,
        expected=expected_text,
        actual=actual_input_text,
    )

    client = OllamaClient(cfg.ollama_base_url, model or cfg.default_model)

    start_gen = time.time()
    actual_output = client.chat(
        [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": user_generate},
        ],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
    )
    actual_output = _strip_markdown_fence(actual_output)
    actual_output = _quote_reason_values(actual_output)

    gen_time = time.time() - start_gen

    actual_path = run_dir / output_name
    write_text(actual_path, actual_output)

    run_meta = RunMeta(
        run_id=run_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        rulebook_path=str(rulebook_copy),
        input_path=str(input_copy) if input_copy else "",
        expected_path=str(expected_copy) if expected_copy else None,
        model_params=RunParams(
            model=model or cfg.default_model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
        ),
        file_hashes={
            "rulebook": sha256_text(rulebook_text),
            "input": sha256_text(input_text) if input_text else "",
            "expected": sha256_text(expected_text) if expected_text else "",
            "actual_input": sha256_text(actual_input_text) if actual_input_text else "",
            "actual_output": sha256_text(actual_output),
        },
        timings={
            "generate_seconds": gen_time,
        },
        extra={
            "output_paths": {
                "actual_output": str(actual_path),
            }
        },
    )
    run_meta_path = run_dir / "run_meta.yaml"
    dump_yaml_path(run_meta_path, run_meta.model_dump())

    if store_chroma_flag:
        run_meta_yaml = dump_yaml(run_meta.model_dump())
        documents = {
            "rulebook": rulebook_text,
            "input": input_text,
            "actual": actual_output,
            "run_meta": run_meta_yaml,
        }
        if expected_text:
            documents["expected"] = expected_text
        if actual_input_text:
            documents["actual_input"] = actual_input_text

        store_run(
            chroma_url=cfg.chroma_url,
            collection_name=collection,
            documents=documents,
            run_id=run_id,
            metadata={"model": model or cfg.default_model},
            ollama_client=client,
        )

    return run_dir


@app.command()
def doctor(verbose: bool = typer.Option(False, "--verbose")) -> None:
    """Check connectivity to Ollama and ChromaDB."""

    _setup_logging(verbose)
    cfg = load_config()

    ok_ollama, msg_ollama = check_ollama(cfg.ollama_base_url)
    ok_chroma, msg_chroma = _check_chroma(cfg.chroma_url)

    typer.echo(f"Ollama: {'OK' if ok_ollama else 'FAIL'} ({msg_ollama})")
    typer.echo(f"ChromaDB: {'OK' if ok_chroma else 'FAIL'} ({msg_chroma})")

    if not (ok_ollama and ok_chroma):
        raise typer.Exit(code=1)


@app.command()
def diff(
    expected: Path = typer.Option(..., "--expected", exists=True, readable=True),
    actual: Path = typer.Option(..., "--actual", exists=True, readable=True),
    rulebook: Path = typer.Option(..., "--rulebook", exists=True, readable=True),
    prompt: Path = typer.Option(Path("prompts/stage_d_judge.yaml"), "--prompt"),
    out_dir: Path = typer.Option(Path("out"), "--out-dir"),
    model: Optional[str] = typer.Option(None, "--model"),
    temperature: Optional[float] = typer.Option(None, "--temperature"),
    top_p: Optional[float] = typer.Option(None, "--top-p"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens"),
    seed: Optional[int] = typer.Option(None, "--seed"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Run the judge prompt to compare expected and actual outputs."""

    expected_obj = load_yaml_path(expected)
    actual_obj = load_yaml_path(actual)
    expected_norm = _normalize_flags_doc(expected_obj)
    actual_norm = _normalize_flags_doc(actual_obj)

    if expected_norm == actual_norm:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = out_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=False)
        report_path = run_dir / "judge_report.yaml"
        dump_yaml_path(
            report_path,
            {
                "judge": {
                    "overall_pass": True,
                    "score": 1.0,
                    "mismatches": [],
                }
            },
        )
        typer.echo(f"Diff artifacts written to {run_dir}")
        return

    run_dir = _run_once(
        rulebook=rulebook,
        input_path=None,
        examples=[],
        expected=expected,
        actual_path=actual,
        prompt_path=prompt,
        output_name="judge_report.yaml",
        schema_text="",
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
        out_dir=out_dir,
        store_chroma_flag=False,
        collection="ai_etl_runs",
        verbose=verbose,
    )
    report_path = run_dir / "judge_report.yaml"
    if expected_obj == actual_obj:
        dump_yaml_path(
            report_path,
            {
                "judge": {
                    "overall_pass": True,
                    "score": 1.0,
                    "mismatches": [],
                }
            },
        )
    typer.echo(read_text(report_path))


@app.command()
def propose(
    rulebook: Path = typer.Option(..., "--rulebook", exists=True, readable=True),
    diff_path: Path = typer.Option(..., "--diff", exists=True, readable=True),
    input_path: Optional[Path] = typer.Option(None, "--input", exists=True, readable=True),
    expected_path: Optional[Path] = typer.Option(None, "--expected", exists=True, readable=True),
    actual_path: Optional[Path] = typer.Option(None, "--actual", exists=True, readable=True),
    prompt: Path = typer.Option(Path("prompts/propose_patch.yaml"), "--prompt"),
    model: Optional[str] = typer.Option(None, "--model"),
    temperature: Optional[float] = typer.Option(None, "--temperature"),
    top_p: Optional[float] = typer.Option(None, "--top-p"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens"),
    seed: Optional[int] = typer.Option(None, "--seed"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Generate a rulebook patch proposal using the provided judge report.

    Optionally provide --input/--expected/--actual to give the model full context
    for higher-quality rulebook revision suggestions.
    """

    _setup_logging(verbose)
    cfg = load_config()

    rulebook_text = read_text(rulebook)
    judge_report = read_text(diff_path)

    input_text = read_text(input_path) if input_path is not None else ""
    expected_text = read_text(expected_path) if expected_path is not None else ""
    actual_text = read_text(actual_path) if actual_path is not None else ""

    system, user = build_patch_prompt(
        str(prompt),
        rulebook=rulebook_text,
        input_text=input_text,
        expected=expected_text,
        actual=actual_text,
        judge_report=judge_report,
    )

    client = OllamaClient(cfg.ollama_base_url, model or cfg.default_model)
    output = client.chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
    )
    patch_markdown, patch_diff = prepare_patch_artifacts(rulebook_text, output)
    typer.echo(patch_markdown)
    if patch_diff:
        typer.echo("\n---\n")
        typer.echo(patch_diff)
        

@app.command()
def run(
    rulebook: Path = typer.Option(..., "--rulebook", exists=True, readable=True),
    input_path: Path = typer.Option(..., "--input", exists=True, readable=True),
    examples: List[Path] = typer.Option(None, "--examples"),
    expected: Optional[Path] = typer.Option(None, "--expected", exists=True, readable=True),
    prompt: Path = typer.Option(Path("prompts/run_generate.yaml"), "--prompt"),
    model: Optional[str] = typer.Option(None, "--model"),
    temperature: Optional[float] = typer.Option(None, "--temperature"),
    top_p: Optional[float] = typer.Option(None, "--top-p"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens"),
    seed: Optional[int] = typer.Option(None, "--seed"),
    out_dir: Path = typer.Option(Path("out"), "--out-dir"),
    store_chroma_flag: bool = typer.Option(False, "--store-chroma"),
    collection: str = typer.Option("ai_etl_runs", "--collection"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Run the prompt-driven AI ETL workflow."""

    run_dir = _run_once(
        rulebook=rulebook,
        input_path=input_path,
        examples=examples or [],
        expected=expected,
        actual_path=None,
        prompt_path=prompt,
        output_name="actual_output.yaml",
        schema_text="",
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
        out_dir=out_dir,
        store_chroma_flag=store_chroma_flag,
        collection=collection,
        verbose=verbose,
    )
    typer.echo(f"Run artifacts written to {run_dir}")


def _select_rulebook(pack: Path, stem: str) -> Path:
    yaml_path = pack / "rulebooks" / f"{stem}.yaml"
    md_path = pack / "rulebooks" / f"{stem}.md"
    if yaml_path.exists():
        return yaml_path
    return md_path


def _select_input(pack: Path, stem: str) -> Path:
    yaml_path = pack / "inputs" / f"{stem}.yaml"
    md_path = pack / "inputs" / f"{stem}.md"
    if yaml_path.exists():
        return yaml_path
    return md_path


def _validate_benchmark_pack(pack: Path) -> list[str]:
    required_paths = [
        _select_rulebook(pack, "reg_to_controls"),
        _select_rulebook(pack, "controls_to_requirements"),
        _select_rulebook(pack, "validate_reporting_requirements"),
        _select_rulebook(pack, "judge"),
        _select_input(pack, "regulatory_excerpt"),
        pack / "expected" / "controls.yaml",
        pack / "expected" / "reporting_requirements.yaml",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    return missing


@app.command()
def benchmark(
    pack: Path = typer.Option(..., "--pack", exists=True, readable=True),
    out_dir: Path = typer.Option(Path("out"), "--out-dir"),
    model: Optional[str] = typer.Option(None, "--model"),
    temperature: Optional[float] = typer.Option(None, "--temperature"),
    top_p: Optional[float] = typer.Option(None, "--top-p"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens"),
    seed: Optional[int] = typer.Option(None, "--seed"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Run Benchmark Pack 01 end-to-end in four stages."""

    missing = _validate_benchmark_pack(pack)
    if missing:
        typer.echo("Benchmark pack missing required files:")
        for path in missing:
            typer.echo(f"- {path}")
        raise typer.Exit(code=1)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    benchmark_root = out_dir / "benchmarks" / timestamp
    benchmark_root.mkdir(parents=True, exist_ok=False)

    stage_a_dir = _run_once(
        rulebook=_select_rulebook(pack, "reg_to_controls"),
        input_path=_select_input(pack, "regulatory_excerpt"),
        examples=[],
        expected=pack / "expected" / "controls.yaml",
        actual_path=None,
        prompt_path=Path("prompts/run_generate.yaml"),
        output_name="actual_output.yaml",
        schema_text="",
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
        out_dir=benchmark_root / "stage_a",
        store_chroma_flag=False,
        collection="ai_etl_runs",
        verbose=verbose,
    )

    stage_b_dir = _run_once(
        rulebook=_select_rulebook(pack, "controls_to_requirements"),
        input_path=stage_a_dir / "actual_output.yaml",
        examples=[],
        expected=pack / "expected" / "reporting_requirements.yaml",
        actual_path=None,
        prompt_path=Path("prompts/run_generate.yaml"),
        output_name="actual_output.yaml",
        schema_text="",
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
        out_dir=benchmark_root / "stage_b",
        store_chroma_flag=False,
        collection="ai_etl_runs",
        verbose=verbose,
    )

    stage_c_dir = _run_once(
        rulebook=_select_rulebook(pack, "validate_reporting_requirements"),
        input_path=stage_b_dir / "actual_output.yaml",
        examples=[],
        expected=None,
        actual_path=None,
        prompt_path=Path("prompts/stage_c_validate.yaml"),
        output_name="validation_report.yaml",
        schema_text="",
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
        out_dir=benchmark_root / "stage_c",
        store_chroma_flag=False,
        collection="ai_etl_runs",
        verbose=verbose,
    )

    stage_d_dir = _run_once(
        rulebook=_select_rulebook(pack, "judge"),
        input_path=None,
        examples=[],
        expected=pack / "expected" / "reporting_requirements.yaml",
        actual_path=stage_b_dir / "actual_output.yaml",
        prompt_path=Path("prompts/stage_d_judge.yaml"),
        output_name="judge_report.yaml",
        schema_text="",
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
        out_dir=benchmark_root / "stage_d",
        store_chroma_flag=False,
        collection="ai_etl_runs",
        verbose=verbose,
    )

    stage_d_report = stage_d_dir / "judge_report.yaml"
    status = "PASS" if stage_d_report.exists() else "FAIL"
    notes = []
    if status == "FAIL":
        notes.append("Stage D did not produce judge_report.yaml.")

    manifest = {
        "pack": str(pack),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "stage_a": {
            "run_dir": str(stage_a_dir),
            "actual": str(stage_a_dir / "actual_output.yaml"),
        },
        "stage_b": {
            "run_dir": str(stage_b_dir),
            "actual": str(stage_b_dir / "actual_output.yaml"),
        },
        "stage_c": {
            "run_dir": str(stage_c_dir),
            "validation_report": str(stage_c_dir / "validation_report.yaml"),
        },
        "stage_d": {
            "run_dir": str(stage_d_dir),
            "judge_report": str(stage_d_report) if stage_d_report.exists() else "",
        },
        "status": status,
        "notes": notes,
    }
    manifest_path = benchmark_root / "benchmark_manifest.yaml"
    dump_yaml_path(manifest_path, manifest)

    typer.echo("Benchmark completed:")
    typer.echo(f"- stage_a: {stage_a_dir}")
    typer.echo(f"- stage_b: {stage_b_dir}")
    typer.echo(f"- stage_c: {stage_c_dir}")
    typer.echo(f"- stage_d: {stage_d_dir}")
    typer.echo(f"- status: {status}")


if __name__ == "__main__":
    app()
