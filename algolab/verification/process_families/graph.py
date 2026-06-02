"""Process validators: graph."""

from __future__ import annotations

from algolab.verification.process_families.common import *
import heapq
from collections import deque

def _validate_graph_trace_contract(trace: SemanticTrace) -> list[str]:
    contract = _graph_contract_for_trace(trace)
    if contract is None:
        return []
    submode = _normalize_graph_submode(contract.get("submode"))
    if not submode:
        return ["Graph contract 缺少 submode，无法选择图算法过程合同"]
    if submode not in GRAPH_CONTRACT_SUBMODES:
        return [f"Graph contract 未支持的 submode：{submode}"]
    if submode == "bfs":
        return _validate_graph_contract_bfs(trace, contract)
    if submode == "dfs":
        return _validate_graph_contract_dfs(trace, contract)
    if submode == "connected_components":
        return _validate_graph_contract_connected_components(trace, contract)
    if submode == "bipartite_coloring":
        return _validate_graph_contract_bipartite_coloring(trace, contract)
    if submode == "dijkstra":
        return _validate_graph_contract_dijkstra(trace, contract)
    if submode == "bellman_ford":
        return _validate_graph_contract_bellman_ford(trace, contract)
    if submode == "floyd_warshall":
        return _validate_graph_contract_floyd_warshall(trace, contract)
    if submode == "zero_one_bfs":
        return _validate_graph_contract_zero_one_bfs(trace, contract)
    if submode == "topological_sort":
        return _validate_graph_contract_topological(trace, contract)
    if submode == "mst":
        return _validate_graph_contract_mst(trace, contract)
    if submode == "tarjan":
        return _validate_graph_contract_tarjan(trace, contract)
    if submode == "network_flow":
        return _validate_graph_contract_network_flow(trace, contract)
    return []


def _graph_contract_for_trace(trace: SemanticTrace) -> dict[str, Any] | None:
    for event in trace.events:
        contract = (event.state or {}).get("graph_contract")
        if isinstance(contract, dict):
            return contract
    return None


def _normalize_graph_submode(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "topo": "topological_sort",
        "topological": "topological_sort",
        "topological_sorting": "topological_sort",
        "connected": "connected_components",
        "components": "connected_components",
        "connected_component": "connected_components",
        "bipartite": "bipartite_coloring",
        "bipartite_color": "bipartite_coloring",
        "bellman-ford": "bellman_ford",
        "bellmanford": "bellman_ford",
        "floyd": "floyd_warshall",
        "floyd-warshall": "floyd_warshall",
        "floydwarshall": "floyd_warshall",
        "01_bfs": "zero_one_bfs",
        "0_1_bfs": "zero_one_bfs",
        "zero_one": "zero_one_bfs",
        "zero-one-bfs": "zero_one_bfs",
        "kruskal": "mst",
        "prim": "mst",
        "max_flow": "network_flow",
        "edmonds_karp": "network_flow",
        "edmonds-karp": "network_flow",
        "flow": "network_flow",
    }
    return aliases.get(normalized, normalized)


