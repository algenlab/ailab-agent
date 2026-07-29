from __future__ import annotations

from argparse import Namespace

from algolab.generation.execution_modes import (
    execution_mode_metadata,
    load_execution_prompt,
)
from algolab.generation.repair import build_solution_repair_prompt
from algolab.schemas.input import ProblemInput
from scripts.run_llm_benchmark import make_request, result_metadata
from benchmark.cases import benchmark_cases


def test_atomic_and_decoupled_prompts_freeze_the_declared_interface_difference() -> None:
    atomic = load_execution_prompt("tracker_system.txt", "hybrid_current", "atomic")
    decoupled = load_execution_prompt("tracker_system.txt", "hybrid_current", "decoupled")

    assert "唯一权威执行" in atomic
    assert "sess.record(" not in atomic.split("# 单执行实验模式", 1)[1]
    assert "sess.record()" not in decoupled
    assert 'op="set"' in decoupled
    assert 'targets=["value"]' in decoupled
    assert "before=before" in decoupled
    assert "after=new_value" in decoupled
    assert "events=[" in decoupled
    assert "每个 factory 后立即 record" in decoupled
    assert "before == after" in decoupled
    assert "PointerObj.move" in decoupled
    assert "ArrayObj.swap" in decoupled
    assert "下一次服务调用前" in decoupled
    assert atomic != decoupled

    atomic_meta = execution_mode_metadata("atomic", "hybrid_current")
    decoupled_meta = execution_mode_metadata("decoupled", "hybrid_current")
    assert atomic_meta["profile_version"] == "single-execution-pilot-v2"
    assert atomic_meta["execution_mode"] == "atomic"
    assert decoupled_meta["execution_mode"] == "decoupled"
    assert atomic_meta["generation_prompt_sha256"] != decoupled_meta["generation_prompt_sha256"]


def test_decoupled_repair_guidance_reserves_event_fields_for_manual_record_claims() -> None:
    prompt = build_solution_repair_prompt(
        request_prompt="request",
        previous={"variants": []},
        errors=["trace_schema"],
        repair_context=[
            {
                "message": "trace_schema",
                "repair_category": "trace_schema",
                "repair_instruction": "repair trace",
            }
        ],
        execution_mode="decoupled",
    )

    assert "sess.record(...) 的显式 claim" in prompt
    assert "claim 必须包含 op、targets、before、after" in prompt


def test_problem_input_defaults_to_atomic_mode() -> None:
    request = ProblemInput(problem="demo", input_data={})

    assert request.execution_mode == "atomic"


def test_benchmark_request_and_result_metadata_record_execution_mode() -> None:
    case = benchmark_cases()[0]
    request = make_request(
        case,
        case.samples[0],
        solutions=1,
        execution_mode="atomic",
    )
    args = Namespace(
        case_set="deterministic",
        language="zh",
        prompt_profile="hybrid_current",
        execution_mode="atomic",
        family_sets_config=None,
    )

    assert request.execution_mode == "atomic"
    assert result_metadata(case, 0, args)["execution_mode"] == "atomic"
