"""Process validators: hash, sorting, linked list, greedy."""

from __future__ import annotations

from algolab.verification.process_families.common import *


def _validate_hash_map_process(trace: SemanticTrace) -> list[str]:
    if not _trace_has_hash_signal(trace):
        return []
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        contract = state.get("hash_contract") if isinstance(state.get("hash_contract"), dict) else {}
        submode = str(contract.get("submode") or state.get("hash_submode") or "").lower()
        if submode in {"two_sum", "two-sum"} or _looks_like_two_sum_state(state):
            errors.extend(_validate_two_sum_hash_event(event))
    return errors


def _trace_has_hash_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if any(token in algorithm for token in ("two sum", "hash", "map", "哈希", "两数之和")):
        return True
    for event in trace.events:
        state = event.state or {}
        if isinstance(state.get("hash_contract"), dict) or isinstance(state.get("seen"), dict) or isinstance(state.get("count"), dict):
            return True
    return False


def _looks_like_two_sum_state(state: dict[str, Any]) -> bool:
    return isinstance(state.get("nums"), list) and "target" in state and isinstance(state.get("seen"), dict)


def _validate_two_sum_hash_event(event) -> list[str]:
    state = event.state or {}
    nums = state.get("nums")
    seen = state.get("seen")
    target = state.get("target")
    i = state.get("i")
    errors: list[str] = []
    if not isinstance(nums, list) or not isinstance(seen, dict) or not isinstance(target, (int, float)):
        return errors
    if isinstance(i, int) and 0 <= i < len(nums):
        expected_need = target - nums[i]
        need = state.get("need", expected_need)
        if need != expected_need:
            errors.append(f"第 {event.step} 步 哈希 two_sum need 应为 {expected_need}，实际为 {need}")
        exists = state.get("exists")
        actual_exists = _dict_lookup(seen, expected_need) is not None
        if isinstance(exists, bool) and exists != actual_exists:
            errors.append(f"第 {event.step} 步 哈希命中状态错误：seen[{expected_need}] {'已写入' if actual_exists else '未写入'}")
        if event.op == SemanticOp.COMPARE and event.deps:
            for dep in _event_dep_ids(event):
                if dep.startswith("seen["):
                    key = dep.removeprefix("seen[").removesuffix("]")
                    if _dict_lookup(seen, key) is None:
                        errors.append(f"第 {event.step} 步 哈希依赖 {dep} 未写入")
        if event.role == "answer" or "answer" in state:
            answer = state.get("answer", event.value)
            if isinstance(answer, list) and len(answer) == 2 and all(isinstance(index, int) for index in answer):
                left, right = answer
                if not (0 <= left < len(nums) and 0 <= right < len(nums)):
                    errors.append(f"第 {event.step} 步 哈希 two_sum 答案下标越界")
                elif nums[left] + nums[right] != target:
                    errors.append(f"第 {event.step} 步 哈希 two_sum 答案不满足 nums[i]+nums[j]=target")
                current_index = i if isinstance(i, int) else right
                other_index = left if right == current_index else right
                other_value = nums[other_index] if 0 <= other_index < len(nums) else None
                if other_value is not None and _dict_lookup(seen, other_value) is None:
                    errors.append(f"第 {event.step} 步 哈希答案依赖 seen[{other_value}] 未写入")
    if event.op == SemanticOp.SET:
        for target in _event_target_ids(event):
            if not target.startswith("seen["):
                continue
            key = target.removeprefix("seen[").removesuffix("]")
            stored = _dict_lookup(seen, key)
            if stored is None:
                errors.append(f"第 {event.step} 步 哈希写入 {target} 后 state.seen 缺少该 key")
            elif isinstance(i, int) and 0 <= i < len(nums) and str(key) == str(nums[i]) and stored != i:
                errors.append(f"第 {event.step} 步 哈希 seen[{key}] 应写入当前下标 {i}，实际为 {stored}")
    return errors


def _validate_sorting_process(trace: SemanticTrace) -> list[str]:
    if not _trace_has_sorting_signal(trace):
        return []
    errors: list[str] = []
    original = _sorting_original_input(trace)
    for event in trace.events:
        state = event.state or {}
        contract = state.get("sorting_contract") if isinstance(state.get("sorting_contract"), dict) else {}
        submode = str(contract.get("submode") or state.get("sorting_submode") or "").lower()
        if submode in {"insertion_sort", "insertion-sort", ""} and _sorting_state_array(state) is not None:
            errors.extend(_validate_insertion_sort_state(event, original))
    final = _sorting_final_array(trace)
    if original is not None and final is not None and sorted(final) != sorted(original):
        errors.append("排序结果未保持输入多重集")
    if original is not None and final is not None and final != sorted(original):
        errors.append("排序最终结果不是升序")
    return errors


