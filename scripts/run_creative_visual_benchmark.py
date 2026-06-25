"""Generate LLM Direct Visual Renderer pages for verified BuildArtifact JSON files."""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import os
import queue
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.direct_visual_renderer import (
    DirectVisualRenderResult,
    build_direct_visual_prompt,
    build_direct_visual_stage_prompt,
    generate_direct_visual_html,
    generate_direct_visual_stage_shell_html,
    repair_direct_visual_stage_shell_html,
)
from algolab.schemas.validation import BuildArtifact
from llm_client import llm_config
from scripts.creative_quality_gate import (
    compact_creative_quality_report,
    creative_quality_score,
    is_better_creative_quality_report,
    run_creative_quality_gate,
)


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def collect_artifacts(artifact_dir: Path, glob_pattern: str, *, case_filters: set[str]) -> list[Path]:
    paths = []
    for path in sorted(artifact_dir.glob(glob_pattern)):
        if not path.is_file() or path.name in {"llm_benchmark_report.json", "family_summary.json"}:
            continue
        if case_filters and not any(case_id in path.stem for case_id in case_filters):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("schema_version") == "algolab-build-v1":
            paths.append(path)
    return paths


def load_problem_map(report: Path | None) -> dict[str, str]:
    from tests.benchmark_cases import benchmark_cases

    result: dict[str, str] = {
        case.id: case.problem
        for case in benchmark_cases()
        if str(case.problem or "").strip()
    }
    if report is None or not report.exists():
        return result
    data = json.loads(report.read_text(encoding="utf-8"))
    for item in data.get("results") or []:
        case_id = str(item.get("case_id") or "")
        problem = str(
            item.get("problem_description")
            or item.get("problem")
            or ""
        ).strip()
        title = str(item.get("title") or "").strip()
        if case_id and problem:
            result[case_id] = problem
        elif case_id and title and case_id not in result:
            result[case_id] = title
    return result


def infer_stage1_model_from_report(report: Path | None) -> str:
    """Infer the Stage1 generation model recorded by a benchmark report."""

    if report is None or not report.exists():
        return ""
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    results = data.get("results")
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            model = str(item.get("model") or "").strip()
            if model:
                return model
            calls = item.get("model_calls")
            if isinstance(calls, list):
                for call in calls:
                    if not isinstance(call, dict):
                        continue
                    if str(call.get("kind") or "") == "generation":
                        model = str(call.get("model") or "").strip()
                        if model:
                            return model
                for call in calls:
                    if isinstance(call, dict):
                        model = str(call.get("model") or "").strip()
                        if model:
                            return model
    llm = data.get("llm")
    if isinstance(llm, dict):
        model = str(llm.get("model") or "").strip()
        if model:
            return model
    model_config = data.get("model_config")
    if isinstance(model_config, dict):
        llm_config_data = model_config.get("llm")
        if isinstance(llm_config_data, dict):
            model = str(llm_config_data.get("model") or "").strip()
            if model:
                return model
    return ""


def resolve_generation_model(
    *,
    explicit_model: str | None,
    artifact_dir: Path,
    problem_report: Path | None,
) -> str | None:
    """Resolve Stage2 text LLM, defaulting to the Stage1 benchmark model."""

    if str(explicit_model or "").strip():
        return str(explicit_model).strip()
    for report in (problem_report, artifact_dir / "llm_benchmark_report.json"):
        model = infer_stage1_model_from_report(report)
        if model:
            return model
    return None


def infer_case_id(path: Path) -> str:
    stem = path.stem
    if stem.startswith("llm_"):
        stem = stem[4:]
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return stem


