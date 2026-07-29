"""Run the Plan-2 automatic source-to-trace audit and prepare human review."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REVIEW_LABELS = {
    "exact",
    "semantically_adjacent",
    "wrong",
    "no_source_counterpart",
}
STATE_MODIFICATION_OPS = {
    "append",
    "create",
    "dequeue",
    "enqueue",
    "insert",
    "move",
    "pop",
    "push",
    "relax",
    "remove",
    "set",
    "swap",
    "union",
    "update",
}
CONTROL_OPS = {
    "branch",
    "call",
    "compare",
    "enter",
    "exit",
    "loop",
    "return",
}


def return_line_numbers(source: str) -> list[int]:
    try:
        tree = ast.parse(source or "")
    except SyntaxError:
        return [
            index
            for index, line in enumerate((source or "").splitlines(), start=1)
            if re.match(r"^\s*return\b", line)
        ]
    return sorted({node.lineno for node in ast.walk(tree) if isinstance(node, ast.Return)})


def classify_answer_mapping(
    code_line: Any,
    return_lines: list[int],
    *,
    source_line_count: int,
) -> str:
    line = _as_positive_int(code_line)
    if line is None:
        return "missing_code_line"
    if line > source_line_count:
        return "out_of_range"
    if line in return_lines:
        return "exact_return"
    if any(abs(line - return_line) == 1 for return_line in return_lines):
        return "adjacent_return"
    return "other_source_line"


def audit_variant(
    *,
    case_id: str,
    family_id: str,
    variant_index: int,
    variant: dict[str, Any],
    scene: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = str(variant.get("code") or "")
    source_lines = source.splitlines()
    return_lines = return_line_numbers(source)
    trace = variant.get("trace") if isinstance(variant.get("trace"), dict) else {}
    events = list(trace.get("events") or [])
    scene_frames = list((scene or {}).get("frames") or [])
    variant_id = str(variant.get("id") or f"variant-{variant_index}")
    event_rows: list[dict[str, Any]] = []
    valid_line_counts: Counter[int] = Counter()
    answer_mapping_counts: Counter[str] = Counter()
    code_line_1_count = 0
    out_of_range_count = 0
    missing_code_line_count = 0

    for event_index, raw_event in enumerate(events):
        event = raw_event if isinstance(raw_event, dict) else {}
        scene_frame = scene_frames[event_index] if event_index < len(scene_frames) else {}
        line = _as_positive_int(event.get("code_line"))
        if line is None:
            missing_code_line_count += 1
        elif line <= len(source_lines):
            valid_line_counts[line] += 1
        else:
            out_of_range_count += 1
        if line == 1:
            code_line_1_count += 1
        is_answer = _is_answer_event(event, event_index=event_index, event_count=len(events))
        answer_mapping = (
            classify_answer_mapping(
                event.get("code_line"),
                return_lines,
                source_line_count=len(source_lines),
            )
            if is_answer
            else ""
        )
        if answer_mapping:
            answer_mapping_counts[answer_mapping] += 1
        risk_score, risk, risk_reasons = _event_risk(
            code_line=line,
            source_line_count=len(source_lines),
            is_answer=is_answer,
            answer_mapping=answer_mapping,
        )
        step = event.get("step", event_index)
        event_id = f"{case_id}:{variant_id}:{step}:{event_index}"
        event_rows.append(
            {
                "event_id": event_id,
                "case_id": case_id,
                "family_id": family_id,
                "variant_id": variant_id,
                "variant_index": variant_index,
                "event_index": event_index,
                "step": step,
                "op": str(event.get("op") or ""),
                "role": str(event.get("role") or ""),
                "reason": str(event.get("reason") or ""),
                "targets": event.get("targets") or [],
                "deps": event.get("deps") or [],
                "before": event.get("before"),
                "after": event.get("after"),
                "value": event.get("value"),
                "state": event.get("state") or {},
                "interaction": event.get("interaction") or scene_frame.get("interaction"),
                "code_line": line,
                "source_line": source_lines[line - 1] if line is not None and line <= len(source_lines) else "",
                "source_line_count": len(source_lines),
                "return_lines": return_lines,
                "is_answer": is_answer,
                "is_state_modification": _is_state_modification(event),
                "is_control": str(event.get("op") or "").lower() in CONTROL_OPS,
                "answer_mapping": answer_mapping,
                "risk_score": risk_score,
                "risk": risk,
                "risk_reasons": risk_reasons,
            }
        )

    dominant_line, dominant_count = (valid_line_counts.most_common(1)[0] if valid_line_counts else (None, 0))
    event_count = len(events)
    terminal_event = event_rows[-1] if event_rows else None
    summary = {
        "case_id": case_id,
        "family_id": family_id,
        "variant_id": variant_id,
        "variant_index": variant_index,
        "event_count": event_count,
        "source_line_count": len(source_lines),
        "return_lines": return_lines,
        "code_line_1_count": code_line_1_count,
        "code_line_1_rate": _ratio(code_line_1_count, event_count),
        "missing_code_line_count": missing_code_line_count,
        "out_of_range_count": out_of_range_count,
        "distinct_valid_code_lines": len(valid_line_counts),
        "dominant_line": dominant_line,
        "dominant_line_count": dominant_count,
        "dominant_line_rate": _ratio(dominant_count, event_count),
        "single_line_collapse": bool(event_count and len(valid_line_counts) == 1),
        "dominant_line_dominated_80pct": (
            _ratio(dominant_count, event_count) >= 0.8 if event_count else False
        ),
        "line_1_dominated_80pct": _ratio(code_line_1_count, event_count) >= 0.8 if event_count else False,
        "answer_event_count": sum(answer_mapping_counts.values()),
        "answer_mapping_counts": dict(sorted(answer_mapping_counts.items())),
        "terminal_source_mapping": (
            classify_answer_mapping(
                terminal_event.get("code_line"),
                return_lines,
                source_line_count=len(source_lines),
            )
            if terminal_event is not None
            else "missing_terminal_event"
        ),
        "terminal_has_explicit_answer": bool(terminal_event and terminal_event.get("is_answer")),
        "risk_score": max((row["risk_score"] for row in event_rows), default=0),
    }
    return event_rows, summary


def select_review_events(
    event_rows: list[dict[str, Any]],
    *,
    max_events: int = 4,
) -> list[dict[str, Any]]:
    if max_events <= 0 or not event_rows:
        return []
    selected: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any] | None, role: str) -> None:
        if row is None:
            return
        event_id = str(row.get("event_id") or "")
        if not event_id:
            return
        if event_id not in selected and len(selected) >= max_events:
            return
        item = selected.setdefault(event_id, {**row, "selection_roles": []})
        if role not in item["selection_roles"]:
            item["selection_roles"].append(role)

    answers = [row for row in event_rows if row.get("is_answer")]
    mutations = [row for row in event_rows if row.get("is_state_modification")]
    controls = [row for row in event_rows if row.get("is_control")]
    add(max(answers, key=_answer_review_key, default=None), "final_answer")
    add(max(mutations, key=_risk_review_key, default=None), "state_modification")
    add(max(controls, key=_risk_review_key, default=None), "control_event")
    add(max(event_rows, key=_risk_review_key, default=None), "highest_risk")
    for row in sorted(event_rows, key=_risk_review_key, reverse=True):
        if len(selected) >= max_events:
            break
        add(row, "risk_fill")
    return sorted(
        selected.values(),
        key=lambda row: (int(row.get("variant_index") or 0), int(row.get("event_index") or 0)),
    )


def select_review_cases(
    case_rows: list[dict[str, Any]],
    *,
    count: int,
    seed: int,
) -> list[dict[str, Any]]:
    if count > len(case_rows):
        raise ValueError(f"requested {count} cases from only {len(case_rows)}")
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        by_family[str(row.get("family_id") or "unknown")].append(row)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    family_order = sorted(
        by_family,
        key=lambda family: (
            -max(float(row.get("risk_score") or 0) for row in by_family[family]),
            _seeded_order(seed, family),
        ),
    )
    for family in family_order[:count]:
        chosen = max(
            by_family[family],
            key=lambda row: (
                float(row.get("risk_score") or 0),
                _seeded_order(seed, str(row.get("case_id") or "")),
            ),
        )
        selected.append(chosen)
        selected_ids.add(str(chosen.get("case_id") or ""))
    remaining = [row for row in case_rows if str(row.get("case_id") or "") not in selected_ids]
    remaining.sort(
        key=lambda row: (
            -float(row.get("risk_score") or 0),
            _seeded_order(seed, str(row.get("case_id") or "")),
        )
    )
    selected.extend(remaining[: max(0, count - len(selected))])
    return sorted(selected, key=lambda row: str(row.get("case_id") or ""))


def review_status(
    reviewer_a: list[dict[str, Any]],
    reviewer_b: list[dict[str, Any]],
    *,
    expected_ids: set[str],
) -> str:
    rows_a = _review_map(reviewer_a)
    rows_b = _review_map(reviewer_b)
    for rows in (rows_a, rows_b):
        for event_id, label in rows.items():
            if label and label not in REVIEW_LABELS:
                raise ValueError(f"invalid review label for {event_id}: {label}")
    if any(not rows_a.get(event_id) or not rows_b.get(event_id) for event_id in expected_ids):
        return "pending_human_labels"
    if any(rows_a[event_id] != rows_b[event_id] for event_id in expected_ids):
        return "pending_adjudication"
    return "complete"


def run_audit(
    *,
    report_path: Path,
    output_dir: Path,
    review_count: int,
    seed: int,
) -> dict[str, Any]:
    report_path = _repo_path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    all_events: list[dict[str, Any]] = []
    variant_rows: list[dict[str, Any]] = []
    events_by_case_variant: dict[tuple[str, str], list[dict[str, Any]]] = {}
    review_cases: dict[str, dict[str, Any]] = {}
    review_variants: dict[tuple[str, str], dict[str, Any]] = {}
    report_rows = [row for row in report.get("results") or [] if row.get("case_id") and row.get("json")]

    for report_row in report_rows:
        case_id = str(report_row.get("case_id") or "")
        family_id = str(report_row.get("family_id") or "unknown")
        artifact_path = _repo_path(Path(str(report_row.get("json") or "")))
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        review_cases[case_id] = {
            "problem_title": artifact.get("problem_title", report_row.get("title")),
            "input_data": artifact.get("input_data", report_row.get("input_data")),
            "expected_result": artifact.get("expected_result", report_row.get("expected")),
            "verifier_result": artifact.get("verifier_result"),
        }
        for variant_index, variant in enumerate(artifact.get("variants") or []):
            if not isinstance(variant, dict):
                continue
            event_rows, variant_summary = audit_variant(
                case_id=case_id,
                family_id=family_id,
                variant_index=variant_index,
                variant=variant,
                scene=(artifact.get("scenes") or {}).get(str(variant.get("id") or "")),
            )
            variant_summary["artifact"] = str(artifact_path)
            all_events.extend(event_rows)
            variant_rows.append(variant_summary)
            events_by_case_variant[(case_id, variant_summary["variant_id"])] = event_rows
            review_variants[(case_id, variant_summary["variant_id"])] = {
                "name": variant.get("name"),
                "strategy": variant.get("strategy"),
                "result": variant.get("result"),
                "source_lines": [
                    {"line_number": line_number, "text": text}
                    for line_number, text in enumerate(str(variant.get("code") or "").splitlines(), start=1)
                ],
            }

    case_rows = _aggregate_cases(variant_rows)
    _write_jsonl(output_dir / "source_trace_auto_events.jsonl", all_events)
    _write_csv(output_dir / "source_trace_auto_variants.csv", variant_rows)
    _write_csv(output_dir / "source_trace_auto_cases.csv", case_rows)
    selected_cases = select_review_cases(case_rows, count=review_count, seed=seed)
    public_selected_cases = [
        {**row, **review_cases.get(str(row.get("case_id") or ""), {})}
        for row in selected_cases
    ]
    public_variant_rows = [
        {
            **row,
            **review_variants.get(
                (str(row.get("case_id") or ""), str(row.get("variant_id") or "")),
                {},
            ),
        }
        for row in variant_rows
    ]
    review_manifest = _write_review_package(
        output_dir=output_dir / "human_review",
        selected_cases=public_selected_cases,
        variant_rows=public_variant_rows,
        events_by_case_variant=events_by_case_variant,
        seed=seed,
    )
    answer_counts: Counter[str] = Counter()
    for row in variant_rows:
        answer_counts.update(row.get("answer_mapping_counts") or {})
    answer_total = sum(answer_counts.values())
    exact_adjacent = answer_counts["exact_return"] + answer_counts["adjacent_return"]
    summary = {
        "kind": "plan2_source_to_trace_automatic_audit",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "status": "automatic_complete_human_pending",
        "input_report": str(report_path),
        "input_report_sha256": _file_sha256(report_path),
        "case_count": len(case_rows),
        "family_count": len({row["family_id"] for row in case_rows}),
        "variant_count": len(variant_rows),
        "event_count": len(all_events),
        "interaction_event_count": sum(isinstance(row.get("interaction"), dict) for row in all_events),
        "code_line_1_count": sum(int(row.get("code_line_1_count") or 0) for row in variant_rows),
        "code_line_1_rate": _ratio(
            sum(int(row.get("code_line_1_count") or 0) for row in variant_rows),
            len(all_events),
        ),
        "single_line_collapse_variants": sum(bool(row.get("single_line_collapse")) for row in variant_rows),
        "dominant_line_dominated_80pct_variants": sum(
            bool(row.get("dominant_line_dominated_80pct")) for row in variant_rows
        ),
        "line_1_dominated_80pct_variants": sum(bool(row.get("line_1_dominated_80pct")) for row in variant_rows),
        "out_of_range_events": sum(int(row.get("out_of_range_count") or 0) for row in variant_rows),
        "missing_code_line_events": sum(int(row.get("missing_code_line_count") or 0) for row in variant_rows),
        "answer_mapping_counts": dict(sorted(answer_counts.items())),
        "automatic_exact_plus_adjacent_rate": _ratio(exact_adjacent, answer_total),
        "terminal_source_mapping_counts": dict(
            sorted(Counter(str(row.get("terminal_source_mapping") or "") for row in variant_rows).items())
        ),
        "terminal_explicit_answer_variants": sum(
            bool(row.get("terminal_has_explicit_answer")) for row in variant_rows
        ),
        "automatic_result_boundary": (
            "The exact+adjacent rate is a source-line risk diagnostic, not a human correctness rate. "
            "Strong source-aligned claims remain blocked until the two-reviewer package is labeled and adjudicated."
        ),
        "human_review": review_manifest,
        "outputs": {
            "events": "source_trace_auto_events.jsonl",
            "variants": "source_trace_auto_variants.csv",
            "cases": "source_trace_auto_cases.csv",
            "review_package": "human_review",
        },
    }
    (output_dir / "source_trace_auto_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def _is_answer_event(event: dict[str, Any], *, event_index: int, event_count: int) -> bool:
    if str(event.get("role") or "").lower() == "answer":
        return True
    target_ids = {
        str(item.get("id") or "").lower()
        for item in event.get("targets") or []
        if isinstance(item, dict)
    }
    if "answer" in target_ids or any(target.endswith(":answer") for target in target_ids):
        return True
    return event_index == event_count - 1 and str(event.get("op") or "").lower() in {"return", "result"}


def _is_state_modification(event: dict[str, Any]) -> bool:
    op = str(event.get("op") or "").lower()
    return op in STATE_MODIFICATION_OPS or event.get("before") != event.get("after")


def _event_risk(
    *,
    code_line: int | None,
    source_line_count: int,
    is_answer: bool,
    answer_mapping: str,
) -> tuple[int, str, list[str]]:
    score = 0
    reasons: list[str] = []
    if code_line is None:
        score = max(score, 80)
        reasons.append("missing_code_line")
    elif code_line > source_line_count:
        score = max(score, 100)
        reasons.append("out_of_range")
    elif code_line == 1:
        score = max(score, 40)
        reasons.append("code_line_1")
    if is_answer:
        if answer_mapping == "other_source_line":
            score = max(score, 70)
            reasons.append("answer_not_near_return")
        elif answer_mapping in {"out_of_range", "missing_code_line"}:
            score = max(score, 100)
            reasons.append("answer_has_invalid_source_line")
        elif answer_mapping == "adjacent_return":
            score = max(score, 10)
            reasons.append("answer_adjacent_to_return")
    risk = "critical" if score >= 90 else "high" if score >= 60 else "medium" if score >= 30 else "low"
    return score, risk, reasons


def _aggregate_cases(variant_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in variant_rows:
        grouped[str(row["case_id"])].append(row)
    result = []
    for case_id, rows in sorted(grouped.items()):
        event_count = sum(int(row.get("event_count") or 0) for row in rows)
        line1_count = sum(int(row.get("code_line_1_count") or 0) for row in rows)
        result.append(
            {
                "case_id": case_id,
                "family_id": str(rows[0].get("family_id") or "unknown"),
                "variant_count": len(rows),
                "event_count": event_count,
                "code_line_1_count": line1_count,
                "code_line_1_rate": _ratio(line1_count, event_count),
                "single_line_collapse_variants": sum(bool(row.get("single_line_collapse")) for row in rows),
                "dominant_line_dominated_80pct_variants": sum(
                    bool(row.get("dominant_line_dominated_80pct")) for row in rows
                ),
                "line_1_dominated_80pct_variants": sum(bool(row.get("line_1_dominated_80pct")) for row in rows),
                "out_of_range_count": sum(int(row.get("out_of_range_count") or 0) for row in rows),
                "risk_score": max(float(row.get("risk_score") or 0) for row in rows),
            }
        )
    return result


def _write_review_package(
    *,
    output_dir: Path,
    selected_cases: list[dict[str, Any]],
    variant_rows: list[dict[str, Any]],
    events_by_case_variant: dict[tuple[str, str], list[dict[str, Any]]],
    seed: int,
) -> dict[str, Any]:
    variants_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in variant_rows:
        variants_by_case[str(row["case_id"])].append(row)
    existing_manifest = _compatible_existing_review_package(
        output_dir=output_dir,
        selected_cases=selected_cases,
        variants_by_case=variants_by_case,
        events_by_case_variant=events_by_case_variant,
        seed=seed,
    )
    if existing_manifest is not None:
        return existing_manifest

    output_dir.mkdir(parents=True, exist_ok=True)
    items_dir = output_dir / "items"
    items_dir.mkdir(exist_ok=True)
    key_rows: list[dict[str, Any]] = []
    annotation_rows: list[dict[str, Any]] = []
    for case in selected_cases:
        case_id = str(case["case_id"])
        audit_id = "TRACE-" + hashlib.sha256(f"{seed}:{case_id}".encode()).hexdigest()[:12].upper()
        item_variants = []
        for variant in sorted(variants_by_case[case_id], key=lambda row: int(row.get("variant_index") or 0)):
            variant_id = str(variant["variant_id"])
            variant_events = events_by_case_variant[(case_id, variant_id)]
            selected_events = select_review_events(variant_events, max_events=4)
            item_variants.append(
                {
                    "variant_id": variant_id,
                    "variant_index": variant["variant_index"],
                    "name": variant.get("name"),
                    "strategy": variant.get("strategy"),
                    "result": variant.get("result"),
                    "source_line_count": variant["source_line_count"],
                    "source_lines": variant.get("source_lines") or [],
                    "selected_events": [
                        _public_review_event(event, variant_events=variant_events)
                        for event in selected_events
                    ],
                }
            )
            for event in selected_events:
                annotation_rows.append(
                    {
                        "audit_id": audit_id,
                        "event_id": event["event_id"],
                        "case_id": case_id,
                        "family_id": case["family_id"],
                        "variant_id": variant_id,
                        "event_index": event["event_index"],
                        "step": event["step"],
                        "op": event["op"],
                        "role": event["role"],
                        "reason": event["reason"],
                        "code_line": event["code_line"],
                        "source_line": event["source_line"],
                        "label": "",
                        "critical_error": "",
                        "notes": "",
                    }
                )
        item_path = items_dir / f"{audit_id}.json"
        item_path.write_text(
            json.dumps(
                {
                    "audit_id": audit_id,
                    "case_id": case_id,
                    "family_id": case["family_id"],
                    "problem_title": case.get("problem_title"),
                    "input_data": case.get("input_data"),
                    "expected_result": case.get("expected_result"),
                    "verifier_result": case.get("verifier_result"),
                    "variants": item_variants,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        key_rows.append(
            {
                "audit_id": audit_id,
                "case_id": case_id,
                "family_id": case["family_id"],
                "item": str(item_path.relative_to(output_dir)),
            }
        )
    reviewer_a_rows = [dict(row) for row in annotation_rows]
    reviewer_b_rows = [dict(row) for row in annotation_rows]
    random.Random(seed + 1).shuffle(reviewer_a_rows)
    random.Random(seed + 2).shuffle(reviewer_b_rows)
    if len(reviewer_b_rows) > 1 and [row["event_id"] for row in reviewer_a_rows] == [
        row["event_id"] for row in reviewer_b_rows
    ]:
        reviewer_b_rows = reviewer_b_rows[1:] + reviewer_b_rows[:1]
    _write_csv(output_dir / "reviewer_a.csv", reviewer_a_rows)
    _write_csv(output_dir / "reviewer_b.csv", reviewer_b_rows)
    (output_dir / "private_review_key.json").write_text(
        json.dumps({"items": key_rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "kind": "plan2_source_to_trace_human_review",
        "status": "pending_human_labels",
        "human_labels_present": False,
        "reviewers_required": 2,
        "case_count": len(selected_cases),
        "family_count": len({row["family_id"] for row in selected_cases}),
        "variant_count": sum(len(variants_by_case[str(row["case_id"])]) for row in selected_cases),
        "event_count": len(annotation_rows),
        "allowed_labels": sorted(REVIEW_LABELS),
        "seed": seed,
    }
    (output_dir / "package_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Plan-2 Source-to-Trace 双评审包",
                "",
                "- 当前状态：`pending_human_labels`",
                f"- 题目数：{manifest['case_count']}；算法族数：{manifest['family_count']}",
                f"- 待标事件：{manifest['event_count']}（抽中题目的所有 variant，每个 variant 最多 4 个关键事件）",
                "",
                "每个 item 提供题目输入、期望结果、实际结果、带行号的完整 solve 源码，以及待标事件的前后事件摘要。",
                "事件中的 code_line 是当前待评映射行；两份 CSV 已使用不同的确定性随机顺序。",
                "",
                "两位评审者分别填写 reviewer_a.csv 和 reviewer_b.csv。label 只能填写：",
                "`exact`、`semantically_adjacent`、`wrong`、`no_source_counterpart`。",
                "critical_error 填 1/0，表示该映射错误是否会改变算法事实或教学结论。",
                "不得使用模型自动补标签；分歧需人工裁决。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def _compatible_existing_review_package(
    *,
    output_dir: Path,
    selected_cases: list[dict[str, Any]],
    variants_by_case: dict[str, list[dict[str, Any]]],
    events_by_case_variant: dict[tuple[str, str], list[dict[str, Any]]],
    seed: int,
) -> dict[str, Any] | None:
    manifest_path = output_dir / "package_manifest.json"
    key_path = output_dir / "private_review_key.json"
    reviewer_a_path = output_dir / "reviewer_a.csv"
    reviewer_b_path = output_dir / "reviewer_b.csv"
    item_paths = list((output_dir / "items").glob("*.json")) if (output_dir / "items").is_dir() else []
    core_paths = (manifest_path, key_path, reviewer_a_path, reviewer_b_path)
    if not any(path.exists() for path in core_paths) and not item_paths:
        return None
    if not all(path.is_file() for path in core_paths):
        raise FileExistsError(
            f"refusing to overwrite partial human review package: {output_dir}"
        )

    expected_case_ids = {str(row.get("case_id") or "") for row in selected_cases}
    expected_event_ids: set[str] = set()
    for case in selected_cases:
        case_id = str(case.get("case_id") or "")
        for variant in variants_by_case.get(case_id, []):
            variant_id = str(variant.get("variant_id") or "")
            for event in select_review_events(
                events_by_case_variant[(case_id, variant_id)],
                max_events=4,
            ):
                expected_event_ids.add(str(event.get("event_id") or ""))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key_data = json.loads(key_path.read_text(encoding="utf-8"))
    key_rows = list(key_data.get("items") or [])
    key_case_ids = {str(row.get("case_id") or "") for row in key_rows}
    reviewer_a = _read_csv_rows(reviewer_a_path)
    reviewer_b = _read_csv_rows(reviewer_b_path)
    ids_a = [str(row.get("event_id") or "") for row in reviewer_a]
    ids_b = [str(row.get("event_id") or "") for row in reviewer_b]
    referenced_items = [output_dir / str(row.get("item") or "") for row in key_rows]
    compatible = (
        manifest.get("kind") == "plan2_source_to_trace_human_review"
        and manifest.get("seed") == seed
        and manifest.get("case_count") == len(selected_cases)
        and manifest.get("event_count") == len(expected_event_ids)
        and key_case_ids == expected_case_ids
        and len(ids_a) == len(set(ids_a)) == len(expected_event_ids)
        and len(ids_b) == len(set(ids_b)) == len(expected_event_ids)
        and set(ids_a) == expected_event_ids
        and set(ids_b) == expected_event_ids
        and all(path.is_file() for path in referenced_items)
    )
    if not compatible:
        raise FileExistsError(
            f"refusing to overwrite existing human review package with a different protocol: {output_dir}"
        )
    return manifest


def analyze_human_reviews(
    reviewer_a: list[dict[str, Any]],
    reviewer_b: list[dict[str, Any]],
    *,
    expected_ids: set[str],
) -> dict[str, Any]:
    rows_a = _review_rows_by_id(reviewer_a, expected_ids=expected_ids, reviewer="reviewer_a")
    rows_b = _review_rows_by_id(reviewer_b, expected_ids=expected_ids, reviewer="reviewer_b")
    complete_a = sum(_complete_review_row(rows_a.get(event_id)) for event_id in expected_ids)
    complete_b = sum(_complete_review_row(rows_b.get(event_id)) for event_id in expected_ids)
    if complete_a != len(expected_ids) or complete_b != len(expected_ids):
        return {
            "kind": "plan2_source_to_trace_human_analysis",
            "status": "pending_human_labels",
            "expected_events": len(expected_ids),
            "complete_events": {"reviewer_a": complete_a, "reviewer_b": complete_b},
            "required": "two complete human label sheets; no model-generated labels",
        }

    labels_a = [str(rows_a[event_id]["label"]).strip() for event_id in sorted(expected_ids)]
    labels_b = [str(rows_b[event_id]["label"]).strip() for event_id in sorted(expected_ids)]
    critical_a = [_critical_flag(rows_a[event_id]["critical_error"]) for event_id in sorted(expected_ids)]
    critical_b = [_critical_flag(rows_b[event_id]["critical_error"]) for event_id in sorted(expected_ids)]
    label_agreement = _ratio(sum(a == b for a, b in zip(labels_a, labels_b)), len(labels_a))
    critical_agreement = _ratio(
        sum(a == b for a, b in zip(critical_a, critical_b)),
        len(critical_a),
    )
    inter_rater = {
        "n": len(labels_a),
        "label_exact_agreement": label_agreement,
        "label_cohens_kappa": _nominal_kappa(labels_a, labels_b),
        "critical_exact_agreement": critical_agreement,
        "critical_cohens_kappa": _nominal_kappa(critical_a, critical_b),
    }
    if labels_a != labels_b or critical_a != critical_b:
        return {
            "kind": "plan2_source_to_trace_human_analysis",
            "status": "pending_adjudication",
            "expected_events": len(expected_ids),
            "inter_rater": inter_rater,
            "disagreement_events": sum(
                labels_a[index] != labels_b[index]
                or critical_a[index] != critical_b[index]
                for index in range(len(labels_a))
            ),
        }

    label_counts = Counter(labels_a)
    aligned_count = label_counts["exact"] + label_counts["semantically_adjacent"]
    critical_count = sum(critical_a)
    aligned_rate = _ratio(aligned_count, len(labels_a))
    critical_rate = _ratio(critical_count, len(labels_a))
    aligned_ci = _wilson_interval(aligned_count, len(labels_a))
    return {
        "kind": "plan2_source_to_trace_human_analysis",
        "status": "complete",
        "event_count": len(labels_a),
        "label_counts": dict(sorted(label_counts.items())),
        "exact_plus_adjacent": {
            "count": aligned_count,
            "rate": aligned_rate,
            "wilson_ci_95": aligned_ci,
        },
        "critical_error": {
            "count": critical_count,
            "rate": critical_rate,
        },
        "inter_rater": inter_rater,
        "strong_claim_gate": {
            "exact_plus_adjacent_ci_lower_ge_0_90": aligned_ci[0] >= 0.90,
            "critical_error_rate_le_0_05": critical_rate <= 0.05,
            "passed": aligned_ci[0] >= 0.90 and critical_rate <= 0.05,
        },
    }


def _review_rows_by_id(
    rows: list[dict[str, Any]],
    *,
    expected_ids: set[str],
    reviewer: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        event_id = str(row.get("event_id") or "")
        if not event_id:
            continue
        if event_id in indexed:
            raise ValueError(f"{reviewer} contains duplicate event_id: {event_id}")
        if event_id not in expected_ids:
            raise ValueError(f"{reviewer} contains unexpected event_id: {event_id}")
        indexed[event_id] = row
    return indexed


def _complete_review_row(row: dict[str, Any] | None) -> bool:
    if row is None:
        return False
    label = str(row.get("label") or "").strip()
    if not label:
        return False
    if label not in REVIEW_LABELS:
        raise ValueError(f"invalid review label: {label}")
    try:
        _critical_flag(row.get("critical_error"))
    except ValueError:
        return False
    return True


def _critical_flag(value: Any) -> int:
    text = str(value or "").strip()
    if text not in {"0", "1"}:
        raise ValueError(f"critical_error must be 0 or 1, got {value!r}")
    return int(text)


def _wilson_interval(successes: int, total: int, *, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        return [0.0, 0.0]
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = z * (
        (proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5
    ) / denominator
    return [round(max(0.0, center - radius), 12), round(min(1.0, center + radius), 12)]


def _nominal_kappa(left: list[Any], right: list[Any]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    total = len(left)
    observed = sum(a == b for a, b in zip(left, right)) / total
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum(
        (left_counts[value] / total) * (right_counts[value] / total)
        for value in set(left_counts) | set(right_counts)
    )
    if expected == 1.0:
        return 1.0 if observed == 1.0 else None
    return round((observed - expected) / (1 - expected), 12)


def _public_review_event(
    event: dict[str, Any],
    *,
    variant_events: list[dict[str, Any]],
) -> dict[str, Any]:
    event_index = int(event.get("event_index") or 0)
    return {
        "event_id": event.get("event_id"),
        "event_index": event_index,
        "step": event.get("step"),
        "op": event.get("op"),
        "role": event.get("role"),
        "reason": event.get("reason"),
        "targets": event.get("targets") or [],
        "deps": event.get("deps") or [],
        "before": event.get("before"),
        "after": event.get("after"),
        "value": event.get("value"),
        "state": event.get("state") or {},
        "interaction": event.get("interaction"),
        "code_line": event.get("code_line"),
        "source_line": event.get("source_line"),
        "previous_event": (
            _public_event_summary(variant_events[event_index - 1]) if event_index > 0 else None
        ),
        "next_event": (
            _public_event_summary(variant_events[event_index + 1])
            if event_index + 1 < len(variant_events)
            else None
        ),
    }


def _public_event_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "event_index": event.get("event_index"),
        "step": event.get("step"),
        "op": event.get("op"),
        "role": event.get("role"),
        "reason": event.get("reason"),
        "targets": event.get("targets") or [],
        "before": event.get("before"),
        "after": event.get("after"),
        "value": event.get("value"),
        "interaction": event.get("interaction"),
        "code_line": event.get("code_line"),
        "source_line": event.get("source_line"),
    }


def _review_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    result = {}
    for row in rows:
        event_id = str(row.get("event_id") or "")
        if event_id:
            result[event_id] = str(row.get("label") or "").strip()
    return result


def _answer_review_key(row: dict[str, Any]) -> tuple[int, int]:
    return int(row.get("event_index") or 0), int(row.get("risk_score") or 0)


def _risk_review_key(row: dict[str, Any]) -> tuple[int, int]:
    return int(row.get("risk_score") or 0), int(row.get("event_index") or 0)


def _seeded_order(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def _as_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 1 else None


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 12) if denominator else 0.0


def _repo_path(path: Path) -> Path:
    if path.is_absolute():
        if path.exists():
            return path
        try:
            relative = path.relative_to("/work")
        except ValueError:
            return path
        return ROOT / relative
    return ROOT / path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["case_id"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fields})


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT
        / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--review-count", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--analyze-human", action="store_true")
    parser.add_argument("--reviewer-a", type=Path)
    parser.add_argument("--reviewer-b", type=Path)
    args = parser.parse_args()
    output_dir = _repo_path(args.output_dir)
    if args.analyze_human:
        review_dir = output_dir / "human_review"
        expected_ids = {
            str(event.get("event_id") or "")
            for item_path in (review_dir / "items").glob("*.json")
            for variant in json.loads(item_path.read_text(encoding="utf-8")).get("variants") or []
            for event in variant.get("selected_events") or []
            if str(event.get("event_id") or "")
        }
        result = analyze_human_reviews(
            _read_csv_rows(args.reviewer_a or review_dir / "reviewer_a.csv"),
            _read_csv_rows(args.reviewer_b or review_dir / "reviewer_b.csv"),
            expected_ids=expected_ids,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "source_trace_human_analysis.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") == "complete" else 2
    summary = run_audit(
        report_path=args.report,
        output_dir=output_dir,
        review_count=args.review_count,
        seed=args.seed,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
