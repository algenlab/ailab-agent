"""Regression tests for R7 deterministic residual repair guidance."""

from __future__ import annotations

from algolab.generation.repair import build_solution_repair_prompt
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.process_validator import validate_process
from algolab.verification.repair_context import build_repair_context

from tests.regression.helpers import _family_contract_event, _family_contract_trace


def _guidance_for(message: str) -> tuple[list[dict], str]:
    context = build_repair_context([message])
    prompt = build_solution_repair_prompt(
        request_prompt="生成算法轨迹 JSON。",
        previous={"variants": [{"id": "v", "tracker_code": ""}]},
        errors=[message],
        repair_context=context,
    )
    joined = "\n".join(
        [
            *(item["repair_instruction"] for item in context),
            *(line for item in context for line in item["family_guidance"]),
            prompt,
        ]
    )
    return context, joined


def _process_errors(raw_trace: dict) -> list[str]:
    trace = SemanticTrace.model_validate(raw_trace)
    errors, _warnings = validate_process(trace)
    return errors


def test_r7_runtime_api_guidance_forbids_to_trace_result_and_private_add_stage():
    context, guidance = _guidance_for(
        "trace 执行失败：TypeError: Tracer.to_trace() got an unexpected keyword argument 'result'; "
        "TypeError: Tracer._add() got an unexpected keyword argument 'stage'; "
        "TypeError: Tracer._add() got an unexpected keyword argument 'action'"
    )

    assert {item["failure_type"] for item in context} == {"execution_error"}
    assert {item["repair_category"] for item in context} == {"execution"}
    assert "tracer.result(answer)" in guidance
    assert "return tracer.to_trace()" in guidance
    assert "to_trace(result=" in guidance
    assert "不要" in guidance
    assert "tracer._add" in guidance
    assert "stage=" in guidance
    assert "action=" in guidance


def test_r7_runtime_api_guidance_forbids_contract_kwargs_in_tracer_init():
    context, guidance = _guidance_for(
        "Andrew 单调链算法 失败：trace 执行失败：TypeError: Tracer.__init__() got an unexpected keyword argument 'family_contract'"
    )

    assert {item["failure_type"] for item in context} == {"execution_error"}
    assert "Tracer(input_data, algorithm=..., pseudocode=...)" in guidance
    assert "family_contract" in guidance
    assert "不能传给 Tracer.__init__" in guidance
    assert "放进每个事件的 state" in guidance


def test_r7_targetref_id_list_schema_guidance_rewrites_each_target_as_string_id():
    _context, guidance = _guidance_for(
        "二分查找法 失败：1 validation error for SemanticTrace\n"
        "events.0.targets.0.id\n"
        "  Input should be a valid string [type=string_type, input_value=['pointer:left', 'pointer:right'], input_type=list]"
    )

    assert "TargetRef.id 必须是字符串" in guidance
    assert "不要把多个 target 塞进同一个 id" in guidance
    assert "pointer:left" in guidance
    assert "pointer:right" in guidance
    assert '{"id": "pointer:left"}' in guidance
    assert '{"id": "pointer:right"}' in guidance


def test_r7_array_pointer_guidance_requires_submode_key_updates_and_compare_deps():
    context, guidance = _guidance_for(
        "二分查找 失败：Array pointer contract 缺少 submode，无法选择数组指针过程合同；"
        "failure_type=demo_state_jump: step 9 二分区间无比较证据就发生跳变；"
        "滑动窗口 失败：Array pointer contract 缺少关键更新：nums[0], nums[5]"
    )

    assert context[0]["family"] == "array_pointer"
    assert "array_contract" in guidance
    assert "binary_answer" in guidance
    assert "sliding_window" in guidance
    assert "prefix_sum" in guidance
    assert "difference_array" in guidance
    assert "fast_slow" in guidance
    assert "compare" in guidance
    assert "deps" in guidance
    assert "expected_targets" in guidance
    assert "不能把 nums[i] 当作更新 target" in guidance


def test_r7_binary_search_guidance_requires_closed_interval_template_without_state_jump():
    _context, guidance = _guidance_for(
        "闭区间二分查找 失败：Array pointer contract 缺少关键更新：pointer:right; "
        "第 3 步 mid 不在 [left,right] 内; 第 3 步 二分 mid 应为 4; "
        "failure_type=demo_state_jump: step 7 二分区间无比较证据就发生跳变"
    )

    assert "闭区间" in guidance
    assert "left <= right" in guidance
    assert "mid=(left+right)//2" in guidance
    assert "pointer:right" in guidance
    assert "right=mid-1" in guidance
    assert "left=mid+1" in guidance
    assert "先 compare" in guidance
    assert "再 move" in guidance
    assert "move pointer:left/right 后 state.mid 必须等于新窗口 (left+right)//2" in guidance
    assert "不要把 mid 置为 None" in guidance


def test_r7_binary_search_move_guidance_requires_observable_evidence():
    _context, guidance = _guidance_for(
        "闭区间二分查找 失败：第 4 步 move 缺少可观测过程证据：需要 deps、before/after/value 或可解析的状态变化"
    )

    assert "每个 pointer:left/right move 必须带 value、deps 或 before/after" in guidance
    assert "value 写新指针位置" in guidance
    assert "before/after 写旧窗口和新窗口" in guidance
    assert "deps 指向上一帧 compare 的 nums[mid] 或 pointer:mid" in guidance


def test_r7_binary_answer_guidance_requires_initialization_phase_and_compare_before_every_move():
    _context, guidance = _guidance_for(
        "二分查找 失败：failure_type=demo_key_step_missing: 缺少 initialization 阶段; "
        "failure_type=demo_state_jump: step 9 二分区间无比较证据就发生跳变"
    )

    assert "initialization" in guidance
    assert "tracer.create" in guidance
    assert "phase" in guidance
    assert "binary_answer" in guidance
    assert "每次 move pointer:left/right 前必须有 compare" in guidance
    assert "在跳变 step 前插入 compare" in guidance


def test_r7_binary_answer_state_jump_guidance_requires_immediate_compare_before_move():
    _context, guidance = _guidance_for(
        "二分查找 失败：failure_type=demo_state_jump: step 10 二分区间无比较证据就发生跳变"
    )

    assert "move 的前一个事件必须是 compare" in guidance
    assert "不要在 compare 和 move 之间插入 explain/set/mark" in guidance
    assert "移动前窗口" in guidance
    assert "state.left/right/mid" in guidance
    assert "mid*mid <= n" in guidance


def test_r7_dp_knapsack_guidance_requires_loop_keys_deps_and_direction():
    context, guidance = _guidance_for(
        "0-1背包动态规划 失败：第 11 步 DP contract state 缺少循环变量：i, j, k, capacity_index, capacity, mask, digit, current; "
        "DP contract 缺少关键更新：dp[0], dp[2], dp[3]; 第 11 步 dp[11] 不满足 0-1 背包可达性；"
        "动态规划 失败：第 1 步 DP contract 关键更新缺少 deps; bounded_knapsack"
    )

    assert context[0]["family"] == "dynamic_programming"
    assert "knapsack_01" in guidance
    assert "bounded_knapsack" in guidance
    assert "capacity_index" in guidance
    assert "capacity" in guidance
    assert "0-1" in guidance
    assert "倒序" in guidance
    assert "count" in guidance or "数量上限" in guidance
    assert "deps" in guidance


def test_r7_bounded_knapsack_guidance_allows_incremental_candidate_but_requires_final_max():
    _context, guidance = _guidance_for(
        "一维空间优化多重背包 失败：第 4 步多重背包 dp[5] 应为 6; "
        "第 6 步多重背包 dp[4] 应为 6"
    )

    assert "bounded_knapsack" in guidance
    assert "candidate" in guidance
    assert "old_value" in guidance
    assert "take" in guidance or "选第 i 个物品" in guidance
    assert "最终" in guidance
    assert "dp[capacity]" in guidance


def test_r7_bounded_knapsack_missing_reason_guidance_requires_non_empty_reasons():
    _context, guidance = _guidance_for(
        "一维空间优化多重背包 失败：failure_type=demo_missing_reason: step 0 缺少 reason; "
        "failure_type=demo_missing_reason: step 1 缺少 reason"
    )

    assert "所有事件 reason 非空" in guidance
    assert "create/set/compare/mark" in guidance
    assert "多重背包" in guidance


