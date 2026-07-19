"""Visual plan schemas."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


class RenderTarget(str, Enum):
    TEACHING_2D = "teaching_2d"
    SPATIAL_3D = "spatial_3d"
    HYBRID_2_5D = "hybrid_2_5d"
    CREATIVE = "creative"


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "fixed"
    default_view: str = "top_down"
    focus_policy: str = "current_target"
    allow_controls: bool = True

    @field_validator("type", "default_view", "focus_policy")
    @classmethod
    def text_is_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("camera text fields must be non-empty")
        return value


class AnimationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pace: Literal["slow", "medium", "fast"] = "medium"
    transition: Literal["step", "smooth"] = "step"
    emphasize: list[str] = Field(default_factory=list)

    @field_validator("emphasize")
    @classmethod
    def emphasis_items_are_non_empty(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("animation emphasis entries must be non-empty")
        return cleaned


class TeachingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["beginner", "interview", "code"] = "beginner"
    show_invariant: bool = True
    quiz_density: Literal["none", "low", "medium", "high"] = "low"


class LayoutPreferences(RootModel[dict[str, str]]):
    """Renderer layout preferences keyed by scene family."""

    @field_validator("root")
    @classmethod
    def preferences_are_valid(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, preference in value.items():
            clean_key = key.strip()
            clean_preference = preference.strip()
            if not clean_key:
                raise ValueError("layout preference keys must be non-empty")
            if not clean_preference:
                raise ValueError(f"layout preference {clean_key!r} must be non-empty")
            cleaned[clean_key] = clean_preference
        return cleaned


def _empty_layout_preferences() -> LayoutPreferences:
    return LayoutPreferences({})


class VisualPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["visual-plan-v1"] = "visual-plan-v1"
    mode: str = "teaching"
    stage: RenderTarget = RenderTarget.TEACHING_2D
    metaphor: str = ""
    camera: CameraConfig = Field(default_factory=CameraConfig)
    animation: AnimationConfig = Field(default_factory=AnimationConfig)
    teaching: TeachingConfig = Field(default_factory=TeachingConfig)
    layout_preferences: LayoutPreferences = Field(default_factory=_empty_layout_preferences)
    baseline_target: RenderTarget = RenderTarget.TEACHING_2D

    @field_validator("mode")
    @classmethod
    def mode_is_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("visual plan mode must be non-empty")
        return value
