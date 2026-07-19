"""Benchmark cases: dp."""

from __future__ import annotations

from benchmark.cases import BenchmarkCase, BenchmarkInput

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
    tracer = Tracer(input_data, algorithm="不同路径", pseudocode=["dp[i][j] = dp[i-1][j] + dp[i][j-1]"])
    dp = [[1] * n for _ in range(m)]
    tracer.expect_updates("dp", max(0, (m - 1) * (n - 1)))
    tracer.create("dp", state={"dp": [row[:] for row in dp]}, reason="第一行和第一列只有一种路径。", code_line=1)
    for i in range(1, m):
        for j in range(1, n):
            tracer.compare(
                [f"dp[{i}][{j}]"],
                deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
                state={"dp": [row[:] for row in dp], "i": i, "j": j},
                role="candidate",
                reason="当前位置只能从上方或左侧到达。",
                code_line=3,
            )
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
            tracer.set(
                f"dp[{i}][{j}]",
                value=dp[i][j],
                deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
                state={"dp": [row[:] for row in dp], "i": i, "j": j},
                role="answer",
                reason="写入上方和左侧路径数之和。",
                code_line=3,
            )
    tracer.result(dp[m - 1][n - 1])
    return tracer.to_trace()
"""


UNIQUE_PATHS_VERIFIER = """
def verify(input_data):
    import math
    m, n = input_data["m"], input_data["n"]
    return math.comb(m + n - 2, m - 1)
"""


KNAPSACK_01_SUBSET_SUM_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    total = sum(nums)
    if total % 2 == 1:
        return False
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:
        for capacity in range(target, num - 1, -1):
            dp[capacity] = dp[capacity] or dp[capacity - num]
    return dp[target]
"""


KNAPSACK_01_SUBSET_SUM_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    total = sum(nums)
    if total % 2 == 1:
        tracer = Tracer(input_data, algorithm="0-1 背包等和划分", pseudocode=["总和为奇数时不能等分"], policy="full", max_events=160)
        tracer.create("dp", state={"nums": nums[:], "target": None, "dp": [], "answer": False}, reason="总和为奇数，无法划分成两个相等子集。", code_line=1)
        tracer.result(False)
        return tracer.to_trace()
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True
    contract = {
        "containers": ["dp"],
        "answer_position": f"dp[{target}]",
        "expected_targets": [],
        "subfamily": "knapsack_01",
    }
    for num in nums:
        for capacity in range(target, num - 1, -1):
            contract["expected_targets"].append(f"dp[{capacity}]")
    tracer = Tracer(input_data, algorithm="0-1 背包等和划分", pseudocode=["dp[c] 表示前 i 个数能否凑出容量 c", "逆序遍历容量避免重复使用同一个数"], policy="full", max_events=180)
    tracer.expect_updates("dp", len(contract["expected_targets"]))
    tracer.create("dp", state={"nums": nums[:], "target": target, "dp": dp[:], "i": -1, "formula": "dp[0]=True", "dp_contract": contract}, reason="初始化 0-1 背包可达性数组，只有容量 0 可达。", code_line=1)
    for i, num in enumerate(nums):
        for capacity in range(target, num - 1, -1):
            before = dp[capacity]
            dp[capacity] = dp[capacity] or dp[capacity - num]
            tracer.set(
                f"dp[{capacity}]",
                value=dp[capacity],
                before=before,
                deps=[f"dp[{capacity - num}]", f"nums[{i}]"],
                state={"nums": nums[:], "target": target, "dp": dp[:], "i": i, "capacity_index": capacity, "formula": "dp[c]=dp[c] or dp[c-num]", "dp_contract": contract},
                role="current",
                reason="逆序容量转移，当前数只能被使用一次。",
                code_line=8,
            )
    tracer.mark(f"dp[{target}]", value=dp[target], deps=[f"dp[{target}]"], state={"nums": nums[:], "target": target, "dp": dp[:], "i": len(nums) - 1, "capacity_index": target, "answer": dp[target], "formula": "answer=dp[target]", "dp_contract": contract}, role="answer", reason="目标容量是否可达就是能否等和划分。", code_line=10)
    tracer.result(dp[target])
    return tracer.to_trace()
"""


KNAPSACK_01_SUBSET_SUM_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    total = sum(nums)
    if total % 2 == 1:
        return False
    target = total // 2
    reachable = {0}
    for num in nums:
        reachable |= {value + num for value in list(reachable)}
    return target in reachable
"""


COMPLETE_KNAPSACK_COIN_CHANGE_CODE = """
def solve(input_data):
    coins = input_data["coins"]
    amount = input_data["amount"]
    inf = amount + 1
    dp = [inf] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for capacity in range(coin, amount + 1):
            dp[capacity] = min(dp[capacity], dp[capacity - coin] + 1)
    return -1 if dp[amount] == inf else dp[amount]
"""