def test_r7_lcs_guidance_requires_i_j_current_formula_and_deps():
    context, guidance = _guidance_for(
        "lcs_length 失败：动态规划 失败：第 1-9 步 DP contract state 缺少循环变量："
        "i, j, k, capacity_index, capacity, mask, digit, current"
    )

    assert context[0]["family"] == "dynamic_programming"
    assert context[0]["dp_submode"] == "lcs"
    assert "submode=lcs" in guidance
    assert "dp_contract.subfamily=\"lcs\"" in guidance
    assert "i、j、current" in guidance
    assert "text1[i-1]" in guidance
    assert "text2[j-1]" in guidance
    assert "formula" in guidance
    assert 'deps=["dp[i-1][j]", "dp[i][j-1]", "dp[i-1][j-1]", "text1[i-1]", "text2[j-1]"]' in guidance


def test_r7_lcs_guidance_keeps_initialized_base_cells_out_of_expected_targets():
    _context, guidance = _guidance_for(
        "lcs_length 失败：动态规划 失败：DP contract 缺少关键更新："
        "dp[0][0], dp[0][1], dp[0][2], dp[0][3], dp[1][0], dp[2][0]"
    )

    assert "LCS base row/column" in guidance
    assert "只放在 tracer.create(\"dp\") 的 state.dp" in guidance
    assert "不要把 dp[0][j] 或 dp[i][0] 放进 dp_contract.expected_targets" in guidance
    assert "expected_targets 只列真实 tracer.set 的 dp[i][j]" in guidance


def test_r7_string_sliding_window_guidance_uses_single_text_window_contract():
    _context, guidance = _guidance_for(
        "滑动窗口 失败：Family contract string 缺少 text/pattern 指针; "
        "Family contract string 缺少 text[i] / pattern[j] 字符 target; "
        "第 1 步字符串滑动窗口缺少 text 或 pointer target"
    )

    assert "string_sliding_window" in guidance
    assert "单串" in guidance
    assert "pattern" in guidance
    assert "window_counts" in guidance
    assert "pointer:left" in guidance
    assert "pointer:right" in guidance
    assert "text[i]" in guidance


def test_r7_string_sliding_window_duplicate_guidance_shrinks_before_best_update():
    _context, guidance = _guidance_for(
        "滑动窗口法 失败：第 11 步字符串滑动窗口包含重复字符; "
        "第 28 步字符串滑动窗口 window_counts 应为 {'b': 2, 'c': 1}; "
        "第 41 步字符串滑动窗口缺少 text 或 pointer target"
    )

    assert "先收缩到无重复再更新 best" in guidance
    assert "每次收缩都 set window_counts" in guidance
    assert "while window_counts[text[right]] > 1" in guidance
    assert "answer 事件 deps/targets 引用 text 或 pointer" in guidance
    assert "不要发布含重复字符的 state.window_counts" in guidance


def test_r7_string_sliding_window_guidance_keeps_counts_aligned_with_left_right():
    _context, guidance = _guidance_for(
        "滑动窗口 失败：第 7 步字符串滑动窗口 window_counts 应为 {'a': 2, 'b': 1, 'c': 1}; "
        "第 8 步字符串滑动窗口 window_counts 应为 {'b': 1, 'c': 1, 'a': 1}; "
        "第 21 步字符串滑动窗口 window_counts 应为 {'b': 2}"
    )

    assert "window_counts 必须等于 text[left:right+1] 的逐字符计数" in guidance
    assert "不要把收缩后的 window_counts 配上收缩前的 left/right" in guidance
    assert "重复帧" in guidance


def test_r7_tree_and_heap_residual_guidance_requires_current_node_and_heap_invariants():
    _tree_context, tree_guidance = _guidance_for(
        "后序遍历递归 失败：Family contract tree 缺少 expected_nodes 覆盖：3, 4, 5"
    )
    _heap_context, heap_guidance = _guidance_for(
        "小顶堆法 失败：failure_type=demo_algorithm_mismatch: 堆演示缺少 heap_type 不变量; "
        "failure_type=demo_algorithm_mismatch: 堆演示缺少 heap_top 或等价结构不变量"
    )
    guidance = tree_guidance + "\n" + heap_guidance

    assert "state.current" in guidance
    assert "node:<id>" in guidance
    assert "expected_nodes" in guidance
    assert "heap_type" in guidance
    assert "heap_top" in guidance
    assert "heap[0]" in guidance


def test_r7_lca_guidance_uses_tree_contract_instead_of_graph_dfs_contract():
    context, guidance = _guidance_for("后序遍历 DFS 失败：Graph contract DFS visited 未覆盖 expected_nodes")

    assert context[0]["family"] == "tree"
    assert "LCA/树递归固定短模板" in guidance
    assert "不要使用 graph_contract submode=dfs" in guidance
    assert 'family_contract={"family":"tree"' in guidance
    assert "return_value" in guidance
    assert "state.current" in guidance


def test_r7_lca_guidance_requires_initialization_create_tree_frame():
    _context, guidance = _guidance_for(
        "深度优先搜索 (DFS) 失败：failure_type=demo_key_step_missing: 缺少 initialization 阶段"
    )

    assert "LCA 第一帧必须是 initialization/create 阶段" in guidance
    assert 'tracer.create("tree")' in guidance
    assert 'state.phase="initialization"' in guidance
    assert "state 保留 tree、p、q" in guidance


def test_r7_range_timeout_guidance_requires_short_segment_and_fenwick_templates():
    _context, guidance = _guidance_for(
        "segment_tree_range_sum 失败：TimeoutError: LLM benchmark 超过 600 秒\n"
        "fenwick_tree_prefix_sum 失败：TimeoutError: LLM benchmark 超过 600 秒"
    )

    assert "紧凑修复" in guidance
    assert "segment_tree" in guidance
    assert "fenwick" in guidance
    assert "短模板" in guidance
    assert "少于 80 行" in guidance
    assert "6-10 个 events" in guidance


def test_r7_segment_tree_range_sum_guidance_syncs_parent_sums_after_update():
    _context, guidance = _guidance_for(
        "线段树 失败：第 2 步线段树节点 2-3 区间和应为 11; "
        "第 2 步线段树节点 root 区间和应为 14; 第 3 步线段树节点 root 区间和应为 14"
    )

    assert "线段树 update 后必须沿叶子到 root 同步 sum/value" in guidance
    assert "state.segment_tree.nodes[].meta.sum 必须等于当前 state.nums 区间和" in guidance
    assert "不要只更新叶子或 answer" in guidance
    assert "父区间和 root" in guidance


def test_r7_sparse_table_guidance_requires_complete_correct_table_in_state():
    _context, guidance = _guidance_for(
        "ST表解法 失败：第 0 步稀疏表 st[1][0] 应为 2; 第 0 步稀疏表 st[2][2] 应为 1"
    )

    assert "Sparse table state 必须包含完整正确 st 表" in guidance
    assert "st[0]=nums" in guidance
    assert "st[k][i]=min(st[k-1][i], st[k-1][i+2^(k-1)])" in guidance
    assert "nums=[5,2,7,3,6,1] 时 st[1]=[2,2,3,3,1]" in guidance


def test_r7_sparse_table_timeout_guidance_uses_compact_create_query_answer_template():
    _context, guidance = _guidance_for(
        "sparse_table_range_min 失败：TimeoutError: LLM benchmark 超过 1200 秒"
    )

    assert "Sparse table 超时必须用紧凑固定模板" in guidance
    assert "tracker_code 少于 80 行" in guidance
    assert "只保留 create st、query 两个区间、answer" in guidance
    assert "不要逐格展开所有 st build 事件" in guidance
    assert "create state 写完整 st" in guidance


def test_r7_z_algorithm_guidance_sets_final_z_value_after_expansion_only():
    _context, guidance = _guidance_for(
        "Z 算法 失败：第 2 步 Z Algorithm z[4] 应为 3; 第 4 步 Z Algorithm z[4] 应为 3"
    )

    assert "text=\"aabcaabx\"" in guidance
    assert "z[4]=3" in guidance
    assert "不要在扩展完成前 tracer.set(\"z[4]\")" in guidance
    assert "先 compare text[0]/text[4]、text[1]/text[5]、text[2]/text[6]" in guidance
    assert "扩展完成后再 tracer.set(\"z[4]\"" in guidance


def test_r7_trie_create_node_guidance_requires_explicit_create_node_event():
    _context, guidance = _guidance_for(
        "字典树前缀统计 失败：Family contract trie 缺少关键事件：create_node"
    )

    assert "role=\"create_node\"" in guidance
    assert "tracer.set(\"node:<id>\"" in guidance
    assert "reason/action 含 create_node/创建新节点" in guidance
    assert "state.trie.nodes" in guidance
    assert "state.trie.edges" in guidance


