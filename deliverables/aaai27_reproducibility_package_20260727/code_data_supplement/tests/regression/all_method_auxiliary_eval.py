from __future__ import annotations

import json
import base64
import os
import subprocess
import sys
from pathlib import Path


def test_web_source_feature_flags_detect_supported_engagement_levels() -> None:
    from scripts.run_all_method_auxiliary_eval import feature_flags_from_text

    flags = feature_flags_from_text(
        """
        export default function App() {
          return <main>
            <input aria-label="custom input" />
            <button>修改输入并重新运行</button>
            <p>构建自己的可视化，并向同学展示。</p>
          </main>;
        }
        """
    )

    assert flags == {
        "input_change_supported": True,
        "construction_supported": True,
        "presentation_supported": True,
    }


def test_cli_help_runs_without_external_pythonpath() -> None:
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "scripts/run_all_method_auxiliary_eval.py", "--help"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "--run-multimodal" in result.stdout


def test_multimodal_prompt_is_blind_to_method_identity_and_uses_machine_evidence() -> None:
    from scripts.run_all_method_auxiliary_eval import build_multimodal_prompt

    system, user = build_multimodal_prompt(
        {
            "condition": "secret_method_name",
            "case_id": "binary_search",
            "problem_title": "二分查找",
            "problem_description": "在有序数组中查找目标值。",
            "learning_objectives": ["理解区间收缩"],
            "page_load_ok": True,
            "visible_answer_match": True,
            "interaction_reachable": False,
            "correct_feedback_ok": False,
            "wrong_feedback_ok": False,
            "hint_ok": True,
            "show_answer_ok": True,
            "learning_log_ok": False,
            "mutation_free_ok": True,
        }
    )
    payload = json.loads(user)

    assert "secret_method_name" not in system
    assert "secret_method_name" not in user
    assert payload["case"]["case_id"] == "binary_search"
    assert payload["machine_evidence"]["interaction_reachable"] is False
    assert payload["machine_evidence"]["hint_ok"] is True


def test_normalize_multimodal_payload_clamps_all_teaching_and_visual_scores() -> None:
    from scripts.run_all_method_auxiliary_eval import (
        ALL_SCORE_FIELDS,
        normalize_multimodal_payload,
    )

    raw_scores = {field: 3 for field in ALL_SCORE_FIELDS}
    raw_scores[ALL_SCORE_FIELDS[0]] = 9
    raw_scores[ALL_SCORE_FIELDS[-1]] = 0

    normalized = normalize_multimodal_payload(
        {
            "scores": raw_scores,
            "strengths": ["结构清楚"],
            "weaknesses": ["反馈不足"],
            "recommendation": "加强过程标注",
            "confidence": 1.4,
        }
    )

    assert normalized["scores"][ALL_SCORE_FIELDS[0]] == 5
    assert normalized["scores"][ALL_SCORE_FIELDS[-1]] == 1
    assert normalized["confidence"] == 1.0
    assert normalized["teaching_overall_score"] == 3.286
    assert normalized["visual_overall_score"] == 2.5


def test_summarize_condition_combines_naps_trakla_and_multimodal_scores() -> None:
    from scripts.run_all_method_auxiliary_eval import summarize_condition

    records = [
        {
            "case_id": "a",
            "naps_engagement": {"level": "responding", "score": 2},
            "trakla2_style": {"score": 7, "core_pass": True},
        },
        {
            "case_id": "b",
            "naps_engagement": {"level": "viewing", "score": 1},
            "trakla2_style": {"score": 5, "core_pass": False},
        },
    ]
    reviews = [
        {
            "case_id": "a",
            "ok": True,
            "scores": {
                "content_quality": 5,
                "learning_goal_alignment": 4,
                "feedback_adaptation": 4,
                "interaction_usability": 4,
                "presentation_design": 5,
                "teaching_effectiveness": 4,
                "ease_of_use": 4,
                "problem_visual_alignment": 5,
                "algorithm_state_readability": 4,
                "process_transition_clarity": 4,
                "instructional_visual_design": 5,
            },
            "teaching_overall_score": 4.286,
            "visual_overall_score": 4.5,
        },
        {"case_id": "b", "ok": False, "error": "missing screenshot"},
    ]

    summary = summarize_condition(records, reviews)

    assert summary["total"] == 2
    assert summary["avg_naps_score"] == 1.5
    assert summary["trakla2_core_pass"] == 1
    assert summary["avg_trakla2_score"] == 6.0
    assert summary["multimodal_valid"] == 1
    assert summary["avg_teaching_overall"] == 4.286
    assert summary["avg_visual_overall"] == 4.5
    assert summary["visual_all_dimensions_pass"] == 1


