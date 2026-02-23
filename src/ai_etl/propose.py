"""Rulebook patch proposal helpers."""

from __future__ import annotations

import difflib
import re
from typing import Optional, Tuple


def build_patch_prompt(
    rulebook: str,
    input_text: str,
    expected: str,
    actual: str,
    diff_summary_json: str,
) -> tuple[str, str]:
    """Build system and user prompts for patch proposal."""

    system = (
        "You propose concise, actionable rulebook edits to reduce mismatches. "
        "Return Markdown with sections: '## Proposed Rulebook' (full text), "
        "'## Rationale', and optional '## Diff' with a ```diff block if possible."
    )

    user = (
        "Rulebook:\n" + rulebook + "\n\n"
        "Input:\n" + input_text + "\n\n"
        "Expected Output:\n" + expected + "\n\n"
        "Actual Output:\n" + actual + "\n\n"
        "Diff Summary (JSON):\n" + diff_summary_json
    )
    return system, user


def extract_proposed_rulebook(text: str) -> Optional[str]:
    """Extract the proposed full rulebook from a markdown response."""

    pattern = re.compile(r"## Proposed Rulebook\s+(.*?)(?:\n## |\Z)", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip()


def extract_diff_block(text: str) -> Optional[str]:
    """Extract a diff fenced block if present."""

    pattern = re.compile(r"```diff\n(.*?)```", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip() + "\n"


def build_unified_diff(original: str, proposed: str) -> str:
    """Create a unified diff between original and proposed rulebooks."""

    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile="rulebook.md",
            tofile="rulebook_proposed.md",
        )
    )


def prepare_patch_artifacts(rulebook: str, llm_output: str) -> Tuple[str, str]:
    """Return (patch_markdown, patch_diff) from LLM output."""

    patch_markdown = llm_output.strip() + "\n"

    diff_block = extract_diff_block(llm_output)
    if diff_block:
        return patch_markdown, diff_block

    proposed = extract_proposed_rulebook(llm_output)
    if proposed:
        return patch_markdown, build_unified_diff(rulebook, proposed)

    return patch_markdown, ""
