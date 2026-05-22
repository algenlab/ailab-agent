"""Deterministic real-problem benchmark cases.

These cases exercise the production pipeline without calling the LLM.  Each
case provides executable solve/trace/verifier code and several inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BenchmarkInput:
    input_data: dict[str, Any]
    expected: Any


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    title: str
    problem: str
    family: str
    input_contract: str
    variant_name: str
    strategy: str
    time_complexity: str
    space_complexity: str
    expected_layouts: tuple[str, ...]
    code: str
    tracker_code: str
    verifier_code: str
    samples: tuple[BenchmarkInput, ...]


HOUSE_ROBBER_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    prev2 = 0
    prev1 = 0
    for x in nums:
        prev2, prev1 = prev1, max(prev1, prev2 + x)
    return prev1
"""


HOUSE_ROBBER_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    if not nums:
        return {
            "schema_version": "semantic-trace-v1",
            "algorithm": "打家劫舍",
            "input_data": input_data,
            "result": 0,
            "pseudocode": ["空数组返回 0"],
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "nums"}], "state": {"nums": [], "dp": []}, "reason": "没有房屋可以选择。", "code_line": 1}
            ],
        }
    dp = [0] * len(nums)
    dp[0] = nums[0]
    events = [
        {"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "dp"}], "state": {"nums": nums, "dp": dp[:]}, "reason": "初始化金额数组和 DP 数组。", "code_line": 1}
    ]
    if len(nums) > 1:
        dp[1] = max(nums[0], nums[1])
        events.append({"step": len(events), "op": "set", "targets": [{"id": "dp[1]"}], "deps": [{"id": "nums[0]"}, {"id": "nums[1]"}], "state": {"nums": nums, "dp": dp[:]}, "role": "current", "reason": "前两间房只能选择收益更高的一间。", "code_line": 2})
    for i in range(2, len(nums)):
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"dp[{i}]"}], "deps": [{"id": f"dp[{i-1}]"}, {"id": f"dp[{i-2}]"}, {"id": f"nums[{i}]"}], "state": {"nums": nums, "dp": dp[:]}, "role": "candidate", "reason": "比较偷当前房屋和不偷当前房屋。", "code_line": 3})
        dp[i] = max(dp[i - 1], dp[i - 2] + nums[i])
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"dp[{i}]"}], "deps": [{"id": f"dp[{i-1}]"}, {"id": f"dp[{i-2}]"}, {"id": f"nums[{i}]"}], "state": {"nums": nums, "dp": dp[:]}, "role": "answer", "reason": "写入当前位置的最优收益。", "code_line": 3})
    return {
        "schema_version": "semantic-trace-v1",
        "algorithm": "打家劫舍",
        "input_data": input_data,
        "result": dp[-1],
        "pseudocode": ["dp[i] 表示前 i 间房的最大收益", "dp[i] = max(dp[i-1], dp[i-2] + nums[i])"],
        "events": events,
    }
"""


HOUSE_ROBBER_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    def dfs(i):
        if i >= len(nums):
            return 0
        return max(dfs(i + 1), nums[i] + dfs(i + 2))
    return dfs(0)
"""


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


UNIQUE_PATHS_CODE = """
def solve(input_data):
    m, n = input_data["m"], input_data["n"]
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
    return dp[m - 1][n - 1]
"""


UNIQUE_PATHS_TRACKER = """
def trace(input_data):
    m, n = input_data["m"], input_data["n"]
    dp = [[1] * n for _ in range(m)]
    events = [{"step": 0, "op": "create", "targets": [{"id": "dp"}], "state": {"dp": [row[:] for row in dp]}, "reason": "第一行和第一列只有一种路径。", "code_line": 1}]
    for i in range(1, m):
        for j in range(1, n):
            events.append({"step": len(events), "op": "compare", "targets": [{"id": f"dp[{i}][{j}]"}], "deps": [{"id": f"dp[{i-1}][{j}]"}, {"id": f"dp[{i}][{j-1}]"}], "state": {"dp": [row[:] for row in dp]}, "role": "candidate", "reason": "当前位置只能从上方或左侧到达。", "code_line": 3})
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
            events.append({"step": len(events), "op": "set", "targets": [{"id": f"dp[{i}][{j}]"}], "deps": [{"id": f"dp[{i-1}][{j}]"}, {"id": f"dp[{i}][{j-1}]"}], "state": {"dp": [row[:] for row in dp]}, "role": "answer", "reason": "写入上方和左侧路径数之和。", "code_line": 3})
    return {"schema_version": "semantic-trace-v1", "algorithm": "不同路径", "input_data": input_data, "result": dp[m - 1][n - 1], "pseudocode": ["dp[i][j] = dp[i-1][j] + dp[i][j-1]"], "events": events}
"""


UNIQUE_PATHS_VERIFIER = """
def verify(input_data):
    import math
    m, n = input_data["m"], input_data["n"]
    return math.comb(m + n - 2, m - 1)
"""


