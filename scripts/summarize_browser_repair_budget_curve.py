"""Summarize Direct-BrowserRepair call, token, time, and audit curves."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT_DIR = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5"


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 3) if values else 0.0


def summarize_budget(
    *,
    call_budget: int,
    method_report: dict[str, Any],
    strict_audit: dict[str, Any],
    paired_statistics: dict[str, Any],
    paired_strict_statistics: dict[str, Any],
    token_target: int,
) -> dict[str, Any]:
    rows = list(method_report.get("results") or [])
    call_counts: list[float] = []
    total_tokens: list[float] = []
    generation_seconds: list[float] = []
    for row in rows:
        calls = [call for call in row.get("model_calls") or [] if isinstance(call, dict)]
        call_counts.append(float(len(calls)))
        total_tokens.append(float(sum(int(call.get("total_tokens") or 0) for call in calls)))
        generation_seconds.append(float(sum(float(call.get("duration_s") or 0.0) for call in calls)))

    condition = f"direct_browser_repair_{call_budget}"
    machine = (strict_audit.get("summary") or {}).get(condition) or {}
    strict = (strict_audit.get("self_contained_summary") or {}).get(condition) or {}
    paired_machine = (paired_statistics.get("machine_boolean") or {}).get("machine_ok") or {}
    paired_strict = (paired_strict_statistics.get("machine_boolean") or {}).get("strict_machine_ok") or {}
    return {
        "call_budget": call_budget,
        "condition": condition,
        "cases": len(rows),
        "avg_calls": _mean(call_counts),
        "avg_total_tokens": _mean(total_tokens),
        "median_total_tokens": round(float(statistics.median(total_tokens)), 3) if total_tokens else 0.0,
        "avg_generation_seconds": _mean(generation_seconds),
        "token_target": int(token_target),
        "over_token_target_cases": sum(value > token_target for value in total_tokens),
        "machine_ok": int(machine.get("machine_ok") or 0),
        "self_contained_ok": int(strict.get("self_contained_ok") or 0),
        "strict_machine_ok": int(strict.get("strict_machine_ok") or 0),
        "paired_machine_ok": paired_machine,
        "paired_strict_machine_ok": paired_strict,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Direct-BrowserRepair Budget Curve",
        "",
        "| Calls | Machine OK | Self-contained | Strict joint | Avg tokens | Median tokens | Avg generation s | Over token target | Functional p | Strict p |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["budgets"]:
        paired = row.get("paired_machine_ok") or {}
        paired_strict = row.get("paired_strict_machine_ok") or {}
        cases = int(row["cases"])
        lines.append(
            f"| {row['call_budget']} | {row['machine_ok']}/{cases} | {row['self_contained_ok']}/{cases} | "
            f"{row['strict_machine_ok']}/{cases} | {row['avg_total_tokens']:.1f} | "
            f"{row['median_total_tokens']:.1f} | {row['avg_generation_seconds']:.1f} | "
            f"{row['over_token_target_cases']}/{cases} | {float(paired.get('mcnemar_exact_p') or 1.0):.6g} | "
            f"{float(paired_strict.get('mcnemar_exact_p') or 1.0):.6g} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _path(value: Path) -> Path:
    return value if value.is_absolute() else ROOT / value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, default=DEFAULT_EXPERIMENT_DIR)
    parser.add_argument("--budgets", default="1,2,3,5")
    parser.add_argument("--token-target", type=int, default=80000)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    experiment_dir = _path(args.experiment_dir)
    budgets = [int(value) for value in args.budgets.split(",") if value.strip()]
    summaries = []
    for budget in budgets:
        method_path = experiment_dir / "budget_reports" / f"calls_{budget}" / "llm_benchmark_report.json"
        audit_path = experiment_dir / "machine_audits" / f"calls_{budget}" / "interaction_semantic_eval_report_strict.json"
        paired_path = experiment_dir / "statistics" / f"calls_{budget}" / "functional" / "paired_machine_statistics.json"
        paired_strict_path = experiment_dir / "statistics" / f"calls_{budget}" / "strict" / "paired_machine_statistics.json"
        summaries.append(
            summarize_budget(
                call_budget=budget,
                method_report=json.loads(method_path.read_text(encoding="utf-8")),
                strict_audit=json.loads(audit_path.read_text(encoding="utf-8")),
                paired_statistics=json.loads(paired_path.read_text(encoding="utf-8")),
                paired_strict_statistics=json.loads(paired_strict_path.read_text(encoding="utf-8")),
                token_target=args.token_target,
            )
        )

    payload = {
        "kind": "direct_browser_repair_budget_curve",
        "created_at": datetime.now().astimezone().isoformat(),
        "experiment_dir": str(experiment_dir),
        "token_target": args.token_target,
        "budgets": summaries,
    }
    output = _path(args.output) if args.output else experiment_dir / "budget_curve_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output.with_suffix(".md"), payload)
    print(json.dumps({"output": str(output), "budgets": len(summaries)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
