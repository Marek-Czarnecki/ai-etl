# contract_to_controls

Objective: Extract a concise set of auditable controls from the contract excerpt.

Output format:

```yaml
controls:
  - control_id: "CTRL-001"
    title: "..."
    description: "..."
    severity: "High"
    rationale: "..."
```

Rules:
- Create 6-10 controls only. No duplicates.
- Controls must be testable and specific to the excerpt.
- Use control_id values in order: CTRL-001, CTRL-002, ...
- Use severity exactly: High, Medium, or Low.
- Keep descriptions short and action-oriented.
- Keep rationale tied to the excerpt wording.
- Output only YAML. No markdown fences in the final output.
