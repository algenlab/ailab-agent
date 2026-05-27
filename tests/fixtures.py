"""Deterministic artifacts used by offline tests."""

from __future__ import annotations

from algolab.compiler.scene_compiler import compile_scene
from algolab.schemas.semantic_trace import SemanticTrace, TeachingStep
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport


def house_robber_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "打家劫舍",
            "input_data": {"nums": [2, 7, 9, 3, 1]},
            "result": 12,
            "pseudocode": [
                "初始化 dp 数组",
                "dp[i] = max(dp[i-1], dp[i-2] + nums[i])",
                "返回 dp[n-1]",
            ],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}, {"id": "dp"}],
                    "state": {"nums": [2, 7, 9, 3, 1], "dp": [2, 7, 0, 0, 0]},
                    "role": "current",
                    "reason": "创建房屋金额数组和 DP 数组。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "dp[2]"}],
                    "deps": [{"id": "dp[1]"}, {"id": "dp[0]"}, {"id": "nums[2]"}],
                    "state": {"nums": [2, 7, 9, 3, 1], "dp": [2, 7, 0, 0, 0]},
                    "role": "current",
                    "reason": "比较不偷第 2 间与偷第 2 间的收益。",
                    "code_line": 2,
                    "interaction": {
                        "type": "choice",
                        "prompt": "dp[2] 应该是多少？",
                        "options": ["9", "11", "12"],
                        "answer": "11",
                        "explanation": "max(7, 2 + 9) = 11。",
                    },
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "dp[2]"}],
                    "deps": [{"id": "dp[1]"}, {"id": "dp[0]"}, {"id": "nums[2]"}],
                    "before": 0,
                    "after": 11,
                    "state": {"nums": [2, 7, 9, 3, 1], "dp": [2, 7, 11, 0, 0]},
                    "role": "answer",
                    "reason": "更新 dp[2] 为 11。",
                    "code_line": 2,
                },
            ],
        }
    )


def bfs_trace() -> SemanticTrace:
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BFS",
            "input_data": {"graph": graph, "start": "A"},
            "result": {"A": 0, "B": 1, "C": 1, "D": 2},
            "pseudocode": ["queue <- start", "pop current", "visit neighbors"],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "queue"}, {"id": "node:A"}],
                    "state": {"graph": graph, "queue": ["A"], "dist": {"A": 0}},
                    "role": "current",
                    "reason": "初始化队列和起点距离。",
                    "code_line": 1,
                    "teaching": {
                        "what": "起点入队",
                        "why": "BFS 从起点按层扩展，起点距离为 0。",
                        "formula": "dist[start] = 0",
                        "invariant": "队列中节点按距离非递减顺序等待处理。",
                        "hint": "观察 queue 与 dist 表。",
                    },
                },
                {
                    "step": 1,
                    "op": "pop",
                    "targets": [{"id": "queue"}, {"id": "node:A"}],
                    "state": {"graph": graph, "queue": [], "dist": {"A": 0}},
                    "role": "current",
                    "reason": "弹出 A 并检查邻居。",
                    "code_line": 2,
                    "teaching": {
                        "what": "弹出当前节点 A",
                        "why": "弹出队首后检查它的所有邻居。",
                        "formula": "current = queue.pop(0)",
                        "invariant": "弹出的节点已经拥有最短距离。",
                        "hint": "下一步首次发现的邻居依赖 A。",
                    },
                },
                {
                    "step": 2,
                    "op": "mark",
                    "targets": [{"id": "node:B"}, {"id": "node:C"}],
                    "deps": [{"id": "node:A"}, {"id": "edge:A->B"}, {"id": "edge:A->C"}],
                    "state": {"graph": graph, "queue": ["B", "C"], "dist": {"A": 0, "B": 1, "C": 1}},
                    "role": "visited",
                    "reason": "首次发现 B 和 C。",
                    "code_line": 3,
                    "teaching": {
                        "what": "首次发现 B 和 C",
                        "why": "它们由 A 扩展得到，第一次访问时距离最短。",
                        "formula": "dist[v] = dist[A] + 1",
                        "invariant": "未访问节点第一次入队时确定最短层数。",
                        "hint": "依赖边从 A 指向新发现节点。",
                    },
                    "interaction": {
                        "type": "choice",
                        "prompt": "从 A 首次发现的节点距离应该是多少？",
                        "options": ["0", "1", "2"],
                        "answer": "1",
                        "explanation": "B 和 C 由距离为 0 的 A 扩展得到，所以距离是 1。",
                    },
                },
                {
                    "step": 3,
                    "op": "mark",
                    "targets": [{"id": "node:D"}],
                    "deps": [{"id": "node:B"}, {"id": "edge:B->D"}],
                    "state": {"graph": graph, "queue": ["C", "D"], "dist": {"A": 0, "B": 1, "C": 1, "D": 2}},
                    "role": "visited",
                    "reason": "从 B 首次发现 D。",
                    "code_line": 3,
                    "teaching": {
                        "what": "首次发现 D",
                        "why": "D 由距离为 1 的 B 扩展得到，所以距离为 2。",
                        "formula": "dist[D] = dist[B] + 1",
                        "invariant": "节点首次访问即得到最短距离。",
                        "hint": "队列保留后续待处理节点。",
                    },
                },
            ],
        }
    )