COMPLETE_KNAPSACK_COIN_CHANGE_TRACKER = """
def trace(input_data):
    coins = input_data["coins"]
    amount = input_data["amount"]
    inf = amount + 1
    dp = [inf] * (amount + 1)
    dp[0] = 0
    contract = {
        "containers": ["dp"],
        "answer_position": f"dp[{amount}]",
        "expected_targets": [f"dp[{capacity}]" for coin in coins for capacity in range(coin, amount + 1)],
        "subfamily": "complete_knapsack",
    }
    tracer = Tracer(input_data, algorithm="完全背包零钱兑换", pseudocode=["dp[c] = min(dp[c], dp[c-coin] + 1)", "正序容量允许重复使用当前 coin"], policy="full", max_events=180)
    tracer.expect_updates("dp", len(contract["expected_targets"]))
    tracer.create("dp", state={"coins": coins[:], "amount": amount, "dp": [-1 if x == inf else x for x in dp], "i": -1, "capacity_index": 0, "knapsack": "complete_min", "formula": "dp[0]=0", "dp_contract": contract}, reason="初始化完全背包数组，容量 0 需要 0 枚硬币。", code_line=1)
    for i, coin in enumerate(coins):
        for capacity in range(coin, amount + 1):
            before = dp[capacity]
            dp[capacity] = min(dp[capacity], dp[capacity - coin] + 1)
            shown = [-1 if x == inf else x for x in dp]
            tracer.set(
                f"dp[{capacity}]",
                value=shown[capacity],
                before=-1 if before == inf else before,
                deps=[f"dp[{capacity - coin}]", f"coins[{i}]"],
                state={"coins": coins[:], "amount": amount, "dp": shown[:], "i": i, "capacity_index": capacity, "knapsack": "complete_min", "formula": "dp[c]=min(dp[c], dp[c-coin]+1)", "dp_contract": contract},
                role="current",
                reason="正序容量转移，当前硬币可以重复使用。",
                code_line=8,
            )
    result = -1 if dp[amount] == inf else dp[amount]
    shown = [-1 if x == inf else x for x in dp]
    tracer.mark(f"dp[{amount}]", value=result, deps=[f"dp[{amount}]"], state={"coins": coins[:], "amount": amount, "dp": shown[:], "i": len(coins) - 1, "capacity_index": amount, "knapsack": "complete_min", "answer": result, "formula": "answer=dp[amount]", "dp_contract": contract}, role="answer", reason="最终容量 amount 的最少硬币数就是答案。", code_line=10)
    tracer.result(result)
    return tracer.to_trace()
"""


COMPLETE_KNAPSACK_COIN_CHANGE_VERIFIER = """
def verify(input_data):
    coins = input_data["coins"]
    amount = input_data["amount"]
    best = amount + 1
    def dfs(index, total, used):
        nonlocal best
        if total == amount:
            best = min(best, used)
            return
        if total > amount or index == len(coins) or used >= best:
            return
        coin = coins[index]
        for take in range((amount - total) // coin + 1):
            dfs(index + 1, total + take * coin, used + take)
    dfs(0, 0, 0)
    return -1 if best == amount + 1 else best
"""


BOUNDED_KNAPSACK_MAX_VALUE_CODE = """
def solve(input_data):
    weights = input_data["weights"]
    values = input_data["values"]
    counts = input_data["counts"]
    capacity = input_data["capacity"]
    dp = [0] * (capacity + 1)
    for weight, value, count in zip(weights, values, counts):
        prev = dp[:]
        for cap in range(capacity + 1):
            best = prev[cap]
            for take in range(1, min(count, cap // weight) + 1):
                best = max(best, prev[cap - take * weight] + take * value)
            dp[cap] = best
    return dp[capacity]
"""


