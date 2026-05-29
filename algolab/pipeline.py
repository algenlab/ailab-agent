"""New AlgoLab build pipeline."""

from __future__ import annotations

import json
from typing import Any

from algolab.compiler.scene_compiler import compile_scene
from algolab.generation.solution_generator import generate_solution_spec, parse_variants, repair_solution_spec
from algolab.runtime.executor import canonical, execute_variant, run_verifier
from algolab.runtime.sandbox import run_function
from algolab.schemas.correctness import CorrectnessContract, OracleStrategy
from algolab.schemas.input import ProblemInput
from algolab.schemas.validation import BuildArtifact, ValidationReport
from algolab.verification.contract_validator import run_contract_oracle, validate_contract
from algolab.verification.demo_readiness import (
    demo_readiness_report_from_variants,
    validate_variant_demo_readiness,
)
from algolab.verification.degradation import (
    dedupe_degradations,
    demo_warning_degradation,
    process_degradation_for_trace,
    release_state_degradations,
)
from algolab.verification.release_gate import compute_release_gate
from algolab.verification.process_validator import validate_process
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace


class BuildError(RuntimeError):
    """Raised when no releasable artifact can be built."""


def build_artifact(request: ProblemInput, max_rounds: int = 2) -> BuildArtifact:
    spec = generate_solution_spec(request)
    last_errors: list[str] = []

    for round_idx in range(max_rounds + 1):
        artifact, errors = _try_materialize(request, spec)
        if artifact.validation.release_gate.release_ready:
            return artifact
        last_errors = errors
        if round_idx < max_rounds:
            spec = repair_solution_spec(request, spec, errors)

    raise BuildError("没有生成可发布产物：\n" + "\n".join(last_errors))


