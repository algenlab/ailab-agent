"""Run the no-process-validator ablation as an external experiment."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import algolab.pipeline as pipeline
from algolab.generation.solution_generator import generate_solution_spec, repair_solution_spec
from algolab.pipeline import BuildError
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput
from algolab.schemas.validation import BuildArtifact
from algolab.verification.repair_context import repair_failure_types
from llm_client import _model_name, clear_model_calls, consume_model_calls
from scripts.baseline_experiment_utils import add_common_args, run_benchmark
from scripts.run_llm_benchmark import (
    BenchmarkCase,
    BenchmarkInput,
    UnseenBenchmarkCase,
    benchmark_condition,
    classify_failure,
    make_request,
    result_metadata,
)


def _try_materialize_without_process(request: ProblemInput, spec: dict[str, Any]):
    original_validate_process = pipeline.validate_process
    original_process_degradation = pipeline.process_degradation_for_trace
    pipeline.validate_process = lambda _trace: ([], [])
    pipeline.process_degradation_for_trace = lambda *_args, **_kwargs: None
    try:
        return pipeline._try_materialize(request, spec)
    finally:
        pipeline.validate_process = original_validate_process
        pipeline.process_degradation_for_trace = original_process_degradation


def build_artifact_no_process(
    request: ProblemInput,
    *,
    max_rounds: int,
    strict_warnings: bool,
    repair_failure_types_out: list[str],
) -> BuildArtifact:
    spec = generate_solution_spec(request)
    last_errors: list[str] = []
    for round_idx in range(max_rounds + 1):
        artifact, errors = _try_materialize_without_process(request, spec)
        artifact.validation.checks.append("ablation: process validator disabled")
        if artifact.validation.release_gate.release_ready and (not strict_warnings or not artifact.validation.warnings):
            return artifact
        last_errors = errors or []
        if artifact.validation.release_gate.release_ready and strict_warnings and artifact.validation.warnings:
            last_errors = [f"严格模式拒绝 warning：{warning}" for warning in artifact.validation.warnings]
        if round_idx < max_rounds:
            for failure_type in repair_failure_types(last_errors):
                if failure_type not in repair_failure_types_out:
                    repair_failure_types_out.append(failure_type)
            spec = repair_solution_spec(request, spec, last_errors)
    raise BuildError("没有生成可发布产物：\n" + "\n".join(last_errors))


def run_one_no_process_validator(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started = time.time()
    clear_model_calls()
    request = make_request(case, sample, solutions=args.solutions)
    output_stem = f"no_process_validator_{case.id}_{sample_index}"
    output_html = args.output_dir / f"{output_stem}.html"
    metadata = result_metadata(case, sample_index, args)
    repair_types: list[str] = []
    try:
        artifact = build_artifact_no_process(
            request,
            max_rounds=args.max_rounds,
            strict_warnings=args.strict_warnings,
            repair_failure_types_out=repair_types,
        )
        strict_warning_errors = []
        if args.strict_warnings and artifact.validation.warnings:
            strict_warning_errors = [f"严格模式拒绝 warning：{warning}" for warning in artifact.validation.warnings]
        save_html(artifact, output_html)
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
            "ablation": "no_process_validator",
            "process_validator_enabled": False,
            "scenegraph_compiler_enabled": True,
            "ok": artifact.validation.release_gate.release_ready and not strict_warning_errors,
            "release_gate": artifact.validation.release_gate.model_dump(),
            "checks": artifact.validation.checks,
            "warnings": artifact.validation.warnings,
            "errors": [*artifact.validation.errors, *strict_warning_errors],
            "variants": variants,
            "html": str(output_html),
            "json": str(output_html.with_suffix(".json")),
            "duration_s": round(time.time() - started, 3),
            "failure_type": "",
            "repair_failure_types": repair_types,
            "model_calls": consume_model_calls(),
        }
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
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
            "ablation": "no_process_validator",
            "process_validator_enabled": False,
            "scenegraph_compiler_enabled": True,
            "ok": False,
            "error": message,
            "failure_type": classify_failure(message),
            "duration_s": round(time.time() - started, 3),
            "repair_failure_types": repair_types,
            "model_calls": consume_model_calls(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 no_process_validator 消融，不修改主 pipeline 默认行为")
    add_common_args(parser, condition="no_process_validator")
    args = parser.parse_args()
    args.ablation = "no_process_validator"
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = True
    args.direct_html_baseline = False
    args.trace_only_renderer_enabled = False
    return run_benchmark(args, run_one_no_process_validator)


if __name__ == "__main__":
    raise SystemExit(main())
