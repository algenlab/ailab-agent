from __future__ import annotations

from scripts.run_direct_browser_repair_fair import (
    DEFAULT_API_TIMEOUT_S,
    DEFAULT_BROWSER_TIMEOUT_MS,
    DEFAULT_CONCURRENCY,
    DEFAULT_REPAIR_BUDGETS,
    DEFAULT_REPAIR_MAX_TOKENS,
    MACHINE_BOOL_KEYS,
    build_fair_repair_prompt,
    choose_best_attempt,
    machine_transition,
    run_repair_policy,
)


def _audit(score: int, *, machine_ok: bool = False) -> dict:
    values = {key: index < score for index, key in enumerate(MACHINE_BOOL_KEYS)}
    values["machine_ok"] = machine_ok
    return values


def test_default_protocol_uses_high_limits_and_32_way_concurrency() -> None:
    assert DEFAULT_CONCURRENCY == 32
    assert DEFAULT_REPAIR_BUDGETS == (0, 1, 2, 3, 5)
    assert DEFAULT_REPAIR_MAX_TOKENS == 32768
    assert DEFAULT_API_TIMEOUT_S >= 1800
    assert DEFAULT_BROWSER_TIMEOUT_MS >= 60000


def test_repair_prompt_contains_the_complete_previous_html_and_redacts_hidden_metrics() -> None:
    previous_html = "<html><head>BEGIN_SENTINEL</head><body>" + ("x" * 25000) + "END_SENTINEL</body></html>"
    prompt = build_fair_repair_prompt(
        title="Demo",
        problem="Sort values",
        family="sorting",
        strategy="insertion sort",
        input_data=[3, 1, 2],
        expected=[1, 2, 3],
        previous_html=previous_html,
        feedback={
            "page_load_ok": True,
            "machine_ok": False,
            "correct_feedback_ok": False,
            "dom_summary": {"body_text_excerpt": "ok"},
        },
        repair_round=1,
        language="en",
    )

    assert "BEGIN_SENTINEL" in prompt
    assert "END_SENTINEL" in prompt
    assert previous_html in prompt
    assert "machine_ok" not in prompt
    assert "correct_feedback_ok" not in prompt


def test_choose_best_attempt_prefers_more_machine_dimensions_then_earlier_attempt() -> None:
    attempts = [
        {"call_index": 1, "audit": _audit(6)},
        {"call_index": 2, "audit": _audit(8)},
        {"call_index": 3, "audit": _audit(8)},
    ]

    assert choose_best_attempt(attempts)["call_index"] == 2


def test_machine_transition_records_fail_to_pass_and_pass_to_fail_per_dimension() -> None:
    before = _audit(4)
    after = dict(before)
    after[MACHINE_BOOL_KEYS[4]] = True
    after[MACHINE_BOOL_KEYS[1]] = False

    transition = machine_transition(before, after)

    assert transition["overall"] == "fail_to_fail"
    assert transition["fail_to_pass"] == [MACHINE_BOOL_KEYS[4]]
    assert transition["pass_to_fail"] == [MACHINE_BOOL_KEYS[1]]


def test_policy_early_stops_and_never_calls_repair_after_machine_ok() -> None:
    repair_calls: list[int] = []
    audits = iter([_audit(7), _audit(9, machine_ok=True)])

    result = run_repair_policy(
        initial_attempt={"call_index": 1, "html": "initial.html", "model_call": {}},
        repair_budget=5,
        audit_attempt=lambda attempt: next(audits),
        collect_feedback=lambda attempt: {"page_load_ok": True},
        repair_attempt=lambda previous, feedback, repair_round: (
            repair_calls.append(repair_round)
            or {"call_index": repair_round + 1, "html": f"repair-{repair_round}.html", "model_call": {}}
        ),
    )

    assert repair_calls == [1]
    assert result["repair_calls_used"] == 1
    assert result["stop_reason"] == "machine_ok"
    assert result["best_attempt"]["call_index"] == 2
    assert len(result["transitions"]) == 1
    assert result["transitions"][0]["overall"] == "fail_to_pass"


def test_policy_keeps_best_so_far_when_later_rewrite_regresses() -> None:
    audits = iter([_audit(6), _audit(8), _audit(5)])

    result = run_repair_policy(
        initial_attempt={"call_index": 1, "html": "initial.html", "model_call": {}},
        repair_budget=2,
        audit_attempt=lambda attempt: next(audits),
        collect_feedback=lambda attempt: {"page_load_ok": True},
        repair_attempt=lambda previous, feedback, repair_round: {
            "call_index": repair_round + 1,
            "html": f"repair-{repair_round}.html",
            "model_call": {},
        },
    )

    assert result["stop_reason"] == "repair_budget_exhausted"
    assert result["repair_calls_used"] == 2
    assert result["best_attempt"]["call_index"] == 2
    assert result["final_attempt"]["call_index"] == 3
    assert result["transitions"][1]["pass_to_fail"]