def _trace_has_sorting_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if any(token in algorithm for token in ("sort", "排序")):
        return True
    for event in trace.events:
        if isinstance((event.state or {}).get("sorting_contract"), dict):
            return True
    return False


def _sorting_original_input(trace: SemanticTrace) -> list[Any] | None:
    nums = trace.input_data.get("nums") if isinstance(trace.input_data, dict) else None
    return list(nums) if isinstance(nums, list) else None


def _sorting_state_array(state: dict[str, Any]) -> list[Any] | None:
    nums = state.get("nums")
    return list(nums) if isinstance(nums, list) else None


def _validate_insertion_sort_state(event, original: list[Any] | None) -> list[str]:
    state = event.state or {}
    arr = _sorting_state_array(state)
    if arr is None:
        return []
    errors: list[str] = []
    if (event.role == "answer" or state.get("answer") is not None) and original is not None and sorted(arr) != sorted(original):
        errors.append(f"第 {event.step} 步 排序状态未保持输入多重集")
    i = state.get("i")
    if isinstance(i, int) and 0 <= i < len(arr):
        prefix_end = min(i + 1, len(arr))
        if event.role == "answer" or event.op == SemanticOp.SET:
            prefix = arr[:prefix_end]
            if prefix != sorted(prefix):
                errors.append(f"第 {event.step} 步 排序有序前缀 nums[0:{prefix_end}] 不升序")
    if event.role == "answer" and state.get("answer") is not None:
        answer = state.get("answer")
        if isinstance(answer, list) and answer != sorted(answer):
            errors.append(f"第 {event.step} 步 排序 answer 不是升序")
    return errors


def _sorting_final_array(trace: SemanticTrace) -> list[Any] | None:
    for event in reversed(trace.events):
        state = event.state or {}
        answer = state.get("answer")
        if isinstance(answer, list):
            return list(answer)
        arr = _sorting_state_array(state)
        if arr is not None:
            return arr
    return trace.result if isinstance(trace.result, list) else None


def _validate_linked_list_process(trace: SemanticTrace) -> list[str]:
    if not _trace_has_linked_list_signal(trace):
        return []
    errors: list[str] = []
    expected_current = _linked_head_id(trace)
    active_current: str | None = None
    visited: set[str] = set()
    for event in trace.events:
        state = event.state or {}
        linked = state.get("linked_list")
        if not isinstance(linked, dict):
            continue
        current = state.get("current")
        prev = state.get("prev")
        next_node = state.get("next")
        if event.op == SemanticOp.MOVE and current is not None:
            current_id = str(current)
            if expected_current is not None and current_id != expected_current:
                errors.append(f"第 {event.step} 步 链表 current 应为 {expected_current}，实际为 {current_id}")
            active_current = current_id
            visited.add(current_id)
            expected_current = str(next_node) if next_node is not None else None
        elif event.op in {SemanticOp.LINK, SemanticOp.UNLINK, SemanticOp.SET} and current is not None:
            current_id = str(current)
            expected = active_current or expected_current
            if expected is not None and current_id != expected:
                errors.append(f"第 {event.step} 步 链表 current 应为 {expected}，实际为 {current_id}")
            visited.add(current_id)
        next_map = _linked_next_map(linked)
        edges = _linked_edges(linked)
        for node, mapped_next in next_map.items():
            if mapped_next is not None and (node, mapped_next) not in edges:
                errors.append(f"第 {event.step} 步 链表 next 状态缺少对应 edge:{node}->{mapped_next}")
        if event.role == "answer" or "answer" in state:
            answer = state.get("answer", event.value)
            values = _linked_values_in_order(linked, str(prev) if prev is not None else None)
            if isinstance(answer, list) and values and answer != values:
                errors.append(f"第 {event.step} 步 链表 answer 与 next 链顺序不一致")
    return errors


def _trace_has_linked_list_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if any(token in algorithm for token in ("linked", "链表")):
        return True
    return any(isinstance((event.state or {}).get("linked_list"), dict) for event in trace.events)


