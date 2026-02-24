# Benchmark Pack 01 — Extract → Transform → Validate → Judge

This benchmark pack is designed to stress-test the AI-ETL workflow across four stages.

Stages:
A) regulatory_excerpt.yaml -> controls.yaml
B) controls.yaml -> reporting_requirements.yaml
C) reporting_requirements.yaml -> validation_report.yaml
D) judge(expected vs actual reporting_requirements)
E) (manual) reporting_requirements + transactions -> flags, then judge flags

Notes:
- All content is synthetic.
- The "expected" outputs can be used for ai-etl judge comparisons.
- Requirement logic is intentionally simple and computable (thresholds, regex-ish cues, rolling windows).
- If you want a quick sanity check before this pack, run the simple test in the repo root README ("Running a Simple Job").

## Task List (from nothing running to a completed simple test)

1) Start the local services (Ollama + ChromaDB)
2) Set up the local CLI (virtualenv + editable install)
3) Verify connectivity with `ai-etl doctor`
4) Run Stage A (regulatory excerpt -> controls)
5) Run Stage B (controls -> reporting requirements)
6) Run Stage C (reporting requirements -> validation report)
7) Run Stage D (judge expected vs actual)
8) (Optional) Run Stage E (apply requirements to transactions, then judge flags)

## Step-by-step (do one at a time)

### Step 1: Start the local services

From the repo root:

```bash
docker compose up -d
```

If the model did not pull automatically:

```bash
docker compose exec ollama ollama pull llama3.2:1b
```

### Step 2: Set up the local CLI

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Step 3: Verify connectivity

```bash
ai-etl doctor --verbose
```

### Step 4: Stage A

```bash
ai-etl run --rulebook rulebooks/reg_to_controls.yaml --input inputs/regulatory_excerpt.yaml
```

### Step 5: Stage B

```bash
ai-etl run --rulebook rulebooks/controls_to_requirements.yaml --input expected/controls.yaml
```

### Step 6: Stage C

```bash
ai-etl run --rulebook rulebooks/validate_reporting_requirements.yaml --input out/<stage_b>/actual_output.yaml
```

### Step 7: Stage D (judge)

```bash
ai-etl diff --rulebook rulebooks/judge.yaml --expected expected/reporting_requirements.yaml --actual out/<stage_b>/actual_output.yaml
```

### Step 8: Stage E (requirements + transactions -> flags, then judge)

This step is manual and not part of `ai-etl benchmark`. The input file below uses the expected requirements to avoid compounding earlier stage errors.

```bash
ai-etl run --rulebook rulebooks/requirements_to_flags.yaml --input inputs/requirements_and_transactions.yaml
```

```bash
ai-etl diff --rulebook rulebooks/flags_judge.yaml --expected expected/flags.yaml --actual out/<stage_e>/actual_output.yaml
```
