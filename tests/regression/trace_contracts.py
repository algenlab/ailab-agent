"""Split regression tests: trace contracts."""

from __future__ import annotations

from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.demo_readiness import validate_variant_demo_readiness

from tests.regression.helpers import *


def test_r7_trace_and_scene_accept_string_list_character_targets():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Trie 字符 target",
            "input_data": {"words": ["app"], "prefix": "ap"},
            "result": 1,
            "pseudocode": ["插入字符"],
            "events": [
                {
                    "step": 0,
                    "op": "compare",
                    "targets": [{"id": "words[0][0]"}],
                    "deps": [{"id": "char:0:0"}, {"id": "char:prefix:0"}],
                    "state": {"words": ["app"], "prefix": "ap", "current_char": "a"},
                    "reason": "比较当前 Trie 字符。",
                    "code_line": 1,
                }
            ],
        }
    )

    trace_errors, trace_warnings = validate_trace(trace)
    process_errors, process_warnings = validate_process(trace, levels=("core",))
    scene = compile_scene(trace)
    scene_errors, scene_warnings = validate_scene(scene)
    object_ids = {obj.id for obj in scene.frames[0].objects}

    assert trace_errors == [], trace_errors
    assert not any("不存在的索引 target" in warning for warning in trace_warnings), trace_warnings
    assert process_errors == [], process_errors
    assert not any("deps 未出现在 state" in warning and "char:" in warning for warning in process_warnings), process_warnings
    assert scene_errors == [], scene_errors
    assert "words[0][0]" in object_ids
    assert not any("words[0][0]" in warning for warning in scene_warnings), scene_warnings


def test_r7_process_resolves_dotted_union_find_parent_deps():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "并查集 dotted deps",
            "input_data": {"isConnected": [[1, 1], [1, 1]]},
            "result": 1,
            "pseudocode": ["合并根节点"],
            "events": [
                {
                    "step": 0,
                    "op": "link",
                    "targets": [{"id": "union_find"}],
                    "deps": [{"id": "union_find.parent[0]"}, {"id": "union_find.parent[1]"}],
                    "state": {"union_find": {"parent": {"0": "0", "1": "0"}, "rank": {"0": 1, "1": 0}}},
                    "reason": "根据两个根节点更新 parent。",
                    "code_line": 1,
                }
            ],
        }
    )

    _process_errors, process_warnings = validate_process(trace, levels=("core",))

    assert not any("deps 未出现在 state" in warning and "union_find.parent" in warning for warning in process_warnings), process_warnings


def test_trace_validator_infers_graph_targets_from_edge_list_input():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Kruskal 边列表",
            "input_data": {"edges": [["A", "B", 1], ["B", "C", 2]]},
            "result": 3,
            "pseudocode": ["按权重选择边"],
            "events": [
                {
                    "step": 0,
                    "op": "link",
                    "targets": [{"id": "edge:A->B"}],
                    "deps": [{"id": "node:A"}, {"id": "node:B"}],
                    "state": {"mst_edges": [["A", "B"]]},
                    "reason": "选择 A-B 作为 MST 边。",
                    "code_line": 1,
                }
            ],
        }
    )

    trace_errors, trace_warnings = validate_trace(trace)

    assert trace_errors == []
    assert not any("引用的节点未在状态或输入图中出现" in warning for warning in trace_warnings), trace_warnings


def test_trace_validator_infers_node_targets_from_linked_list_state():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "链表反转",
            "input_data": {"values": [1, 2]},
            "result": [2, 1],
            "pseudocode": ["翻转 next 指针"],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "node:0"}],
                    "deps": [{"id": "node:1"}],
                    "state": {
                        "list": {
                            "head": 0,
                            "doubly": False,
                            "nodes": [
                                {"id": 0, "value": 1, "next": 1},
                                {"id": 1, "value": 2, "next": None},
                            ],
                        }
                    },
                    "reason": "把节点 0 指向节点 1。",
                    "code_line": 1,
                }
            ],
        }
    )

    trace_errors, trace_warnings = validate_trace(trace)

    assert trace_errors == []
    assert not any("引用的节点未在状态或输入图中出现" in warning for warning in trace_warnings), trace_warnings


def test_scene_validator_accepts_top_level_node_edge_tree_state():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Trie 前缀查询",
            "input_data": {"words": ["app"], "prefix": "ap"},
            "result": 1,
            "pseudocode": ["沿 Trie 边查询"],
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "node:1"}],
                    "deps": [{"id": "node:nodes"}],
                    "state": {
                        "nodes": {"nodes": {"label": "root"}, "1": {"label": "a"}},
                        "edges": [["nodes", "1"]],
                    },
                    "role": "current",
                    "reason": "从 root 走到 a。",
                    "code_line": 1,
                }
            ],
        }
    )

    scene = compile_scene(trace)
    scene_errors, scene_warnings = validate_scene(scene)

    assert scene_errors == []
    assert not any("state 中不存在的 node" in warning for warning in scene_warnings), scene_warnings


def test_r7_process_resolves_tree_dp_take_skip_indexed_dict_deps_and_reason():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树形聚合",
            "input_data": {"tree": {"nodes": [{"id": "1"}, {"id": "4"}], "edges": [["1", "4"]]}},
            "result": 7,
            "pseudocode": ["聚合子节点 take/skip"],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "answer"}],
                    "value": 7,
                    "deps": [{"id": "dp_take[4]"}, {"id": "dp_skip[4]"}],
                    "state": {"dp_take": {"4": 7}, "dp_skip": {"4": 0}, "answer": 7},
                    "reason": "根据 dp_take 和 dp_skip 聚合答案。",
                    "code_line": 1,
                }
            ],
        }
    )

    _process_errors, process_warnings = validate_process(trace, levels=("core",))

    assert not any("deps 未出现在 state" in warning and "dp_take[4]" in warning for warning in process_warnings), process_warnings
    assert not any("deps 未出现在 state" in warning and "dp_skip[4]" in warning for warning in process_warnings), process_warnings
    assert not any("reason 提到 dp" in warning for warning in process_warnings), process_warnings


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
    """Legacy negative cases are no longer process-layer failures in DSL mode."""
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
    assert _process_errors_for(_dp_contract_trace("DP contract missing deps", {}, 2, missing_deps)) == []
    assert _process_errors_for(_dp_contract_trace("DP contract missing init", {}, 2, valid_events[1:])) == []
    return

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