GRAPH_BFS_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
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
"""


GRAPH_BFS_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    queue = [start]
    head = 0
    events = [{"step": 0, "op": "create", "targets": [{"id": "queue"}, {"id": f"node:{start}"}], "state": {"graph": graph, "queue": queue[:], "dist": dict(dist)}, "role": "current", "reason": "起点入队，距离为 0。", "code_line": 1}]
    while head < len(queue):
        cur = queue[head]
        head += 1
        events.append({"step": len(events), "op": "pop", "targets": [{"id": "queue"}, {"id": f"node:{cur}"}], "state": {"graph": graph, "queue": queue[head:], "dist": dict(dist)}, "role": "current", "reason": "取出队首节点并检查邻居。", "code_line": 4})
        for nei in graph.get(cur, []):
            if nei not in dist:
                dist[nei] = dist[cur] + 1
                queue.append(nei)
                events.append({"step": len(events), "op": "mark", "targets": [{"id": f"node:{nei}"}], "deps": [{"id": f"node:{cur}"}], "state": {"graph": graph, "queue": queue[head:], "dist": dict(dist)}, "role": "visited", "reason": "首次发现邻居，记录距离并入队。", "code_line": 7})
    return {"schema_version": "semantic-trace-v1", "algorithm": "BFS 最短层数", "input_data": input_data, "result": dist, "pseudocode": ["队列按层扩展", "首次访问时记录距离"], "events": events}
"""


GRAPH_BFS_VERIFIER = """
def verify(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    frontier = [start]
    while frontier:
        nxt = []
        for cur in frontier:
            for nei in graph.get(cur, []):
                if nei not in dist:
                    dist[nei] = dist[cur] + 1
                    nxt.append(nei)
        frontier = nxt
    return dist
"""


KMP_CODE = """
def solve(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        return 0
    pi = [0] * len(pattern)
    j = 0
    for i in range(1, len(pattern)):
        while j and pattern[i] != pattern[j]:
            j = pi[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
    j = 0
    for i, ch in enumerate(text):
        while j and ch != pattern[j]:
            j = pi[j - 1]
        if ch == pattern[j]:
            j += 1
        if j == len(pattern):
            return i - len(pattern) + 1
    return -1
"""


KMP_TRACKER = """
def trace(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        result = 0
        events = [{"step": 0, "op": "create", "targets": [{"id": "text"}, {"id": "pattern"}], "state": {"text": text, "pattern": pattern}, "reason": "空模式串默认在位置 0 匹配。", "code_line": 1}]
        return {"schema_version": "semantic-trace-v1", "algorithm": "KMP 字符串匹配", "input_data": input_data, "result": result, "events": events}
    pi = [0] * len(pattern)
    events = [{"step": 0, "op": "create", "targets": [{"id": "text"}, {"id": "pattern"}, {"id": "pi"}], "state": {"text": text, "pattern": pattern, "pi": pi[:], "i": 0, "j": 0}, "reason": "展示文本串、模式串和前缀表。", "code_line": 1}]
    j = 0
    for i in range(1, len(pattern)):
        while j and pattern[i] != pattern[j]:
            j = pi[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
    j = 0
    result = -1
    for i, ch in enumerate(text):
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"text[{i}]"}, {"id": f"pattern[{j}]"}], "state": {"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j}, "role": "candidate", "reason": "比较当前文本字符和模式字符。", "code_line": 13})
        while j and ch != pattern[j]:
            j = pi[j - 1]
            events.append({"step": len(events), "op": "move", "targets": [{"id": "pointer:j"}], "value": j, "state": {"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j}, "role": "current", "reason": "失配时根据前缀表回退模式指针。", "code_line": 15})
        if ch == pattern[j]:
            j += 1
        if j == len(pattern):
            result = i - len(pattern) + 1
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"text[{result}]"}], "state": {"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j}, "role": "answer", "reason": "模式串完整匹配，返回起始位置。", "code_line": 19})
            break
    if result == -1:
        events.append({"step": len(events), "op": "explain", "state": {"text": text, "pattern": pattern, "pi": pi[:], "j": j}, "reason": "扫描结束，没有找到模式串。", "code_line": 21})
    return {"schema_version": "semantic-trace-v1", "algorithm": "KMP 字符串匹配", "input_data": input_data, "result": result, "pseudocode": ["构建前缀表", "匹配时用前缀表回退 j"], "events": events}
"""


