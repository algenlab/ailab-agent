from __future__ import annotations

import json
import os
import subprocess
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import llm_client
from algolab.generation.prompt_profiles import (
    PROMPT_PROFILES,
    load_profiled_prompt,
    prompt_profile_metadata,
)
from algolab.generation.repair import build_solution_repair_prompt
from algolab.generation import solution_generator
from algolab.schemas.input import ProblemInput
from algolab.verification.repair_context import classify_repair_error
from scripts import run_llm_benchmark as benchmark_runner
from scripts.run_llm_benchmark import make_request, result_metadata


ROOT = Path(__file__).resolve().parents[2]
PLAN2_RUNNER = ROOT / "scripts" / "run_plan2_prompt_ablation.sh"
PLAN2_PROFILES = ("hybrid_current", "service_only")
PLAN2_MODEL = "DeepSeek-V4-Pro"
PLAN2_PROFILE_METADATA = {
    "hybrid_current": {
        "prompt_profile": "hybrid_current",
        "profile_version": "plan2-prompt-profile-v2",
        "removed_algorithm_templates": False,
        "strategy_hint_policy": "benchmark_strategy",
        "generation_prompt_sha256": "3e8d7b6bdde69e0889b6c440235971a085d5b1a56b52872135d8fd7b669bda71",
        "repair_prompt_sha256": "fda3bc7c61d8aa274f9e581f7f8a2c3d5d6b7f3ab37f8dd1cbe11e081e0a3ac3",
    },
    "service_only": {
        "prompt_profile": "service_only",
        "profile_version": "plan2-prompt-profile-v2",
        "removed_algorithm_templates": True,
        "strategy_hint_policy": "removed",
        "generation_prompt_sha256": "6271846c0a2491434f08dc48326fbfb34b0a3d79de62f2f344fd1adb58a67c47",
        "repair_prompt_sha256": "54fbf417c774566e7b0ae85eded6cd67550fc83a8eb94b7d6c9641d058896899",
    },
}


def _plan2_case_ids(count: int) -> list[str]:
    return [f"case-{index:03d}" for index in range(count)]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _plan2_report(
    profile: str,
    case_ids: list[str],
    *,
    failed: int = 0,
    failure_type: str = "generation",
) -> dict:
    total = len(case_ids)
    passed = total - failed
    return {
        "kind": "llm_benchmark_report",
        "config": {
            "model": PLAN2_MODEL,
            "prompt_profile": profile,
            "sample": 0,
            "solutions": 2,
            "max_rounds": 2,
            "max_candidates": 2,
            "timeout_s": 3000,
            "strict_warnings": True,
            "browser_smoke": False,
            "teaching_enrichment": True,
            "write_each": True,
            "concurrency": 8,
            "case_set": "deterministic",
            "language": "zh",
            "benchmark_condition": "algolab_full",
            "prompt_profile_metadata": dict(PLAN2_PROFILE_METADATA[profile]),
            "llm": {
                "timeout_s": 600,
                "max_tokens": 32768,
                "json_retries": 3,
                "api_retries": 1,
                "sdk_max_retries": 0,
                "json_temperature": 0.2,
            },
        },
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total else 0,
        "results": [
            {
                "case_id": case_id,
                "problem": f"Problem {case_id}",
                "strategy": f"Strategy {case_id}",
                "input_data": {"value": index},
                "expected": index,
                "sample_index": 0,
                "family_id": "array_pointer",
                "subfamily_id": "scan",
                "case_set": "deterministic",
                "condition": "algolab_full",
                "ok": index >= failed,
                "first_pass_specification_valid": index >= failed,
                "candidate_summary": {"unknown_dsl_call_failure_count": 0},
                **(
                    {
                        "variants": [{"id": "v1"}, {"id": "v2"}],
                        "release_gate": {"multi_solution_ready": True, "release_ready": True},
                    }
                    if index >= failed
                    else {}
                ),
                **({"failure_type": failure_type} if index < failed else {}),
            }
            for index, case_id in enumerate(case_ids)
        ],
    }


def _write_plan2_report(
    base: Path,
    mode: str,
    profile: str,
    report: dict,
) -> None:
    _write_json(base / mode / profile / "llm_benchmark_report.json", report)


