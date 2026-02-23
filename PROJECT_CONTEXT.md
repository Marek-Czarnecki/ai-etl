## Project Overview

AI-ETL is a Typer-based CLI that drives a prompt-centric ETL workflow against a local Ollama instance, optionally persisting artifacts to ChromaDB. It reads rulebook/input files as text, renders YAML prompt templates, calls Ollama chat, writes outputs and run metadata to timestamped directories, and supports a multi-stage benchmark pack runner.

- Primary purpose: generate YAML outputs from rulebook-driven prompts and evaluate them via an LLM judge, with optional patch proposals for rulebooks.
- High-level architecture:
  - CLI orchestration: `src/ai_etl/cli.py`
  - Prompt loading/templating: `src/ai_etl/prompts.py`
  - Ollama client: `src/ai_etl/llm_ollama.py`
  - IO/YAML helpers: `src/ai_etl/io.py`, `src/ai_etl/yamlutil.py`, `src/ai_etl/models.py`
  - Chroma storage: `src/ai_etl/store_chroma.py`

## Runtime Architecture

Execution flow of `run`:

- `ai-etl run` calls `_run_once` (see `src/ai_etl/cli.py:315`, `src/ai_etl/cli.py:52`).
- `_run_once` loads config, creates a timestamped run directory (see `src/ai_etl/cli.py:72`, `src/ai_etl/cli.py:74`).
- Copies rulebook/input/expected files into the run directory (see `src/ai_etl/cli.py:84`).
- Loads and renders the prompt (see `src/ai_etl/cli.py:114`).
- Sends a chat request to Ollama (see `src/ai_etl/cli.py:125`).
- Writes `actual_output.yaml` (see `src/ai_etl/cli.py:141`).
- Writes `run_meta.yaml` (see `src/ai_etl/cli.py:173`).
- Optionally stores documents in Chroma when `--store-chroma` is set (see `src/ai_etl/cli.py:176`).

Execution flow of `benchmark`:

- Validates required pack files (see `src/ai_etl/cli.py:372`).
- Creates `out/benchmarks/<timestamp>` (see `src/ai_etl/cli.py:406`).
- Runs four `_run_once` stages (A/B/C/D) (see `src/ai_etl/cli.py:410`).
- Writes `benchmark_manifest.yaml` summarizing paths and status (see `src/ai_etl/cli.py:518`).

Stage definitions:

- A) `reg_to_controls` rulebook + `regulatory_excerpt` input (see `src/ai_etl/cli.py:410`).
- B) `controls_to_requirements` rulebook + Stage A `actual_output.yaml` (see `src/ai_etl/cli.py:430`).
- C) `validate_reporting_requirements` rulebook + Stage B `actual_output.yaml` using `prompts/stage_c_validate.yaml` (see `src/ai_etl/cli.py:450`).
- D) `judge` rulebook + expected `reporting_requirements.yaml` vs Stage B `actual_output.yaml` using `prompts/stage_d_judge.yaml` (see `src/ai_etl/cli.py:470`).

File outputs per stage:

- Stage A: `actual_output.yaml` + `run_meta.yaml` (see `src/ai_etl/cli.py:410`, `src/ai_etl/cli.py:173`).
- Stage B: `actual_output.yaml` + `run_meta.yaml` (see `src/ai_etl/cli.py:430`, `src/ai_etl/cli.py:173`).
- Stage C: `validation_report.yaml` + `run_meta.yaml` (see `src/ai_etl/cli.py:450`, `src/ai_etl/cli.py:173`).
- Stage D: `judge_report.yaml` + `run_meta.yaml` (see `src/ai_etl/cli.py:470`, `src/ai_etl/cli.py:173`).

Run directory structure:

- `<out_dir>/<YYYYMMDD-HHMMSS>/`
- `rulebook.<ext>` (see `src/ai_etl/cli.py:84`).
- Optional `input.<ext>` (see `src/ai_etl/cli.py:88`).
- Optional `expected.<ext>` (see `src/ai_etl/cli.py:94`).
- Optional `actual_input.<ext>` (see `src/ai_etl/cli.py:100`).
- `<output_name>` (`actual_output.yaml` or `judge_report.yaml` or `validation_report.yaml`) (see `src/ai_etl/cli.py:141`).
- `run_meta.yaml` (see `src/ai_etl/cli.py:173`).

Benchmark run directory structure:

