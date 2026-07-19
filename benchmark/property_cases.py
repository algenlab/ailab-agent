"""Deterministic randomized property benchmark cases for small inputs.

P11.2 keeps this layer separate from deterministic V1 release gates.  Each case
generates small samples from a fixed seed, computes an independent expected
value, and compares it with a production-shaped implementation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
import heapq
import random
from typing import Any, Callable


DEFAULT_PROPERTY_SEED = 260527

JsonDict = dict[str, Any]
CaseGenerator = Callable[[random.Random, int], JsonDict]
CaseSolver = Callable[[JsonDict], Any]


@dataclass(frozen=True)
class PropertyCase:
    id: str
    family: str
    family_id: str
    subfamily: str
    subfamily_id: str
    generator: CaseGenerator
    expected_solver: CaseSolver
    actual_solver: CaseSolver
    oracle_type: str
    sample_count: int = 5


def property_cases() -> list[PropertyCase]:
    return [
        PropertyCase(
            id="property_house_robber",
            family="动态规划",
            family_id="dynamic_programming",
            subfamily="House Robber",
            subfamily_id="house_robber",
            generator=_gen_house_robber,
            expected_solver=_house_robber_bruteforce,
            actual_solver=_house_robber_dp,
            oracle_type="bruteforce",
        ),
        PropertyCase(
            id="property_subset_sum",
            family="动态规划",
            family_id="dynamic_programming",
            subfamily="Subset Sum",
            subfamily_id="subset_sum",
            generator=_gen_subset_sum,
            expected_solver=_subset_sum_bruteforce,
            actual_solver=_subset_sum_dp,
            oracle_type="bruteforce",
        ),
        PropertyCase(
            id="property_lcs",
            family="动态规划",
            family_id="dynamic_programming",
            subfamily="LCS",
            subfamily_id="lcs",
            generator=_gen_two_strings,
            expected_solver=_lcs_bruteforce,
            actual_solver=_lcs_dp,
            oracle_type="bruteforce",
        ),
        PropertyCase(
            id="property_edit_distance",
            family="动态规划",
            family_id="dynamic_programming",
            subfamily="Edit Distance",
            subfamily_id="edit_distance",
            generator=_gen_two_strings,
            expected_solver=_edit_distance_bruteforce,
            actual_solver=_edit_distance_dp,
            oracle_type="bruteforce",
        ),
        PropertyCase(
            id="property_knapsack_01",
            family="动态规划",
            family_id="dynamic_programming",
            subfamily="0/1 Knapsack",
            subfamily_id="knapsack_01",
            generator=_gen_knapsack,
            expected_solver=_knapsack_bruteforce,
            actual_solver=_knapsack_dp,
            oracle_type="bruteforce",
        ),
        PropertyCase(
            id="property_bfs_layers",
            family="图",
            family_id="basic_graph",
            subfamily="BFS Layers",
            subfamily_id="bfs_layers",
            generator=_gen_unweighted_graph,
            expected_solver=_bfs_layers_by_path_enumeration,
            actual_solver=_bfs_layers_queue,
            oracle_type="independent_reference",
        ),
        PropertyCase(
            id="property_dfs_connected",
            family="图",
            family_id="basic_graph",
            subfamily="DFS Connected",
            subfamily_id="dfs_connected",
            generator=_gen_unweighted_graph,
            expected_solver=_connected_by_transitive_closure,
            actual_solver=_connected_by_dfs,
            oracle_type="independent_reference",
        ),
        PropertyCase(
            id="property_topological_sort",
            family="图",
            family_id="basic_graph",
            subfamily="Topological Sort",
            subfamily_id="topological_sort",
            generator=_gen_dag,
            expected_solver=_topological_rank_property,
            actual_solver=_topological_kahn_property,
            oracle_type="property",
        ),
        PropertyCase(
            id="property_dijkstra_positive",
            family="图",
            family_id="basic_graph",
            subfamily="Dijkstra Positive",
            subfamily_id="dijkstra_positive",
            generator=_gen_weighted_graph,
            expected_solver=_shortest_paths_bruteforce,
            actual_solver=_dijkstra_positive,
            oracle_type="bruteforce",
        ),
        PropertyCase(
            id="property_kmp",
            family="字符串",
            family_id="string_matching",
            subfamily="KMP",
            subfamily_id="kmp",
            generator=_gen_pattern_text,
            expected_solver=_string_find_direct,
            actual_solver=_kmp_search,
            oracle_type="independent_reference",
        ),
        PropertyCase(
            id="property_z_algorithm",
            family="字符串",
            family_id="string_matching",
            subfamily="Z Algorithm",
            subfamily_id="z_algorithm",
            generator=_gen_single_string,
            expected_solver=_z_naive,
            actual_solver=_z_linear,
            oracle_type="independent_reference",
        ),
        PropertyCase(
            id="property_manacher",
            family="字符串",
            family_id="string_matching",
            subfamily="Manacher",
            subfamily_id="manacher",
            generator=_gen_single_string,
            expected_solver=_longest_palindrome_naive,
            actual_solver=_manacher_longest_palindrome,
            oracle_type="independent_reference",
        ),
        PropertyCase(
            id="property_insertion_sort",
            family="排序",
            family_id="sorting",
            subfamily="Insertion Sort",
            subfamily_id="insertion_sort",
            generator=_gen_array,
            expected_solver=_sorted_builtin,
            actual_solver=_insertion_sort,
            oracle_type="property",
        ),
        PropertyCase(
            id="property_merge_sort",
            family="排序",
            family_id="sorting",
            subfamily="Merge Sort",
            subfamily_id="merge_sort",
            generator=_gen_array,
            expected_solver=_sorted_builtin,
            actual_solver=_merge_sort,
            oracle_type="property",
        ),
        PropertyCase(
            id="property_quickselect",
            family="排序",
            family_id="sorting",
            subfamily="Quickselect",
            subfamily_id="quickselect",
            generator=_gen_quickselect,
            expected_solver=_quickselect_expected,
            actual_solver=_quickselect_actual,
            oracle_type="property",
        ),
        PropertyCase(
            id="property_union_find_connectivity",
            family="并查集",
            family_id="union_find",
            subfamily="Union/Find Connectivity",
            subfamily_id="union_find_connectivity",
            generator=_gen_union_find_ops,
            expected_solver=_union_find_bruteforce_queries,
            actual_solver=_union_find_actual_queries,
            oracle_type="bruteforce",
        ),
        PropertyCase(
            id="property_range_sum_update",
            family="区间结构",
            family_id="range_structure",
            subfamily="Range Sum Query/Update",
            subfamily_id="range_sum_update",
            generator=_gen_range_ops,
            expected_solver=_range_ops_direct,
            actual_solver=_range_ops_fenwick,
            oracle_type="independent_reference",
        ),
    ]


def generate_property_samples(
    seed: int = DEFAULT_PROPERTY_SEED,
    sample_count: int | None = None,
    cases: list[PropertyCase] | None = None,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for case_index, case in enumerate(cases or property_cases()):
        count = sample_count if sample_count is not None else case.sample_count
        rng = random.Random(seed + case_index * 1009)
        for sample_index in range(count):
            input_data = case.generator(rng, sample_index)
            samples.append(
                {
                    "case": case,
                    "case_id": case.id,
                    "sample_index": sample_index,
                    "input": input_data,
                }
            )
    return samples


def _gen_house_robber(rng: random.Random, _index: int) -> JsonDict:
    return {"nums": [rng.randint(0, 12) for _ in range(rng.randint(0, 8))]}


def _house_robber_bruteforce(input_data: JsonDict) -> int:
    nums = input_data["nums"]
    best = 0
    for mask in range(1 << len(nums)):
        if mask & (mask << 1):
            continue
        best = max(best, sum(value for index, value in enumerate(nums) if mask & (1 << index)))
    return best


def _house_robber_dp(input_data: JsonDict) -> int:
    prev2 = 0
    prev1 = 0
    for value in input_data["nums"]:
        prev2, prev1 = prev1, max(prev1, prev2 + value)
    return prev1


def _gen_subset_sum(rng: random.Random, _index: int) -> JsonDict:
    nums = [rng.randint(0, 12) for _ in range(rng.randint(0, 8))]
    target = rng.randint(0, max(1, sum(nums) + 3))
    return {"nums": nums, "target": target}


def _subset_sum_bruteforce(input_data: JsonDict) -> bool:
    nums = input_data["nums"]
    target = input_data["target"]
    return any(sum(nums[index] for index in range(len(nums)) if mask & (1 << index)) == target for mask in range(1 << len(nums)))


def _subset_sum_dp(input_data: JsonDict) -> bool:
    reachable = {0}
    for value in input_data["nums"]:
        reachable |= {current + value for current in list(reachable)}
    return input_data["target"] in reachable


def _gen_two_strings(rng: random.Random, _index: int) -> JsonDict:
    alphabet = "abc"
    left = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 6)))
    right = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 6)))
    return {"a": left, "b": right}


def _lcs_bruteforce(input_data: JsonDict) -> int:
    a = input_data["a"]
    b = input_data["b"]
    best = 0
    for mask in range(1 << len(a)):
        candidate = "".join(a[index] for index in range(len(a)) if mask & (1 << index))
        if len(candidate) <= best:
            continue
        pos = 0
        for char in b:
            if pos < len(candidate) and candidate[pos] == char:
                pos += 1
        if pos == len(candidate):
            best = len(candidate)
    return best


def _lcs_dp(input_data: JsonDict) -> int:
    a = input_data["a"]
    b = input_data["b"]
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i, char_a in enumerate(a, 1):
        for j, char_b in enumerate(b, 1):
            if char_a == char_b:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def _edit_distance_bruteforce(input_data: JsonDict) -> int:
    from functools import lru_cache

    a = input_data["a"]
    b = input_data["b"]

    @lru_cache(maxsize=None)
    def distance(i: int, j: int) -> int:
        if i == len(a):
            return len(b) - j
        if j == len(b):
            return len(a) - i
        if a[i] == b[j]:
            return distance(i + 1, j + 1)
        return 1 + min(distance(i + 1, j), distance(i, j + 1), distance(i + 1, j + 1))

    return distance(0, 0)


def _edit_distance_dp(input_data: JsonDict) -> int:
    a = input_data["a"]
    b = input_data["b"]
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[-1][-1]


def _gen_knapsack(rng: random.Random, _index: int) -> JsonDict:
    item_count = rng.randint(0, 7)
    weights = [rng.randint(1, 8) for _ in range(item_count)]
    values = [rng.randint(0, 15) for _ in range(item_count)]
    capacity = rng.randint(0, 16)
    return {"weights": weights, "values": values, "capacity": capacity}


def _knapsack_bruteforce(input_data: JsonDict) -> int:
    weights = input_data["weights"]
    values = input_data["values"]
    capacity = input_data["capacity"]
    best = 0
    for mask in range(1 << len(weights)):
        weight = sum(weights[index] for index in range(len(weights)) if mask & (1 << index))
        if weight <= capacity:
            best = max(best, sum(values[index] for index in range(len(values)) if mask & (1 << index)))
    return best


def _knapsack_dp(input_data: JsonDict) -> int:
    capacity = input_data["capacity"]
    dp = [0] * (capacity + 1)
    for weight, value in zip(input_data["weights"], input_data["values"]):
        for current in range(capacity, weight - 1, -1):
            dp[current] = max(dp[current], dp[current - weight] + value)
    return max(dp) if dp else 0


def _gen_unweighted_graph(rng: random.Random, _index: int) -> JsonDict:
    n = rng.randint(1, 6)
    graph = {str(node): [] for node in range(n)}
    for i, j in combinations(range(n), 2):
        if rng.random() < 0.38:
            graph[str(i)].append(str(j))
            graph[str(j)].append(str(i))
    for neighbors in graph.values():
        neighbors.sort(key=int)
    return {"graph": graph, "start": str(rng.randrange(n))}


def _bfs_layers_by_path_enumeration(input_data: JsonDict) -> dict[str, int]:
    graph = input_data["graph"]
    start = input_data["start"]
    nodes = sorted(graph, key=int)
    best: dict[str, int] = {start: 0}
    frontier = {start}
    for distance in range(1, len(nodes) + 1):
        next_frontier = set()
        for node in frontier:
            next_frontier.update(neighbor for neighbor in graph.get(node, []) if neighbor not in best)
        for node in sorted(next_frontier, key=int):
            best.setdefault(node, distance)
        frontier = next_frontier
    return dict(sorted(best.items(), key=lambda item: int(item[0])))


def _bfs_layers_queue(input_data: JsonDict) -> dict[str, int]:
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph.get(node, []):
            if neighbor not in dist:
                dist[neighbor] = dist[node] + 1
                queue.append(neighbor)
    return dict(sorted(dist.items(), key=lambda item: int(item[0])))


def _connected_by_transitive_closure(input_data: JsonDict) -> list[str]:
    graph = input_data["graph"]
    start = input_data["start"]
    reachable = {start}
    changed = True
    while changed:
        changed = False
        for node in list(reachable):
            for neighbor in graph.get(node, []):
                if neighbor not in reachable:
                    reachable.add(neighbor)
                    changed = True
    return sorted(reachable, key=int)


def _connected_by_dfs(input_data: JsonDict) -> list[str]:
    graph = input_data["graph"]
    start = input_data["start"]
    seen = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(reversed(graph.get(node, [])))
    return sorted(seen, key=int)


def _gen_dag(rng: random.Random, _index: int) -> JsonDict:
    n = rng.randint(1, 6)
    order = list(range(n))
    rng.shuffle(order)
    position = {node: index for index, node in enumerate(order)}
    edges: list[list[str]] = []
    for i, j in combinations(range(n), 2):
        source, target = (i, j) if position[i] < position[j] else (j, i)
        if rng.random() < 0.42:
            edges.append([str(source), str(target)])
    return {"nodes": [str(node) for node in range(n)], "edges": edges}


def _topological_rank_property(input_data: JsonDict) -> dict[str, Any]:
    nodes = input_data["nodes"]
    edges = input_data["edges"]
    return {"node_count": len(nodes), "edges": edges, "valid": True}


def _topological_kahn_property(input_data: JsonDict) -> dict[str, Any]:
    nodes = input_data["nodes"]
    edges = input_data["edges"]
    graph = {node: [] for node in nodes}
    indegree = {node: 0 for node in nodes}
    for source, target in edges:
        graph[source].append(target)
        indegree[target] += 1
    queue = deque(sorted((node for node in nodes if indegree[node] == 0), key=int))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in sorted(graph[node], key=int):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    position = {node: index for index, node in enumerate(order)}
    return {
        "node_count": len(order),
        "edges": edges,
        "valid": len(order) == len(nodes) and all(position[source] < position[target] for source, target in edges),
    }


def _gen_weighted_graph(rng: random.Random, _index: int) -> JsonDict:
    n = rng.randint(1, 6)
    graph = {str(node): [] for node in range(n)}
    for i, j in combinations(range(n), 2):
        if rng.random() < 0.44:
            weight = rng.randint(1, 9)
            graph[str(i)].append([str(j), weight])
            graph[str(j)].append([str(i), weight])
    for edges in graph.values():
        edges.sort(key=lambda item: int(item[0]))
    return {"graph": graph, "start": str(rng.randrange(n))}


def _shortest_paths_bruteforce(input_data: JsonDict) -> dict[str, int]:
    graph = input_data["graph"]
    start = input_data["start"]
    nodes = sorted(graph, key=int)
    best = {node: float("inf") for node in nodes}
    best[start] = 0
    for _ in range(max(0, len(nodes) - 1)):
        changed = False
        for source in nodes:
            if best[source] == float("inf"):
                continue
            for target, weight in graph[source]:
                if best[source] + weight < best[target]:
                    best[target] = best[source] + weight
                    changed = True
        if not changed:
            break
    return {node: int(value) for node, value in best.items() if value != float("inf")}


def _dijkstra_positive(input_data: JsonDict) -> dict[str, int]:
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        distance, node = heapq.heappop(heap)
        if distance != dist[node]:
            continue
        for neighbor, weight in graph.get(node, []):
            candidate = distance + weight
            if candidate < dist.get(neighbor, 10**9):
                dist[neighbor] = candidate
                heapq.heappush(heap, (candidate, neighbor))
    return dict(sorted(dist.items(), key=lambda item: int(item[0])))


def _gen_pattern_text(rng: random.Random, _index: int) -> JsonDict:
    alphabet = "abca"
    text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9)))
    pattern = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 4)))
    return {"text": text, "pattern": pattern}


def _string_find_direct(input_data: JsonDict) -> int:
    return input_data["text"].find(input_data["pattern"])


def _kmp_search(input_data: JsonDict) -> int:
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        return 0
    pi = [0] * len(pattern)
    j = 0
    for i in range(1, len(pattern)):
        while j and pattern[i] != pattern[j]:
            j = pi[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
    j = 0
    for i, char in enumerate(text):
        while j and char != pattern[j]:
            j = pi[j - 1]
        if char == pattern[j]:
            j += 1
        if j == len(pattern):
            return i - len(pattern) + 1
    return -1


def _gen_single_string(rng: random.Random, _index: int) -> JsonDict:
    alphabet = "abac"
    return {"text": "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 10)))}


def _z_naive(input_data: JsonDict) -> list[int]:
    text = input_data["text"]
    z = [0] * len(text)
    for i in range(1, len(text)):
        while i + z[i] < len(text) and text[z[i]] == text[i + z[i]]:
            z[i] += 1
    return z


def _z_linear(input_data: JsonDict) -> list[int]:
    text = input_data["text"]
    z = [0] * len(text)
    left = 0
    right = 0
    for i in range(1, len(text)):
        if i <= right:
            z[i] = min(right - i + 1, z[i - left])
        while i + z[i] < len(text) and text[z[i]] == text[i + z[i]]:
            z[i] += 1
        if i + z[i] - 1 > right:
            left = i
            right = i + z[i] - 1
    return z


def _longest_palindrome_naive(input_data: JsonDict) -> int:
    text = input_data["text"]
    best = 0
    for left in range(len(text) + 1):
        for right in range(left, len(text) + 1):
            candidate = text[left:right]
            if candidate == candidate[::-1]:
                best = max(best, len(candidate))
    return best


def _manacher_longest_palindrome(input_data: JsonDict) -> int:
    text = input_data["text"]
    transformed = "^#" + "#".join(text) + "#$"
    radius = [0] * len(transformed)
    center = 0
    right = 0
    best = 0
    for i in range(1, len(transformed) - 1):
        mirror = 2 * center - i
        if i < right:
            radius[i] = min(right - i, radius[mirror])
        while transformed[i + 1 + radius[i]] == transformed[i - 1 - radius[i]]:
            radius[i] += 1
        if i + radius[i] > right:
            center = i
            right = i + radius[i]
        best = max(best, radius[i])
    return best


def _gen_array(rng: random.Random, _index: int) -> JsonDict:
    return {"nums": [rng.randint(-8, 12) for _ in range(rng.randint(0, 10))]}


def _sorted_builtin(input_data: JsonDict) -> list[int]:
    return sorted(input_data["nums"])


def _insertion_sort(input_data: JsonDict) -> list[int]:
    nums = list(input_data["nums"])
    for i in range(1, len(nums)):
        value = nums[i]
        j = i - 1
        while j >= 0 and nums[j] > value:
            nums[j + 1] = nums[j]
            j -= 1
        nums[j + 1] = value
    return nums


def _merge_sort(input_data: JsonDict) -> list[int]:
    def sort(values: list[int]) -> list[int]:
        if len(values) <= 1:
            return values
        mid = len(values) // 2
        left = sort(values[:mid])
        right = sort(values[mid:])
        merged: list[int] = []
        i = 0
        j = 0
        while i < len(left) or j < len(right):
            if j == len(right) or (i < len(left) and left[i] <= right[j]):
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        return merged

    return sort(list(input_data["nums"]))


def _gen_quickselect(rng: random.Random, _index: int) -> JsonDict:
    nums = [rng.randint(-10, 20) for _ in range(rng.randint(1, 10))]
    return {"nums": nums, "k": rng.randrange(len(nums))}


def _quickselect_expected(input_data: JsonDict) -> int:
    return sorted(input_data["nums"])[input_data["k"]]


def _quickselect_actual(input_data: JsonDict) -> int:
    nums = list(input_data["nums"])
    k = input_data["k"]
    left = 0
    right = len(nums) - 1
    while True:
        pivot = nums[(left + right) // 2]
        i = left
        j = right
        while i <= j:
            while nums[i] < pivot:
                i += 1
            while nums[j] > pivot:
                j -= 1
            if i <= j:
                nums[i], nums[j] = nums[j], nums[i]
                i += 1
                j -= 1
        if k <= j:
            right = j
        elif k >= i:
            left = i
        else:
            return nums[k]


def _gen_union_find_ops(rng: random.Random, _index: int) -> JsonDict:
    n = rng.randint(1, 7)
    ops: list[list[Any]] = []
    for _ in range(rng.randint(3, 12)):
        left = rng.randrange(n)
        right = rng.randrange(n)
        if rng.random() < 0.58:
            ops.append(["union", left, right])
        else:
            ops.append(["connected", left, right])
    return {"n": n, "ops": ops}


def _union_find_bruteforce_queries(input_data: JsonDict) -> list[bool]:
    components = [{node} for node in range(input_data["n"])]
    answers: list[bool] = []
    for op, left, right in input_data["ops"]:
        left_set = next(component for component in components if left in component)
        right_set = next(component for component in components if right in component)
        if op == "union":
            if left_set is not right_set:
                left_set |= right_set
                components.remove(right_set)
        elif op == "connected":
            answers.append(left_set is right_set)
        else:
            raise ValueError(f"unknown union-find op: {op}")
    return answers


def _union_find_actual_queries(input_data: JsonDict) -> list[bool]:
    parent = list(range(input_data["n"]))
    rank = [0] * input_data["n"]

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: int, right: int) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        if rank[root_left] < rank[root_right]:
            root_left, root_right = root_right, root_left
        parent[root_right] = root_left
        if rank[root_left] == rank[root_right]:
            rank[root_left] += 1

    answers: list[bool] = []
    for op, left, right in input_data["ops"]:
        if op == "union":
            union(left, right)
        elif op == "connected":
            answers.append(find(left) == find(right))
        else:
            raise ValueError(f"unknown union-find op: {op}")
    return answers


def _gen_range_ops(rng: random.Random, _index: int) -> JsonDict:
    nums = [rng.randint(-5, 10) for _ in range(rng.randint(1, 9))]
    ops: list[list[int | str]] = []
    for _ in range(rng.randint(4, 12)):
        if rng.random() < 0.55:
            left = rng.randrange(len(nums))
            right = rng.randrange(left, len(nums))
            ops.append(["query", left, right])
        else:
            pos = rng.randrange(len(nums))
            delta = rng.randint(-4, 5)
            ops.append(["update", pos, delta])
    return {"nums": nums, "ops": ops}


def _range_ops_direct(input_data: JsonDict) -> list[int]:
    nums = list(input_data["nums"])
    answers: list[int] = []
    for op in input_data["ops"]:
        if op[0] == "query":
            _kind, left, right = op
            answers.append(sum(nums[left : right + 1]))
        elif op[0] == "update":
            _kind, pos, delta = op
            nums[pos] += delta
        else:
            raise ValueError(f"unknown range op: {op[0]}")
    return answers


def _range_ops_fenwick(input_data: JsonDict) -> list[int]:
    nums = list(input_data["nums"])
    bit = [0] * (len(nums) + 1)

    def add(index: int, delta: int) -> None:
        index += 1
        while index < len(bit):
            bit[index] += delta
            index += index & -index

    def prefix(index: int) -> int:
        total = 0
        index += 1
        while index > 0:
            total += bit[index]
            index -= index & -index
        return total

    for index, value in enumerate(nums):
        add(index, value)
    answers: list[int] = []
    for op in input_data["ops"]:
        if op[0] == "query":
            _kind, left, right = op
            answers.append(prefix(right) - (prefix(left - 1) if left > 0 else 0))
        elif op[0] == "update":
            _kind, pos, delta = op
            nums[pos] += delta
            add(pos, delta)
        else:
            raise ValueError(f"unknown range op: {op[0]}")
    return answers
