# controls_to_requirements

Objective: Convert controls into concrete reporting requirements that can be evaluated against contract event data.

Output format:

```yaml
requirements:
  - requirement_id: "REQ-001"
    title: "..."
    description: "..."
    severity: "High"
    control_ids:
      - "CTRL-001"
    detection_logic: "if event_type == ... and value > ..."
```

Rules:
- Create 6-10 requirements only. No duplicates.
- Each requirement must map back to one or more control_ids.
- Use requirement_id values in order: REQ-001, REQ-002, ...
- Keep detection_logic as a single plain string.
- Use severity exactly: High, Medium, or Low.
- Keep requirements testable against the CSV schema.
- Output only YAML. No markdown fences in the final output.