def test_r7_sparse_table_invalid_st_target_guidance_limits_targets_to_existing_cells():
    _context, guidance = _guidance_for(
        "稀疏表 (Sparse Table) 失败：第 1 步引用了不存在的索引 target：st[2][1]; 第 2 步引用了不存在的索引 target：st[2][1]"
    )

    assert "不要引用不存在的 st[2][1]" in guidance
    assert "nums=[5,2,7,3,6,1] 时 st[2] 只有 st[2][0]、st[2][1]、st[2][2]" in guidance
    assert "如果 state.st[2] 长度不足 2，就不能把 st[2][1] 放进 target/deps" in guidance
    assert "create state 写完整 st" in guidance


def test_r7_full_dp_residual_guidance_covers_difference_subset_tsp_digit_and_floyd():
    _diff_context, diff_guidance = _guidance_for("差分数组 失败：第 5 步 diff[0] 应为 1; 第 6 步 diff[2] 应为 0")
    _dp_context, dp_guidance = _guidance_for(
        "0-1背包动态规划 失败：第 0 步 subset-sum dp[0] 必须为 True; 第 1 步 DP contract 关键更新缺少 deps\n"
        "状态压缩动态规划 失败：DP contract 缺少关键更新：ans\n"
        "前缀组合计数 失败：failure_type=demo_key_step_missing: DP 演示缺少状态转移写入帧\n"
        "Floyd-Warshall 算法 失败：failure_type=demo_key_step_missing: DP 演示缺少状态转移写入帧"
    )
    guidance = diff_guidance + "\n" + dp_guidance

    assert "diff[0]=nums[0]" in guidance
    assert "diff[i]=nums[i]-nums[i-1]" in guidance
    assert "diff[left]+=delta" in guidance
    assert "dp[0]=True" in guidance
    assert "capacity_index" in guidance
    assert "dp_contract.expected_targets" in guidance
    assert "ans" in guidance
    assert "full_mask" in guidance
    assert "tracer.set" in guidance
    assert "dist[i][j]" in guidance


def test_r7_difference_array_guidance_reconstructs_final_nums_targets():
    _context, guidance = _guidance_for(
        "差分数组 失败：Array pointer contract 缺少关键更新：nums[0], nums[1], nums[2]"
    )

    assert "差分数组最终重建必须逐个 tracer.set(\"nums[i]\")" in guidance
    assert "expected_targets 包含 nums[0], nums[1], nums[2]" in guidance
    assert "running_sum" in guidance
    assert "不要只更新 diff" in guidance


def test_r7_dijkstra_relax_guidance_requires_node_and_edge_deps():
    _context, guidance = _guidance_for(
        "Dijkstra 最小堆解法 失败：failure_type=demo_missing_deps: step 2 图首次访问或 relax 缺少 deps"
    )

    assert "Dijkstra relax 必须用 tracer.set(\"dist[v]\")" in guidance
    assert 'deps=["node:u", "node:v", "edge:u->v", "dist[u]"]' in guidance
    assert "state.current/neighbor" in guidance
    assert "old_dist/new_dist/edge_weight" in guidance


def test_r7_remaining_dp_residual_guidance_is_strict_for_base_and_transition_sets():
    _context, guidance = _guidance_for(
        "0-1背包解法 失败：第 1 步 DP contract 关键更新缺少 deps; "
        "第 1 步 DP contract 转移事件缺少可复原公式; 第 0 步 subset-sum dp[0] 必须为 True; "
        "状态压缩动态规划 失败：第 1 步 DP contract 关键更新缺少 deps"
    )

    assert "不要把 set dp[0] 写成无 deps 的关键更新" in guidance
    assert 'deps=["dp"]' in guidance
    assert "formula=\"dp[0]=True\"" in guidance
    assert "每一个 tracer.set" in guidance
    assert "初始化 set 也必须带 deps" in guidance
    assert "dp[1<<start][start]" in guidance
    assert "state 保留 nums" in guidance
    assert 'deps=["dp[c]","dp[c-weight]","nums[i]"]' in guidance
    assert "reason/teaching 提到 nums" in guidance


def test_r7_permutation_record_guidance_requires_answer_role_and_path_deps():
    _context, guidance = _guidance_for(
        "回溯法 失败：Family contract backtracking 缺少关键事件：record"
    )

    assert 'record 事件必须 role="answer"' in guidance
    assert "state.answer 包含新记录" in guidance
    assert 'deps=["path"]' in guidance
    assert "reason/action 含 record 或 记录" in guidance


def test_r7_permutation_frame_ids_must_not_contain_spaces():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：回溯法: 第 4 步 target 含空格：frame:dfs([1, 2]); "
        "严格模式拒绝 warning：回溯法: 第 13 步 target 含空格：frame:dfs([2, 1])"
    )

    assert "frame id 禁止包含空格" in guidance
    assert "不要用 str(path)" in guidance
    assert "frame:dfs(1_2)" in guidance
    assert "enter 和 exit 必须使用完全相同的 frame id" in guidance


def test_r7_knapsack_create_initialization_guidance_forbids_set_only_base_case():
    _context, guidance = _guidance_for(
        "0-1背包解法 失败：DP contract 缺少初始化事件：必须用 create 事件给出 DP 容器初始状态"
    )

    assert "必须用 tracer.create(\"dp\")" in guidance
    assert "state.dp[0]=True" in guidance
    assert "不要只用 tracer.set(\"dp[0]\")" in guidance
    assert "create 事件" in guidance
    assert "dp_contract" in guidance


def test_r7_generation_json_failures_request_short_tracker_template():
    _context, guidance = _guidance_for(
        "状态压缩动态规划 失败：LLMJsonError: 模型返回内容不是合法 JSON：Unterminated string starting at: line 12 column 23; preview={...<truncated>\n"
        "Kahn算法（BFS） 失败：LLMJsonError: 模型返回空内容，无法解析 JSON"
    )

    assert "1 个 variant" in guidance
    assert "6-10 个 events" in guidance
    assert "短 tracker_code" in guidance
    assert "不要复制长代码" in guidance
    assert "TSP" in guidance
    assert "拓扑排序" in guidance


def test_r7_full_graph_residual_guidance_requires_edge_check_deps_and_enqueue_reason():
    _context, guidance = _guidance_for(
        "广度优先搜索 (BFS) 失败：Graph contract BFS 缺少边检查事件; failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge\n"
        "深度优先搜索解法 失败：failure_type=demo_missing_deps: step 2 图首次访问或 relax 缺少 deps\n"
        "BFS 染色法 失败：failure_type=demo_key_step_missing: 图演示缺少边检查帧\n"
        "BFS 染色法 失败：第 1 步 dist 包含不可达节点：A\n"
        "Kahn算法（BFS） 失败：第 3 步 Graph contract topological_sort 缺少入队原因\n"
        "匈牙利算法 失败：failure_type=demo_key_step_missing: 图演示缺少边检查帧"
    )

    assert "tracer.compare" in guidance
    assert "edge:u->v" in guidance
    assert "check_edge" in guidance
    assert "deps=[\"node:u\", \"node:v\", \"edge:u->v\"]" in guidance
    assert "首次访问" in guidance
    assert "submode=bipartite_coloring" in guidance
    assert "不要使用 dist" in guidance
    assert "color" in guidance
    assert "indegree[v]==0" in guidance
    assert "入队" in guidance


def test_r7_bfs_first_visit_guidance_requires_node_and_edge_deps():
    _context, guidance = _guidance_for(
        "graph_bfs 失败：failure_type=demo_missing_deps: step 3 图首次访问或 relax 缺少 deps"
    )

    assert 'tracer.set("dist[neighbor]")' in guidance
    assert 'deps=["node:current", "node:neighbor", "edge:current->neighbor"]' in guidance
    assert "dist[current]+1" in guidance
    assert "parent[neighbor]=current" in guidance
    assert "不要只写 deps=[\"dist[current]\", \"edge:current->neighbor\"]" in guidance