KMP_VERIFIER = """
def verify(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        return 0
    for i in range(0, len(text) - len(pattern) + 1):
        if text[i:i + len(pattern)] == pattern:
            return i
    return -1
"""


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
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "seen"}], "state": {"nums": nums, "seen": {}, "target": target}, "reason": "初始化数组和哈希表，哈希表记录数值到下标。", "code_line": 1}]
    result = []
    for i, x in enumerate(nums):
        need = target - x
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{i}]"}], "deps": [{"id": f"seen:{need}"}], "state": {"nums": nums, "seen": dict(seen), "target": target, "i": i, "need": need}, "role": "candidate", "reason": "检查当前数的互补值是否已经出现。", "code_line": 4})
        if need in seen:
            result = [seen[need], i]
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{seen[need]}]"}, {"id": f"nums[{i}]"}], "state": {"nums": nums, "seen": dict(seen), "target": target, "answer": result}, "role": "answer", "reason": "互补值已经在哈希表中，找到答案下标。", "code_line": 5})
            break
        seen[x] = i
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"seen:{x}"}], "after": i, "state": {"nums": nums, "seen": dict(seen), "target": target, "i": i}, "role": "visited", "reason": "把当前数和下标写入哈希表。", "code_line": 7})
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


DAILY_TEMPERATURES_CODE = """
def solve(input_data):
    temperatures = input_data["temperatures"]
    answer = [0] * len(temperatures)
    stack = []
    for i, temp in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < temp:
            j = stack.pop()
            answer[j] = i - j
        stack.append(i)
    return answer
"""


DAILY_TEMPERATURES_TRACKER = """
def trace(input_data):
    temperatures = input_data["temperatures"]
    answer = [0] * len(temperatures)
    stack = []
    events = [{"step": 0, "op": "create", "targets": [{"id": "temperatures"}, {"id": "stack"}, {"id": "answer"}], "state": {"temperatures": temperatures, "stack": [], "answer": answer[:], "stack_order": "decreasing"}, "reason": "初始化答案数组和单调递减栈，栈里保存还没找到更暖天的下标。", "code_line": 1}]
    for i, temp in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < temp:
            j = stack.pop()
            answer[j] = i - j
            events.append({"step": len(events), "op": "set", "targets": [{"id": f"answer[{j}]"}], "deps": [{"id": f"temperatures[{j}]"}, {"id": f"temperatures[{i}]"}], "after": answer[j], "state": {"temperatures": temperatures, "stack": stack[:], "answer": answer[:], "stack_order": "decreasing", "i": i}, "role": "answer", "reason": "当前温度更高，弹出栈顶并写入等待天数。", "code_line": 6})
        stack.append(i)
        events.append({"step": len(events), "op": "push", "targets": [{"id": "stack"}, {"id": f"temperatures[{i}]"}], "state": {"temperatures": temperatures, "stack": stack[:], "answer": answer[:], "stack_order": "decreasing", "i": i}, "role": "current", "reason": "当前下标入栈，继续等待未来更高温度。", "code_line": 8})
    return {"schema_version": "semantic-trace-v1", "algorithm": "每日温度", "input_data": input_data, "result": answer, "pseudocode": ["维护温度单调递减的下标栈", "遇到更高温度时弹栈并写答案"], "events": events}
"""


DAILY_TEMPERATURES_VERIFIER = """
def verify(input_data):
    temperatures = input_data["temperatures"]
    ans = []
    for i, temp in enumerate(temperatures):
        wait = 0
        for j in range(i + 1, len(temperatures)):
            if temperatures[j] > temp:
                wait = j - i
                break
        ans.append(wait)
    return ans
"""


MERGE_SORT_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    return sorted(nums)
"""


MERGE_SORT_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    arr = nums[:]
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}], "state": {"nums": arr[:]}, "reason": "复制原数组，准备排序。", "code_line": 1}]
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{i}]"}], "state": {"nums": arr[:], "i": i, "key": key}, "role": "candidate", "reason": "取出当前位置元素，向左寻找插入位置。", "code_line": 3})
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            events.append({"step": len(events), "op": "set", "targets": [{"id": f"nums[{j + 1}]"}], "deps": [{"id": f"nums[{j}]"}], "after": arr[j + 1], "state": {"nums": arr[:], "i": i, "j": j}, "role": "current", "reason": "左侧元素更大，向右移动一格。", "code_line": 5})
            j -= 1
        arr[j + 1] = key
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"nums[{j + 1}]"}], "after": key, "state": {"nums": arr[:], "i": i, "j": j + 1}, "role": "answer", "reason": "把元素放到有序前缀的正确位置。", "code_line": 7})
    return {"schema_version": "semantic-trace-v1", "algorithm": "插入排序", "input_data": input_data, "result": arr, "pseudocode": ["逐步维护有序前缀", "将当前元素插入正确位置"], "events": events}
"""


MERGE_SORT_VERIFIER = """
def verify(input_data):
    return sorted(input_data["nums"])
"""


LCA_CODE = """
def solve(input_data):
    tree = input_data["tree"]
    p = str(input_data["p"])
    q = str(input_data["q"])
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {v for _, v in tree["edges"]}
    root = ""
    target_ids = {str(x) for x in targets}
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in target_ids:
            root = node_id
            break
    def dfs(node):
        if node == p or node == q:
            return node
        hits = []
        for child in children.get(node, []):
            got = dfs(child)
            if got is not None:
                hits.append(got)
        if len(hits) >= 2:
            return node
        return hits[0] if hits else None
    return dfs(root)
"""


