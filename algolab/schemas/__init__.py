"""Shared schemas for the new AlgoLab pipeline."""

from algolab.schemas.input import ProblemInput
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

__all__ = [
    "BuildArtifact",
    "Interaction",
    "ProblemInput",
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
    "ValidationReport",
    "VisualMark",
]
