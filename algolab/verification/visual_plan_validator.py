"""Validate VisualPlan against runtime capabilities."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from algolab.renderer.capabilities import runtime_capabilities
from algolab.schemas.visual_plan import RenderTarget, VisualPlan


def validate_visual_plan(
    plan_data: VisualPlan | dict[str, Any] | None,
    capabilities: dict[str, Any] | None = None,
) -> tuple[VisualPlan, dict[str, Any]]:
    caps = capabilities or runtime_capabilities()
    warnings: list[str] = []
    errors: list[str] = []
    fallback_reasons: list[str] = []

    try:
        plan = plan_data if isinstance(plan_data, VisualPlan) else VisualPlan.model_validate(plan_data or {})
    except ValidationError as exc:
        errors.append(f"visual plan schema 无效：{exc.errors()[0]['msg']}")
        fallback_reasons.append("invalid visual plan schema")
        plan = VisualPlan()

    render_targets = set(caps.get("render_targets") or [])
    supported_layouts = set(caps.get("supported_layouts") or [])
    target_status = caps.get("target_status") or {}

    if plan.stage.value not in render_targets:
        errors.append(f"unsupported render target: {plan.stage.value}")
        fallback_reasons.append(f"unsupported render target: {plan.stage.value}")
        plan.stage = RenderTarget.TEACHING_2D

    if plan.baseline_target.value not in render_targets:
        warnings.append(f"unsupported baseline target: {plan.baseline_target.value}; using teaching_2d")
        fallback_reasons.append(f"unsupported baseline target: {plan.baseline_target.value}")
        plan.baseline_target = RenderTarget.TEACHING_2D

    unsupported_layouts = sorted(set(plan.layout_preferences.root) - supported_layouts)
    if unsupported_layouts:
        warnings.append(f"unsupported layout preferences: {', '.join(unsupported_layouts)}")
        fallback_reasons.append(f"unsupported layouts: {', '.join(unsupported_layouts)}")
        plan.layout_preferences.root = {
            key: value for key, value in plan.layout_preferences.root.items() if key in supported_layouts
        }

    actual_target = plan.stage.value
    if target_status.get(actual_target) == "planned":
        fallback_reasons.append(f"{actual_target} runtime is planned")
        actual_target = plan.baseline_target.value

    report = {
        "schema_version": "visual-plan-validation-v1",
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "requested_target": plan.stage.value,
        "actual_target": actual_target,
        "baseline_target": plan.baseline_target.value,
        "used_baseline_renderer": actual_target != plan.stage.value,
        "fallback_reasons": fallback_reasons,
    }
    return plan, report
