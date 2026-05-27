"""Process-level validation for semantic traces.

These checks sit between schema validation and rendering. They do not try to
prove every algorithm, but they catch common inconsistencies in generated
traces: impossible set events, missing dependencies, and family-level invariant
violations for a small set of well-understood visual forms.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Literal

from algolab.compiler.target_parser import parse_target
from algolab.schemas.semantic_trace import SemanticOp, SemanticTrace


ProcessInvariantLevel = Literal["core", "structure", "algorithm", "all"]

CORE_LEVEL: ProcessInvariantLevel = "core"
STRUCTURE_LEVEL: ProcessInvariantLevel = "structure"
ALGORITHM_LEVEL: ProcessInvariantLevel = "algorithm"
ALL_LEVEL: ProcessInvariantLevel = "all"
DEFAULT_PROCESS_LEVELS: tuple[ProcessInvariantLevel, ...] = (CORE_LEVEL, STRUCTURE_LEVEL, ALGORITHM_LEVEL)
FULL_DP_TRACE_CELL_LIMIT = 80
SMALL_BFS_NODE_LIMIT = 20
SMALL_BFS_EDGE_LIMIT = 80
SMALL_BINARY_SEARCH_INPUT_LIMIT = 64
SMALL_MONOTONIC_STACK_INPUT_LIMIT = 64
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
        coverage_rule="Tracer _trace_meta 覆盖率 + matcher-gated DP 转移；小 unique_paths 表要求逐格转移",
        failure_type="process_invariant",
        checks=(
            "_validate_unique_paths_dp",
            "_validate_house_robber_dp",
            "_validate_subset_sum_dp",
            "_validate_lcs_dp",
            "_validate_edit_distance_dp",
            "_validate_complete_knapsack",
            "_validate_interval_dp",
        ),
        aliases=("dp", "动态规划", "一维 dp", "二维 dp", "背包", "lcs", "编辑距离", "区间 dp"),
    ),
    ProcessFamilyRegistration(
        family="bfs",
        label="BFS 图遍历",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="无权图 start + graph 输入触发 BFS 距离不变量；小图要求出队、检查边、首次访问",
        failure_type="process_invariant",
        checks=("_validate_bfs_distances",),
        aliases=("bfs", "宽度优先", "基础图", "图 bfs"),
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
        status="fallback",
        level=CORE_LEVEL,
        coverage_rule="基础 schema / scene / answer gate + 可观测过程证据；暂不声明哈希族强过程不变量",
        failure_type="process_fallback",
        aliases=("hash", "哈希", "哈希表", "map", "集合"),
    ),
    ProcessFamilyRegistration(
        family="string",
        label="字符串算法",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="KMP 前缀表、Rabin-Karp 滚动哈希、Z 数组和 Manacher 半径表按输入字符串复核",
        failure_type="process_invariant",
        checks=(
            "_validate_kmp_prefix",
            "_validate_rabin_karp_hashes",
            "_validate_z_algorithm",
            "_validate_manacher_radius",
        ),
        aliases=("string", "字符串", "字符串高级算法", "kmp", "rabin-karp", "rabin karp", "z algorithm", "manacher"),
    ),
    ProcessFamilyRegistration(
        family="tree",
        label="树 / BST / LCA",
        status="strong",
        level=ALGORITHM_LEVEL,
        coverage_rule="BST/LCA/树直径/树形 DP 等有明确 state 信号的子族触发强校验；普通树遍历仍依赖基础门禁",
        failure_type="process_invariant",
        checks=("_validate_bst_order", "_validate_lca_node", "_validate_tree_diameter", "_validate_tree_max_independent_set"),
        aliases=("tree", "树", "bst", "lca", "二叉树", "树直径", "树形 dp", "tree dp"),
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
        coverage_rule="Tarjan dfn/low、桥/割点、二分图匹配和 Edmonds-Karp flow/capacity 按 state 复核",
        failure_type="process_invariant",
        checks=(
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
        "背包",
        "bfs",
        "dijkstra",
        "kmp",
        "rabin",
        "z algorithm",
        "manacher",
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


def _validate_core_invariants(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(_validate_trace_meta_coverage(trace))
    errors.extend(_validate_observable_process_evidence(trace))
    replay_errors, replay_warnings = _validate_set_replay(trace)
    errors.extend(replay_errors)
    warnings.extend(replay_warnings)
    warnings.extend(_validate_dependency_presence(trace))
    warnings.extend(_validate_reason_grounding(trace))
    return errors, warnings


def _validate_trace_meta_coverage(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        meta = (event.state or {}).get("_trace_meta")
        if not isinstance(meta, dict):
            continue
        sampled = meta.get("sampled") is True
        if sampled:
            continue
        coverage = _recompute_trace_meta_coverage(trace, meta)
        for name, value in coverage.items():
            if value < 1.0:
                errors.append(f"第 {event.step} 步 trace coverage {name} 不足：{value}")
    return errors


def _recompute_trace_meta_coverage(trace: SemanticTrace, meta: dict[str, Any]) -> dict[str, float]:
    expected_updates = meta.get("expected_updates")
    if not isinstance(expected_updates, dict):
        return {}
    recorded_updates = _count_recorded_updates(trace)
    coverage: dict[str, float] = {}
    for raw_name, raw_expected in expected_updates.items():
        if not isinstance(raw_expected, int):
            continue
        name = str(raw_name)
        recorded = recorded_updates.get(name, 0)
        coverage[name] = 1.0 if raw_expected == 0 else round(recorded / raw_expected, 6)
    return coverage


def _count_recorded_updates(trace: SemanticTrace) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in trace.events:
        if event.op not in {SemanticOp.SET, SemanticOp.MARK, SemanticOp.MOVE, SemanticOp.PUSH, SemanticOp.POP}:
            continue
        for target in event.targets:
            name = _coverage_name_for_target(target.id)
            counts[name] = counts.get(name, 0) + 1
    return counts


def _coverage_name_for_target(target_id: str) -> str:
    if target_id.startswith("pointer:"):
        return target_id
    return target_id.split("[", 1)[0]


def _validate_observable_process_evidence(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    previous_state: dict[str, Any] | None = None
    for event in trace.events:
        state = event.state or {}
        if event.op in {SemanticOp.SET, SemanticOp.MOVE, SemanticOp.PUSH, SemanticOp.POP, SemanticOp.MARK, SemanticOp.LINK, SemanticOp.UNLINK}:
            if not event.targets:
                errors.append(f"第 {event.step} 步 {event.op.value} 缺少 targets，无法核对过程动作")
            if not _event_has_observable_evidence(event, previous_state, state):
                errors.append(f"第 {event.step} 步 {event.op.value} 缺少可观测过程证据：需要 deps、before/after/value 或可解析的状态变化")
        if event.op == SemanticOp.COMPARE and len(event.targets) < 2 and not event.deps and not _has_explicit_aux_value(event.value):
            errors.append(f"第 {event.step} 步 compare 缺少 deps/value，无法说明比较依据")
        previous_state = state
    return errors


def _event_has_observable_evidence(event, previous_state: dict[str, Any] | None, state: dict[str, Any]) -> bool:
    if event.op in {SemanticOp.MARK, SemanticOp.UNMARK} and event.role:
        return True
    if event.deps or _has_explicit_aux_value(event.value) or _has_explicit_aux_value(event.before) or _has_explicit_aux_value(event.after):
        return True
    if previous_state is None:
        return bool(state)
    if _state_changed(previous_state, state):
        return True
    return any(_target_changed(target.id, previous_state, state) for target in event.targets)


def _event_ref_ids(refs: Iterable[Any]) -> set[str]:
    return {ref.id for ref in refs if getattr(ref, "id", "")}


def _state_changed(previous_state: dict[str, Any], state: dict[str, Any]) -> bool:
    keys = set(previous_state) | set(state)
    return any(not _same_value(previous_state.get(key), state.get(key)) for key in keys)


def _target_changed(target_id: str, previous_state: dict[str, Any], state: dict[str, Any]) -> bool:
    before = _resolve_target(previous_state, target_id)
    after = _resolve_target(state, target_id)
    if not before.exists and not after.exists:
        return False
    return not _same_value(before.value, after.value)


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
        ],
    )
    return errors, warnings


def _validate_algorithm_invariants(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
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
            _validate_complete_knapsack,
            _validate_interval_dp,
            _validate_lca_node,
            _validate_tree_diameter,
            _validate_tree_max_independent_set,
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


def _run_error_only_checks(
    trace: SemanticTrace,
    checks: Iterable[Callable[[SemanticTrace], list[str]]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    for check in checks:
        errors.extend(check(trace))
    return errors, []


def _validate_set_replay(trace: SemanticTrace) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    previous_state: dict[str, Any] | None = None
    for event in trace.events:
        state = event.state or {}
        if event.op != SemanticOp.SET or not event.targets:
            previous_state = state
            continue

        target_values = [_single_target_aux_value(event.before, event.targets, index) for index, _target in enumerate(event.targets)]
        after_values = [_single_target_aux_value(event.after, event.targets, index) for index, _target in enumerate(event.targets)]
        for index, target in enumerate(event.targets):
            if _has_explicit_aux_value(event.after):
                resolved_after = _resolve_target(state, target.id)
                expected_after = after_values[index]
                if resolved_after.exists and _has_explicit_aux_value(expected_after) and not _same_value(resolved_after.value, expected_after):
                    warnings.append(f"第 {event.step} 步 after 与 state 不一致：{target.id}")
            if previous_state is not None and _has_explicit_aux_value(event.before):
                resolved_before = _resolve_target(previous_state, target.id)
                expected_before = target_values[index]
                if resolved_before.exists and _has_explicit_aux_value(expected_before) and not _same_value(resolved_before.value, expected_before):
                    warnings.append(f"第 {event.step} 步 before 与上一状态不一致：{target.id}")
        previous_state = state
    return errors, warnings


def _single_target_aux_value(value: Any, targets: list[Any], index: int) -> Any:
    if isinstance(value, list) and len(value) == len(targets):
        return value[index]
    if len(targets) == 1:
        return value
    return None


def _has_explicit_aux_value(value: Any) -> bool:
    return value is not None and value != ""


def _same_value(left: Any, right: Any) -> bool:
    import json

    try:
        return json.dumps(left, ensure_ascii=False, sort_keys=True) == json.dumps(right, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return left == right


def _validate_dependency_presence(trace: SemanticTrace) -> list[str]:
    warnings: list[str] = []
    for event in trace.events:
        state = event.state or {}
        for dep in event.deps:
            resolved = _resolve_target(state, dep.id)
            parsed = parse_target(dep.id)
            if not resolved.exists and parsed.kind not in {"node", "edge", "pointer"} and not _is_map_container_ref(parsed, state):
                warnings.append(f"第 {event.step} 步 deps 未出现在 state 中：{dep.id}")
    return warnings


def _is_map_container_ref(parsed, state: dict[str, Any]) -> bool:
    if parsed.kind != "map":
        return False
    key, _, item = parsed.name.partition(":")
    if key == "map" and item in state and isinstance(state.get(item), dict):
        return True
    return parsed.name in state and isinstance(state.get(parsed.name), dict)


def _validate_reason_grounding(trace: SemanticTrace) -> list[str]:
    warnings: list[str] = []
    for event in trace.events:
        reason = event.reason or ""
        if not reason:
            continue
        refs = {ref.id for ref in [*event.targets, *event.deps]}
        refs.update((event.state or {}).keys())
        for key in ("dp", "nums", "queue", "stack", "graph", "text", "pattern", "heap"):
            if key in reason and not any(ref == key or ref.startswith(f"{key}[") for ref in refs):
                warnings.append(f"第 {event.step} 步 reason 提到 {key}，但 targets/deps/state 缺少对应依据")
    return warnings


class Resolved:
    def __init__(self, exists: bool, value: Any = None):
        self.exists = exists
        self.value = value


def _resolve_target(state: dict[str, Any], target_id: str) -> Resolved:
    parsed = parse_target(target_id)
    if parsed.kind == "indexed":
        value = state.get(parsed.name)
        try:
            for idx in parsed.indices:
                value = value[idx]
            return Resolved(True, value)
        except Exception:
            return Resolved(False)
    if parsed.kind == "slice":
        value = state.get(parsed.name)
        start, end = parsed.indices
        if isinstance(value, (list, str)) and 0 <= start <= end <= len(value):
            return Resolved(True, value[start:end])
        return Resolved(False)
    if parsed.kind == "map":
        name = parsed.name
        key, _, item = name.partition(":")
        data = state.get(key)
        if isinstance(data, dict) and item in data:
            return Resolved(True, data[item])
        if isinstance(data, dict):
            for existing_key, existing_value in data.items():
                if str(existing_key) == item:
                    return Resolved(True, existing_value)
        if target_id in state:
            return Resolved(True, state[target_id])
        return Resolved(False)
    if target_id in state:
        return Resolved(True, state[target_id])
    return Resolved(False)


def _dict_lookup(data: dict[Any, Any], key: Any) -> Any:
    if key in data:
        return data[key]
    key_text = str(key)
    for existing_key, value in data.items():
        if str(existing_key) == key_text:
            return value
    return None


def _same_node(left: Any, right: Any) -> bool:
    return str(left) == str(right)


def _node_display(node: Any) -> str:
    return str(node)


def _looks_like_unique_paths(trace: SemanticTrace) -> bool:
    if not isinstance(trace.input_data, dict):
        return False
    return {"m", "n"}.issubset(trace.input_data) and any("dp" in (event.state or {}) for event in trace.events)


def _validate_unique_paths_dp(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    m, n = trace.input_data.get("m"), trace.input_data.get("n")
    if not isinstance(m, int) or not isinstance(n, int) or m <= 0 or n <= 0:
        return errors
    observed_set_cells: set[tuple[int, int]] = set()
    for event in trace.events:
        dp = (event.state or {}).get("dp")
        if not _is_matrix(dp):
            continue
        if len(dp) != m or any(len(row) != n for row in dp):
            errors.append(f"第 {event.step} 步 unique_paths dp 维度不匹配")
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "dp" or len(parsed.indices) != 2:
                continue
            i, j = parsed.indices
            if not (0 <= i < m and 0 <= j < n):
                continue
            observed_set_cells.add((i, j))
            expected = 1 if i == 0 or j == 0 else dp[i - 1][j] + dp[i][j - 1]
            value = dp[i][j]
            if isinstance(value, int) and value != expected:
                errors.append(f"第 {event.step} 步 dp[{i}][{j}] 不满足不同路径转移")
            if i > 0 and j > 0:
                expected_deps = {f"dp[{i - 1}][{j}]", f"dp[{i}][{j - 1}]"}
                actual_deps = _event_ref_ids(event.deps)
                if not expected_deps <= actual_deps:
                    errors.append(f"第 {event.step} 步 dp[{i}][{j}] 依赖应为 {', '.join(sorted(expected_deps))}")
    interior_cells = {(i, j) for i in range(1, m) for j in range(1, n)}
    if 0 < len(interior_cells) <= FULL_DP_TRACE_CELL_LIMIT:
        missing = sorted(interior_cells - observed_set_cells)
        if missing:
            preview = ", ".join(f"dp[{i}][{j}]" for i, j in missing[:6])
            suffix = "..." if len(missing) > 6 else ""
            errors.append(f"不同路径小 DP 表缺少逐帧状态转移：{preview}{suffix}")
    return errors


def _looks_like_house_robber(trace: SemanticTrace) -> bool:
    if not isinstance(trace.input_data, dict):
        return False
    return isinstance(trace.input_data.get("nums"), list) and any("dp" in (event.state or {}) for event in trace.events)


def _looks_like_subset_sum(trace: SemanticTrace) -> bool:
    if not isinstance(trace.input_data, dict):
        return False
    nums = trace.input_data.get("nums")
    if not isinstance(nums, list) or not all(isinstance(x, int) and x > 0 for x in nums):
        return False
    for event in trace.events:
        state = event.state or {}
        dp = state.get("dp")
        target = state.get("target")
        if isinstance(dp, list) and isinstance(target, int) and len(dp) == target + 1 and all(isinstance(x, bool) for x in dp):
            return True
    return False


def _validate_subset_sum_dp(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    nums = trace.input_data.get("nums")
    if not isinstance(nums, list):
        return errors
    total = sum(nums)
    if total % 2 == 1:
        return errors
    target = total // 2
    for event in trace.events:
        state = event.state or {}
        dp = state.get("dp")
        if not isinstance(dp, list) or len(dp) != target + 1 or not all(isinstance(x, bool) for x in dp):
            continue
        if dp[0] is not True:
            errors.append(f"第 {event.step} 步 subset-sum dp[0] 必须为 True")
        if event.op != SemanticOp.SET:
            continue
        prefix_len = _subset_prefix_len(state)
        reachable = _subset_reachable(nums[:prefix_len], target)
        for target_ref in event.targets:
            parsed = parse_target(target_ref.id)
            if parsed.kind != "indexed" or parsed.name != "dp" or len(parsed.indices) != 1:
                continue
            j = parsed.indices[0]
            if 0 <= j <= target and dp[j] != reachable[j]:
                errors.append(f"第 {event.step} 步 dp[{j}] 不满足 0-1 背包可达性")
    return errors


def _subset_prefix_len(state: dict[str, Any]) -> int:
    i = state.get("i")
    if isinstance(i, int):
        return max(0, i + 1)
    processed = state.get("processed")
    if isinstance(processed, int):
        return max(0, processed)
    return 0


def _subset_reachable(nums: list[int], target: int) -> list[bool]:
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:
        for j in range(target, num - 1, -1):
            dp[j] = dp[j] or dp[j - num]
    return dp


def _validate_house_robber_dp(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    nums = trace.input_data.get("nums")
    if not isinstance(nums, list) or not all(isinstance(x, int) for x in nums):
        return errors
    for event in trace.events:
        dp = (event.state or {}).get("dp")
        if not isinstance(dp, list) or len(dp) != len(nums):
            continue
        for i, value in enumerate(dp):
            if not isinstance(value, int):
                continue
            if i == 0:
                expected = nums[0] if nums else 0
            elif i == 1:
                expected = max(nums[0], nums[1])
            else:
                expected = max(dp[i - 1], dp[i - 2] + nums[i]) if isinstance(dp[i - 1], int) and isinstance(dp[i - 2], int) else value
            if value not in {0, expected}:
                errors.append(f"第 {event.step} 步 dp[{i}] 不满足打家劫舍转移")
    return errors


def _looks_like_bfs(trace: SemanticTrace) -> bool:
    if not isinstance(trace.input_data, dict):
        return False
    graph = trace.input_data.get("graph")
    return (
        isinstance(graph, dict)
        and "start" in trace.input_data
        and all(isinstance(neighbors, list) and all(not isinstance(nei, (list, tuple, dict)) for nei in neighbors) for neighbors in graph.values())
    )


def _validate_bfs_distances(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    graph = trace.input_data.get("graph")
    start = trace.input_data.get("start")
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
    start = trace.input_data.get("start")
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


def _event_target_ids(event) -> set[str]:
    return _event_ref_ids(event.targets)


def _event_dep_ids(event) -> set[str]:
    return _event_ref_ids(event.deps)


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


def _looks_like_binary_search(trace: SemanticTrace) -> bool:
    if not isinstance(trace.input_data, dict):
        return False
    if not isinstance(trace.input_data.get("nums"), list) or "target" not in trace.input_data:
        return False
    algorithm = (trace.algorithm or "").lower()
    if "二分" in trace.algorithm or "binary" in algorithm or "bisect" in algorithm:
        return True
    for event in trace.events:
        state = event.state or {}
        if {"left", "right", "mid"} <= set(state):
            return True
        refs = _event_target_ids(event) | _event_dep_ids(event)
        if refs & {"pointer:left", "pointer:right", "pointer:mid"}:
            return True
    return False


def _validate_binary_search_window(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    nums = trace.input_data.get("nums")
    target = trace.input_data.get("target")
    if not isinstance(nums, list):
        return errors
    last_compare: dict[str, Any] | None = None
    for event in trace.events:
        state = event.state or {}
        left, right, mid = state.get("left"), state.get("right"), state.get("mid")
        if isinstance(left, int) and not (0 <= left <= len(nums)):
            errors.append(f"第 {event.step} 步 left 越界")
        if isinstance(right, int) and not (-1 <= right < len(nums)):
            errors.append(f"第 {event.step} 步 right 越界")
        if isinstance(left, int) and isinstance(right, int) and left <= right and isinstance(mid, int):
            if not (left <= mid <= right):
                errors.append(f"第 {event.step} 步 mid 不在 [left,right] 内")
        if event.op == SemanticOp.COMPARE and isinstance(left, int) and isinstance(right, int) and isinstance(mid, int) and 0 <= mid < len(nums):
            last_compare = {"left": left, "right": right, "mid": mid, "mid_value": nums[mid]}
            continue
        if event.op == SemanticOp.MOVE and last_compare is not None:
            errors.extend(_validate_binary_search_shrink(event.step, state, target, last_compare))
            last_compare = None
    return errors


def _validate_binary_search_key_step_coverage(trace: SemanticTrace) -> list[str]:
    nums = trace.input_data.get("nums")
    target = trace.input_data.get("target")
    if not isinstance(nums, list) or len(nums) > SMALL_BINARY_SEARCH_INPUT_LIMIT:
        return []
    if not nums:
        return []
    compare_events = [_binary_search_compare_event(event, nums) for event in trace.events]
    compare_events = [event for event in compare_events if event is not None]
    missing: list[str] = []
    if not compare_events:
        missing.append("compare_mid")
    if _binary_search_requires_shrink(nums, target) and not _trace_has_binary_search_shrink(trace):
        missing.append("shrink_interval")
    if missing:
        return [f"failure_type=coverage_error: 二分缺少关键步骤覆盖：{', '.join(missing)}"]
    return []


def _binary_search_compare_event(event, nums: list[Any]) -> Any | None:
    if event.op != SemanticOp.COMPARE:
        return None
    state = event.state or {}
    mid = state.get("mid")
    if not isinstance(mid, int) or not (0 <= mid < len(nums)):
        return None
    refs = _event_target_ids(event) | _event_dep_ids(event)
    if f"nums[{mid}]" in refs or "pointer:mid" in refs:
        return event
    return None


def _binary_search_requires_shrink(nums: list[Any], target: Any) -> bool:
    left, right = 0, len(nums) - 1
    if left > right:
        return False
    mid = (left + right) // 2
    if nums[mid] == target:
        return False
    return left < right


def _trace_has_binary_search_shrink(trace: SemanticTrace) -> bool:
    for event in trace.events:
        if event.op != SemanticOp.MOVE:
            continue
        refs = _event_target_ids(event) | _event_dep_ids(event)
        state = event.state or {}
        if ("pointer:left" in refs or "pointer:right" in refs) and (
            isinstance(state.get("left"), int) or isinstance(state.get("right"), int)
        ):
            return True
    return False


def _validate_binary_search_shrink(step: int, state: dict[str, Any], target: Any, last_compare: dict[str, Any]) -> list[str]:
    if not isinstance(target, (int, float)):
        return []
    new_left, new_right = state.get("left"), state.get("right")
    if not isinstance(new_left, int) or not isinstance(new_right, int):
        return []
    old_left = last_compare["left"]
    old_right = last_compare["right"]
    mid = last_compare["mid"]
    mid_value = last_compare["mid_value"]
    if not isinstance(mid_value, (int, float)) or mid_value == target:
        return []
    if mid_value < target:
        if new_left <= mid or new_right != old_right:
            return [f"第 {step} 步 二分收缩方向错误：nums[{mid}] < target 时应移动 left 到 {mid + 1}"]
    if mid_value > target:
        if new_right >= mid or new_left != old_left:
            return [f"第 {step} 步 二分收缩方向错误：nums[{mid}] > target 时应移动 right 到 {mid - 1}"]
    return []


def _looks_like_ml_training(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if any(token in algorithm for token in ("regression", "linear", "logistic", "gradient", "loss", "机器学习", "回归", "梯度", "训练")):
        return True
    for event in trace.events:
        if _extract_ml_state(event.state or {}) is not None:
            return True
    return False


def _validate_ml_correctness(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        ml_state = _extract_ml_state(event.state or {})
        if ml_state is None:
            continue
        tolerance = _ml_tolerance(ml_state)
        errors.extend(_validate_ml_random_seed(event.step, ml_state))
        errors.extend(_validate_ml_loss_curve(event.step, ml_state, tolerance))
        errors.extend(_validate_ml_linear_regression_step(event.step, ml_state, tolerance))
        errors.extend(_validate_ml_parameter_update(event.step, ml_state, tolerance))
    return errors


def _extract_ml_state(state: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("training", "model", "ml", "linear_regression", "logistic_regression"):
        value = state.get(key)
        if isinstance(value, dict) and _dict_has_ml_signal(value):
            return value
    if _dict_has_ml_signal(state):
        return state
    return None


def _dict_has_ml_signal(value: dict[str, Any]) -> bool:
    return any(
        key in value
        for key in (
            "features",
            "x",
            "X",
            "labels",
            "y",
            "parameters",
            "parameters_before",
            "parameters_after",
            "weights",
            "gradient",
            "gradients",
            "loss",
            "loss_curve",
            "epoch",
            "learning_rate",
            "prediction",
            "predictions",
            "decision_boundary",
            "batch",
        )
    )


def _ml_tolerance(state: dict[str, Any]) -> float:
    raw = state.get("tolerance")
    if raw is None:
        meta = state.get("ml") if isinstance(state.get("ml"), dict) else state.get("meta")
        raw = meta.get("tolerance") if isinstance(meta, dict) else None
    if isinstance(raw, (int, float)) and math.isfinite(float(raw)) and raw >= 0:
        return float(raw)
    return 1e-6


def _validate_ml_random_seed(step: int, state: dict[str, Any]) -> list[str]:
    if not _ml_uses_randomness(state):
        return []
    if _has_seed(state):
        return []
    return [f"第 {step} 步 ML 随机训练声明缺少固定 seed"]


def _ml_uses_randomness(state: dict[str, Any]) -> bool:
    random_flags = (
        state.get("randomized"),
        state.get("shuffle"),
        state.get("sample_randomly"),
        state.get("random_sampling"),
        state.get("stochastic"),
    )
    if any(flag is True for flag in random_flags):
        return True
    batch_sampling = state.get("batch_sampling") or state.get("sampling")
    if isinstance(batch_sampling, str) and batch_sampling.lower() in {"random", "shuffle", "stochastic"}:
        return True
    batch = state.get("batch")
    if isinstance(batch, dict):
        mode = batch.get("mode") or batch.get("sampling")
        if isinstance(mode, str) and mode.lower() in {"random", "shuffle", "stochastic"}:
            return True
    return False


def _has_seed(state: dict[str, Any]) -> bool:
    if state.get("seed") is not None or state.get("random_seed") is not None:
        return True
    batch = state.get("batch")
    return isinstance(batch, dict) and (batch.get("seed") is not None or batch.get("random_seed") is not None)


def _validate_ml_loss_curve(step: int, state: dict[str, Any], tolerance: float) -> list[str]:
    errors: list[str] = []
    curve = state.get("loss_curve") or state.get("loss_history")
    if curve is None:
        return errors
    if not isinstance(curve, list) or not curve:
        return [f"第 {step} 步 loss_curve 必须是非空数值序列"]
    losses: list[float] = []
    for index, value in enumerate(curve):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            errors.append(f"第 {step} 步 loss_curve[{index}] 不是有限数值")
            continue
        loss = float(value)
        losses.append(loss)
        if loss < -tolerance:
            errors.append(f"第 {step} 步 loss_curve[{index}] 为负数")
    should_decrease = state.get("loss_should_decrease")
    if should_decrease is not False and len(losses) == len(curve):
        for index, (left, right) in enumerate(zip(losses, losses[1:]), start=1):
            if right > left + tolerance:
                errors.append(f"第 {step} 步 loss_curve[{index}] 未按容差下降")
    return errors


def _validate_ml_linear_regression_step(step: int, state: dict[str, Any], tolerance: float) -> list[str]:
    features = state.get("features", state.get("x", state.get("X")))
    labels = state.get("labels", state.get("y"))
    if not _is_numeric_vector(labels):
        return []
    rows = _as_feature_rows(features)
    if rows is None or len(rows) != len(labels):
        return []
    params = _ml_parameters(state)
    gradient = _ml_gradient(state)
    if params is None or gradient is None:
        return []
    weights = _parameter_weights(params)
    if weights is None:
        return []
    bias = _parameter_bias(params)
    predictions = _numeric_list(state.get("prediction") or state.get("predictions"))
    if predictions is None:
        predictions = [sum(weight * x for weight, x in zip(weights, row)) + bias for row in rows]
    if len(predictions) != len(labels):
        return [f"第 {step} 步 prediction 长度与标签不一致"]
    expected_weights = _linear_gradient_weights(rows, [float(y) for y in labels], predictions)
    actual_weights = _gradient_weights(gradient, len(expected_weights))
    if actual_weights is not None:
        for index, expected in enumerate(expected_weights):
            if not _close(actual_weights[index], expected, tolerance):
                errors = [f"第 {step} 步 线性回归 grad_w[{index}] 应为 {expected:.6g}，实际为 {actual_weights[index]:.6g}"]
                return errors
    expected_bias = _linear_gradient_bias([float(y) for y in labels], predictions)
    actual_bias = _gradient_bias(gradient)
    if actual_bias is not None and not _close(actual_bias, expected_bias, tolerance):
        return [f"第 {step} 步 线性回归 grad_b 应为 {expected_bias:.6g}，实际为 {actual_bias:.6g}"]
    loss = state.get("loss")
    if isinstance(loss, (int, float)) and math.isfinite(float(loss)):
        expected_loss = sum((pred - float(label)) ** 2 for pred, label in zip(predictions, labels)) / (2 * len(labels))
        if not _close(float(loss), expected_loss, tolerance):
            return [f"第 {step} 步 线性回归 loss 应为 {expected_loss:.6g}，实际为 {float(loss):.6g}"]
    return []


def _validate_ml_parameter_update(step: int, state: dict[str, Any], tolerance: float) -> list[str]:
    before = state.get("parameters_before") or state.get("before_parameters")
    after = state.get("parameters_after") or state.get("after_parameters")
    gradient = _ml_gradient(state)
    learning_rate = state.get("learning_rate") or state.get("lr")
    if not isinstance(before, dict) or not isinstance(after, dict) or gradient is None or not isinstance(learning_rate, (int, float)):
        return []
    lr = float(learning_rate)
    errors: list[str] = []
    for name, before_value in before.items():
        if name not in after:
            continue
        grad = _gradient_value_for_name(gradient, str(name))
        if grad is None:
            continue
        actual = after[name]
        if isinstance(before_value, (int, float)) and isinstance(actual, (int, float)) and isinstance(grad, (int, float)):
            expected = float(before_value) - lr * float(grad)
            if not _close(float(actual), expected, tolerance):
                errors.append(f"第 {step} 步 参数 {name} 更新不满足 after = before - lr * gradient")
    return errors


def _as_feature_rows(value: Any) -> list[list[float]] | None:
    if not isinstance(value, list) or not value:
        return None
    if all(isinstance(item, (int, float)) for item in value):
        return [[float(item)] for item in value]
    rows: list[list[float]] = []
    for row in value:
        if not isinstance(row, list) or not row or not all(isinstance(item, (int, float)) for item in row):
            return None
        rows.append([float(item) for item in row])
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        return None
    return rows


def _is_numeric_vector(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, (int, float)) for item in value)


def _numeric_list(value: Any) -> list[float] | None:
    if not _is_numeric_vector(value):
        return None
    return [float(item) for item in value]


def _ml_parameters(state: dict[str, Any]) -> dict[str, Any] | None:
    params = state.get("parameters") or state.get("params")
    if isinstance(params, dict):
        return params
    weights = state.get("weights") or state.get("w")
    if weights is None:
        return None
    params = {"w": weights}
    if "b" in state:
        params["b"] = state["b"]
    return params


def _ml_gradient(state: dict[str, Any]) -> Any:
    return state.get("gradient") or state.get("gradients") or state.get("grad")


def _parameter_weights(params: dict[str, Any]) -> list[float] | None:
    for key in ("w", "weights", "theta"):
        value = params.get(key)
        if isinstance(value, (int, float)):
            return [float(value)]
        if _is_numeric_vector(value):
            return [float(item) for item in value]
    numeric_named = [(name, value) for name, value in params.items() if str(name).startswith("w") and isinstance(value, (int, float))]
    if numeric_named:
        return [float(value) for _name, value in sorted(numeric_named)]
    return None


def _parameter_bias(params: dict[str, Any]) -> float:
    value = params.get("b", params.get("bias", 0.0))
    return float(value) if isinstance(value, (int, float)) else 0.0


def _linear_gradient_weights(rows: list[list[float]], labels: list[float], predictions: list[float]) -> list[float]:
    n = len(labels)
    width = len(rows[0])
    return [
        sum((predictions[i] - labels[i]) * rows[i][j] for i in range(n)) / n
        for j in range(width)
    ]


def _linear_gradient_bias(labels: list[float], predictions: list[float]) -> float:
    return sum(pred - label for pred, label in zip(predictions, labels)) / len(labels)


def _gradient_weights(gradient: Any, expected_len: int) -> list[float] | None:
    if isinstance(gradient, (int, float)) and expected_len == 1:
        return [float(gradient)]
    if _is_numeric_vector(gradient) and len(gradient) == expected_len:
        return [float(item) for item in gradient]
    if not isinstance(gradient, dict):
        return None
    for key in ("w", "weights", "theta"):
        value = gradient.get(key)
        if isinstance(value, (int, float)) and expected_len == 1:
            return [float(value)]
        if _is_numeric_vector(value) and len(value) == expected_len:
            return [float(item) for item in value]
    named = [(name, value) for name, value in gradient.items() if str(name).startswith("w") and isinstance(value, (int, float))]
    if len(named) == expected_len:
        return [float(value) for _name, value in sorted(named)]
    return None


def _gradient_bias(gradient: Any) -> float | None:
    if not isinstance(gradient, dict):
        return None
    value = gradient.get("b", gradient.get("bias"))
    return float(value) if isinstance(value, (int, float)) else None


def _gradient_value_for_name(gradient: Any, name: str) -> Any:
    if isinstance(gradient, dict):
        if name in gradient:
            return gradient[name]
        if name == "b":
            return gradient.get("bias")
    return None


def _close(left: float, right: float, tolerance: float) -> bool:
    return math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)


def _is_matrix(value: Any) -> bool:
    return isinstance(value, list) and value and all(isinstance(row, list) for row in value)


def _validate_heap_property(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        heap = (event.state or {}).get("heap")
        if not isinstance(heap, list) or not heap or not all(isinstance(x, (int, float)) for x in heap):
            continue
        mode = (event.state or {}).get("heap_type") or "min"
        for i, value in enumerate(heap):
            left, right = 2 * i + 1, 2 * i + 2
            for child in (left, right):
                if child >= len(heap):
                    continue
                if mode == "max" and value < heap[child]:
                    errors.append(f"第 {event.step} 步 heap[{i}] 小于子节点，不满足大顶堆")
                if mode != "max" and value > heap[child]:
                    errors.append(f"第 {event.step} 步 heap[{i}] 大于子节点，不满足小顶堆")
    return errors


def _validate_monotonic_stack(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        stack = state.get("stack")
        mode = state.get("stack_order") or state.get("monotonic")
        if mode not in {"increasing", "decreasing"} or not isinstance(stack, list):
            continue
        values = _stack_values(state, stack)
        if values is None:
            continue
        pairs = zip(values, values[1:])
        if mode == "increasing" and any(a > b for a, b in pairs):
            errors.append(f"第 {event.step} 步 stack 不满足单调递增")
        if mode == "decreasing" and any(a < b for a, b in pairs):
            errors.append(f"第 {event.step} 步 stack 不满足单调递减")
        errors.extend(_validate_monotonic_stack_answer_write(event))
    return errors


def _validate_monotonic_stack_key_step_coverage(trace: SemanticTrace) -> list[str]:
    sequence = _monotonic_stack_input_sequence(trace)
    if sequence is None or len(sequence) > SMALL_MONOTONIC_STACK_INPUT_LIMIT:
        return []
    if not _trace_has_monotonic_stack_signal(trace):
        return []
    missing: list[str] = []
    if not _trace_has_stack_push(trace):
        missing.append("push")
    requires_pop, requires_answer_write = _monotonic_stack_requires_pop_and_answer(sequence)
    if requires_pop and not _trace_has_stack_pop(trace):
        missing.append("pop")
    if requires_answer_write and not _trace_has_answer_write(trace):
        missing.append("answer_write")
    if missing:
        return [f"failure_type=coverage_error: 单调栈缺少关键步骤覆盖：{', '.join(missing)}"]
    return []


def _monotonic_stack_input_sequence(trace: SemanticTrace) -> list[Any] | None:
    if not isinstance(trace.input_data, dict):
        return None
    for key in ("temperatures", "nums", "heights"):
        value = trace.input_data.get(key)
        if isinstance(value, list):
            return value
    return None


def _trace_has_monotonic_stack_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if "单调栈" in trace.algorithm or "monotonic stack" in algorithm:
        return True
    for event in trace.events:
        state = event.state or {}
        if state.get("stack_order") in {"increasing", "decreasing"} or state.get("monotonic") in {"increasing", "decreasing"}:
            return True
    return False


def _monotonic_stack_requires_pop_and_answer(sequence: list[Any]) -> tuple[bool, bool]:
    stack: list[int] = []
    requires = False
    for i, value in enumerate(sequence):
        while stack and isinstance(sequence[stack[-1]], (int, float)) and isinstance(value, (int, float)) and sequence[stack[-1]] < value:
            requires = True
            stack.pop()
        stack.append(i)
    return requires, requires


def _trace_has_stack_push(trace: SemanticTrace) -> bool:
    return any(event.op == SemanticOp.PUSH and "stack" in _event_target_ids(event) for event in trace.events)


def _trace_has_stack_pop(trace: SemanticTrace) -> bool:
    return any(event.op == SemanticOp.POP and "stack" in _event_target_ids(event) for event in trace.events)


def _trace_has_answer_write(trace: SemanticTrace) -> bool:
    for event in trace.events:
        if event.op != SemanticOp.SET:
            continue
        for ref in _event_target_ids(event):
            parsed = parse_target(ref)
            if parsed.kind == "indexed" and parsed.name in {"answer", "answers", "ans"}:
                return True
    return False


def _stack_values(state: dict[str, Any], stack: list[Any]) -> list[Any] | None:
    values = state.get("stack_values")
    if isinstance(values, list) and len(values) == len(stack) and all(isinstance(x, (int, float)) for x in values):
        return values
    nums = state.get("nums") or state.get("temperatures") or state.get("heights")
    if isinstance(nums, list) and all(isinstance(i, int) and 0 <= i < len(nums) for i in stack):
        vals = [nums[i] for i in stack]
        if all(isinstance(x, (int, float)) for x in vals):
            return vals
    if all(isinstance(x, (int, float)) for x in stack):
        return stack
    return None


def _validate_monotonic_stack_answer_write(event) -> list[str]:
    if event.op != SemanticOp.SET:
        return []
    state = event.state or {}
    temperatures = state.get("temperatures") or state.get("nums") or state.get("heights")
    answer = state.get("answer") or state.get("answers") or state.get("ans")
    i = state.get("i")
    if not isinstance(temperatures, list) or not isinstance(answer, list) or not isinstance(i, int):
        return []
    errors: list[str] = []
    for target in event.targets:
        parsed = parse_target(target.id)
        if parsed.kind != "indexed" or parsed.name not in {"answer", "answers", "ans"} or len(parsed.indices) != 1:
            continue
        j = parsed.indices[0]
        if not (0 <= j < len(answer) and 0 <= i < len(temperatures)):
            continue
        current = temperatures[i]
        previous = temperatures[j]
        actual = answer[j]
        expected = i - j
        if isinstance(current, (int, float)) and isinstance(previous, (int, float)) and current <= previous:
            errors.append(f"第 {event.step} 步 answer[{j}] 写入时当前值未打破单调栈条件")
        if actual != expected:
            errors.append(f"第 {event.step} 步 answer[{j}] 应为 {expected}，实际为 {actual}")
        expected_deps = {f"{_sequence_name_for_answer_state(state)}[{j}]", f"{_sequence_name_for_answer_state(state)}[{i}]"}
        actual_deps = _event_ref_ids(event.deps)
        if event.deps and not expected_deps <= actual_deps:
            errors.append(f"第 {event.step} 步 answer[{j}] 依赖应包含 {', '.join(sorted(expected_deps))}")
    return errors


def _sequence_name_for_answer_state(state: dict[str, Any]) -> str:
    if isinstance(state.get("temperatures"), list):
        return "temperatures"
    if isinstance(state.get("heights"), list):
        return "heights"
    return "nums"


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


def _validate_lcs_dp(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    a = input_data.get("text1") or input_data.get("s1") or input_data.get("a")
    b = input_data.get("text2") or input_data.get("s2") or input_data.get("b")
    if not isinstance(a, str) or not isinstance(b, str):
        return errors
    for event in trace.events:
        dp = (event.state or {}).get("dp")
        if not _is_matrix(dp) or len(dp) != len(a) + 1 or any(len(row) != len(b) + 1 for row in dp):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "dp" or len(parsed.indices) != 2:
                continue
            i, j = parsed.indices
            if i == 0 or j == 0:
                expected = 0
            elif a[i - 1] == b[j - 1]:
                expected = dp[i - 1][j - 1] + 1
            else:
                expected = max(dp[i - 1][j], dp[i][j - 1])
            if dp[i][j] != expected:
                errors.append(f"第 {event.step} 步 dp[{i}][{j}] 不满足 LCS 转移")
    return errors


def _validate_edit_distance_dp(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    a = input_data.get("word1")
    b = input_data.get("word2")
    if not isinstance(a, str) or not isinstance(b, str):
        return errors
    for event in trace.events:
        dp = (event.state or {}).get("dp")
        if not _is_matrix(dp) or len(dp) != len(a) + 1 or any(len(row) != len(b) + 1 for row in dp):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "dp" or len(parsed.indices) != 2:
                continue
            i, j = parsed.indices
            if i == 0:
                expected = j
            elif j == 0:
                expected = i
            elif a[i - 1] == b[j - 1]:
                expected = dp[i - 1][j - 1]
            else:
                expected = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
            if dp[i][j] != expected:
                errors.append(f"第 {event.step} 步 dp[{i}][{j}] 不满足编辑距离转移")
    return errors


def _validate_kmp_prefix(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    pattern = input_data.get("pattern") or input_data.get("needle")
    if not isinstance(pattern, str):
        return errors
    expected = _kmp_prefix(pattern)
    for event in trace.events:
        state = event.state or {}
        pi = state.get("pi") or state.get("prefix") or state.get("lps") or state.get("next")
        if not isinstance(pi, list) or len(pi) != len(pattern) or not all(isinstance(x, int) for x in pi):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name in {"pi", "prefix", "lps", "next"} and len(parsed.indices) == 1:
                i = parsed.indices[0]
                if 0 <= i < len(expected) and pi[i] != expected[i]:
                    errors.append(f"第 {event.step} 步 {parsed.name}[{i}] 不满足 KMP 前缀函数")
    return errors


def _kmp_prefix(pattern: str) -> list[int]:
    pi = [0] * len(pattern)
    j = 0
    for i in range(1, len(pattern)):
        while j and pattern[i] != pattern[j]:
            j = pi[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
    return pi


def _validate_rabin_karp_hashes(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    text = input_data.get("text") or input_data.get("haystack")
    pattern = input_data.get("pattern") or input_data.get("needle")
    if not isinstance(text, str) or not isinstance(pattern, str):
        return errors
    algorithm = (trace.algorithm or "").lower()
    if "rabin" not in algorithm and "karp" not in algorithm and "rolling" not in algorithm and "滚动哈希" not in trace.algorithm:
        return errors
    expected_pattern_hash = _string_hash(pattern)
    expected_windows = [_string_hash(text[i : i + len(pattern)]) for i in range(0, max(0, len(text) - len(pattern) + 1))]
    for event in trace.events:
        state = event.state or {}
        pattern_hash = state.get("pattern_hash")
        if isinstance(pattern_hash, int) and pattern_hash != expected_pattern_hash:
            errors.append(f"第 {event.step} 步 Rabin-Karp pattern_hash 应为 {expected_pattern_hash}")
        hashes = state.get("window_hashes") or state.get("hashes")
        if isinstance(hashes, list):
            for index, expected in enumerate(expected_windows[: len(hashes)]):
                value = hashes[index]
                if isinstance(value, int) and value != expected:
                    errors.append(f"第 {event.step} 步 Rabin-Karp window_hashes[{index}] 应为 {expected}")
            if event.op == SemanticOp.SET:
                for target in event.targets:
                    parsed = parse_target(target.id)
                    if parsed.kind == "indexed" and parsed.name in {"window_hashes", "hashes"} and len(parsed.indices) == 1:
                        i = parsed.indices[0]
                        if 0 <= i < len(expected_windows) and i < len(hashes) and isinstance(hashes[i], int) and hashes[i] != expected_windows[i]:
                            errors.append(f"第 {event.step} 步 Rabin-Karp {parsed.name}[{i}] 不满足滚动哈希")
        window_hash = state.get("window_hash")
        window_start = state.get("window_start", state.get("i"))
        if isinstance(window_hash, int) and isinstance(window_start, int) and 0 <= window_start < len(expected_windows):
            expected = expected_windows[window_start]
            if window_hash != expected:
                errors.append(f"第 {event.step} 步 Rabin-Karp window_hash 应为 {expected}")
    return errors


def _string_hash(value: str, *, base: int = 257, mod: int = 1_000_000_007) -> int:
    h = 0
    for ch in value:
        h = (h * base + ord(ch)) % mod
    return h


def _validate_z_algorithm(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    text = _string_input_for_algorithm(trace, state_key="text")
    if not isinstance(text, str):
        return errors
    algorithm = (trace.algorithm or "").lower()
    has_z_signal = "z algorithm" in algorithm or "z 算法" in trace.algorithm or any("z" in (event.state or {}) for event in trace.events)
    if not has_z_signal:
        return errors
    expected = _z_values(text)
    for event in trace.events:
        z = (event.state or {}).get("z")
        if not isinstance(z, list) or len(z) != len(text) or not all(isinstance(x, int) for x in z):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name == "z" and len(parsed.indices) == 1:
                i = parsed.indices[0]
                if 0 <= i < len(expected) and z[i] != expected[i]:
                    errors.append(f"第 {event.step} 步 Z Algorithm z[{i}] 应为 {expected[i]}")
    return errors


def _string_input_for_algorithm(trace: SemanticTrace, *, state_key: str) -> str | None:
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    value = input_data.get(state_key) or input_data.get("s") or input_data.get("string")
    if isinstance(value, str):
        return value
    for event in trace.events:
        state_value = (event.state or {}).get(state_key)
        if isinstance(state_value, str):
            return state_value
    return None


def _z_values(text: str) -> list[int]:
    n = len(text)
    z = [0] * n
    left = right = 0
    for i in range(1, n):
        if i <= right:
            z[i] = min(right - i + 1, z[i - left])
        while i + z[i] < n and text[z[i]] == text[i + z[i]]:
            z[i] += 1
        if i + z[i] - 1 > right:
            left, right = i, i + z[i] - 1
    return z


def _validate_manacher_radius(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    algorithm = (trace.algorithm or "").lower()
    has_signal = "manacher" in algorithm or "回文半径" in trace.algorithm or any("radius" in (event.state or {}) for event in trace.events)
    if not has_signal:
        return errors
    raw_text = _string_input_for_algorithm(trace, state_key="text")
    if not isinstance(raw_text, str):
        return errors
    expected_by_text = {
        raw_text: _manacher_radius(raw_text) if _looks_transformed_manacher_text(raw_text) else _odd_palindrome_radius(raw_text),
    }
    transformed = _manacher_transform(raw_text)
    expected_by_text.setdefault(transformed, _manacher_radius(transformed))
    for event in trace.events:
        state = event.state or {}
        state_text = state.get("text")
        radius = state.get("radius") or state.get("p")
        if not isinstance(state_text, str) or not isinstance(radius, list) or not all(isinstance(x, int) for x in radius):
            continue
        expected = expected_by_text.get(state_text)
        if expected is None and _looks_transformed_manacher_text(state_text):
            expected = _manacher_radius(state_text)
        if expected is None or len(radius) != len(expected):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name in {"radius", "p"} and len(parsed.indices) == 1:
                i = parsed.indices[0]
                if 0 <= i < len(expected) and radius[i] != expected[i]:
                    errors.append(f"第 {event.step} 步 Manacher {parsed.name}[{i}] 应为 {expected[i]}")
    return errors


def _looks_transformed_manacher_text(text: str) -> bool:
    return len(text) % 2 == 1 and all((i % 2 == 0) == (ch == "#") for i, ch in enumerate(text))


def _manacher_transform(text: str) -> str:
    return "#" + "#".join(text) + "#"


def _manacher_radius(text: str) -> list[int]:
    radius = [0] * len(text)
    center = right = 0
    for i in range(len(text)):
        mirror = 2 * center - i
        if i < right and 0 <= mirror < len(text):
            radius[i] = min(right - i, radius[mirror])
        while i - radius[i] - 1 >= 0 and i + radius[i] + 1 < len(text) and text[i - radius[i] - 1] == text[i + radius[i] + 1]:
            radius[i] += 1
        if i + radius[i] > right:
            center, right = i, i + radius[i]
    return radius


def _odd_palindrome_radius(text: str) -> list[int]:
    radius = [0] * len(text)
    left = 0
    right = -1
    for i in range(len(text)):
        k = 1 if i > right else min(radius[left + right - i], right - i + 1)
        while i - k >= 0 and i + k < len(text) and text[i - k] == text[i + k]:
            k += 1
        radius[i] = k
        if i + k - 1 > right:
            left, right = i - k + 1, i + k - 1
    return radius


def _validate_complete_knapsack(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    coins = input_data.get("coins") or input_data.get("nums")
    amount = input_data.get("amount") or input_data.get("target")
    if not isinstance(coins, list) or not all(isinstance(x, int) and x > 0 for x in coins) or not isinstance(amount, int):
        return errors
    mode = _knapsack_mode(trace)
    if mode not in {"complete_min", "complete_count"}:
        return errors
    expected = _complete_knapsack_expected(coins, amount, mode)
    for event in trace.events:
        dp = (event.state or {}).get("dp")
        if not isinstance(dp, list) or len(dp) != amount + 1:
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name == "dp" and len(parsed.indices) == 1:
                j = parsed.indices[0]
                if 0 <= j <= amount and _normal_inf(dp[j]) != _normal_inf(expected[j]):
                    errors.append(f"第 {event.step} 步 dp[{j}] 不满足完全背包转移")
    return errors


def _knapsack_mode(trace: SemanticTrace) -> str:
    for event in trace.events:
        state = event.state or {}
        mode = state.get("knapsack") or state.get("dp_mode") or state.get("problem_type")
        if mode in {"complete_min", "complete_count"}:
            return mode
    text = (trace.algorithm or "").lower()
    if "coin" in text or "零钱" in text:
        return "complete_min"
    return ""


def _complete_knapsack_expected(coins: list[int], amount: int, mode: str) -> list[Any]:
    if mode == "complete_count":
        dp = [0] * (amount + 1)
        dp[0] = 1
        for coin in coins:
            for j in range(coin, amount + 1):
                dp[j] += dp[j - coin]
        return dp
    inf = amount + 1
    dp = [inf] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for j in range(coin, amount + 1):
            dp[j] = min(dp[j], dp[j - coin] + 1)
    return [-1 if x == inf else x for x in dp]


def _normal_inf(value: Any) -> Any:
    if value in {float("inf"), "inf", "Infinity", None}:
        return -1
    return value


def _validate_interval_dp(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    nums = input_data.get("nums") or input_data.get("stones")
    if not isinstance(nums, list) or not all(isinstance(x, int) for x in nums):
        return errors
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)
    for event in trace.events:
        state = event.state or {}
        dp = state.get("dp")
        mode = state.get("interval_dp") or state.get("dp_mode")
        if mode not in {"merge_stones", "min_merge"} or not _is_matrix(dp):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "dp" or len(parsed.indices) != 2:
                continue
            i, j = parsed.indices
            if not (0 <= i <= j < len(nums)):
                continue
            expected = 0 if i == j else min(dp[i][k] + dp[k + 1][j] for k in range(i, j)) + prefix[j + 1] - prefix[i]
            if dp[i][j] != expected:
                errors.append(f"第 {event.step} 步 dp[{i}][{j}] 不满足区间 DP 转移")
    return errors


def _validate_bst_order(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        tree = (event.state or {}).get("tree") or (event.state or {}).get("binary_tree")
        if not _tree_has_layout(tree, "bst"):
            continue
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        roots = _roots(nodes, edges)
        for root in roots:
            errors.extend(_check_bst_node(root, children, nodes, None, None, event.step))
    return errors


def _tree_has_layout(tree: Any, layout: str) -> bool:
    if not isinstance(tree, dict):
        return False
    meta = tree.get("meta") if isinstance(tree.get("meta"), dict) else {}
    return tree.get("kind") == layout or tree.get("type") == layout or meta.get("kind") == layout


def _tree_nodes_edges(tree: dict[str, Any]) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    nodes: dict[str, Any] = {}
    for node in tree.get("nodes") or []:
        if isinstance(node, dict):
            node_id = str(node.get("id"))
            value = node.get("value", node.get("label", node_id))
        else:
            node_id = str(node)
            value = node
        nodes[node_id] = _as_number(value)
    edges = []
    for edge in tree.get("edges") or []:
        if isinstance(edge, dict):
            src, dst = edge.get("from"), edge.get("to")
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            src, dst = edge[0], edge[1]
        else:
            continue
        edges.append((str(src), str(dst)))
    return nodes, edges


def _children_map(edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}
    for src, dst in edges:
        children.setdefault(src, []).append(dst)
    return children


def _roots(nodes: dict[str, Any], edges: list[tuple[str, str]]) -> list[str]:
    targets = {dst for _src, dst in edges}
    roots = [node for node in nodes if node not in targets]
    return roots or list(nodes)[:1]


def _check_bst_node(node: str, children: dict[str, list[str]], values: dict[str, Any], lo: Any, hi: Any, step: int) -> list[str]:
    errors: list[str] = []
    value = values.get(node)
    if isinstance(value, (int, float)):
        if lo is not None and value <= lo:
            errors.append(f"第 {step} 步 BST 节点 {node} 不大于下界")
        if hi is not None and value >= hi:
            errors.append(f"第 {step} 步 BST 节点 {node} 不小于上界")
    kids = children.get(node, [])
    if len(kids) >= 1:
        errors.extend(_check_bst_node(kids[0], children, values, lo, value if isinstance(value, (int, float)) else hi, step))
    if len(kids) >= 2:
        errors.extend(_check_bst_node(kids[1], children, values, value if isinstance(value, (int, float)) else lo, hi, step))
    return errors


def _as_number(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return value


def _validate_lca_node(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    p = str(input_data.get("p")) if "p" in input_data else None
    q = str(input_data.get("q")) if "q" in input_data else None
    if p is None or q is None:
        return errors
    for event in trace.events:
        state = event.state or {}
        tree = state.get("tree") or input_data.get("tree")
        lca = state.get("lca") or state.get("answer")
        if not isinstance(tree, dict) or lca is None:
            continue
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        roots = _roots(nodes, edges)
        expected = _lca(str(roots[0]), p, q, children) if roots else None
        if expected is not None and str(lca) != str(expected):
            errors.append(f"第 {event.step} 步 LCA 应为 {expected}，实际为 {lca}")
    return errors


def _lca(root: str, p: str, q: str, children: dict[str, list[str]]) -> str | None:
    if root == p or root == q:
        return root
    hits = []
    for child in children.get(root, []):
        got = _lca(child, p, q, children)
        if got is not None:
            hits.append(got)
    if len(hits) >= 2:
        return root
    return hits[0] if hits else None


def _validate_tree_diameter(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    algorithm = trace.algorithm or ""
    has_signal = "树直径" in algorithm or "diameter" in algorithm.lower() or any(
        "diameter" in (event.state or {}) for event in trace.events
    )
    if not has_signal:
        return errors
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    for event in trace.events:
        state = event.state or {}
        tree = state.get("tree") or input_data.get("tree")
        if not isinstance(tree, dict):
            continue
        current = state.get("current")
        height = state.get("height")
        diameter = state.get("diameter")
        if current is None or not isinstance(height, dict) or not isinstance(diameter, dict):
            continue
        node = str(current)
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        expected_height = _tree_height(node, children)
        child_diameters = [_dict_int(diameter, child, default=0) for child in children.get(node, [])]
        child_heights = [_tree_height(child, children) for child in children.get(node, [])]
        through = sum(sorted(child_heights, reverse=True)[:2])
        expected_diameter = max([through, *child_diameters], default=0)
        actual_height = _dict_int(height, node)
        actual_diameter = _dict_int(diameter, node)
        if node in nodes and actual_height is not None and actual_height != expected_height:
            errors.append(f"第 {event.step} 步树直径 height[{node}] 应为 {expected_height}")
        if node in nodes and actual_diameter is not None and actual_diameter != expected_diameter:
            errors.append(f"第 {event.step} 步树直径 diameter[{node}] 应为 {expected_diameter}")
    return errors


def _validate_tree_max_independent_set(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    algorithm = trace.algorithm or ""
    has_signal = "树形 dp" in algorithm.lower() or "树形 DP" in algorithm or any(
        "dp_take" in (event.state or {}) or "dp_skip" in (event.state or {}) for event in trace.events
    )
    if not has_signal:
        return errors
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    for event in trace.events:
        state = event.state or {}
        tree = state.get("tree") or input_data.get("tree")
        dp_take = state.get("dp_take")
        dp_skip = state.get("dp_skip")
        current = state.get("current")
        if not isinstance(tree, dict) or not isinstance(dp_take, dict) or not isinstance(dp_skip, dict) or current is None:
            continue
        node = str(current)
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        if node not in nodes:
            continue
        expected_take = _node_weight(tree, node) + sum(_dict_int(dp_skip, child, default=0) for child in children.get(node, []))
        expected_skip = sum(
            max(_dict_int(dp_take, child, default=0), _dict_int(dp_skip, child, default=0)) for child in children.get(node, [])
        )
        actual_take = _dict_int(dp_take, node)
        actual_skip = _dict_int(dp_skip, node)
        if actual_take is not None and actual_take != expected_take:
            errors.append(f"第 {event.step} 步树形 DP dp_take[{node}] 应为 {expected_take}")
        if actual_skip is not None and actual_skip != expected_skip:
            errors.append(f"第 {event.step} 步树形 DP dp_skip[{node}] 应为 {expected_skip}")
    return errors


def _validate_segment_tree_sums(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums")
        tree = state.get("segment_tree")
        if not _is_numeric_sequence(nums) or not isinstance(tree, dict):
            continue
        for node in tree.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            left = _int_or_none(meta.get("l", meta.get("left")))
            right = _int_or_none(meta.get("r", meta.get("right")))
            actual = _int_or_none(meta.get("sum", meta.get("value", node.get("value"))))
            if left is None or right is None or actual is None:
                continue
            if not (0 <= left <= right < len(nums)):
                errors.append(f"第 {event.step} 步线段树节点 {node.get('id')} 覆盖区间越界")
                continue
            expected = sum(nums[left : right + 1])
            if actual != expected:
                errors.append(f"第 {event.step} 步线段树节点 {node.get('id')} 区间和应为 {expected}")
    return errors


def _validate_fenwick_tree(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums")
        bit = state.get("bit") or state.get("fenwick")
        if not _is_numeric_sequence(nums) or not _is_numeric_sequence(bit):
            continue
        if len(bit) != len(nums) + 1:
            errors.append(f"第 {event.step} 步树状数组 bit 长度应为 nums 长度 + 1")
            continue
        expected = _fenwick_expected(nums)
        for i in range(1, len(expected)):
            if bit[i] != expected[i]:
                errors.append(f"第 {event.step} 步树状数组 bit[{i}] 应为 {expected[i]}")
    return errors


def _validate_sparse_table(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums") or input_data.get("nums")
        st = state.get("st") or state.get("sparse_table")
        if not _is_numeric_sequence(nums) or not _is_matrix(st):
            continue
        for k, row in enumerate(st):
            if not isinstance(row, list):
                continue
            span = 1 << k
            if span > len(nums):
                continue
            for i, value in enumerate(row):
                if value is None:
                    continue
                if not isinstance(value, (int, float)):
                    continue
                if i + span > len(nums):
                    continue
                expected = min(nums[i : i + span])
                if value != expected:
                    errors.append(f"第 {event.step} 步稀疏表 st[{k}][{i}] 应为 {expected}")
    return errors


def _validate_gcd_remainders(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    a = _int_or_none(input_data.get("a"))
    b = _int_or_none(input_data.get("b"))
    if a is None or b is None:
        return errors
    expected = _gcd_remainders(abs(a), abs(b))
    for event in trace.events:
        remainders = (event.state or {}).get("remainders")
        if not isinstance(remainders, list):
            continue
        for i, value in enumerate(remainders):
            if i >= len(expected) or not isinstance(value, int):
                continue
            if value != expected[i]:
                errors.append(f"第 {event.step} 步最大公约数 remainders[{i}] 应为 {expected[i]}")
    return errors


def _validate_fast_power_table(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    base = _int_or_none(input_data.get("base"))
    exponent = _int_or_none(input_data.get("exponent"))
    mod = _int_or_none(input_data.get("mod"))
    if base is None or exponent is None or mod is None or exponent < 0 or mod <= 0:
        return errors
    expected_bits = _bits_lsb_first(exponent)
    expected_powers = _fast_power_powers(base, exponent, mod)
    for event in trace.events:
        state = event.state or {}
        bits = state.get("bits")
        powers = state.get("powers")
        if isinstance(bits, list):
            for i, value in enumerate(bits):
                if i < len(expected_bits) and isinstance(value, int) and value != expected_bits[i]:
                    errors.append(f"第 {event.step} 步快速幂 bits[{i}] 应为 {expected_bits[i]}")
        if isinstance(powers, list):
            for i, value in enumerate(powers):
                if i < len(expected_powers) and isinstance(value, int) and value != expected_powers[i]:
                    errors.append(f"第 {event.step} 步快速幂 powers[{i}] 应为 {expected_powers[i]}")
    return errors


def _validate_sieve_primes(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    n = _int_or_none(input_data.get("n"))
    if n is None or n < 0:
        return errors
    expected = _sieve_flags(n)
    for event in trace.events:
        flags = (event.state or {}).get("is_prime")
        if not isinstance(flags, list) or len(flags) != len(expected):
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "is_prime" or len(parsed.indices) != 1:
                continue
            i = parsed.indices[0]
            if 0 <= i < len(expected) and isinstance(flags[i], bool) and flags[i] != expected[i]:
                errors.append(f"第 {event.step} 步筛法 is_prime[{i}] 应为 {expected[i]}")
    return errors


def _validate_pascal_combinations(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    n = _int_or_none(input_data.get("n"))
    k = _int_or_none(input_data.get("k"))
    if n is None or k is None or n < 0 or k < 0:
        return errors
    for event in trace.events:
        table = (event.state or {}).get("table")
        if not _is_matrix(table):
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "table" or len(parsed.indices) != 2:
                continue
            i, j = parsed.indices
            if not (0 <= i <= n and 0 <= j <= min(i, k) and i < len(table) and j < len(table[i])):
                continue
            value = table[i][j]
            if not isinstance(value, int):
                continue
            expected = _comb(i, j)
            if value != expected:
                errors.append(f"第 {event.step} 步组合数 table[{i}][{j}] 应为 {expected}")
    return errors


def _validate_bitmask_subset(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    nums = input_data.get("nums")
    if not isinstance(nums, list):
        return errors
    for event in trace.events:
        state = event.state or {}
        mask = _int_or_none(state.get("mask"))
        bits = state.get("bits")
        subset = state.get("subset")
        if mask is None or not isinstance(bits, list):
            continue
        expected_bits = [((mask >> i) & 1) for i in range(len(nums))]
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "bits" or len(parsed.indices) != 1:
                continue
            i = parsed.indices[0]
            if i < len(expected_bits) and i < len(bits) and isinstance(bits[i], int) and bits[i] != expected_bits[i]:
                errors.append(f"第 {event.step} 步位掩码 bits[{i}] 应为 {expected_bits[i]}")
        expected_subset = [nums[i] for i, bit in enumerate(expected_bits) if bit]
        if event.role == "answer" and isinstance(subset, list) and subset != expected_subset:
            errors.append(f"第 {event.step} 步位掩码 subset 应为 {expected_subset}")
    return errors


def _validate_lowbit_decomposition(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    n = _int_or_none(input_data.get("n"))
    if n is None or n < 0:
        return errors
    expected = _lowbit_parts(n)
    for event in trace.events:
        state = event.state or {}
        lowbit = _int_or_none(state.get("lowbit"))
        remaining = _int_or_none(state.get("remaining"))
        if lowbit is not None and remaining is not None and remaining > 0:
            expected_low = remaining & -remaining
            if lowbit != expected_low:
                errors.append(f"第 {event.step} 步 lowbit 应为 {expected_low}")
        lowbits = state.get("lowbits")
        if isinstance(lowbits, list):
            for i, value in enumerate(lowbits):
                if i < len(expected) and isinstance(value, int) and value != expected[i]:
                    errors.append(f"第 {event.step} 步 lowbit lowbits[{i}] 应为 {expected[i]}")
    return errors


def _is_numeric_sequence(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _fenwick_expected(nums: list[int | float]) -> list[int | float]:
    bit: list[int | float] = [0] * (len(nums) + 1)
    for i, value in enumerate(nums):
        j = i + 1
        while j <= len(nums):
            bit[j] += value
            j += j & -j
    return bit


def _gcd_remainders(a: int, b: int) -> list[int]:
    values: list[int] = []
    while b:
        r = a % b
        values.append(r)
        a, b = b, r
    return values


def _bits_lsb_first(value: int) -> list[int]:
    if value == 0:
        return [0]
    bits: list[int] = []
    while value:
        bits.append(value & 1)
        value >>= 1
    return bits


def _fast_power_powers(base: int, exponent: int, mod: int) -> list[int]:
    count = len(_bits_lsb_first(exponent))
    powers: list[int] = []
    cur = base % mod
    for _ in range(count):
        powers.append(cur)
        cur = (cur * cur) % mod
    return powers


def _sieve_flags(n: int) -> list[bool]:
    if n < 0:
        return []
    flags = [True] * (n + 1)
    if n >= 0:
        flags[0] = False
    if n >= 1:
        flags[1] = False
    p = 2
    while p * p <= n:
        if flags[p]:
            m = p * p
            while m <= n:
                flags[m] = False
                m += p
        p += 1
    return flags


def _comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for i in range(1, k + 1):
        result = result * (n - k + i) // i
    return result


def _lowbit_parts(value: int) -> list[int]:
    parts: list[int] = []
    while value:
        low = value & -value
        parts.append(low)
        value -= low
    return parts


def _tree_height(node: str, children: dict[str, list[str]]) -> int:
    kids = children.get(node, [])
    if not kids:
        return 1
    return 1 + max(_tree_height(child, children) for child in kids)


def _dict_int(data: dict[Any, Any], key: Any, *, default: int | None = None) -> int | None:
    value = _dict_lookup(data, key)
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return default


def _node_weight(tree: dict[str, Any], node_id: str) -> int:
    for node in tree.get("nodes") or []:
        if not isinstance(node, dict) or str(node.get("id")) != node_id:
            continue
        value = node.get("weight", node.get("value", node.get("label", 1)))
        if isinstance(value, bool):
            return 1
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.lstrip("-").isdigit():
            return int(value)
        return 1
    return 1


def _validate_tarjan_lowlink(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        dfn = state.get("dfn") or state.get("disc")
        low = state.get("low") or state.get("lowlink")
        if not isinstance(dfn, dict) or not isinstance(low, dict):
            continue
        for node, value in low.items():
            if _dict_lookup(dfn, node) is not None and isinstance(value, int) and isinstance(_dict_lookup(dfn, node), int) and value > _dict_lookup(dfn, node):
                errors.append(f"第 {event.step} 步 low[{node}] 大于 dfn[{node}]")
        stack = state.get("stack")
        on_stack = state.get("on_stack")
        if isinstance(stack, list) and isinstance(on_stack, dict):
            stack_nodes = {str(node) for node in stack}
            for node, flagged in on_stack.items():
                if flagged is True and str(node) not in stack_nodes:
                    errors.append(f"第 {event.step} 步 Tarjan on_stack[{node}] 为 True 但节点不在 stack 中")
        component = state.get("component")
        if isinstance(component, list) and isinstance(stack, list):
            stack_nodes = {str(node) for node in stack}
            overlap = [node for node in component if str(node) in stack_nodes]
            if overlap:
                errors.append(f"第 {event.step} 步 Tarjan component 节点仍在 stack 中：{overlap[0]}")
    return errors


def _validate_articulation_bridges(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        dfn = state.get("dfn") or state.get("disc")
        low = state.get("low") or state.get("lowlink")
        parent = state.get("parent")
        if not isinstance(dfn, dict) or not isinstance(low, dict) or not isinstance(parent, dict):
            continue
        bridges = state.get("bridges")
        if isinstance(bridges, list):
            for edge in bridges:
                u, v = _edge_uv(edge)
                if u is None or v is None:
                    continue
                parent_u = _dict_lookup(parent, u)
                parent_v = _dict_lookup(parent, v)
                if _same_node(parent_v, u):
                    ancestor, child = u, v
                elif _same_node(parent_u, v):
                    ancestor, child = v, u
                else:
                    errors.append(f"第 {event.step} 步 桥 {u}-{v} 不是 DFS 树边")
                    continue
                child_low = _dict_int(low, child)
                ancestor_dfn = _dict_int(dfn, ancestor)
                if child_low is not None and ancestor_dfn is not None and child_low <= ancestor_dfn:
                    errors.append(f"第 {event.step} 步 桥 {ancestor}-{child} 不满足 low[{child}] > dfn[{ancestor}]")
        articulation = state.get("articulation")
        if isinstance(articulation, list):
            children = _children_by_parent(parent)
            for node in articulation:
                node_dfn = _dict_int(dfn, node)
                if node_dfn is None:
                    continue
                kids = children.get(str(node), [])
                root = _dict_lookup(parent, node) in {None, ""}
                if root:
                    if len(kids) <= 1:
                        errors.append(f"第 {event.step} 步 割点 {node} 是根节点但 DFS 子节点不足两个")
                    continue
                if not any((_dict_int(low, child) is not None and _dict_int(low, child) >= node_dfn) for child in kids):
                    errors.append(f"第 {event.step} 步 割点 {node} 缺少满足 low[child] >= dfn[{node}] 的子节点")
    return errors


def _children_by_parent(parent: dict[Any, Any]) -> dict[str, list[Any]]:
    children: dict[str, list[Any]] = {}
    for node, raw_parent in parent.items():
        if raw_parent in {None, ""}:
            continue
        children.setdefault(str(raw_parent), []).append(node)
    return children


def _validate_bipartite_matching(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        match = state.get("match")
        if not isinstance(match, dict):
            continue
        graph = state.get("graph") if isinstance(state.get("graph"), dict) else {}
        left_nodes = {str(node) for node in state.get("left_nodes", []) if node is not None}
        right_nodes = {str(node) for node in state.get("right_nodes", []) if node is not None}
        if not left_nodes and not right_nodes:
            left_nodes, right_nodes = _infer_bipartite_sides(graph, match)
        right_owner: dict[str, Any] = {}
        for left in left_nodes:
            mate = _dict_lookup(match, left)
            if mate in {None, ""}:
                continue
            if str(mate) not in right_nodes:
                errors.append(f"第 {event.step} 步 匹配 match[{left}] 指向非右侧点 {mate}")
            if graph and not _graph_has_edge(graph, left, mate):
                errors.append(f"第 {event.step} 步 匹配边 {left}-{mate} 不存在于 graph")
            previous = right_owner.get(str(mate))
            if previous is not None and not _same_node(previous, left):
                errors.append(f"第 {event.step} 步 匹配冲突：右侧点 {mate} 同时匹配 {previous} 和 {left}")
            right_owner[str(mate)] = left
            reverse = _dict_lookup(match, mate)
            if reverse not in {None, ""} and not _same_node(reverse, left):
                errors.append(f"第 {event.step} 步 匹配不一致：match[{left}]={mate} 但 match[{mate}]={reverse}")
        for right in right_nodes:
            mate = _dict_lookup(match, right)
            if mate in {None, ""}:
                continue
            if str(mate) not in left_nodes:
                errors.append(f"第 {event.step} 步 匹配 match[{right}] 指向非左侧点 {mate}")
            reverse = _dict_lookup(match, mate)
            if reverse not in {None, ""} and not _same_node(reverse, right):
                errors.append(f"第 {event.step} 步 匹配不一致：match[{right}]={mate} 但 match[{mate}]={reverse}")
    return errors


def _infer_bipartite_sides(graph: dict[Any, Any], match: dict[Any, Any]) -> tuple[set[str], set[str]]:
    left_nodes = {str(node) for node in graph}
    right_nodes = {str(nei) for neighbors in graph.values() if isinstance(neighbors, list) for nei in neighbors}
    if not left_nodes:
        for node, mate in match.items():
            if str(node).startswith("L"):
                left_nodes.add(str(node))
            if str(node).startswith("R"):
                right_nodes.add(str(node))
            if str(mate).startswith("L"):
                left_nodes.add(str(mate))
            if str(mate).startswith("R"):
                right_nodes.add(str(mate))
    return left_nodes, right_nodes


def _graph_has_edge(graph: dict[Any, Any], left: Any, right: Any) -> bool:
    neighbors = _dict_lookup(graph, left)
    return isinstance(neighbors, list) and any(_same_node(nei, right) for nei in neighbors)


def _validate_flow_capacity(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        capacity = state.get("capacity") or state.get("cap")
        flow = state.get("flow")
        if not isinstance(capacity, dict) or not isinstance(flow, dict):
            continue
        graph = state.get("graph") if isinstance(state.get("graph"), dict) else {}
        source = _dict_lookup(trace.input_data, "source") if isinstance(trace.input_data, dict) else state.get("source")
        sink = _dict_lookup(trace.input_data, "sink") if isinstance(trace.input_data, dict) else state.get("sink")
        for edge, raw_value in flow.items():
            value = _as_int(raw_value)
            cap = _as_int(_dict_lookup(capacity, edge))
            if value is None:
                continue
            if value < 0:
                errors.append(f"第 {event.step} 步 flow[{edge}] 为负数")
            if cap is not None and value > cap:
                errors.append(f"第 {event.step} 步 flow[{edge}] 超过容量 {cap}")
            if cap is None and graph:
                u, v = _flow_edge_uv(edge)
                if u is not None and v is not None and not _graph_has_edge(graph, u, v):
                    errors.append(f"第 {event.step} 步 flow[{edge}] 不在容量图中")
        balance = _flow_balance(flow)
        for node, value in balance.items():
            if _same_node(node, source) or _same_node(node, sink):
                continue
            if value != 0:
                errors.append(f"第 {event.step} 步 flow 在中间节点 {node} 不守恒：净流 {value}")
        bottleneck = state.get("bottleneck")
        if isinstance(bottleneck, int) and bottleneck < 0:
            errors.append(f"第 {event.step} 步 Edmonds-Karp bottleneck 不能为负数")
    return errors


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _flow_edge_uv(edge: Any) -> tuple[Any, Any]:
    if isinstance(edge, str) and "->" in edge:
        return tuple(edge.split("->", 1))
    return _edge_uv(edge)


def _flow_balance(flow: dict[Any, Any]) -> dict[str, int]:
    balance: dict[str, int] = {}
    for edge, raw_value in flow.items():
        value = _as_int(raw_value)
        if value is None:
            continue
        u, v = _flow_edge_uv(edge)
        if u is None or v is None:
            continue
        balance[str(u)] = balance.get(str(u), 0) - value
        balance[str(v)] = balance.get(str(v), 0) + value
    return balance


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


def _edge_uv(edge: Any) -> tuple[Any, Any]:
    if isinstance(edge, dict):
        return edge.get("u", edge.get("from")), edge.get("v", edge.get("to"))
    if isinstance(edge, (list, tuple)) and len(edge) >= 2:
        return edge[0], edge[1]
    return None, None


def _find(parent: dict[Any, Any], node: Any) -> Any:
    while parent[node] != node:
        parent[node] = parent[parent[node]]
        node = parent[node]
    return node


def _validate_convex_hull(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        geometry = (event.state or {}).get("geometry")
        if not isinstance(geometry, dict):
            continue
        points = _point_map(geometry.get("points") or [])
        hull = geometry.get("hull")
        if not isinstance(hull, list) or len(hull) < 3:
            continue
        coords = [points.get(str(pid)) for pid in hull]
        if any(p is None for p in coords):
            errors.append(f"第 {event.step} 步 hull 引用了不存在的点")
            continue
        signs = []
        for i in range(len(coords)):
            a, b, c = coords[i], coords[(i + 1) % len(coords)], coords[(i + 2) % len(coords)]
            cross = _cross(a, b, c)
            if cross:
                signs.append(cross > 0)
        if signs and any(s != signs[0] for s in signs):
            errors.append(f"第 {event.step} 步 hull 不是一致转向的凸多边形")
    return errors


def _point_map(points: list[Any]) -> dict[str, tuple[float, float]]:
    result = {}
    for i, point in enumerate(points):
        if isinstance(point, dict):
            point_id = str(point.get("id", i))
            x, y = point.get("x"), point.get("y")
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            point_id = str(i)
            x, y = point[0], point[1]
        else:
            continue
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            result[point_id] = (float(x), float(y))
    return result


def _cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _validate_backtracking_tree(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        tree = (event.state or {}).get("recursion_tree") or (event.state or {}).get("search_tree")
        if not isinstance(tree, dict):
            continue
        nodes, edges = _tree_nodes_edges(tree)
        roots = _roots(nodes, edges)
        if len(roots) != 1:
            errors.append(f"第 {event.step} 步回溯搜索树应只有一个根")
        children = _children_map(edges)
        seen = set()
        stack = roots[:]
        while stack:
            node = stack.pop()
            if node in seen:
                errors.append(f"第 {event.step} 步回溯搜索树存在重复访问节点：{node}")
                break
            seen.add(node)
            stack.extend(children.get(node, []))
        if len(edges) > max(0, len(nodes) - 1):
            errors.append(f"第 {event.step} 步回溯搜索树边数超过节点数约束")
    return errors