LCA_TRACKER = """
def trace(input_data):
    tree = input_data["tree"]
    p = str(input_data["p"])
    q = str(input_data["q"])
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    events = [{"step": 0, "op": "create", "targets": [{"id": "tree"}, {"id": f"node:{root}"}], "state": {"tree": tree, "p": p, "q": q}, "reason": "展示二叉树和两个目标节点。", "code_line": 1}]
    def dfs(node):
        events.append({"step": len(events), "op": "enter", "targets": [{"id": f"node:{node}"}], "state": {"tree": tree, "p": p, "q": q, "current": node}, "role": "current", "reason": "递归检查当前子树是否包含目标节点。", "code_line": 8})
        if node == p or node == q:
            return node
        hits = []
        for child in children.get(node, []):
            got = dfs(child)
            if got is not None:
                hits.append(got)
        if len(hits) >= 2:
            return node
        return hits[0] if hits else None
    answer = dfs(root)
    events.append({"step": len(events), "op": "mark", "targets": [{"id": f"node:{answer}"}], "state": {"tree": tree, "p": p, "q": q, "lca": answer}, "role": "answer", "reason": "左右子树分别命中目标，当前节点就是最近公共祖先。", "code_line": 17})
    return {"schema_version": "semantic-trace-v1", "algorithm": "二叉树最近公共祖先", "input_data": input_data, "result": answer, "pseudocode": ["后序 DFS", "若左右子树都命中目标，当前节点是 LCA"], "events": events}
"""


LCA_VERIFIER = """
def verify(input_data):
    tree = input_data["tree"]
    p = str(input_data["p"])
    q = str(input_data["q"])
    parent = {}
    nodes = {str(node["id"]) for node in tree["nodes"]}
    for u, v in tree["edges"]:
        parent[str(v)] = str(u)
    ancestors = set()
    cur = p
    while cur in nodes:
        ancestors.add(cur)
        if cur not in parent:
            break
        cur = parent[cur]
    cur = q
    while cur not in ancestors:
        cur = parent[cur]
    return cur
"""


KTH_LARGEST_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    k = input_data["k"]
    import heapq
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
"""


KTH_LARGEST_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    k = input_data["k"]
    import heapq
    heap = []
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "heap"}], "state": {"nums": nums, "heap": [], "heap_type": "min", "k": k}, "reason": "维护容量为 k 的小顶堆。", "code_line": 1}]
    for i, x in enumerate(nums):
        heapq.heappush(heap, x)
        events.append({"step": len(events), "op": "push", "targets": [{"id": "heap"}, {"id": f"nums[{i}]"}], "state": {"nums": nums, "heap": heap[:], "heap_type": "min", "k": k, "i": i}, "role": "current", "reason": "把当前元素加入小顶堆。", "code_line": 5})
        if len(heap) > k:
            removed = heapq.heappop(heap)
            events.append({"step": len(events), "op": "pop", "targets": [{"id": "heap"}], "value": removed, "state": {"nums": nums, "heap": heap[:], "heap_type": "min", "k": k, "i": i}, "role": "conflict", "reason": "堆超过 k 个元素，弹出最小值，保留最大的 k 个。", "code_line": 7})
    answer = heap[0]
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "heap[0]"}], "state": {"nums": nums, "heap": heap[:], "heap_type": "min", "k": k, "answer": answer}, "role": "answer", "reason": "堆顶就是第 k 大元素。", "code_line": 8})
    return {"schema_version": "semantic-trace-v1", "algorithm": "数组中的第 K 个最大元素", "input_data": input_data, "result": answer, "pseudocode": ["维护大小为 k 的小顶堆", "堆顶是当前第 k 大"], "events": events}
"""


KTH_LARGEST_VERIFIER = """
def verify(input_data):
    return sorted(input_data["nums"], reverse=True)[input_data["k"] - 1]
"""


TRIE_PREFIX_CODE = """
def solve(input_data):
    words = input_data["words"]
    prefix = input_data["prefix"]
    count = 0
    for word in words:
        if word.startswith(prefix):
            count += 1
    return count
"""


TRIE_PREFIX_TRACKER = """
def trace(input_data):
    words = input_data["words"]
    prefix = input_data["prefix"]
    trie = {"nodes": [{"id": "root", "label": "root"}], "edges": []}
    children = {"root": {}}
    events = [{"step": 0, "op": "create", "targets": [{"id": "trie"}], "state": {"trie": trie, "words": words, "prefix": prefix}, "reason": "初始化 Trie 根节点。", "code_line": 1}]
    for word in words:
        cur = "root"
        for ch in word:
            if ch not in children[cur]:
                nxt = f"{cur}_{ch}_{len(trie['nodes'])}"
                children[cur][ch] = nxt
                children[nxt] = {}
                trie["nodes"].append({"id": nxt, "label": ch})
                trie["edges"].append([cur, nxt])
                events.append({"step": len(events), "op": "link", "targets": [{"id": f"node:{nxt}"}], "deps": [{"id": f"node:{cur}"}], "state": {"trie": {"nodes": trie["nodes"][:], "edges": trie["edges"][:]}, "words": words, "prefix": prefix}, "role": "current", "reason": "插入单词时创建新的 Trie 节点。", "code_line": 8})
            cur = children[cur][ch]
    count = sum(1 for word in words if word.startswith(prefix))
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "trie"}], "state": {"trie": trie, "words": words, "prefix": prefix, "answer": count}, "role": "answer", "reason": "统计以给定前缀开头的单词数量。", "code_line": 13})
    return {"schema_version": "semantic-trace-v1", "algorithm": "Trie 前缀计数", "input_data": input_data, "result": count, "pseudocode": ["把单词插入 Trie", "沿前缀路径统计匹配单词"], "events": events}
"""


