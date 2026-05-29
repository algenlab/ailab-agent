"""Process validators: array pointer."""

from __future__ import annotations

from algolab.verification.process_families.common import *

def _validate_array_pointer_contract(trace: SemanticTrace) -> list[str]:
    contract = _array_contract_for_trace(trace)
    if contract is None:
        return []
    submode = _normalize_array_contract_submode(contract.get("submode"))
    if not submode:
        return ["Array pointer contract 缺少 submode，无法选择数组指针过程合同"]
    if submode not in ARRAY_POINTER_SUBMODES:
        return [f"Array pointer contract 未支持的 submode：{submode}"]
    errors: list[str] = []
    if submode == "prefix_sum":
        errors.extend(_validate_array_contract_prefix_sum(trace, contract))
    elif submode == "difference_array":
        errors.extend(_validate_array_contract_difference_array(trace, contract))
    elif submode == "sliding_window":
        errors.extend(_validate_array_contract_window(trace, contract))
    elif submode in {"two_pointer", "fast_slow"}:
        errors.extend(_validate_array_contract_pointer_bounds(trace, contract))
    elif submode == "binary_answer":
        errors.extend(_validate_array_contract_pointer_bounds(trace, contract))
    errors.extend(_validate_array_contract_expected_targets(trace, contract))
    return errors


def _array_contract_for_trace(trace: SemanticTrace) -> dict[str, Any] | None:
    for event in trace.events:
        contract = (event.state or {}).get("array_contract")
        if isinstance(contract, dict):
            return contract
    return None


def _normalize_array_contract_submode(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "prefix": "prefix_sum",
        "prefixsum": "prefix_sum",
        "prefix_array": "prefix_sum",
        "diff": "difference_array",
        "difference": "difference_array",
        "sliding": "sliding_window",
        "window": "sliding_window",
        "binary_search_answer": "binary_answer",
        "binary_answer_search": "binary_answer",
        "fast_slow_pointer": "fast_slow",
        "slow_fast": "fast_slow",
    }
    return aliases.get(normalized, normalized)


def _array_contract_string_list(contract: dict[str, Any], key: str) -> list[str]:
    raw = contract.get(key)
    if not isinstance(raw, list):
        return []
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()]


