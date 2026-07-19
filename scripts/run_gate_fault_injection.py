"""Evaluate gate soundness with controlled artifact fault injection."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.replay_llm_specs import replay_artifact_file
from algolab.schemas.validation import BuildArtifact
from algolab.verification.scene_validator import validate_scene


DEFAULT_FAULTS = [
    "expected_result_wrong",
    "solve_result_wrong",
    "trace_result_wrong",
    "trace_input_wrong",
    "trace_events_empty",
    "trace_event_deleted",
    "trace_event_reordered",
    "trace_state_wrong",
    "trace_target_missing",
    "interaction_answer_wrong",
    "scene_objects_empty",
    "scene_reference_missing",
]

FAULT_VALIDATION_LAYERS = {
    "expected_result_wrong": "result_consistency",
    "solve_result_wrong": "solve_result",
    "trace_result_wrong": "trace_result",
    "trace_input_wrong": "trace_input",
    "trace_events_empty": "trace_structure",
    "trace_event_deleted": "process_completeness",
    "trace_event_reordered": "process_order",
    "trace_state_wrong": "trace_state",
    "trace_target_missing": "target_reference",
    "interaction_answer_wrong": "interaction_oracle",
    "scene_objects_empty": "scene_structure",
    "scene_reference_missing": "scene_reference",
}


def wrong_value(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int) and not isinstance(value, bool):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    if isinstance(value, str):
        return value + "__fault"
    if isinstance(value, list):
        return list(reversed(value)) if len(value) > 1 else [*value, "__fault"]
    if isinstance(value, dict):
        mutated = dict(value)
        mutated["__fault"] = True
        return mutated
    if value is None:
        return "__fault"
    return "__fault"


def _append_solve_wrapper(code: str) -> str:
    return (
        str(code or "")
        + "\n\n_algolab_original_solve_for_fault = solve\n"
        + "def solve(input_data):\n"
        + "    return '__algolab_fault_wrong_result__'\n"
    )


def _append_trace_wrapper(code: str, fault_type: str) -> str:
    body = [
        str(code or ""),
        "",
        "_algolab_original_trace_for_fault = trace",
        "def trace(input_data):",
        "    t = _algolab_original_trace_for_fault(input_data)",
    ]
    if fault_type == "trace_result_wrong":
        body.append("    t['result'] = '__algolab_fault_wrong_result__'")
    elif fault_type == "trace_input_wrong":
        body.append("    t['input_data'] = {'__fault': True}")
    elif fault_type == "trace_events_empty":
        body.append("    t['events'] = []")
    elif fault_type == "trace_event_deleted":
        body.append("    t['events'] = t.get('events', [])[1:]")
        body.append("    for i, event in enumerate(t['events']): event['step'] = i")
    elif fault_type == "trace_event_reordered":
        body.append("    events = t.get('events', [])")
        body.append("    events.reverse()")
        body.append("    for i, event in enumerate(events): event['step'] = i")
    elif fault_type == "trace_state_wrong":
        body.append("    events = t.get('events', [])")
        body.append("    if events: events[0].setdefault('state', {})['__algolab_fault_state__'] = True")
    elif fault_type == "interaction_answer_wrong":
        body.append("    for event in t.get('events', []):")
        body.append("        if event.get('interaction') is not None:")
        body.append("            event['interaction']['answer'] = '__algolab_fault_answer__'")
        body.append("            break")
    elif fault_type == "trace_target_missing":
        body.append("    events = t.get('events', [])")
        body.append("    if events: events[-1]['targets'] = [{'id': '__algolab_missing__[999999]'}]")
    else:
        body.append("    t['__fault'] = True")
    body.append("    return t")
    return "\n".join(body) + "\n"


def inject_fault(artifact: dict[str, Any], fault_type: str) -> dict[str, Any]:
    """Return a mutated artifact with a controlled negative fault."""

    data = copy.deepcopy(artifact)
    if fault_type == "clean_control":
        return data
    if fault_type == "expected_result_wrong":
        data["expected_result"] = wrong_value(data.get("expected_result"))
        return data
    if fault_type in {"scene_objects_empty", "scene_reference_missing"}:
        scenes = data.get("scenes") or {}
        if not scenes:
            raise ValueError("artifact has no scenes to mutate")
        scene = next(iter(scenes.values()))
        frames = scene.get("frames") or []
        if not frames:
            raise ValueError("artifact scene has no frames to mutate")
        if fault_type == "scene_objects_empty":
            frames[0]["objects"] = []
        else:
            frames[0].setdefault("marks", []).append(
                {"target": "__algolab_missing_scene_object__", "role": "current", "label": "fault"}
            )
        return data

    variants = data.get("variants") or []
    if not variants:
        raise ValueError("artifact has no variants to mutate")
    variant = variants[0]
    if fault_type == "solve_result_wrong":
        variant["code"] = _append_solve_wrapper(str(variant.get("code") or ""))
    elif fault_type in {
        "trace_result_wrong",
        "trace_input_wrong",
        "trace_events_empty",
        "trace_event_deleted",
        "trace_event_reordered",
            "trace_state_wrong",
            "trace_target_missing",
            "interaction_answer_wrong",
    }:
        variant["tracker_code"] = _append_trace_wrapper(str(variant.get("tracker_code") or ""), fault_type)
    else:
        raise ValueError(f"unknown fault_type: {fault_type}")
    data["variants"] = variants
    return data


def summarize_fault_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
        injected = len(items)
        rejected = sum(1 for item in items if item.get("rejected") is True)
        false_accepted = injected - rejected
        return {
            "injected": injected,
            "rejected": rejected,
            "false_accepted": false_accepted,
            "rejection_rate": rejected / injected if injected else 0.0,
            "false_accept_rate": false_accepted / injected if injected else 0.0,
        }

    fault_rows = [row for row in rows if not row.get("is_control")]
    control_rows = [row for row in rows if row.get("is_control")]
    by_fault: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_validation_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in fault_rows:
        by_fault[str(row.get("fault_type") or "")].append(row)
        by_case[str(row.get("case_id") or "")].append(row)
        by_family[str(row.get("family_id") or "unknown")].append(row)
        by_validation_layer[str(row.get("validation_layer") or "unknown")].append(row)
    return {
        "overall": summarize(fault_rows),
        "controls": {
            "total": len(control_rows),
            "accepted": sum(row.get("rejected") is False for row in control_rows),
            "false_rejected": sum(row.get("rejected") is True for row in control_rows),
            "false_reject_rate": (
                sum(row.get("rejected") is True for row in control_rows) / len(control_rows)
                if control_rows
                else 0.0
            ),
        },
        "by_fault_type": {key: summarize(items) for key, items in sorted(by_fault.items())},
        "by_case": {key: summarize(items) for key, items in sorted(by_case.items())},
        "by_family": {key: summarize(items) for key, items in sorted(by_family.items())},
        "by_validation_layer": {
            key: summarize(items) for key, items in sorted(by_validation_layer.items())
        },
    }


def _repo_path(path: Path | str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _load_report_artifacts(report_path: Path, *, cases: set[str], max_cases: int) -> list[dict[str, Any]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = []
    for item in report.get("results") or []:
        case_id = str(item.get("case_id") or "")
        json_path = str(item.get("json") or "")
        if not case_id or not json_path:
            continue
        if cases and case_id not in cases:
            continue
        rows.append(
            {
                "case_id": case_id,
                "family_id": str(item.get("family_id") or ""),
                "subfamily_id": str(item.get("subfamily_id") or ""),
                "artifact_path": _repo_path(json_path),
                "source_report": str(report_path.relative_to(ROOT) if report_path.is_absolute() else report_path),
            }
        )
        if max_cases > 0 and len(rows) >= max_cases:
            break
    return rows


def run_fault_injection(
    *,
    report_path: Path,
    output_dir: Path,
    faults: list[str],
    cases: set[str],
    max_cases: int,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    fault_dir = output_dir / "fault_artifacts"
    fault_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    artifacts = _load_report_artifacts(report_path, cases=cases, max_cases=max_cases)
    for source in artifacts:
        original = json.loads(source["artifact_path"].read_text(encoding="utf-8"))
        for fault_type in ["clean_control", *faults]:
            row = {
                "case_id": source["case_id"],
                "fault_type": fault_type,
                "is_control": fault_type == "clean_control",
                "source_artifact": str(source["artifact_path"].relative_to(ROOT)),
                "family_id": source["family_id"],
                "subfamily_id": source["subfamily_id"],
                "validation_layer": "clean_control" if fault_type == "clean_control" else FAULT_VALIDATION_LAYERS[fault_type],
            }
            try:
                mutated = inject_fault(original, fault_type)
                mutated_path = fault_dir / f"{source['case_id']}_{fault_type}.json"
                mutated_path.write_text(json.dumps(mutated, ensure_ascii=False, indent=2), encoding="utf-8")
                if fault_type in {"scene_objects_empty", "scene_reference_missing"}:
                    parsed = BuildArtifact.model_validate(mutated)
                    scene_errors = []
                    scene_warnings = []
                    for scene in parsed.scenes.values():
                        errors, warnings = validate_scene(scene)
                        scene_errors.extend(errors)
                        scene_warnings.extend(warnings)
                    replay = {"ok": not scene_errors, "errors": scene_errors, "warnings": scene_warnings}
                else:
                    replay = replay_artifact_file(
                        mutated_path,
                        case_id=source["case_id"],
                        family_id=source["family_id"],
                        subfamily_id=source["subfamily_id"],
                    )
                row.update(
                    {
                        "mutated_artifact": str(mutated_path.relative_to(ROOT)),
                        "replay_ok": bool(replay.get("ok")),
                        "rejected": not bool(replay.get("ok")),
                        "errors": replay.get("errors") or [],
                        "warnings": replay.get("warnings") or [],
                    }
                )
            except Exception as exc:
                row.update(
                    {
                        "replay_ok": False,
                        "rejected": True,
                        "errors": [f"{type(exc).__name__}: {exc}"],
                        "warnings": [],
                    }
                )
            rows.append(row)
    summary = summarize_fault_rows(rows)
    report = {
        "kind": "gate_fault_injection_report",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "source_report": str(report_path.relative_to(ROOT) if report_path.is_absolute() else report_path),
        "fault_types": faults,
        "clean_controls": True,
        "summary": summary,
        "results": rows,
    }
    (output_dir / "gate_fault_injection_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(report, output_dir / "gate_fault_injection_report.md")
    return report


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    overall = report["summary"]["overall"]
    lines = [
        "# Gate Fault Injection Report",
        "",
        f"- created_at: `{report['created_at']}`",
        f"- source_report: `{report['source_report']}`",
        f"- injected: {overall['injected']}",
        f"- rejected: {overall['rejected']}",
        f"- false_accepted: {overall['false_accepted']}",
        f"- rejection_rate: {overall['rejection_rate']:.2%}",
        f"- clean_controls: {report['summary']['controls']['total']}",
        f"- clean_control_false_reject_rate: {report['summary']['controls']['false_reject_rate']:.2%}",
        "",
        "## By Fault Type",
        "",
        "| Fault Type | Injected | Rejected | False Accepted | Rejection Rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for fault_type, item in report["summary"]["by_fault_type"].items():
        lines.append(
            f"| {fault_type} | {item['injected']} | {item['rejected']} | "
            f"{item['false_accepted']} | {item['rejection_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## By Validation Layer",
            "",
            "| Layer | Injected | Rejected | False Accepted | Rejection Rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for layer, item in report["summary"]["by_validation_layer"].items():
        lines.append(
            f"| {layer} | {item['injected']} | {item['rejected']} | "
            f"{item['false_accepted']} | {item['rejection_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## By Family",
            "",
            "| Family | Injected | Rejected | False Accepted | Rejection Rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for family, item in report["summary"]["by_family"].items():
        lines.append(
            f"| {family} | {item['injected']} | {item['rejected']} | "
            f"{item['false_accepted']} | {item['rejection_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## False Accepted Cases",
            "",
            "| Case | Fault Type | Artifact |",
            "|---|---|---|",
        ]
    )
    false_rows = [row for row in report["results"] if not row.get("rejected")]
    if false_rows:
        for row in false_rows:
            lines.append(f"| {row.get('case_id')} | {row.get('fault_type')} | `{row.get('mutated_artifact')}` |")
    else:
        lines.append("| none | none | none |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fault", action="append", default=[])
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_fault_injection(
        report_path=_repo_path(args.input_report),
        output_dir=_repo_path(args.output_dir),
        faults=args.fault or DEFAULT_FAULTS,
        cases=set(args.case),
        max_cases=int(args.max_cases or 0),
    )
    overall = report["summary"]["overall"]
    print(
        json.dumps(
            {
                "injected": overall["injected"],
                "rejected": overall["rejected"],
                "false_accepted": overall["false_accepted"],
                "rejection_rate": overall["rejection_rate"],
                "report": str((_repo_path(args.output_dir) / "gate_fault_injection_report.json").relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