def test_r7_zero_one_bfs_guidance_requires_first_visit_relax_deps():
    context, guidance = _guidance_for(
        "zero_one_bfs_shortest_path 失败：0-1 BFS 失败：failure_type=demo_missing_deps: "
        "step 1 图首次访问或 relax 缺少 deps"
    )

    assert context[0]["family"] == "graph"
    assert context[0]["graph_submode"] == "zero_one_bfs"
    assert "submode=zero_one_bfs" in guidance
    assert "0/1 权边" in guidance
    assert "first_visit" in guidance
    assert "relax" in guidance
    assert 'deps=["node:u", "node:v", "edge:u->v"]' in guidance
    assert "dist[u]" in guidance
    assert "edge_weight" in guidance
    assert "push_front" in guidance
    assert "push_back" in guidance


def test_r7_bellman_ford_node_warning_guidance_repeats_graph_nodes_edges():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：Bellman-Ford 算法: 第 1 步引用的节点未在状态或输入图中出现：node:A; "
        "第 1 步引用的节点未在状态或输入图中出现：node:B"
    )

    assert "Bellman-Ford 固定短模板" in guidance
    assert "state.graph.nodes" in guidance
    assert "state.graph.edges" in guidance
    assert "每个 relax/check 事件都重复完整 state.graph" in guidance


def test_r7_two_sum_hash_guidance_forbids_unsupported_hash_family_contract():
    _context, guidance = _guidance_for(
        "哈希表一次遍历 失败：Family contract 未支持的 family：hash; "
        "failure_type=demo_key_step_missing: 缺少 initialization 阶段"
    )

    assert "Two Sum 哈希固定短模板" in guidance
    assert "不要设置 family_contract family=hash" in guidance
    assert "hash_contract" in guidance
    assert "seen[need]" in guidance
    assert "Two Sum 第一帧必须是 initialization/create 阶段" in guidance
    assert 'tracer.create("seen")' in guidance
    assert "state.phase=\"initialization\"" in guidance
    assert "state.seen={}" in guidance


def test_r7_residual_guidance_covers_bfs_parent_dfs_frontier_matching_and_digit_json_object():
    _bfs_context, bfs_guidance = _guidance_for("graph_bfs 失败：第 13 步 BFS 首次发现 node:B 来源应为上一层相邻节点，实际为 B")
    _components_context, components_guidance = _guidance_for("graph_connected_components 失败：Graph contract DFS 必须记录 stack 或 recursion frame frontier")
    _matching_context, matching_guidance = _guidance_for(
        "bipartite_matching 失败：Graph contract DFS 必须记录 stack 或 recursion frame frontier; "
        "第 12 步 匹配不一致：match[R1]=L1 但 match[L1]=R2"
    )
    _digit_context, digit_guidance = _guidance_for("digit_dp_no_seven 失败：ValueError: LLM 顶层输出必须是 JSON object，实际为 str")
    _digit_timeout_context, digit_timeout_guidance = _guidance_for("digit_dp_no_seven 失败：TimeoutError: LLM benchmark 超过 600 秒")
    _digit_shortcut_context, digit_shortcut_guidance = _guidance_for(
        "digit_dp_no_seven 九进制转换法 失败：第 1 步 DP contract state 缺少循环变量：i, j, k, capacity_index, capacity, mask, digit, current; DP contract 缺少关键更新：ans"
    )
    guidance = "\n".join([bfs_guidance, components_guidance, matching_guidance, digit_guidance, digit_timeout_guidance, digit_shortcut_guidance])

    assert 'tracer.set("dist[neighbor]")' in guidance
    assert "first_visit" in guidance
    assert "parent[neighbor]=current" in guidance
    assert "不要写 parent[neighbor]=neighbor" in guidance
    assert "stack 或 frame:dfs" in guidance
    assert "connected_components" in guidance
    assert "二分图匹配" in guidance
    assert "match[right]=left" in guidance
    assert "旧 match[R1]=L1 必须清除或改为 match[R1]=L2" in guidance
    assert "顶层" in guidance
    assert "JSON object" in guidance
    assert "digit_dp" in guidance
    assert "tracker_code 少于 80 行" in guidance
    assert "不要使用九进制转换法" in guidance
    assert "只保留 create dp、set dp[1]、set dp[2]、set ans" in guidance
    assert "dp[1]=2" in guidance
    assert "dp[2]=18" in guidance
    assert 'tracer.set("ans")' in guidance


def test_r7_connected_components_guidance_keeps_component_connected_only():
    _context, guidance = _guidance_for(
        "DFS 连通分量 失败：第 9 步 Graph contract connected_components component 包含非连通节点; "
        "第 13 步 Graph contract connected_components components 包含跨分量节点"
    )

    assert "state.component 只能是当前正在遍历的连通分量" in guidance
    assert "不要把多个 component 合并进 state.component" in guidance
    assert "已完成分量放 state.components" in guidance
    assert "样例 A-B 和 C 必须分成 ['A','B'] 与 ['C']" in guidance
    assert "state.components 的每个内层列表也必须是一个连通分量" in guidance
    assert "不要发布 [['A','B','C']]" in guidance
    assert "开始遍历 C 时重置 state.component=['C']" in guidance


def test_r7_bipartite_matching_guidance_forbids_unpaired_bare_dfs_frames():
    _context, guidance = _guidance_for(
        "匈牙利算法 (DFS增广路) 失败：第 17 步递归 frame frame:dfs 未进入就退出; 递归 frame frame:dfs 缺少 exit"
    )

    assert "不要使用裸 frame:dfs" in guidance
    assert "frame:dfs(L1)" in guidance
    assert "每个 tracer.exit 的 target 必须和之前 tracer.enter 完全相同" in guidance
    assert "简单匹配过程建议不用 enter/exit" in guidance


def test_r7_topological_sort_guidance_keeps_indegree_counts_until_all_predecessors_processed():
    _context, guidance = _guidance_for(
        "Kahn算法（BFS） 失败：第 13 步 Graph contract topological_sort 缺少入队原因; "
        "第 17 步 Graph contract topological_sort indegree[D] 应为 2，实际为 1"
    )

    assert "初始化 indegree[D]" in guidance
    assert "所有入边数量" in guidance
    assert "每条 edge:u->v 只 decrement 一次" in guidance
    assert "所有前驱处理完成后" in guidance


def test_r7_topological_sort_process_repair_stays_compact_to_avoid_empty_json():
    _context, guidance = _guidance_for(
        "Kahn算法（BFS） 失败：Graph contract topological_sort 缺少入队原因; "
        "第 17 步 Graph contract topological_sort indegree[D] 应为 2，实际为 1"
    )

    assert "拓扑排序每次 repair 都必须保持短 tracker_code" in guidance
    assert "6-10 个 events" in guidance
    assert "不要重写成长篇 tracker" in guidance
    assert "create graph/indegree" in guidance
    assert "mark topo_order" in guidance


def test_r7_data_structure_guidance_covers_trie_linked_heap_union_find_and_range():
    messages = [
        "Trie prefix_count 缺少 count / prefix_count 证据; Family contract trie 缺少字符路径证据; Family contract trie 缺少关键事件：create_node",
        "严格模式拒绝 warning：迭代反转链表: 第 2 步 deps 未出现在 state 中：node_0",
        "小顶堆解法 失败：Family contract heap 缺少 pop 事件; Family contract heap 缺少关键事件：pop",
        "并查集 失败：Family contract 未支持的 family：union_find",
        "线段树 失败：Family contract 未支持的 family：data_structure",
    ]
    _context, guidance = _guidance_for("\n".join(messages))

    assert "node:<id>" in guidance
    assert "node_0" in guidance
    assert "tracer.pop" in guidance
    assert "expected_events" in guidance
    assert "union_find" in guidance
    assert "family_contract" in guidance
    assert "parent" in guidance
    assert "rank" in guidance or "size" in guidance
    assert "range_structure" in guidance
    assert "segment_tree" in guidance
    assert "fenwick" in guidance


def test_r7_scene_and_range_guidance_handles_trie_node_none_and_segment_tree_mark_evidence():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：字典树(Trie)前缀统计: 第 1 帧 edge source 不在对象集合：node:None; "
        "第 1 帧 edge target 引用 state 中不存在的 node：node:None; "
        "线段树 失败：第 3 步 mark 缺少可观测过程证据：需要 deps、before/after/value 或可解析的状态变化"
    )

    assert "node:None" in guidance
    assert "禁止" in guidance
    assert "root" in guidance
    assert "node:<id>" in guidance
    assert "mark" in guidance
    assert "value" in guidance
    assert "deps" in guidance
    assert "answer" in guidance