def test_frozen_full200_inputs_cover_the_same_cases_for_all_five_methods(tmp_path: Path) -> None:
    from scripts.run_all_method_auxiliary_eval import METHOD_ORDER, build_method_records

    root = Path(__file__).resolve().parents[2]
    grouped = build_method_records(root=root, output_dir=tmp_path)

    assert list(grouped) == list(METHOD_ORDER)
    assert all(len(rows) == 200 for rows in grouped.values())
    case_sets = [{row["case_id"] for row in rows} for rows in grouped.values()]
    assert all(case_set == case_sets[0] for case_set in case_sets[1:])
    assert all(row["problem_description"] for rows in grouped.values() for row in rows)
    assert sum(Path(row["screenshot"]).exists() for row in grouped["webgen_agent"]) == 199
    assert sum(Path(row["screenshot"]).exists() for row in grouped["htmlcure_strict"]) == 0
    assert sum(Path(row["screenshot"]).exists() for row in grouped["browser_repair_1call"]) == 200


def test_enrich_machine_metrics_reads_web_source_and_computes_naps_and_trakla(tmp_path: Path) -> None:
    from scripts.run_all_method_auxiliary_eval import enrich_machine_metrics

    source_dir = tmp_path / "webgen_case"
    (source_dir / "src").mkdir(parents=True)
    (source_dir / "src/App.jsx").write_text(
        '<input aria-label="custom input"/><button>修改输入并重新运行</button>',
        encoding="utf-8",
    )
    record = {
        "condition": "webgen_agent",
        "case_id": "case",
        "source_dir": str(source_dir),
        "html": str(source_dir / "index.html"),
        "page_load_ok": True,
        "visible_answer_match": True,
        "interaction_reachable": True,
        "correct_feedback_ok": True,
        "wrong_feedback_ok": True,
        "hint_ok": True,
        "show_answer_ok": True,
        "learning_log_ok": True,
        "mutation_free_ok": True,
    }

    enriched = enrich_machine_metrics(record)

    assert enriched["feature_flags"]["input_change_supported"] is True
    assert enriched["naps_engagement"]["level"] == "changing"
    assert enriched["naps_engagement"]["score"] == 3
    assert enriched["trakla2_style"]["core_pass"] is True
    assert enriched["trakla2_style"]["score"] == 7


def test_missing_screenshot_plan_only_contains_htmlcure_and_one_webgen_case(tmp_path: Path) -> None:
    from scripts.run_all_method_auxiliary_eval import build_method_records, missing_screenshot_counts

    root = Path(__file__).resolve().parents[2]
    grouped = build_method_records(root=root, output_dir=tmp_path)

    assert missing_screenshot_counts(grouped) == {
        "algotutorgen_stage2": 0,
        "direct_html": 0,
        "webgen_agent": 1,
        "htmlcure_strict": 200,
        "browser_repair_1call": 0,
    }


def test_static_html_capture_produces_a_nonempty_full_page_screenshot(tmp_path: Path) -> None:
    from scripts.run_all_method_auxiliary_eval import capture_static_html_screenshots

    html = tmp_path / "page.html"
    screenshot = tmp_path / "page.png"
    html.write_text(
        "<html><body><h1>算法教学页面</h1><p>状态变化清楚可见。</p></body></html>",
        encoding="utf-8",
    )

    results = capture_static_html_screenshots(
        [{"case_id": "case", "html": str(html), "screenshot": str(screenshot)}],
        wait_ms=0,
    )

    assert results == [{"case_id": "case", "ok": True, "error": ""}]
    assert screenshot.exists()
    assert screenshot.stat().st_size > 0


