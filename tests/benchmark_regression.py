"""Real-problem benchmark regression.

This suite does not call the LLM. It validates that generated-style specs for
real algorithm tasks can pass the full materialization pipeline on multiple
inputs.
"""

from __future__ import annotations

from pathlib import Path

from algolab.compiler.scene_compiler import compile_scene
from algolab.pipeline import _try_materialize
from algolab.generation.solution_generator import normalize_solution_spec
from algolab.renderer.capabilities import capabilities_prompt_context, runtime_capabilities
from algolab.renderer.creative import render_creative_html
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from algolab.verification.process_validator import validate_process
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace
from tests.benchmark_cases import BenchmarkCase, benchmark_cases
from scripts.run_llm_benchmark import (
    average_duration,
    build_artifact_timed,
    classify_failure,
    completed_phase_timings,
    last_phase,
    last_phase_elapsed_s,
    make_request,
    selected_samples,
    summarize_phase_timings,
    write_report,
)
from scripts.build_demo_dashboard import CUSTOM_SUBSET_SUM_ID, build_dashboard, selected_demo_definitions
from scripts.check_benchmark_html import html_paths_from_report, resolve_required_case_htmls
from scripts.build_evaluation_manifest import build_manifest, write_manifest
from scripts.build_evaluation_report import build_evaluation_report, comparison_protocols, compute_metrics, condition_summary
from scripts.build_reproducibility_package import build_reproducibility_package, write_reproducibility_package
from scripts.check_v1_release_gate import build_v1_release_gate_report, write_v1_release_gate_report
from llm_client import parse_json_content
import argparse
import json
import os
import tempfile


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


def test_phase12_dp_trace_contract_accepts_representative_subfamilies():
    one_d_contract = {
        "containers": ["dp"],
        "answer_position": "dp[2]",
        "expected_targets": ["dp[1]", "dp[2]"],
        "subfamily": "1d",
    }
    two_d_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1][1]",
        "expected_targets": ["dp[1][1]"],
        "subfamily": "2d",
    }
    knapsack_contract = {
        "containers": ["dp"],
        "answer_position": "dp[2]",
        "expected_targets": ["dp[2]"],
        "subfamily": "knapsack",
    }
    interval_contract = {
        "containers": ["dp"],
        "answer_position": "dp[0][1]",
        "expected_targets": ["dp[0][1]"],
        "subfamily": "interval",
    }
    tree_contract = {
        "containers": ["dp_take", "dp_skip"],
        "answer_position": "dp_take[1]",
        "expected_targets": ["dp_take[1]", "dp_skip[1]"],
        "subfamily": "tree",
    }
    bitmask_contract = {
        "containers": ["dp"],
        "answer_position": "dp[3]",
        "expected_targets": ["dp[1]", "dp[2]", "dp[3]"],
        "subfamily": "state_compression",
    }

    traces = [
        _dp_contract_trace(
            "一维 DP 合同正例",
            {"houses": [2, 7, 9]},
            11,
            [
                _dp_contract_event(0, "create", ["dp"], state={"houses": [2, 7, 9], "dp": [2, 0, 0], "i": 0, "formula": "dp[0]=houses[0]", "dp_contract": one_d_contract}),
                _dp_contract_event(1, "set", ["dp[1]"], value=7, before=0, deps=["dp[0]", "houses[1]"], state={"houses": [2, 7, 9], "dp": [2, 7, 0], "i": 1, "formula": "dp[i]=max(dp[i-1], houses[i])", "dp_contract": one_d_contract}),
                _dp_contract_event(2, "set", ["dp[2]"], value=11, before=0, deps=["dp[1]", "dp[0]", "houses[2]"], state={"houses": [2, 7, 9], "dp": [2, 7, 11], "i": 2, "formula": "dp[i]=max(dp[i-1], dp[i-2]+houses[i])", "dp_contract": one_d_contract}),
                _dp_contract_event(3, "mark", ["dp[2]"], value=11, deps=["dp[2]"], role="answer", state={"houses": [2, 7, 9], "dp": [2, 7, 11], "i": 2, "answer": 11, "formula": "answer=dp[2]", "dp_contract": one_d_contract}),
            ],
            ["dp[i]=max(dp[i-1], dp[i-2]+value)"],
        ),
        _dp_contract_trace(
            "二维 DP 合同正例",
            {"rows": 2, "cols": 2},
            2,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [[1, 1], [1, 0]], "i": 0, "j": 0, "formula": "boundary=1", "dp_contract": two_d_contract}),
                _dp_contract_event(1, "set", ["dp[1][1]"], value=2, before=0, deps=["dp[0][1]", "dp[1][0]"], state={"dp": [[1, 1], [1, 2]], "i": 1, "j": 1, "formula": "dp[i][j]=dp[i-1][j]+dp[i][j-1]", "dp_contract": two_d_contract}),
                _dp_contract_event(2, "mark", ["dp[1][1]"], value=2, deps=["dp[1][1]"], role="answer", state={"dp": [[1, 1], [1, 2]], "i": 1, "j": 1, "answer": 2, "formula": "answer=dp[1][1]", "dp_contract": two_d_contract}),
            ],
            ["dp[i][j]=dp[i-1][j]+dp[i][j-1]"],
        ),
        _dp_contract_trace(
            "0-1 背包 DP 合同正例",
            {"weights": [2], "capacity": 2},
            True,
            [
                _dp_contract_event(0, "create", ["dp"], state={"weights": [2], "capacity": 2, "dp": [True, False, False], "i": -1, "formula": "dp[0]=True", "dp_contract": knapsack_contract}),
                _dp_contract_event(1, "set", ["dp[2]"], value=True, before=False, deps=["dp[0]", "weights[0]"], state={"weights": [2], "capacity": 2, "dp": [True, False, True], "i": 0, "capacity_index": 2, "formula": "dp[c]=dp[c] or dp[c-weight]", "dp_contract": knapsack_contract}),
                _dp_contract_event(2, "mark", ["dp[2]"], value=True, deps=["dp[2]"], role="answer", state={"weights": [2], "capacity": 2, "dp": [True, False, True], "i": 0, "capacity_index": 2, "answer": True, "formula": "answer=dp[capacity]", "dp_contract": knapsack_contract}),
            ],
            ["dp[c]=dp[c] or dp[c-weight]"],
        ),
        _dp_contract_trace(
            "区间 DP 合同正例",
            {"stones": [1, 2]},
            3,
            [
                _dp_contract_event(0, "create", ["dp"], state={"stones": [1, 2], "prefix": [0, 1, 3], "dp": [[0, 0], [0, 0]], "i": 0, "j": 0, "formula": "dp[i][i]=0", "dp_mode": "min_merge", "dp_contract": interval_contract}),
                _dp_contract_event(1, "set", ["dp[0][1]"], value=3, before=0, deps=["dp[0][0]", "dp[1][1]", "prefix[2]", "prefix[0]"], state={"stones": [1, 2], "prefix": [0, 1, 3], "dp": [[0, 3], [0, 0]], "i": 0, "j": 1, "k": 0, "formula": "dp[i][j]=min(dp[i][k]+dp[k+1][j])+sum(i,j)", "dp_mode": "min_merge", "dp_contract": interval_contract}),
                _dp_contract_event(2, "mark", ["dp[0][1]"], value=3, deps=["dp[0][1]"], role="answer", state={"stones": [1, 2], "prefix": [0, 1, 3], "dp": [[0, 3], [0, 0]], "i": 0, "j": 1, "answer": 3, "formula": "answer=dp[0][1]", "dp_mode": "min_merge", "dp_contract": interval_contract}),
            ],
            ["dp[i][j]=min(dp[i][k]+dp[k+1][j])+sum(i,j)"],
        ),
        _dp_contract_trace(
            "树形 DP 合同正例",
            {"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}},
            3,
            [
                _dp_contract_event(0, "create", ["tree"], state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {}, "dp_skip": {}, "formula": "postorder tree dp", "dp_contract": tree_contract}),
                _dp_contract_event(1, "set", ["dp_skip[1]"], value=0, before=None, deps=["node:1"], state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {}, "dp_skip": {"1": 0}, "formula": "dp_skip[u]=sum(max(child states))", "dp_contract": tree_contract}),
                _dp_contract_event(2, "set", ["dp_take[1]"], value=3, before=None, deps=["node:1", "dp_skip[1]"], state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "formula": "dp_take[u]=weight[u]+sum(dp_skip[child])", "dp_contract": tree_contract}),
                _dp_contract_event(3, "mark", ["dp_take[1]"], value=3, deps=["dp_take[1]", "dp_skip[1]"], role="answer", state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": 3, "formula": "answer=max(dp_take[root], dp_skip[root])", "dp_contract": tree_contract}),
            ],
            ["dp_take[u]=weight[u]+sum(dp_skip[child])", "dp_skip[u]=sum(max(child states))"],
        ),
        _dp_contract_trace(
            "状态压缩 DP 合同正例",
            {"item_count": 2},
            2,
            [
                _dp_contract_event(0, "create", ["dp"], state={"item_count": 2, "dp": [0, 0, 0, 0], "mask": 0, "formula": "dp[0]=0", "dp_contract": bitmask_contract}),
                _dp_contract_event(1, "set", ["dp[1]"], value=1, before=0, deps=["dp[0]"], state={"item_count": 2, "dp": [0, 1, 0, 0], "mask": 1, "formula": "dp[mask]=popcount(mask)", "dp_contract": bitmask_contract}),
                _dp_contract_event(2, "set", ["dp[2]"], value=1, before=0, deps=["dp[0]"], state={"item_count": 2, "dp": [0, 1, 1, 0], "mask": 2, "formula": "dp[mask]=popcount(mask)", "dp_contract": bitmask_contract}),
                _dp_contract_event(3, "set", ["dp[3]"], value=2, before=0, deps=["dp[1]", "dp[2]"], state={"item_count": 2, "dp": [0, 1, 1, 2], "mask": 3, "formula": "dp[mask]=popcount(mask)", "dp_contract": bitmask_contract}),
                _dp_contract_event(4, "mark", ["dp[3]"], value=2, deps=["dp[3]"], role="answer", state={"item_count": 2, "dp": [0, 1, 1, 2], "mask": 3, "answer": 2, "formula": "answer=dp[(1<<n)-1]", "dp_contract": bitmask_contract}),
            ],
            ["dp[mask]=popcount(mask)"],
        ),
    ]

    for raw_trace in traces:
        errors = _process_errors_for(raw_trace)
        assert errors == [], (raw_trace["algorithm"], errors)


def test_phase12_dp_trace_contract_rejects_missing_deps_init_answer_and_key_updates():
    contract = {
        "containers": ["dp"],
        "answer_position": "dp[2]",
        "expected_targets": ["dp[1]", "dp[2]"],
        "subfamily": "1d",
    }
    valid_events = [
        _dp_contract_event(0, "create", ["dp"], state={"dp": [1, 0, 0], "i": 0, "formula": "dp[0]=1", "dp_contract": contract}),
        _dp_contract_event(1, "set", ["dp[1]"], value=1, before=0, deps=["dp[0]"], state={"dp": [1, 1, 0], "i": 1, "formula": "dp[i]=dp[i-1]", "dp_contract": contract}),
        _dp_contract_event(2, "set", ["dp[2]"], value=2, before=0, deps=["dp[1]"], state={"dp": [1, 1, 2], "i": 2, "formula": "dp[i]=dp[i-1]+1", "dp_contract": contract}),
        _dp_contract_event(3, "mark", ["dp[2]"], value=2, deps=["dp[2]"], role="answer", state={"dp": [1, 1, 2], "i": 2, "answer": 2, "formula": "answer=dp[2]", "dp_contract": contract}),
    ]

    missing_deps = [dict(event) for event in valid_events]
    missing_deps[1] = dict(missing_deps[1], deps=[])
    missing_deps_errors = _process_errors_for(_dp_contract_trace("DP contract missing deps", {}, 2, missing_deps))
    assert any("DP contract" in error and "deps" in error for error in missing_deps_errors), missing_deps_errors

    missing_init_errors = _process_errors_for(_dp_contract_trace("DP contract missing init", {}, 2, valid_events[1:]))
    assert any("DP contract" in error and "初始化" in error for error in missing_init_errors), missing_init_errors

    wrong_answer_contract = dict(contract, answer_position="dp[1]")
    wrong_answer_events = [
        dict(event, state={**event["state"], "dp_contract": wrong_answer_contract})
        for event in valid_events
    ]
    wrong_answer_errors = _process_errors_for(_dp_contract_trace("DP contract wrong answer", {}, 2, wrong_answer_events))
    assert any("DP contract" in error and "答案位置" in error for error in wrong_answer_errors), wrong_answer_errors

    skipped_update_events = [valid_events[0], valid_events[2], valid_events[3]]
    skipped_update_errors = _process_errors_for(_dp_contract_trace("DP contract skipped update", {}, 2, skipped_update_events))
    assert any("DP contract" in error and "关键更新" in error for error in skipped_update_errors), skipped_update_errors


def test_phase12_graph_trace_contract_accepts_representative_submodes():
    bfs_contract = {"submode": "bfs", "source": "A", "expected_nodes": ["A", "B"]}
    dfs_contract = {"submode": "dfs", "source": "A", "expected_nodes": ["A", "B"]}
    dijkstra_contract = {"submode": "dijkstra", "source": "A", "expected_relax_edges": ["A->B"]}
    topo_contract = {"submode": "topological_sort", "expected_nodes": ["A", "B"]}
    mst_contract = {"submode": "mst", "expected_edges": ["A-B"]}
    tarjan_contract = {"submode": "tarjan", "expected_nodes": ["A", "B"]}
    flow_contract = {"submode": "network_flow", "source": "S", "sink": "T", "expected_paths": [["S", "T"]]}

    traces = [
        _graph_contract_trace(
            "BFS graph contract positive",
            {"graph": {"A": ["B"], "B": []}, "start": "A"},
            {"A": 0, "B": 1},
            [
                _graph_contract_event(0, "create", ["queue", "node:A"], state={"graph": {"A": ["B"], "B": []}, "queue": ["A"], "dist": {"A": 0}, "parent": {}, "graph_contract": bfs_contract}),
                _graph_contract_event(1, "pop", ["queue"], value="A", deps=["node:A"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0}, "parent": {}, "current": "A", "graph_contract": bfs_contract}),
                _graph_contract_event(2, "compare", ["edge:A->B"], deps=["node:A", "node:B"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0}, "parent": {}, "current": "A", "neighbor": "B", "graph_contract": bfs_contract}),
                _graph_contract_event(3, "set", ["dist[B]"], value=1, deps=["dist[A]", "edge:A->B"], role="visited", state={"graph": {"A": ["B"], "B": []}, "queue": ["B"], "dist": {"A": 0, "B": 1}, "parent": {"B": "A"}, "current": "A", "neighbor": "B", "graph_contract": bfs_contract}),
                _graph_contract_event(4, "mark", ["dist[B]"], deps=["dist[B]"], role="answer", state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0, "B": 1}, "parent": {"B": "A"}, "graph_contract": bfs_contract}),
            ],
        ),
        _graph_contract_trace(
            "DFS graph contract positive",
            {"graph": {"A": ["B"], "B": []}, "root": "A"},
            ["A", "B"],
            [
                _graph_contract_event(0, "create", ["graph"], state={"graph": {"A": ["B"], "B": []}, "stack": [], "visited": {}, "graph_contract": dfs_contract}),
                _graph_contract_event(1, "enter", ["frame:dfs(A)"], deps=["node:A"], state={"graph": {"A": ["B"], "B": []}, "stack": ["A"], "visited": {"A": True}, "current": "A", "graph_contract": dfs_contract}),
                _graph_contract_event(2, "compare", ["edge:A->B"], deps=["node:A", "node:B"], state={"graph": {"A": ["B"], "B": []}, "stack": ["A"], "visited": {"A": True}, "current": "A", "neighbor": "B", "graph_contract": dfs_contract}),
                _graph_contract_event(3, "enter", ["frame:dfs(B)"], deps=["edge:A->B"], state={"graph": {"A": ["B"], "B": []}, "stack": ["A", "B"], "visited": {"A": True, "B": True}, "current": "B", "graph_contract": dfs_contract}),
                _graph_contract_event(4, "exit", ["frame:dfs(B)"], deps=["frame:dfs(B)"], state={"graph": {"A": ["B"], "B": []}, "stack": ["A"], "visited": {"A": True, "B": True}, "current": "B", "graph_contract": dfs_contract}),
                _graph_contract_event(5, "exit", ["frame:dfs(A)"], deps=["frame:dfs(A)"], role="answer", state={"graph": {"A": ["B"], "B": []}, "stack": [], "visited": {"A": True, "B": True}, "graph_contract": dfs_contract}),
            ],
        ),
        _graph_contract_trace(
            "Dijkstra graph contract positive",
            {"weighted_graph": {"A": [["B", 2]], "B": []}, "start": "A"},
            {"A": 0, "B": 2},
            [
                _graph_contract_event(0, "create", ["heap", "node:A"], state={"weighted_graph": {"A": [["B", 2]], "B": []}, "heap": [[0, "A"]], "dist": {"A": 0}, "parent": {}, "graph_contract": dijkstra_contract}),
                _graph_contract_event(1, "pop", ["heap"], value=[0, "A"], deps=["node:A"], state={"weighted_graph": {"A": [["B", 2]], "B": []}, "heap": [], "dist": {"A": 0}, "parent": {}, "current": "A", "graph_contract": dijkstra_contract}),
                _graph_contract_event(2, "set", ["dist[B]"], value=2, before=None, after=2, deps=["dist[A]", "edge:A->B"], state={"weighted_graph": {"A": [["B", 2]], "B": []}, "heap": [[2, "B"]], "dist": {"A": 0, "B": 2}, "parent": {"B": "A"}, "current": "A", "neighbor": "B", "edge_weight": 2, "old_dist": None, "new_dist": 2, "graph_contract": dijkstra_contract}),
                _graph_contract_event(3, "mark", ["dist[B]"], deps=["dist[B]"], role="answer", state={"weighted_graph": {"A": [["B", 2]], "B": []}, "heap": [], "dist": {"A": 0, "B": 2}, "parent": {"B": "A"}, "graph_contract": dijkstra_contract}),
            ],
        ),
        _graph_contract_trace(
            "Topological graph contract positive",
            {"graph": {"A": ["B"], "B": []}},
            ["A", "B"],
            [
                _graph_contract_event(0, "create", ["queue"], state={"graph": {"A": ["B"], "B": []}, "queue": ["A"], "indegree": {"A": 0, "B": 1}, "topo_order": [], "graph_contract": topo_contract}),
                _graph_contract_event(1, "pop", ["queue"], value="A", deps=["node:A"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "indegree": {"A": 0, "B": 1}, "topo_order": ["A"], "current": "A", "graph_contract": topo_contract}),
                _graph_contract_event(2, "set", ["indegree[B]"], value=0, before=1, after=0, deps=["edge:A->B", "indegree[B]"], state={"graph": {"A": ["B"], "B": []}, "queue": ["B"], "indegree": {"A": 0, "B": 0}, "topo_order": ["A"], "current": "A", "neighbor": "B", "enqueue_reason": "indegree_zero", "graph_contract": topo_contract}),
                _graph_contract_event(3, "mark", ["node:B"], deps=["indegree[B]"], role="answer", state={"graph": {"A": ["B"], "B": []}, "queue": [], "indegree": {"A": 0, "B": 0}, "topo_order": ["A", "B"], "enqueue_reason": "indegree_zero", "graph_contract": topo_contract}),
            ],
        ),
        _graph_contract_trace(
            "MST graph contract positive",
            {"edges": [["A", "B", 1]], "n": 2},
            [["A", "B", 1]],
            [
                _graph_contract_event(0, "create", ["union_find"], state={"edges": [["A", "B", 1]], "mst_edges": [], "union_find": {"parent": {"A": "A", "B": "B"}}, "graph_contract": mst_contract}),
                _graph_contract_event(1, "mark", ["edge:A->B"], value="selected", deps=["node:A", "node:B"], role="selected", reason="MST 选择连接不同连通分量的最小边。", state={"edges": [["A", "B", 1]], "mst_edges": [["A", "B", 1]], "union_find": {"parent": {"A": "A", "B": "A"}}, "edge_decision": "select", "decision_reason": "different_components", "graph_contract": mst_contract}),
                _graph_contract_event(2, "mark", ["edge:A->B"], deps=["edge:A->B"], role="answer", state={"edges": [["A", "B", 1]], "mst_edges": [["A", "B", 1]], "union_find": {"parent": {"A": "A", "B": "A"}}, "graph_contract": mst_contract}),
            ],
        ),
        _graph_contract_trace(
            "Tarjan graph contract positive",
            {"graph": {"A": ["B"], "B": []}},
            [["B"], ["A"]],
            [
                _graph_contract_event(0, "create", ["graph"], state={"graph": {"A": ["B"], "B": []}, "dfn": {}, "low": {}, "stack": [], "on_stack": {}, "graph_contract": tarjan_contract}),
                _graph_contract_event(1, "set", ["dfn[A]"], value=1, deps=["node:A"], state={"graph": {"A": ["B"], "B": []}, "dfn": {"A": 1}, "low": {"A": 1}, "stack": ["A"], "on_stack": {"A": True}, "current": "A", "graph_contract": tarjan_contract}),
                _graph_contract_event(2, "set", ["low[A]"], value=1, deps=["dfn[A]"], state={"graph": {"A": ["B"], "B": []}, "dfn": {"A": 1}, "low": {"A": 1}, "stack": ["A"], "on_stack": {"A": True}, "current": "A", "graph_contract": tarjan_contract}),
                _graph_contract_event(3, "set", ["dfn[B]"], value=2, deps=["edge:A->B", "node:B"], state={"graph": {"A": ["B"], "B": []}, "dfn": {"A": 1, "B": 2}, "low": {"A": 1, "B": 2}, "stack": ["A", "B"], "on_stack": {"A": True, "B": True}, "current": "B", "graph_contract": tarjan_contract}),
                _graph_contract_event(4, "set", ["low[B]"], value=2, deps=["dfn[B]"], state={"graph": {"A": ["B"], "B": []}, "dfn": {"A": 1, "B": 2}, "low": {"A": 1, "B": 2}, "stack": ["A", "B"], "on_stack": {"A": True, "B": True}, "current": "B", "graph_contract": tarjan_contract}),
                _graph_contract_event(5, "mark", ["node:B"], deps=["low[B]", "dfn[B]"], role="component", state={"graph": {"A": ["B"], "B": []}, "dfn": {"A": 1, "B": 2}, "low": {"A": 1, "B": 2}, "stack": ["A"], "on_stack": {"A": True, "B": False}, "component": ["B"], "current": "B", "graph_contract": tarjan_contract}),
            ],
        ),
        _graph_contract_trace(
            "Network flow graph contract positive",
            {"graph": {"S": ["T"], "T": []}, "capacity": {"S->T": 3}, "source": "S", "sink": "T"},
            3,
            [
                _graph_contract_event(0, "create", ["queue"], state={"graph": {"S": ["T"], "T": []}, "capacity": {"S->T": 3}, "flow": {"S->T": 0}, "queue": ["S"], "parent": {"S": None}, "bottleneck": 3, "augmenting_path": [], "graph_contract": flow_contract}),
                _graph_contract_event(1, "set", ["parent[T]"], value="S", deps=["edge:S->T", "cap[S->T]", "flow[S->T]"], state={"graph": {"S": ["T"], "T": []}, "capacity": {"S->T": 3}, "flow": {"S->T": 0}, "queue": ["T"], "parent": {"S": None, "T": "S"}, "bottleneck": 3, "augmenting_path": ["S", "T"], "graph_contract": flow_contract}),
                _graph_contract_event(2, "set", ["flow[S->T]"], value=3, before=0, after=3, deps=["edge:S->T", "cap[S->T]", "parent[T]"], role="answer", state={"graph": {"S": ["T"], "T": []}, "capacity": {"S->T": 3}, "flow": {"S->T": 3}, "queue": [], "parent": {"S": None, "T": "S"}, "bottleneck": 3, "augmenting_path": ["S", "T"], "graph_contract": flow_contract}),
            ],
        ),
    ]

    for raw_trace in traces:
        errors = _process_errors_for(raw_trace)
        assert errors == [], (raw_trace["algorithm"], errors)