def test_r7_scene_guidance_requires_state_struct_for_every_node_ref():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：线段树: 第 1 步引用的节点未在状态或输入图中出现：node:5; "
        "严格模式拒绝 warning：迭代反转法: 第 1 步引用的节点未在状态或输入图中出现：node:0"
    )

    assert "每个引用 node:<id> 的事件" in guidance
    assert "state.segment_tree.nodes" in guidance
    assert "state.linked_list.nodes" in guidance
    assert "id" in guidance


def test_r7_trie_guidance_requires_char_target_or_state_for_each_path_step():
    _context, guidance = _guidance_for("字典树(Trie)解法 失败：Family contract trie 缺少字符路径证据")

    assert "char" in guidance
    assert "current_char" in guidance
    assert "words[i][j]" in guidance
    assert "prefix[j]" in guidance
    assert "state.words" in guidance
    assert "state.prefix" in guidance
    assert "node:<id>" in guidance


def test_r7_trie_missing_words_index_guidance_prefers_char_targets_or_visible_state():
    _context, guidance = _guidance_for(
        "字典树前缀统计 失败：第 1 步引用了不存在的索引 target：words[0][0]; "
        "第 2 步引用了不存在的索引 target：prefix[0]"
    )

    assert "char:<word_index>:<char_index>" in guidance
    assert "不要把 words[0][0]" in guidance
    assert "state.words" in guidance
    assert "state.prefix" in guidance
    assert "state.current_char" in guidance


def test_r7_trie_prefix_count_guidance_requires_observable_count_state():
    _context, guidance = _guidance_for("字典树前缀统计 失败：Trie prefix_count 缺少 count / prefix_count 证据")

    assert "state.prefix_count" in guidance
    assert "node.meta.count" in guidance
    assert "node.meta.prefix_count" in guidance
    assert "pass_count" in guidance
    assert "不能只在 reason 写 count" in guidance
    assert "query 前缀终点 node:<id>" in guidance
    assert "value=prefix_count" in guidance


def test_r7_trie_empty_prefix_guidance_uses_root_prefix_count_as_answer():
    _context, guidance = _guidance_for(
        "字典树前缀统计 失败：第 1 步 Trie prefix_count 应为 3，实际为 0; "
        "第 4 步 Trie prefix_count 应为 3，实际为 0"
    )

    assert "prefix 为空时答案来自 root.meta.prefix_count" in guidance
    assert "root.meta.prefix_count=len(words)" in guidance
    assert "不要把 root prefix_count 写成 0" in guidance


def test_r7_trie_empty_word_guidance_marks_root_terminal():
    _context, guidance = _guidance_for(
        "字典树前缀统计 失败：Family contract trie 缺少 terminal 标记; Family contract trie 缺少关键事件：terminal"
    )

    assert "words 包含空串时 root 必须 terminal/is_word=True" in guidance
    assert "tracer.mark(\"node:root\")" in guidance
    assert "terminal 事件" in guidance
    assert "root.meta.terminal" in guidance


def test_r7_range_contract_guidance_and_validator_recognize_update_event():
    _context, guidance = _guidance_for("线段树解法 失败：Family contract range_structure 缺少关键事件：update")

    assert "update" in guidance
    assert "更新" in guidance
    assert "expected_events" in guidance

    contract = {"family": "range_structure", "submode": "segment_tree", "expected_events": ["build", "update", "query"]}
    segment_tree = {"nodes": [{"id": "root", "label": "[0,0]", "meta": {"l": 0, "r": 0, "sum": 3}}], "edges": []}
    raw_trace = _family_contract_trace(
        "线段树 update 合同正例",
        {"nums": [3]},
        3,
        [
            _family_contract_event(0, "create", ["segment_tree"], state={"nums": [3], "segment_tree": segment_tree, "family_contract": contract}, reason="build 初始化线段树。"),
            _family_contract_event(1, "set", ["node:root"], value=3, deps=["nums[0]"], state={"nums": [3], "segment_tree": segment_tree, "family_contract": contract}, reason="update 更新叶子节点和区间和。"),
            _family_contract_event(2, "mark", ["node:root"], value=3, deps=["node:root"], role="answer", state={"nums": [3], "segment_tree": segment_tree, "answer": 3, "family_contract": contract}, reason="query 查询区间和。"),
        ],
    )
    assert not _process_errors(raw_trace)


def test_r7_linked_list_execution_guidance_initializes_next_node_name():
    _context, guidance = _guidance_for("迭代反转法 失败：trace 执行失败：NameError: name 'next' is not defined")

    assert "next_node" in guidance
    assert "不要使用未定义的 next" in guidance
    assert "while" in guidance
    assert "单调推进" in guidance


def test_r7_segment_tree_node_none_guidance_requires_non_null_edge_endpoints():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：线段树基础实现: 第 0 帧 edge source 不在对象集合：node:None; "
        "严格模式拒绝 warning：线段树基础实现: 第 0 帧 edge target 引用 state 中不存在的 node：node:None"
    )

    assert "state.segment_tree.edges" in guidance
    assert '["root", "left"]' in guidance
    assert '{"from": "root", "to": "left"}' in guidance
    assert "from/to/source/target 不能为 None" in guidance
    assert "每条 edge 的两个端点都必须出现在 state.segment_tree.nodes" in guidance


def test_r7_linked_list_nameerror_next_guidance_forbids_builtin_next_variable():
    _context, guidance = _guidance_for("迭代反转法 失败：trace 执行失败：NameError: name 'next' is not defined")

    assert "Python 内置 next 不是链表变量" in guidance
    assert "nxt = current" in guidance
    assert "next_node = current" in guidance
    assert "不要写 current = next" in guidance


def test_r7_invalid_target_guidance_rewrites_input_and_result_index_targets():
    context, guidance = _guidance_for(
        "回溯法 失败：第 0 步引用了不存在的索引 target：nums[0]; "
        "二进制掩码法 失败：第 2 步引用了不存在的索引 target：result[1]; "
        "二进制掩码枚举 失败：第 3 步引用了不存在的索引 target：res[2]"
    )

    assert {item["repair_category"] for item in context} == {"target_or_deps"}
    assert "nums[0]" in guidance
    assert "result[1]" in guidance
    assert "输入数组只读" in guidance
    assert "不要把 result[i]" in guidance
    assert "不要把 res[i]" in guidance
    assert "不要把 result[i]" in guidance
    assert "位掩码子集固定短模板" in guidance
    assert "不要使用 res[i]/result[i] 作为 target/deps" in guidance
    assert 'tracer.create("subsets")' in guidance
    assert 'tracer.set("subset")' in guidance
    assert 'tracer.set("subsets")' in guidance
    assert 'tracer.mark("answer")' in guidance
    assert "answer" in guidance
    assert "recursion_tree" in guidance or "path" in guidance


def test_r7_bitmask_subsets_guidance_keeps_subset_deps_visible_in_state():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：位掩码法: 第 3 步 deps 未出现在 state 中：subset; "
        "严格模式拒绝 warning：位掩码法: 第 13 步 deps 未出现在 state 中：subsets"
    )

    assert "位掩码子集固定短模板" in guidance
    assert "deps 写 subset 时同一事件 state.subset 必须存在" in guidance
    assert "deps 写 subsets 时同一事件 state.subsets 必须存在" in guidance
    assert "也可以把 tracer.set(\"subsets\") 的 deps 改为 [\"mask\"]" in guidance


def test_r7_linked_list_guidance_requires_next_prev_in_node_meta_and_state():
    _context, guidance = _guidance_for("迭代反转法 失败：Family contract linked_list 缺少 next/prev 状态")

    assert "linked_list.nodes" in guidance
    assert "meta.next" in guidance
    assert "current" in guidance
    assert "prev" in guidance
    assert "next" in guidance
    assert "edge:u->v" in guidance


def test_r7_linked_list_node_warning_guidance_repeats_full_linked_list_state_per_event():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：迭代反转法: 第 2 步引用的节点未在状态或输入图中出现：node:0; "
        "严格模式拒绝 warning：迭代反转法: 第 2 步引用的节点未在状态或输入图中出现：node:1"
    )

    assert "不要只在初始化 state 写 linked_list" in guidance
    assert "每个引用 node:0/node:1 的事件" in guidance
    assert "state.linked_list.nodes" in guidance
    assert '"id": "0"' in guidance
    assert '"id": "1"' in guidance


