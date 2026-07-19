"""Merge disjoint interaction-semantic audit shards."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_interaction_semantic_eval import summarize_condition_results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    pair_judges: list[dict[str, Any]] = []
    for report_path in args.input:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for row in report.get("records") or []:
            key = (str(row.get("condition") or ""), str(row.get("case_id") or ""))
            if not all(key):
                continue
            if key in by_key:
                raise ValueError(f"Duplicate audit record: {key}")
            by_key[key] = row
        pair_judges.extend(report.get("pair_judges") or [])

    records = sorted(by_key.values(), key=lambda row: (str(row["case_id"]), str(row["condition"])))
    merged = {
        "kind": "interaction_semantic_eval_report",
        "created_at": datetime.now().astimezone().isoformat(),
        "summary": summarize_condition_results(records),
        "records": records,
        "pair_judges": pair_judges,
        "merged_shards": [str(item) for item in args.input],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(records), "summary": merged["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
