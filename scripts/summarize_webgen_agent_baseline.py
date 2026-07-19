#!/usr/bin/env python3
"""Finalize WebGen-Agent generation and machine-audit reports."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_interaction_semantic_eval import MACHINE_BOOL_KEYS


MANIFEST = ROOT / "benchmark/external_baseline_all200_sample0.json"
RUN = ROOT / "output/external_baselines/webgen/logs/WebGenAgent_external_baseline_all200_sample0_webgen_DeepSeek-V4-Pro_iter5_all200_sample0_budget5"
AUDIT = ROOT / "output/external_baselines/webgen/audit_all200_sample0"


def summarize(rows: list[dict]) -> dict:
    summary = {"total": len(rows)}
    for key in ["machine_ok", *MACHINE_BOOL_KEYS]:
        count = sum(row.get(key) is True for row in rows)
        summary[key] = count
        summary[f"{key}_rate"] = round(count / len(rows), 4) if rows else 0.0
    return summary


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = {row["case_id"]: row for row in manifest["cases"]}
    generation = [json.loads(line) for line in (RUN / "output.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    generation_ids = {row["id"] for row in generation}
    audit_rows = [json.loads(line) for line in (AUDIT / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    audit_by_id = {row["case_id"]: row for row in audit_rows}
    for case_id, case in cases.items():
        if case_id not in audit_by_id:
            audit_by_id[case_id] = {
                "condition": "webgen_agent",
                **case,
                **{key: False for key in MACHINE_BOOL_KEYS},
                "machine_ok": False,
                "console_page_errors": ["audit_timeout: exceeded 300 seconds after an earlier 600-second timeout"],
            }
    rows = [audit_by_id[case_id] for case_id in cases]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["gate_layer"]].append(row)
    report = {
        "schema_version": "webgen-agent-baseline-report-v1",
        "method": {
            "name": "WebGen-Agent (budget-controlled)",
            "upstream_commit": "3e3fad05e99ca523bb45aea19427c99be27b5f80",
            "model": "DeepSeek-V4-Pro",
            "vlm_model": "gemini-3-flash-preview",
            "feedback_model": "DeepSeek-V4-Pro",
            "max_iter": 5,
            "concurrency": 8,
        },
        "dataset": {
            "source_cases": 200,
            "source_samples": 646,
            "evaluated_cases": 200,
            "sample_selection": "sample index 0 for every case",
        },
        "generation": {
            "successful": len(generation_ids),
            "missing": sorted(set(cases) - generation_ids),
            "success_rate": round(len(generation_ids) / len(cases), 4),
        },
        "machine_audit": {
            "overall": summarize(rows),
            "by_gate_layer": {key: summarize(value) for key, value in sorted(grouped.items())},
            "audit_timeout_cases": [row["case_id"] for row in rows if any("audit_timeout" in e for e in row.get("console_page_errors", []))],
        },
        "results": rows,
    }
    AUDIT.mkdir(parents=True, exist_ok=True)
    (AUDIT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    overall = report["machine_audit"]["overall"]
    lines = [
        "# WebGen-Agent External Baseline Report",
        "",
        "## Protocol",
        "",
        "- Scope: all 200 benchmark cases, using sample 0 from each case (200/646 samples).",
        "- Upstream: WebGen-Agent commit `3e3fad05e99ca523bb45aea19427c99be27b5f80`.",
        "- Budget-controlled setting: 5 agent iterations, 8 concurrent workers.",
        "- Models: DeepSeek-V4-Pro for coding/feedback; gemini-3-flash-preview for visual feedback.",
        "- Audit: black-box browser execution using the same nine machine metric semantics.",
        "",
        "## Results",
        "",
        f"- Generation success: {report['generation']['successful']}/200 ({report['generation']['success_rate']:.1%}).",
        f"- Machine OK: {overall['machine_ok']}/200 ({overall['machine_ok_rate']:.1%}).",
        "",
        "| Metric | Passed | Rate |",
        "|---|---:|---:|",
    ]
    labels = {
        "page_load_ok": "Page load",
        "visible_answer_match": "Visible answer match",
        "interaction_reachable": "Interaction reachable",
        "correct_feedback_ok": "Correct feedback",
        "wrong_feedback_ok": "Wrong feedback",
        "hint_ok": "Hint",
        "show_answer_ok": "Show answer",
        "learning_log_ok": "Learning log",
        "mutation_free_ok": "Mutation-free",
    }
    for key in MACHINE_BOOL_KEYS:
        lines.append(f"| {labels[key]} | {overall[key]}/200 | {overall[key + '_rate']:.1%} |")
    lines.extend(["", "## Stratified Results", "", "| Layer | N | Machine OK | Rate |", "|---|---:|---:|---:|"])
    for layer, item in report["machine_audit"]["by_gate_layer"].items():
        lines.append(f"| {layer} | {item['total']} | {item['machine_ok']} | {item['machine_ok_rate']:.1%} |")
    lines.extend([
        "",
        "## Run Notes",
        "",
        "- One upstream GUI-instruction parsing failure (`None + str`) interrupted the initial batch; completed records were preserved and missing cases were retried unchanged.",
        "- Disk exhaustion occurred after npm dependencies accumulated. Only regenerable `node_modules` and invalid preliminary-run directories were removed; generated source, logs, screenshots, and selected nodes were preserved.",
        "- `tarjan_scc` exceeded both 600-second and 300-second audit limits and is conservatively counted as a machine-audit failure.",
        "- This is the 200-case, one-sample-per-case result. It is not a 646-sample result.",
    ])
    (AUDIT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"generation": report["generation"], "machine_audit": report["machine_audit"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
