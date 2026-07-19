"""Compare anonymous review runs across models and blind orders."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_external_eval_methods import EXTERNAL_REVIEW_SCORE_KEYS


def _overall_score(review: dict[str, Any], condition: str) -> float | None:
    scores = ((review.get("conditions") or {}).get(condition) or {}).get("scores") or {}
    values = [float(value) for value in scores.values()]
    return sum(values) / len(values) if values else None


def _metric_score(review: dict[str, Any], condition: str, metric: str) -> float | None:
    value = ((((review.get("conditions") or {}).get(condition) or {}).get("scores") or {}).get(metric))
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def validate_review_report(report: dict[str, Any], *, label: str, expected_pairs: int = 200) -> None:
    seen: set[str] = set()
    for row in report.get("pair_reviews") or []:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{label}: missing case_id")
        if case_id in seen:
            raise ValueError(f"{label}: duplicate case_id {case_id}")
        seen.add(case_id)
    if len(seen) != expected_pairs:
        raise ValueError(f"{label}: expected {expected_pairs} pairs, found {len(seen)}")


def _spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2:
        return None
    value = float(spearmanr(left, right).statistic)
    return value if math.isfinite(value) else None


def _cohen_kappa(left: list[str], right: list[str]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    labels = sorted(set(left) | set(right))
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum((left_counts[label] / len(left)) * (right_counts[label] / len(right)) for label in labels)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def compare_review_sets(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    left = {str(row.get("case_id")): row for row in baseline.get("pair_reviews") or []}
    right = {str(row.get("case_id")): row for row in candidate.get("pair_reviews") or []}
    case_ids = sorted(set(left) & set(right))
    left_winners = [str(left[case_id].get("winner") or "tie") for case_id in case_ids]
    right_winners = [str(right[case_id].get("winner") or "tie") for case_id in case_ids]
    agreement = sum(a == b for a, b in zip(left_winners, right_winners)) / len(case_ids) if case_ids else 0.0
    correlations: dict[str, Any] = {}
    for condition in ("algolab_full", "direct_html"):
        pairs = [
            (_overall_score(left[case_id], condition), _overall_score(right[case_id], condition))
            for case_id in case_ids
        ]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        by_metric = {}
        for metric in EXTERNAL_REVIEW_SCORE_KEYS:
            metric_pairs = [
                (_metric_score(left[case_id], condition, metric), _metric_score(right[case_id], condition, metric))
                for case_id in case_ids
            ]
            metric_pairs = [(a, b) for a, b in metric_pairs if a is not None and b is not None]
            by_metric[metric] = _spearman(
                [a for a, _ in metric_pairs],
                [b for _, b in metric_pairs],
            )
        correlations[condition] = {
            "overall": _spearman([a for a, _ in pairs], [b for _, b in pairs]),
            "by_metric": by_metric,
        }
    return {
        "pairs": len(case_ids),
        "winner_agreement": agreement,
        "winner_flip_rate": 1.0 - agreement,
        "cohen_kappa": _cohen_kappa(left_winners, right_winners),
        "score_spearman": correlations,
        "disagreement_cases": [case_id for case_id in case_ids if left[case_id].get("winner") != right[case_id].get("winner")],
    }


def _report_label(path: Path, report: dict[str, Any]) -> str:
    execution = report.get("execution") or {}
    model = str(execution.get("model") or (report.get("llm") or {}).get("model") or path.parent.name)
    order = str(execution.get("blind_order") or "frozen")
    return f"{model}:{order}"


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Judge Robustness Report",
        "",
        "| Comparison | Pairs | Winner agreement | Flip rate | Cohen kappa | AlgoTutorGen score rho | Direct score rho |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in payload["comparisons"].items():
        algolab_rho = row["score_spearman"]["algolab_full"]["overall"]
        direct_rho = row["score_spearman"]["direct_html"]["overall"]
        lines.append(
            f"| {name} | {row['pairs']} | {row['winner_agreement']:.4f} | {row['winner_flip_rate']:.4f} | "
            f"{row['cohen_kappa']:.4f} | {algolab_rho} | {direct_rho} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline_path = args.baseline if args.baseline.is_absolute() else ROOT / args.baseline
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    reports: dict[str, tuple[Path, dict[str, Any]]] = {}
    baseline_label = _report_label(baseline_path, baseline)
    validate_review_report(baseline, label=baseline_label)
    reports[baseline_label] = (baseline_path, baseline)
    for raw_path in args.candidate:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        report = json.loads(path.read_text(encoding="utf-8"))
        label = _report_label(path, report)
        if label in reports:
            raise ValueError(f"duplicate report label: {label}")
        validate_review_report(report, label=label)
        reports[label] = (path, report)
    comparisons = {
        f"{left_label} vs {right_label}": compare_review_sets(left_report, right_report)
        for (left_label, (_, left_report)), (right_label, (_, right_report)) in combinations(reports.items(), 2)
    }
    payload = {
        "kind": "judge_robustness_report",
        "reports": {label: str(path) for label, (path, _) in reports.items()},
        "comparisons": comparisons,
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output.with_suffix(".md"), payload)
    print(json.dumps({"output": str(output), "comparisons": len(comparisons)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
