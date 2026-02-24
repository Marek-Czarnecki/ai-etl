# Benchmark Pack 02 (Medical)

This pack exercises a 3-stage pipeline over a synthetic clinical guideline excerpt and event data.

Stage A (guideline -> controls):

```bash
ai-etl run --rulebook examples/benchmark_pack_02/rulebooks/guideline_to_controls.md \
           --input examples/benchmark_pack_02/inputs/medical_guideline_excerpt.md \
           --expected examples/benchmark_pack_02/expected/controls.yaml
```

Stage B (controls -> reporting requirements):

```bash
ai-etl run --rulebook examples/benchmark_pack_02/rulebooks/controls_to_requirements.md \
           --input <StageA actual_output.yaml> \
           --expected examples/benchmark_pack_02/expected/reporting_requirements.yaml
```

Stage C (requirements + events -> flags):

```bash
ai-etl run --rulebook examples/benchmark_pack_02/rulebooks/requirements_to_flags.md \
           --input examples/benchmark_pack_02/inputs/clinical_events.csv \
           --examples <StageB actual_output.yaml> \
           --expected examples/benchmark_pack_02/expected/flags.yaml
```

Note: Stage B actual output is used as examples input for Stage C.
