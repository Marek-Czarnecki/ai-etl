"""Prompt loader and renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ai_etl.yamlutil import load_yaml_path


def load_prompt(path: Path) -> Dict[str, str]:
    """Load a prompt YAML file and validate required keys."""

    data = load_yaml_path(path)
    if not isinstance(data, dict):
        raise ValueError(f"Prompt file must be a YAML mapping: {path}")

    required = {"name", "system", "user_template"}
    missing = required - set(data.keys())
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Prompt file missing keys ({missing_list}): {path}")

    return {
        "name": str(data["name"]),
        "system": str(data["system"]),
        "user_template": str(data["user_template"]),
    }


def render_user(user_template: str, **kwargs: Any) -> str:
    """Render user template with format_map and explicit missing-key errors."""

    try:
        return user_template.format_map(kwargs)
    except KeyError as exc:
        raise ValueError(f"Missing prompt variable: {exc}") from exc
