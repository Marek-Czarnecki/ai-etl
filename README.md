# AI ETL

A small, production-lean CLI that runs alongside the local Ollama + ChromaDB stack.

## Requirements

- Python 3.11+
- Docker + docker compose (for the existing stack)

## Setup

From the repo root:

```bash
docker compose up -d
```

Install the CLI locally:

```bash
cd ai_etl
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Usage

Web endpoints (when the stack is up):

- Open WebUI: http://localhost:3000
- Ollama API: http://localhost:11434
- ChromaDB API: http://localhost:8000

CLI entry points:

- `ai-etl doctor` (health checks for Ollama + ChromaDB)
- `ai-etl run` (run the end-to-end workflow and persist artifacts)
- `ai-etl diff` (compare expected vs actual outputs)
- `ai-etl propose` (generate rulebook patch proposals)

Check connectivity:

```bash
ai-etl doctor
```

If the model did not pull automatically, install it manually:

```bash
docker exec -it ai-etl-ollama-1 ollama pull llama3.2:1b
```

Run the workflow:

```bash
ai-etl run \
  --rulebook examples/rulebook.md \
  --input examples/input.txt \
  --examples examples/example_1.md \
  --expected examples/expected.txt
```

Print a structured diff:

```bash
ai-etl diff --expected examples/expected.txt --actual out/<timestamp>/actual_output.md
```

Generate a patch proposal from a diff JSON:

```bash
ai-etl propose --rulebook examples/rulebook.md --diff out/<timestamp>/comparison.json
```

## Outputs

Each `run` creates:

```
out/<YYYYMMDD-HHMMSS>/
  rulebook.md
  input.<ext>
  expected.<ext>
  actual_output.md
  comparison.json
  rulebook_patch.md
  rulebook_patch.diff
  run_meta.json
```

## Configuration

Environment variables:

- `OLLAMA_BASE_URL` (default: http://localhost:11434)
- `CHROMA_URL` (default: http://localhost:8000)
- `AI_ETL_DEFAULT_MODEL` (default: llama3.1)

CLI flags override env vars.

## Determinism

`--temperature`, `--top-p`, and `--seed` are passed to Ollama options where supported.
If the model ignores a parameter, Ollama will fall back to its default behavior.

## Runtime notes

- On macOS with Python 3.9, `urllib3` may warn about LibreSSL; this is harmless.
- `ai-etl doctor` checks multiple ChromaDB health endpoints to support different versions.
- If `ollama-init` fails to pull the model, use the manual pull command above.

## Tests

```bash
cd ai_etl
pytest -q
```