def test_r7_linked_list_guidance_requires_explicit_link_change_and_no_blank_next_edge():
    _context, guidance = _guidance_for(
        "迭代反转 失败：Family contract linked_list 缺少 next/prev 改变事件; "
        "迭代反转法 失败：第 0 步 链表 next 状态缺少对应 edge:1->"
    )

    assert "link_change 事件" in guidance
    assert 'tracer.link("edge:current->prev")' in guidance
    assert 'tracer.unlink("edge:current->old_next")' in guidance
    assert '不要写 meta.next=""' in guidance
    assert "用 JSON null 或省略 next" in guidance


def test_r7_linked_list_guidance_requires_observable_set_or_move_evidence():
    _context, guidance = _guidance_for(
        "迭代反转法 失败：第 3 步 set 缺少可观测过程证据：需要 deps、before/after/value 或可解析的状态变化"
    )

    assert "每个 tracer.set 必须带 value、deps 或 before/after" in guidance
    assert "不要用空 set 只改 reason" in guidance
    assert "current/prev/next 指针移动用 tracer.move" in guidance
    assert "link_change 用 tracer.link/tracer.unlink" in guidance


def test_r7_linked_list_current_guidance_advances_to_saved_next_node():
    _context, guidance = _guidance_for(
        "迭代反转法 失败：第 3 步 链表 current 应为 1，实际为 0; "
        "第 8 步 链表 current 应为 2，实际为 1"
    )

    assert "下一轮第一帧 pointer:current 才写 next_node" in guidance
    assert "prev 必须移动到 old_current" in guidance
    assert "不要在本轮继续发布旧 current" in guidance
    assert "先保存 next_node，再改 current.next" in guidance


def test_r7_linked_list_guidance_forbids_half_updated_next_edges():
    _context, guidance = _guidance_for(
        "迭代反转 失败：第 2 步 链表 next 状态缺少对应 edge:0->1; "
        "第 6 步 链表 next 状态缺少对应 edge:1->2"
    )

    assert "不要发布半更新链表状态" in guidance
    assert "如果 meta.next 仍是 old_next，就必须保留 edge:current->old_next" in guidance
    assert "如果移除了 edge:current->old_next，就必须同时把 meta.next 改为 null 或 prev" in guidance
    assert "事件 state 表示动作后的完整一致状态" in guidance


def test_r7_linked_list_guidance_processes_old_current_before_advancing():
    _context, guidance = _guidance_for("迭代反转法 失败：第 3 步 链表 current 应为 0，实际为 1")

    assert "每轮 link/unlink/set 处理的 current 必须仍是 old_current" in guidance
    assert "不要在完成 old_current 的 link_change 前把 current 写成 next_node" in guidance
    assert "第一轮必须从 head/current=0 开始" in guidance
    assert "下一轮第一帧 pointer:current 才写 next_node" in guidance


def test_r7_linked_list_current_move_guidance_uses_before_state_then_next_state():
    _context, guidance = _guidance_for("迭代反转 失败：第 3 步 链表 current 应为 1，实际为 0")

    assert 'tracer.move("pointer:current") 是每轮开始帧' in guidance
    assert "state.current 写本轮 old_current" in guidance
    assert "state.next 写 next_node" in guidance
    assert "下一轮第一帧 pointer:current 才写 next_node" in guidance
    assert "每个节点只发布一次 pointer:current move" in guidance


def test_r7_linked_list_expansion_guidance_advances_current_to_second_node():
    _context, guidance = _guidance_for(
        "reverse_linked_list_expansion 失败：迭代反转 失败：第 3 步 链表 current 应为 1，实际为 0"
    )

    assert "两节点扩展样例 values=[1,2]" in guidance
    assert "保存 next_node=\"1\"" in guidance
    assert "处理完 old_current=\"0\" 后，下一帧 current 必须是 \"1\"" in guidance
    assert "不要在下一轮 pointer:current frame 继续写 current=\"0\"" in guidance


def test_r7_linked_list_three_node_guidance_advances_current_every_round():
    _context, guidance = _guidance_for(
        "迭代反转 失败：第 3 步 链表 current 应为 1，实际为 0; 第 7 步 链表 current 应为 2，实际为 1"
    )

    assert "三节点样例 values=[1,2,3]" in guidance
    assert "current 帧顺序必须是 \"0\" -> \"1\" -> \"2\"" in guidance
    assert "处理完 old_current=\"1\" 后，下一帧 current 必须是 \"2\"" in guidance


def test_r7_full_structure_tree_backtracking_math_guidance_covers_residuals():
    messages = [
        "单调栈解法 失败：Family contract range_structure 缺少 segment_tree/fenwick/sparse_table state",
        "递归中序遍历 失败：Family contract tree 缺少子树返回值或聚合结果; 树形DP（后序遍历） 失败：第 0 步树形 DP dp_take[1] 应为 3",
        "字典树前缀统计 失败：第 7 步 Trie prefix_count[node_1] 应为 4，实际为 3",
        "严格模式拒绝 warning：并查集: 第 2 步 deps 未出现在 state 中：union_find.parent[0]",
        "Andrew 单调链算法 失败：failure_type=demo_key_step_missing: 回溯演示缺少选择进入帧",
        "辗转相除法 失败：第 2 步 compare 缺少 deps/value，无法说明比较依据",
        "贪心算法 失败：第 3 步 贪心 jump_game reach 应为 3，实际为 1",
        "回溯法 失败：第 1 步回溯搜索树应只有一个根",
        "迭代反转法 失败：第 0 步 链表 next 状态缺少对应 edge:0->1",
    ]
    guidance = "\n".join(_guidance_for(message)[1] for message in messages)

    assert "daily_temperatures" in guidance
    assert "不要使用 range_structure" in guidance
    assert "return_values" in guidance
    assert "aggregate" in guidance
    assert "dp_take[current]" in guidance
    assert "dp_skip[current]" in guidance
    assert "node.label 必须是单个字符" in guidance
    assert "union_find.parent[0]" in guidance
    assert "deps 改用 node:0" in guidance
    assert "tracer.enter" in guidance
    assert "tracer.exit" in guidance
    assert "compare 必须带 deps 或 value" in guidance
    assert "previous_reach" in guidance
    assert "candidate_reach" in guidance
    assert "搜索树只能有一个 root" in guidance
    assert "meta.next" in guidance
    assert "edge:0->1" in guidance


def test_r7_jump_game_unreachable_guidance_stops_with_false_answer():
    _context, guidance = _guidance_for(
        "贪心算法 失败：第 5 步 贪心 jump_game 扫描到不可达下标 i=2, reach=1; "
        "第 6 步 贪心 jump_game reach 应为 3，实际为 1"
    )

    assert 'i > previous_reach 时立即 role="answer"' in guidance
    assert "value=False" in guidance
    assert "停止 trace" in guidance
    assert "不要继续扫描不可达下标" in guidance


def test_r7_jump_game_guidance_updates_reach_on_first_scanned_index():
    _context, guidance = _guidance_for(
        "贪心算法 失败：第 1 步 贪心 jump_game reach 应为 1，实际为 0; "
        "第 5 步 贪心 jump_game reach 应为 3，实际为 1"
    )

    assert "初始化 create 可以用 i=-1" in guidance
    assert "第一个扫描事件若 i=0" in guidance
    assert "previous_reach=0" in guidance
    assert "candidate_reach=nums[0]" in guidance
    assert "reach=nums[0]" in guidance
    assert "state.i=2 只能出现在最终 answer=False 帧" in guidance


def test_r7_tree_dp_demo_guidance_requires_set_events_for_take_and_skip():
    _context, guidance = _guidance_for(
        "树形动态规划 失败：failure_type=demo_key_step_missing: DP 演示缺少状态转移写入帧"
    )

    assert "tracer.set(\"dp_take[current]\")" in guidance
    assert "tracer.set(\"dp_skip[current]\")" in guidance
    assert "不要只在 state 里更新 dp_take/dp_skip" in guidance
    assert "role=answer" in guidance


def test_r7_tree_dp_mark_and_answer_position_guidance_requires_observable_dp_targets():
    _context, guidance = _guidance_for(
        "树形动态规划 失败：第 3 步 mark 缺少可观测过程证据：需要 deps、before/after/value 或可解析的状态变化; "
        "DP contract 答案位置未明确：role=answer 事件必须引用 1"
    )

    assert "mark 必须带 value" in guidance
    assert "deps=[\"dp_take[current]\", \"dp_skip[current]\"]" in guidance
    assert "不要把 answer_position 写成裸根节点" in guidance
    assert "dp_take[1]" in guidance
    assert "dp_skip[1]" in guidance
    assert "role=answer" in guidance