def test_multimodal_evaluator_parses_and_records_a_valid_model_response(tmp_path: Path) -> None:
    from scripts.run_all_method_auxiliary_eval import ALL_SCORE_FIELDS, evaluate_multimodal_record

    screenshot = tmp_path / "one.png"
    screenshot.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nWQAAAAASUVORK5CYII="
        )
    )
    calls = []

    def fake_chat(system: str, user: str, image_b64: str, model: str | None) -> dict:
        calls.append((system, user, image_b64, model))
        return {
            "content": json.dumps(
                {
                    "scores": {field: 4 for field in ALL_SCORE_FIELDS},
                    "strengths": ["清晰"],
                    "weaknesses": [],
                    "recommendation": "保持",
                    "confidence": 0.8,
                },
                ensure_ascii=False,
            ),
            "model_call": {"kind": "all_method_auxiliary_vlm", "usage_available": True, "total_tokens": 123},
        }

    result = evaluate_multimodal_record(
        {
            "condition": "direct_html",
            "case_id": "case",
            "problem_title": "Case",
            "problem_description": "Problem",
            "learning_objectives": [],
            "screenshot": str(screenshot),
            "page_load_ok": True,
        },
        model="gemini-test",
        retries=0,
        chat_fn=fake_chat,
    )

    assert result["ok"] is True
    assert result["teaching_overall_score"] == 4.0
    assert result["visual_overall_score"] == 4.0
    assert result["model_calls"][0]["total_tokens"] == 123
    assert len(calls) == 1
    assert calls[0][3] == "gemini-test"


def test_machine_render_failure_gets_a_deterministic_minimum_score_without_api_call(
    tmp_path: Path,
) -> None:
    from scripts.run_all_method_auxiliary_eval import ALL_SCORE_FIELDS, evaluate_multimodal_record

    calls = []

    def fake_chat(system: str, user: str, image_b64: str, model: str | None) -> dict:
        calls.append((system, user, image_b64, model))
        raise AssertionError("render-failure floor must not call the VLM")

    result = evaluate_multimodal_record(
        {
            "condition": "webgen_agent",
            "case_id": "tarjan_scc",
            "problem_title": "Tarjan 强连通分量",
            "problem_description": "求图中的强连通分量。",
            "learning_objectives": [],
            "screenshot": str(tmp_path / "missing.png"),
            "page_load_ok": False,
        },
        model="gemini-test",
        retries=0,
        chat_fn=fake_chat,
    )

    assert result["ok"] is True
    assert result["scoring_mode"] == "deterministic_render_failure_floor"
    assert result["failure_type"] == "machine_render_failure"
    assert result["scores"] == {field: 1 for field in ALL_SCORE_FIELDS}
    assert result["teaching_overall_score"] == 1.0
    assert result["visual_overall_score"] == 1.0
    assert result["model_calls"] == []
    assert calls == []


def test_summarize_condition_separates_model_reviews_from_failure_floor_scores() -> None:
    from scripts.run_all_method_auxiliary_eval import ALL_SCORE_FIELDS, summarize_condition

    records = [
        {
            "case_id": "model_scored",
            "naps_engagement": {"level": "viewing", "score": 1},
            "trakla2_style": {"score": 6, "core_pass": False},
        },
        {
            "case_id": "render_failed",
            "naps_engagement": {"level": "no_viewing", "score": 0},
            "trakla2_style": {"score": 0, "core_pass": False},
        },
    ]
    reviews = [
        {
            "case_id": "model_scored",
            "ok": True,
            "scores": {field: 4 for field in ALL_SCORE_FIELDS},
            "teaching_overall_score": 4.0,
            "visual_overall_score": 4.0,
        },
        {
            "case_id": "render_failed",
            "ok": True,
            "scoring_mode": "deterministic_render_failure_floor",
            "scores": {field: 1 for field in ALL_SCORE_FIELDS},
            "teaching_overall_score": 1.0,
            "visual_overall_score": 1.0,
        },
    ]

    summary = summarize_condition(records, reviews)

    assert summary["multimodal_valid"] == 2
    assert summary["multimodal_model_scored"] == 1
    assert summary["deterministic_render_failure_floor"] == 1
    assert summary["avg_teaching_overall"] == 2.5
    assert summary["avg_visual_overall"] == 2.5


