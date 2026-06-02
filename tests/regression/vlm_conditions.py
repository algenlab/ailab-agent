"""Regression tests for VLM condition comparison helpers."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.build_evaluation_manifest import build_manifest as build_evaluation_manifest
from scripts.build_evaluation_report import build_evaluation_report
from scripts.capture_report_html_screenshots import build_manifest, collect_html_records
from scripts.merge_llm_reports import build_report as build_merged_llm_report
from scripts.merge_llm_reports import write_report as write_merged_llm_report
from scripts.merge_vlm_condition_reports import build_report as build_vlm_condition_report
from scripts.merge_vlm_condition_reports import write_report as write_vlm_condition_report


def _llm_report(path: Path, html_path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "total": 2,
                "passed": 1,
                "failed": 1,
                "results": [
                    {
                        "ok": True,
                        "case_id": "case_a",
                        "condition": "algolab_full",
                        "html": str(html_path),
                        "title": "Case A",
                        "case_set": "deterministic",
                        "family": "array",
                        "sample_index": 0,
                    },
                    {
                        "ok": False,
                        "case_id": "case_b",
                        "condition": "algolab_full",
                        "html": "",
                        "failure_type": "generation",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _vlm_result(condition: str, ok: bool = True) -> dict:
    return {
        "ok": ok,
        "failure_type": "" if ok else "vlm_eval_error",
        "case_id": "case_a",
        "condition": condition,
        "screenshot": f"{condition}_case_a.png",
        "viewport": "desktop",
        "kind": "page",
        "screenshot_type": "page",
        "html": "case_a.html",
        "phase": "",
        "scores": {
            "layout_readability": 5,
            "algorithm_state_visibility": 4,
            "teaching_explanation": 4,
            "interaction_affordance": 4,
            "evidence_alignment": 4,
            "overall_teaching_quality": 4,
        }
        if ok
        else None,
        "confidence": 0.8 if ok else 0.0,
        "issues": [],
        "suggested_caption": "Clear teaching state.",
        "judge_model": "fake-vlm",
        "model_call": {
            "kind": "vlm_eval",
            "model": "fake-vlm",
            "duration_s": 1.0,
            "usage_available": True,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
        "model_calls": [
            {
                "kind": "vlm_eval",
                "model": "fake-vlm",
                "duration_s": 1.0,
                "usage_available": True,
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
        ],
    }


def _vlm_report(path: Path, condition: str, ok: bool = True) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "vlm-screenshot-scores-v1",
                "condition": condition,
                "summary": {"condition": condition, "total": 1},
                "results": [_vlm_result(condition, ok=ok)],
            }
        ),
        encoding="utf-8",
    )


def test_collect_html_records_uses_condition_override_and_skips_failed_results():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        html = root / "case_a.html"
        html.write_text("<html><body>ok</body></html>", encoding="utf-8")
        report = root / "llm_benchmark_report.json"
        _llm_report(report, html)

        records = collect_html_records([("unseen_algolab_full", report)])
        manifest = build_manifest(
            report_specs=[("unseen_algolab_full", report)],
            viewports=["desktop"],
            records=[{**records[0], "viewport": "desktop", "screenshot": str(root / "case_a.png"), "ok": True}],
            output_dir=root,
        )

    assert len(records) == 1
    assert records[0]["condition"] == "unseen_algolab_full"
    assert records[0]["source_condition"] == "algolab_full"
    assert manifest["condition_counts"] == {"unseen_algolab_full": 1}
    assert manifest["ok"] is True


def test_merge_vlm_condition_reports_writes_required_artifacts():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        report_a = root / "deterministic.json"
        report_b = root / "algolab_full.json"
        _vlm_report(report_a, "deterministic", ok=True)
        _vlm_report(report_b, "algolab_full", ok=False)

        merged = build_vlm_condition_report([report_a, report_b])
        out = root / "out"
        path = write_vlm_condition_report(merged, out)

        assert path.name == "vlm_condition_scores.json"
        assert (out / "vlm_condition_scores.csv").exists()
        assert (out / "vlm_condition_summary.csv").exists()
        assert merged["conditions"] == ["algolab_full", "deterministic"]
        assert merged["summary"]["total"] == 2
        condition_rows = {row["condition"]: row for row in merged["summary"]["conditions"]}
        assert condition_rows["deterministic"]["passed"] == 1
        assert condition_rows["algolab_full"]["failed"] == 1


def test_merge_llm_reports_overrides_conditions_and_evaluation_exports_vlm_csvs():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        html = root / "case_a.html"
        html.write_text("<html><body>ok</body></html>", encoding="utf-8")
        llm_a = root / "llm_a.json"
        llm_b = root / "llm_b.json"
        _llm_report(llm_a, html)
        _llm_report(llm_b, html)

        merged_llm = build_merged_llm_report([("algolab_full", llm_a), ("unseen_algolab_full", llm_b)])
        merged_llm_path = write_merged_llm_report(merged_llm, root)
        assert merged_llm["total"] == 4
        assert {item["condition"] for item in merged_llm["results"]} == {"algolab_full", "unseen_algolab_full"}
        assert merged_llm["results"][2]["source_condition"] == "algolab_full"

        vlm_a = root / "vlm_a.json"
        vlm_b = root / "vlm_b.json"
        _vlm_report(vlm_a, "deterministic", ok=True)
        _vlm_report(vlm_b, "algolab_full", ok=True)
        merged_vlm = build_vlm_condition_report([vlm_a, vlm_b])
        merged_vlm_path = write_vlm_condition_report(merged_vlm, root / "vlm")

        manifest_path = root / "evaluation_manifest.json"
        manifest_path.write_text(json.dumps(build_evaluation_manifest(), ensure_ascii=False), encoding="utf-8")
        evaluation_path = build_evaluation_report(
            output_dir=root / "evaluation",
            manifest_path=manifest_path,
            llm_report_path=merged_llm_path,
            vlm_report_path=merged_vlm_path,
        )
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))

        assert evaluation["inputs"]["vlm_report"] == str(merged_vlm_path)
        assert evaluation["vlm_summary"]["status"] == "ok"
        assert {row["condition"] for row in evaluation["vlm_summary"]["conditions"]} == {"deterministic", "algolab_full"}
        assert (root / "evaluation" / "evaluation_vlm_scores.csv").exists()
        assert (root / "evaluation" / "evaluation_vlm_condition_summary.csv").exists()
        assert "VLM Condition Summary" in (root / "evaluation" / "evaluation_report.md").read_text(encoding="utf-8")


def run_all() -> None:
    test_collect_html_records_uses_condition_override_and_skips_failed_results()
    test_merge_vlm_condition_reports_writes_required_artifacts()
    test_merge_llm_reports_overrides_conditions_and_evaluation_exports_vlm_csvs()


if __name__ == "__main__":
    run_all()
    print("vlm_conditions: PASS")
