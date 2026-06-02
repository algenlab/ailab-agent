"""Regression tests for paper artifact generation helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path

from scripts.build_paper_artifacts import (
    failure_case_markdown,
    lowest_vlm_screenshot,
    table1_deterministic_gate_summary,
    table4_unseen_family_summary,
    table6_ablation_comparison,
    write_readme,
)


def test_paper_artifact_tables_and_failure_notes_are_reproducible():
    dashboard = {"passed": 2, "total": 2}
    family_gate = {
        "summary": {
            "sample_count": 4,
            "answer_passed_samples": 4,
            "answer_pass_rate": 1.0,
            "process_passed_samples": 3,
            "process_pass_rate": 0.75,
            "demo_ready_cases": 2,
            "demo_required_cases": 2,
            "demo_readiness_pass_rate": 1.0,
        }
    }
    table1 = table1_deterministic_gate_summary(dashboard, family_gate)
    assert table1[0]["metric"] == "dashboard_generation"
    assert table1[2]["rate"] == 0.75

    merged_llm = {
        "results": [
            {
                "condition": "unseen_algolab_full",
                "case_id": "unseen_a",
                "family": "array",
                "ok": True,
            },
            {
                "condition": "unseen_algolab_full",
                "case_id": "unseen_b",
                "family": "array",
                "ok": False,
                "failure_type": "process_invariant",
                "errors": ["bad process"],
                "sample_index": 0,
                "expected": 1,
            },
        ]
    }
    unseen = table4_unseen_family_summary(merged_llm)
    assert unseen[0]["family"] == "array"
    assert unseen[0]["pass_rate"] == 0.5
    assert "process_invariant" in unseen[0]["failure_types"]

    ablation = table6_ablation_comparison(
        [
            {"condition": "algolab_full", "kind": "full", "total": "2", "passed": "1", "failed": "1", "pass_rate": "0.5"},
            {"condition": "no_repair", "kind": "ablation", "total": "2", "passed": "0", "failed": "2", "pass_rate": "0.0"},
        ]
    )
    assert ablation[1]["delta_vs_algolab_full"] == -0.5

    vlm = {
        "results": [
            {
                "condition": "unseen_algolab_full",
                "case_id": "unseen_b",
                "screenshot": "",
                "issues": [{"message": "state is unclear"}],
            }
        ]
    }
    notes = failure_case_markdown(merged_llm, vlm, None)
    assert "unseen_b" in notes
    assert "state is unclear" in notes


def test_paper_artifact_lowest_vlm_screenshot_and_readme():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        high = root / "high.png"
        low = root / "low.png"
        high.write_bytes(b"png-high")
        low.write_bytes(b"png-low")
        report = {
            "results": [
                {"condition": "a", "case_id": "a", "screenshot": str(high), "scores": {"overall_teaching_quality": 5}},
                {"condition": "b", "case_id": "b", "screenshot": str(low), "scores": {"overall_teaching_quality": 1}},
            ]
        }
        assert lowest_vlm_screenshot(report) == low
        write_readme(root)
        assert (root / "README.md").exists()


def run_all() -> None:
    test_paper_artifact_tables_and_failure_notes_are_reproducible()
    test_paper_artifact_lowest_vlm_screenshot_and_readme()


if __name__ == "__main__":
    run_all()
    print("paper_artifacts: PASS")