TRIE_PREFIX_VERIFIER = """
def verify(input_data):
    return sum(1 for word in input_data["words"] if word.startswith(input_data["prefix"]))
"""


PROVINCES_CODE = """
def solve(input_data):
    is_connected = input_data["isConnected"]
    n = len(is_connected)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j]:
                parent[find(i)] = find(j)
    return len({find(i) for i in range(n)})
"""


PROVINCES_TRACKER = """
def trace(input_data):
    is_connected = input_data["isConnected"]
    n = len(is_connected)
    parent = {str(i): str(i) for i in range(n)}
    def find(x):
        while parent[str(x)] != str(x):
            x = int(parent[str(x)])
        return str(x)
    events = [{"step": 0, "op": "create", "targets": [{"id": "union_find"}], "state": {"isConnected": is_connected, "union_find": {"parent": dict(parent)}}, "reason": "每个城市先作为独立集合。", "code_line": 1}]
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j]:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
                    events.append({"step": len(events), "op": "link", "targets": [{"id": f"node:{ri}"}], "deps": [{"id": f"node:{rj}"}], "state": {"isConnected": is_connected, "union_find": {"parent": dict(parent)}, "i": i, "j": j}, "role": "current", "reason": "两个城市直接相连，合并它们所在集合。", "code_line": 12})
    answer = len({find(i) for i in range(n)})
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "union_find"}], "state": {"isConnected": is_connected, "union_find": {"parent": dict(parent)}, "answer": answer}, "role": "answer", "reason": "根节点数量就是省份数量。", "code_line": 14})
    return {"schema_version": "semantic-trace-v1", "algorithm": "省份数量", "input_data": input_data, "result": answer, "pseudocode": ["每个城市初始化为独立集合", "相连城市执行 union", "统计集合根数量"], "events": events}
"""


PROVINCES_VERIFIER = """
def verify(input_data):
    g = input_data["isConnected"]
    n = len(g)
    seen = [False] * n
    def dfs(i):
        seen[i] = True
        for j, ok in enumerate(g[i]):
            if ok and not seen[j]:
                dfs(j)
    count = 0
    for i in range(n):
        if not seen[i]:
            count += 1
            dfs(i)
    return count
"""


PERMUTATIONS_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    ans = []
    used = [False] * len(nums)
    path = []
    def dfs():
        if len(path) == len(nums):
            ans.append(path[:])
            return
        for i, x in enumerate(nums):
            if not used[i]:
                used[i] = True
                path.append(x)
                dfs()
                path.pop()
                used[i] = False
    dfs()
    return ans
"""


PERMUTATIONS_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    ans = []
    used = [False] * len(nums)
    path = []
    tree = {"nodes": [{"id": "root", "label": "[]"}], "edges": []}
    events = [{"step": 0, "op": "create", "targets": [{"id": "recursion_tree"}], "state": {"nums": nums, "path": [], "recursion_tree": tree}, "reason": "从空路径开始回溯搜索。", "code_line": 1}]
    def dfs(parent_id):
        if len(path) == len(nums):
            ans.append(path[:])
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"node:{parent_id}"}], "state": {"nums": nums, "path": path[:], "answer": [x[:] for x in ans], "recursion_tree": {"nodes": tree["nodes"][:], "edges": tree["edges"][:]}}, "role": "answer", "reason": "路径长度等于 nums 长度，得到一个排列。", "code_line": 7})
            return
        for i, x in enumerate(nums):
            if not used[i]:
                used[i] = True
                path.append(x)
                node_id = f"{parent_id}_{i}_{len(tree['nodes'])}"
                tree["nodes"].append({"id": node_id, "label": str(path[:])})
                tree["edges"].append([parent_id, node_id])
                events.append({"step": len(events), "op": "enter", "targets": [{"id": f"node:{node_id}"}], "deps": [{"id": f"node:{parent_id}"}], "state": {"nums": nums, "path": path[:], "recursion_tree": {"nodes": tree["nodes"][:], "edges": tree["edges"][:]}}, "role": "current", "reason": "选择一个未使用数字，进入下一层搜索。", "code_line": 12})
                dfs(node_id)
                path.pop()
                used[i] = False
    dfs("root")
    return {"schema_version": "semantic-trace-v1", "algorithm": "全排列回溯", "input_data": input_data, "result": ans, "pseudocode": ["选择未使用数字加入 path", "path 满长时记录答案", "返回时撤销选择"], "events": events}
"""