def write_case_outputs(
    *,
    artifact_path: Path,
    artifact: BuildArtifact,
    output_dir: Path,
    problem_description: str,
    prompt_only: bool,
    model: str | None,
    timeout_s: int,
    mode: str,
    timeout_retries: int,
    require_stage_visual_quality: bool,
    layout_repair_retries: int,
    require_creative_quality: bool,
    creative_quality_repair_retries: int,
    creative_quality_vlm: bool,
    vlm_model: str | None,
    stage_audit_wait_ms: int,
    stage_audit_max_frames: int,
) -> dict[str, Any]:
    case_id = infer_case_id(artifact_path)
    stem_suffix = "creative_stage" if mode == "stage_shell" else "creative"
    stem = f"{artifact_path.stem}_{stem_suffix}"
    html_dir = output_dir / "html"
    raw_dir = output_dir / "raw_llm"
    prompt_dir = output_dir / "prompts"
    audit_dir = output_dir / "audit"
    for directory in (html_dir, raw_dir, prompt_dir, audit_dir):
        directory.mkdir(parents=True, exist_ok=True)

    prompt = (
        build_direct_visual_stage_prompt(artifact, problem_description=problem_description)
        if mode == "stage_shell"
        else build_direct_visual_prompt(artifact, problem_description=problem_description)
    )
    prompt_path = prompt_dir / f"{stem}_prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    base_row: dict[str, Any] = {
        "case_id": case_id,
        "artifact_json": str(artifact_path),
        "problem_title": artifact.problem_title,
        "problem_description": problem_description,
        "prompt": str(prompt_path),
        "creative_attempted": not prompt_only,
        "render_mode": mode,
        "timeout_s": timeout_s,
        "timeout_retries": timeout_retries,
        "require_stage_visual_quality": require_stage_visual_quality,
        "layout_repair_retries": layout_repair_retries,
        "require_creative_quality": require_creative_quality,
        "creative_quality_repair_retries": creative_quality_repair_retries,
        "creative_quality_vlm": creative_quality_vlm,
        "vlm_model": vlm_model or "",
        "stage_audit_wait_ms": stage_audit_wait_ms,
        "stage_audit_max_frames": stage_audit_max_frames,
        "attempt_count": 0,
        "attempt_reports": [],
        "layout_repair_attempts": 0,
        "layout_audit_reports": [],
        "creative_quality_repair_attempts": 0,
        "creative_quality_reports": [],
        "creative_quality_ok": False,
        "creative_quality_score": 0,
        "browser_smoke_ok": False,
        "stage_visual_quality_ok": False,
        "strict_visual_quality_ok": False,
        "stage_overlap_count": 0,
        "stage_permitted_overlap_count": 0,
        "stage_clipped_count": 0,
        "stage_text_occlusion_count": 0,
        "creative_ok": False,
        "fallback_used": True,
        "html": "",
        "raw_output": "",
        "errors": [],
        "warnings": [],
        "model_calls": [],
    }
    if prompt_only:
        base_row["errors"] = ["prompt_only"]
        return base_row

    result, attempt_reports = generate_with_timeout_retries(
        artifact,
        problem_description=problem_description,
        model=model,
        timeout_s=timeout_s,
        mode=mode,
        timeout_retries=timeout_retries,
    )
    raw_path = raw_dir / f"{stem}_raw.txt"
    raw_path.write_text(result.raw_output, encoding="utf-8")
    report_path = audit_dir / f"{stem}_generation_report.json"
    html_path = html_dir / f"{stem}.html"
    if result.creative_ok:
        html_path.write_text(result.html, encoding="utf-8")
        if require_creative_quality:
            result, layout_reports = enforce_creative_quality(
                artifact=artifact,
                result=result,
                html_path=html_path,
                html_dir=html_dir,
                raw_dir=raw_dir,
                audit_dir=audit_dir,
                stem=stem,
                initial_stage=result.raw_output or result.extracted_html,
                problem_description=problem_description,
                model=model,
                mode=mode,
                wait_ms=stage_audit_wait_ms,
                stage_audit_max_frames=stage_audit_max_frames,
                repair_retries=creative_quality_repair_retries,
                enable_vlm=creative_quality_vlm,
                vlm_model=vlm_model,
            )
        elif require_stage_visual_quality:
            result, layout_reports = enforce_stage_visual_quality(
                artifact=artifact,
                result=result,
                html_path=html_path,
                html_dir=html_dir,
                raw_dir=raw_dir,
                audit_dir=audit_dir,
                stem=stem,
                initial_stage=result.raw_output or result.extracted_html,
                problem_description=problem_description,
                model=model,
                mode=mode,
                wait_ms=stage_audit_wait_ms,
                stage_audit_max_frames=stage_audit_max_frames,
                layout_repair_retries=layout_repair_retries,
            )
        else:
            layout_reports = []
    else:
        layout_reports = []
    model_calls = collect_case_model_calls(attempt_reports, layout_reports, fallback=result.model_calls)
    layout_status = summarize_layout_status(layout_reports)
    creative_quality_status = summarize_creative_quality_status(layout_reports)
    row = {
        **base_row,
        "creative_ok": result.creative_ok,
        "fallback_used": not result.creative_ok,
        "attempt_count": len(attempt_reports),
        "attempt_reports": attempt_reports,
        "layout_repair_attempts": sum(1 for item in layout_reports if item.get("kind") == "layout_repair"),
        "layout_audit_reports": layout_reports,
        "creative_quality_repair_attempts": sum(
            1 for item in layout_reports if item.get("kind") == "creative_quality_repair"
        ),
        "creative_quality_reports": [
            item for item in layout_reports if item.get("kind") in {"creative_quality_gate", "creative_quality_repair"}
        ],
        **layout_status,
        **creative_quality_status,
        "html": str(html_path) if result.creative_ok else "",
        "raw_output": str(raw_path),
        "errors": result.errors,
        "warnings": result.warnings,
        "model_calls": model_calls,
        "generation_report": str(report_path),
    }
    report_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def enforce_stage_visual_quality(
    *,
    artifact: BuildArtifact,
    result: DirectVisualRenderResult,
    html_path: Path,
    html_dir: Path,
    raw_dir: Path,
    audit_dir: Path,
    stem: str,
    initial_stage: str,
    problem_description: str,
    model: str | None,
    mode: str,
    wait_ms: int,
    stage_audit_max_frames: int,
    layout_repair_retries: int,
) -> tuple[DirectVisualRenderResult, list[dict[str, Any]]]:
    """Run the browser layout gate and repair stage-shell layout failures."""

    reports: list[dict[str, Any]] = []
    current_result = result
    current_stage = initial_stage

    audit_row = run_stage_layout_audit(
        html_path,
        audit_dir / f"{stem}_layout_attempt0",
        wait_ms=wait_ms,
        stage_audit_max_frames=stage_audit_max_frames,
    )
    reports.append({"kind": "layout_audit", "attempt": 0, "audit": _layout_failure_report(audit_row)})
    best_audit_row = audit_row
    best_result = current_result
    best_stage = current_stage
    if audit_row.get("creative_ok"):
        return current_result, reports

    if mode != "stage_shell":
        failed = _layout_failed_result(current_result, audit_row, reports)
        return failed, reports

    for attempt in range(1, max(0, int(layout_repair_retries)) + 1):
        repair_result = repair_direct_visual_stage_shell_html(
            artifact,
            broken_stage=current_stage,
            failure_report=_layout_failure_report(audit_row),
            problem_description=problem_description,
            model=model,
        )
        repair_raw_path = raw_dir / f"{stem}_layout_repair{attempt}_raw.txt"
        repair_raw_path.write_text(repair_result.raw_output, encoding="utf-8")
        repair_report: dict[str, Any] = {
            "kind": "layout_repair",
            "attempt": attempt,
            "creative_ok": repair_result.creative_ok,
            "raw_output": str(repair_raw_path),
            "errors": repair_result.errors,
            "warnings": repair_result.warnings,
            "model_calls": repair_result.model_calls,
        }
        reports.append(repair_report)
        if not repair_result.creative_ok:
            continue

        candidate_path = html_dir / f"{stem}_layout_repair{attempt}.html"
        candidate_path.write_text(repair_result.html, encoding="utf-8")
        candidate_audit_row = run_stage_layout_audit(
            candidate_path,
            audit_dir / f"{stem}_layout_attempt{attempt}",
            wait_ms=wait_ms,
            stage_audit_max_frames=stage_audit_max_frames,
        )
        reports.append({"kind": "layout_audit", "attempt": attempt, "audit": _layout_failure_report(candidate_audit_row)})
        if candidate_audit_row.get("creative_ok"):
            html_path.write_text(repair_result.html, encoding="utf-8")
            return repair_result, reports
        if is_better_layout_audit(candidate_audit_row, best_audit_row):
            best_audit_row = candidate_audit_row
            best_result = repair_result
            best_stage = repair_result.raw_output or repair_result.extracted_html or best_stage
        current_result = best_result
        current_stage = best_stage
        audit_row = best_audit_row

    return _layout_failed_result(best_result, best_audit_row, reports), reports


