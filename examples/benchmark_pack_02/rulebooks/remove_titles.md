Objective: Remove markdown titles and unnumbered paragraphs from the input.

Output format:
- Output plain text only.
- Keep only numbered list items (lines that start with a number followed by a period and a space, e.g., "1. ").

Rules:
- Remove markdown titles (lines starting with "#").
- Remove unnumbered paragraphs and blank lines.
- Preserve the original numbered lines exactly as they appear, including punctuation.
