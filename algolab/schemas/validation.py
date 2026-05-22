"""Validation and build artifact schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from algolab.schemas.scene_graph import SceneGraph
from algolab.schemas.semantic_trace import SolutionVariant


class ReleaseGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_ready: bool = False
    process_ready: bool = False
    trace_ready: bool = False
    visual_ready: bool = False
    multi_solution_ready: bool = False
    release_ready: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    release_gate: ReleaseGate = Field(default_factory=ReleaseGate)


class BuildArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "algolab-build-v1"
    problem_title: str
    input_contract: str = ""
    input_data: Any
    expected_result: Any = None
    verifier_result: Any = None
    variants: list[SolutionVariant]
    scenes: dict[str, SceneGraph]
    validation: ValidationReport
