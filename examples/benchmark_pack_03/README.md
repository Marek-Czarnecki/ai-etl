# Benchmark Pack 03 (Contract Clauses)

This pack exercises a 3-stage pipeline over a synthetic contract excerpt and event data.

Stage A (contract -> controls):

```bash
ai-etl run --rulebook examples/benchmark_pack_03/rulebooks/contract_to_controls.md \
           --input examples/benchmark_pack_03/inputs/contract_excerpt.md \
           --expected examples/benchmark_pack_03/expected/controls.yaml
```

Stage B (controls -> reporting requirements):

```bash
ai-etl run --rulebook examples/benchmark_pack_03/rulebooks/controls_to_requirements.md \
           --input <StageA actual_output.yaml> \
           --expected examples/benchmark_pack_03/expected/reporting_requirements.yaml
```

Stage C (requirements + events -> flags):

```bash
ai-etl run --rulebook examples/benchmark_pack_03/rulebooks/requirements_to_flags.md \
           --input examples/benchmark_pack_03/inputs/contract_events.csv \
           --examples <StageB actual_output.yaml> \
           --expected examples/benchmark_pack_03/expected/flags.yaml
```

Note: Stage B actual output is used as examples input for Stage C.
