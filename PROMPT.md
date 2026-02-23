You are Codex acting as a senior Python engineer. Build a small, production-lean “AI ETL” CLI application that runs alongside this existing docker-compose stack (already present at /mnt/data/docker-compose.yml):

- ollama at http://localhost:11434
- chromadb-server at http://localhost:8000
- open-webui (already configured)

Goal
Create a Python application wrapper that executes a generic prompt-driven workflow:

1) Read the rule book (text/markdown)
2) Read the input (text/markdown/json)
3) If examples are provided, read those to guide generation of the output
4) Use the rule book to generate an output (LLM call via Ollama)
5) If an “expected output” is provided, compare expected vs generated
6) Use the comparison to suggest modifications to the rule book:
   - propose new rules and/or revisions to existing rules
   - output should be actionable (diff-like suggestions + rationale)
7) Persist run artifacts (inputs/outputs/diffs/metadata) for traceability, and optionally embed/index them in ChromaDB.

Non-negotiables
- The app must run locally via the existing stack (no external network calls required).
- Use the Ollama HTTP API (requests) and support configurable model name.
- Provide a clean CLI with subcommands and good error messages.
- Provide deterministic-ish behavior options: temperature/top_p/seed where supported; document what’s supported.
- Provide unit tests for the core comparison and “rulebook patch proposal” formatting logic.
- Include a README with exact commands to run, including docker compose steps.
- Do NOT implement a web UI; CLI-only is enough.

Deliverables (create these files)
Repository layout (create exactly this structure):

ai_etl/
  pyproject.toml
  README.md
  src/ai_etl/
    __init__.py
    cli.py
    config.py
    io.py
    llm_ollama.py
    compare.py
    propose.py
    store_chroma.py
    models.py
  tests/
    test_compare.py
    test_propose.py
  examples/
    rulebook.md
    input.txt
    expected.txt
    example_1.md
  docker/
    Dockerfile
    docker-compose.override.yml

Key behaviours
A) CLI
Implement:
- ai-etl run --rulebook path --input path [--examples dir_or_files...] [--expected path]
             [--model MODEL] [--temperature X] [--top-p X] [--max-tokens N]
             [--out-dir path] [--store-chroma] [--collection NAME]
- ai-etl diff --expected path --actual path  (prints structured diff/metrics)
- ai-etl propose --rulebook path --diff path (prints a “patch proposal”)
- ai-etl doctor (checks connectivity to Ollama + Chroma endpoints and prints status)

B) Run output artifacts
When `run` executes, write a timestamped run folder:
out/<YYYYMMDD-HHMMSS>/
  rulebook.md (copy)
  input.<ext> (copy)
  expected.<ext> (if provided)
  actual_output.md
  comparison.json
  rulebook_patch.md   (human-readable)
  rulebook_patch.diff (unified diff format against the original rulebook if possible)
  run_meta.json       (model, params, timings, hashes, file paths)

C) LLM prompting
Implement two LLM calls (both via Ollama):
1) “Generate output” call:
   System: concise instruction to obey rulebook, use examples, produce output only.
   User: include: rulebook content, input content, examples content (if any).
   Output: actual_output.md

2) “Suggest rulebook improvements” call (only if expected provided):
   System: instruct model to propose rule changes that reduce mismatch.
   User: include: rulebook, input, expected, actual, and a machine-readable diff/metrics summary.
   Output: rulebook_patch.md (and attempt to produce a unified diff, or a structured patch section that can be converted to diff)

D) Comparison logic (local)
Create a comparison module that works without the LLM:
- If both expected and actual are text:
  - compute similarity metrics (token/line-level; e.g., difflib ratio)
  - generate a unified diff (difflib.unified_diff)
  - output a stable JSON structure in comparison.json:
    { "summary": {...}, "diff_unified": "...", "by_section": [... optional ...] }
- Keep it simple and robust; no heavy NLP dependencies.

E) Chroma persistence (optional)
If --store-chroma is set:
- store run documents in ChromaDB (chromadb python client) in collection NAME (default “ai_etl_runs”)
- store embeddings via Ollama embeddings endpoint if available; if not available, store without embeddings but still persist metadata+documents.
- At minimum: store documents (rulebook, input, expected, actual, patch) and run_meta.

F) Docker integration
- Create docker/Dockerfile for the ai_etl app (small, python-slim)
- Create docker/docker-compose.override.yml that adds a service `ai-etl` to the existing compose stack, wired to:
  - OLLAMA_BASE_URL=http://ollama:11434
  - CHROMA_URL=http://chromadb-server:8000
  - mount a local ./out directory
- Do not modify the user’s base compose file; override only.

Config
- Environment variables supported:
  - OLLAMA_BASE_URL (default http://localhost:11434)
  - CHROMA_URL (default http://localhost:8000)
  - AI_ETL_DEFAULT_MODEL (default something sensible like “llama3.1” but allow override)
- Also allow CLI flags to override.

Implementation details
- Use Python 3.11+
- Use typer or argparse (choose one; prefer typer for ergonomics)
- Use pydantic for config/models if helpful, but don’t over-engineer.
- Use requests for HTTP to Ollama.
- Add logging with --verbose.
- Make the code readable; docstrings for public functions.

Acceptance criteria (must satisfy)
1) `ai-etl doctor` returns OK when docker compose stack is up.
2) `ai-etl run --rulebook examples/rulebook.md --input examples/input.txt --examples examples/example_1.md --expected examples/expected.txt`
   produces an out/<timestamp>/ directory with all required artifacts.
3) `ai-etl diff` produces unified diff and JSON metrics.
4) Unit tests pass: `pytest -q`
5) README provides exact run commands:
   - docker compose up -d (base stack)
   - docker compose -f docker-compose.yml -f docker/docker-compose.override.yml up -d (with ai-etl service)
   - CLI invocations from host

Steps
- First, generate the full project scaffold and implement the modules.
- Then add tests.
- Then write README.
- Finally, add Dockerfile and compose override.

Return the final result as created files (write the code into the repository). Do not ask me questions; make reasonable defaults and document them.