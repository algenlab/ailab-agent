"""Analyze two-human calibration labels for the black-box machine evaluator."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


METRICS = (
    "page_load_ok",
    "visible_answer_match",
    "interaction_reachable",
    "correct_feedback_ok",
    "wrong_feedback_ok",
    "hint_ok",
    "show_answer_ok",
    "learning_log_ok",
    "mutation_free_ok",
)


def confusion_metrics(machine: Iterable[bool], human: Iterable[bool]) -> dict[str, Any]:
    pairs = list(zip(machine, human))
    tp = sum(bool(pred) and bool(truth) for pred, truth in pairs)
    fp = sum(bool(pred) and not bool(truth) for pred, truth in pairs)
    fn = sum(not bool(pred) and bool(truth) for pred, truth in pairs)
    tn = sum(not bool(pred) and not bool(truth) for pred, truth in pairs)
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None:
        f1 = _ratio(2 * precision * recall, precision + recall)
    return {
        "n": len(pairs),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": _ratio(fp, fp + tn),
        "false_negative_rate": _ratio(fn, fn + tp),
        "accuracy": _ratio(tp + tn, len(pairs)),
    }


def cohen_kappa(labels_a: Iterable[bool], labels_b: Iterable[bool]) -> float | None:
    pairs = list(zip(labels_a, labels_b))
    if not pairs:
        return None
    observed = sum(a == b for a, b in pairs) / len(pairs)
    a_pos = sum(bool(a) for a, _ in pairs) / len(pairs)
    b_pos = sum(bool(b) for _, b in pairs) / len(pairs)
    expected = a_pos * b_pos + (1 - a_pos) * (1 - b_pos)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return round((observed - expected) / (1 - expected), 12)


def analyze_rows(
    *,
    key_rows: list[dict[str, Any]],
    annotator_a: list[dict[str, Any]],
    annotator_b: list[dict[str, Any]],
) -> dict[str, Any]:
    key = {str(row["blind_id"]): row for row in key_rows}
    rows_a = {str(row.get("blind_id") or ""): row for row in annotator_a}
    rows_b = {str(row.get("blind_id") or ""): row for row in annotator_b}
    metric_reports: dict[str, Any] = {}
    disagreements: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    complete_machine_ok: list[tuple[dict[str, Any], bool]] = []

    for metric in (*METRICS, "human_machine_ok"):
        labels_a: list[bool] = []
        labels_b: list[bool] = []
        predictions: list[bool] = []
        truths: list[bool] = []
        by_method: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
        for blind_id, key_row in key.items():
            value_a = _label_for_metric(rows_a.get(blind_id, {}), metric)
            value_b = _label_for_metric(rows_b.get(blind_id, {}), metric)
            if value_a is None or value_b is None:
                if metric == "human_machine_ok":
                    missing.append({"blind_id": blind_id, "metric": metric})
                continue
            labels_a.append(value_a)
            labels_b.append(value_b)
            if value_a != value_b:
                if metric == "human_machine_ok":
                    disagreements.append({"blind_id": blind_id, "metric": metric})
                continue
            machine_key = "machine_ok" if metric == "human_machine_ok" else metric
            prediction = bool(key_row.get(machine_key))
            predictions.append(prediction)
            truths.append(value_a)
            by_method[str(key_row.get("method") or "unknown")].append((prediction, value_a))
            if metric == "human_machine_ok":
                complete_machine_ok.append((key_row, value_a))
        metric_reports[metric] = {
            "double_labeled": len(labels_a),
            "agreed_truth": len(truths),
            "inter_rater_agreement": _ratio(sum(a == b for a, b in zip(labels_a, labels_b)), len(labels_a)),
            "cohen_kappa": cohen_kappa(labels_a, labels_b),
            "overall": confusion_metrics(predictions, truths),
            "by_method": {
                method: confusion_metrics(
                    [prediction for prediction, _truth in pairs],
                    [truth for _prediction, truth in pairs],
                )
                for method, pairs in sorted(by_method.items())
            },
        }

    all_double_labeled = metric_reports["human_machine_ok"]["double_labeled"] == len(key)
    status = "complete"
    if not all_double_labeled:
        status = "pending_human_labels"
    elif disagreements:
        status = "pending_adjudication"
    return {
        "kind": "machine_evaluator_human_calibration",
        "status": status,
        "expected_pages": len(key),
        "complete_pairs": metric_reports["human_machine_ok"]["agreed_truth"],
        "missing": missing,
        "disagreements": disagreements,
        "metrics": metric_reports,
    }


def _label_for_metric(row: dict[str, Any], metric: str) -> bool | None:
    if metric == "human_machine_ok":
        explicit = _parse_bool(row.get(metric))
        if explicit is not None:
            return explicit
        values = [_parse_bool(row.get(name)) for name in METRICS]
        if any(value is None for value in values):
            return None
        return all(bool(value) for value in values)
    return _parse_bool(row.get(metric))


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "pass", "通过"}:
        return True
    if text in {"0", "false", "no", "n", "fail", "不通过"}:
        return False
    return None


def _ratio(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator, 12) if denominator else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--annotator-a", type=Path, required=True)
    parser.add_argument("--annotator-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    key_data = json.loads(args.key.read_text(encoding="utf-8"))
    result = analyze_rows(
        key_rows=list(key_data.get("pages") or key_data),
        annotator_a=_read_csv(args.annotator_a),
        annotator_b=_read_csv(args.annotator_b),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
