"""Run the benchmark through the real LLM generation path.

This script intentionally does not cache model outputs. Every case calls
build_artifact(), which calls the configured LLM generator and repair loop.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing as mp
import queue
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.solution_generator import generate_solution_spec, repair_solution_spec
from algolab.pipeline import BuildError, _try_materialize
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput
from algolab.schemas.validation import BuildArtifact
from algolab.verification.demo_readiness import DEMO_FAILURE_TYPES
from algolab.verification.process_validator import process_failure_type_for_message
from algolab.verification.repair_context import repair_failure_types, summarize_repair_failure_types
from llm_client import _model_name, clear_model_calls, consume_model_calls, llm_config
from tests.benchmark_cases import BenchmarkCase, BenchmarkInput, benchmark_cases


LLM_FAMILY_SETS_PATH = ROOT / "benchmark" / "llm_family_sets.json"
UNSEEN_FAMILY_CASES_PATH = ROOT / "benchmark" / "unseen_family_cases.json"
FAMILY_CAPABILITIES_PATH = ROOT / "benchmark" / "family_capabilities.json"
FORBIDDEN_UNSEEN_CASE_FIELDS = {"code", "tracker_code", "verifier_code"}


@dataclass(frozen=True)
class UnseenBenchmarkCase:
    id: str
    title: str
    problem: str
    family: str
    strategy: str
    samples: tuple[BenchmarkInput, ...]
    family_id: str
    subfamily_id: str
    gate_layer: str
    support_level: str
    process_profile: str


def load_llm_family_sets(path: Path | None = None) -> dict[str, Any]:
    family_sets_path = path or LLM_FAMILY_SETS_PATH
    if not family_sets_path.exists():
        return {
            "schema_version": "llm-family-sets-v1",
            "families": [],
            "default_sample_styles": {"seen_style": [0], "unseen_style": [1]},
            "remaining_sample_style": "unseen_style",
        }
    return json.loads(family_sets_path.read_text(encoding="utf-8"))


def _family_set_entries(family_sets: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for entry in family_sets.get("families") or []:
        family_id = entry.get("family_id")
        if isinstance(family_id, str) and family_id:
            entries[family_id] = entry
    return entries


def validate_llm_family_sets(family_sets: dict[str, Any], cases: tuple[BenchmarkCase, ...] | None = None) -> list[str]:
    benchmark = cases or benchmark_cases()
    entries = _family_set_entries(family_sets)
    errors: list[str] = []
    family_ids = sorted({case.family_id for case in benchmark})
    for family_id in family_ids:
        family_cases = [case for case in benchmark if case.family_id == family_id]
        entry = entries.get(family_id)
        if not entry:
            errors.append(f"llm_family_sets 缺少 family_id={family_id}")
            continue
        configured = set(entry.get("case_ids") or [])
        actual = {case.id for case in family_cases}
        missing_cases = actual - configured
        unknown_cases = configured - actual
        if missing_cases:
            errors.append(f"llm_family_sets family_id={family_id} 缺少 case：{', '.join(sorted(missing_cases))}")
        if unknown_cases:
            errors.append(f"llm_family_sets family_id={family_id} 包含未知或跨族 case：{', '.join(sorted(unknown_cases))}")
        styles = {case_style_for_sample(case, index, family_sets) for case in family_cases for index, _sample in enumerate(case.samples)}
        for required_style in ("seen_style", "unseen_style"):
            if required_style not in styles:
                errors.append(f"llm_family_sets family_id={family_id} 缺少 {required_style} 样本")
    return errors


def load_unseen_family_cases(path: Path | None = None) -> dict[str, Any]:
    unseen_path = path or UNSEEN_FAMILY_CASES_PATH
    if not unseen_path.exists():
        return {"schema_version": "unseen-family-cases-v1", "cases": []}
    return json.loads(unseen_path.read_text(encoding="utf-8"))


def load_family_capabilities(path: Path | None = None) -> dict[str, Any]:
    capabilities_path = path or FAMILY_CAPABILITIES_PATH
    if not capabilities_path.exists():
        return {"schema_version": "family-capabilities-v1", "families": []}
    return json.loads(capabilities_path.read_text(encoding="utf-8"))


def strong_family_ids_from_capabilities(capabilities: dict[str, Any] | None = None) -> set[str]:
    config = capabilities or load_family_capabilities()
    return {
        str(entry.get("family_id"))
        for entry in config.get("families") or []
        if entry.get("current_level") == "strong" and isinstance(entry.get("family_id"), str)
    }


def validate_unseen_family_cases(
    config: dict[str, Any],
    *,
    deterministic_cases: tuple[BenchmarkCase, ...] | None = None,
    capabilities: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if config.get("schema_version") != "unseen-family-cases-v1":
        errors.append("unseen_family_cases schema_version 必须是 unseen-family-cases-v1")
    cases = config.get("cases")
    if not isinstance(cases, list):
        return [*errors, "unseen_family_cases.cases 必须是列表"]

    deterministic_ids = {case.id for case in (deterministic_cases or benchmark_cases())}
    capabilities_config = capabilities or load_family_capabilities()
    capability_by_family = {
        str(entry.get("family_id")): entry
        for entry in capabilities_config.get("families") or []
        if isinstance(entry.get("family_id"), str)
    }
    strong_family_ids = strong_family_ids_from_capabilities(capabilities_config)
    seen_case_ids: set[str] = set()
    covered_strong_families: set[str] = set()

    for index, item in enumerate(cases):
        if not isinstance(item, dict):
            errors.append(f"unseen case #{index} 必须是对象")
            continue
        forbidden = sorted(FORBIDDEN_UNSEEN_CASE_FIELDS & set(item))
        if forbidden:
            errors.append(f"unseen case #{index} 不能包含 deterministic 代码字段：{', '.join(forbidden)}")
        case_id = item.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"unseen case #{index} 缺少 id")
        elif case_id in seen_case_ids:
            errors.append(f"unseen case id 重复：{case_id}")
        elif case_id in deterministic_ids:
            errors.append(f"unseen case id 不能与 deterministic fixture 重名：{case_id}")
        if isinstance(case_id, str):
            seen_case_ids.add(case_id)

        family_id = item.get("family_id")
        if not isinstance(family_id, str) or not family_id:
            errors.append(f"unseen case {case_id or index} 缺少 family_id")
            continue
        if family_id not in capability_by_family:
            errors.append(f"unseen case {case_id or index} 使用未知 family_id={family_id}")
        elif capability_by_family[family_id].get("current_level") != "strong":
            errors.append(f"unseen case {case_id or index} 只允许覆盖 strong family，当前 family_id={family_id}")
        else:
            covered_strong_families.add(family_id)

        for field in ("title", "problem", "family", "subfamily_id", "gate_layer", "support_level", "process_profile", "strategy"):
            if not isinstance(item.get(field), str) or not item.get(field):
                errors.append(f"unseen case {case_id or index} 缺少 {field}")
        if item.get("gate_layer") != "llm_eval":
            errors.append(f"unseen case {case_id or index} gate_layer 必须是 llm_eval")
        if item.get("support_level") != "strong":
            errors.append(f"unseen case {case_id or index} support_level 必须是 strong")

        samples = item.get("samples")
        if not isinstance(samples, list) or not samples:
            errors.append(f"unseen case {case_id or index} 至少需要 1 个 sample")
            continue
        for sample_index, sample in enumerate(samples):
            if not isinstance(sample, dict):
                errors.append(f"unseen case {case_id or index} sample {sample_index} 必须是对象")
                continue
            forbidden_sample = sorted(FORBIDDEN_UNSEEN_CASE_FIELDS & set(sample))
            if forbidden_sample:
                errors.append(
                    f"unseen case {case_id or index} sample {sample_index} 不能包含代码字段：{', '.join(forbidden_sample)}"
                )
            if "input_data" not in sample:
                errors.append(f"unseen case {case_id or index} sample {sample_index} 缺少 input_data")
            if "expected" not in sample:
                errors.append(f"unseen case {case_id or index} sample {sample_index} 缺少 expected")

    missing = strong_family_ids - covered_strong_families
    if missing:
        errors.append(f"unseen_family_cases 缺少 strong family：{', '.join(sorted(missing))}")
    return errors


def unseen_cases_from_config(config: dict[str, Any]) -> tuple[UnseenBenchmarkCase, ...]:
    cases: list[UnseenBenchmarkCase] = []
    for item in config.get("cases") or []:
        samples = tuple(
            BenchmarkInput(input_data=sample["input_data"], expected=sample.get("expected"))
            for sample in item.get("samples") or []
        )
        cases.append(
            UnseenBenchmarkCase(
                id=item["id"],
                title=item["title"],
                problem=item["problem"],
                family=item["family"],
                strategy=item["strategy"],
                samples=samples,
                family_id=item["family_id"],
                subfamily_id=item["subfamily_id"],
                gate_layer=item["gate_layer"],
                support_level=item["support_level"],
                process_profile=item["process_profile"],
            )
        )
    return tuple(cases)


def case_style_for_sample(case: BenchmarkCase, sample_index: int, family_sets: dict[str, Any] | None = None) -> str:
    config = family_sets or load_llm_family_sets()
    entry = _family_set_entries(config).get(case.family_id, {})
    sample_styles = entry.get("sample_styles") or config.get("default_sample_styles") or {}
    for style, indices in sample_styles.items():
        if isinstance(indices, list) and sample_index in indices:
            return str(style)
    return str(entry.get("remaining_sample_style") or config.get("remaining_sample_style") or "unseen_style")


def selected_cases(
    ids: set[str] | None = None,
    *,
    families: set[str] | None = None,
    gate_layers: set[str] | None = None,
    family_sets: dict[str, Any] | None = None,
    case_set: str = "deterministic",
    unseen_cases_config: dict[str, Any] | None = None,
) -> tuple[BenchmarkCase | UnseenBenchmarkCase, ...]:
    if case_set == "unseen":
        cases: tuple[BenchmarkCase | UnseenBenchmarkCase, ...] = unseen_cases_from_config(
            unseen_cases_config or load_unseen_family_cases()
        )
    elif case_set == "deterministic":
        cases = benchmark_cases()
    else:
        raise SystemExit(f"未知 case set：{case_set}")
    if not ids:
        found = cases
    else:
        found = tuple(case for case in cases if case.id in ids)
        missing = ids - {case.id for case in found}
        if missing:
            raise SystemExit(f"未知 benchmark case：{', '.join(sorted(missing))}")
    if families:
        allowed = set(families)
        known = {case.family_id for case in cases} | {case.family for case in cases}
        unknown = allowed - known
        if unknown:
            raise SystemExit(f"未知 family：{', '.join(sorted(unknown))}")
        found = tuple(case for case in found if case.family_id in allowed or case.family in allowed)
    if gate_layers:
        allowed_layers = set(gate_layers)
        found = tuple(case for case in found if case.gate_layer in allowed_layers)
    if family_sets is not None and case_set == "deterministic":
        configured_case_ids = {
            case_id
            for entry in (family_sets.get("families") or [])
            for case_id in (entry.get("case_ids") or [])
            if isinstance(case_id, str)
        }
        if configured_case_ids:
            found = tuple(case for case in found if case.id in configured_case_ids)
    if not found:
        raise SystemExit("没有匹配的 LLM benchmark case")
    return found


def selected_samples(case: BenchmarkCase | UnseenBenchmarkCase, args: argparse.Namespace) -> tuple[tuple[int, BenchmarkInput], ...]:
    if args.sample is not None:
        if args.sample < 0 or args.sample >= len(case.samples):
            raise SystemExit(f"{case.id} 不存在 sample {args.sample}，可用范围 0..{len(case.samples) - 1}")
        return ((args.sample, case.samples[args.sample]),)
    samples = case.samples if args.all_samples else case.samples[:1]
    return tuple(enumerate(samples))


def selected_tasks(
    cases: tuple[BenchmarkCase | UnseenBenchmarkCase, ...],
    args: argparse.Namespace,
) -> tuple[tuple[BenchmarkCase | UnseenBenchmarkCase, int, BenchmarkInput], ...]:
    tasks = tuple(
        (case, sample_index, sample)
        for case in cases
        for sample_index, sample in selected_samples(case, args)
    )
    return _limit_tasks_per_family(tasks, getattr(args, "limit_per_family", 0) or 0)


def _limit_tasks_per_family(
    tasks: tuple[tuple[BenchmarkCase | UnseenBenchmarkCase, int, BenchmarkInput], ...],
    limit_per_family: int,
) -> tuple[tuple[BenchmarkCase | UnseenBenchmarkCase, int, BenchmarkInput], ...]:
    if limit_per_family <= 0:
        return tasks
    grouped: OrderedDict[str, OrderedDict[str, list[tuple[BenchmarkCase | UnseenBenchmarkCase, int, BenchmarkInput]]]] = OrderedDict()
    for task in tasks:
        case = task[0]
        grouped.setdefault(case.family_id, OrderedDict()).setdefault(case.subfamily_id, []).append(task)

    limited: list[tuple[BenchmarkCase | UnseenBenchmarkCase, int, BenchmarkInput]] = []
    for subfamilies in grouped.values():
        selected = 0
        while selected < limit_per_family and any(queue for queue in subfamilies.values()):
            for queue in subfamilies.values():
                if not queue:
                    continue
                limited.append(queue.pop(0))
                selected += 1
                if selected >= limit_per_family:
                    break
    return tuple(limited)


def make_request(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    *,
    solutions: int,
    teaching_enrichment: bool = True,
) -> ProblemInput:
    return ProblemInput(
        problem=case.problem,
        input_data=sample.input_data,
        strategy_hint=case.strategy,
        expected_result=sample.expected,
        solution_count=solutions,
        teaching_enrichment=teaching_enrichment,
        case_id=case.id,
        family_id=case.family_id,
        subfamily_id=case.subfamily_id,
    )


def benchmark_condition(args: argparse.Namespace) -> str:
    return getattr(args, "condition", "algolab_full")


ProgressCallback = Callable[[dict[str, Any]], None]


def result_metadata(case: BenchmarkCase | UnseenBenchmarkCase, sample_index: int, args: argparse.Namespace) -> dict[str, Any]:
    family_sets = getattr(args, "family_sets_config", None)
    case_set = getattr(args, "case_set", "deterministic")
    case_style = "unseen_style" if case_set == "unseen" else case_style_for_sample(case, sample_index, family_sets)
    return {
        "family_id": case.family_id,
        "subfamily_id": case.subfamily_id,
        "gate_layer": case.gate_layer,
        "support_level": case.support_level,
        "process_profile": case.process_profile,
        "case_set": case_set,
        "case_style": case_style,
    }


def run_one(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    started = time.time()
    clear_model_calls()
    request = make_request(
        case,
        sample,
        solutions=args.solutions,
        teaching_enrichment=getattr(args, "teaching_enrichment", True),
    )
    output_stem = f"llm_{case.id}_{sample_index}"
    output_html = args.output_dir / f"{output_stem}.html"
    phase_log: list[dict[str, Any]] = []
    repair_types: list[str] = []
    metadata = result_metadata(case, sample_index, args)

    def record_progress(event: dict[str, Any]) -> None:
        phase_log.append(event)
        if progress is not None:
            progress(event)

    try:
        candidate_summary: dict[str, Any] = {}
        artifact = build_artifact_timed(
            request,
            max_rounds=args.max_rounds,
            max_candidates=getattr(args, "max_candidates", 1),
            progress=record_progress,
            strict_warnings=args.strict_warnings,
            repair_failure_types_out=repair_types,
            spec_log_dir=args.output_dir,
            spec_log_stem=output_stem,
            candidate_summary_out=candidate_summary,
        )
        timed_phase("render", record_progress, lambda: save_html(artifact, output_html))
        variants = [
            {
                "id": variant.id,
                "name": variant.name,
                "result": variant.result,
                "steps": len(variant.trace.events) if variant.trace else 0,
            }
            for variant in artifact.variants
        ]
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "ok": artifact.validation.release_gate.release_ready,
            "release_gate": artifact.validation.release_gate.model_dump(),
            "checks": artifact.validation.checks,
            "warnings": artifact.validation.warnings,
            "errors": artifact.validation.errors,
            "variants": variants,
            "html": str(output_html),
            "json": str(output_html.with_suffix(".json")),
            "phase_timings": completed_phase_timings(phase_log),
            "last_phase": last_phase(phase_log) or "done",
            "duration_s": round(time.time() - started, 3),
            "failure_type": "",
            "repair_failure_types": repair_types,
            "candidate_summary": candidate_summary,
            "model_calls": consume_model_calls(),
        }
    except Exception as exc:
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "failure_type": classify_failure(f"{type(exc).__name__}: {exc}"),
            "phase_timings": completed_phase_timings(phase_log),
            "last_phase": last_phase(phase_log),
            "duration_s": round(time.time() - started, 3),
            "repair_failure_types": repair_types,
            "candidate_summary": locals().get("candidate_summary", {}),
            "model_calls": consume_model_calls(),
        }


def build_artifact_timed(
    request: ProblemInput,
    max_rounds: int = 2,
    max_candidates: int = 1,
    progress: ProgressCallback | None = None,
    strict_warnings: bool = False,
    repair_failure_types_out: list[str] | None = None,
    spec_log_dir: Path | None = None,
    spec_log_stem: str = "",
    candidate_summary_out: dict[str, Any] | None = None,
) -> BuildArtifact:
    if max_rounds < 0:
        raise ValueError("max_rounds 不能为负数")
    if max_candidates < 1:
        raise ValueError("max_candidates 至少为 1")

    stats: dict[str, Any] = {
        "max_candidates": max_candidates,
        "repairs_per_candidate": max_rounds,
        "candidates_attempted": 0,
        "materialize_attempts": 0,
        "repair_attempts": 0,
        "selected_candidate": None,
        "selected_round": None,
        "selection": "failed",
    }
    last_errors: list[str] = []
    candidate_failures: list[dict[str, Any]] = []

    for candidate_idx in range(max_candidates):
        stats["candidates_attempted"] += 1
        candidate_label = _candidate_label(candidate_idx, max_candidates)
        generate_phase = _candidate_phase("generate", candidate_idx, max_candidates)
        try:
            spec = timed_phase(generate_phase, progress, lambda: generate_solution_spec(request))
            _write_spec_snapshot(
                spec_log_dir,
                spec_log_stem,
                _candidate_snapshot_label(candidate_label, "round0_generation_spec"),
                spec,
            )
        except Exception as exc:
            last_errors = [f"{type(exc).__name__}: {exc}"]
            candidate_failures.append({"candidate": candidate_idx, "round": -1, "errors": last_errors})
            _write_spec_snapshot(
                spec_log_dir,
                spec_log_stem,
                _candidate_snapshot_label(candidate_label, "generation_errors"),
                {"errors": last_errors, "release_ready": False},
            )
            continue

        for round_idx in range(max_rounds + 1):
            try:
                artifact, errors = timed_phase(
                    _candidate_phase(f"materialize_round_{round_idx}", candidate_idx, max_candidates),
                    progress,
                    lambda spec=spec: _try_materialize(request, spec),
                )
                stats["materialize_attempts"] += 1
            except Exception as exc:
                artifact = None
                errors = [f"{type(exc).__name__}: {exc}"]

            last_errors = _release_blocking_errors(artifact, errors or [], strict_warnings=strict_warnings)
            if artifact is not None and not last_errors:
                stats["selected_candidate"] = candidate_idx
                stats["selected_round"] = round_idx
                stats["selection"] = _selection_label(candidate_idx, round_idx)
                _copy_candidate_summary(stats, candidate_summary_out)
                _write_spec_snapshot(
                    spec_log_dir,
                    spec_log_stem,
                    _candidate_snapshot_label(candidate_label, f"round{round_idx}_materialize_ok"),
                    {"errors": [], "release_ready": True, "candidate": candidate_idx, "round": round_idx},
                )
                return artifact

            candidate_failures.append({"candidate": candidate_idx, "round": round_idx, "errors": last_errors})
            _write_spec_snapshot(
                spec_log_dir,
                spec_log_stem,
                _candidate_snapshot_label(candidate_label, f"round{round_idx}_materialize_errors"),
                {"errors": last_errors, "release_ready": False, "candidate": candidate_idx, "round": round_idx},
            )
            if round_idx < max_rounds:
                if repair_failure_types_out is not None:
                    for failure_type in repair_failure_types(last_errors):
                        if failure_type not in repair_failure_types_out:
                            repair_failure_types_out.append(failure_type)
                try:
                    spec = timed_phase(
                        _candidate_phase(f"repair_round_{round_idx}", candidate_idx, max_candidates),
                        progress,
                        lambda spec=spec, errors=last_errors: repair_solution_spec(request, spec, errors),
                    )
                    stats["repair_attempts"] += 1
                    _write_spec_snapshot(
                        spec_log_dir,
                        spec_log_stem,
                        _candidate_snapshot_label(candidate_label, f"round{round_idx + 1}_repair_spec"),
                        spec,
                    )
                except Exception as exc:
                    last_errors = [f"{type(exc).__name__}: {exc}"]
                    candidate_failures.append({"candidate": candidate_idx, "round": round_idx, "errors": last_errors})
                    _write_spec_snapshot(
                        spec_log_dir,
                        spec_log_stem,
                        _candidate_snapshot_label(candidate_label, f"round{round_idx}_repair_errors"),
                        {"errors": last_errors, "release_ready": False, "candidate": candidate_idx, "round": round_idx},
                    )
                    break

    stats["candidate_failures"] = candidate_failures[-max_candidates:]
    _copy_candidate_summary(stats, candidate_summary_out)
    raise BuildError("没有生成可发布产物：\n" + "\n".join(last_errors))


def _release_blocking_errors(
    artifact: BuildArtifact | None,
    errors: list[str],
    *,
    strict_warnings: bool,
) -> list[str]:
    if artifact is None:
        return errors or ["materialize 未返回 artifact"]
    if errors:
        return errors
    if not artifact.validation.release_gate.release_ready:
        return [
            *artifact.validation.errors,
            *artifact.validation.release_gate.blocking_reasons,
        ] or ["release gate 未通过"]
    if strict_warnings and artifact.validation.warnings:
        return [f"严格模式拒绝 warning：{warning}" for warning in artifact.validation.warnings]
    return []


def _candidate_label(candidate_idx: int, max_candidates: int) -> str:
    return "" if max_candidates == 1 else f"candidate{candidate_idx}"


def _candidate_phase(base: str, candidate_idx: int, max_candidates: int) -> str:
    return base if max_candidates == 1 else f"candidate_{candidate_idx}_{base}"


def _candidate_snapshot_label(candidate_label: str, label: str) -> str:
    return f"{candidate_label}_{label}" if candidate_label else label


def _selection_label(candidate_idx: int, round_idx: int) -> str:
    if candidate_idx == 0 and round_idx == 0:
        return "first_try"
    if candidate_idx == 0:
        return "repair"
    if round_idx == 0:
        return "regen_first_try"
    return "regen_repair"


def _copy_candidate_summary(stats: dict[str, Any], out: dict[str, Any] | None) -> None:
    if out is None:
        return
    out.clear()
    out.update(stats)


def _write_spec_snapshot(base_dir: Path | None, stem: str, label: str, payload: Any) -> None:
    if base_dir is None or not stem:
        return
    try:
        snapshot_dir = base_dir / "spec_rounds"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        path = snapshot_dir / f"{stem}_{label}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception:
        return


def timed_phase(name: str, progress: ProgressCallback | None, fn: Callable[[], Any]) -> Any:
    emit_progress(progress, {"type": "progress", "event": "start", "phase": name, "at": round(time.time(), 3)})
    started = time.time()
    status = "ok"
    try:
        return fn()
    except Exception:
        status = "error"
        raise
    finally:
        emit_progress(
            progress,
            {
                "type": "progress",
                "event": "end",
                "phase": name,
                "status": status,
                "duration_s": round(time.time() - started, 3),
                "at": round(time.time(), 3),
            },
        )


def emit_progress(progress: ProgressCallback | None, event: dict[str, Any]) -> None:
    if progress is None:
        return
    try:
        progress(event)
    except Exception:
        return


def completed_phase_timings(phase_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "phase": event["phase"],
            "duration_s": event["duration_s"],
            "status": event.get("status", ""),
        }
        for event in phase_log
        if event.get("event") == "end" and "duration_s" in event
    ]


def average_duration(results: list[dict[str, Any]]) -> float:
    durations = [float(item.get("duration_s") or 0) for item in results]
    return round(sum(durations) / len(durations), 3) if durations else 0.0


def summarize_phase_timings(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    phases: dict[str, list[float]] = {}
    for item in results:
        for phase in item.get("phase_timings") or []:
            name = phase.get("phase")
            duration = phase.get("duration_s")
            if isinstance(name, str) and isinstance(duration, (int, float)):
                phases.setdefault(name, []).append(float(duration))
    return {
        name: {
            "count": len(values),
            "avg_s": round(sum(values) / len(values), 3),
            "max_s": round(max(values), 3),
        }
        for name, values in sorted(phases.items())
        if values
    }


def _model_calls_from_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for item in results:
        for call in item.get("model_calls") or []:
            if isinstance(call, dict):
                calls.append(call)
    return calls


def summarize_model_usage(results: list[dict[str, Any]]) -> dict[str, Any]:
    calls = _model_calls_from_results(results)
    call_count = len(calls)
    usage_calls = [call for call in calls if call.get("usage_available") is True]
    all_usage_available = call_count > 0 and len(usage_calls) == call_count
    duration_s = round(sum(float(call.get("duration_s") or 0.0) for call in calls), 3)
    total_tokens = sum(int(call["total_tokens"]) for call in usage_calls) if all_usage_available else None
    by_kind: dict[str, dict[str, Any]] = {}
    for call in calls:
        kind = str(call.get("kind") or "unknown")
        row = by_kind.setdefault(
            kind,
            {
                "call_count": 0,
                "usage_available": True,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "duration_s": 0.0,
            },
        )
        row["call_count"] += 1
        row["duration_s"] = round(float(row["duration_s"]) + float(call.get("duration_s") or 0.0), 3)
        if call.get("usage_available") is True:
            row["prompt_tokens"] += int(call.get("prompt_tokens") or 0)
            row["completion_tokens"] += int(call.get("completion_tokens") or 0)
            row["total_tokens"] += int(call.get("total_tokens") or 0)
        else:
            row["usage_available"] = False
            row["prompt_tokens"] = None
            row["completion_tokens"] = None
            row["total_tokens"] = None
    for row in by_kind.values():
        count = row["call_count"]
        row["avg_duration_s"] = round(row["duration_s"] / count, 6) if count else 0.0
        row["avg_total_tokens"] = (
            round(row["total_tokens"] / count, 6)
            if row.get("usage_available") is True and count
            else None
        )
    return {
        "usage_available": all_usage_available,
        "usage_available_rate": (len(usage_calls) / call_count) if call_count else 0.0,
        "call_count": call_count,
        "prompt_tokens": sum(int(call["prompt_tokens"]) for call in usage_calls) if all_usage_available else None,
        "completion_tokens": sum(int(call["completion_tokens"]) for call in usage_calls) if all_usage_available else None,
        "total_tokens": total_tokens,
        "duration_s": duration_s,
        "avg_duration_s": (duration_s / call_count) if call_count else 0.0,
        "avg_total_tokens": (total_tokens / call_count) if all_usage_available and call_count else None,
        "by_kind": dict(sorted(by_kind.items())),
        "estimated_cost": None,
        "cost_estimation_available": False,
        "pricing_source": "",
    }


def summarize_candidate_selection(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item.get("ok"))
    summaries = [item.get("candidate_summary") or {} for item in results]
    candidates_used = [
        int(summary.get("candidates_attempted") or 0)
        for summary in summaries
        if summary.get("candidates_attempted") is not None
    ]
    llm_calls = [len(item.get("model_calls") or []) for item in results]
    selection_counts: dict[str, int] = {}
    for item, summary in zip(results, summaries):
        selection = str(summary.get("selection") or ("failed" if not item.get("ok") else "unknown"))
        selection_counts[selection] = selection_counts.get(selection, 0) + 1
    return {
        "total": total,
        "final_pass": passed,
        "first_try_pass": selection_counts.get("first_try", 0),
        "repair_pass": selection_counts.get("repair", 0),
        "regen_pass": selection_counts.get("regen_first_try", 0) + selection_counts.get("regen_repair", 0),
        "regen_first_try_pass": selection_counts.get("regen_first_try", 0),
        "regen_repair_pass": selection_counts.get("regen_repair", 0),
        "failed": total - passed,
        "selection_counts": dict(sorted(selection_counts.items())),
        "avg_candidates_used": round(sum(candidates_used) / len(candidates_used), 6) if candidates_used else 0.0,
        "avg_llm_calls_per_case": round(sum(llm_calls) / len(llm_calls), 6) if llm_calls else 0.0,
        "repair_attempts": sum(int(summary.get("repair_attempts") or 0) for summary in summaries),
        "materialize_attempts": sum(int(summary.get("materialize_attempts") or 0) for summary in summaries),
    }


def last_phase(phase_log: list[dict[str, Any]]) -> str:
    for event in reversed(phase_log):
        phase = event.get("phase")
        if isinstance(phase, str):
            suffix = "中" if event.get("event") == "start" else event.get("status", "")
            return f"{phase}:{suffix}" if suffix else phase
    return ""


def last_phase_elapsed_s(phase_log: list[dict[str, Any]], now: float | None = None) -> float:
    now = now or time.time()
    active: dict[str, float] = {}
    for event in phase_log:
        phase = event.get("phase")
        if not isinstance(phase, str):
            continue
        if event.get("event") == "start" and isinstance(event.get("at"), (int, float)):
            active[phase] = float(event["at"])
        elif event.get("event") == "end":
            active.pop(phase, None)
    if not active:
        return 0.0
    _phase, started_at = next(reversed(active.items()))
    return round(max(0.0, now - started_at), 3)


def _run_one_worker(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
    queue: mp.Queue,
):
    def progress(event: dict[str, Any]) -> None:
        queue.put({"type": "progress", "event": event})

    queue.put({"type": "result", "result": run_one(case, sample, sample_index, args, progress=progress)})


def run_one_with_timeout(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if args.timeout_s <= 0:
        return run_one(case, sample, sample_index, args)
    started = time.time()
    metadata = result_metadata(case, sample_index, args)
    result_queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_run_one_worker, args=(case, sample, sample_index, args, result_queue))
    process.start()
    phase_log: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    deadline = time.time() + args.timeout_s
    while process.is_alive() and time.time() < deadline:
        process.join(min(1.0, max(0.0, deadline - time.time())))
        result = drain_worker_queue(result_queue, phase_log) or result
    result = drain_worker_queue(result_queue, phase_log) or result
    if result is not None:
        return result
    if process.is_alive():
        process.terminate()
        process.join(2)
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "ok": False,
            "error": f"TimeoutError: LLM benchmark 超过 {args.timeout_s} 秒",
            "failure_type": "timeout",
            "phase_timings": completed_phase_timings(phase_log),
            "last_phase": last_phase(phase_log),
            "last_phase_elapsed_s": last_phase_elapsed_s(phase_log),
            "duration_s": round(time.time() - started, 3),
            "model_calls": [],
        }
    return {
        "case_id": case.id,
        "title": case.title,
        "family": case.family,
        **metadata,
        "sample_index": sample_index,
        "input_data": sample.input_data,
        "expected": sample.expected,
        "model": _model_name(),
        "condition": benchmark_condition(args),
        "ok": False,
        "error": "RuntimeError: LLM benchmark 子进程无返回",
        "failure_type": "runner_error",
        "phase_timings": completed_phase_timings(phase_log),
        "last_phase": last_phase(phase_log),
        "last_phase_elapsed_s": last_phase_elapsed_s(phase_log),
        "duration_s": round(time.time() - started, 3),
        "model_calls": [],
    }


def drain_worker_queue(result_queue: mp.Queue, phase_log: list[dict[str, Any]]) -> dict[str, Any] | None:
    result: dict[str, Any] | None = None
    while True:
        try:
            item = result_queue.get_nowait()
        except queue.Empty:
            break
        if not isinstance(item, dict):
            continue
        if item.get("type") == "progress" and isinstance(item.get("event"), dict):
            phase_log.append(item["event"])
        elif item.get("type") == "result" and isinstance(item.get("result"), dict):
            result = item["result"]
    return result


def classify_failure(message: str) -> str:
    text = message.lower()
    explicit = _explicit_failure_type(message)
    if explicit in DEMO_FAILURE_TYPES:
        return explicit
    if "algolab_llm_api_key" in text or "api_key" in text or "环境变量" in message or "api key" in text:
        return "configuration"
    if "arrearage" in text or "access denied" in text or "account is in good standing" in text:
        return "configuration"
    if "timeout" in text or "超时" in message or "超过" in message:
        return "timeout"
    process_failure_type = process_failure_type_for_message(message)
    if process_failure_type:
        return process_failure_type
    if "严格模式拒绝 warning" in message or "warning" in text:
        return "visual_warning"
    if "scene" in text or "layout" in text or "渲染" in message or "视觉" in message:
        return "visual_scene"
    if "verifier" in text or "expected" in text or "结果" in message:
        return "correctness"
    if "执行失败" in message or "sandbox" in text or "nameerror" in text or "syntaxerror" in text:
        return "execution"
    if "validation error" in text or "semantictrace" in text or "schema" in text:
        return "trace_schema"
    if "js errors" in text or "browser" in text:
        return "browser"
    return "generation"


def _explicit_failure_type(message: str) -> str:
    marker = "failure_type="
    if marker not in message:
        return ""
    value = message.split(marker, 1)[1]
    return value.split(":", 1)[0].split(";", 1)[0].strip()


def summarize_failures(results: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        if item.get("ok"):
            continue
        failure_type = item.get("failure_type") or classify_failure(item.get("error") or "; ".join(item.get("errors", [])))
        item["failure_type"] = failure_type
        summary[failure_type] = summary.get(failure_type, 0) + 1
    return summary


def summarize_field_counts(results: list[dict[str, Any]], field: str, default: str = "unknown") -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        value = str(item.get(field) or default)
        summary[value] = summary.get(value, 0) + 1
    return dict(sorted(summary.items()))


def build_family_summary(
    results: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
    started_at: str,
    ended_at: str,
) -> dict[str, Any]:
    condition = benchmark_condition(args)
    rows: dict[str, dict[str, Any]] = {}
    for item in results:
        family_id = str(item.get("family_id") or item.get("family") or "unknown")
        row = rows.setdefault(
            family_id,
            {
                "family_id": family_id,
                "family": item.get("family") or family_id,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failure_types": {},
                "repair_failure_types": {},
                "repair_attempted": 0,
                "repair_successes": 0,
                "subfamilies": {},
                "gate_layers": {},
                "case_sets": {},
                "case_styles": {},
                "cases": {},
            },
        )
        row["family"] = row["family"] or item.get("family") or family_id
        row["total"] += 1
        if item.get("ok"):
            row["passed"] += 1
        else:
            row["failed"] += 1
            failure_type = item.get("failure_type") or classify_failure(item.get("error") or "; ".join(item.get("errors", [])))
            item["failure_type"] = failure_type
            row["failure_types"][failure_type] = row["failure_types"].get(failure_type, 0) + 1

        if _result_attempted_repair(item):
            row["repair_attempted"] += 1
            if item.get("ok"):
                row["repair_successes"] += 1
        for failure_type in item.get("repair_failure_types") or []:
            row["repair_failure_types"][failure_type] = row["repair_failure_types"].get(failure_type, 0) + 1

        subfamily_id = str(item.get("subfamily_id") or "unknown")
        sub = row["subfamilies"].setdefault(subfamily_id, {"subfamily_id": subfamily_id, "total": 0, "passed": 0, "failed": 0})
        sub["total"] += 1
        if item.get("ok"):
            sub["passed"] += 1
        else:
            sub["failed"] += 1

        gate_layer = str(item.get("gate_layer") or "unknown")
        row["gate_layers"][gate_layer] = row["gate_layers"].get(gate_layer, 0) + 1
        case_set = str(item.get("case_set") or "deterministic")
        row["case_sets"][case_set] = row["case_sets"].get(case_set, 0) + 1
        case_style = str(item.get("case_style") or "unknown")
        row["case_styles"][case_style] = row["case_styles"].get(case_style, 0) + 1
        case_id = str(item.get("case_id") or "unknown")
        row["cases"][case_id] = row["cases"].get(case_id, 0) + 1

    families: list[dict[str, Any]] = []
    for row in rows.values():
        total = row["total"]
        repair_attempted = row["repair_attempted"]
        subfamilies = []
        for sub in row["subfamilies"].values():
            sub_total = sub["total"]
            subfamilies.append(
                {
                    **sub,
                    "pass_rate": round(sub["passed"] / sub_total, 6) if sub_total else None,
                }
            )
        families.append(
            {
                "family_id": row["family_id"],
                "family": row["family"],
                "total": total,
                "passed": row["passed"],
                "failed": row["failed"],
                "generation_success_rate": round(row["passed"] / total, 6) if total else None,
                "repair_attempted": repair_attempted,
                "repair_successes": row["repair_successes"],
                "repair_success_rate": round(row["repair_successes"] / repair_attempted, 6) if repair_attempted else None,
                "failure_types": dict(sorted(row["failure_types"].items())),
                "repair_failure_types": dict(sorted(row["repair_failure_types"].items())),
                "subfamilies": sorted(subfamilies, key=lambda item: item["subfamily_id"]),
                "gate_layers": dict(sorted(row["gate_layers"].items())),
                "case_sets": dict(sorted(row["case_sets"].items())),
                "case_styles": dict(sorted(row["case_styles"].items())),
                "cases": dict(sorted(row["cases"].items())),
            }
        )
    families.sort(key=lambda item: item["family_id"])
    total = len(results)
    passed = sum(1 for item in results if item.get("ok"))
    return {
        "kind": "llm_family_summary",
        "schema_version": "llm-family-summary-v1",
        "started_at": started_at,
        "ended_at": ended_at,
        "condition": condition,
        "config": {
            "family": getattr(args, "family", []),
            "gate_layer": getattr(args, "gate_layer", []),
            "limit_per_family": getattr(args, "limit_per_family", 0),
            "all_samples": getattr(args, "all_samples", False),
            "sample": getattr(args, "sample", None),
            "case_set": getattr(args, "case_set", "deterministic"),
            "family_sets": str(getattr(args, "family_sets", LLM_FAMILY_SETS_PATH)),
            "unseen_cases": str(getattr(args, "unseen_cases", UNSEEN_FAMILY_CASES_PATH)),
        },
        "summary": {
            "family_count": len(families),
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "generation_success_rate": round(passed / total, 6) if total else None,
            "failure_types": summarize_failures(results),
            "repair_failure_types": summarize_repair_failure_types(results),
            "case_sets": summarize_field_counts(results, "case_set", "deterministic"),
            "case_styles": summarize_field_counts(results, "case_style"),
            "model_usage": summarize_model_usage(results),
        },
        "families": families,
    }


def _result_attempted_repair(item: dict[str, Any]) -> bool:
    if item.get("repair_failure_types"):
        return True
    for phase in item.get("phase_timings") or []:
        name = phase.get("phase") if isinstance(phase, dict) else ""
        if isinstance(name, str) and (name.startswith("repair_round_") or "_repair_round_" in name):
            return True
    return False


def browser_smoke_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    html_paths = [Path(item["html"]) for item in results if item.get("ok") and item.get("html")]
    return browser_smoke_html_paths(html_paths)


def browser_smoke_html_paths(html_paths: list[Path]) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    checked: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for path in html_paths:
            checked.append(_check_html_path(browser, path))
        browser.close()
    return checked


def _check_html_path(browser: Any, path: Path) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        page.goto(path.resolve().as_uri())
        page.wait_for_timeout(300)
        title = page.locator("#title").inner_text().strip()
        counter = page.locator("#counter").inner_text().strip()
        canvas_text = page.locator("#canvas").inner_text().strip()
        ok = bool(title and "/" in counter and canvas_text and not errors)
        return {
            "html": str(path),
            "ok": ok,
            "title": title,
            "counter": counter,
            "canvas_chars": len(canvas_text),
            "errors": errors,
        }
    except Exception as exc:
        return {"html": str(path), "ok": False, "errors": [f"{type(exc).__name__}: {exc}"]}
    finally:
        page.close()


def write_report(
    results: list[dict[str, Any]],
    output_dir: Path,
    *,
    args: argparse.Namespace,
    started_at: str,
    ended_at: str,
    browser_checks: list[dict[str, Any]] | None = None,
) -> Path:
    condition = benchmark_condition(args)
    for item in results:
        item.setdefault("condition", condition)
    passed = sum(1 for item in results if item.get("ok"))
    total = len(results)
    failure_summary = summarize_failures(results)
    repair_failure_summary = summarize_repair_failure_types(results)
    phase_summary = summarize_phase_timings(results)
    model_usage = summarize_model_usage(results)
    candidate_selection = summarize_candidate_selection(results)
    family_summary = build_family_summary(results, args=args, started_at=started_at, ended_at=ended_at)
    family_summary_path = output_dir / "family_summary.json"
    family_summary_path.write_text(json.dumps(family_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    config = {
        "cases": args.case,
        "sample": args.sample,
        "all_samples": args.all_samples,
        "solutions": args.solutions,
        "max_rounds": args.max_rounds,
        "max_candidates": getattr(args, "max_candidates", 1),
        "timeout_s": args.timeout_s,
        "strict_warnings": args.strict_warnings,
        "browser_smoke": args.browser_smoke,
        "teaching_enrichment": getattr(args, "teaching_enrichment", True),
        "write_each": args.write_each,
        "concurrency": getattr(args, "concurrency", 1),
        "family": getattr(args, "family", []),
        "gate_layer": getattr(args, "gate_layer", []),
        "limit_per_family": getattr(args, "limit_per_family", 0),
        "case_set": getattr(args, "case_set", "deterministic"),
        "family_sets": str(getattr(args, "family_sets", LLM_FAMILY_SETS_PATH)),
        "unseen_cases": str(getattr(args, "unseen_cases", UNSEEN_FAMILY_CASES_PATH)),
        "benchmark_condition": benchmark_condition(args),
        "llm": llm_config(),
        "model": _model_name(),
    }
    for key in (
        "baseline",
        "ablation",
        "process_validator_enabled",
        "scenegraph_compiler_enabled",
        "direct_html_baseline",
        "expected_visible_to_model",
        "direct_html_repair_enabled",
        "direct_html_browser_repair_enabled",
        "llm_max_tokens",
        "direct_html_llm_max_tokens",
        "trace_only_renderer_enabled",
    ):
        if hasattr(args, key):
            config[key] = getattr(args, key)

    report = {
        "kind": "llm_benchmark_report",
        "cached": False,
        "started_at": started_at,
        "ended_at": ended_at,
        "config": config,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0,
        "avg_duration_s": average_duration(results),
        "failure_summary": failure_summary,
        "repair_failure_summary": repair_failure_summary,
        "case_set_summary": summarize_field_counts(results, "case_set", "deterministic"),
        "case_style_summary": summarize_field_counts(results, "case_style"),
        "family_summary_path": str(family_summary_path),
        "family_summary": family_summary["families"],
        "phase_summary": phase_summary,
        "model_usage": model_usage,
        "candidate_selection": candidate_selection,
        "browser_smoke": browser_checks or [],
        "results": results,
    }
    path = output_dir / "llm_benchmark_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = output_dir / "llm_benchmark_report.md"
    lines = [
        "# LLM Benchmark Report",
        "",
        f"- 缓存：未使用",
        f"- 模型：{_model_name()}",
        f"- 总数：{total}",
        f"- 通过：{passed}",
        f"- 失败：{total - passed}",
        f"- 通过率：{passed / total:.2%}" if total else "- 通过率：N/A",
        f"- 平均耗时：{average_duration(results)}s/case",
        f"- LLM calls：{model_usage['call_count']}",
        f"- Token usage：{model_usage['total_tokens'] if model_usage['usage_available'] else 'usage_available=false'}",
        f"- 候选策略：max_candidates={getattr(args, 'max_candidates', 1)}, repairs_per_candidate={args.max_rounds}",
        f"- 候选命中：first_try={candidate_selection['first_try_pass']}, repair={candidate_selection['repair_pass']}, regen={candidate_selection['regen_pass']}, failed={candidate_selection['failed']}",
        f"- 平均候选数：{candidate_selection['avg_candidates_used']}",
        f"- 平均 LLM calls/题：{candidate_selection['avg_llm_calls_per_case']}",
        f"- Case set：{getattr(args, 'case_set', 'deterministic')}",
        f"- 严格 warning：{'开启' if args.strict_warnings else '关闭'}",
        f"- 浏览器检查：{'开启' if args.browser_smoke else '关闭'}",
        "",
        "| Case | Sample | Family | Case Set | Style | Status | Failure | Duration | Last Phase | Artifact |",
        "|---|---:|---|---|---|---|---|---:|---|---|",
    ]
    for item in results:
        status = "PASS" if item.get("ok") else "FAIL"
        artifact = item.get("html", "")
        failure = item.get("failure_type", "")
        last = item.get("last_phase", "")
        elapsed = item.get("last_phase_elapsed_s")
        last_phase_text = f"{last} ({elapsed}s)" if elapsed else str(last)
        lines.append(
            f"| {item['case_id']} | {item['sample_index']} | {item['family']} | "
            f"{item.get('case_set', 'deterministic')} | {item.get('case_style', '')} | {status} | "
            f"{failure} | {item.get('duration_s', 0)}s | {last_phase_text} | {artifact} |"
        )
    if phase_summary:
        lines.extend(["", "## Phase Timings", "", "| Phase | Count | Avg | Max |", "|---|---:|---:|---:|"])
        for phase, stat in phase_summary.items():
            lines.append(f"| {phase} | {stat['count']} | {stat['avg_s']}s | {stat['max_s']}s |")
    if family_summary["families"]:
        lines.extend(
            [
                "",
                "## Family Summary",
                "",
                "| Family | Total | Pass Rate | Repair Success | Failure Types | Case Sets | Styles |",
                "|---|---:|---:|---:|---|---|---|",
            ]
        )
        for family in family_summary["families"]:
            repair_rate = family["repair_success_rate"]
            repair_text = "N/A" if repair_rate is None else f"{repair_rate:.2%}"
            failure_text = ", ".join(f"{key}:{value}" for key, value in family["failure_types"].items())
            set_text = ", ".join(f"{key}:{value}" for key, value in family["case_sets"].items())
            style_text = ", ".join(f"{key}:{value}" for key, value in family["case_styles"].items())
            lines.append(
                f"| {family['family']} | {family['total']} | {family['generation_success_rate']:.2%} | "
                f"{repair_text} | {failure_text} | {set_text} | {style_text} |"
            )
    if browser_checks:
        lines.extend(["", "## Browser Smoke", "", "| HTML | Status | Canvas Chars |", "|---|---|---:|"])
        for item in browser_checks:
            lines.append(f"| {item.get('html', '')} | {'PASS' if item.get('ok') else 'FAIL'} | {item.get('canvas_chars', 0)} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="运行真实 LLM 生成 benchmark，不使用缓存")
    parser.add_argument("--case", action="append", default=[], help="只运行指定 case id，可重复传入")
    parser.add_argument("--sample", type=int, default=None, help="只运行指定 sample index；默认首个输入，配合 --all-samples 时不使用")
    parser.add_argument("--all-samples", action="store_true", help="运行每个 case 的所有输入；默认只跑首个输入")
    parser.add_argument("--solutions", type=int, default=1, help="每个输入请求的解法数量；benchmark 默认用 1 个解法降低模型超时")
    parser.add_argument("--max-rounds", type=int, default=2, help="生成失败后的修复轮数")
    parser.add_argument("--max-candidates", type=int, default=1, help="每个样例最多独立重新生成多少个候选；每个候选各自执行 max-rounds 轮修复")
    parser.add_argument("--timeout-s", type=int, default=1200, help="单个样例最大运行秒数；0 表示不限制")
    parser.add_argument("--strict-warnings", action=argparse.BooleanOptionalAction, default=True, help="有 warning 时判为失败")
    parser.add_argument("--browser-smoke", action=argparse.BooleanOptionalAction, default=False, help="对本次通过的 HTML 产物执行浏览器 smoke")
    parser.add_argument(
        "--teaching-enrichment",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否在 trace 校验后调用 LLM 生成讲解和交互增强；默认开启，可用 --no-teaching-enrichment 关闭",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/llm_benchmark"), help="输出目录")
    parser.add_argument("--fail-fast", action="store_true", help="遇到第一个失败立即退出")
    parser.add_argument("--write-each", action=argparse.BooleanOptionalAction, default=True, help="每个样例结束后立即写入当前 report")
    parser.add_argument("--concurrency", type=int, default=1, help="并发运行的样例数；每个样例仍有独立 timeout")
    parser.add_argument("--family", action="append", default=[], help="只运行指定 family_id 或中文 family 名，可重复传入")
    parser.add_argument(
        "--gate-layer",
        action="append",
        default=[],
        choices=["smoke", "family_core", "expansion", "property", "llm_eval"],
        help="只运行指定 gate layer，可重复传入",
    )
    parser.add_argument("--limit-per-family", type=int, default=0, help="每个 family 最多运行多少个样例；0 表示不限制")
    parser.add_argument(
        "--case-set",
        default="deterministic",
        choices=["deterministic", "unseen"],
        help="选择 deterministic fixture 或独立 unseen family case registry。",
    )
    parser.add_argument("--family-sets", type=Path, default=LLM_FAMILY_SETS_PATH, help="LLM benchmark family split 配置")
    parser.add_argument("--unseen-cases", type=Path, default=UNSEEN_FAMILY_CASES_PATH, help="unseen family case 配置")
    parser.add_argument(
        "--condition",
        default="algolab_full",
        choices=["algolab_full", "direct_html_baseline", "no_process_validator", "no_scenegraph_compiler", "no_repair"],
        help="写入 report 的实验条件标签；不改变主 pipeline 行为。",
    )
    args = parser.parse_args()
    if args.limit_per_family < 0:
        raise SystemExit("--limit-per-family 不能为负数")
    if args.max_rounds < 0:
        raise SystemExit("--max-rounds 不能为负数")
    if args.max_candidates < 1:
        raise SystemExit("--max-candidates 至少为 1")
    args.family_sets_config = load_llm_family_sets(args.family_sets)
    family_set_errors = validate_llm_family_sets(args.family_sets_config)
    if family_set_errors:
        raise SystemExit("LLM family sets 配置无效：\n" + "\n".join(family_set_errors))
    args.unseen_cases_config = None
    if args.case_set == "unseen":
        args.unseen_cases_config = load_unseen_family_cases(args.unseen_cases)
        unseen_errors = validate_unseen_family_cases(args.unseen_cases_config)
        if unseen_errors:
            raise SystemExit("Unseen family cases 配置无效：\n" + "\n".join(unseen_errors))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")
    results: list[dict[str, Any]] = []
    cases = selected_cases(
        set(args.case) if args.case else None,
        families=set(args.family) if args.family else None,
        gate_layers=set(args.gate_layer) if args.gate_layer else None,
        family_sets=args.family_sets_config,
        case_set=args.case_set,
        unseen_cases_config=args.unseen_cases_config,
    )
    tasks = selected_tasks(cases, args)

    def handle_result(result: dict[str, Any]) -> bool:
        results.append(result)
        if args.write_each:
            write_report(
                results,
                args.output_dir,
                args=args,
                started_at=started_at,
                ended_at=datetime.now().isoformat(timespec="seconds"),
            )
        status = "PASS" if result.get("ok") else "FAIL"
        print(f"{status} {result['case_id']}[{result['sample_index']}] {result.get('duration_s')}s", flush=True)
        if not result.get("ok"):
            print(result.get("error") or "; ".join(result.get("errors", [])), flush=True)
            return False
        return True

    if args.concurrency > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_task = {}
            for case, sample_index, sample in tasks:
                print(f"RUN {case.id}[{sample_index}] expected={sample.expected!r}", flush=True)
                future = executor.submit(run_one_with_timeout, case, sample, sample_index, args)
                future_to_task[future] = (case, sample_index)
            for future in concurrent.futures.as_completed(future_to_task):
                result = future.result()
                ok = handle_result(result)
                if not ok and args.fail_fast:
                    for pending in future_to_task:
                        pending.cancel()
                    browser_checks = browser_smoke_results(results) if args.browser_smoke else []
                    write_report(
                        results,
                        args.output_dir,
                        args=args,
                        started_at=started_at,
                        ended_at=datetime.now().isoformat(timespec="seconds"),
                        browser_checks=browser_checks,
                    )
                    return 1
    else:
        for case, sample_index, sample in tasks:
            print(f"RUN {case.id}[{sample_index}] expected={sample.expected!r}", flush=True)
            result = run_one_with_timeout(case, sample, sample_index, args)
            if not handle_result(result):
                if args.fail_fast:
                    browser_checks = browser_smoke_results(results) if args.browser_smoke else []
                    write_report(
                        results,
                        args.output_dir,
                        args=args,
                        started_at=started_at,
                        ended_at=datetime.now().isoformat(timespec="seconds"),
                        browser_checks=browser_checks,
                    )
                    return 1
    browser_checks = browser_smoke_results(results) if args.browser_smoke else []
    report_path = write_report(
        results,
        args.output_dir,
        args=args,
        started_at=started_at,
        ended_at=datetime.now().isoformat(timespec="seconds"),
        browser_checks=browser_checks,
    )
    passed = sum(1 for item in results if item.get("ok"))
    print(f"llm_benchmark: {passed}/{len(results)} PASS")
    print(f"report: {report_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
