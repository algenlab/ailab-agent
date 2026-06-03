"""Benchmark cases: hash, sorting, linked list, greedy."""

from __future__ import annotations

from tests.benchmark_cases import BenchmarkCase, BenchmarkInput

TWO_SUM_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    seen = {}
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:
            return [seen[need], i]
        seen[x] = i
    return []
"""


TWO_SUM_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    seen = {}
    contract = {"submode": "two_sum"}
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "seen"}], "state": {"nums": nums, "seen": {}, "target": target, "hash_contract": contract}, "reason": "初始化数组和哈希表，哈希表记录数值到下标。", "code_line": 1}]
    result = []
    for i, x in enumerate(nums):
        need = target - x
        hit = need in seen
        deps = [{"id": f"seen[{need}]"}] if hit else []
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{i}]"}], "deps": deps, "value": {"need": need, "exists": hit}, "state": {"nums": nums, "seen": dict(seen), "target": target, "i": i, "need": need, "exists": hit, "hash_contract": contract}, "role": "candidate", "reason": "检查当前数的互补值是否已经写入哈希表。", "code_line": 4})
        if hit:
            result = [seen[need], i]
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{seen[need]}]"}, {"id": f"nums[{i}]"}], "deps": [{"id": f"seen[{need}]"}, {"id": f"nums[{i}]"}], "value": result, "state": {"nums": nums, "seen": dict(seen), "target": target, "i": i, "need": need, "answer": result, "hash_contract": contract}, "role": "answer", "reason": "互补值已经在哈希表中，找到答案下标。", "code_line": 5})
            break
        seen[x] = i
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"seen[{x}]"}], "after": i, "state": {"nums": nums, "seen": dict(seen), "target": target, "i": i, "hash_contract": contract}, "role": "visited", "reason": "把当前数和下标写入哈希表，后续元素才能命中它。", "code_line": 7})
    return {"schema_version": "semantic-trace-v1", "algorithm": "两数之和", "input_data": input_data, "result": result, "pseudocode": ["遍历 nums", "若 target - nums[i] 已出现，则返回两个下标", "否则记录 nums[i]"], "events": events}
"""


TWO_SUM_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""


SUBARRAY_SUM_EQUALS_K_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    k = input_data["k"]
    counts = {0: 1}
    prefix = 0
    answer = 0
    for x in nums:
        prefix += x
        answer += counts.get(prefix - k, 0)
        counts[prefix] = counts.get(prefix, 0) + 1
    return answer
"""


SUBARRAY_SUM_EQUALS_K_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    k = input_data["k"]
    sess = TraceSession(
        algorithm="和为 K 的子数组",
        input_data=input_data,
        max_events=80,
        pseudocode=["维护前缀和 prefix", "查询 prefix-k 出现次数", "把当前 prefix 写入计数器"],
    )
    arr = sess.array("nums", nums)
    counts = sess.counter("prefix_counts", {0: 1})
    prefix = sess.scalar("prefix", 0)
    answer = sess.scalar("answer", 0)
    for i in range(len(arr)):
        arr.highlight(i, role="current")
        prefix.set(prefix.value + arr[i], reason="累加当前元素得到新的前缀和。")
        need = prefix.value - k
        hit = counts.get(need, 0, reason="查询 prefix-k 出现次数，这些位置都能形成和为 k 的子数组。")
        if hit:
            counts.highlight(need, role="dependency")
        answer.set(answer.value + hit, reason="把命中的前缀和次数累加到答案。")
        counts.inc(prefix.value, reason="记录当前前缀和，供后续位置查询。")
    sess.result(answer.value)
    return sess.to_trace()
"""


SUBARRAY_SUM_EQUALS_K_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    k = input_data["k"]
    answer = 0
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total == k:
                answer += 1
    return answer
"""


INSERTION_SORT_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    arr = nums[:]
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
"""


INSERTION_SORT_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    arr = nums[:]
    contract = {"submode": "insertion_sort"}
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}], "state": {"nums": arr[:], "i": 0, "sorting_contract": contract}, "reason": "复制原数组，准备插入排序。", "code_line": 1}]
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{i}]"}], "value": key, "state": {"nums": arr[:], "i": i, "key": key, "sorting_contract": contract}, "role": "candidate", "reason": "取出当前位置元素，向左寻找插入位置。", "code_line": 3})
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            events.append({"step": len(events), "op": "set", "targets": [{"id": f"nums[{j + 1}]"}], "deps": [{"id": f"nums[{j}]"}], "after": arr[j + 1], "state": {"nums": arr[:], "i": i, "j": j, "key": key, "sorting_contract": contract}, "role": "current", "reason": "左侧元素更大，向右移动一格，保持待插入区间之外的有序前缀。", "code_line": 5})
            j -= 1
        arr[j + 1] = key
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"nums[{j + 1}]"}], "after": key, "state": {"nums": arr[:], "i": i, "j": j + 1, "answer": arr[:] if i == len(arr) - 1 else None, "sorting_contract": contract}, "role": "answer", "reason": "把 key 放到有序前缀的正确位置，nums[0..i] 保持升序。", "code_line": 7})
    if len(arr) <= 1:
        events.append({"step": len(events), "op": "mark", "targets": [{"id": "nums"}], "value": arr[:], "state": {"nums": arr[:], "i": 0, "answer": arr[:], "sorting_contract": contract}, "role": "answer", "reason": "长度不超过 1 的数组天然有序。", "code_line": 8})
    return {"schema_version": "semantic-trace-v1", "algorithm": "插入排序", "input_data": input_data, "result": arr, "pseudocode": ["逐步维护有序前缀", "将当前元素插入正确位置"], "events": events}
