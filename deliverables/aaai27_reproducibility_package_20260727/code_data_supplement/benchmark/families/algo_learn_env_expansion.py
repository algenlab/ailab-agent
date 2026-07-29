"""Public synthetic AlgoLearnEnv benchmark expansion cases."""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import indent
from typing import Any

from benchmark.cases import BenchmarkCase, BenchmarkInput


@dataclass(frozen=True)
class _Spec:
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
    samples: tuple[BenchmarkInput, ...]
    difficulty: str
    learning_objectives: tuple[str, ...]
    interaction_focus: str


def cases() -> tuple[BenchmarkCase, ...]:
    return tuple(_case_from_spec(spec) for spec in _SPECS)


def metadata() -> dict[str, dict[str, Any]]:
    return {spec.id: _metadata_from_spec(spec) for spec in _SPECS}


def _case_from_spec(spec: _Spec) -> BenchmarkCase:
    return BenchmarkCase(
        id=spec.id,
        title=spec.title,
        problem=spec.problem,
        family=spec.family,
        input_contract=spec.input_contract,
        variant_name=spec.variant_name,
        strategy=spec.strategy,
        time_complexity=spec.time_complexity,
        space_complexity=spec.space_complexity,
        expected_layouts=spec.expected_layouts,
        code=_function_code("solve", spec.solve_body),
        tracker_code=_tracker_code(spec),
        verifier_code=_function_code("verify", spec.verifier_body),
        samples=spec.samples,
    )


def _metadata_from_spec(spec: _Spec) -> dict[str, Any]:
    return {
        "family_id": spec.family_id,
        "subfamily_id": spec.subfamily_id,
        "gate_layer": "expansion",
        "support_level": spec.support_level,
        "process_profile": spec.process_profile,
        "oracle_type": spec.oracle_type,
        "demo_required": True,
        "difficulty": spec.difficulty,
        "dataset_source": "public_synthetic",
        "learning_objectives": list(spec.learning_objectives),
        "input_generator": "synthetic fixed samples with small edge cases; suitable for later fixed-seed random generation",
        "reference_solver": "verifier_code.verify",
        "trace_oracle": "semantic-trace schema + solve/trace/verifier result equivalence",
        "required_views": list(spec.expected_layouts),
        "interaction_tasks": [
            "predict_next_state",
            "identify_active_invariant",
            "modify_input_and_rerun",
        ],
        "assessment_rubric": (
            "Student answer is correct when it predicts the next algorithm state, "
            "names the maintained invariant, and matches the reference solver after input edits."
        ),
    }


def _function_code(function_name: str, body: str) -> str:
    return f"\ndef {function_name}(input_data):\n{indent(body.strip(), '    ')}\n"


def _tracker_code(spec: _Spec) -> str:
    pseudocode = [
        spec.strategy,
        "在每一步维护可解释的不变量。",
        "最终结果必须与 reference solver 一致。",
    ]
    return f"""
def _compute(input_data):
{indent(spec.solve_body.strip(), '    ')}


def trace(input_data):
    result = _compute(input_data)
    input_snapshot = input_data
    events = [
        {{
            "step": 0,
            "op": "create",
            "targets": [{{"id": "input"}}],
            "value": input_snapshot,
            "state": {{"input": input_snapshot}},
            "reason": "读取输入并确认本题目标。",
            "code_line": 1,
            "interaction": {{
                "type": "choice",
                "prompt": "开始前应先确认什么？",
                "options": ["输入约束和目标", "直接猜最终答案"],
                "answer": "输入约束和目标",
                "explanation": "算法学习环境需要先绑定输入、目标和可判分 oracle。",
                "wrong_explanation": "直接猜答案无法验证过程语义。",
            }},
        }},
        {{
            "step": 1,
            "op": "compare",
            "targets": [{{"id": "invariant"}}],
            "value": "{spec.interaction_focus}",
            "state": {{"input": input_snapshot, "candidate": result}},
            "role": "candidate",
            "reason": "根据算法族维护当前关键状态或不变量。",
            "code_line": 2,
            "interaction": {{
                "type": "choice",
                "prompt": "这一类算法的关键过程状态是什么？",
                "options": ["{spec.interaction_focus}", "忽略已经处理的状态"],
                "answer": "{spec.interaction_focus}",
                "explanation": "正确交互应指向当前算法不变量，而不是只看最终答案。",
                "wrong_explanation": "忽略过程状态会导致错误反馈无法被 oracle 校验。",
            }},
        }},
        {{
            "step": 2,
            "op": "mark",
            "targets": [{{"id": "answer"}}],
            "value": result,
            "state": {{"input": input_snapshot, "answer": result}},
            "role": "answer",
            "reason": "完成计算并标记 reference answer。",
            "code_line": 3,
            "interaction": {{
                "type": "choice",
                "prompt": "最终答案应如何判定？",
                "options": ["与 reference solver 一致", "只要页面上有数字即可"],
                "answer": "与 reference solver 一致",
                "explanation": "本 benchmark 的答案由 solve、trace 和 verifier 三方一致性判定。",
                "wrong_explanation": "只显示数字不能证明算法过程正确。",
            }},
        }},
        {{
            "step": 3,
            "op": "explain",
            "targets": [{{"id": "rerun"}}],
            "value": result,
            "state": {{"input": input_snapshot, "answer": result}},
            "reason": "如果学习者修改输入，需要重新运行 tracker 并复核 trace/result。",
            "code_line": 4,
            "interaction": {{
                "type": "choice",
                "prompt": "修改输入后应该怎么做？",
                "options": ["重新运行 tracker 并比较 trace/result", "只替换页面文本"],
                "answer": "重新运行 tracker 并比较 trace/result",
                "explanation": "交互环境必须保持输入、trace、反馈和最终答案同步。",
                "wrong_explanation": "只替换页面文本会破坏可验证性。",
            }},
        }},
    ]
    return {{
        "schema_version": "semantic-trace-v1",
        "algorithm": "{spec.title}",
        "input_data": input_data,
        "result": result,
        "pseudocode": {pseudocode!r},
        "events": events,
    }}
"""


