"""Full-scale public synthetic AlgoLearnEnv task bundle expansion."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, Callable

from benchmark.cases import BenchmarkCase, BenchmarkInput
from benchmark.families.algo_learn_env_expansion import _Spec, _case_from_spec, _metadata_from_spec


ExpectedFn = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class _Operation:
    id: str
    title: str
    problem: str
    family: str
    family_id: str
    subfamily_id: str
    support_level: str
    process_profile: str
    oracle_type: str
    input_contract: str
    variant_name: str
    strategy: str
    time_complexity: str
    space_complexity: str
    expected_layouts: tuple[str, ...]
    solve_body: str
    verifier_body: str
    sample_sets: dict[str, tuple[dict[str, Any], ...]]
    difficulty: str
    learning_objectives: tuple[str, ...]
    interaction_focus: str


_VARIANT_LABELS = {
    "core": "核心样例",
    "edge": "边界样例",
    "transfer": "迁移样例",
}


def cases() -> tuple[BenchmarkCase, ...]:
    return tuple(_case_from_spec(spec) for spec in _expanded_specs())


def metadata() -> dict[str, dict[str, Any]]:
    return {spec.id: _metadata_from_spec(spec) for spec in _expanded_specs()}


def _expanded_specs() -> tuple[_Spec, ...]:
    specs: list[_Spec] = []
    for operation in _OPERATIONS:
        expected_fn = _EXPECTED[operation.id]
        for variant, sample_inputs in operation.sample_sets.items():
            label = _VARIANT_LABELS[variant]
            case_id = f"{operation.id}_full_{variant}"
            specs.append(
                _Spec(
                    id=case_id,
                    title=f"{operation.title}（{label}）",
                    problem=f"{operation.problem} 本任务属于 full-scale public synthetic benchmark 的{label}。",
                    family=operation.family,
                    family_id=operation.family_id,
                    subfamily_id=operation.subfamily_id,
                    support_level=operation.support_level,
                    process_profile=operation.process_profile,
                    oracle_type=operation.oracle_type,
                    input_contract=operation.input_contract,
                    variant_name=operation.variant_name,
                    strategy=operation.strategy,
                    time_complexity=operation.time_complexity,
                    space_complexity=operation.space_complexity,
                    expected_layouts=operation.expected_layouts,
                    solve_body=operation.solve_body,
                    verifier_body=operation.verifier_body,
                    samples=tuple(BenchmarkInput(input_data, expected_fn(input_data)) for input_data in sample_inputs),
                    difficulty=operation.difficulty if variant != "edge" else "medium",
                    learning_objectives=operation.learning_objectives,
                    interaction_focus=operation.interaction_focus,
                )
            )
    return tuple(specs)


def _array_count_positive(input_data: dict[str, Any]) -> int:
    return sum(1 for value in input_data["nums"] if value > 0)


def _array_longest_run(input_data: dict[str, Any]) -> int:
    nums = input_data["nums"]
    best = current = 0
    previous = None
    for value in nums:
        current = current + 1 if previous is not None and previous <= value else 1
        best = max(best, current)
        previous = value
    return best


def _array_pivot_index(input_data: dict[str, Any]) -> int:
    nums = input_data["nums"]
    total = sum(nums)
    left = 0
    for index, value in enumerate(nums):
        if left == total - left - value:
            return index
        left += value
    return -1


def _array_product_except_self(input_data: dict[str, Any]) -> list[int]:
    nums = input_data["nums"]
    result = []
    for i in range(len(nums)):
        product = 1
        for j, value in enumerate(nums):
            if i != j:
                product *= value
        result.append(product)
    return result


def _binary_lower_bound(input_data: dict[str, Any]) -> int:
    nums = input_data["nums"]
    target = input_data["target"]
    for index, value in enumerate(nums):
        if value >= target:
            return index
    return len(nums)


def _binary_floor_value(input_data: dict[str, Any]) -> int:
    answer = -1
    for value in input_data["nums"]:
        if value <= input_data["target"]:
            answer = value
        else:
            break
    return answer


def _hash_first_repeated(input_data: dict[str, Any]) -> int:
    seen = set()
    for value in input_data["nums"]:
        if value in seen:
            return value
        seen.add(value)
    return -1


def _hash_is_anagram(input_data: dict[str, Any]) -> bool:
    return sorted(input_data["a"]) == sorted(input_data["b"])


def _hash_longest_consecutive(input_data: dict[str, Any]) -> int:
    values = set(input_data["nums"])
    best = 0
    for value in values:
        if value - 1 in values:
            continue
        length = 1
        while value + length in values:
            length += 1
        best = max(best, length)
    return best


def _stack_valid_parentheses(input_data: dict[str, Any]) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for ch in input_data["text"]:
        if ch in "([{":
            stack.append(ch)
        elif not stack or stack.pop() != pairs[ch]:
            return False
    return not stack


def _stack_remove_adjacent_duplicates(input_data: dict[str, Any]) -> str:
    stack: list[str] = []
    for ch in input_data["text"]:
        if stack and stack[-1] == ch:
            stack.pop()
        else:
            stack.append(ch)
    return "".join(stack)


def _sorting_inversion_count(input_data: dict[str, Any]) -> int:
    nums = input_data["nums"]
    return sum(1 for i in range(len(nums)) for j in range(i + 1, len(nums)) if nums[i] > nums[j])


def _sorting_merge_two(input_data: dict[str, Any]) -> list[int]:
    result: list[int] = []
    a = input_data["a"]
    b = input_data["b"]
    i = j = 0
    while i < len(a) or j < len(b):
        if j == len(b) or (i < len(a) and a[i] <= b[j]):
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    return result


def _sorting_sort_colors(input_data: dict[str, Any]) -> list[int]:
    return sorted(input_data["nums"])


def _graph_reachable(input_data: dict[str, Any]) -> bool:
    graph = input_data["graph"]
    start = input_data["start"]
    goal = input_data["goal"]
    stack = [start]
    seen = {start}
    while stack:
        node = stack.pop()
        if node == goal:
            return True
        for nxt in graph.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return False


def _graph_component_count(input_data: dict[str, Any]) -> int:
    n = input_data["n"]
    graph = {i: [] for i in range(n)}
    for a, b in input_data["edges"]:
        graph[a].append(b)
        graph[b].append(a)
    seen: set[int] = set()
    count = 0
    for node in range(n):
        if node in seen:
            continue
        count += 1
        stack = [node]
        seen.add(node)
        while stack:
            current = stack.pop()
            for nxt in graph[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return count


def _graph_bfs_distances(input_data: dict[str, Any]) -> dict[str, int]:
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    queue = [start]
    for node in queue:
        for nxt in graph.get(node, []):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    return {key: dist[key] for key in sorted(dist)}


def _dp_climb_three_steps(input_data: dict[str, Any]) -> int:
    n = input_data["n"]
    dp = [0] * (max(n, 2) + 1)
    dp[0] = 1
    for i in range(1, n + 1):
        dp[i] = dp[i - 1]
        if i >= 2:
            dp[i] += dp[i - 2]
        if i >= 3:
            dp[i] += dp[i - 3]
    return dp[n]


def _dp_max_subarray(input_data: dict[str, Any]) -> int:
    nums = input_data["nums"]
    best = current = nums[0]
    for value in nums[1:]:
        current = max(value, current + value)
        best = max(best, current)
    return best


def _dp_decode_ways(input_data: dict[str, Any]) -> int:
    s = input_data["digits"]
    dp = [0] * (len(s) + 1)
    dp[0] = 1
    for i in range(1, len(s) + 1):
        if s[i - 1] != "0":
            dp[i] += dp[i - 1]
        if i >= 2 and 10 <= int(s[i - 2:i]) <= 26:
            dp[i] += dp[i - 2]
    return dp[len(s)]


def _dp_grid_paths_obstacles(input_data: dict[str, Any]) -> int:
    grid = input_data["grid"]
    rows, cols = len(grid), len(grid[0])
    dp = [[0] * cols for _ in range(rows)]
    dp[0][0] = 0 if grid[0][0] else 1
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] or (r == 0 and c == 0):
                continue
            dp[r][c] = (dp[r - 1][c] if r else 0) + (dp[r][c - 1] if c else 0)
    return dp[-1][-1]


def _dp_subset_sum_possible(input_data: dict[str, Any]) -> bool:
    reachable = {0}
    for value in input_data["nums"]:
        reachable |= {total + value for total in list(reachable)}
    return input_data["target"] in reachable


def _tree_max_depth(input_data: dict[str, Any]) -> int:
    tree = input_data["tree"]
    children = tree.get("children", {})
    def depth(node: Any) -> int:
        if node is None:
            return 0
        left, right = children.get(node, [None, None])
        return 1 + max(depth(left), depth(right))
    return depth(tree.get("root"))


def _tree_path_sum_exists(input_data: dict[str, Any]) -> bool:
    tree = input_data["tree"]
    values = tree.get("values", {})
    children = tree.get("children", {})
    target = input_data["target"]
    def visit(node: Any, total: int) -> bool:
        if node is None:
            return False
        left, right = children.get(node, [None, None])
        new_total = total + values[node]
        if left is None and right is None:
            return new_total == target
        return visit(left, new_total) or visit(right, new_total)
    return visit(tree.get("root"), 0)


def _tree_preorder(input_data: dict[str, Any]) -> list[Any]:
    tree = input_data["tree"]
    children = tree.get("children", {})
    result: list[Any] = []
    def visit(node: Any) -> None:
        if node is None:
            return
        result.append(node)
        left, right = children.get(node, [None, None])
        visit(left)
        visit(right)
    visit(tree.get("root"))
    return result


def _heap_last_stone(input_data: dict[str, Any]) -> int:
    heap = [-value for value in input_data["stones"]]
    heapq.heapify(heap)
    while len(heap) > 1:
        a = -heapq.heappop(heap)
        b = -heapq.heappop(heap)
        if a != b:
            heapq.heappush(heap, -(a - b))
    return -heap[0] if heap else 0


def _heap_k_smallest(input_data: dict[str, Any]) -> list[int]:
    nums = list(input_data["nums"])
    heapq.heapify(nums)
    return [heapq.heappop(nums) for _ in range(min(input_data["k"], len(nums)))]


def _greedy_assign_cookies(input_data: dict[str, Any]) -> int:
    children = sorted(input_data["children"])
    cookies = sorted(input_data["cookies"])
    child = cookie = answer = 0
    while child < len(children) and cookie < len(cookies):
        if cookies[cookie] >= children[child]:
            answer += 1
            child += 1
        cookie += 1
    return answer


def _greedy_lemonade_change(input_data: dict[str, Any]) -> bool:
    five = ten = 0
    for bill in input_data["bills"]:
        if bill == 5:
            five += 1
        elif bill == 10:
            if five == 0:
                return False
            five -= 1
            ten += 1
        else:
            if ten and five:
                ten -= 1
                five -= 1
            elif five >= 3:
                five -= 3
            else:
                return False
    return True


def _string_longest_common_prefix(input_data: dict[str, Any]) -> str:
    words = input_data["words"]
    if not words:
        return ""
    prefix = words[0]
    for word in words[1:]:
        while not word.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix


def _string_is_subsequence(input_data: dict[str, Any]) -> bool:
    s = input_data["s"]
    t = input_data["t"]
    index = 0
    for ch in t:
        if index < len(s) and s[index] == ch:
            index += 1
    return index == len(s)


def _string_count_palindromic_substrings(input_data: dict[str, Any]) -> int:
    text = input_data["text"]
    count = 0
    for center in range(len(text)):
        left = right = center
        while left >= 0 and right < len(text) and text[left] == text[right]:
            count += 1
            left -= 1
            right += 1
        left, right = center, center + 1
        while left >= 0 and right < len(text) and text[left] == text[right]:
            count += 1
            left -= 1
            right += 1
    return count


def _union_count_components(input_data: dict[str, Any]) -> int:
    n = input_data["n"]
    parent = list(range(n))
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in input_data["edges"]:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    return len({find(i) for i in range(n)})


_EXPECTED: dict[str, ExpectedFn] = {
    "array_count_positive": _array_count_positive,
    "array_longest_run": _array_longest_run,
    "array_pivot_index": _array_pivot_index,
    "array_product_except_self": _array_product_except_self,
    "binary_lower_bound": _binary_lower_bound,
    "binary_floor_value": _binary_floor_value,
    "hash_first_repeated": _hash_first_repeated,
    "hash_is_anagram": _hash_is_anagram,
    "hash_longest_consecutive": _hash_longest_consecutive,
    "stack_valid_parentheses": _stack_valid_parentheses,
    "stack_remove_adjacent_duplicates": _stack_remove_adjacent_duplicates,
    "sorting_inversion_count": _sorting_inversion_count,
    "sorting_merge_two": _sorting_merge_two,
    "sorting_sort_colors": _sorting_sort_colors,
    "graph_reachable": _graph_reachable,
    "graph_component_count": _graph_component_count,
    "graph_bfs_distances": _graph_bfs_distances,
    "dp_climb_three_steps": _dp_climb_three_steps,
    "dp_max_subarray": _dp_max_subarray,
    "dp_decode_ways": _dp_decode_ways,
    "dp_grid_paths_obstacles": _dp_grid_paths_obstacles,
    "dp_subset_sum_possible": _dp_subset_sum_possible,
    "tree_max_depth": _tree_max_depth,
    "tree_path_sum_exists": _tree_path_sum_exists,
    "tree_preorder": _tree_preorder,
    "heap_last_stone": _heap_last_stone,
    "heap_k_smallest": _heap_k_smallest,
    "greedy_assign_cookies": _greedy_assign_cookies,
    "greedy_lemonade_change": _greedy_lemonade_change,
    "string_longest_common_prefix": _string_longest_common_prefix,
    "string_is_subsequence": _string_is_subsequence,
    "string_count_palindromic_substrings": _string_count_palindromic_substrings,
    "union_count_components": _union_count_components,
}


_OPERATIONS: tuple[_Operation, ...] = (
    _Operation(
        id="array_count_positive",
        title="统计正数个数",
        problem="给定整数数组 nums，返回其中大于 0 的元素个数。",
        family="数组指针 / 窗口 / 前缀",
        family_id="array_pointer",
        subfamily_id="array_scan_count",
        support_level="strong",
        process_profile="array_pointer",
        oracle_type="independent_reference",
        input_contract="输入整数数组 nums。",
        variant_name="线性扫描计数",
        strategy="从左到右扫描数组，遇到正数就增加计数。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array",),
        solve_body="""