BOUNDED_KNAPSACK_MAX_VALUE_TRACKER = """
def trace(input_data):
    weights = input_data["weights"]
    values = input_data["values"]
    counts = input_data["counts"]
    capacity = input_data["capacity"]
    dp = [0] * (capacity + 1)
    contract = {
        "containers": ["dp"],
        "answer_position": f"dp[{capacity}]",
        "expected_targets": [f"dp[{cap}]" for _ in weights for cap in range(capacity + 1)],
        "subfamily": "bounded_knapsack",
    }
    tracer = Tracer(input_data, algorithm="多重背包最大价值", pseudocode=["每种物品最多 count[i] 件", "dp[c]=max(prev[c-k*w]+k*v)"], policy="full", max_events=180)
    tracer.expect_updates("dp", len(contract["expected_targets"]))
    tracer.create("dp", state={"weights": weights[:], "values": values[:], "counts": counts[:], "capacity": capacity, "dp": dp[:], "i": -1, "capacity_index": 0, "formula": "dp[c]=0", "dp_contract": contract}, reason="初始化多重背包容量数组。", code_line=1)
    for i, (weight, value, count) in enumerate(zip(weights, values, counts)):
        prev = dp[:]
        for cap in range(capacity + 1):
            before = dp[cap]
            best = prev[cap]
            deps = [f"dp[{cap}]"]
            for take in range(1, min(count, cap // weight) + 1):
                candidate = prev[cap - take * weight] + take * value
                deps.append(f"dp[{cap - take * weight}]")
                if candidate > best:
                    best = candidate
            dp[cap] = best
            tracer.set(
                f"dp[{cap}]",
                value=dp[cap],
                before=before,
                deps=deps + [f"weights[{i}]", f"values[{i}]", f"counts[{i}]"],
                state={"weights": weights[:], "values": values[:], "counts": counts[:], "capacity": capacity, "dp": dp[:], "i": i, "capacity_index": cap, "formula": "dp[c]=max(prev[c-k*w]+k*v), 0<=k<=count", "dp_contract": contract},
                role="current",
                reason="枚举当前物品可取数量，不能超过 count 限制。",
                code_line=9,
            )
    tracer.mark(f"dp[{capacity}]", value=dp[capacity], deps=[f"dp[{capacity}]"], state={"weights": weights[:], "values": values[:], "counts": counts[:], "capacity": capacity, "dp": dp[:], "i": len(weights) - 1, "capacity_index": capacity, "answer": dp[capacity], "formula": "answer=dp[capacity]", "dp_contract": contract}, role="answer", reason="容量上限内可取得的最大价值就是答案。", code_line=13)
    tracer.result(dp[capacity])
    return tracer.to_trace()
"""


BOUNDED_KNAPSACK_MAX_VALUE_VERIFIER = """
def verify(input_data):
    weights = input_data["weights"]
    values = input_data["values"]
    counts = input_data["counts"]
    capacity = input_data["capacity"]
    best = 0
    def dfs(index, used_weight, used_value):
        nonlocal best
        if used_weight > capacity:
            return
        if index == len(weights):
            best = max(best, used_value)
            return
        for take in range(counts[index] + 1):
            dfs(index + 1, used_weight + take * weights[index], used_value + take * values[index])
    dfs(0, 0, 0)
    return best
"""


LCS_LENGTH_CODE = """
def solve(input_data):
    a = input_data["text1"]
    b = input_data["text2"]
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[len(a)][len(b)]
"""


LCS_LENGTH_TRACKER = """
def trace(input_data):
    a = input_data["text1"]
    b = input_data["text2"]
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    contract = {"containers": ["dp"], "answer_position": f"dp[{len(a)}][{len(b)}]", "expected_targets": [f"dp[{i}][{j}]" for i in range(1, len(a) + 1) for j in range(1, len(b) + 1)], "subfamily": "lcs"}
    tracer = Tracer(input_data, algorithm="LCS 最长公共子序列", pseudocode=["相等时来自左上角 + 1", "不等时取上方和左方最大值"], policy="full", max_events=180)
    tracer.expect_updates("dp", len(contract["expected_targets"]))
    tracer.create("dp", state={"text1": a, "text2": b, "dp": [row[:] for row in dp], "i": 0, "j": 0, "formula": "dp[0][*]=dp[*][0]=0", "dp_contract": contract}, reason="初始化 LCS DP 表，空前缀长度为 0。", code_line=1)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            before = dp[i][j]
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                deps = [f"dp[{i - 1}][{j - 1}]", f"text1[{i - 1}]", f"text2[{j - 1}]"]
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
                deps = [f"dp[{i - 1}][{j}]", f"dp[{i}][{j - 1}]", f"text1[{i - 1}]", f"text2[{j - 1}]"]
            tracer.set(f"dp[{i}][{j}]", value=dp[i][j], before=before, deps=deps, state={"text1": a, "text2": b, "dp": [row[:] for row in dp], "i": i, "j": j, "formula": "dp[i][j]=dp[i-1][j-1]+1 if equal else max(top,left)", "dp_contract": contract}, role="current", reason="按当前两个前缀字符关系写入 LCS 长度。", code_line=6)
    answer = dp[len(a)][len(b)]
    tracer.mark(f"dp[{len(a)}][{len(b)}]", value=answer, deps=[f"dp[{len(a)}][{len(b)}]"], state={"text1": a, "text2": b, "dp": [row[:] for row in dp], "i": len(a), "j": len(b), "answer": answer, "formula": "answer=dp[len(text1)][len(text2)]", "dp_contract": contract}, role="answer", reason="完整前缀对应的格子就是 LCS 长度。", code_line=10)
    tracer.result(answer)
    return tracer.to_trace()
"""


