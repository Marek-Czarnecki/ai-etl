Objective: Convert a numbered list of rules into structured controls.

Input format:
- Plain text with numbered lines (e.g., "1. ...", "2. ...").

Output format:
```yaml
controls:
  - control_id: CTRL-001
    title: Control title
    description: Description text
    severity: High
    rationale: Rationale text
  - control_id: CTRL-002
    title: Control title 2
    description: Description text 2
    severity: Medium
    rationale: Rationale text 2
```

Rules:
- Output only YAML. No markdown fences. No commentary.
- Output a single YAML mapping with a key named controls.
- The controls value is a list (array) of elements.
- Each numbered input line becomes one element in the controls list.
- Each element is a mapping (dictionary) with key/value pairs: control_id, title, description, severity, rationale.
- Use unique control_id values in ascending order: CTRL-001, CTRL-002, ...
- Each control must include a title that summarizes the rule.
- Each control must include a description that restates the rule in a full sentence.
- Each control must include a severity which is either: High, Medium, or Low.
- Each control must include a rationale that briefly explains why the rule is needed.
- Indent controls two spaces under controls: and indent child keys two spaces further.
