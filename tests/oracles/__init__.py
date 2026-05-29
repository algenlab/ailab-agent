"""Independent oracle examples for deterministic benchmark families.

These examples document oracle shape and provide small reference functions that
are intentionally separate from the benchmark solve/trace implementations.
They are not a property benchmark runner; P11.2 owns randomized sample
generation.
"""

from __future__ import annotations

from collections import deque
from itertools import combinations
from math import gcd
from typing import Any, Callable


OracleReference = Callable[[dict[str, Any]], Any]


def house_robber_bruteforce(input_data: dict[str, Any]) -> int:
    nums = input_data["nums"]
    best = 0
    for mask in range(1 << len(nums)):
        if mask & (mask << 1):
            continue
        total = sum(value for index, value in enumerate(nums) if mask & (1 << index))
        best = max(best, total)
    return best


def bfs_layers_reference(input_data: dict[str, Any]) -> dict[str, int]:
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph.get(node, []):
            if neighbor in dist:
                continue
            dist[neighbor] = dist[node] + 1
            queue.append(neighbor)
    return dist


def string_find_reference(input_data: dict[str, Any]) -> int:
    return input_data["text"].find(input_data["pattern"])


def string_unique_window_reference(input_data: dict[str, Any]) -> int:
    text = input_data["text"]
    best = 0
    for left in range(len(text) + 1):
        seen: set[str] = set()
        for right in range(left, len(text)):
            if text[right] in seen:
                break
            seen.add(text[right])
            best = max(best, right - left + 1)
    return best


def trie_prefix_count_reference(input_data: dict[str, Any]) -> int:
    prefix = input_data["prefix"]
    return sum(1 for word in input_data["words"] if word.startswith(prefix))


def sorted_property_reference(input_data: dict[str, Any]) -> dict[str, Any]:
    nums = list(input_data["nums"])
    return {
        "sorted": sorted(nums),
        "same_multiset": sorted(nums),
    }


def union_find_components_reference(input_data: dict[str, Any]) -> int:
    matrix = input_data["isConnected"]
    n = len(matrix)
    seen = [False] * n

    def visit(start: int) -> None:
        stack = [start]
        seen[start] = True
        while stack:
            node = stack.pop()
            for neighbor, connected in enumerate(matrix[node]):
                if connected and not seen[neighbor]:
                    seen[neighbor] = True
                    stack.append(neighbor)

    components = 0
    for node in range(n):
        if seen[node]:
            continue
        components += 1
        visit(node)
    return components


def range_sum_after_update_reference(input_data: dict[str, Any]) -> dict[str, int]:
    nums = list(input_data["nums"])
    left, right = input_data["query"]
    before = sum(nums[left : right + 1])
    pos, value = input_data["update"]
    nums[pos] = value
    after = sum(nums[left : right + 1])
    return {"before": before, "after": after}


def range_sum_after_delta_reference(input_data: dict[str, Any]) -> dict[str, int]:
    nums = list(input_data["nums"])
    left, right = input_data["query"]
    before = sum(nums[left : right + 1])
    pos, delta = input_data["update"]
    nums[pos] += delta
    after = sum(nums[left : right + 1])
    return {"before": before, "after": after}


def range_min_direct_reference(input_data: dict[str, Any]) -> int:
    nums = input_data["nums"]
    left, right = input_data["query"]
    return min(nums[left : right + 1])


def tree_inorder_reference(input_data: dict[str, Any]) -> list[str]:
    tree = input_data["tree"]
    children: dict[str, list[str]] = {}
    pointed = set()
    for parent, child in tree["edges"]:
        parent_id = str(parent)
        child_id = str(child)
        children.setdefault(parent_id, []).append(child_id)
        pointed.add(child_id)
    root = next(str(node["id"]) for node in tree["nodes"] if str(node["id"]) not in pointed)
    result: list[str] = []
    stack: list[tuple[str, bool]] = [(root, False)]
    while stack:
        node, expanded = stack.pop()
        kids = children.get(node, [])
        if expanded:
            result.append(node)
            continue
        if len(kids) >= 2:
            stack.append((kids[1], False))
        stack.append((node, True))
        if kids:
            stack.append((kids[0], False))
    return result


def tree_diameter_reference(input_data: dict[str, Any]) -> int:
    tree = input_data["tree"]
    adjacency: dict[str, list[str]] = {}
    for parent, child in tree["edges"]:
        adjacency.setdefault(str(parent), []).append(str(child))
        adjacency.setdefault(str(child), []).append(str(parent))
    if not adjacency:
        return 0

    def farthest(start: str) -> tuple[str, int]:
        seen = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        best = (start, 0)
        while queue:
            node, distance = queue.popleft()
            best = (node, distance)
            for neighbor in adjacency.get(node, []):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, distance + 1))
        return best

    first = next(iter(adjacency))
    end, _ = farthest(first)
    _other, diameter = farthest(end)
    return diameter


