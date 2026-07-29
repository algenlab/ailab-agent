"""Reclassify fault injection by semantic intent and test preserving mutations."""

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

from algolab.schemas.validation import BuildArtifact
from algolab.verification.scene_validator import validate_scene
from algolab.verification.result_normalizer import results_equivalent


SEMANTIC_VIOLATION_FAULTS = {
    "expected_result_wrong",
    "solve_result_wrong",
    "trace_result_wrong",
    "trace_input_wrong",
    "trace_events_empty",
    "trace_event_reordered",
    "trace_state_wrong",
    "trace_target_missing",
    "interaction_answer_wrong",
    "scene_objects_empty",
    "scene_reference_missing",
}


def expected_mutation_is_equivalent(
    original: Any,
    mutated: Any,
    *,
    case_id: str,
    family_id: str,
    subfamily_id: str,
) -> bool:
    return results_equivalent(
        original,
        mutated,
        case_id=case_id,
        family_id=family_id,
        subfamily_id=subfamily_id,
    )


def summarize_semantic_mutations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("mutation_class") or "unknown")].append(row)
    summary: dict[str, Any] = {}
    for mutation_class, items in sorted(grouped.items()):
        total = len(items)
        accepted = sum(row.get("accepted") is True for row in items)
        rejected = total - accepted
        summary[mutation_class] = {
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": accepted / total if total else 0.0,
            "rejection_rate": rejected / total if total else 0.0,
        }
    return summary


def _validate_scene_only(artifact: dict[str, Any]) -> tuple[bool, list[str]]:
    try:
        parsed = BuildArtifact.model_validate(artifact)
    except Exception as exc:
        return False, [f"schema: {type(exc).__name__}: {exc}"]
    errors: list[str] = []
    for scene in parsed.scenes.values():
        scene_errors, _warnings = validate_scene(scene)
        errors.extend(scene_errors)
    return not errors, errors


def preserving_mutation_rows(artifact_path: Path, *, case_id: str) -> list[dict[str, Any]]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

    teaching = copy.deepcopy(artifact)
    teaching_changed = False
    for scene in (teaching.get("scenes") or {}).values():
        for frame in scene.get("frames") or []:
            if isinstance(frame.get("teaching"), dict):
                frame["teaching"]["what"] = "语义保持的替代教学文案"
                teaching_changed = True
                break
        if teaching_changed:
            break
    accepted, errors = _validate_scene_only(teaching)
    rows.append(
        {
            "case_id": case_id,
            "mutation_type": "teaching_text_rewrite",
            "mutation_class": "semantics_preserving",
            "applicable": teaching_changed,
            "accepted": accepted if teaching_changed else None,
            "errors": errors,
        }
    )

    layout = copy.deepcopy(artifact)
    layout_changed = False
    for scene in (layout.get("scenes") or {}).values():
        for frame in scene.get("frames") or []:
            objects = frame.get("objects") or []
            if objects:
                objects[0].setdefault("meta", {})["experiment_layout_note"] = "visual-only"
                layout_changed = True
                break
        if layout_changed:
            break
    accepted, errors = _validate_scene_only(layout)
    rows.append(
        {
            "case_id": case_id,
            "mutation_type": "visual_metadata_change",
            "mutation_class": "semantics_preserving",
            "applicable": layout_changed,
            "accepted": accepted if layout_changed else None,
            "errors": errors,
        }
    )
    return rows


def build_report(fault_report: Path, artifact_dir: Path, *, max_artifacts: int = 0) -> dict[str, Any]:
    source = json.loads(fault_report.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for row in source.get("results") or []:
        fault_type = str(row.get("fault_type") or "")
        if fault_type not in SEMANTIC_VIOLATION_FAULTS:
            continue
        mutation_class = "semantic_violation"
        mutation_type = fault_type
        if fault_type == "expected_result_wrong" and row.get("rejected") is not True:
            source_path = ROOT / str(row.get("source_artifact") or "")
            mutated_path = ROOT / str(row.get("mutated_artifact") or "")
            if source_path.exists() and mutated_path.exists():
                original = json.loads(source_path.read_text(encoding="utf-8"))
                mutated = json.loads(mutated_path.read_text(encoding="utf-8"))
                if expected_mutation_is_equivalent(
                    original.get("expected_result"),
                    mutated.get("expected_result"),
                    case_id=str(row.get("case_id") or ""),
                    family_id=str(row.get("family_id") or ""),
                    subfamily_id=str(row.get("subfamily_id") or ""),
                ):
                    mutation_class = "semantics_preserving"
                    mutation_type = "expected_result_equivalent_reordering"
        rows.append(
            {
                "case_id": row.get("case_id"),
                "mutation_type": mutation_type,
                "source_fault_type": fault_type,
                "mutation_class": mutation_class,
                "accepted": row.get("rejected") is not True,
                "validation_layer": row.get("validation_layer"),
                "errors": row.get("errors") or [],
            }
        )

    artifacts = sorted(path for path in artifact_dir.glob("*.json") if path.name.startswith("llm_"))
    if max_artifacts > 0:
        artifacts = artifacts[:max_artifacts]
    for path in artifacts:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("schema_version") != "algolab-build-v1":
            continue
        case_id = path.stem.removeprefix("llm_").removesuffix("_0")
        rows.extend(preserving_mutation_rows(path, case_id=case_id))
    effective_rows = [row for row in rows if row.get("applicable") is not False]
    return {
        "kind": "semantic_mutation_analysis",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "fault_report": str(fault_report),
        "artifact_dir": str(artifact_dir),
        "excluded_ambiguous_faults": ["trace_event_deleted"],
        "summary": summarize_semantic_mutations(effective_rows),
        "results": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fault-report", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--max-artifacts", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    args = parse_args()
    report = build_report(
        _repo_path(args.fault_report),
        _repo_path(args.artifact_dir),
        max_artifacts=args.max_artifacts,
    )
    output = _repo_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
