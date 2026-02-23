"""YAML helpers with stable formatting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml_text(text: str) -> Any:
    """Parse YAML text into Python objects."""

    return yaml.safe_load(text)


def dump_yaml(obj: Any) -> str:
    """Dump YAML with stable formatting."""

    return yaml.safe_dump(
        obj,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        explicit_start=False,
        indent=2,
    )


def load_yaml_path(path: Path) -> Any:
    """Parse YAML file content into Python objects."""

    return load_yaml_text(path.read_text(encoding="utf-8", errors="replace"))


def dump_yaml_path(path: Path, obj: Any) -> None:
    """Write YAML to a file with stable formatting."""

    path.write_text(dump_yaml(obj), encoding="utf-8")
