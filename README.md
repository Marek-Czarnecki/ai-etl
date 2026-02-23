# AI ETL

A small, production-lean CLI that runs alongside a local Ollama + ChromaDB stack.

## Prerequisites

- Python 3.9+
- Docker + docker compose

## Docker Setup

From the repo root:

```bash
docker compose up -d
```

If the model did not pull automatically:

```bash
docker compose exec ollama ollama pull llama3.2:1b
```

## Local Development Setup

Create and activate a virtual environment, then install the CLI:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify connectivity:

```bash
ai-etl doctor --verbose
```

## Running a Simple Job

Example packs live in `examples/`.

Minimal run:

```bash
ai-etl run \
  --rulebook examples/rulebook.yaml \
  --input examples/input.yaml
```

Run with all `run` options:

```bash
ai-etl run \
  --rulebook examples/rulebook.yaml \
  --input examples/input.yaml \
  --examples examples/example_1.yaml \
  --expected examples/expected.yaml \
  --prompt prompts/run_generate.yaml \
  --model llama3.2:1b \
  --temperature 0 \
  --top-p 1 \
  --max-tokens 2048 \
  --seed 42 \
  --out-dir out \
  --store-chroma \
  --collection ai_etl_runs \
  --verbose
```

## Running a Benchmark

Benchmark Pack 01 runs four stages:
A) regulatory excerpt -> controls
B) controls -> reporting requirements
C) reporting requirements -> validation report
D) judge expected vs actual reporting requirements

```bash
ai-etl benchmark \
  --pack examples/benchmark_pack_01 \
  --out-dir out \
  --model llama3.2:1b \
  --temperature 0 \
  --top-p 1 \
  --max-tokens 2048 \
  --seed 42 \
  --verbose
```

## Using diff

Run with all `diff` options:

```bash
RUN_DIR="$(ls -dt out/[0-9]*/actual_output.yaml | head -1 | xargs dirname)/"
ai-etl diff \
  --rulebook examples/rulebook.yaml \
  --expected examples/expected.yaml \
  --actual "${RUN_DIR}actual_output.yaml" \
  --prompt prompts/stage_d_judge.yaml \
  --out-dir out \
  --model llama3.2:1b \
  --temperature 0 \
  --top-p 1 \
  --max-tokens 2048 \
  --seed 42 \
  --verbose
```

## Using propose

Run with all `propose` options:

```bash
RUN_DIR="$(ls -dt out/[0-9]*/actual_output.yaml | head -1 | xargs dirname)/"
DIFF_DIR="$(ls -dt out/[0-9]*/judge_report.yaml | head -1 | xargs dirname)/"
ai-etl propose \
  --rulebook examples/rulebook.yaml \
  --diff "${DIFF_DIR}judge_report.yaml" \
  --input examples/input.yaml \
  --expected examples/expected.yaml \
  --actual "${RUN_DIR}actual_output.yaml" \
  --prompt prompts/propose_patch.yaml \
  --model llama3.2:1b \
  --temperature 0 \
  --top-p 1 \
  --max-tokens 2048 \
  --seed 42 \
  --verbose
```

## Output Structure

Each `run` creates a timestamped folder (`expected.<ext>` appears only when `--expected` is set):

```
out/<YYYYMMDD-HHMMSS>/
  rulebook.<ext>
  input.<ext>
  expected.<ext>
  actual_output.yaml
  run_meta.yaml
```

Each `diff` creates a timestamped folder (`actual_input.<ext>` is the provided `--actual` copy):

```
out/<YYYYMMDD-HHMMSS>/
  rulebook.<ext>
  expected.<ext>
  actual_input.<ext>
  judge_report.yaml
  run_meta.yaml
```

Each `benchmark` creates:

```
out/benchmarks/<YYYYMMDD-HHMMSS>/
  stage_a/<YYYYMMDD-HHMMSS>/
  stage_b/<YYYYMMDD-HHMMSS>/
  stage_c/<YYYYMMDD-HHMMSS>/
  stage_d/<YYYYMMDD-HHMMSS>/
  benchmark_manifest.yaml
```

## Tests

```bash
pytest -q
```

## Troubleshooting

- If `ai-etl` is not found, confirm your virtual environment is active and `pip install -e .` has run.
- If you cannot reach Ollama or ChromaDB, re-run `ai-etl doctor --verbose` and ensure `docker compose up -d` is running.
