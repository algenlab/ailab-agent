"""Regression tests for LLM repair prompt contracts."""

from __future__ import annotations

from algolab.generation.repair import build_solution_repair_prompt
from algolab.generation import solution_generator
from algolab.schemas.input import ProblemInput
from algolab.verification.repair_context import build_repair_context
from llm_client import LLMJsonError


def _prompt_for(errors: list[str]) -> str:
    context = build_repair_context(errors)
    return build_solution_repair_prompt(
        request_prompt="生成算法轨迹 JSON。",
        previous={"variants": [{"id": "v", "tracker_code": ""}]},
        errors=errors,
        repair_context=context,
    )


def test_r1_schema_and_target_errors_are_classified_for_repair():
    errors = [
        "ValidationError: events.0.type Extra inputs are not permitted [type=extra_forbidden, input_value='set']",
        "ValidationError: events.0.target Extra inputs are not permitted [type=extra_forbidden, input_value='dp[1]']",
        "ValidationError: events.0.targets.0 Input should be a valid dictionary or instance of TargetRef [type=model_type, input_value='dp[1]']",
        "ValidationError: trace input_data Field required [type=missing]",
    ]

    contexts = build_repair_context(errors)
    failure_types = {item["failure_type"] for item in contexts}
    categories = {item["repair_category"] for item in contexts}
    instructions = " ".join(item["repair_instruction"] for item in contexts)

    assert {"schema_error", "target_error"} <= failure_types
    assert {"trace_schema", "target_or_deps"} <= categories
    assert "Tracer API" in instructions
    assert "op/targets" in instructions


def test_r1_runtime_api_errors_are_execution_repairs():
    errors = [
        "TypeError: Tracer.__init__() missing 1 required positional argument: 'input_data'",
        "AttributeError: 'Tracer' object has no attribute 'choose'",
        "TypeError: unhashable type: 'list'",
        "TypeError: Tracer.compare() missing 1 required positional argument: 'targets'",
        "TypeError: Tracer.link() takes 2 positional arguments but 3 were given",
    ]

    contexts = build_repair_context(errors)

    assert {item["failure_type"] for item in contexts} == {"execution_error"}
    assert {item["repair_category"] for item in contexts} == {"execution"}
    joined = " ".join(item["repair_instruction"] for item in contexts)
    assert "Tracer(input_data" in joined
    assert "push" in joined
    assert "mark" in joined
    assert "enter" in joined
    assert "exit" in joined
    assert "tracer.compare([" in joined
    assert "tracer.link(" in joined
    assert "deps=" in joined


def test_r1_repair_prompt_adds_tracer_checklist_and_forbids_renderer_code():
    prompt = _prompt_for(
        [
            "ValidationError: events.0.targets.0 Input should be a valid dictionary or instance of TargetRef [type=model_type, input_value='dp[1]']",
            "AttributeError: 'Tracer' object has no attribute 'choose'",
        ]
    )

    assert "Tracer(input_data" in prompt
    assert "op/targets" in prompt
    assert 'deps 为 {"id": ...}' in prompt
    assert "不要手写旧 events" in prompt
    assert "push" in prompt
    assert "mark" in prompt
    assert "enter" in prompt
    assert "exit" in prompt
    assert "不存在 tracer.choose()" in prompt
    assert "不要生成 HTML、CSS、JS" in prompt
    assert "不要生成 HTML、CSS、JS 或 renderer 代码" in prompt
    assert "必须使用 choose()" not in prompt
    assert "改用 choose()" not in prompt


def test_r1_map_target_quotes_are_repaired_to_semantic_ids():
    errors = [
        "第 1 步引用了不存在的 map target：indegree['A']",
        '第 2 步引用了不存在的 map target：dist["B"]',
    ]

    contexts = build_repair_context(errors)
    prompt = _prompt_for(errors)
    joined = " ".join(item["repair_instruction"] for item in contexts)

    assert {item["failure_type"] for item in contexts} == {"target_error"}
    assert {item["repair_category"] for item in contexts} == {"target_or_deps"}
    assert "indegree[A]" in joined
    assert "dist[B]" in joined
    assert "不要写 indegree['A']" in prompt
    assert '不要写 dist["B"]' in prompt


