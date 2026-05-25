"""Renderer-facing scene graph schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SceneObjectType(str, Enum):
    PANEL = "panel"
    CONTAINER = "container"
    CELL = "cell"
    NODE = "node"
    EDGE = "edge"
    ARROW = "arrow"
    POINTER = "pointer"
    LABEL = "label"
    HIGHLIGHT = "highlight"
    CALLOUT = "callout"
    CODE_LINE = "code_line"
    TENSOR = "tensor"
    BATCH = "batch"
    PARAMETER = "parameter"
    LOSS_CURVE = "loss_curve"
    GRADIENT_VECTOR = "gradient_vector"
    DECISION_BOUNDARY = "decision_boundary"
    TRAINING_EPOCH = "training_epoch"
    PREDICTION = "prediction"


class SceneObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: SceneObjectType
    value: Any = None
    label: str = ""
    parent: str = ""
    row: int | None = None
    col: int | None = None
    index: int | None = None
    source: str = ""
    target: str = ""
    role: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class VisualMark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    role: str = "current"
    label: str = ""


class SceneFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int
    title: str
    description: str
    operation: str
    code_line: int = 1
    objects: list[SceneObject] = Field(default_factory=list)
    marks: list[VisualMark] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    interaction: dict[str, Any] | None = None
    teaching: dict[str, Any] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class SceneGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "scene-graph-v1"
    algorithm: str
    input_data: Any
    result: Any = None
    pseudocode: list[str] = Field(default_factory=list)
    frames: list[SceneFrame]