- `out/benchmarks/<timestamp>/stage_a/<run_timestamp>/...`
- `out/benchmarks/<timestamp>/stage_b/<run_timestamp>/...`
- `out/benchmarks/<timestamp>/stage_c/<run_timestamp>/...`
- `out/benchmarks/<timestamp>/stage_d/<run_timestamp>/...`
- `out/benchmarks/<timestamp>/benchmark_manifest.yaml` (see `src/ai_etl/cli.py:518`).

## CLI Surface

All Typer commands (from `src/ai_etl/cli.py`):

- `doctor(verbose: bool = False)`
  - Options: `--verbose` default `False` (see `src/ai_etl/cli.py:201`).
  - Side effects: network checks to Ollama `/api/tags` and multiple Chroma health endpoints; no files written (see `src/ai_etl/cli.py:32`, `src/ai_etl/llm_ollama.py:66`).

- `diff(expected: Path, actual: Path, rulebook: Path, prompt: Path = prompts/stage_d_judge.yaml, out_dir: Path = out, model: Optional[str] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, max_tokens: Optional[int] = None, seed: Optional[int] = None, verbose: bool = False)`
  - Side effects: creates `<out_dir>/<timestamp>/`, writes `judge_report.yaml` and `run_meta.yaml` plus copied inputs (see `src/ai_etl/cli.py:218`, `src/ai_etl/cli.py:234`).

- `propose(rulebook: Path, diff_path: Path, input_path: Optional[Path] = None, expected_path: Optional[Path] = None, actual_path: Optional[Path] = None, prompt: Path = prompts/propose_patch.yaml, model: Optional[str] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, max_tokens: Optional[int] = None, seed: Optional[int] = None, verbose: bool = False)`
  - Side effects: none on disk; prints patch markdown and optional diff to stdout (see `src/ai_etl/cli.py:257`, `src/ai_etl/cli.py:308`).

- `run(rulebook: Path, input_path: Path, examples: Optional[List[Path]] = None, expected: Optional[Path] = None, prompt: Path = prompts/run_generate.yaml, model: Optional[str] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, max_tokens: Optional[int] = None, seed: Optional[int] = None, out_dir: Path = out, store_chroma_flag: bool = False, collection: str = ai_etl_runs, verbose: bool = False)`
  - Side effects: creates `<out_dir>/<timestamp>/`, writes `actual_output.yaml`, `run_meta.yaml`, and copied inputs; optionally stores documents in ChromaDB with embeddings (see `src/ai_etl/cli.py:315`, `src/ai_etl/cli.py:141`, `src/ai_etl/cli.py:176`).

- `benchmark(pack: Path, out_dir: Path = out, model: Optional[str] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, max_tokens: Optional[int] = None, seed: Optional[int] = None, verbose: bool = False)`
  - Side effects: creates `out/benchmarks/<timestamp>/stage_{a|b|c|d}/<run_timestamp>/...`, writes stage outputs and a `benchmark_manifest.yaml` (see `src/ai_etl/cli.py:386`, `src/ai_etl/cli.py:406`, `src/ai_etl/cli.py:518`).

## Prompt Architecture

Where prompts are stored:

- `prompts/run_generate.yaml`
- `prompts/stage_c_validate.yaml`
- `prompts/stage_d_judge.yaml`
- `prompts/propose_patch.yaml`

How prompts are loaded:

- `load_prompt` reads YAML with required keys `name`, `system`, `user_template` (see `src/ai_etl/prompts.py:11`).
- Missing keys or non-mapping YAML raise `ValueError` (see `src/ai_etl/prompts.py:16`).

Placeholder rendering mechanism:

- `render_user` uses `str.format_map` over `user_template` (see `src/ai_etl/prompts.py:31`).
- Missing variables raise `ValueError` (see `src/ai_etl/prompts.py:35`).

How prompts are passed to Ollama:

- `_run_once` builds `[{role: system}, {role: user}]` and calls `OllamaClient.chat` (see `src/ai_etl/cli.py:114`, `src/ai_etl/cli.py:128`).
- `propose` builds `[{role: system}, {role: user}]` and calls `OllamaClient.chat` (see `src/ai_etl/cli.py:288`, `src/ai_etl/cli.py:297`).

## LLM Integration

Ollama endpoint used:

- Base URL from `OLLAMA_BASE_URL` (default `http://localhost:11434`) (see `src/ai_etl/config.py:21`).
- Chat: `POST <base>/api/chat` (see `src/ai_etl/llm_ollama.py:46`).
- Embeddings: `POST <base>/api/embeddings` (see `src/ai_etl/llm_ollama.py:53`).
- Health: `GET <base>/api/tags` (see `src/ai_etl/llm_ollama.py:66`).

