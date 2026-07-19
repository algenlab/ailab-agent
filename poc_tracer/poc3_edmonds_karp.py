"""PoC 3: Edmonds-Karp max flow.

The hardest graph algorithm in the benchmark — graph + residual edges +
BFS for augmenting paths + flow updates. The system today writes
hand-coded validators per family (graph.py:1214 lines, 271 conditions).
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from poc_tracer.dsl import TraceSession  # noqa: E402


def _bfs_augment(capacity: dict, flow: dict, n: int, source, sink, neighbors: dict):
    """Returns (parent dict, bottleneck) or (None, 0) if no augmenting path."""
    parent: dict = {source: None}
    visited = {source}
    queue: deque = deque([source])
    while queue:
        u = queue.popleft()
        if u == sink:
            break
        for v in neighbors.get(u, []):
            if v not in visited and capacity[(u, v)] - flow[(u, v)] > 0:
                visited.add(v)
                parent[v] = u
                queue.append(v)
    if sink not in parent:
        return None, 0
    bottleneck = float("inf")
    cur = sink
    while parent[cur] is not None:
        u = parent[cur]
        bottleneck = min(bottleneck, capacity[(u, cur)] - flow[(u, cur)])
        cur = u
    return parent, bottleneck


def solve(input_data: dict) -> int:
    nodes = list(input_data["nodes"])
    edges = list(input_data["edges"])
    source = input_data["source"]
    sink = input_data["sink"]

    capacity = {(u, v): 0 for u in nodes for v in nodes}
    flow = {(u, v): 0 for u in nodes for v in nodes}
    neighbors = {u: [] for u in nodes}
    for u, v, c in edges:
        capacity[(u, v)] = c
        if v not in neighbors[u]:
            neighbors[u].append(v)
        if u not in neighbors[v]:
            neighbors[v].append(u)

    total_flow = 0
    while True:
        parent, bn = _bfs_augment(capacity, flow, len(nodes), source, sink, neighbors)
        if parent is None:
            break
        cur = sink
        while parent[cur] is not None:
            u = parent[cur]
            flow[(u, cur)] += bn
            flow[(cur, u)] -= bn
            cur = u
        total_flow += bn
    return total_flow


def trace(input_data: dict) -> dict:
    nodes = list(input_data["nodes"])
    edges = list(input_data["edges"])
    source = input_data["source"]
    sink = input_data["sink"]

    sess = TraceSession(
        algorithm="Edmonds-Karp 网络流",
        input_data=input_data,
        max_events=80,
        pseudocode=[
            "while 存在增广路径 (BFS):",
            "  bottleneck = min 残余容量",
            "  沿路径 flow += bn, 反向 -= bn",
            "  total_flow += bn",
            "返回 total_flow",
        ],
    )

    g = sess.graph("g", nodes, [(u, v, c) for u, v, c in edges], directed=True)
    flow_var = sess.scalar("total_flow", 0)

    capacity = {(u, v): 0 for u in nodes for v in nodes}
    flow = {(u, v): 0 for u in nodes for v in nodes}
    neighbors: dict = {u: [] for u in nodes}
    for u, v, c in edges:
        capacity[(u, v)] = c
        if v not in neighbors[u]:
            neighbors[u].append(v)
        if u not in neighbors[v]:
            neighbors[v].append(u)

    iteration = 0
    while True:
        iteration += 1
        with sess.step(f"第 {iteration} 轮 BFS 找增广路径"):
            parent, bn = _bfs_augment(capacity, flow, len(nodes), source, sink, neighbors)
            if parent is None:
                sess.note("没有增广路径，结束")
                break

            path = []
            cur = sink
            while parent[cur] is not None:
                path.append((parent[cur], cur))
                cur = parent[cur]
            path.reverse()

            sess.note(f"增广路径：{' -> '.join([source] + [v for _, v in path])}，bottleneck={bn}")
            for u, v in path:
                g.highlight_edge(u, v, role="augmenting", reason=f"路径边 {u}->{v}")

            for u, v in path:
                flow[(u, v)] += bn
                flow[(v, u)] -= bn
                g.update_edge(u, v,
                              flow=flow[(u, v)],
                              capacity=capacity[(u, v)],
                              reason=f"沿 {u}->{v} 增加 {bn} 单位流")

            flow_var.set(flow_var.value + bn,
                         reason=f"total_flow += {bn}")

    sess.result(flow_var.value)
    return sess.to_trace()


if __name__ == "__main__":
    import json

    case = {
        "nodes": ["s", "a", "b", "t"],
        "edges": [
            ["s", "a", 3],
            ["s", "b", 2],
            ["a", "t", 2],
            ["a", "b", 1],
            ["b", "t", 3],
        ],
        "source": "s",
        "sink": "t",
    }
    expected = solve(case)
    raw_trace = trace(case)

    print(f"=== Edmonds-Karp PoC ===")
    print(f"input: {case['nodes']}, edges={case['edges']}")
    print(f"solve result: max flow = {expected}")
    print(f"trace result: max flow = {raw_trace['result']}")
    print(f"events: {len(raw_trace['events'])}")

    from algolab.schemas.semantic_trace import SemanticTrace
    validated = SemanticTrace.model_validate(raw_trace)
    print(f"schema OK, algorithm={validated.algorithm}")

    print("\nSample events:")
    for ev in raw_trace["events"][:8]:
        print(f"  step={ev['step']:>2} op={ev['op']:<7} targets={[t['id'] for t in ev['targets']]} reason={ev['reason'][:60]}")
    print("  ...")
    for ev in raw_trace["events"][-5:]:
        print(f"  step={ev['step']:>2} op={ev['op']:<7} targets={[t['id'] for t in ev['targets']]} reason={ev['reason'][:60]}")

    out_path = Path(__file__).parent / "edmonds_karp_trace.json"
    out_path.write_text(json.dumps(raw_trace, ensure_ascii=False, indent=2))
    print(f"\nfull trace: {out_path}")