def _validate_graph_contract_bfs(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = _graph_contract_graph(trace)
    source = contract.get("source") or (trace.input_data.get("start") if isinstance(trace.input_data, dict) else None)
    if not isinstance(graph, dict):
        errors.append("Graph contract BFS 缺少 graph state")
        return errors
    if source is None:
        errors.append("Graph contract BFS 缺少 source/start")
    if not any(isinstance((event.state or {}).get("queue"), list) for event in trace.events):
        errors.append("Graph contract BFS 必须记录 frontier queue")
    if not _trace_has_bfs_pop(trace):
        errors.append("Graph contract BFS 缺少 queue pop 事件")
    if _reachable_edge_count(graph, _bfs_dist(graph, source)) > 0 and not _trace_has_bfs_edge_check(trace):
        errors.append("Graph contract BFS 缺少边检查事件")

    expected_dist = _bfs_dist(graph, source)
    first_seen: dict[str, int] = {}
    previous_queue: list[Any] | None = None
    previous_dist: dict[Any, Any] = {}
    for event in trace.events:
        state = event.state or {}
        queue = state.get("queue")
        if isinstance(queue, list):
            if previous_queue is not None:
                errors.extend(_validate_bfs_queue_transition(event.step, previous_queue, queue, event))
            previous_queue = list(queue)
        dist = state.get("dist")
        if not isinstance(dist, dict):
            continue
        for node, value in dist.items():
            if node in expected_dist and value != expected_dist[node]:
                errors.append(f"第 {event.step} 步 Graph contract BFS dist[{node}] 应为 {expected_dist[node]}，实际为 {value}")
        new_nodes = [node for node in dist if node not in previous_dist]
        if event.op == SemanticOp.SET:
            target_nodes = _graph_contract_dist_targets(event)
            for node in target_nodes:
                if str(node) in first_seen:
                    errors.append(f"第 {event.step} 步 Graph contract BFS 重复首次访问 node:{node}")
                first_seen[str(node)] = event.step
        for node in new_nodes:
            if str(node) == str(source):
                continue
            if str(node) in first_seen:
                continue
            first_seen[str(node)] = event.step
        previous_dist = dict(dist)
    return errors


def _graph_contract_graph(trace: SemanticTrace) -> Any:
    for event in trace.events:
        state = event.state or {}
        value = state.get("graph")
        if isinstance(value, dict):
            return value
    if isinstance(trace.input_data, dict):
        return trace.input_data.get("graph")
    return None


def _graph_contract_weighted_graph(trace: SemanticTrace) -> Any:
    for event in trace.events:
        value = (event.state or {}).get("weighted_graph")
        if isinstance(value, dict):
            return value
    if isinstance(trace.input_data, dict):
        value = trace.input_data.get("weighted_graph")
        if isinstance(value, dict):
            return value
    return None


def _undirected_neighbors(graph: dict[Any, Any], node: Any) -> set[str]:
    neighbors: set[str] = set()
    raw_neighbors = graph.get(node)
    if isinstance(raw_neighbors, list):
        for neighbor in raw_neighbors:
            if isinstance(neighbor, dict):
                target = neighbor.get("to") or neighbor.get("target") or neighbor.get("node")
            elif isinstance(neighbor, (list, tuple)) and neighbor:
                target = neighbor[0]
            else:
                target = neighbor
            if target is not None:
                neighbors.add(str(target))
    node_text = str(node)
    for src, raw_items in graph.items():
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if isinstance(item, dict):
                target = item.get("to") or item.get("target") or item.get("node")
            elif isinstance(item, (list, tuple)) and item:
                target = item[0]
            else:
                target = item
            if str(target) == node_text:
                neighbors.add(str(src))
    return neighbors


def _connected_components(graph: dict[Any, Any]) -> list[set[str]]:
    nodes: set[str] = {str(node) for node in graph}
    for raw_neighbors in graph.values():
        if not isinstance(raw_neighbors, list):
            continue
        for item in raw_neighbors:
            if isinstance(item, dict):
                target = item.get("to") or item.get("target") or item.get("node")
            elif isinstance(item, (list, tuple)) and item:
                target = item[0]
            else:
                target = item
            if target is not None:
                nodes.add(str(target))
    seen: set[str] = set()
    components: list[set[str]] = []
    keys_by_text = {str(node): node for node in graph}
    for node in sorted(nodes):
        if node in seen:
            continue
        component: set[str] = set()
        stack = [node]
        seen.add(node)
        while stack:
            cur = stack.pop()
            component.add(cur)
            raw_key = keys_by_text.get(cur, cur)
            for neighbor in _undirected_neighbors(graph, raw_key):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    return sorted(components, key=lambda group: sorted(group))


def _normalize_components(raw_components: list[Any]) -> list[set[str]]:
    groups: list[set[str]] = []
    for component in raw_components:
        if isinstance(component, (list, tuple, set)):
            group = {str(node) for node in component}
            if group:
                groups.append(group)
        elif component is not None:
            groups.append({str(component)})
    return sorted(groups, key=lambda group: sorted(group))


def _validate_bfs_queue_transition(step: int, previous: list[Any], current: list[Any], event) -> list[str]:
    if event.op == SemanticOp.POP and len(current) <= len(previous):
        return []
    if event.op in {SemanticOp.PUSH, SemanticOp.SET, SemanticOp.MARK} and len(current) <= len(previous) + 1:
        return []
    if event.op in {SemanticOp.COMPARE, SemanticOp.EXPLAIN} and current == previous:
        return []
    if current == previous:
        return []
    return [f"第 {step} 步 Graph contract BFS queue 跳变：{previous} -> {current}"]


def _graph_contract_dist_targets(event) -> list[str]:
    nodes: list[str] = []
    for target in event.targets:
        parsed = parse_target(target.id)
        if parsed.kind == "map":
            key, _, item = parsed.name.partition(":")
            if key == "dist" and item:
                nodes.append(item)
    return nodes


def _validate_graph_contract_dfs(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    has_frontier = any(isinstance((event.state or {}).get("stack"), list) or isinstance((event.state or {}).get("frames"), list) for event in trace.events)
    has_frame_event = any(
        event.op in {SemanticOp.ENTER, SemanticOp.EXIT}
        and any(ref.startswith("frame:") for ref in (_event_target_ids(event) | _event_dep_ids(event)))
        for event in trace.events
    )
    if not has_frontier:
        errors.append("Graph contract DFS 必须记录 stack 或 recursion frame frontier")
    if not has_frame_event:
        errors.append("Graph contract DFS 缺少 recursion frame enter/exit 事件")
    if (
        _graph_contract_string_list(contract, "expected_nodes")
        and not _looks_like_bipartite_matching_dfs(trace)
        and not _visited_covers_expected_nodes(trace, contract)
    ):
        errors.append("Graph contract DFS visited 未覆盖 expected_nodes")
    return errors


def _looks_like_bipartite_matching_dfs(trace: SemanticTrace) -> bool:
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    input_has_partitions = _has_bipartite_partitions(input_data)
    for event in trace.events:
        state = event.state or {}
        if "match" not in state:
            continue
        if _has_bipartite_partitions(state) or input_has_partitions:
            return True
    return False


def _has_bipartite_partitions(data: dict[str, Any]) -> bool:
    return (
        ("left_nodes" in data and "right_nodes" in data)
        or ("left" in data and "right" in data)
        or ("left_partition" in data and "right_partition" in data)
    )


def _validate_graph_contract_connected_components(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = _graph_contract_graph(trace)
    if not isinstance(graph, dict):
        errors.append("Graph contract connected_components 缺少 graph state")
        return errors
    expected = _connected_components(graph)
    for event in trace.events:
        state = event.state or {}
        components = state.get("components")
        component = state.get("component")
        if isinstance(components, list):
            actual = _normalize_components(components)
            if actual:
                actual_nodes = set().union(*actual)
                expected_nodes = set().union(*expected) if expected else set()
                if expected_nodes and actual_nodes >= expected_nodes and actual != expected:
                    errors.append(f"第 {event.step} 步 Graph contract connected_components components 应为 {expected}")
                for group in actual:
                    if not any(group <= expected_group for expected_group in expected):
                        errors.append(f"第 {event.step} 步 Graph contract connected_components components 包含跨分量节点")
        if isinstance(component, list):
            node = state.get("current")
            if node is not None and not any(str(node) in group and set(str(x) for x in component) <= group for group in expected):
                errors.append(f"第 {event.step} 步 Graph contract connected_components component 包含非连通节点")
    if not any(isinstance((event.state or {}).get("visited"), (dict, list, set)) for event in trace.events):
        errors.append("Graph contract connected_components 必须记录 visited 状态")
    return errors


def _validate_graph_contract_bipartite_coloring(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = _graph_contract_graph(trace)
    if not isinstance(graph, dict):
        errors.append("Graph contract bipartite_coloring 缺少 graph state")
        return errors
    for event in trace.events:
        color = (event.state or {}).get("color")
        if not isinstance(color, dict):
            continue
        for node, neighbors in graph.items():
            node_color = _dict_lookup(color, node)
            if node_color is None:
                continue
            for neighbor in neighbors if isinstance(neighbors, list) else []:
                neighbor_color = _dict_lookup(color, neighbor)
                if neighbor_color is not None and neighbor_color == node_color:
                    errors.append(f"第 {event.step} 步 Graph contract bipartite_coloring 相邻节点 {node} 和 {neighbor} 颜色相同")
    if not any(isinstance((event.state or {}).get("color"), dict) for event in trace.events):
        errors.append("Graph contract bipartite_coloring 必须记录 color 状态")
    return errors


def _visited_covers_expected_nodes(trace: SemanticTrace, contract: dict[str, Any]) -> bool:
    expected = set(_graph_contract_string_list(contract, "expected_nodes"))
    if not expected:
        return True
    for event in reversed(trace.events):
        visited = (event.state or {}).get("visited")
        if isinstance(visited, dict):
            covered = {str(node) for node, flag in visited.items() if flag}
            if expected <= covered:
                return True
        if isinstance(visited, list):
            covered = {str(node) for node in visited}
            if expected <= covered:
                return True
        for key in ("dfn", "disc"):
            discovered = (event.state or {}).get(key)
            if isinstance(discovered, dict):
                covered = {str(node) for node, value in discovered.items() if value is not None}
                if expected <= covered:
                    return True
    return False


def _graph_contract_string_list(contract: dict[str, Any], key: str) -> list[str]:
    raw = contract.get(key)
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if item is not None and str(item)]


def _validate_graph_contract_dijkstra(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = _graph_contract_weighted_graph(trace) or _graph_contract_graph(trace)
    if _weighted_graph_has_negative_edge(graph):
        errors.append("Graph contract Dijkstra 遇到负权输入，必须拒绝或提供降级说明")
    if not any(isinstance((event.state or {}).get("heap"), list) or isinstance((event.state or {}).get("queue"), list) for event in trace.events):
        errors.append("Graph contract Dijkstra 必须记录 heap/frontier")
    relax_events = [event for event in trace.events if event.op == SemanticOp.SET and any(ref.startswith("dist[") for ref in _event_target_ids(event))]
    if _weighted_edge_count(graph) > 0 and not relax_events:
        errors.append("Graph contract Dijkstra 缺少 edge relax 事件")
    expected_edges = set(_graph_contract_string_list(contract, "expected_relax_edges"))
    covered_edges: set[str] = set()
    for event in relax_events:
        state = event.state or {}
        deps = _event_dep_ids(event)
        edge_refs = [ref for ref in deps if ref.startswith("edge:")]
        if not edge_refs:
            errors.append(f"第 {event.step} 步 Graph contract Dijkstra relax 缺少 edge dep")
        for edge in edge_refs:
            covered_edges.add(edge.split(":", 1)[1])
        if "old_dist" not in state or "new_dist" not in state:
            errors.append(f"第 {event.step} 步 Graph contract Dijkstra relax 缺少 old_dist/new_dist")
        parent = state.get("parent") or state.get("predecessor") or state.get("prev")
        if not isinstance(parent, dict):
            errors.append(f"第 {event.step} 步 Graph contract Dijkstra relax 缺少 parent/predecessor")
        errors.extend(_validate_relax_value(event, graph, label="Dijkstra"))
    missing = sorted(expected_edges - covered_edges)
    if missing:
        errors.append(f"Graph contract Dijkstra 缺少 relax 覆盖：{', '.join(missing)}")
    return errors


def _validate_graph_contract_bellman_ford(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    edges = _graph_contract_edges(trace)
    if not edges:
        errors.append("Graph contract Bellman-Ford 缺少 edges/weighted_graph")
        return errors
    relax_events = [event for event in trace.events if event.op == SemanticOp.SET and any(ref.startswith("dist[") for ref in _event_target_ids(event))]
    if not relax_events:
        errors.append("Graph contract Bellman-Ford 缺少 edge relax 事件")
    covered_edges: set[str] = set()
    expected_edges = set(_graph_contract_string_list(contract, "expected_relax_edges"))
    for event in relax_events:
        state = event.state or {}
        edge_refs = [ref for ref in _event_dep_ids(event) if ref.startswith("edge:")]
        if not edge_refs and not _edge_from_state(state):
            errors.append(f"第 {event.step} 步 Graph contract Bellman-Ford relax 缺少 edge dep")
        for edge in edge_refs:
            covered_edges.add(edge.split(":", 1)[1])
        edge = _edge_from_event(event, edges)
        if edge is None:
            continue
        u, v, weight = edge
        dist = state.get("dist")
        if not isinstance(dist, dict):
            continue
        source_dist = _dict_lookup(dist, u)
        target_dist = _dict_lookup(dist, v)
        new_dist = state.get("new_dist", event.after if event.after is not None else event.value)
        if isinstance(source_dist, (int, float)) and isinstance(new_dist, (int, float)):
            expected = source_dist + weight
            if not _close(float(new_dist), float(expected), 1e-9):
                errors.append(f"第 {event.step} 步 Graph contract Bellman-Ford dist[{v}] 应为 {expected}，实际为 {new_dist}")
        if isinstance(target_dist, (int, float)) and isinstance(new_dist, (int, float)) and not _close(float(target_dist), float(new_dist), 1e-9):
            errors.append(f"第 {event.step} 步 Graph contract Bellman-Ford dist[{v}] 与 new_dist 不一致")
    missing = sorted(expected_edges - covered_edges)
    if missing:
        errors.append(f"Graph contract Bellman-Ford 缺少 relax 覆盖：{', '.join(missing)}")
    return errors


def _validate_graph_contract_floyd_warshall(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        if event.op != SemanticOp.SET:
            continue
        state = event.state or {}
        dist = state.get("dist")
        if not _is_matrix(dist):
            continue
        k, i, j = state.get("k"), state.get("i"), state.get("j")
        if not all(isinstance(value, int) for value in (k, i, j)):
            errors.append(f"第 {event.step} 步 Graph contract Floyd 缺少 k/i/j 阶段索引")
            continue
        if not (0 <= i < len(dist) and 0 <= j < len(dist[i]) and 0 <= k < len(dist)):
            errors.append(f"第 {event.step} 步 Graph contract Floyd k/i/j 越界")
            continue
        via_left = _matrix_get(dist, i, k)
        via_right = _matrix_get(dist, k, j)
        if not isinstance(via_left, (int, float)) or not isinstance(via_right, (int, float)):
            continue
        candidate = via_left + via_right
        new_value = event.after if event.after is not None else event.value
        if isinstance(new_value, (int, float)) and not _close(float(new_value), float(candidate), 1e-9):
            errors.append(f"第 {event.step} 步 Graph contract Floyd dist[{i}][{j}] 应为 {candidate}，实际为 {new_value}")
        refs = _event_dep_ids(event)
        expected_deps = {f"dist[{i}][{k}]", f"dist[{k}][{j}]"}
        if not expected_deps <= refs:
            errors.append(f"第 {event.step} 步 Graph contract Floyd dist[{i}][{j}] 依赖应包含 {', '.join(sorted(expected_deps))}")
    return errors


def _validate_graph_contract_zero_one_bfs(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = _graph_contract_weighted_graph(trace) or _graph_contract_graph(trace)
    if not _looks_like_weighted_graph(graph):
        errors.append("Graph contract 0-1 BFS 缺少 0/1 weighted_graph")
        return errors
    for node in graph:
        for _neighbor, weight in _weighted_neighbors(graph, node):
            if weight not in {0, 1}:
                errors.append("Graph contract 0-1 BFS 只能强校验权重 0 或 1 的图")
    if not any(isinstance((event.state or {}).get("deque"), list) or isinstance((event.state or {}).get("queue"), list) for event in trace.events):
        errors.append("Graph contract 0-1 BFS 必须记录 deque/frontier")
    for event in trace.events:
        if event.op == SemanticOp.SET and any(ref.startswith("dist[") for ref in _event_target_ids(event)):
            errors.extend(_validate_relax_value(event, graph, label="0-1 BFS"))
    return errors


def _weighted_graph_has_negative_edge(graph: Any) -> bool:
    if not isinstance(graph, dict):
        return False
    for node in graph:
        for _neighbor, weight in _weighted_neighbors(graph, node):
            if weight < 0:
                return True
    return False


def _weighted_edge_count(graph: Any) -> int:
    if not isinstance(graph, dict):
        return 0
    return sum(len(_weighted_neighbors(graph, node)) for node in graph)


def _validate_graph_contract_topological(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = _graph_contract_graph(trace)
    has_edges = isinstance(graph, dict) and any(isinstance(neighbors, list) and neighbors for neighbors in graph.values())
    if not any(isinstance((event.state or {}).get("queue"), list) for event in trace.events):
        errors.append("Graph contract topological_sort 必须记录 zero-indegree queue")
    indegree_events = [
        event for event in trace.events
        if event.op == SemanticOp.SET and any(ref.startswith("indegree[") for ref in _event_target_ids(event))
    ]
    if has_edges and not indegree_events:
        errors.append("Graph contract topological_sort 缺少 indegree 变化事件")
    for event in indegree_events:
        for node in _topological_indegree_target_nodes(event):
            if _topological_indegree_value(event, node) == 0 and not _has_topological_enqueue_evidence(trace, event, node):
                errors.append(f"第 {event.step} 步 Graph contract topological_sort 缺少入队原因")
        errors.extend(_validate_topological_indegree_transition(event))
    if _graph_contract_string_list(contract, "expected_nodes"):
        expected = set(_graph_contract_string_list(contract, "expected_nodes"))
        seen_order = set()
        for event in trace.events:
            order = (event.state or {}).get("topo_order") or (event.state or {}).get("order")
            if isinstance(order, list):
                seen_order.update(str(node) for node in order)
        if not expected <= seen_order:
            errors.append("Graph contract topological_sort topo_order 未覆盖 expected_nodes")
    return errors


def _topological_indegree_target_nodes(event) -> list[str]:
    nodes: list[str] = []
    for target_id in _event_target_ids(event):
        parsed = parse_target(target_id)
        if parsed.kind != "map":
            continue
        key, _, node = parsed.name.partition(":")
        if key == "indegree" and node:
            nodes.append(node)
    return nodes


def _topological_indegree_value(event, node: str) -> Any:
    state = event.state or {}
    indegree = state.get("indegree")
    if not isinstance(indegree, dict):
        return None
    return _dict_lookup(indegree, node)


def _has_topological_enqueue_evidence(trace: SemanticTrace, event, node: str) -> bool:
    if _topological_event_mentions_enqueue(event) and _event_queue_contains(event, node):
        return True
    if _topological_event_mentions_enqueue(event) and "enqueue_reason" in (event.state or {}):
        return True
    for later in trace.events:
        if later.step <= event.step:
            continue
        if later.op != SemanticOp.PUSH or "queue" not in _event_target_ids(later):
            continue
        if str(later.value) != node and not _event_queue_contains(later, node):
            continue
        if _topological_event_mentions_enqueue(later):
            return True
    return False


def _topological_event_mentions_enqueue(event) -> bool:
    state = event.state or {}
    reason = (event.reason or "").lower()
    return (
        "enqueue_reason" in state
        or "入队" in (event.reason or "")
        or "zero" in reason
        or "==0" in reason
        or "归零" in (event.reason or "")
    )


def _event_queue_contains(event, node: str) -> bool:
    queue = (event.state or {}).get("queue")
    return isinstance(queue, list) and any(str(item) == node for item in queue)


def _validate_graph_contract_mst(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not any(isinstance((event.state or {}).get("union_find"), dict) or isinstance((event.state or {}).get("dsu"), dict) for event in trace.events):
        errors.append("Graph contract MST 必须记录 union-find 状态")
    decision_events = [event for event in trace.events if any(ref.startswith("edge:") for ref in (_event_target_ids(event) | _event_dep_ids(event)))]
    if not decision_events:
        errors.append("Graph contract MST 缺少选边/弃边事件")
    selected = False
    for event in decision_events:
        state = event.state or {}
        decision = state.get("edge_decision") or event.role
        reason = state.get("decision_reason") or event.reason
        if decision in {"selected", "select", "chosen"}:
            selected = True
        if decision in {"selected", "select", "chosen", "rejected", "reject", "skip"} and not reason:
            errors.append(f"第 {event.step} 步 Graph contract MST 缺少选边/弃边原因")
    if _graph_contract_string_list(contract, "expected_edges") and not selected:
        errors.append("Graph contract MST 未记录 expected_edges 的选边事件")
    return errors


def _validate_graph_contract_tarjan(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    has_dfn = has_low = has_stack = False
    for event in trace.events:
        state = event.state or {}
        has_dfn = has_dfn or isinstance(state.get("dfn") or state.get("disc"), dict)
        has_low = has_low or isinstance(state.get("low") or state.get("lowlink"), dict)
        has_stack = has_stack or isinstance(state.get("stack"), list)
    if not (has_dfn and has_low and has_stack):
        errors.append("Graph contract Tarjan 必须记录 dfn/low/stack 更新")
    if not any(event.op == SemanticOp.SET and any(ref.startswith("dfn[") for ref in _event_target_ids(event)) for event in trace.events):
        errors.append("Graph contract Tarjan 缺少 dfn 写入事件")
    if not any(event.op == SemanticOp.SET and any(ref.startswith("low[") for ref in _event_target_ids(event)) for event in trace.events):
        errors.append("Graph contract Tarjan 缺少 low 写入事件")
    if not any(isinstance((event.state or {}).get("component"), list) for event in trace.events):
        errors.append("Graph contract Tarjan 缺少 component 弹栈事件")
    return errors


def _validate_graph_contract_network_flow(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    has_path = has_bottleneck = has_capacity = has_flow = False
    flow_update = False
    for event in trace.events:
        state = event.state or {}
        has_path = has_path or isinstance(state.get("augmenting_path"), list)
        bottleneck = state.get("bottleneck")
        has_bottleneck = has_bottleneck or isinstance(bottleneck, (int, float))
        has_capacity = has_capacity or isinstance(state.get("capacity") or state.get("cap"), dict)
        has_flow = has_flow or isinstance(state.get("flow"), dict)
        if event.op == SemanticOp.SET and any(ref.startswith("flow[") for ref in _event_target_ids(event)):
            flow_update = True
            deps = _event_dep_ids(event)
            if not any(ref.startswith("cap[") for ref in deps) and not isinstance(state.get("capacity") or state.get("cap"), dict):
                errors.append(f"第 {event.step} 步 Graph contract network_flow flow 更新缺少 capacity 依据")
    if not has_path:
        errors.append("Graph contract network_flow 缺少 augmenting path")
    if not has_bottleneck:
        errors.append("Graph contract network_flow 缺少 bottleneck")
    if not has_capacity or not has_flow:
        errors.append("Graph contract network_flow 必须记录 flow/capacity")
    if not flow_update:
        errors.append("Graph contract network_flow 缺少 flow/capacity 更新事件")
    return errors


def _looks_like_bfs(trace: SemanticTrace) -> bool:
    if not isinstance(trace.input_data, dict):
        return False
    contract = _graph_contract_for_trace(trace)
    if isinstance(contract, dict):
        return _normalize_graph_submode(contract.get("submode")) == "bfs"
    graph = trace.input_data.get("graph")
    algorithm = (trace.algorithm or "").lower()
    return (
        isinstance(graph, dict)
        and "start" in trace.input_data
        and ("bfs" in algorithm or "宽度优先" in algorithm)
        and all(isinstance(neighbors, list) and all(not isinstance(nei, (list, tuple, dict)) for nei in neighbors) for neighbors in graph.values())
    )


def _validate_bfs_distances(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    graph = trace.input_data.get("graph")
    start = _bfs_source_for_trace(trace)
    if not isinstance(graph, dict):
        return errors
    expected = _bfs_dist(graph, start)
    for event in trace.events:
        dist = (event.state or {}).get("dist")
        if not isinstance(dist, dict):
            continue
        for node, value in dist.items():
            if node not in expected:
                errors.append(f"第 {event.step} 步 dist 包含不可达节点：{node}")
            elif expected[node] != value:
                errors.append(f"第 {event.step} 步 dist[{node}] 应为 {expected[node]}，实际为 {value}")
        errors.extend(_validate_bfs_discovery_source(event, graph, expected, start))
    return errors


def _validate_bfs_key_step_coverage(trace: SemanticTrace) -> list[str]:
    graph = trace.input_data.get("graph")
    start = _bfs_source_for_trace(trace)
    if not isinstance(graph, dict) or not _is_small_bfs_graph(graph):
        return []
    expected = _bfs_dist(graph, start)
    if not expected:
        return []
    missing: list[str] = []
    if not _trace_has_bfs_pop(trace):
        missing.append("pop_queue")
    if _reachable_edge_count(graph, expected) > 0 and not _trace_has_bfs_edge_check(trace):
        missing.append("check_edge")
    discovered = {str(node) for node in expected if not _same_node(node, start)}
    if discovered and not _trace_has_bfs_first_visit(trace, discovered):
        missing.append("first_visit")
    if missing:
        return [f"failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：{', '.join(missing)}"]
    return []


def _bfs_source_for_trace(trace: SemanticTrace) -> Any:
    contract = _graph_contract_for_trace(trace)
    if isinstance(contract, dict) and contract.get("source") is not None:
        return contract.get("source")
    if isinstance(trace.input_data, dict):
        if trace.input_data.get("start") is not None:
            return trace.input_data.get("start")
        return trace.input_data.get("source")
    return None


def _is_small_bfs_graph(graph: dict[Any, Any]) -> bool:
    edge_count = sum(len(neighbors) for neighbors in graph.values() if isinstance(neighbors, list))
    return len(graph) <= SMALL_BFS_NODE_LIMIT and edge_count <= SMALL_BFS_EDGE_LIMIT


def _trace_has_bfs_pop(trace: SemanticTrace) -> bool:
    for event in trace.events:
        if event.op != SemanticOp.POP:
            continue
        target_ids = _event_target_ids(event)
        if "queue" in target_ids or any(target.startswith("node:") for target in target_ids):
            return True
    return False


def _trace_has_bfs_edge_check(trace: SemanticTrace) -> bool:
    for event in trace.events:
        if event.op not in {SemanticOp.COMPARE, SemanticOp.MARK, SemanticOp.EXPLAIN}:
            continue
        refs = _event_target_ids(event) | _event_dep_ids(event)
        if any(ref.startswith("edge:") for ref in refs):
            return True
    return False


def _trace_has_bfs_first_visit(trace: SemanticTrace, discovered: set[str]) -> bool:
    for event in trace.events:
        if event.op not in {SemanticOp.MARK, SemanticOp.SET, SemanticOp.PUSH}:
            continue
        refs = _event_target_ids(event)
        if any(_bfs_refers_to_discovered_node(ref, discovered) for ref in refs):
            return True
    return False


def _bfs_refers_to_discovered_node(ref: str, discovered: set[str]) -> bool:
    parsed = parse_target(ref)
    if parsed.kind == "node":
        return str(parsed.name) in discovered
    if parsed.kind == "map":
        key, _, item = parsed.name.partition(":")
        return key in {"dist", "parent", "parents", "prev"} and item in discovered
    return False


def _reachable_edge_count(graph: dict[Any, Any], expected: dict[Any, int]) -> int:
    reachable = {str(node) for node in expected}
    count = 0
    for node, neighbors in graph.items():
        if str(node) not in reachable or not isinstance(neighbors, list):
            continue
        count += len(neighbors)
    return count


def _bfs_dist(graph: dict[str, Any], start: Any) -> dict[Any, int]:
    dist = {start: 0}
    queue = [start]
    head = 0
    while head < len(queue):
        cur = queue[head]
        head += 1
        for nei in graph.get(cur, []):
            if nei not in dist:
                dist[nei] = dist[cur] + 1
                queue.append(nei)
    return dist


def _validate_bfs_discovery_source(event, graph: dict[Any, Any], expected: dict[Any, int], start: Any) -> list[str]:
    errors: list[str] = []
    state = event.state or {}
    dist = state.get("dist")
    if not isinstance(dist, dict):
        return errors
    discovered_nodes = _bfs_event_discovered_nodes(event)
    parent_map = state.get("parent") or state.get("parents") or state.get("prev")
    for node in discovered_nodes:
        if _same_node(node, start):
            continue
        value = _dict_lookup(dist, node)
        if not isinstance(value, int):
            continue
        if node in expected and value != expected[node]:
            continue
        sources = _bfs_declared_sources(event, parent_map, node)
        if not sources:
            continue
        if not any(_is_valid_bfs_parent(graph, dist, source, node, value) for source in sources):
            display = _node_display(node)
            source_text = ", ".join(_node_display(source) for source in sources)
            errors.append(f"第 {event.step} 步 BFS 首次发现 node:{display} 来源应为上一层相邻节点，实际为 {source_text}")
    return errors


def _bfs_event_discovered_nodes(event) -> list[Any]:
    nodes: list[Any] = []
    for target in event.targets:
        parsed = parse_target(target.id)
        if parsed.kind == "node":
            nodes.append(parsed.name)
        elif parsed.kind == "map":
            key, _, item = parsed.name.partition(":")
            if key in {"dist", "parent", "parents", "prev"} and item:
                nodes.append(item)
    return nodes


def _bfs_declared_sources(event, parent_map: Any, node: Any) -> list[Any]:
    sources: list[Any] = []
    if isinstance(parent_map, dict):
        parent = _dict_lookup(parent_map, node)
        if parent is not None:
            sources.append(parent)
    for dep in event.deps:
        parsed = parse_target(dep.id)
        if parsed.kind == "node":
            sources.append(parsed.name)
        elif parsed.kind == "map":
            key, _, item = parsed.name.partition(":")
            if key in {"dist", "parent", "parents", "prev"} and item:
                sources.append(item)
    return _dedupe_nodes(sources)


def _is_valid_bfs_parent(graph: dict[Any, Any], dist: dict[Any, Any], source: Any, node: Any, node_dist: int) -> bool:
    source_dist = _dict_lookup(dist, source)
    if source_dist != node_dist - 1:
        return False
    return any(_same_node(nei, node) for nei in _graph_neighbors(graph, source))


def _graph_neighbors(graph: dict[Any, Any], node: Any) -> list[Any]:
    for graph_node, neighbors in graph.items():
        if _same_node(graph_node, node):
            return neighbors if isinstance(neighbors, list) else []
    return []


def _dedupe_nodes(nodes: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for node in nodes:
        key = str(node)
        if key in seen:
            continue
        seen.add(key)
        result.append(node)
    return result


def _validate_union_find_forest(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        uf = (event.state or {}).get("union_find") or (event.state or {}).get("dsu")
        parent = uf.get("parent") if isinstance(uf, dict) else None
        if not isinstance(parent, dict):
            continue
        nodes = set(parent)
        for node, par in parent.items():
            if par not in nodes:
                errors.append(f"第 {event.step} 步 parent[{node}] 指向不存在节点 {par}")
        for node in nodes:
            seen = set()
            cur = node
            while cur in parent and cur not in seen:
                seen.add(cur)
                cur = parent[cur]
            if cur in seen and parent.get(cur) != cur:
                errors.append(f"第 {event.step} 步 union_find 存在非根环：{node}")
        errors.extend(_validate_union_find_link_event(event, parent))
    return errors


def _validate_union_find_link_event(event, parent: dict[Any, Any] | None) -> list[str]:
    if event.op not in {SemanticOp.LINK, SemanticOp.SET, SemanticOp.MARK} or not isinstance(parent, dict):
        return []
    state = event.state or {}
    pairs = _union_find_pairs(event, state)
    errors: list[str] = []
    for left, right in pairs:
        if _uf_find(parent, left) != _uf_find(parent, right):
            errors.append(f"第 {event.step} 步 union 后 {left} 和 {right} 应连通")
    return errors


def _union_find_pairs(event, state: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    i, j = state.get("i"), state.get("j")
    is_connected = state.get("isConnected") or state.get("connected")
    if isinstance(i, int) and isinstance(j, int) and _matrix_has_connection(is_connected, i, j):
        pairs.append((str(i), str(j)))
    target_nodes = [_target_node_name(target.id) for target in event.targets]
    dep_nodes = [_target_node_name(dep.id) for dep in event.deps]
    for left in target_nodes:
        for right in dep_nodes:
            if left is not None and right is not None:
                pairs.append((left, right))
    return list(dict.fromkeys(pairs))


def _matrix_has_connection(matrix: Any, i: int, j: int) -> bool:
    try:
        return bool(matrix[i][j])
    except Exception:
        return False


def _target_node_name(target_id: str) -> str | None:
    parsed = parse_target(target_id)
    if parsed.kind == "node":
        return str(parsed.name)
    if parsed.kind == "map":
        key, _, item = parsed.name.partition(":")
        if key == "parent" and item:
            return item
    return None


def _uf_find(parent: dict[Any, Any], node: Any) -> str | None:
    keys = {str(key): key for key in parent}
    cur_key = str(node)
    seen: set[str] = set()
    while cur_key in keys and cur_key not in seen:
        seen.add(cur_key)
        raw_key = keys[cur_key]
        next_key = str(parent[raw_key])
        if next_key == cur_key:
            return cur_key
        cur_key = next_key
    return None


def _validate_topological_order(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        order = state.get("topo_order") or state.get("order")
        graph = state.get("graph") or trace.input_data.get("graph") if isinstance(trace.input_data, dict) else state.get("graph")
        if not isinstance(order, list) or not isinstance(graph, dict):
            continue
        pos = {node: i for i, node in enumerate(order)}
        for src, neighbors in graph.items():
            if not isinstance(neighbors, list):
                continue
            for dst in neighbors:
                if src in pos and dst in pos and pos[src] > pos[dst]:
                    errors.append(f"第 {event.step} 步 topo_order 违反边 {src}->{dst}")
    return errors


def _validate_topological_indegree_transition(event) -> list[str]:
    state = event.state or {}
    graph = state.get("graph")
    indegree = state.get("indegree")
    if not isinstance(graph, dict) or not isinstance(indegree, dict):
        return []
    errors: list[str] = []
    for target_id in _event_target_ids(event):
        parsed = parse_target(target_id)
        if parsed.kind != "map":
            continue
        key, _, node = parsed.name.partition(":")
        if key != "indegree" or not node:
            continue
        incoming_sources = [
            str(src)
            for src, neighbors in graph.items()
            if isinstance(neighbors, list) and any(str(neighbor) == node for neighbor in neighbors)
        ]
        popped = {str(item) for item in state.get("topo_order", []) if item is not None}
        expected = max(0, len(incoming_sources) - sum(1 for src in incoming_sources if src in popped))
        actual = _dict_lookup(indegree, node)
        if isinstance(actual, int) and actual != expected:
            errors.append(f"第 {event.step} 步 Graph contract topological_sort indegree[{node}] 应为 {expected}，实际为 {actual}")
        queue = state.get("queue")
        if isinstance(queue, list) and any(str(item) == node for item in queue) and actual not in {0, None}:
            errors.append(f"第 {event.step} 步 Graph contract topological_sort indegree[{node}] 未归零却入队")
    return errors


def _validate_dijkstra_distances(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    if not isinstance(trace.input_data, dict):
        return errors
    graph = trace.input_data.get("weighted_graph") or trace.input_data.get("graph")
    start = trace.input_data.get("start")
    if not _looks_like_weighted_graph(graph) or start is None:
        return errors
    expected = _dijkstra(graph, start)
    for event in trace.events:
        dist = (event.state or {}).get("dist")
        if not isinstance(dist, dict):
            continue
        for node, value in dist.items():
            if node in expected and isinstance(value, (int, float)) and value < expected[node]:
                errors.append(f"第 {event.step} 步 dist[{node}] 小于 Dijkstra 最短路")
    return errors


def _looks_like_weighted_graph(graph: Any) -> bool:
    return isinstance(graph, dict) and any(
        isinstance(edges, list)
        and any((isinstance(edge, dict) and "weight" in edge) or (isinstance(edge, (list, tuple)) and len(edge) >= 2) for edge in edges)
        for edges in graph.values()
    )


def _weighted_neighbors(graph: dict[Any, Any], node: Any) -> list[tuple[Any, float]]:
    result = []
    for edge in graph.get(node, []):
        if isinstance(edge, dict):
            dst = edge.get("to") or edge.get("target") or edge.get("node")
            weight = edge.get("weight")
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            dst, weight = edge[0], edge[1]
        else:
            continue
        if isinstance(weight, (int, float)):
            result.append((dst, weight))
    return result


def _graph_contract_edges(trace: SemanticTrace) -> list[tuple[Any, Any, float]]:
    edges: list[tuple[Any, Any, float]] = []
    data = trace.input_data if isinstance(trace.input_data, dict) else {}
    raw_edges = data.get("edges")
    if isinstance(raw_edges, list):
        edges.extend(_weighted_edges_from_list(raw_edges))
    graph = data.get("weighted_graph") or data.get("graph")
    if isinstance(graph, dict):
        edges.extend(_weighted_edges_from_graph(graph))
    for event in trace.events:
        state = event.state or {}
        raw_state_edges = state.get("edges")
        if isinstance(raw_state_edges, list):
            edges.extend(_weighted_edges_from_list(raw_state_edges))
        state_graph = state.get("weighted_graph")
        if isinstance(state_graph, dict):
            edges.extend(_weighted_edges_from_graph(state_graph))
    deduped: dict[tuple[str, str, float], tuple[Any, Any, float]] = {}
    for u, v, weight in edges:
        deduped[(str(u), str(v), float(weight))] = (u, v, weight)
    return list(deduped.values())


def _weighted_edges_from_graph(graph: dict[Any, Any]) -> list[tuple[Any, Any, float]]:
    edges: list[tuple[Any, Any, float]] = []
    for node in graph:
        for neighbor, weight in _weighted_neighbors(graph, node):
            edges.append((node, neighbor, float(weight)))
    return edges


def _weighted_edges_from_list(raw_edges: list[Any]) -> list[tuple[Any, Any, float]]:
    edges: list[tuple[Any, Any, float]] = []
    for edge in raw_edges:
        u = v = weight = None
        if isinstance(edge, dict):
            u = edge.get("u", edge.get("from"))
            v = edge.get("v", edge.get("to"))
            weight = edge.get("weight", edge.get("w"))
        elif isinstance(edge, (list, tuple)) and len(edge) >= 3:
            u, v, weight = edge[0], edge[1], edge[2]
        if u is not None and v is not None and isinstance(weight, (int, float)):
            edges.append((u, v, float(weight)))
    return edges


def _edge_from_state(state: dict[str, Any]) -> tuple[Any, Any, float] | None:
    raw = state.get("current_edge") or state.get("edge")
    edges = _weighted_edges_from_list([raw]) if raw is not None else []
    return edges[0] if edges else None


def _edge_from_event(event, edges: list[tuple[Any, Any, float]]) -> tuple[Any, Any, float] | None:
    state_edge = _edge_from_state(event.state or {})
    if state_edge is not None:
        return state_edge
    refs = _event_target_ids(event) | _event_dep_ids(event)
    for ref in refs:
        if not ref.startswith("edge:"):
            continue
        raw = ref.split(":", 1)[1]
        if "->" not in raw:
            continue
        u, v = raw.split("->", 1)
        for edge_u, edge_v, weight in edges:
            if str(edge_u) == u and str(edge_v) == v:
                return edge_u, edge_v, weight
    return None


def _validate_relax_value(event, graph: Any, *, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(graph, dict):
        return errors
    edges = _weighted_edges_from_graph(graph)
    edge = _edge_from_event(event, edges)
    if edge is None:
        return errors
    u, v, weight = edge
    state = event.state or {}
    dist = state.get("dist")
    if not isinstance(dist, dict):
        return errors
    source_dist = _dict_lookup(dist, u)
    new_dist = state.get("new_dist", event.after if event.after is not None else event.value)
    if not isinstance(source_dist, (int, float)) or not isinstance(new_dist, (int, float)):
        return errors
    expected = source_dist + weight
    if not _close(float(new_dist), float(expected), 1e-9):
        errors.append(f"第 {event.step} 步 Graph contract {label} dist[{v}] 应为 {expected:g}，实际为 {new_dist}")
    return errors


def _dijkstra(graph: dict[Any, Any], start: Any) -> dict[Any, float]:
    import heapq

    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        cur_dist, node = heapq.heappop(heap)
        if cur_dist != dist.get(node):
            continue
        for nei, weight in _weighted_neighbors(graph, node):
            nd = cur_dist + weight
            if nd < dist.get(nei, float("inf")):
                dist[nei] = nd
                heapq.heappush(heap, (nd, nei))
    return dist


def _validate_mst_edges(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    edges = input_data.get("edges")
    n = input_data.get("n")
    if not isinstance(edges, list):
        return errors
    nodes = _mst_nodes(edges, n)
    for event in trace.events:
        mst = (event.state or {}).get("mst_edges") or (event.state or {}).get("mst")
        if not isinstance(mst, list) or not mst:
            continue
        parent = {node: node for node in nodes}
        count = 0
        for edge in mst:
            u, v = _edge_uv(edge)
            if u is None or v is None:
                continue
            if u not in parent:
                parent[u] = u
            if v not in parent:
                parent[v] = v
            ru, rv = _find(parent, u), _find(parent, v)
            if ru == rv:
                errors.append(f"第 {event.step} 步 MST 边集存在环：{u}-{v}")
            else:
                parent[ru] = rv
                count += 1
        if nodes and count > len(nodes) - 1:
            errors.append(f"第 {event.step} 步 MST 边数超过 n-1")
    return errors


def _mst_nodes(edges: list[Any], n: Any) -> set[Any]:
    if isinstance(n, int):
        return set(range(n))
    nodes = set()
    for edge in edges:
        u, v = _edge_uv(edge)
        if u is not None:
            nodes.add(u)
        if v is not None:
            nodes.add(v)
    return nodes

__all__ = [name for name in globals() if not name.startswith("__")]
