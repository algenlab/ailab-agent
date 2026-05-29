"""Validate whether a trace is ready for a teaching demo."""

from __future__ import annotations

from algolab.schemas.demo_readiness import DemoReadinessReport, DemoReadinessVariantReport
from algolab.schemas.semantic_trace import SemanticEvent, SemanticOp, SemanticTrace, SolutionVariant


DEMO_FAILURE_TYPES = {
    "demo_warn",
    "demo_missing_reason",
    "demo_missing_deps",
    "demo_missing_state",
    "demo_state_jump",
    "demo_algorithm_mismatch",
    "demo_key_step_missing",
}

_TRANSITION_OPS = {
    SemanticOp.SET,
    SemanticOp.MOVE,
    SemanticOp.PUSH,
    SemanticOp.POP,
    SemanticOp.LINK,
    SemanticOp.UNLINK,
    SemanticOp.COMPARE,
    SemanticOp.ENTER,
    SemanticOp.EXIT,
}

_DEPS_REQUIRED_OPS = {
    SemanticOp.SET,
    SemanticOp.LINK,
    SemanticOp.UNLINK,
}


def validate_demo_readiness(variants: list[SolutionVariant]) -> DemoReadinessReport:
    variant_reports = [
        validate_variant_demo_readiness(variant.id, variant.name, variant.trace)
        for variant in variants
        if variant.trace is not None
    ]
    return demo_readiness_report_from_variants(variant_reports)


def demo_readiness_report_from_variants(
    variant_reports: list[DemoReadinessVariantReport],
) -> DemoReadinessReport:
    errors = [
        f"{report.variant_name or report.variant_id}: {error}"
        for report in variant_reports
        for error in report.errors
    ]
    warnings = [
        f"{report.variant_name or report.variant_id}: {warning}"
        for report in variant_reports
        for warning in report.warnings
    ]
    checks = [
        f"{report.variant_name or report.variant_id}: {check}"
        for report in variant_reports
        for check in report.checks
    ]
    if errors:
        status = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "pass"
    return DemoReadinessReport(
        status=status,
        errors=errors,
        warnings=warnings,
        checks=checks,
        variants=variant_reports,
    )


def validate_variant_demo_readiness(
    variant_id: str,
    variant_name: str,
    trace: SemanticTrace | None,
) -> DemoReadinessVariantReport:
    if trace is None:
        return DemoReadinessVariantReport(
            variant_id=variant_id,
            variant_name=variant_name,
            status="fail",
            errors=[_demo_error("demo_key_step_missing", "缺少可演示 trace")],
            phase_coverage=_empty_phase_coverage(),
        )

    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []
    phase_coverage = _phase_coverage(trace)
    key_events = _key_events(trace)

    for event in key_events:
        prefix = f"step {event.step}"
        if not event.reason.strip():
            errors.append(_demo_error("demo_missing_reason", f"{prefix} 缺少 reason"))
        if not event.state:
            errors.append(_demo_error("demo_missing_state", f"{prefix} 缺少可复原 state"))
        if _needs_deps(event) and not event.deps:
            errors.append(_demo_error("demo_missing_deps", f"{prefix} 缺少 deps"))

    for phase in ("initialization", "answer"):
        covered = phase_coverage[phase]
        if not covered:
            errors.append(_demo_error("demo_key_step_missing", f"缺少 {phase} 阶段"))

    if _algorithm_mismatch(trace):
        errors.append(_demo_error("demo_algorithm_mismatch", "algorithm 与 trace 过程存在明显矛盾"))

    errors.extend(_family_rule_errors(trace))

    if not errors:
        checks.append("demo readiness schema passed")
    return DemoReadinessVariantReport(
        variant_id=variant_id,
        variant_name=variant_name,
        status="fail" if errors else ("warn" if warnings else "pass"),
        errors=errors,
        warnings=warnings,
        checks=checks,
        phase_coverage=phase_coverage,
    )