def dfs_trace() -> SemanticTrace:
    graph = {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "DFS 图遍历",
            "input_data": {"graph": graph, "start": "A"},
            "result": ["A", "B", "D", "C"],
            "pseudocode": ["进入节点", "递归访问未访问邻居", "回溯"],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "node:A"}],
                    "state": {"graph": graph, "stack": ["A"], "visited": {"A": True}},
                    "role": "current",
                    "reason": "从起点 A 开始深度优先搜索。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "enter",
                    "targets": [{"id": "node:B"}, {"id": "stack"}],
                    "deps": [{"id": "node:A"}],
                    "state": {"graph": graph, "stack": ["A", "B"], "visited": {"A": True, "B": True}},
                    "role": "current",
                    "reason": "沿 A 到 B 的边进入下一层。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "exit",
                    "targets": [{"id": "node:B"}, {"id": "stack"}],
                    "state": {"graph": graph, "stack": ["A"], "visited": {"A": True, "B": True, "D": True}},
                    "role": "visited",
                    "reason": "B 的分支处理完成，回溯到 A。",
                    "code_line": 3,
                },
            ],
        }
    )


def two_pointer_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "双指针两数之和",
            "input_data": {"nums": [1, 2, 4, 6, 8], "target": 10},
            "result": [1, 4],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}, {"id": "pointer:left"}, {"id": "pointer:right"}],
                    "value": [0, 4],
                    "state": {"nums": [1, 2, 4, 6, 8], "left": 0, "right": 4, "target": 10},
                    "reason": "在有序数组两端放置左右指针。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "nums[0]"}, {"id": "nums[4]"}],
                    "state": {"nums": [1, 2, 4, 6, 8], "left": 0, "right": 4, "target": 10},
                    "role": "candidate",
                    "reason": "比较 nums[left] + nums[right] 与 target。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}],
                    "value": [1, 4],
                    "state": {"nums": [1, 2, 4, 6, 8], "left": 1, "right": 4, "target": 10},
                    "role": "current",
                    "reason": "当前和太小，左指针右移。",
                    "code_line": 3,
                },
            ],
        }
    )


def binary_search_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分查找",
            "input_data": {"nums": [-1, 0, 3, 5, 9, 12], "target": 9},
            "result": 4,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [-1, 0, 3, 5, 9, 12], "left": 0, "right": 5, "target": 9},
                    "reason": "在有序数组上建立二分区间。",
                    "code_line": 1,
                    "teaching": {
                        "what": "初始化闭区间",
                        "why": "目标如果存在，一定在当前 [left, right] 内。",
                        "formula": "[left, right] = [0, n - 1]",
                        "invariant": "搜索区间始终包含所有可能答案。",
                        "hint": "观察 left 和 right 指针。",
                    },
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "nums[2]"}, {"id": "pointer:mid"}],
                    "value": 2,
                    "deps": [{"id": "pointer:left"}, {"id": "pointer:right"}],
                    "state": {"nums": [-1, 0, 3, 5, 9, 12], "left": 0, "right": 5, "mid": 2, "target": 9},
                    "role": "candidate",
                    "reason": "比较中点 3 与目标 9。",
                    "code_line": 2,
                    "teaching": {
                        "what": "比较中点 nums[2]",
                        "why": "中点值 3 小于目标 9，左半边都不可能是答案。",
                        "formula": "mid = (left + right) // 2",
                        "invariant": "数组有序使得一次比较能排除一半区间。",
                        "hint": "mid 来自 left 与 right。",
                    },
                },
                {
                    "step": 2,
                    "op": "move",
                    "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}],
                    "value": [3, 5],
                    "deps": [{"id": "nums[2]"}, {"id": "pointer:mid"}],
                    "state": {"nums": [-1, 0, 3, 5, 9, 12], "left": 3, "right": 5, "target": 9},
                    "role": "current",
                    "reason": "目标更大，搜索区间移动到右半边。",
                    "code_line": 3,
                    "teaching": {
                        "what": "收缩到右半区间",
                        "why": "nums[mid] < target，所以更新 left = mid + 1。",
                        "formula": "left = mid + 1",
                        "invariant": "新区间仍覆盖所有可能答案。",
                        "hint": "左侧区间被排除。",
                    },
                    "interaction": {
                        "type": "choice",
                        "prompt": "nums[mid] < target 时下一步应该移动哪个边界？",
                        "options": ["left = mid + 1", "right = mid - 1", "返回 mid"],
                        "answer": "left = mid + 1",
                        "explanation": "中点值偏小，左侧和中点都可以排除。",
                    },
                },
                {
                    "step": 3,
                    "op": "compare",
                    "targets": [{"id": "nums[4]"}, {"id": "pointer:mid"}],
                    "value": 4,
                    "deps": [{"id": "pointer:left"}, {"id": "pointer:right"}],
                    "state": {"nums": [-1, 0, 3, 5, 9, 12], "left": 3, "right": 5, "mid": 4, "target": 9},
                    "role": "answer",
                    "reason": "中点值 9 命中目标。",
                    "code_line": 2,
                    "teaching": {
                        "what": "命中目标",
                        "why": "nums[4] 等于 target，返回当前下标。",
                        "formula": "nums[mid] == target",
                        "invariant": "返回的下标来自仍然有效的搜索区间。",
                        "hint": "当前 mid 就是答案。",
                    },
                },
            ],
        }
    )


