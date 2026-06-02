"""Process validators: dp."""

from __future__ import annotations

from algolab.verification.process_families.common import *

def _validate_dp_trace_contract(trace: SemanticTrace) -> list[str]:
    contract = _dp_contract_for_trace(trace)
    if contract is None:
        return []

    containers = _dp_contract_string_list(contract, "containers")
    answer_position = contract.get("answer_position")
    expected_targets = _dp_contract_string_list(contract, "expected_targets")
    errors: list[str] = []

    if not containers:
        errors.append("DP contract 缺少 containers，无法确认当前 DP 容器")
        return errors
    if not isinstance(answer_position, str) or not answer_position.strip():
        errors.append("DP contract 缺少答案位置 answer_position")

    init_events = [event for event in trace.events if event.op == SemanticOp.CREATE and _dp_event_state_has_container(event, containers)]
    if not init_events:
        errors.append("DP contract 缺少初始化事件：必须用 create 事件给出 DP 容器初始状态")

    covered_targets: set[str] = set()
    answer_position = answer_position.strip() if isinstance(answer_position, str) else ""
    answer_position_seen = False

    for event in trace.events:
        target_ids = _event_target_ids(event)
        dep_ids = _event_dep_ids(event)
        if event.op == SemanticOp.SET:
            for target_id in target_ids:
                if _target_belongs_to_containers(target_id, containers):
                    covered_targets.add(target_id)
            if (not target_ids and _dp_event_state_has_container(event, containers)) or any(
                _target_belongs_to_containers(target_id, containers) for target_id in target_ids
            ):
                errors.extend(_validate_dp_contract_set_event(event, containers))
        if answer_position and event.role == "answer" and (
            answer_position in (target_ids | dep_ids)
            or (
                answer_position in expected_targets
                and _is_declared_scalar_answer_target(answer_position, containers)
                and _dp_answer_mark_has_evidence(event, answer_position)
            )
        ):
            answer_position_seen = True
            if (
                answer_position in expected_targets
                and _is_declared_scalar_answer_target(answer_position, containers)
                and _dp_answer_mark_has_evidence(event, answer_position)
            ):
                covered_targets.add(answer_position)

    if answer_position and not answer_position_seen:
        errors.append(f"DP contract 答案位置未明确：role=answer 事件必须引用 {answer_position}")

    covered_targets.update(_dp_contract_implicitly_covered_targets(trace, containers, expected_targets))
    missing_targets = [target for target in expected_targets if target not in covered_targets]
    if missing_targets:
        preview = ", ".join(missing_targets[:6])
        suffix = "..." if len(missing_targets) > 6 else ""
        errors.append(f"DP contract 缺少关键更新：{preview}{suffix}")

    return errors


def _dp_contract_for_trace(trace: SemanticTrace) -> dict[str, Any] | None:
    for event in trace.events:
        contract = (event.state or {}).get("dp_contract")
        if isinstance(contract, dict):
            return contract
    return None


def _dp_contract_string_list(contract: dict[str, Any], key: str) -> list[str]:
    raw = contract.get(key)
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def _dp_contract_implicitly_covered_targets(
    trace: SemanticTrace,
    containers: list[str],
    expected_targets: list[str],
) -> set[str]:
    return _bounded_knapsack_initialized_expected_targets(trace, containers, expected_targets)


def _bounded_knapsack_initialized_expected_targets(
    trace: SemanticTrace,
    containers: list[str],
    expected_targets: list[str],
) -> set[str]:
    if "dp" not in set(containers) or not _has_dp_subfamily_signal(trace, "bounded_knapsack", "multiple_knapsack", "bounded"):
        return set()
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    weights = input_data.get("weights")
    capacity = input_data.get("capacity")
    if (
        not isinstance(weights, list)
        or not weights
        or not all(isinstance(item, int) and item > 0 for item in weights)
        or not isinstance(capacity, int)
    ):
        return set()
    init_dp = None
    for event in trace.events:
        state = event.state or {}
        dp = state.get("dp")
        if event.op == SemanticOp.CREATE and isinstance(dp, list):
            init_dp = dp
            break
    if not isinstance(init_dp, list):
        return set()

    min_weight = min(weights)
    covered: set[str] = set()
    for target in expected_targets:
        parsed = parse_target(target)
        if parsed.kind != "indexed" or parsed.name != "dp" or len(parsed.indices) != 1:
            continue
        index = parsed.indices[0]
        if isinstance(index, int) and 0 <= index < min_weight and index <= capacity and index < len(init_dp) and init_dp[index] == 0:
            covered.add(target)
    return covered


def _dp_event_state_has_container(event, containers: list[str]) -> bool:
    state = event.state or {}
    return any(container in state for container in containers)


def _dp_answer_mark_has_evidence(event, answer_position: str = "") -> bool:
    if not event.deps or not event.state:
        return False
    if _has_explicit_aux_value(event.value):
        return True
    if answer_position and answer_position in event.state:
        return _has_explicit_aux_value(event.state.get(answer_position))
    return False