_SPECS: tuple[_Spec, ...] = (
    _Spec(
        id="rotate_array_right_synthetic",
        title="循环右移数组",
        problem="给定数组 nums 和非负整数 k，将数组循环右移 k 步并返回新数组。",
        family="数组指针 / 窗口 / 前缀",
        family_id="array_pointer",
        subfamily_id="array_rotation",
        support_level="strong",
        process_profile="array_pointer",
        oracle_type="independent_reference",
        input_contract="输入 nums 数组和非负整数 k。",
        variant_name="模长切片旋转",
        strategy="先把 k 对数组长度取模，再拼接末尾 k 个元素和前缀。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = list(input_data["nums"])
k = input_data["k"]
if not nums:
    return []
k %= len(nums)
return nums[-k:] + nums[:-k] if k else nums
""",
        verifier_body="""
nums = list(input_data["nums"])
k = input_data["k"]
if not nums:
    return []
result = nums[:]
for _ in range(k % len(nums)):
    result = [result[-1]] + result[:-1]
return result
""",
        samples=(
            BenchmarkInput({"nums": [1, 2, 3, 4, 5], "k": 2}, [4, 5, 1, 2, 3]),
            BenchmarkInput({"nums": [1, 2], "k": 3}, [2, 1]),
            BenchmarkInput({"nums": [], "k": 5}, []),
        ),
        difficulty="easy",
        learning_objectives=("理解模长归一化", "观察数组元素位置变化", "区分原地和返回新数组语义"),
        interaction_focus="旋转后的边界切分位置",
    ),
    _Spec(
        id="move_zeroes_stable_synthetic",
        title="稳定移动零",
        problem="给定数组 nums，保持非零元素相对顺序，把所有 0 移到末尾并返回新数组。",
        family="数组指针 / 窗口 / 前缀",
        family_id="array_pointer",
        subfamily_id="stable_partition",
        support_level="strong",
        process_profile="array_pointer",
        oracle_type="independent_reference",
        input_contract="输入整数数组 nums。",
        variant_name="稳定双写指针",
        strategy="先按原顺序收集非零元素，再补齐同样数量的 0。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = input_data["nums"]
nonzero = [x for x in nums if x != 0]
return nonzero + [0] * (len(nums) - len(nonzero))
""",
        verifier_body="""
nums = input_data["nums"]
result = []
zero_count = 0
for value in nums:
    if value == 0:
        zero_count += 1
    else:
        result.append(value)
for _ in range(zero_count):
    result.append(0)
return result
""",
        samples=(
            BenchmarkInput({"nums": [0, 1, 0, 3, 12]}, [1, 3, 12, 0, 0]),
            BenchmarkInput({"nums": [0, 0, 1]}, [1, 0, 0]),
            BenchmarkInput({"nums": [1, 2]}, [1, 2]),
        ),
        difficulty="easy",
        learning_objectives=("理解稳定分区", "识别写指针位置", "验证非零相对顺序不变"),
        interaction_focus="非零写入位置和零计数",
    ),
    _Spec(
        id="fixed_window_max_sum_synthetic",
        title="定长窗口最大和",
        problem="给定数组 nums 和窗口长度 k，返回任意长度为 k 的连续子数组最大和。",
        family="数组指针 / 窗口 / 前缀",
        family_id="array_pointer",
        subfamily_id="fixed_sliding_window",
        support_level="strong",
        process_profile="array_pointer",
        oracle_type="bruteforce",
        input_contract="输入整数数组 nums 和 1 <= k <= len(nums)。",
        variant_name="定长滑动窗口",
        strategy="维护长度为 k 的窗口和，右移时加入新元素并移出旧元素。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = input_data["nums"]
k = input_data["k"]
window = sum(nums[:k])
best = window
for right in range(k, len(nums)):
    window += nums[right] - nums[right - k]
    if window > best:
        best = window
return best
""",
        verifier_body="""
nums = input_data["nums"]
k = input_data["k"]
best = None
for left in range(0, len(nums) - k + 1):
    total = 0
    for index in range(left, left + k):
        total += nums[index]
    if best is None or total > best:
        best = total
return best
""",
        samples=(
            BenchmarkInput({"nums": [1, 3, -2, 5, 4], "k": 2}, 9),
            BenchmarkInput({"nums": [-1, -2, -3], "k": 2}, -3),
            BenchmarkInput({"nums": [5], "k": 1}, 5),
        ),
        difficulty="easy",
        learning_objectives=("理解定长窗口更新", "比较窗口和候选答案", "避免重复求和"),
        interaction_focus="窗口左右边界与当前窗口和",
    ),
    _Spec(
        id="first_ge_binary_search_synthetic",
        title="二分查找第一个不小于目标",
        problem="给定升序数组 nums 和 target，返回第一个满足 nums[i] >= target 的下标，不存在则返回 -1。",
        family="二分",
        family_id="binary_search",
        subfamily_id="lower_bound",
        support_level="strong",
        process_profile="binary_search",
        oracle_type="independent_reference",
        input_contract="输入升序数组 nums 和目标值 target。",
        variant_name="lower_bound 二分",
        strategy="维护答案候选 ans，命中可行位置时继续搜索左半区间。",
        time_complexity="O(log n)",
        space_complexity="O(1)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = input_data["nums"]
target = input_data["target"]
left, right = 0, len(nums) - 1
ans = -1
while left <= right:
    mid = (left + right) // 2
    if nums[mid] >= target:
        ans = mid
        right = mid - 1
    else:
        left = mid + 1
return ans
""",
        verifier_body="""
nums = input_data["nums"]
target = input_data["target"]
for index, value in enumerate(nums):
    if value >= target:
        return index
return -1
""",
        samples=(
            BenchmarkInput({"nums": [1, 3, 3, 7], "target": 3}, 1),
            BenchmarkInput({"nums": [1, 2, 4], "target": 5}, -1),
            BenchmarkInput({"nums": [], "target": 1}, -1),
        ),
        difficulty="easy",
        learning_objectives=("理解 lower_bound 语义", "维护闭区间边界", "解释可行后继续向左搜索"),
        interaction_focus="left/right/mid 与 ans 候选",
    ),
    _Spec(
        id="mountain_peak_index_synthetic",
        title="山脉数组峰值下标",
        problem="给定先严格递增后严格递减的山脉数组 nums，返回峰值元素下标。",
        family="二分",
        family_id="binary_search",
        subfamily_id="slope_binary_search",
        support_level="strong",
        process_profile="binary_search",
        oracle_type="independent_reference",
        input_contract="输入山脉数组 nums，长度至少为 1。",
        variant_name="斜率二分",
        strategy="比较 nums[mid] 与 nums[mid+1] 判断峰值在左侧还是右侧。",
        time_complexity="O(log n)",
        space_complexity="O(1)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = input_data["nums"]
left, right = 0, len(nums) - 1
while left < right:
    mid = (left + right) // 2
    if nums[mid] < nums[mid + 1]:
        left = mid + 1
    else:
        right = mid
return left
""",
        verifier_body="""
nums = input_data["nums"]
best_index = 0
for index, value in enumerate(nums):
    if value > nums[best_index]:
        best_index = index
return best_index
""",
        samples=(
            BenchmarkInput({"nums": [1, 3, 5, 4, 2]}, 2),
            BenchmarkInput({"nums": [0, 2, 1]}, 1),
            BenchmarkInput({"nums": [1]}, 0),
        ),
        difficulty="medium",
        learning_objectives=("理解斜率方向", "掌握 left<right 二分模板", "判断峰值保留区间"),
        interaction_focus="mid 与 mid+1 的斜率比较",
    ),
    _Spec(
        id="first_unique_char_synthetic",
        title="第一个只出现一次的字符",
        problem="给定小写字符串 text，返回第一个只出现一次字符的下标，不存在返回 -1。",
        family="哈希表 / map",
        family_id="hash_map",
        subfamily_id="frequency_count",
        support_level="medium_plus",
        process_profile="hash",
        oracle_type="independent_reference",
        input_contract="输入小写字符串 text。",
        variant_name="频次表二次扫描",
        strategy="先统计每个字符频次，再按原顺序找到第一个频次为 1 的位置。",
        time_complexity="O(n)",
        space_complexity="O(字符集大小)",
        expected_layouts=("string", "map"),
        solve_body="""
text = input_data["text"]
freq = {}
for ch in text:
    freq[ch] = freq.get(ch, 0) + 1
for index, ch in enumerate(text):
    if freq[ch] == 1:
        return index
return -1
""",
        verifier_body="""
text = input_data["text"]
for index, ch in enumerate(text):
    seen_elsewhere = False
    for other_index, other in enumerate(text):
        if index != other_index and ch == other:
            seen_elsewhere = True
            break
    if not seen_elsewhere:
        return index
return -1
""",
        samples=(
            BenchmarkInput({"text": "leetcode"}, 0),
            BenchmarkInput({"text": "aabbcd"}, 4),
            BenchmarkInput({"text": "aabb"}, -1),
        ),
        difficulty="easy",
        learning_objectives=("构建频次表", "区分首次出现和唯一出现", "解释二次扫描必要性"),
        interaction_focus="字符频次和扫描下标",
    ),
    _Spec(
        id="group_anagrams_synthetic",
        title="按字母异位词分组",
        problem="给定小写单词数组 words，把字母异位词分到同一组，组内和组间都按字典序稳定输出。",
        family="哈希表 / map",
        family_id="hash_map",
        subfamily_id="anagram_grouping",
        support_level="medium_plus",
        process_profile="hash",
        oracle_type="independent_reference",
        input_contract="输入小写字符串数组 words。",
        variant_name="排序签名哈希",
        strategy="把每个单词排序后的字符串作为哈希 key，再收集并排序分组。",
        time_complexity="O(total_chars log word_len)",
        space_complexity="O(total_chars)",
        expected_layouts=("string", "map"),
        solve_body="""
words = input_data["words"]
groups = {}
for word in words:
    key = "".join(sorted(word))
    groups.setdefault(key, []).append(word)
result = [sorted(group) for group in groups.values()]
result.sort(key=lambda group: (group[0], len(group), group))
return result
""",
        verifier_body="""
words = input_data["words"]
groups = {}
for word in words:
    counts = [0] * 26
    for ch in word:
        counts[ord(ch) - ord("a")] += 1
    key = tuple(counts)
    if key not in groups:
        groups[key] = []
    groups[key].append(word)
result = []
for group in groups.values():
    result.append(sorted(group))
result.sort(key=lambda group: (group[0], len(group), group))
return result
""",
        samples=(
            BenchmarkInput({"words": ["eat", "tea", "tan", "ate", "nat", "bat"]}, [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]),
            BenchmarkInput({"words": [""]}, [[""]]),
            BenchmarkInput({"words": ["ab", "ba", "abc"]}, [["ab", "ba"], ["abc"]]),
        ),
        difficulty="medium",
        learning_objectives=("理解 canonical key", "维护哈希分组", "保证输出确定性"),
        interaction_focus="单词签名和哈希桶",
    ),
    _Spec(
        id="unique_intersection_synthetic",
        title="两个数组的唯一交集",
        problem="给定两个整数数组 nums1 和 nums2，返回升序排列的唯一交集。",
        family="哈希表 / map",
        family_id="hash_map",
        subfamily_id="set_intersection",
        support_level="medium_plus",
        process_profile="hash",
        oracle_type="independent_reference",
        input_contract="输入 nums1 和 nums2 两个整数数组。",
        variant_name="集合交集",
        strategy="把两个数组转成集合，求交集后排序输出。",
        time_complexity="O(n+m)",
        space_complexity="O(n+m)",
        expected_layouts=("array", "map"),
        solve_body="""
return sorted(set(input_data["nums1"]) & set(input_data["nums2"]))
""",
        verifier_body="""
nums1 = input_data["nums1"]
nums2 = input_data["nums2"]
result = []
for x in nums1:
    found = False
    for y in nums2:
        if x == y:
            found = True
            break
    if found and x not in result:
        result.append(x)
return sorted(result)
""",
        samples=(
            BenchmarkInput({"nums1": [1, 2, 2, 1], "nums2": [2, 2]}, [2]),
            BenchmarkInput({"nums1": [4, 9, 5], "nums2": [9, 4, 9, 8, 4]}, [4, 9]),
            BenchmarkInput({"nums1": [], "nums2": [1]}, []),
        ),
        difficulty="easy",
        learning_objectives=("理解集合去重", "识别交集语义", "验证输出排序"),
        interaction_focus="已见集合与交集候选",
    ),
    _Spec(
        id="valid_parentheses_synthetic",
        title="有效括号串",
        problem="给定只含括号字符的字符串 text，判断括号是否按类型正确闭合。",
        family="栈 / 队列 / 单调栈",
        family_id="monotonic_stack",
        subfamily_id="parentheses_stack",
        support_level="strong",
        process_profile="monotonic_stack",
        oracle_type="independent_reference",
        input_contract="输入括号字符串 text。",
        variant_name="括号匹配栈",
        strategy="遇到左括号入栈，遇到右括号时检查栈顶是否匹配。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("string", "stack"),
        solve_body="""
text = input_data["text"]
pairs = {")": "(", "]": "[", "}": "{"}
stack = []
for ch in text:
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
current = text
while previous != current:
    previous = current
    current = current.replace("()", "").replace("[]", "").replace("{}", "")
return current == ""
""",
        samples=(
            BenchmarkInput({"text": "()[]{}"}, True),
            BenchmarkInput({"text": "(]"}, False),
            BenchmarkInput({"text": "([{}])"}, True),
        ),
        difficulty="easy",
        learning_objectives=("理解栈顶匹配", "识别提前失败条件", "解释最终栈空不变量"),
        interaction_focus="当前字符和栈顶括号",
    ),
    _Spec(
        id="next_greater_right_synthetic",
        title="右侧下一个更大元素",
        problem="给定数组 nums，返回每个位置右侧第一个比它大的元素，不存在则为 -1。",
        family="栈 / 队列 / 单调栈",
        family_id="monotonic_stack",
        subfamily_id="next_greater",
        support_level="strong",
        process_profile="monotonic_stack",
        oracle_type="bruteforce",
        input_contract="输入整数数组 nums。",
        variant_name="递减单调栈",
        strategy="从右向左扫描，弹出不大于当前值的元素，栈顶即下一个更大值。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array", "stack"),
        solve_body="""
nums = input_data["nums"]
answer = [-1] * len(nums)
stack = []
for index in range(len(nums) - 1, -1, -1):
    while stack and stack[-1] <= nums[index]:
        stack.pop()
    if stack:
        answer[index] = stack[-1]
    stack.append(nums[index])
return answer
""",
        verifier_body="""
nums = input_data["nums"]
answer = []
for i, value in enumerate(nums):
    found = -1
    for j in range(i + 1, len(nums)):
        if nums[j] > value:
            found = nums[j]
            break
    answer.append(found)
return answer
""",
        samples=(
            BenchmarkInput({"nums": [2, 1, 2, 4, 3]}, [4, 2, 4, -1, -1]),
            BenchmarkInput({"nums": [5, 4, 3]}, [-1, -1, -1]),
            BenchmarkInput({"nums": [1, 3, 2]}, [3, -1, -1]),
        ),
        difficulty="medium",
        learning_objectives=("理解单调栈含义", "掌握弹栈条件", "解释栈顶代表最近更大值"),
        interaction_focus="递减栈和当前下标",
    ),
    _Spec(
        id="stock_span_synthetic",
        title="股票价格跨度",
        problem="给定每日价格 prices，返回每一天向左连续不高于当天价格的天数。",
        family="栈 / 队列 / 单调栈",
        family_id="monotonic_stack",
        subfamily_id="stock_span",
        support_level="strong",
        process_profile="monotonic_stack",
        oracle_type="bruteforce",
        input_contract="输入 prices 数组。",
        variant_name="单调递减索引栈",
        strategy="维护价格严格大于当前价格的索引栈，跨度由当前下标和栈顶下标决定。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("array", "stack"),
        solve_body="""
prices = input_data["prices"]
answer = []
stack = []
for index, price in enumerate(prices):
    while stack and prices[stack[-1]] <= price:
        stack.pop()
    previous_greater = stack[-1] if stack else -1
    answer.append(index - previous_greater)
    stack.append(index)
return answer
""",
        verifier_body="""
prices = input_data["prices"]
answer = []
for i, price in enumerate(prices):
    span = 1
    j = i - 1
    while j >= 0 and prices[j] <= price:
        span += 1
        j -= 1
    answer.append(span)
return answer
""",
        samples=(
            BenchmarkInput({"prices": [100, 80, 60, 70, 60, 75, 85]}, [1, 1, 1, 2, 1, 4, 6]),
            BenchmarkInput({"prices": [10, 20, 30]}, [1, 2, 3]),
            BenchmarkInput({"prices": [30, 20, 25]}, [1, 1, 2]),
        ),
        difficulty="medium",
        learning_objectives=("理解跨度定义", "维护递减索引栈", "解释弹栈聚合连续区间"),
        interaction_focus="栈顶更高价格下标和跨度",
    ),
    _Spec(
        id="merge_sort_synthetic",
        title="归并排序",
        problem="给定整数数组 nums，使用归并排序思想返回升序数组。",
        family="排序",
        family_id="sorting",
        subfamily_id="merge_sort",
        support_level="medium_plus",
        process_profile="sorting",
        oracle_type="property",
        input_contract="输入整数数组 nums。",
        variant_name="分治归并",
        strategy="递归拆分数组，分别排序左右半段后线性归并。",
        time_complexity="O(n log n)",
        space_complexity="O(n)",
        expected_layouts=("array", "recursion_tree"),
        solve_body="""
def merge_sort(values):
    if len(values) <= 1:
        return values[:]
    mid = len(values) // 2
    left = merge_sort(values[:mid])
    right = merge_sort(values[mid:])
    merged = []
    i = j = 0
    while i < len(left) or j < len(right):
        if j == len(right) or (i < len(left) and left[i] <= right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    return merged
return merge_sort(list(input_data["nums"]))
""",
        verifier_body="""
return sorted(input_data["nums"])
""",
        samples=(
            BenchmarkInput({"nums": [5, 2, 4, 1]}, [1, 2, 4, 5]),
            BenchmarkInput({"nums": []}, []),
            BenchmarkInput({"nums": [3, -1, 3]}, [-1, 3, 3]),
        ),
        difficulty="medium",
        learning_objectives=("理解分治递归", "追踪 merge 指针", "验证排序稳定输出"),
        interaction_focus="左右子数组和归并指针",
    ),
    _Spec(
        id="quickselect_kth_smallest_synthetic",
        title="快速选择第 K 小",
        problem="给定数组 nums 和 1-based 的 k，返回第 k 小元素。",
        family="排序",
        family_id="sorting",
        subfamily_id="quickselect",
        support_level="medium_plus",
        process_profile="sorting",
        oracle_type="property",
        input_contract="输入 nums 和 1 <= k <= len(nums)。",
        variant_name="确定性 pivot 快速选择",
        strategy="选末尾元素为 pivot，按小于等于 pivot 分区后只递归目标一侧。",
        time_complexity="O(n^2) worst-case, O(n) average",
        space_complexity="O(n)",
        expected_layouts=("array", "pointer"),
        solve_body="""
nums = list(input_data["nums"])
target = input_data["k"] - 1
def select(values, k_index):
    pivot = values[-1]
    lows = []
    highs = []
    pivots = []
    for value in values:
        if value < pivot:
            lows.append(value)
        elif value > pivot:
            highs.append(value)
        else:
            pivots.append(value)
    if k_index < len(lows):
        return select(lows, k_index)
    if k_index < len(lows) + len(pivots):
        return pivot
    return select(highs, k_index - len(lows) - len(pivots))
return select(nums, target)
""",
        verifier_body="""
return sorted(input_data["nums"])[input_data["k"] - 1]
""",
        samples=(
            BenchmarkInput({"nums": [7, 10, 4, 3, 20, 15], "k": 3}, 7),
            BenchmarkInput({"nums": [1, 1, 2], "k": 2}, 1),
            BenchmarkInput({"nums": [-2, 5, 0], "k": 1}, -2),
        ),
        difficulty="medium",
        learning_objectives=("理解分区结果", "只递归目标侧", "区分第 k 小和下标"),
        interaction_focus="pivot 分区和目标 rank",
    ),
    _Spec(
        id="counting_sort_synthetic",
        title="计数排序",
        problem="给定非负整数数组 nums，使用计数排序返回升序数组。",
        family="排序",
        family_id="sorting",
        subfamily_id="counting_sort",
        support_level="medium_plus",
        process_profile="sorting",
        oracle_type="property",
        input_contract="输入非负整数数组 nums。",
        variant_name="频次数组展开",
        strategy="统计每个值出现次数，再按值从小到大展开。",
        time_complexity="O(n+U)",
        space_complexity="O(U)",
        expected_layouts=("array", "map"),
        solve_body="""
nums = input_data["nums"]
if not nums:
    return []
counts = [0] * (max(nums) + 1)
for value in nums:
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
        samples=(
            BenchmarkInput({"nums": [4, 2, 2, 8, 3, 3, 1]}, [1, 2, 2, 3, 3, 4, 8]),
            BenchmarkInput({"nums": [0, 0, 0]}, [0, 0, 0]),
            BenchmarkInput({"nums": []}, []),
        ),
        difficulty="easy",
        learning_objectives=("理解值域计数", "观察频次数组", "验证按值展开"),
        interaction_focus="计数桶和当前展开值",
    ),
    _Spec(
        id="grid_bfs_shortest_path_synthetic",
        title="网格 BFS 最短路",
        problem="给定 0/1 网格、起点 start 和终点 goal，0 可走、1 障碍，返回四邻接最短步数，不可达返回 -1。",
        family="BFS/DFS 基础图",
        family_id="basic_graph",
        subfamily_id="grid_bfs_shortest_path",
        support_level="strong",
        process_profile="bfs",
        oracle_type="independent_reference",
        input_contract="输入 grid、start、goal。",
        variant_name="队列分层 BFS",
        strategy="从 start 入队，按距离层扩展四邻接未访问空格。",
        time_complexity="O(RC)",
        space_complexity="O(RC)",
        expected_layouts=("matrix", "queue"),
        solve_body="""
grid = input_data["grid"]
start = tuple(input_data["start"])
goal = tuple(input_data["goal"])
rows, cols = len(grid), len(grid[0])
queue = [(start[0], start[1], 0)]
seen = {start}
for r, c, dist in queue:
    if (r, c) == goal:
        return dist
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0 and (nr, nc) not in seen:
            seen.add((nr, nc))
            queue.append((nr, nc, dist + 1))
return -1
""",
        verifier_body="""
grid = input_data["grid"]
start = tuple(input_data["start"])
goal = tuple(input_data["goal"])
rows, cols = len(grid), len(grid[0])
dist = {start: 0}
changed = True
while changed:
    changed = False
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != 0 or (r, c) not in dist:
                continue
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
                    candidate = dist[(r, c)] + 1
                    if (nr, nc) not in dist or candidate < dist[(nr, nc)]:
                        dist[(nr, nc)] = candidate
                        changed = True
return dist.get(goal, -1)
""",
        samples=(
            BenchmarkInput({"grid": [[0, 0, 0], [1, 1, 0], [0, 0, 0]], "start": [0, 0], "goal": [2, 2]}, 4),
            BenchmarkInput({"grid": [[0, 1], [1, 0]], "start": [0, 0], "goal": [1, 1]}, -1),
            BenchmarkInput({"grid": [[0]], "start": [0, 0], "goal": [0, 0]}, 0),
        ),
        difficulty="medium",
        learning_objectives=("理解 BFS 分层", "维护 visited 集合", "解释第一次到达即最短"),
        interaction_focus="队列前端格子和距离层",
    ),
    _Spec(
        id="count_islands_synthetic",
        title="岛屿数量",
        problem="给定 0/1 网格，统计四邻接连通的 1 组成的岛屿数量。",
        family="BFS/DFS 基础图",
        family_id="basic_graph",
        subfamily_id="grid_connected_components",
        support_level="strong",
        process_profile="bfs",
        oracle_type="independent_reference",
        input_contract="输入 grid 矩阵。",
        variant_name="DFS 连通块标记",
        strategy="扫描每个陆地格，遇到未访问陆地就启动一次 DFS/BFS 并计数。",
        time_complexity="O(RC)",
        space_complexity="O(RC)",
        expected_layouts=("matrix", "queue"),
        solve_body="""
grid = input_data["grid"]
if not grid:
    return 0
rows, cols = len(grid), len(grid[0])
seen = set()
count = 0
for r in range(rows):
    for c in range(cols):
        if grid[r][c] != 1 or (r, c) in seen:
            continue
        count += 1
        stack = [(r, c)]
        seen.add((r, c))
        while stack:
            cr, cc = stack.pop()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1 and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    stack.append((nr, nc))
return count
""",
        verifier_body="""
grid = input_data["grid"]
if not grid:
    return 0
rows, cols = len(grid), len(grid[0])
parent = {}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra
for r in range(rows):
    for c in range(cols):
        if grid[r][c] == 1:
            parent[(r, c)] = (r, c)
for r in range(rows):
    for c in range(cols):
        if grid[r][c] != 1:
            continue
        for dr, dc in ((1, 0), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                union((r, c), (nr, nc))
roots = set()
for cell in parent:
    roots.add(find(cell))
return len(roots)
""",
        samples=(
            BenchmarkInput({"grid": [[1, 1, 0], [0, 1, 0], [1, 0, 1]]}, 3),
            BenchmarkInput({"grid": [[0, 0], [0, 0]]}, 0),
            BenchmarkInput({"grid": [[1]]}, 1),
        ),
        difficulty="medium",
        learning_objectives=("识别连通块入口", "追踪访问标记", "区分四邻接和对角连接"),
        interaction_focus="未访问陆地和当前连通块",
    ),
    _Spec(
        id="course_schedule_possible_synthetic",
        title="课程安排可行性",
        problem="给定课程数 n 和先修关系 prerequisites=[course, prereq]，判断是否可以完成所有课程。",
        family="BFS/DFS 基础图",
        family_id="basic_graph",
        subfamily_id="topological_cycle_detection",
        support_level="strong",
        process_profile="bfs",
        oracle_type="independent_reference",
        input_contract="输入 n 和 prerequisites。",
        variant_name="Kahn 拓扑排序",
        strategy="统计入度，从入度为 0 的课程开始出队并删除出边。",
        time_complexity="O(V+E)",
        space_complexity="O(V+E)",
        expected_layouts=("graph", "queue", "map"),
        solve_body="""
n = input_data["n"]
prerequisites = input_data["prerequisites"]
graph = {i: [] for i in range(n)}
indegree = [0] * n
for course, prereq in prerequisites:
    graph[prereq].append(course)
    indegree[course] += 1
queue = [i for i in range(n) if indegree[i] == 0]
visited = 0
for node in queue:
    visited += 1
    for nxt in graph[node]:
        indegree[nxt] -= 1
        if indegree[nxt] == 0:
            queue.append(nxt)
return visited == n
""",
        verifier_body="""
n = input_data["n"]
prerequisites = input_data["prerequisites"]
graph = {i: [] for i in range(n)}
for course, prereq in prerequisites:
    graph[prereq].append(course)
color = [0] * n
def has_cycle(node):
    if color[node] == 1:
        return True
    if color[node] == 2:
        return False
    color[node] = 1
    for nxt in graph[node]:
        if has_cycle(nxt):
            return True
    color[node] = 2
    return False
for node in range(n):
    if has_cycle(node):
        return False
return True
""",
        samples=(
            BenchmarkInput({"n": 2, "prerequisites": [[1, 0]]}, True),
            BenchmarkInput({"n": 2, "prerequisites": [[1, 0], [0, 1]]}, False),
            BenchmarkInput({"n": 4, "prerequisites": [[1, 0], [2, 1], [3, 2]]}, True),
        ),
        difficulty="medium",
        learning_objectives=("理解入度", "识别拓扑序和环", "解释出队计数为何判定可行"),
        interaction_focus="入度为 0 的队列和已完成课程数",
    ),
    _Spec(
        id="unweighted_distances_synthetic",
        title="无权图起点距离",
        problem="给定无权图 graph 和起点 start，返回所有可达节点到 start 的最短边数距离。",
        family="BFS/DFS 基础图",
        family_id="basic_graph",
        subfamily_id="bfs_distance_map",
        support_level="strong",
        process_profile="bfs",
        oracle_type="independent_reference",
        input_contract="输入 graph 邻接表和 start。",
        variant_name="BFS 距离表",
        strategy="BFS 第一次访问节点时写入距离，之后不再覆盖。",
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
nodes = sorted(set(graph) | {v for values in graph.values() for v in values})
for _ in range(len(nodes)):
    changed = False
    for node in nodes:
        if node not in dist:
            continue
        for nxt in graph.get(node, []):
            candidate = dist[node] + 1
            if nxt not in dist or candidate < dist[nxt]:
                dist[nxt] = candidate
                changed = True
    if not changed:
        break
return {key: dist[key] for key in sorted(dist)}
""",
        samples=(
            BenchmarkInput({"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, "start": "A"}, {"A": 0, "B": 1, "C": 1, "D": 2}),
            BenchmarkInput({"graph": {"S": ["A"], "A": [], "B": ["C"], "C": []}, "start": "S"}, {"A": 1, "S": 0}),
            BenchmarkInput({"graph": {"0": []}, "start": "0"}, {"0": 0}),
        ),
        difficulty="easy",
        learning_objectives=("理解无权最短路", "维护距离表", "解释首次访问最短性"),
        interaction_focus="队列节点和距离表",
    ),
    _Spec(
        id="climbing_stairs_ways_synthetic",
        title="爬楼梯方案数",
        problem="一次可以爬 1 或 2 级台阶，给定 n，返回到达第 n 级的不同方案数。",
        family="一维 DP",
        family_id="dp_1d",
        subfamily_id="linear_dp_climbing_stairs",
        support_level="strong",
        process_profile="dp",
        oracle_type="closed_form",
        input_contract="输入正整数 n。",
        variant_name="Fibonacci 线性 DP",
        strategy="dp[i]=dp[i-1]+dp[i-2]，逐级累积方案数。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array",),
        solve_body="""
n = input_data["n"]
if n <= 2:
    return n
prev2, prev1 = 1, 2
for _ in range(3, n + 1):
    prev2, prev1 = prev1, prev1 + prev2
return prev1
""",
        verifier_body="""
n = input_data["n"]
def count(remaining):
    if remaining == 0:
        return 1
    if remaining < 0:
        return 0
    return count(remaining - 1) + count(remaining - 2)
return count(n)
""",
        samples=(
            BenchmarkInput({"n": 1}, 1),
            BenchmarkInput({"n": 2}, 2),
            BenchmarkInput({"n": 5}, 8),
        ),
        difficulty="easy",
        learning_objectives=("理解状态转移", "观察滚动变量", "解释 base case"),
        interaction_focus="前两级方案数和当前 dp",
    ),
    _Spec(
        id="min_cost_climbing_synthetic",
        title="最小花费爬楼梯",
        problem="给定 cost[i] 表示踩到第 i 级的花费，可以爬 1 或 2 级，返回到达楼顶的最小花费。",
        family="一维 DP",
        family_id="dp_1d",
        subfamily_id="min_cost_climbing",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入 cost 数组。",
        variant_name="滚动最小代价 DP",
        strategy="dp[i] 表示到达第 i 级的最小花费，楼顶可由最后两级转移。",
        time_complexity="O(n)",
        space_complexity="O(1)",
        expected_layouts=("array",),
        solve_body="""
cost = input_data["cost"]
prev2, prev1 = 0, 0
for i in range(2, len(cost) + 1):
    current = min(prev1 + cost[i - 1], prev2 + cost[i - 2])
    prev2, prev1 = prev1, current
return prev1
""",
        verifier_body="""
cost = input_data["cost"]
memo = {}
def best(i):
    if i >= len(cost):
        return 0
    if i not in memo:
        memo[i] = cost[i] + min(best(i + 1), best(i + 2))
    return memo[i]
return min(best(0), best(1))
""",
        samples=(
            BenchmarkInput({"cost": [10, 15, 20]}, 15),
            BenchmarkInput({"cost": [1, 100, 1, 1, 1, 100, 1, 1, 100, 1]}, 6),
            BenchmarkInput({"cost": [5, 6]}, 5),
        ),
        difficulty="medium",
        learning_objectives=("定义楼顶状态", "比较两种转移来源", "掌握滚动数组"),
        interaction_focus="前两级最小代价",
    ),
    _Spec(
        id="coin_change_min_synthetic",
        title="零钱兑换最少硬币",
        problem="给定硬币面额 coins 和金额 amount，返回凑成金额所需最少硬币数，无法凑成返回 -1。",
        family="DP 核心扩展",
        family_id="dp_core",
        subfamily_id="coin_change_min",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入 coins 数组和 amount。",
        variant_name="完全背包最短路 DP",
        strategy="dp[x] 表示金额 x 的最少硬币数，每个 coin 可重复使用。",
        time_complexity="O(amount * len(coins))",
        space_complexity="O(amount)",
        expected_layouts=("array",),
        solve_body="""
coins = input_data["coins"]
amount = input_data["amount"]
inf = amount + 1
dp = [inf] * (amount + 1)
dp[0] = 0
for value in range(1, amount + 1):
    for coin in coins:
        if value >= coin and dp[value - coin] + 1 < dp[value]:
            dp[value] = dp[value - coin] + 1
return -1 if dp[amount] == inf else dp[amount]
""",
        verifier_body="""
coins = input_data["coins"]
amount = input_data["amount"]
memo = {0: 0}
def best(value):
    if value < 0:
        return 10 ** 9
    if value not in memo:
        answer = 10 ** 9
        for coin in coins:
            answer = min(answer, best(value - coin) + 1)
        memo[value] = answer
    return memo[value]
answer = best(amount)
return -1 if answer >= 10 ** 9 else answer
""",
        samples=(
            BenchmarkInput({"coins": [1, 2, 5], "amount": 11}, 3),
            BenchmarkInput({"coins": [2], "amount": 3}, -1),
            BenchmarkInput({"coins": [1], "amount": 0}, 0),
        ),
        difficulty="medium",
        learning_objectives=("理解完全背包转移", "识别不可达状态", "比较候选硬币"),
        interaction_focus="金额 dp[value] 和 coin 候选",
    ),
    _Spec(
        id="grid_min_path_sum_synthetic",
        title="网格最小路径和",
        problem="给定非负权网格 grid，只能向右或向下移动，返回从左上到右下的最小路径和。",
        family="二维 DP",
        family_id="dp_2d",
        subfamily_id="grid_min_path_sum",
        support_level="strong",
        process_profile="dp",
        oracle_type="independent_reference",
        input_contract="输入 grid 矩阵。",
        variant_name="二维路径 DP",
        strategy="dp[r][c] 等于当前格权重加上上方或左方最小代价。",
        time_complexity="O(RC)",
        space_complexity="O(RC)",
        expected_layouts=("matrix",),
        solve_body="""
grid = input_data["grid"]
rows, cols = len(grid), len(grid[0])
dp = [[0] * cols for _ in range(rows)]
for r in range(rows):
    for c in range(cols):
        if r == 0 and c == 0:
            dp[r][c] = grid[r][c]
        else:
            best = 10 ** 9
            if r > 0:
                best = min(best, dp[r - 1][c])
            if c > 0:
                best = min(best, dp[r][c - 1])
            dp[r][c] = best + grid[r][c]
return dp[-1][-1]
""",
        verifier_body="""
grid = input_data["grid"]
rows, cols = len(grid), len(grid[0])
memo = {}
def best(r, c):
    if r == rows - 1 and c == cols - 1:
        return grid[r][c]
    key = (r, c)
    if key not in memo:
        answer = 10 ** 9
        if r + 1 < rows:
            answer = min(answer, best(r + 1, c))
        if c + 1 < cols:
            answer = min(answer, best(r, c + 1))
        memo[key] = grid[r][c] + answer
    return memo[key]
return best(0, 0)
""",
        samples=(
            BenchmarkInput({"grid": [[1, 3, 1], [1, 5, 1], [4, 2, 1]]}, 7),
            BenchmarkInput({"grid": [[1, 2, 3]]}, 6),
            BenchmarkInput({"grid": [[5], [1], [2]]}, 8),
        ),
        difficulty="medium",
        learning_objectives=("理解二维状态", "比较上方和左方来源", "解释边界行列初始化"),
        interaction_focus="当前单元格和上/左转移",
    ),
    _Spec(
        id="lis_length_synthetic",
        title="最长递增子序列长度",
        problem="给定整数数组 nums，返回最长严格递增子序列的长度。",
        family="DP 核心扩展",
        family_id="dp_core",
        subfamily_id="lis_length",
        support_level="strong",
        process_profile="dp",
        oracle_type="bruteforce",
        input_contract="输入整数数组 nums。",
        variant_name="O(n^2) LIS DP",
        strategy="dp[i] 表示以 nums[i] 结尾的最长递增子序列长度。",
        time_complexity="O(n^2)",
        space_complexity="O(n)",
        expected_layouts=("array",),
        solve_body="""
nums = input_data["nums"]
if not nums:
    return 0
dp = [1] * len(nums)
for i in range(len(nums)):
    for j in range(i):
        if nums[j] < nums[i] and dp[j] + 1 > dp[i]:
            dp[i] = dp[j] + 1
return max(dp)
""",
        verifier_body="""
nums = input_data["nums"]
best = 0
for mask in range(1 << len(nums)):
    seq = []
    for i, value in enumerate(nums):
        if mask & (1 << i):
            seq.append(value)
    ok = True
    for i in range(1, len(seq)):
        if seq[i - 1] >= seq[i]:
            ok = False
            break
    if ok and len(seq) > best:
        best = len(seq)
return best
""",
        samples=(
            BenchmarkInput({"nums": [10, 9, 2, 5, 3, 7, 101, 18]}, 4),
            BenchmarkInput({"nums": [0, 1, 0, 3, 2, 3]}, 4),
            BenchmarkInput({"nums": []}, 0),
        ),
        difficulty="medium",
        learning_objectives=("理解以 i 结尾的状态", "比较所有前驱", "区分子序列和子数组"),
        interaction_focus="前驱 j 与 dp[i] 更新",
    ),
    _Spec(
        id="tree_level_order_synthetic",
        title="二叉树层序遍历",
        problem="给定二叉树 root 和 children 映射，返回从上到下每层节点 id 列表。",
        family="树 / BST / LCA",
        family_id="tree_bst_lca",
        subfamily_id="level_order_traversal",
        support_level="strong",
        process_profile="tree",
        oracle_type="independent_reference",
        input_contract="输入 tree={root, children}，children[node]=[left,right]。",
        variant_name="队列层序遍历",
        strategy="按层处理队列长度，把下一层非空子节点加入队列。",
        time_complexity="O(n)",
        space_complexity="O(n)",
        expected_layouts=("tree", "queue"),
        solve_body="""
tree = input_data["tree"]
root = tree.get("root")
if root is None:
    return []
children = tree.get("children", {})
queue = [root]
levels = []
while queue:
    current_level = []
    next_queue = []
    for node in queue:
        current_level.append(node)
        left, right = children.get(node, [None, None])
        if left is not None:
            next_queue.append(left)
        if right is not None:
            next_queue.append(right)
    levels.append(current_level)
    queue = next_queue
return levels
""",
        verifier_body="""
tree = input_data["tree"]
root = tree.get("root")
if root is None:
    return []
children = tree.get("children", {})
levels = []
def visit(node, depth):
    if node is None:
        return
    while len(levels) <= depth:
        levels.append([])
    levels[depth].append(node)
    left, right = children.get(node, [None, None])
    visit(left, depth + 1)
    visit(right, depth + 1)
visit(root, 0)
return levels
""",
        samples=(
            BenchmarkInput({"tree": {"root": "A", "children": {"A": ["B", "C"], "B": ["D", None], "C": [None, "E"], "D": [None, None], "E": [None, None]}}}, [["A"], ["B", "C"], ["D", "E"]]),
            BenchmarkInput({"tree": {"root": None, "children": {}}}, []),
            BenchmarkInput({"tree": {"root": "R", "children": {"R": [None, None]}}}, [["R"]]),
        ),
        difficulty="easy",
        learning_objectives=("理解队列层序", "区分当前层和下一层", "验证空树边界"),
        interaction_focus="队列中的当前层节点",
    ),
    _Spec(
        id="tree_validate_bst_synthetic",
        title="验证二叉搜索树",
        problem="给定带数值的二叉树，判断它是否满足严格二叉搜索树性质。",
        family="树 / BST / LCA",
        family_id="tree_bst_lca",
        subfamily_id="bst_validation",
        support_level="strong",
        process_profile="tree",
        oracle_type="independent_reference",
        input_contract="输入 tree={root, values, children}。",
        variant_name="上下界递归",
        strategy="递归携带每个节点允许的开区间上下界。",
        time_complexity="O(n)",
        space_complexity="O(h)",
        expected_layouts=("tree", "recursion_tree"),
        solve_body="""
tree = input_data["tree"]
root = tree.get("root")
values = tree.get("values", {})
children = tree.get("children", {})
def valid(node, low, high):
    if node is None:
        return True
    value = values[node]
    if not (low < value < high):
        return False
    left, right = children.get(node, [None, None])
    return valid(left, low, value) and valid(right, value, high)
return valid(root, -10 ** 18, 10 ** 18)
""",
        verifier_body="""
tree = input_data["tree"]
root = tree.get("root")
values = tree.get("values", {})
children = tree.get("children", {})
order = []
def inorder(node):
    if node is None:
        return
    left, right = children.get(node, [None, None])
    inorder(left)
    order.append(values[node])
    inorder(right)
inorder(root)
for i in range(1, len(order)):
    if order[i - 1] >= order[i]:
        return False
return True
""",
        samples=(
            BenchmarkInput({"tree": {"root": "5", "values": {"5": 5, "3": 3, "7": 7}, "children": {"5": ["3", "7"], "3": [None, None], "7": [None, None]}}}, True),
            BenchmarkInput({"tree": {"root": "5", "values": {"5": 5, "6": 6, "7": 7}, "children": {"5": ["6", "7"], "6": [None, None], "7": [None, None]}}}, False),
            BenchmarkInput({"tree": {"root": "1", "values": {"1": 1}, "children": {"1": [None, None]}}}, True),
        ),
        difficulty="medium",
        learning_objectives=("理解 BST 上下界", "追踪递归约束", "发现局部判断不足"),
        interaction_focus="节点值和允许的上下界",
    ),
    _Spec(
        id="bst_insert_inorder_synthetic",
        title="BST 插入后的中序序列",
        problem="按顺序把 values 插入一棵二叉搜索树，重复值放右子树，返回最终中序遍历序列。",
        family="树 / BST / LCA",
        family_id="tree_bst_lca",
        subfamily_id="bst_insert",
        support_level="strong",
        process_profile="tree",
        oracle_type="property",
        input_contract="输入 values 插入序列。",
        variant_name="BST 插入模拟",
        strategy="从根开始比较，小于走左侧，否则走右侧，最后中序输出。",
        time_complexity="O(nh)",
        space_complexity="O(n)",
        expected_layouts=("tree",),
        solve_body="""
values = input_data["values"]
tree = []
def insert(value):
    if not tree:
        tree.append([value, None, None])
        return
    index = 0
    while True:
        direction = 1 if value < tree[index][0] else 2
        child = tree[index][direction]
        if child is None:
            tree[index][direction] = len(tree)
            tree.append([value, None, None])
            return
        index = child
def inorder(index, output):
    if index is None:
        return
    inorder(tree[index][1], output)
    output.append(tree[index][0])
    inorder(tree[index][2], output)
for value in values:
    insert(value)
answer = []
inorder(0 if tree else None, answer)
return answer
""",
        verifier_body="""
return sorted(input_data["values"])
""",
        samples=(
            BenchmarkInput({"values": [5, 3, 7, 4]}, [3, 4, 5, 7]),
            BenchmarkInput({"values": [2, 2, 1]}, [1, 2, 2]),
            BenchmarkInput({"values": []}, []),
        ),
        difficulty="medium",
        learning_objectives=("理解 BST 插入方向", "观察重复值策略", "验证中序有序性"),
        interaction_focus="当前节点比较和插入方向",
    ),
    _Spec(
        id="huffman_merge_cost_synthetic",
        title="Huffman 合并总代价",
        problem="给定正整数权重 weights，每次合并两个最小权重并累加代价，返回总代价。",
        family="堆 / TopK / Huffman",
        family_id="heap_topk_huffman",
        subfamily_id="huffman_merge_cost",
        support_level="medium_plus",
        process_profile="heap",
        oracle_type="independent_reference",
        input_contract="输入 weights 数组。",
        variant_name="小顶堆贪心合并",
        strategy="每轮取出两个最小权重合并，再把新权重放回堆。",
        time_complexity="O(n log n)",
        space_complexity="O(n)",
        expected_layouts=("heap", "tree"),
        solve_body="""
heap = list(input_data["weights"])
heapq.heapify(heap)
total = 0
while len(heap) > 1:
    a = heapq.heappop(heap)
    b = heapq.heappop(heap)
    merged = a + b
    total += merged
    heapq.heappush(heap, merged)
return total
""",
        verifier_body="""
items = list(input_data["weights"])
total = 0
while len(items) > 1:
    items.sort()
    merged = items.pop(0) + items.pop(0)
    total += merged
    items.append(merged)
return total
""",
        samples=(
            BenchmarkInput({"weights": [5, 9, 12, 13, 16, 45]}, 224),
            BenchmarkInput({"weights": [1, 2, 3]}, 9),
            BenchmarkInput({"weights": [7]}, 0),
        ),
        difficulty="medium",
        learning_objectives=("理解贪心合并", "观察小顶堆弹出", "计算累计代价"),
        interaction_focus="堆顶两个最小权重",
    ),
    _Spec(
        id="merge_k_sorted_lists_synthetic",
        title="合并 K 个有序列表",
        problem="给定若干升序整数列表 lists，返回合并后的升序列表。",
        family="堆 / TopK / Huffman",
        family_id="heap_topk_huffman",
        subfamily_id="k_way_merge",
        support_level="medium_plus",
        process_profile="heap",
        oracle_type="property",
        input_contract="输入 lists，为升序整数列表数组。",
        variant_name="小顶堆多路归并",
        strategy="堆中保存每个列表当前元素，弹出最小值后推进对应列表。",
        time_complexity="O(N log k)",
        space_complexity="O(k)",
        expected_layouts=("heap", "array"),
        solve_body="""
lists = input_data["lists"]
heap = []
for list_index, values in enumerate(lists):
    if values:
        heapq.heappush(heap, (values[0], list_index, 0))
result = []
while heap:
    value, list_index, item_index = heapq.heappop(heap)
    result.append(value)
    next_index = item_index + 1
    if next_index < len(lists[list_index]):
        heapq.heappush(heap, (lists[list_index][next_index], list_index, next_index))
return result
""",
        verifier_body="""
result = []
for values in input_data["lists"]:
    for value in values:
        result.append(value)
return sorted(result)
""",
        samples=(
            BenchmarkInput({"lists": [[1, 4, 5], [1, 3, 4], [2, 6]]}, [1, 1, 2, 3, 4, 4, 5, 6]),
            BenchmarkInput({"lists": [[], [1]]}, [1]),
            BenchmarkInput({"lists": []}, []),
        ),
        difficulty="medium",
        learning_objectives=("理解多路归并", "维护堆元素来源", "推进弹出元素所在列表"),
        interaction_focus="堆顶值和来源列表指针",
    ),
    _Spec(
        id="redundant_connection_synthetic",
        title="冗余连接检测",
        problem="给定无向图逐条加入的 edges，返回第一条会让图形成环的边；若没有返回空数组。",
        family="并查集",
        family_id="union_find",
        subfamily_id="cycle_detection",
        support_level="strong",
        process_profile="union_find",
        oracle_type="independent_reference",
        input_contract="输入 n 和 edges。",
        variant_name="Union-Find 环检测",
        strategy="加入边前检查两个端点是否已连通，已连通则该边冗余。",
        time_complexity="O(E alpha(V))",
        space_complexity="O(V)",
        expected_layouts=("union_find", "graph"),
        solve_body="""
n = input_data["n"]
edges = input_data["edges"]
parent = list(range(n + 1))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
for a, b in edges:
    ra, rb = find(a), find(b)
    if ra == rb:
        return [a, b]
    parent[rb] = ra
return []
""",
        verifier_body="""
n = input_data["n"]
edges = input_data["edges"]
graph = {i: [] for i in range(1, n + 1)}
def connected(start, goal):
    stack = [start]
    seen = {start}
    while stack:
        node = stack.pop()
        if node == goal:
            return True
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return False
for a, b in edges:
    if connected(a, b):
        return [a, b]
    graph[a].append(b)
    graph[b].append(a)
return []
""",
        samples=(
            BenchmarkInput({"n": 3, "edges": [[1, 2], [1, 3], [2, 3]]}, [2, 3]),
            BenchmarkInput({"n": 4, "edges": [[1, 2], [2, 3], [3, 4]]}, []),
            BenchmarkInput({"n": 5, "edges": [[1, 2], [3, 4], [2, 3], [1, 4]]}, [1, 4]),
        ),
        difficulty="medium",
        learning_objectives=("理解连通分量代表元", "识别成环边", "观察路径压缩效果"),
        interaction_focus="端点代表元和 union 操作",
    ),
    _Spec(
        id="interval_scheduling_max_count_synthetic",
        title="最多不重叠区间",
        problem="给定若干闭开区间 intervals=[start,end]，返回最多能选择多少个互不重叠区间。",
        family="贪心",
        family_id="greedy",
        subfamily_id="interval_scheduling",
        support_level="medium_plus",
        process_profile="greedy",
        oracle_type="bruteforce",
        input_contract="输入 intervals 数组，允许 start == end。",
        variant_name="按结束时间贪心",
        strategy="按结束时间从小到大选择，当前区间 start >= last_end 时接纳。",
        time_complexity="O(n log n)",
        space_complexity="O(n)",
        expected_layouts=("array", "interval"),
        solve_body="""
intervals = sorted(input_data["intervals"], key=lambda item: (item[1], item[0]))
count = 0
last_end = -10 ** 18
for start, end in intervals:
    if start >= last_end:
        count += 1
        last_end = end
return count
""",
        verifier_body="""
intervals = input_data["intervals"]
best = 0
for mask in range(1 << len(intervals)):
    chosen = []
    for i, interval in enumerate(intervals):
        if mask & (1 << i):
            chosen.append(interval)
    chosen.sort()
    ok = True
    for i in range(1, len(chosen)):
        if chosen[i][0] < chosen[i - 1][1]:
            ok = False
            break
    if ok and len(chosen) > best:
        best = len(chosen)
return best
""",
        samples=(
            BenchmarkInput({"intervals": [[1, 3], [2, 4], [3, 5], [0, 7]]}, 2),
            BenchmarkInput({"intervals": [[1, 2], [2, 3], [3, 4]]}, 3),
            BenchmarkInput({"intervals": []}, 0),
        ),
        difficulty="medium",
        learning_objectives=("理解结束时间贪心", "判断区间兼容", "区分局部选择和全局最优"),
        interaction_focus="当前最早结束区间和 last_end",
    ),
)


__all__ = ["cases", "metadata"]
