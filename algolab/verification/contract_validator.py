"""Validate correctness contracts before they enter release evidence."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from algolab.runtime.executor import canonical, to_jsonable
from algolab.runtime.sandbox import SandboxError, run_function
from algolab.schemas.correctness import (
    ContractReleaseGate,
    ContractValidationReport,
    CorrectnessContract,
    OracleStrategy,
)
from algolab.schemas.input import ProblemInput


def validate_contract(
    contract_data: CorrectnessContract | dict[str, Any],
    request: ProblemInput | None = None,
    *,
    oracle_timeout_s: int = 5,
) -> ContractValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []

    contract: CorrectnessContract | None = None
    try:
        contract = (
            contract_data
            if isinstance(contract_data, CorrectnessContract)
            else CorrectnessContract.model_validate(contract_data)
        )
        checks.append("contract schema_version / Pydantic schema 通过")
    except ValidationError as exc:
        errors.append(f"contract schema 无效：{exc.errors()[0]['msg']}")

    schema_ready = contract is not None
    expected_consistent = False
    generated_tests_pass = False
    oracle_ready = False

    if contract is not None:
        input_fields = set(contract.input_schema.root)
        if not input_fields:
            errors.append("input_schema 不能为空")
        else:
            checks.append("input_schema 定义了输入字段")
        if contract.output_schema.root:
            checks.append("output_schema 定义了输出表达")
        else:
            errors.append("output_schema 不能为空")

        if request is not None:
            request_errors = _validate_input_against_schema(request.input_data, input_fields, "request.input_data")
            errors.extend(request_errors)
            if not request_errors:
                checks.append("request.input_data 与 input_schema 字段一致")
            if request.expected_result is not None:
                expected_consistent = _expected_matches_contract_tests(contract, request)
                if expected_consistent:
                    checks.append("request.expected_result 与 contract test_cases 一致")
                else:
                    errors.append("request.expected_result 与 contract test_cases 不一致")
            elif any(canonical(case.input) == canonical(request.input_data) for case in contract.test_cases):
                warnings.append("request 未提供 expected，无法做当前输入 expected 一致性检查")
        else:
            expected_consistent = True

        test_errors = _validate_test_cases(contract, input_fields)
        errors.extend(test_errors)
        generated_tests_pass = not test_errors
        if generated_tests_pass:
            checks.append("contract test_cases 可用于后续执行")

        oracle_errors, oracle_checks, oracle_ready = _validate_oracle_outputs(
            contract,
            request,
            timeout_s=oracle_timeout_s,
        )
        errors.extend(oracle_errors)
        checks.extend(oracle_checks)
        if contract.oracle_strategy == OracleStrategy.NONE and (
            request is not None and request.expected_result is not None
        ):
            warnings.append("contract 未提供 oracle，当前 request.expected_result 可用于部分校验")
            expected_consistent = True if not contract.test_cases else expected_consistent
        elif contract.oracle_strategy == OracleStrategy.EXPECTED_ONLY and oracle_ready:
            expected_consistent = True if not contract.test_cases else expected_consistent

    if request is None and contract is not None:
        expected_consistent = True

    expected_available = request is not None and request.expected_result is not None
    contract_ready = (
        schema_ready
        and generated_tests_pass
        and expected_consistent
        and not errors
        and (oracle_ready or expected_available)
    )
    blocking_reasons: list[str] = []
    if errors:
        blocking_reasons.extend(errors)
    if schema_ready and not (oracle_ready or expected_available):
        blocking_reasons.append("缺少 oracle 或 request.expected_result")

    return ContractValidationReport(
        errors=errors,
        warnings=warnings,
        checks=checks,
        release_gate=ContractReleaseGate(
            contract_ready=contract_ready,
            schema_ready=schema_ready,
            oracle_ready=oracle_ready,
            expected_consistent=expected_consistent,
            generated_tests_pass=generated_tests_pass,
            blocking_reasons=blocking_reasons,
        ),
    )


def _validate_input_against_schema(input_data: Any, input_fields: set[str], label: str) -> list[str]:
    if not isinstance(input_data, dict):
        return [f"{label} 必须是 object 才能匹配 input_schema"]
    missing = sorted(input_fields - set(input_data))
    if missing:
        return [f"{label} 缺少字段：{', '.join(missing)}"]
    return []


def _validate_test_cases(contract: CorrectnessContract, input_fields: set[str]) -> list[str]:
    errors: list[str] = []
    for index, case in enumerate(contract.test_cases):
        errors.extend(_validate_jsonable(case.input, f"test_cases[{index}].input"))
        errors.extend(_validate_jsonable(case.expected, f"test_cases[{index}].expected"))
        errors.extend(_validate_input_against_schema(case.input, input_fields, f"test_cases[{index}].input"))
    if contract.oracle_strategy in {OracleStrategy.NONE, OracleStrategy.EXPECTED_ONLY} and not contract.test_cases:
        errors.append("无 oracle strategy 时至少需要一个 test_case 或 request.expected_result")
    return errors


def _validate_jsonable(value: Any, label: str) -> list[str]:
    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError as exc:
        return [f"{label} 不能 JSON 序列化：{exc}"]
    return []


def _expected_matches_contract_tests(contract: CorrectnessContract, request: ProblemInput) -> bool:
    matching_cases = [case for case in contract.test_cases if canonical(case.input) == canonical(request.input_data)]
    if not matching_cases:
        return True
    return any(canonical(case.expected) == canonical(request.expected_result) for case in matching_cases)


def _validate_oracle_outputs(
    contract: CorrectnessContract,
    request: ProblemInput | None,
    *,
    timeout_s: int,
) -> tuple[list[str], list[str], bool]:
    if contract.oracle_strategy == OracleStrategy.NONE:
        return [], [], False

    errors: list[str] = []
    checks: list[str] = []

    if contract.oracle_strategy == OracleStrategy.EXPECTED_ONLY:
        if request is None or request.expected_result is None:
            errors.append("expected_only strategy 需要 request.expected_result")
            return errors, checks, False
        missing_expected = [index for index, case in enumerate(contract.test_cases) if case.expected is None]
        if missing_expected:
            errors.append(f"expected_only strategy 的 test_cases 缺少 expected：{missing_expected}")
            return errors, checks, False
        checks.append("expected_only strategy 使用 request/test_case expected")
        return errors, checks, True

    if not contract.oracle_code.strip():
        errors.append(f"oracle strategy {contract.oracle_strategy.value} 缺少可执行 oracle_code")
        return errors, checks, False

    ready = True
    for index, case in enumerate(contract.test_cases):
        result, error = run_contract_oracle(contract, case.input, timeout_s=timeout_s)
        if error:
            errors.append(f"test_cases[{index}] oracle 执行失败：{error}")
            ready = False
            continue
        checks.append(f"test_cases[{index}] oracle 执行通过")
        if case.expected is not None and canonical(result) != canonical(case.expected):
            errors.append(f"oracle result {result!r} 与 test_cases[{index}].expected {case.expected!r} 不一致")
            ready = False

    if request is not None and request.expected_result is not None:
        result, error = run_contract_oracle(contract, request.input_data, timeout_s=timeout_s)
        if error:
            errors.append(f"request oracle 执行失败：{error}")
            ready = False
        else:
            checks.append("request oracle 执行通过")
            if canonical(result) != canonical(request.expected_result):
                errors.append(f"oracle result {result!r} 与 request.expected_result {request.expected_result!r} 不一致")
                ready = False

    return errors, checks, ready


def run_contract_oracle(
    contract: CorrectnessContract,
    input_data: Any,
    *,
    timeout_s: int = 5,
) -> tuple[Any, str]:
    candidates = _oracle_function_candidates(contract.oracle_strategy)
    missing_errors: list[str] = []
    for function_name in candidates:
        try:
            return to_jsonable(run_function(contract.oracle_code, function_name, input_data, timeout_s=timeout_s)), ""
        except SandboxError as exc:
            message = str(exc)
            if f"代码必须定义 {function_name}(input_data)" in message:
                missing_errors.append(message)
                continue
            return None, message
    return None, "; ".join(missing_errors) or "oracle code 未定义可调用入口"


def _oracle_function_candidates(strategy: OracleStrategy) -> tuple[str, ...]:
    if strategy == OracleStrategy.BRUTE_FORCE:
        return ("brute_force", "verify", "oracle")
    if strategy in {OracleStrategy.USER_PROVIDED, OracleStrategy.GENERATED_VERIFIER}:
        return ("verify", "oracle", "brute_force")
    return ("verify", "oracle", "brute_force")