def test_multimodal_runner_resumes_from_per_case_cache(tmp_path: Path) -> None:
    from scripts.run_all_method_auxiliary_eval import ALL_SCORE_FIELDS, run_multimodal_reviews

    calls = []

    def fake_evaluator(record: dict, *, model: str | None, retries: int) -> dict:
        calls.append(record["case_id"])
        return {
            "ok": True,
            "scores": {field: 4 for field in ALL_SCORE_FIELDS},
            "teaching_overall_score": 4.0,
            "visual_overall_score": 4.0,
            "model_calls": [],
        }

    records = [
        {"condition": "direct_html", "case_id": "a"},
        {"condition": "direct_html", "case_id": "b"},
    ]
    first = run_multimodal_reviews(
        records,
        output_dir=tmp_path,
        model="gemini-test",
        retries=0,
        concurrency=2,
        force=False,
        evaluator=fake_evaluator,
    )
    second = run_multimodal_reviews(
        records,
        output_dir=tmp_path,
        model="gemini-test",
        retries=0,
        concurrency=2,
        force=False,
        evaluator=fake_evaluator,
    )

    assert sorted(calls) == ["a", "b"]
    assert [row["case_id"] for row in first] == ["a", "b"]
    assert second == first


def test_webgen_capture_reuses_an_existing_screenshot_without_starting_a_server(tmp_path: Path) -> None:
    from scripts.run_all_method_auxiliary_eval import capture_webgen_workspace_screenshot

    screenshot = tmp_path / "existing.png"
    screenshot.write_bytes(b"png")

    result = capture_webgen_workspace_screenshot(
        {
            "case_id": "case",
            "source_dir": str(tmp_path / "missing-workspace"),
            "screenshot": str(screenshot),
        }
    )

    assert result == {"case_id": "case", "ok": True, "error": "", "cached": True}


def test_build_report_keeps_method_summaries_and_model_usage() -> None:
    from scripts.run_all_method_auxiliary_eval import ALL_SCORE_FIELDS, build_report

    record = {
        "condition": "direct_html",
        "case_id": "a",
        "naps_engagement": {"level": "viewing", "score": 1},
        "trakla2_style": {"score": 6, "core_pass": False},
    }
    review = {
        "condition": "direct_html",
        "case_id": "a",
        "ok": True,
        "scores": {field: 4 for field in ALL_SCORE_FIELDS},
        "teaching_overall_score": 4.0,
        "visual_overall_score": 4.0,
        "model_calls": [
            {
                "usage_available": True,
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "duration_s": 1.5,
            }
        ],
    }

    report = build_report(
        {"direct_html": [record]},
        [review],
        model="gemini-test",
    )

    assert report["methods"]["direct_html"]["summary"]["avg_naps_score"] == 1.0
    assert report["methods"]["direct_html"]["summary"]["avg_visual_overall"] == 4.0
    assert report["model_usage"]["call_count"] == 1
    assert report["model_usage"]["total_tokens"] == 120


def test_markdown_report_discloses_model_scores_and_deterministic_failure_floors(
    tmp_path: Path,
) -> None:
    from scripts.run_all_method_auxiliary_eval import ALL_SCORE_FIELDS, build_report, write_report

    records = [
        {
            "condition": "webgen_agent",
            "case_id": "ok",
            "naps_engagement": {"level": "viewing", "score": 1},
            "trakla2_style": {"score": 6, "core_pass": False},
        },
        {
            "condition": "webgen_agent",
            "case_id": "failed",
            "naps_engagement": {"level": "no_viewing", "score": 0},
            "trakla2_style": {"score": 0, "core_pass": False},
        },
    ]
    reviews = [
        {
            "condition": "webgen_agent",
            "case_id": "ok",
            "ok": True,
            "scores": {field: 4 for field in ALL_SCORE_FIELDS},
            "teaching_overall_score": 4.0,
            "visual_overall_score": 4.0,
            "model_calls": [],
        },
        {
            "condition": "webgen_agent",
            "case_id": "failed",
            "ok": True,
            "scoring_mode": "deterministic_render_failure_floor",
            "scores": {field: 1 for field in ALL_SCORE_FIELDS},
            "teaching_overall_score": 1.0,
            "visual_overall_score": 1.0,
            "model_calls": [],
        },
    ]

    write_report(build_report({"webgen_agent": records}, reviews, model="gemini-test"), tmp_path)
    markdown = (tmp_path / "all_method_auxiliary_eval_report.md").read_text(encoding="utf-8")

    assert "| Method | Valid | Model-scored | Failure floor | Teaching overall" in markdown
    assert "| WebGen-Agent | 2/2 | 1 | 1 | 2.500 |" in markdown
