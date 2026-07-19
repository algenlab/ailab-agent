"""Compute cumulative and conditional survival for nested page contracts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CONTRACTS = [
    ("C1_answer", ("visible_answer_match",)),
    ("C2_load", ("page_load_ok",)),
    ("C3_interaction", ("interaction_reachable",)),
    ("C4_bidirectional_feedback", ("correct_feedback_ok", "wrong_feedback_ok")),
    ("C5_teaching_support", ("hint_ok", "show_answer_ok", "learning_log_ok")),
    ("C6_noninterference", ("mutation_free_ok",)),
]


def summarize_condition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    surviving = list(rows)
    contracts: list[dict[str, Any]] = []
    conditional_product = 1.0
    previous_count = total
    for name, fields in CONTRACTS:
        surviving = [row for row in surviving if all(row.get(field) is True for field in fields)]
        passed = len(surviving)
        conditional = passed / previous_count if previous_count else 0.0
        conditional_product *= conditional
        contracts.append(
            {
                "name": name,
                "fields": list(fields),
                "passed": passed,
                "total": total,
                "cumulative_rate": passed / total if total else 0.0,
                "conditional_survival": conditional,
            }
        )
        previous_count = passed
    return {
        "total": total,
        "contracts": contracts,
        "product_of_conditional_survival": conditional_product,
        "final_joint_rate": contracts[-1]["cumulative_rate"] if contracts else 0.0,
    }


def _load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("records") or data.get("results") or []
    return [row for row in rows if isinstance(row, dict)]


def analyze_reports(report_specs: list[str]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources: list[dict[str, str]] = []
    for spec in report_specs:
        alias, separator, raw_path = spec.partition("=")
        path = Path(raw_path if separator else alias)
        if not path.is_absolute():
            path = ROOT / path
        rows = _load_rows(path)
        if separator:
            grouped[alias].extend(rows)
        else:
            for row in rows:
                grouped[str(row.get("condition") or path.parent.name)].append(row)
        sources.append({"alias": alias if separator else "from_condition", "path": str(path)})
    return {
        "kind": "nested_contract_survival_report",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "contracts": [{"name": name, "fields": list(fields)} for name, fields in CONTRACTS],
        "sources": sources,
        "methods": {name: summarize_condition(rows) for name, rows in sorted(grouped.items())},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, help="PATH or METHOD=PATH")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = analyze_reports(args.report)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"methods": len(report["methods"]), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
