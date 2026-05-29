"""Benchmark cases: array pointer."""

from __future__ import annotations

from tests.benchmark_cases import BenchmarkCase, BenchmarkInput

BINARY_SEARCH_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""


BINARY_SEARCH_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    left, right = 0, len(nums) - 1
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "pointer:left"}, {"id": "pointer:right"}], "value": [left, right], "state": {"nums": nums, "left": left, "right": right, "target": target}, "reason": "初始化二分搜索区间。", "code_line": 1}]
    result = -1
    while left <= right:
        mid = (left + right) // 2
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{mid}]"}, {"id": "pointer:mid"}], "value": mid, "state": {"nums": nums, "left": left, "right": right, "mid": mid, "target": target}, "role": "candidate", "reason": "比较中点值和目标值。", "code_line": 3})
        if nums[mid] == target:
            result = mid
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{mid}]"}], "state": {"nums": nums, "left": left, "right": right, "mid": mid, "target": target}, "role": "answer", "reason": "中点正好等于目标，返回下标。", "code_line": 4})
            break
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
        events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}], "value": [left, right], "state": {"nums": nums, "left": left, "right": right, "target": target}, "role": "current", "reason": "根据比较结果收缩搜索区间。", "code_line": 6})
    if result == -1:
        events.append({"step": len(events), "op": "explain", "state": {"nums": nums, "left": left, "right": right, "target": target}, "reason": "搜索区间为空，目标不存在。", "code_line": 9})
    return {"schema_version": "semantic-trace-v1", "algorithm": "二分查找", "input_data": input_data, "result": result, "pseudocode": ["维护闭区间 [left, right]", "比较中点后丢弃一半区间"], "events": events}
"""


BINARY_SEARCH_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    for i, x in enumerate(nums):
        if x == target:
            return i
    return -1
"""


BINARY_ANSWER_SQRT_CODE = """
def solve(input_data):
    n = input_data["n"]
    left, right = 0, n
    ans = 0
    while left <= right:
        mid = (left + right) // 2
        if mid * mid <= n:
            ans = mid
            left = mid + 1
        else:
            right = mid - 1
    return ans
"""


BINARY_ANSWER_SQRT_TRACKER = """
def trace(input_data):
    n = input_data["n"]
    left, right = 0, n
    ans = 0
    contract = {"submode": "binary_answer"}
    events = [{"step": 0, "op": "create", "targets": [{"id": "candidates"}], "state": {"candidates": list(range(n + 1)), "left": left, "right": right, "answer": ans, "array_contract": contract}, "reason": "初始化整数答案二分区间。", "code_line": 1}]
    while left <= right:
        mid = (left + right) // 2
        ok = mid * mid <= n
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"candidates[{mid}]"}, {"id": "pointer:mid"}], "value": {"mid": mid, "ok": ok}, "state": {"candidates": list(range(n + 1)), "left": left, "right": right, "mid": mid, "answer": ans, "array_contract": contract}, "role": "candidate", "reason": "检查 mid*mid 是否不超过 n。", "code_line": 5})
        if ok:
            ans = mid
            left = mid + 1
        else:
            right = mid - 1
        events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}], "value": [left, right], "state": {"candidates": list(range(n + 1)), "left": left, "right": right, "answer": ans, "array_contract": contract}, "role": "current", "reason": "根据单调谓词收缩答案区间。", "code_line": 9})
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "answer"}], "value": ans, "state": {"candidates": list(range(n + 1)), "left": left, "right": right, "answer": ans, "array_contract": contract}, "role": "answer", "reason": "区间为空，保留的 ans 是最大平方不超过 n 的整数。", "code_line": 12})
    return {"schema_version": "semantic-trace-v1", "algorithm": "二分答案整数平方根", "input_data": input_data, "result": ans, "pseudocode": ["在答案范围上二分", "mid*mid<=n 时向右找更大答案"], "events": events}
"""


BINARY_ANSWER_SQRT_VERIFIER = """
def verify(input_data):
    n = input_data["n"]
    x = 0
    while (x + 1) * (x + 1) <= n:
        x += 1
    return x
"""


TWO_POINTER_PAIR_SUM_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    left, right = 0, len(nums) - 1
    while left < right:
        total = nums[left] + nums[right]
        if total == target:
            return [left, right]
        if total < target:
            left += 1
        else:
            right -= 1
    return []