def _demo_error(failure_type: str, message: str) -> str:
    return f"failure_type={failure_type}: {message}"


def _empty_phase_coverage() -> dict[str, bool]:
    return {
        "initialization": False,
        "main_loop": False,
        "transition": False,
        "answer": False,
    }


def _phase_coverage(trace: SemanticTrace) -> dict[str, bool]:
    events = trace.events
    degenerate = (
        len(events) == 1
        and events[0].op == SemanticOp.CREATE
        and bool(events[0].state)
        and bool(events[0].reason.strip())
    )
    return {
        "initialization": any(event.op == SemanticOp.CREATE for event in events),
        "main_loop": degenerate or any(event.op not in {SemanticOp.CREATE, SemanticOp.EXPLAIN} for event in events),
        "transition": degenerate or any(event.op in _TRANSITION_OPS or _is_answer_event(event) for event in events),
        "answer": degenerate or any(_is_answer_event(event) for event in events) or _last_key_event_has_state(events),
    }


def _key_events(trace: SemanticTrace) -> list[SemanticEvent]:
    return [
        event
        for event in trace.events
        if event.op != SemanticOp.EXPLAIN or event.reason.strip() or event.state
    ]


def _is_answer_event(event: SemanticEvent) -> bool:
    if event.role == "answer":
        return True
    if "answer" in event.state:
        return True
    if event.op == SemanticOp.MARK and event.targets:
        return True
    if event.op == SemanticOp.EXPLAIN and event.reason.strip() and event.state:
        return True
    return False


def _last_key_event_has_state(events: list[SemanticEvent]) -> bool:
    for event in reversed(events):
        if event.op == SemanticOp.CREATE:
            continue
        if event.op == SemanticOp.EXPLAIN and not event.reason.strip():
            continue
        return bool(event.state)
    return False


def _needs_deps(event: SemanticEvent) -> bool:
    if event.op not in _DEPS_REQUIRED_OPS:
        return False
    if event.op == SemanticOp.SET and not event.state:
        return True
    reason = event.reason.lower()
    dependency_reason = any(word in reason for word in ("依赖", "来自", "转移", "来源", "根据"))
    has_change_evidence = event.before is not None or event.after is not None
    return dependency_reason and has_change_evidence


def _algorithm_mismatch(trace: SemanticTrace) -> bool:
    algorithm = trace.algorithm.lower()
    reasons = " ".join(event.reason.lower() for event in trace.events)
    has_queue = any("queue" in event.state for event in trace.events)
    has_stack_or_frame = any("stack" in event.state or event.op in {SemanticOp.ENTER, SemanticOp.EXIT} for event in trace.events)
    if "bfs" in algorithm and ("dfs" in reasons or (has_stack_or_frame and not has_queue)):
        return True
    if "dfs" in algorithm and "bfs" in reasons:
        return True
    return False


def _family_rule_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    if _looks_like_dp(trace):
        errors.extend(_dp_demo_errors(trace))
    if _looks_like_graph(trace):
        errors.extend(_graph_demo_errors(trace))
    if _looks_like_array_pointer(trace):
        errors.extend(_array_pointer_demo_errors(trace))
    if _looks_like_monotonic_stack(trace):
        errors.extend(_monotonic_stack_demo_errors(trace))
    if _looks_like_string(trace):
        errors.extend(_string_demo_errors(trace))
    if _looks_like_recursion(trace):
        errors.extend(_recursion_demo_errors(trace))
    if _looks_like_heap(trace):
        errors.extend(_heap_demo_errors(trace))
    if _looks_like_union_find(trace):
        errors.extend(_union_find_demo_errors(trace))
    return _dedupe(errors)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _trace_text(trace: SemanticTrace) -> str:
    parts = [trace.algorithm, *trace.pseudocode]
    parts.extend(event.reason for event in trace.events)
    return " ".join(parts).lower()


