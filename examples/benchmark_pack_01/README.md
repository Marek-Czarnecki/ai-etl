# Benchmark Pack 01 — Extract → Transform → Validate → Judge

This benchmark pack is designed to stress-test the AI-ETL workflow across four stages.

Stages:
A) regulatory_excerpt.yaml -> controls.yaml
B) controls.yaml -> reporting_requirements.yaml
C) reporting_requirements.yaml -> validation_report.yaml
D) judge(expected vs actual reporting_requirements)

Notes:
- All content is synthetic.
- The "expected" outputs can be used for ai-etl judge comparisons.
- Requirement logic is intentionally simple and computable (thresholds, regex-ish cues, rolling windows).

Suggested commands (adjust to your CLI conventions):
- Stage A:
  ai-etl run --rulebook rulebooks/reg_to_controls.yaml --input inputs/regulatory_excerpt.yaml

- Stage B:
  ai-etl run --rulebook rulebooks/controls_to_requirements.yaml --input expected/controls.yaml

- Stage C:
  ai-etl run --rulebook rulebooks/validate_reporting_requirements.yaml --input out/<stage_b>/actual_output.yaml

You can also judge:
  ai-etl diff --rulebook rulebooks/judge.yaml --expected expected/reporting_requirements.yaml --actual out/<stage_b>/actual_output.yaml