def test_phase12_graph_trace_contract_rejects_submode_process_errors():
    def errors_for(submode: str, events: list[dict], input_data: dict | None = None) -> list[str]:
        return _process_errors_for(_graph_contract_trace(f"Graph contract {submode}", input_data or {}, None, events))

    bfs_contract = {"submode": "bfs", "source": "A", "expected_nodes": ["A", "B"]}
    bfs_valid = [
        _graph_contract_event(0, "create", ["queue", "node:A"], state={"graph": {"A": ["B"], "B": []}, "queue": ["A"], "dist": {"A": 0}, "parent": {}, "graph_contract": bfs_contract}),
        _graph_contract_event(1, "pop", ["queue"], value="A", deps=["node:A"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0}, "parent": {}, "current": "A", "graph_contract": bfs_contract}),
        _graph_contract_event(2, "compare", ["edge:A->B"], deps=["node:A", "node:B"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0}, "parent": {}, "current": "A", "neighbor": "B", "graph_contract": bfs_contract}),
        _graph_contract_event(3, "set", ["dist[B]"], value=1, deps=["dist[A]", "edge:A->B"], role="visited", state={"graph": {"A": ["B"], "B": []}, "queue": ["B"], "dist": {"A": 0, "B": 1}, "parent": {"B": "A"}, "current": "A", "neighbor": "B", "graph_contract": bfs_contract}),
    ]
    duplicate_visit = [*bfs_valid, _graph_contract_event(4, "set", ["dist[B]"], value=1, deps=["dist[A]", "edge:A->B"], role="visited", state={"graph": {"A": ["B"], "B": []}, "queue": ["B", "B"], "dist": {"A": 0, "B": 1}, "parent": {"B": "A"}, "current": "A", "neighbor": "B", "graph_contract": bfs_contract})]
    duplicate_errors = errors_for("bfs duplicate", duplicate_visit, {"graph": {"A": ["B"], "B": []}, "start": "A"})
    assert any("Graph contract" in error and "重复首次访问" in error for error in duplicate_errors), duplicate_errors

    wrong_dist = [
        dict(event, state={**event["state"], "dist": {"A": 0, "B": 2}})
        if event["step"] == 3 else event
        for event in bfs_valid
    ]
    wrong_dist_errors = errors_for("bfs wrong dist", wrong_dist, {"graph": {"A": ["B"], "B": []}, "start": "A"})
    assert any("Graph contract" in error and "dist" in error for error in wrong_dist_errors), wrong_dist_errors

    queue_jump = [
        dict(event, state={**event["state"], "queue": ["B"]})
        if event["step"] == 1 else event
        for event in bfs_valid
    ]
    queue_jump_errors = errors_for("bfs queue jump", queue_jump, {"graph": {"A": ["B"], "B": []}, "start": "A"})
    assert any("Graph contract" in error and "queue 跳变" in error for error in queue_jump_errors), queue_jump_errors

    dfs_contract = {"submode": "dfs", "source": "A", "expected_nodes": ["A", "B"]}
    dfs_errors = errors_for(
        "dfs missing frame",
        [
            _graph_contract_event(0, "create", ["graph"], state={"graph": {"A": ["B"], "B": []}, "visited": {"A": True, "B": True}, "graph_contract": dfs_contract}),
        ],
    )
    assert any("Graph contract" in error and "recursion frame" in error for error in dfs_errors), dfs_errors

    dijkstra_contract = {"submode": "dijkstra", "source": "A", "expected_relax_edges": ["A->B"]}
    dijkstra_missing_relax_errors = errors_for(
        "dijkstra missing relax",
        [
            _graph_contract_event(0, "create", ["heap"], state={"weighted_graph": {"A": [["B", 2]], "B": []}, "heap": ["A"], "dist": {"A": 0, "B": 2}, "parent": {"B": "A"}, "graph_contract": dijkstra_contract}),
        ],
        {"weighted_graph": {"A": [["B", 2]], "B": []}, "start": "A"},
    )
    assert any("Graph contract" in error and "relax" in error for error in dijkstra_missing_relax_errors), dijkstra_missing_relax_errors

    dijkstra_negative_errors = errors_for(
        "dijkstra negative",
        [
            _graph_contract_event(0, "create", ["heap"], state={"weighted_graph": {"A": [["B", -1]], "B": []}, "heap": ["A"], "dist": {"A": 0}, "graph_contract": dijkstra_contract}),
        ],
        {"weighted_graph": {"A": [["B", -1]], "B": []}, "start": "A"},
    )
    assert any("Graph contract" in error and "负权" in error for error in dijkstra_negative_errors), dijkstra_negative_errors

    topo_contract = {"submode": "topological_sort", "expected_nodes": ["A", "B"]}
    topo_errors = errors_for(
        "topo missing indegree",
        [
            _graph_contract_event(0, "create", ["queue"], state={"graph": {"A": ["B"], "B": []}, "queue": ["A"], "topo_order": [], "graph_contract": topo_contract}),
            _graph_contract_event(1, "mark", ["node:B"], deps=["edge:A->B"], role="answer", state={"graph": {"A": ["B"], "B": []}, "queue": ["B"], "topo_order": ["A"], "graph_contract": topo_contract}),
        ],
    )
    assert any("Graph contract" in error and "indegree" in error for error in topo_errors), topo_errors

    mst_contract = {"submode": "mst", "expected_edges": ["A-B"]}
    mst_errors = errors_for(
        "mst missing uf",
        [
            _graph_contract_event(0, "create", ["graph"], state={"edges": [["A", "B", 1]], "mst_edges": [], "graph_contract": mst_contract}),
            _graph_contract_event(1, "mark", ["edge:A->B"], role="selected", state={"edges": [["A", "B", 1]], "mst_edges": [["A", "B", 1]], "graph_contract": mst_contract}),
        ],
        {"edges": [["A", "B", 1]], "n": 2},
    )
    assert any("Graph contract" in error and "union-find" in error for error in mst_errors), mst_errors

    tarjan_contract = {"submode": "tarjan", "expected_nodes": ["A"]}
    tarjan_errors = errors_for(
        "tarjan missing low",
        [
            _graph_contract_event(0, "create", ["graph"], state={"graph": {"A": []}, "dfn": {"A": 1}, "stack": ["A"], "graph_contract": tarjan_contract}),
        ],
    )
    assert any("Graph contract" in error and "dfn/low/stack" in error for error in tarjan_errors), tarjan_errors

    flow_contract = {"submode": "network_flow", "source": "S", "sink": "T", "expected_paths": [["S", "T"]]}
    flow_errors = errors_for(
        "flow missing bottleneck",
        [
            _graph_contract_event(0, "create", ["queue"], state={"graph": {"S": ["T"], "T": []}, "capacity": {"S->T": 3}, "flow": {"S->T": 0}, "parent": {"T": "S"}, "augmenting_path": ["S", "T"], "graph_contract": flow_contract}),
            _graph_contract_event(1, "set", ["flow[S->T]"], value=3, deps=["edge:S->T"], state={"graph": {"S": ["T"], "T": []}, "capacity": {"S->T": 3}, "flow": {"S->T": 3}, "parent": {"T": "S"}, "augmenting_path": ["S", "T"], "graph_contract": flow_contract}),
        ],
    )
    assert any("Graph contract" in error and "bottleneck" in error for error in flow_errors), flow_errors


def test_phase12_family_trace_contract_accepts_string_tree_backtracking_and_structures():
    string_contract = {"family": "string", "submode": "kmp", "expected_tables": ["pi"], "expected_events": ["compare", "fallback"]}
    tree_contract = {"family": "tree", "submode": "postorder", "expected_nodes": ["1"], "expected_frames": ["frame:dfs(1)"]}
    backtracking_contract = {"family": "backtracking", "submode": "permutation", "expected_events": ["choose", "record", "undo"]}
    heap_contract = {"family": "heap", "submode": "topk", "expected_events": ["push", "pop"]}
    trie_contract = {"family": "trie", "submode": "insert_search", "expected_events": ["create_node", "terminal", "prefix_count"]}
    linked_contract = {"family": "linked_list", "submode": "reverse", "expected_events": ["move_pointer", "link_change"]}

    tree_state = {
        "tree": {"nodes": [{"id": "1"}], "edges": []},
        "current": "1",
        "frames": ["frame:dfs(1)"],
        "return_values": {},
        "family_contract": tree_contract,
    }
    recursion_tree = {"nodes": [{"id": "root", "label": "[]"}, {"id": "root_1", "label": "[1]"}], "edges": [["root", "root_1"]]}
    linked_nodes = [
        {"id": "1", "label": "1", "meta": {"next": "2"}},
        {"id": "2", "label": "2", "meta": {"next": None}},
    ]

    traces = [
        _family_contract_trace(
            "KMP family contract positive",
            {"text": "ababc", "pattern": "abc"},
            2,
            [
                _family_contract_event(0, "create", ["text", "pattern", "pi"], state={"text": "ababc", "pattern": "abc", "i": 0, "j": 0, "pi": [0, 0, 0], "family_contract": string_contract}, reason="初始化 text/pattern 指针和 KMP 前缀表。"),
                _family_contract_event(1, "compare", ["text[2]", "pattern[0]"], deps=["text[2]", "pattern[0]"], state={"text": "ababc", "pattern": "abc", "i": 2, "j": 0, "pi": [0, 0, 0], "mismatch_reason": "失配后按 pi 回退", "family_contract": string_contract}, reason="KMP 比较当前文本字符和模式字符，失配时准备回退。"),
                _family_contract_event(2, "move", ["pointer:j"], value=0, deps=["pi[0]", "pattern[0]"], state={"text": "ababc", "pattern": "abc", "i": 2, "j": 0, "pi": [0, 0, 0], "fallback_reason": "失配回退到 pi[j-1]", "family_contract": string_contract}, reason="KMP 失配回退使用 pi 表，不重新扫描已经匹配的文本。"),
                _family_contract_event(3, "mark", ["text[2]"], deps=["pattern[0]"], role="answer", state={"text": "ababc", "pattern": "abc", "i": 4, "j": 3, "pi": [0, 0, 0], "answer": 2, "family_contract": string_contract}, reason="模式串完整匹配，答案起点是 i - len(pattern) + 1。"),
            ],
        ),
        _family_contract_trace(
            "Tree family contract positive",
            {"tree": {"nodes": [{"id": "1"}], "edges": []}},
            ["1"],
            [
                _family_contract_event(0, "create", ["tree"], state={"tree": tree_state["tree"], "current": "1", "frames": [], "return_values": {}, "family_contract": tree_contract}, reason="初始化树结构。"),
                _family_contract_event(1, "enter", ["frame:dfs(1)"], deps=["node:1"], state=tree_state, reason="进入节点 1 的递归 frame。"),
                _family_contract_event(2, "exit", ["frame:dfs(1)"], value=["1"], deps=["node:1"], role="answer", state={**tree_state, "frames": [], "return_values": {"1": ["1"]}, "aggregate": ["1"], "answer": ["1"]}, reason="子树返回值已经聚合，退出 frame。"),
            ],
        ),
        _family_contract_trace(
            "Backtracking family contract positive",
            {"nums": [1]},
            [[1]],
            [
                _family_contract_event(0, "create", ["recursion_tree"], state={"nums": [1], "path": [], "used": [False], "answer": [], "recursion_tree": {"nodes": [{"id": "root", "label": "[]"}], "edges": []}, "family_contract": backtracking_contract}, reason="从空路径开始回溯。"),
                _family_contract_event(1, "enter", ["frame:dfs([])"], deps=["recursion_tree"], state={"nums": [1], "path": [], "used": [False], "answer": [], "recursion_tree": recursion_tree, "choice": None, "family_contract": backtracking_contract}, reason="进入当前回溯 frame。"),
                _family_contract_event(2, "push", ["path"], value=1, deps=["nums[0]"], role="choose", state={"nums": [1], "path": [1], "used": [True], "answer": [], "recursion_tree": recursion_tree, "choice": 1, "family_contract": backtracking_contract}, reason="选择 nums[0] 放入 path。"),
                _family_contract_event(3, "mark", ["answer"], value=[[1]], deps=["path[0]"], role="answer", state={"nums": [1], "path": [1], "used": [True], "answer": [[1]], "recursion_tree": recursion_tree, "choice": 1, "family_contract": backtracking_contract}, reason="path 长度达到 nums 长度，记录一个答案。"),
                _family_contract_event(4, "pop", ["path"], value=1, deps=["path[0]"], role="undo", state={"nums": [1], "path": [], "used": [False], "answer": [[1]], "recursion_tree": recursion_tree, "choice": 1, "family_contract": backtracking_contract}, reason="撤销选择，恢复 path 和 used 后继续尝试其他分支。"),
            ],
        ),
        _family_contract_trace(
            "Heap family contract positive",
            {"nums": [3, 1], "k": 1},
            3,
            [
                _family_contract_event(0, "create", ["heap"], state={"nums": [3, 1], "heap": [], "heap_type": "min", "k": 1, "family_contract": heap_contract}, reason="初始化容量为 k 的小顶堆。"),
                _family_contract_event(1, "push", ["heap"], value=3, deps=["nums[0]"], state={"nums": [3, 1], "heap": [3], "heap_type": "min", "k": 1, "i": 0, "heap_top": 3, "family_contract": heap_contract}, reason="把当前元素加入堆并维护堆顶。"),
                _family_contract_event(2, "push", ["heap"], value=1, deps=["nums[1]"], state={"nums": [3, 1], "heap": [1, 3], "heap_type": "min", "k": 1, "i": 1, "heap_top": 1, "family_contract": heap_contract}, reason="加入新元素后小顶堆堆顶是最小候选。"),
                _family_contract_event(3, "pop", ["heap"], value=1, deps=["heap[0]"], role="conflict", state={"nums": [3, 1], "heap": [3], "heap_type": "min", "k": 1, "i": 1, "heap_top": 3, "family_contract": heap_contract}, reason="堆超过 k 个元素，弹出堆顶后保留最大的 k 个。"),
                _family_contract_event(4, "mark", ["heap[0]"], value=3, deps=["heap[0]"], role="answer", state={"nums": [3, 1], "heap": [3], "heap_type": "min", "k": 1, "answer": 3, "heap_top": 3, "family_contract": heap_contract}, reason="堆顶就是第 k 大元素。"),
            ],
        ),
        _family_contract_trace(
            "Trie family contract positive",
            {"words": ["a"], "prefix": "a"},
            1,
            [
                _family_contract_event(0, "create", ["trie"], state={"words": ["a"], "prefix": "a", "trie": {"nodes": [{"id": "root", "label": "root", "meta": {"count": 0}}], "edges": []}, "current": "root", "family_contract": trie_contract}, reason="初始化 Trie 根节点。"),
                _family_contract_event(1, "link", ["node:root_a"], deps=["node:root", "words[0]"], state={"words": ["a"], "prefix": "a", "trie": {"nodes": [{"id": "root", "label": "root", "meta": {"count": 1}}, {"id": "root_a", "label": "a", "meta": {"count": 1, "terminal": True}}], "edges": [["root", "root_a"]]}, "current": "root_a", "char": "a", "prefix_count": 1, "family_contract": trie_contract}, reason="沿字符 a 创建 Trie 子节点，并更新经过计数。"),
                _family_contract_event(2, "mark", ["node:root_a"], value=1, deps=["node:root_a"], role="answer", state={"words": ["a"], "prefix": "a", "trie": {"nodes": [{"id": "root", "label": "root", "meta": {"count": 1}}, {"id": "root_a", "label": "a", "meta": {"count": 1, "terminal": True}}], "edges": [["root", "root_a"]]}, "current": "root_a", "char": "a", "prefix_count": 1, "answer": 1, "family_contract": trie_contract}, reason="前缀路径结束，当前节点 count 就是前缀匹配数量。"),
            ],
        ),
        _family_contract_trace(
            "Linked list family contract positive",
            {"values": [1, 2]},
            [2, 1],
            [
                _family_contract_event(0, "create", ["linked_list"], state={"linked_list": {"nodes": linked_nodes, "edges": [["1", "2"]]}, "current": "1", "prev": None, "next": "2", "family_contract": linked_contract}, reason="初始化链表和 prev/current/next 指针。"),
                _family_contract_event(1, "move", ["pointer:current"], value=1, deps=["node:1"], state={"linked_list": {"nodes": linked_nodes, "edges": [["1", "2"]]}, "current": "1", "prev": None, "next": "2", "family_contract": linked_contract}, reason="定位当前待反转节点。"),
                _family_contract_event(2, "unlink", ["edge:1->2"], deps=["node:1", "node:2"], state={"linked_list": {"nodes": linked_nodes, "edges": []}, "current": "1", "prev": None, "next": "2", "family_contract": linked_contract}, reason="断开 current 原来的 next 指向，为反转做准备。"),
                _family_contract_event(3, "link", ["edge:2->1"], deps=["node:2", "node:1"], state={"linked_list": {"nodes": [{"id": "1", "label": "1", "meta": {"next": None}}, {"id": "2", "label": "2", "meta": {"next": "1"}}], "edges": [["2", "1"]]}, "current": "2", "prev": "1", "next": None, "family_contract": linked_contract}, reason="修改 next 指针，让节点 2 指向已经反转好的前缀。"),
                _family_contract_event(4, "mark", ["node:2"], value=[2, 1], deps=["edge:2->1"], role="answer", state={"linked_list": {"nodes": [{"id": "1", "label": "1", "meta": {"next": None}}, {"id": "2", "label": "2", "meta": {"next": "1"}}], "edges": [["2", "1"]]}, "current": None, "prev": "2", "next": None, "answer": [2, 1], "family_contract": linked_contract}, reason="current 为空，prev 指向反转后链表头。"),
            ],
        ),
    ]

    for raw_trace in traces:
        trace_errors, process_errors, scene_errors = _contract_stack_errors(raw_trace)
        assert trace_errors == [], (raw_trace["algorithm"], trace_errors)
        assert process_errors == [], (raw_trace["algorithm"], process_errors)
        assert scene_errors == [], (raw_trace["algorithm"], scene_errors)