def test_r7_json_parse_failures_force_compact_single_variant_repair():
    errors = [
        "LLMJsonError: 模型返回内容不是合法 JSON：Unterminated string starting at: line 12 column 23; preview={...<truncated>",
        "LLMJsonError: 模型返回空内容，无法解析 JSON",
    ]

    contexts = build_repair_context(errors)
    prompt = _prompt_for(errors)
    joined = " ".join(item["repair_instruction"] for item in contexts)

    assert {item["repair_category"] for item in contexts} == {"generation"}
    assert "1 个 variant" in joined
    assert "完整必要过程" in joined
    assert "短 tracker_code" in joined
    assert "不要复制长代码" in prompt
    assert "max_events" not in prompt
    assert "不要输出 16000 tokens" in prompt


def test_r7_solution_repair_retries_with_compact_context_after_json_parse_failure():
    prompts: list[str] = []

    def fake_chat_json(_system_prompt: str, user_prompt: str, *, kind: str):
        prompts.append(user_prompt)
        if len(prompts) == 1:
            raise LLMJsonError("模型返回空内容，无法解析 JSON")
        return {
            "problem_title": "拓扑排序",
            "input_contract": "graph",
            "variants": [
                {
                    "id": "kahn",
                    "name": "Kahn",
                    "strategy": "短修复",
                    "code": "def solve(input_data):\n    return []\n",
                    "tracker_code": "def trace(input_data):\n    return {}\n",
                }
            ],
        }

    request = ProblemInput(
        problem="给定 DAG，返回一个拓扑序。",
        input_data={"graph": {"A": ["B"]}},
        expected_result=["A", "B"],
        solution_count=1,
    )
    previous = {"variants": [{"id": "kahn", "tracker_code": "x" * 2000}]}
    original = solution_generator._chat_json
    solution_generator._chat_json = fake_chat_json
    try:
        repaired = solution_generator.repair_solution_spec(request, previous, ["Graph contract topological_sort 缺少入队原因"])
    finally:
        solution_generator._chat_json = original

    assert repaired["variants"][0]["id"] == "kahn"
    assert len(prompts) == 2
    assert "LLMJsonError" in prompts[1]
    assert "1 个 variant" in prompts[1]
    assert "短 tracker_code" in prompts[1]
    assert "不要复制长代码" in prompts[1]


def test_r7_solution_repair_retries_with_compact_context_after_top_level_string_response():
    prompts: list[str] = []

    def fake_chat_json(_system_prompt: str, user_prompt: str, *, kind: str):
        prompts.append(user_prompt)
        if len(prompts) == 1:
            return "not a json object"
        return {
            "problem_title": "数位 DP",
            "input_contract": "n",
            "variants": [
                {
                    "id": "digit_dp",
                    "name": "数位 DP",
                    "strategy": "短修复",
                    "code": "def solve(input_data):\n    return 18\n",
                    "tracker_code": "def trace(input_data):\n    return {}\n",
                }
            ],
        }

    request = ProblemInput(
        problem="给定非负整数 n，统计 1 到 n 中十进制表示不包含数字 7 的正整数个数。",
        input_data={"n": 20},
        expected_result=18,
        solution_count=1,
    )
    previous = {"variants": [{"id": "digit_dp", "tracker_code": "x" * 2000}]}
    original = solution_generator._chat_json
    solution_generator._chat_json = fake_chat_json
    try:
        repaired = solution_generator.repair_solution_spec(request, previous, ["ValueError: LLM 顶层输出必须是 JSON object，实际为 str"])
    finally:
        solution_generator._chat_json = original

    assert repaired["variants"][0]["id"] == "digit_dp"
    assert len(prompts) == 2
    assert "ValueError" in prompts[1]
    assert "顶层输出必须是 JSON object" in prompts[1]
    assert "短 tracker_code" in prompts[1]
    assert "不要复制长代码" in prompts[1]