def _target_ids(event: SemanticEvent) -> list[str]:
    return [target.id for target in event.targets]


def _dep_ids(event: SemanticEvent) -> list[str]:
    return [dep.id for dep in event.deps]


def _all_states(trace: SemanticTrace) -> list[dict]:
    return [event.state for event in trace.events if event.state]


def _has_state_key(trace: SemanticTrace, *keys: str) -> bool:
    return any(any(key in event.state for key in keys) for event in trace.events)


def _state_contract(trace: SemanticTrace, key: str) -> dict:
    for state in _all_states(trace):
        contract = state.get(key)
        if isinstance(contract, dict):
            return contract
    return {}


def _family_contract(trace: SemanticTrace) -> dict:
    return _state_contract(trace, "family_contract")


def _family_contract_family(trace: SemanticTrace) -> str:
    family = _family_contract(trace).get("family")
    return str(family).lower() if family is not None else ""


def _graph_contract_submode(trace: SemanticTrace) -> str:
    submode = _state_contract(trace, "graph_contract").get("submode")
    return str(submode).lower() if submode is not None else ""


def _array_contract_submode(trace: SemanticTrace) -> str:
    submode = _state_contract(trace, "array_contract").get("submode")
    return str(submode).lower() if submode is not None else ""


def _event_has_target_prefix(event: SemanticEvent, *prefixes: str) -> bool:
    return any(target.startswith(prefixes) for target in _target_ids(event))


def _event_has_dep_prefix(event: SemanticEvent, *prefixes: str) -> bool:
    return any(dep.startswith(prefixes) for dep in _dep_ids(event))


def _is_edge_process_evidence(event: SemanticEvent) -> bool:
    if event.op == SemanticOp.COMPARE and _event_has_target_prefix(event, "edge:"):
        return True
    if not _event_has_dep_prefix(event, "edge:"):
        return False
    if event.op not in {SemanticOp.SET, SemanticOp.MARK, SemanticOp.LINK, SemanticOp.UNLINK}:
        return False
    if event.role in {"visited", "current", "relax", "candidate"}:
        return True
    return _event_has_target_prefix(
        event,
        "node:",
        "dist[",
        "parent[",
        "color[",
        "indegree[",
        "dfn[",
        "low[",
        "match[",
        "flow[",
        "capacity[",
    )


def _is_relax_or_first_visit(event: SemanticEvent) -> bool:
    targets = _target_ids(event)
    if event.role == "visited":
        return True
    return any(
        target.startswith(("dist[", "parent[", "match[", "flow[", "capacity[", "indegree["))
        for target in targets
    )


def _has_formula_evidence(trace: SemanticTrace) -> bool:
    if any(state.get("formula") for state in _all_states(trace)):
        return True
    if any(event.teaching and event.teaching.formula for event in trace.events):
        return True
    text = " ".join(trace.pseudocode).lower()
    return any(token in text for token in ("=", "max(", "min(", "dp[", "gcd(", "转移"))


def _has_answer_reference(trace: SemanticTrace, target_id: str) -> bool:
    if not target_id:
        return True
    for event in trace.events:
        if not _is_answer_event(event):
            continue
        ids = [*_target_ids(event), *_dep_ids(event)]
        if target_id in ids:
            return True
    return False


def _looks_like_dp(trace: SemanticTrace) -> bool:
    text = _trace_text(trace)
    return (
        _has_state_key(trace, "dp_contract", "dp")
        or any(token in text for token in ("dynamic programming", "动态规划", "背包", "lcs", "编辑距离"))
        or any(target.startswith("dp[") for event in trace.events for target in _target_ids(event))
    )