def sliding_window_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "最短子数组滑动窗口",
            "input_data": {"nums": [2, 3, 1, 2, 4, 3], "target": 7},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [2, 3, 1, 2, 4, 3], "left": 0, "right": 0, "sum": 0, "target": 7},
                    "reason": "初始化窗口左右边界。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "move",
                    "targets": [{"id": "pointer:right"}],
                    "value": 4,
                    "state": {"nums": [2, 3, 1, 2, 4, 3], "left": 0, "right": 4, "sum": 12, "target": 7},
                    "role": "current",
                    "reason": "右边界扩张直到窗口和达到目标。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "move",
                    "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}],
                    "value": [3, 4],
                    "state": {"nums": [2, 3, 1, 2, 4, 3], "left": 3, "right": 4, "sum": 6, "best": 2},
                    "role": "answer",
                    "reason": "持续收缩左边界，得到长度为 2 的候选窗口。",
                    "code_line": 3,
                },
            ],
        }
    )


def unique_paths_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "不同路径二维 DP",
            "input_data": {"m": 3, "n": 7},
            "result": 28,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [[1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0]]},
                    "reason": "第一行和第一列只有一种到达方式。",
                    "code_line": 1,
                    "teaching": {
                        "what": "初始化 DP 表",
                        "why": "第一行和第一列只有一种走法。",
                        "formula": "dp[0][j] = dp[i][0] = 1",
                        "invariant": "已经初始化的边界格子是正确的。",
                        "hint": "内部格子稍后由上方和左侧推出。",
                    },
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "dp[1][1]"}],
                    "deps": [{"id": "dp[0][1]"}, {"id": "dp[1][0]"}],
                    "state": {"dp": [[1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0]]},
                    "role": "candidate",
                    "reason": "当前位置依赖上方和左侧。",
                    "code_line": 2,
                    "teaching": {
                        "what": "查看 dp[1][1] 的依赖",
                        "why": "机器人只能从上方或左方到达当前格。",
                        "formula": "dp[i][j] = dp[i-1][j] + dp[i][j-1]",
                        "invariant": "处理当前格时，上方和左侧已经正确。",
                        "hint": "两个依赖格会指向当前格。",
                    },
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "dp[1][1]"}],
                    "deps": [{"id": "dp[0][1]"}, {"id": "dp[1][0]"}],
                    "before": 0,
                    "after": 2,
                    "state": {"dp": [[1, 1, 1, 1, 1, 1, 1], [1, 2, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0]]},
                    "role": "answer",
                    "reason": "dp[1][1] = 1 + 1 = 2。",
                    "code_line": 2,
                    "teaching": {
                        "what": "写入 dp[1][1]",
                        "why": "当前路径数等于上方和左方路径数之和。",
                        "formula": "dp[1][1] = 1 + 1 = 2",
                        "invariant": "写入后 dp[1][1] 也成为后续格子的可信依赖。",
                        "hint": "观察状态变化摘要。",
                    },
                    "interaction": {
                        "type": "input",
                        "prompt": "请填写 dp[1][1] 的值。",
                        "answer": "2",
                        "explanation": "dp[1][1] = dp[0][1] + dp[1][0] = 1 + 1 = 2。",
                    },
                },
                {
                    "step": 3,
                    "op": "set",
                    "targets": [{"id": "dp[2][6]"}],
                    "deps": [{"id": "dp[1][6]"}, {"id": "dp[2][5]"}],
                    "before": 0,
                    "after": 28,
                    "state": {"dp": [[1, 1, 1, 1, 1, 1, 1], [1, 2, 3, 4, 5, 6, 7], [1, 3, 6, 10, 15, 21, 28]]},
                    "role": "answer",
                    "reason": "最后一个格子由上方 7 和左方 21 得到 28。",
                    "code_line": 2,
                    "teaching": {
                        "what": "得到右下角答案",
                        "why": "右下角路径数就是整个网格的路径总数。",
                        "formula": "dp[2][6] = 7 + 21 = 28",
                        "invariant": "所有内部格都按同一转移公式计算。",
                        "hint": "答案来自右下角单元。",
                    },
                },
            ],
        }
    )


def hash_map_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "哈希表 Two Sum",
            "input_data": {"nums": [2, 7, 11, 15], "target": 9},
            "result": [0, 1],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "seen"}],
                    "state": {"nums": [2, 7, 11, 15], "seen": {}, "target": 9},
                    "reason": "创建哈希表记录已访问值。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "seen[2]"}],
                    "state": {"nums": [2, 7, 11, 15], "seen": {"2": 0}, "target": 9},
                    "role": "current",
                    "reason": "记录数值 2 的下标。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "compare",
                    "targets": [{"id": "nums[1]"}, {"id": "seen[2]"}],
                    "state": {"nums": [2, 7, 11, 15], "seen": {"2": 0}, "target": 9},
                    "role": "answer",
                    "reason": "7 的补数 2 已经出现，得到答案。",
                    "code_line": 3,
                },
            ],
        }
    )