def test_phase12_family_trace_contract_rejects_missing_process_evidence():
    def errors_for(events: list[dict], algorithm: str = "Family contract negative") -> list[str]:
        return _process_errors_for(_family_contract_trace(algorithm, {}, None, events))

    string_contract = {"family": "string", "submode": "kmp", "expected_tables": ["pi"], "expected_events": ["compare", "fallback"]}
    string_errors = errors_for(
        [
            _family_contract_event(0, "create", ["text", "pattern"], state={"text": "ababc", "pattern": "abc", "i": 0, "family_contract": string_contract}, reason="初始化字符串。"),
            _family_contract_event(1, "mark", ["text[2]"], role="answer", state={"text": "ababc", "pattern": "abc", "i": 2, "answer": 2, "family_contract": string_contract}, reason="匹配完成。"),
        ],
        "String family contract negative",
    )
    assert any("Family contract string" in error and "pattern 指针" in error for error in string_errors), string_errors
    assert any("Family contract string" in error and "表结构" in error for error in string_errors), string_errors
    assert any("Family contract string" in error and "失配/扩展" in error for error in string_errors), string_errors

    tree_contract = {"family": "tree", "submode": "postorder", "expected_nodes": ["1"], "expected_frames": ["frame:dfs(1)"]}
    tree_errors = errors_for(
        [
            _family_contract_event(0, "create", ["tree"], state={"tree": {"nodes": [{"id": "1"}], "edges": []}, "current": "1", "family_contract": tree_contract}, reason="初始化树。"),
            _family_contract_event(1, "mark", ["node:1"], role="answer", state={"tree": {"nodes": [{"id": "1"}], "edges": []}, "current": "1", "answer": ["1"], "family_contract": tree_contract}, reason="直接给出结果。"),
        ],
        "Tree family contract negative",
    )
    assert any("Family contract tree" in error and "enter/exit" in error for error in tree_errors), tree_errors
    assert any("Family contract tree" in error and "返回值" in error for error in tree_errors), tree_errors

    backtracking_contract = {"family": "backtracking", "submode": "permutation", "expected_events": ["choose", "record", "undo"]}
    backtracking_errors = errors_for(
        [
            _family_contract_event(0, "create", ["recursion_tree"], state={"nums": [1], "path": [], "used": [False], "answer": [], "recursion_tree": {"nodes": [{"id": "root"}], "edges": []}, "family_contract": backtracking_contract}, reason="初始化。"),
            _family_contract_event(1, "mark", ["answer"], role="answer", state={"nums": [1], "path": [], "used": [False], "answer": [[1]], "recursion_tree": {"nodes": [{"id": "root"}], "edges": []}, "family_contract": backtracking_contract}, reason="直接给出答案。"),
        ],
        "Backtracking family contract negative",
    )
    assert any("Family contract backtracking" in error and "choose" in error for error in backtracking_errors), backtracking_errors
    assert any("Family contract backtracking" in error and "undo" in error for error in backtracking_errors), backtracking_errors

    heap_contract = {"family": "heap", "submode": "topk", "expected_events": ["push", "pop"]}
    heap_errors = errors_for(
        [
            _family_contract_event(0, "create", ["heap"], state={"nums": [3, 1], "heap": [], "heap_type": "min", "k": 1, "family_contract": heap_contract}, reason="初始化堆。"),
            _family_contract_event(1, "push", ["heap"], value=3, deps=["nums[0]"], state={"nums": [3, 1], "heap": [3], "heap_type": "min", "k": 1, "family_contract": heap_contract}, reason="加入堆。"),
        ],
        "Heap family contract negative",
    )
    assert any("Family contract heap" in error and "pop" in error for error in heap_errors), heap_errors
    assert any("Family contract heap" in error and "heap_top" in error for error in heap_errors), heap_errors

    trie_contract = {"family": "trie", "submode": "insert_search", "expected_events": ["create_node", "terminal", "prefix_count"]}
    trie_errors = errors_for(
        [
            _family_contract_event(0, "create", ["trie"], state={"words": ["a"], "prefix": "a", "trie": {"nodes": [{"id": "root"}], "edges": []}, "family_contract": trie_contract}, reason="初始化 Trie。"),
            _family_contract_event(1, "link", ["node:root_a"], deps=["node:root"], state={"words": ["a"], "prefix": "a", "trie": {"nodes": [{"id": "root"}, {"id": "root_a", "label": "a"}], "edges": [["root", "root_a"]]}, "family_contract": trie_contract}, reason="创建节点。"),
        ],
        "Trie family contract negative",
    )
    assert any("Family contract trie" in error and "terminal" in error for error in trie_errors), trie_errors
    assert any("Family contract trie" in error and "count" in error for error in trie_errors), trie_errors

    linked_contract = {"family": "linked_list", "submode": "reverse", "expected_events": ["move_pointer", "link_change"]}
    linked_errors = errors_for(
        [
            _family_contract_event(0, "create", ["linked_list"], state={"linked_list": {"nodes": [{"id": "1"}, {"id": "2"}], "edges": [["1", "2"]]}, "family_contract": linked_contract}, reason="初始化链表。"),
            _family_contract_event(1, "mark", ["node:2"], role="answer", state={"linked_list": {"nodes": [{"id": "1"}, {"id": "2"}], "edges": [["2", "1"]]}, "answer": [2, 1], "family_contract": linked_contract}, reason="直接给出最终链。"),
        ],
        "Linked list family contract negative",
    )
    assert any("Family contract linked_list" in error and "pointer" in error for error in linked_errors), linked_errors
    assert any("Family contract linked_list" in error and "next/prev" in error for error in linked_errors), linked_errors