"""


TWO_POINTER_PAIR_SUM_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    left, right = 0, len(nums) - 1
    contract = {"submode": "two_pointer"}
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "pointer:left"}, {"id": "pointer:right"}], "state": {"nums": nums, "left": left, "right": right, "target": target, "array_contract": contract}, "reason": "初始化左右指针。", "code_line": 1}]
    answer = []
    while left < right:
        total = nums[left] + nums[right]
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{left}]"}, {"id": f"nums[{right}]"}], "value": total, "state": {"nums": nums, "left": left, "right": right, "target": target, "sum": total, "array_contract": contract}, "role": "candidate", "reason": "比较左右指针对应元素之和。", "code_line": 5})
        if total == target:
            answer = [left, right]
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{left}]"}, {"id": f"nums[{right}]"}], "value": answer[:], "state": {"nums": nums, "left": left, "right": right, "target": target, "sum": total, "answer": answer[:], "array_contract": contract}, "role": "answer", "reason": "两数之和等于 target，返回指针位置。", "code_line": 7})
            break
        if total < target:
            left += 1
        else:
            right -= 1
        events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}], "value": [left, right], "state": {"nums": nums, "left": left, "right": right, "target": target, "array_contract": contract}, "role": "current", "reason": "根据有序数组和当前和移动一侧指针。", "code_line": 11})
    if not answer:
        events.append({"step": len(events), "op": "mark", "targets": [{"id": "nums"}], "value": [], "state": {"nums": nums, "left": left, "right": right, "target": target, "answer": [], "array_contract": contract}, "role": "answer", "reason": "左右指针相遇，没有找到目标和。", "code_line": 12})
    return {"schema_version": "semantic-trace-v1", "algorithm": "双指针有序两数之和", "input_data": input_data, "result": answer, "pseudocode": ["小于 target 移动 left", "大于 target 移动 right"], "events": events}
"""


TWO_POINTER_PAIR_SUM_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""


SLIDING_WINDOW_MIN_LEN_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    left = 0
    total = 0
    best = len(nums) + 1
    for right, value in enumerate(nums):
        total += value
        while total >= target:
            best = min(best, right - left + 1)
            total -= nums[left]
            left += 1
    return 0 if best == len(nums) + 1 else best
"""


SLIDING_WINDOW_MIN_LEN_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    left = 0
    total = 0
    best = len(nums) + 1
    contract = {"submode": "sliding_window"}
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}], "state": {"nums": nums, "left": 0, "right": -1, "window_sum": 0, "best": None, "array_contract": contract}, "reason": "初始化空滑动窗口。", "code_line": 1}]
    for right, value in enumerate(nums):
        total += value
        events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:right"}], "value": right, "state": {"nums": nums, "left": left, "right": right, "window_sum": total, "best": None if best == len(nums) + 1 else best, "array_contract": contract}, "role": "current", "reason": "右端进入新元素，扩大窗口。", "code_line": 6})
        while total >= target:
            best = min(best, right - left + 1)
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{left}:{right + 1}]"}], "value": best, "state": {"nums": nums, "left": left, "right": right, "window_sum": total, "best": best, "array_contract": contract}, "role": "candidate", "reason": "当前窗口满足条件，更新最短长度候选。", "code_line": 8})
            total -= nums[left]
            left += 1
            events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:left"}], "value": left, "state": {"nums": nums, "left": left, "right": right, "window_sum": total, "best": best, "array_contract": contract}, "role": "current", "reason": "左端移出一个元素，尝试收缩窗口。", "code_line": 10})
    answer = 0 if best == len(nums) + 1 else best
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "best"}], "value": answer, "state": {"nums": nums, "left": left, "right": len(nums) - 1, "window_sum": total, "best": answer, "answer": answer, "array_contract": contract}, "role": "answer", "reason": "扫描结束，得到最短满足窗口长度。", "code_line": 12})
    return {"schema_version": "semantic-trace-v1", "algorithm": "滑动窗口最短子数组", "input_data": input_data, "result": answer, "pseudocode": ["右端扩张", "满足条件时左端收缩"], "events": events}
"""


SLIDING_WINDOW_MIN_LEN_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    best = len(nums) + 1
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total >= target:
                best = min(best, j - i + 1)
                break
    return 0 if best == len(nums) + 1 else best
"""


PREFIX_SUM_RANGE_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    left, right = input_data["query"]
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)
    return prefix[right + 1] - prefix[left]
"""