def monotonic_stack_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "每日温度单调栈",
            "input_data": {"temperatures": [73, 74, 75, 71, 69, 72, 76, 73]},
            "result": [1, 1, 4, 2, 1, 1, 0, 0],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "temperatures"}, {"id": "stack"}, {"id": "answer"}],
                    "state": {"temperatures": [73, 74, 75, 71, 69, 72, 76, 73], "stack": [], "answer": [0, 0, 0, 0, 0, 0, 0, 0]},
                    "reason": "栈中保存还没找到更高温度的下标。",
                    "code_line": 1,
                    "teaching": {
                        "what": "初始化单调栈",
                        "why": "栈保存尚未找到更高温度的下标。",
                        "formula": "answer[i] = 0 until resolved",
                        "invariant": "栈内下标对应温度保持单调递减。",
                        "hint": "数组、栈和答案会联动变化。",
                    },
                },
                {
                    "step": 1,
                    "op": "push",
                    "targets": [{"id": "stack"}],
                    "deps": [{"id": "temperatures[0]"}],
                    "state": {"temperatures": [73, 74, 75, 71, 69, 72, 76, 73], "stack": [0], "answer": [0, 0, 0, 0, 0, 0, 0, 0]},
                    "role": "current",
                    "reason": "下标 0 入栈等待更高温度。",
                    "code_line": 2,
                    "teaching": {
                        "what": "下标 0 入栈",
                        "why": "还没有遇到比 73 更高的温度。",
                        "formula": "stack.push(0)",
                        "invariant": "栈中下标仍等待答案。",
                        "hint": "栈元素引用原数组下标。",
                    },
                },
                {
                    "step": 2,
                    "op": "pop",
                    "targets": [{"id": "stack"}, {"id": "answer[0]"}, {"id": "temperatures[1]"}],
                    "deps": [{"id": "temperatures[0]"}, {"id": "temperatures[1]"}],
                    "before": 0,
                    "after": 1,
                    "state": {"temperatures": [73, 74, 75, 71, 69, 72, 76, 73], "stack": [], "answer": [1, 0, 0, 0, 0, 0, 0, 0]},
                    "role": "answer",
                    "reason": "74 高于 73，下标 0 等待 1 天。",
                    "code_line": 3,
                    "teaching": {
                        "what": "弹出并写 answer[0]",
                        "why": "当前温度 74 是下标 0 之后第一个更高温度。",
                        "formula": "answer[0] = 1 - 0 = 1",
                        "invariant": "被弹出的下标已经找到最近更高温度。",
                        "hint": "answer 更新依赖两个温度单元。",
                    },
                    "interaction": {
                        "type": "judge",
                        "prompt": "遇到 74 时可以弹出下标 0 吗？",
                        "answer": True,
                        "explanation": "74 高于 73，下标 0 已经找到第一个更高温度。",
                    },
                },
                {
                    "step": 3,
                    "op": "push",
                    "targets": [{"id": "stack"}],
                    "deps": [{"id": "temperatures[1]"}],
                    "state": {"temperatures": [73, 74, 75, 71, 69, 72, 76, 73], "stack": [1], "answer": [1, 0, 0, 0, 0, 0, 0, 0]},
                    "role": "current",
                    "reason": "下标 1 入栈等待更高温度。",
                    "code_line": 4,
                    "teaching": {
                        "what": "下标 1 入栈",
                        "why": "74 还需要等待后续更高温度。",
                        "formula": "stack.push(1)",
                        "invariant": "栈内仍保持单调递减候选。",
                        "hint": "继续扫描右侧温度。",
                    },
                },
            ],
        }
    )


def queue_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "队列先进先出",
            "input_data": {"items": ["A", "B", "C"]},
            "result": ["A", "B", "C"],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "queue"}],
                    "state": {"queue": []},
                    "reason": "创建队列容器。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "push",
                    "targets": [{"id": "queue"}],
                    "state": {"queue": ["A", "B", "C"]},
                    "role": "current",
                    "reason": "元素按到达顺序进入队尾。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "pop",
                    "targets": [{"id": "queue[0]"}],
                    "state": {"queue": ["B", "C"]},
                    "role": "answer",
                    "reason": "队首 A 最先出队。",
                    "code_line": 3,
                },
            ],
        }
    )


def sorting_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "快速排序分区",
            "input_data": {"nums": [4, 2, 5, 1]},
            "result": [1, 2, 4, 5],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [4, 2, 5, 1], "pivot": 4, "i": 0, "j": 3},
                    "reason": "选择首元素作为 pivot。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "nums[0]"}, {"id": "nums[3]"}],
                    "state": {"nums": [4, 2, 5, 1], "pivot": 4, "i": 0, "j": 3},
                    "role": "candidate",
                    "reason": "从右侧寻找小于 pivot 的元素。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1, 2, 4, 5], "pivot": 4, "i": 2, "j": 2},
                    "role": "answer",
                    "reason": "分区完成，pivot 左侧都不大于它。",
                    "code_line": 3,
                },
            ],
        }
    )


def tree_trace() -> SemanticTrace:
    tree = {
        "nodes": [{"id": "4"}, {"id": "2"}, {"id": "7"}, {"id": "1"}, {"id": "3"}],
        "edges": [["4", "2"], ["4", "7"], ["2", "1"], ["2", "3"]],
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二叉树中序遍历",
            "input_data": {"tree": tree},
            "result": [1, 2, 3, 4, 7],
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "tree"}], "state": {"tree": tree}, "reason": "展示二叉树结构。", "code_line": 1},
                {"step": 1, "op": "mark", "targets": [{"id": "node:2"}], "state": {"tree": tree}, "role": "current", "reason": "递归进入左子树。", "code_line": 2},
            ],
        }
    )


def bst_lca_trace() -> SemanticTrace:
    tree = {
        "nodes": [{"id": "6"}, {"id": "2"}, {"id": "8"}, {"id": "0"}, {"id": "4"}, {"id": "3"}, {"id": "5"}],
        "edges": [["6", "2"], ["6", "8"], ["2", "0"], ["2", "4"], ["4", "3"], ["4", "5"]],
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BST 最近公共祖先",
            "input_data": {"p": 2, "q": 8, "tree": tree},
            "result": 6,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "tree"}],
                    "state": {"tree": tree, "p": 2, "q": 8},
                    "reason": "展示 BST 结构与两个目标节点。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "node:6"}],
                    "deps": [{"id": "node:2"}, {"id": "node:8"}],
                    "state": {"tree": tree, "p": 2, "q": 8},
                    "role": "answer",
                    "reason": "2 在左侧，8 在右侧，当前根 6 就是 LCA。",
                    "code_line": 2,
                },
            ],
        }
    )


