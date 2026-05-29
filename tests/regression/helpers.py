"""Shared helpers for benchmark regression modules."""

from __future__ import annotations

from pathlib import Path
import argparse
import importlib
import json
import os
import tempfile

from algolab.pipeline import _try_materialize
from algolab.compiler.scene_compiler import compile_scene
from algolab.schemas.input import ProblemInput
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from algolab.verification.process_validator import validate_process
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace
from tests.benchmark_cases import BenchmarkCase, benchmark_cases

REPO_ROOT = Path(__file__).resolve().parents[2]


def spec_for_case(case: BenchmarkCase) -> dict:
    return {
        "problem_title": case.title,
        "input_contract": case.input_contract,
        "correctness_contract": contract_for_case(case) if case.id in contract_enabled_case_ids() else None,
        "variants": [
            {
                "id": case.id,
                "name": case.variant_name,
                "strategy": case.strategy,
                "time_complexity": case.time_complexity,
                "space_complexity": case.space_complexity,
                "code": case.code,
                "tracker_code": case.tracker_code,
            }
        ],
        "verifier_code": case.verifier_code,
    }


def contract_enabled_case_ids() -> set[str]:
    return {"house_robber", "binary_search", "unique_paths", "graph_bfs", "two_sum"}


def contract_for_case(case: BenchmarkCase) -> dict:
    first = case.samples[0]
    return {
        "schema_version": "correctness-contract-v1",
        "input_schema": {key: _type_expr(value) for key, value in first.input_data.items()},
        "output_schema": _type_expr(first.expected),
        "postconditions": [f"{case.title} solve output must satisfy deterministic verifier"],
        "oracle_strategy": "generated_verifier",
        "oracle_code": case.verifier_code,
        "test_cases": [
            {
                "name": f"{case.id}_sample_{index}",
                "input": sample.input_data,
                "expected": sample.expected,
            }
            for index, sample in enumerate(case.samples)
        ],
        "process_invariants": [f"expected layout: {layout}" for layout in case.expected_layouts],
    }


def _type_expr(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        if not value:
            return "any[]"
        return f"{_type_expr(value[0])}[]"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return "any"


def materialize_case(case: BenchmarkCase, sample_index: int = 0):
    sample = case.samples[sample_index]
    request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)
    return _try_materialize(request, spec_for_case(case))


def _process_errors_for(raw_trace: dict) -> list[str]:
    trace = SemanticTrace.model_validate(raw_trace)
    errors, _warnings = validate_process(trace)
    return errors


def _dp_contract_event(
    step: int,
    op: str,
    targets: list[str],
    *,
    state: dict,
    value=None,
    before=None,
    after=None,
    deps: list[str] | None = None,
    role: str = "",
    reason: str = "DP contract test event.",
    code_line: int = 1,
) -> dict:
    return {
        "step": step,
        "op": op,
        "targets": [{"id": target} for target in targets],
        "value": value,
        "before": before,
        "after": after,
        "deps": [{"id": dep} for dep in (deps or [])],
        "role": role,
        "reason": reason,
        "state": state,
        "code_line": code_line,
    }


def _dp_contract_trace(algorithm: str, input_data: dict, result, events: list[dict], pseudocode: list[str] | None = None) -> dict:
    normalized_events = [dict(event, step=index) for index, event in enumerate(events)]
    return {
        "schema_version": "semantic-trace-v1",
        "algorithm": algorithm,
        "input_data": input_data,
        "result": result,
        "pseudocode": pseudocode or ["dp transition"],
        "events": normalized_events,
    }


def _graph_contract_event(
    step: int,
    op: str,
    targets: list[str],
    *,
    state: dict,
    value=None,
    before=None,
    after=None,
    deps: list[str] | None = None,
    role: str = "",
    reason: str = "Graph contract test event.",
    code_line: int = 1,
) -> dict:
    return {
        "step": step,
        "op": op,
        "targets": [{"id": target} for target in targets],
        "value": value,
        "before": before,
        "after": after,
        "deps": [{"id": dep} for dep in (deps or [])],
        "role": role,
        "reason": reason,
        "state": state,
        "code_line": code_line,
    }


def _graph_contract_trace(
    algorithm: str,
    input_data: dict,
    result,
    events: list[dict],
    pseudocode: list[str] | None = None,
) -> dict:
    normalized_events = [dict(event, step=index) for index, event in enumerate(events)]
    return {
        "schema_version": "semantic-trace-v1",
        "algorithm": algorithm,
        "input_data": input_data,
        "result": result,
        "pseudocode": pseudocode or ["graph transition"],
        "events": normalized_events,
    }


def _family_contract_event(
    step: int,
    op: str,
    targets: list[str],
    *,
    state: dict,
    value=None,
    before=None,
    after=None,
    deps: list[str] | None = None,
    role: str = "",
    reason: str = "Family contract test event.",
    code_line: int = 1,
) -> dict:
    return {
        "step": step,
        "op": op,
        "targets": [{"id": target} for target in targets],
        "value": value,
        "before": before,
        "after": after,
        "deps": [{"id": dep} for dep in (deps or [])],
        "role": role,
        "reason": reason,
        "state": state,
        "code_line": code_line,
    }


def _family_contract_trace(
    algorithm: str,
    input_data: dict,
    result,
    events: list[dict],
    pseudocode: list[str] | None = None,
) -> dict:
    normalized_events = [dict(event, step=index) for index, event in enumerate(events)]
    return {
        "schema_version": "semantic-trace-v1",
        "algorithm": algorithm,
        "input_data": input_data,
        "result": result,
        "pseudocode": pseudocode or ["family transition"],
        "events": normalized_events,
    }


def _contract_stack_errors(raw_trace: dict) -> tuple[list[str], list[str], list[str]]:
    trace = SemanticTrace.model_validate(raw_trace)
    trace_errors, _trace_warnings = validate_trace(trace)
    process_errors, _process_warnings = validate_process(trace)
    scene = compile_scene(trace)
    scene_errors, _scene_warnings = validate_scene(scene)
    return trace_errors, process_errors, scene_errors


def _array_contract_trace(
    algorithm: str,
    input_data: dict,
    result,
    events: list[dict],
    pseudocode: list[str] | None = None,
) -> dict:
    normalized_events = [dict(event, step=index) for index, event in enumerate(events)]
    return {
        "schema_version": "semantic-trace-v1",
        "algorithm": algorithm,
        "input_data": input_data,
        "result": result,
        "pseudocode": pseudocode or ["array pointer transition"],
        "events": normalized_events,
    }


def benchmark_coverage_artifact() -> BuildArtifact:
    variants = []
    scenes = {}
    checks = []
    for case in benchmark_cases():
        artifact, errors = materialize_case(case, sample_index=0)
        if errors or not artifact.validation.release_gate.release_ready:
            raise AssertionError((case.id, errors, artifact.validation.release_gate))
        variant = artifact.variants[0]
        variants.append(variant)
        scenes[variant.id] = artifact.scenes[variant.id]
        checks.append(f"{case.title}：首个 benchmark 输入通过")
    return BuildArtifact(
        problem_title="真实题型 Benchmark 覆盖",
        input_contract="离线多输入 benchmark，聚合每题首个输入的可视化产物。",
        input_data={"benchmark_cases": [case.id for case in benchmark_cases()]},
        variants=variants,
        scenes=scenes,
        validation=ValidationReport(
            checks=checks,
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                multi_solution_ready=True,
                release_ready=True,
            ),
        ),
    )


__all__ = [name for name in globals() if not name.startswith("__")]