Request payload structure:

- `{"model": <model>, "messages": [{"role": "system"|"user", "content": <text>}], "stream": false}` (see `src/ai_etl/llm_ollama.py:38`).
- Optional `options` with: `temperature`, `top_p`, `num_predict`, `seed` (see `src/ai_etl/llm_ollama.py:28`).

Model selection logic:

- CLI `--model` overrides config default (see `src/ai_etl/cli.py:125`).
- Default model from `AI_ETL_DEFAULT_MODEL` (default `llama3.1`) (see `src/ai_etl/config.py:21`).

Timeout handling:

- Chat and embeddings requests: `timeout=1200` seconds (see `src/ai_etl/llm_ollama.py:48`, `src/ai_etl/llm_ollama.py:57`).
- Health checks: `timeout=10` seconds (see `src/ai_etl/llm_ollama.py:71`).

Streaming behavior:

- `stream` is always `False` in chat payload (see `src/ai_etl/llm_ollama.py:38`).

Seed/temperature handling:

- `temperature`, `top_p`, `max_tokens` (mapped to `num_predict`), and `seed` are passed only when not `None` (see `src/ai_etl/llm_ollama.py:28`).

## Data Formats

Input formats:

- Rulebooks and inputs are read as UTF-8 text with replacement on decode errors (see `src/ai_etl/io.py:10`).
- No parsing or validation is performed by the CLI (see `src/ai_etl/cli.py:79`).
- Benchmark pack rulebooks/inputs support `.yaml` or `.md` (see `src/ai_etl/cli.py:356`, `src/ai_etl/cli.py:364`).

Output formats:

- `actual_output.yaml` is the raw LLM response for `run_generate` and is not validated by code (see `prompts/run_generate.yaml:1`, `src/ai_etl/cli.py:141`).

Expected benchmark formats:

- Required expected files: `expected/controls.yaml`, `expected/reporting_requirements.yaml` (see `src/ai_etl/cli.py:372`).

Validation report format:

- Schema defined in `prompts/stage_c_validate.yaml` under `validation` (see `prompts/stage_c_validate.yaml:1`).

Judge report format:

- Schema defined in `prompts/stage_d_judge.yaml` under `judge` (see `prompts/stage_d_judge.yaml:1`).

Run metadata format:

- `run_meta.yaml` follows `RunMeta`/`RunParams` (see `src/ai_etl/models.py:10`).
- Fields include `run_id`, `created_at`, `rulebook_path`, `input_path`, `expected_path`, `model_params`, `file_hashes`, `timings`, `extra` (see `src/ai_etl/cli.py:144`).

Benchmark manifest format:

- Fields: `pack`, `created_at`, `stage_a`..`stage_d`, `status`, `notes` (see `src/ai_etl/cli.py:496`).

## Benchmark System

Required pack structure:

- `rulebooks/reg_to_controls.{yaml|md}`
- `rulebooks/controls_to_requirements.{yaml|md}`
- `rulebooks/validate_reporting_requirements.{yaml|md}`
- `rulebooks/judge.{yaml|md}`
- `inputs/regulatory_excerpt.{yaml|md}`
- `expected/controls.yaml`
- `expected/reporting_requirements.yaml` (see `src/ai_etl/cli.py:372`).

Stage chaining logic:

- Stage A output feeds Stage B input (see `src/ai_etl/cli.py:430`).
- Stage B output feeds Stage C input (see `src/ai_etl/cli.py:450`).
- Stage B output is the `actual` input for Stage D (see `src/ai_etl/cli.py:470`).
- Expected reporting requirements are used in Stages B and D (see `src/ai_etl/cli.py:434`, `src/ai_etl/cli.py:474`).

Manifest structure:

- `benchmark_manifest.yaml` with `stage_a`, `stage_b`, `stage_c`, `stage_d` blocks containing `run_dir` and output paths (see `src/ai_etl/cli.py:496`).

Hardcoded paths:

- Benchmark root: `<out_dir>/benchmarks/<timestamp>` (see `src/ai_etl/cli.py:406`).
- Stage prompts: `prompts/run_generate.yaml`, `prompts/stage_c_validate.yaml`, `prompts/stage_d_judge.yaml` (see `src/ai_etl/cli.py:416`, `src/ai_etl/cli.py:456`, `src/ai_etl/cli.py:476`).

