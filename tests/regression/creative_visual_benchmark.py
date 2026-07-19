"""Regression tests for the creative visual benchmark runner."""

from __future__ import annotations

from algolab.generation.direct_visual_renderer import DirectVisualRenderResult
from scripts import audit_creative_visual_renderer as audit
from scripts import run_creative_visual_benchmark as benchmark


def test_generate_with_timeout_retries_retries_api_502_errors(monkeypatch):
    calls: list[object] = []

    def fake_generate_with_process_timeout(artifact, **kwargs):
        calls.append(artifact)
        if len(calls) < 3:
            return DirectVisualRenderResult(
                creative_ok=False,
                errors=["InternalServerError: Error code: 502 - upstream service error"],
            )
        return DirectVisualRenderResult(creative_ok=True, html="<html></html>")

    monkeypatch.setattr(benchmark, "generate_with_process_timeout", fake_generate_with_process_timeout)
    monkeypatch.setenv("ALGOLAB_LLM_API_RETRIES", "2")
    monkeypatch.setenv("ALGOLAB_LLM_API_RETRY_DELAY_S", "0")

    result, attempts = benchmark.generate_with_timeout_retries(
        object(),
        problem_description="demo",
        model=None,
        timeout_s=30,
        mode="stage_shell",
        timeout_retries=0,
    )

    assert result.creative_ok is True
    assert len(calls) == 3
    assert [item["attempt"] for item in attempts] == [1, 2, 3]


def test_stage_quality_audit_allows_current_outline_and_svg_hit_test_roots():
    js = audit.STAGE_QUALITY_AUDIT_JS

    assert "current-outline" in js
    assert "tag === 'svg'" in js


def test_stage_quality_audit_treats_svg_shape_labels_as_visual_containers():
    js = audit.STAGE_QUALITY_AUDIT_JS

    assert "svgShapeTag" in js
    assert "pointer-chip" in js
