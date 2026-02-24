# requirements_to_flags

Objective: Apply reporting requirements to clinical events and emit deterministic flags with summary counts.

Output format:

```yaml
flags:
  - transaction_id: "TX-0001"
    requirement_id: "REQ-001"
    severity: "High"
    reason: "..."
    evidence: "..."
summary:
  total_transactions: 20
  flagged_transactions: 9
  flagged_by_severity:
    High: 3
    Medium: 4
    Low: 2
```

Rules:
- Output must be a single YAML mapping with keys: flags, summary.
- Do not include markdown fences or commentary. Return only YAML.
- Apply each requirement's detection_logic to the input CSV rows.
- A transaction can produce multiple flags if it meets multiple requirements.
- Provide concise reasons and concrete evidence values.
- Ensure summary counts match the flags list.
