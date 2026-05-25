"""Process-level validation for semantic traces.

These checks sit between schema validation and rendering. They do not try to
prove every algorithm, but they catch common inconsistencies in generated
traces: impossible set events, missing dependencies, and family-level invariant
violations for a small set of well-understood visual forms.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
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
    return _run_error_only_checks(
        trace,
        [
            _validate_heap_property,
            _validate_monotonic_stack,
            _validate_union_find_forest,
            _validate_topological_order,
            _validate_bst_order,
            _validate_mst_edges,
            _validate_convex_hull,
            _validate_backtracking_tree,
        ],
    )


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
    if _looks_like_binary_search(trace):
        errors.extend(_validate_binary_search_window(trace))
    if _looks_like_ml_training(trace):
        errors.extend(_validate_ml_correctness(trace))
    family_errors, family_warnings = _run_error_only_checks(
        trace,
        [
            _validate_dijkstra_distances,
            _validate_lcs_dp,
            _validate_edit_distance_dp,
            _validate_kmp_prefix,
            _validate_complete_knapsack,
            _validate_interval_dp,
            _validate_lca_node,
            _validate_tarjan_lowlink,
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
            if key in reason and not any(ref == key or ref.startswith(f"{key}[") or ref.startswith(f"{key}:") for ref in refs):
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
    return errors


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


def _looks_like_binary_search(trace: SemanticTrace) -> bool:
    if not isinstance(trace.input_data, dict):
        return False
    return isinstance(trace.input_data.get("nums"), list) and "target" in trace.input_data


def _validate_binary_search_window(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    nums = trace.input_data.get("nums")
    if not isinstance(nums, list):
        return errors
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
    return errors


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
    return errors


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
    return errors


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


def _validate_tarjan_lowlink(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        dfn = state.get("dfn") or state.get("disc")
        low = state.get("low") or state.get("lowlink")
        if not isinstance(dfn, dict) or not isinstance(low, dict):
            continue
        for node, value in low.items():
            if node in dfn and isinstance(value, int) and isinstance(dfn[node], int) and value > dfn[node]:
                errors.append(f"第 {event.step} 步 low[{node}] 大于 dfn[{node}]")
    return errors


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