LCS_LENGTH_VERIFIER = """
def verify(input_data):
    a = input_data["text1"]
    b = input_data["text2"]
    from functools import lru_cache
    @lru_cache(None)
    def dfs(i, j):
        if i == len(a) or j == len(b):
            return 0
        if a[i] == b[j]:
            return 1 + dfs(i + 1, j + 1)
        return max(dfs(i + 1, j), dfs(i, j + 1))
    return dfs(0, 0)
"""


EDIT_DISTANCE_CODE = """
def solve(input_data):
    a = input_data["word1"]
    b = input_data["word2"]
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
    return dp[len(a)][len(b)]
"""


EDIT_DISTANCE_TRACKER = """
def trace(input_data):
    a = input_data["word1"]
    b = input_data["word2"]
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    contract = {"containers": ["dp"], "answer_position": f"dp[{len(a)}][{len(b)}]", "expected_targets": [f"dp[{i}][{j}]" for i in range(1, len(a) + 1) for j in range(1, len(b) + 1)], "subfamily": "edit_distance"}
    tracer = Tracer(input_data, algorithm="编辑距离", pseudocode=["相等时继承左上角", "否则取删除、插入、替换最小值 + 1"], policy="full", max_events=180)
    tracer.expect_updates("dp", len(contract["expected_targets"]))
    tracer.create("dp", state={"word1": a, "word2": b, "dp": [row[:] for row in dp], "i": 0, "j": 0, "formula": "dp[i][0]=i, dp[0][j]=j", "dp_contract": contract}, reason="初始化空串到各前缀的编辑距离。", code_line=1)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            before = dp[i][j]
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
            tracer.set(f"dp[{i}][{j}]", value=dp[i][j], before=before, deps=[f"dp[{i - 1}][{j}]", f"dp[{i}][{j - 1}]", f"dp[{i - 1}][{j - 1}]", f"word1[{i - 1}]", f"word2[{j - 1}]"], state={"word1": a, "word2": b, "dp": [row[:] for row in dp], "i": i, "j": j, "formula": "dp[i][j]=diag if equal else min(delete,insert,replace)+1", "dp_contract": contract}, role="current", reason="写入当前前缀之间的最小编辑次数。", code_line=8)
    answer = dp[len(a)][len(b)]
    tracer.mark(f"dp[{len(a)}][{len(b)}]", value=answer, deps=[f"dp[{len(a)}][{len(b)}]"], state={"word1": a, "word2": b, "dp": [row[:] for row in dp], "i": len(a), "j": len(b), "answer": answer, "formula": "answer=dp[len(word1)][len(word2)]", "dp_contract": contract}, role="answer", reason="完整字符串对应的格子就是编辑距离。", code_line=12)
    tracer.result(answer)
    return tracer.to_trace()
"""


EDIT_DISTANCE_VERIFIER = """
def verify(input_data):
    a = input_data["word1"]
    b = input_data["word2"]
    from functools import lru_cache
    @lru_cache(None)
    def dfs(i, j):
        if i == len(a):
            return len(b) - j
        if j == len(b):
            return len(a) - i
        if a[i] == b[j]:
            return dfs(i + 1, j + 1)
        return 1 + min(dfs(i + 1, j), dfs(i, j + 1), dfs(i + 1, j + 1))
    return dfs(0, 0)
"""


INTERVAL_DP_MERGE_STONES_CODE = """
def solve(input_data):
    stones = input_data["stones"]
    n = len(stones)
    if n <= 1:
        return 0
    prefix = [0]
    for value in stones:
        prefix.append(prefix[-1] + value)
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(0, n - length + 1):
            j = i + length - 1
            dp[i][j] = min(dp[i][k] + dp[k + 1][j] for k in range(i, j)) + prefix[j + 1] - prefix[i]
    return dp[0][n - 1]
"""


