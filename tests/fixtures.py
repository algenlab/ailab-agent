"""Deterministic artifacts used by offline tests."""

from __future__ import annotations

from algolab.compiler.scene_compiler import compile_scene
from algolab.schemas.semantic_trace import SemanticTrace
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
    graph = {"A": ["B", "C"], "B": ["A"], "C": ["A"]}
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BFS",
            "input_data": {"graph": graph, "start": "A"},
            "result": {"A": 0, "B": 1, "C": 1},
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
                },
                {
                    "step": 1,
                    "op": "pop",
                    "targets": [{"id": "queue"}, {"id": "node:A"}],
                    "state": {"graph": graph, "queue": [], "dist": {"A": 0}},
                    "role": "current",
                    "reason": "弹出 A 并检查邻居。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "mark",
                    "targets": [{"id": "node:B"}, {"id": "node:C"}],
                    "deps": [{"id": "node:A"}],
                    "state": {"graph": graph, "queue": ["B", "C"], "dist": {"A": 0, "B": 1, "C": 1}},
                    "role": "visited",
                    "reason": "首次发现 B 和 C。",
                    "code_line": 3,
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
            "input_data": {"nums": [1, 3, 5, 7, 9, 11], "target": 9},
            "result": 4,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1, 3, 5, 7, 9, 11], "left": 0, "right": 5, "target": 9},
                    "reason": "在有序数组上建立二分区间。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "nums[2]"}, {"id": "pointer:mid"}],
                    "value": 2,
                    "state": {"nums": [1, 3, 5, 7, 9, 11], "left": 0, "right": 5, "mid": 2, "target": 9},
                    "role": "candidate",
                    "reason": "比较中点 5 与目标 9。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "move",
                    "targets": [{"id": "pointer:left"}, {"id": "pointer:right"}],
                    "value": [3, 5],
                    "state": {"nums": [1, 3, 5, 7, 9, 11], "left": 3, "right": 5, "target": 9},
                    "role": "current",
                    "reason": "目标更大，搜索区间移动到右半边。",
                    "code_line": 3,
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
            "input_data": {"m": 3, "n": 3},
            "result": 6,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [[1, 1, 1], [1, 0, 0], [1, 0, 0]]},
                    "reason": "第一行和第一列只有一种到达方式。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "compare",
                    "targets": [{"id": "dp[1][1]"}],
                    "deps": [{"id": "dp[0][1]"}, {"id": "dp[1][0]"}],
                    "state": {"dp": [[1, 1, 1], [1, 0, 0], [1, 0, 0]]},
                    "role": "candidate",
                    "reason": "当前位置依赖上方和左侧。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "set",
                    "targets": [{"id": "dp[1][1]"}],
                    "deps": [{"id": "dp[0][1]"}, {"id": "dp[1][0]"}],
                    "state": {"dp": [[1, 1, 1], [1, 2, 0], [1, 0, 0]]},
                    "role": "answer",
                    "reason": "dp[1][1] = 1 + 1 = 2。",
                    "code_line": 2,
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
                    "targets": [{"id": "seen:2"}],
                    "state": {"nums": [2, 7, 11, 15], "seen": {"2": 0}, "target": 9},
                    "role": "current",
                    "reason": "记录数值 2 的下标。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "compare",
                    "targets": [{"id": "nums[1]"}, {"id": "seen:2"}],
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
            "input_data": {"temperatures": [73, 74, 75, 71]},
            "result": [1, 1, 0, 0],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "stack"}],
                    "state": {"temperatures": [73, 74, 75, 71], "stack": []},
                    "reason": "栈中保存还没找到更高温度的下标。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "push",
                    "targets": [{"id": "stack"}],
                    "state": {"temperatures": [73, 74, 75, 71], "stack": [0]},
                    "role": "current",
                    "reason": "下标 0 入栈等待更高温度。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "pop",
                    "targets": [{"id": "stack"}, {"id": "temperatures[1]"}],
                    "state": {"temperatures": [73, 74, 75, 71], "stack": [], "answer": [1, 0, 0, 0]},
                    "role": "answer",
                    "reason": "74 高于 73，下标 0 等待 1 天。",
                    "code_line": 3,
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
        ("hash_map", "哈希表/map", hash_map_trace(), ("map",), ("seen:2",)),
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