def _dp_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    contract = _state_contract(trace, "dp_contract")
    containers = contract.get("containers") if isinstance(contract.get("containers"), list) else ["dp"]
    has_init = any(
        event.op == SemanticOp.CREATE and any(container in event.state for container in containers)
        for event in trace.events
    )
    if not has_init:
        errors.append(_demo_error("demo_key_step_missing", "DP 演示缺少包含 DP 容器的初始化帧"))

    transition_events = [
        event
        for event in trace.events
        if event.op == SemanticOp.SET and any(target.startswith("dp[") for target in _target_ids(event))
    ]
    expected_targets = contract.get("expected_targets")
    requires_transition = bool(expected_targets) or any(event.op == SemanticOp.COMPARE and any(target.startswith("dp[") for target in _target_ids(event)) for event in trace.events)
    if requires_transition and not transition_events:
        errors.append(_demo_error("demo_key_step_missing", "DP 演示缺少状态转移写入帧"))
    elif any(not event.deps for event in transition_events):
        errors.append(_demo_error("demo_missing_deps", "DP 转移帧缺少来源 deps"))

    if requires_transition and not _has_formula_evidence(trace):
        errors.append(_demo_error("demo_algorithm_mismatch", "DP 演示缺少可见转移公式"))

    answer_position = str(contract.get("answer_position") or "")
    if answer_position and not _has_answer_reference(trace, answer_position):
        errors.append(_demo_error("demo_algorithm_mismatch", f"DP 答案帧没有引用 answer_position={answer_position}"))
    return errors


def _looks_like_graph(trace: SemanticTrace) -> bool:
    if _has_state_key(trace, "graph_contract", "graph", "weighted_graph"):
        return True
    return any(_event_has_target_prefix(event, "edge:") for event in trace.events) and _has_state_key(trace, "graph", "weighted_graph")


def _graph_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    has_frontier = _has_state_key(trace, "queue", "frontier", "stack", "heap")
    has_visit_state = _has_state_key(
        trace,
        "visited",
        "dist",
        "parent",
        "color",
        "indegree",
        "dfn",
        "low",
        "on_stack",
        "match",
        "flow",
        "union_find",
        "mst_edges",
        "current_edge",
        "edge_decision",
    )
    if not (has_frontier or has_visit_state):
        errors.append(_demo_error("demo_algorithm_mismatch", "图演示缺少 frontier/visited/dist 等过程状态"))

    submode = _graph_contract_submode(trace)
    if submode in {"bfs", "dfs", "connected_components", "topological_sort", "bipartite", "dijkstra", "bellman_ford", "zero_one_bfs", "mst", "kruskal"}:
        if _graph_has_edges(trace) and not any(_is_edge_process_evidence(event) for event in trace.events):
            errors.append(_demo_error("demo_key_step_missing", "图演示缺少边检查帧"))
        for event in trace.events:
            if _is_relax_or_first_visit(event) and not event.deps:
                errors.append(_demo_error("demo_missing_deps", f"step {event.step} 图首次访问或 relax 缺少 deps"))
    return errors


def _graph_has_edges(trace: SemanticTrace) -> bool:
    for state in _all_states(trace):
        graph = state.get("graph") or state.get("weighted_graph")
        if isinstance(graph, dict):
            for neighbors in graph.values():
                if isinstance(neighbors, dict) and neighbors:
                    return True
                if isinstance(neighbors, list) and neighbors:
                    return True
        edges = state.get("edges")
        if isinstance(edges, list) and edges:
            return True
    return any(_event_has_target_prefix(event, "edge:") for event in trace.events)


def _looks_like_array_pointer(trace: SemanticTrace) -> bool:
    text = _trace_text(trace)
    return (
        bool(_state_contract(trace, "array_contract"))
        or _has_state_key(trace, "left", "right", "mid", "window_sum", "slow", "fast")
        or any(_event_has_target_prefix(event, "pointer:") for event in trace.events)
        or any(token in text for token in ("binary search", "二分", "滑动窗口", "双指针"))
    )


