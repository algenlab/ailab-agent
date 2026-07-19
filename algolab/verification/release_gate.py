"""Compute release readiness."""

from __future__ import annotations

from algolab.schemas.validation import ReleaseGate


def compute_release_gate(
    *,
    variant_count: int,
    scene_count: int,
    errors: list[str],
    verifier_available: bool,
    expected_available: bool,
) -> ReleaseGate:
    blocking: list[str] = []
    artifact_ready = variant_count > 0 and scene_count == variant_count
    trace_ready = variant_count > 0
    process_ready = variant_count > 0 and (verifier_available or expected_available or variant_count > 1)
    visual_ready = scene_count == variant_count and scene_count > 0
    multi_solution_ready = variant_count > 1

    if errors:
        blocking.append("存在校验错误")
    if not artifact_ready:
        blocking.append("没有可发布的产物")
    if not process_ready:
        blocking.append("缺少独立 verifier、expected 或多解法交叉校验")
    if not visual_ready:
        blocking.append("缺少可渲染 scene graph")

    release_ready = artifact_ready and process_ready and trace_ready and visual_ready and not errors
    return ReleaseGate(
        artifact_ready=artifact_ready,
        process_ready=process_ready,
        trace_ready=trace_ready,
        visual_ready=visual_ready,
        multi_solution_ready=multi_solution_ready,
        release_ready=release_ready,
        blocking_reasons=blocking,
    )