PREFIX_SUM_RANGE_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    left, right = input_data["query"]
    prefix = [0] * (len(nums) + 1)
    contract = {"submode": "prefix_sum", "expected_targets": [f"prefix[{i}]" for i in range(1, len(nums) + 1)]}
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "prefix"}], "state": {"nums": nums, "prefix": prefix[:], "query": [left, right], "array_contract": contract}, "reason": "初始化前缀和数组，prefix[0]=0。", "code_line": 1}]
    for i, x in enumerate(nums):
        prefix[i + 1] = prefix[i] + x
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"prefix[{i + 1}]"}], "value": prefix[i + 1], "deps": [{"id": f"prefix[{i}]"}, {"id": f"nums[{i}]"}], "state": {"nums": nums, "prefix": prefix[:], "query": [left, right], "i": i, "array_contract": contract}, "role": "current", "reason": "prefix[i+1] 等于 prefix[i] 加当前 nums[i]。", "code_line": 5})
    answer = prefix[right + 1] - prefix[left]
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "answer"}], "value": answer, "deps": [{"id": f"prefix[{right + 1}]"}, {"id": f"prefix[{left}]"}], "state": {"nums": nums, "prefix": prefix[:], "query": [left, right], "answer": answer, "array_contract": contract}, "role": "answer", "reason": "区间和由右端前缀减去左端前一位前缀。", "code_line": 6})
    return {"schema_version": "semantic-trace-v1", "algorithm": "前缀和区间查询", "input_data": input_data, "result": answer, "pseudocode": ["prefix[i+1]=prefix[i]+nums[i]", "sum(l,r)=prefix[r+1]-prefix[l]"], "events": events}
"""


PREFIX_SUM_RANGE_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    left, right = input_data["query"]
    return sum(nums[left:right + 1])
"""


DIFFERENCE_ARRAY_RANGE_ADD_CODE = """
def solve(input_data):
    nums = input_data["nums"][:]
    updates = input_data["updates"]
    diff = [0] * (len(nums) + 1)
    if nums:
        diff[0] = nums[0]
        for i in range(1, len(nums)):
            diff[i] = nums[i] - nums[i - 1]
    for left, right, delta in updates:
        diff[left] += delta
        if right + 1 < len(diff):
            diff[right + 1] -= delta
    result = []
    cur = 0
    for i in range(len(nums)):
        cur += diff[i]
        result.append(cur)
    return result
"""


DIFFERENCE_ARRAY_RANGE_ADD_TRACKER = """
def trace(input_data):
    nums = input_data["nums"][:]
    updates = input_data["updates"]
    diff = [0] * (len(nums) + 1)
    if nums:
        diff[0] = nums[0]
        for i in range(1, len(nums)):
            diff[i] = nums[i] - nums[i - 1]
    expected = []
    for left, right, delta in updates:
        expected.append(f"diff[{left}]")
        expected.append(f"diff[{right + 1}]")
    contract = {"submode": "difference_array", "expected_targets": expected}
    events = [{"step": 0, "op": "create", "targets": [{"id": "diff"}], "state": {"nums": nums[:], "diff": diff[:], "updates": updates, "array_contract": contract}, "reason": "初始化差分数组。", "code_line": 1}]
    for update_index, (left, right, delta) in enumerate(updates):
        diff[left] += delta
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"diff[{left}]"}], "value": diff[left], "deps": [{"id": f"updates[{update_index}]"}], "state": {"nums": nums[:], "diff": diff[:], "updates": updates, "update_index": update_index, "array_contract": contract}, "role": "current", "reason": "区间左端差分加 delta。", "code_line": 9})
        if right + 1 < len(diff):
            diff[right + 1] -= delta
            events.append({"step": len(events), "op": "set", "targets": [{"id": f"diff[{right + 1}]"}], "value": diff[right + 1], "deps": [{"id": f"updates[{update_index}]"}], "state": {"nums": nums[:], "diff": diff[:], "updates": updates, "update_index": update_index, "array_contract": contract}, "role": "current", "reason": "区间右端后一位差分减 delta。", "code_line": 11})
    result = []
    cur = 0
    for i in range(len(nums)):
        cur += diff[i]
        result.append(cur)
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "diff"}], "value": result[:], "state": {"nums": nums[:], "diff": diff[:], "updates": updates, "answer": result[:], "array_contract": contract}, "role": "answer", "reason": "对差分数组做前缀还原得到最终数组。", "code_line": 15})
    return {"schema_version": "semantic-trace-v1", "algorithm": "差分数组区间加", "input_data": input_data, "result": result, "pseudocode": ["diff[l]+=delta", "diff[r+1]-=delta", "前缀还原数组"], "events": events}
"""