def test_r7_tree_dp_guidance_forbids_partial_parent_dp_and_requires_answer_set():
    _context, guidance = _guidance_for(
        "树形动态规划 失败：DP contract 缺少关键更新：answer; "
        "第 2 步树形 DP dp_skip[1] 应为 3; 第 4 步树形 DP dp_skip[2] 应为 11"
    )

    assert "后序完成前不要在 state.dp_take/dp_skip 中写当前父节点的半成品" in guidance
    assert "先完成所有 child 的 dp_take/dp_skip" in guidance
    assert "再 set dp_take[current]" in guidance
    assert "再 set dp_skip[current]" in guidance
    assert 'tracer.set("answer")' in guidance
    assert "deps=[\"dp_take[root]\", \"dp_skip[root]\"]" in guidance


def test_r7_convex_hull_final_frame_guidance_requires_cleared_backtracking_path():
    _context, guidance = _guidance_for(
        "Andrew 单调链算法 失败：failure_type=demo_state_jump: 回溯最终答案帧仍停留在未撤销路径上"
    )

    assert "Andrew/凸包" in guidance
    assert "最终答案帧" in guidance
    assert "不要使用 backtracking family_contract" in guidance
    assert "geometry.hull" in guidance
    assert "不能保留 pending/current/candidate" in guidance
    assert "最终 role=answer" in guidance


def test_r7_convex_hull_guidance_uses_geometry_contract_not_backtracking():
    context, guidance = _guidance_for(
        "Andrew单调链算法 失败：第 8 步 compare 缺少 deps/value，无法说明比较依据; "
        "Family contract backtracking 缺少 choose 事件; Family contract backtracking 缺少 record 事件; "
        "第 13 步 Family contract backtracking path 跳变"
    )

    assert context[0]["family"] == "geometry"
    assert "不要使用 backtracking family_contract" in guidance
    assert "geometry.hull" in guidance
    assert "compare 带 value=叉积" in guidance
    assert 'deps=["geometry"]' in guidance
    assert "不要在 deps 使用 point:" in guidance
    assert "最终 role=answer" in guidance


def test_r7_convex_hull_point_deps_guidance_repeats_geometry_points_per_event():
    context, guidance = _guidance_for(
        "严格模式拒绝 warning：Andrew 单调链算法: 第 3 步 deps 未出现在 state 中：point:0; "
        "第 3 步 deps 未出现在 state 中：point:1; 第 3 步 deps 未出现在 state 中：point:2"
    )

    assert context[0]["family"] == "geometry"
    assert "point:0" in guidance
    assert "不要在 deps 使用 point:" in guidance
    assert 'deps=["geometry"]' in guidance
    assert "每个 compare/pop/answer 事件都重复完整 state.geometry.points" in guidance


def test_r7_convex_hull_point_named_deps_require_matching_point_ids():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：Andrew 单调链算法: 第 3 步 deps 未出现在 state 中：point:p0; "
        "第 3 步 deps 未出现在 state 中：point:p1; 第 3 步 deps 未出现在 state 中：point:p2"
    )

    assert "point:p0" in guidance
    assert "不要在 deps 使用 point:" in guidance
    assert 'deps=["geometry"]' in guidance
    assert "point:p0 只能作为 target/高亮对象" in guidance


def test_r7_convex_hull_guidance_forbids_geometry_family_contract_and_invalid_hull_frames():
    _context, guidance = _guidance_for(
        "Andrew 单调链算法 失败：第 12 步 hull 不是一致转向的凸多边形; "
        "Family contract 未支持的 family：geometry"
    )

    assert "不要设置 family_contract" in guidance
    assert "family=geometry" in guidance
    assert "中间候选只放 geometry.stack" in guidance
    assert "geometry.hull 只放最终或已验证凸包" in guidance
    assert "最终 hull 顺序必须和 solve/expected answer 一致" in guidance


def test_r7_convex_hull_final_answer_deps_use_geometry_not_points():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：Andrew 单调链算法: 第 18 步 deps 未出现在 state 中：point:p0; "
        "第 18 步 deps 未出现在 state 中：point:p2; 第 18 步 deps 未出现在 state 中：point:p3"
    )

    assert "最终答案 deps 也必须是 [\"geometry\"]" in guidance
    assert "不要在 answer deps 使用 point:" in guidance


def test_r7_tarjan_articulation_guidance_requires_dfn_and_low_set_events():
    _context, guidance = _guidance_for("Tarjan 算法 失败：Graph contract Tarjan 缺少 dfn 写入事件")

    assert "Tarjan 割点桥固定短模板" in guidance
    assert 'tracer.set("dfn[u]")' in guidance
    assert 'tracer.set("low[u]")' in guidance
    assert "dfn 写入事件" in guidance


def test_r7_tarjan_guidance_requires_component_pop_frame():
    _context, guidance = _guidance_for("Tarjan 算法 失败：Graph contract Tarjan 缺少 component 弹栈事件")

    assert "component 弹栈事件" in guidance
    assert "state.component" in guidance
    assert "component 节点已从 stack 移除" in guidance


def test_r7_tarjan_answer_guidance_forbids_articulation_and_bridges_as_node_ids():
    _context, guidance = _guidance_for(
        "严格模式拒绝 warning：Tarjan 算法: 第 30 帧 scene object 引用 state 中不存在的 node：node:articulation; "
        "严格模式拒绝 warning：Tarjan 算法: 第 30 帧 scene object 引用 state 中不存在的 node：node:bridges"
    )

    assert "不要使用 node:articulation 或 node:bridges" in guidance
    assert "最终 answer 事件 target/deps 使用 answer 或 graph" in guidance
    assert "state.articulation" in guidance
    assert "state.bridges" in guidance


def test_r7_tarjan_articulation_guidance_requires_initialization_phase():
    _context, guidance = _guidance_for(
        "Tarjan 算法 失败：failure_type=demo_key_step_missing: 缺少 initialization 阶段"
    )

    assert "Tarjan 第一帧必须是 initialization/create 阶段" in guidance
    assert "state.phase=\"initialization\"" in guidance
    assert "tracer.create(\"graph\")" in guidance
    assert "dfn/low/parent/stack/on_stack 初始化" in guidance


def test_r7_tarjan_missing_reason_guidance_requires_reasons_on_all_event_types():
    _context, guidance = _guidance_for(
        "Tarjan 算法 失败：failure_type=demo_missing_reason: step 21 缺少 reason; "
        "step 24 缺少 reason; step 25 缺少 reason"
    )

    assert "Tarjan 割点桥所有事件 reason 非空" in guidance
    assert "create/set/compare/mark/enter/exit" in guidance
    assert "dfn/low/bridge/articulation/component 事件都写简短 reason" in guidance


def test_r7_family_contract_accepts_union_find_family_instead_of_unsupported():
    contract = {"family": "union_find", "submode": "connected_components", "expected_events": ["union"]}
    raw_trace = _family_contract_trace(
        "并查集合同正例",
        {"isConnected": [[1, 1], [1, 1]]},
        1,
        [
            _family_contract_event(
                0,
                "create",
                ["union_find"],
                state={"isConnected": [[1, 1], [1, 1]], "union_find": {"parent": {"0": "0", "1": "1"}, "rank": {"0": 0, "1": 0}}, "family_contract": contract},
                reason="初始化并查集 parent/rank。",
            ),
            _family_contract_event(
                1,
                "link",
                ["node:1"],
                deps=["node:0"],
                state={"isConnected": [[1, 1], [1, 1]], "union_find": {"parent": {"0": "0", "1": "0"}, "rank": {"0": 1, "1": 0}}, "i": 0, "j": 1, "family_contract": contract},
                reason="union 相连城市，把根 1 合并到根 0。",
            ),
            _family_contract_event(
                2,
                "mark",
                ["union_find"],
                state={"isConnected": [[1, 1], [1, 1]], "union_find": {"parent": {"0": "0", "1": "0"}, "rank": {"0": 1, "1": 0}}, "answer": 1, "family_contract": contract},
                role="answer",
                reason="find 所有根后统计连通块数量。",
            ),
        ],
    )

    errors = _process_errors(raw_trace)
    assert not any("Family contract 未支持的 family：union_find" in error for error in errors)
    assert not errors