def _validate_array_contract_prefix_sum(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums") or state.get("array")
        prefix = state.get("prefix") or state.get("prefix_sum")
        if not _is_numeric_sequence(nums) or not _is_numeric_sequence(prefix):
            continue
        base_zero = len(prefix) == len(nums) + 1
        if len(prefix) not in {len(nums), len(nums) + 1}:
            errors.append(f"第 {event.step} 步 prefix 长度应为 nums 长度或 nums 长度 + 1")
            continue
        target_indices = _array_contract_index_targets(event, {"prefix", "prefix_sum"})
        if not target_indices and event.role == "answer":
            target_indices = set(range(len(prefix)))
        for index in sorted(target_indices):
            if index >= len(prefix):
                continue
            actual = prefix[index]
            if actual is None:
                continue
            if not isinstance(actual, (int, float)):
                continue
            expected = sum(nums[:index]) if base_zero else sum(nums[: index + 1])
            if actual != expected:
                errors.append(f"第 {event.step} 步 prefix[{index}] 应为 {expected}")
    if not any(_event_refs_include_prefix(event, ("prefix[", "prefix_sum[")) for event in trace.events):
        errors.append("Array pointer contract prefix_sum 缺少 prefix 更新 target")
    return errors


def _validate_array_contract_difference_array(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums") or state.get("array")
        diff = state.get("diff") or state.get("difference")
        updates = state.get("updates") or state.get("ranges")
        if not _is_numeric_sequence(nums) or not _is_numeric_sequence(diff) or not isinstance(updates, list):
            continue
        update_index = state.get("update_index")
        active_updates = updates[: update_index + 1] if isinstance(update_index, int) and update_index >= 0 else updates if event.role == "answer" else []
        expected = _expected_diff_after_updates(nums, active_updates, len(diff))
        if expected is None:
            continue
        target_indices = _array_contract_index_targets(event, {"diff", "difference"})
        if not target_indices and event.role == "answer":
            target_indices = set(range(len(diff)))
        for index in sorted(target_indices):
            if index >= len(diff):
                continue
            actual = diff[index]
            if actual is None:
                continue
            if not isinstance(actual, (int, float)):
                continue
            if index < len(expected) and actual != expected[index]:
                errors.append(f"第 {event.step} 步 diff[{index}] 应为 {expected[index]}")
    if not any(_event_refs_include_prefix(event, ("diff[", "difference[")) for event in trace.events):
        errors.append("Array pointer contract difference_array 缺少 diff 更新 target")
    return errors


def _array_contract_index_targets(event, names: set[str]) -> set[int]:
    indices: set[int] = set()
    for target_id in _event_target_ids(event):
        parsed = parse_target(target_id)
        if parsed.kind == "indexed" and parsed.name in names and len(parsed.indices) == 1:
            indices.add(parsed.indices[0])
    return indices


def _expected_diff_after_updates(nums: list[Any], updates: list[Any], length: int) -> list[int | float] | None:
    if length not in {len(nums), len(nums) + 1}:
        return None
    diff: list[int | float] = [0] * length
    if nums:
        diff[0] = nums[0]
        for index in range(1, len(nums)):
            diff[index] = nums[index] - nums[index - 1]
    for update in updates:
        if not isinstance(update, (list, tuple)) or len(update) < 3:
            continue
        left, right, delta = update[0], update[1], update[2]
        if not isinstance(left, int) or not isinstance(right, int) or not isinstance(delta, (int, float)):
            continue
        if not (0 <= left <= right < len(nums)):
            continue
        diff[left] += delta
        if right + 1 < length:
            diff[right + 1] -= delta
    return diff


def _validate_array_contract_window(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    previous: tuple[int, int] | None = None
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums") or state.get("array")
        if not isinstance(nums, list):
            nums = []
        left = state.get("left")
        right = state.get("right")
        if not isinstance(left, int) or not isinstance(right, int):
            continue
        upper = len(nums) if nums else max(left, right, 0) + 1
        if left < 0 or right < -1 or left > upper or right >= upper:
            errors.append(f"第 {event.step} 步窗口指针越界")
        if left <= right and "window_sum" in state and nums and all(isinstance(item, (int, float)) for item in nums):
            expected_sum = sum(nums[left : right + 1])
            if state.get("window_sum") != expected_sum:
                errors.append(f"第 {event.step} 步 window_sum 应为 {expected_sum}")
        if previous is not None:
            prev_left, prev_right = previous
            if abs(left - prev_left) > 1 or abs(right - prev_right) > 1:
                errors.append(f"第 {event.step} 步窗口指针跳变")
        previous = (left, right)
    return errors


def _validate_array_contract_pointer_bounds(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pointer_keys = ("left", "right", "slow", "fast", "i", "j")
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums") or state.get("array") or state.get("candidates")
        if not isinstance(nums, list):
            continue
        for key in pointer_keys:
            value = state.get(key)
            if isinstance(value, int) and not (-1 <= value <= len(nums)):
                errors.append(f"第 {event.step} 步 pointer:{key} 越界")
    return errors


def _validate_array_contract_expected_targets(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    expected = _array_contract_string_list(contract, "expected_targets")
    if not expected:
        return []
    covered = {
        ref
        for event in trace.events
        if event.op in {SemanticOp.SET, SemanticOp.MOVE, SemanticOp.MARK, SemanticOp.PUSH, SemanticOp.POP}
        for ref in _event_target_ids(event)
    }
    missing = [target for target in expected if target not in covered]
    if not missing:
        return []
    return [f"Array pointer contract 缺少关键更新：{', '.join(missing[:6])}"]


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
        if "pointer:mid" in refs:
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
            expected_mid = (left + right) // 2
            if mid != expected_mid:
                errors.append(f"第 {event.step} 步 二分 mid 应为 {expected_mid}")
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

__all__ = [name for name in globals() if not name.startswith("__")]
