"""Local comparison logic for expected vs actual outputs.

Only text diffs are supported. Semantic comparisons are handled by the judge prompt.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict


def _similarity_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=a, b=b).ratio()


def diff_unified(expected_text: str, actual_text: str) -> str:
    expected_lines = expected_text.splitlines(keepends=True)
    actual_lines = actual_text.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile="expected",
            tofile="actual",
        )
    )


def compare_texts(expected: str, actual: str) -> Dict[str, Any]:
    """Compare two outputs and return metrics plus unified diff."""

    expected_tokens = expected.split()
    actual_tokens = actual.split()

    diff = diff_unified(expected, actual)

    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)

    summary = {
        "mode": "text",
        "expected_chars": len(expected),
        "actual_chars": len(actual),
        "expected_lines": len(expected_lines),
        "actual_lines": len(actual_lines),
        "expected_tokens": len(expected_tokens),
        "actual_tokens": len(actual_tokens),
        "char_similarity": _similarity_ratio(expected, actual),
        "line_similarity": _similarity_ratio("".join(expected_lines), "".join(actual_lines)),
        "token_similarity": _similarity_ratio(" ".join(expected_tokens), " ".join(actual_tokens)),
    }

    return {
        "summary": summary,
        "diff_unified": diff,
        "by_section": [],
    }
