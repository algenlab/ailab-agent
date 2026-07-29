"""Runtime-owned evidence for a single instrumented algorithm execution."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from algolab.verification.result_normalizer import to_jsonable


ExecutionMode = Literal["atomic", "decoupled"]


def state_digest(value: Any) -> str:
    payload = json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ExecutionTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    index: int = Field(ge=0)
    op: str
    targets: list[str] = Field(default_factory=list)
    before_state_hash: str
    after_state_hash: str
    event_index: int | None = Field(default=None, ge=0)
    callsite_line: int = Field(ge=1)
    committed: bool
    claim_mismatches: list[str] = Field(default_factory=list)


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "single-execution-record-v1"
    run_id: str
    mode: ExecutionMode
    result: Any = None
    result_hash: str
    initial_state_hash: str
    final_state_hash: str
    transitions: list[ExecutionTransition] = Field(default_factory=list)