def _is_declared_scalar_answer_target(target_id: str, containers: list[str]) -> bool:
    parsed = parse_target(target_id)
    return parsed.kind in {"container", "symbol"} and _target_container_name(target_id) in set(containers)


def _target_belongs_to_containers(target_id: str, containers: list[str]) -> bool:
    return _target_container_name(target_id) in set(containers)


def _target_container_name(target_id: str) -> str:
    parsed = parse_target(target_id)
    if parsed.kind in {"indexed", "slice"}:
        return parsed.name
    if parsed.kind == "map":
        key, _, _item = parsed.name.partition(":")
        return key
    if parsed.kind == "container":
        return parsed.name
    return target_id


def _validate_dp_contract_set_event(event, containers: list[str]) -> list[str]:
    errors: list[str] = []
    tree_dp_state_derived_update = _is_tree_dp_state_derived_update(event, containers)
    if not event.targets:
        errors.append(f"第 {event.step} 步 DP contract 关键更新缺少 targets")
    if not event.deps and not tree_dp_state_derived_update:
        errors.append(f"第 {event.step} 步 DP contract 关键更新缺少 deps")
    if not (
        _has_explicit_aux_value(event.value)
        or _has_explicit_aux_value(event.before)
        or _has_explicit_aux_value(event.after)
    ):
        errors.append(f"第 {event.step} 步 DP contract 关键更新缺少 value / before / after")
    if not event.state:
        errors.append(f"第 {event.step} 步 DP contract 关键更新缺少 state")
        return errors
    if not any(container in event.state for container in containers):
        errors.append(f"第 {event.step} 步 DP contract state 缺少当前 DP 容器")
    if not _is_scalar_answer_set_event(event, containers) and not any(key in event.state for key in DP_CONTRACT_LOOP_KEYS):
        keys = ", ".join(DP_CONTRACT_LOOP_KEYS)
        errors.append(f"第 {event.step} 步 DP contract state 缺少循环变量：{keys}")
    if not _dp_event_has_formula(event) and not tree_dp_state_derived_update:
        errors.append(f"第 {event.step} 步 DP contract 转移事件缺少可复原公式")
    return errors


def _is_tree_dp_state_derived_update(event, containers: list[str]) -> bool:
    state = event.state or {}
    contract = state.get("dp_contract") if isinstance(state.get("dp_contract"), dict) else {}
    subfamily = str(contract.get("subfamily", "")).lower()
    if "tree" not in subfamily and not {"dp_take", "dp_skip"}.issubset(set(containers)):
        return False
    current = state.get("current")
    if current is None or not isinstance(state.get("tree"), dict):
        return False
    if not isinstance(state.get("dp_take"), dict) or not isinstance(state.get("dp_skip"), dict):
        return False
    current_id = str(current)
    for target_id in _event_target_ids(event):
        parsed = parse_target(target_id)
        if parsed.kind != "indexed" or parsed.name not in {"dp_take", "dp_skip"} or len(parsed.indices) != 1:
            continue
        if str(parsed.indices[0]) == current_id:
            return True
    return False


def _is_scalar_answer_set_event(event, containers: list[str]) -> bool:
    if event.role != "answer" or not event.targets:
        return False
    target_ids = _event_target_ids(event)
    if not target_ids:
        return False
    if not all(_is_declared_scalar_answer_target(target_id, containers) for target_id in target_ids):
        return False
    return _dp_answer_mark_has_evidence(event)


def _dp_event_has_formula(event) -> bool:
    state = event.state or {}
    formula = state.get("formula")
    if isinstance(formula, str) and formula.strip():
        return True
    teaching = event.teaching
    teaching_formula = getattr(teaching, "formula", "") if teaching is not None else ""
    if isinstance(teaching_formula, str) and teaching_formula.strip():
        return True
    reason = event.reason or ""
    return "=" in reason and any(token in reason for token in ("dp", "状态", "转移"))


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
    for event in trace.events:
        state = event.state or {}
        dp = state.get("dp")
        if not isinstance(dp, list) or len(dp) != amount + 1:
            continue
        item_index = state.get("i")
        active_coins = coins[: item_index + 1] if isinstance(item_index, int) and item_index >= 0 else coins
        expected = _complete_knapsack_expected(active_coins, amount, mode)
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