## Diff / Judge Logic

How comparison currently works:

- `ai-etl diff` invokes the LLM judge prompt and writes `judge_report.yaml` (see `src/ai_etl/cli.py:218`, `src/ai_etl/cli.py:234`).
- No local diff is used in the CLI path.

Whether semantic diffing occurs in Python or via LLM:

- LLM judge performs semantic diffing (see `prompts/stage_d_judge.yaml:1`).
- Python `compare_texts` provides text metrics and unified diff but is not wired into CLI (see `src/ai_etl/compare.py:1`).

Output schema of judge:

- Defined in `prompts/stage_d_judge.yaml` under `judge` (see `prompts/stage_d_judge.yaml:1`).

## Proposal System

How rulebook patches are generated:

- `ai-etl propose` renders `prompts/propose_patch.yaml` and calls Ollama (see `src/ai_etl/cli.py:257`).
- LLM response is returned as markdown and optionally parsed into a diff (see `src/ai_etl/propose.py:46`).

Inputs used:

- Required: `rulebook`, `judge_report` (see `src/ai_etl/cli.py:281`).
- Optional: `input_text`, `expected`, `actual` (see `src/ai_etl/cli.py:284`).

Output format:

- If a fenced ```diff``` block is present, it is used directly (see `src/ai_etl/propose.py:23`).
- Else if `## Proposed Rulebook` is present, a unified diff is generated (see `src/ai_etl/propose.py:13`, `src/ai_etl/propose.py:33`).
- Else no diff is produced.

## Storage / Optional Components

Chroma integration:

- `--store-chroma` on `run` triggers `store_run` (see `src/ai_etl/cli.py:176`).
- Connects to ChromaDB over HTTP using `CHROMA_URL` (see `src/ai_etl/store_chroma.py:24`).
- Stores documents and metadata in a collection (see `src/ai_etl/store_chroma.py:34`).

Embeddings:

- If an `OllamaClient` is provided, embeddings are requested for each document (see `src/ai_etl/store_chroma.py:50`).
- If any embedding fails, the run is stored without embeddings (see `src/ai_etl/store_chroma.py:53`).

When invoked:

- Only `ai-etl run` can store to Chroma, controlled by `--store-chroma` (see `src/ai_etl/cli.py:315`).

## Dependency Graph

Internal module relationships:

- `src/ai_etl/cli.py` depends on `src/ai_etl/config.py`, `src/ai_etl/io.py`, `src/ai_etl/llm_ollama.py`, `src/ai_etl/models.py`, `src/ai_etl/prompts.py`, `src/ai_etl/propose.py`, `src/ai_etl/store_chroma.py`, `src/ai_etl/yamlutil.py`.
- `src/ai_etl/prompts.py` depends on `src/ai_etl/yamlutil.py`.
- `src/ai_etl/propose.py` depends on `src/ai_etl/prompts.py`.
- `src/ai_etl/store_chroma.py` depends on `src/ai_etl/llm_ollama.py`.
- `src/ai_etl/llm_ollama.py` depends on `requests`.
- `src/ai_etl/yamlutil.py` depends on `yaml` (PyYAML).
- `src/ai_etl/models.py` depends on `pydantic`.
- `src/ai_etl/compare.py` is standalone and not referenced by the CLI.

## Known Constraints and Assumptions

Format assumptions:

- Prompt outputs are expected to be YAML per prompt instructions (see `prompts/run_generate.yaml:1`).
- No YAML parsing/validation is enforced in code (see `src/ai_etl/cli.py:79`).
- All inputs are treated as UTF-8 text (see `src/ai_etl/io.py:10`).

Determinism assumptions:

- `temperature`, `top_p`, `max_tokens`, and `seed` are passed to Ollama when provided (see `src/ai_etl/llm_ollama.py:28`).
- Determinism depends on the model honoring these options.

Single-shot vs batch behavior:

- Each command issues a single Ollama chat call per stage (see `src/ai_etl/cli.py:127`).
- No batching or streaming (see `src/ai_etl/llm_ollama.py:38`).

Architectural limitations:

- Diffing for correctness is LLM-based (see `prompts/stage_d_judge.yaml:1`).
- Local diff logic exists but is not integrated into CLI (see `src/ai_etl/compare.py:1`).
- Prompt rendering fails fast on missing placeholders (see `src/ai_etl/prompts.py:31`).
