from __future__ import annotations

from pathlib import Path


def test_stage2_visual_eval_extracts_final_gate_paths(tmp_path) -> None:
    from scripts.run_stage2_visual_eval import compact_record, host_path

    screenshot = tmp_path / "shot.png"
    html = tmp_path / "page.html"
    screenshot.write_bytes(b"png-bytes")
    html.write_text("<html></html>", encoding="utf-8")

    row = {
        "case_id": "demo_case",
        "problem_title": "Demo",
        "html_host_path": str(html),
        "creative_ok": True,
        "browser_smoke_ok": True,
        "strict_visual_quality_ok": True,
        "creative_quality_ok": True,
        "initial_creative_quality_ok": False,
        "stage2_selection": "retry",
        "creative_quality_reports": [
            {
                "gate": {
                    "score": 72,
                    "playwright": {
                        "screenshot": "/work/output/old.png",
                        "stage_audited_frame_count": 2,
                    },
                }
            },
            {
                "gate": {
                    "score": 100,
                    "playwright": {
                        "screenshot": str(screenshot),
                        "stage_audited_frame_count": 8,
                    },
                    "hard_failures": [],
                    "soft_failures": [],
                }
            },
        ],
    }

    record = compact_record(row)

    assert host_path("/work/output/demo.png").endswith("output/demo.png")
    assert record["case_id"] == "demo_case"
    assert record["stage2_selection"] == "retry"
    assert record["screenshot"] == str(screenshot)
    assert record["screenshot_exists"] is True
    assert record["html_exists"] is True
    assert record["final_gate_score"] == 100
    assert record["stage_audited_frame_count"] == 8


def test_stage2_machine_summary_counts_repairs() -> None:
    from scripts.run_stage2_visual_eval import compact_record, summarize_machine

    rows = [
        {
            "case_id": "a",
            "creative_ok": True,
            "browser_smoke_ok": True,
            "strict_visual_quality_ok": True,
            "creative_quality_ok": True,
            "initial_creative_quality_ok": False,
            "initial_stage_visual_quality_ok": False,
            "last_creative_quality_ok": True,
            "last_stage_visual_quality_ok": True,
            "creative_quality_score": 100,
            "initial_creative_quality_score": 80,
            "stage2_selection": "primary",
        },
        {
            "case_id": "b",
            "creative_ok": True,
            "browser_smoke_ok": True,
            "strict_visual_quality_ok": True,
            "creative_quality_ok": True,
            "initial_creative_quality_ok": True,
            "initial_stage_visual_quality_ok": True,
            "last_creative_quality_ok": True,
            "last_stage_visual_quality_ok": True,
            "creative_quality_score": 100,
            "initial_creative_quality_score": 100,
            "stage2_selection": "retry",
        },
    ]
    records = [compact_record(row) for row in rows]

    summary = summarize_machine(rows, records, {"summary": {"creative_quality_repair_attempts": 1}})

    assert summary["total"] == 2
    assert summary["bool_counts"]["creative_quality_ok"] == 2
    assert summary["selection_counts"] == {"primary": 1, "retry": 1}
    assert summary["repair_effect"]["repaired_from_initial_failure"] == 1
    assert summary["repair_effect"]["avg_score_delta"] == 10.0


def test_stage2_external_visual_summary_uses_four_main_scores() -> None:
    from scripts.run_stage2_visual_eval import STAGE2_EXTERNAL_SCORE_FIELDS, summarize_external_visual

    results = [
        {
            "ok": True,
            "case_id": "a",
            "scores": {
                "problem_visual_alignment": 5,
                "algorithm_state_readability": 4,
                "process_transition_clarity": 3,
                "instructional_visual_design": 4,
            },
            "model_calls": [{"usage_available": True, "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "duration_s": 2.0}],
        },
        {
            "ok": True,
            "case_id": "b",
            "scores": {
                "problem_visual_alignment": 2,
                "algorithm_state_readability": 5,
                "process_transition_clarity": 5,
                "instructional_visual_design": 3,
            },
            "model_calls": [{"usage_available": True, "prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25, "duration_s": 3.0}],
        },
    ]

    summary = summarize_external_visual(results, total_available=2)

    assert STAGE2_EXTERNAL_SCORE_FIELDS == (
        "problem_visual_alignment",
        "algorithm_state_readability",
        "process_transition_clarity",
        "instructional_visual_design",
    )
    assert summary["ok"] == 2
    assert summary["avg_scores"]["problem_visual_alignment"] == 3.5
    assert summary["avg_scores"]["algorithm_state_readability"] == 4.5
    assert summary["overall_avg_score"] == 3.875
    assert summary["dimension_pass_counts"]["problem_visual_alignment"] == 1
    assert summary["dimension_pass_counts"]["process_transition_clarity"] == 2
    assert summary["model_usage"]["total_tokens"] == 40


def test_stage2_external_visual_prompt_names_external_frameworks() -> None:
    from scripts.run_stage2_visual_eval import build_external_visual_prompt

    system, user = build_external_visual_prompt(
        {
            "case_id": "convex_hull",
            "problem_title": "凸包",
            "problem_description": "给定二维点集，返回凸包顶点。",
            "html": "/tmp/demo.html",
            "screenshot": "/tmp/demo.png",
        }
    )

    prompt = system + "\n" + user

    assert "Munzner" in prompt
    assert "LORI" in prompt
    assert "Mayer" in prompt
    assert "problem_visual_alignment" in prompt
    assert "algorithm_state_readability" in prompt
    assert "process_transition_clarity" in prompt
    assert "instructional_visual_design" in prompt
    assert "不要把抽象算法题强行按生活场景扣分" in prompt
