"""File IO utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


def read_text(path: Path) -> str:
    """Read a text file with utf-8 fallback."""

    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    """Write text to file with utf-8 encoding."""

    path.write_text(content, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    """Copy file contents by reading and writing."""

    dst.write_bytes(src.read_bytes())


def sha256_text(text: str) -> str:
    """Return sha256 hex digest for text."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gather_example_files(paths: Iterable[Path]) -> list[Path]:
    """Return a list of example files from paths or directories."""

    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.iterdir() if p.is_file()))
        else:
            files.append(path)
    return files
