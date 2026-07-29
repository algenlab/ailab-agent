from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.analyze_total_token_cost_reliability import (
    analyze_reports,
    build_direct_ledger,
    extract_algotutorgen_costs,
    replay_under_token_cap,
    summarize_fixed_repair_budgets,
)


ROOT = Path(__file__).resolve().parents[2]
DIRECT_REPORT = (
    ROOT
    / "output/experiments/direct_browser_repair_fair_20260723/fair_repair_report.json"
)
ALGOTUTORGEN_REPORT = (
    ROOT
    / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
)
MACHINE_REPORT = (
    ROOT
    / "output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine_rendered_text"
    / "interaction_semantic_eval_report.json"
)


def test_analysis_script_supports_direct_cli_execution() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/analyze_total_token_cost_reliability.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--direct-report" in result.stdout


def _attempt(call_index: int, tokens: int, machine_ok: bool) -> dict:
    return {
        "call_index": call_index,
        "audit": {"machine_ok": machine_ok},
        "model_call": {
            "usage_available": True,
            "prompt_tokens": tokens // 2,
            "completion_tokens": tokens - tokens // 2,
            "total_tokens": tokens,
            "duration_s": float(call_index),
        },
    }


def _direct_report(*results: dict) -> dict:
    return {"results": list(results)}


def test_token_cap_includes_initial_call_but_never_partially_includes_a_repair() -> None:
    report = _direct_report(
        {
            "case_id": "case-a",
            "attempts": [
                _attempt(1, 30, False),
                _attempt(2, 25, False),
                _attempt(3, 10, True),
            ],
        }
    )
    case = build_direct_ledger(report, expected_cases=1)[0]

    below_initial = replay_under_token_cap(case, token_cap=0)
    cannot_split_second_call = replay_under_token_cap(case, token_cap=50)

    assert below_initial["total_tokens"] == 30
    assert below_initial["included_calls"] == 1
    assert cannot_split_second_call["total_tokens"] == 30
    assert cannot_split_second_call["included_calls"] == 1
    assert cannot_split_second_call["machine_ok"] is False


def test_token_cap_keeps_best_so_far_after_a_later_page_regresses() -> None:
    report = _direct_report(
        {
            "case_id": "case-a",
            "attempts": [
                _attempt(1, 20, False),
                _attempt(2, 20, True),
                _attempt(3, 20, False),
            ],
        }
    )
    case = build_direct_ledger(report, expected_cases=1)[0]

    replay = replay_under_token_cap(case, token_cap=100)

    assert replay["included_calls"] == 3
    assert replay["machine_ok"] is True
    assert replay["first_machine_ok_call"] == 2


def test_missing_or_inconsistent_api_usage_fails_closed() -> None:
    missing = _direct_report(
        {
            "case_id": "case-a",
            "attempts": [
                {
                    "call_index": 1,
                    "audit": {"machine_ok": False},
                    "model_call": {"usage_available": False},
                }
            ],
        }
    )
    inconsistent = _direct_report(
        {
            "case_id": "case-a",
            "attempts": [
                {
                    "call_index": 1,
                    "audit": {"machine_ok": False},
                    "model_call": {
                        "usage_available": True,
                        "prompt_tokens": 4,
                        "completion_tokens": 5,
                        "total_tokens": 10,
                    },
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="usage unavailable"):
        build_direct_ledger(missing, expected_cases=1)
    with pytest.raises(ValueError, match="token total mismatch"):
        build_direct_ledger(inconsistent, expected_cases=1)


def test_frozen_direct_report_recovers_budget_curve_and_token_totals() -> None:
    report = json.loads(DIRECT_REPORT.read_text(encoding="utf-8"))
    ledger = build_direct_ledger(report, expected_cases=200)

    curve = summarize_fixed_repair_budgets(ledger, budgets=[0, 1, 2, 3, 5])

    assert [row["machine_ok"] for row in curve] == [106, 118, 119, 120, 120]
    assert [row["total_tokens"] for row in curve] == [
        3_935_488,
        7_216_568,
        10_211_319,
        13_265_476,
        19_582_977,
    ]
    assert sum(case["initial_tokens"] for case in ledger) == 3_935_488
    assert sum(case["total_tokens"] - case["initial_tokens"] for case in ledger) == 15_647_489


def test_frozen_algotutorgen_costs_include_selected_and_all_attempt_usage() -> None:
    report = json.loads(ALGOTUTORGEN_REPORT.read_text(encoding="utf-8"))

    costs = extract_algotutorgen_costs(report, expected_cases=200)

    assert costs["selected_final"]["total_tokens"] == 15_369_433
    assert costs["selected_final"]["tokens_per_task"] == pytest.approx(76_847.165)
    assert costs["all_attempts"]["total_tokens"] == 16_870_557
    assert costs["all_attempts"]["tokens_per_task"] == pytest.approx(84_352.785)


def test_full_analysis_requires_exact_case_alignment_and_uses_algo_minus_direct_direction() -> None:
    direct = json.loads(DIRECT_REPORT.read_text(encoding="utf-8"))
    algotutor = json.loads(ALGOTUTORGEN_REPORT.read_text(encoding="utf-8"))
    machine = json.loads(MACHINE_REPORT.read_text(encoding="utf-8"))

    payload = analyze_reports(
        direct_report=direct,
        algotutorgen_report=algotutor,
        machine_report=machine,
        token_caps=[84_352.785],
        expected_cases=200,
    )
    comparison = payload["comparisons"]["all_attempts_cost_matched"]

    assert payload["case_alignment"]["paired_cases"] == 200
    assert payload["algotutorgen"]["machine_ok"] == 198
    assert comparison["direction"] == "AlgoTutorGen - Direct"
    assert comparison["paired_statistics"]["a_pass"] == 198
    assert comparison["paired_statistics"]["b_pass"] == 120
    assert comparison["paired_statistics"]["difference"] == pytest.approx(0.39)

    broken_machine = dict(machine)
    broken_machine["records"] = [
        row
        for row in machine["records"]
        if not (row.get("condition") == "algolab_full" and row.get("case_id") == "binary_search")
    ]
    with pytest.raises(ValueError, match="unmatched case IDs"):
        analyze_reports(
            direct_report=direct,
            algotutorgen_report=algotutor,
            machine_report=broken_machine,
            token_caps=[84_352.785],
            expected_cases=200,
        )