def heap_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "堆顶弹出",
            "input_data": {"heap": [1, 3, 5, 7, 9, 8]},
            "result": 1,
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "heap"}], "state": {"heap": [1, 3, 5, 7, 9, 8]}, "reason": "最小堆按层展示。", "code_line": 1},
                {"step": 1, "op": "pop", "targets": [{"id": "heap[0]"}], "state": {"heap": [3, 7, 5, 8, 9]}, "role": "current", "reason": "弹出堆顶并下沉调整。", "code_line": 2},
            ],
        }
    )


def topk_heap_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "TopK 小顶堆",
            "input_data": {"nums": [5, 1, 9, 3, 7], "k": 3},
            "result": [9, 7, 5],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "heap"}],
                    "state": {"nums": [5, 1, 9, 3, 7], "heap": []},
                    "reason": "维护大小为 k 的小顶堆。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "push",
                    "targets": [{"id": "heap"}],
                    "state": {"nums": [5, 1, 9, 3, 7], "heap": [1, 5, 9]},
                    "role": "current",
                    "reason": "前三个元素进入堆。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "heap[0]"}],
                    "state": {"nums": [5, 1, 9, 3, 7], "heap": [5, 7, 9]},
                    "role": "answer",
                    "reason": "遇到 7 后替换堆顶 1，堆中保留前三大元素。",
                    "code_line": 3,
                },
            ],
        }
    )


def huffman_trace() -> SemanticTrace:
    tree = {
        "nodes": [{"id": "ab", "label": "5"}, {"id": "a", "label": "2"}, {"id": "b", "label": "3"}],
        "edges": [{"from": "ab", "to": "a", "label": "0"}, {"from": "ab", "to": "b", "label": "1"}],
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Huffman 合并",
            "input_data": {"freq": {"a": 2, "b": 3, "c": 7}},
            "result": {"ab": 5},
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "heap"}],
                    "state": {"heap": [2, 3, 7]},
                    "reason": "把频率放入最小堆。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "link",
                    "targets": [{"id": "tree"}],
                    "state": {"tree": tree, "heap": [5, 7]},
                    "role": "current",
                    "reason": "弹出两个最小权重 2 和 3，合并成权重 5 的父节点。",
                    "code_line": 2,
                },
            ],
        }
    )


def trie_trace() -> SemanticTrace:
    trie = {
        "nodes": [{"id": "root", "label": "root"}, {"id": "a"}, {"id": "ap"}, {"id": "app"}],
        "edges": [["root", "a"], ["a", "ap"], ["ap", "app"]],
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Trie 插入",
            "input_data": {"word": "app"},
            "result": True,
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "trie"}], "state": {"trie": trie}, "reason": "按字符逐层建立前缀树。", "code_line": 1},
                {"step": 1, "op": "mark", "targets": [{"id": "node:app"}], "state": {"trie": trie}, "role": "answer", "reason": "单词 app 结束节点。", "code_line": 2},
            ],
        }
    )


def trie_search_trace() -> SemanticTrace:
    trie = {
        "nodes": [
            {"id": "root", "label": "root"},
            {"id": "a", "label": "a"},
            {"id": "ap", "label": "p"},
            {"id": "app", "label": "p*"},
            {"id": "apl", "label": "l"},
        ],
        "edges": [["root", "a"], ["a", "ap"], ["ap", "app"], ["ap", "apl"]],
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Trie 前缀查询",
            "input_data": {"prefix": "ap"},
            "result": True,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "trie"}],
                    "state": {"trie": trie},
                    "reason": "展示已经建立好的前缀树。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "mark",
                    "targets": [{"id": "node:ap"}],
                    "state": {"trie": trie, "prefix": "ap"},
                    "role": "answer",
                    "reason": "沿字符 a、p 走到前缀终点，说明前缀存在。",
                    "code_line": 2,
                },
            ],
        }
    )


def union_find_trace() -> SemanticTrace:
    uf = {"parent": {"1": "1", "2": "1", "3": "3", "4": "3"}}
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "并查集合并",
            "input_data": {"edges": [[1, 2], [3, 4]]},
            "result": uf["parent"],
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "union_find"}], "state": {"union_find": uf}, "reason": "每个集合用父指针森林展示。", "code_line": 1},
                {"step": 1, "op": "link", "targets": [{"id": "node:2"}], "deps": [{"id": "node:1"}], "state": {"union_find": uf}, "role": "current", "reason": "将 2 合并到 1 的集合。", "code_line": 2},
            ],
        }
    )


def union_find_compression_trace() -> SemanticTrace:
    before = {"parent": {"1": "1", "2": "1", "3": "2", "4": "3"}}
    after = {"parent": {"1": "1", "2": "1", "3": "1", "4": "1"}}
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "并查集路径压缩",
            "input_data": {"query": [4, 1]},
            "result": True,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "union_find"}],
                    "state": {"union_find": before},
                    "reason": "展示压缩前的父指针链。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "node:4"}, {"id": "node:3"}],
                    "deps": [{"id": "node:1"}],
                    "state": {"union_find": after},
                    "role": "answer",
                    "reason": "查找根节点后，把路径上的节点直接连到根。",
                    "code_line": 2,
                },
            ],
        }
    )


