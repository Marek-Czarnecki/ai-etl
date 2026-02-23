"""Configuration helpers for AI ETL."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration sourced from env vars."""

    ollama_base_url: str
    chroma_url: str
    default_model: str


def load_config() -> AppConfig:
    """Load configuration from environment variables."""

    return AppConfig(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        chroma_url=os.getenv("CHROMA_URL", "http://localhost:8000"),
        default_model=os.getenv("AI_ETL_DEFAULT_MODEL", "llama3.1"),
    )