def test_phase13_array_pointer_validator_rejects_process_errors_and_tracks_samples():
    profiles = {profile.family: profile for profile in __import__("algolab.verification.process_validator", fromlist=["process_validation_registry"]).process_validation_registry()}
    assert "array_pointer" in profiles
    assert profiles["array_pointer"].status == "strong"

    array_pointer_samples = [
        sample
        for case in benchmark_cases()
        if case.process_profile == "array_pointer"
        for sample in case.samples
    ]
    assert len(array_pointer_samples) >= 18

    valid_two_pointer_errors = _process_errors_for(
        _array_contract_trace(
            "Two pointer pair sum trace",
            {"nums": [1, 2, 4, 6, 10], "target": 8},
            [1, 3],
            [
                _family_contract_event(
                    0,
                    "create",
                    ["nums", "pointer:left", "pointer:right"],
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 4, "target": 8, "array_contract": {"submode": "two_pointer"}},
                    reason="初始化左右双指针。",
                ),
                _family_contract_event(
                    1,
                    "compare",
                    ["nums[0]", "nums[4]"],
                    value=11,
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 4, "target": 8, "sum": 11, "array_contract": {"submode": "two_pointer"}},
                    reason="比较左右指针元素之和。",
                ),
                _family_contract_event(
                    2,
                    "move",
                    ["pointer:right"],
                    value=3,
                    deps=["nums[0]", "nums[4]", "target"],
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 3, "target": 8, "array_contract": {"submode": "two_pointer"}},
                    reason="当前和大于 target，右指针左移。",
                ),
                _family_contract_event(
                    3,
                    "compare",
                    ["nums[0]", "nums[3]"],
                    value=7,
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 3, "target": 8, "sum": 7, "array_contract": {"submode": "two_pointer"}},
                    reason="比较移动后的两数之和。",
                ),
                _family_contract_event(
                    4,
                    "move",
                    ["pointer:left"],
                    value=1,
                    deps=["nums[0]", "nums[3]", "target"],
                    state={"nums": [1, 2, 4, 6, 10], "left": 1, "right": 3, "target": 8, "array_contract": {"submode": "two_pointer"}},
                    reason="当前和小于 target，左指针右移。",
                ),
                _family_contract_event(
                    5,
                    "mark",
                    ["nums[1]", "nums[3]"],
                    value=[1, 3],
                    state={"nums": [1, 2, 4, 6, 10], "left": 1, "right": 3, "target": 8, "sum": 8, "answer": [1, 3], "array_contract": {"submode": "two_pointer"}},
                    role="answer",
                    reason="两数之和等于 target，返回当前指针。",
                ),
            ],
        )
    )
    assert valid_two_pointer_errors == [], valid_two_pointer_errors

    wrong_mid_errors = _process_errors_for(
        _array_contract_trace(
            "Binary search wrong mid array pointer",
            {"nums": [1, 3, 5, 7], "target": 7},
            3,
            [
                _family_contract_event(0, "create", ["nums"], state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "mid": 3, "target": 7}, reason="初始化错误 mid。"),
                _family_contract_event(1, "compare", ["nums[3]", "pointer:mid"], value=3, state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "mid": 3, "target": 7}, reason="比较错误中点。"),
            ],
        )
    )
    assert any("mid" in error and "二分" in error for error in wrong_mid_errors), wrong_mid_errors

    wrong_shrink_errors = _process_errors_for(
        _array_contract_trace(
            "Binary search wrong shrink array pointer",
            {"nums": [1, 3, 5, 7], "target": 7},
            3,
            [
                _family_contract_event(0, "create", ["nums"], state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "target": 7}, reason="初始化。"),
                _family_contract_event(1, "compare", ["nums[1]", "pointer:mid"], value=1, state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "mid": 1, "target": 7}, reason="比较中点。"),
                _family_contract_event(2, "move", ["pointer:right"], value=0, deps=["nums[1]", "target"], state={"nums": [1, 3, 5, 7], "left": 0, "right": 0, "target": 7}, reason="错误地向左收缩。"),
            ],
        )
    )
    assert any("收缩方向错误" in error for error in wrong_shrink_errors), wrong_shrink_errors

    wrong_prefix_errors = _process_errors_for(
        _array_contract_trace(
            "Prefix sum wrong update",
            {"nums": [2, 4, 6], "query": [1, 2]},
            10,
            [
                _family_contract_event(0, "create", ["nums", "prefix"], state={"nums": [2, 4, 6], "prefix": [0, 0, 0, 0], "array_contract": {"submode": "prefix_sum", "expected_targets": ["prefix[1]", "prefix[2]", "prefix[3]"]}}, reason="初始化前缀数组。"),
                _family_contract_event(1, "set", ["prefix[1]"], value=2, deps=["prefix[0]", "nums[0]"], state={"nums": [2, 4, 6], "prefix": [0, 2, 0, 0], "i": 0, "array_contract": {"submode": "prefix_sum", "expected_targets": ["prefix[1]", "prefix[2]", "prefix[3]"]}}, reason="写入 prefix[1]。"),
                _family_contract_event(2, "set", ["prefix[2]"], value=7, deps=["prefix[1]", "nums[1]"], state={"nums": [2, 4, 6], "prefix": [0, 2, 7, 0], "i": 1, "array_contract": {"submode": "prefix_sum", "expected_targets": ["prefix[1]", "prefix[2]", "prefix[3]"]}}, reason="错误写入 prefix[2]。"),
            ],
        )
    )
    assert any("prefix" in error and "应为" in error for error in wrong_prefix_errors), wrong_prefix_errors

    wrong_diff_errors = _process_errors_for(
        _array_contract_trace(
            "Difference array wrong update",
            {"nums": [1, 1, 1], "updates": [[0, 1, 2]]},
            [3, 3, 1],
            [
                _family_contract_event(0, "create", ["diff"], state={"nums": [1, 1, 1], "diff": [1, 0, 0, 0], "updates": [[0, 1, 2]], "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]}}, reason="初始化差分数组。"),
                _family_contract_event(1, "set", ["diff[0]"], value=3, deps=["diff[0]", "updates[0]"], state={"nums": [1, 1, 1], "diff": [3, 0, 0, 0], "updates": [[0, 1, 2]], "update_index": 0, "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]}}, reason="区间左端加 delta。"),
                _family_contract_event(2, "set", ["diff[2]"], value=0, deps=["diff[2]", "updates[0]"], state={"nums": [1, 1, 1], "diff": [3, 0, 0, 0], "updates": [[0, 1, 2]], "update_index": 0, "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]}}, reason="错误地没有在右端后一位减 delta。"),
            ],
        )
    )
    assert any("diff" in error and "应为" in error for error in wrong_diff_errors), wrong_diff_errors

    valid_diff_trace = _array_contract_trace(
        "Difference array valid update dependency",
        {"nums": [1, 1, 1], "updates": [[0, 1, 2]]},
        [3, 3, 1],
        [
            _family_contract_event(
                0,
                "create",
                ["diff"],
                state={
                    "nums": [1, 1, 1],
                    "diff": [1, 0, 0, 0],
                    "updates": [[0, 1, 2]],
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                reason="初始化差分数组。",
            ),
            _family_contract_event(
                1,
                "set",
                ["diff[0]"],
                value=3,
                deps=["diff[0]", "updates[0]"],
                state={
                    "nums": [1, 1, 1],
                    "diff": [3, 0, 0, 0],
                    "updates": [[0, 1, 2]],
                    "update_index": 0,
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                reason="区间左端差分加 delta。",
            ),
            _family_contract_event(
                2,
                "set",
                ["diff[2]"],
                value=-2,
                deps=["diff[2]", "updates[0]"],
                state={
                    "nums": [1, 1, 1],
                    "diff": [3, 0, -2, 0],
                    "updates": [[0, 1, 2]],
                    "update_index": 0,
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                reason="区间右端后一位差分减 delta。",
            ),
            _family_contract_event(
                3,
                "mark",
                ["diff"],
                value=[3, 3, 1],
                state={
                    "nums": [1, 1, 1],
                    "diff": [3, 0, -2, 0],
                    "updates": [[0, 1, 2]],
                    "answer": [3, 3, 1],
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                role="answer",
                reason="前缀还原最终数组。",
            ),
        ],
    )
    valid_diff_trace_errors, valid_diff_process_errors, valid_diff_scene_errors = _contract_stack_errors(valid_diff_trace)
    assert valid_diff_trace_errors == []
    assert valid_diff_process_errors == []
    assert valid_diff_scene_errors == []

    window_jump_errors = _process_errors_for(
        _array_contract_trace(
            "Sliding window jump",
            {"nums": [1, 2, 3], "target": 3},
            2,
            [
                _family_contract_event(0, "create", ["nums"], state={"nums": [1, 2, 3], "left": 0, "right": 0, "window_sum": 1, "array_contract": {"submode": "sliding_window"}}, reason="初始化窗口。"),
                _family_contract_event(1, "move", ["pointer:right"], value=2, state={"nums": [1, 2, 3], "left": 0, "right": 2, "window_sum": 6, "array_contract": {"submode": "sliding_window"}}, reason="错误跳过一个窗口位置。"),
            ],
        )
    )
    assert any("窗口" in error and "跳变" in error for error in window_jump_errors), window_jump_errors


def test_phase13_dp_validator_expands_family_core_samples_and_rejects_digit_dp_errors():
    profiles = {profile.family: profile for profile in __import__("algolab.verification.process_validator", fromlist=["process_validation_registry"]).process_validation_registry()}
    assert "dp" in profiles
    assert profiles["dp"].status == "strong"

    dp_cases = [
        case
        for case in benchmark_cases()
        if case.gate_layer == "family_core" and case.process_profile == "dp"
    ]
    dp_samples = [sample for case in dp_cases for sample in case.samples]
    subfamilies = {case.subfamily_id for case in dp_cases}
    assert len(dp_samples) >= 35
    assert {
        "house_robber",
        "unique_paths",
        "knapsack_01",
        "complete_knapsack",
        "bounded_knapsack",
        "lcs",
        "edit_distance",
        "interval_dp",
        "tree_max_independent_set",
        "state_compression",
        "digit_dp",
    } <= subfamilies

    def assert_dp_error(raw_trace: dict, *expected_terms: str) -> None:
        errors = _process_errors_for(raw_trace)
        assert any(all(term in error for term in expected_terms) for error in errors), errors

    house_robber_contract = {
        "containers": ["dp"],
        "answer_position": "dp[2]",
        "expected_targets": ["dp[2]"],
        "subfamily": "house_robber",
    }
    assert_dp_error(
        _dp_contract_trace(
            "打家劫舍 DP 错误转移",
            {"nums": [2, 7, 9]},
            11,
            [
                _dp_contract_event(0, "create", ["dp"], state={"nums": [2, 7, 9], "dp": [2, 7, 0], "i": 1, "formula": "dp[1]=max(nums[0], nums[1])", "dp_contract": house_robber_contract}),
                _dp_contract_event(1, "set", ["dp[2]"], value=99, before=0, deps=["dp[1]", "dp[0]", "nums[2]"], state={"nums": [2, 7, 9], "dp": [2, 7, 99], "i": 2, "formula": "dp[i]=max(dp[i-1], dp[i-2]+nums[i])", "dp_contract": house_robber_contract}),
                _dp_contract_event(2, "mark", ["dp[2]"], value=99, deps=["dp[2]"], role="answer", state={"nums": [2, 7, 9], "dp": [2, 7, 99], "i": 2, "answer": 99, "formula": "answer=dp[2]", "dp_contract": house_robber_contract}),
            ],
        ),
        "打家劫舍",
        "不满足",
    )

    unique_paths_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1][1]",
        "expected_targets": ["dp[1][1]"],
        "subfamily": "unique_paths",
    }
    assert_dp_error(
        _dp_contract_trace(
            "不同路径 DP 错误转移",
            {"m": 2, "n": 2},
            2,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [[1, 1], [1, 0]], "i": 0, "j": 0, "formula": "boundary=1", "dp_contract": unique_paths_contract}),
                _dp_contract_event(1, "set", ["dp[1][1]"], value=3, before=0, deps=["dp[0][1]", "dp[1][0]"], state={"dp": [[1, 1], [1, 3]], "i": 1, "j": 1, "formula": "dp[i][j]=dp[i-1][j]+dp[i][j-1]", "dp_contract": unique_paths_contract}),
                _dp_contract_event(2, "mark", ["dp[1][1]"], value=3, deps=["dp[1][1]"], role="answer", state={"dp": [[1, 1], [1, 3]], "i": 1, "j": 1, "answer": 3, "formula": "answer=dp[1][1]", "dp_contract": unique_paths_contract}),
            ],
        ),
        "不同路径",
        "不满足",
    )

    subset_contract = {
        "containers": ["dp"],
        "answer_position": "dp[11]",
        "expected_targets": ["dp[5]"],
        "subfamily": "knapsack_01",
    }
    assert_dp_error(
        _dp_contract_trace(
            "0-1 背包可达性错误",
            {"nums": [1, 5, 11, 5]},
            True,
            [
                _dp_contract_event(0, "create", ["dp"], state={"nums": [1, 5, 11, 5], "target": 11, "dp": [True] + [False] * 11, "i": -1, "formula": "dp[0]=True", "dp_contract": subset_contract}),
                _dp_contract_event(1, "set", ["dp[5]"], value=True, before=False, deps=["dp[4]", "nums[0]"], state={"nums": [1, 5, 11, 5], "target": 11, "dp": [True, True, False, False, False, True, False, False, False, False, False, False], "i": 0, "capacity_index": 5, "formula": "dp[j]=dp[j] or dp[j-num]", "dp_contract": subset_contract}),
                _dp_contract_event(2, "mark", ["dp[11]"], value=True, deps=["dp[11]"], role="answer", state={"nums": [1, 5, 11, 5], "target": 11, "dp": [True, True, False, False, False, True, False, False, False, False, False, True], "i": 0, "capacity_index": 11, "answer": True, "formula": "answer=dp[target]", "dp_contract": subset_contract}),
            ],
        ),
        "0-1 背包",
        "不满足",
    )

    complete_contract = {
        "containers": ["dp"],
        "answer_position": "dp[3]",
        "expected_targets": ["dp[3]"],
        "subfamily": "complete_knapsack",
    }
    assert_dp_error(
        _dp_contract_trace(
            "完全背包零钱兑换错误",
            {"coins": [2], "amount": 3},
            -1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"coins": [2], "amount": 3, "dp": [0, -1, -1, -1], "i": -1, "formula": "dp[0]=0", "dp_mode": "complete_min", "dp_contract": complete_contract}),
                _dp_contract_event(1, "set", ["dp[3]"], value=1, before=-1, deps=["dp[1]", "coins[0]"], state={"coins": [2], "amount": 3, "dp": [0, -1, 1, 1], "i": 0, "capacity_index": 3, "formula": "dp[j]=min(dp[j], dp[j-coin]+1)", "dp_mode": "complete_min", "dp_contract": complete_contract}),
                _dp_contract_event(2, "mark", ["dp[3]"], value=1, deps=["dp[3]"], role="answer", state={"coins": [2], "amount": 3, "dp": [0, -1, 1, 1], "i": 0, "capacity_index": 3, "answer": 1, "formula": "answer=dp[amount]", "dp_mode": "complete_min", "dp_contract": complete_contract}),
            ],
        ),
        "完全背包",
        "不满足",
    )

    lcs_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1][1]",
        "expected_targets": ["dp[1][1]"],
        "subfamily": "lcs",
    }
    assert_dp_error(
        _dp_contract_trace(
            "LCS 错误转移",
            {"text1": "a", "text2": "a"},
            1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [[0, 0], [0, 0]], "i": 0, "j": 0, "formula": "boundary=0", "dp_contract": lcs_contract}),
                _dp_contract_event(1, "set", ["dp[1][1]"], value=0, before=0, deps=["dp[0][0]", "text1[0]", "text2[0]"], state={"dp": [[0, 0], [0, 0]], "i": 1, "j": 1, "formula": "dp[i][j]=dp[i-1][j-1]+1", "dp_contract": lcs_contract}),
                _dp_contract_event(2, "mark", ["dp[1][1]"], value=0, deps=["dp[1][1]"], role="answer", state={"dp": [[0, 0], [0, 0]], "i": 1, "j": 1, "answer": 0, "formula": "answer=dp[m][n]", "dp_contract": lcs_contract}),
            ],
        ),
        "LCS",
        "不满足",
    )

    edit_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1][1]",
        "expected_targets": ["dp[1][1]"],
        "subfamily": "edit_distance",
    }
    assert_dp_error(
        _dp_contract_trace(
            "编辑距离错误转移",
            {"word1": "a", "word2": "b"},
            1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [[0, 1], [1, 0]], "i": 0, "j": 0, "formula": "boundary=i or j", "dp_contract": edit_contract}),
                _dp_contract_event(1, "set", ["dp[1][1]"], value=0, before=0, deps=["dp[0][1]", "dp[1][0]", "dp[0][0]"], state={"dp": [[0, 1], [1, 0]], "i": 1, "j": 1, "formula": "dp[i][j]=min(delete, insert, replace)+1", "dp_contract": edit_contract}),
                _dp_contract_event(2, "mark", ["dp[1][1]"], value=0, deps=["dp[1][1]"], role="answer", state={"dp": [[0, 1], [1, 0]], "i": 1, "j": 1, "answer": 0, "formula": "answer=dp[m][n]", "dp_contract": edit_contract}),
            ],
        ),
        "编辑距离",
        "不满足",
    )

    interval_contract = {
        "containers": ["dp"],
        "answer_position": "dp[0][1]",
        "expected_targets": ["dp[0][1]"],
        "subfamily": "interval_dp",
    }
    assert_dp_error(
        _dp_contract_trace(
            "区间 DP 合并石子错误转移",
            {"stones": [1, 2]},
            3,
            [
                _dp_contract_event(0, "create", ["dp"], state={"stones": [1, 2], "dp": [[0, 0], [0, 0]], "i": 0, "j": 0, "formula": "dp[i][i]=0", "dp_mode": "merge_stones", "dp_contract": interval_contract}),
                _dp_contract_event(1, "set", ["dp[0][1]"], value=4, before=0, deps=["dp[0][0]", "dp[1][1]"], state={"stones": [1, 2], "dp": [[0, 4], [0, 0]], "i": 0, "j": 1, "k": 0, "formula": "dp[i][j]=min(dp[i][k]+dp[k+1][j])+sum(i,j)", "dp_mode": "merge_stones", "dp_contract": interval_contract}),
                _dp_contract_event(2, "mark", ["dp[0][1]"], value=4, deps=["dp[0][1]"], role="answer", state={"stones": [1, 2], "dp": [[0, 4], [0, 0]], "i": 0, "j": 1, "answer": 4, "formula": "answer=dp[0][n-1]", "dp_mode": "merge_stones", "dp_contract": interval_contract}),
            ],
        ),
        "区间 DP",
        "不满足",
    )

    tree_contract = {
        "containers": ["dp_take", "dp_skip"],
        "answer_position": "dp_take[1]",
        "expected_targets": ["dp_take[1]"],
        "subfamily": "tree_max_independent_set",
    }
    tree = {"nodes": [{"id": "1", "value": 3}], "edges": []}
    assert_dp_error(
        _dp_contract_trace(
            "树形 DP 错误转移",
            {"tree": tree},
            3,
            [
                _dp_contract_event(0, "create", ["tree"], state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "formula": "postorder tree dp", "dp_contract": tree_contract}),
                _dp_contract_event(1, "set", ["dp_take[1]"], value=4, before=None, deps=["node:1", "dp_skip[1]"], state={"tree": tree, "current": "1", "dp_take": {"1": 4}, "dp_skip": {"1": 0}, "formula": "dp_take[u]=weight[u]+sum(dp_skip[child])", "dp_contract": tree_contract}),
                _dp_contract_event(2, "mark", ["dp_take[1]"], value=4, deps=["dp_take[1]"], role="answer", state={"tree": tree, "current": "1", "dp_take": {"1": 4}, "dp_skip": {"1": 0}, "answer": 4, "formula": "answer=max(dp_take[root], dp_skip[root])", "dp_contract": tree_contract}),
            ],
        ),
        "树形 DP",
        "应为",
    )

    bitmask_contract = {
        "containers": ["dp"],
        "answer_position": "dp[3]",
        "expected_targets": ["dp[1]", "dp[3]"],
        "subfamily": "state_compression",
    }
    assert_dp_error(
        _dp_contract_trace(
            "状态压缩 DP 合同缺少依赖",
            {"item_count": 2},
            2,
            [
                _dp_contract_event(0, "create", ["dp"], state={"item_count": 2, "dp": [0, 0, 0, 0], "mask": 0, "formula": "dp[0]=0", "dp_contract": bitmask_contract}),
                _dp_contract_event(1, "set", ["dp[1]"], value=1, before=0, deps=[], state={"item_count": 2, "dp": [0, 1, 0, 0], "mask": 1, "formula": "dp[mask]=popcount(mask)", "dp_contract": bitmask_contract}),
                _dp_contract_event(2, "set", ["dp[3]"], value=2, before=0, deps=["dp[1]"], state={"item_count": 2, "dp": [0, 1, 0, 2], "mask": 3, "formula": "dp[mask]=popcount(mask)", "dp_contract": bitmask_contract}),
                _dp_contract_event(3, "mark", ["dp[3]"], value=2, deps=["dp[3]"], role="answer", state={"item_count": 2, "dp": [0, 1, 0, 2], "mask": 3, "answer": 2, "formula": "answer=dp[(1<<n)-1]", "dp_contract": bitmask_contract}),
            ],
        ),
        "DP contract",
        "deps",
    )

    digit_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1]",
        "expected_targets": ["dp[1]"],
        "subfamily": "digit_dp",
    }
    digit_errors = _process_errors_for(
        _dp_contract_trace(
            "数位 DP 统计不含 7 的数字",
            {"n": 20},
            18,
            [
                _dp_contract_event(
                    0,
                    "create",
                    ["dp"],
                    state={"digits": [2, 0], "dp": [1, 0], "digit": 0, "tight": True, "formula": "dp[0]=1", "dp_contract": digit_contract},
                    reason="初始化数位 DP。",
                ),
                _dp_contract_event(
                    1,
                    "set",
                    ["dp[1]"],
                    value=19,
                    before=0,
                    deps=["dp[0]"],
                    state={"digits": [2, 0], "dp": [1, 19], "digit": 1, "tight": False, "formula": "dp[pos+1]+=dp[pos]*valid_choices", "dp_contract": digit_contract},
                    reason="错误地把数字 7 也计入可选分支。",
                ),
                _dp_contract_event(
                    2,
                    "mark",
                    ["dp[1]"],
                    value=19,
                    deps=["dp[1]"],
                    role="answer",
                    state={"digits": [2, 0], "dp": [1, 19], "digit": 1, "answer": 19, "formula": "answer=dp[1]", "dp_contract": digit_contract},
                    reason="返回错误计数。",
                ),
            ],
        )
    )
    assert any("数位 DP" in error and "应为" in error for error in digit_errors), digit_errors

    bounded_contract = {
        "containers": ["dp"],
        "answer_position": "dp[5]",
        "expected_targets": ["dp[5]"],
        "subfamily": "bounded_knapsack",
    }
    bounded_errors = _process_errors_for(
        _dp_contract_trace(
            "多重背包最大价值",
            {"weights": [2], "values": [3], "counts": [2], "capacity": 5},
            6,
            [
                _dp_contract_event(
                    0,
                    "create",
                    ["dp"],
                    state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 0, 0, 0, 0], "i": -1, "formula": "dp[c]=0", "dp_contract": bounded_contract},
                    reason="初始化多重背包 DP。",
                ),
                _dp_contract_event(
                    1,
                    "set",
                    ["dp[5]"],
                    value=9,
                    before=0,
                    deps=["dp[1]", "weights[0]", "values[0]"],
                    state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 3, 3, 6, 9], "i": 0, "capacity_index": 5, "formula": "dp[c]=max(dp[c], prev[c-k*w]+k*v)", "dp_contract": bounded_contract},
                    reason="错误地使用超过 count 的物品数量。",
                ),
                _dp_contract_event(
                    2,
                    "mark",
                    ["dp[5]"],
                    value=9,
                    deps=["dp[5]"],
                    role="answer",
                    state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 3, 3, 6, 9], "i": 0, "capacity_index": 5, "answer": 9, "formula": "answer=dp[capacity]", "dp_contract": bounded_contract},
                    reason="返回错误最大价值。",
                ),
            ],
        )
    )
    assert any("多重背包" in error and "应为" in error for error in bounded_errors), bounded_errors


def test_phase13_graph_validator_expands_core_shortest_mst_samples_and_rejects_process_errors():
    profiles = {
        profile.family: profile
        for profile in __import__(
            "algolab.verification.process_validator",
            fromlist=["process_validation_registry"],
        ).process_validation_registry()
    }
    assert "bfs" in profiles
    assert profiles["bfs"].status == "strong"
    assert "shortest_path_mst" in profiles
    assert profiles["shortest_path_mst"].status == "strong"

    basic_graph_cases = [
        case
        for case in benchmark_cases()
        if case.gate_layer == "family_core" and case.family_id == "basic_graph"
    ]
    basic_graph_samples = [sample for case in basic_graph_cases for sample in case.samples]
    basic_graph_subfamilies = {case.subfamily_id for case in basic_graph_cases}
    assert len(basic_graph_samples) >= 22
    assert {
        "bfs_shortest_layers",
        "dfs_traversal",
        "connected_components",
        "topological_sort",
        "bipartite_coloring",
    } <= basic_graph_subfamilies

    shortest_mst_cases = [
        case
        for case in benchmark_cases()
        if case.gate_layer == "family_core" and case.family_id == "shortest_path_mst"
    ]
    shortest_mst_samples = [sample for case in shortest_mst_cases for sample in case.samples]
    shortest_mst_subfamilies = {case.subfamily_id for case in shortest_mst_cases}
    assert len(shortest_mst_samples) >= 18
    assert {
        "dijkstra",
        "bellman_ford",
        "floyd_warshall",
        "zero_one_bfs",
        "kruskal_mst",
    } <= shortest_mst_subfamilies

    wrong_dijkstra_relax = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Dijkstra wrong relax",
            {"weighted_graph": {"A": [["B", 2]], "B": []}, "start": "A"},
            {"A": 0, "B": 2},
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["heap"],
                    state={
                        "weighted_graph": {"A": [["B", 2]], "B": []},
                        "heap": [[0, "A"]],
                        "dist": {"A": 0},
                        "parent": {},
                        "graph_contract": {"submode": "dijkstra", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="初始化 Dijkstra 堆。",
                ),
                _graph_contract_event(
                    1,
                    "set",
                    ["dist[B]"],
                    value=3,
                    after=3,
                    deps=["dist[A]", "edge:A->B"],
                    state={
                        "weighted_graph": {"A": [["B", 2]], "B": []},
                        "heap": [[3, "B"]],
                        "dist": {"A": 0, "B": 3},
                        "parent": {"B": "A"},
                        "old_dist": None,
                        "new_dist": 3,
                        "current": "A",
                        "neighbor": "B",
                        "weight": 2,
                        "graph_contract": {"submode": "dijkstra", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="错误松弛 Dijkstra 距离。",
                ),
            ],
        )
    )
    assert any("Dijkstra" in error and "dist[B]" in error for error in wrong_dijkstra_relax), wrong_dijkstra_relax

    wrong_bellman_relax = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Bellman-Ford wrong relax",
            {"edges": [["A", "B", 2]], "start": "A"},
            {"A": 0, "B": 2},
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["dist"],
                    state={
                        "edges": [["A", "B", 2]],
                        "dist": {"A": 0, "B": float("inf")},
                        "round": 0,
                        "graph_contract": {"submode": "bellman_ford", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="初始化 Bellman-Ford 距离。",
                ),
                _graph_contract_event(
                    1,
                    "set",
                    ["dist[B]"],
                    value=5,
                    before=float("inf"),
                    after=5,
                    deps=["dist[A]", "edge:A->B"],
                    state={
                        "edges": [["A", "B", 2]],
                        "dist": {"A": 0, "B": 5},
                        "round": 1,
                        "current_edge": ["A", "B", 2],
                        "old_dist": float("inf"),
                        "new_dist": 5,
                        "graph_contract": {"submode": "bellman_ford", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="错误松弛 Bellman-Ford 距离。",
                ),
            ],
        )
    )
    assert any("Bellman-Ford" in error and "dist[B]" in error for error in wrong_bellman_relax), wrong_bellman_relax

    wrong_floyd_phase = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Floyd wrong transition",
            {"dist": [[0, 2, 9], [2, 0, 3], [9, 3, 0]]},
            [[0, 2, 5], [2, 0, 3], [5, 3, 0]],
            [
                _graph_contract_event(
                    0,
                    "set",
                    ["dist[0][2]"],
                    value=6,
                    before=9,
                    after=6,
                    deps=["dist[0][1]", "dist[1][2]"],
                    state={
                        "dist": [[0, 2, 6], [2, 0, 3], [9, 3, 0]],
                        "k": 1,
                        "i": 0,
                        "j": 2,
                        "graph_contract": {"submode": "floyd_warshall", "expected_relax_edges": ["0->2"]},
                    },
                    reason="错误 Floyd 中转松弛。",
                )
            ],
        )
    )
    assert any("Floyd" in error and "dist[0][2]" in error for error in wrong_floyd_phase), wrong_floyd_phase

    wrong_topo_indegree = _process_errors_for(
        _graph_contract_trace(
            "P13.3 topo wrong indegree",
            {"graph": {"A": ["B"], "B": []}},
            ["A", "B"],
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["queue"],
                    state={
                        "graph": {"A": ["B"], "B": []},
                        "queue": ["A"],
                        "indegree": {"A": 0, "B": 1},
                        "topo_order": [],
                        "graph_contract": {"submode": "topological_sort", "expected_nodes": ["A", "B"]},
                    },
                    reason="初始化拓扑入度。",
                ),
                _graph_contract_event(
                    1,
                    "set",
                    ["indegree[B]"],
                    value=1,
                    before=1,
                    after=1,
                    deps=["edge:A->B"],
                    state={
                        "graph": {"A": ["B"], "B": []},
                        "queue": ["B"],
                        "indegree": {"A": 0, "B": 1},
                        "topo_order": ["A"],
                        "current": "A",
                        "graph_contract": {"submode": "topological_sort", "expected_nodes": ["A", "B"]},
                    },
                    reason="错误地没有降低 B 的入度却让它入队。",
                ),
            ],
        )
    )
    assert any("topological_sort" in error and "indegree[B]" in error for error in wrong_topo_indegree), wrong_topo_indegree

    wrong_mst_cycle = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Kruskal wrong selected cycle",
            {"edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]]},
            2,
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["union_find"],
                    state={
                        "edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]],
                        "mst_edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]],
                        "union_find": {"parent": {"A": "A", "B": "A", "C": "A"}},
                        "edge_decision": "selected",
                        "graph_contract": {"submode": "mst", "expected_edges": ["A-B", "B-C"]},
                    },
                    reason="错误地选择了形成环的边。",
                )
            ],
        )
    )
    assert any("MST" in error and "环" in error for error in wrong_mst_cycle), wrong_mst_cycle


