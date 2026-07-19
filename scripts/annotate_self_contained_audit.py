"""Add self-contained compliance and strict joint pass to a machine audit."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_interaction_semantic_eval import summarize_condition_results
from scripts.run_direct_browser_repair_baseline import external_resource_urls


def _resource_urls(row: dict[str, Any]) -> list[str]:
    urls = set(row.get("observed_external_requests") or [])
    html_value = str(row.get("html") or "")
    html_path = Path(html_value)
    if html_value and not html_path.is_absolute():
        html_path = ROOT / html_path
    if html_path.is_file():
        urls.update(external_resource_urls(html_path.read_text(encoding="utf-8")))
    else:
        urls.update(row.get("external_resource_urls") or [])
    return sorted(urls)


def annotate_report(
    machine_report: dict[str, Any],
    method_report: dict[str, Any],
    *,
    method_condition: str,
) -> dict[str, Any]:
    method_rows: dict[str, dict[str, Any]] = {}
    for row in method_report.get("results") or []:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError("method report contains a row without case_id")
        if case_id in method_rows:
            raise ValueError(f"method report contains duplicate case_id: {case_id}")
        method_rows[case_id] = row

    records = copy.deepcopy(machine_report.get("records") or [])
    for record in records:
        case_id = str(record.get("case_id") or "")
        condition = str(record.get("condition") or "")
        if condition == method_condition:
            if case_id not in method_rows:
                raise ValueError(f"machine audit case missing from method report: {case_id}")
            urls = _resource_urls(method_rows[case_id])
        else:
            urls = _resource_urls(record)
        record["external_resource_urls"] = urls
        record["self_contained_ok"] = not urls
        record["strict_machine_ok"] = record.get("machine_ok") is True and not urls

    summary: dict[str, dict[str, Any]] = {}
    for condition in sorted({str(row.get("condition") or "") for row in records}):
        rows = [row for row in records if row.get("condition") == condition]
        total = len(rows)
        self_contained = sum(row.get("self_contained_ok") is True for row in rows)
        strict = sum(row.get("strict_machine_ok") is True for row in rows)
        summary[condition] = {
            "total": total,
            "self_contained_ok": self_contained,
            "self_contained_rate": self_contained / total if total else 0.0,
            "strict_machine_ok": strict,
            "strict_machine_ok_rate": strict / total if total else 0.0,
        }

    return {
        **{key: copy.deepcopy(value) for key, value in machine_report.items() if key not in {"records", "summary"}},
        "kind": "interaction_semantic_eval_report_with_self_contained",
        "summary": summarize_condition_results(records),
        "self_contained_summary": summary,
        "records": records,
        "self_contained_method_condition": method_condition,
    }


def _path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine-report", type=Path, required=True)
    parser.add_argument("--method-report", type=Path, required=True)
    parser.add_argument("--method-condition", default="direct_html")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    machine_path = _path(args.machine_report)
    method_path = _path(args.method_report)
    output = _path(args.output)
    payload = annotate_report(
        json.loads(machine_path.read_text(encoding="utf-8")),
        json.loads(method_path.read_text(encoding="utf-8")),
        method_condition=args.method_condition,
    )
    payload["self_contained_sources"] = {
        "machine_report": str(machine_path),
        "method_report": str(method_path),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["self_contained_summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
