from __future__ import annotations

import ast

from scripts.run_wrong_self_consistent_solver_audit import (
    _is_applicable,
    audit_case,
    build_report,
    evaluate_mutant,
    generate_mutation_candidates,
    wilson_interval,
)


SOURCE = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    value = sess.scalar("value", input_data["value"])
    answer = 0
    if int(value) < 3:
        answer += 1
    sess.result(answer)
    return sess.to_trace()
'''


def test_mutation_candidates_are_deterministic_parseable_and_cover_all_kinds() -> None:
    first = generate_mutation_candidates(SOURCE)
    second = generate_mutation_candidates(SOURCE)

    assert first == second
    assert len({row["mutation_id"] for row in first}) == len(first)
    assert {row["mutation_kind"] for row in first} >= {
        "comparison_boundary",
        "omitted_update",
        "wrong_return",
    }
    for row in first:
        ast.parse(row["source"])


def test_wrong_return_is_internally_consistent_but_rejected_by_oracle_gate() -> None:
    mutant = next(
        row
        for row in generate_mutation_candidates(SOURCE)
        if row["mutation_kind"] == "wrong_return"
    )

    result = evaluate_mutant(
        mutant["source"],
        input_data={"value": 1},
        expected=1,
        case_id="demo",
        family_id="demo-family",
        subfamily_id="demo-subfamily",
    )

    assert result["executed_normally"] is True
    assert result["same_execution_binding"] is True
    assert result["prefix_replay_ok"] is True
    assert result["final_replay_ok"] is True
    assert result["deterministic_replay_ok"] is True
    assert result["oracle_mismatch"] is True
    assert result["release_rejected"] is True
    assert result["oracle_gate_detected"] is True
    assert result["release_evaluation"] == "pipeline_materialize"
    assert any("expected" in error for error in result["release_errors"])


def test_audit_case_keeps_attempts_and_selects_exactly_two_applicable_mutants() -> None:
    report = audit_case(
        case_id="demo",
        family_id="demo-family",
        subfamily_id="demo-subfamily",
        source=SOURCE,
        input_data={"value": 1},
        expected=1,
        target_applicable=2,
    )

    assert report["applicable_count"] == 2
    assert len(report["selected_mutation_ids"]) == 2
    assert report["attempted_count"] >= 2
    assert report["attempted_count"] == len(report["attempts"])
    assert all("applicable" in row for row in report["attempts"])
    assert all(row["release_rejected"] for row in report["attempts"] if row["applicable"])


def test_wilson_interval_contains_observed_rate() -> None:
    low, high = wilson_interval(9, 10)

    assert 0.0 <= low <= 0.9 <= high <= 1.0


def test_nonterminating_mutant_is_recorded_as_not_executed_after_a_short_timeout() -> None:
    source = '''def trace(input_data):
    sess = TraceSession("demo", input_data)
    while True:
        pass
'''

    result = evaluate_mutant(
        source,
        input_data={},
        expected=1,
        timeout_s=1,
    )

    assert result["executed_normally"] is False
    assert "超过 1 秒" in result["error"]


def test_applicable_filter_does_not_preselect_internal_consistency() -> None:
    row = {
        "executed_normally": True,
        "oracle_mismatch": True,
        "same_execution_binding": False,
        "prefix_replay_ok": False,
        "final_replay_ok": False,
        "deterministic_replay_ok": False,
    }

    assert _is_applicable(row) is True


def test_screening_counts_include_candidates_that_failed_before_mutation_audit() -> None:
    selected_case = {
        "case_id": "selected",
        "family_id": "family",
        "baseline_ok": True,
        "attempts": [],
    }
    report = build_report(
        [selected_case],
        [
            {"case_id": "selected", "accepted": True},
            {"case_id": "load-error", "accepted": False},
            {"case_id": "audit-reject", "accepted": False},
        ],
        [
            selected_case,
            {
                "case_id": "audit-reject",
                "family_id": "family",
                "baseline_ok": False,
                "attempts": [],
            },
        ],
    )

    assert report["screened_task_count"] == 3
    assert report["mutation_audited_task_count"] == 2
    assert report["rejected_task_count"] == 2