def test_benchmark_cases_are_multi_input_release_ready():
    cases = benchmark_cases()
    assert len(cases) >= 5
    for case in cases:
        assert len(case.samples) >= 2
        for index, sample in enumerate(case.samples):
            request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)
            artifact, errors = _try_materialize(request, spec_for_case(case))
            assert errors == [], (case.id, index, errors)
            assert artifact.validation.release_gate.release_ready, (case.id, index, artifact.validation.release_gate)
            assert len(artifact.variants) == 1
            assert artifact.variants[0].result == sample.expected
            assert artifact.verifier_result == sample.expected
            assert artifact.variants[0].trace is not None
            assert len(artifact.variants[0].trace.events) >= 1
            if case.id in contract_enabled_case_ids():
                assert artifact.correctness_contract is not None
                assert artifact.validation.contract_validation is not None
                assert artifact.validation.contract_validation.release_gate.contract_ready
                assert artifact.validation.contract_test_results
                assert all(item["ok"] for item in artifact.validation.contract_test_results)
            if index == 0:
                scene = artifact.scenes[case.id]
                layouts = {
                    obj.meta.get("layout")
                    for frame in scene.frames
                    for obj in frame.objects
                    if obj.type.value == "container"
                }
                for expected_layout in case.expected_layouts:
                    assert expected_layout in layouts, (case.id, index, expected_layout, layouts)


def test_benchmark_cases_expose_phase10_metadata():
    from scripts.check_family_capabilities import load_family_capabilities

    capabilities_by_label = {
        entry["label"]: entry for entry in load_family_capabilities()["families"]
    }
    valid_gate_layers = {"smoke", "family_core", "expansion", "llm_eval"}
    valid_support_levels = {"strong", "medium_plus", "medium", "basic", "planned"}
    valid_oracle_types = {"closed_form", "independent_reference", "bruteforce", "property"}

    for case in benchmark_cases():
        family_capability = capabilities_by_label[case.family]
        assert case.family_id == family_capability["family_id"], case.id
        assert case.process_profile == family_capability["process_profile"], case.id
        assert case.support_level == family_capability["current_level"], case.id
        assert case.subfamily_id, case.id
        assert case.gate_layer in valid_gate_layers, case.id
        assert case.support_level in valid_support_levels, case.id
        assert case.oracle_type in valid_oracle_types, case.id
        assert isinstance(case.demo_required, bool), case.id


def test_benchmark_cases_expose_phase11_oracle_metadata_and_independent_examples():
    from tests.oracles import oracle_examples

    valid_oracle_types = {"closed_form", "independent_reference", "bruteforce", "property"}
    valid_risks = {"none", "missing_verifier", "verifier_matches_solve"}
    example_families = {example["family_id"] for example in oracle_examples()}

    assert {"dp_1d", "basic_graph", "string_advanced", "sorting", "union_find", "range_structure"} <= example_families
    for example in oracle_examples():
        assert example["oracle_type"] in valid_oracle_types
        assert callable(example["reference"])
        assert example["notes"]

    risky_case_ids = {"tarjan_scc", "articulation_bridges", "bipartite_matching", "edmonds_karp"}
    for case in benchmark_cases():
        assert case.oracle_type in valid_oracle_types, case.id
        assert case.oracle_risk in valid_risks, case.id
        assert case.oracle_notes, case.id
        if not case.verifier_code.strip():
            assert case.oracle_risk == "missing_verifier", case.id
        if case.id in risky_case_ids:
            assert case.oracle_risk == "verifier_matches_solve", case.id
            assert "solve" in case.oracle_notes.lower() or "结构" in case.oracle_notes, case.id
        if case.support_level == "strong" and case.oracle_risk != "none":
            assert case.oracle_reference, case.id


def test_process_validator_rejects_missing_key_step_coverage_for_small_traces():
    dp_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "不同路径",
            "input_data": {"m": 2, "n": 2},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [[1, 1], [1, 2]]},
                    "reason": "只展示最终 DP 表。",
                    "code_line": 1,
                }
            ],
        }
    )
    bfs_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BFS 最短层数",
            "input_data": {"graph": {"A": ["B"], "B": []}, "start": "A"},
            "result": {"A": 0, "B": 1},
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "queue"}, {"id": "node:A"}],
                    "state": {"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0, "B": 1}},
                    "reason": "只展示 BFS 最终距离。",
                    "code_line": 1,
                }
            ],
        }
    )
    binary_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分查找",
            "input_data": {"nums": [1, 3, 5], "target": 5},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1, 3, 5], "left": 2, "right": 2, "target": 5},
                    "reason": "只展示最终搜索区间。",
                    "code_line": 1,
                }
            ],
        }
    )
    stack_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "每日温度",
            "input_data": {"temperatures": [30, 40]},
            "result": [1, 0],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "temperatures"}, {"id": "stack"}, {"id": "answer"}],
                    "state": {
                        "temperatures": [30, 40],
                        "stack": [],
                        "answer": [1, 0],
                        "stack_order": "decreasing",
                    },
                    "reason": "只展示最终答案。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("不同路径小 DP 表缺少逐帧状态转移" in error for error in dp_errors)
    assert any("BFS 小图缺少关键步骤覆盖" in error for error in bfs_errors)
    assert any("二分缺少关键步骤覆盖" in error for error in binary_errors)
    assert any("单调栈缺少关键步骤覆盖" in error for error in stack_errors)
    assert classify_failure("failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge") == "coverage_error"


def test_process_validator_rejects_bad_string_algorithm_tables():
    rabin_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Rabin-Karp 滚动哈希",
            "input_data": {"text": "abcd", "pattern": "bc"},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "window_hashes[1]"}],
                    "state": {
                        "text": "abcd",
                        "pattern": "bc",
                        "pattern_hash": 99,
                        "window_hashes": [10, 999, 30],
                    },
                    "reason": "错误滚动哈希。",
                    "code_line": 1,
                }
            ],
        }
    )
    z_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Z Algorithm",
            "input_data": {"text": "aabcaabx"},
            "result": [0, 1, 0, 0, 3, 1, 0, 0],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "z[4]"}],
                    "state": {"text": "aabcaabx", "z": [0, 1, 0, 0, 9, 1, 0, 0]},
                    "reason": "错误 Z 值。",
                    "code_line": 1,
                }
            ],
        }
    )
    manacher_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Manacher 回文半径",
            "input_data": {"text": "ababa"},
            "result": 5,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "radius[5]"}],
                    "state": {"text": "#a#b#a#b#a#", "radius": [0, 1, 0, 3, 0, 4, 0, 3, 0, 1, 0]},
                    "reason": "错误回文半径。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("Rabin-Karp" in error for error in rabin_errors), rabin_errors
    assert any("Z Algorithm" in error for error in z_errors), z_errors
    assert any("Manacher" in error for error in manacher_errors), manacher_errors


def test_convex_hull_trace_exposes_scan_phases_and_pop_steps():
    case = next(item for item in benchmark_cases() if item.id == "convex_hull")
    artifact, errors = materialize_case(case, sample_index=0)

    assert errors == []
    trace = artifact.variants[0].trace
    assert trace is not None
    events = trace.events
    states = [event.state for event in events]
    phases = [state.get("phase") for state in states]
    pop_events = [event for event in events if event.op.value == "pop"]
    current_values = [tuple(state.get("current")) for state in states if state.get("current") is not None]
    hull_snapshots = {
        tuple((state.get("geometry") or {}).get("hull") or [])
        for state in states
        if state.get("geometry")
    }
    scene = artifact.scenes[case.id]
    hull_edge_counts = [
        sum(1 for obj in frame.objects if obj.type.value == "edge" and obj.meta.get("shape") == "hull")
        for frame in scene.frames
    ]

    assert "lower" in phases
    assert "upper" in phases
    assert pop_events
    assert any("非左转" in event.reason for event in pop_events)
    assert len(set(current_values)) >= 3
    assert len(hull_snapshots) >= 4
    assert max(hull_edge_counts) > min(hull_edge_counts)


def test_phase7_string_algorithms_have_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "kmp": {"state_keys": {"text", "pattern", "pi"}, "target_prefix": "pi[", "reason_token": "回退"},
        "rabin_karp": {"state_keys": {"text", "pattern", "pattern_hash"}, "target_prefix": "window_hashes[", "reason_token": "哈希"},
        "z_algorithm": {"state_keys": {"text", "z"}, "target_prefix": "z[", "reason_token": "Z"},
        "manacher": {"state_keys": {"text", "radius"}, "target_prefix": "radius[", "reason_token": "半径"},
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert "string" in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
        for key in expectation["state_keys"]:
            assert key in object_ids, (case_id, key, sorted(object_ids)[:20])
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids), (case_id, target_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        assert expectation["reason_token"] in reasons, (case_id, reasons)

    example_names = {
        "string_kmp.md": ["string", "pi", "失配回退"],
        "string_rabin_karp.md": ["string", "pattern_hash", "滚动哈希"],
        "string_z_algorithm.md": ["string", "z", "Z-box"],
        "string_manacher.md": ["string", "radius", "半径扩展"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_tree_recursion_aggregates():
    diameter_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二叉树直径",
            "input_data": {
                "tree": {
                    "nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                    "edges": [["1", "2"], ["1", "3"]],
                }
            },
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "diameter[1]"}],
                    "state": {
                        "tree": {
                            "nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                            "edges": [["1", "2"], ["1", "3"]],
                        },
                        "current": "1",
                        "height": {"1": 2, "2": 1, "3": 1},
                        "diameter": {"1": 9, "2": 0, "3": 0},
                    },
                    "reason": "错误树直径聚合。",
                    "code_line": 1,
                }
            ],
        }
    )
    tree_dp_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树形 DP 最大独立集",
            "input_data": {
                "tree": {
                    "nodes": [{"id": "1", "value": 3}, {"id": "2", "value": 2}, {"id": "3", "value": 1}],
                    "edges": [["1", "2"], ["1", "3"]],
                }
            },
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dp_take[1]"}],
                    "state": {
                        "tree": {
                            "nodes": [{"id": "1", "value": 3}, {"id": "2", "value": 2}, {"id": "3", "value": 1}],
                            "edges": [["1", "2"], ["1", "3"]],
                        },
                        "current": "1",
                        "dp_take": {"1": 99, "2": 2, "3": 1},
                        "dp_skip": {"1": 3, "2": 0, "3": 0},
                    },
                    "reason": "错误树形 DP 聚合。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("树直径" in error for error in diameter_errors), diameter_errors
    assert any("树形 DP" in error for error in tree_dp_errors), tree_dp_errors


def test_phase7_tree_recursion_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "binary_tree_inorder": {"layout": "tree", "state_keys": {"current", "call_stack", "return_values"}, "reason_token": "中序"},
        "lca": {"layout": "tree", "state_keys": {"current", "call_stack", "return_values"}, "reason_token": "最近公共祖先"},
        "tree_diameter": {"layout": "tree", "state_keys": {"current", "call_stack", "height", "diameter"}, "reason_token": "子树高度"},
        "tree_max_independent_set": {"layout": "tree", "state_keys": {"current", "call_stack", "dp_take", "dp_skip"}, "reason_token": "子树聚合"},
        "permutations": {"layout": "recursion_tree", "state_keys": {"path", "call_stack", "return_values"}, "reason_token": "撤销选择"},
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        target_ids = {target.id for event in artifact.variants[0].trace.events for target in event.targets}
        dep_ids = {dep.id for event in artifact.variants[0].trace.events for dep in event.deps}
        assert any(target.startswith("frame:") for target in target_ids), (case_id, target_ids)
        assert any(target.startswith("node:") for target in target_ids), (case_id, target_ids)
        assert any(dep.startswith("frame:") for dep in dep_ids), (case_id, dep_ids)
        assert any(dep.startswith("node:") for dep in dep_ids), (case_id, dep_ids)
        arrow_pairs = {(obj.source, obj.target) for frame in scene.frames for obj in frame.objects if obj.type.value == "arrow"}
        assert any(source.startswith("frame:") and target.startswith("node:") for source, target in arrow_pairs) or any(
            source.startswith("node:") and target.startswith("frame:") for source, target in arrow_pairs
        ), (case_id, arrow_pairs)
        reasons = "\n".join(event.reason or "" for event in artifact.variants[0].trace.events)
        assert expectation["reason_token"] in reasons, (case_id, reasons)

    example_names = {
        "tree_inorder.md": ["tree", "call_stack", "返回值"],
        "tree_lca.md": ["tree", "frame:", "最近公共祖先"],
        "tree_diameter.md": ["tree", "height", "diameter"],
        "tree_dp.md": ["tree", "dp_take", "子树聚合"],
        "recursion_permutations.md": ["recursion_tree", "path", "撤销选择"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_range_structure_tables():
    segment_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "线段树区间和",
            "input_data": {"nums": [2, 1, 4], "query": [0, 2], "update": [1, 3]},
            "result": {"before": 7, "after": 9},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "node:seg_1_0_2"}],
                    "state": {
                        "nums": [2, 1, 4],
                        "query": [0, 2],
                        "segment_tree": {
                            "nodes": [
                                {"id": "seg_1_0_2", "label": "[0,2]=99", "meta": {"l": 0, "r": 2, "sum": 99}},
                                {"id": "seg_2_0_1", "label": "[0,1]=3", "meta": {"l": 0, "r": 1, "sum": 3}},
                                {"id": "seg_3_2_2", "label": "[2,2]=4", "meta": {"l": 2, "r": 2, "sum": 4}},
                            ],
                            "edges": [["seg_1_0_2", "seg_2_0_1"], ["seg_1_0_2", "seg_3_2_2"]],
                        },
                    },
                    "reason": "错误线段树聚合。",
                    "code_line": 1,
                }
            ],
        }
    )
    fenwick_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树状数组前缀和",
            "input_data": {"nums": [1, 2, 3, 4], "query": [1, 3], "update": [2, 1]},
            "result": {"before": 9, "after": 10},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "bit[2]"}],
                    "state": {"nums": [1, 2, 3, 4], "bit": [0, 1, 99, 3, 10], "query": [1, 3]},
                    "reason": "错误树状数组节点。",
                    "code_line": 1,
                }
            ],
        }
    )
    sparse_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "稀疏表区间最小值",
            "input_data": {"nums": [5, 2, 7, 3], "query": [1, 3]},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "st[1][1]"}],
                    "state": {"nums": [5, 2, 7, 3], "st": [[5, 2, 7, 3], [2, 9, 3], [2]], "log": [0, 0, 1, 1, 2], "query": [1, 3]},
                    "reason": "错误稀疏表单元。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("线段树" in error for error in segment_errors), segment_errors
    assert any("树状数组" in error for error in fenwick_errors), fenwick_errors
    assert any("稀疏表" in error for error in sparse_errors), sparse_errors


def test_phase7_range_structures_have_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "segment_tree_range_sum": {
            "layout": "tree",
            "state_keys": {"segment_tree", "nums", "query", "update", "answer"},
            "target_prefix": "node:seg_",
            "reason_tokens": ("查询区间", "更新路径"),
        },
        "fenwick_tree_prefix_sum": {
            "layout": "array",
            "state_keys": {"nums", "bit", "query", "update", "answer"},
            "target_prefix": "bit[",
            "reason_tokens": ("lowbit", "前缀", "更新路径"),
        },
        "sparse_table_range_min": {
            "layout": "matrix",
            "state_keys": {"nums", "st", "log", "query", "answer"},
            "target_prefix": "st[",
            "reason_tokens": ("稀疏表", "重叠区间"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("range:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids | dep_ids), (case_id, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "range_segment_tree.md": ["segment_tree", "node:seg_", "查询区间", "更新路径"],
        "range_fenwick_tree.md": ["bit[", "lowbit", "前缀"],
        "range_sparse_table.md": ["st[", "稀疏表", "重叠区间"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_math_bit_invariants():
    gcd_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "最大公约数 Euclid",
            "input_data": {"a": 48, "b": 18},
            "result": 6,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "remainders[0]"}],
                    "state": {"a": 48, "b": 18, "remainders": [99]},
                    "reason": "错误余数。",
                    "code_line": 1,
                }
            ],
        }
    )
    fast_power_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "快速幂",
            "input_data": {"base": 3, "exponent": 5, "mod": 13},
            "result": 9,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "powers[2]"}],
                    "state": {"base": 3, "exponent": 5, "mod": 13, "bits": [1, 0, 1], "powers": [3, 9, 99]},
                    "reason": "错误快速幂平方表。",
                    "code_line": 1,
                }
            ],
        }
    )
    sieve_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "埃氏筛",
            "input_data": {"n": 10},
            "result": [2, 3, 5, 7],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "is_prime[9]"}],
                    "state": {"n": 10, "is_prime": [False, False, True, True, False, True, False, True, False, True, False]},
                    "reason": "错误筛法倍数标记。",
                    "code_line": 1,
                }
            ],
        }
    )
    combination_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "组合数 Pascal",
            "input_data": {"n": 5, "k": 2},
            "result": 10,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "table[5][2]"}],
                    "state": {"n": 5, "k": 2, "table": [[1, 0, 0], [1, 1, 0], [1, 2, 1], [1, 3, 3], [1, 4, 6], [1, 99, 99]]},
                    "reason": "错误组合数表。",
                    "code_line": 1,
                }
            ],
        }
    )
    bitmask_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "位掩码枚举子集",
            "input_data": {"nums": [1, 2, 3]},
            "result": [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "bits[1]"}],
                    "state": {"nums": [1, 2, 3], "mask": 5, "bits": [1, 1, 1], "subset": [1, 2, 3]},
                    "reason": "错误位掩码位图。",
                    "code_line": 1,
                }
            ],
        }
    )
    lowbit_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "lowbit 分解",
            "input_data": {"n": 12},
            "result": [4, 8],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "lowbits[0]"}],
                    "state": {"n": 12, "remaining": 12, "lowbit": 99, "bits": [0, 0, 1, 1], "lowbits": [99]},
                    "reason": "错误 lowbit。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("最大公约数" in error or "GCD" in error for error in gcd_errors), gcd_errors
    assert any("快速幂" in error for error in fast_power_errors), fast_power_errors
    assert any("筛法" in error for error in sieve_errors), sieve_errors
    assert any("组合数" in error for error in combination_errors), combination_errors
    assert any("位掩码" in error for error in bitmask_errors), bitmask_errors
    assert any("lowbit" in error for error in lowbit_errors), lowbit_errors


