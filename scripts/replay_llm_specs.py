"""Replay saved LLM artifact specs without calling an LLM."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.compiler.scene_compiler import compile_scene
from algolab.runtime.executor import execute_variant, results_equivalent
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.verification.demo_readiness import validate_variant_demo_readiness
from algolab.verification.process_validator import validate_process
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace


def replay_artifact_file(
    artifact_path: Path,
    *,
    case_id: str | None = None,
    family_id: str | None = None,
    subfamily_id: str | None = None,
) -> dict[str, Any]:
    started = time.time()
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    inferred_case_id = case_id or _case_id_from_artifact_name(artifact_path)
    input_data = data.get("input_data")
    expected = data.get("expected_result")
    errors: list[str] = []
    warnings: list[str] = []
    variant_count = 0
    scene_count = 0
    context = {"case_id": inferred_case_id, "family_id": family_id, "subfamily_id": subfamily_id}

    for index, raw_variant in enumerate(data.get("variants") or []):
        try:
            variant_count += 1
            variant = SolutionVariant.model_validate(_variant_spec_for_replay(raw_variant, index))
            materialized = execute_variant(variant, input_data, **context)
            if expected is not None and not results_equivalent(materialized.result, expected, **context):
                raise ValueError(f"结果 {materialized.result!r} 与 expected {expected!r} 不一致")
            assert materialized.trace is not None
            trace_errors, trace_warnings = validate_trace(materialized.trace)
            if trace_errors:
                raise ValueError("; ".join(trace_errors))
            warnings.extend(f"{variant.name}: {warning}" for warning in trace_warnings)
            process_errors, process_warnings = validate_process(materialized.trace)
            if process_errors:
                raise ValueError("; ".join(process_errors))
            warnings.extend(f"{variant.name}: {warning}" for warning in process_warnings)
            demo_report = validate_variant_demo_readiness(materialized.id, materialized.name, materialized.trace)
            if demo_report.errors:
                raise ValueError("; ".join(demo_report.errors))
            warnings.extend(f"{variant.name}: {warning}" for warning in demo_report.warnings)
            scene = compile_scene(materialized.trace)
            scene_errors, scene_warnings = validate_scene(scene)
            if scene_errors:
                raise ValueError("; ".join(scene_errors))
            warnings.extend(f"{variant.name}: {warning}" for warning in scene_warnings)
            scene_count += 1
        except Exception as exc:
            errors.append(f"variant[{index}] 失败：{type(exc).__name__}: {exc}")

    ok = bool(variant_count) and scene_count == variant_count and not errors
    return {
        "artifact": str(artifact_path),
        "case_id": inferred_case_id,
        "family_id": family_id or "",
        "subfamily_id": subfamily_id or "",
        "ok": ok,
        "variant_count": variant_count,
        "scene_count": scene_count,
        "errors": errors,
        "warnings": warnings,
        "duration_s": round(time.time() - started, 3),
    }


def replay_directory(input_dir: Path) -> list[dict[str, Any]]:
    metadata = _load_report_metadata(input_dir)
    rows: list[dict[str, Any]] = []
    for artifact_path in sorted(input_dir.glob("*.json")):
        if artifact_path.name in {"llm_benchmark_report.json", "family_summary.json"}:
            continue
        if not artifact_path.name.startswith("llm_"):
            continue
        row_meta = metadata.get(artifact_path.name, {})
        rows.append(
            replay_artifact_file(
                artifact_path,
                case_id=row_meta.get("case_id"),
                family_id=row_meta.get("family_id"),
                subfamily_id=row_meta.get("subfamily_id"),
            )
        )
    return rows


def _variant_spec_for_replay(raw_variant: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": str(raw_variant.get("id") or f"variant_{index}"),
        "name": str(raw_variant.get("name") or f"variant_{index}"),
        "strategy": str(raw_variant.get("strategy") or ""),
        "time_complexity": str(raw_variant.get("time_complexity") or ""),
        "space_complexity": str(raw_variant.get("space_complexity") or ""),
        "code": str(raw_variant.get("code") or ""),
        "tracker_code": str(raw_variant.get("tracker_code") or raw_variant.get("trace_code") or ""),
    }


def _case_id_from_artifact_name(path: Path) -> str:
    name = path.stem
    if name.startswith("llm_"):
        name = name[4:]
    parts = name.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return name


def _load_report_metadata(input_dir: Path) -> dict[str, dict[str, str]]:
    report_path = input_dir / "llm_benchmark_report.json"
    if not report_path.exists():
        return {}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metadata: dict[str, dict[str, str]] = {}
    for item in report.get("results") or []:
        json_path = Path(str(item.get("json") or ""))
        if not json_path.name:
            continue
        metadata[json_path.name] = {
            "case_id": str(item.get("case_id") or ""),
            "family_id": str(item.get("family_id") or ""),
            "subfamily_id": str(item.get("subfamily_id") or ""),
        }
    return metadata


def write_report(rows: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    passed = sum(1 for row in rows if row.get("ok"))
    report = {
        "kind": "llm_spec_replay_report",
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 6) if total else 0,
        "results": rows,
    }
    (output_dir / "replay_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# LLM Spec Replay Report",
        "",
        f"- 总数：{total}",
        f"- 通过：{passed}",
        f"- 失败：{total - passed}",
        f"- 通过率：{(passed / total * 100) if total else 0:.2f}%",
        "",
        "| Case | Status | Errors | Artifact |",
        "|---|---|---|---|",
    ]
    for row in rows:
        errors = "<br>".join(str(error).replace("|", "\\|") for error in row.get("errors") or [])
        lines.append(
            f"| {row.get('case_id', '')} | {'PASS' if row.get('ok') else 'FAIL'} | {errors} | {row.get('artifact', '')} |"
        )
    (output_dir / "replay_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    rows = replay_directory(args.input_dir)
    write_report(rows, args.output_dir)
    passed = sum(1 for row in rows if row.get("ok"))
    print(f"llm_spec_replay: {passed}/{len(rows)} PASS")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
