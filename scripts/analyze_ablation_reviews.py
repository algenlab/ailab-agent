"""Compute paired statistics for full-vs-ablation review reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_paired_experiments import holm_adjust, paired_ordinal_summary
from scripts.run_external_eval_methods import EXTERNAL_REVIEW_SCORE_KEYS


def analyze_ablation_report(report: dict[str, Any], *, expected_pairs: int = 200) -> dict[str, Any]:
    condition = str(report.get("condition") or "")
    if not condition:
        raise ValueError("ablation report missing condition")
    reviews: dict[str, dict[str, Any]] = {}
    for row in report.get("pair_reviews") or []:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{condition}: missing case_id")
        if case_id in reviews:
            raise ValueError(f"{condition}: duplicate case_id {case_id}")
        reviews[case_id] = row
    if len(reviews) != expected_pairs:
        raise ValueError(f"{condition}: expected {expected_pairs} pairs, found {len(reviews)}")
    case_ids = sorted(reviews)
    metrics = {}
    for metric in EXTERNAL_REVIEW_SCORE_KEYS:
        full = [float(reviews[case_id]["conditions"]["full"]["scores"][metric]) for case_id in case_ids]
        ablated = [float(reviews[case_id]["conditions"][condition]["scores"][metric]) for case_id in case_ids]
        metrics[metric] = paired_ordinal_summary(full, ablated)
    adjusted = holm_adjust({name: row["wilcoxon_p"] for name, row in metrics.items()})
    for name, value in adjusted.items():
        metrics[name]["holm_within_condition_p"] = value
    return {"condition": condition, "pair_count": len(case_ids), "metrics": metrics}


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Ablation Paired Statistics",
        "",
        "| Condition | Metric | Full mean | Ablated mean | Mean diff | Wilcoxon p | Holm within | Holm global | Rank-biserial |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, result in payload["conditions"].items():
        for metric, row in result["metrics"].items():
            lines.append(
                f"| {condition} | {metric} | {row['a_mean']:.4f} | {row['b_mean']:.4f} | "
                f"{row['mean_difference']:.4f} | {row['wilcoxon_p']:.6g} | "
                f"{row['holm_within_condition_p']:.6g} | {row['holm_global_p']:.6g} | "
                f"{row['matched_pairs_rank_biserial']:.4f} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    conditions: dict[str, dict[str, Any]] = {}
    sources = {}
    for raw_path in args.report:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        result = analyze_ablation_report(json.loads(path.read_text(encoding="utf-8")))
        condition = result["condition"]
        if condition in conditions:
            raise ValueError(f"duplicate condition {condition}")
        conditions[condition] = result
        sources[condition] = str(path)

    global_pvalues = {
        f"{condition}:{metric}": row["wilcoxon_p"]
        for condition, result in conditions.items()
        for metric, row in result["metrics"].items()
    }
    global_adjusted = holm_adjust(global_pvalues)
    for key, value in global_adjusted.items():
        condition, metric = key.split(":", 1)
        conditions[condition]["metrics"][metric]["holm_global_p"] = value

    payload = {"kind": "ablation_paired_statistics", "sources": sources, "conditions": conditions}
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output.with_suffix(".md"), payload)
    print(json.dumps({"output": str(output), "conditions": sorted(conditions)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