def test_phase7_math_bit_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "gcd_euclid": {
            "layout": "array",
            "state_keys": {"a", "b", "remainders", "answer"},
            "target_prefix": "remainders[",
            "reason_tokens": ("最大公约数", "不变量"),
        },
        "fast_power_mod": {
            "layout": "array",
            "state_keys": {"base", "exponent", "mod", "bits", "powers", "answer"},
            "target_prefix": "powers[",
            "reason_tokens": ("快速幂", "指数"),
        },
        "sieve_primes": {
            "layout": "array",
            "state_keys": {"n", "is_prime", "current", "multiples", "answer"},
            "target_prefix": "is_prime[",
            "reason_tokens": ("筛法", "倍数"),
        },
        "combinations_pascal": {
            "layout": "matrix",
            "state_keys": {"n", "k", "table", "answer"},
            "target_prefix": "table[",
            "reason_tokens": ("组合数", "帕斯卡"),
        },
        "bitmask_subsets": {
            "layout": "array",
            "state_keys": {"nums", "mask", "bits", "subset", "answer"},
            "target_prefix": "bits[",
            "reason_tokens": ("位掩码", "子集"),
        },
        "lowbit_decomposition": {
            "layout": "array",
            "state_keys": {"n", "remaining", "bits", "lowbits", "answer"},
            "target_prefix": "lowbits[",
            "reason_tokens": ("lowbit", "最低位"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("number:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids | dep_ids), (case_id, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "math_gcd.md": ["remainders", "最大公约数", "不变量"],
        "math_fast_power.md": ["powers", "bits", "快速幂"],
        "math_sieve.md": ["is_prime", "筛法", "倍数"],
        "math_combinations.md": ["table", "组合数", "帕斯卡"],
        "bitmask_subsets.md": ["bits", "mask", "子集"],
        "bit_lowbit.md": ["lowbits", "lowbit", "最低位"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_advanced_graph_invariants():
    tarjan_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Tarjan 强连通分量",
            "input_data": {"graph": {"A": ["B"], "B": ["A"]}},
            "result": [["A", "B"]],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "low[A]"}],
                    "state": {
                        "graph": {"A": ["B"], "B": ["A"]},
                        "dfn": {"A": 1, "B": 2},
                        "low": {"A": 3, "B": 1},
                        "stack": ["A", "B"],
                        "on_stack": {"A": True, "B": True},
                    },
                    "reason": "错误 lowlink。",
                    "code_line": 1,
                }
            ],
        }
    )
    bridge_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "割点和桥 Tarjan",
            "input_data": {"graph": {"A": ["B"], "B": ["A", "C"], "C": ["B"]}},
            "result": {"articulation": ["B"], "bridges": [["A", "B"], ["B", "C"]]},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "edge:A->B"}],
                    "state": {
                        "graph": {"A": ["B"], "B": ["A", "C"], "C": ["B"]},
                        "dfn": {"A": 1, "B": 2, "C": 3},
                        "low": {"A": 1, "B": 1, "C": 3},
                        "parent": {"A": None, "B": "A", "C": "B"},
                        "bridges": [["A", "B"]],
                        "articulation": [],
                    },
                    "role": "bridge",
                    "reason": "错误桥判定。",
                    "code_line": 1,
                }
            ],
        }
    )
    matching_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分图匹配",
            "input_data": {"graph": {"L1": ["R1"], "L2": ["R1"]}, "left": ["L1", "L2"], "right": ["R1"]},
            "result": {"L1": "R1", "L2": "R1"},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "match[L2]"}],
                    "state": {
                        "graph": {"L1": ["R1"], "L2": ["R1"]},
                        "left_nodes": ["L1", "L2"],
                        "right_nodes": ["R1"],
                        "match": {"L1": "R1", "L2": "R1", "R1": "L2"},
                        "visited": {"R1": True},
                    },
                    "reason": "错误匹配：两个左侧点匹配同一个右侧点。",
                    "code_line": 1,
                }
            ],
        }
    )
    flow_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Edmonds-Karp 最大流",
            "input_data": {"graph": {"S": ["A"], "A": ["T"], "T": []}, "source": "S", "sink": "T"},
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "flow[S->A]"}],
                    "state": {
                        "graph": {"S": ["A"], "A": ["T"], "T": []},
                        "capacity": {"S->A": 2, "A->T": 2},
                        "flow": {"S->A": 3, "A->T": 1},
                        "queue": ["S"],
                        "parent": {"A": "S", "T": "A"},
                        "bottleneck": 3,
                    },
                    "reason": "错误 flow 超过容量。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("Tarjan" in error or "low" in error for error in tarjan_errors), tarjan_errors
    assert any("桥" in error or "bridge" in error.lower() for error in bridge_errors), bridge_errors
    assert any("匹配" in error or "match" in error.lower() for error in matching_errors), matching_errors
    assert any("flow" in error.lower() or "容量" in error for error in flow_errors), flow_errors


