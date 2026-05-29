"""Split regression tests: trace contracts."""

from __future__ import annotations

from algolab.schemas.semantic_trace import SemanticTrace

from tests.regression.helpers import *

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


__all__ = [name for name in globals() if name.startswith("test_")]