def recursion_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "回溯全排列",
            "input_data": {"nums": [1, 2, 3]},
            "result": [[1, 2, 3]],
            "events": [
                {"step": 0, "op": "enter", "targets": [{"id": "frames"}], "state": {"stack": ["dfs([])"]}, "reason": "进入根递归帧。", "code_line": 1},
                {"step": 1, "op": "push", "targets": [{"id": "stack"}], "state": {"stack": ["dfs([])", "dfs([1])"]}, "role": "current", "reason": "选择 1，进入下一层。", "code_line": 2},
            ],
        }
    )


def recursion_tree_trace() -> SemanticTrace:
    search_tree = {
        "nodes": [
            {"id": "root", "label": "[]"},
            {"id": "choose1", "label": "[1]"},
            {"id": "choose12", "label": "[1,2]"},
            {"id": "choose13", "label": "[1,3]"},
        ],
        "edges": [["root", "choose1"], ["choose1", "choose12"], ["choose1", "choose13"]],
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "回溯搜索树",
            "input_data": {"nums": [1, 2, 3]},
            "result": [[1, 2, 3], [1, 3, 2]],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "recursion_tree"}],
                    "state": {"recursion_tree": search_tree, "stack": ["dfs([])"]},
                    "reason": "用搜索树展示回溯分支。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "mark",
                    "targets": [{"id": "node:choose12"}],
                    "deps": [{"id": "node:choose1"}],
                    "state": {"recursion_tree": search_tree, "stack": ["dfs([])", "dfs([1])", "dfs([1,2])"]},
                    "role": "current",
                    "reason": "选择 1 后继续选择 2，进入对应分支。",
                    "code_line": 2,
                },
            ],
        }
    )


def string_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "KMP 匹配",
            "input_data": {"text": "ababc", "pattern": "abc"},
            "result": 2,
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "text"}, {"id": "pattern"}], "state": {"text": "ababc", "pattern": "abc", "i": 0, "j": 0}, "reason": "展示文本串和模式串。", "code_line": 1},
                {"step": 1, "op": "compare", "targets": [{"id": "text[2]"}, {"id": "pattern[0]"}], "state": {"text": "ababc", "pattern": "abc", "i": 2, "j": 0}, "role": "candidate", "reason": "比较当前字符。", "code_line": 2},
            ],
        }
    )


def rabin_karp_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Rabin-Karp 滚动哈希",
            "input_data": {"text": "abcdef", "pattern": "cde"},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "text"}, {"id": "pattern"}],
                    "state": {"text": "abcdef", "pattern": "cde", "window_hash": 0, "pattern_hash": 42},
                    "reason": "把文本和模式按字符展示。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "text[2]"}, {"id": "text[3]"}, {"id": "text[4]"}],
                    "deps": [{"id": "pattern[0]"}, {"id": "pattern[1]"}, {"id": "pattern[2]"}],
                    "state": {"text": "abcdef", "pattern": "cde", "window_hash": 42, "pattern_hash": 42},
                    "role": "answer",
                    "reason": "窗口 cde 的哈希与模式哈希相等，再逐字符确认。",
                    "code_line": 2,
                },
            ],
        }
    )


def manacher_trace() -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Manacher 回文半径",
            "input_data": {"text": "ababa"},
            "result": 5,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "text"}, {"id": "radius"}],
                    "state": {"text": "#a#b#a#b#a#", "radius": [0, 1, 0, 3, 0, 5, 0, 3, 0, 1, 0]},
                    "reason": "插入分隔符后维护每个中心的回文半径。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "text[5]"}, {"id": "radius[5]"}],
                    "state": {"text": "#a#b#a#b#a#", "radius": [0, 1, 0, 3, 0, 5, 0, 3, 0, 1, 0], "center": 5, "right": 10},
                    "role": "answer",
                    "reason": "中心 5 的半径覆盖整个字符串，得到最长回文。",
                    "code_line": 2,
                },
            ],
        }
    )


def geometry_trace() -> SemanticTrace:
    geometry = {
        "points": [
            {"id": "0", "x": 0, "y": 0, "label": "0"},
            {"id": "1", "x": 1, "y": 1, "label": "1"},
            {"id": "2", "x": 2, "y": 0, "label": "2"},
            {"id": "3", "x": 1, "y": 2, "label": "3"},
        ],
        "hull": ["0", "2", "3"],
        "closed": True,
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "凸包扫描",
            "input_data": {"points": [[0, 0], [1, 1], [2, 0], [1, 2]]},
            "result": [[0, 0], [2, 0], [1, 2]],
            "events": [
                {"step": 0, "op": "create", "targets": [{"id": "geometry"}], "state": {"geometry": geometry}, "reason": "在坐标平面展示点集和当前凸包边。", "code_line": 1},
                {"step": 1, "op": "mark", "targets": [{"id": "point:3"}], "state": {"geometry": geometry}, "role": "current", "reason": "选择候选凸包点。", "code_line": 2},
            ],
        }
    )


def sweep_line_trace() -> SemanticTrace:
    geometry = {
        "points": [
            {"id": "a", "x": 0, "y": 1, "label": "a"},
            {"id": "b", "x": 4, "y": 1, "label": "b"},
            {"id": "c", "x": 2, "y": 0, "label": "c"},
            {"id": "d", "x": 2, "y": 3, "label": "d"},
        ],
        "segments": [{"from": "a", "to": "b"}, {"from": "c", "to": "d"}],
        "sweep_x": 2,
    }
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "扫描线线段相交",
            "input_data": {"segments": [[[0, 1], [4, 1]], [[2, 0], [2, 3]]]},
            "result": True,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "geometry"}],
                    "state": {"geometry": geometry},
                    "reason": "把线段放到坐标平面上。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "point:c"}, {"id": "point:d"}],
                    "state": {"geometry": geometry, "active": ["a-b"]},
                    "role": "answer",
                    "reason": "扫描线到 x=2 时，垂直线段与活动水平线段相交。",
                    "code_line": 2,
                },
            ],
        }
    )


