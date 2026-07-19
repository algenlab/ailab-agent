"""Audit Solver-Trace-SceneGraph state preservation and deterministic rendering."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.compiler.scene_compiler import compile_scene
from algolab.renderer.export import render_html
from algolab.runtime.executor import canonical
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.validation import BuildArtifact


def canonical_algorithm_state(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def state_hash(value: Any) -> str:
    return hashlib.sha256(canonical_algorithm_state(value).encode("utf-8")).hexdigest()


def compare_trace_scene(trace: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    events = trace.get("events") or []
    frames = scene.get("frames") or []
    equivalent = 0
    first_mismatch: dict[str, Any] | None = None
    total = max(len(events), len(frames))
    for index in range(total):
        event = events[index] if index < len(events) else None
        frame = frames[index] if index < len(frames) else None
        event_step = event.get("step") if isinstance(event, dict) else None
        frame_step = frame.get("step") if isinstance(frame, dict) else None
        trace_state = event.get("state") if isinstance(event, dict) else None
        scene_state = frame.get("state") if isinstance(frame, dict) else None
        ok = (
            event is not None
            and frame is not None
            and event_step == frame_step
            and canonical_algorithm_state(trace_state) == canonical_algorithm_state(scene_state)
        )
        if ok:
            equivalent += 1
        elif first_mismatch is None:
            first_mismatch = {
                "index": index,
                "step": event_step if event_step is not None else frame_step,
                "trace_step": event_step,
                "scene_step": frame_step,
                "trace_state_hash": state_hash(trace_state),
                "scene_state_hash": state_hash(scene_state),
            }
    return {
        "trace_frames": len(events),
        "scene_frames": len(frames),
        "total_compared_frames": total,
        "equivalent_frames": equivalent,
        "all_frames_equivalent": total == equivalent,
        "first_mismatch": first_mismatch,
    }


def _case_id(path: Path) -> str:
    name = path.stem
    if name.startswith("llm_"):
        name = name[4:]
    if name.endswith("_0"):
        name = name[:-2]
    return name


def audit_artifact_data(data: dict[str, Any], *, path: Path, dataset: str) -> dict[str, Any]:
    variants = data.get("variants") or []
    scenes = data.get("scenes") or {}
    variant_rows: list[dict[str, Any]] = []
    for variant in variants:
        variant_id = str(variant.get("id") or "")
        trace = variant.get("trace") or {}
        scene = scenes.get(variant_id) or {}
        preservation = compare_trace_scene(trace, scene)
        result_values = [variant.get("result"), trace.get("result"), scene.get("result")]
        expected = data.get("expected_result")
        if expected is not None:
            result_values.append(expected)
        solver_trace_result_ok = len({canonical(value) for value in result_values}) == 1
        input_ok = canonical(trace.get("input_data")) == canonical(data.get("input_data"))
        scene_input_ok = canonical(scene.get("input_data")) == canonical(trace.get("input_data"))
        variant_rows.append(
            {
                "variant_id": variant_id,
                "solver_trace_result_ok": solver_trace_result_ok,
                "trace_input_ok": input_ok,
                "scene_input_ok": scene_input_ok,
                **preservation,
            }
        )
    frames = sum(row["total_compared_frames"] for row in variant_rows)
    equivalent = sum(row["equivalent_frames"] for row in variant_rows)
    artifact_ok = bool(variant_rows) and all(
        row["solver_trace_result_ok"]
        and row["trace_input_ok"]
        and row["scene_input_ok"]
        and row["all_frames_equivalent"]
        for row in variant_rows
    )
    return {
        "dataset": dataset,
        "case_id": _case_id(path),
        "artifact": str(path),
        "streaming": False,
        "variant_count": len(variant_rows),
        "total_frames": frames,
        "equivalent_frames": equivalent,
        "frame_equivalence_rate": equivalent / frames if frames else 0.0,
        "artifact_ok": artifact_ok,
        "variants": variant_rows,
    }


def _stream_items(path: Path, prefix: str) -> Iterable[Any]:
    try:
        import ijson
    except ImportError as exc:
        raise RuntimeError("large-artifact streaming requires ijson") from exc
    with path.open("rb") as handle:
        yield from ijson.items(handle, prefix, use_float=True)


def audit_large_single_variant(path: Path, *, dataset: str) -> dict[str, Any]:
    variant_id = next(iter(_stream_items(path, "variants.item.id")), "")
    trace_rows: list[tuple[int, str]] = []
    for event in _stream_items(path, "variants.item.trace.events.item"):
        trace_rows.append((int(event.get("step", len(trace_rows))), state_hash(event.get("state"))))
    frame_rows: list[tuple[int, str]] = []
    prefix = f"scenes.{variant_id}.frames.item"
    for frame in _stream_items(path, prefix):
        frame_rows.append((int(frame.get("step", len(frame_rows))), state_hash(frame.get("state"))))
    total = max(len(trace_rows), len(frame_rows))
    equivalent = 0
    first_mismatch = None
    for index in range(total):
        trace_row = trace_rows[index] if index < len(trace_rows) else None
        frame_row = frame_rows[index] if index < len(frame_rows) else None
        if trace_row == frame_row and trace_row is not None:
            equivalent += 1
        elif first_mismatch is None:
            first_mismatch = {"index": index, "trace": trace_row, "scene": frame_row}
    row = {
        "variant_id": variant_id,
        "solver_trace_result_ok": None,
        "trace_input_ok": None,
        "scene_input_ok": None,
        "trace_frames": len(trace_rows),
        "scene_frames": len(frame_rows),
        "total_compared_frames": total,
        "equivalent_frames": equivalent,
        "all_frames_equivalent": total == equivalent,
        "first_mismatch": first_mismatch,
    }
    return {
        "dataset": dataset,
        "case_id": f"{path.parent.name}:{path.stem}",
        "artifact": str(path),
        "streaming": True,
        "variant_count": 1,
        "total_frames": total,
        "equivalent_frames": equivalent,
        "frame_equivalence_rate": equivalent / total if total else 0.0,
        "artifact_ok": row["all_frames_equivalent"],
        "variants": [row],
    }


def deterministic_rebuild(path: Path, *, repeats: int) -> dict[str, Any]:
    artifact = BuildArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    render_hashes = [hashlib.sha256(render_html(artifact).encode("utf-8")).hexdigest() for _ in range(repeats)]
    compile_rows = []
    for variant in artifact.variants:
        if variant.trace is None:
            continue
        compiled_hashes = []
        for _ in range(repeats):
            scene = compile_scene(SemanticTrace.model_validate(variant.trace.model_dump()))
            compiled_hashes.append(
                state_hash([{"step": frame.step, "state": frame.state} for frame in scene.frames])
            )
        compile_rows.append(
            {
                "variant_id": variant.id,
                "unique_projection_hashes": len(set(compiled_hashes)),
                "deterministic": len(set(compiled_hashes)) == 1,
            }
        )
    return {
        "artifact": str(path),
        "repeats": repeats,
        "unique_render_hashes": len(set(render_hashes)),
        "render_deterministic": len(set(render_hashes)) == 1,
        "compile": compile_rows,
    }


def artifact_paths_from_source(source: Path) -> list[Path]:
    if source.is_file():
        report = json.loads(source.read_text(encoding="utf-8"))
        paths: list[Path] = []
        seen: set[Path] = set()
        for row in report.get("results") or []:
            raw_path = str(row.get("json") or "").strip()
            if not raw_path:
                continue
            path = Path(raw_path)
            if not path.is_absolute():
                path = ROOT / path
            if path.exists() and path not in seen:
                paths.append(path)
                seen.add(path)
        return paths
    return sorted(path for path in source.rglob("*.json") if path.name != "llm_benchmark_report.json")


def run_audit(
    dataset_specs: list[str],
    *,
    max_bytes_in_memory: int,
    determinism_count: int,
    determinism_repeats: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    determinism_candidates: list[Path] = []
    failures: list[dict[str, str]] = []
    for spec in dataset_specs:
        label, separator, raw_path = spec.partition("=")
        if not separator:
            raw_path = label
            label = Path(raw_path).name
        source = Path(raw_path)
        if not source.is_absolute():
            source = ROOT / source
        for path in artifact_paths_from_source(source):
            try:
                if path.stat().st_size > max_bytes_in_memory:
                    row = audit_large_single_variant(path, dataset=label)
                else:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if data.get("schema_version") != "algolab-build-v1":
                        continue
                    row = audit_artifact_data(data, path=path, dataset=label)
                    if len(determinism_candidates) < determinism_count:
                        determinism_candidates.append(path)
                rows.append(row)
            except Exception as exc:
                failures.append({"dataset": label, "artifact": str(path), "error": f"{type(exc).__name__}: {exc}"})
    by_dataset: dict[str, Any] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["dataset"]].append(row)
    for dataset, items in sorted(grouped.items()):
        frames = sum(item["total_frames"] for item in items)
        equivalent = sum(item["equivalent_frames"] for item in items)
        by_dataset[dataset] = {
            "artifacts": len(items),
            "artifact_all_frame_pass": sum(item["artifact_ok"] is True for item in items),
            "artifact_all_frame_pass_rate": sum(item["artifact_ok"] is True for item in items) / len(items),
            "frames": frames,
            "equivalent_frames": equivalent,
            "frame_equivalence_rate": equivalent / frames if frames else 0.0,
            "streamed_large_artifacts": sum(item["streaming"] is True for item in items),
        }
    determinism = [
        deterministic_rebuild(path, repeats=determinism_repeats) for path in determinism_candidates
    ]
    return {
        "kind": "semantic_preservation_audit",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "projection_boundary": "trace.state -> scene.frame.state -> runtime frame state",
        "pixel_semantics_claimed": False,
        "summary": by_dataset,
        "determinism": determinism,
        "failures": failures,
        "results": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", required=True, help="LABEL=DIR")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-bytes-in-memory", type=int, default=400_000_000)
    parser.add_argument("--determinism-count", type=int, default=20)
    parser.add_argument("--determinism-repeats", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_audit(
        args.dataset,
        max_bytes_in_memory=args.max_bytes_in_memory,
        determinism_count=args.determinism_count,
        determinism_repeats=args.determinism_repeats,
    )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "failures": len(report["failures"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
