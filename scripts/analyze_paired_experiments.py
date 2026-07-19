"""Paired statistical analysis for machine, visual, and teaching outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest, rankdata, wilcoxon

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_STAGE2_VISUAL = ROOT / "output/experiments/algotutorgen_full_200_20260706/stage2_eval/stage2_visual_eval_report.json"
DEFAULT_DIRECT_VISUAL = ROOT / "output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/visual_baseline_eval_report.json"
DEFAULT_EXTERNAL_REVIEW = ROOT / "output/experiments/algotutorgen_full_200_20260706/external_eval_methods/external_eval_methods_report.json"

MACHINE_METRICS = [
    "machine_ok",
    "page_load_ok",
    "visible_answer_match",
    "interaction_reachable",
    "correct_feedback_ok",
    "wrong_feedback_ok",
    "hint_ok",
    "show_answer_ok",
    "learning_log_ok",
    "mutation_free_ok",
]
VISUAL_METRICS = [
    "problem_visual_alignment",
    "algorithm_state_readability",
    "process_transition_clarity",
    "instructional_visual_design",
]
LORI_MERLOT_METRICS = [
    "content_quality",
    "learning_goal_alignment",
    "feedback_adaptation",
    "interaction_usability",
    "presentation_design",
    "teaching_effectiveness",
    "ease_of_use",
]


def exact_mcnemar(a_only: int, b_only: int) -> float:
    discordant = int(a_only) + int(b_only)
    if discordant == 0:
        return 1.0
    return float(binomtest(min(a_only, b_only), discordant, 0.5, alternative="two-sided").pvalue)


def paired_binary_summary(
    a: list[bool],
    b: list[bool],
    *,
    seed: int = 20260713,
    draws: int = 10000,
) -> dict[str, Any]:
    if len(a) != len(b):
        raise ValueError("paired vectors must have equal length")
    a_values = np.asarray(a, dtype=np.int8)
    b_values = np.asarray(b, dtype=np.int8)
    diffs = a_values - b_values
    rng = np.random.default_rng(seed)
    if len(diffs):
        indices = rng.integers(0, len(diffs), size=(draws, len(diffs)))
        boot = diffs[indices].mean(axis=1)
        low, high = np.quantile(boot, [0.025, 0.975]).tolist()
    else:
        low = high = 0.0
    a_only = int(np.sum((a_values == 1) & (b_values == 0)))
    b_only = int(np.sum((a_values == 0) & (b_values == 1)))
    return {
        "pairs": len(a),
        "a_pass": int(a_values.sum()),
        "b_pass": int(b_values.sum()),
        "difference": float(diffs.mean()) if len(diffs) else 0.0,
        "bootstrap_ci_95": [float(low), float(high)],
        "a_only": a_only,
        "b_only": b_only,
        "mcnemar_exact_p": exact_mcnemar(a_only, b_only),
    }


def paired_ordinal_summary(a: list[float], b: list[float]) -> dict[str, Any]:
    if len(a) != len(b):
        raise ValueError("paired vectors must have equal length")
    diffs = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    nonzero = diffs[diffs != 0]
    if len(nonzero):
        test = wilcoxon(diffs, zero_method="wilcox", alternative="two-sided")
        ranks = rankdata(np.abs(nonzero), method="average")
        positive_ranks = float(np.sum(ranks[nonzero > 0]))
        negative_ranks = float(np.sum(ranks[nonzero < 0]))
        rank_biserial = (positive_ranks - negative_ranks) / (positive_ranks + negative_ranks)
        pvalue = float(test.pvalue)
    else:
        positive_ranks = negative_ranks = 0.0
        rank_biserial = 0.0
        pvalue = 1.0
    return {
        "pairs": len(a),
        "a_mean": float(np.mean(a)) if a else None,
        "b_mean": float(np.mean(b)) if b else None,
        "mean_difference": float(np.mean(diffs)) if len(diffs) else 0.0,
        "median_difference": float(np.median(diffs)) if len(diffs) else 0.0,
        "nonzero_pairs": int(len(nonzero)),
        "positive_rank_sum": positive_ranks,
        "negative_rank_sum": negative_ranks,
        "wilcoxon_p": pvalue,
        "matched_pairs_rank_biserial": float(rank_biserial),
    }


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, value * (total - index)))
        adjusted[name] = running
    return adjusted


def index_unique_rows(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{label}: missing case_id")
        if case_id in indexed:
            raise ValueError(f"{label}: duplicate case_id {case_id}")
        indexed[case_id] = row
    return indexed


def require_same_pairs(
    left: dict[str, dict[str, Any]],
    right: dict[str, dict[str, Any]],
    *,
    label: str,
    expected_pairs: int | None = 200,
) -> list[str]:
    left_ids = set(left)
    right_ids = set(right)
    if left_ids != right_ids:
        missing_left = sorted(right_ids - left_ids)
        missing_right = sorted(left_ids - right_ids)
        raise ValueError(
            f"{label}: unmatched case IDs; missing_left={missing_left[:10]} missing_right={missing_right[:10]}"
        )
    if expected_pairs is not None and len(left_ids) != expected_pairs:
        raise ValueError(f"{label}: expected {expected_pairs} pairs, found {len(left_ids)}")
    return sorted(left_ids)


def _path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _add_holm(results: dict[str, dict[str, Any]], p_key: str) -> None:
    adjusted = holm_adjust({name: float(item[p_key]) for name, item in results.items()})
    for name, value in adjusted.items():
        results[name]["holm_adjusted_p"] = value


def analyze_machine_conditions(
    report: dict[str, Any],
    *,
    left_condition: str,
    right_condition: str,
    expected_pairs: int | None = None,
    metrics: list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    by_condition: dict[str, list[dict[str, Any]]] = {}
    for row in report.get("records") or []:
        by_condition.setdefault(str(row.get("condition") or ""), []).append(row)
    left = index_unique_rows(by_condition.get(left_condition, []), label=f"machine {left_condition}")
    right = index_unique_rows(by_condition.get(right_condition, []), label=f"machine {right_condition}")
    case_ids = require_same_pairs(left, right, label="machine", expected_pairs=expected_pairs)
    results = {
        metric: paired_binary_summary(
            [left[case_id].get(metric) is True for case_id in case_ids],
            [right[case_id].get(metric) is True for case_id in case_ids],
        )
        for metric in (metrics or MACHINE_METRICS)
    }
    _add_holm(results, "mcnemar_exact_p")
    return results, case_ids


def analyze_machine(report: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    return analyze_machine_conditions(
        report,
        left_condition="algolab_full",
        right_condition="direct_html",
        expected_pairs=200,
    )


def build_machine_pair_payload(
    report: dict[str, Any],
    *,
    source: str,
    left_condition: str,
    right_condition: str,
    expected_pairs: int | None = None,
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    results, case_ids = analyze_machine_conditions(
        report,
        left_condition=left_condition,
        right_condition=right_condition,
        expected_pairs=expected_pairs,
        metrics=metrics,
    )
    return {
        "kind": "paired_machine_statistics",
        "source": source,
        "conditions": {"left": left_condition, "right": right_condition},
        "pair_completeness": len(case_ids),
        "case_ids": case_ids,
        "machine_boolean": results,
    }


def analyze_visual(stage2: dict[str, Any], direct: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    left = index_unique_rows(stage2.get("external_visual_results") or [], label="stage2 visual")
    right = index_unique_rows(direct.get("visual_results") or [], label="direct visual")
    case_ids = require_same_pairs(left, right, label="visual")
    results = {}
    for metric in VISUAL_METRICS:
        a = [float(left[case_id]["scores"][metric]) for case_id in case_ids]
        b = [float(right[case_id]["scores"][metric]) for case_id in case_ids]
        results[metric] = paired_ordinal_summary(a, b)
    _add_holm(results, "wilcoxon_p")
    return results, case_ids


def analyze_lori_merlot(report: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    reviews = index_unique_rows(report.get("pair_reviews") or [], label="LORI/MERLOT")
    if len(reviews) != 200:
        raise ValueError(f"LORI/MERLOT: expected 200 pairs, found {len(reviews)}")
    case_ids = sorted(reviews)
    results = {}
    for metric in LORI_MERLOT_METRICS:
        a = [float(reviews[case_id]["conditions"]["algolab_full"]["scores"][metric]) for case_id in case_ids]
        b = [float(reviews[case_id]["conditions"]["direct_html"]["scores"][metric]) for case_id in case_ids]
        results[metric] = paired_ordinal_summary(a, b)
    _add_holm(results, "wilcoxon_p")
    return results, case_ids


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Paired Experiment Statistics",
        "",
        "All analyses use the same 200 case IDs within each comparison.",
        "",
        "## Machine Metrics",
        "",
        "| Metric | AlgoTutorGen | Direct | Difference | 95% bootstrap CI | McNemar p | Holm p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for metric, row in payload["machine_boolean"].items():
        ci = row["bootstrap_ci_95"]
        lines.append(
            f"| {metric} | {row['a_pass']}/200 | {row['b_pass']}/200 | {row['difference']:.4f} | "
            f"[{ci[0]:.4f}, {ci[1]:.4f}] | {row['mcnemar_exact_p']:.6g} | {row['holm_adjusted_p']:.6g} |"
        )
    for title, key, a_name, b_name in [
        ("Visual Metrics", "visual_ordinal", "Stage2", "Direct"),
        ("LORI/MERLOT Metrics", "lori_merlot_ordinal", "AlgoTutorGen", "Direct"),
    ]:
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                f"| Metric | {a_name} mean | {b_name} mean | Mean diff | Wilcoxon p | Holm p | Rank-biserial |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for metric, row in payload[key].items():
            lines.append(
                f"| {metric} | {row['a_mean']:.4f} | {row['b_mean']:.4f} | {row['mean_difference']:.4f} | "
                f"{row['wilcoxon_p']:.6g} | {row['holm_adjusted_p']:.6g} | "
                f"{row['matched_pairs_rank_biserial']:.4f} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, payload: dict[str, Any]) -> None:
    fields = [
        "section", "metric", "pairs", "a_value", "b_value", "difference", "ci_low", "ci_high",
        "raw_p", "holm_adjusted_p", "effect_size",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for metric, row in payload["machine_boolean"].items():
            writer.writerow(
                {
                    "section": "machine_boolean",
                    "metric": metric,
                    "pairs": row["pairs"],
                    "a_value": row["a_pass"],
                    "b_value": row["b_pass"],
                    "difference": row["difference"],
                    "ci_low": row["bootstrap_ci_95"][0],
                    "ci_high": row["bootstrap_ci_95"][1],
                    "raw_p": row["mcnemar_exact_p"],
                    "holm_adjusted_p": row["holm_adjusted_p"],
                    "effect_size": "",
                }
            )
        for section in ("visual_ordinal", "lori_merlot_ordinal"):
            for metric, row in payload[section].items():
                writer.writerow(
                    {
                        "section": section,
                        "metric": metric,
                        "pairs": row["pairs"],
                        "a_value": row["a_mean"],
                        "b_value": row["b_mean"],
                        "difference": row["mean_difference"],
                        "ci_low": "",
                        "ci_high": "",
                        "raw_p": row["wilcoxon_p"],
                        "holm_adjusted_p": row["holm_adjusted_p"],
                        "effect_size": row["matched_pairs_rank_biserial"],
                    }
                )


def write_machine_pair_markdown(path: Path, payload: dict[str, Any]) -> None:
    left = payload["conditions"]["left"]
    right = payload["conditions"]["right"]
    pairs = int(payload["pair_completeness"])
    lines = [
        "# Paired Machine Statistics",
        "",
        f"Paired cases: `{pairs}`. Left: `{left}`. Right: `{right}`.",
        "",
        f"| Metric | {left} | {right} | Difference | 95% bootstrap CI | McNemar p | Holm p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for metric, row in payload["machine_boolean"].items():
        ci = row["bootstrap_ci_95"]
        lines.append(
            f"| {metric} | {row['a_pass']}/{pairs} | {row['b_pass']}/{pairs} | {row['difference']:.4f} | "
            f"[{ci[0]:.4f}, {ci[1]:.4f}] | {row['mcnemar_exact_p']:.6g} | {row['holm_adjusted_p']:.6g} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_machine_pair_csv(path: Path, payload: dict[str, Any]) -> None:
    fields = [
        "left_condition", "right_condition", "metric", "pairs", "left_pass", "right_pass",
        "difference", "ci_low", "ci_high", "mcnemar_exact_p", "holm_adjusted_p", "left_only", "right_only",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for metric, row in payload["machine_boolean"].items():
            writer.writerow(
                {
                    "left_condition": payload["conditions"]["left"],
                    "right_condition": payload["conditions"]["right"],
                    "metric": metric,
                    "pairs": row["pairs"],
                    "left_pass": row["a_pass"],
                    "right_pass": row["b_pass"],
                    "difference": row["difference"],
                    "ci_low": row["bootstrap_ci_95"][0],
                    "ci_high": row["bootstrap_ci_95"][1],
                    "mcnemar_exact_p": row["mcnemar_exact_p"],
                    "holm_adjusted_p": row["holm_adjusted_p"],
                    "left_only": row["a_only"],
                    "right_only": row["b_only"],
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine-report", type=Path, required=True)
    parser.add_argument("--stage2-visual-report", type=Path, default=DEFAULT_STAGE2_VISUAL)
    parser.add_argument("--direct-visual-report", type=Path, default=DEFAULT_DIRECT_VISUAL)
    parser.add_argument("--external-review-report", type=Path, default=DEFAULT_EXTERNAL_REVIEW)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--machine-only", action="store_true")
    parser.add_argument("--left-condition", default="algolab_full")
    parser.add_argument("--right-condition", default="direct_html")
    parser.add_argument("--expected-pairs", type=int, default=0)
    parser.add_argument("--metric", action="append", default=[])
    args = parser.parse_args()

    machine_path = _path(args.machine_report)
    output = _path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if args.machine_only:
        payload = build_machine_pair_payload(
            json.loads(machine_path.read_text(encoding="utf-8")),
            source=str(machine_path),
            left_condition=args.left_condition,
            right_condition=args.right_condition,
            expected_pairs=args.expected_pairs or None,
            metrics=args.metric or None,
        )
        (output / "paired_machine_statistics.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_machine_pair_markdown(output / "paired_machine_statistics.md", payload)
        write_machine_pair_csv(output / "paired_machine_statistics.csv", payload)
        print(json.dumps({"pairs": payload["pair_completeness"], "output": str(output)}, ensure_ascii=False))
        return 0

    stage2_path = _path(args.stage2_visual_report)
    direct_visual_path = _path(args.direct_visual_report)
    external_path = _path(args.external_review_report)
    machine_results, machine_ids = analyze_machine(json.loads(machine_path.read_text(encoding="utf-8")))
    visual_results, visual_ids = analyze_visual(
        json.loads(stage2_path.read_text(encoding="utf-8")),
        json.loads(direct_visual_path.read_text(encoding="utf-8")),
    )
    lori_results, lori_ids = analyze_lori_merlot(json.loads(external_path.read_text(encoding="utf-8")))
    payload = {
        "kind": "paired_experiment_statistics",
        "sources": {
            "machine": str(machine_path),
            "stage2_visual": str(stage2_path),
            "direct_visual": str(direct_visual_path),
            "external_review": str(external_path),
        },
        "pair_completeness": {
            "machine": len(machine_ids),
            "visual": len(visual_ids),
            "lori_merlot": len(lori_ids),
        },
        "machine_boolean": machine_results,
        "visual_ordinal": visual_results,
        "lori_merlot_ordinal": lori_results,
    }
    (output / "paired_statistics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output / "paired_statistics.md", payload)
    write_csv(output / "paired_statistics.csv", payload)
    print(json.dumps({"pairs": payload["pair_completeness"], "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