def fixture_artifact() -> BuildArtifact:
    trace = house_robber_trace()
    scene = compile_scene(trace)
    return BuildArtifact(
        problem_title="离线打家劫舍",
        input_contract="输入 nums 数组。",
        input_data=trace.input_data,
        expected_result=12,
        verifier_result=12,
        variants=[
            {
                "id": "dp",
                "name": "动态规划",
                "strategy": "使用 dp 记录最优值。",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)",
                "code": "def solve(input_data):\n    return 12",
                "tracker_code": "def trace(input_data):\n    return {}",
                "result": 12,
                "trace": trace.model_dump(),
            }
        ],
        scenes={"dp": scene},
        validation=ValidationReport(
            checks=["fixture"],
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                multi_solution_ready=False,
                release_ready=True,
            ),
        ),
    )


def classic_coverage_artifact() -> BuildArtifact:
    traces = [
        ("tree", "二叉树遍历", tree_trace()),
        ("heap", "堆操作", heap_trace()),
        ("trie", "Trie 插入", trie_trace()),
        ("union_find", "并查集", union_find_trace()),
        ("recursion", "回溯递归", recursion_trace()),
        ("string", "字符串匹配", string_trace()),
        ("geometry", "几何点集", geometry_trace()),
    ]
    variants = []
    scenes = {}
    for variant_id, name, trace in traces:
        variants.append(
            {
                "id": variant_id,
                "name": name,
                "strategy": "经典视觉形态覆盖样例。",
                "time_complexity": "fixture",
                "space_complexity": "fixture",
                "code": "def solve(input_data):\n    return None",
                "tracker_code": "def trace(input_data):\n    return {}",
                "result": trace.result,
                "trace": trace.model_dump(),
            }
        )
        scenes[variant_id] = compile_scene(trace)
    return BuildArtifact(
        problem_title="经典算法视觉形态覆盖",
        input_contract="离线 fixture，不调用 LLM。",
        input_data={"fixture": True},
        variants=variants,
        scenes=scenes,
        validation=ValidationReport(
            checks=["classic coverage fixture"],
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                multi_solution_ready=True,
                release_ready=True,
            ),
        ),
    )


def algorithm_family_traces() -> list[tuple[str, str, SemanticTrace, str]]:
    return [
        ("two_pointer", "二分/双指针/滑动窗口", two_pointer_trace(), "array"),
        ("dp", "一维/二维 DP", house_robber_trace(), "array"),
        ("hash_map", "哈希表/map", hash_map_trace(), "map"),
        ("graph", "BFS/DFS 基础图", bfs_trace(), "graph"),
        ("monotonic_stack", "栈/队列/单调栈", monotonic_stack_trace(), "stack"),
        ("sorting", "排序", sorting_trace(), "array"),
        ("tree", "树/BST/LCA", tree_trace(), "tree"),
        ("heap", "堆/TopK/Huffman", heap_trace(), "heap"),
        ("trie", "Trie", trie_trace(), "trie"),
        ("union_find", "并查集", union_find_trace(), "union_find"),
        ("recursion", "回溯/递归", recursion_trace(), "stack"),
        ("string", "字符串高级算法", string_trace(), "string"),
        ("geometry", "几何/扫描线", geometry_trace(), "geometry"),
    ]


def algorithm_subfamily_traces() -> list[tuple[str, str, SemanticTrace, tuple[str, ...], tuple[str, ...]]]:
    return [
        ("binary_search", "二分查找", binary_search_trace(), ("array",), ("pointer:left", "pointer:right", "pointer:mid")),
        ("two_pointer", "双指针", two_pointer_trace(), ("array",), ("pointer:left", "pointer:right")),
        ("sliding_window", "滑动窗口", sliding_window_trace(), ("array",), ("pointer:left", "pointer:right")),
        ("dp_1d", "一维 DP", house_robber_trace(), ("array",), ("dp", "nums")),
        ("dp_2d", "二维 DP", unique_paths_trace(), ("matrix",), ("dp[1][1]",)),
        ("hash_map", "哈希表/map", hash_map_trace(), ("map",), ("seen[2]",)),
        ("bfs_graph", "BFS 基础图", bfs_trace(), ("graph", "queue"), ("node:A", "queue")),
        ("dfs_graph", "DFS 基础图", dfs_trace(), ("graph", "stack"), ("node:B", "stack")),
        ("monotonic_stack", "单调栈", monotonic_stack_trace(), ("stack",), ("stack",)),
        ("queue", "队列", queue_trace(), ("queue",), ("queue[0]",)),
        ("sorting", "排序", sorting_trace(), ("array",), ("nums",)),
        ("tree", "二叉树遍历", tree_trace(), ("tree",), ("node:2",)),
        ("bst_lca", "BST/LCA", bst_lca_trace(), ("tree",), ("node:6",)),
        ("heap", "堆操作", heap_trace(), ("heap",), ("heap[0]",)),
        ("topk_heap", "TopK", topk_heap_trace(), ("heap",), ("heap[0]",)),
        ("huffman", "Huffman", huffman_trace(), ("heap", "tree"), ("heap[0]", "node:ab")),
        ("trie_insert", "Trie 插入", trie_trace(), ("trie",), ("node:app",)),
        ("trie_search", "Trie 查询", trie_search_trace(), ("trie",), ("node:ap",)),
        ("union_find", "并查集合并", union_find_trace(), ("union_find",), ("node:2",)),
        ("union_find_compression", "并查集路径压缩", union_find_compression_trace(), ("union_find",), ("node:4",)),
        ("recursion_stack", "递归调用栈", recursion_trace(), ("stack",), ("stack",)),
        ("recursion_tree", "回溯搜索树", recursion_tree_trace(), ("recursion_tree", "stack"), ("node:choose12",)),
        ("kmp", "KMP", string_trace(), ("string",), ("text[2]", "pattern[0]")),
        ("rabin_karp", "Rabin-Karp", rabin_karp_trace(), ("string",), ("text[2]", "pattern[0]")),
        ("manacher", "Manacher", manacher_trace(), ("string", "array"), ("text[5]", "radius[5]")),
        ("geometry_hull", "凸包", geometry_trace(), ("geometry",), ("point:3",)),
        ("sweep_line", "扫描线", sweep_line_trace(), ("geometry",), ("point:c", "point:d")),
    ]


