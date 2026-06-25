"""Regression tests for the Stage2 Creative Quality gate."""

from __future__ import annotations

from scripts.creative_quality_gate import (
    build_creative_quality_report,
    creative_quality_score,
    is_better_creative_quality_report,
    normalize_creative_vlm_payload,
)


def _passing_playwright_row() -> dict:
    return {
        "case_id": "daily_temperatures",
        "creative_ok": True,
        "browser_smoke_ok": True,
        "page_load_ok": True,
        "console_error_count": 0,
        "page_error_count": 0,
        "visual_non_empty": True,
        "frame_switch_ok": True,
        "trace_mutation_detected": False,
        "main_area_not_blank": True,
        "screenshot_non_empty": True,
        "stage_visual_quality_ok": True,
        "strict_visual_quality_ok": True,
        "stage_overlap_count": 0,
        "stage_clipped_count": 0,
        "stage_text_occlusion_count": 0,
        "failure_categories": [],
        "screenshot": "/tmp/daily_temperatures.png",
    }


def _passing_vlm_payload() -> dict:
    return {
        "scenario_salience_score": 5,
        "algorithm_readability_score": 4,
        "is_generic_algorithm_visual": False,
        "scenario_objects_visible": ["温室", "通风策略", "遮阳"],
        "algorithm_state_visible": True,
        "issues": [],
        "repair_advice": "",
        "confidence": 0.86,
    }


def test_creative_quality_report_passes_when_browser_and_vlm_pass():
    report = build_creative_quality_report(
        playwright_row=_passing_playwright_row(),
        problem_description="农业温室每日温度调控",
        vlm_result={"ok": True, **_passing_vlm_payload()},
        require_vlm=True,
    )

    assert report["creative_quality_ok"] is True
    assert report["hard_failures"] == []
    assert report["soft_failures"] == []
    assert report["vlm"]["scenario_salience_score"] == 5
    assert report["score"] >= 90


def test_creative_quality_report_fails_runtime_error_even_if_vlm_passes():
    row = _passing_playwright_row()
    row["browser_smoke_ok"] = False
    row["creative_ok"] = False
    row["console_error_count"] = 1
    row["failure_categories"] = ["console_errors"]

    report = build_creative_quality_report(
        playwright_row=row,
        problem_description="农业温室每日温度调控",
        vlm_result={"ok": True, **_passing_vlm_payload()},
        require_vlm=True,
    )

    assert report["creative_quality_ok"] is False
    assert "console_errors" in report["hard_failures"]
    assert "console_errors" in report["repair_brief"]


def test_creative_quality_report_fails_low_vlm_scenario_score():
    vlm = _passing_vlm_payload()
    vlm["scenario_salience_score"] = 2
    vlm["issues"] = ["主视图仍像普通数组图，没有温室设施"]

    report = build_creative_quality_report(
        playwright_row=_passing_playwright_row(),
        problem_description="农业温室每日温度调控",
        vlm_result={"ok": True, **vlm},
        require_vlm=True,
    )

    assert report["creative_quality_ok"] is False
    assert "scenario_salience_low" in report["soft_failures"]
    assert "主视图仍像普通数组图" in report["repair_brief"]


def test_creative_quality_report_fails_generic_algorithm_visual():
    vlm = _passing_vlm_payload()
    vlm["is_generic_algorithm_visual"] = True

    report = build_creative_quality_report(
        playwright_row=_passing_playwright_row(),
        problem_description="农业温室每日温度调控",
        vlm_result={"ok": True, **vlm},
        require_vlm=True,
    )

    assert report["creative_quality_ok"] is False
    assert "generic_algorithm_visual" in report["soft_failures"]


def test_creative_quality_score_prefers_scenario_pass_over_layout_only_candidate():
    low_vlm = _passing_vlm_payload()
    low_vlm["scenario_salience_score"] = 2
    weak = build_creative_quality_report(
        playwright_row=_passing_playwright_row(),
        problem_description="农业温室每日温度调控",
        vlm_result={"ok": True, **low_vlm},
        require_vlm=True,
    )
    strong = build_creative_quality_report(
        playwright_row=_passing_playwright_row(),
        problem_description="农业温室每日温度调控",
        vlm_result={"ok": True, **_passing_vlm_payload()},
        require_vlm=True,
    )

    assert creative_quality_score(strong) > creative_quality_score(weak)
    assert is_better_creative_quality_report(strong, weak)


def test_normalize_creative_vlm_payload_accepts_compact_json_shape():
    normalized = normalize_creative_vlm_payload(_passing_vlm_payload(), model="gemini-3-flash-preview")

    assert normalized["ok"] is True
    assert normalized["scenario_salience_score"] == 5
    assert normalized["algorithm_readability_score"] == 4
    assert normalized["judge_model"] == "gemini-3-flash-preview"