def _array_pointer_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    submode = _array_contract_submode(trace)
    text = _trace_text(trace)
    is_binary = submode.startswith("binary") or "binary search" in text or "二分查找" in text or "二分答案" in text
    if is_binary:
        if not any("mid" in event.state for event in trace.events):
            errors.append(_demo_error("demo_algorithm_mismatch", "二分演示缺少 mid 状态"))
        if not any(event.op == SemanticOp.COMPARE and ("mid" in event.state or _event_has_target_prefix(event, "pointer:mid")) for event in trace.events):
            errors.append(_demo_error("demo_key_step_missing", "二分演示缺少 mid 比较帧"))
        errors.extend(_binary_state_jump_errors(trace))
    elif "sliding_window" in submode or "滑动窗口" in text:
        if not _has_state_key(trace, "left", "right", "window_sum", "window_counts"):
            errors.append(_demo_error("demo_algorithm_mismatch", "窗口演示缺少窗口边界或聚合状态"))
    return errors


def _binary_state_jump_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    previous: SemanticEvent | None = None
    previous_compare = False
    for event in trace.events:
        if "left" not in event.state or "right" not in event.state:
            previous = event
            previous_compare = event.op == SemanticOp.COMPARE and "mid" in event.state
            continue
        if previous and "left" in previous.state and "right" in previous.state:
            old_left, old_right = previous.state.get("left"), previous.state.get("right")
            new_left, new_right = event.state.get("left"), event.state.get("right")
            if all(isinstance(value, int) for value in (old_left, old_right, new_left, new_right)):
                left_jump = abs(new_left - old_left) > 1
                right_jump = abs(new_right - old_right) > 1
                if event.op == SemanticOp.MOVE and (left_jump or right_jump) and not previous_compare:
                    errors.append(_demo_error("demo_state_jump", f"step {event.step} 二分区间无比较证据就发生跳变"))
        previous = event
        previous_compare = event.op == SemanticOp.COMPARE and "mid" in event.state
    return errors


def _looks_like_monotonic_stack(trace: SemanticTrace) -> bool:
    text = _trace_text(trace)
    return _has_state_key(trace, "stack_order") or "monotonic" in text or "单调栈" in text or "每日温度" in text


def _monotonic_stack_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    push_events = [event for event in trace.events if event.op == SemanticOp.PUSH]
    pop_events = [event for event in trace.events if event.op == SemanticOp.POP]
    if not push_events:
        errors.append(_demo_error("demo_key_step_missing", "单调栈演示缺少 push 帧"))
    for event in pop_events:
        if not event.deps:
            errors.append(_demo_error("demo_missing_deps", f"step {event.step} 单调栈 pop 缺少被弹元素和当前元素 deps"))
    if pop_events and not any(event.op == SemanticOp.SET and any(target.startswith("answer[") for target in _target_ids(event)) for event in trace.events):
        errors.append(_demo_error("demo_algorithm_mismatch", "单调栈 pop 后缺少被弹元素贡献写入"))
    return errors


def _looks_like_string(trace: SemanticTrace) -> bool:
    text = _trace_text(trace)
    family = _family_contract_family(trace)
    return (
        family == "string"
        or _has_state_key(trace, "pi", "z", "radius", "window_hashes", "window_counts", "prefix_count")
        or any(token in text for token in ("kmp", "rabin", "z algorithm", "manacher", "字符串滑动窗口", "最长子串"))
    )


def _string_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    if _family_contract_family(trace) == "trie" or _has_state_key(trace, "trie"):
        if not _has_state_key(trace, "trie", "prefix_count"):
            errors.append(_demo_error("demo_algorithm_mismatch", "Trie 字符串演示缺少 trie 或 prefix_count 状态"))
        return errors
    if _is_degenerate_string_short_path(trace):
        return errors
    has_pointer = _has_state_key(trace, "i", "j", "left", "right") or any(
        _event_has_target_prefix(event, "text[", "pattern[") for event in trace.events
    )
    has_table = _has_state_key(trace, "pi", "z", "radius", "window_hashes", "window_counts", "prefix_count", "trie")
    if not has_pointer:
        errors.append(_demo_error("demo_algorithm_mismatch", "字符串演示缺少文本/模式指针"))
    if not has_table:
        errors.append(_demo_error("demo_algorithm_mismatch", "字符串演示缺少表项、哈希、半径或前缀计数状态"))
    if "kmp" in _trace_text(trace) and not _has_state_key(trace, "pi"):
        errors.append(_demo_error("demo_algorithm_mismatch", "KMP 演示缺少 pi 前缀表"))
    return errors


