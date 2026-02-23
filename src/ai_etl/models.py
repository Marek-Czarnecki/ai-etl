"""Pydantic models for run artifacts."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RunParams(BaseModel):
    """Parameters used for LLM calls."""

    model: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    seed: Optional[int] = None


class RunMeta(BaseModel):
    """Run metadata persisted alongside artifacts."""

    run_id: str
    created_at: str
    rulebook_path: str
    input_path: str
    expected_path: Optional[str] = None
    model_params: RunParams
    file_hashes: Dict[str, str]
    timings: Dict[str, float]
    extra: Dict[str, Any] = Field(default_factory=dict)
