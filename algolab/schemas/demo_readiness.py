"""Demo readiness schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DemoReadinessStatus = Literal["pass", "warn", "fail"]


class DemoReadinessVariantReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str = ""
    status: DemoReadinessStatus = "pass"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    phase_coverage: dict[str, bool] = Field(default_factory=dict)


class DemoReadinessReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: DemoReadinessStatus = "pass"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    variants: list[DemoReadinessVariantReport] = Field(default_factory=list)
