"""Regression tests for Creative Visual benchmark repair bookkeeping."""

from __future__ import annotations

import json

from scripts.run_creative_visual_benchmark import (
    best_creative_quality_gate,
    best_layout_audit,
    infer_stage1_model_from_report,
    load_problem_map,
    resolve_generation_model,
    summarize_creative_quality_status,
    summarize_layout_status,
)


def test_summarize_layout_status_uses_best_failed_audit_not_last_worse_repair():
    reports = [
        {
            "kind": "layout_audit",
            "attempt": 0,
            "audit": {
                "browser_smoke_ok": True,
                "stage_visual_quality_ok": False,
                "strict_visual_quality_ok": False,
                "stage_overlap_count": 0,
                "stage_permitted_overlap_count": 0,
                "stage_clipped_count": 0,
                "stage_text_occlusion_count": 2,
            },
        },
        {
            "kind": "layout_audit",
            "attempt": 1,
            "audit": {
                "browser_smoke_ok": True,
                "stage_visual_quality_ok": False,
                "strict_visual_quality_ok": False,
                "stage_overlap_count": 32,
                "stage_permitted_overlap_count": 0,
                "stage_clipped_count": 0,
                "stage_text_occlusion_count": 0,
            },
        },
    ]

    best = best_layout_audit(reports)
    status = summarize_layout_status(reports)

    assert best["stage_overlap_count"] == 0
    assert best["stage_text_occlusion_count"] == 2
    assert status["stage_overlap_count"] == 0
    assert status["stage_text_occlusion_count"] == 2
    assert status["last_stage_overlap_count"] == 32


def test_creative_problem_map_uses_full_benchmark_problem_descriptions():
    problem_map = load_problem_map(None)

    assert "农业温室" in problem_map["daily_temperatures"]
    assert "城市应急调度中心" in problem_map["dijkstra_shortest_path"]
    assert problem_map["daily_temperatures"] != "每日温度"


def test_creative_problem_map_does_not_downgrade_to_report_title(tmp_path):
    report = tmp_path / "llm_benchmark_report.json"
    report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "case_id": "daily_temperatures",
                        "title": "每日温度",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    problem_map = load_problem_map(report)

    assert "农业温室" in problem_map["daily_temperatures"]
    assert problem_map["daily_temperatures"] != "每日温度"


def test_creative_benchmark_infers_stage1_model_from_report_result(tmp_path):
    report = tmp_path / "llm_benchmark_report.json"
    report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "case_id": "dijkstra_shortest_path",
                        "model": "DeepSeek-V4-Pro",
                        "model_calls": [
                            {"kind": "generation", "model": "DeepSeek-V4-Pro"},
                            {"kind": "teaching", "model": "DeepSeek-V4-Pro"},
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert infer_stage1_model_from_report(report) == "DeepSeek-V4-Pro"


def test_creative_benchmark_resolves_model_from_artifact_dir_stage1_report(tmp_path):
    report = tmp_path / "llm_benchmark_report.json"
    report.write_text(
        json.dumps({"results": [{"case_id": "two_sum", "model": "DeepSeek-V4-Pro"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert (
        resolve_generation_model(
            explicit_model=None,
            artifact_dir=tmp_path,
            problem_report=None,
        )
        == "DeepSeek-V4-Pro"
    )


def test_creative_benchmark_explicit_model_overrides_stage1_report(tmp_path):
    report = tmp_path / "llm_benchmark_report.json"
    report.write_text(
        json.dumps({"results": [{"case_id": "two_sum", "model": "DeepSeek-V4-Pro"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert (
        resolve_generation_model(
            explicit_model="gpt-5.4",
            artifact_dir=tmp_path,
            problem_report=None,
        )
        == "gpt-5.4"
    )


def test_summarize_creative_quality_status_uses_best_gate_not_last_worse_repair():
    reports = [
        {
            "kind": "creative_quality_gate",
            "attempt": 0,
            "gate": {
                "creative_quality_ok": False,
                "score": 72,
                "soft_failures": ["scenario_salience_low"],
                "hard_failures": [],
                "vlm": {"scenario_salience_score": 2, "algorithm_readability_score": 4},
            },
        },
        {
            "kind": "creative_quality_gate",
            "attempt": 1,
            "gate": {
                "creative_quality_ok": False,
                "score": 61,
                "soft_failures": ["generic_algorithm_visual"],
                "hard_failures": [],
                "vlm": {"scenario_salience_score": 3, "algorithm_readability_score": 3},
            },
        },
    ]

    best = best_creative_quality_gate(reports)
    status = summarize_creative_quality_status(reports)

    assert best["score"] == 72
    assert status["creative_quality_score"] == 72
    assert status["creative_quality_ok"] is False
    assert status["last_creative_quality_score"] == 61


def run_all() -> None:
    test_summarize_layout_status_uses_best_failed_audit_not_last_worse_repair()
    print("creative_visual_benchmark: PASS")


if __name__ == "__main__":
    run_all()
