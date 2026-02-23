"""Rulebook patch proposal helpers."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Optional, Tuple

from ai_etl.prompts import load_prompt, render_user


def extract_proposed_rulebook(text: str) -> Optional[str]:
    """Extract the proposed full rulebook from a markdown response."""

    pattern = re.compile(r"## Proposed Rulebook\s+(.*?)(?:\n## |\Z)", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip()


def extract_diff_block(text: str) -> Optional[str]:
    """Extract a diff fenced block if present."""

    pattern = re.compile(r"```diff\s*\n(.*?)```", re.DOTALL)
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
            fromfile="rulebook.yaml",
            tofile="rulebook_proposed.yaml",
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


def build_patch_prompt(
    prompt_path: str,
    *,
    rulebook: str,
    input_text: str,
    expected: str,
    actual: str,
    judge_report: str,
) -> tuple[str, str]:
    """Load a prompt file and render system/user content for patch proposal."""

    prompt = load_prompt(Path(prompt_path))
    user = render_user(
        prompt["user_template"],
        rulebook=rulebook,
        input_text=input_text,
        expected=expected,
        actual=actual,
        judge_report=judge_report,
    )
    return prompt["system"], user