def algorithm_family_coverage_artifact() -> BuildArtifact:
    variants = []
    scenes = {}
    for variant_id, name, trace, _layouts, _objects in algorithm_subfamily_traces():
        variants.append(
            {
                "id": variant_id,
                "name": name,
                "strategy": "算法族/子形态覆盖样例。",
                "time_complexity": "fixture",
                "space_complexity": "fixture",
                "code": "def solve(input_data):\n    return None",
                "tracker_code": "def trace(input_data):\n    return {}",
                "result": trace.result,
                "trace": trace.model_dump(),
            }
        )
        scenes[variant_id] = compile_scene(trace)
    return BuildArtifact(
        problem_title="13 类经典算法族覆盖",
        input_contract="离线 fixture，不调用 LLM。",
        input_data={"fixture": True},
        variants=variants,
        scenes=scenes,
        validation=ValidationReport(
            checks=["algorithm family coverage fixture"],
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                multi_solution_ready=True,
                release_ready=True,
            ),
        ),
    )


def golden_visual_matrix() -> list[dict[str, object]]:
    return [
        {
            "id": "unique_paths",
            "name": "不同路径二维 DP",
            "doc": "docs/examples/unique_paths.md",
            "trace": unique_paths_trace(),
            "primary_primitives": ("matrix",),
            "support_primitives": (),
            "key_objects": ("dp", "dp[1][1]", "dp[0][1]", "dp[1][0]"),
            "key_deps": ("dp[0][1]", "dp[1][0]", "dp[1][6]", "dp[2][5]"),
            "key_teaching_fields": ("what", "why", "formula", "invariant"),
        },
        {
            "id": "bfs",
            "name": "BFS 最短层数",
            "doc": "docs/examples/bfs.md",
            "trace": bfs_trace(),
            "primary_primitives": ("graph",),
            "support_primitives": ("queue", "map"),
            "key_objects": ("graph", "queue", "dist", "node:A", "node:B", "edge:A->B"),
            "key_deps": ("node:A", "edge:A->B", "edge:A->C", "node:B", "edge:B->D"),
            "key_teaching_fields": ("what", "why", "formula", "invariant"),
        },
        {
            "id": "binary_search",
            "name": "二分查找",
            "doc": "docs/examples/binary_search.md",
            "trace": binary_search_trace(),
            "primary_primitives": ("array",),
            "support_primitives": (),
            "key_objects": ("nums", "nums[2]", "nums[4]", "pointer:left", "pointer:right", "pointer:mid"),
            "key_deps": ("pointer:left", "pointer:right", "nums[2]", "pointer:mid"),
            "key_teaching_fields": ("what", "why", "formula", "invariant"),
        },
        {
            "id": "monotonic_stack",
            "name": "每日温度单调栈",
            "doc": "docs/examples/monotonic_stack.md",
            "trace": monotonic_stack_trace(),
            "primary_primitives": ("stack",),
            "support_primitives": ("array",),
            "key_objects": ("temperatures", "temperatures[0]", "temperatures[1]", "stack", "answer", "answer[0]"),
            "key_deps": ("temperatures[0]", "temperatures[1]"),
            "key_teaching_fields": ("what", "why", "formula", "invariant"),
        },
    ]


def golden_visual_artifact() -> BuildArtifact:
    variants = []
    scenes = {}
    for example in golden_visual_matrix():
        trace = example["trace"]
        assert isinstance(trace, SemanticTrace)
        variant_id = str(example["id"])
        variants.append(
            {
                "id": variant_id,
                "name": str(example["name"]),
                "strategy": "黄金样例视觉矩阵，验证通用 SceneGraph 编译和 renderer 展示。",
                "time_complexity": "fixture",
                "space_complexity": "fixture",
                "code": "def solve(input_data):\n    return None",
                "tracker_code": "def trace(input_data):\n    return {}",
                "result": trace.result,
                "trace": trace.model_dump(),
            }
        )
        scenes[variant_id] = compile_scene(trace)
    return BuildArtifact(
        problem_title="黄金样例视觉矩阵",
        input_contract="覆盖 unique_paths、bfs、binary_search、monotonic_stack。",
        input_data={"fixture": "golden_visual_matrix"},
        variants=variants,
        scenes=scenes,
        validation=ValidationReport(
            checks=["golden visual matrix fixture"],
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                multi_solution_ready=True,
                release_ready=True,
            ),
        ),
    )