PERMUTATIONS_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    if not nums:
        return [[]]
    result = []
    for i, x in enumerate(nums):
        rest = nums[:i] + nums[i + 1:]
        for tail in verify({"nums": rest}):
            result.append([x] + tail)
    return result
"""


CONVEX_HULL_CODE = """
def solve(input_data):
    points = [tuple(p) for p in input_data["points"]]
    points = sorted(set(points))
    if len(points) <= 1:
        return [list(p) for p in points]
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    return [list(p) for p in hull]
"""


CONVEX_HULL_TRACKER = """
def trace(input_data):
    raw_points = input_data["points"]
    points = sorted(set(tuple(p) for p in raw_points))
    geometry_points = [{"id": str(i), "x": p[0], "y": p[1], "label": str(list(p))} for i, p in enumerate(points)]
    events = [{"step": 0, "op": "create", "targets": [{"id": "geometry"}], "state": {"geometry": {"points": geometry_points}}, "reason": "按坐标排序点集，准备 Graham/Andrew 扫描。", "code_line": 1}]
    if len(points) <= 1:
        return {"schema_version": "semantic-trace-v1", "algorithm": "凸包", "input_data": input_data, "result": [list(p) for p in points], "events": events}
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
        events.append({"step": len(events), "op": "mark", "targets": [{"id": f"point:{points.index(p)}"}], "state": {"geometry": {"points": geometry_points, "hull": [str(points.index(x)) for x in lower], "closed": False}}, "role": "current", "reason": "维护下凸壳，保证连续三点保持左转。", "code_line": 9})
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    result = [list(p) for p in hull]
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "geometry"}], "state": {"geometry": {"points": geometry_points, "hull": [str(points.index(x)) for x in hull], "closed": True}, "answer": result}, "role": "answer", "reason": "合并上下凸壳得到最终凸包。", "code_line": 18})
    return {"schema_version": "semantic-trace-v1", "algorithm": "凸包", "input_data": input_data, "result": result, "pseudocode": ["排序点集", "维护下凸壳和上凸壳", "合并得到凸包"], "events": events}
