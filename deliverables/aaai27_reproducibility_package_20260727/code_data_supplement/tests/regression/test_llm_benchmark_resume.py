from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from llm_client import _model_name, llm_config
from algolab.generation.execution_modes import execution_mode_metadata
from algolab.generation.prompt_profiles import prompt_profile_metadata
from scripts.run_llm_benchmark import load_resume_state


def _args(*, mode: str = "atomic") -> SimpleNamespace:
    return SimpleNamespace(
        resume=True,
        case=[],
        sample=0,
        all_samples=False,
        solutions=2,
        max_rounds=2,
        max_candidates=2,
        timeout_s=3000,
        strict_warnings=True,
        browser_smoke=False,
        teaching_enrichment=True,
        case_set="deterministic",
        language="zh",
        prompt_profile="hybrid_current",
        execution_mode=mode,
        condition=f"{mode}_service",
        concurrency=16,
    )


def _config(args: SimpleNamespace, *, concurrency: int = 8) -> dict:
    return {
        "cases": args.case,
        "sample": args.sample,
        "all_samples": args.all_samples,
        "solutions": args.solutions,
        "max_rounds": args.max_rounds,
        "max_candidates": args.max_candidates,
        "timeout_s": args.timeout_s,
        "strict_warnings": args.strict_warnings,
        "browser_smoke": args.browser_smoke,
        "teaching_enrichment": args.teaching_enrichment,
        "case_set": args.case_set,
        "language": args.language,
        "prompt_profile": args.prompt_profile,
        "prompt_profile_metadata": prompt_profile_metadata(args.prompt_profile),
        "execution_mode": args.execution_mode,
        "execution_mode_metadata": execution_mode_metadata(
            args.execution_mode, args.prompt_profile
        ),
        "benchmark_condition": args.condition,
        "model": _model_name(),
        "llm": llm_config(),
        "concurrency": concurrency,
    }


def test_resume_skips_completed_cases_and_allows_only_concurrency_change(tmp_path) -> None:
    args = _args()
    report_path = tmp_path / "llm_benchmark_report.json"
    report_path.write_text(
        json.dumps(
            {
                "kind": "llm_benchmark_report",
                "started_at": "2026-07-25T10:00:00",
                "config": _config(args, concurrency=8),
                "results": [{"case_id": "a", "sample_index": 0, "ok": True}],
            }
        ),
        encoding="utf-8",
    )
    tasks = [
        (SimpleNamespace(id="a"), 0, object()),
        (SimpleNamespace(id="b"), 0, object()),
    ]

    results, remaining, started_at, history = load_resume_state(
        report_path, tasks, args
    )

    assert [row["case_id"] for row in results] == ["a"]
    assert [(case.id, sample_index) for case, sample_index, _ in remaining] == [
        ("b", 0)
    ]
    assert started_at == "2026-07-25T10:00:00"
    assert history == [8, 16]


def test_resume_rejects_configuration_drift_and_unknown_completed_cases(tmp_path) -> None:
    args = _args()
    report_path = tmp_path / "llm_benchmark_report.json"
    config = _config(args)
    config["max_rounds"] = 1
    report_path.write_text(
        json.dumps(
            {
                "kind": "llm_benchmark_report",
                "config": config,
                "results": [{"case_id": "a", "sample_index": 0, "ok": True}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="resume configuration mismatch.*max_rounds"):
        load_resume_state(
            report_path, [(SimpleNamespace(id="a"), 0, object())], args
        )

    config["max_rounds"] = 2
    report_path.write_text(
        json.dumps(
            {
                "kind": "llm_benchmark_report",
                "config": config,
                "results": [{"case_id": "unknown", "sample_index": 0}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="outside the selected task set"):
        load_resume_state(
            report_path, [(SimpleNamespace(id="a"), 0, object())], args
        )