def enforce_creative_quality(
    *,
    artifact: BuildArtifact,
    result: DirectVisualRenderResult,
    html_path: Path,
    html_dir: Path,
    raw_dir: Path,
    audit_dir: Path,
    stem: str,
    initial_stage: str,
    problem_description: str,
    model: str | None,
    mode: str,
    wait_ms: int,
    stage_audit_max_frames: int,
    repair_retries: int,
    enable_vlm: bool,
    vlm_model: str | None,
) -> tuple[DirectVisualRenderResult, list[dict[str, Any]]]:
    """Run the unified Creative Quality gate and repair stage-shell failures."""

    reports: list[dict[str, Any]] = []
    current_result = result
    current_stage = initial_stage

    gate = run_creative_quality_audit(
        html_path,
        audit_dir / f"{stem}_creative_quality_attempt0",
        problem_description=problem_description,
        wait_ms=wait_ms,
        stage_audit_max_frames=stage_audit_max_frames,
        enable_vlm=enable_vlm,
        vlm_model=vlm_model,
    )
    append_creative_quality_reports(reports, attempt=0, gate=gate)
    best_gate = gate
    best_result = current_result
    best_stage = current_stage
    if gate.get("creative_quality_ok"):
        return current_result, reports

    if mode != "stage_shell":
        failed = _creative_quality_failed_result(current_result, gate, reports)
        return failed, reports

    for attempt in range(1, max(0, int(repair_retries)) + 1):
        repair_result = repair_direct_visual_stage_shell_html(
            artifact,
            broken_stage=current_stage,
            failure_report=compact_creative_quality_report(gate),
            problem_description=problem_description,
            model=model,
        )
        repair_raw_path = raw_dir / f"{stem}_creative_quality_repair{attempt}_raw.txt"
        repair_raw_path.write_text(repair_result.raw_output, encoding="utf-8")
        repair_report: dict[str, Any] = {
            "kind": "creative_quality_repair",
            "attempt": attempt,
            "creative_ok": repair_result.creative_ok,
            "raw_output": str(repair_raw_path),
            "errors": repair_result.errors,
            "warnings": repair_result.warnings,
            "model_calls": repair_result.model_calls,
        }
        reports.append(repair_report)
        if not repair_result.creative_ok:
            continue

        candidate_path = html_dir / f"{stem}_creative_quality_repair{attempt}.html"
        candidate_path.write_text(repair_result.html, encoding="utf-8")
        candidate_gate = run_creative_quality_audit(
            candidate_path,
            audit_dir / f"{stem}_creative_quality_attempt{attempt}",
            problem_description=problem_description,
            wait_ms=wait_ms,
            stage_audit_max_frames=stage_audit_max_frames,
            enable_vlm=enable_vlm,
            vlm_model=vlm_model,
        )
        append_creative_quality_reports(reports, attempt=attempt, gate=candidate_gate)
        if candidate_gate.get("creative_quality_ok"):
            html_path.write_text(repair_result.html, encoding="utf-8")
            return repair_result, reports
        if is_better_creative_quality_report(candidate_gate, best_gate):
            best_gate = candidate_gate
            best_result = repair_result
            best_stage = repair_result.raw_output or repair_result.extracted_html or best_stage
        current_result = best_result
        current_stage = best_stage
        gate = best_gate

    return _creative_quality_failed_result(best_result, best_gate, reports), reports