def test_r7_topological_request_prompt_includes_compact_kahn_template():
    request = ProblemInput(
        problem="给定有向无环图 graph，返回一个拓扑序。",
        input_data={"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}},
        expected_result=["A", "B", "C", "D"],
        strategy_hint="Kahn 算法维护 indegree 和 queue。",
        solution_count=1,
    )

    prompt = solution_generator._build_user_prompt(request)

    assert "拓扑排序固定短模板" in prompt
    assert "6-10 个 events" in prompt
    assert "create graph/indegree" in prompt
    assert "decrement indegree" in prompt
    assert "mark topo_order" in prompt
    assert "tracer.result(topo_order)" in prompt
    assert "不要写成长篇 tracker" in prompt


def test_r7_tree_dp_request_prompt_includes_postorder_take_skip_template():
    request = ProblemInput(
        problem="给定带权树，返回树上最大独立集权重。",
        input_data={"tree": {"nodes": [{"id": 1, "value": 3}], "edges": []}},
        expected_result=3,
        strategy_hint="树形 DP，dp_take 和 dp_skip 后序聚合。",
        solution_count=1,
    )

    prompt = solution_generator._build_user_prompt(request)

    assert "树形 DP 固定短模板" in prompt
    assert "先递归完成所有 child" in prompt
    assert "不要发布父节点半成品" in prompt
    assert 'tracer.set("dp_take' in prompt
    assert 'tracer.set("dp_skip' in prompt
    assert 'tracer.set("answer")' in prompt
    assert 'answer_position="answer"' in prompt
    assert "expected_targets" in prompt
    assert "answer" in prompt
    assert "expected_nodes" in prompt


def test_r7_residual_request_prompt_includes_family_specific_short_templates():
    requests = [
        (
            ProblemInput(
                problem="给定升序数组 nums 和 target，用闭区间二分查找返回 target 下标。",
                input_data={"nums": [1, 3, 5, 7, 9], "target": 9},
                expected_result=4,
                strategy_hint="闭区间二分查找，每轮比较 nums[mid] 和 target。",
                solution_count=1,
            ),
            [
                "闭区间二分固定短模板",
                "move pointer:left/right 后 state.mid 必须等于新窗口 (left+right)//2",
                "不要把 mid 置为 None",
                "move 的前一个事件必须是 compare",
            ],
        ),
        (
            ProblemInput(
                problem="给定正整数数组 nums，判断能否把数组划分成两个元素和相等的子集。",
                input_data={"nums": [1, 5, 11, 5]},
                expected_result=True,
                strategy_hint="把目标设为总和一半，逆序容量更新 dp[c]，确保每个数只用一次。",
                solution_count=1,
            ),
            [
                "0-1 背包固定短模板",
                "dp_contract.expected_targets 只列实际 tracer.set",
                "dp[0]=True",
                "state 保留 nums",
                'deps=["dp[c]","dp[c-weight]","nums[i]"]',
            ],
        ),
        (
            ProblemInput(
                problem="给定不含重复数字的数组 nums，返回所有可能的排列。",
                input_data={"nums": [1, 2, 3]},
                expected_result=[[1, 2, 3]],
                strategy_hint="回溯搜索树，选择、记录完整排列、撤销选择。",
                solution_count=1,
            ),
            [
                "全排列回溯固定短模板",
                'record 事件必须 role="answer"',
                "state.answer 包含新排列",
                'deps=["path"]',
                "reason 写 record/记录完整排列",
                "frame id 禁止包含空格",
                "frame:dfs(1_2)",
            ],
        ),
        (
            ProblemInput(
                problem="给定二维点集 points，返回凸包顶点。",
                input_data={"points": [[0, 0], [1, 1], [2, 0], [1, 2]]},
                expected_result=[[0, 0], [2, 0], [1, 2]],
                strategy_hint="Andrew 单调链算法，使用叉积维护 hull。",
                solution_count=1,
            ),
            [
                "凸包 Andrew 固定短模板",
                "不要使用 backtracking family_contract",
                "geometry.hull",
                "compare 带 value=叉积",
                'deps=["geometry"]',
                "不要在 deps 使用 point:",
                "不要设置 family_contract",
                "中间候选只放 geometry.stack",
                "geometry.hull 只放最终或已验证凸包",
                "每个 compare/pop/answer 事件都重复完整 state.geometry.points",
                'geometry_points=[{"id":"p0"',
            ],
        ),
        (
            ProblemInput(
                problem="给定一个无权图的邻接表 graph 和起点 start，返回从 start 到所有可达节点的最短边数距离。",
                input_data={"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, "start": "A"},
                expected_result={"A": 0, "B": 1, "C": 1, "D": 2},
                strategy_hint="队列按层扩展，首次访问时确定距离。",
                solution_count=1,
            ),
            ["BFS 固定短模板", 'tracer.set("dist[neighbor]")', "parent[neighbor]=current", "不要写 parent[neighbor]=neighbor"],
        ),
        (
            ProblemInput(
                problem="给定无向图邻接表 graph，返回所有连通分量，每个分量内节点按字典序排列。",
                input_data={"graph": {"A": ["B"], "B": ["A"], "C": []}},
                expected_result=[["A", "B"], ["C"]],
                strategy_hint="从每个未访问节点开始 DFS，把同一连通块中的节点收集成一个分量。",
                solution_count=1,
            ),
            ["连通分量固定短模板", "submode\":\"connected_components", "stack 或 frame:dfs"],
        ),
        (
            ProblemInput(
                problem="给定非负整数 n，统计 1 到 n 中十进制表示不包含数字 7 的正整数个数。",
                input_data={"n": 20},
                expected_result=18,
                strategy_hint="逐位处理 n 的前缀，维护当前前缀范围内不含禁用数字的计数。",
                solution_count=1,
            ),
            [
                "数位 DP 固定短模板",
                "不包含数字 7",
                "只返回 JSON object",
                "tracker_code 少于 80 行",
                "不要使用九进制转换法",
                "只保留 create dp、set dp[1]、set dp[2]、set ans",
                "dp[1]=2",
                "dp[2]=18",
                'tracer.set("ans")',
            ],
        ),
        (
            ProblemInput(
                problem="给定二分图的左侧点、右侧点和邻接表 graph，使用增广路径求最大匹配。",
                input_data={"graph": {"L1": ["R1", "R2"], "L2": ["R1"], "L3": ["R2"]}, "left": ["L1", "L2", "L3"], "right": ["R1", "R2"]},
                expected_result={"L1": "R2", "L2": "R1"},
                strategy_hint="逐个左侧点寻找增广路径，成功后更新 match 映射。",
                solution_count=1,
            ),
            ["二分图匹配固定短模板", "不要设置 graph_contract submode=dfs", "match[right]=left", "旧 match[R1]=L1 必须清除或改为 match[R1]=L2"],
        ),
        (
            ProblemInput(problem="给定 nums 和 updates，用差分数组做区间加法。", input_data={}, expected_result=[], strategy_hint="差分数组", solution_count=1),
            ["差分数组固定短模板", "diff[0]=nums[0]", "diff[right+1]-=delta", 'tracer.set("nums[i]")', "running_sum"],
        ),
        (
            ProblemInput(problem="使用 Dijkstra 求非负权图单源最短路。", input_data={}, expected_result={}, strategy_hint="dijkstra 最小堆", solution_count=1),
            ["Dijkstra 固定短模板", 'tracer.set("dist[v]")', 'deps=["node:u", "node:v", "edge:u->v", "dist[u]"]', "old_dist/new_dist/edge_weight"],
        ),
        (
            ProblemInput(problem="统计 1 到 n 中不含 7 的数字个数。", input_data={}, expected_result=0, strategy_hint="数位 DP", solution_count=1),
            ["数位 DP 固定短模板", "deps", "digit", 'tracer.set("ans")'],
        ),
        (
            ProblemInput(problem="用 Floyd-Warshall 求全源最短路。", input_data={}, expected_result=[], strategy_hint="Floyd", solution_count=1),
            ["Floyd 固定短模板", "不要把未 set 的 dist[i][j] 放进 expected_targets", "deps=[\"dist[i][k]\", \"dist[k][j]\"]"],
        ),
        (
            ProblemInput(problem="每日温度，返回等待几天后有更高温。", input_data={}, expected_result=[], strategy_hint="单调栈 daily_temperatures", solution_count=1),
            ["单调栈固定短模板", "family_contract", "不要使用 range_structure"],
        ),
        (
            ProblemInput(problem="二叉树中序遍历。", input_data={}, expected_result=[], strategy_hint="递归中序遍历", solution_count=1),
            ["树遍历固定短模板", "每个 enter/exit/mark 都必须有非空 reason"],
        ),
        (
            ProblemInput(problem="求二叉树中两个节点的最近公共祖先。", input_data={}, expected_result="3", strategy_hint="LCA lowest common ancestor", solution_count=1),
            ["LCA/树递归固定短模板", "不要使用 graph_contract submode=dfs", 'family_contract={"family":"tree"', "return_value", 'tracer.create("tree")', 'state.phase="initialization"'],
        ),
        (
            ProblemInput(problem="Trie 前缀统计。", input_data={}, expected_result=0, strategy_hint="字典树 prefix_count", solution_count=1),
            ["Trie 前缀统计固定短模板", "root.meta.prefix_count=len(words)", "role=\"create_node\"", "state.trie.nodes", "query 前缀终点", "prefix 为空时答案来自 root.meta.prefix_count"],
        ),
        (
            ProblemInput(problem="给定 weights、values、counts 和 capacity，求多重背包最大价值。", input_data={}, expected_result=0, strategy_hint="bounded_knapsack 一维空间优化", solution_count=1),
            ["多重背包固定短模板", "candidate", "old_value", "最终答案必须是 dp[capacity]", "所有事件 reason 非空"],
        ),
        (
            ProblemInput(problem="给定 text1 和 text2，返回最长公共子序列长度。", input_data={}, expected_result=0, strategy_hint="LCS 二维动态规划", solution_count=1),
            ["LCS 固定短模板", 'dp_contract.subfamily="lcs"', "i、j、current", "text1[i-1]", "text2[j-1]", "dp[i-1][j-1]", "不要把 dp[0][j] 或 dp[i][0] 放进 dp_contract.expected_targets"],
        ),
        (
            ProblemInput(problem="给定字符串 text，求最长无重复子串长度。", input_data={}, expected_result=0, strategy_hint="字符串滑动窗口，维护 window_counts。", solution_count=1),
            ["字符串滑动窗口固定短模板", "string_sliding_window", "不要添加 pattern", "pointer:left", "pointer:right", "先收缩到无重复再更新 best", "每次收缩都 set window_counts"],
        ),
        (
            ProblemInput(problem="给定字符串 text，返回 Z 数组。", input_data={"text": "aabcaabx"}, expected_result=[0, 1, 0, 0, 3, 1, 0, 0], strategy_hint="Z Algorithm", solution_count=1),
            ["Z Algorithm 固定短模板", "z[4]=3", "不要在扩展完成前", 'tracer.set("z[4]"'],
        ),
        (
            ProblemInput(problem="给定 0/1 权重图 weighted_graph 和起点 start，返回最短距离。", input_data={}, expected_result={}, strategy_hint="zero_one_bfs 使用 deque", solution_count=1),
            ["0-1 BFS 固定短模板", "push_front", "push_back", 'deps=["node:u", "node:v", "edge:u->v"]', "dist[u]", "edge_weight"],
        ),
        (
            ProblemInput(problem="线段树区间和，支持一次 update 后再 query。", input_data={}, expected_result={}, strategy_hint="segment_tree range sum", solution_count=1),
            ["线段树固定短模板", "tracker_code 少于 80 行", "6-10 个 events", "node:root", "线段树 update 后必须沿叶子到 root 同步 sum/value"],
        ),
        (
            ProblemInput(problem="树状数组前缀和，支持一次单点 update 和区间 query。", input_data={}, expected_result={}, strategy_hint="fenwick_tree prefix sum", solution_count=1),
            ["树状数组固定短模板", "tracker_code 少于 80 行", "bit", "lowbit", "先 set nums[pos]"],
        ),
        (
            ProblemInput(problem="Sparse Table 区间最小值查询。", input_data={"nums": [5, 2, 7, 3, 6, 1]}, expected_result=2, strategy_hint="sparse_table range min", solution_count=1),
            ["Sparse table 超时必须用紧凑固定模板", "Sparse table state 必须包含完整正确 st 表", "st[0]=nums", "st[1]=[2,2,3,3,1]", "st[2]=[2,2,1]", "不要引用不存在的 st[2][1]"],
        ),
        (
            ProblemInput(problem="返回数组中第 k 大元素。", input_data={}, expected_result=0, strategy_hint="topk_min_heap 小顶堆", solution_count=1),
            ["堆 TopK 固定短模板", "heap_type", "heap_top", "heap[0]"],
        ),
        (
            ProblemInput(problem="反转链表。", input_data={"values": [1, 2]}, expected_result=[2, 1], strategy_hint="reverse_linked_list 迭代反转", solution_count=1),
            ["两节点扩展样例 values=[1,2]", "保存 next_node=\"1\"", "下一帧 current 必须是 \"1\"", "三节点样例 values=[1,2,3]", "current 帧顺序必须是 \"0\" -> \"1\" -> \"2\""],
        ),
        (
            ProblemInput(problem="使用 Bellman-Ford 求带负权边图的单源最短路。", input_data={}, expected_result={}, strategy_hint="bellman_ford", solution_count=1),
            ["Bellman-Ford 固定短模板", "state.graph.nodes", "state.graph.edges", "每个 relax/check 事件都重复完整 state.graph"],
        ),
        (
            ProblemInput(problem="给定 nums，返回所有子集。", input_data={}, expected_result=[[]], strategy_hint="bitmask_subsets 二进制掩码枚举", solution_count=1),
            ["位掩码子集固定短模板", 'tracer.create("subsets")', 'tracer.set("subset")', 'tracer.set("subsets")', 'tracer.mark("answer")', "不要使用 res[i]/result[i] 作为 target/deps", "deps 写 subset 时同一事件 state.subset 必须存在"],
        ),
        (
            ProblemInput(problem="Two Sum：给定 nums 和 target，返回两个下标。", input_data={}, expected_result=[0, 1], strategy_hint="哈希表一次遍历 two_sum", solution_count=1),
            ["Two Sum 哈希固定短模板", "hash_contract", "不要设置 family_contract family=hash", "seen[need]", 'tracer.create("seen")', "state.phase=\"initialization\""],
        ),
        (
            ProblemInput(problem="Tarjan 求无向图的割点和桥。", input_data={}, expected_result={}, strategy_hint="articulation_bridges tarjan", solution_count=1),
            ["Tarjan 割点桥固定短模板", 'tracer.set("dfn[u]")', 'tracer.set("low[u]")', "dfn 写入事件", "Tarjan 割点桥所有事件 reason 非空"],
        ),
    ]

    for request, expected_parts in requests:
        prompt = solution_generator._build_user_prompt(request)
        for part in expected_parts:
            assert part in prompt, (request.problem, part, prompt)


def run_all() -> None:
    test_r1_schema_and_target_errors_are_classified_for_repair()
    test_r1_runtime_api_errors_are_execution_repairs()
    test_r1_repair_prompt_adds_tracer_checklist_and_forbids_renderer_code()
    test_r1_map_target_quotes_are_repaired_to_semantic_ids()
    test_r7_json_parse_failures_force_compact_single_variant_repair()
    test_r7_solution_repair_retries_with_compact_context_after_json_parse_failure()
    test_r7_solution_repair_retries_with_compact_context_after_top_level_string_response()
    test_r7_topological_request_prompt_includes_compact_kahn_template()
    test_r7_tree_dp_request_prompt_includes_postorder_take_skip_template()
    test_r7_residual_request_prompt_includes_family_specific_short_templates()


if __name__ == "__main__":
    run_all()
    print("repair_prompt_contracts: PASS")
