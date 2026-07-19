"""Shared schemas for the new AlgoLab pipeline."""

from algolab.schemas.correctness import (
    ContractReleaseGate,
    ContractTestCase,
    ContractValidationReport,
    CorrectnessContract,
    InputSchema,
    MetamorphicRelation,
    OracleStrategy,
    OutputSchema,
    Postcondition,
)
from algolab.schemas.input import ProblemInput
from algolab.schemas.render_report import BrowserSmokeResult, RenderReport
from algolab.schemas.semantic_trace import (
    Interaction,
    SemanticEvent,
    SemanticOp,
    SemanticTrace,
    SolutionVariant,
    TargetRef,
)
from algolab.schemas.scene_graph import (
    SceneFrame,
    SceneGraph,
    SceneObject,
    SceneObjectType,
    VisualMark,
)
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from algolab.schemas.visual_plan import (
    AnimationConfig,
    CameraConfig,
    LayoutPreferences,
    RenderTarget,
    TeachingConfig,
    VisualPlan,
)

__all__ = [
    "AnimationConfig",
    "BrowserSmokeResult",
    "BuildArtifact",
    "CameraConfig",
    "ContractReleaseGate",
    "ContractTestCase",
    "ContractValidationReport",
    "CorrectnessContract",
    "InputSchema",
    "Interaction",
    "LayoutPreferences",
    "MetamorphicRelation",
    "OracleStrategy",
    "OutputSchema",
    "Postcondition",
    "ProblemInput",
    "RenderTarget",
    "RenderReport",
    "ReleaseGate",
    "SceneFrame",
    "SceneGraph",
    "SceneObject",
    "SceneObjectType",
    "SemanticEvent",
    "SemanticOp",
    "SemanticTrace",
    "SolutionVariant",
    "TargetRef",
    "TeachingConfig",
    "ValidationReport",
    "VisualPlan",
    "VisualMark",
]