def run_creative_quality_audit(
    html_path: Path,
    output_dir: Path,
    *,
    problem_description: str,
    wait_ms: int,
    stage_audit_max_frames: int,
    enable_vlm: bool,
    vlm_model: str | None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_creative_quality_gate(
        html_path,
        output_dir,
        problem_description=problem_description,
        wait_ms=wait_ms,
        stage_audit_max_frames=stage_audit_max_frames,
        enable_vlm=enable_vlm,
        vlm_model=vlm_model,
    )


def append_creative_quality_reports(reports: list[dict[str, Any]], *, attempt: int, gate: dict[str, Any]) -> None:
    reports.append(
        {
            "kind": "creative_quality_gate",
            "attempt": attempt,
            "gate": compact_creative_quality_report(gate),
            "model_calls": (gate.get("vlm") or {}).get("model_calls") if isinstance(gate.get("vlm"), dict) else [],
        }
    )
    reports.append(
        {
            "kind": "layout_audit",
            "attempt": attempt,
            "audit": gate.get("playwright") or {},
        }
    )


def run_stage_layout_audit(
    html_path: Path,
    output_dir: Path,
    *,
    wait_ms: int,
    stage_audit_max_frames: int,
) -> dict[str, Any]:
    from scripts.audit_creative_visual_renderer import audit_html_path

    output_dir.mkdir(parents=True, exist_ok=True)
    row = audit_html_path(
        html_path,
        output_dir,
        wait_ms=wait_ms,
        require_stage_visual_quality=True,
        stage_audit_max_frames=stage_audit_max_frames,
    )
    audit_path = output_dir / "layout_gate.json"
    audit_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def _layout_failure_report(row: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "case_id",
        "creative_ok",
        "browser_smoke_ok",
        "failure_categories",
        "strict_visual_quality_ok",
        "stage_visual_quality_ok",
        "stage_audited_frame_count",
        "stage_audited_frames",
        "stage_overlap_count",
        "stage_overlap_max",
        "stage_permitted_overlap_count",
        "stage_permitted_overlap_max",
        "stage_clipped_count",
        "stage_clipped_max",
        "stage_text_occlusion_count",
        "stage_text_occlusion_max",
        "stage_layout_issues",
        "stage_permitted_layout_issues",
        "stage_layout_frame_reports",
        "console_errors",
        "page_errors",
        "failure_reason",
        "screenshot",
    ]
    return {key: row.get(key) for key in keys if key in row}


def layout_audit_score(row: dict[str, Any]) -> tuple[int, int, int, int, int, int, int, int]:
    """Lower is better; strict pass beats partial layout improvements."""

    overlap = int(row.get("stage_overlap_count") or 0)
    clipped = int(row.get("stage_clipped_count") or 0)
    text = int(row.get("stage_text_occlusion_count") or 0)
    permitted = int(row.get("stage_permitted_overlap_count") or 0)
    weighted = clipped * 1000 + overlap * 20 + text * 10
    return (
        0 if row.get("creative_ok") else 1,
        0 if row.get("browser_smoke_ok") else 1,
        0 if row.get("strict_visual_quality_ok", row.get("stage_visual_quality_ok")) else 1,
        weighted,
        clipped,
        overlap,
        text,
        permitted,
    )


def is_better_layout_audit(candidate: dict[str, Any], incumbent: dict[str, Any] | None) -> bool:
    if incumbent is None:
        return True
    return layout_audit_score(candidate) < layout_audit_score(incumbent)


def best_layout_audit(layout_reports: list[dict[str, Any]]) -> dict[str, Any]:
    audits = [item.get("audit") or {} for item in layout_reports if item.get("kind") == "layout_audit"]
    best: dict[str, Any] = {}
    for audit in audits:
        if is_better_layout_audit(audit, best if best else None):
            best = audit
    return best


def summarize_layout_status(layout_reports: list[dict[str, Any]]) -> dict[str, Any]:
    audits = [item.get("audit") or {} for item in layout_reports if item.get("kind") == "layout_audit"]
    if not audits:
        return {}
    first = audits[0]
    last = audits[-1]
    best = best_layout_audit(layout_reports) or last
    return {
        "browser_smoke_ok": bool(best.get("browser_smoke_ok")),
        "stage_visual_quality_ok": bool(best.get("stage_visual_quality_ok")),
        "strict_visual_quality_ok": bool(best.get("strict_visual_quality_ok", best.get("stage_visual_quality_ok"))),
        "stage_overlap_count": int(best.get("stage_overlap_count") or 0),
        "stage_permitted_overlap_count": int(best.get("stage_permitted_overlap_count") or 0),
        "stage_clipped_count": int(best.get("stage_clipped_count") or 0),
        "stage_text_occlusion_count": int(best.get("stage_text_occlusion_count") or 0),
        "initial_browser_smoke_ok": bool(first.get("browser_smoke_ok")),
        "initial_stage_visual_quality_ok": bool(first.get("stage_visual_quality_ok")),
        "initial_stage_overlap_count": int(first.get("stage_overlap_count") or 0),
        "initial_stage_permitted_overlap_count": int(first.get("stage_permitted_overlap_count") or 0),
        "initial_stage_clipped_count": int(first.get("stage_clipped_count") or 0),
        "initial_stage_text_occlusion_count": int(first.get("stage_text_occlusion_count") or 0),
        "last_browser_smoke_ok": bool(last.get("browser_smoke_ok")),
        "last_stage_visual_quality_ok": bool(last.get("stage_visual_quality_ok")),
        "last_strict_visual_quality_ok": bool(last.get("strict_visual_quality_ok", last.get("stage_visual_quality_ok"))),
        "last_stage_overlap_count": int(last.get("stage_overlap_count") or 0),
        "last_stage_permitted_overlap_count": int(last.get("stage_permitted_overlap_count") or 0),
        "last_stage_clipped_count": int(last.get("stage_clipped_count") or 0),
        "last_stage_text_occlusion_count": int(last.get("stage_text_occlusion_count") or 0),
    }


def best_creative_quality_gate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    gates = [item.get("gate") or {} for item in reports if item.get("kind") == "creative_quality_gate"]
    best: dict[str, Any] = {}
    for gate in gates:
        if is_better_creative_quality_report(gate, best if best else None):
            best = gate
    return best


def summarize_creative_quality_status(reports: list[dict[str, Any]]) -> dict[str, Any]:
    gates = [item.get("gate") or {} for item in reports if item.get("kind") == "creative_quality_gate"]
    if not gates:
        return {}
    first = gates[0]
    last = gates[-1]
    best = best_creative_quality_gate(reports) or last
    best_vlm = best.get("vlm") if isinstance(best.get("vlm"), dict) else {}
    first_vlm = first.get("vlm") if isinstance(first.get("vlm"), dict) else {}
    last_vlm = last.get("vlm") if isinstance(last.get("vlm"), dict) else {}
    return {
        "creative_quality_ok": bool(best.get("creative_quality_ok")),
        "creative_quality_score": int(best.get("score") or creative_quality_score(best)),
        "creative_quality_hard_failures": list(best.get("hard_failures") or []),
        "creative_quality_soft_failures": list(best.get("soft_failures") or []),
        "vlm_creative_quality_ok": bool(best_vlm.get("ok")),
        "vlm_scenario_salience_score": best_vlm.get("scenario_salience_score"),
        "vlm_algorithm_readability_score": best_vlm.get("algorithm_readability_score"),
        "vlm_generic_algorithm_visual": bool(best_vlm.get("is_generic_algorithm_visual")),
        "initial_creative_quality_ok": bool(first.get("creative_quality_ok")),
        "initial_creative_quality_score": int(first.get("score") or creative_quality_score(first)),
        "initial_vlm_scenario_salience_score": first_vlm.get("scenario_salience_score"),
        "last_creative_quality_ok": bool(last.get("creative_quality_ok")),
        "last_creative_quality_score": int(last.get("score") or creative_quality_score(last)),
        "last_vlm_scenario_salience_score": last_vlm.get("scenario_salience_score"),
    }


def _layout_failed_result(
    result: DirectVisualRenderResult,
    audit_row: dict[str, Any],
    reports: list[dict[str, Any]],
) -> DirectVisualRenderResult:
    return DirectVisualRenderResult(
        creative_ok=False,
        html="",
        raw_output=result.raw_output,
        extracted_html=result.extracted_html,
        prompt=result.prompt,
        errors=list(result.errors)
        + [
            "stage_visual_quality_gate_failed: "
            + json.dumps(_layout_failure_report(audit_row), ensure_ascii=False, sort_keys=True)
        ],
        warnings=list(result.warnings),
        model_calls=list(result.model_calls)
        + [
            call
            for report in reports
            if report.get("kind") == "layout_repair"
            for call in (report.get("model_calls") or [])
        ],
    )


def _creative_quality_failed_result(
    result: DirectVisualRenderResult,
    gate: dict[str, Any],
    reports: list[dict[str, Any]],
) -> DirectVisualRenderResult:
    return DirectVisualRenderResult(
        creative_ok=False,
        html="",
        raw_output=result.raw_output,
        extracted_html=result.extracted_html,
        prompt=result.prompt,
        errors=list(result.errors)
        + [
            "creative_quality_gate_failed: "
            + json.dumps(compact_creative_quality_report(gate), ensure_ascii=False, sort_keys=True)
        ],
        warnings=list(result.warnings),
        model_calls=list(result.model_calls)
        + [
            call
            for report in reports
            if report.get("kind") in {"layout_repair", "creative_quality_repair"}
            for call in (report.get("model_calls") or [])
        ],
    )


def write_report(rows: list[dict[str, Any]], output_dir: Path, *, started_at: str, args: argparse.Namespace) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ended_at = now_iso()
    attempted = sum(1 for row in rows if row.get("creative_attempted"))
    passed = sum(1 for row in rows if row.get("creative_ok"))
    browser_passed = sum(1 for row in rows if row.get("browser_smoke_ok"))
    strict_visual_passed = sum(1 for row in rows if row.get("strict_visual_quality_ok") or row.get("stage_visual_quality_ok"))
    creative_quality_passed = sum(1 for row in rows if row.get("creative_quality_ok"))
    failed = attempted - passed
    usage = summarize_model_usage(rows)
    report = {
        "kind": "creative_visual_benchmark_report",
        "schema_version": "creative-visual-benchmark-v1",
        "started_at": started_at,
        "ended_at": ended_at,
        "artifact_dir": str(args.artifact_dir),
        "artifact_glob": args.artifact_glob,
        "render_mode": args.mode,
        "timeout_s": args.timeout_s,
        "timeout_retries": args.timeout_retries,
        "require_stage_visual_quality": args.require_stage_visual_quality,
        "layout_repair_retries": args.layout_repair_retries,
        "require_creative_quality": getattr(args, "require_creative_quality", False),
        "creative_quality_repair_retries": getattr(args, "creative_quality_repair_retries", 0),
        "creative_quality_vlm": getattr(args, "creative_quality_vlm", False),
        "vlm_model": getattr(args, "vlm_model", "") or "",
        "stage_audit_max_frames": args.stage_audit_max_frames,
        "requested_model": args.model or "",
        "generation_model": getattr(args, "generation_model", "") or args.model or "",
        "llm": llm_config(),
        "summary": {
            "total_artifacts": len(rows),
            "creative_attempted": attempted,
            "creative_ok": passed,
            "failed": failed,
            "fallback_used": sum(1 for row in rows if row.get("fallback_used")),
            "browser_smoke_ok": browser_passed,
            "browser_smoke_ok_rate": browser_passed / attempted if attempted else 0.0,
            "strict_visual_quality_ok": strict_visual_passed,
            "strict_visual_quality_ok_rate": strict_visual_passed / attempted if attempted else 0.0,
            "creative_quality_ok": creative_quality_passed,
            "creative_quality_ok_rate": creative_quality_passed / attempted if attempted else 0.0,
            "layout_repair_attempts": sum(int(row.get("layout_repair_attempts") or 0) for row in rows),
            "creative_quality_repair_attempts": sum(
                int(row.get("creative_quality_repair_attempts") or 0) for row in rows
            ),
            "stage_overlap_total": sum(int(row.get("stage_overlap_count") or 0) for row in rows),
            "stage_permitted_overlap_total": sum(int(row.get("stage_permitted_overlap_count") or 0) for row in rows),
            "stage_clipped_total": sum(int(row.get("stage_clipped_count") or 0) for row in rows),
            "stage_text_occlusion_total": sum(int(row.get("stage_text_occlusion_count") or 0) for row in rows),
            "creative_ok_rate": passed / attempted if attempted else 0.0,
            "model_call_count": usage["model_call_count"],
            "usage_available_count": usage["usage_available_count"],
            "llm_duration_s": usage["llm_duration_s"],
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["total_tokens"],
            "avg_total_tokens_per_attempted": usage["total_tokens"] / attempted if attempted else 0.0,
            "avg_llm_duration_s_per_attempted": usage["llm_duration_s"] / attempted if attempted else 0.0,
        },
        "results": rows,
    }
    json_path = output_dir / "creative_benchmark_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = output_dir / "case_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "creative_attempted",
                "creative_ok",
                "browser_smoke_ok",
                "strict_visual_quality_ok",
                "creative_quality_ok",
                "creative_quality_score",
                "fallback_used",
                "layout_repair_attempts",
                "creative_quality_repair_attempts",
                "stage_overlap_count",
                "stage_permitted_overlap_count",
                "stage_clipped_count",
                "stage_text_occlusion_count",
                "vlm_scenario_salience_score",
                "vlm_algorithm_readability_score",
                "vlm_generic_algorithm_visual",
                "model_call_count",
                "usage_available_count",
                "llm_duration_s",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "html",
                "artifact_json",
                "problem_title",
                "errors",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "case_id": row.get("case_id", ""),
                    "creative_attempted": row.get("creative_attempted", False),
                    "creative_ok": row.get("creative_ok", False),
                    "browser_smoke_ok": row.get("browser_smoke_ok", False),
                    "strict_visual_quality_ok": row.get("strict_visual_quality_ok", row.get("stage_visual_quality_ok", False)),
                    "creative_quality_ok": row.get("creative_quality_ok", False),
                    "creative_quality_score": row.get("creative_quality_score", 0),
                    "fallback_used": row.get("fallback_used", True),
                    "layout_repair_attempts": row.get("layout_repair_attempts", 0),
                    "creative_quality_repair_attempts": row.get("creative_quality_repair_attempts", 0),
                    "stage_overlap_count": row.get("stage_overlap_count", 0),
                    "stage_permitted_overlap_count": row.get("stage_permitted_overlap_count", 0),
                    "stage_clipped_count": row.get("stage_clipped_count", 0),
                    "stage_text_occlusion_count": row.get("stage_text_occlusion_count", 0),
                    "vlm_scenario_salience_score": row.get("vlm_scenario_salience_score", ""),
                    "vlm_algorithm_readability_score": row.get("vlm_algorithm_readability_score", ""),
                    "vlm_generic_algorithm_visual": row.get("vlm_generic_algorithm_visual", ""),
                    **summarize_row_usage(row),
                    "html": row.get("html", ""),
                    "artifact_json": row.get("artifact_json", ""),
                    "problem_title": row.get("problem_title", ""),
                    "errors": "; ".join(str(item) for item in row.get("errors") or []),
                }
            )
    md_path = output_dir / "creative_benchmark_report.md"
    lines = [
        "# Creative Visual Benchmark Report",
        "",
        f"- artifacts: {len(rows)}",
        f"- attempted: {attempted}",
        f"- browser_smoke_ok: {browser_passed}",
        f"- creative_ok: {passed}",
        f"- strict_visual_quality_ok: {strict_visual_passed}",
        f"- creative_quality_ok: {creative_quality_passed}",
        f"- fallback_used: {sum(1 for row in rows if row.get('fallback_used'))}",
        f"- layout_repair_attempts: {sum(int(row.get('layout_repair_attempts') or 0) for row in rows)}",
        f"- creative_quality_repair_attempts: {sum(int(row.get('creative_quality_repair_attempts') or 0) for row in rows)}",
        f"- model_call_count: {usage['model_call_count']}",
        f"- llm_duration_s: {usage['llm_duration_s']}",
        f"- total_tokens: {usage['total_tokens']}",
        "",
        "| Case | Browser | Creative | Strict Visual | Creative Quality | CQ Score | Fallback | Layout Repairs | CQ Repairs | Overlap | Permitted Overlay | Clipped | Text Occlusion | VLM Scenario | LLM s | Tokens | HTML | Errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        row_usage = summarize_row_usage(row)
        lines.append(
            f"| {row.get('case_id', '')} | {row.get('browser_smoke_ok', False)} | "
            f"{row.get('creative_ok', False)} | {row.get('strict_visual_quality_ok', row.get('stage_visual_quality_ok', False))} | "
            f"{row.get('creative_quality_ok', False)} | {row.get('creative_quality_score', 0)} | "
            f"{row.get('fallback_used', True)} | {row.get('layout_repair_attempts', 0)} | "
            f"{row.get('creative_quality_repair_attempts', 0)} | "
            f"{row.get('stage_overlap_count', 0)} | {row.get('stage_permitted_overlap_count', 0)} | "
            f"{row.get('stage_clipped_count', 0)} | {row.get('stage_text_occlusion_count', 0)} | "
            f"{row.get('vlm_scenario_salience_score', '')} | "
            f"{row_usage['llm_duration_s']} | {row_usage['total_tokens']} | {row.get('html', '')} | "
            f"{'; '.join(str(item) for item in row.get('errors') or [])} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path


def collect_case_model_calls(
    attempt_reports: list[dict[str, Any]],
    layout_reports: list[dict[str, Any]],
    *,
    fallback: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for report in attempt_reports:
        calls.extend(call for call in (report.get("model_calls") or []) if isinstance(call, dict))
    for report in layout_reports:
        if report.get("kind") in {"layout_repair", "creative_quality_repair"}:
            calls.extend(call for call in (report.get("model_calls") or []) if isinstance(call, dict))
        if report.get("kind") == "creative_quality_gate":
            calls.extend(call for call in (report.get("model_calls") or []) if isinstance(call, dict))
    if not calls:
        calls.extend(call for call in (fallback or []) if isinstance(call, dict))
    return _dedupe_model_calls(calls)


def _dedupe_model_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for call in calls:
        key = (
            call.get("kind"),
            call.get("model"),
            call.get("started_at"),
            call.get("ended_at"),
            call.get("total_tokens"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(call)
    return result


def summarize_model_usage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "model_call_count": 0,
        "usage_available_count": 0,
        "llm_duration_s": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    for row in rows:
        row_usage = summarize_row_usage(row)
        for key in totals:
            totals[key] += row_usage[key]
    totals["llm_duration_s"] = round(float(totals["llm_duration_s"]), 3)
    return totals


def summarize_row_usage(row: dict[str, Any]) -> dict[str, Any]:
    calls = list(row.get("model_calls") or [])
    totals = {
        "model_call_count": len(calls),
        "usage_available_count": sum(1 for call in calls if call.get("usage_available")),
        "llm_duration_s": round(sum(float(call.get("duration_s") or 0.0) for call in calls), 3),
        "prompt_tokens": sum(int(call.get("prompt_tokens") or 0) for call in calls),
        "completion_tokens": sum(int(call.get("completion_tokens") or 0) for call in calls),
        "total_tokens": sum(int(call.get("total_tokens") or 0) for call in calls),
    }
    return totals


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True, help="Directory containing BuildArtifact JSON files")
    parser.add_argument("--artifact-glob", default="*.json")
    parser.add_argument("--output-dir", type=Path, default=Path("output/creative_visual_benchmark"))
    parser.add_argument("--case", action="append", default=[], help="Filter by case id substring; repeatable")
    parser.add_argument("--max-artifacts", type=int, default=0)
    parser.add_argument("--problem-report", type=Path, default=None, help="Optional llm_benchmark_report.json for case titles")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-s", type=int, default=1800, help="Per-case creative generation timeout; 0 disables")
    parser.add_argument(
        "--timeout-retries",
        type=int,
        default=2,
        help="Retry only process timeout failures this many extra times per case.",
    )
    parser.add_argument(
        "--mode",
        choices=["stage_shell", "full_html"],
        default="stage_shell",
        help="stage_shell uses deterministic Creative Shell plus LLM stage; full_html keeps the older full-page mode.",
    )
    parser.add_argument(
        "--llm-max-tokens",
        type=int,
        default=24000,
        help="Override ALGOLAB_LLM_MAX_TOKENS for creative generation; 0 keeps the environment/default.",
    )
    parser.add_argument(
        "--require-stage-visual-quality",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run browser layout gate for Creative Stage overlap/clipping/text occlusion and fail/fallback if it cannot be repaired.",
    )
    parser.add_argument(
        "--layout-repair-retries",
        type=int,
        default=0,
        help="How many LLM stage-only layout repair attempts to run after the browser layout gate fails.",
    )
    parser.add_argument(
        "--require-creative-quality",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run the unified Creative Quality gate: browser/layout checks plus optional VLM scenario salience checks.",
    )
    parser.add_argument(
        "--creative-quality-repair-retries",
        type=int,
        default=0,
        help="How many LLM stage-only repair attempts to run after the Creative Quality gate fails.",
    )
    parser.add_argument(
        "--creative-quality-vlm",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable Gemini/VLM scenario salience checks inside the Creative Quality gate.",
    )
    parser.add_argument(
        "--vlm-model",
        default=None,
        help="Optional VLM model override for --creative-quality-vlm, e.g. gemini-3-flash-preview.",
    )
    parser.add_argument(
        "--stage-audit-wait-ms",
        type=int,
        default=300,
        help="Wait time after each sampled frame switch during stage layout audit.",
    )
    parser.add_argument(
        "--stage-audit-max-frames",
        type=int,
        default=4,
        help="Representative frames audited by the stage layout gate; 0 audits all frames.",
    )
    parser.add_argument("--prompt-only", action="store_true", help="Write prompts without calling the LLM")
    return parser.parse_args()


def generate_with_timeout_retries(
    artifact: BuildArtifact,
    *,
    problem_description: str,
    model: str | None,
    timeout_s: int,
    mode: str,
    timeout_retries: int,
) -> tuple[DirectVisualRenderResult, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    total_attempts = max(1, int(timeout_retries) + 1)
    last = DirectVisualRenderResult(creative_ok=False, errors=["no_generation_attempt"])
    for attempt in range(1, total_attempts + 1):
        result = generate_with_process_timeout(
            artifact,
            problem_description=problem_description,
            model=model,
            timeout_s=timeout_s,
            mode=mode,
        )
        attempts.append(
            {
                "attempt": attempt,
                "creative_ok": result.creative_ok,
                "errors": result.errors,
                "warnings": result.warnings,
                "timed_out": _is_timeout_result(result),
                "model_calls": result.model_calls,
            }
        )
        last = result
        if result.creative_ok or not _is_timeout_result(result):
            break
    return last, attempts


def generate_with_process_timeout(
    artifact: BuildArtifact,
    *,
    problem_description: str,
    model: str | None,
    timeout_s: int,
    mode: str = "full_html",
) -> DirectVisualRenderResult:
    if timeout_s <= 0:
        return _generate_for_mode(artifact, problem_description=problem_description, model=model, mode=mode)
    result_queue: mp.Queue = mp.Queue()
    process = mp.Process(
        target=_generate_worker,
        args=(artifact.model_dump_json(), problem_description, model, mode, result_queue),
    )
    process.start()
    deadline = time.time() + timeout_s
    payload: dict[str, Any] | None = None
    while time.time() < deadline:
        try:
            payload = result_queue.get(timeout=0.5)
            break
        except queue.Empty:
            if not process.is_alive():
                break
    process.join(2)
    if process.is_alive():
        process.terminate()
        process.join(2)
        return DirectVisualRenderResult(
            creative_ok=False,
            errors=[f"creative_timeout: Creative visual generation exceeded {timeout_s}s"],
        )
    if payload is None:
        try:
            payload = result_queue.get_nowait()
        except queue.Empty:
            payload = None
    if payload is None:
        return DirectVisualRenderResult(creative_ok=False, errors=["creative_worker_no_result"])
    if payload.get("type") == "error":
        return DirectVisualRenderResult(creative_ok=False, errors=[str(payload.get("error") or "creative_worker_error")])
    result = payload.get("result") or {}
    return DirectVisualRenderResult(
        creative_ok=bool(result.get("creative_ok")),
        html=str(result.get("html") or ""),
        raw_output=str(result.get("raw_output") or ""),
        extracted_html=str(result.get("extracted_html") or ""),
        prompt=str(result.get("prompt") or ""),
        errors=list(result.get("errors") or []),
        warnings=list(result.get("warnings") or []),
        model_calls=list(result.get("model_calls") or []),
    )


def _generate_worker(
    artifact_json: str,
    problem_description: str,
    model: str | None,
    mode: str,
    queue: mp.Queue,
) -> None:
    try:
        artifact = BuildArtifact.model_validate_json(artifact_json)
        result = _generate_for_mode(artifact, problem_description=problem_description, model=model, mode=mode)
        queue.put(
            {
                "type": "result",
                "result": {
                    "creative_ok": result.creative_ok,
                    "html": result.html,
                    "raw_output": result.raw_output,
                    "extracted_html": result.extracted_html,
                    "prompt": result.prompt,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "model_calls": result.model_calls,
                },
            }
        )
    except Exception as exc:
        queue.put({"type": "error", "error": f"{type(exc).__name__}: {exc}"})


def _generate_for_mode(
    artifact: BuildArtifact,
    *,
    problem_description: str,
    model: str | None,
    mode: str,
) -> DirectVisualRenderResult:
    if mode == "stage_shell":
        return generate_direct_visual_stage_shell_html(artifact, problem_description=problem_description, model=model)
    return generate_direct_visual_html(artifact, problem_description=problem_description, model=model)


def _is_timeout_result(result: DirectVisualRenderResult) -> bool:
    return any("creative_timeout" in str(error) for error in result.errors)


def main() -> int:
    args = parse_args()
    started_at = now_iso()
    artifact_dir = args.artifact_dir.resolve()
    output_dir = args.output_dir.resolve()
    generation_model = resolve_generation_model(
        explicit_model=args.model,
        artifact_dir=artifact_dir,
        problem_report=args.problem_report,
    )
    args.generation_model = generation_model or ""
    apply_llm_overrides(args)
    artifacts = collect_artifacts(artifact_dir, args.artifact_glob, case_filters=set(args.case))
    if args.max_artifacts and args.max_artifacts > 0:
        artifacts = artifacts[: args.max_artifacts]
    if not artifacts:
        raise SystemExit(f"no BuildArtifact JSON files found in {artifact_dir}")
    problem_map = load_problem_map(args.problem_report)
    rows: list[dict[str, Any]] = []
    for index, artifact_path in enumerate(artifacts, start=1):
        artifact = BuildArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
        case_id = infer_case_id(artifact_path)
        problem_description = problem_map.get(case_id) or artifact.problem_title
        print(f"CREATIVE {index}/{len(artifacts)} {case_id}", flush=True)
        row = write_case_outputs(
            artifact_path=artifact_path,
            artifact=artifact,
            output_dir=output_dir,
            problem_description=problem_description,
            prompt_only=bool(args.prompt_only),
            model=generation_model,
            timeout_s=int(args.timeout_s),
            mode=args.mode,
            timeout_retries=int(args.timeout_retries),
            require_stage_visual_quality=bool(args.require_stage_visual_quality),
            layout_repair_retries=int(args.layout_repair_retries),
            require_creative_quality=bool(args.require_creative_quality),
            creative_quality_repair_retries=int(args.creative_quality_repair_retries),
            creative_quality_vlm=bool(args.creative_quality_vlm),
            vlm_model=args.vlm_model,
            stage_audit_wait_ms=int(args.stage_audit_wait_ms),
            stage_audit_max_frames=int(args.stage_audit_max_frames),
        )
        rows.append(row)
        write_report(rows, output_dir, started_at=started_at, args=args)
    report_path = write_report(rows, output_dir, started_at=started_at, args=args)
    passed = sum(1 for row in rows if row.get("creative_ok"))
    attempted = sum(1 for row in rows if row.get("creative_attempted"))
    print(f"creative_visual_benchmark: {passed}/{attempted} creative_ok")
    print(f"report: {report_path}")
    return 0 if passed == attempted else 1


def apply_llm_overrides(args: argparse.Namespace) -> None:
    """Apply Creative View defaults before llm_config() or LLM calls run."""

    if int(args.timeout_s) > 0:
        os.environ["ALGOLAB_LLM_TIMEOUT_S"] = str(int(args.timeout_s))
    if int(args.llm_max_tokens) > 0:
        os.environ["ALGOLAB_LLM_MAX_TOKENS"] = str(int(args.llm_max_tokens))
    generation_model = getattr(args, "generation_model", None) or args.model
    if generation_model:
        os.environ["ALGOLAB_LLM_MODEL"] = str(generation_model)
    if getattr(args, "vlm_model", None):
        os.environ["ALGOLAB_VLM_MODEL"] = str(args.vlm_model)


if __name__ == "__main__":
    raise SystemExit(main())
