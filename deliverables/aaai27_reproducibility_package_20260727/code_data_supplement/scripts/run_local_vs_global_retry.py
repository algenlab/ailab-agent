"""Compare spec-local repair with full-spec global restart under equal decision budgets."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
from collections import Counter, defaultdict, deque
from datetime import datetime
from math import comb
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.solution_generator import generate_solution_spec, repair_solution_spec
from algolab.pipeline import _try_materialize
from algolab.renderer.export import save_html
from algolab.verification.repair_context import repair_failure_types
from llm_client import _model_name, clear_model_calls, consume_model_calls, llm_config
from scripts.run_llm_benchmark import (
    _release_blocking_errors,
    make_request,
    selected_cases,
    summarize_model_usage,
)


PolicyCallable = Callable[..., Any]


def execute_retry_policy(
    *,
    strategy: str,
    max_llm_calls: int,
    generate: Callable[[], Any],
    repair: Callable[[Any, list[str]], Any],
    materialize: Callable[[Any], tuple[Any, list[str]]],
    is_valid: Callable[[Any, list[str]], bool],
    consume_calls: Callable[[], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    if strategy not in {"local_resume", "global_restart"}:
        raise ValueError(f"unknown strategy: {strategy}")
    if max_llm_calls < 1:
        raise ValueError("max_llm_calls must be positive")

    spec: Any = None
    last_errors: list[str] = []
    attempts: list[dict[str, Any]] = []
    generate_calls = 0
    repair_calls = 0
    materialize_attempts = 0
    selected_artifact: Any = None

    for decision_index in range(max_llm_calls):
        decision = "generate" if spec is None or strategy == "global_restart" else "repair"
        started = time.perf_counter()
        try:
            if decision == "generate":
                spec = generate()
                generate_calls += 1
            else:
                spec = repair(spec, last_errors)
                repair_calls += 1
        except Exception as exc:
            last_errors = [f"{type(exc).__name__}: {exc}"]
            calls = consume_calls() if consume_calls is not None else []
            attempts.append(
                {
                    "decision_index": decision_index,
                    "decision": decision,
                    "materialized": False,
                    "valid": False,
                    "errors": last_errors,
                    "duration_s": round(time.perf_counter() - started, 3),
                    "model_calls": calls,
                }
            )
            if decision == "generate":
                spec = None
            continue

        artifact = None
        errors: list[str] = []
        try:
            artifact, errors = materialize(spec)
            materialize_attempts += 1
        except Exception as exc:
            errors = [f"{type(exc).__name__}: {exc}"]
        valid = is_valid(artifact, errors)
        last_errors = errors
        calls = consume_calls() if consume_calls is not None else []
        attempts.append(
            {
                "decision_index": decision_index,
                "decision": decision,
                "materialized": artifact is not None,
                "valid": valid,
                "errors": errors,
                "duration_s": round(time.perf_counter() - started, 3),
                "model_calls": calls,
            }
        )
        if valid:
            selected_artifact = artifact
            break
        if strategy == "global_restart":
            spec = None

    model_calls = [call for attempt in attempts for call in attempt.get("model_calls") or []]
    return {
        "ok": selected_artifact is not None,
        "strategy": strategy,
        "llm_calls": generate_calls + repair_calls,
        "policy_decision_calls": generate_calls + repair_calls,
        "actual_model_calls": len(model_calls),
        "generate_calls": generate_calls,
        "repair_calls": repair_calls,
        "materialize_attempts": materialize_attempts,
        "last_errors": last_errors,
        "attempts": attempts,
        "model_calls": model_calls,
        "artifact": selected_artifact,
    }


def _stratified_cases(count: int, requested: set[str]) -> list[Any]:
    cases = list(selected_cases(requested or None))
    if count <= 0 or count >= len(cases):
        return cases
    grouped: dict[str, deque[Any]] = defaultdict(deque)
    for case in sorted(cases, key=lambda item: (item.family_id, item.subfamily_id, item.id)):
        grouped[case.family_id].append(case)
    selected: list[Any] = []
    family_ids = sorted(grouped)
    while len(selected) < count and any(grouped.values()):
        for family_id in family_ids:
            if grouped[family_id]:
                selected.append(grouped[family_id].popleft())
            if len(selected) >= count:
                break
    return selected


def _sample_zero(case: Any) -> Any:
    if not case.samples:
        raise ValueError(f"case {case.id} has no samples")
    return case.samples[0]


def _run_one(case: Any, strategy: str, args: argparse.Namespace) -> dict[str, Any]:
    sample = _sample_zero(case)
    request = make_request(
        case,
        sample,
        solutions=args.solutions,
        teaching_enrichment=not args.disable_teaching,
    )
    started = time.perf_counter()
    clear_model_calls()

    def materialize(spec: dict[str, Any]) -> tuple[Any, list[str]]:
        artifact, errors = _try_materialize(request, spec)
        blocking = _release_blocking_errors(artifact, errors or [], strict_warnings=args.strict_warnings)
        return artifact, blocking

    policy = execute_retry_policy(
        strategy=strategy,
        max_llm_calls=args.max_policy_calls,
        generate=lambda: generate_solution_spec(request),
        repair=lambda spec, errors: repair_solution_spec(request, spec, errors),
        materialize=materialize,
        is_valid=lambda artifact, errors: artifact is not None and not errors,
        consume_calls=consume_model_calls,
    )
    artifact = policy.pop("artifact")
    output_html = args.output_dir / "artifacts" / strategy / f"llm_{case.id}_0.html"
    if artifact is not None:
        save_html(artifact, output_html)
    result = {
        "case_id": case.id,
        "title": case.title,
        "family": case.family,
        "family_id": case.family_id,
        "subfamily_id": case.subfamily_id,
        "sample_index": 0,
        "input_data": sample.input_data,
        "expected": sample.expected,
        "model": _model_name(),
        "duration_s": round(time.perf_counter() - started, 3),
        "html": str(output_html) if artifact is not None else "",
        "json": str(output_html.with_suffix(".json")) if artifact is not None else "",
        **policy,
    }
    result_path = args.output_dir / "results" / strategy / f"{case.id}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _call_tokens(calls: list[dict[str, Any]]) -> int | None:
    if not calls or any(call.get("usage_available") is not True for call in calls):
        return None
    return sum(int(call.get("total_tokens") or 0) for call in calls)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def failure_stage_for_message(message: str) -> str:
    """Map validator-emitted errors to the contract boundary that rejected them."""
    text = (message or "").lower()
    if "teaching_contract" in text:
        return "teaching"
    if "solve 代码为空" in message:
        return "solver"
    if "没有可发布的产物" in message:
        return "release_gate"
    if "独立 verifier" in text or "多解法交叉校验" in message:
        return "oracle_consistency"
    if "scenegraph" in text or "scene graph" in text or "scene contract" in text or "帧对象" in message:
        return "scene_graph"
    if "solve 结果" in message and "trace 结果" in message:
        return "solver_trace_consistency"
    if "result mismatch" in text or ("结果" in message and "expected" in text):
        return "oracle_consistency"
    if any(
        marker in text
        for marker in (
            "trace",
            "dsl",
            "process_invariant",
            "process invariant",
            "coverage_error",
            "trace_schema",
        )
    ) or ("第 " in message and any(marker in message for marker in ("步", "帧", "target", "节点"))):
        return "semantic_trace"
    if any(marker in text for marker in ("llmjsonerror", "jsondecodeerror", "模型返回", "apierror")):
        return "generation"
    return "unclassified"


def annotate_failure_metadata(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        for attempt in row.get("attempts") or []:
            errors = [str(error) for error in attempt.get("errors") or []]
            attempt["failure_types"] = repair_failure_types(errors)
            attempt["failure_stages"] = [failure_stage_for_message(error) for error in errors]
    return rows


def paired_strategy_comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_case: dict[str, dict[str, bool]] = defaultdict(dict)
    for row in rows:
        strategy = str(row.get("strategy") or "")
        if strategy in {"local_resume", "global_restart"}:
            by_case[str(row.get("case_id") or "")][strategy] = row.get("ok") is True
    pairs = [item for item in by_case.values() if {"local_resume", "global_restart"} <= item.keys()]
    both = sum(item["local_resume"] and item["global_restart"] for item in pairs)
    local_only = sum(item["local_resume"] and not item["global_restart"] for item in pairs)
    global_only = sum(not item["local_resume"] and item["global_restart"] for item in pairs)
    neither = sum(not item["local_resume"] and not item["global_restart"] for item in pairs)
    discordant = local_only + global_only
    if discordant:
        tail = sum(comb(discordant, index) for index in range(min(local_only, global_only) + 1))
        p_value = min(1.0, 2.0 * tail / (2**discordant))
    else:
        p_value = 1.0
    return {
        "matched_cases": len(pairs),
        "both_pass": both,
        "local_only_pass": local_only,
        "global_only_pass": global_only,
        "neither_pass": neither,
        "local_minus_global_pass_rate": (local_only - global_only) / len(pairs) if pairs else 0.0,
        "mcnemar_exact_two_sided_p": p_value,
    }


def estimate_strategy_cost(
    rows: list[dict[str, Any]],
    *,
    strategy: str,
    max_policy_calls: int,
) -> dict[str, Any]:
    initial = [row["attempts"][0] for row in rows if row.get("attempts")]
    recovery = [attempt for row in rows for attempt in (row.get("attempts") or [])[1:]]
    initial_success_rate = sum(attempt.get("valid") is True for attempt in initial) / len(initial) if initial else 0.0
    recovery_success_rate = (
        sum(attempt.get("valid") is True for attempt in recovery) / len(recovery) if recovery else 0.0
    )
    initial_costs = [
        float(tokens)
        for attempt in initial
        if (tokens := _call_tokens(attempt.get("model_calls") or [])) is not None
    ]
    recovery_costs = [
        float(tokens)
        for attempt in recovery
        if (tokens := _call_tokens(attempt.get("model_calls") or [])) is not None
    ]
    observed_total_tokens = sum(
        tokens
        for row in rows
        for attempt in row.get("attempts") or []
        if (tokens := _call_tokens(attempt.get("model_calls") or [])) is not None
    )
    passed = sum(row.get("ok") is True for row in rows)
    observed_success_rate = passed / len(rows) if rows else 0.0
    observed_tokens_per_success = observed_total_tokens / passed if passed else None
    predicted_success_rate = 0.0
    predicted_cost_per_input = None
    if strategy == "local_resume":
        c0 = _mean(initial_costs)
        cr = _mean(recovery_costs)
        recovery_rounds = max(0, max_policy_calls - 1)
        if c0 is not None:
            if recovery_rounds == 0:
                predicted_success_rate = initial_success_rate
                predicted_cost_per_input = c0
            elif recovery_success_rate > 0 and cr is not None:
                recovery_success = 1.0 - (1.0 - recovery_success_rate) ** recovery_rounds
                predicted_success_rate = initial_success_rate + (1.0 - initial_success_rate) * recovery_success
                retry_multiplier = sum((1.0 - recovery_success_rate) ** index for index in range(recovery_rounds))
                predicted_cost_per_input = c0 + (1.0 - initial_success_rate) * cr * retry_multiplier
            else:
                predicted_success_rate = initial_success_rate
                predicted_cost_per_input = c0 + (1.0 - initial_success_rate) * (cr or 0.0) * recovery_rounds
    else:
        attempts = [attempt for row in rows for attempt in row.get("attempts") or []]
        attempt_success_rate = (
            sum(attempt.get("valid") is True for attempt in attempts) / len(attempts) if attempts else 0.0
        )
        attempt_costs = [
            float(tokens)
            for attempt in attempts
            if (tokens := _call_tokens(attempt.get("model_calls") or [])) is not None
        ]
        attempt_cost = _mean(attempt_costs)
        predicted_success_rate = 1.0 - (1.0 - attempt_success_rate) ** max_policy_calls
        if attempt_cost is not None:
            multiplier = sum((1.0 - attempt_success_rate) ** index for index in range(max_policy_calls))
            predicted_cost_per_input = attempt_cost * multiplier
    predicted_tokens_per_success = (
        predicted_cost_per_input / predicted_success_rate
        if predicted_cost_per_input is not None and predicted_success_rate > 0
        else None
    )
    relative_error = (
        abs(predicted_tokens_per_success - observed_tokens_per_success) / observed_tokens_per_success
        if predicted_tokens_per_success is not None and observed_tokens_per_success
        else None
    )
    return {
        "initial_success_rate": initial_success_rate,
        "recovery_success_rate": recovery_success_rate,
        "mean_initial_attempt_tokens": _mean(initial_costs),
        "mean_recovery_attempt_tokens": _mean(recovery_costs),
        "predicted_success_rate_at_cap": predicted_success_rate,
        "observed_success_rate_at_cap": observed_success_rate,
        "success_prediction_absolute_error": abs(predicted_success_rate - observed_success_rate),
        "predicted_tokens_per_success_at_cap": predicted_tokens_per_success,
        "observed_tokens_per_success": observed_tokens_per_success,
        "token_prediction_relative_error": relative_error,
    }


def _strategy_summary(rows: list[dict[str, Any]], *, strategy: str, max_policy_calls: int) -> dict[str, Any]:
    passed = [row for row in rows if row.get("ok") is True]
    calls = [int(row.get("actual_model_calls") or 0) for row in rows]
    tokens = [_call_tokens(row.get("model_calls") or []) for row in rows]
    available_tokens = [value for value in tokens if value is not None]
    initial_attempts = [row["attempts"][0] for row in rows if row.get("attempts")]
    recovery_attempts = [attempt for row in rows for attempt in (row.get("attempts") or [])[1:]]
    initial_pass = sum(attempt.get("valid") is True for attempt in initial_attempts)
    recovery_pass = sum(attempt.get("valid") is True for attempt in recovery_attempts)
    failed_attempts = [
        attempt
        for row in rows
        for attempt in row.get("attempts") or []
        if attempt.get("valid") is not True
    ]
    failure_type_counts = Counter(
        failure_type
        for attempt in failed_attempts
        for failure_type in attempt.get("failure_types") or []
    )
    failure_stage_counts = Counter(
        failure_stage
        for attempt in failed_attempts
        for failure_stage in attempt.get("failure_stages") or []
    )
    located_failed_attempts = sum(
        any(stage != "unclassified" for stage in attempt.get("failure_stages") or [])
        for attempt in failed_attempts
    )
    successful_tokens = [
        _call_tokens(row.get("model_calls") or []) for row in passed
    ]
    successful_tokens = [value for value in successful_tokens if value is not None]
    return {
        "total": len(rows),
        "passed": len(passed),
        "pass_rate": len(passed) / len(rows) if rows else 0.0,
        "avg_actual_model_calls": sum(calls) / len(calls) if calls else 0.0,
        "avg_tokens": sum(available_tokens) / len(available_tokens) if available_tokens else None,
        "avg_tokens_for_successful_rows": sum(successful_tokens) / len(successful_tokens) if successful_tokens else None,
        "observed_actual_model_calls_per_success": sum(calls) / len(passed) if passed else None,
        "avg_time_to_valid_s": (
            sum(float(row.get("duration_s") or 0.0) for row in passed) / len(passed) if passed else None
        ),
        "initial_attempt_success": initial_pass,
        "initial_attempts": len(initial_attempts),
        "initial_attempt_success_rate": initial_pass / len(initial_attempts) if initial_attempts else 0.0,
        "recovery_attempt_success": recovery_pass,
        "recovery_attempts": len(recovery_attempts),
        "recovery_attempt_success_rate": recovery_pass / len(recovery_attempts) if recovery_attempts else 0.0,
        "failure_type_counts": dict(sorted(failure_type_counts.items())),
        "failure_stage_counts": dict(sorted(failure_stage_counts.items())),
        "failed_attempts": len(failed_attempts),
        "failed_attempts_with_stage": located_failed_attempts,
        "failed_attempt_stage_localization_rate": (
            located_failed_attempts / len(failed_attempts) if failed_attempts else 1.0
        ),
        "discarded_spec_count": sum(
            1
            for row in rows
            for attempt in row.get("attempts") or []
            if row.get("strategy") == "global_restart" and attempt.get("valid") is not True
        ),
        "model_usage": summarize_model_usage(rows),
        "theory_fit": estimate_strategy_cost(
            rows,
            strategy=strategy,
            max_policy_calls=max_policy_calls,
        ),
    }


def summarize_results(rows: list[dict[str, Any]], *, max_policy_calls: int) -> dict[str, Any]:
    annotate_failure_metadata(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("strategy") or "unknown")].append(row)
    summaries = {
        strategy: _strategy_summary(items, strategy=strategy, max_policy_calls=max_policy_calls)
        for strategy, items in sorted(grouped.items())
    }
    actual_call_budgets = sorted({int(row.get("actual_model_calls") or 0) for row in rows})
    token_budgets = sorted(
        {
            tokens
            for row in rows
            if (tokens := _call_tokens(row.get("model_calls") or [])) is not None
        }
    )
    call_curves = {}
    token_curves = {}
    for strategy, items in sorted(grouped.items()):
        call_curves[strategy] = [
            {
                "actual_model_call_budget": budget,
                "successes": sum(
                    row.get("ok") is True and int(row.get("actual_model_calls") or 0) <= budget for row in items
                ),
                "total": len(items),
            }
            for budget in actual_call_budgets
        ]
        token_curves[strategy] = [
            {
                "token_budget": budget,
                "successes": sum(
                    row.get("ok") is True
                    and (tokens := _call_tokens(row.get("model_calls") or [])) is not None
                    and tokens <= budget
                    for row in items
                ),
                "total": len(items),
            }
            for budget in token_budgets
        ]
    return {
        "strategies": summaries,
        "paired_comparison": paired_strategy_comparison(rows),
        "fixed_actual_call_budget_curve": call_curves,
        "fixed_token_budget_curve": token_curves,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=50)
    parser.add_argument("--strategy", choices=["local_resume", "global_restart", "both"], default="both")
    parser.add_argument("--max-policy-calls", type=int, default=3)
    parser.add_argument("--solutions", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--strict-warnings", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--disable-teaching", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = _stratified_cases(args.max_cases, set(args.case))
    strategies = ["local_resume", "global_restart"] if args.strategy == "both" else [args.strategy]
    jobs = [(case, strategy) for case in cases for strategy in strategies]
    rows: list[dict[str, Any]] = []
    pending: list[tuple[Any, str]] = []
    for case, strategy in jobs:
        result_path = args.output_dir / "results" / strategy / f"{case.id}.json"
        if args.resume and result_path.exists():
            rows.append(json.loads(result_path.read_text(encoding="utf-8")))
        else:
            pending.append((case, strategy))
    started_at = datetime.now().replace(microsecond=0).isoformat()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(_run_one, case, strategy, args): (case.id, strategy) for case, strategy in pending}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            case_id, strategy = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {
                    "case_id": case_id,
                    "strategy": strategy,
                    "model": _model_name(),
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "attempts": [],
                    "model_calls": [],
                    "actual_model_calls": 0,
                }
            rows.append(row)
            print(f"RETRY_POLICY {index}/{len(pending)} {strategy} {case_id} ok={row.get('ok')}", flush=True)
    rows.sort(key=lambda row: (str(row.get("case_id")), str(row.get("strategy"))))
    report = {
        "kind": "local_vs_global_retry_report",
        "started_at": started_at,
        "ended_at": datetime.now().replace(microsecond=0).isoformat(),
        "model": _model_name(),
        "llm": llm_config(),
        "config": {
            "cases": [case.id for case in cases],
            "sample": 0,
            "strategies": strategies,
            "max_policy_calls": args.max_policy_calls,
            "solutions": args.solutions,
            "strict_warnings": args.strict_warnings,
            "teaching_enrichment": not args.disable_teaching,
            "concurrency": args.concurrency,
            "recovery_boundary": "retain current solution spec then repair vs discard spec and regenerate",
            "materialization_reexecutes_deterministic_stages": True,
        },
        "summary": summarize_results(rows, max_policy_calls=args.max_policy_calls),
        "results": rows,
    }
    output = args.output_dir / "local_vs_global_retry_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