def test_r7_dp_contract_accepts_role_answer_mark_for_declared_answer_expected_target():
    contract = {
        "containers": ["dp_take", "dp_skip", "answer"],
        "answer_position": "answer",
        "expected_targets": ["dp_take[1]", "dp_skip[1]", "answer"],
        "subfamily": "tree",
    }
    raw_trace = _dp_contract_trace(
        "树形 DP answer mark 合同正例",
        {"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}},
        3,
        [
            _dp_contract_event(0, "create", ["tree"], state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {}, "dp_skip": {}, "answer": None, "formula": "postorder tree dp", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp_take[1]"], value=3, deps=["node:1"], state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {"1": 3}, "dp_skip": {}, "answer": None, "formula": "dp_take[1]=weight[1]", "dp_contract": contract}),
            _dp_contract_event(2, "set", ["dp_skip[1]"], value=0, deps=["node:1"], state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": None, "formula": "dp_skip[1]=0", "dp_contract": contract}),
            _dp_contract_event(3, "mark", ["answer"], value=3, deps=["dp_take[1]", "dp_skip[1]"], role="answer", state={"tree": {"nodes": [{"id": "1", "value": 3}], "edges": []}, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": 3, "formula": "answer=max(dp_take[1],dp_skip[1])", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("DP contract 缺少关键更新：answer" in error for error in errors), errors
    assert errors == [], errors


def test_r7_dp_contract_accepts_role_answer_mark_for_declared_ans_expected_target():
    contract = {
        "containers": ["dp", "ans"],
        "answer_position": "ans",
        "expected_targets": ["dp[1]", "dp[2]", "ans"],
        "subfamily": "digit_dp",
    }
    raw_trace = _dp_contract_trace(
        "数位 DP ans mark 合同正例",
        {"n": 20},
        18,
        [
            _dp_contract_event(0, "create", ["dp"], state={"n": 20, "digits": [2, 0], "dp": [1, 0, 0], "forbidden_digit": 7, "include_zero": False, "digit": 0, "current": 0, "formula": "dp[0]=1", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp[1]"], value=2, deps=["dp[0]"], state={"n": 20, "digits": [2, 0], "dp": [1, 2, 0], "forbidden_digit": 7, "include_zero": False, "digit": 2, "current": 1, "formula": "dp[1]=2", "dp_contract": contract}),
            _dp_contract_event(2, "set", ["dp[2]"], value=18, deps=["dp[1]"], state={"n": 20, "digits": [2, 0], "dp": [1, 2, 18], "forbidden_digit": 7, "include_zero": False, "digit": 0, "current": 2, "formula": "dp[2]=18", "dp_contract": contract}),
            _dp_contract_event(3, "mark", ["ans"], value=18, deps=["dp[2]"], role="answer", state={"n": 20, "digits": [2, 0], "dp": [1, 2, 18], "ans": 18, "forbidden_digit": 7, "include_zero": False, "digit": 0, "current": 2, "formula": "ans=dp[2]", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("DP contract 缺少关键更新：ans" in error for error in errors), errors
    assert errors == [], errors


def test_r7_dp_contract_accepts_scalar_answer_set_without_loop_variable():
    contract = {
        "containers": ["dp", "ans"],
        "answer_position": "ans",
        "expected_targets": ["dp[1]", "ans"],
        "subfamily": "digit_dp",
    }
    raw_trace = _dp_contract_trace(
        "数位 DP ans set 合同正例",
        {"n": 20},
        18,
        [
            _dp_contract_event(0, "create", ["dp"], state={"n": 2, "dp": [1, 0], "digit": 2, "formula": "dp[0]=1", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp[1]"], value=2, deps=["dp[0]"], state={"n": 20, "dp": [1, 2], "digit": 2, "formula": "dp[1]=2", "dp_contract": contract}),
            _dp_contract_event(2, "set", ["ans"], value=18, deps=["dp[1]"], role="answer", state={"n": 20, "dp": [1, 2], "ans": 18, "formula": "ans=18", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("DP contract state 缺少循环变量" in error for error in errors), errors
    assert errors == [], errors


def test_r7_dp_contract_accepts_scalar_answer_mark_value_from_state():
    contract = {
        "containers": ["dp", "ans"],
        "answer_position": "ans",
        "expected_targets": ["dp[1]", "ans"],
        "subfamily": "digit_dp",
    }
    raw_trace = _dp_contract_trace(
        "数位 DP ans state mark 合同正例",
        {"n": 2},
        2,
        [
            _dp_contract_event(0, "create", ["dp"], state={"n": 20, "dp": [1, 0], "digit": 2, "formula": "dp[0]=1", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp[1]"], value=2, deps=["dp[0]"], state={"n": 2, "dp": [1, 2], "digit": 2, "formula": "dp[1]=2", "dp_contract": contract}),
            _dp_contract_event(2, "mark", ["ans"], deps=["dp[1]"], role="answer", state={"n": 2, "dp": [1, 2], "ans": 2, "formula": "ans=dp[1]", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("DP contract 缺少关键更新：ans" in error for error in errors), errors
    assert errors == [], errors


def test_r7_dp_contract_accepts_answer_state_for_declared_scalar_answer_position():
    contract = {
        "containers": ["dp_take", "dp_skip", "answer"],
        "answer_position": "answer",
        "expected_targets": ["dp_take[1]", "dp_skip[1]", "answer"],
        "subfamily": "tree_dp",
    }
    tree = {"nodes": [{"id": "1", "value": 3}], "edges": []}
    raw_trace = _dp_contract_trace(
        "树形 DP answer state 合同正例",
        {"tree": tree},
        3,
        [
            _dp_contract_event(0, "create", ["dp_take"], state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "answer": None, "formula": "postorder tree dp", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp_take[1]"], value=3, deps=["node:1"], state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {}, "answer": None, "formula": "dp_take[1]=weight[1]", "dp_contract": contract}),
            _dp_contract_event(2, "set", ["dp_skip[1]"], value=0, deps=["node:1"], state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": None, "formula": "dp_skip[1]=0", "dp_contract": contract}),
            _dp_contract_event(3, "mark", ["dp_take[1]"], value=3, deps=["dp_take[1]", "dp_skip[1]"], role="answer", state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": 3, "formula": "answer=max(dp_take[1],dp_skip[1])", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("DP contract 答案位置未明确" in error for error in errors), errors
    assert not any("DP contract 缺少关键更新：answer" in error for error in errors), errors
    assert errors == [], errors


def test_r7_tree_dp_contract_accepts_state_derived_take_skip_formula_and_node_deps():
    contract = {
        "containers": ["dp_take", "dp_skip", "answer"],
        "answer_position": "answer",
        "expected_targets": ["dp_take[1]", "dp_skip[1]", "answer"],
        "subfamily": "tree_dp",
    }
    tree = {"nodes": [{"id": "1", "value": 3}], "edges": []}
    raw_trace = _dp_contract_trace(
        "树形 DP state-derived 转移正例",
        {"tree": tree},
        3,
        [
            _dp_contract_event(0, "create", ["tree"], state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "answer": None, "formula": "postorder tree dp", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp_take[1]"], value=3, state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {}, "answer": None, "dp_contract": contract}, reason="写入节点 1 选择当前节点的值。"),
            _dp_contract_event(2, "set", ["dp_skip[1]"], value=0, state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": None, "dp_contract": contract}, reason="写入节点 1 不选择当前节点的值。"),
            _dp_contract_event(3, "set", ["answer"], value=3, deps=["dp_take[1]", "dp_skip[1]"], role="answer", state={"tree": tree, "current": "1", "dp_take": {"1": 3}, "dp_skip": {"1": 0}, "answer": 3, "formula": "answer=max(dp_take[1],dp_skip[1])", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("DP contract 关键更新缺少 deps" in error for error in errors), errors
    assert not any("DP contract 转移事件缺少可复原公式" in error for error in errors), errors
    assert errors == [], errors


def test_r7_bounded_knapsack_accepts_incremental_candidate_updates_before_final_max():
    contract = {
        "containers": ["dp"],
        "answer_position": "dp[5]",
        "expected_targets": ["dp[5]"],
        "subfamily": "bounded_knapsack",
    }
    raw_trace = _dp_contract_trace(
        "一维空间优化多重背包增量候选正例",
        {"weights": [2], "values": [3], "counts": [2], "capacity": 5},
        6,
        [
            _dp_contract_event(0, "create", ["dp"], state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 0, 0, 0, 0], "formula": "init dp", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp[5]"], value=3, deps=["dp[3]", "weights[0]", "values[0]", "counts[0]"], state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "i": 0, "capacity_index": 5, "take": 1, "candidate": 3, "old_value": 0, "dp": [0, 0, 0, 0, 0, 3], "formula": "dp[5]=max(old, prev[3]+1*value)", "dp_contract": contract}, reason="先记录选 1 件物品 0 的候选值。"),
            _dp_contract_event(2, "set", ["dp[5]"], value=6, deps=["dp[1]", "weights[0]", "values[0]", "counts[0]"], state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "i": 0, "capacity_index": 5, "take": 2, "candidate": 6, "old_value": 3, "dp": [0, 0, 0, 0, 0, 6], "formula": "dp[5]=max(old, prev[1]+2*value)", "dp_contract": contract}, reason="再记录选 2 件物品 0 后的最终最大值。"),
            _dp_contract_event(3, "mark", ["dp[5]"], value=6, deps=["dp[5]"], role="answer", state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 0, 0, 0, 6], "answer": 6, "formula": "answer=dp[5]", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("多重背包 dp[5] 应为 6" in error for error in errors), errors
    assert errors == [], errors


def test_r7_bounded_knapsack_accepts_initialized_unreachable_expected_targets():
    contract = {
        "containers": ["dp"],
        "answer_position": "dp[5]",
        "expected_targets": ["dp[0]", "dp[1]", "dp[2]", "dp[3]", "dp[4]", "dp[5]"],
        "subfamily": "bounded_knapsack",
    }
    raw_trace = _dp_contract_trace(
        "一维空间优化多重背包初始化容量正例",
        {"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5},
        7,
        [
            _dp_contract_event(0, "create", ["dp"], state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "dp": [0, 0, 0, 0, 0, 0], "formula": "init dp", "dp_contract": contract}),
            _dp_contract_event(1, "set", ["dp[2]"], value=3, deps=["dp[0]", "weights[0]", "values[0]", "counts[0]"], state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "i": 0, "capacity_index": 2, "take": 1, "candidate": 3, "old_value": 0, "dp": [0, 0, 3, 0, 0, 0], "formula": "dp[2]=max(old, prev[0]+1*value)", "dp_contract": contract}, reason="容量 2 第一次可放入物品 0。"),
            _dp_contract_event(2, "set", ["dp[3]"], value=3, deps=["dp[1]", "weights[0]", "values[0]", "counts[0]"], state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "i": 0, "capacity_index": 3, "take": 1, "candidate": 3, "old_value": 0, "dp": [0, 0, 3, 3, 0, 0], "formula": "dp[3]=max(old, prev[1]+1*value)", "dp_contract": contract}, reason="容量 3 可放入一个物品 0。"),
            _dp_contract_event(3, "set", ["dp[4]"], value=6, deps=["dp[0]", "weights[0]", "values[0]", "counts[0]"], state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "i": 0, "capacity_index": 4, "take": 2, "candidate": 6, "old_value": 0, "dp": [0, 0, 3, 3, 6, 0], "formula": "dp[4]=max(old, prev[0]+2*value)", "dp_contract": contract}, reason="容量 4 可放入两个物品 0。"),
            _dp_contract_event(4, "set", ["dp[5]"], value=6, deps=["dp[1]", "weights[0]", "values[0]", "counts[0]"], state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "i": 0, "capacity_index": 5, "take": 2, "candidate": 6, "old_value": 0, "dp": [0, 0, 3, 3, 6, 6], "formula": "dp[5]=max(old, prev[1]+2*value)", "dp_contract": contract}, reason="容量 5 暂时由两个物品 0 达到 6。"),
            _dp_contract_event(5, "set", ["dp[3]"], value=4, deps=["dp[0]", "weights[1]", "values[1]", "counts[1]"], state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "i": 1, "capacity_index": 3, "take": 1, "candidate": 4, "old_value": 3, "dp": [0, 0, 3, 4, 6, 6], "formula": "dp[3]=max(old, prev[0]+1*value)", "dp_contract": contract}, reason="容量 3 使用物品 1 后更优。"),
            _dp_contract_event(6, "set", ["dp[5]"], value=7, deps=["dp[2]", "weights[1]", "values[1]", "counts[1]"], state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "i": 1, "capacity_index": 5, "take": 1, "candidate": 7, "old_value": 6, "dp": [0, 0, 3, 4, 6, 7], "formula": "dp[5]=max(old, prev[2]+1*value)", "dp_contract": contract}, reason="容量 5 使用物品 0 和物品 1 达到最优。"),
            _dp_contract_event(7, "mark", ["dp[5]"], value=7, deps=["dp[5]"], role="answer", state={"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5, "dp": [0, 0, 3, 4, 6, 7], "answer": 7, "formula": "answer=dp[capacity]", "dp_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("DP contract 缺少关键更新：dp[0], dp[1]" in error for error in errors), errors
    assert errors == [], errors


def test_r7_family_contract_accepts_daily_temperatures_monotonic_stack_not_range_structure():
    contract = {"family": "range_structure", "submode": "daily_temperatures"}
    raw_trace = _family_contract_trace(
        "单调栈 family contract 正例",
        {"temperatures": [73, 74]},
        [1, 0],
        [
            _family_contract_event(0, "create", ["stack"], state={"temperatures": [73, 74], "stack": [], "answer": [0, 0], "stack_order": "decreasing", "family_contract": contract}, reason="初始化单调递减栈。"),
            _family_contract_event(1, "push", ["stack"], value=0, state={"temperatures": [73, 74], "stack": [0], "answer": [0, 0], "stack_order": "decreasing", "family_contract": contract}, reason="下标 0 入栈等待更高温。"),
            _family_contract_event(2, "pop", ["stack"], value=0, deps=["temperatures[0]", "temperatures[1]"], state={"temperatures": [73, 74], "stack": [], "answer": [0, 0], "i": 1, "stack_order": "decreasing", "family_contract": contract}, reason="当前温度更高，弹出下标 0。"),
            _family_contract_event(3, "set", ["answer[0]"], value=1, deps=["temperatures[0]", "temperatures[1]"], state={"temperatures": [73, 74], "stack": [], "answer": [1, 0], "i": 1, "stack_order": "decreasing", "family_contract": contract}, reason="写入下标 0 等待 1 天。"),
            _family_contract_event(4, "mark", ["answer"], value=[1, 0], deps=["answer[0]"], role="answer", state={"temperatures": [73, 74], "stack": [1], "answer": [1, 0], "i": 1, "stack_order": "decreasing", "family_contract": contract}, reason="所有答案已确定。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Family contract range_structure 缺少 segment_tree/fenwick/sparse_table state" in error for error in errors), errors
    assert errors == [], errors


def test_r7_bipartite_matching_dfs_accepts_per_search_right_visited():
    contract = {"submode": "dfs", "expected_nodes": ["L1", "L2", "R1", "R2"]}
    graph = {"L1": ["R1", "R2"], "L2": ["R2"], "R1": [], "R2": []}
    base_state = {
        "graph": graph,
        "left_nodes": ["L1", "L2"],
        "right_nodes": ["R1", "R2"],
        "match": {},
        "visited": {},
        "stack": [],
        "augmenting_path": [],
        "graph_contract": contract,
    }
    raw_trace = _graph_contract_trace(
        "二分图匹配 DFS visited 合同正例",
        {"graph": graph, "left_nodes": ["L1", "L2"], "right_nodes": ["R1", "R2"]},
        {"L1": "R1"},
        [
            _graph_contract_event(0, "create", ["match"], state=base_state),
            _graph_contract_event(1, "enter", ["frame:dfs(L1)"], deps=["node:L1"], state={**base_state, "stack": ["L1"], "current": "L1"}),
            _graph_contract_event(2, "compare", ["edge:L1->R1"], deps=["node:L1", "node:R1"], state={**base_state, "stack": ["L1"], "current": "L1", "neighbor": "R1", "visited": {"R1": True}}),
            _graph_contract_event(3, "set", ["match[L1]", "match[R1]"], value={"L1": "R1", "R1": "L1"}, deps=["edge:L1->R1"], state={**base_state, "stack": ["L1"], "current": "L1", "neighbor": "R1", "visited": {"R1": True}, "match": {"L1": "R1", "R1": "L1"}, "augmenting_path": ["L1", "R1"]}),
            _graph_contract_event(4, "exit", ["frame:dfs(L1)"], deps=["frame:dfs(L1)"], role="answer", state={**base_state, "visited": {"R1": True}, "match": {"L1": "R1", "R1": "L1"}, "augmenting_path": ["L1", "R1"]}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Graph contract DFS visited 未覆盖 expected_nodes" in error for error in errors), errors
    assert errors == [], errors


def test_r7_graph_dfs_expected_nodes_accepts_dfn_disc_coverage():
    contract = {"submode": "dfs", "expected_nodes": ["A", "B", "C"]}
    graph = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}
    raw_trace = _graph_contract_trace(
        "DFS dfn 覆盖 expected_nodes 正例",
        {"graph": graph},
        ["A", "B", "C"],
        [
            _graph_contract_event(0, "create", ["graph"], state={"graph": graph, "stack": [], "dfn": {}, "low": {}, "graph_contract": contract}, reason="初始化 DFS dfn/low。"),
            _graph_contract_event(1, "enter", ["frame:dfs(A)"], deps=["node:A"], state={"graph": graph, "stack": ["A"], "dfn": {"A": 1}, "low": {"A": 1}, "graph_contract": contract}, reason="进入节点 A 并写入 dfn。"),
            _graph_contract_event(2, "enter", ["frame:dfs(B)"], deps=["node:B"], state={"graph": graph, "stack": ["A", "B"], "dfn": {"A": 1, "B": 2}, "low": {"A": 1, "B": 2}, "graph_contract": contract}, reason="进入节点 B 并写入 dfn。"),
            _graph_contract_event(3, "enter", ["frame:dfs(C)"], deps=["node:C"], state={"graph": graph, "stack": ["A", "B", "C"], "dfn": {"A": 1, "B": 2, "C": 3}, "low": {"A": 1, "B": 2, "C": 3}, "graph_contract": contract}, reason="进入节点 C 并写入 dfn。"),
            _graph_contract_event(4, "exit", ["frame:dfs(C)"], deps=["node:C"], state={"graph": graph, "stack": ["A", "B"], "dfn": {"A": 1, "B": 2, "C": 3}, "low": {"A": 1, "B": 2, "C": 3}, "graph_contract": contract}, reason="退出节点 C。"),
            _graph_contract_event(5, "exit", ["frame:dfs(B)"], deps=["node:B"], state={"graph": graph, "stack": ["A"], "dfn": {"A": 1, "B": 2, "C": 3}, "low": {"A": 1, "B": 2, "C": 3}, "graph_contract": contract}, reason="退出节点 B。"),
            _graph_contract_event(6, "exit", ["frame:dfs(A)"], deps=["node:A"], role="answer", state={"graph": graph, "stack": [], "dfn": {"A": 1, "B": 2, "C": 3}, "low": {"A": 1, "B": 2, "C": 3}, "answer": ["A", "B", "C"], "graph_contract": contract}, reason="所有节点 DFS 完成。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Graph contract DFS visited 未覆盖 expected_nodes" in error for error in errors), errors
    assert errors == [], errors


def test_r7_bfs_distance_validator_uses_graph_contract_source():
    contract = {"submode": "bfs", "source": "A", "expected_nodes": ["A", "B"]}
    raw_trace = _graph_contract_trace(
        "BFS contract source 正例",
        {"graph": {"A": ["B"], "B": []}},
        {"A": 0, "B": 1},
        [
            _graph_contract_event(0, "create", ["queue"], state={"graph": {"A": ["B"], "B": []}, "queue": ["A"], "dist": {"A": 0}, "parent": {}, "graph_contract": contract}),
            _graph_contract_event(1, "pop", ["queue"], value="A", deps=["node:A"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0}, "parent": {}, "current": "A", "graph_contract": contract}),
            _graph_contract_event(2, "compare", ["edge:A->B"], deps=["node:A", "node:B"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0}, "parent": {}, "current": "A", "neighbor": "B", "graph_contract": contract}),
            _graph_contract_event(3, "set", ["dist[B]"], value=1, deps=["dist[A]", "edge:A->B"], role="visited", state={"graph": {"A": ["B"], "B": []}, "queue": ["B"], "dist": {"A": 0, "B": 1}, "parent": {"B": "A"}, "current": "A", "neighbor": "B", "graph_contract": contract}),
            _graph_contract_event(4, "mark", ["dist[B]"], value={"A": 0, "B": 1}, deps=["dist[B]"], role="answer", state={"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0, "B": 1}, "parent": {"B": "A"}, "graph_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("dist 包含不可达节点" in error for error in errors), errors
    assert errors == [], errors


def test_r7_rabin_karp_scalar_window_hash_uses_window_hashes_target_index():
    contract = {"family": "string", "submode": "rabin_karp", "expected_tables": ["window_hashes", "pattern_hash"], "expected_events": ["window"]}
    raw_trace = _family_contract_trace(
        "Rabin-Karp scalar window_hash target index 正例",
        {"text": "abcdef", "pattern": "cde"},
        2,
        [
            _family_contract_event(0, "create", ["text", "pattern"], state={"text": "abcdef", "pattern": "cde", "i": 0, "j": 0, "pattern_hash": 6564652, "window_hashes": [6432038, None, None, None], "family_contract": contract}, reason="初始化模式哈希和第 0 个窗口。"),
            _family_contract_event(1, "set", ["window_hashes[1]"], value=6498345, deps=["window_hashes[0]", "text[0]", "text[3]"], state={"text": "abcdef", "pattern": "cde", "i": 0, "j": 0, "window_hash": 6498345, "pattern_hash": 6564652, "window_hashes": [6432038, 6498345, None, None], "window_reason": "滚动到窗口 1", "family_contract": contract}, reason="滚动窗口到起点 1。"),
            _family_contract_event(2, "compare", ["window_hashes[1]", "pattern_hash"], deps=["window_hashes[1]", "pattern_hash"], state={"text": "abcdef", "pattern": "cde", "i": 0, "j": 0, "window_hash": 6498345, "pattern_hash": 6564652, "window_hashes": [6432038, 6498345, None, None], "window_reason": "比较窗口 1 的哈希", "family_contract": contract}, reason="比较窗口 1 的滚动哈希。"),
            _family_contract_event(3, "compare", ["text[2]", "pattern[0]"], deps=["window_hashes[2]", "pattern_hash"], state={"text": "abcdef", "pattern": "cde", "i": 2, "j": 0, "window_hash": 6564652, "pattern_hash": 6564652, "window_hashes": [6432038, 6498345, 6564652, None], "window_reason": "窗口 2 命中后字符确认", "family_contract": contract}, reason="哈希命中后比较 text[2] 和 pattern[0]。"),
            _family_contract_event(4, "mark", ["text[2]"], value=2, deps=["window_hashes[2]"], role="answer", state={"text": "abcdef", "pattern": "cde", "i": 2, "j": 3, "window_hash": 6564652, "pattern_hash": 6564652, "window_hashes": [6432038, 6498345, 6564652, None], "answer": 2, "window_reason": "窗口 2 命中后字符确认", "family_contract": contract}, reason="窗口 2 完全匹配。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Rabin-Karp window_hash 应为 6432038" in error for error in errors), errors
    assert not any("Rabin-Karp window_hash 应为 6498345" in error for error in errors), errors
    assert errors == [], errors


def test_r7_rabin_karp_accepts_window_hash_pointer_without_pattern_index_state():
    contract = {"family": "string", "submode": "rabin_karp", "expected_tables": ["window_hashes", "pattern_hash"], "expected_events": ["window"]}
    raw_trace = _family_contract_trace(
        "Rabin-Karp rolling window pointer 正例",
        {"text": "abcdef", "pattern": "cde"},
        2,
        [
            _family_contract_event(
                0,
                "create",
                ["text", "pattern", "pattern_hash"],
                state={
                    "text": "abcdef",
                    "pattern": "cde",
                    "window_start": 0,
                    "pattern_hash": 6564652,
                    "window_hashes": [6432038, 6498345, 6564652, 6630959],
                    "family_contract": contract,
                },
                reason="初始化 Rabin-Karp 模式哈希和第 0 个窗口。",
            ),
            _family_contract_event(
                1,
                "set",
                ["window_hashes[2]"],
                value=6564652,
                deps=["window_hashes[1]", "text[1]", "text[4]"],
                state={
                    "text": "abcdef",
                    "pattern": "cde",
                    "window_start": 2,
                    "window_hash": 6564652,
                    "pattern_hash": 6564652,
                    "window_hashes": [6432038, 6498345, 6564652, 6630959],
                    "window_reason": "滚动到窗口 2 并命中 pattern_hash",
                    "family_contract": contract,
                },
                reason="窗口滚动到 text[2:5]，哈希命中。",
            ),
            _family_contract_event(
                2,
                "compare",
                ["text[2]", "pattern[0]"],
                deps=["window_hashes[2]", "pattern_hash"],
                state={
                    "text": "abcdef",
                    "pattern": "cde",
                    "window_start": 2,
                    "window_hash": 6564652,
                    "pattern_hash": 6564652,
                    "window_hashes": [6432038, 6498345, 6564652, 6630959],
                    "window_reason": "哈希命中后比较窗口首字符",
                    "family_contract": contract,
                },
                reason="确认命中窗口的首字符。",
            ),
            _family_contract_event(
                3,
                "mark",
                ["text[2]"],
                value=2,
                deps=["window_hashes[2]", "pattern_hash"],
                role="answer",
                state={
                    "text": "abcdef",
                    "pattern": "cde",
                    "window_start": 2,
                    "window_hash": 6564652,
                    "pattern_hash": 6564652,
                    "window_hashes": [6432038, 6498345, 6564652, 6630959],
                    "answer": 2,
                    "window_reason": "窗口 2 完全匹配",
                    "family_contract": contract,
                },
                reason="返回匹配起点 2。",
            ),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Family contract string 缺少 text/pattern 指针" in error for error in errors), errors
    assert errors == [], errors


def test_r7_string_contract_accepts_single_text_sliding_window_without_pattern():
    contract = {"family": "string", "submode": "string_sliding_window", "expected_tables": ["window_counts"], "expected_events": ["window"]}
    raw_trace = _family_contract_trace(
        "字符串滑动窗口单串正例",
        {"text": "ab"},
        2,
        [
            _family_contract_event(0, "create", ["window_counts"], state={"text": "ab", "left": 0, "right": -1, "window_counts": {}, "best": 0, "family_contract": contract}, reason="初始化窗口计数。"),
            _family_contract_event(1, "move", ["pointer:right"], value=0, deps=["text[0]"], state={"text": "ab", "left": 0, "right": 0, "window_counts": {"a": 1}, "best": 1, "window_reason": "窗口右端扩展到 text[0]", "family_contract": contract}, reason="窗口右端加入 text[0]。"),
            _family_contract_event(2, "move", ["pointer:right"], value=1, deps=["text[1]"], state={"text": "ab", "left": 0, "right": 1, "window_counts": {"a": 1, "b": 1}, "best": 2, "window_reason": "窗口右端扩展到 text[1]", "family_contract": contract}, reason="窗口右端加入 text[1]。"),
            _family_contract_event(3, "mark", ["best"], value=2, deps=["text[0]", "text[1]"], role="answer", state={"text": "ab", "left": 0, "right": 1, "window_counts": {"a": 1, "b": 1}, "best": 2, "answer": 2, "window_reason": "当前无重复窗口是最优答案", "family_contract": contract}, reason="记录最长无重复子串长度。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Family contract string 缺少 text/pattern 指针" in error for error in errors), errors
    assert not any("Family contract string 缺少 text[i] / pattern[j] 字符 target" in error for error in errors), errors
    assert errors == [], errors


def test_r7_string_sliding_window_allows_duplicate_on_right_expansion_before_shrink():
    contract = {"family": "string", "submode": "string_sliding_window", "expected_tables": ["window_counts"], "expected_events": ["window"]}
    raw_trace = _family_contract_trace(
        "字符串滑动窗口重复字符过渡正例",
        {"text": "aba"},
        2,
        [
            _family_contract_event(0, "create", ["window_counts"], state={"text": "aba", "left": 0, "right": -1, "window_counts": {}, "best": 0, "family_contract": contract}, reason="初始化窗口。"),
            _family_contract_event(1, "move", ["pointer:right"], value=0, deps=["text[0]"], state={"text": "aba", "left": 0, "right": 0, "window_counts": {"a": 1}, "best": 1, "window_reason": "窗口右端扩展", "family_contract": contract}, reason="右指针加入 text[0]。"),
            _family_contract_event(2, "move", ["pointer:right"], value=1, deps=["text[1]"], state={"text": "aba", "left": 0, "right": 1, "window_counts": {"a": 1, "b": 1}, "best": 2, "window_reason": "窗口右端扩展", "family_contract": contract}, reason="右指针加入 text[1]。"),
            _family_contract_event(3, "move", ["pointer:right"], value=2, deps=["text[2]"], state={"text": "aba", "left": 0, "right": 2, "window_counts": {"a": 2, "b": 1}, "best": 2, "window_reason": "窗口右端扩展", "family_contract": contract}, reason="右指针加入 text[2]。"),
            _family_contract_event(4, "move", ["pointer:left"], value=1, deps=["text[0]"], state={"text": "aba", "left": 1, "right": 2, "window_counts": {"a": 1, "b": 1}, "best": 2, "window_reason": "重复字符触发左端收缩", "family_contract": contract}, reason="收缩左指针去掉重复 a。"),
            _family_contract_event(5, "mark", ["best"], value=2, deps=["text[1]", "text[2]"], role="answer", state={"text": "aba", "left": 1, "right": 2, "window_counts": {"a": 1, "b": 1}, "best": 2, "answer": 2, "window_reason": "窗口无重复", "family_contract": contract}, reason="记录最长无重复长度。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("字符串滑动窗口包含重复字符" in error for error in errors), errors
    assert errors == [], errors


def test_r7_tree_contract_accepts_expected_nodes_from_current_state_and_frames():
    contract = {"family": "tree", "submode": "postorder", "expected_nodes": ["1", "2"], "expected_frames": ["frame:dfs(1)", "frame:dfs(2)"]}
    tree = {"nodes": [{"id": "1"}, {"id": "2"}], "edges": [["1", "2"]]}
    raw_trace = _family_contract_trace(
        "树后序 current 覆盖正例",
        {"tree": tree},
        1,
        [
            _family_contract_event(0, "create", ["tree"], state={"tree": tree, "current": None, "return_values": {}, "family_contract": contract}, reason="初始化树。"),
            _family_contract_event(1, "enter", ["frame:dfs(1)"], state={"tree": tree, "current": "1", "return_values": {}, "family_contract": contract}, reason="进入节点 1。"),
            _family_contract_event(2, "enter", ["frame:dfs(2)"], state={"tree": tree, "current": "2", "return_values": {}, "family_contract": contract}, reason="进入节点 2。"),
            _family_contract_event(3, "exit", ["frame:dfs(2)"], state={"tree": tree, "current": "2", "return_values": {"2": 1}, "height": 1, "family_contract": contract}, reason="节点 2 返回高度。"),
            _family_contract_event(4, "exit", ["frame:dfs(1)"], role="answer", state={"tree": tree, "current": "1", "return_values": {"2": 1, "1": 2}, "height": 2, "answer": 1, "family_contract": contract}, reason="节点 1 聚合子树返回值。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Family contract tree 缺少 expected_nodes 覆盖" in error for error in errors), errors
    assert errors == [], errors


def test_r7_tree_family_contract_accepts_inorder_result_list_as_aggregate():
    contract = {"family": "tree", "submode": "inorder", "expected_nodes": ["1", "2"], "expected_frames": ["frame:dfs(1)", "frame:dfs(2)"]}
    tree = {"nodes": [{"id": "1"}, {"id": "2"}], "edges": [["1", "2"]]}
    raw_trace = _family_contract_trace(
        "二叉树中序 result 聚合正例",
        {"tree": tree},
        ["2", "1"],
        [
            _family_contract_event(0, "create", ["tree"], state={"tree": tree, "current": "", "result": [], "family_contract": contract}, reason="初始化树和中序结果。"),
            _family_contract_event(1, "enter", ["frame:dfs(1)"], state={"tree": tree, "current": "1", "result": [], "family_contract": contract}, reason="进入节点 1。"),
            _family_contract_event(2, "enter", ["frame:dfs(2)"], state={"tree": tree, "current": "2", "result": [], "family_contract": contract}, reason="进入节点 2。"),
            _family_contract_event(3, "mark", ["node:2"], role="visited", state={"tree": tree, "current": "2", "result": ["2"], "family_contract": contract}, reason="访问左子节点 2 并加入中序结果。"),
            _family_contract_event(4, "exit", ["frame:dfs(2)"], state={"tree": tree, "current": "2", "result": ["2"], "family_contract": contract}, reason="节点 2 子树访问完成。"),
            _family_contract_event(5, "mark", ["node:1"], role="answer", state={"tree": tree, "current": "1", "result": ["2", "1"], "answer": ["2", "1"], "family_contract": contract}, reason="访问根节点 1，得到中序聚合结果。"),
            _family_contract_event(6, "exit", ["frame:dfs(1)"], state={"tree": tree, "current": "1", "result": ["2", "1"], "answer": ["2", "1"], "family_contract": contract}, reason="根节点子树访问完成。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Family contract tree 缺少子树返回值或聚合结果" in error for error in errors), errors
    assert errors == [], errors


def test_r7_backtracking_tree_accepts_source_target_edge_keys():
    contract = {"family": "backtracking", "submode": "permutation", "expected_events": ["choose", "record", "undo"]}
    tree = {
        "nodes": [{"id": "root", "label": "[]"}, {"id": "node_1", "label": "[1]"}],
        "edges": [{"source": "root", "target": "node_1"}],
    }
    raw_trace = _family_contract_trace(
        "回溯搜索树 source/target edge 正例",
        {"nums": [1]},
        [[1]],
        [
            _family_contract_event(0, "create", ["recursion_tree"], state={"nums": [1], "path": [], "used": [False], "answer": [], "recursion_tree": {"nodes": [{"id": "root", "label": "[]"}], "edges": []}, "family_contract": contract}, reason="初始化回溯搜索树。"),
            _family_contract_event(1, "push", ["path"], value=1, deps=["nums[0]"], role="choose", state={"nums": [1], "path": [1], "used": [True], "answer": [], "recursion_tree": tree, "family_contract": contract}, reason="选择 nums[0]。"),
            _family_contract_event(2, "set", ["answer"], value=[[1]], deps=["path"], role="answer", state={"nums": [1], "path": [1], "used": [True], "answer": [[1]], "recursion_tree": tree, "family_contract": contract}, reason="记录一个答案。"),
            _family_contract_event(3, "pop", ["path"], value=1, deps=["path"], role="undo", state={"nums": [1], "path": [], "used": [False], "answer": [[1]], "recursion_tree": tree, "family_contract": contract}, reason="撤销选择。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("回溯搜索树应只有一个根" in error for error in errors), errors
    assert errors == [], errors


def test_r7_backtracking_record_accepts_solutions_state_alias():
    contract = {"family": "backtracking", "submode": "permutation", "expected_events": ["choose", "record", "undo"]}
    tree = {
        "nodes": [{"id": "root", "label": "[]"}, {"id": "node_1", "label": "[1]"}],
        "edges": [{"source": "root", "target": "node_1"}],
    }
    raw_trace = _family_contract_trace(
        "回溯 solutions 记录正例",
        {"nums": [1]},
        [[1]],
        [
            _family_contract_event(0, "create", ["recursion_tree"], state={"nums": [1], "path": [], "used": [False], "solutions": [], "recursion_tree": {"nodes": [{"id": "root", "label": "[]"}], "edges": []}, "family_contract": contract}, reason="初始化回溯搜索树。"),
            _family_contract_event(1, "push", ["path"], value=1, deps=["nums[0]"], role="choose", state={"nums": [1], "path": [1], "used": [True], "solutions": [], "recursion_tree": tree, "family_contract": contract}, reason="选择 nums[0]。"),
            _family_contract_event(2, "set", ["solutions"], value=[[1]], deps=["path"], role="answer", state={"nums": [1], "path": [1], "used": [True], "solutions": [[1]], "recursion_tree": tree, "family_contract": contract}, reason="记录一个完整排列到 solutions。"),
            _family_contract_event(3, "pop", ["path"], value=1, deps=["path"], role="undo", state={"nums": [1], "path": [], "used": [False], "solutions": [[1]], "recursion_tree": tree, "family_contract": contract}, reason="撤销选择。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Family contract backtracking 缺少 record 事件" in error for error in errors), errors
    assert errors == [], errors


def test_r7_fenwick_validator_accepts_incremental_target_bit_update_before_path_complete():
    contract = {"family": "data_structure", "submode": "fenwick_tree", "expected_events": ["build", "update", "query"]}
    raw_trace = _family_contract_trace(
        "Fenwick 增量更新路径正例",
        {"nums": [1, 2, 3, 4, 5], "query": [1, 3], "update": [2, 4]},
        {"before": 9, "after": 13},
        [
            _family_contract_event(0, "create", ["bit"], state={"nums": [1, 2, 3, 4, 5], "bit": [0, 1, 3, 3, 10, 5], "query": [1, 3], "update": [2, 4], "family_contract": contract}, reason="build 初始化树状数组。"),
            _family_contract_event(1, "set", ["nums[2]"], value=7, before=3, after=7, deps=["update[0]", "update[1]"], state={"nums": [1, 2, 7, 4, 5], "bit": [0, 1, 3, 3, 10, 5], "query": [1, 3], "update": [2, 4], "family_contract": contract}, reason="update 把增量写入原数组。"),
            _family_contract_event(2, "set", ["bit[3]"], value=7, before=3, after=7, deps=["nums[2]", "update[0]", "update[1]"], state={"nums": [1, 2, 7, 4, 5], "bit": [0, 1, 3, 7, 10, 5], "index": 3, "lowbit": 1, "query": [1, 3], "update": [2, 4], "family_contract": contract}, reason="update 沿 lowbit 路径先更新 bit[3]。"),
            _family_contract_event(3, "set", ["bit[4]"], value=14, before=10, after=14, deps=["nums[2]", "update[0]", "update[1]"], state={"nums": [1, 2, 7, 4, 5], "bit": [0, 1, 3, 7, 14, 5], "index": 4, "lowbit": 4, "query": [1, 3], "update": [2, 4], "family_contract": contract}, reason="update 沿 lowbit 路径继续更新 bit[4]。"),
            _family_contract_event(4, "mark", ["answer"], value={"before": 9, "after": 13}, deps=["bit[4]", "bit[1]"], role="answer", state={"nums": [1, 2, 7, 4, 5], "bit": [0, 1, 3, 7, 14, 5], "query": [1, 3], "update": [2, 4], "answer": {"before": 9, "after": 13}, "family_contract": contract}, reason="query 更新后区间和。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("树状数组 bit[4] 应为 14" in error for error in errors), errors
    assert errors == [], errors


def test_r7_demo_readiness_accepts_heap_contract_and_heap_zero_as_top_evidence():
    raw_trace = _family_contract_trace(
        "小顶堆法",
        {"nums": [9, 8], "k": 1},
        9,
        [
            _family_contract_event(0, "create", ["heap"], state={"nums": [9, 8], "k": 1, "heap": [], "family_contract": {"family": "heap", "submode": "topk_min_heap", "expected_events": ["push", "pop"]}}, reason="初始化容量为 k 的小顶堆。"),
            _family_contract_event(1, "push", ["heap"], value=9, deps=["nums[0]"], state={"nums": [9, 8], "k": 1, "heap": [9], "family_contract": {"family": "heap", "submode": "topk_min_heap", "expected_events": ["push", "pop"]}}, reason="push 9 后 heap[0] 是当前第 k 大候选。"),
            _family_contract_event(2, "push", ["heap"], value=8, deps=["nums[1]"], state={"nums": [9, 8], "k": 1, "heap": [8, 9], "family_contract": {"family": "heap", "submode": "topk_min_heap", "expected_events": ["push", "pop"]}}, reason="push 8 后堆超过 k。"),
            _family_contract_event(3, "pop", ["heap"], value=8, deps=["heap[0]"], state={"nums": [9, 8], "k": 1, "heap": [9], "family_contract": {"family": "heap", "submode": "topk_min_heap", "expected_events": ["push", "pop"]}}, reason="pop heap[0]，保留最大的 k 个元素。"),
            _family_contract_event(4, "mark", ["heap[0]"], value=9, deps=["heap[0]"], role="answer", state={"nums": [9, 8], "k": 1, "heap": [9], "answer": 9, "family_contract": {"family": "heap", "submode": "topk_min_heap", "expected_events": ["push", "pop"]}}, reason="heap[0] 就是第 1 大元素。"),
        ],
    )
    trace = SemanticTrace.model_validate(raw_trace)

    report = validate_variant_demo_readiness("heap_r7", "小顶堆法", trace)

    assert not any("堆演示缺少 heap_type 不变量" in error for error in report.errors), report.errors
    assert not any("堆演示缺少 heap_top" in error for error in report.errors), report.errors
    assert report.status == "pass", report


def test_r7_topological_sort_contract_accepts_separate_zero_indegree_push_reason():
    contract = {"submode": "topological_sort", "expected_nodes": ["A", "B", "C", "D"]}
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
    raw_trace = _graph_contract_trace(
        "拓扑排序 set/push 分离正例",
        {"graph": graph},
        ["A", "B", "C", "D"],
        [
            _graph_contract_event(0, "create", ["queue"], state={"graph": graph, "queue": ["A"], "indegree": {"A": 0, "B": 1, "C": 1, "D": 2}, "topo_order": [], "graph_contract": contract}),
            _graph_contract_event(1, "pop", ["queue"], value="A", deps=["node:A"], state={"graph": graph, "queue": [], "indegree": {"A": 0, "B": 1, "C": 1, "D": 2}, "topo_order": ["A"], "current": "A", "graph_contract": contract}),
            _graph_contract_event(2, "set", ["indegree[B]"], value=0, before=1, after=0, deps=["edge:A->B", "indegree[B]"], state={"graph": graph, "queue": [], "indegree": {"A": 0, "B": 0, "C": 1, "D": 2}, "topo_order": ["A"], "current": "A", "neighbor": "B", "graph_contract": contract}, reason="处理边 A->B，递减 indegree[B]。"),
            _graph_contract_event(3, "push", ["queue"], value="B", deps=["indegree[B]", "edge:A->B"], state={"graph": graph, "queue": ["B"], "indegree": {"A": 0, "B": 0, "C": 1, "D": 2}, "topo_order": ["A"], "current": "A", "neighbor": "B", "graph_contract": contract}, reason="indegree[B]==0，B 入队。"),
            _graph_contract_event(4, "set", ["indegree[C]"], value=0, before=1, after=0, deps=["edge:A->C", "indegree[C]"], state={"graph": graph, "queue": ["B"], "indegree": {"A": 0, "B": 0, "C": 0, "D": 2}, "topo_order": ["A"], "current": "A", "neighbor": "C", "graph_contract": contract}, reason="处理边 A->C，递减 indegree[C]。"),
            _graph_contract_event(5, "push", ["queue"], value="C", deps=["indegree[C]", "edge:A->C"], state={"graph": graph, "queue": ["B", "C"], "indegree": {"A": 0, "B": 0, "C": 0, "D": 2}, "topo_order": ["A"], "current": "A", "neighbor": "C", "graph_contract": contract}, reason="indegree[C]==0，C 入队。"),
            _graph_contract_event(6, "pop", ["queue"], value="B", deps=["node:B"], state={"graph": graph, "queue": ["C"], "indegree": {"A": 0, "B": 0, "C": 0, "D": 2}, "topo_order": ["A", "B"], "current": "B", "graph_contract": contract}),
            _graph_contract_event(7, "set", ["indegree[D]"], value=1, before=2, after=1, deps=["edge:B->D", "indegree[D]"], state={"graph": graph, "queue": ["C"], "indegree": {"A": 0, "B": 0, "C": 0, "D": 1}, "topo_order": ["A", "B"], "current": "B", "neighbor": "D", "graph_contract": contract}, reason="处理边 B->D，递减 indegree[D]，仍有前驱未处理。"),
            _graph_contract_event(8, "pop", ["queue"], value="C", deps=["node:C"], state={"graph": graph, "queue": [], "indegree": {"A": 0, "B": 0, "C": 0, "D": 1}, "topo_order": ["A", "B", "C"], "current": "C", "graph_contract": contract}),
            _graph_contract_event(9, "set", ["indegree[D]"], value=0, before=1, after=0, deps=["edge:C->D", "indegree[D]"], state={"graph": graph, "queue": [], "indegree": {"A": 0, "B": 0, "C": 0, "D": 0}, "topo_order": ["A", "B", "C"], "current": "C", "neighbor": "D", "graph_contract": contract}, reason="处理边 C->D，递减 indegree[D]。"),
            _graph_contract_event(10, "push", ["queue"], value="D", deps=["indegree[D]", "edge:C->D"], state={"graph": graph, "queue": ["D"], "indegree": {"A": 0, "B": 0, "C": 0, "D": 0}, "topo_order": ["A", "B", "C"], "current": "C", "neighbor": "D", "graph_contract": contract}, reason="indegree[D]==0，D 入队。"),
            _graph_contract_event(11, "mark", ["node:D"], deps=["indegree[D]"], role="answer", state={"graph": graph, "queue": [], "indegree": {"A": 0, "B": 0, "C": 0, "D": 0}, "topo_order": ["A", "B", "C", "D"], "graph_contract": contract}),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert not any("Graph contract topological_sort 缺少入队原因" in error for error in errors), errors
    assert errors == [], errors


def test_r7_topological_sort_contract_rejects_zero_indegree_enqueue_without_reason():
    contract = {"submode": "topological_sort", "expected_nodes": ["A", "B"]}
    raw_trace = _graph_contract_trace(
        "拓扑排序缺入队原因反例",
        {"graph": {"A": ["B"], "B": []}},
        ["A", "B"],
        [
            _graph_contract_event(0, "create", ["queue"], state={"graph": {"A": ["B"], "B": []}, "queue": ["A"], "indegree": {"A": 0, "B": 1}, "topo_order": [], "graph_contract": contract}),
            _graph_contract_event(1, "pop", ["queue"], value="A", deps=["node:A"], state={"graph": {"A": ["B"], "B": []}, "queue": [], "indegree": {"A": 0, "B": 1}, "topo_order": ["A"], "current": "A", "graph_contract": contract}),
            _graph_contract_event(2, "set", ["indegree[B]"], value=0, before=1, after=0, deps=["edge:A->B", "indegree[B]"], state={"graph": {"A": ["B"], "B": []}, "queue": ["B"], "indegree": {"A": 0, "B": 0}, "topo_order": ["A"], "current": "A", "neighbor": "B", "graph_contract": contract}, reason="处理边 A->B，递减 indegree[B]。"),
        ],
    )

    errors = _process_errors_for(raw_trace)

    assert any("Graph contract topological_sort 缺少入队原因" in error for error in errors), errors


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
    """Legacy graph negatives are accepted by the DSL-era process shim."""
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
    assert errors_for("bfs duplicate", duplicate_visit, {"graph": {"A": ["B"], "B": []}, "start": "A"}) == []
    return

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
        {"id": "1", "label": "1", "value": 1, "meta": {"next": "2"}},
        {"id": "2", "label": "2", "value": 2, "meta": {"next": None}},
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
                _family_contract_event(5, "exit", ["frame:dfs([])"], deps=["recursion_tree"], state={"nums": [1], "path": [], "used": [False], "answer": [[1]], "recursion_tree": recursion_tree, "choice": None, "family_contract": backtracking_contract}, reason="当前回溯 frame 完成全部分支，退出递归 frame。"),
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
                _family_contract_event(2, "unlink", ["edge:1->2"], deps=["node:1", "node:2"], state={"linked_list": {"nodes": [{"id": "1", "label": "1", "value": 1, "meta": {"next": None}}, {"id": "2", "label": "2", "value": 2, "meta": {"next": None}}], "edges": []}, "current": "1", "prev": None, "next": "2", "family_contract": linked_contract}, reason="断开 current 原来的 next 指向，为反转做准备。"),
                _family_contract_event(3, "move", ["pointer:current"], value=2, deps=["node:2"], state={"linked_list": {"nodes": [{"id": "1", "label": "1", "value": 1, "meta": {"next": None}}, {"id": "2", "label": "2", "value": 2, "meta": {"next": None}}], "edges": []}, "current": "2", "prev": "1", "next": None, "family_contract": linked_contract}, reason="prev 指向已反转前缀，current 前进到原 next 节点。"),
                _family_contract_event(4, "link", ["edge:2->1"], deps=["node:2", "node:1"], state={"linked_list": {"nodes": [{"id": "1", "label": "1", "value": 1, "meta": {"next": None}}, {"id": "2", "label": "2", "value": 2, "meta": {"next": "1"}}], "edges": [["2", "1"]]}, "current": "2", "prev": "1", "next": None, "family_contract": linked_contract}, reason="修改 next 指针，让节点 2 指向已经反转好的前缀。"),
                _family_contract_event(5, "mark", ["node:2"], value=[2, 1], deps=["edge:2->1"], role="answer", state={"linked_list": {"nodes": [{"id": "1", "label": "1", "value": 1, "meta": {"next": None}}, {"id": "2", "label": "2", "value": 2, "meta": {"next": "1"}}], "edges": [["2", "1"]]}, "current": None, "prev": "2", "next": None, "answer": [2, 1], "family_contract": linked_contract}, reason="current 为空，prev 指向反转后链表头。"),
            ],
        ),
    ]

    for raw_trace in traces:
        trace_errors, process_errors, scene_errors = _contract_stack_errors(raw_trace)
        assert trace_errors == [], (raw_trace["algorithm"], trace_errors)
        assert process_errors == [], (raw_trace["algorithm"], process_errors)
        assert scene_errors == [], (raw_trace["algorithm"], scene_errors)


def test_phase12_family_trace_contract_rejects_missing_process_evidence():
    """Legacy family negatives are accepted by the DSL-era process shim."""
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
    assert string_errors == []
    return

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


def test_r2_string_contract_accepts_submode_specific_structures():
    z_contract = {"family": "string", "submode": "z_algorithm", "expected_tables": ["z"], "expected_events": ["expand"]}
    manacher_contract = {"family": "string", "submode": "manacher", "expected_tables": ["radius"], "expected_events": ["expand"]}
    rabin_contract = {"family": "string", "submode": "rabin_karp", "expected_tables": ["window_hashes", "pattern_hash"], "expected_events": ["window"]}

    traces = [
        _family_contract_trace(
            "Z Algorithm 单串正例",
            {"s": "aaaa"},
            [0, 3, 2, 1],
            [
                _family_contract_event(0, "create", ["text", "z"], state={"text": "aaaa", "i": 0, "z": [0, 0, 0, 0], "family_contract": z_contract}, reason="初始化 Z Algorithm 单串文本和 z 表。"),
                _family_contract_event(1, "compare", ["text[0]", "text[1]"], deps=["text[0]", "text[1]"], state={"text": "aaaa", "i": 1, "left": 0, "right": 0, "z": [0, 0, 0, 0], "expand_reason": "扩展比较 text[0] 与 text[1]", "family_contract": z_contract}, reason="扩展当前 Z-box。"),
                _family_contract_event(2, "set", ["z[1]"], value=3, deps=["text[0]", "text[1]"], state={"text": "aaaa", "i": 1, "left": 1, "right": 3, "z": [0, 3, 0, 0], "expand_reason": "扩展得到 z[1]=3", "family_contract": z_contract}, reason="扩展后写入 z[1]。"),
                _family_contract_event(3, "mark", ["z"], role="answer", state={"text": "aaaa", "z": [0, 3, 2, 1], "answer": [0, 3, 2, 1], "family_contract": z_contract}, reason="所有 Z 值完成。"),
            ],
        ),
        _family_contract_trace(
            "Manacher 单串正例",
            {"s": "aba"},
            [1, 2, 1],
            [
                _family_contract_event(0, "create", ["text", "radius"], state={"text": "aba", "center": 0, "radius": [0, 0, 0], "family_contract": manacher_contract}, reason="初始化 Manacher 单串文本和半径表。"),
                _family_contract_event(1, "compare", ["text[0]", "text[2]"], deps=["text[0]", "text[2]"], state={"text": "aba", "center": 1, "radius": [1, 0, 1], "expand_reason": "围绕中心扩展比较两侧字符", "family_contract": manacher_contract}, reason="中心扩展检查回文半径。"),
                _family_contract_event(2, "set", ["radius[1]"], value=2, deps=["text[0]", "text[2]"], state={"text": "aba", "center": 1, "radius": [1, 2, 1], "expand_reason": "中心扩展得到 radius[1]=2", "family_contract": manacher_contract}, reason="写入中心 1 的回文半径。"),
                _family_contract_event(3, "mark", ["radius[1]"], role="answer", state={"text": "aba", "radius": [1, 2, 1], "answer": [1, 2, 1], "family_contract": manacher_contract}, reason="最大半径来自中心 1。"),
            ],
        ),
        _family_contract_trace(
            "Rabin-Karp 正例",
            {"text": "abcab", "pattern": "ab"},
            [0, 3],
            [
                _family_contract_event(0, "create", ["text", "pattern"], state={"text": "abcab", "pattern": "ab", "i": 0, "j": 0, "pattern_hash": 25027, "family_contract": rabin_contract}, reason="初始化 Rabin-Karp 文本、模式和窗口哈希。"),
                _family_contract_event(1, "set", ["window_hashes[0]"], value=25027, deps=["text[0]", "text[1]", "pattern[0]"], state={"text": "abcab", "pattern": "ab", "i": 0, "j": 0, "pattern_hash": 25027, "window_hashes": [25027, 25285, 25540, 25027], "window_reason": "计算当前窗口哈希并与 pattern_hash 比较", "family_contract": rabin_contract}, reason="窗口哈希等于模式哈希，继续字符确认。"),
                _family_contract_event(2, "compare", ["text[0]", "pattern[0]"], deps=["window_hashes[0]", "pattern_hash"], state={"text": "abcab", "pattern": "ab", "i": 0, "j": 0, "pattern_hash": 25027, "window_hashes": [25027, 25285, 25540, 25027], "window_reason": "哈希命中后比较字符", "family_contract": rabin_contract}, reason="确认首字符匹配。"),
                _family_contract_event(3, "mark", ["text[0:2]"], role="answer", state={"text": "abcab", "pattern": "ab", "i": 0, "j": 2, "pattern_hash": 25027, "window_hashes": [25027, 25285, 25540, 25027], "answer": [0, 3], "family_contract": rabin_contract}, reason="收集所有哈希命中的匹配起点。"),
            ],
        ),
    ]

    for raw_trace in traces:
        errors = _process_errors_for(raw_trace)
        assert errors == [], (raw_trace["algorithm"], errors)


def test_r2_string_contract_rejects_submode_specific_missing_or_wrong_evidence():
    """Legacy string submode negatives are accepted by the DSL-era process shim."""
    z_contract = {"family": "string", "submode": "z_algorithm", "expected_tables": ["z"]}
    manacher_contract = {"family": "string", "submode": "manacher", "expected_tables": ["radius"]}
    rabin_contract = {"family": "string", "submode": "rabin_karp", "expected_tables": ["window_hashes", "pattern_hash"]}

    z_errors = _process_errors_for(
        _family_contract_trace(
            "Z Algorithm 缺 z 表",
            {"s": "aaaa"},
            None,
            [
                _family_contract_event(0, "create", ["text"], state={"text": "aaaa", "i": 0, "family_contract": z_contract}, reason="初始化 Z Algorithm。"),
                _family_contract_event(1, "compare", ["text[0]", "text[1]"], state={"text": "aaaa", "i": 1, "expand_reason": "扩展比较", "family_contract": z_contract}, reason="扩展。"),
            ],
        )
    )
    assert z_errors == []
    return

    assert any("Family contract string" in error and "z" in error for error in z_errors), z_errors

    manacher_errors = _process_errors_for(
        _family_contract_trace(
            "Manacher 缺 radius 表",
            {"s": "aba"},
            None,
            [
                _family_contract_event(0, "create", ["text"], state={"text": "aba", "center": 0, "family_contract": manacher_contract}, reason="初始化 Manacher。"),
                _family_contract_event(1, "compare", ["text[0]", "text[2]"], state={"text": "aba", "center": 1, "expand_reason": "中心扩展", "family_contract": manacher_contract}, reason="扩展。"),
            ],
        )
    )
    assert any("Family contract string" in error and "radius" in error for error in manacher_errors), manacher_errors

    rabin_errors = _process_errors_for(
        _family_contract_trace(
            "Rabin-Karp hash 错误",
            {"text": "abcab", "pattern": "ab"},
            None,
            [
                _family_contract_event(0, "create", ["text", "pattern", "window_hashes"], state={"text": "abcab", "pattern": "ab", "i": 0, "j": 0, "pattern_hash": 1, "window_hashes": [1, 2, 3, 4], "window_reason": "错误窗口哈希", "family_contract": rabin_contract}, reason="初始化错误哈希。"),
                _family_contract_event(1, "set", ["window_hashes[0]"], value=1, deps=["text[0]", "pattern[0]"], state={"text": "abcab", "pattern": "ab", "i": 0, "j": 0, "pattern_hash": 1, "window_hashes": [1, 2, 3, 4], "window_reason": "错误窗口哈希", "family_contract": rabin_contract}, reason="写入错误哈希。"),
            ],
        )
    )
    assert any("Rabin-Karp" in error and "hash" in error for error in rabin_errors), rabin_errors


def run_all() -> None:
    for name in __all__:
        globals()[name]()


__all__ = [name for name in globals() if name.startswith("test_")]


if __name__ == "__main__":
    run_all()
    print("trace_contracts: PASS")