"""


INSERTION_SORT_VERIFIER = """
def verify(input_data):
    return sorted(input_data["nums"])
"""


REVERSE_LINKED_LIST_CODE = """
def solve(input_data):
    values = input_data["values"]
    return list(reversed(values))
"""


REVERSE_LINKED_LIST_TRACKER = """
def trace(input_data):
    values = input_data["values"]
    contract = {"family": "linked_list", "submode": "reverse", "expected_events": ["move_pointer", "link_change"]}

    def linked_state(next_map):
        nodes = []
        edges = []
        for index, value in enumerate(values):
            node_id = str(index)
            next_id = next_map.get(node_id)
            nodes.append({"id": node_id, "label": value, "value": value, "meta": {"next": next_id}})
            if next_id is not None:
                edges.append([node_id, str(next_id)])
        return {"nodes": nodes, "edges": edges}

    next_map = {str(i): str(i + 1) for i in range(len(values) - 1)}
    if values:
        next_map[str(len(values) - 1)] = None
    prev = None
    current = "0" if values else None
    events = [{"step": 0, "op": "create", "targets": [{"id": "tree"}], "state": {"tree": linked_state(next_map), "linked_list": linked_state(next_map), "current": current, "prev": prev, "next": next_map.get(current) if current is not None else None, "family_contract": contract}, "reason": "初始化链表节点和 current/prev/next 指针。", "code_line": 1}]
    while current is not None:
        nxt = next_map.get(current)
        events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:current"}], "value": int(current), "deps": [{"id": f"node:{current}"}], "state": {"tree": linked_state(next_map), "linked_list": linked_state(next_map), "current": current, "prev": prev, "next": nxt, "family_contract": contract}, "role": "current", "reason": "移动 current 指针到当前待反转节点。", "code_line": 3})
        if nxt is not None:
            events.append({"step": len(events), "op": "unlink", "targets": [{"id": f"edge:{current}->{nxt}"}], "deps": [{"id": f"node:{current}"}, {"id": f"node:{nxt}"}], "state": {"tree": linked_state({**next_map, current: None}), "linked_list": linked_state({**next_map, current: None}), "current": current, "prev": prev, "next": nxt, "family_contract": contract}, "reason": "断开 current 原来的 next 指向，为反转重连做准备。", "code_line": 4})
        next_map[current] = prev
        if prev is not None:
            events.append({"step": len(events), "op": "link", "targets": [{"id": f"edge:{current}->{prev}"}], "deps": [{"id": f"node:{current}"}, {"id": f"node:{prev}"}], "state": {"tree": linked_state(next_map), "linked_list": linked_state(next_map), "current": current, "prev": prev, "next": nxt, "family_contract": contract}, "reason": "把 current.next 改为 prev，反转当前指针方向。", "code_line": 5})
        prev = current
        current = nxt
    answer = list(reversed(values))
    events.append({"step": len(events), "op": "mark", "targets": [{"id": f"node:{prev}"}] if prev is not None else [{"id": "tree"}], "value": answer, "deps": [{"id": f"node:{prev}"}] if prev is not None else [], "state": {"tree": linked_state(next_map), "linked_list": linked_state(next_map), "current": None, "prev": prev, "next": None, "answer": answer, "family_contract": contract}, "role": "answer", "reason": "current 为空，prev 指向反转后链表头。", "code_line": 8})
    return {"schema_version": "semantic-trace-v1", "algorithm": "反转链表", "input_data": input_data, "result": answer, "pseudocode": ["保存 next", "current.next = prev", "prev/current 前进"], "events": events}
"""


REVERSE_LINKED_LIST_VERIFIER = """
def verify(input_data):
    return input_data["values"][::-1]
"""


JUMP_GAME_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    reach = 0
    for i, jump in enumerate(nums):
        if i > reach:
            return False
        reach = max(reach, i + jump)
    return True
"""


