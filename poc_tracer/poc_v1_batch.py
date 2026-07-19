"""PoC v1 batch: Dijkstra, Kruskal, Trie.

Validates the v1 additions to the DSL: heap + union_find + trie + linked_list.
Each algorithm:
1) has a reference solve(input) → answer
2) has a trace(input) → SemanticTrace dict using only the DSL
3) is verified against the executor's compatibility checks
"""

from __future__ import annotations

import heapq
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from poc_tracer.dsl import TraceSession  # noqa: E402


# =============================================================================
# Dijkstra (heap + graph)
# =============================================================================

def dijkstra_solve(input_data: dict) -> dict:
    nodes = input_data["nodes"]
    edges = input_data["edges"]
    src = input_data["source"]
    adj: dict = {n: [] for n in nodes}
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    dist = {n: float("inf") for n in nodes}
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return {n: (None if dist[n] == float("inf") else dist[n]) for n in nodes}


def dijkstra_trace(input_data: dict) -> dict:
    nodes = input_data["nodes"]
    edges = input_data["edges"]
    src = input_data["source"]

    sess = TraceSession(
        algorithm="Dijkstra 最短路",
        input_data=input_data,
        max_events=80,
        pseudocode=[
            "dist[src]=0, 其余 inf",
            "while heap 非空：pop 最小 (d,u)",
            "  对每条 (u,v,w)：若 d+w<dist[v] 则更新+入堆",
        ],
    )

    g = sess.graph("g", nodes, edges, directed=False)
    dist_arr = sess.array("dist", [99999] * len(nodes))
    name2idx = {n: i for i, n in enumerate(nodes)}
    pq = sess.heap("pq", [])

    adj: dict = {n: [] for n in nodes}
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))

    dist_arr[name2idx[src]] = 0
    pq.push((0, src), reason=f"源点 {src} 入堆")

    while not pq.empty():
        d, u = pq.pop(reason=f"取出最小")
        if d > dist_arr[name2idx[u]]:
            sess.note(f"跳过 ({d},{u})：已被更短路径替代")
            continue
        g.highlight_node(u, role="visited", reason=f"确定 {u} 最短距离 = {d}")
        for v, w in adj[u]:
            nd = d + w
            if nd < dist_arr[name2idx[v]]:
                with sess.step(f"松弛 {u}->{v}: {dist_arr[name2idx[v]]} -> {nd}"):
                    dist_arr[name2idx[v]] = nd
                    pq.push((nd, v), reason=f"({nd},{v}) 入堆")

    result = {n: (None if dist_arr[i] == 99999 else dist_arr[i])
              for i, n in enumerate(nodes)}
    sess.result(result)
    return sess.to_trace()


# =============================================================================
# Kruskal MST (union_find + sort)
# =============================================================================

