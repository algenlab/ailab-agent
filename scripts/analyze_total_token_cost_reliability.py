"""Analyze total model-token cost against Machine OK reliability."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.analyze_paired_experiments import paired_binary_summary
except ModuleNotFoundError:  # Direct execution places scripts/, not the repository root, on sys.path.
    from analyze_paired_experiments import paired_binary_summary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECT_REPORT = (
    ROOT
    / "output/experiments/direct_browser_repair_fair_20260723/fair_repair_report.json"
)
DEFAULT_ALGOTUTORGEN_REPORT = (
    ROOT
    / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
)
DEFAULT_MACHINE_REPORT = (
    ROOT
    / "output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine_rendered_text"
    / "interaction_semantic_eval_report.json"
)
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/total_token_cost_reliability_20260725"
DEFAULT_TOKEN_CAPS = (
    0.0,
    50_000.0,
    60_000.0,
    76_847.165,
    84_352.785,
    100_000.0,
    120_000.0,
    140_000.0,
    160_000.0,
    180_000.0,
    200_000.0,
    250_000.0,
    300_000.0,
)


def _mean(values: list[float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def _median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def _index_unique(rows: Iterable[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{label}: missing case_id")
        if case_id in indexed:
            raise ValueError(f"{label}: duplicate case_id {case_id}")
        indexed[case_id] = row
    return indexed


def _require_count(indexed: dict[str, Any], expected_cases: int | None, *, label: str) -> None:
    if expected_cases is not None and len(indexed) != expected_cases:
        raise ValueError(f"{label}: expected {expected_cases} cases, found {len(indexed)}")


def _require_same_ids(left: set[str], right: set[str], *, label: str) -> list[str]:
    if left != right:
        missing_left = sorted(right - left)
        missing_right = sorted(left - right)
        raise ValueError(
            f"{label}: unmatched case IDs; missing_left={missing_left[:10]} "
            f"missing_right={missing_right[:10]}"
        )
    return sorted(left)


def _validated_usage(call: dict[str, Any], *, label: str) -> dict[str, float | int]:
    if call.get("usage_available") is not True:
        raise ValueError(f"{label}: usage unavailable")
    values: dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = call.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{label}: invalid {key}={value!r}")
        values[key] = value
    if values["prompt_tokens"] + values["completion_tokens"] != values["total_tokens"]:
        raise ValueError(f"{label}: token total mismatch")
    duration = call.get("duration_s")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0:
        raise ValueError(f"{label}: invalid duration_s={duration!r}")
    return {**values, "duration_s": float(duration)}


def build_direct_ledger(
    report: dict[str, Any], *, expected_cases: int | None = 200
) -> list[dict[str, Any]]:
    indexed = _index_unique(report.get("results") or [], label="Direct report")
    _require_count(indexed, expected_cases, label="Direct report")
    ledger: list[dict[str, Any]] = []
    for case_id in sorted(indexed):
        row = indexed[case_id]
        raw_attempts = row.get("attempts") or []
        if not raw_attempts:
            raise ValueError(f"Direct {case_id}: no attempts")
        attempts: list[dict[str, Any]] = []
        cumulative_tokens = 0
        for position, attempt in enumerate(raw_attempts, start=1):
            call_index = attempt.get("call_index")
            if call_index != position:
                raise ValueError(
                    f"Direct {case_id}: expected call_index {position}, found {call_index!r}"
                )
            usage = _validated_usage(
                attempt.get("model_call") or {}, label=f"Direct {case_id} call {call_index}"
            )
            machine_ok = (attempt.get("audit") or {}).get("machine_ok")
            if not isinstance(machine_ok, bool):
                raise ValueError(f"Direct {case_id} call {call_index}: missing boolean machine_ok")
            cumulative_tokens += int(usage["total_tokens"])
            attempts.append(
                {
                    "call_index": call_index,
                    "repair_round": max(0, position - 1),
                    "prompt_tokens": int(usage["prompt_tokens"]),
                    "completion_tokens": int(usage["completion_tokens"]),
                    "total_tokens": int(usage["total_tokens"]),
                    "cumulative_tokens": cumulative_tokens,
                    "api_latency_seconds": float(usage["duration_s"]),
                    "machine_ok": machine_ok,
                }
            )
        ledger.append(
            {
                "case_id": case_id,
                "family_id": row.get("family_id"),
                "attempts": attempts,
                "initial_tokens": attempts[0]["total_tokens"],
                "total_tokens": cumulative_tokens,
            }
        )
    return ledger


def _summarize_replays(
    replays: list[dict[str, Any]], *, strategy_fields: dict[str, Any]
) -> dict[str, Any]:
    total_tokens = sum(int(row["total_tokens"]) for row in replays)
    prompt_tokens = sum(int(row["prompt_tokens"]) for row in replays)
    completion_tokens = sum(int(row["completion_tokens"]) for row in replays)
    calls = sum(int(row["included_calls"]) for row in replays)
    api_seconds = sum(float(row["api_latency_seconds"]) for row in replays)
    machine_ok = sum(row["machine_ok"] is True for row in replays)
    cases = len(replays)
    return {
        **strategy_fields,
        "cases": cases,
        "total_tokens": total_tokens,
        "tokens_per_task": total_tokens / cases if cases else 0.0,
        "median_tokens_per_task": _median([float(row["total_tokens"]) for row in replays]),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "model_calls": calls,
        "model_calls_per_task": calls / cases if cases else 0.0,
        "api_latency_seconds": api_seconds,
        "api_latency_seconds_per_task": api_seconds / cases if cases else 0.0,
        "machine_ok": machine_ok,
        "machine_ok_rate": machine_ok / cases if cases else 0.0,
    }


def replay_fixed_repair_budget(case: dict[str, Any], *, repair_budget: int) -> dict[str, Any]:
    if repair_budget < 0:
        raise ValueError("repair_budget must be non-negative")
    included = case["attempts"][: repair_budget + 1]
    return _replay_payload(case, included)


def replay_under_token_cap(case: dict[str, Any], *, token_cap: float) -> dict[str, Any]:
    if token_cap < 0:
        raise ValueError("token_cap must be non-negative")
    included: list[dict[str, Any]] = []
    running = 0
    for position, attempt in enumerate(case["attempts"]):
        call_tokens = int(attempt["total_tokens"])
        if position == 0 or running + call_tokens <= token_cap:
            included.append(attempt)
            running += call_tokens
        else:
            break
    return _replay_payload(case, included)


def _replay_payload(case: dict[str, Any], included: list[dict[str, Any]]) -> dict[str, Any]:
    if not included:
        raise ValueError(f"Direct {case['case_id']}: replay must include the initial call")
    first_ok = next((row["call_index"] for row in included if row["machine_ok"]), None)
    return {
        "case_id": case["case_id"],
        "included_calls": len(included),
        "prompt_tokens": sum(int(row["prompt_tokens"]) for row in included),
        "completion_tokens": sum(int(row["completion_tokens"]) for row in included),
        "total_tokens": sum(int(row["total_tokens"]) for row in included),
        "api_latency_seconds": sum(float(row["api_latency_seconds"]) for row in included),
        "machine_ok": first_ok is not None,
        "first_machine_ok_call": first_ok,
    }


def summarize_fixed_repair_budgets(
    ledger: list[dict[str, Any]], *, budgets: Iterable[int]
) -> list[dict[str, Any]]:
    return [
        _summarize_replays(
            [replay_fixed_repair_budget(case, repair_budget=budget) for case in ledger],
            strategy_fields={"repair_budget": int(budget)},
        )
        for budget in budgets
    ]


def summarize_token_caps(
    ledger: list[dict[str, Any]], *, token_caps: Iterable[float]
) -> list[dict[str, Any]]:
    rows = []
    for cap in sorted(set(float(value) for value in token_caps)):
        replays = [replay_under_token_cap(case, token_cap=cap) for case in ledger]
        row = _summarize_replays(replays, strategy_fields={"token_cap": cap})
        row["initial_calls_over_cap"] = sum(case["initial_tokens"] > cap for case in ledger)
        rows.append(row)
    return rows


def _selected_pipeline_timing(report: dict[str, Any]) -> dict[str, float | str]:
    total_pipeline = sum(float(row.get("duration_s") or 0.0) for row in report.get("results") or [])
    api_latency = sum(
        float(call.get("duration_s") or 0.0)
        for row in report.get("results") or []
        for call in row.get("model_calls") or []
    )
    render = sum(
        float(phase.get("duration_s") or 0.0)
        for row in report.get("results") or []
        for phase in row.get("phase_timings") or []
        if phase.get("phase") == "render"
    )
    return {
        "pipeline_seconds": total_pipeline,
        "non_model_pipeline_residual_seconds": total_pipeline - api_latency,
        "render_seconds": render,
        "compile_seconds": "not_separately_instrumented",
    }


def extract_algotutorgen_costs(
    report: dict[str, Any], *, expected_cases: int | None = 200
) -> dict[str, Any]:
    indexed = _index_unique(report.get("results") or [], label="AlgoTutorGen report")
    _require_count(indexed, expected_cases, label="AlgoTutorGen report")
    selected_calls: list[dict[str, Any]] = []
    for case_id in sorted(indexed):
        calls = indexed[case_id].get("model_calls") or []
        if not calls:
            raise ValueError(f"AlgoTutorGen {case_id}: no selected-final model calls")
        for position, call in enumerate(calls, start=1):
            selected_calls.append(
                _validated_usage(call, label=f"AlgoTutorGen {case_id} selected call {position}")
            )
    selected_total = sum(int(call["total_tokens"]) for call in selected_calls)
    selected_prompt = sum(int(call["prompt_tokens"]) for call in selected_calls)
    selected_completion = sum(int(call["completion_tokens"]) for call in selected_calls)
    selected_duration = sum(float(call["duration_s"]) for call in selected_calls)

    metadata = ((report.get("merge_metadata") or {}).get("all_attempts_model_usage") or {})
    primary = metadata.get("primary") or {}
    retry = metadata.get("retry") or {}
    all_total = metadata.get("combined_total_tokens")
    all_calls = metadata.get("combined_call_count")
    if not isinstance(all_total, int) or not isinstance(all_calls, int):
        raise ValueError("AlgoTutorGen report: missing all-attempt usage totals")
    combined_from_parts = int(primary.get("total_tokens") or 0) + int(retry.get("total_tokens") or 0)
    calls_from_parts = int(primary.get("call_count") or 0) + int(retry.get("call_count") or 0)
    if all_total != combined_from_parts or all_calls != calls_from_parts:
        raise ValueError("AlgoTutorGen report: inconsistent all-attempt usage totals")
    all_prompt = int(primary.get("prompt_tokens") or 0) + int(retry.get("prompt_tokens") or 0)
    all_completion = int(primary.get("completion_tokens") or 0) + int(retry.get("completion_tokens") or 0)
    if all_prompt + all_completion != all_total:
        raise ValueError("AlgoTutorGen report: all-attempt token total mismatch")
    all_duration = float(primary.get("duration_s") or 0.0) + float(retry.get("duration_s") or 0.0)
    cases = len(indexed)
    timing = _selected_pipeline_timing(report)
    return {
        "selected_final": {
            "total_tokens": selected_total,
            "tokens_per_task": selected_total / cases,
            "prompt_tokens": selected_prompt,
            "completion_tokens": selected_completion,
            "model_calls": len(selected_calls),
            "model_calls_per_task": len(selected_calls) / cases,
            "api_latency_seconds": selected_duration,
            "api_latency_seconds_per_task": selected_duration / cases,
            **timing,
        },
        "all_attempts": {
            "total_tokens": all_total,
            "tokens_per_task": all_total / cases,
            "prompt_tokens": all_prompt,
            "completion_tokens": all_completion,
            "model_calls": all_calls,
            "model_calls_per_task": all_calls / cases,
            "api_latency_seconds": all_duration,
            "api_latency_seconds_per_task": all_duration / cases,
            "compile_seconds": "not_recoverable_for_discarded_attempts",
        },
    }


def _machine_index(
    report: dict[str, Any], *, expected_cases: int | None
) -> dict[str, dict[str, Any]]:
    rows = [row for row in report.get("records") or [] if row.get("condition") == "algolab_full"]
    indexed = _index_unique(rows, label="AlgoTutorGen Machine OK report")
    _require_count(indexed, expected_cases, label="AlgoTutorGen Machine OK report")
    for case_id, row in indexed.items():
        if not isinstance(row.get("machine_ok"), bool):
            raise ValueError(f"AlgoTutorGen Machine OK {case_id}: missing boolean machine_ok")
    return indexed


def find_closest_realized_cost_cap(
    ledger: list[dict[str, Any]], *, target_tokens_per_task: float
) -> dict[str, Any]:
    candidate_caps = sorted(
        {
            float(attempt["cumulative_tokens"])
            for case in ledger
            for attempt in case["attempts"]
        }
    )
    best: tuple[float, float, dict[str, Any]] | None = None
    for cap in candidate_caps:
        summary = summarize_token_caps(ledger, token_caps=[cap])[0]
        candidate = (abs(summary["tokens_per_task"] - target_tokens_per_task), cap, summary)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    if best is None:
        raise ValueError("Direct ledger has no token-cap candidates")
    summary = dict(best[2])
    summary["target_tokens_per_task"] = target_tokens_per_task
    summary["absolute_cost_gap_per_task"] = best[0]
    return summary


def _comparison(
    *,
    case_ids: list[str],
    algo_machine: dict[str, dict[str, Any]],
    direct_ledger: dict[str, dict[str, Any]],
    direct_cap_summary: dict[str, Any],
) -> dict[str, Any]:
    cap = float(direct_cap_summary["token_cap"])
    direct_replays = {
        case_id: replay_under_token_cap(direct_ledger[case_id], token_cap=cap)
        for case_id in case_ids
    }
    paired = paired_binary_summary(
        [algo_machine[case_id]["machine_ok"] is True for case_id in case_ids],
        [direct_replays[case_id]["machine_ok"] is True for case_id in case_ids],
        seed=20260725,
        draws=10_000,
    )
    return {
        "direction": "AlgoTutorGen - Direct",
        "direct_strategy": direct_cap_summary,
        "paired_statistics": paired,
    }


def analyze_reports(
    *,
    direct_report: dict[str, Any],
    algotutorgen_report: dict[str, Any],
    machine_report: dict[str, Any],
    token_caps: Iterable[float] = DEFAULT_TOKEN_CAPS,
    expected_cases: int | None = 200,
) -> dict[str, Any]:
    ledger = build_direct_ledger(direct_report, expected_cases=expected_cases)
    direct_index = {row["case_id"]: row for row in ledger}
    algo_result_index = _index_unique(
        algotutorgen_report.get("results") or [], label="AlgoTutorGen report"
    )
    _require_count(algo_result_index, expected_cases, label="AlgoTutorGen report")
    # Compare IDs before applying a redundant count check so missing cases are diagnosed by name.
    algo_machine = _machine_index(machine_report, expected_cases=None)
    case_ids = _require_same_ids(set(direct_index), set(algo_result_index), label="Direct/AlgoTutorGen")
    _require_same_ids(set(direct_index), set(algo_machine), label="Direct/Machine OK")

    costs = extract_algotutorgen_costs(algotutorgen_report, expected_cases=expected_cases)
    fixed_curve = summarize_fixed_repair_budgets(ledger, budgets=[0, 1, 2, 3, 5])
    selected_match = find_closest_realized_cost_cap(
        ledger, target_tokens_per_task=costs["selected_final"]["tokens_per_task"]
    )
    all_match = find_closest_realized_cost_cap(
        ledger, target_tokens_per_task=costs["all_attempts"]["tokens_per_task"]
    )
    literal_caps = list(token_caps) + [selected_match["token_cap"], all_match["token_cap"]]
    cap_curve = summarize_token_caps(ledger, token_caps=literal_caps)
    machine_ok = sum(row["machine_ok"] is True for row in algo_machine.values())
    comparisons = {
        "selected_final_cost_matched": _comparison(
            case_ids=case_ids,
            algo_machine=algo_machine,
            direct_ledger=direct_index,
            direct_cap_summary=selected_match,
        ),
        "all_attempts_cost_matched": _comparison(
            case_ids=case_ids,
            algo_machine=algo_machine,
            direct_ledger=direct_index,
            direct_cap_summary=all_match,
        ),
    }
    for name, cost_key in (
        ("selected_final_literal_hard_cap", "selected_final"),
        ("all_attempts_literal_hard_cap", "all_attempts"),
    ):
        cap = costs[cost_key]["tokens_per_task"]
        literal = summarize_token_caps(ledger, token_caps=[cap])[0]
        comparisons[name] = _comparison(
            case_ids=case_ids,
            algo_machine=algo_machine,
            direct_ledger=direct_index,
            direct_cap_summary=literal,
        )
    max_direct = fixed_curve[-1]
    comparisons["maximum_observed_direct_budget"] = {
        "direction": "AlgoTutorGen - Direct",
        "direct_strategy": max_direct,
        "paired_statistics": paired_binary_summary(
            [algo_machine[case_id]["machine_ok"] is True for case_id in case_ids],
            [
                replay_fixed_repair_budget(direct_index[case_id], repair_budget=5)["machine_ok"]
                for case_id in case_ids
            ],
            seed=20260725,
            draws=10_000,
        ),
    }
    return {
        "kind": "total_token_cost_reliability",
        "protocol": {
            "token_definition": "API prompt_tokens + completion_tokens",
            "fixed_budget_policy": "initial call plus at most r whole repair calls; early stop retained",
            "hard_cap_policy": (
                "the mandatory initial call is always charged; each repair is included only if the whole "
                "call remains within the per-task cap; Machine OK uses best-so-far"
            ),
            "primary_cost_basis": "operational all-attempt AlgoTutorGen cost",
            "paired_statistics": "10,000 paired bootstrap draws and two-sided exact McNemar",
        },
        "case_alignment": {"paired_cases": len(case_ids), "case_ids": case_ids},
        "direct": {
            "fixed_repair_budget_curve": fixed_curve,
            "token_cap_curve": cap_curve,
        },
        "algotutorgen": {
            **costs,
            "machine_ok": machine_ok,
            "machine_ok_rate": machine_ok / len(case_ids) if case_ids else 0.0,
        },
        "comparisons": comparisons,
        "limitations": [
            "This is an offline replay of a frozen adaptive repair policy, not a randomized causal comparison.",
            "AlgoTutorGen local compilation time was not independently instrumented; only a non-model pipeline residual is recoverable for selected-final attempts.",
            "AlgoTutorGen measurements come from the current solve/trace-separated implementation and must be rerun after a single-execution migration.",
        ],
        "_direct_ledger": ledger,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = payload.pop("_direct_ledger")
    (output_dir / "total_token_cost_reliability.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    budget_fields = [
        "repair_budget", "cases", "total_tokens", "tokens_per_task", "median_tokens_per_task",
        "prompt_tokens", "completion_tokens", "model_calls", "model_calls_per_task",
        "api_latency_seconds", "api_latency_seconds_per_task", "machine_ok", "machine_ok_rate",
    ]
    _write_csv(
        output_dir / "budget_curve.csv",
        payload["direct"]["fixed_repair_budget_curve"],
        budget_fields,
    )
    cap_fields = [
        "token_cap", "cases", "total_tokens", "tokens_per_task", "median_tokens_per_task",
        "prompt_tokens", "completion_tokens", "model_calls", "model_calls_per_task",
        "api_latency_seconds", "api_latency_seconds_per_task", "machine_ok", "machine_ok_rate",
        "initial_calls_over_cap",
    ]
    _write_csv(output_dir / "token_cap_curve.csv", payload["direct"]["token_cap_curve"], cap_fields)
    ledger_rows = []
    for case in ledger:
        for attempt in case["attempts"]:
            ledger_rows.append({"case_id": case["case_id"], "family_id": case["family_id"], **attempt})
    _write_csv(
        output_dir / "per_task_ledger.csv",
        ledger_rows,
        [
            "case_id", "family_id", "call_index", "repair_round", "prompt_tokens",
            "completion_tokens", "total_tokens", "cumulative_tokens", "api_latency_seconds",
            "machine_ok",
        ],
    )
    write_markdown(output_dir / "total_token_cost_reliability.md", payload)
    write_figure(output_dir / "total_token_cost_reliability.png", payload)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    algo = payload["algotutorgen"]
    main = payload["comparisons"]["all_attempts_cost_matched"]
    stats = main["paired_statistics"]
    strategy = main["direct_strategy"]
    lines = [
        "# Total Token Cost-Reliability Curve",
        "",
        "## 主要结果",
        "",
        "| 方法/策略 | 总 tokens/题 | Machine OK | 模型调用/题 | API latency/题 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in payload["direct"]["fixed_repair_budget_curve"]:
        lines.append(
            f"| Direct + 最多 {row['repair_budget']} 次修复 | {row['tokens_per_task']:,.3f} | "
            f"{row['machine_ok']}/{row['cases']} | {row['model_calls_per_task']:.3f} | "
            f"{row['api_latency_seconds_per_task']:.3f} s |"
        )
    for label, key in (("AlgoTutorGen selected-final", "selected_final"), ("AlgoTutorGen all-attempt", "all_attempts")):
        row = algo[key]
        lines.append(
            f"| {label} | {row['tokens_per_task']:,.3f} | {algo['machine_ok']}/200 | "
            f"{row['model_calls_per_task']:.3f} | {row['api_latency_seconds_per_task']:.3f} s |"
        )
    lines.extend(
        [
            "",
            "## 主比较",
            "",
            f"AlgoTutorGen all-attempt 的平均成本为 {algo['all_attempts']['tokens_per_task']:,.3f} tokens/题。"
            f"Direct 每题硬 cap={strategy['token_cap']:,.0f} 时，实际平均成本为 "
            f"{strategy['tokens_per_task']:,.3f} tokens/题，是冻结日志中最接近该目标的点；"
            f"其 Machine OK 为 {strategy['machine_ok']}/200。",
            "",
            f"配对差值按 AlgoTutorGen - Direct 定义，为 {stats['difference'] * 100:.1f} 个百分点，"
            f"95% paired-bootstrap CI [{stats['bootstrap_ci_95'][0] * 100:.1f}, "
            f"{stats['bootstrap_ci_95'][1] * 100:.1f}]，exact McNemar p={stats['mcnemar_exact_p']:.6g}。",
            "",
            "## 口径说明",
            "",
            "- token 为 API 返回的 prompt_tokens + completion_tokens；所有 617 次 Direct 调用 usage 均完整。",
            "- 硬 cap 不允许纳入部分模型调用；初始调用是不可避免的已发生成本，即使它自身高于 cap 也计入。",
            "- Machine OK 使用 best-so-far，因此后续失败页面不会让已经通过的任务退化。",
            "- 84.4k 是 AlgoTutorGen 的平均成本，不等于 Direct 的逐题 84.4k 硬 cap。两者均在 JSON/CSV 中报告。",
            "- API latency 与调用数独立汇总。旧日志没有独立的本地编译计时，selected-final 只能恢复非模型流水线残差。",
            "",
            "## 结论边界",
            "",
            "在冻结的 Direct 初始页、反馈器、整页重写策略和最多五次修复范围内，Direct 在更高平均 token 成本下仍未追上 AlgoTutorGen。"
            "这支持该测试预算范围内的结构化链路成本-可靠性优势，但不是对所有 browser repair 方法的严格因果结论。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_figure(path: Path, payload: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fixed = payload["direct"]["fixed_repair_budget_curve"]
    caps = payload["direct"]["token_cap_curve"]
    algo = payload["algotutorgen"]
    fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=180)
    ax.plot(
        [row["tokens_per_task"] / 1000 for row in caps],
        [row["machine_ok_rate"] * 100 for row in caps],
        color="#26734d",
        marker="o",
        markersize=3.5,
        linewidth=1.5,
        label="Direct: per-task hard-cap replay",
    )
    ax.plot(
        [row["tokens_per_task"] / 1000 for row in fixed],
        [row["machine_ok_rate"] * 100 for row in fixed],
        color="#b54708",
        marker="s",
        markersize=5,
        linewidth=1.8,
        label="Direct: fixed repair budget",
    )
    for label, key, marker in (
        ("AlgoTutorGen selected-final", "selected_final", "D"),
        ("AlgoTutorGen all-attempt", "all_attempts", "*"),
    ):
        row = algo[key]
        ax.scatter(
            [row["tokens_per_task"] / 1000],
            [algo["machine_ok_rate"] * 100],
            s=90 if marker == "*" else 55,
            marker=marker,
            color="#174ea6",
            zorder=5,
            label=label,
        )
    ax.set_xlabel("Realized total model tokens per task (thousands)")
    ax.set_ylabel("Machine OK (%)")
    ax.set_xlim(left=15)
    ax.set_ylim(45, 102)
    ax.grid(True, color="#d9d9d9", linewidth=0.6, alpha=0.8)
    ax.legend(loc="center right", fontsize=8, frameon=True)
    ax.set_title("Total Token Cost-Reliability")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _path(value: Path) -> Path:
    return value if value.is_absolute() else ROOT / value


def _parse_caps(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct-report", type=Path, default=DEFAULT_DIRECT_REPORT)
    parser.add_argument("--algotutorgen-report", type=Path, default=DEFAULT_ALGOTUTORGEN_REPORT)
    parser.add_argument("--machine-report", type=Path, default=DEFAULT_MACHINE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--token-caps", default=",".join(str(value) for value in DEFAULT_TOKEN_CAPS)
    )
    args = parser.parse_args()
    direct_path = _path(args.direct_report)
    algo_path = _path(args.algotutorgen_report)
    machine_path = _path(args.machine_report)
    payload = analyze_reports(
        direct_report=json.loads(direct_path.read_text(encoding="utf-8")),
        algotutorgen_report=json.loads(algo_path.read_text(encoding="utf-8")),
        machine_report=json.loads(machine_path.read_text(encoding="utf-8")),
        token_caps=_parse_caps(args.token_caps),
        expected_cases=200,
    )
    payload["sources"] = {
        "direct_report": {"path": str(direct_path), "sha256": _sha256(direct_path)},
        "algotutorgen_report": {"path": str(algo_path), "sha256": _sha256(algo_path)},
        "machine_report": {"path": str(machine_path), "sha256": _sha256(machine_path)},
    }
    output_dir = _path(args.output_dir)
    write_outputs(output_dir, payload)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "paired_cases": payload["case_alignment"]["paired_cases"],
                "direct_max_machine_ok": payload["direct"]["fixed_repair_budget_curve"][-1]["machine_ok"],
                "algotutorgen_machine_ok": payload["algotutorgen"]["machine_ok"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