DIFFERENCE_ARRAY_RANGE_ADD_VERIFIER = """
def verify(input_data):
    result = input_data["nums"][:]
    for left, right, delta in input_data["updates"]:
        for i in range(left, right + 1):
            result[i] += delta
    return result
"""


FAST_SLOW_CYCLE_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    if not nums:
        return False
    slow = fast = 0
    for _ in range(len(nums) + 1):
        slow = nums[slow]
        fast = nums[nums[fast]]
        if slow == fast:
            return True
    return False
"""


FAST_SLOW_CYCLE_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    contract = {"submode": "fast_slow"}
    if not nums:
        return {"schema_version": "semantic-trace-v1", "algorithm": "快慢指针判环", "input_data": input_data, "result": False, "pseudocode": ["空映射无环"], "events": [{"step": 0, "op": "create", "targets": [{"id": "nums"}], "state": {"nums": nums, "answer": False, "array_contract": contract}, "reason": "空数组没有可走指针。", "code_line": 1}]}
    slow = fast = 0
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "pointer:slow"}, {"id": "pointer:fast"}], "state": {"nums": nums, "slow": slow, "fast": fast, "array_contract": contract}, "reason": "初始化快慢指针。", "code_line": 1}]
    answer = False
    for _ in range(len(nums) + 1):
        slow = nums[slow]
        fast = nums[nums[fast]]
        events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:slow"}, {"id": "pointer:fast"}], "value": [slow, fast], "deps": [{"id": f"nums[{slow}]"}, {"id": f"nums[{fast}]"}], "state": {"nums": nums, "slow": slow, "fast": fast, "array_contract": contract}, "role": "current", "reason": "slow 走一步，fast 走两步。", "code_line": 5})
        if slow == fast:
            answer = True
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{slow}]"}], "value": True, "state": {"nums": nums, "slow": slow, "fast": fast, "answer": True, "array_contract": contract}, "role": "answer", "reason": "快慢指针相遇，存在环。", "code_line": 7})
            break
    return {"schema_version": "semantic-trace-v1", "algorithm": "快慢指针判环", "input_data": input_data, "result": answer, "pseudocode": ["slow 走一步", "fast 走两步", "相遇则有环"], "events": events}
"""


FAST_SLOW_CYCLE_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    seen = set()
    pos = 0
    while 0 <= pos < len(nums):
        if pos in seen:
            return True
        seen.add(pos)
        pos = nums[pos]
    return False
