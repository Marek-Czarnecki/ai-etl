# controls_to_requirements

Objective: Convert controls into concrete reporting requirements that can be evaluated against clinical event data.

Output format:
- For each requirement, output a markdown heading:
  ## REQ-001
- Under each heading, include markdown bullets for keys:
  - title: Title text
  - requirement_id: REQ-001
  - description: Full description text
  - severity: High
  - control_ids: CTRL-001
  - detection_logic: if event_type == med_order and medication == Nevarel and lab_name == eGFR and lab_value < 30

Input format:
- Markdown table with columns: control_id | title | description | severity | rationale

Rules:
- Output only markdown. No YAML. No commentary.
- Create one requirement for every control row in the table.
- Each requirement must map back to the control_id from the same row.
- Use requirement_id values in ascending order: REQ-001, REQ-002, ...
- Use severity exactly: High, Medium, or Low.
- Provide detection_logic as a single plain string.
- Constrain detection_logic to the clinical_events.csv fields only (event_type, medication, dose_mg, lab_name, lab_value, allergy, systolic_bp, pregnancy_status, follow_up_days, documentation_complete).
- Replace the sample title and sample field values with actual content derived from the input.