def test_phase7_advanced_graph_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "tarjan_scc": {
            "state_keys": {"graph", "dfn", "low", "stack", "on_stack", "component"},
            "target_prefixes": ("dfn[", "low[", "node:", "edge:"),
            "reason_tokens": ("Tarjan", "low"),
        },
        "articulation_bridges": {
            "state_keys": {"graph", "dfn", "low", "parent", "bridges", "articulation"},
            "target_prefixes": ("dfn[", "low[", "node:", "edge:"),
            "reason_tokens": ("割点", "桥"),
        },
        "bipartite_matching": {
            "state_keys": {"graph", "match", "visited", "left_nodes", "right_nodes"},
            "target_prefixes": ("match[", "node:", "edge:"),
            "reason_tokens": ("匹配", "增广"),
        },
        "edmonds_karp": {
            "state_keys": {"graph", "capacity", "flow", "queue", "parent", "bottleneck"},
            "target_prefixes": ("cap[", "flow[", "node:", "edge:"),
            "reason_tokens": ("Edmonds-Karp", "残量"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert "graph" in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert "graph" in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("flow:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        for prefix in expectation["target_prefixes"]:
            assert any(item.startswith(prefix) for item in target_ids | dep_ids), (case_id, prefix, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "graph_tarjan_scc.md": ["dfn", "low", "stack", "Tarjan"],
        "graph_articulation_bridges.md": ["dfn", "low", "桥", "割点"],
        "graph_bipartite_matching.md": ["match[", "增广", "匹配"],
        "graph_edmonds_karp.md": ["capacity", "flow[", "残量"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_contract_tests_block_bad_solve():
    case = next(item for item in benchmark_cases() if item.id == "two_sum")
    spec = spec_for_case(case)
    spec["variants"][0]["code"] = "def solve(input_data):\n    return [0, 1]"
    sample = case.samples[0]
    request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)

    artifact, errors = _try_materialize(request, spec)

    assert errors
    assert not artifact.validation.release_gate.release_ready
    assert artifact.validation.contract_test_results
    assert any(not item["ok"] for item in artifact.validation.contract_test_results)
    assert any("contract test_cases" in error for error in errors)


def test_benchmark_aggregate_artifact(tmp_path: Path):
    artifact = benchmark_coverage_artifact()
    assert len(artifact.variants) == len(benchmark_cases())
    assert len(artifact.scenes) == len(benchmark_cases())
    out = save_html(artifact, tmp_path / "benchmark_coverage.html")
    html = out.read_text(encoding="utf-8")
    assert "真实题型 Benchmark 覆盖" in html
    assert out.with_suffix(".json").exists()


def test_creative_renderer_contains_theme_controls_and_stage():
    artifact = benchmark_coverage_artifact()
    html = render_creative_html(artifact)
    assert "创意演示模式" in html
    assert 'data-theme-btn="fantasy"' in html
    assert 'data-theme-btn="cyber"' in html
    assert 'id="metaphor"' in html
    assert "renderMetaphor" in html


def test_llm_benchmark_request_uses_problem_and_expected():
    case = benchmark_cases()[0]
    sample = case.samples[0]
    request = make_request(case, sample, solutions=2)
    assert request.problem == case.problem
    assert request.input_data == sample.input_data
    assert request.expected_result == sample.expected
    assert request.strategy_hint == case.strategy
    assert request.solution_count == 2


def test_llm_client_reads_local_api_settings_without_committing_key(tmp_path: Path):
    settings_path = tmp_path / "api_settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "api_settings:",
                '  base_url: "http://example.test/v1"',
                '  api_key: "sk-test-local-only"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    import llm_client

    old_env = {
        key: os.environ.get(key)
        for key in ("ALGOLAB_LLM_API_KEY", "ALGOLAB_LLM_BASE_URL", "ALGOLAB_LLM_SETTINGS_FILE")
    }
    old_cache = llm_client._LOCAL_API_SETTINGS
    try:
        os.environ.pop("ALGOLAB_LLM_API_KEY", None)
        os.environ.pop("ALGOLAB_LLM_BASE_URL", None)
        os.environ["ALGOLAB_LLM_SETTINGS_FILE"] = str(settings_path)
        llm_client._LOCAL_API_SETTINGS = None
        config = llm_client.llm_config()
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        llm_client._LOCAL_API_SETTINGS = old_cache

    assert config["base_url"] == "http://example.test/v1"
    assert config["api_key_configured"] is True
    assert config["api_key_source"] == str(settings_path)
    assert "sk-test-local-only" not in json.dumps(config)


def test_llm_benchmark_sample_selection_and_failure_classification(tmp_path: Path):
    case = benchmark_cases()[0]
    args = argparse.Namespace(sample=1, all_samples=False)
    selected = selected_samples(case, args)
    assert len(selected) == 1
    assert selected[0][0] == 1
    assert classify_failure("RuntimeError: 缺少 ALGOLAB_LLM_API_KEY 环境变量") == "configuration"
    assert classify_failure("TimeoutError: LLM benchmark 超过 1 秒") == "timeout"
    assert classify_failure("严格模式拒绝 warning：x") == "visual_warning"
    assert classify_failure("严格模式拒绝 warning：failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge") == "coverage_error"
    assert classify_failure("第 3 步 dp[2] 不满足 0-1 背包可达性") == "process_invariant"
    assert classify_failure("failure_type=coverage_error: 小 DP 表缺少逐帧状态转移") == "coverage_error"
    assert classify_failure("failure_type=process_uncovered: 未注册算法族只执行基础门禁") == "process_uncovered"
    assert classify_failure("第 1 步 union_find 存在非根环") == "process_invariant"
    assert classify_failure("第 2 步 二分收缩方向错误：nums[1] < target") == "process_invariant"
    assert classify_failure("第 4 步 BFS 首次发现 node:B 来源应为上一层相邻节点") == "process_invariant"
    assert classify_failure("scene validator 渲染布局失败") == "visual_scene"
    assert classify_failure("solve 执行失败：NameError") == "execution"
    assert classify_failure("结果 1 与 expected 2 不一致") == "correctness"

    report_args = argparse.Namespace(
        case=[case.id],
        sample=1,
        all_samples=False,
        solutions=1,
        max_rounds=2,
        timeout_s=1,
        strict_warnings=True,
        browser_smoke=False,
        write_each=True,
        concurrency=1,
        condition="direct_html_baseline",
    )
    report_path = write_report(
        [
            {
                "case_id": case.id,
                "title": case.title,
                "family": case.family,
                "sample_index": 1,
                "ok": False,
                "failure_type": "timeout",
                "duration_s": 1.0,
            }
        ],
        tmp_path,
        args=report_args,
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["cached"] is False
    assert report["config"]["model"]
    assert report["config"]["sample"] == 1
    assert report["config"]["write_each"] is True
    assert report["config"]["concurrency"] == 1
    assert report["config"]["benchmark_condition"] == "direct_html_baseline"
    assert report["results"][0]["condition"] == "direct_html_baseline"
    assert report["failure_summary"] == {"timeout": 1}
    assert report["avg_duration_s"] == 1.0


def test_benchmark_report_summarizes_process_registry_failure_types(tmp_path: Path):
    case = benchmark_cases()[0]
    report_args = argparse.Namespace(
        case=[case.id],
        sample=1,
        all_samples=False,
        solutions=1,
        max_rounds=2,
        timeout_s=1,
        strict_warnings=True,
        browser_smoke=False,
        write_each=True,
        concurrency=1,
        condition="algolab_full",
    )

    report_path = write_report(
        [
            {
                "case_id": case.id,
                "title": case.title,
                "family": case.family,
                "sample_index": 1,
                "ok": False,
                "errors": ["failure_type=coverage_error: 小 DP 表缺少逐帧状态转移"],
                "duration_s": 1.0,
            },
            {
                "case_id": case.id,
                "title": case.title,
                "family": "未注册算法族",
                "sample_index": 1,
                "ok": False,
                "errors": ["failure_type=process_uncovered: 未注册算法族只执行基础门禁"],
                "duration_s": 1.0,
            },
        ],
        tmp_path,
        args=report_args,
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["failure_summary"] == {"coverage_error": 1, "process_uncovered": 1}
    assert [item["failure_type"] for item in report["results"]] == ["coverage_error", "process_uncovered"]


def test_llm_benchmark_phase_timing_helpers():
    phase_log = [
        {"event": "start", "phase": "generate", "at": 10.0},
        {"event": "end", "phase": "generate", "status": "ok", "duration_s": 2.5, "at": 12.5},
        {"event": "start", "phase": "repair_round_0", "at": 13.0},
    ]
    timings = completed_phase_timings(phase_log)
    assert timings == [{"phase": "generate", "duration_s": 2.5, "status": "ok"}]
    assert last_phase(phase_log) == "repair_round_0:中"
    assert last_phase_elapsed_s(phase_log, now=16.0) == 3.0
    results = [
        {"duration_s": 10, "phase_timings": timings},
        {"duration_s": 20, "phase_timings": [{"phase": "generate", "duration_s": 3.5, "status": "ok"}]},
    ]
    assert average_duration(results) == 15.0
    assert summarize_phase_timings(results)["generate"] == {"count": 2, "avg_s": 3.0, "max_s": 3.5}


def test_llm_benchmark_strict_warning_enters_repair(monkeypatch):
    request = ProblemInput(problem="警告修复测试", input_data={"nums": [2, 1]}, expected_result=[1, 2])
    gate = ReleaseGate(
        artifact_ready=True,
        process_ready=True,
        trace_ready=True,
        visual_ready=True,
        release_ready=True,
    )
    warned = BuildArtifact(
        problem_title="警告修复测试",
        input_contract="",
        input_data=request.input_data,
        expected_result=request.expected_result,
        variants=[],
        scenes={},
        validation=ValidationReport(warnings=["第 1 步 after 与 state 不一致：nums[0]"], release_gate=gate),
    )
    clean = BuildArtifact(
        problem_title="警告修复测试",
        input_contract="",
        input_data=request.input_data,
        expected_result=request.expected_result,
        variants=[],
        scenes={},
        validation=ValidationReport(warnings=[], release_gate=gate),
    )
    calls = {"materialize": 0, "repair_errors": []}

    def fake_generate(_request):
        return {"variants": []}

    def fake_materialize(_request, _spec):
        calls["materialize"] += 1
        return (warned if calls["materialize"] == 1 else clean), []

    def fake_repair(_request, spec, errors):
        calls["repair_errors"].append(errors)
        return spec

    monkeypatch.setattr("scripts.run_llm_benchmark.generate_solution_spec", fake_generate)
    monkeypatch.setattr("scripts.run_llm_benchmark._try_materialize", fake_materialize)
    monkeypatch.setattr("scripts.run_llm_benchmark.repair_solution_spec", fake_repair)

    artifact = build_artifact_timed(request, max_rounds=1, strict_warnings=True)

    assert artifact.validation.warnings == []
    assert calls["materialize"] == 2
    assert calls["repair_errors"] == [["严格模式拒绝 warning：第 1 步 after 与 state 不一致：nums[0]"]]


def test_llm_json_and_spec_normalization_helpers():
    parsed = parse_json_content('```json\n{"ok": true}\n```')
    assert parsed == {"ok": True}
    parsed = parse_json_content('说明\n{"ok": true, "items": [1, 2]}\n结束')
    assert parsed == {"ok": True, "items": [1, 2]}

    spec = normalize_solution_spec([{"id": "x", "code": "", "tracker_code": ""}])
    assert spec["problem_title"] == "算法可视化实验"
    assert len(spec["variants"]) == 1
    assert spec["variants"][0]["id"] == "x"
    spec = normalize_solution_spec({"variants": {"id": "y", "code": "", "tracker_code": ""}})
    assert len(spec["variants"]) == 1
    assert spec["variants"][0]["id"] == "y"


def test_existing_benchmark_html_report_helper(tmp_path: Path):
    report_path = tmp_path / "llm_benchmark_report.json"
    report_path.write_text(
        json.dumps(
            {
                "results": [
                    {"ok": True, "html": "output/a.html"},
                    {"ok": False, "html": "output/b.html"},
                    {"ok": True, "html": "output/c.html"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert html_paths_from_report(report_path) == [Path("output/a.html"), Path("output/c.html")]


def test_benchmark_html_checker_resolves_required_phase8_cases(tmp_path: Path):
    report = {
        "results": [
            {"case_id": "unique_paths", "ok": True, "html": str(tmp_path / "unique.html")},
            {"case_id": "graph_bfs", "ok": True, "html": str(tmp_path / "bfs.html")},
            {"case_id": "binary_search", "ok": True, "html": str(tmp_path / "binary.html")},
            {"case_id": "daily_temperatures", "ok": True, "html": str(tmp_path / "daily.html")},
            {"case_id": "two_sum", "ok": True, "html": str(tmp_path / "two_sum.html")},
        ]
    }
    report_path = tmp_path / "llm_benchmark_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    required = ["unique_paths", "graph_bfs", "binary_search", "daily_temperatures"]
    paths = resolve_required_case_htmls(report_path, required_cases=required)
    assert [path.name for path in paths] == ["unique.html", "bfs.html", "binary.html", "daily.html"]

    incomplete_path = tmp_path / "incomplete_report.json"
    incomplete_path.write_text(json.dumps({"results": report["results"][:3]}), encoding="utf-8")
    try:
        resolve_required_case_htmls(incomplete_path, required_cases=required)
    except ValueError as exc:
        assert "daily_temperatures" in str(exc)
    else:
        raise AssertionError("missing required case should fail")


def test_demo_dashboard_selection_defaults_to_curated_showcase():
    definitions = selected_demo_definitions()
    ids = [definition.id for definition in definitions]
    assert ids[0] == CUSTOM_SUBSET_SUM_ID
    assert len(ids) == 8
    assert "binary_search" in ids
    assert "graph_bfs" in ids
    assert "daily_temperatures" in ids
    assert "trie_prefix" in ids
    assert "provinces" in ids
    assert "permutations" in ids
    assert "convex_hull" in ids


def test_demo_dashboard_writes_bundle_and_index(tmp_path: Path):
    index = build_dashboard(
        tmp_path / "dashboard",
        demo_ids=[CUSTOM_SUBSET_SUM_ID, "binary_search"],
        style="both",
    )
    assert index.exists()
    report_path = index.with_name("dashboard.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["kind"] == "algolab_demo_dashboard"
    assert report["total"] == 2
    assert report["passed"] == 2
    assert report["failed"] == 0
    family_coverage = {item["family"]: item for item in report["family_coverage"]}
    assert {"0-1 背包 / 子集和", "二分"} <= set(family_coverage)
    assert family_coverage["0-1 背包 / 子集和"]["total"] == 1
    assert family_coverage["0-1 背包 / 子集和"]["passed"] == 1
    assert family_coverage["二分"]["layouts"]
    for demo in report["demos"]:
        bundle = index.parent / demo["bundle_dir"]
        assert (bundle / "request.json").exists()
        assert (bundle / "generated_spec.json").exists()
        assert (bundle / "correctness_contract.json").exists()
        assert (bundle / "visual_plan.json").exists()
        assert (bundle / "render_report.json").exists()
        assert (bundle / "capabilities.json").exists()
        assert (bundle / "artifact.json").exists()
        assert (bundle / "validation_report.json").exists()
        assert (bundle / "repair_log.json").exists()
        assert (bundle / "stable.html").exists()
        assert (bundle / "creative.html").exists()
        assert demo["ok"] is True
        assert demo["contract_gate_ready"] is True
        assert demo["oracle_strategy"] in {"generated_verifier", "expected_only"}
        assert "interaction_coverage" in demo
        interaction_count, frame_count = [int(part) for part in demo["interaction_coverage"].split("/", 1)]
        assert interaction_count >= 2
        assert frame_count >= interaction_count
        assert set(demo["interaction_types"]) <= {"choice", "input", "judge"}
        assert demo["interaction_types"]
        assert demo["visual_plan_stage"] in {"teaching_2d", "spatial_3d", "hybrid_2_5d", "creative"}
        assert demo["requested_render_target"] == demo["visual_plan_stage"]
        assert demo["actual_render_target"] in {"teaching_2d", "spatial_3d", "creative"}
        assert isinstance(demo["used_baseline_renderer"], bool)
        assert demo["correctness_contract_json"].endswith("correctness_contract.json")
        assert demo["visual_plan_json"].endswith("visual_plan.json")
        assert demo["render_report_json"].endswith("render_report.json")
        assert demo["capabilities_json"].endswith("capabilities.json")
        assert demo["artifact_json"].endswith("artifact.json")
        contract = json.loads((bundle / "correctness_contract.json").read_text(encoding="utf-8"))
        visual_plan = json.loads((bundle / "visual_plan.json").read_text(encoding="utf-8"))
        render_report = json.loads((bundle / "render_report.json").read_text(encoding="utf-8"))
        capabilities = json.loads((bundle / "capabilities.json").read_text(encoding="utf-8"))
        artifact = json.loads((bundle / "artifact.json").read_text(encoding="utf-8"))
        interactions = [
            frame["interaction"]
            for scene in artifact["scenes"].values()
            for frame in scene["frames"]
            if frame.get("interaction")
        ]
        assert len(interactions) >= 2
        assert contract["schema_version"] == "correctness-contract-v1"
        assert visual_plan["schema_version"] == "visual-plan-v1"
        assert render_report["schema_version"] == "render-report-v1"
        assert capabilities["schema_version"] == "runtime-capabilities-v1"
        assert {"teaching_2d", "spatial_3d", "hybrid_2_5d", "creative"} <= set(capabilities["render_targets"])
        assert "array" in capabilities["supported_layouts"]
        assert "node" in capabilities["primitive_3d_support"]
        assert capabilities["device_constraints"]["mobile_prefer_2d"] is True
        assert artifact["correctness_contract"]["schema_version"] == "correctness-contract-v1"
        assert artifact["visual_plan"]["schema_version"] == "visual-plan-v1"
        assert artifact["render_report"]["requested_target"] == demo["requested_render_target"]
        assert "contract_test_pass_rate" in demo
        assert demo["contract_test_pass_rate"] in {"", "0/0"} or "/" in demo["contract_test_pass_rate"]
        assert demo["stable_html"].endswith("stable.html")
        assert demo["creative_html"].endswith("creative.html")
    html = index.read_text(encoding="utf-8")
    core_table = index.with_name("dashboard_core_table.csv")
    assert core_table.exists()
    core_table_text = core_table.read_text(encoding="utf-8")
    assert "contract_test_pass_rate" in core_table_text
    assert "interaction_coverage" in core_table_text
    assert "actual_render_target" in core_table_text
    assert "AlgoLab Demo Dashboard" in html
    assert "contract" in html
    assert "VisualPlan" in html
    assert "render report" in html
    assert "capabilities" in html
    assert "oracle=" in html
    assert "交互题" in html
    assert "target" in html
    assert "稳定版" in html
    assert "创意版" in html
    assert "算法族覆盖" in html
    assert 'id="family-coverage"' in html
    assert 'id="family"' in html
    assert "artifact.json" in html


def test_demo_dashboard_groups_by_family_and_gate_layer(tmp_path: Path):
    index = build_dashboard(
        tmp_path / "dashboard",
        demo_ids=["binary_search", "graph_bfs"],
        style="stable",
    )
    report = json.loads(index.with_name("dashboard.json").read_text(encoding="utf-8"))

    for demo in report["demos"]:
        assert demo["family_id"]
        assert demo["subfamily_id"]
        assert demo["gate_layer"] == "family_core"
        assert demo["support_level"] == "strong"
        assert demo["process_profile"] in {"binary_search", "bfs"}
        assert demo["oracle_type"] in {"independent_reference", "property"}
        assert demo["oracle_risk"] == "none"
        assert demo["oracle_notes"]
        assert demo["demo_required"] is True

    coverage = {(row["family"], row["gate_layer"]): row for row in report["family_coverage"]}
    assert ("二分", "family_core") in coverage
    assert ("BFS/DFS 基础图", "family_core") in coverage
    assert coverage[("二分", "family_core")]["family_id"] == "binary_search"
    assert coverage[("BFS/DFS 基础图", "family_core")]["process_profile"] == "bfs"

    core_table = index.with_name("dashboard_core_table.csv").read_text(encoding="utf-8")
    for field in (
        "family_id",
        "subfamily_id",
        "gate_layer",
        "support_level",
        "process_profile",
        "oracle_type",
        "oracle_risk",
        "oracle_reference",
        "demo_required",
    ):
        assert field in core_table
    html = index.read_text(encoding="utf-8")
    assert "Gate layer" in html
    assert "family_core" in html


def test_runtime_capabilities_prompt_context_is_json():
    capabilities = runtime_capabilities()
    assert capabilities["schema_version"] == "runtime-capabilities-v1"
    assert "teaching_2d" in capabilities["render_targets"]
    assert "graph" in capabilities["supported_layouts"]
    assert "camera_focus" in capabilities["primitive_3d_support"]
    assert capabilities["device_constraints"]["max_nodes_3d"] == 120
    prompt_context = capabilities_prompt_context()
    parsed = json.loads(prompt_context)
    assert parsed == capabilities


def test_evaluation_manifest_covers_phase10_datasets(tmp_path: Path):
    manifest = build_manifest()
    assert manifest["schema_version"] == "evaluation-manifest-v1"
    assert manifest["summary"]["benchmark_case_count"] == len(benchmark_cases())
    assert manifest["summary"]["ml_demo_count"] >= 2
    assert manifest["summary"]["sample_count"] >= 35
    strata = manifest["strata"]
    assert "LeetCode 基础算法集" in strata
    assert "数据结构算法集" in strata
    assert "DP / graph / stack / tree / geometry 分层" in strata
    assert "ML demo 集" in strata
    assert {"linear_regression_single_step", "logistic_regression_boundary"} <= set(strata["ML demo 集"]["case_ids"])
    case_ids = {case["id"] for case in manifest["cases"]}
    assert {"two_sum", "daily_temperatures", "unique_paths", "graph_bfs"} <= case_ids
    cases_by_id = {case["id"]: case for case in manifest["cases"]}
    two_sum = cases_by_id["two_sum"]
    assert two_sum["problem"]
    assert two_sum["visual_forms"] == two_sum["expected_layouts"]
    assert "artifact_json" in two_sum["artifact_paths"]
    assert "html" in two_sum["artifact_paths"]
    assert len(two_sum["samples"]) == two_sum["sample_count"]
    assert two_sum["samples"][0]["input_data"] == next(case for case in benchmark_cases() if case.id == "two_sum").samples[0].input_data
    assert two_sum["samples"][0]["expected"] == next(case for case in benchmark_cases() if case.id == "two_sum").samples[0].expected
    assert two_sum["samples"][0]["artifact_paths"]["json"].endswith("llm_two_sum_0.json")
    assert two_sum["samples"][0]["artifact_paths"]["html"].endswith("llm_two_sum_0.html")

    path = write_manifest(tmp_path)
    assert path.exists()
    csv_path = tmp_path / "evaluation_cases.csv"
    sample_csv_path = tmp_path / "evaluation_samples.csv"
    assert csv_path.exists()
    assert sample_csv_path.exists()
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == manifest
    assert "linear_regression_single_step" in csv_path.read_text(encoding="utf-8")
    sample_csv_text = sample_csv_path.read_text(encoding="utf-8")
    assert "two_sum" in sample_csv_text
    assert "llm_two_sum_0.json" in sample_csv_text


def test_evaluation_manifest_exports_phase10_case_metadata_and_summaries(tmp_path: Path):
    manifest = build_manifest()
    summary = manifest["summary"]

    assert "families_by_id" in summary
    assert "subfamilies" in summary
    assert "gate_layers" in summary
    assert "support_levels" in summary
    assert "process_profiles" in summary
    assert "oracle_types" in summary
    assert "oracle_risks" in summary
    assert "demo_required_count" in summary
    assert summary["gate_layers"]["family_core"] >= 1
    assert summary["process_profiles"]["dp"] >= 1

    cases_by_id = {case["id"]: case for case in manifest["cases"]}
    binary = cases_by_id["binary_search"]
    assert binary["family_id"] == "binary_search"
    assert binary["subfamily_id"] == "closed_interval_search"
    assert binary["gate_layer"] == "family_core"
    assert binary["support_level"] == "strong"
    assert binary["process_profile"] == "binary_search"
    assert binary["oracle_type"] == "independent_reference"
    assert binary["oracle_risk"] == "none"
    assert binary["oracle_notes"]
    assert binary["demo_required"] is True

    two_sum = cases_by_id["two_sum"]
    assert two_sum["family_id"] == "hash_map"
    assert two_sum["support_level"] == "basic"
    assert two_sum["process_profile"] == "hash"
    assert two_sum["oracle_type"] == "bruteforce"
    assert two_sum["oracle_risk"] == "none"

    tarjan = cases_by_id["tarjan_scc"]
    assert tarjan["oracle_risk"] == "verifier_matches_solve"
    assert tarjan["oracle_reference"] == "tests.oracles.advanced_graph_oracle_examples"

    path = write_manifest(tmp_path)
    csv_text = (tmp_path / "evaluation_cases.csv").read_text(encoding="utf-8")
    for field in (
        "family_id",
        "subfamily_id",
        "gate_layer",
        "support_level",
        "process_profile",
        "oracle_type",
        "oracle_risk",
        "oracle_notes",
        "oracle_reference",
        "demo_required",
    ):
        assert field in csv_text
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["summary"]["gate_layers"] == summary["gate_layers"]


def test_evaluation_report_exports_phase10_metrics_and_core_tables(tmp_path: Path):
    manifest = build_manifest()
    dashboard = {
        "kind": "algolab_demo_dashboard",
        "total": 2,
        "passed": 2,
        "failed": 0,
        "demos": [
            {
                "id": "binary_search",
                "ok": True,
                "contract_gate_ready": True,
                "contract_test_pass_rate": "3/3",
                "interaction_coverage": "2/5",
                "actual_render_target": "teaching_2d",
            },
            {
                "id": "graph_bfs",
                "ok": True,
                "contract_gate_ready": True,
                "contract_test_pass_rate": "2/2",
                "interaction_coverage": "3/6",
                "actual_render_target": "spatial_3d",
            },
        ],
    }
    llm_report = {
        "kind": "llm_benchmark_report",
        "config": {
            "model": "demo-model",
            "max_rounds": 2,
            "llm": {"model": "demo-model", "base_url": "http://example.invalid/v1"},
        },
        "total": 2,
        "passed": 1,
        "failed": 1,
        "failure_summary": {"process_invariant": 1},
        "repair_failure_summary": {"schema_error": 1},
        "browser_smoke": [{"ok": True}, {"ok": False}],
        "results": [
            {
                "case_id": "binary_search",
                "family": "二分",
                "ok": True,
                "phase_timings": [
                    {"phase": "generate", "status": "ok"},
                    {"phase": "materialize_round_0", "status": "error"},
                    {"phase": "repair_round_0", "status": "ok"},
                    {"phase": "materialize_round_1", "status": "ok"},
                ],
            },
            {
                "case_id": "graph_bfs",
                "family": "BFS/DFS 基础图",
                "ok": False,
                "failure_type": "process_invariant",
                "phase_timings": [
                    {"phase": "generate", "status": "ok"},
                    {"phase": "materialize_round_0", "status": "error"},
                ],
            },
        ],
    }
    family_gate = {
        "schema_version": "family-release-gate-v1",
        "overall_ready": True,
        "summary": {
            "case_count": 47,
            "sample_count": 131,
            "answer_pass_rate": 1.0,
            "process_pass_rate": 1.0,
            "demo_readiness_pass_rate": 1.0,
            "process_fallback_cases": 1,
            "process_uncovered_cases": 5,
            "degraded_family_count": 6,
        },
    }
    metrics = compute_metrics(manifest=manifest, dashboard=dashboard, llm_report=llm_report)
    by_name = {metric["name"]: metric for metric in metrics}
    assert by_name["generation_success_rate"]["value"] == 1.0
    assert by_name["contract_pass_rate"]["value"] == 1.0
    assert by_name["correctness_gate_pass_rate"]["value"] == 0.5
    assert by_name["repair_success_rate"]["value"] == 1.0
    assert by_name["visual_smoke_pass_rate"]["value"] == 0.5
    assert by_name["interaction_coverage"]["value"] == round(5 / 11, 6)
    assert by_name["human_teaching_quality_score"]["status"] == "missing"
    comparisons = comparison_protocols()
    assert {item["baseline"] for item in comparisons} >= {
        "pure_llm_judge",
        "code2video_manim",
        "no_correctness_gate_renderer",
        "direct_html_baseline",
        "no_process_validator_ablation",
        "no_scenegraph_compiler_ablation",
    }

    manifest_path = tmp_path / "evaluation_manifest.json"
    dashboard_path = tmp_path / "dashboard.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    family_gate_path = tmp_path / "family_release_gate.json"
    human_path = tmp_path / "human.csv"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(llm_report, ensure_ascii=False), encoding="utf-8")
    family_gate_path.write_text(json.dumps(family_gate, ensure_ascii=False), encoding="utf-8")
    human_path.write_text("case_id,score\nbinary_search,4\ngraph_bfs,5\n", encoding="utf-8")

    report_path = build_evaluation_report(
        output_dir=tmp_path,
        manifest_path=manifest_path,
        dashboard_path=dashboard_path,
        llm_report_path=llm_path,
        human_ratings_path=human_path,
        family_gate_path=family_gate_path,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_metrics = {metric["name"]: metric for metric in report["metrics"]}
    assert report_metrics["human_teaching_quality_score"]["value"] == 4.5
    assert report["model_config"]["model"] == "demo-model"
    assert report["model_config"]["llm"]["base_url"] == "http://example.invalid/v1"
    assert report["repair_summary"]["max_rounds_configured"] == 2
    assert report["repair_summary"]["cases_with_repair"] == 1
    assert report["repair_summary"]["repair_rounds_attempted"] == 1
    assert report["repair_summary"]["repair_successes"] == 1
    assert report["family_release_gate"]["status"] == "ok"
    assert report["family_release_gate"]["sample_count"] == 131
    assert report["family_release_gate"]["process_uncovered_cases"] == 5
    family_by_name = {item["family"]: item for item in report["family_summary"]}
    assert family_by_name["二分"]["pass_rate"] == 1.0
    assert family_by_name["BFS/DFS 基础图"]["failure_types"] == {"process_invariant": 1}
    assert {item["baseline"] for item in report["comparisons"]} >= {
        "pure_llm_judge",
        "code2video_manim",
        "no_correctness_gate_renderer",
        "direct_html_baseline",
        "no_process_validator_ablation",
        "no_scenegraph_compiler_ablation",
    }
    assert (tmp_path / "evaluation_metrics.csv").exists()
    assert (tmp_path / "evaluation_comparisons.csv").exists()
    assert (tmp_path / "evaluation_core_cases.csv").exists()
    assert (tmp_path / "evaluation_family_summary.csv").exists()
    assert (tmp_path / "evaluation_report.md").exists()
    assert "generation_success_rate" in (tmp_path / "evaluation_metrics.csv").read_text(encoding="utf-8")
    assert "纯 LLM judge" in (tmp_path / "evaluation_comparisons.csv").read_text(encoding="utf-8")
    assert "process_invariant" in (tmp_path / "evaluation_family_summary.csv").read_text(encoding="utf-8")
    assert "## Family Summary" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")
    assert "## Family Release Gate" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")
    assert "## Comparisons" in (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")


def test_evaluation_report_summarizes_baseline_ablation_conditions(tmp_path: Path):
    manifest = build_manifest()
    llm_report = {
        "kind": "llm_benchmark_report",
        "config": {"model": "demo-model", "benchmark_condition": "algolab_full"},
        "results": [
            {
                "case_id": "two_sum",
                "family": "哈希 / 双指针",
                "ok": True,
                "condition": "algolab_full",
            },
            {
                "case_id": "binary_search",
                "family": "二分",
                "ok": False,
                "condition": "direct_html_baseline",
                "failure_type": "html_error",
            },
            {
                "case_id": "graph_bfs",
                "family": "BFS/DFS 基础图",
                "ok": False,
                "ablation": "no_process_validator",
                "error": "failure_type=process_invariant: BFS 层级错误未被过程校验拦截",
            },
            {
                "case_id": "unique_paths",
                "family": "DP 基础",
                "ok": False,
                "experiment_condition": "no_scenegraph_compiler",
                "errors": ["scene compiler disabled caused scene validator failure"],
            },
        ],
    }

    summary = condition_summary(llm_report)
    by_condition = {row["condition"]: row for row in summary}
    assert by_condition["algolab_full"]["pass_rate"] == 1.0
    assert by_condition["direct_html_baseline"]["kind"] == "baseline"
    assert by_condition["direct_html_baseline"]["failure_types"] == {"html_error": 1}
    assert by_condition["no_process_validator"]["kind"] == "ablation"
    assert by_condition["no_process_validator"]["failure_types"] == {"process_invariant": 1}
    assert by_condition["no_scenegraph_compiler"]["kind"] == "ablation"
    assert by_condition["no_scenegraph_compiler"]["failure_types"] == {"scene_error": 1}

    manifest_path = tmp_path / "evaluation_manifest.json"
    llm_path = tmp_path / "llm_benchmark_report.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    llm_path.write_text(json.dumps(llm_report, ensure_ascii=False), encoding="utf-8")
    report_path = build_evaluation_report(output_dir=tmp_path, manifest_path=manifest_path, llm_report_path=llm_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert {row["condition"] for row in report["condition_summary"]} >= {
        "algolab_full",
        "direct_html_baseline",
        "no_process_validator",
        "no_scenegraph_compiler",
    }
    assert report["failure_type_summary"] == {
        "html_error": 1,
        "process_invariant": 1,
        "scene_error": 1,
    }
    assert {item["baseline"] for item in report["comparisons"]} >= {
        "direct_html_baseline",
        "no_process_validator_ablation",
        "no_scenegraph_compiler_ablation",
    }
    assert "direct_html_baseline" in (tmp_path / "evaluation_condition_summary.csv").read_text(encoding="utf-8")
    md = (tmp_path / "evaluation_report.md").read_text(encoding="utf-8")
    assert "## Baseline And Ablation Summary" in md
    assert "no_scenegraph_compiler" in md


def test_reproducibility_package_records_environment_commands_samples_and_modes(tmp_path: Path):
    package = build_reproducibility_package()

    assert package["schema_version"] == "reproducibility-package-v1"
    assert package["environment"]["python"] == "/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
    assert package["model_config"]["secret_policy"]
    assert "ALGOLAB_LLM_MODEL" in package["model_config"]["env_vars"]
    assert package["commands"]["deterministic_quality_check"] == (
        "/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py"
    )
    assert package["commands"]["llm_benchmark"].startswith(
        "/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py"
    )

    modes = package["benchmark_modes"]
    assert modes["deterministic"]["calls_llm"] is False
    assert modes["deterministic"]["source"] == "tests/benchmark_cases.py"
    assert modes["llm"]["calls_llm"] is True
    assert modes["llm"]["source"] == "scripts/run_llm_benchmark.py"
    assert modes["deterministic"]["output_paths"] != modes["llm"]["output_paths"]

    samples = package["sample_inputs"]
    assert len(samples) >= build_manifest()["summary"]["sample_count"]
    first = samples[0]
    assert {"case_id", "sample_index", "input_data", "expected", "suite", "output_paths"} <= set(first)
    assert first["output_paths"].get("artifact_json")
    assert first["output_paths"].get("html")

    written = write_reproducibility_package(tmp_path)
    assert written.name == "reproducibility_package.json"
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == package
    readme = tmp_path / "README.md"
    commands = tmp_path / "commands.sh"
    assert readme.exists()
    assert commands.exists()
    readme_text = readme.read_text(encoding="utf-8")
    commands_text = commands.read_text(encoding="utf-8")
    for token in ("确定性质量检查", "LLM benchmark", "deterministic benchmark", "输出路径"):
        assert token in readme_text
    assert "scripts/run_quality_checks.py" in commands_text
    assert "scripts/run_llm_benchmark.py" in commands_text


def test_v1_release_gate_report_records_release_requirements(tmp_path: Path):
    report = build_v1_release_gate_report()

    assert report["schema_version"] == "v1-release-gate-v1"
    assert report["overall_ready"] is True
    assert report["commands"]["quality_checks"] == (
        "/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py"
    )
    deterministic = report["checks"]["deterministic_benchmark"]
    assert 80 <= deterministic["benchmark_sample_count"] <= 160
    assert deterministic["benchmark_sample_count"] == sum(len(case.samples) for case in benchmark_cases())
    assert deterministic["status"] == "pass"

    golden = report["checks"]["golden_browser_smoke"]
    assert golden["status"] == "pass"
    assert {"unique_paths", "graph_bfs", "binary_search", "daily_temperatures"} <= set(golden["required_cases"])
    assert golden["covered_by"] == "scripts/run_quality_checks.py -> tests.browser_smoke.run_all"

    debug = report["checks"]["debug_drawer_evidence"]
    assert debug["status"] == "pass"
    for selector in ("#debug-validation-json", "#debug-release", "#debug-state", "#debug-artifact"):
        assert selector in debug["required_selectors"]

    evaluation = report["checks"]["evaluation_failure_types"]
    assert evaluation["status"] == "pass"
    assert evaluation["synthetic_failure_type_summary"] == {"process_invariant": 1, "scene_error": 1}
    assert "output/evaluation/evaluation_failure_types.csv" in evaluation["output_paths"]

    docs = report["checks"]["pinned_python_docs"]
    assert docs["status"] == "pass"
    assert docs["python"] == "/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
    assert docs["disallowed_commands"] == []

    written = write_v1_release_gate_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    assert (tmp_path / "v1_release_gate.md").exists()
    assert "V1 Release Gate" in (tmp_path / "v1_release_gate.md").read_text(encoding="utf-8")


def test_family_capabilities_registry_covers_existing_benchmark_families(tmp_path: Path):
    from scripts.check_family_capabilities import (
        build_family_capabilities_report,
        load_family_capabilities,
        validate_family_capabilities,
        write_family_capabilities_report,
    )

    capabilities = load_family_capabilities()
    report = build_family_capabilities_report(capabilities)

    assert report["schema_version"] == "family-capabilities-report-v1"
    assert report["overall_ready"] is True
    assert report["benchmark_family_count"] == len({case.family for case in benchmark_cases()})
    assert report["registered_family_count"] >= report["benchmark_family_count"]
    assert report["missing_benchmark_families"] == []
    assert report["unknown_process_profiles"] == []

    raw_entries_by_label = {entry["label"]: entry for entry in capabilities["families"]}
    report_entries_by_label = {entry["label"]: entry for entry in report["families"]}
    for case in benchmark_cases():
        assert case.family in raw_entries_by_label, case.family
        raw_entry = raw_entries_by_label[case.family]
        entry = report_entries_by_label[case.family]
        assert raw_entry["process_profile"] == entry["process_profile"]
        assert entry["family_id"]
        assert entry["target_level"] in {"strong", "medium_plus", "medium", "basic", "planned"}
        assert entry["current_level"] in {"strong", "medium_plus", "medium", "basic", "planned"}
        assert entry["process_profile"] in report["known_process_profiles"]
        assert entry["process_status"] in {"strong", "fallback", "uncovered"}
        assert entry["core_subfamilies"]
        assert entry["visual_primitives"]
        assert entry["benchmark_target"]["min_cases"] >= 1
        if entry["process_status"] != "strong":
            assert entry["fallback_boundaries"]

    broken = dict(capabilities)
    broken["families"] = [entry for entry in capabilities["families"] if entry["label"] != benchmark_cases()[0].family]
    broken_report = validate_family_capabilities(broken, benchmark_cases())
    assert broken_report["overall_ready"] is False
    assert benchmark_cases()[0].family in broken_report["missing_benchmark_families"]

    written = write_family_capabilities_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    assert (tmp_path / "family_capabilities.md").exists()
    assert "Family Capabilities" in (tmp_path / "family_capabilities.md").read_text(encoding="utf-8")


def test_family_release_gate_reports_layered_family_readiness_and_strong_fallback_failures(tmp_path: Path):
    from scripts.check_family_capabilities import load_family_capabilities
    from scripts.check_family_release_gate import (
        build_family_release_gate_report,
        validate_family_release_gate,
        write_family_release_gate_report,
    )

    capabilities = load_family_capabilities()
    report = build_family_release_gate_report(capabilities)

    assert report["schema_version"] == "family-release-gate-v1"
    assert report["overall_ready"] is True
    assert report["v1_release_gate"]["schema_version"] == "v1-release-gate-v1"
    assert report["v1_release_gate"]["overall_ready"] is True
    assert report["summary"]["case_count"] == len(benchmark_cases())
    assert report["summary"]["sample_count"] == sum(len(case.samples) for case in benchmark_cases())

    rows_by_label = {row["label"]: row for row in report["families"]}
    assert rows_by_label["二分"]["current_level"] == "strong"
    assert rows_by_label["二分"]["answer"]["passed_samples"] == rows_by_label["二分"]["sample_count"]
    assert rows_by_label["二分"]["process"]["passed_samples"] == rows_by_label["二分"]["sample_count"]
    assert rows_by_label["二分"]["demo_readiness"]["ready_cases"] == rows_by_label["二分"]["case_count"]
    assert rows_by_label["二分"]["fallback"]["process_fallback_cases"] == 0
    assert rows_by_label["二分"]["fallback"]["process_uncovered_cases"] == 0

    sorting = rows_by_label["排序"]
    assert sorting["current_level"] == "basic"
    assert sorting["fallback"]["process_uncovered_cases"] == sorting["case_count"]
    assert sorting["status"] == "pass"
    assert sorting["warnings"]

    written = write_family_release_gate_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    md = (tmp_path / "family_release_gate.md").read_text(encoding="utf-8")
    assert "Family Release Gate" in md
    assert "process_uncovered" in md

    broken = dict(capabilities)
    broken["families"] = [dict(entry) for entry in capabilities["families"]]
    broken["families"][0]["process_profile"] = "uncovered"
    broken_report = validate_family_release_gate(broken, benchmark_cases())
    assert broken_report["overall_ready"] is False
    broken_row = next(row for row in broken_report["families"] if row["label"] == broken["families"][0]["label"])
    assert broken_row["current_level"] == "strong"
    assert broken_row["fallback"]["process_uncovered_cases"] == broken_row["case_count"]
    assert any("strong family" in error for error in broken_row["errors"])


def test_property_benchmark_generates_seeded_robustness_report(tmp_path: Path):
    from tests.property_cases import DEFAULT_PROPERTY_SEED, property_cases
    from scripts.run_property_benchmark import build_property_benchmark_report, write_property_benchmark_report

    cases = property_cases()
    subfamilies = {case.subfamily_id for case in cases}
    assert {
        "house_robber",
        "subset_sum",
        "lcs",
        "edit_distance",
        "knapsack_01",
        "bfs_layers",
        "dfs_connected",
        "topological_sort",
        "dijkstra_positive",
        "kmp",
        "z_algorithm",
        "manacher",
        "insertion_sort",
        "merge_sort",
        "quickselect",
        "union_find_connectivity",
        "range_sum_update",
    } <= subfamilies

    report_a = build_property_benchmark_report(seed=DEFAULT_PROPERTY_SEED, sample_count=3)
    report_b = build_property_benchmark_report(seed=DEFAULT_PROPERTY_SEED, sample_count=3)
    assert report_a == report_b
    assert report_a["schema_version"] == "property-benchmark-v1"
    assert report_a["release_gate_included"] is False
    assert report_a["summary"]["seed"] == DEFAULT_PROPERTY_SEED
    assert report_a["summary"]["total"] == len(cases) * 3
    assert report_a["summary"]["failed"] == 0
    assert report_a["summary"]["passed"] == report_a["summary"]["total"]
    assert set(report_a["summary"]["families"]) >= {
        "dynamic_programming",
        "basic_graph",
        "string_matching",
        "sorting",
        "union_find",
        "range_structure",
    }
    for family_id, row in report_a["summary"]["family_robustness"].items():
        assert row["total"] > 0, family_id
        assert row["passed"] == row["total"], family_id
        assert row["failed"] == 0, family_id
        assert row["pass_rate"] == 1.0, family_id

    for result in report_a["results"]:
        assert {
            "family",
            "family_id",
            "subfamily",
            "subfamily_id",
            "input",
            "expected",
            "actual",
            "ok",
            "failure_type",
        } <= set(result), result

    json_path = write_property_benchmark_report(tmp_path, seed=DEFAULT_PROPERTY_SEED, sample_count=2)
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded == build_property_benchmark_report(seed=DEFAULT_PROPERTY_SEED, sample_count=2)
    md = (tmp_path / "property_benchmark_report.md").read_text(encoding="utf-8")
    assert "Property Benchmark" in md
    assert "not included in V1 release gate" in md


def test_boundary_case_registry_reports_family_core_coverage_and_strong_upgrade_gate(tmp_path: Path):
    from scripts.check_boundary_cases import (
        BOUNDARY_CATEGORIES,
        build_boundary_case_report,
        load_boundary_cases,
        validate_boundary_cases,
        write_boundary_case_report,
    )

    registry = load_boundary_cases()
    report = build_boundary_case_report(registry)
    family_core_cases = [case for case in benchmark_cases() if case.gate_layer == "family_core"]
    strong_core_cases = [case for case in family_core_cases if case.support_level == "strong"]

    assert registry["schema_version"] == "boundary-cases-v1"
    assert set(BOUNDARY_CATEGORIES) == {"empty", "single", "duplicate", "zero_or_negative", "extreme", "no_solution", "multiple_solutions"}
    assert report["schema_version"] == "boundary-case-report-v1"
    assert report["summary"]["family_core_case_count"] == len(family_core_cases)
    assert report["summary"]["strong_family_core_case_count"] == len(strong_core_cases)
    assert report["summary"]["missing_family_core_cases"] == []
    assert report["summary"]["strong_upgrade_blocked_cases"] == []
    assert report["summary"]["overall_ready"] is True
    assert report["summary"]["strong_upgrade_ready"] is True

    rows_by_case = {row["case_id"]: row for row in report["cases"]}
    for case in family_core_cases:
        row = rows_by_case[case.id]
        assert row["gate_layer"] == "family_core", case.id
        assert row["covered_categories"] or row["not_applicable_categories"], case.id
        assert set(row["covered_categories"]) | set(row["not_applicable_categories"]) == set(BOUNDARY_CATEGORIES), case.id
        assert row["missing_categories"] == [], case.id
        assert row["status"] == "pass", case.id
        for item in row["not_applicable"]:
            assert item["reason"], (case.id, item)

    for family_id, row in report["families"].items():
        assert row["case_count"] > 0, family_id
        assert row["boundary_counts"], family_id
        assert row["missing_case_count"] == 0, family_id

    written = write_boundary_case_report(tmp_path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == report
    md = (tmp_path / "boundary_cases.md").read_text(encoding="utf-8")
    assert "Boundary Cases" in md
    assert "strong_upgrade_ready" in md

    broken = dict(registry)
    broken["cases"] = [dict(item) for item in registry["cases"]]
    broken["cases"][0] = dict(broken["cases"][0])
    broken["cases"][0]["coverage"] = []
    broken["cases"][0]["not_applicable"] = []
    broken_report = validate_boundary_cases(broken, benchmark_cases())
    assert broken_report["summary"]["overall_ready"] is False
    if rows_by_case[broken["cases"][0]["case_id"]]["support_level"] == "strong":
        assert broken_report["summary"]["strong_upgrade_ready"] is False
        assert broken_report["summary"]["strong_upgrade_blocked_cases"]
    assert broken_report["summary"]["missing_boundary_cases"]


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


def run_all():
    test_phase12_dp_trace_contract_accepts_representative_subfamilies()
    test_phase12_dp_trace_contract_rejects_missing_deps_init_answer_and_key_updates()
    test_phase12_graph_trace_contract_accepts_representative_submodes()
    test_phase12_graph_trace_contract_rejects_submode_process_errors()
    test_phase12_family_trace_contract_accepts_string_tree_backtracking_and_structures()
    test_phase12_family_trace_contract_rejects_missing_process_evidence()
    test_phase13_array_pointer_validator_rejects_process_errors_and_tracks_samples()
    test_phase13_dp_validator_expands_family_core_samples_and_rejects_digit_dp_errors()
    test_benchmark_cases_are_multi_input_release_ready()
    test_process_validator_rejects_missing_key_step_coverage_for_small_traces()
    test_process_validator_rejects_bad_string_algorithm_tables()
    test_benchmark_cases_expose_phase10_metadata()
    test_benchmark_cases_expose_phase11_oracle_metadata_and_independent_examples()
    test_convex_hull_trace_exposes_scan_phases_and_pop_steps()
    test_phase7_string_algorithms_have_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_tree_recursion_aggregates()
    test_phase7_tree_recursion_group_has_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_range_structure_tables()
    test_phase7_range_structures_have_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_math_bit_invariants()
    test_phase7_math_bit_group_has_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_advanced_graph_invariants()
    test_phase7_advanced_graph_group_has_benchmarks_visual_state_and_examples()
    test_contract_tests_block_bad_solve()
    test_llm_benchmark_request_uses_problem_and_expected()
    test_llm_benchmark_sample_selection_and_failure_classification(Path(tempfile.gettempdir()))
    test_benchmark_report_summarizes_process_registry_failure_types(Path(tempfile.gettempdir()))
    test_llm_benchmark_phase_timing_helpers()
    test_llm_json_and_spec_normalization_helpers()
    test_existing_benchmark_html_report_helper(Path(tempfile.gettempdir()))
    test_benchmark_html_checker_resolves_required_phase8_cases(Path(tempfile.gettempdir()))
    test_demo_dashboard_selection_defaults_to_curated_showcase()
    test_runtime_capabilities_prompt_context_is_json()

    with tempfile.TemporaryDirectory() as d:
        test_llm_client_reads_local_api_settings_without_committing_key(Path(d))
        test_benchmark_aggregate_artifact(Path(d))
        test_demo_dashboard_writes_bundle_and_index(Path(d))
        test_demo_dashboard_groups_by_family_and_gate_layer(Path(d))
        test_evaluation_manifest_covers_phase10_datasets(Path(d))
        test_evaluation_manifest_exports_phase10_case_metadata_and_summaries(Path(d))
        test_evaluation_report_exports_phase10_metrics_and_core_tables(Path(d))
        test_evaluation_report_summarizes_baseline_ablation_conditions(Path(d))
        test_reproducibility_package_records_environment_commands_samples_and_modes(Path(d))
        test_v1_release_gate_report_records_release_requirements(Path(d))
        test_family_capabilities_registry_covers_existing_benchmark_families(Path(d))
        test_family_release_gate_reports_layered_family_readiness_and_strong_fallback_failures(Path(d))
        test_property_benchmark_generates_seeded_robustness_report(Path(d))
        test_boundary_case_registry_reports_family_core_coverage_and_strong_upgrade_gate(Path(d))
    test_creative_renderer_contains_theme_controls_and_stage()


if __name__ == "__main__":
    run_all()
    print("benchmark_regression: PASS")
