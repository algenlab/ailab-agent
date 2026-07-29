"""Analyze independent two-reviewer semantic-trace correctness labels."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_evaluator_calibration import cohen_kappa


DIMENSIONS = (
    "result_correct",
    "state_transition_correct",
    "dependency_correct",
    "explanation_aligned",
    "critical_error",
)


def analyze_trace_rows(
    *,
    key_rows: list[dict[str, Any]],
    annotator_a: list[dict[str, Any]],
    annotator_b: list[dict[str, Any]],
) -> dict[str, Any]:
    key = {str(row["audit_id"]): row for row in key_rows}
    rows_a = {str(row.get("audit_id") or ""): row for row in annotator_a}
    rows_b = {str(row.get("audit_id") or ""): row for row in annotator_b}
    dimensions: dict[str, Any] = {}
    critical_agreed: list[tuple[dict[str, Any], bool]] = []
    missing_ids: set[str] = set()
    disagreement_ids: set[str] = set()

    for dimension in DIMENSIONS:
        labels_a: list[bool] = []
        labels_b: list[bool] = []
        agreed: list[tuple[dict[str, Any], bool]] = []
        for audit_id, key_row in key.items():
            value_a = _parse_bool(rows_a.get(audit_id, {}).get(dimension))
            value_b = _parse_bool(rows_b.get(audit_id, {}).get(dimension))
            if value_a is None or value_b is None:
                if dimension == "critical_error":
                    missing_ids.add(audit_id)
                continue
            labels_a.append(value_a)
            labels_b.append(value_b)
            if value_a == value_b:
                agreed.append((key_row, value_a))
            elif dimension == "critical_error":
                disagreement_ids.add(audit_id)
        by_family: dict[str, list[bool]] = defaultdict(list)
        for key_row, value in agreed:
            by_family[str(key_row.get("family_id") or "unknown")].append(value)
        dimensions[dimension] = {
            "double_labeled": len(labels_a),
            "agreed": len(agreed),
            "agreement_rate": _ratio(sum(a == b for a, b in zip(labels_a, labels_b)), len(labels_a)),
            "cohen_kappa": cohen_kappa(labels_a, labels_b),
            "positive_rate": _ratio(sum(value for _row, value in agreed), len(agreed)),
            "by_family": {
                family: {"n": len(values), "positive_rate": _ratio(sum(values), len(values))}
                for family, values in sorted(by_family.items())
            },
        }
        if dimension == "critical_error":
            critical_agreed = agreed

    status = "complete"
    if dimensions["critical_error"]["double_labeled"] != len(key):
        status = "pending_human_labels"
    elif disagreement_ids:
        status = "pending_adjudication"
    return {
        "kind": "independent_trace_correctness_audit",
        "status": status,
        "expected_cases": len(key),
        "agreed_cases": len(critical_agreed),
        "critical_semantic_error_rate": _ratio(
            sum(value for _row, value in critical_agreed), len(critical_agreed)
        ),
        "missing_audit_ids": sorted(missing_ids),
        "disagreement_audit_ids": sorted(disagreement_ids),
        "dimensions": dimensions,
    }


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "pass", "通过", "有"}:
        return True
    if text in {"0", "false", "no", "fail", "不通过", "无"}:
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
    result = analyze_trace_rows(
        key_rows=list(key_data.get("items") or key_data),
        annotator_a=_read_csv(args.annotator_a),
        annotator_b=_read_csv(args.annotator_b),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