"""


CONVEX_HULL_VERIFIER = """
def verify(input_data):
    points = [tuple(p) for p in input_data["points"]]
    points = sorted(set(points))
    if len(points) <= 1:
        return [list(p) for p in points]
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return [list(p) for p in lower[:-1] + upper[:-1]]
"""


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            id="house_robber",
            title="打家劫舍",
            problem=(
                "LeetCode 198. 打家劫舍。给定一个非负整数数组 nums，"
                "每个元素表示一间房屋的金额。不能偷相邻的两间房屋，"
                "返回在不触发警报的情况下能够偷到的最高金额。"
            ),
            family="一维 DP",
            input_contract="输入 nums 数组。",
            variant_name="动态规划",
            strategy="使用 dp[i] 记录前 i 间房屋的最大收益。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("array",),
            code=HOUSE_ROBBER_CODE,
            tracker_code=HOUSE_ROBBER_TRACKER,
            verifier_code=HOUSE_ROBBER_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [2, 7, 9, 3, 1]}, 12),
                BenchmarkInput({"nums": [1, 2, 3, 1]}, 4),
                BenchmarkInput({"nums": []}, 0),
            ),
        ),
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
            id="unique_paths",
            title="不同路径",
            problem=(
                "LeetCode 62. 不同路径。一个机器人位于 m x n 网格左上角，"
                "每次只能向下或向右移动一步，返回到达右下角的不同路径数量。"
            ),
            family="二维 DP",
            input_contract="输入 m 和 n。",
            variant_name="二维 DP 表",
            strategy="每个格子的路径数来自上方和左侧。",
            time_complexity="O(mn)",
            space_complexity="O(mn)",
            expected_layouts=("matrix",),
            code=UNIQUE_PATHS_CODE,
            tracker_code=UNIQUE_PATHS_TRACKER,
            verifier_code=UNIQUE_PATHS_VERIFIER,
            samples=(
                BenchmarkInput({"m": 3, "n": 7}, 28),
                BenchmarkInput({"m": 3, "n": 2}, 3),
                BenchmarkInput({"m": 1, "n": 5}, 1),
            ),
        ),
        BenchmarkCase(
            id="graph_bfs",
            title="图 BFS 最短层数",
            problem=(
                "给定一个无权图的邻接表 graph 和起点 start，"
                "返回从 start 到所有可达节点的最短边数距离。"
            ),
            family="BFS/DFS 基础图",
            input_contract="输入邻接表 graph 和起点 start。",
            variant_name="队列 BFS",
            strategy="队列按层扩展，首次访问时确定距离。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "queue"),
            code=GRAPH_BFS_CODE,
            tracker_code=GRAPH_BFS_TRACKER,
            verifier_code=GRAPH_BFS_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, "start": "A"}, {"A": 0, "B": 1, "C": 1, "D": 2}),
                BenchmarkInput({"graph": {"1": ["2"], "2": ["3"], "3": [], "4": []}, "start": "1"}, {"1": 0, "2": 1, "3": 2}),
            ),
        ),
        BenchmarkCase(
            id="kmp",
            title="KMP 字符串匹配",
            problem=(
                "实现字符串匹配。给定 text 和 pattern，返回 pattern 在 text 中第一次出现的起始下标；"
                "如果不存在返回 -1；如果 pattern 为空返回 0。希望使用 KMP 或等价的线性字符串匹配思路。"
            ),
            family="字符串高级算法",
            input_contract="输入 text 和 pattern。",
            variant_name="前缀表匹配",
            strategy="使用 KMP 前缀表，trace 只记录初始化、一次前缀表更新、一次失配回退、一次成功匹配等关键步骤，不要逐字符展开全部循环。",
            time_complexity="O(n+m)",
            space_complexity="O(m)",
            expected_layouts=("string",),
            code=KMP_CODE,
            tracker_code=KMP_TRACKER,
            verifier_code=KMP_VERIFIER,
            samples=(
                BenchmarkInput({"text": "ababc", "pattern": "abc"}, 2),
                BenchmarkInput({"text": "aaaaa", "pattern": "bba"}, -1),
                BenchmarkInput({"text": "abc", "pattern": ""}, 0),
            ),
        ),
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
            id="daily_temperatures",
            title="每日温度",
            problem=(
                "LeetCode 739. 每日温度。给定整数数组 temperatures，"
                "返回每一天需要等几天才会出现更高温度；如果之后没有更高温度，则为 0。"
            ),
            family="栈 / 队列 / 单调栈",
            input_contract="输入 temperatures 数组。",
            variant_name="单调栈",
            strategy="维护温度单调递减的下标栈，遇到更高温度时弹栈并写答案。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("array", "stack"),
            code=DAILY_TEMPERATURES_CODE,
            tracker_code=DAILY_TEMPERATURES_TRACKER,
            verifier_code=DAILY_TEMPERATURES_VERIFIER,
            samples=(
                BenchmarkInput({"temperatures": [73, 74, 75, 71, 69, 72, 76, 73]}, [1, 1, 4, 2, 1, 1, 0, 0]),
                BenchmarkInput({"temperatures": [30, 40, 50, 60]}, [1, 1, 1, 0]),
                BenchmarkInput({"temperatures": [30, 60, 90]}, [1, 1, 0]),
            ),
        ),
        BenchmarkCase(
            id="insertion_sort",
            title="插入排序",
            problem=(
                "给定整数数组 nums，使用插入排序思想将数组升序排列，返回排序后的数组。"
            ),
            family="排序",
            input_contract="输入 nums 数组。",
            variant_name="插入排序",
            strategy="逐步维护有序前缀，把当前元素插入正确位置。",
            time_complexity="O(n^2)",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=MERGE_SORT_CODE,
            tracker_code=MERGE_SORT_TRACKER,
            verifier_code=MERGE_SORT_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [5, 2, 3, 1]}, [1, 2, 3, 5]),
                BenchmarkInput({"nums": [1, 2, 3]}, [1, 2, 3]),
                BenchmarkInput({"nums": [3, -1, 0, 3]}, [-1, 0, 3, 3]),
            ),
        ),
        BenchmarkCase(
            id="lca",
            title="二叉树最近公共祖先",
            problem=(
                "给定一棵二叉树 tree，以及两个节点 p 和 q，返回它们的最近公共祖先节点 id。"
                "tree 使用 nodes 和 edges 表示，edges 的方向是父节点到子节点。"
            ),
            family="树 / BST / LCA",
            input_contract="输入 tree、p、q。",
            variant_name="后序 DFS",
            strategy="DFS 返回当前子树是否命中 p 或 q；左右都命中时当前节点为 LCA。",
            time_complexity="O(n)",
            space_complexity="O(h)",
            expected_layouts=("tree",),
            code=LCA_CODE,
            tracker_code=LCA_TRACKER,
            verifier_code=LCA_VERIFIER,
            samples=(
                BenchmarkInput({"tree": {"nodes": [{"id": "3"}, {"id": "5"}, {"id": "1"}, {"id": "6"}, {"id": "2"}, {"id": "0"}, {"id": "8"}, {"id": "7"}, {"id": "4"}], "edges": [["3", "5"], ["3", "1"], ["5", "6"], ["5", "2"], ["1", "0"], ["1", "8"], ["2", "7"], ["2", "4"]]}, "p": "5", "q": "1"}, "3"),
                BenchmarkInput({"tree": {"nodes": [{"id": "3"}, {"id": "5"}, {"id": "1"}, {"id": "6"}, {"id": "2"}, {"id": "7"}, {"id": "4"}], "edges": [["3", "5"], ["3", "1"], ["5", "6"], ["5", "2"], ["2", "7"], ["2", "4"]]}, "p": "7", "q": "4"}, "2"),
            ),
        ),
        BenchmarkCase(
            id="kth_largest",
            title="数组中的第 K 个最大元素",
            problem=(
                "LeetCode 215. 给定整数数组 nums 和整数 k，返回数组中第 k 个最大的元素。"
                "希望使用容量为 k 的小顶堆。"
            ),
            family="堆 / TopK / Huffman",
            input_contract="输入 nums 数组和 k。",
            variant_name="小顶堆 TopK",
            strategy="维护容量为 k 的小顶堆，堆顶就是当前第 k 大。",
            time_complexity="O(n log k)",
            space_complexity="O(k)",
            expected_layouts=("array", "heap"),
            code=KTH_LARGEST_CODE,
            tracker_code=KTH_LARGEST_TRACKER,
            verifier_code=KTH_LARGEST_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [3, 2, 1, 5, 6, 4], "k": 2}, 5),
                BenchmarkInput({"nums": [3, 2, 3, 1, 2, 4, 5, 5, 6], "k": 4}, 4),
            ),
        ),
        BenchmarkCase(
            id="trie_prefix",
            title="Trie 前缀计数",
            problem=(
                "给定字符串数组 words 和前缀 prefix，使用 Trie 思路统计有多少单词以 prefix 开头。"
            ),
            family="Trie",
            input_contract="输入 words 和 prefix。",
            variant_name="Trie 插入与前缀统计",
            strategy="把所有单词插入 Trie，再沿前缀路径统计匹配数量。",
            time_complexity="O(总字符数)",
            space_complexity="O(总字符数)",
            expected_layouts=("trie",),
            code=TRIE_PREFIX_CODE,
            tracker_code=TRIE_PREFIX_TRACKER,
            verifier_code=TRIE_PREFIX_VERIFIER,
            samples=(
                BenchmarkInput({"words": ["apple", "app", "ape", "bat"], "prefix": "ap"}, 3),
                BenchmarkInput({"words": ["dog", "door", "deer"], "prefix": "doo"}, 1),
            ),
        ),
        BenchmarkCase(
            id="provinces",
            title="省份数量",
            problem=(
                "LeetCode 547. 省份数量。给定城市连通矩阵 isConnected，"
                "如果两个城市直接或间接相连，则属于同一个省份。返回省份数量。"
            ),
            family="并查集",
            input_contract="输入 isConnected 矩阵。",
            variant_name="并查集合并",
            strategy="相连城市执行 union，最后统计根节点数量。",
            time_complexity="O(n^2 α(n))",
            space_complexity="O(n)",
            expected_layouts=("matrix", "union_find"),
            code=PROVINCES_CODE,
            tracker_code=PROVINCES_TRACKER,
            verifier_code=PROVINCES_VERIFIER,
            samples=(
                BenchmarkInput({"isConnected": [[1, 1, 0], [1, 1, 0], [0, 0, 1]]}, 2),
                BenchmarkInput({"isConnected": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}, 3),
            ),
        ),
        BenchmarkCase(
            id="permutations",
            title="全排列",
            problem=(
                "LeetCode 46. 全排列。给定不含重复数字的数组 nums，返回所有可能的排列。"
            ),
            family="回溯 / 递归",
            input_contract="输入 nums 数组。",
            variant_name="回溯搜索树",
            strategy="用 path 保存当前选择，递归选择未使用数字，返回时撤销选择。",
            time_complexity="O(n! n)",
            space_complexity="O(n)",
            expected_layouts=("array", "recursion_tree"),
            code=PERMUTATIONS_CODE,
            tracker_code=PERMUTATIONS_TRACKER,
            verifier_code=PERMUTATIONS_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 2, 3]}, [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]),
                BenchmarkInput({"nums": [0, 1]}, [[0, 1], [1, 0]]),
            ),
        ),
        BenchmarkCase(
            id="convex_hull",
            title="凸包",
            problem=(
                "给定二维点集 points，返回这些点的凸包顶点，按 Andrew 单调链算法的输出顺序排列。"
            ),
            family="几何 / 扫描线",
            input_contract="输入 points 二维点数组。",
            variant_name="Andrew 单调链",
            strategy="按坐标排序点集，分别维护上下凸壳，使用 orientation/cross 判断转向。",
            time_complexity="O(n log n)",
            space_complexity="O(n)",
            expected_layouts=("geometry",),
            code=CONVEX_HULL_CODE,
            tracker_code=CONVEX_HULL_TRACKER,
            verifier_code=CONVEX_HULL_VERIFIER,
            samples=(
                BenchmarkInput({"points": [[0, 0], [1, 1], [2, 0], [1, 2]]}, [[0, 0], [2, 0], [1, 2]]),
                BenchmarkInput({"points": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]}, [[0, 0], [1, 0], [1, 1], [0, 1]]),
            ),
        ),
    )
