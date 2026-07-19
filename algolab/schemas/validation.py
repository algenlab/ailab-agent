"""Validation and build artifact schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from algolab.schemas.correctness import ContractValidationReport, CorrectnessContract
from algolab.schemas.demo_readiness import DemoReadinessReport
from algolab.schemas.render_report import RenderReport
from algolab.schemas.scene_graph import SceneGraph
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.visual_plan import VisualPlan


class ReleaseGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_ready: bool = False
    process_ready: bool = False
    trace_ready: bool = False
    visual_ready: bool = False
    multi_solution_ready: bool = False
    release_ready: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)


DegradationType = Literal[
    "answer_only",
    "schema_scene_only",
    "process_fallback",
    "process_uncovered",
    "demo_warn",
]


class DegradationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: DegradationType
    reason: str
    source: str = ""
    affected_variant: str = ""
    blocking: bool = False


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    degradations: list[DegradationEntry] = Field(default_factory=list)
    contract_validation: ContractValidationReport | None = None
    contract_test_results: list[dict[str, Any]] = Field(default_factory=list)
    demo_readiness: DemoReadinessReport = Field(default_factory=DemoReadinessReport)
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
    correctness_contract: CorrectnessContract | None = None
    visual_plan: VisualPlan | None = None
    render_report: RenderReport | None = None
