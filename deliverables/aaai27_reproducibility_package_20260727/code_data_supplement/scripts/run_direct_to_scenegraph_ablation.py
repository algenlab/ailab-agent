"""Run the Direct-to-SceneGraph non-degenerate ablation."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.renderer.export import save_html
from algolab.schemas.scene_graph import SceneGraph
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from algolab.verification.scene_validator import validate_scene
from benchmark.cases import BenchmarkCase, benchmark_cases
from llm_client import _model_name, chat_json_with_metadata, llm_config
from scripts.prepare_evaluator_calibration import select_stratified_cases


DEFAULT_SOURCE_REPORT = ROOT / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/nondegenerate_ablations/direct_to_scenegraph_50"


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def select_ablation_rows(rows: list[dict[str, Any]], *, count: int = 50, seed: int = 20260713) -> list[dict[str, Any]]:
    candidates = [
        {
            **copy.deepcopy(row),
            "interaction_type": str(row.get("interaction_type") or "unknown"),
            "status_bits": str(row.get("status_bits") or ""),
        }
        for row in rows
    ]
    return select_stratified_cases(candidates, count=count, seed=seed)


def build_artifact_from_scene(
    *,
    title: str,
    strategy: str,
    expected: Any,
    scene_data: dict[str, Any],
) -> BuildArtifact:
    scene = SceneGraph.model_validate(scene_data)
    errors, warnings = validate_scene(scene)
    if errors:
        raise ValueError("; ".join(errors))
    variant = SolutionVariant(
        id="direct_scenegraph",
        name=title,
        strategy=strategy,
        code="def solve(input_data):\n    raise RuntimeError('solver removed by ablation')",
        tracker_code="def trace(input_data):\n    raise RuntimeError('trace removed by ablation')",
        result=scene.result,
        trace=None,
    )
    return BuildArtifact(
        problem_title=title,
        input_contract="Direct-to-SceneGraph ablation: problem to SceneGraph without executable solver or SemanticTrace.",
        input_data=scene.input_data,
        expected_result=expected,
        verifier_result=None,
        variants=[variant],
        scenes={variant.id: scene},
        validation=ValidationReport(
            checks=["SceneGraph schema validation passed", "SceneGraph referential validation passed"],
            warnings=warnings,
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=False,
                trace_ready=False,
                visual_ready=True,
                multi_solution_ready=False,
                release_ready=False,
                blocking_reasons=["executable solver, SemanticTrace, and process gate removed by ablation"],
            ),
        ),
    )


def build_scenegraph_prompt(case: BenchmarkCase, row: dict[str, Any]) -> str:
    schema = SceneGraph.model_json_schema()
    return "\n".join(
        [
            "Generate one complete SceneGraph JSON object for a fixed algorithm-teaching web runtime.",
            "Do not output HTML, JavaScript, Python, markdown, or wrapper keys.",
            f"Title: {case.title}",
            f"Problem: {case.problem}",
            f"Family: {case.family}",
            f"Strategy hint: {case.strategy}",
            f"Input JSON: {json.dumps(row.get('input_data'), ensure_ascii=False)}",
            f"Expected result JSON: {json.dumps(row.get('expected'), ensure_ascii=False)}",
            "Requirements:",
            "- result must equal the expected result and every frame state must be algorithmically coherent.",
            "- Use at least 3 frames: initialization, a key transition, and answer confirmation.",
            "- Frame steps must be contiguous from 0. Object IDs must be unique within a frame and all marks/source/target/parent references must resolve in that frame.",
            "- Each key frame must include grounded teaching and a choice/input/judge interaction with answer, correct explanation, wrong explanation, and hint.",
            "- Only use object types allowed by the schema. Prefer simple label/cell/node/edge objects and compact states.",
            "JSON Schema:",
            json.dumps(schema, ensure_ascii=False),
        ]
    )


def _normalize_scene_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("scene_graph", "scene", "content"):
        value = payload.get(key)
        if isinstance(value, dict) and "frames" in value:
            return value
    return payload


def run_one(
    row: dict[str, Any],
    *,
    case: BenchmarkCase,
    output_dir: Path,
    model: str,
) -> dict[str, Any]:
    result_path = output_dir / "cases" / case.id / "result.json"
    if result_path.exists():
        existing = json.loads(result_path.read_text(encoding="utf-8"))
        if existing.get("html") and _repo_path(str(existing["html"])).exists():
            return existing
    case_dir = result_path.parent
    case_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_scenegraph_prompt(case, row)
    prompt_path = case_dir / "prompt.txt"
    response_path = case_dir / "response.json"
    prompt_path.write_text(prompt, encoding="utf-8")
    started = time.time()
    try:
        response = chat_json_with_metadata(
            "You generate strict JSON for an algorithm teaching SceneGraph. Return only one JSON object.",
            prompt,
            model=model,
            kind="direct_to_scenegraph",
        )
        payload = _normalize_scene_payload(response["content"])
        _write_json(response_path, payload)
        artifact = build_artifact_from_scene(
            title=case.title,
            strategy=case.strategy,
            expected=row.get("expected"),
            scene_data=payload,
        )
        html_path = save_html(artifact, case_dir / "page.html")
        result = {
            **{key: copy.deepcopy(value) for key, value in row.items() if key not in {"html", "json", "model_calls"}},
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            "condition": "direct_to_scenegraph",
            "baseline": "direct_to_scenegraph",
            "ok": True,
            "html": _display_path(html_path),
            "json": _display_path(html_path.with_suffix(".json")),
            "prompt": _display_path(prompt_path),
            "response": _display_path(response_path),
            "duration_s": round(time.time() - started, 3),
            "model_calls": response.get("model_calls") or [],
            "scene_frames": len(artifact.scenes["direct_scenegraph"].frames),
            "trace_present": False,
            "process_validator_enabled": False,
            "fixed_runtime_enabled": True,
        }
    except Exception as exc:
        result = {
            **{key: copy.deepcopy(value) for key, value in row.items() if key not in {"html", "json", "model_calls"}},
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            "condition": "direct_to_scenegraph",
            "baseline": "direct_to_scenegraph",
            "ok": False,
            "html": "",
            "json": "",
            "prompt": _display_path(prompt_path),
            "response": _display_path(response_path) if response_path.exists() else "",
            "duration_s": round(time.time() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
            "model_calls": [],
            "trace_present": False,
            "process_validator_enabled": False,
            "fixed_runtime_enabled": True,
        }
    _write_json(result_path, result)
    return result


def _manifest_rows(source_rows: list[dict[str, Any]], manifest_path: Path, *, count: int, seed: int) -> list[dict[str, Any]]:
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        wanted = set(manifest.get("case_ids") or [])
        by_id = {str(row.get("case_id")): row for row in source_rows}
        if wanted <= set(by_id) and len(wanted) == count:
            return [by_id[case_id] for case_id in manifest["case_ids"]]
    selected = select_ablation_rows(source_rows, count=count, seed=seed)
    _write_json(
        manifest_path,
        {
            "kind": "nondegenerate_ablation_selection",
            "seed": seed,
            "count": count,
            "case_ids": [row["case_id"] for row in selected],
            "families": sorted({row.get("family_id") for row in selected}),
        },
    )
    return selected


def _write_report(output_dir: Path, results: list[dict[str, Any]], *, source_report: Path, model: str, started_at: str) -> dict[str, Any]:
    ordered = sorted(results, key=lambda row: str(row.get("case_id") or ""))
    report = {
        "kind": "llm_benchmark_report",
        "condition": "direct_to_scenegraph",
        "started_at": started_at,
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "source_report": _display_path(source_report),
        "config": {"model": model, "llm": llm_config(), "count": len(ordered), "seed": 20260713},
        "total": len(ordered),
        "passed": sum(1 for row in ordered if row.get("ok")),
        "failed": sum(1 for row in ordered if not row.get("ok")),
        "results": ordered,
    }
    _write_json(output_dir / "llm_benchmark_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--selection-manifest", type=Path, default=DEFAULT_OUTPUT_DIR.parent / "selected_cases_50.json")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--model", default="")
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    source_report = _repo_path(args.source_report)
    output_dir = _repo_path(args.output_dir)
    manifest_path = _repo_path(args.selection_manifest)
    source = json.loads(source_report.read_text(encoding="utf-8"))
    selected = _manifest_rows(source.get("results") or [], manifest_path, count=args.count, seed=args.seed)
    if args.case:
        wanted = set(args.case)
        selected = [row for row in selected if row.get("case_id") in wanted]
    case_map = {case.id: case for case in benchmark_cases()}
    model = args.model or str((source.get("config") or {}).get("model") or _model_name())
    started_at = datetime.now().isoformat(timespec="seconds")
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {
            executor.submit(run_one, row, case=case_map[str(row["case_id"])], output_dir=output_dir, model=model): str(row["case_id"])
            for row in selected
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            _write_report(output_dir, results, source_report=source_report, model=model, started_at=started_at)
            print(f"DONE {result['case_id']} ok={result.get('ok')}", flush=True)
    report = _write_report(output_dir, results, source_report=source_report, model=model, started_at=started_at)
    print(json.dumps({"report": _display_path(output_dir / "llm_benchmark_report.json"), "passed": report["passed"], "total": report["total"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