def _linked_head_id(trace: SemanticTrace) -> str | None:
    for event in trace.events:
        state = event.state or {}
        head = state.get("head")
        if head is not None:
            return str(head)
        linked = state.get("linked_list")
        if isinstance(linked, dict):
            nodes = linked.get("nodes")
            if isinstance(nodes, list) and nodes:
                first = nodes[0]
                if isinstance(first, dict) and first.get("id") is not None:
                    return str(first["id"])
    return None


def _linked_next_map(linked: dict[str, Any]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for node in linked.get("nodes") or []:
        if not isinstance(node, dict) or node.get("id") is None:
            continue
        node_id = str(node["id"])
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        next_value = node.get("next", meta.get("next"))
        result[node_id] = str(next_value) if next_value is not None else None
    return result


def _linked_edges(linked: dict[str, Any]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for edge in linked.get("edges") or []:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            edges.add((str(edge[0]), str(edge[1])))
        elif isinstance(edge, dict) and edge.get("source") is not None and edge.get("target") is not None:
            edges.add((str(edge["source"]), str(edge["target"])))
    return edges


def _linked_values_in_order(linked: dict[str, Any], head: str | None) -> list[Any]:
    if head is None:
        return []
    next_map = _linked_next_map(linked)
    values = {}
    for node in linked.get("nodes") or []:
        if isinstance(node, dict) and node.get("id") is not None:
            values[str(node["id"])] = node.get("value", node.get("label", node.get("id")))
    result = []
    seen: set[str] = set()
    current = head
    while current is not None and current not in seen:
        seen.add(current)
        result.append(values.get(current, current))
        current = next_map.get(current)
    return result


def _validate_greedy_process(trace: SemanticTrace) -> list[str]:
    if not _trace_has_greedy_signal(trace):
        return []
    errors: list[str] = []
    previous_reach: int | None = None
    for event in trace.events:
        state = event.state or {}
        contract = state.get("greedy_contract") if isinstance(state.get("greedy_contract"), dict) else {}
        submode = str(contract.get("submode") or state.get("greedy_submode") or "").lower()
        if submode in {"jump_game", "jump-game"} or _looks_like_jump_game_state(state):
            errors.extend(_validate_jump_game_event(event, previous_reach))
            reach = state.get("reach", state.get("max_reach"))
            if isinstance(reach, int):
                previous_reach = reach
    return errors


def _trace_has_greedy_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if any(token in algorithm for token in ("greedy", "贪心", "跳跃游戏", "jump game")):
        return True
    return any(isinstance((event.state or {}).get("greedy_contract"), dict) for event in trace.events)


def _looks_like_jump_game_state(state: dict[str, Any]) -> bool:
    return isinstance(state.get("nums"), list) and ("reach" in state or "max_reach" in state)


def _validate_jump_game_event(event, fallback_previous_reach: int | None = None) -> list[str]:
    state = event.state or {}
    nums = state.get("nums")
    i = state.get("i")
    reach = state.get("reach", state.get("max_reach"))
    errors: list[str] = []
    if not isinstance(nums, list) or not isinstance(i, int) or not isinstance(reach, int):
        return errors
    if 0 <= i < len(nums):
        previous_reach = state.get("previous_reach")
        if not isinstance(previous_reach, int):
            previous_reach = state.get("before_reach")
        if not isinstance(previous_reach, int):
            previous_reach = state.get("old_reach")
        if not isinstance(previous_reach, int):
            previous_reach = reach if event.op == SemanticOp.CREATE else fallback_previous_reach
        if previous_reach is not None:
            expected = max(previous_reach, i + nums[i])
            candidate = state.get("candidate_reach", i + nums[i])
            if candidate != i + nums[i]:
                errors.append(f"第 {event.step} 步 贪心 jump_game candidate_reach 应为 {i + nums[i]}，实际为 {candidate}")
            is_unreachable_answer = i > previous_reach and (event.role == "answer" or state.get("answer") is False or event.value is False)
            if event.op in {SemanticOp.SET, SemanticOp.MARK, SemanticOp.MOVE} and not is_unreachable_answer and reach != expected:
                errors.append(f"第 {event.step} 步 贪心 jump_game reach 应为 {expected}，实际为 {reach}")
        if i > reach and not (event.role == "answer" or state.get("answer") is False or event.value is False):
            errors.append(f"第 {event.step} 步 贪心 jump_game 扫描到不可达下标 i={i}, reach={reach}")
    return errors


__all__ = [name for name in globals() if not name.startswith("__")]