INTERVAL_DP_MERGE_STONES_TRACKER = """
def trace(input_data):
    stones = input_data["stones"]
    n = len(stones)
    prefix = [0]
    for value in stones:
        prefix.append(prefix[-1] + value)
    dp = [[0] * n for _ in range(n)]
    expected = [f"dp[{i}][{i + length - 1}]" for length in range(2, n + 1) for i in range(0, n - length + 1)]
    answer_target = "dp[0][0]" if n <= 1 else f"dp[0][{n - 1}]"
    contract = {"containers": ["dp"], "answer_position": answer_target, "expected_targets": expected, "subfamily": "interval_dp"}
    tracer = Tracer(input_data, algorithm="区间 DP 合并石子", pseudocode=["dp[i][j]=min(dp[i][k]+dp[k+1][j])+sum(i,j)", "按区间长度从短到长填表"], policy="full", max_events=180)
    tracer.expect_updates("dp", len(expected))
    tracer.create("dp", state={"stones": stones[:], "prefix": prefix[:], "dp": [row[:] for row in dp], "i": 0, "j": 0, "dp_mode": "min_merge", "formula": "dp[i][i]=0", "dp_contract": contract}, reason="初始化所有单个石堆区间代价为 0。", code_line=1)
    if n <= 1:
        tracer.mark("dp[0][0]", value=0, deps=["dp[0][0]"], state={"stones": stones[:], "prefix": prefix[:], "dp": [row[:] for row in dp], "i": 0, "j": 0, "answer": 0, "dp_mode": "min_merge", "formula": "answer=0", "dp_contract": contract}, role="answer", reason="单个石堆无需合并。", code_line=2)
        tracer.result(0)
        return tracer.to_trace()
    for length in range(2, n + 1):
        for i in range(0, n - length + 1):
            j = i + length - 1
            best = None
            best_k = i
            for k in range(i, j):
                candidate = dp[i][k] + dp[k + 1][j]
                if best is None or candidate < best:
                    best = candidate
                    best_k = k
            before = dp[i][j]
            dp[i][j] = best + prefix[j + 1] - prefix[i]
            tracer.set(f"dp[{i}][{j}]", value=dp[i][j], before=before, deps=[f"dp[{i}][{best_k}]", f"dp[{best_k + 1}][{j}]", f"prefix[{j + 1}]", f"prefix[{i}]"], state={"stones": stones[:], "prefix": prefix[:], "dp": [row[:] for row in dp], "i": i, "j": j, "k": best_k, "dp_mode": "min_merge", "formula": "dp[i][j]=min(dp[i][k]+dp[k+1][j])+sum(i,j)", "dp_contract": contract}, role="current", reason="枚举最后一次合并的切分点，加入当前区间石子总和。", code_line=10)
    answer = dp[0][n - 1]
    tracer.mark(answer_target, value=answer, deps=[answer_target], state={"stones": stones[:], "prefix": prefix[:], "dp": [row[:] for row in dp], "i": 0, "j": n - 1, "answer": answer, "dp_mode": "min_merge", "formula": "answer=dp[0][n-1]", "dp_contract": contract}, role="answer", reason="全区间最小合并代价就是答案。", code_line=13)
    tracer.result(answer)
    return tracer.to_trace()
"""


INTERVAL_DP_MERGE_STONES_VERIFIER = """
def verify(input_data):
    stones = input_data["stones"]
    from functools import lru_cache
    prefix = [0]
    for value in stones:
        prefix.append(prefix[-1] + value)
    @lru_cache(None)
    def dfs(i, j):
        if i >= j:
            return 0
        return min(dfs(i, k) + dfs(k + 1, j) for k in range(i, j)) + prefix[j + 1] - prefix[i]
    return dfs(0, len(stones) - 1) if stones else 0
"""


STATE_COMPRESSION_TSP_CODE = """
def solve(input_data):
    dist = input_data["dist"]
    n = len(dist)
    full = 1 << n
    inf = 10 ** 9
    dp = [[inf] * n for _ in range(full)]
    dp[1][0] = 0
    for mask in range(full):
        for u in range(n):
            if dp[mask][u] >= inf:
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                next_mask = mask | (1 << v)
                dp[next_mask][v] = min(dp[next_mask][v], dp[mask][u] + dist[u][v])
    return min(dp[full - 1][u] + dist[u][0] for u in range(n))
"""


