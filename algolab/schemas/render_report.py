"""Renderer target selection report schema."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from algolab.schemas.visual_plan import RenderTarget


class BrowserSmokeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checked: bool = False
    passed: bool | None = None
    reason: str = ""


class RenderReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["render-report-v1"] = "render-report-v1"
    requested_target: RenderTarget = RenderTarget.TEACHING_2D
    actual_target: RenderTarget = RenderTarget.TEACHING_2D
    baseline_target: RenderTarget = RenderTarget.TEACHING_2D
    used_baseline_renderer: bool = False
    fallback_reasons: list[str] = Field(default_factory=list)
    browser_smoke: BrowserSmokeResult = Field(default_factory=BrowserSmokeResult)
    visual_plan_validation: dict[str, Any] = Field(default_factory=dict)
    release_ready: bool = False
