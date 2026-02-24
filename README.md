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
  --input examples/input.yaml \
  --model llama3.2:1b
```

Simple job with a clean diff:

```bash
ai-etl run \
  --rulebook examples/rulebook.yaml \
  --input examples/input.yaml \
  --examples examples/example_1.yaml \
  --expected examples/expected.yaml \
  --model llama3.2:1b \
  --temperature 0
```

```bash
ai-etl diff \
  --rulebook examples/rulebook.yaml \
  --expected examples/expected.yaml \
  --actual out/<run_id>/actual_output.yaml \
  --prompt prompts/stage_d_judge.yaml \
  --model llama3.2:1b \
  --temperature 0
```

Note: `ai-etl diff` prints the judge report to stdout and writes it to `out/<timestamp>/judge_report.yaml`.

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

Benchmark Packs 02 and 03 run a 3-stage pipeline (A/B/C) and follow the same `ai-etl run` pattern as pack 01:

```bash
ai-etl run \
  --rulebook examples/benchmark_pack_02/rulebooks/guideline_to_controls.md \
  --input examples/benchmark_pack_02/inputs/medical_guideline_excerpt.md \
  --expected examples/benchmark_pack_02/expected/controls.yaml
```

```bash
ai-etl run \
  --rulebook examples/benchmark_pack_02/rulebooks/controls_to_requirements.md \
  --input <StageA actual_output.yaml> \
  --expected examples/benchmark_pack_02/expected/reporting_requirements.yaml
```

```bash
ai-etl run \
  --rulebook examples/benchmark_pack_02/rulebooks/requirements_to_flags.md \
  --input examples/benchmark_pack_02/inputs/clinical_events.csv \
  --examples <StageB actual_output.yaml> \
  --expected examples/benchmark_pack_02/expected/flags.yaml
```

```bash
ai-etl run \
  --rulebook examples/benchmark_pack_03/rulebooks/contract_to_controls.md \
  --input examples/benchmark_pack_03/inputs/contract_excerpt.md \
  --expected examples/benchmark_pack_03/expected/controls.yaml
```

```bash
ai-etl run \
  --rulebook examples/benchmark_pack_03/rulebooks/controls_to_requirements.md \
  --input <StageA actual_output.yaml> \
  --expected examples/benchmark_pack_03/expected/reporting_requirements.yaml
```

```bash
ai-etl run \
  --rulebook examples/benchmark_pack_03/rulebooks/requirements_to_flags.md \
  --input examples/benchmark_pack_03/inputs/contract_events.csv \
  --examples <StageB actual_output.yaml> \
  --expected examples/benchmark_pack_03/expected/flags.yaml
```

Transaction flags flow (requirements + transactions -> flags, then diff):

```bash
ai-etl run \
  --rulebook examples/benchmark_pack_01/rulebooks/requirements_to_flags.yaml \
  --input examples/benchmark_pack_01/inputs/requirements_and_transactions.yaml \
  --examples examples/benchmark_pack_01/expected/flags.yaml \
  --prompt examples/benchmark_pack_01/prompts/requirements_to_flags.yaml \
  --out-dir out \
  --model llama3.2:1b \
  --temperature 0 \
  --top-p 1 \
  --max-tokens 2048 \
  --seed 42 \
  --verbose
```

```bash
ai-etl diff \
  --rulebook examples/benchmark_pack_01/rulebooks/flags_judge.yaml \
  --expected examples/benchmark_pack_01/expected/flags.yaml \
  --actual out/<stage_e>/actual_output.yaml \
  --prompt examples/benchmark_pack_01/prompts/flags_judge.yaml \
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