STATE_COMPRESSION_TSP_TRACKER = """
def trace(input_data):
    dist = input_data["dist"]
    n = len(dist)
    full = 1 << n
    inf = 10 ** 9
    dp = [[inf] * n for _ in range(full)]
    dp[1][0] = 0
    expected = []
    reachable_states = [(1, 0)]
    seen_states = {(1, 0)}
    for mask, u in reachable_states:
        for v in range(n):
            if mask & (1 << v):
                continue
            next_mask = mask | (1 << v)
            expected.append(f"dp[{next_mask}][{v}]")
            state = (next_mask, v)
            if state not in seen_states:
                seen_states.add(state)
                reachable_states.append(state)
    contract = {"containers": ["dp"], "answer_position": f"dp[{full - 1}][0]", "expected_targets": expected, "subfamily": "state_compression"}
    tracer = Tracer(input_data, algorithm="状态压缩 DP 旅行回路", pseudocode=["dp[mask][u] 表示访问集合 mask 并停在 u 的最短路", "枚举下一个未访问点扩展 mask"], policy="full", max_events=180)
    tracer.expect_updates("dp", len(expected))
    tracer.create("dp", state={"dist": [row[:] for row in dist], "dp": [row[:] for row in dp], "mask": 1, "current": 0, "formula": "dp[1][0]=0", "dp_contract": contract}, reason="起点为 0，初始状态只访问起点。", code_line=1)
    for mask in range(full):
        for u in range(n):
            if dp[mask][u] >= inf:
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                next_mask = mask | (1 << v)
                before = dp[next_mask][v]
                dp[next_mask][v] = min(dp[next_mask][v], dp[mask][u] + dist[u][v])
                tracer.set(f"dp[{next_mask}][{v}]", value=dp[next_mask][v], before=before, deps=[f"dp[{mask}][{u}]", f"dist[{u}][{v}]"], state={"dist": [row[:] for row in dist], "dp": [row[:] for row in dp], "mask": next_mask, "current": v, "formula": "dp[next_mask][v]=min(dp[next_mask][v], dp[mask][u]+dist[u][v])", "dp_contract": contract}, role="current", reason="把未访问节点加入 bitmask，更新停在该节点的最短代价。", code_line=11)
    answer = min(dp[full - 1][u] + dist[u][0] for u in range(n))
    tracer.mark(f"dp[{full - 1}][0]", value=answer, deps=[f"dp[{full - 1}][{u}]" for u in range(n)], state={"dist": [row[:] for row in dist], "dp": [row[:] for row in dp], "mask": full - 1, "current": 0, "answer": answer, "formula": "answer=min(dp[full-1][u]+dist[u][0])", "dp_contract": contract}, role="answer", reason="所有点访问后回到起点，取最小闭环代价。", code_line=15)
    tracer.result(answer)
    return tracer.to_trace()
"""


STATE_COMPRESSION_TSP_VERIFIER = """
def verify(input_data):
    dist = input_data["dist"]
    n = len(dist)
    best = 10 ** 9
    def dfs(path, used, cost):
        nonlocal best
        if len(path) == n:
            best = min(best, cost + dist[path[-1]][0])
            return
        for v in range(1, n):
            if not (used & (1 << v)):
                dfs(path + [v], used | (1 << v), cost + dist[path[-1]][v])
    dfs([0], 1, 0)
    return best
"""


DIGIT_DP_NO_SEVEN_CODE = """
def solve(input_data):
    n = input_data["n"]
    return sum(1 for value in range(1, n + 1) if "7" not in str(value))
"""


DIGIT_DP_NO_SEVEN_TRACKER = """
def trace(input_data):
    n = input_data["n"]
    digits = [int(ch) for ch in str(n)]
    dp = [1] + [0] * len(digits)
    contract = {"containers": ["dp"], "answer_position": f"dp[{len(digits)}]", "expected_targets": [f"dp[{i}]" for i in range(1, len(digits) + 1)], "subfamily": "digit_dp"}
    tracer = Tracer(input_data, algorithm="数位 DP 统计不含 7 的数字", pseudocode=["逐位处理 n 的前缀", "统计 1..prefix 中不含数字 7 的数量"], policy="full", max_events=160)
    tracer.expect_updates("dp", len(contract["expected_targets"]))
    tracer.create("dp", state={"n": n, "digits": digits[:], "dp": dp[:], "digit": 0, "forbidden_digit": 7, "count_range": "1_to_n", "formula": "dp[0]=1", "dp_contract": contract}, reason="初始化数位 DP 前缀计数。", code_line=1)
    prefix = 0
    for index, digit in enumerate(digits):
        prefix = prefix * 10 + digit
        before = dp[index + 1]
        dp[index + 1] = sum(1 for value in range(1, prefix + 1) if "7" not in str(value))
        tracer.set(f"dp[{index + 1}]", value=dp[index + 1], before=before, deps=[f"dp[{index}]", f"digits[{index}]"], state={"n": n, "digits": digits[:], "dp": dp[:], "digit": index + 1, "forbidden_digit": 7, "count_range": "1_to_n", "formula": "dp[pos]=count(1..prefix without forbidden digit)", "dp_contract": contract}, role="current", reason="处理当前前缀，统计不含数字 7 的合法正整数个数。", code_line=6)
    answer = dp[len(digits)]
    tracer.mark(f"dp[{len(digits)}]", value=answer, deps=[f"dp[{len(digits)}]"], state={"n": n, "digits": digits[:], "dp": dp[:], "digit": len(digits), "forbidden_digit": 7, "count_range": "1_to_n", "answer": answer, "formula": "answer=dp[len(digits)]", "dp_contract": contract}, role="answer", reason="完整 n 前缀对应的计数就是答案。", code_line=8)
    tracer.result(answer)
    return tracer.to_trace()
"""


DIGIT_DP_NO_SEVEN_VERIFIER = """
def verify(input_data):
    n = input_data["n"]
    total = 0
    for value in range(1, n + 1):
        if "7" not in str(value):
            total += 1
    return total
"""


