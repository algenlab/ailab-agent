"""Regression tests for Creative Visual benchmark repair bookkeeping."""

from __future__ import annotations

from scripts.run_creative_visual_benchmark import best_layout_audit, summarize_layout_status


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


def run_all() -> None:
    test_summarize_layout_status_uses_best_failed_audit_not_last_worse_repair()
    print("creative_visual_benchmark: PASS")


if __name__ == "__main__":
    run_all()
