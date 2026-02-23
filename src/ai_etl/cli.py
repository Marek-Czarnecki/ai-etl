"""CLI entrypoint for AI ETL."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
import typer

from ai_etl.compare import compare_texts
from ai_etl.config import load_config
from ai_etl.io import copy_file, gather_example_files, read_text, sha256_text, write_text
from ai_etl.llm_ollama import OllamaClient, check_ollama
from ai_etl.models import RunMeta, RunParams
from ai_etl.propose import build_patch_prompt, prepare_patch_artifacts
from ai_etl.store_chroma import store_run

app = typer.Typer(add_completion=False)
logger = logging.getLogger(__name__)


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
) -> None:
    """Compute a structured diff between expected and actual outputs."""

    expected_text = read_text(expected)
    actual_text = read_text(actual)
    comparison = compare_texts(expected_text, actual_text)
    typer.echo(json.dumps(comparison, indent=2))


@app.command()
def propose(
    rulebook: Path = typer.Option(..., "--rulebook", exists=True, readable=True),
    diff_path: Path = typer.Option(..., "--diff", exists=True, readable=True),
    model: Optional[str] = typer.Option(None, "--model"),
    temperature: Optional[float] = typer.Option(None, "--temperature"),
    top_p: Optional[float] = typer.Option(None, "--top-p"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens"),
    seed: Optional[int] = typer.Option(None, "--seed"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Generate a rulebook patch proposal using the provided diff JSON."""

    _setup_logging(verbose)
    cfg = load_config()

    rulebook_text = read_text(rulebook)
    diff_json = read_text(diff_path)

    system, user = build_patch_prompt(rulebook_text, "", "", "", diff_json)
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

    _setup_logging(verbose)
    cfg = load_config()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = timestamp
    run_dir = out_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)

    rulebook_text = read_text(rulebook)
    input_text = read_text(input_path)

    rulebook_copy = run_dir / "rulebook.md"
    copy_file(rulebook, rulebook_copy)

    input_suffix = input_path.suffix or ".txt"
    input_copy = run_dir / f"input{input_suffix}"
    copy_file(input_path, input_copy)

    expected_text = None
    expected_copy = None
    if expected is not None:
        expected_text = read_text(expected)
        expected_suffix = expected.suffix or ".txt"
        expected_copy = run_dir / f"expected{expected_suffix}"
        copy_file(expected, expected_copy)

    example_files = gather_example_files(examples or [])
    example_blocks = []
    for ex_path in example_files:
        ex_text = read_text(ex_path)
        example_blocks.append(f"### {ex_path.name}\n{ex_text}")

    system_generate = (
        "Follow the rulebook strictly. Use examples if provided. "
        "Return only the output, no explanations."
    )
    user_parts = [
        "Rulebook:\n" + rulebook_text,
        "Input:\n" + input_text,
    ]
    if example_blocks:
        user_parts.append("Examples:\n" + "\n\n".join(example_blocks))
    user_generate = "\n\n".join(user_parts)

    client = OllamaClient(cfg.ollama_base_url, model or cfg.default_model)

    start_gen = time.time()
    actual_output = client.chat(
        [
            {"role": "system", "content": system_generate},
            {"role": "user", "content": user_generate},
        ],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
    )
    gen_time = time.time() - start_gen

    actual_path = run_dir / "actual_output.md"
    write_text(actual_path, actual_output)

    comparison = None
    patch_markdown = ""
    patch_diff = ""
    compare_time = 0.0
    patch_time = 0.0

    if expected_text is not None:
        start_compare = time.time()
        comparison = compare_texts(expected_text, actual_output)
        compare_time = time.time() - start_compare
        comparison_path = run_dir / "comparison.json"
        write_text(comparison_path, json.dumps(comparison, indent=2))

        diff_summary_json = json.dumps(comparison, indent=2)
        system_patch, user_patch = build_patch_prompt(
            rulebook_text,
            input_text,
            expected_text,
            actual_output,
            diff_summary_json,
        )
        start_patch = time.time()
        patch_output = client.chat(
            [
                {"role": "system", "content": system_patch},
                {"role": "user", "content": user_patch},
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
        )
        patch_time = time.time() - start_patch
        patch_markdown, patch_diff = prepare_patch_artifacts(rulebook_text, patch_output)

        patch_path = run_dir / "rulebook_patch.md"
        write_text(patch_path, patch_markdown)
        diff_path = run_dir / "rulebook_patch.diff"
        write_text(diff_path, patch_diff)

    run_meta = RunMeta(
        run_id=run_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        rulebook_path=str(rulebook_copy),
        input_path=str(input_copy),
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
            "input": sha256_text(input_text),
            "expected": sha256_text(expected_text) if expected_text else "",
            "actual": sha256_text(actual_output),
        },
        timings={
            "generate_seconds": gen_time,
            "compare_seconds": compare_time,
            "patch_seconds": patch_time,
        },
        extra={
            "output_paths": {
                "actual_output": str(actual_path),
                "comparison": str(run_dir / "comparison.json") if comparison else "",
                "rulebook_patch": str(run_dir / "rulebook_patch.md") if patch_markdown else "",
                "rulebook_patch_diff": str(run_dir / "rulebook_patch.diff") if patch_diff else "",
            }
        },
    )
    run_meta_path = run_dir / "run_meta.json"
    write_text(run_meta_path, run_meta.model_dump_json(indent=2))

    if store_chroma_flag:
        documents = {
            "rulebook": rulebook_text,
            "input": input_text,
            "actual": actual_output,
            "run_meta": run_meta.model_dump_json(),
        }
        if expected_text:
            documents["expected"] = expected_text
        if patch_markdown:
            documents["patch"] = patch_markdown

        store_run(
            chroma_url=cfg.chroma_url,
            collection_name=collection,
            documents=documents,
            run_id=run_id,
            metadata={"model": model or cfg.default_model},
            ollama_client=client,
        )

    typer.echo(f"Run artifacts written to {run_dir}")


if __name__ == "__main__":
    app()
