Objective: Convert a numbered list of rules into a markdown table of controls.

Input format:
- Plain text with numbered lines (e.g., "1. ...", "2. ...").

Output format:
- Return only a markdown table with this header and separator:
  control_id | title | description | severity | rationale
  --- | --- | --- | --- | ---
- Each numbered input line becomes one table row.

Rules:
- Output only the markdown table. No extra text or commentary.
- Use unique control_id values in ascending order: CTRL-001, CTRL-002, ...
- Title: short summary of the rule.
- Description: full sentence restating the rule with conditions/thresholds.
- Severity: High, Medium, or Low.
- Rationale: brief reason why the rule is needed.