def _validate_bounded_knapsack(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    weights = input_data.get("weights")
    values = input_data.get("values")
    counts = input_data.get("counts")
    capacity = input_data.get("capacity")
    if (
        not isinstance(weights, list)
        or not isinstance(values, list)
        or not isinstance(counts, list)
        or not isinstance(capacity, int)
        or len(weights) != len(values)
        or len(weights) != len(counts)
        or not all(isinstance(item, int) and item > 0 for item in weights)
        or not all(isinstance(item, int) for item in values)
        or not all(isinstance(item, int) and item >= 0 for item in counts)
        or capacity < 0
    ):
        return errors
    if not _has_dp_subfamily_signal(trace, "bounded_knapsack", "multiple_knapsack", "bounded"):
        return errors
    for event in trace.events:
        state = event.state or {}
        dp = state.get("dp")
        if not isinstance(dp, list) or len(dp) != capacity + 1:
            continue
        item_index = state.get("i")
        if not isinstance(item_index, int) or item_index < 0:
            continue
        expected = _bounded_knapsack_expected(weights[: item_index + 1], values[: item_index + 1], counts[: item_index + 1], capacity)
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name == "dp" and len(parsed.indices) == 1:
                j = parsed.indices[0]
                if (
                    0 <= j <= capacity
                    and isinstance(dp[j], int)
                    and not _bounded_knapsack_target_value_is_acceptable(event, dp[j], expected[j])
                ):
                    errors.append(f"第 {event.step} 步多重背包 dp[{j}] 应为 {expected[j]}")
    return errors


def _bounded_knapsack_target_value_is_acceptable(event, actual: int, expected: int) -> bool:
    if actual == expected:
        return True
    if event.role == "answer":
        return False
    state = event.state or {}
    candidate = state.get("candidate")
    take = state.get("take", state.get("count_used", state.get("quantity")))
    old_value = state.get("old_value")
    has_incremental_evidence = isinstance(candidate, int) and candidate == actual and isinstance(take, int) and take >= 0
    if not has_incremental_evidence:
        return False
    if isinstance(old_value, int) and actual < old_value:
        return False
    return actual <= expected


def _bounded_knapsack_expected(weights: list[int], values: list[int], counts: list[int], capacity: int) -> list[int]:
    dp = [0] * (capacity + 1)
    for weight, value, count in zip(weights, values, counts):
        prev = dp[:]
        for cap in range(capacity + 1):
            best = prev[cap]
            max_take = min(count, cap // weight)
            for take in range(1, max_take + 1):
                best = max(best, prev[cap - take * weight] + take * value)
            dp[cap] = best
    return dp


def _validate_digit_dp(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    n = input_data.get("n")
    if not isinstance(n, int) or n < 0:
        return errors
    if not _has_dp_subfamily_signal(trace, "digit_dp", "digit"):
        return errors
    forbidden_digit = _digit_dp_forbidden_digit(trace)
    include_zero = _digit_dp_include_zero(trace)
    expected_answer = _count_without_digit(n, forbidden_digit=forbidden_digit, include_zero=include_zero)
    expected_by_prefix = _digit_dp_prefix_counts(n, forbidden_digit=forbidden_digit, include_zero=include_zero)
    for event in trace.events:
        state = event.state or {}
        dp = state.get("dp")
        if not isinstance(dp, list):
            continue
        if event.op == SemanticOp.SET:
            for target in event.targets:
                parsed = parse_target(target.id)
                if parsed.kind != "indexed" or parsed.name != "dp" or len(parsed.indices) != 1:
                    continue
                index = parsed.indices[0]
                if 0 <= index < len(dp) and index < len(expected_by_prefix) and isinstance(dp[index], int) and dp[index] != expected_by_prefix[index]:
                    errors.append(f"第 {event.step} 步数位 DP dp[{index}] 应为 {expected_by_prefix[index]}")
        if event.role == "answer":
            answer = state.get("answer", event.value)
            if isinstance(answer, int) and answer != expected_answer:
                errors.append(f"第 {event.step} 步数位 DP answer 应为 {expected_answer}")
    return errors


def _has_dp_subfamily_signal(trace: SemanticTrace, *subfamilies: str) -> bool:
    wanted = {item.lower().replace("-", "_").replace(" ", "_") for item in subfamilies}
    for event in trace.events:
        contract = (event.state or {}).get("dp_contract")
        if isinstance(contract, dict):
            raw = contract.get("subfamily")
            if isinstance(raw, str) and raw.strip().lower().replace("-", "_").replace(" ", "_") in wanted:
                return True
    algorithm = (trace.algorithm or "").lower().replace("-", "_").replace(" ", "_")
    return any(item in algorithm for item in wanted)


def _digit_dp_forbidden_digit(trace: SemanticTrace) -> int:
    for event in trace.events:
        value = (event.state or {}).get("forbidden_digit")
        if isinstance(value, int) and 0 <= value <= 9:
            return value
    return 7


def _digit_dp_include_zero(trace: SemanticTrace) -> bool:
    for event in trace.events:
        state = event.state or {}
        if "include_zero" in state:
            return state.get("include_zero") is True
        count_range = state.get("count_range")
        if count_range == "0_to_n":
            return True
        if count_range == "1_to_n":
            return False
    return False


def _digit_dp_prefix_counts(n: int, *, forbidden_digit: int, include_zero: bool) -> list[int]:
    digits = [int(ch) for ch in str(n)]
    counts = [1]
    prefix_value = 0
    for digit in digits:
        prefix_value = prefix_value * 10 + digit
        counts.append(_count_without_digit(prefix_value, forbidden_digit=forbidden_digit, include_zero=include_zero))
    return counts


def _count_without_digit(n: int, *, forbidden_digit: int, include_zero: bool) -> int:
    start = 0 if include_zero else 1
    if n < start:
        return 0
    forbidden = str(forbidden_digit)
    return sum(1 for value in range(start, n + 1) if forbidden not in str(value))

__all__ = [name for name in globals() if not name.startswith("__")]