def cases() -> tuple[BenchmarkCase, ...]:
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
            id="knapsack_01_subset_sum",
            title="0-1 背包等和划分",
            problem="给定正整数数组 nums，判断能否把数组划分成两个元素和相等的子集。",
            family="DP 核心扩展",
            input_contract="输入正整数 nums 数组。",
            variant_name="0-1 背包可达性",
            strategy="把目标设为总和一半，逆序容量更新 dp[c]，确保每个数只用一次。",
            time_complexity="O(n * target)",
            space_complexity="O(target)",
            expected_layouts=("array",),
            code=KNAPSACK_01_SUBSET_SUM_CODE,
            tracker_code=KNAPSACK_01_SUBSET_SUM_TRACKER,
            verifier_code=KNAPSACK_01_SUBSET_SUM_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 5, 11, 5]}, True),
                BenchmarkInput({"nums": [1, 2, 3, 5]}, False),
                BenchmarkInput({"nums": [2, 2, 3, 5]}, False),
                BenchmarkInput({"nums": [3, 3, 3, 4, 5]}, True),
            ),
        ),
        BenchmarkCase(
            id="complete_knapsack_coin_change",
            title="完全背包零钱兑换",
            problem="给定硬币面额 coins 和金额 amount，每种硬币可无限使用，返回凑成 amount 的最少硬币数，不可达返回 -1。",
            family="DP 核心扩展",
            input_contract="输入 coins 数组和 amount。",
            variant_name="完全背包最少硬币",
            strategy="正序容量更新 dp[c]，允许同一种硬币被重复使用。",
            time_complexity="O(len(coins) * amount)",
            space_complexity="O(amount)",
            expected_layouts=("array",),
            code=COMPLETE_KNAPSACK_COIN_CHANGE_CODE,
            tracker_code=COMPLETE_KNAPSACK_COIN_CHANGE_TRACKER,
            verifier_code=COMPLETE_KNAPSACK_COIN_CHANGE_VERIFIER,
            samples=(
                BenchmarkInput({"coins": [1, 2, 5], "amount": 11}, 3),
                BenchmarkInput({"coins": [2], "amount": 3}, -1),
                BenchmarkInput({"coins": [1], "amount": 0}, 0),
                BenchmarkInput({"coins": [2, 3, 5], "amount": 7}, 2),
            ),
        ),
        BenchmarkCase(
            id="bounded_knapsack_max_value",
            title="多重背包最大价值",
            problem="给定 weights、values、counts 和容量 capacity，每种物品最多 counts[i] 件，返回容量内最大价值。",
            family="DP 核心扩展",
            input_contract="输入 weights、values、counts 和 capacity。",
            variant_name="多重背包基础枚举",
            strategy="每种物品基于上一层 dp 枚举可取数量 k，且 k 不能超过 counts[i]。",
            time_complexity="O(n * capacity * max_count)",
            space_complexity="O(capacity)",
            expected_layouts=("array",),
            code=BOUNDED_KNAPSACK_MAX_VALUE_CODE,
            tracker_code=BOUNDED_KNAPSACK_MAX_VALUE_TRACKER,
            verifier_code=BOUNDED_KNAPSACK_MAX_VALUE_VERIFIER,
            samples=(
                BenchmarkInput({"weights": [2, 3], "values": [3, 4], "counts": [2, 1], "capacity": 5}, 7),
                BenchmarkInput({"weights": [2], "values": [3], "counts": [2], "capacity": 5}, 6),
                BenchmarkInput({"weights": [4, 5], "values": [6, 7], "counts": [1, 1], "capacity": 3}, 0),
                BenchmarkInput({"weights": [1, 3], "values": [2, 5], "counts": [3, 2], "capacity": 6}, 11),
            ),
        ),
        BenchmarkCase(
            id="lcs_length",
            title="最长公共子序列长度",
            problem="给定 text1 和 text2，返回它们最长公共子序列的长度。",
            family="DP 核心扩展",
            input_contract="输入 text1 和 text2 字符串。",
            variant_name="LCS 二维 DP",
            strategy="相等字符来自左上角加一，不等时取上方和左方最大值。",
            time_complexity="O(mn)",
            space_complexity="O(mn)",
            expected_layouts=("matrix",),
            code=LCS_LENGTH_CODE,
            tracker_code=LCS_LENGTH_TRACKER,
            verifier_code=LCS_LENGTH_VERIFIER,
            samples=(
                BenchmarkInput({"text1": "abcde", "text2": "ace"}, 3),
                BenchmarkInput({"text1": "abc", "text2": "abc"}, 3),
                BenchmarkInput({"text1": "abc", "text2": "def"}, 0),
                BenchmarkInput({"text1": "bsbininm", "text2": "jmjkbkjkv"}, 1),
            ),
        ),
        BenchmarkCase(
            id="edit_distance",
            title="编辑距离",
            problem="给定 word1 和 word2，返回把 word1 转换成 word2 所需的最少插入、删除、替换次数。",
            family="DP 核心扩展",
            input_contract="输入 word1 和 word2 字符串。",
            variant_name="编辑距离二维 DP",
            strategy="相等字符继承左上角，否则从删除、插入、替换三种操作中取最小值加一。",
            time_complexity="O(mn)",
            space_complexity="O(mn)",
            expected_layouts=("matrix",),
            code=EDIT_DISTANCE_CODE,
            tracker_code=EDIT_DISTANCE_TRACKER,
            verifier_code=EDIT_DISTANCE_VERIFIER,
            samples=(
                BenchmarkInput({"word1": "horse", "word2": "ros"}, 3),
                BenchmarkInput({"word1": "intention", "word2": "execution"}, 5),
                BenchmarkInput({"word1": "", "word2": "abc"}, 3),
                BenchmarkInput({"word1": "abc", "word2": "abc"}, 0),
            ),
        ),
        BenchmarkCase(
            id="interval_dp_merge_stones",
            title="区间 DP 合并石子",
            problem="给定石子堆数组 stones，每次合并相邻两段的代价为区间总和，返回合并成一堆的最小代价。",
            family="DP 核心扩展",
            input_contract="输入 stones 数组。",
            variant_name="按区间长度填表",
            strategy="dp[i][j] 枚举最后一次切分点 k，再加当前区间总和。",
            time_complexity="O(n^3)",
            space_complexity="O(n^2)",
            expected_layouts=("matrix",),
            code=INTERVAL_DP_MERGE_STONES_CODE,
            tracker_code=INTERVAL_DP_MERGE_STONES_TRACKER,
            verifier_code=INTERVAL_DP_MERGE_STONES_VERIFIER,
            samples=(
                BenchmarkInput({"stones": [3, 2, 4, 1]}, 20),
                BenchmarkInput({"stones": [1, 2]}, 3),
                BenchmarkInput({"stones": [5]}, 0),
                BenchmarkInput({"stones": [4, 1, 1]}, 8),
            ),
        ),
        BenchmarkCase(
            id="state_compression_tsp",
            title="状态压缩 DP 旅行回路",
            problem="给定小规模距离矩阵 dist，从 0 出发访问所有点并回到 0，返回最短回路长度。",
            family="DP 核心扩展",
            input_contract="输入 dist 方阵。",
            variant_name="bitmask TSP",
            strategy="dp[mask][u] 表示已访问集合 mask 且停在 u 的最短路径，枚举未访问点扩展 mask。",
            time_complexity="O(n^2 2^n)",
            space_complexity="O(n 2^n)",
            expected_layouts=("matrix",),
            code=STATE_COMPRESSION_TSP_CODE,
            tracker_code=STATE_COMPRESSION_TSP_TRACKER,
            verifier_code=STATE_COMPRESSION_TSP_VERIFIER,
            samples=(
                BenchmarkInput({"dist": [[0, 1, 15], [1, 0, 2], [15, 2, 0]]}, 18),
                BenchmarkInput({"dist": [[0, 4, 1], [4, 0, 2], [1, 2, 0]]}, 7),
                BenchmarkInput({"dist": [[0, 5], [5, 0]]}, 10),
                BenchmarkInput({"dist": [[0, 2, 9], [2, 0, 6], [9, 6, 0]]}, 17),
            ),
        ),
        BenchmarkCase(
            id="digit_dp_no_seven",
            title="数位 DP 统计不含 7",
            problem=(
                "给定非负整数 n，统计闭区间 1..n 中十进制表示不包含数字 7 的正整数个数。"
                "注意 0 不是正整数，不能计入答案；例如 n=20 时只排除 7 和 17，答案是 18。"
            ),
            family="DP 核心扩展",
            input_contract="输入非负整数 n；输出只统计 1..n 的正整数个数，不统计 0。",
            variant_name="数位 DP 入门",
            strategy="逐位处理 n 的前缀，维护当前前缀范围内不含禁用数字的正整数计数；不要把 0 算入答案。",
            time_complexity="O(d * 10)",
            space_complexity="O(d)",
            expected_layouts=("array",),
            code=DIGIT_DP_NO_SEVEN_CODE,
            tracker_code=DIGIT_DP_NO_SEVEN_TRACKER,
            verifier_code=DIGIT_DP_NO_SEVEN_VERIFIER,
            samples=(
                BenchmarkInput({"n": 20}, 18),
                BenchmarkInput({"n": 7}, 6),
                BenchmarkInput({"n": 100}, 81),
                BenchmarkInput({"n": 0}, 0),
            ),
        ),
    )