def test_r7_family_contract_accepts_data_structure_range_contract_instead_of_unsupported():
    contract = {"family": "data_structure", "submode": "segment_tree", "expected_events": ["build", "query"]}
    segment_tree = {
        "nodes": [
            {"id": "root", "label": "[0,1]", "meta": {"l": 0, "r": 1, "sum": 3}},
            {"id": "left", "label": "[0,0]", "meta": {"l": 0, "r": 0, "sum": 1}},
            {"id": "right", "label": "[1,1]", "meta": {"l": 1, "r": 1, "sum": 2}},
        ],
        "edges": [["root", "left"], ["root", "right"]],
    }
    raw_trace = _family_contract_trace(
        "线段树合同正例",
        {"nums": [1, 2]},
        3,
        [
            _family_contract_event(
                0,
                "create",
                ["segment_tree"],
                state={"nums": [1, 2], "segment_tree": segment_tree, "family_contract": contract},
                reason="build segment_tree，每个节点 meta 记录区间和。",
            ),
            _family_contract_event(
                1,
                "mark",
                ["node:root"],
                deps=["node:left", "node:right"],
                state={"nums": [1, 2], "segment_tree": segment_tree, "answer": 3, "family_contract": contract},
                role="answer",
                reason="query root 区间得到 range sum。",
            ),
        ],
    )

    errors = _process_errors(raw_trace)
    assert not any("Family contract 未支持的 family：data_structure" in error for error in errors)
    assert not errors


def run_all() -> None:
    test_r7_runtime_api_guidance_forbids_to_trace_result_and_private_add_stage()
    test_r7_runtime_api_guidance_forbids_contract_kwargs_in_tracer_init()
    test_r7_targetref_id_list_schema_guidance_rewrites_each_target_as_string_id()
    test_r7_array_pointer_guidance_requires_submode_key_updates_and_compare_deps()
    test_r7_binary_search_guidance_requires_closed_interval_template_without_state_jump()
    test_r7_binary_search_move_guidance_requires_observable_evidence()
    test_r7_binary_answer_guidance_requires_initialization_phase_and_compare_before_every_move()
    test_r7_binary_answer_state_jump_guidance_requires_immediate_compare_before_move()
    test_r7_dp_knapsack_guidance_requires_loop_keys_deps_and_direction()
    test_r7_bounded_knapsack_guidance_allows_incremental_candidate_but_requires_final_max()
    test_r7_bounded_knapsack_missing_reason_guidance_requires_non_empty_reasons()
    test_r7_lcs_guidance_requires_i_j_current_formula_and_deps()
    test_r7_lcs_guidance_keeps_initialized_base_cells_out_of_expected_targets()
    test_r7_string_sliding_window_guidance_uses_single_text_window_contract()
    test_r7_string_sliding_window_duplicate_guidance_shrinks_before_best_update()
    test_r7_string_sliding_window_guidance_keeps_counts_aligned_with_left_right()
    test_r7_lca_guidance_uses_tree_contract_instead_of_graph_dfs_contract()
    test_r7_lca_guidance_requires_initialization_create_tree_frame()
    test_r7_segment_tree_range_sum_guidance_syncs_parent_sums_after_update()
    test_r7_sparse_table_guidance_requires_complete_correct_table_in_state()
    test_r7_sparse_table_timeout_guidance_uses_compact_create_query_answer_template()
    test_r7_z_algorithm_guidance_sets_final_z_value_after_expansion_only()
    test_r7_trie_create_node_guidance_requires_explicit_create_node_event()
    test_r7_sparse_table_invalid_st_target_guidance_limits_targets_to_existing_cells()
    test_r7_full_dp_residual_guidance_covers_difference_subset_tsp_digit_and_floyd()
    test_r7_difference_array_guidance_reconstructs_final_nums_targets()
    test_r7_dijkstra_relax_guidance_requires_node_and_edge_deps()
    test_r7_remaining_dp_residual_guidance_is_strict_for_base_and_transition_sets()
    test_r7_permutation_record_guidance_requires_answer_role_and_path_deps()
    test_r7_permutation_frame_ids_must_not_contain_spaces()
    test_r7_knapsack_create_initialization_guidance_forbids_set_only_base_case()
    test_r7_generation_json_failures_request_short_tracker_template()
    test_r7_full_graph_residual_guidance_requires_edge_check_deps_and_enqueue_reason()
    test_r7_bfs_first_visit_guidance_requires_node_and_edge_deps()
    test_r7_zero_one_bfs_guidance_requires_first_visit_relax_deps()
    test_r7_bellman_ford_node_warning_guidance_repeats_graph_nodes_edges()
    test_r7_two_sum_hash_guidance_forbids_unsupported_hash_family_contract()
    test_r7_residual_guidance_covers_bfs_parent_dfs_frontier_matching_and_digit_json_object()
    test_r7_connected_components_guidance_keeps_component_connected_only()
    test_r7_bipartite_matching_guidance_forbids_unpaired_bare_dfs_frames()
    test_r7_topological_sort_guidance_keeps_indegree_counts_until_all_predecessors_processed()
    test_r7_topological_sort_process_repair_stays_compact_to_avoid_empty_json()
    test_r7_data_structure_guidance_covers_trie_linked_heap_union_find_and_range()
    test_r7_scene_and_range_guidance_handles_trie_node_none_and_segment_tree_mark_evidence()
    test_r7_scene_guidance_requires_state_struct_for_every_node_ref()
    test_r7_trie_guidance_requires_char_target_or_state_for_each_path_step()
    test_r7_trie_missing_words_index_guidance_prefers_char_targets_or_visible_state()
    test_r7_trie_prefix_count_guidance_requires_observable_count_state()
    test_r7_trie_empty_prefix_guidance_uses_root_prefix_count_as_answer()
    test_r7_trie_empty_word_guidance_marks_root_terminal()
    test_r7_range_contract_guidance_and_validator_recognize_update_event()
    test_r7_invalid_target_guidance_rewrites_input_and_result_index_targets()
    test_r7_bitmask_subsets_guidance_keeps_subset_deps_visible_in_state()
    test_r7_linked_list_guidance_requires_next_prev_in_node_meta_and_state()
    test_r7_linked_list_node_warning_guidance_repeats_full_linked_list_state_per_event()
    test_r7_linked_list_guidance_requires_explicit_link_change_and_no_blank_next_edge()
    test_r7_linked_list_guidance_requires_observable_set_or_move_evidence()
    test_r7_linked_list_current_guidance_advances_to_saved_next_node()
    test_r7_linked_list_guidance_forbids_half_updated_next_edges()
    test_r7_linked_list_guidance_processes_old_current_before_advancing()
    test_r7_linked_list_current_move_guidance_uses_before_state_then_next_state()
    test_r7_linked_list_expansion_guidance_advances_current_to_second_node()
    test_r7_linked_list_three_node_guidance_advances_current_every_round()
    test_r7_linked_list_execution_guidance_initializes_next_node_name()
    test_r7_segment_tree_node_none_guidance_requires_non_null_edge_endpoints()
    test_r7_linked_list_nameerror_next_guidance_forbids_builtin_next_variable()
    test_r7_full_structure_tree_backtracking_math_guidance_covers_residuals()
    test_r7_jump_game_unreachable_guidance_stops_with_false_answer()
    test_r7_jump_game_guidance_updates_reach_on_first_scanned_index()
    test_r7_tree_dp_demo_guidance_requires_set_events_for_take_and_skip()
    test_r7_tree_dp_mark_and_answer_position_guidance_requires_observable_dp_targets()
    test_r7_tree_dp_guidance_forbids_partial_parent_dp_and_requires_answer_set()
    test_r7_convex_hull_final_frame_guidance_requires_cleared_backtracking_path()
    test_r7_convex_hull_guidance_uses_geometry_contract_not_backtracking()
    test_r7_convex_hull_point_deps_guidance_repeats_geometry_points_per_event()
    test_r7_convex_hull_point_named_deps_require_matching_point_ids()
    test_r7_convex_hull_guidance_forbids_geometry_family_contract_and_invalid_hull_frames()
    test_r7_convex_hull_final_answer_deps_use_geometry_not_points()
    test_r7_tarjan_articulation_guidance_requires_dfn_and_low_set_events()
    test_r7_tarjan_guidance_requires_component_pop_frame()
    test_r7_tarjan_answer_guidance_forbids_articulation_and_bridges_as_node_ids()
    test_r7_tarjan_articulation_guidance_requires_initialization_phase()
    test_r7_tarjan_missing_reason_guidance_requires_reasons_on_all_event_types()
    test_r7_family_contract_accepts_union_find_family_instead_of_unsupported()
    test_r7_family_contract_accepts_data_structure_range_contract_instead_of_unsupported()


if __name__ == "__main__":
    run_all()
    print("r7_residual_repair_guidance: PASS")
