"""Process-level validation for semantic traces.

These checks sit between schema validation and rendering. They do not try to
prove every algorithm, but they catch common inconsistencies in generated
traces: impossible set events, missing dependencies, and family-level invariant
violations for a small set of well-understood visual forms.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.process_families.array_pointer import (
    _looks_like_binary_search,
    _validate_array_pointer_contract,
    _validate_binary_search_key_step_coverage,
    _validate_binary_search_window,
)
from algolab.verification.process_families.common import (
    _run_error_only_checks,
    _validate_core_invariants,
)
from algolab.verification.process_families.contracts import _validate_family_trace_contract
from algolab.verification.process_families.dp import (
    _looks_like_house_robber,
    _looks_like_subset_sum,
    _looks_like_unique_paths,
    _validate_bounded_knapsack,
    _validate_complete_knapsack,
    _validate_digit_dp,
    _validate_dp_trace_contract,
    _validate_edit_distance_dp,
    _validate_house_robber_dp,
    _validate_interval_dp,
    _validate_lcs_dp,
    _validate_subset_sum_dp,
    _validate_unique_paths_dp,
)
from algolab.verification.process_families.graph import (
    _looks_like_bfs,
    _validate_bfs_distances,
    _validate_bfs_key_step_coverage,
    _validate_dijkstra_distances,
    _validate_graph_trace_contract,
    _validate_mst_edges,
    _validate_topological_order,
    _validate_union_find_forest,
)
from algolab.verification.process_families.hash_sort_linked_greedy import (
    _validate_greedy_process,
    _validate_hash_map_process,
    _validate_linked_list_process,
    _validate_sorting_process,
)
from algolab.verification.process_families.string import (
    _validate_kmp_prefix,
    _validate_manacher_radius,
    _validate_rabin_karp_hashes,
    _validate_string_sliding_window,
    _validate_trie_prefix_match,
    _validate_z_algorithm,
)
from algolab.verification.process_families.tree_range_math import (
    _looks_like_ml_training,
    _validate_articulation_bridges,
    _validate_backtracking_tree,
    _validate_bipartite_matching,
    _validate_bitmask_subset,
    _validate_bst_order,
    _validate_convex_hull,
    _validate_fast_power_table,
    _validate_fenwick_tree,
    _validate_flow_capacity,
    _validate_gcd_remainders,
    _validate_heap_property,
    _validate_lca_node,
    _validate_lowbit_decomposition,
    _validate_ml_correctness,
    _validate_monotonic_stack,
    _validate_monotonic_stack_key_step_coverage,
    _validate_pascal_combinations,
    _validate_recursion_frame_balance,
    _validate_segment_tree_sums,
    _validate_sieve_primes,
    _validate_sparse_table,
    _validate_tarjan_lowlink,
    _validate_tree_diameter,
    _validate_tree_max_independent_set,
    _validate_trie_prefix_count,
)


ProcessInvariantLevel = Literal["core", "structure", "algorithm", "all"]

CORE_LEVEL: ProcessInvariantLevel = "core"
STRUCTURE_LEVEL: ProcessInvariantLevel = "structure"
ALGORITHM_LEVEL: ProcessInvariantLevel = "algorithm"
ALL_LEVEL: ProcessInvariantLevel = "all"
DEFAULT_PROCESS_LEVELS: tuple[ProcessInvariantLevel, ...] = (CORE_LEVEL, STRUCTURE_LEVEL, ALGORITHM_LEVEL)
ProcessValidationStatus = Literal["strong", "fallback"]


@dataclass(frozen=True)
class ProcessFamilyRegistration:
    family: str
    label: str
    status: ProcessValidationStatus
    level: ProcessInvariantLevel
    coverage_rule: str
    failure_type: str
    checks: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


PROCESS_VALIDATION_REGISTRY: tuple[ProcessFamilyRegistration, ...] = (
    ProcessFamilyRegistration(
        family="dp",
        label="动态规划",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="显式 dp_contract + Tracer _trace_meta 覆盖率 + matcher-gated DP 转移；小 full-trace 样例要求逐格/逐状态转移",
        failure_type="process_invariant",
        checks=(
            "_validate_dp_trace_contract",
            "_validate_unique_paths_dp",
            "_validate_house_robber_dp",
            "_validate_subset_sum_dp",
            "_validate_lcs_dp",
            "_validate_edit_distance_dp",
            "_validate_complete_knapsack",
            "_validate_bounded_knapsack",
            "_validate_interval_dp",
            "_validate_digit_dp",
        ),
        aliases=("dp", "动态规划", "一维 dp", "二维 dp", "背包", "lcs", "编辑距离", "区间 dp", "数位 dp"),
    ),
    ProcessFamilyRegistration(
        family="bfs",
        label="BFS 图遍历",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="显式 graph_contract + 无权图 start + graph 输入触发 BFS/DFS/连通分量/拓扑/二分图基础不变量；小图要求关键访问步骤",
        failure_type="process_invariant",
        checks=("_validate_graph_trace_contract", "_validate_bfs_distances", "_validate_topological_order"),
        aliases=("bfs", "dfs", "宽度优先", "深度优先", "基础图", "图 bfs", "连通分量", "拓扑排序", "二分图染色"),
    ),
    ProcessFamilyRegistration(
        family="shortest_path_mst",
        label="最短路 / MST",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="显式 graph_contract + weighted_graph/edges/dist state 复核 Dijkstra、Bellman-Ford、Floyd、0-1 BFS relax 和 Kruskal MST 选边",
        failure_type="process_invariant",
        checks=(
            "_validate_graph_trace_contract",
            "_validate_dijkstra_distances",
            "_validate_mst_edges",
        ),
        aliases=(
            "shortest_path_mst",
            "shortest path",
            "最短路",
            "mst",
            "最小生成树",
            "dijkstra",
            "bellman-ford",
            "bellman ford",
            "floyd",
            "floyd-warshall",
            "0-1 bfs",
            "zero one bfs",
            "kruskal",
            "prim",
        ),
    ),
    ProcessFamilyRegistration(
        family="array_pointer",
        label="数组指针 / 窗口 / 前缀",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="显式 array_contract + 二分/双指针/滑窗/前缀和/差分/快慢指针状态连续性和递推校验",
        failure_type="process_invariant",
        checks=("_validate_array_pointer_contract", "_validate_binary_search_window"),
        aliases=("array pointer", "array_pointer", "数组指针", "滑动窗口", "前缀和", "差分", "双指针", "快慢指针"),
    ),
    ProcessFamilyRegistration(
        family="binary_search",
        label="二分",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="二分算法信号触发闭区间窗口边界检查；小输入要求比较 mid 和必要区间收缩",
        failure_type="process_invariant",
        checks=("_validate_binary_search_window",),
        aliases=("binary search", "binary_search", "二分", "二分查找", "二分答案"),
    ),
    ProcessFamilyRegistration(
        family="monotonic_stack",
        label="单调栈",
        status="strong",
        level=STRUCTURE_LEVEL,
        coverage_rule="state 声明 stack_order/monotonic 后检查栈值单调性；小输入要求 push / pop / answer_write",
        failure_type="process_invariant",
        checks=("_validate_monotonic_stack",),
        aliases=("monotonic stack", "monotonic_stack", "单调栈", "栈 / 队列 / 单调栈"),
    ),
    ProcessFamilyRegistration(
        family="hash",
        label="哈希表 / map",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="哈希 map state + hash_contract 复核 Two Sum 命中前写入顺序、need/complement、答案依赖和计数/集合可观测更新",
        failure_type="process_invariant",
        checks=("_validate_hash_map_process",),
        aliases=("hash", "哈希", "哈希表", "map", "集合"),
    ),
    ProcessFamilyRegistration(
        family="sorting",
        label="排序",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="sorting_contract + 数组 state 复核插入排序有序前缀、输入多重集保持和最终升序；复杂排序变体后续可分阶段接入",
        failure_type="process_invariant",
        checks=("_validate_sorting_process",),
        aliases=("sorting", "sort", "排序", "插入排序", "insertion sort", "merge sort", "quick sort", "quickselect"),
    ),
    ProcessFamilyRegistration(
        family="linked_list",
        label="链表与缓存",
        status="strong",
        level=STRUCTURE_LEVEL,
        coverage_rule="family_contract + linked_list nodes/edges/current/prev/next 复核链表指针重连连续性；LRU/LFU 缓存映射后续扩展",
        failure_type="process_invariant",
        checks=("_validate_family_trace_contract", "_validate_linked_list_process"),
        aliases=("linked list", "linked_list", "linkedlist", "链表", "链表与缓存", "reverse linked list", "lru", "lfu"),
    ),
    ProcessFamilyRegistration(
        family="greedy",
        label="贪心",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="greedy_contract 复核跳跃游戏 reach 局部最优转移、排序依据与选择状态；区间/Huffman 子模式后续扩展",
        failure_type="process_invariant",
        checks=("_validate_greedy_process",),
        aliases=("greedy", "贪心", "跳跃游戏", "jump game", "interval scheduling", "区间调度", "merge intervals", "huffman"),
    ),
    ProcessFamilyRegistration(
        family="string",
        label="字符串算法",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="显式 family_contract + KMP 前缀表、Rabin-Karp 滚动哈希、Z 数组、Manacher 半径表、字符串滑动窗口计数和 Trie 前缀路径按输入复核",
        failure_type="process_invariant",
        checks=(
            "_validate_family_trace_contract",
            "_validate_kmp_prefix",
            "_validate_rabin_karp_hashes",
            "_validate_z_algorithm",
            "_validate_manacher_radius",
            "_validate_string_sliding_window",
            "_validate_trie_prefix_match",
        ),
        aliases=(
            "string",
            "字符串",
            "字符串高级算法",
            "kmp",
            "rabin-karp",
            "rabin karp",
            "z algorithm",
            "manacher",
            "string sliding window",
            "字符串滑动窗口",
            "longest substring",
            "trie prefix match",
            "trie 前缀匹配",
        ),
    ),
    ProcessFamilyRegistration(
        family="tree",
        label="树 / BST / LCA",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="显式 family_contract + 递归 frame enter/exit 配对 + BST/LCA/树直径/树形 DP 等有明确 state 信号的子族触发强校验",
        failure_type="process_invariant",
        checks=(
            "_validate_family_trace_contract",
            "_validate_recursion_frame_balance",
            "_validate_bst_order",
            "_validate_lca_node",
            "_validate_tree_diameter",
            "_validate_tree_max_independent_set",
        ),
        aliases=("tree", "树", "bst", "lca", "二叉树", "树直径", "树形 dp", "tree dp"),
    ),
    ProcessFamilyRegistration(
        family="heap",
        label="堆 / TopK / Huffman",
        status="strong",
        level=STRUCTURE_LEVEL,
        coverage_rule="heap state + heap_type 复核小顶/大顶堆父子顺序，family_contract 约束 push/pop/heap[0] 证据",
        failure_type="process_invariant",
        checks=("_validate_family_trace_contract", "_validate_heap_property"),
        aliases=("heap", "堆", "priority queue", "topk", "top k", "huffman", "第 k 大"),
    ),
    ProcessFamilyRegistration(
        family="trie",
        label="Trie",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="trie nodes/edges/meta count 与 words/prefix 输入复核，family_contract 要求终止标记、字符路径和 prefix_count 证据",
        failure_type="process_invariant",
        checks=("_validate_family_trace_contract", "_validate_trie_prefix_count"),
        aliases=("trie", "前缀树", "prefix tree", "prefix_count", "前缀计数"),
    ),
    ProcessFamilyRegistration(
        family="backtracking",
        label="回溯 / 递归",
        status="strong",
        level=STRUCTURE_LEVEL,
        coverage_rule="recursion_tree/search_tree 结构 + frame enter/exit 配对 + path/used 连续性，阻塞跳层选择和撤销缺失",
        failure_type="process_invariant",
        checks=("_validate_family_trace_contract", "_validate_backtracking_tree", "_validate_recursion_frame_balance"),
        aliases=("backtracking", "回溯", "recursion", "递归", "permutation", "permutations", "全排列", "组合", "子集"),
    ),
    ProcessFamilyRegistration(
        family="range_structure",
        label="区间结构",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="线段树节点 meta、树状数组 bit 和稀疏表 st 按输入数组复核；query/update 路径由现有 target/deps 绑定",
        failure_type="process_invariant",
        checks=("_validate_segment_tree_sums", "_validate_fenwick_tree", "_validate_sparse_table"),
        aliases=("range structure", "range_structure", "区间结构", "线段树", "segment tree", "树状数组", "fenwick", "binary indexed tree", "稀疏表", "sparse table"),
    ),
    ProcessFamilyRegistration(
        family="geometry",
        label="几何 / 扫描线",
        status="strong",
        level=STRUCTURE_LEVEL,
        coverage_rule="geometry points/hull state 复核凸包点引用和一致转向；扫描线与线段相交子模式后续扩展",
        failure_type="process_invariant",
        checks=("_validate_convex_hull",),
        aliases=("geometry", "geometry_sweep", "几何", "几何 / 扫描线", "凸包", "convex hull", "orientation", "扫描线"),
    ),
    ProcessFamilyRegistration(
        family="math_bit",
        label="数学与位运算",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="Euclid 余数、快速幂平方表、筛法布尔表、组合数 DP 表、mask 位图和 lowbit 项按输入复核",
        failure_type="process_invariant",
        checks=(
            "_validate_gcd_remainders",
            "_validate_fast_power_table",
            "_validate_sieve_primes",
            "_validate_pascal_combinations",
            "_validate_bitmask_subset",
            "_validate_lowbit_decomposition",
        ),
        aliases=("math", "bit", "math_bit", "数学", "数学与位运算", "位运算", "gcd", "最大公约数", "快速幂", "筛法", "组合数", "位掩码", "lowbit"),
    ),
    ProcessFamilyRegistration(
        family="advanced_graph",
        label="图高级",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="显式 graph_contract + Tarjan dfn/low、桥/割点、二分图匹配和 Edmonds-Karp flow/capacity 按 state 复核",
        failure_type="process_invariant",
        checks=(
            "_validate_graph_trace_contract",
            "_validate_tarjan_lowlink",
            "_validate_articulation_bridges",
            "_validate_bipartite_matching",
            "_validate_flow_capacity",
        ),
        aliases=(
            "advanced graph",
            "advanced_graph",
            "图高级",
            "tarjan",
            "scc",
            "强连通分量",
            "割点",
            "桥",
            "二分图匹配",
            "matching",
            "edmonds-karp",
            "edmonds karp",
            "最大流",
            "网络流",
        ),
    ),
    ProcessFamilyRegistration(
        family="union_find",
        label="并查集",
        status="strong",
        level=STRUCTURE_LEVEL,
        coverage_rule="state.union_find/dsu.parent 触发 forest 指向与环检查；覆盖率仍由 Tracer _trace_meta 约束",
        failure_type="process_invariant",
        checks=("_validate_union_find_forest",),
        aliases=("union find", "union_find", "并查集", "dsu"),
    ),
)

_UNCOVERED_PROCESS_PROFILE = ProcessFamilyRegistration(
    family="uncovered",
    label="未覆盖算法族",
    status="fallback",
    level=CORE_LEVEL,
    coverage_rule="基础 schema / scene / answer gate；不声明算法族强过程不变量",
    failure_type="process_uncovered",
)
_EXPLICIT_PROCESS_FAILURE_TYPES = {
    "process_invariant",
    "coverage_error",
    "process_fallback",
    "process_uncovered",
}
_EXPLICIT_PROCESS_FAILURE_TYPES.update(profile.failure_type for profile in PROCESS_VALIDATION_REGISTRY)


def process_validation_registry() -> tuple[ProcessFamilyRegistration, ...]:
    return PROCESS_VALIDATION_REGISTRY


def process_validation_profile_for_family(family: str | None) -> ProcessFamilyRegistration:
    key = _normalize_family_name(family or "")
    if not key:
        return _UNCOVERED_PROCESS_PROFILE
    for profile in PROCESS_VALIDATION_REGISTRY:
        candidates = (profile.family, profile.label, *profile.aliases)
        if any(_family_alias_matches(key, candidate) for candidate in candidates):
            return profile
    return _UNCOVERED_PROCESS_PROFILE


def process_failure_type_for_message(message: str) -> str | None:
    text = message.lower()
    explicit = _explicit_failure_type(text)
    if explicit in _EXPLICIT_PROCESS_FAILURE_TYPES:
        return explicit
    if "trace coverage" in text or "coverage" in text or "覆盖率" in message or "缺少逐帧状态转移" in message:
        return "coverage_error"
    if "process_uncovered" in text or "未注册算法族" in message:
        return "process_uncovered"
    invariant_tokens = (
        "process",
        "invariant",
        "dp[",
        "dp contract",
        "graph contract",
        "family contract",
        "背包",
        "bfs",
        "dijkstra",
        "kmp",
        "rabin",
        "z algorithm",
        "manacher",
        "字符串滑动窗口",
        "window_counts",
        "trie 前缀匹配",
        "trie prefix_count",
        "prefix_count",
        "哈希",
        "sorting",
        "排序",
        "有序前缀",
        "链表",
        "linked_list",
        "greedy",
        "贪心",
        "jump_game",
        "reach",
        "frame:",
        "缺少 exit",
        "未进入",
        "回溯",
        "used",
        "path",
        "小顶堆",
        "大顶堆",
        "lca",
        "segment tree",
        "fenwick",
        "sparse table",
        "gcd",
        "lowbit",
        "快速幂",
        "筛法",
        "组合数",
        "位掩码",
        "线段树",
        "树状数组",
        "稀疏表",
        "tarjan",
        "union_find",
        "window_hashes",
        "回文半径",
        "monotonic",
        "单调",
        "并查集",
        "非根环",
        "二分",
        "收缩方向",
        "首次发现",
        "answer[",
        "bst",
        "low[",
        "bridge",
        "桥",
        "割点",
        "match[",
        "匹配",
        "flow[",
        "容量",
        "edmonds",
        "topo_order",
    )
    if any(token in text or token in message for token in invariant_tokens):
        return "process_invariant"
    return None


def _normalize_family_name(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _family_alias_matches(key: str, alias: str) -> bool:
    normalized = _normalize_family_name(alias)
    return bool(normalized) and (key == normalized or normalized in key)


def _explicit_failure_type(text: str) -> str | None:
    marker = "failure_type="
    if marker not in text:
        return None
    tail = text.split(marker, 1)[1]
    value = []
    for char in tail:
        if char.islower() or char == "_":
            value.append(char)
        else:
            break
    return "".join(value) or None



def validate_process(
    trace: SemanticTrace,
    levels: ProcessInvariantLevel | Iterable[ProcessInvariantLevel] | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    enabled_levels = _normalize_levels(levels)
    if CORE_LEVEL in enabled_levels:
        core_errors, core_warnings = _validate_core_invariants(trace)
        errors.extend(core_errors)
        warnings.extend(core_warnings)
    if STRUCTURE_LEVEL in enabled_levels:
        structure_errors, structure_warnings = _validate_structure_invariants(trace)
        errors.extend(structure_errors)
        warnings.extend(structure_warnings)
    if ALGORITHM_LEVEL in enabled_levels:
        algorithm_errors, algorithm_warnings = _validate_algorithm_invariants(trace)
        errors.extend(algorithm_errors)
        warnings.extend(algorithm_warnings)
    return errors, warnings


def _normalize_levels(levels: ProcessInvariantLevel | Iterable[ProcessInvariantLevel] | None) -> set[ProcessInvariantLevel]:
    if levels is None:
        return set(DEFAULT_PROCESS_LEVELS)
    requested = {levels} if isinstance(levels, str) else set(levels)
    if not requested:
        return set(DEFAULT_PROCESS_LEVELS)
    valid = set(DEFAULT_PROCESS_LEVELS)
    unknown = requested - valid - {ALL_LEVEL}
    if unknown:
        raise ValueError(f"未知 process invariant 层级：{', '.join(sorted(unknown))}")
    if ALL_LEVEL in requested:
        return set(DEFAULT_PROCESS_LEVELS)
    return requested


def _validate_structure_invariants(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors, warnings = _run_error_only_checks(
        trace,
        [
            _validate_heap_property,
            _validate_monotonic_stack,
            _validate_monotonic_stack_key_step_coverage,
            _validate_union_find_forest,
            _validate_topological_order,
            _validate_bst_order,
            _validate_mst_edges,
            _validate_convex_hull,
            _validate_backtracking_tree,
            _validate_recursion_frame_balance,
        ],
    )
    return errors, warnings


def _validate_algorithm_invariants(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(_validate_array_pointer_contract(trace))
    errors.extend(_validate_dp_trace_contract(trace))
    errors.extend(_validate_graph_trace_contract(trace))
    errors.extend(_validate_family_trace_contract(trace))
    if _looks_like_unique_paths(trace):
        errors.extend(_validate_unique_paths_dp(trace))
    if _looks_like_house_robber(trace):
        errors.extend(_validate_house_robber_dp(trace))
    if _looks_like_subset_sum(trace):
        errors.extend(_validate_subset_sum_dp(trace))
    if _looks_like_bfs(trace):
        errors.extend(_validate_bfs_distances(trace))
        errors.extend(_validate_bfs_key_step_coverage(trace))
    if _looks_like_binary_search(trace):
        errors.extend(_validate_binary_search_window(trace))
        errors.extend(_validate_binary_search_key_step_coverage(trace))
    if _looks_like_ml_training(trace):
        errors.extend(_validate_ml_correctness(trace))
    family_errors, family_warnings = _run_error_only_checks(
        trace,
        [
            _validate_dijkstra_distances,
            _validate_lcs_dp,
            _validate_edit_distance_dp,
            _validate_kmp_prefix,
            _validate_rabin_karp_hashes,
            _validate_z_algorithm,
            _validate_manacher_radius,
            _validate_string_sliding_window,
            _validate_trie_prefix_match,
            _validate_complete_knapsack,
            _validate_bounded_knapsack,
            _validate_interval_dp,
            _validate_digit_dp,
            _validate_lca_node,
            _validate_tree_diameter,
            _validate_tree_max_independent_set,
            _validate_trie_prefix_count,
            _validate_hash_map_process,
            _validate_sorting_process,
            _validate_linked_list_process,
            _validate_greedy_process,
            _validate_convex_hull,
            _validate_segment_tree_sums,
            _validate_fenwick_tree,
            _validate_sparse_table,
            _validate_gcd_remainders,
            _validate_fast_power_table,
            _validate_sieve_primes,
            _validate_pascal_combinations,
            _validate_bitmask_subset,
            _validate_lowbit_decomposition,
            _validate_tarjan_lowlink,
            _validate_articulation_bridges,
            _validate_bipartite_matching,
            _validate_flow_capacity,
        ],
    )
    errors.extend(family_errors)
    warnings.extend(family_warnings)
    return errors, warnings
