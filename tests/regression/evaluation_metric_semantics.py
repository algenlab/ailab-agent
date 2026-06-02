"""Regression tests for R8 evaluation metric semantics."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.build_evaluation_manifest import build_manifest
from scripts.build_evaluation_report import build_evaluation_report
from scripts.merge_llm_reports import build_report as build_merged_llm_report
from scripts.merge_llm_reports import write_report as write_merged_llm_report
from scripts.merge_vlm_condition_reports import build_report as build_vlm_condition_report
from scripts.merge_vlm_condition_reports import write_report as write_vlm_condition_report


def _write_llm_report(path: Path, *, condition: str, model: str, passed: int, failed: int) -> None:
    results = []
    for index in range(passed):
        results.append(
            {
                "case_id": f"{condition}_pass_{index}",
                "condition": condition,
                "case_set": "deterministic",
                "ok": True,
                "model_calls": [{"kind": "generation", "model": model, "usage_available": False}],
            }
        )
    for index in range(failed):
        results.append(
            {
                "case_id": f"{condition}_fail_{index}",
                "condition": condition,
                "case_set": "deterministic",
                "ok": False,
                "failure_type": "html_error" if condition == "direct_html_baseline" else "process_invariant",
                "error": "failed",
                "model_calls": [{"kind": "generation", "model": model, "usage_available": False}],
            }
        )
    total = passed + failed
    path.write_text(
        json.dumps(
            {
                "kind": "llm_benchmark_report",
                "config": {
                    "benchmark_condition": condition,
                    "model": model,
                    "llm": {"model": model, "base_url": "https://example.invalid/v1"},
                    "direct_html_baseline": condition == "direct_html_baseline",
                },
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / total if total else 0.0,
                "results": results,
                "browser_smoke": [{"ok": True, "condition": condition} for _ in range(passed)],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_vlm_report(path: Path, *, condition: str, overall: int) -> None:
    result = {
        "ok": True,
        "condition": condition,
        "case_id": f"{condition}_case",
        "viewport": "desktop",
        "screenshot_type": "page",
        "screenshot": f"{condition}.png",
        "scores": {
            "layout_readability": overall,
            "algorithm_state_visibility": overall,
            "teaching_explanation": overall,
            "interaction_affordance": overall,
            "evidence_alignment": overall,
            "overall_teaching_quality": overall,
        },
        "confidence": 0.9,
        "issues": [],
        "model_calls": [{"kind": "vlm_eval", "model": "fake-vlm", "usage_available": False}],
    }
    path.write_text(
        json.dumps(
            {
                "schema_version": "vlm-screenshot-scores-v1",
                "condition": condition,
                "summary": {"condition": condition, "total": 1},
                "results": [result],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_r8_evaluation_keeps_direct_html_out_of_strict_correctness_gate():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        algolab = root / "algolab.json"
        direct = root / "direct.json"
        _write_llm_report(algolab, condition="algolab_full", model="algolab-model", passed=1, failed=1)
        _write_llm_report(direct, condition="direct_html_baseline", model="direct-model", passed=2, failed=0)

        merged = build_merged_llm_report([("algolab_full", algolab), ("direct_html_baseline", direct)])
        merged_path = write_merged_llm_report(merged, root / "merged")

        assert {item["model"] for item in merged["config"]["source_reports"]} == {"algolab-model", "direct-model"}
        assert sorted(merged["config"]["models"]) == ["algolab-model", "direct-model"]

        manifest = root / "evaluation_manifest.json"
        manifest.write_text(json.dumps(build_manifest(), ensure_ascii=False), encoding="utf-8")
        evaluation_path = build_evaluation_report(output_dir=root / "evaluation", manifest_path=manifest, llm_report_path=merged_path)
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))

        metrics = {item["name"]: item for item in evaluation["metrics"]}
        assert metrics["algolab_full_strict_release_gate_pass_rate"]["numerator"] == 1
        assert metrics["algolab_full_strict_release_gate_pass_rate"]["denominator"] == 2
        assert metrics["correctness_gate_pass_rate"]["numerator"] == 1
        assert metrics["correctness_gate_pass_rate"]["denominator"] == 2
        assert "direct_html_baseline" in metrics["correctness_gate_pass_rate"]["note"]
        conditions = {item["condition"]: item for item in evaluation["condition_summary"]}
        assert conditions["algolab_full"]["machine_correctness_gate_available"] is True
        assert conditions["direct_html_baseline"]["machine_correctness_gate_available"] is False
        assert evaluation["model_config"]["models"] == ["algolab-model", "direct-model"]
        assert {item["condition"] for item in evaluation["model_config"]["source_reports"]} == {
            "algolab_full",
            "direct_html_baseline",
        }


def test_r8_vlm_quality_fields_are_named_as_successful_screenshot_scores():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        vlm_a = root / "vlm_algolab.json"
        vlm_b = root / "vlm_direct.json"
        _write_vlm_report(vlm_a, condition="algolab_full", overall=4)
        _write_vlm_report(vlm_b, condition="direct_html_baseline", overall=5)
        merged_vlm = build_vlm_condition_report([vlm_a, vlm_b])
        merged_vlm_path = write_vlm_condition_report(merged_vlm, root / "vlm")

        manifest = root / "evaluation_manifest.json"
        manifest.write_text(json.dumps(build_manifest(), ensure_ascii=False), encoding="utf-8")
        evaluation_path = build_evaluation_report(
            output_dir=root / "evaluation",
            manifest_path=manifest,
            vlm_report_path=merged_vlm_path,
        )
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))

        assert "vlm_quality_on_successful_screenshots" in evaluation["vlm_summary"]
        assert {
            row["condition"]: row["avg_overall_teaching_quality_on_successful_screenshots"]
            for row in evaluation["vlm_summary"]["vlm_quality_on_successful_screenshots"]
        } == {"algolab_full": 4.0, "direct_html_baseline": 5.0}
        csv_text = (root / "evaluation" / "evaluation_vlm_condition_summary.csv").read_text(encoding="utf-8")
        assert "avg_overall_teaching_quality_on_successful_screenshots" in csv_text
        md = (root / "evaluation" / "evaluation_report.md").read_text(encoding="utf-8")
        assert "successful screenshots" in md


def run_all() -> None:
    test_r8_evaluation_keeps_direct_html_out_of_strict_correctness_gate()
    test_r8_vlm_quality_fields_are_named_as_successful_screenshot_scores()


if __name__ == "__main__":
    run_all()
    print("evaluation_metric_semantics: PASS")