def tree_independent_set_bruteforce(input_data: dict[str, Any]) -> int:
    tree = input_data["tree"]
    nodes = [str(node["id"]) for node in tree["nodes"]]
    weights = {str(node["id"]): int(node.get("value", 1)) for node in tree["nodes"]}
    edges = {(str(a), str(b)) for a, b in tree["edges"]}
    best = 0
    for mask in range(1 << len(nodes)):
        chosen = {node for index, node in enumerate(nodes) if mask & (1 << index)}
        if any(a in chosen and b in chosen for a, b in edges):
            continue
        best = max(best, sum(weights[node] for node in chosen))
    return best


def gcd_reference(input_data: dict[str, Any]) -> int:
    return gcd(input_data["a"], input_data["b"])


def bitmask_subset_property_reference(input_data: dict[str, Any]) -> dict[str, Any]:
    nums = input_data["nums"]
    return {
        "expected_count": 1 << len(nums),
        "empty_subset": [],
        "full_subset": list(nums),
    }


def lowbit_property_reference(input_data: dict[str, Any]) -> dict[str, Any]:
    n = input_data["n"]
    parts: list[int] = []
    remaining = n
    while remaining:
        low = remaining & -remaining
        parts.append(low)
        remaining -= low
    return {
        "sum": sum(parts),
        "parts_are_powers_of_two": all(part > 0 and part & (part - 1) == 0 for part in parts),
        "parts": parts,
    }


def advanced_graph_oracle_examples(input_data: dict[str, Any]) -> dict[str, Any]:
    graph = input_data.get("graph", {})
    nodes = sorted(graph)
    reachability = {
        source: sorted(_reachable(graph, source))
        for source in nodes
    }
    undirected_edges = sorted(tuple(sorted((u, v))) for u in graph for v in graph.get(u, []))
    return {
        "nodes": nodes,
        "reachability": reachability,
        "edge_count": len(set(undirected_edges)),
    }


def _reachable(graph: dict[str, list[str]], source: str) -> set[str]:
    seen = {source}
    stack = [source]
    while stack:
        node = stack.pop()
        for neighbor in graph.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return seen


def convex_hull_property_reference(input_data: dict[str, Any]) -> dict[str, Any]:
    points = [tuple(point) for point in input_data["points"]]
    return {
        "point_count": len(points),
        "all_pairs": list(combinations(points, 2)),
    }


def oracle_examples() -> list[dict[str, Any]]:
    return [
        {
            "family_id": "dp_1d",
            "case_id": "house_robber",
            "oracle_type": "bruteforce",
            "reference": house_robber_bruteforce,
            "notes": "Enumerates all non-adjacent subsets for small inputs.",
        },
        {
            "family_id": "basic_graph",
            "case_id": "graph_bfs",
            "oracle_type": "independent_reference",
            "reference": bfs_layers_reference,
            "notes": "Uses deque-based layer traversal, separate from benchmark solve structure.",
        },
        {
            "family_id": "string_advanced",
            "case_id": "kmp",
            "oracle_type": "independent_reference",
            "reference": string_find_reference,
            "notes": "Uses language substring search as an independent expected-result oracle.",
        },
        {
            "family_id": "sorting",
            "case_id": "insertion_sort",
            "oracle_type": "property",
            "reference": sorted_property_reference,
            "notes": "Checks sorted order and multiset preservation.",
        },
        {
            "family_id": "union_find",
            "case_id": "provinces",
            "oracle_type": "independent_reference",
            "reference": union_find_components_reference,
            "notes": "Uses graph traversal rather than DSU parent mutation.",
        },
        {
            "family_id": "range_structure",
            "case_id": "segment_tree_range_sum",
            "oracle_type": "independent_reference",
            "reference": range_sum_after_update_reference,
            "notes": "Computes range sums directly from the array.",
        },
        {
            "family_id": "tree_bst_lca",
            "case_id": "binary_tree_inorder",
            "oracle_type": "independent_reference",
            "reference": tree_inorder_reference,
            "notes": "Uses an explicit stack rather than recursive benchmark traversal.",
        },
        {
            "family_id": "math_bit",
            "case_id": "gcd_euclid",
            "oracle_type": "independent_reference",
            "reference": gcd_reference,
            "notes": "Uses standard-library gcd as an independent arithmetic oracle.",
        },
        {
            "family_id": "advanced_graph",
            "case_id": "tarjan_scc",
            "oracle_type": "property",
            "reference": advanced_graph_oracle_examples,
            "notes": "Provides independent graph reachability evidence for advanced graph case review.",
        },
        {
            "family_id": "geometry_sweep",
            "case_id": "convex_hull",
            "oracle_type": "property",
            "reference": convex_hull_property_reference,
            "notes": "Provides geometry property inputs without duplicating hull construction.",
        },
    ]