def _write_fake_plan2_python(path: Path) -> None:
    path.write_text(
        """#!/ssd1/liaokunpeng/agent-py310-cu/bin/python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[2:]

PROFILE_METADATA = {
    "hybrid_current": {
        "prompt_profile": "hybrid_current",
        "profile_version": "plan2-prompt-profile-v2",
        "removed_algorithm_templates": False,
        "strategy_hint_policy": "benchmark_strategy",
        "generation_prompt_sha256": "3e8d7b6bdde69e0889b6c440235971a085d5b1a56b52872135d8fd7b669bda71",
        "repair_prompt_sha256": "fda3bc7c61d8aa274f9e581f7f8a2c3d5d6b7f3ab37f8dd1cbe11e081e0a3ac3",
    },
    "service_only": {
        "prompt_profile": "service_only",
        "profile_version": "plan2-prompt-profile-v2",
        "removed_algorithm_templates": True,
        "strategy_hint_policy": "removed",
        "generation_prompt_sha256": "6271846c0a2491434f08dc48326fbfb34b0a3d79de62f2f344fd1adb58a67c47",
        "repair_prompt_sha256": "54fbf417c774566e7b0ae85eded6cd67550fc83a8eb94b7d6c9641d058896899",
    },
}


def option(name):
    return args[args.index(name) + 1]


case_ids = [args[index + 1] for index, value in enumerate(args) if value == "--case"]
profile = option("--prompt-profile")
output_dir = Path(option("--output-dir"))
call_log = Path(os.environ["FAKE_PLAN2_CALL_LOG"])
call_detail_log = Path(os.environ["FAKE_PLAN2_CALL_DETAIL_LOG"])
call_log.parent.mkdir(parents=True, exist_ok=True)
with call_log.open("a", encoding="utf-8") as handle:
    handle.write(profile + "\\n")
with call_detail_log.open("a", encoding="utf-8") as handle:
    handle.write(f"{profile}\\t{option('--concurrency')}\\n")

if os.environ.get("FAKE_PLAN2_WRITE_REPORT", "1") == "1":
    total = len(case_ids)
    failed = 1 if total else 0
    passed = total - failed
    failure_type = os.environ.get("FAKE_PLAN2_FAILURE_TYPE", "generation")
    report = {
        "kind": "llm_benchmark_report",
        "config": {
            "model": os.environ.get("ALGOLAB_LLM_MODEL", ""),
            "prompt_profile": profile,
            "sample": int(option("--sample")),
            "solutions": int(option("--solutions")),
            "max_rounds": int(option("--max-rounds")),
            "max_candidates": int(option("--max-candidates")),
            "timeout_s": int(option("--timeout-s")),
            "strict_warnings": "--strict-warnings" in args,
            "browser_smoke": "--no-browser-smoke" not in args,
            "teaching_enrichment": "--teaching-enrichment" in args,
            "write_each": "--write-each" in args,
            "concurrency": int(option("--concurrency")),
            "case_set": option("--case-set") if "--case-set" in args else "deterministic",
            "language": option("--language") if "--language" in args else "zh",
            "benchmark_condition": option("--condition"),
            "prompt_profile_metadata": PROFILE_METADATA[profile],
            "llm": {
                "timeout_s": int(os.environ["ALGOLAB_LLM_TIMEOUT_S"]),
                "max_tokens": int(os.environ["ALGOLAB_LLM_MAX_TOKENS"]),
                "json_retries": int(os.environ["ALGOLAB_LLM_JSON_RETRIES"]),
                "api_retries": int(os.environ["ALGOLAB_LLM_API_RETRIES"]),
                "sdk_max_retries": 0,
                "json_temperature": 0.2,
            },
        },
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total else 0,
        "results": [
            {
                "case_id": case_id,
                "problem": f"Problem {case_id}",
                "strategy": f"Strategy {case_id}",
                "input_data": {"value": index},
                "expected": index,
                "sample_index": 0,
                "family_id": "array_pointer",
                "subfamily_id": "scan",
                "case_set": "deterministic",
                "condition": "algolab_full",
                "ok": index >= failed,
                "first_pass_specification_valid": index >= failed,
                "candidate_summary": {"unknown_dsl_call_failure_count": 0},
                **(
                    {
                        "variants": [{"id": "v1"}, {"id": "v2"}],
                        "release_gate": {"multi_solution_ready": True, "release_ready": True},
                    }
                    if index >= failed
                    else {}
                ),
                **({"failure_type": failure_type} if index < failed else {}),
            }
            for index, case_id in enumerate(case_ids)
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "llm_benchmark_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

raise SystemExit(int(os.environ.get("FAKE_PLAN2_EXIT_CODE", "0")))
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _plan2_runner_environment(tmp_path: Path) -> tuple[dict[str, str], Path, Path, Path]:
    base = tmp_path / "output"
    manifest = tmp_path / "pilot_manifest.json"
    full200_benchmark = tmp_path / "full200_benchmark.json"
    call_log = tmp_path / "fake_python_calls.log"
    call_detail_log = tmp_path / "fake_python_call_details.log"
    fake_python = tmp_path / "fake_python"
    _write_fake_plan2_python(fake_python)
    _write_json(
        full200_benchmark,
        {
            "cases": [
                {
                    "id": case_id,
                    "problem": f"Problem {case_id}",
                    "strategy": f"Strategy {case_id}",
                    "samples": [
                        {"index": 0, "input_data": {"value": index}, "expected": index}
                    ],
                }
                for index, case_id in enumerate(_plan2_case_ids(200))
            ]
        },
    )
    env = os.environ.copy()
    env.update(
        {
            "PLAN2_PYTHON": str(fake_python),
            "PLAN2_OUTPUT_BASE": str(base),
            "PLAN2_PILOT_MANIFEST": str(manifest),
            "PLAN2_FULL200_BENCHMARK": str(full200_benchmark),
            "PLAN2_PROFILE_CONCURRENCY": "8",
            "FAKE_PLAN2_CALL_LOG": str(call_log),
            "FAKE_PLAN2_CALL_DETAIL_LOG": str(call_detail_log),
            "FAKE_PLAN2_WRITE_REPORT": "1",
            "FAKE_PLAN2_EXIT_CODE": "0",
            "ALGOLAB_LLM_MODEL": "wrong-inherited-model",
        }
    )
    return env, base, manifest, call_log


def _run_plan2_runner(mode: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(PLAN2_RUNNER), mode],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def _load_invalid_marker(base: Path, mode: str, profile: str) -> dict:
    path = base / mode / profile / "invalid_run.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _set_plan2_profile_state(
    base: Path,
    mode: str,
    profile: str,
    case_ids: list[str],
    state: str,
) -> None:
    output_dir = base / mode / profile
    if state == "missing":
        return
    if state == "empty":
        output_dir.mkdir(parents=True, exist_ok=True)
        return
    if state == "complete":
        _write_plan2_report(base, mode, profile, _plan2_report(profile, case_ids))
        return
    if state == "invalid":
        report = _plan2_report(profile, case_ids)
        report["config"]["llm"]["api_retries"] = 99
        _write_plan2_report(base, mode, profile, report)
        return
    if state == "marker":
        _write_json(output_dir / "invalid_run.json", {"reason": "test-invalid-state"})
        return
    if state == "partial":
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "partial-result.json").write_text("{}\n", encoding="utf-8")
        return
    raise AssertionError(f"unknown profile state: {state}")


def _request(**overrides) -> ProblemInput:
    values = {
        "problem": "Count positive values.",
        "input_data": {"nums": [1, -1]},
        "expected_result": 1,
    }
    values.update(overrides)
    return ProblemInput(**values)


def test_problem_input_defaults_to_hybrid_and_rejects_unknown_profiles() -> None:
    assert _request().prompt_profile == "hybrid_current"
    assert _request(prompt_profile="service_only").prompt_profile == "service_only"
    with pytest.raises(ValidationError):
        _request(prompt_profile="not-a-profile")


def test_service_only_generation_prompt_keeps_contract_but_removes_family_templates() -> None:
    assert PROMPT_PROFILES == ("hybrid_current", "service_only")
    hybrid = load_profiled_prompt("tracker_system.txt", "hybrid_current")
    service_only = load_profiled_prompt("tracker_system.txt", "service_only")

    assert "# 高频族模板" in hybrid
    assert "## 示例 1：二分查找" in hybrid
    assert "# 高频族模板" not in service_only
    assert "## 示例 1：二分查找" not in service_only
    for forbidden in ("digit_dp_no_seven", "Kruskal / MST", "反转链表", "0/1 背包", "Dijkstra"):
        assert forbidden not in service_only
    for required in (
        "# 输出 JSON 格式",
        "# 代码高亮行号硬约束",
        "sess.array",
        "sess.trie",
        "sess.flow_network",
        "sess.intervals",
        "# 中性服务组合片段",
    ):
        assert required in service_only


def test_service_only_repair_prompt_and_context_remove_benchmark_specific_guidance() -> None:
    service_repair = load_profiled_prompt("repair_system.txt", "service_only")
    for forbidden in ("Kruskal/MST", "前缀计数不一致", "数位 DP 不含 7", "反转链表"):
        assert forbidden not in service_repair
    assert "工厂方法：`sess.array" in service_repair

    hybrid_request = _request(
        problem="统计 1..n 中不含 7 的正整数",
        input_data={"n": 20},
        expected_result=18,
    )
    service_request = hybrid_request.model_copy(update={"prompt_profile": "service_only"})
    error = "digit_dp_no_seven 结果 19 与 expected 18 不一致"

    hybrid = classify_repair_error(error, request=hybrid_request)
    neutral = classify_repair_error(error, request=service_request)

    assert "dfs(pos, tight, started)" in hybrid["repair_instruction"]
    assert "dfs(pos, tight, started)" not in neutral["repair_instruction"]
    assert "n=20" not in neutral["repair_instruction"]


def test_service_only_semantic_repair_checklist_uses_neutral_dsl_wording() -> None:
    prompt = build_solution_repair_prompt(
        request_prompt="request",
        previous={"variants": []},
        errors=["DSL 静态方法检查失败: GraphObj.node"],
        repair_context=[
            {
                "message": "DSL 静态方法检查失败: GraphObj.node",
                "repair_category": "trace_schema",
                "repair_instruction": "Use the documented API.",
            }
        ],
        prompt_profile="service_only",
    )

    assert "GraphObj.node、Trie node.children、LinkedList node.next" not in prompt
    assert "DSL 对象只能调用白名单方法" in prompt


def test_benchmark_request_and_metadata_record_prompt_profile() -> None:
    case = SimpleNamespace(
        id="case-a",
        problem="Problem",
        strategy="Strategy",
        family_id="array_pointer",
        subfamily_id="scan",
        family="数组",
        gate_layer="family_core",
        support_level="strong",
        process_profile="array_pointer",
    )
    sample = SimpleNamespace(input_data={"nums": [1]}, expected=1)
    request = make_request(
        case,
        sample,
        solutions=2,
        teaching_enrichment=True,
        language="zh",
        prompt_profile="service_only",
    )
    args = Namespace(
        prompt_profile="service_only",
        family_sets_config=None,
        case_set="deterministic",
        language="zh",
    )

    assert request.prompt_profile == "service_only"
    assert request.strategy_hint == ""
    hybrid_request = make_request(
        case,
        sample,
        solutions=2,
        teaching_enrichment=True,
        language="zh",
        prompt_profile="hybrid_current",
    )
    assert hybrid_request.strategy_hint == "Strategy"
    assert result_metadata(case, 0, args)["prompt_profile"] == "service_only"


@pytest.mark.parametrize(
    "message",
    [
        "APIConnectionError: Connection error.",
        "httpx.ConnectError: [Errno 111] Connection refused",
        "APITimeoutError: Request timed out.",
        "APITimeoutError: 请求超时",
        "RateLimitError: request failed",
        "InternalServerError: request failed",
        "APIStatusError: request failed",
    ],
)
def test_benchmark_classifies_real_openai_api_errors_as_transport(message: str) -> None:
    assert benchmark_runner.classify_failure(message) == "api_transport"


@pytest.mark.parametrize("status_code", [408, 409, 425, 429, 499, 500, 501, 599])
def test_benchmark_transport_classification_matches_retryable_http_statuses(
    status_code: int,
) -> None:
    class RetryableStatusError(RuntimeError):
        pass

    error = RetryableStatusError(f"HTTP {status_code}")
    error.status_code = status_code

    assert llm_client._is_retryable_llm_api_error(error) is True
    assert benchmark_runner.classify_failure(f"APIStatusError: HTTP {status_code}") == "api_transport"


@pytest.mark.parametrize(
    "signal",
    [
        "error code: 499",
        "upstream_error",
        "operation was cancelled",
        "temporarily unavailable",
        "too many requests",
        "rate limit",
        "gateway",
    ],
)
def test_benchmark_transport_classification_matches_retryable_text_signals(signal: str) -> None:
    error = RuntimeError(signal)

    assert llm_client._is_retryable_llm_api_error(error) is True
    assert benchmark_runner.classify_failure(f"RuntimeError: {signal}") == "api_transport"


def test_benchmark_keeps_runner_timeout_out_of_api_transport() -> None:
    message = "TimeoutError: LLM benchmark 超过 3000 秒"

    assert benchmark_runner.classify_failure(message) == "timeout"


@pytest.mark.parametrize(
    "message",
    [
        "AuthenticationError: Error code: 401",
        "PermissionDeniedError: Error code: 403",
        "APIStatusError: HTTP 401",
        "APIStatusError: HTTP 403",
    ],
)
def test_benchmark_classifies_authentication_and_permission_failures_as_configuration(
    message: str,
) -> None:
    assert benchmark_runner.classify_failure(message) == "configuration"


def test_release_blocking_errors_require_the_requested_number_of_valid_variants() -> None:
    artifact = SimpleNamespace(
        variants=[SimpleNamespace(id="v1")],
        validation=SimpleNamespace(
            errors=[],
            warnings=[],
            release_gate=SimpleNamespace(release_ready=True, blocking_reasons=[]),
        ),
    )

    errors = benchmark_runner._release_blocking_errors(
        artifact,
        [],
        strict_warnings=True,
        expected_variant_count=2,
    )

    assert errors == ["有效解法数量 1 与请求数量 2 不一致"]


def test_benchmark_marks_single_long_stalled_phase_as_infrastructure_timeout() -> None:
    phase_log = [
        {
            "event": "start",
            "phase": "candidate_0_materialize_round_0",
            "at": 93.0,
        }
    ]

    assert benchmark_runner._timeout_failure_type(3000, phase_log, now=3000.0) == "infrastructure_timeout"


def test_benchmark_marks_timeout_without_active_phase_as_infrastructure_timeout() -> None:
    assert benchmark_runner._timeout_failure_type(3000, [], now=3000.0) == "infrastructure_timeout"


def test_benchmark_keeps_cumulative_multi_phase_timeout_as_method_failure() -> None:
    phase_log = [
        {"event": "start", "phase": "generation", "at": 0.0},
        {"event": "end", "phase": "generation", "duration_s": 1400.0, "at": 1400.0},
        {"event": "start", "phase": "repair", "at": 1400.0},
        {"event": "end", "phase": "repair", "duration_s": 1300.0, "at": 2700.0},
        {"event": "start", "phase": "render", "at": 2700.0},
    ]

    assert benchmark_runner._timeout_failure_type(3000, phase_log, now=3000.0) == "timeout"


def test_prompt_profile_metadata_contains_effective_prompt_hashes() -> None:
    metadata = prompt_profile_metadata("service_only")

    assert metadata["prompt_profile"] == "service_only"
    assert len(metadata["generation_prompt_sha256"]) == 64
    assert len(metadata["repair_prompt_sha256"]) == 64
    assert metadata["removed_algorithm_templates"] is True


@pytest.mark.parametrize("profile", PLAN2_PROFILES)
def test_frozen_plan2_profile_metadata_matches_effective_prompts(profile: str) -> None:
    assert prompt_profile_metadata(profile) == PLAN2_PROFILE_METADATA[profile]


def test_generation_and_repair_calls_receive_the_effective_profile_prompt(monkeypatch) -> None:
    captured: list[tuple[str, str]] = []
    previous = {
        "problem_title": "demo",
        "input_contract": "nums",
        "verifier_code": "",
        "variants": [
            {
                "id": "v1",
                "name": "scan",
                "strategy": "scan",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)",
                "code": "def solve(input_data):\n    return 1",
                "tracker_code": "def trace(input_data):\n    return {}",
            }
        ],
    }

    def fake_chat(system_prompt: str, user_prompt: str, *, kind: str):
        captured.append((kind, system_prompt))
        return previous

    monkeypatch.setattr(solution_generator, "_chat_json", fake_chat)
    request = _request(prompt_profile="service_only")

    solution_generator.generate_solution_spec(request)
    solution_generator.repair_solution_spec(request, previous, ["schema error"])

    assert captured[0][0] == "generation"
    assert "# 中性服务组合片段" in captured[0][1]
    assert "# 高频族模板" not in captured[0][1]
    assert captured[1][0] == "repair"
    assert "service_only 条件" in captured[1][1]
    assert "Kruskal/MST" not in captured[1][1]


def test_plan2_machine_audit_runner_exists() -> None:
    path = ROOT / "scripts" / "run_plan2_prompt_machine_audits.sh"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "--algolab-condition" in text
    assert "$profile" in text
    assert "--algolab-only" in text


def test_plan2_prompt_runner_locks_concurrency_and_retry_budgets() -> None:
    text = PLAN2_RUNNER.read_text(encoding="utf-8")

    assert 'PYTHON="${PLAN2_PYTHON:-/ssd1/liaokunpeng/agent-py310-cu/bin/python3}"' in text
    assert 'BASE="${PLAN2_OUTPUT_BASE:-$ROOT/output/experiments/plan2_20260722/p0_2_prompt_ablation}"' in text
    assert 'MANIFEST="${PLAN2_PILOT_MANIFEST:-$BASE/pilot_manifest.json}"' in text
    assert 'FULL200_BENCHMARK="${PLAN2_FULL200_BENCHMARK:-$ROOT/benchmark/algo_learn_env_benchmark.json}"' in text
    assert "profiles=(hybrid_current service_only)" in text
    assert 'PROFILE_CONCURRENCY="${PLAN2_PROFILE_CONCURRENCY:-8}"' in text
    assert '--concurrency "$PROFILE_CONCURRENCY"' in text
    assert 'total_api_concurrency=$((PROFILE_CONCURRENCY * ${#profiles[@]}))' in text
    assert 'if [[ "$total_api_concurrency" -ne 16 ]]; then' in text
    assert 'Total API concurrency must be 16, got $total_api_concurrency' in text
    assert 'export ALGOLAB_LLM_TIMEOUT_S="600"' in text
    assert 'export ALGOLAB_LLM_MAX_TOKENS="32768"' in text
    assert 'export ALGOLAB_LLM_JSON_RETRIES="3"' in text
    assert 'export ALGOLAB_LLM_API_RETRIES="1"' in text
    assert '(.config.llm.json_temperature == 0.2)' in text
    assert '--timeout-s 3000' in text
    assert '--case-set deterministic' in text
    assert '--language zh' in text
    assert '--case-overrides "$FULL200_BENCHMARK"' in text
    assert llm_client.llm_config()["sdk_max_retries"] == 0


@pytest.mark.parametrize("mismatch", ["single-variant-success", "frozen-payload"])
def test_plan2_runner_rejects_reports_that_violate_effective_protocol(
    tmp_path: Path,
    mismatch: str,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    for profile in PLAN2_PROFILES:
        report = _plan2_report(profile, case_ids)
        if mismatch == "single-variant-success":
            report["results"][0]["variants"] = [{"id": "v1"}]
            report["results"][0]["release_gate"]["multi_solution_ready"] = False
        else:
            report["results"][0]["problem"] = "not the frozen problem"
        _write_plan2_report(base, "pilot", profile, report)

    result = _run_plan2_runner("pilot", env)

    assert result.returncode != 0
    assert not call_log.exists()
    for profile in PLAN2_PROFILES:
        assert _load_invalid_marker(base, "pilot", profile)["reason"] == "protocol_mismatch"


@pytest.mark.parametrize(
    "manifest_payload",
    [
        "{not-json",
        {"case_ids": _plan2_case_ids(59)},
        {"case_ids": _plan2_case_ids(59) + ["case-000"]},
        {"case_ids": _plan2_case_ids(59) + [""]},
        {"case_ids": _plan2_case_ids(59) + [7]},
    ],
    ids=("invalid-json", "wrong-count", "duplicate", "empty", "non-string"),
)
def test_plan2_runner_rejects_bad_manifest_before_python(
    tmp_path: Path,
    manifest_payload: object,
) -> None:
    env, _base, manifest, call_log = _plan2_runner_environment(tmp_path)
    if isinstance(manifest_payload, str):
        manifest.write_text(manifest_payload, encoding="utf-8")
    else:
        _write_json(manifest, manifest_payload)

    result = _run_plan2_runner("pilot", env)

    assert result.returncode != 0
    assert not call_log.exists()


@pytest.mark.parametrize("mismatch", ["old-api-budget", "wrong-case-set"])
def test_plan2_runner_refuses_existing_report_with_protocol_mismatch(
    tmp_path: Path,
    mismatch: str,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    for profile in PLAN2_PROFILES:
        report = _plan2_report(profile, case_ids)
        if mismatch == "old-api-budget":
            report["config"]["llm"]["api_retries"] = 3
        else:
            report["results"][-1]["case_id"] = "unexpected-case"
        _write_plan2_report(base, "pilot", profile, report)

    result = _run_plan2_runner("pilot", env)

    assert result.returncode != 0
    assert "Refusing to overwrite" in result.stderr
    assert not call_log.exists()
    for profile in PLAN2_PROFILES:
        report_path = base / "pilot" / profile / "llm_benchmark_report.json"
        assert _load_invalid_marker(base, "pilot", profile) == {
            "schema_version": "plan2-invalid-run-v1",
            "reason": "protocol_mismatch",
            "profile": profile,
            "mode": "pilot",
            "benchmark_status": None,
            "report_path": str(report_path),
        }


@pytest.mark.parametrize(
    "mismatch",
    [
        "generation-prompt-hash",
        "repair-prompt-hash",
        "benchmark-condition",
        "config-case-set",
        "language",
        "write-each",
    ],
)
def test_plan2_runner_rejects_frozen_protocol_metadata_mismatch(
    tmp_path: Path,
    mismatch: str,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    for profile in PLAN2_PROFILES:
        report = _plan2_report(profile, case_ids)
        if mismatch == "generation-prompt-hash":
            report["config"]["prompt_profile_metadata"]["generation_prompt_sha256"] = "0" * 64
        elif mismatch == "repair-prompt-hash":
            report["config"]["prompt_profile_metadata"]["repair_prompt_sha256"] = "0" * 64
        elif mismatch == "benchmark-condition":
            report["config"]["benchmark_condition"] = "no_repair"
        elif mismatch == "config-case-set":
            report["config"]["case_set"] = "unseen"
        elif mismatch == "language":
            report["config"]["language"] = "en"
        else:
            report["config"]["write_each"] = False
        _write_plan2_report(base, "pilot", profile, report)

    result = _run_plan2_runner("pilot", env)

    assert result.returncode != 0
    assert not call_log.exists()
    for profile in PLAN2_PROFILES:
        assert _load_invalid_marker(base, "pilot", profile)["reason"] == "protocol_mismatch"


@pytest.mark.parametrize(
    ("hybrid_state", "service_state"),
    [
        ("complete", "missing"),
        ("missing", "complete"),
        ("marker", "missing"),
        ("missing", "marker"),
        ("invalid", "complete"),
        ("complete", "marker"),
        ("partial", "missing"),
        ("complete", "empty"),
    ],
)
def test_plan2_runner_pair_preflight_rejects_mixed_states_before_python(
    tmp_path: Path,
    hybrid_state: str,
    service_state: str,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    _set_plan2_profile_state(base, "pilot", "hybrid_current", case_ids, hybrid_state)
    _set_plan2_profile_state(base, "pilot", "service_only", case_ids, service_state)

    result = _run_plan2_runner("pilot", env)

    assert result.returncode != 0
    assert not call_log.exists()


@pytest.mark.parametrize("precreate_empty_dirs", [False, True])
def test_plan2_runner_pair_preflight_starts_both_missing_profiles_at_locked_concurrency(
    tmp_path: Path,
    precreate_empty_dirs: bool,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    if precreate_empty_dirs:
        for profile in PLAN2_PROFILES:
            _set_plan2_profile_state(base, "pilot", profile, case_ids, "empty")

    result = _run_plan2_runner("pilot", env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(call_log.read_text(encoding="utf-8").splitlines()) == sorted(PLAN2_PROFILES)
    call_detail_log = Path(env["FAKE_PLAN2_CALL_DETAIL_LOG"])
    assert sorted(call_detail_log.read_text(encoding="utf-8").splitlines()) == [
        "hybrid_current\t8",
        "service_only\t8",
    ]


def test_plan2_runner_skips_matching_complete_reports(tmp_path: Path) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    for profile in PLAN2_PROFILES:
        _write_plan2_report(base, "pilot", profile, _plan2_report(profile, case_ids))

    result = _run_plan2_runner("pilot", env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("SKIP complete") == 2
    assert not call_log.exists()


def test_plan2_runner_invalidates_existing_report_with_infrastructure_failure(
    tmp_path: Path,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    for profile in PLAN2_PROFILES:
        _write_plan2_report(
            base,
            "pilot",
            profile,
            _plan2_report(profile, case_ids, failed=1, failure_type="api_transport"),
        )

    result = _run_plan2_runner("pilot", env)

    assert result.returncode != 0
    assert not call_log.exists()
    for profile in PLAN2_PROFILES:
        report_path = base / "pilot" / profile / "llm_benchmark_report.json"
        assert _load_invalid_marker(base, "pilot", profile) == {
            "schema_version": "plan2-invalid-run-v1",
            "reason": "infrastructure_failure",
            "profile": profile,
            "mode": "pilot",
            "benchmark_status": None,
            "report_path": str(report_path),
        }


def test_plan2_runner_requires_200_unique_cases_for_full200(tmp_path: Path) -> None:
    env, base, _manifest, call_log = _plan2_runner_environment(tmp_path)
    duplicate_case_ids = _plan2_case_ids(199) + ["case-000"]
    for profile in PLAN2_PROFILES:
        _write_plan2_report(
            base,
            "full200",
            profile,
            _plan2_report(profile, duplicate_case_ids),
        )

    result = _run_plan2_runner("full200", env)

    assert result.returncode != 0
    assert not call_log.exists()


@pytest.mark.parametrize("invalid_kind", ["wrong-count", "duplicate"])
def test_plan2_runner_rejects_invalid_full200_benchmark_before_python(
    tmp_path: Path,
    invalid_kind: str,
) -> None:
    env, _base, _manifest, call_log = _plan2_runner_environment(tmp_path)
    benchmark_path = Path(env["PLAN2_FULL200_BENCHMARK"])
    case_ids = _plan2_case_ids(199)
    if invalid_kind == "duplicate":
        case_ids.append("case-000")
    _write_json(benchmark_path, {"cases": [{"id": case_id} for case_id in case_ids]})

    result = _run_plan2_runner("full200", env)

    assert result.returncode != 0
    assert not call_log.exists()


def test_plan2_runner_rejects_full200_report_with_different_case_set(
    tmp_path: Path,
) -> None:
    env, base, _manifest, call_log = _plan2_runner_environment(tmp_path)
    report_case_ids = [f"other-{index:03d}" for index in range(200)]
    for profile in PLAN2_PROFILES:
        _write_plan2_report(
            base,
            "full200",
            profile,
            _plan2_report(profile, report_case_ids),
        )

    result = _run_plan2_runner("full200", env)

    assert result.returncode != 0
    assert not call_log.exists()


def test_plan2_runner_skips_full200_report_with_exact_benchmark_case_set(
    tmp_path: Path,
) -> None:
    env, base, _manifest, call_log = _plan2_runner_environment(tmp_path)
    benchmark_case_ids = _plan2_case_ids(200)
    for profile in PLAN2_PROFILES:
        _write_plan2_report(
            base,
            "full200",
            profile,
            _plan2_report(profile, benchmark_case_ids),
        )

    result = _run_plan2_runner("full200", env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("SKIP complete") == 2
    assert not call_log.exists()


def test_plan2_runner_executes_full200_with_exact_benchmark_case_set(
    tmp_path: Path,
) -> None:
    env, base, _manifest, call_log = _plan2_runner_environment(tmp_path)
    env["FAKE_PLAN2_EXIT_CODE"] = "1"
    env["FAKE_PLAN2_FAILURE_TYPE"] = "generation"

    result = _run_plan2_runner("full200", env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(call_log.read_text(encoding="utf-8").splitlines()) == sorted(PLAN2_PROFILES)
    for profile in PLAN2_PROFILES:
        report = json.loads(
            (base / "full200" / profile / "llm_benchmark_report.json").read_text(encoding="utf-8")
        )
        assert [item["case_id"] for item in report["results"]] == _plan2_case_ids(200)


@pytest.mark.parametrize("failure_type", ["generation", "correctness", "timeout"])
def test_plan2_runner_accepts_complete_reports_with_method_failures_idempotently(
    tmp_path: Path,
    failure_type: str,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    case_ids = _plan2_case_ids(60)
    _write_json(manifest, {"case_ids": case_ids})
    env["FAKE_PLAN2_EXIT_CODE"] = "1"
    env["FAKE_PLAN2_FAILURE_TYPE"] = failure_type

    first = _run_plan2_runner("pilot", env)

    assert first.returncode == 0, first.stdout + first.stderr
    assert sorted(call_log.read_text(encoding="utf-8").splitlines()) == sorted(PLAN2_PROFILES)
    for profile in PLAN2_PROFILES:
        report = json.loads(
            (base / "pilot" / profile / "llm_benchmark_report.json").read_text(encoding="utf-8")
        )
        assert report["total"] == 60
        assert report["failed"] == 1
        assert report["results"][0]["failure_type"] == failure_type
        assert not (base / "pilot" / profile / "invalid_run.json").exists()

    env["FAKE_PLAN2_EXIT_CODE"] = "99"
    second = _run_plan2_runner("pilot", env)

    assert second.returncode == 0, second.stdout + second.stderr
    assert second.stdout.count("SKIP complete") == 2
    assert sorted(call_log.read_text(encoding="utf-8").splitlines()) == sorted(PLAN2_PROFILES)


@pytest.mark.parametrize(
    "failure_type",
    ["configuration", "runner_error", "api_transport", "infrastructure_timeout"],
)
def test_plan2_runner_persists_infrastructure_failure_marker(
    tmp_path: Path,
    failure_type: str,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    _write_json(manifest, {"case_ids": _plan2_case_ids(60)})
    env["FAKE_PLAN2_EXIT_CODE"] = "1"
    env["FAKE_PLAN2_FAILURE_TYPE"] = failure_type

    first = _run_plan2_runner("pilot", env)

    assert first.returncode != 0
    first_calls = sorted(call_log.read_text(encoding="utf-8").splitlines())
    assert first_calls == sorted(PLAN2_PROFILES)
    for profile in PLAN2_PROFILES:
        report_path = base / "pilot" / profile / "llm_benchmark_report.json"
        assert _load_invalid_marker(base, "pilot", profile) == {
            "schema_version": "plan2-invalid-run-v1",
            "reason": "infrastructure_failure",
            "profile": profile,
            "mode": "pilot",
            "benchmark_status": 1,
            "report_path": str(report_path),
        }

    env["FAKE_PLAN2_EXIT_CODE"] = "0"
    second = _run_plan2_runner("pilot", env)

    assert second.returncode != 0
    assert sorted(call_log.read_text(encoding="utf-8").splitlines()) == first_calls


def test_plan2_runner_rejects_infrastructure_exit_even_with_complete_report_idempotently(
    tmp_path: Path,
) -> None:
    env, base, manifest, call_log = _plan2_runner_environment(tmp_path)
    _write_json(manifest, {"case_ids": _plan2_case_ids(60)})
    env["FAKE_PLAN2_EXIT_CODE"] = "2"

    first = _run_plan2_runner("pilot", env)

    assert first.returncode != 0
    first_calls = sorted(call_log.read_text(encoding="utf-8").splitlines())
    assert first_calls == sorted(PLAN2_PROFILES)
    for profile in PLAN2_PROFILES:
        report_path = base / "pilot" / profile / "llm_benchmark_report.json"
        assert _load_invalid_marker(base, "pilot", profile) == {
            "schema_version": "plan2-invalid-run-v1",
            "reason": "benchmark_exit_status",
            "profile": profile,
            "mode": "pilot",
            "benchmark_status": 2,
            "report_path": str(report_path),
        }

    env["FAKE_PLAN2_EXIT_CODE"] = "0"
    second = _run_plan2_runner("pilot", env)

    assert second.returncode != 0
    assert sorted(call_log.read_text(encoding="utf-8").splitlines()) == first_calls