JUMP_GAME_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    contract = {"submode": "jump_game"}
    reach = 0
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "reach"}], "state": {"nums": nums[:], "i": 0, "reach": 0, "greedy_contract": contract}, "reason": "初始化最远可达位置 reach=0。", "code_line": 1}]
    answer = True
    for i, jump in enumerate(nums):
        if i > reach:
            answer = False
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{i}]"}], "value": False, "state": {"nums": nums[:], "i": i, "reach": reach, "answer": False, "greedy_contract": contract}, "role": "answer", "reason": "当前下标超过最远可达位置，无法继续前进。", "code_line": 4})
            break
        previous = reach
        candidate = i + jump
        reach = max(reach, candidate)
        events.append({"step": len(events), "op": "set", "targets": [{"id": "reach"}], "value": reach, "before": previous, "after": reach, "deps": [{"id": f"nums[{i}]"}, {"id": "reach"}], "state": {"nums": nums[:], "i": i, "previous_reach": previous, "candidate_reach": candidate, "reach": reach, "greedy_contract": contract}, "role": "current", "reason": "贪心维护扫描到当前位置时能到达的最远下标。", "code_line": 6})
    if answer:
        events.append({"step": len(events), "op": "mark", "targets": [{"id": "reach"}], "value": True, "deps": [{"id": "reach"}], "state": {"nums": nums[:], "i": len(nums) - 1, "reach": reach, "answer": True, "greedy_contract": contract}, "role": "answer", "reason": "所有下标都未超过 reach，因此可以到达末尾。", "code_line": 8})
    return {"schema_version": "semantic-trace-v1", "algorithm": "跳跃游戏贪心", "input_data": input_data, "result": answer, "pseudocode": ["reach 记录当前最远可达位置", "若 i > reach 则失败", "否则 reach=max(reach,i+nums[i])"], "events": events}
"""


JUMP_GAME_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    reachable = {0} if nums else set()
    for i, jump in enumerate(nums):
        if i not in reachable:
            continue
        for nxt in range(i + 1, min(len(nums), i + jump + 1)):
            reachable.add(nxt)
    return not nums or (len(nums) - 1) in reachable
"""


MERGE_INTERVALS_CODE = """
def solve(input_data):
    intervals = [item[:] for item in input_data["intervals"]]
    intervals.sort(key=lambda item: (item[0], item[1]))
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged
"""


MERGE_INTERVALS_TRACKER = """
def trace(input_data):
    raw = [item[:] for item in input_data["intervals"]]
    sess = TraceSession(
        algorithm="合并区间",
        input_data=input_data,
        max_events=80,
        pseudocode=["按起点排序", "若当前区间与 merged 最后一个重叠则扩展", "否则追加新区间"],
    )
    intervals = sess.intervals("intervals", raw)
    intervals.sort()
    merged = sess.intervals("merged", [])
    for i, current in enumerate(intervals.to_list()):
        intervals.highlight(i, role="current")
        if len(merged) == 0 or current[0] > merged[len(merged) - 1][1]:
            merged.append(current, reason="当前区间与已合并结果不重叠，追加为新区间。")
        else:
            last_idx = len(merged) - 1
            last = merged[last_idx]
            merged.highlight(last_idx, role="dependency")
            merged.set(last_idx, [last[0], max(last[1], current[1])], reason="当前区间与最后区间重叠，扩展右端点。")
    result = merged.to_list()
    sess.result(result)
    return sess.to_trace()
"""


MERGE_INTERVALS_VERIFIER = """
def verify(input_data):
    intervals = [item[:] for item in input_data["intervals"]]
    intervals.sort(key=lambda item: (item[0], item[1]))
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged
"""


def cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            id="two_sum",
            title="两数之和",
            problem=(
                "LeetCode 1. 两数之和。给定整数数组 nums 和整数 target，"
                "请返回两个数的下标，使得它们相加等于 target。假设最多只有一个答案，可以返回空数组表示不存在。"
            ),
            family="哈希表 / map",
            input_contract="输入 nums 数组和 target。",
            variant_name="哈希表一次遍历",
            strategy="遍历数组，用哈希表记录已出现数值的下标，检查互补值。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("array", "map"),
            code=TWO_SUM_CODE,
            tracker_code=TWO_SUM_TRACKER,
            verifier_code=TWO_SUM_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [2, 7, 11, 15], "target": 9}, [0, 1]),
                BenchmarkInput({"nums": [3, 2, 4], "target": 6}, [1, 2]),
                BenchmarkInput({"nums": [1, 2, 3], "target": 7}, []),
            ),
        ),
        BenchmarkCase(
            id="subarray_sum_equals_k",
            title="和为 K 的子数组",
            problem=(
                "LeetCode 560. 和为 K 的子数组。给定整数数组 nums 和整数 k，"
                "返回数组中和为 k 的连续子数组个数。"
            ),
            family="哈希表 / map",
            input_contract="输入 nums 数组和 k。",
            variant_name="前缀和计数器",
            strategy="维护前缀和出现次数，当前位置贡献 counts[prefix-k]。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("array", "map"),
            code=SUBARRAY_SUM_EQUALS_K_CODE,
            tracker_code=SUBARRAY_SUM_EQUALS_K_TRACKER,
            verifier_code=SUBARRAY_SUM_EQUALS_K_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 1, 1], "k": 2}, 2),
                BenchmarkInput({"nums": [1, 2, 3], "k": 3}, 2),
                BenchmarkInput({"nums": [1, -1, 0], "k": 0}, 3),
                BenchmarkInput({"nums": [2, 4], "k": 7}, 0),
                BenchmarkInput({"nums": [3], "k": 3}, 1),
            ),
        ),
        BenchmarkCase(
            id="insertion_sort",
            title="插入排序",
            problem="给定整数数组 nums，使用插入排序思想将数组升序排列，返回排序后的数组。",
            family="排序",
            input_contract="输入 nums 数组。",
            variant_name="插入排序",
            strategy="逐步维护有序前缀，把当前元素插入正确位置。",
            time_complexity="O(n^2)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=INSERTION_SORT_CODE,
            tracker_code=INSERTION_SORT_TRACKER,
            verifier_code=INSERTION_SORT_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [5, 2, 3, 1]}, [1, 2, 3, 5]),
                BenchmarkInput({"nums": [1, 2, 3]}, [1, 2, 3]),
                BenchmarkInput({"nums": [3, -1, 0, 3]}, [-1, 0, 3, 3]),
            ),
        ),
        BenchmarkCase(
            id="reverse_linked_list",
            title="反转链表",
            problem="给定链表节点值 values，按迭代指针重连过程反转链表并返回反转后的值序列。",
            family="链表与缓存",
            input_contract="输入 values 数组，按顺序表示链表节点值。",
            variant_name="迭代三指针反转",
            strategy="维护 prev/current/next，逐个把 current.next 指向 prev。",
            time_complexity="O(n)",
            space_complexity="O(1)",
            expected_layouts=("tree",),
            code=REVERSE_LINKED_LIST_CODE,
            tracker_code=REVERSE_LINKED_LIST_TRACKER,
            verifier_code=REVERSE_LINKED_LIST_VERIFIER,
            samples=(
                BenchmarkInput({"values": [1, 2, 3]}, [3, 2, 1]),
                BenchmarkInput({"values": [5]}, [5]),
                BenchmarkInput({"values": []}, []),
            ),
        ),
        BenchmarkCase(
            id="jump_game",
            title="跳跃游戏",
            problem="LeetCode 55. 给定非负整数数组 nums，每个位置表示最大跳跃长度，判断能否到达最后一个下标。",
            family="贪心",
            input_contract="输入 nums 数组。",
            variant_name="最远可达贪心",
            strategy="从左到右维护最远可达位置 reach，若当前下标超过 reach 则失败。",
            time_complexity="O(n)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=JUMP_GAME_CODE,
            tracker_code=JUMP_GAME_TRACKER,
            verifier_code=JUMP_GAME_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [2, 3, 1, 1, 4]}, True),
                BenchmarkInput({"nums": [3, 2, 1, 0, 4]}, False),
                BenchmarkInput({"nums": [0]}, True),
            ),
        ),
        BenchmarkCase(
            id="merge_intervals",
            title="合并区间",
            problem=(
                "LeetCode 56. 合并区间。给定若干闭区间 intervals，"
                "合并所有重叠区间并返回不重叠区间列表。"
            ),
            family="贪心",
            input_contract="输入 intervals，每个区间为 [start, end]。",
            variant_name="排序后线性合并",
            strategy="按起点排序，维护已合并结果的最后一个区间并按需扩展。",
            time_complexity="O(n log n)",
            space_complexity="O(n)",
            expected_layouts=("matrix",),
            code=MERGE_INTERVALS_CODE,
            tracker_code=MERGE_INTERVALS_TRACKER,
            verifier_code=MERGE_INTERVALS_VERIFIER,
            samples=(
                BenchmarkInput({"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]}, [[1, 6], [8, 10], [15, 18]]),
                BenchmarkInput({"intervals": [[1, 4], [4, 5]]}, [[1, 5]]),
                BenchmarkInput({"intervals": [[1, 4], [0, 2], [3, 5]]}, [[0, 5]]),
                BenchmarkInput({"intervals": [[2, 3]]}, [[2, 3]]),
            ),
        ),
    )


__all__ = [name for name in globals() if not name.startswith("__")]