"""


def cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            id="binary_search",
            title="二分查找",
            problem=(
                "LeetCode 704. 二分查找。给定一个升序整数数组 nums 和目标值 target，"
                "如果 target 存在，返回它的下标；否则返回 -1。"
            ),
            family="二分",
            input_contract="输入有序 nums 数组和 target。",
            variant_name="闭区间二分",
            strategy="维护闭区间，每次比较中点后丢弃一半。",
            time_complexity="O(log n)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=BINARY_SEARCH_CODE,
            tracker_code=BINARY_SEARCH_TRACKER,
            verifier_code=BINARY_SEARCH_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [-1, 0, 3, 5, 9, 12], "target": 9}, 4),
                BenchmarkInput({"nums": [-1, 0, 3, 5, 9, 12], "target": 2}, -1),
                BenchmarkInput({"nums": [5], "target": 5}, 0),
            ),
        ),
        BenchmarkCase(
            id="binary_answer_sqrt",
            title="二分答案整数平方根",
            problem="给定非负整数 n，返回不超过 sqrt(n) 的最大整数。",
            family="数组指针 / 窗口 / 前缀",
            input_contract="输入非负整数 n。",
            variant_name="答案域二分",
            strategy="在 [0,n] 上二分，mid*mid<=n 时记录答案并向右搜索。",
            time_complexity="O(log n)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=BINARY_ANSWER_SQRT_CODE,
            tracker_code=BINARY_ANSWER_SQRT_TRACKER,
            verifier_code=BINARY_ANSWER_SQRT_VERIFIER,
            samples=(
                BenchmarkInput({"n": 8}, 2),
                BenchmarkInput({"n": 16}, 4),
                BenchmarkInput({"n": 1}, 1),
            ),
        ),
        BenchmarkCase(
            id="two_pointer_pair_sum",
            title="有序数组两数之和",
            problem="给定升序数组 nums 和 target，返回一组下标使两数之和等于 target，不存在返回空数组。",
            family="数组指针 / 窗口 / 前缀",
            input_contract="输入升序 nums 数组和 target。",
            variant_name="左右双指针",
            strategy="根据当前两数之和与 target 的关系移动左指针或右指针。",
            time_complexity="O(n)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=TWO_POINTER_PAIR_SUM_CODE,
            tracker_code=TWO_POINTER_PAIR_SUM_TRACKER,
            verifier_code=TWO_POINTER_PAIR_SUM_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 2, 4, 6, 10], "target": 8}, [1, 3]),
                BenchmarkInput({"nums": [1, 3, 5, 8], "target": 20}, []),
                BenchmarkInput({"nums": [2, 7], "target": 9}, [0, 1]),
            ),
        ),
        BenchmarkCase(
            id="sliding_window_min_len",
            title="滑动窗口最短子数组",
            problem="给定正整数数组 nums 和 target，返回和至少为 target 的最短连续子数组长度，不存在返回 0。",
            family="数组指针 / 窗口 / 前缀",
            input_contract="输入正整数 nums 数组和 target。",
            variant_name="滑动窗口收缩",
            strategy="右端扩张累加，满足条件后移动左端收缩窗口。",
            time_complexity="O(n)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=SLIDING_WINDOW_MIN_LEN_CODE,
            tracker_code=SLIDING_WINDOW_MIN_LEN_TRACKER,
            verifier_code=SLIDING_WINDOW_MIN_LEN_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [2, 3, 1, 2, 4, 3], "target": 7}, 2),
                BenchmarkInput({"nums": [1, 1, 1], "target": 5}, 0),
                BenchmarkInput({"nums": [5], "target": 5}, 1),
            ),
        ),
        BenchmarkCase(
            id="prefix_sum_range",
            title="前缀和区间查询",
            problem="给定数组 nums 和闭区间 query=[l,r]，用前缀和返回区间和。",
            family="数组指针 / 窗口 / 前缀",
            input_contract="输入 nums 数组和 query 闭区间。",
            variant_name="前缀和",
            strategy="prefix[i+1]=prefix[i]+nums[i]，区间和由两个前缀项相减。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("array",),
            code=PREFIX_SUM_RANGE_CODE,
            tracker_code=PREFIX_SUM_RANGE_TRACKER,
            verifier_code=PREFIX_SUM_RANGE_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [2, 4, 6], "query": [1, 2]}, 10),
                BenchmarkInput({"nums": [-1, 3, 5], "query": [0, 1]}, 2),
                BenchmarkInput({"nums": [7], "query": [0, 0]}, 7),
            ),
        ),
        BenchmarkCase(
            id="difference_array_range_add",
            title="差分数组区间加",
            problem="给定初始数组 nums 和若干 updates=[l,r,delta]，执行所有区间加后返回最终数组。",
            family="数组指针 / 窗口 / 前缀",
            input_contract="输入 nums 数组和 updates 区间更新列表。",
            variant_name="差分数组",
            strategy="diff[l]+=delta，diff[r+1]-=delta，最后前缀还原。",
            time_complexity="O(n+q)",
            space_complexity="O(n)",
            expected_layouts=("array",),
            code=DIFFERENCE_ARRAY_RANGE_ADD_CODE,
            tracker_code=DIFFERENCE_ARRAY_RANGE_ADD_TRACKER,
            verifier_code=DIFFERENCE_ARRAY_RANGE_ADD_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 1, 1], "updates": [[0, 1, 2]]}, [3, 3, 1]),
                BenchmarkInput({"nums": [0, 0, 0, 0], "updates": [[1, 3, 5], [2, 2, -2]]}, [0, 5, 3, 5]),
                BenchmarkInput({"nums": [5], "updates": [[0, 0, -3]]}, [2]),
            ),
        ),
        BenchmarkCase(
            id="fast_slow_cycle",
            title="快慢指针判环",
            problem="给定数组 nums，把下标 i 的下一步定义为 nums[i]，从 0 出发判断是否进入环。",
            family="数组指针 / 窗口 / 前缀",
            input_contract="输入 nums 数组，每个值是下一步下标。",
            variant_name="Floyd 快慢指针",
            strategy="slow 每轮走一步，fast 每轮走两步，相遇则存在环。",
            time_complexity="O(n)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=FAST_SLOW_CYCLE_CODE,
            tracker_code=FAST_SLOW_CYCLE_TRACKER,
            verifier_code=FAST_SLOW_CYCLE_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 2, 0]}, True),
                BenchmarkInput({"nums": [1, 2, 3, 3]}, True),
                BenchmarkInput({"nums": []}, False),
            ),
        ),
    )