nums = input_data["nums"]
count = 0
for value in nums:
    if value > 0:
        count += 1
return count
""",
        verifier_body="""
return len([value for value in input_data["nums"] if value > 0])
""",
        sample_sets={
            "core": ({"nums": [1, -2, 3, 0]}, {"nums": [-1, -2]}, {"nums": [5]}),
            "edge": ({"nums": []}, {"nums": [0, 0, 0]}, {"nums": [-3, 4, -1, 2]}),
            "transfer": ({"nums": [7, -8, 9, 10, -1]}, {"nums": [-5, 6, 0, 6]}, {"nums": [2, 2, 2]}),
        },
        difficulty="easy",
        learning_objectives=("理解线性扫描", "维护计数变量", "区分正数、零和负数"),
        interaction_focus="当前元素与正数计数",
    ),
    _Operation(
        id="array_longest_run",
        title="最长非递减连续段",
        problem="给定整数数组 nums，返回最长非递减连续子数组长度。",
        family="数组指针 / 窗口 / 前缀",
        family_id="array_pointer",
        subfamily_id="run_length_scan",
        support_level="strong",
        process_profile="array_pointer",
        oracle_type="bruteforce",
        input_contract="输入整数数组 nums。",
        variant_name="连续段扫描",
        strategy="比较相邻元素，能延续非递减关系就扩展当前长度，否则重新开始。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = input_data["nums"]
best = 0
current = 0
previous = None
for value in nums:
    if previous is not None and previous <= value:
        current += 1
    else:
        current = 1
    if current > best:
        best = current
    previous = value
return best
""",
        verifier_body="""
nums = input_data["nums"]
best = 0
for left in range(len(nums)):
    for right in range(left, len(nums)):
        ok = True
        for i in range(left + 1, right + 1):
            if nums[i - 1] > nums[i]:
                ok = False
                break
        if ok:
            best = max(best, right - left + 1)
return best
""",
        sample_sets={
            "core": ({"nums": [1, 2, 2, 1, 3]}, {"nums": [5, 4, 3]}, {"nums": [1, 1, 1]}),
            "edge": ({"nums": []}, {"nums": [4]}, {"nums": [3, 2, 2, 2, 1]}),
            "transfer": ({"nums": [-2, -1, 0, -1, 2, 3]}, {"nums": [10, 9, 10, 11]}, {"nums": [2, 3, 1, 2, 3, 4]}),
        },
        difficulty="medium",
        learning_objectives=("理解连续段状态", "判断相邻元素关系", "维护当前长度和历史最优"),
        interaction_focus="当前连续段长度和 best",
    ),
    _Operation(
        id="array_pivot_index",
        title="数组平衡下标",
        problem="给定整数数组 nums，返回第一个左侧元素和等于右侧元素和的下标，不存在返回 -1。",
        family="数组指针 / 窗口 / 前缀",
        family_id="array_pointer",
        subfamily_id="prefix_balance",
        support_level="strong",
        process_profile="array_pointer",
        oracle_type="independent_reference",
        input_contract="输入整数数组 nums。",
        variant_name="前缀平衡扫描",
        strategy="先计算总和，再从左到右维护 left_sum 判断平衡条件。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array",),
        solve_body="""
nums = input_data["nums"]
total = sum(nums)
left = 0
for index, value in enumerate(nums):
    if left == total - left - value:
        return index
    left += value
return -1
""",
        verifier_body="""
nums = input_data["nums"]
for index in range(len(nums)):
    left = sum(nums[:index])
    right = sum(nums[index + 1:])
    if left == right:
        return index
return -1
""",
        sample_sets={
            "core": ({"nums": [1, 7, 3, 6, 5, 6]}, {"nums": [1, 2, 3]}, {"nums": [2, 1, -1]}),
            "edge": ({"nums": []}, {"nums": [0]}, {"nums": [0, 0, 0]}),
            "transfer": ({"nums": [-1, -1, 0, 1, 1]}, {"nums": [3, -3, 4]}, {"nums": [4, 2, -2, 2, 0]}),
        },
        difficulty="medium",
        learning_objectives=("理解前缀和", "比较左右两侧状态", "处理负数与零"),
        interaction_focus="left_sum 与 right_sum",
    ),
    _Operation(
        id="array_product_except_self",
        title="除自身以外数组乘积",
        problem="给定整数数组 nums，返回 answer，其中 answer[i] 是除 nums[i] 外其余元素的乘积。",
        family="数组指针 / 窗口 / 前缀",
        family_id="array_pointer",
        subfamily_id="prefix_suffix_product",
        support_level="strong",
        process_profile="array_pointer",
        oracle_type="bruteforce",
        input_contract="输入整数数组 nums。",
        variant_name="前缀后缀乘积",
        strategy="分别维护当前位置左侧乘积和右侧乘积，避免使用除法。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array",),
        solve_body="""
nums = input_data["nums"]
n = len(nums)
answer = [1] * n
prefix = 1
for i in range(n):
    answer[i] = prefix
    prefix *= nums[i]
suffix = 1
for i in range(n - 1, -1, -1):
    answer[i] *= suffix
    suffix *= nums[i]
return answer
""",
        verifier_body="""
nums = input_data["nums"]
result = []
for i in range(len(nums)):
    product = 1
    for j, value in enumerate(nums):
        if i != j:
            product *= value
    result.append(product)
return result
""",
        sample_sets={
            "core": ({"nums": [1, 2, 3, 4]}, {"nums": [2, 3]}, {"nums": [5]}),
            "edge": ({"nums": [0, 1, 2]}, {"nums": [0, 0, 2]}, {"nums": [-1, 2, -3]}),
            "transfer": ({"nums": [3, 4, 5]}, {"nums": [-2, -2, 1, 3]}, {"nums": [1, 1, 1, 1]}),
        },
        difficulty="medium",
        learning_objectives=("理解前缀乘积", "理解后缀乘积", "处理包含 0 的输入"),
        interaction_focus="prefix/suffix 与 answer[i]",
    ),
    _Operation(
        id="binary_lower_bound",
        title="下界插入位置",
        problem="给定升序数组 nums 和 target，返回第一个不小于 target 的插入位置。",
        family="二分",
        family_id="binary_search",
        subfamily_id="lower_bound",
        support_level="strong",
        process_profile="binary_search",
        oracle_type="independent_reference",
        input_contract="输入升序数组 nums 和整数 target。",
        variant_name="lower_bound 二分",
        strategy="二分维护可行位置，遇到 nums[mid] >= target 时保留左侧。",
        time_complexity="O(log n)",
        space_complexity="O(1)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = input_data["nums"]
target = input_data["target"]
left, right = 0, len(nums)
while left < right:
    mid = (left + right) // 2
    if nums[mid] >= target:
        right = mid
    else:
        left = mid + 1
return left
""",
        verifier_body="""
nums = input_data["nums"]
target = input_data["target"]
for index, value in enumerate(nums):
    if value >= target:
        return index
return len(nums)
""",
        sample_sets={
            "core": ({"nums": [1, 3, 5, 7], "target": 5}, {"nums": [1, 3, 5, 7], "target": 4}, {"nums": [1, 3], "target": 0}),
            "edge": ({"nums": [], "target": 2}, {"nums": [2, 2, 2], "target": 2}, {"nums": [1, 2, 3], "target": 9}),
            "transfer": ({"nums": [-5, -1, 0, 4], "target": -2}, {"nums": [10], "target": 10}, {"nums": [1, 4, 4, 6], "target": 5}),
        },
        difficulty="easy",
        learning_objectives=("理解下界语义", "维护半开区间", "解释重复元素中的第一个位置"),
        interaction_focus="left/right/mid 与可行位置",
    ),
    _Operation(
        id="binary_floor_value",
        title="不超过目标的最大值",
        problem="给定升序数组 nums 和 target，返回不超过 target 的最大元素；不存在返回 -1。",
        family="二分",
        family_id="binary_search",
        subfamily_id="floor_value",
        support_level="strong",
        process_profile="binary_search",
        oracle_type="independent_reference",
        input_contract="输入升序数组 nums 和整数 target。",
        variant_name="floor 二分",
        strategy="当 nums[mid] <= target 时记录候选并继续向右搜索。",
        time_complexity="O(log n)",
        space_complexity="O(1)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = input_data["nums"]
target = input_data["target"]
left, right = 0, len(nums) - 1
answer = -1
while left <= right:
    mid = (left + right) // 2
    if nums[mid] <= target:
        answer = nums[mid]
        left = mid + 1
    else:
        right = mid - 1
return answer
""",
        verifier_body="""
answer = -1
for value in input_data["nums"]:
    if value <= input_data["target"]:
        answer = value
return answer
""",
        sample_sets={
            "core": ({"nums": [1, 4, 6, 9], "target": 7}, {"nums": [2, 5], "target": 1}, {"nums": [3, 3, 8], "target": 3}),
            "edge": ({"nums": [], "target": 5}, {"nums": [1], "target": 0}, {"nums": [1], "target": 2}),
            "transfer": ({"nums": [-4, -1, 2], "target": -2}, {"nums": [0, 10, 20], "target": 100}, {"nums": [5, 6, 7], "target": 6}),
        },
        difficulty="easy",
        learning_objectives=("理解 floor 查询", "维护答案候选", "区分值和下标"),
        interaction_focus="当前候选 floor 与搜索区间",
    ),
    _Operation(
        id="hash_first_repeated",
        title="第一个重复值",
        problem="给定整数数组 nums，返回扫描过程中第一个第二次出现的值；不存在返回 -1。",
        family="哈希表 / map",
        family_id="hash_map",
        subfamily_id="seen_set",
        support_level="medium_plus",
        process_profile="hash",
        oracle_type="independent_reference",
        input_contract="输入整数数组 nums。",
        variant_name="已见集合扫描",
        strategy="维护 seen 集合，当前元素已在 seen 中时立刻返回。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array", "map"),
        solve_body="""
seen = set()
for value in input_data["nums"]:
    if value in seen:
        return value
    seen.add(value)
return -1
""",
        verifier_body="""
nums = input_data["nums"]
for i in range(len(nums)):
    for j in range(i):
        if nums[i] == nums[j]:
            return nums[i]
return -1
""",
        sample_sets={
            "core": ({"nums": [1, 2, 3, 2]}, {"nums": [4, 5, 6]}, {"nums": [7, 7]}),
            "edge": ({"nums": []}, {"nums": [1]}, {"nums": [0, -1, 0]}),
            "transfer": ({"nums": [3, 1, 3, 1]}, {"nums": [9, 8, 7, 8]}, {"nums": [2, 4, 6, 8]}),
        },
        difficulty="easy",
        learning_objectives=("理解 seen 集合", "区分第一次和第二次出现", "解释提前返回"),
        interaction_focus="当前值与 seen 集合",
    ),
    _Operation(
        id="hash_is_anagram",
        title="判断字母异位词",
        problem="给定两个小写字符串 a 和 b，判断它们是否由相同字符及频次组成。",
        family="哈希表 / map",
        family_id="hash_map",
        subfamily_id="frequency_count",
        support_level="medium_plus",
        process_profile="hash",
        oracle_type="independent_reference",
        input_contract="输入字符串 a 和 b。",
        variant_name="字符频次表比较",
        strategy="统计两个字符串的字符频次，并比较每个字符的计数。",
        time_complexity="O(n+m)",
        space_complexity="O(字符集大小)",
        expected_layouts=("string", "map"),
        solve_body="""
a = input_data["a"]
b = input_data["b"]
if len(a) != len(b):
    return False
counts = {}
for ch in a:
    counts[ch] = counts.get(ch, 0) + 1
for ch in b:
    counts[ch] = counts.get(ch, 0) - 1
for value in counts.values():
    if value != 0:
        return False
return True
""",
        verifier_body="""
return sorted(input_data["a"]) == sorted(input_data["b"])
""",
        sample_sets={
            "core": ({"a": "listen", "b": "silent"}, {"a": "rat", "b": "car"}, {"a": "aabb", "b": "baba"}),
            "edge": ({"a": "", "b": ""}, {"a": "a", "b": ""}, {"a": "aa", "b": "ab"}),
            "transfer": ({"a": "triangle", "b": "integral"}, {"a": "state", "b": "taste"}, {"a": "abc", "b": "abd"}),
        },
        difficulty="easy",
        learning_objectives=("构建频次表", "比较双字符串计数", "处理长度不同的快速失败"),
        interaction_focus="字符频次差值",
    ),
    _Operation(
        id="hash_longest_consecutive",
        title="最长连续整数序列",
        problem="给定整数数组 nums，返回能组成的最长连续整数序列长度。",
        family="哈希表 / map",
        family_id="hash_map",
        subfamily_id="set_sequence",
        support_level="medium_plus",
        process_profile="hash",
        oracle_type="bruteforce",
        input_contract="输入整数数组 nums。",
        variant_name="集合起点扩展",
        strategy="把数放入集合，只从没有前驱的数开始向右扩展连续段。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array", "map"),
        solve_body="""
values = set(input_data["nums"])
best = 0
for value in values:
    if value - 1 in values:
        continue
    length = 1
    while value + length in values:
        length += 1
    best = max(best, length)
return best
""",
        verifier_body="""
nums = input_data["nums"]
best = 0
for value in nums:
    length = 1
    current = value
    while current + 1 in nums:
        current += 1
        length += 1
    best = max(best, length)
return best
""",
        sample_sets={
            "core": ({"nums": [100, 4, 200, 1, 3, 2]}, {"nums": [1, 2, 0, 1]}, {"nums": [9]}),
            "edge": ({"nums": []}, {"nums": [1, 1, 1]}, {"nums": [-2, -1, 0, 2]}),
            "transfer": ({"nums": [10, 5, 6, 7, 20]}, {"nums": [3, 4, 5, 1, 2]}, {"nums": [8, 6, 7, 10]}),
        },
        difficulty="medium",
        learning_objectives=("理解集合去重", "识别连续段起点", "避免重复扩展"),
        interaction_focus="连续段起点和扩展长度",
    ),
    _Operation(
        id="stack_valid_parentheses",
        title="括号匹配",
        problem="给定括号字符串 text，判断三种括号是否正确嵌套和闭合。",
        family="栈 / 队列 / 单调栈",
        family_id="monotonic_stack",
        subfamily_id="parentheses_stack",
        support_level="strong",
        process_profile="monotonic_stack",
        oracle_type="independent_reference",
        input_contract="输入只包含 ()[]{} 的字符串 text。",
        variant_name="栈顶匹配",
        strategy="左括号入栈，右括号必须匹配当前栈顶。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("string", "stack"),
        solve_body="""
pairs = {")": "(", "]": "[", "}": "{"}
stack = []
for ch in input_data["text"]:
    if ch in "([{":
        stack.append(ch)
    else:
        if not stack or stack[-1] != pairs[ch]:
            return False
        stack.pop()
return not stack
""",
        verifier_body="""
text = input_data["text"]
previous = None
while previous != text:
    previous = text
    text = text.replace("()", "").replace("[]", "").replace("{}", "")
return text == ""
""",
        sample_sets={
            "core": ({"text": "()[]{}"}, {"text": "([{}])"}, {"text": "(]"}),
            "edge": ({"text": ""}, {"text": "("}, {"text": "])"}),
            "transfer": ({"text": "{[()]}"}, {"text": "([)]"}, {"text": "((()))[]"}),
        },
        difficulty="easy",
        learning_objectives=("理解栈顶匹配", "识别错误闭合", "验证最终栈为空"),
        interaction_focus="当前括号和栈顶",
    ),
    _Operation(
        id="stack_remove_adjacent_duplicates",
        title="删除相邻重复字符",
        problem="给定字符串 text，反复删除相邻且相同的一对字符，返回最终字符串。",
        family="栈 / 队列 / 单调栈",
        family_id="monotonic_stack",
        subfamily_id="stack_cancellation",
        support_level="strong",
        process_profile="monotonic_stack",
        oracle_type="independent_reference",
        input_contract="输入字符串 text。",
        variant_name="消消乐栈",
        strategy="当前字符等于栈顶时弹出，否则入栈。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("string", "stack"),
        solve_body="""
stack = []
for ch in input_data["text"]:
    if stack and stack[-1] == ch:
        stack.pop()
    else:
        stack.append(ch)
return "".join(stack)
""",
        verifier_body="""
text = input_data["text"]
changed = True
while changed:
    changed = False
    result = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == text[i + 1]:
            changed = True
            i += 2
        else:
            result.append(text[i])
            i += 1
    text = "".join(result)
return text
""",
        sample_sets={
            "core": ({"text": "abbaca"}, {"text": "azxxzy"}, {"text": "abc"}),
            "edge": ({"text": ""}, {"text": "aa"}, {"text": "aaaa"}),
            "transfer": ({"text": "abccba"}, {"text": "aabccbdd"}, {"text": "xxyzz"}),
        },
        difficulty="medium",
        learning_objectives=("理解栈式抵消", "追踪栈顶变化", "解释连锁删除"),
        interaction_focus="当前字符和栈顶字符",
    ),
    _Operation(
        id="sorting_inversion_count",
        title="逆序对计数",
        problem="给定整数数组 nums，返回满足 i<j 且 nums[i]>nums[j] 的逆序对数量。",
        family="排序",
        family_id="sorting",
        subfamily_id="inversion_count",
        support_level="medium_plus",
        process_profile="sorting",
        oracle_type="bruteforce",
        input_contract="输入整数数组 nums。",
        variant_name="归并排序计数",
        strategy="用归并思想统计右半元素先出队时跨越的左半剩余数量。",
        time_complexity="O(n log n)",
        space_complexity="O(n)",
        expected_layouts=("array", "recursion_tree"),
        solve_body="""
nums = input_data["nums"]
def sort_count(values):
    if len(values) <= 1:
        return values, 0
    mid = len(values) // 2
    left, inv_left = sort_count(values[:mid])
    right, inv_right = sort_count(values[mid:])
    merged = []
    i = j = 0
    inv = inv_left + inv_right
    while i < len(left) or j < len(right):
        if j == len(right) or (i < len(left) and left[i] <= right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            inv += len(left) - i
            j += 1
    return merged, inv
return sort_count(nums)[1]
""",
        verifier_body="""
nums = input_data["nums"]
count = 0
for i in range(len(nums)):
    for j in range(i + 1, len(nums)):
        if nums[i] > nums[j]:
            count += 1
return count
""",
        sample_sets={
            "core": ({"nums": [2, 4, 1, 3, 5]}, {"nums": [1, 2, 3]}, {"nums": [3, 2, 1]}),
            "edge": ({"nums": []}, {"nums": [1]}, {"nums": [1, 1, 1]}),
            "transfer": ({"nums": [-1, -2, 0]}, {"nums": [5, 3, 4, 2]}, {"nums": [2, 1, 2, 1]}),
        },
        difficulty="medium",
        learning_objectives=("理解逆序对定义", "观察归并过程", "验证跨区间计数"),
        interaction_focus="左右子数组指针和新增逆序数",
    ),
    _Operation(
        id="sorting_merge_two",
        title="合并两个升序数组",
        problem="给定两个升序数组 a 和 b，返回合并后的升序数组。",
        family="排序",
        family_id="sorting",
        subfamily_id="merge_two_sorted",
        support_level="medium_plus",
        process_profile="sorting",
        oracle_type="property",
        input_contract="输入升序数组 a 和 b。",
        variant_name="双指针归并",
        strategy="比较两个数组当前指针，较小者进入结果并前进。",
        time_complexity="O(n+m)",
        space_complexity="O(n+m)",
        expected_layouts=("array", "pointer"),
        solve_body="""
a = input_data["a"]
b = input_data["b"]
i = j = 0
result = []
while i < len(a) or j < len(b):
    if j == len(b) or (i < len(a) and a[i] <= b[j]):
        result.append(a[i])
        i += 1
    else:
        result.append(b[j])
        j += 1
return result
""",
        verifier_body="""
return sorted(input_data["a"] + input_data["b"])
""",
        sample_sets={
            "core": ({"a": [1, 3, 5], "b": [2, 4]}, {"a": [], "b": [1]}, {"a": [2], "b": []}),
            "edge": ({"a": [], "b": []}, {"a": [1, 1], "b": [1]}, {"a": [-3, 0], "b": [-2, 2]}),
            "transfer": ({"a": [5, 6], "b": [1, 2, 3]}, {"a": [0, 10], "b": [5, 15]}, {"a": [1, 4, 9], "b": [1, 4, 8]}),
        },
        difficulty="easy",
        learning_objectives=("理解双指针归并", "处理一侧耗尽", "保持排序不变量"),
        interaction_focus="两个数组当前指针",
    ),
    _Operation(
        id="sorting_sort_colors",
        title="三色排序",
        problem="给定只含 0、1、2 的数组 nums，返回按 0、1、2 排序后的数组。",
        family="排序",
        family_id="sorting",
        subfamily_id="counting_sort",
        support_level="medium_plus",
        process_profile="sorting",
        oracle_type="property",
        input_contract="输入只含 0、1、2 的数组 nums。",
        variant_name="三桶计数排序",
        strategy="统计三种颜色的数量，再按颜色顺序展开。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array", "map"),
        solve_body="""
counts = [0, 0, 0]
for value in input_data["nums"]:
    counts[value] += 1
result = []
for value, count in enumerate(counts):
    for _ in range(count):
        result.append(value)
return result
""",
        verifier_body="""
return sorted(input_data["nums"])
""",
        sample_sets={
            "core": ({"nums": [2, 0, 2, 1, 1, 0]}, {"nums": [1, 0]}, {"nums": [2, 2, 1]}),
            "edge": ({"nums": []}, {"nums": [0, 0]}, {"nums": [2]}),
            "transfer": ({"nums": [1, 2, 0, 1, 2, 0]}, {"nums": [0, 1, 2]}, {"nums": [2, 1, 0, 0]}),
        },
        difficulty="easy",
        learning_objectives=("理解小值域计数", "观察桶计数", "验证展开顺序"),
        interaction_focus="颜色计数桶",
    ),
    _Operation(
        id="graph_reachable",
        title="有向图可达性",
        problem="给定有向图 graph、起点 start 和终点 goal，判断 goal 是否可从 start 到达。",
        family="BFS/DFS 基础图",
        family_id="basic_graph",
        subfamily_id="reachability",
        support_level="strong",
        process_profile="bfs",
        oracle_type="independent_reference",
        input_contract="输入 graph 邻接表、start、goal。",
        variant_name="DFS 可达性",
        strategy="用栈或队列遍历可达节点，遇到 goal 即返回。",
        time_complexity="O(V+E)",
        space_complexity="O(V)",
        expected_layouts=("graph", "stack"),
        solve_body="""
graph = input_data["graph"]
start = input_data["start"]
goal = input_data["goal"]
stack = [start]
seen = {start}
while stack:
    node = stack.pop()
    if node == goal:
        return True
    for nxt in graph.get(node, []):
        if nxt not in seen:
            seen.add(nxt)
            stack.append(nxt)
return False
""",
        verifier_body="""
graph = input_data["graph"]
start = input_data["start"]
goal = input_data["goal"]
reachable = {start}
changed = True
while changed:
    changed = False
    for node in list(reachable):
        for nxt in graph.get(node, []):
            if nxt not in reachable:
                reachable.add(nxt)
                changed = True
return goal in reachable
""",
        sample_sets={
            "core": ({"graph": {"A": ["B"], "B": ["C"], "C": []}, "start": "A", "goal": "C"}, {"graph": {"A": [], "B": ["A"]}, "start": "A", "goal": "B"}, {"graph": {"S": ["S"]}, "start": "S", "goal": "S"}),
            "edge": ({"graph": {"A": []}, "start": "A", "goal": "A"}, {"graph": {"A": []}, "start": "A", "goal": "Z"}, {"graph": {}, "start": "X", "goal": "X"}),
            "transfer": ({"graph": {"0": ["1", "2"], "1": [], "2": ["3"], "3": []}, "start": "0", "goal": "3"}, {"graph": {"u": ["v"], "v": ["u"]}, "start": "u", "goal": "v"}, {"graph": {"a": ["b"], "b": [], "c": []}, "start": "c", "goal": "a"}),
        },
        difficulty="easy",
        learning_objectives=("理解图遍历", "维护 visited 集合", "判断目标可达"),
        interaction_focus="待访问节点和 visited 集合",
    ),
    _Operation(
        id="graph_component_count",
        title="无向图连通分量数",
        problem="给定 n 个节点和无向边 edges，返回连通分量数量。",
        family="BFS/DFS 基础图",
        family_id="basic_graph",
        subfamily_id="connected_components",
        support_level="strong",
        process_profile="bfs",
        oracle_type="independent_reference",
        input_contract="输入 n 和 edges。",
        variant_name="DFS 连通块计数",
        strategy="扫描所有节点，遇到未访问节点就启动一次 DFS 并计数。",
        time_complexity="O(V+E)",
        space_complexity="O(V+E)",
        expected_layouts=("graph", "stack"),
        solve_body="""
n = input_data["n"]
graph = {i: [] for i in range(n)}
for a, b in input_data["edges"]:
    graph[a].append(b)
    graph[b].append(a)
seen = set()
count = 0
for node in range(n):
    if node in seen:
        continue
    count += 1
    stack = [node]
    seen.add(node)
    while stack:
        current = stack.pop()
        for nxt in graph[current]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
return count
""",
        verifier_body="""
n = input_data["n"]
parent = list(range(n))
def find(x):
    while parent[x] != x:
        x = parent[x]
    return x
for a, b in input_data["edges"]:
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra
return len({find(i) for i in range(n)})
""",
        sample_sets={
            "core": ({"n": 5, "edges": [[0, 1], [1, 2], [3, 4]]}, {"n": 3, "edges": []}, {"n": 4, "edges": [[0, 1], [2, 3], [1, 2]]}),
            "edge": ({"n": 1, "edges": []}, {"n": 0, "edges": []}, {"n": 2, "edges": [[0, 1]]}),
            "transfer": ({"n": 6, "edges": [[0, 1], [2, 3], [4, 5]]}, {"n": 6, "edges": [[0, 1], [1, 2], [3, 4]]}, {"n": 5, "edges": [[0, 4], [4, 2]]}),
        },
        difficulty="medium",
        learning_objectives=("识别连通块入口", "维护已访问节点", "比较 DFS 和并查集视角"),
        interaction_focus="当前连通块和 seen 集合",
    ),
    _Operation(
        id="graph_bfs_distances",
        title="无权图 BFS 距离表",
        problem="给定无权图 graph 和起点 start，返回所有可达节点到 start 的最短边数。",
        family="BFS/DFS 基础图",
        family_id="basic_graph",
        subfamily_id="bfs_distance_map",
        support_level="strong",
        process_profile="bfs",
        oracle_type="independent_reference",
        input_contract="输入 graph 邻接表和 start。",
        variant_name="队列 BFS 距离表",
        strategy="第一次发现节点时写入距离，并按队列层次继续扩展。",
        time_complexity="O(V+E)",
        space_complexity="O(V)",
        expected_layouts=("graph", "queue", "map"),
        solve_body="""
graph = input_data["graph"]
start = input_data["start"]
dist = {start: 0}
queue = [start]
for node in queue:
    for nxt in graph.get(node, []):
        if nxt not in dist:
            dist[nxt] = dist[node] + 1
            queue.append(nxt)
return {key: dist[key] for key in sorted(dist)}
""",
        verifier_body="""
graph = input_data["graph"]
start = input_data["start"]
dist = {start: 0}
for _ in range(len(graph) + 1):
    changed = False
    for node, neighbors in graph.items():
        if node not in dist:
            continue
        for nxt in neighbors:
            candidate = dist[node] + 1
            if nxt not in dist or candidate < dist[nxt]:
                dist[nxt] = candidate
                changed = True
    if not changed:
        break
return {key: dist[key] for key in sorted(dist)}
""",
        sample_sets={
            "core": ({"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, "start": "A"}, {"graph": {"S": ["A"], "A": [], "B": []}, "start": "S"}, {"graph": {"0": []}, "start": "0"}),
            "edge": ({"graph": {}, "start": "X"}, {"graph": {"A": ["A"]}, "start": "A"}, {"graph": {"A": [], "B": ["A"]}, "start": "B"}),
            "transfer": ({"graph": {"1": ["2"], "2": ["3"], "3": []}, "start": "1"}, {"graph": {"s": ["a", "b"], "a": ["c"], "b": [], "c": []}, "start": "s"}, {"graph": {"x": ["y"], "y": ["x"], "z": []}, "start": "x"}),
        },
        difficulty="medium",
        learning_objectives=("理解 BFS 分层", "维护距离表", "解释首次访问即最短"),
        interaction_focus="队列头节点和距离表",
    ),
    _Operation(
        id="dp_climb_three_steps",
        title="三步爬楼梯",
        problem="一次可以爬 1、2 或 3 级台阶，给定 n，返回到达第 n 级的方案数。",
        family="一维 DP",
        family_id="dp_1d",
        subfamily_id="linear_dp_three_steps",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入非负整数 n。",
        variant_name="三来源线性 DP",
        strategy="dp[i]=dp[i-1]+dp[i-2]+dp[i-3]，越界来源贡献 0。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array",),
        solve_body="""
n = input_data["n"]
dp = [0] * (max(n, 2) + 1)
dp[0] = 1
for i in range(1, n + 1):
    dp[i] = dp[i - 1]
    if i >= 2:
        dp[i] += dp[i - 2]
    if i >= 3:
        dp[i] += dp[i - 3]
return dp[n]
""",
        verifier_body="""
n = input_data["n"]
def count(remaining):
    if remaining == 0:
        return 1
    if remaining < 0:
        return 0
    return count(remaining - 1) + count(remaining - 2) + count(remaining - 3)
return count(n)
""",
        sample_sets={
            "core": ({"n": 1}, {"n": 3}, {"n": 5}),
            "edge": ({"n": 0}, {"n": 2}, {"n": 4}),
            "transfer": ({"n": 6}, {"n": 7}, {"n": 8}),
        },
        difficulty="easy",
        learning_objectives=("定义 dp 状态", "理解三种转移来源", "处理 n=0 base case"),
        interaction_focus="dp[i-1], dp[i-2], dp[i-3]",
    ),
    _Operation(
        id="dp_max_subarray",
        title="最大连续子数组和",
        problem="给定整数数组 nums，返回非空连续子数组的最大和。",
        family="一维 DP",
        family_id="dp_1d",
        subfamily_id="max_subarray",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入非空整数数组 nums。",
        variant_name="Kadane 动态规划",
        strategy="current 表示以当前位置结尾的最大和，best 表示历史最大和。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array",),
        solve_body="""
nums = input_data["nums"]
current = nums[0]
best = nums[0]
for value in nums[1:]:
    current = max(value, current + value)
    best = max(best, current)
return best
""",
        verifier_body="""
nums = input_data["nums"]
best = nums[0]
for left in range(len(nums)):
    total = 0
    for right in range(left, len(nums)):
        total += nums[right]
        best = max(best, total)
return best
""",
        sample_sets={
            "core": ({"nums": [-2, 1, -3, 4, -1, 2, 1, -5, 4]}, {"nums": [1]}, {"nums": [5, 4, -1, 7, 8]}),
            "edge": ({"nums": [-1, -2, -3]}, {"nums": [0, 0]}, {"nums": [-2, 0, -1]}),
            "transfer": ({"nums": [3, -2, 5, -1]}, {"nums": [2, -10, 4, 5]}, {"nums": [-5, 6, -2, 3]}),
        },
        difficulty="medium",
        learning_objectives=("理解以当前位置结尾的状态", "比较重启和延续", "维护全局 best"),
        interaction_focus="current 与 best",
    ),
    _Operation(
        id="dp_decode_ways",
        title="数字串解码方案数",
        problem="给定只含数字的字符串 digits，按 1-26 映射到字母，返回解码方案数。",
        family="DP 核心扩展",
        family_id="dp_core",
        subfamily_id="decode_ways",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入数字字符串 digits。",
        variant_name="字符串线性 DP",
        strategy="dp[i] 从单字符解码和双字符解码两个来源累加。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("string", "array"),
        solve_body="""
s = input_data["digits"]
dp = [0] * (len(s) + 1)
dp[0] = 1
for i in range(1, len(s) + 1):
    if s[i - 1] != "0":
        dp[i] += dp[i - 1]
    if i >= 2 and 10 <= int(s[i - 2:i]) <= 26:
        dp[i] += dp[i - 2]
return dp[len(s)]
""",
        verifier_body="""
s = input_data["digits"]
def count(index):
    if index == len(s):
        return 1
    if s[index] == "0":
        return 0
    total = count(index + 1)
    if index + 1 < len(s) and int(s[index:index + 2]) <= 26:
        total += count(index + 2)
    return total
return count(0)
""",
        sample_sets={
            "core": ({"digits": "12"}, {"digits": "226"}, {"digits": "06"}),
            "edge": ({"digits": "0"}, {"digits": "10"}, {"digits": "100"}),
            "transfer": ({"digits": "11106"}, {"digits": "27"}, {"digits": "2612"}),
        },
        difficulty="medium",
        learning_objectives=("理解单字符和双字符转移", "处理 0 的非法情况", "维护字符串前缀 dp"),
        interaction_focus="dp[i-1] 与 dp[i-2] 来源",
    ),
    _Operation(
        id="dp_grid_paths_obstacles",
        title="带障碍网格路径数",
        problem="给定 0/1 网格，0 可走、1 障碍，只能向右或向下，返回从左上到右下路径数。",
        family="二维 DP",
        family_id="dp_2d",
        subfamily_id="grid_obstacle_paths",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入 grid 矩阵。",
        variant_name="障碍网格 DP",
        strategy="障碍格路径数为 0，其余格由上方和左方路径数相加。",
        time_complexity="O(RC)",
        space_complexity="O(RC)",
        expected_layouts=("matrix",),
        solve_body="""
grid = input_data["grid"]
rows, cols = len(grid), len(grid[0])
dp = [[0] * cols for _ in range(rows)]
dp[0][0] = 0 if grid[0][0] else 1
for r in range(rows):
    for c in range(cols):
        if grid[r][c] or (r == 0 and c == 0):
            continue
        dp[r][c] = (dp[r - 1][c] if r else 0) + (dp[r][c - 1] if c else 0)
return dp[-1][-1]
""",
        verifier_body="""
grid = input_data["grid"]
rows, cols = len(grid), len(grid[0])
def count(r, c):
    if r >= rows or c >= cols or grid[r][c]:
        return 0
    if r == rows - 1 and c == cols - 1:
        return 1
    return count(r + 1, c) + count(r, c + 1)
return count(0, 0)
""",
        sample_sets={
            "core": ({"grid": [[0, 0, 0], [0, 1, 0], [0, 0, 0]]}, {"grid": [[0, 1], [0, 0]]}, {"grid": [[0]]}),
            "edge": ({"grid": [[1]]}, {"grid": [[0, 1]]}, {"grid": [[0], [1]]}),
            "transfer": ({"grid": [[0, 0], [0, 0]]}, {"grid": [[0, 0, 1], [0, 0, 0]]}, {"grid": [[0, 0, 0, 0]]}),
        },
        difficulty="medium",
        learning_objectives=("理解二维转移", "处理障碍格", "解释边界行列"),
        interaction_focus="上方和左方路径数",
    ),
    _Operation(
        id="dp_subset_sum_possible",
        title="子集和可达性",
        problem="给定正整数数组 nums 和 target，判断是否存在一个子集和等于 target。",
        family="DP 核心扩展",
        family_id="dp_core",
        subfamily_id="subset_sum_possible",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入 nums 和 target。",
        variant_name="可达集合 DP",
        strategy="维护已经可达的和，处理每个数时加入 total+value 的新和。",
        time_complexity="O(n*target)",
        space_complexity="O(target)",
        expected_layouts=("array", "map"),
        solve_body="""
reachable = {0}
for value in input_data["nums"]:
    additions = set()
    for total in reachable:
        additions.add(total + value)
    reachable |= additions
return input_data["target"] in reachable
""",
        verifier_body="""
nums = input_data["nums"]
target = input_data["target"]
for mask in range(1 << len(nums)):
    total = 0
    for index, value in enumerate(nums):
        if mask & (1 << index):
            total += value
    if total == target:
        return True
return False
""",
        sample_sets={
            "core": ({"nums": [3, 34, 4, 12, 5, 2], "target": 9}, {"nums": [1, 2, 3], "target": 7}, {"nums": [2, 4], "target": 6}),
            "edge": ({"nums": [], "target": 0}, {"nums": [], "target": 1}, {"nums": [5], "target": 5}),
            "transfer": ({"nums": [1, 5, 11, 5], "target": 11}, {"nums": [2, 2, 2], "target": 4}, {"nums": [8, 1, 3], "target": 2}),
        },
        difficulty="medium",
        learning_objectives=("理解可达状态集合", "比较选择和不选择", "用 brute force 校验小样例"),
        interaction_focus="reachable 集合和当前数字",
    ),
    _Operation(
        id="tree_max_depth",
        title="二叉树最大深度",
        problem="给定二叉树，返回从根到最深叶子的节点数。",
        family="树 / BST / LCA",
        family_id="tree_bst_lca",
        subfamily_id="max_depth",
        support_level="strong",
        process_profile="tree",
        oracle_type="independent_reference",
        input_contract="输入 tree={root, children}。",
        variant_name="递归高度",
        strategy="空节点深度为 0，非空节点深度为左右子树最大深度加 1。",
        time_complexity="O(n)",
        space_complexity="O(h)",
        expected_layouts=("tree", "recursion_tree"),
        solve_body="""
tree = input_data["tree"]
children = tree.get("children", {})
def depth(node):
    if node is None:
        return 0
    left, right = children.get(node, [None, None])
    return 1 + max(depth(left), depth(right))
return depth(tree.get("root"))
""",
        verifier_body="""
tree = input_data["tree"]
root = tree.get("root")
if root is None:
    return 0
children = tree.get("children", {})
queue = [(root, 1)]
best = 0
for node, level in queue:
    best = max(best, level)
    left, right = children.get(node, [None, None])
    if left is not None:
        queue.append((left, level + 1))
    if right is not None:
        queue.append((right, level + 1))
return best
""",
        sample_sets={
            "core": ({"tree": {"root": "A", "children": {"A": ["B", "C"], "B": [None, None], "C": ["D", None], "D": [None, None]}}}, {"tree": {"root": "R", "children": {"R": [None, None]}}}, {"tree": {"root": None, "children": {}}}),
            "edge": ({"tree": {"root": "1", "children": {"1": ["2", None], "2": ["3", None], "3": [None, None]}}}, {"tree": {"root": "x", "children": {"x": [None, "y"], "y": [None, None]}}}, {"tree": {"root": None, "children": {}}}),
            "transfer": ({"tree": {"root": "5", "children": {"5": ["3", "7"], "3": ["2", None], "7": [None, "9"], "2": [None, None], "9": [None, None]}}}, {"tree": {"root": "a", "children": {"a": ["b", None], "b": [None, "c"], "c": [None, None]}}}, {"tree": {"root": "solo", "children": {"solo": [None, None]}}}),
        },
        difficulty="easy",
        learning_objectives=("理解树高定义", "合并左右子树结果", "处理空树"),
        interaction_focus="左右子树深度",
    ),
    _Operation(
        id="tree_path_sum_exists",
        title="根到叶路径和",
        problem="给定带节点值的二叉树和 target，判断是否存在根到叶路径和等于 target。",
        family="树 / BST / LCA",
        family_id="tree_bst_lca",
        subfamily_id="path_sum",
        support_level="strong",
        process_profile="tree",
        oracle_type="independent_reference",
        input_contract="输入 tree={root, values, children} 和 target。",
        variant_name="DFS 累加路径和",
        strategy="递归携带从根到当前节点的累计和，到叶子时比较 target。",
        time_complexity="O(n)",
        space_complexity="O(h)",
        expected_layouts=("tree", "recursion_tree"),
        solve_body="""
tree = input_data["tree"]
values = tree.get("values", {})
children = tree.get("children", {})
target = input_data["target"]
def visit(node, total):
    if node is None:
        return False
    left, right = children.get(node, [None, None])
    new_total = total + values[node]
    if left is None and right is None:
        return new_total == target
    return visit(left, new_total) or visit(right, new_total)
return visit(tree.get("root"), 0)
""",
        verifier_body="""
tree = input_data["tree"]
values = tree.get("values", {})
children = tree.get("children", {})
target = input_data["target"]
paths = []
def collect(node, total):
    if node is None:
        return
    left, right = children.get(node, [None, None])
    new_total = total + values[node]
    if left is None and right is None:
        paths.append(new_total)
    collect(left, new_total)
    collect(right, new_total)
collect(tree.get("root"), 0)
return target in paths
""",
        sample_sets={
            "core": ({"tree": {"root": "A", "values": {"A": 5, "B": 4, "C": 8}, "children": {"A": ["B", "C"], "B": [None, None], "C": [None, None]}}, "target": 9}, {"tree": {"root": "A", "values": {"A": 1}, "children": {"A": [None, None]}}, "target": 2}, {"tree": {"root": None, "values": {}, "children": {}}, "target": 0}),
            "edge": ({"tree": {"root": "A", "values": {"A": 0}, "children": {"A": [None, None]}}, "target": 0}, {"tree": {"root": "A", "values": {"A": -1, "B": 1}, "children": {"A": ["B", None], "B": [None, None]}}, "target": 0}, {"tree": {"root": "A", "values": {"A": 2, "B": 3}, "children": {"A": [None, "B"], "B": [None, None]}}, "target": 5}),
            "transfer": ({"tree": {"root": "R", "values": {"R": 3, "L": 2, "X": 6}, "children": {"R": ["L", "X"], "L": [None, None], "X": [None, None]}}, "target": 9}, {"tree": {"root": "R", "values": {"R": 3, "L": 2}, "children": {"R": ["L", None], "L": [None, None]}}, "target": 4}, {"tree": {"root": "R", "values": {"R": 1, "A": 2, "B": 3}, "children": {"R": ["A", "B"], "A": [None, None], "B": [None, None]}}, "target": 3}),
        },
        difficulty="medium",
        learning_objectives=("理解根到叶路径", "维护累计和", "区分内部节点和叶子"),
        interaction_focus="当前路径累计和",
    ),
    _Operation(
        id="tree_preorder",
        title="二叉树先序遍历",
        problem="给定二叉树，返回先访问根、再左子树、再右子树的节点序列。",
        family="树 / BST / LCA",
        family_id="tree_bst_lca",
        subfamily_id="preorder_traversal",
        support_level="strong",
        process_profile="tree",
        oracle_type="independent_reference",
        input_contract="输入 tree={root, children}。",
        variant_name="递归先序遍历",
        strategy="访问当前节点后，递归遍历左孩子和右孩子。",
        time_complexity="O(n)",
        space_complexity="O(h)",
        expected_layouts=("tree", "recursion_tree"),
        solve_body="""
tree = input_data["tree"]
children = tree.get("children", {})
result = []
def visit(node):
    if node is None:
        return
    result.append(node)
    left, right = children.get(node, [None, None])
    visit(left)
    visit(right)
visit(tree.get("root"))
return result
""",
        verifier_body="""
tree = input_data["tree"]
children = tree.get("children", {})
result = []
stack = [tree.get("root")] if tree.get("root") is not None else []
while stack:
    node = stack.pop()
    result.append(node)
    left, right = children.get(node, [None, None])
    if right is not None:
        stack.append(right)
    if left is not None:
        stack.append(left)
return result
""",
        sample_sets={
            "core": ({"tree": {"root": "A", "children": {"A": ["B", "C"], "B": [None, None], "C": [None, None]}}}, {"tree": {"root": "R", "children": {"R": [None, None]}}}, {"tree": {"root": None, "children": {}}}),
            "edge": ({"tree": {"root": "1", "children": {"1": ["2", None], "2": [None, "3"], "3": [None, None]}}}, {"tree": {"root": "x", "children": {"x": [None, "y"], "y": [None, None]}}}, {"tree": {"root": "a", "children": {"a": [None, None]}}}),
            "transfer": ({"tree": {"root": "M", "children": {"M": ["L", "R"], "L": ["LL", None], "R": [None, "RR"], "LL": [None, None], "RR": [None, None]}}}, {"tree": {"root": "0", "children": {"0": ["1", "2"], "1": ["3", "4"], "2": [None, None], "3": [None, None], "4": [None, None]}}}, {"tree": {"root": None, "children": {}}}),
        },
        difficulty="easy",
        learning_objectives=("理解先序顺序", "比较递归和栈实现", "处理空子树"),
        interaction_focus="当前节点与递归调用栈",
    ),
    _Operation(
        id="heap_last_stone",
        title="最后一块石头重量",
        problem="给定石头重量数组，每次取出两块最重石头相撞，返回最后剩余重量，没有则为 0。",
        family="堆 / TopK / Huffman",
        family_id="heap_topk_huffman",
        subfamily_id="max_heap_simulation",
        support_level="medium_plus",
        process_profile="heap",
        oracle_type="independent_reference",
        input_contract="输入 stones 数组。",
        variant_name="负数模拟最大堆",
        strategy="用小顶堆存负权重，反复弹出两个最大值并把差值放回。",
        time_complexity="O(n log n)",
        space_complexity="O(n)",
        expected_layouts=("heap",),
        solve_body="""
heap = [-value for value in input_data["stones"]]
heapq.heapify(heap)
while len(heap) > 1:
    a = -heapq.heappop(heap)
    b = -heapq.heappop(heap)
    if a != b:
        heapq.heappush(heap, -(a - b))
return -heap[0] if heap else 0
""",
        verifier_body="""
stones = list(input_data["stones"])
while len(stones) > 1:
    stones.sort()
    a = stones.pop()
    b = stones.pop()
    if a != b:
        stones.append(a - b)
return stones[0] if stones else 0
""",
        sample_sets={
            "core": ({"stones": [2, 7, 4, 1, 8, 1]}, {"stones": [1]}, {"stones": [3, 3]}),
            "edge": ({"stones": []}, {"stones": [10, 4]}, {"stones": [1, 1, 1]}),
            "transfer": ({"stones": [9, 3, 2, 10]}, {"stones": [5, 5, 5, 5]}, {"stones": [6, 2, 2, 1]}),
        },
        difficulty="medium",
        learning_objectives=("理解最大堆取顶", "模拟相撞规则", "处理堆为空或单元素"),
        interaction_focus="堆顶两块石头",
    ),
    _Operation(
        id="heap_k_smallest",
        title="最小的 K 个数",
        problem="给定整数数组 nums 和 k，返回升序排列的最小 k 个数。",
        family="堆 / TopK / Huffman",
        family_id="heap_topk_huffman",
        subfamily_id="k_smallest",
        support_level="medium_plus",
        process_profile="heap",
        oracle_type="property",
        input_contract="输入 nums 和 k。",
        variant_name="小顶堆弹出 K 次",
        strategy="把所有数建成小顶堆，连续弹出 k 次得到最小 k 个数。",
        time_complexity="O(n+k log n)",
        space_complexity="O(n)",
        expected_layouts=("heap", "array"),
        solve_body="""
nums = list(input_data["nums"])
heapq.heapify(nums)
limit = min(input_data["k"], len(nums))
result = []
for _ in range(limit):
    result.append(heapq.heappop(nums))
return result
""",
        verifier_body="""
return sorted(input_data["nums"])[:input_data["k"]]
""",
        sample_sets={
            "core": ({"nums": [3, 2, 1], "k": 2}, {"nums": [5, 1, 4, 2], "k": 3}, {"nums": [1], "k": 1}),
            "edge": ({"nums": [], "k": 3}, {"nums": [2, 2, 1], "k": 5}, {"nums": [9], "k": 0}),
            "transfer": ({"nums": [-1, 5, 0], "k": 2}, {"nums": [10, 9, 8, 7], "k": 1}, {"nums": [4, 4, 4], "k": 2}),
        },
        difficulty="easy",
        learning_objectives=("理解小顶堆", "追踪弹出次数", "处理 k 超过数组长度"),
        interaction_focus="堆顶与剩余 k",
    ),
    _Operation(
        id="greedy_assign_cookies",
        title="分发饼干",
        problem="给定孩子胃口 children 和饼干尺寸 cookies，返回最多能满足的孩子数量。",
        family="贪心",
        family_id="greedy",
        subfamily_id="assign_cookies",
        support_level="medium_plus",
        process_profile="greedy",
        oracle_type="bruteforce",
        input_contract="输入 children 和 cookies 数组。",
        variant_name="排序双指针贪心",
        strategy="按从小到大匹配，当前饼干能满足最小未满足胃口时分配。",
        time_complexity="O(n log n + m log m)",
        space_complexity="O(n+m)",
        expected_layouts=("array", "pointer"),
        solve_body="""
children = sorted(input_data["children"])
cookies = sorted(input_data["cookies"])
child = 0
cookie = 0
answer = 0
while child < len(children) and cookie < len(cookies):
    if cookies[cookie] >= children[child]:
        answer += 1
        child += 1
    cookie += 1
return answer
""",
        verifier_body="""
children = input_data["children"]
cookies = input_data["cookies"]
best = 0
for mask in range(1 << len(cookies)):
    chosen = []
    for i, cookie in enumerate(cookies):
        if mask & (1 << i):
            chosen.append(cookie)
    if len(chosen) > len(children):
        continue
    chosen.sort()
    needs = sorted(children)
    matched = 0
    for cookie in chosen:
        if matched < len(needs) and cookie >= needs[matched]:
            matched += 1
    best = max(best, matched)
return best
""",
        sample_sets={
            "core": ({"children": [1, 2, 3], "cookies": [1, 1]}, {"children": [1, 2], "cookies": [1, 2, 3]}, {"children": [2], "cookies": [1]}),
            "edge": ({"children": [], "cookies": [1, 2]}, {"children": [1], "cookies": []}, {"children": [], "cookies": []}),
            "transfer": ({"children": [2, 3, 4], "cookies": [1, 3, 5]}, {"children": [1, 1, 2], "cookies": [1, 1]}, {"children": [5, 6], "cookies": [7]}),
        },
        difficulty="easy",
        learning_objectives=("理解排序贪心", "匹配最小可满足需求", "解释为什么小饼干优先尝试"),
        interaction_focus="当前孩子胃口和饼干尺寸",
    ),
    _Operation(
        id="greedy_lemonade_change",
        title="柠檬水找零",
        problem="顾客依次用 5、10、20 元买 5 元柠檬水，判断是否能给每位顾客正确找零。",
        family="贪心",
        family_id="greedy",
        subfamily_id="cash_change",
        support_level="medium_plus",
        process_profile="greedy",
        oracle_type="independent_reference",
        input_contract="输入 bills 数组。",
        variant_name="优先使用 10 元找零",
        strategy="收到 20 元时优先用 10+5 找零，否则用三个 5。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array", "map"),
        solve_body="""
five = 0
ten = 0
for bill in input_data["bills"]:
    if bill == 5:
        five += 1
    elif bill == 10:
        if five == 0:
            return False
        five -= 1
        ten += 1
    else:
        if ten > 0 and five > 0:
            ten -= 1
            five -= 1
        elif five >= 3:
            five -= 3
        else:
            return False
return True
""",
        verifier_body="""
states = {(0, 0)}
for bill in input_data["bills"]:
    next_states = set()
    for five, ten in states:
        if bill == 5:
            next_states.add((five + 1, ten))
        elif bill == 10 and five >= 1:
            next_states.add((five - 1, ten + 1))
        elif bill == 20:
            if ten >= 1 and five >= 1:
                next_states.add((five - 1, ten - 1))
            if five >= 3:
                next_states.add((five - 3, ten))
    states = next_states
    if not states:
        return False
return True
""",
        sample_sets={
            "core": ({"bills": [5, 5, 5, 10, 20]}, {"bills": [5, 5, 10, 10, 20]}, {"bills": [5, 10, 5, 20]}),
            "edge": ({"bills": []}, {"bills": [10]}, {"bills": [20]}),
            "transfer": ({"bills": [5, 5, 10]}, {"bills": [5, 5, 5, 20]}, {"bills": [5, 10, 20]}),
        },
        difficulty="medium",
        learning_objectives=("维护 5 元和 10 元数量", "理解贪心找零优先级", "识别失败时刻"),
        interaction_focus="five/ten 现金状态",
    ),
    _Operation(
        id="string_longest_common_prefix",
        title="最长公共前缀",
        problem="给定字符串数组 words，返回所有字符串共同拥有的最长前缀。",
        family="字符串高级算法",
        family_id="string_advanced",
        subfamily_id="common_prefix",
        support_level="strong",
        process_profile="string",
        oracle_type="independent_reference",
        input_contract="输入 words 字符串数组。",
        variant_name="逐词收缩前缀",
        strategy="用第一个单词作候选前缀，遇到不匹配单词时逐步缩短。",
        time_complexity="O(total_chars)",
        space_complexity="O(1)",
        expected_layouts=("string", "array"),
        solve_body="""
words = input_data["words"]
if not words:
    return ""
prefix = words[0]
for word in words[1:]:
    while not word.startswith(prefix):
        prefix = prefix[:-1]
        if prefix == "":
            return ""
return prefix
""",
        verifier_body="""
words = input_data["words"]
answer = ""
if not words:
    return answer
for length in range(1, len(words[0]) + 1):
    candidate = words[0][:length]
    ok = True
    for word in words:
        if not word.startswith(candidate):
            ok = False
            break
    if ok:
        answer = candidate
return answer
""",
        sample_sets={
            "core": ({"words": ["flower", "flow", "flight"]}, {"words": ["dog", "racecar", "car"]}, {"words": ["interspecies", "interstellar", "interstate"]}),
            "edge": ({"words": []}, {"words": [""]}, {"words": ["a", ""]}),
            "transfer": ({"words": ["throne", "throne"]}, {"words": ["prefix", "preach", "prevent"]}, {"words": ["same"]}),
        },
        difficulty="easy",
        learning_objectives=("理解前缀匹配", "观察候选前缀收缩", "处理空数组和空字符串"),
        interaction_focus="当前候选 prefix",
    ),
    _Operation(
        id="string_is_subsequence",
        title="判断子序列",
        problem="给定字符串 s 和 t，判断 s 是否为 t 的子序列。",
        family="字符串高级算法",
        family_id="string_advanced",
        subfamily_id="subsequence_two_pointer",
        support_level="strong",
        process_profile="string",
        oracle_type="independent_reference",
        input_contract="输入字符串 s 和 t。",
        variant_name="双指针子序列匹配",
        strategy="扫描 t，只有匹配 s 当前字符时才推进 s 指针。",
        time_complexity="O(|t|)",
        space_complexity="O(1)",
        expected_layouts=("string", "pointer"),
        solve_body="""
s = input_data["s"]
t = input_data["t"]
index = 0
for ch in t:
    if index < len(s) and s[index] == ch:
        index += 1
return index == len(s)
""",
        verifier_body="""
s = input_data["s"]
t = input_data["t"]
def match(i, j):
    if i == len(s):
        return True
    if j == len(t):
        return False
    return (s[i] == t[j] and match(i + 1, j + 1)) or match(i, j + 1)
return match(0, 0)
""",
        sample_sets={
            "core": ({"s": "abc", "t": "ahbgdc"}, {"s": "axc", "t": "ahbgdc"}, {"s": "", "t": "abc"}),
            "edge": ({"s": "a", "t": ""}, {"s": "", "t": ""}, {"s": "aaa", "t": "aa"}),
            "transfer": ({"s": "ace", "t": "abcde"}, {"s": "aec", "t": "abcde"}, {"s": "bbb", "t": "bbbbb"}),
        },
        difficulty="easy",
        learning_objectives=("理解子序列非连续性", "维护 s 指针", "处理空串"),
        interaction_focus="s 指针和 t 当前字符",
    ),
    _Operation(
        id="string_count_palindromic_substrings",
        title="回文子串数量",
        problem="给定字符串 text，返回其中所有回文子串的数量。",
        family="字符串高级算法",
        family_id="string_advanced",
        subfamily_id="palindrome_center_expand",
        support_level="strong",
        process_profile="string",
        oracle_type="bruteforce",
        input_contract="输入字符串 text。",
        variant_name="中心扩展",
        strategy="枚举奇数和偶数中心，向两侧扩展直到不相等。",
        time_complexity="O(n^2)",
        space_complexity="O(1)",
        expected_layouts=("string", "pointer"),
        solve_body="""
text = input_data["text"]
count = 0
for center in range(len(text)):
    left = center
    right = center
    while left >= 0 and right < len(text) and text[left] == text[right]:
        count += 1
        left -= 1
        right += 1
    left = center
    right = center + 1
    while left >= 0 and right < len(text) and text[left] == text[right]:
        count += 1
        left -= 1
        right += 1
return count
""",
        verifier_body="""
text = input_data["text"]
count = 0
for left in range(len(text)):
    for right in range(left, len(text)):
        candidate = text[left:right + 1]
        if candidate == candidate[::-1]:
            count += 1
return count
""",
        sample_sets={
            "core": ({"text": "abc"}, {"text": "aaa"}, {"text": "aba"}),
            "edge": ({"text": ""}, {"text": "a"}, {"text": "aa"}),
            "transfer": ({"text": "abba"}, {"text": "abccba"}, {"text": "abcd"}),
        },
        difficulty="medium",
        learning_objectives=("理解回文中心", "区分奇偶长度", "累计扩展成功次数"),
        interaction_focus="中心点和左右指针",
    ),
    _Operation(
        id="union_count_components",
        title="并查集连通分量数",
        problem="给定 n 个节点和无向边 edges，使用并查集返回连通分量数量。",
        family="并查集",
        family_id="union_find",
        subfamily_id="component_count",
        support_level="strong",
        process_profile="union_find",
        oracle_type="independent_reference",
        input_contract="输入 n 和 edges。",
        variant_name="Union-Find 合并计数",
        strategy="初始每个节点自成集合，处理每条边时合并两个集合。",
        time_complexity="O(E alpha(V))",
        space_complexity="O(V)",
        expected_layouts=("union_find", "graph"),
        solve_body="""
n = input_data["n"]
parent = list(range(n))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
for a, b in input_data["edges"]:
    ra = find(a)
    rb = find(b)
    if ra != rb:
        parent[rb] = ra
roots = set()
for node in range(n):
    roots.add(find(node))
return len(roots)
""",
        verifier_body="""
n = input_data["n"]
graph = {i: [] for i in range(n)}
for a, b in input_data["edges"]:
    graph[a].append(b)
    graph[b].append(a)
seen = set()
count = 0
for node in range(n):
    if node in seen:
        continue
    count += 1
    stack = [node]
    seen.add(node)
    while stack:
        current = stack.pop()
        for nxt in graph[current]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
return count
""",
        sample_sets={
            "core": ({"n": 5, "edges": [[0, 1], [1, 2], [3, 4]]}, {"n": 3, "edges": []}, {"n": 4, "edges": [[0, 1], [1, 2], [2, 3]]}),
            "edge": ({"n": 0, "edges": []}, {"n": 1, "edges": []}, {"n": 2, "edges": [[0, 1]]}),
            "transfer": ({"n": 6, "edges": [[0, 5], [1, 2], [2, 3]]}, {"n": 6, "edges": [[0, 1], [2, 3], [4, 5]]}, {"n": 5, "edges": [[0, 1], [3, 4]]}),
        },
        difficulty="medium",
        learning_objectives=("理解代表元", "执行 union 操作", "统计最终根节点数"),
        interaction_focus="两个端点的代表元",
    ),
)


__all__ = ["cases", "metadata"]