def _is_degenerate_string_short_path(trace: SemanticTrace) -> bool:
    if len(trace.events) > 2:
        return False
    for event in trace.events:
        state = event.state
        if not ("text" in state and "pattern" in state):
            return False
        pattern = state.get("pattern")
        text = state.get("text")
        if pattern == "" or text == "" or pattern is None or text is None:
            continue
        if isinstance(pattern, str) and isinstance(text, str) and len(pattern) > len(text):
            continue
        return False
    return True


def _looks_like_recursion(trace: SemanticTrace) -> bool:
    family = _family_contract_family(trace)
    return (
        family in {"tree", "backtracking", "recursion"}
        or _has_state_key(trace, "recursion_tree", "call_stack", "path", "used")
        or any(_event_has_target_prefix(event, "frame:") for event in trace.events)
    )


def _recursion_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    family = _family_contract_family(trace)
    has_enter = any(event.op == SemanticOp.ENTER for event in trace.events)
    has_exit = any(event.op == SemanticOp.EXIT for event in trace.events)
    if family == "backtracking" or _has_state_key(trace, "path", "used"):
        if not has_enter:
            errors.append(_demo_error("demo_key_step_missing", "回溯演示缺少选择进入帧"))
        if not has_exit:
            errors.append(_demo_error("demo_state_jump", "回溯演示缺少返回/撤销帧"))
        for event in trace.events:
            if _is_answer_event(event) and event is trace.events[-1] and event.state.get("path"):
                errors.append(_demo_error("demo_state_jump", "回溯最终答案帧仍停留在未撤销路径上"))
    elif has_enter and not has_exit:
        errors.append(_demo_error("demo_state_jump", "递归演示有 enter 但缺少 exit"))
    return errors


def _looks_like_heap(trace: SemanticTrace) -> bool:
    family = _family_contract_family(trace)
    return family == "heap" or _has_state_key(trace, "heap_type", "heap_top")


def _heap_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    if not _has_state_key(trace, "heap_type"):
        errors.append(_demo_error("demo_algorithm_mismatch", "堆演示缺少 heap_type 不变量"))
    for event in trace.events:
        if event.op in {SemanticOp.PUSH, SemanticOp.POP} and "heap" not in event.state:
            errors.append(_demo_error("demo_algorithm_mismatch", f"step {event.step} 堆结构变化后缺少 heap state"))
    if any(event.op in {SemanticOp.PUSH, SemanticOp.POP} for event in trace.events) and not _has_state_key(trace, "heap_top"):
        errors.append(_demo_error("demo_algorithm_mismatch", "堆演示缺少 heap_top 或等价结构不变量"))
    return errors


def _looks_like_union_find(trace: SemanticTrace) -> bool:
    text = _trace_text(trace)
    return _has_state_key(trace, "union_find", "dsu") or "union find" in text or "并查集" in text


def _union_find_demo_errors(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    if not _has_state_key(trace, "union_find", "dsu"):
        errors.append(_demo_error("demo_algorithm_mismatch", "并查集演示缺少 parent/forest 状态"))
    for event in trace.events:
        if event.op == SemanticOp.LINK and not ("union_find" in event.state or "dsu" in event.state):
            errors.append(_demo_error("demo_algorithm_mismatch", f"step {event.step} union 后缺少结构变化后的 parent 状态"))
    return errors
