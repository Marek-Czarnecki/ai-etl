# guideline_to_controls

Objective: Extract controls from the medical guideline excerpt.

Output format:

```yaml
controls:
  - control_id: CTRL-001
    title: Control title
    description: Description text
    severity: High
    rationale: Rationale text
```

Rules:
- Output only YAML. No markdown fences. No commentary.
- Output must be a single YAML mapping named controls (only one controls key).
- Read each numbered line in the input; every numbered line is a rule.
- Output exactly one control per numbered rule. Do not merge rules.
- Use unique control_id values (CTRL-001, CTRL-002, ...).
- Use severity exactly: High, Medium, or Low.
- Each control must include a title that summarizes the rule.
- Each control must include a description that restates the rule with its conditions/thresholds in a full sentence.
- Each control must include a rationale that briefly explains why that rule is needed.
- Indent controls two spaces under controls: and indent child keys two spaces further.