def _try_materialize(request: ProblemInput, spec: dict[str, Any]) -> tuple[BuildArtifact, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []
    raw_contract = spec.get("correctness_contract")
    contract = _contract_from_spec(spec)
    contract_report = None
    if raw_contract is not None:
        contract_report = validate_contract(raw_contract, request)
        errors.extend(f"contract: {error}" for error in contract_report.errors)
        warnings.extend(f"contract: {warning}" for warning in contract_report.warnings)
        checks.extend(f"contract: {check}" for check in contract_report.checks)

    verifier_result = None
    verifier_available = False
    demo_variant_reports = []
    degradations = []
    verifier_code = str(spec.get("verifier_code") or "")
    if verifier_code.strip():
        try:
            verifier_result = run_verifier(verifier_code, request.input_data)
            verifier_available = True
            checks.append("独立 verifier 执行通过")
        except Exception as exc:
            errors.append(f"独立 verifier 执行失败：{exc}")

    good_variants = []
    scenes = {}
    for variant in parse_variants(spec):
        try:
            materialized = execute_variant(variant, request.input_data)
            if verifier_available and canonical(materialized.result) != canonical(verifier_result):
                raise ValueError(f"结果 {materialized.result!r} 与 verifier {verifier_result!r} 不一致")
            if request.expected_result is not None and canonical(materialized.result) != canonical(request.expected_result):
                raise ValueError(f"结果 {materialized.result!r} 与 expected {request.expected_result!r} 不一致")
            assert materialized.trace is not None
            trace_errors, trace_warnings = validate_trace(materialized.trace)
            if trace_errors:
                raise ValueError("; ".join(trace_errors))
            warnings.extend(f"{materialized.name}: {w}" for w in trace_warnings)
            process_errors, process_warnings = validate_process(materialized.trace)
            if process_errors:
                raise ValueError("; ".join(process_errors))
            warnings.extend(f"{materialized.name}: {w}" for w in process_warnings)
            process_degradation = process_degradation_for_trace(materialized.trace, variant_id=materialized.id)
            if process_degradation is not None:
                degradations.append(process_degradation)
            demo_variant_report = validate_variant_demo_readiness(materialized.id, materialized.name, materialized.trace)
            demo_variant_reports.append(demo_variant_report)
            if demo_variant_report.errors:
                raise ValueError("; ".join(demo_variant_report.errors))
            warnings.extend(f"{materialized.name}: {w}" for w in demo_variant_report.warnings)
            if demo_variant_report.status == "warn":
                degradations.append(
                    demo_warning_degradation(
                        reason="; ".join(demo_variant_report.warnings) or "演示可用但存在教学字段缺口。",
                        variant_id=materialized.id,
                    )
                )
            scene = compile_scene(materialized.trace)
            scene_errors, scene_warnings = validate_scene(scene)
            if scene_errors:
                raise ValueError("; ".join(scene_errors))
            warnings.extend(f"{materialized.name}: {w}" for w in scene_warnings)
            scenes[materialized.id] = scene
            good_variants.append(materialized)
            checks.append(f"{materialized.name}：solve/trace/process/scene 均通过")
        except Exception as exc:
            errors.append(f"{variant.name} 失败：{exc}")

    if len(good_variants) > 1:
        baseline = good_variants[0].result
        for variant in good_variants[1:]:
            if canonical(variant.result) != canonical(baseline):
                errors.append(f"多解法结果不一致：{good_variants[0].name} vs {variant.name}")
        if not any("多解法结果不一致" in e for e in errors):
            checks.append("多解法交叉结果一致")

    contract_test_results: list[dict[str, Any]] = []
    if contract is not None and good_variants:
        test_errors, contract_test_results = _run_contract_tests(contract, good_variants, request)
        errors.extend(test_errors)
        passed = sum(1 for item in contract_test_results if item["ok"])
        total = len(contract_test_results)
        checks.append(f"contract tests：{passed}/{total} passed")

    demo_readiness = demo_readiness_report_from_variants(demo_variant_reports)
    errors.extend(demo_readiness.errors)
    warnings.extend(demo_readiness.warnings)
    checks.extend(f"demo readiness: {check}" for check in demo_readiness.checks)

    gate = compute_release_gate(
        variant_count=len(good_variants),
        scene_count=len(scenes),
        errors=errors,
        verifier_available=verifier_available,
        expected_available=request.expected_result is not None,
    )
    degradations.extend(
        release_state_degradations(
            gate=gate,
            errors=errors,
            verifier_available=verifier_available,
            expected_available=request.expected_result is not None,
        )
    )

    report = ValidationReport(
        errors=errors,
        warnings=warnings,
        checks=checks,
        degradations=dedupe_degradations(degradations),
        contract_validation=contract_report,
        contract_test_results=contract_test_results,
        demo_readiness=demo_readiness,
        release_gate=gate,
    )
    artifact = BuildArtifact(
        problem_title=str(spec.get("problem_title") or "算法可视化实验"),
        input_contract=str(spec.get("input_contract") or ""),
        input_data=request.input_data,
        expected_result=request.expected_result,
        verifier_result=verifier_result,
        variants=good_variants,
        scenes=scenes,
        validation=report,
        correctness_contract=contract,
    )
    return artifact, errors


def _contract_from_spec(spec: dict[str, Any]) -> CorrectnessContract | None:
    raw = spec.get("correctness_contract")
    if raw is None:
        return None
    try:
        return CorrectnessContract.model_validate(raw)
    except Exception:
        return None


def _run_contract_tests(
    contract: CorrectnessContract,
    variants: list,
    request: ProblemInput,
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    results: list[dict[str, Any]] = []
    for case_index, case in enumerate(contract.test_cases):
        expected = case.expected
        oracle_result = None
        oracle_error = ""
        oracle_ran = False
        if contract.oracle_strategy not in {OracleStrategy.NONE, OracleStrategy.EXPECTED_ONLY}:
            oracle_result, oracle_error = run_contract_oracle(contract, case.input)
            oracle_ran = oracle_error == ""
            if oracle_error:
                errors.append(f"contract test_cases[{case_index}] oracle 失败：{oracle_error}")
        elif expected is None and canonical(case.input) == canonical(request.input_data):
            expected = request.expected_result

        for variant in variants:
            solve_result = None
            solve_error = ""
            ok = False
            try:
                solve_result = run_function(variant.code, "solve", case.input)
                reference = oracle_result if oracle_ran else expected
                if reference is None:
                    raise ValueError("contract test 缺少 expected/oracle reference")
                if canonical(solve_result) != canonical(reference):
                    raise ValueError(f"solve result {solve_result!r} 与 contract reference {reference!r} 不一致")
                ok = True
            except Exception as exc:
                solve_error = str(exc)
                errors.append(f"{variant.name} contract test_cases[{case_index}] 失败：{exc}")
            results.append(
                {
                    "case_index": case_index,
                    "variant_id": variant.id,
                    "ok": ok,
                    "input": case.input,
                    "expected": expected,
                    "oracle_result": oracle_result,
                    "solve_result": solve_result,
                    "error": solve_error or oracle_error,
                }
            )
    return errors, results


def artifact_to_json(artifact: BuildArtifact) -> str:
    return artifact.model_dump_json(indent=2)


def artifact_summary(artifact: BuildArtifact) -> str:
    data = json.loads(artifact.model_dump_json())
    gate = data["validation"]["release_gate"]
    lines = [
        f"题目：{artifact.problem_title}",
        f"解法数量：{len(artifact.variants)}",
        f"发布状态：{gate['release_ready']}",
    ]
    for variant in artifact.variants:
        trace = variant.trace
        lines.append(f"- {variant.name}: result={variant.result}, steps={len(trace.events) if trace else 0}")
    return "\n".join(lines)