def kruskal_solve(input_data: dict) -> int:
    nodes = input_data["nodes"]
    edges = input_data["edges"]
    edges_sorted = sorted(edges, key=lambda e: e[2])
    name2idx = {n: i for i, n in enumerate(nodes)}
    parent = list(range(len(nodes)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    total = 0
    used = 0
    for u, v, w in edges_sorted:
        ru, rv = find(name2idx[u]), find(name2idx[v])
        if ru != rv:
            parent[ru] = rv
            total += w
            used += 1
            if used == len(nodes) - 1:
                break
    return total


def kruskal_trace(input_data: dict) -> dict:
    nodes = input_data["nodes"]
    edges = input_data["edges"]

    sess = TraceSession(
        algorithm="Kruskal MST",
        input_data=input_data,
        max_events=80,
        pseudocode=[
            "按边权升序排序",
            "for (u,v,w): 若 find(u) != find(v) 则 union 并选入 MST",
        ],
    )

    g = sess.graph("g", nodes, edges, directed=False)
    uf = sess.union_find("uf", len(nodes))
    name2idx = {n: i for i, n in enumerate(nodes)}
    total = sess.scalar("total", 0)

    edges_sorted = sorted(edges, key=lambda e: e[2])
    used = 0
    for u, v, w in edges_sorted:
        with sess.step(f"考察边 {u}-{v} 权 {w}"):
            if uf.union(name2idx[u], name2idx[v], reason=f"合并 {u},{v}"):
                g.highlight_edge(u, v, role="mst", reason=f"选入 MST")
                total.set(total.value + w, reason=f"total += {w}")
                used += 1
                if used == len(nodes) - 1:
                    sess.note(f"已选 {used} 条边，MST 完成")
                    break
            else:
                sess.note(f"{u},{v} 已连通，跳过")

    sess.result(total.value)
    return sess.to_trace()


# =============================================================================
# Trie + prefix count
# =============================================================================

def trie_solve(input_data: dict) -> list:
    words = input_data["words"]
    queries = input_data["queries"]
    counts = {}
    for w in words:
        for i in range(1, len(w) + 1):
            p = w[:i]
            counts[p] = counts.get(p, 0) + 1
    return [counts.get(q, 0) for q in queries]


def trie_trace(input_data: dict) -> dict:
    words = input_data["words"]
    queries = input_data["queries"]

    sess = TraceSession(
        algorithm="Trie 前缀计数",
        input_data=input_data,
        max_events=80,
        pseudocode=[
            "for word in words: trie.insert(word)",
            "for q in queries: result.append(trie.prefix_count(q))",
        ],
    )

    trie = sess.trie("trie")
    results = sess.array("results", [])

    for w in words:
        with sess.step(f"插入 '{w}'"):
            trie.insert(w)

    out = []
    for q in queries:
        with sess.step(f"查询前缀 '{q}'"):
            cnt = trie.prefix_count(q)
            out.append(cnt)

    sess.result(out)
    return sess.to_trace()


# =============================================================================
# Driver
# =============================================================================

CASES = [
    (
        "Dijkstra",
        dijkstra_solve, dijkstra_trace,
        {"nodes": ["A", "B", "C", "D"],
         "edges": [["A", "B", 1], ["B", "C", 2], ["A", "C", 4], ["C", "D", 1]],
         "source": "A"},
    ),
    (
        "Kruskal",
        kruskal_solve, kruskal_trace,
        {"nodes": ["A", "B", "C", "D"],
         "edges": [["A", "B", 1], ["B", "C", 2], ["A", "C", 4], ["C", "D", 1], ["A", "D", 5]]},
    ),
    (
        "Trie",
        trie_solve, trie_trace,
        {"words": ["apple", "app", "apricot", "banana"],
         "queries": ["app", "apr", "ba", "x"]},
    ),
]


def main() -> bool:
    from algolab.runtime.executor import canonical, _validate_trace_budget
    from algolab.schemas.semantic_trace import SemanticTrace

    print("=" * 60)
    print("DSL v1 batch PoC")
    print("=" * 60)

    passed = 0
    for name, solver, tracer_fn, case in CASES:
        print(f"\n[{name}]")
        try:
            expected = solver(case)
            raw = tracer_fn(case)
            SemanticTrace.model_validate(raw)
            _validate_trace_budget(raw)
            ok_input = canonical(case) == canonical(raw["input_data"])
            ok_result = canonical(expected) == canonical(raw["result"])
            print(f"  events           : {len(raw['events'])}")
            print(f"  schema           : OK")
            print(f"  budget           : OK")
            print(f"  input match      : {'OK' if ok_input else 'FAIL'}")
            print(f"  result match     : {'OK ' + repr(expected) if ok_result else 'FAIL'}")
            if ok_input and ok_result:
                passed += 1
        except Exception as e:
            print(f"  FAIL: {type(e).__name__}: {e}")
    print(f"\n{'=' * 60}\nPASSED {passed}/{len(CASES)}\n{'=' * 60}")
    return passed == len(CASES)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
