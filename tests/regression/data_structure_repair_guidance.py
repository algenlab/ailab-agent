"""Regression tests for R5 DP/data-structure repair guidance."""

from __future__ import annotations

from algolab.generation.repair import build_solution_repair_prompt
from algolab.verification.repair_context import build_repair_context


def _joined_guidance(message: str) -> tuple[str, str, str]:
    context = build_repair_context([message])
    prompt = build_solution_repair_prompt(
        request_prompt="生成算法轨迹 JSON。",
        previous={"variants": [{"id": "v", "tracker_code": ""}]},
        errors=[message],
        repair_context=context,
    )
    guidance = "\n".join(
        [
            context[0]["repair_instruction"],
            *context[0]["family_guidance"],
            prompt,
        ]
    )
    return context[0]["family"], context[0]["repair_category"], guidance


def test_r5_dp_demo_key_step_guidance_requires_key_set_evidence():
    family, category, guidance = _joined_guidance("failure_type=demo_key_step_missing: DP 小表缺少关键 set 事件")

    assert family == "dynamic_programming"
    assert category == "demo_readiness"
    assert "set" in guidance
    assert "deps" in guidance
    assert "formula" in guidance
    assert "answer_position" in guidance
    assert "补" in guidance
    assert "不要只改最终答案" in guidance


def test_r5_dp_answer_position_guidance_requires_answer_target_reference():
    family, category, guidance = _joined_guidance("DP contract 答案位置未明确：role=answer 事件必须引用 dp[11]")

    assert family == "dynamic_programming"
    assert category == "process_invariant"
    assert "role=answer" in guidance
    assert "dp[answer_position]" in guidance
    assert "targets" in guidance
    assert "deps" in guidance
    assert "dp[11]" in guidance


def test_r5_complete_knapsack_guidance_requires_canonical_min_transition():
    family, category, guidance = _joined_guidance("第 2 步 dp[2] 不满足完全背包转移")

    assert family == "dynamic_programming"
    assert category == "process_invariant"
    assert "complete_knapsack" in guidance
    assert "j 从 coin 到 amount 正序" in guidance
    assert "dp[j] = min(dp[j], dp[j-coin] + 1)" in guidance
    assert "candidate" in guidance
    assert "old_value" in guidance
    assert "coins[:i+1]" in guidance
    assert "inf=amount+1" in guidance
    assert "unreachable" in guidance


def test_r5_complete_knapsack_guidance_requires_formula_on_every_dp_set():
    family, category, guidance = _joined_guidance("第 35 步 DP contract 转移事件缺少可复原公式")

    assert family == "dynamic_programming"
    assert category == "process_invariant"
    assert "每个 set dp" in guidance
    assert "state.formula" in guidance
    assert "teaching.formula" in guidance
    assert "answer=dp[amount]" in guidance


def test_r5_state_compression_guidance_requires_formula_and_expected_targets():
    family, category, guidance = _joined_guidance(
        "状态压缩动态规划：DP contract 转移事件缺少可复原公式; DP contract 缺少关键更新：dp[0][0], dp[0][1], dp[0][2]"
    )

    assert family == "dynamic_programming"
    assert category == "process_invariant"
    assert "state_compression" in guidance
    assert "formula" in guidance
    assert "dp[mask][last]" in guidance
    assert "dp[next_mask][next]" in guidance
    assert "expected_targets" in guidance
    assert "不能省略" in guidance


def test_r5_trie_prefix_count_guidance_distinguishes_query_from_insert_count():
    family, category, guidance = _joined_guidance("Trie prefix_count 错误：query prefix count 与插入节点 count 混淆")

    assert family == "data_structure"
    assert category in {"process_invariant", "demo_readiness", "generation"}
    assert "Trie" in guidance or "trie" in guidance
    assert "prefix_count" in guidance
    assert "query" in guidance
    assert "插入节点 count" in guidance
    assert "答案 count" in guidance


def test_r5_trie_guidance_rejects_loose_count_index_targets():
    family, category, guidance = _joined_guidance("第 1 步引用了不存在的索引 target：count[0]; 第 8 步引用了不存在的索引 target：is_end[5]")

    assert family == "data_structure"
    assert category == "target_or_deps"
    assert "count[0]" in guidance
    assert "is_end[5]" in guidance
    assert "node:<id>" in guidance
    assert "node.meta.count" in guidance
    assert "node.meta.terminal" in guidance
    assert "不要使用孤立 count[i]" in guidance


def test_r5_monotonic_stack_guidance_requires_answer_write_after_pop():
    family, category, guidance = _joined_guidance("failure_type=demo_algorithm_mismatch: 单调栈 pop 后没有写 answer target")

    assert family == "data_structure"
    assert category == "demo_readiness"
    assert "单调栈" in guidance
    assert "pop" in guidance
    assert "answer" in guidance
    assert "target" in guidance
    assert "temperatures" in guidance or "daily_temperatures" in guidance


def test_r5_monotonic_stack_guidance_requires_popped_and_current_deps():
    family, category, guidance = _joined_guidance("failure_type=demo_missing_deps: step 5 单调栈 pop 缺少被弹元素和当前元素 deps")

    assert family == "data_structure"
    assert category == "demo_readiness"
    assert "被弹元素" in guidance
    assert "当前元素" in guidance
    assert "deps" in guidance
    assert "temperatures[popped_index]" in guidance
    assert "temperatures[current_index]" in guidance
    assert "answer[popped_index]" in guidance or "result[popped_index]" in guidance
    assert "tracer.pop" in guidance


def test_r5_backtracking_guidance_requires_choose_record_undo_ops():
    family, category, guidance = _joined_guidance("回溯缺 choose / undo，permutation path/used 跳变")

    assert family == "backtracking"
    assert category in {"process_invariant", "trace_step_jump", "generation"}
    assert "choose" in guidance
    assert "record" in guidance
    assert "undo" in guidance
    assert "push" in guidance
    assert "mark" in guidance
    assert "enter" in guidance
    assert "pop" in guidance
    assert "unmark" in guidance
    assert "exit" in guidance


def test_r5_backtracking_guidance_requires_recursion_tree_and_record_event():
    family, category, guidance = _joined_guidance("Family contract backtracking 缺少 recursion_tree/search_tree state; Family contract backtracking 缺少 record 事件")

    assert family == "backtracking"
    assert category == "process_invariant"
    assert "recursion_tree" in guidance
    assert "search_tree" in guidance
    assert "record" in guidance
    assert "role=answer" in guidance
    assert "answer" in guidance
    assert "path" in guidance


def test_r5_backtracking_demo_guidance_requires_enter_and_exit_frames():
    family, category, guidance = _joined_guidance(
        "failure_type=demo_key_step_missing: 回溯演示缺少选择进入帧; failure_type=demo_state_jump: 回溯演示缺少返回/撤销帧"
    )

    assert family == "backtracking"
    assert category == "demo_readiness"
    assert "tracer.enter" in guidance
    assert "frame:dfs" in guidance
    assert "tracer.exit" in guidance
    assert "每个事件" in guidance
    assert "state={\"recursion_tree\"" in guidance
    assert "撤销" in guidance
    assert "path" in guidance
    assert "used" in guidance


def test_r5_backtracking_guidance_rejects_answer_expected_event_token():
    family, category, guidance = _joined_guidance("Family contract backtracking 缺少关键事件：answer")

    assert family == "backtracking"
    assert category == "process_invariant"
    assert "expected_events" in guidance
    assert "choose" in guidance
    assert "record" in guidance
    assert "undo" in guidance
    assert "不要使用 answer" in guidance
    assert "role=answer" in guidance


def test_r5_sparse_table_guidance_requires_st_cell_set_events():
    family, category, guidance = _joined_guidance("failure_type=demo_key_step_missing: DP 演示缺少状态转移写入帧，稀疏表 sparse_table")

    assert family == "data_structure"
    assert category == "demo_readiness"
    assert "sparse table" in guidance or "sparse_table" in guidance
    assert "st[k][i]" in guidance
    assert "set" in guidance
    assert "deps" in guidance
    assert "重叠区间" in guidance
    assert "answer target" in guidance


def test_r5_sparse_table_guidance_requires_correct_min_values():
    family, category, guidance = _joined_guidance("第 0 步稀疏表 st[1][0] 应为 2; 第 6 步稀疏表 st[2][0] 应为 2")

    assert family == "data_structure"
    assert category == "process_invariant"
    assert "st[0][i]=nums[i]" in guidance
    assert "st[k][i] = min(st[k-1][i], st[k-1][i+2^(k-1)])" in guidance
    assert "完整正确的 st" in guidance
    assert "不要把未计算项写成错误数值" in guidance


def run_all() -> None:
    test_r5_dp_demo_key_step_guidance_requires_key_set_evidence()
    test_r5_dp_answer_position_guidance_requires_answer_target_reference()
    test_r5_complete_knapsack_guidance_requires_canonical_min_transition()
    test_r5_complete_knapsack_guidance_requires_formula_on_every_dp_set()
    test_r5_state_compression_guidance_requires_formula_and_expected_targets()
    test_r5_trie_prefix_count_guidance_distinguishes_query_from_insert_count()
    test_r5_trie_guidance_rejects_loose_count_index_targets()
    test_r5_monotonic_stack_guidance_requires_answer_write_after_pop()
    test_r5_monotonic_stack_guidance_requires_popped_and_current_deps()
    test_r5_backtracking_guidance_requires_choose_record_undo_ops()
    test_r5_backtracking_guidance_requires_recursion_tree_and_record_event()
    test_r5_backtracking_demo_guidance_requires_enter_and_exit_frames()
    test_r5_backtracking_guidance_rejects_answer_expected_event_token()
    test_r5_sparse_table_guidance_requires_st_cell_set_events()
    test_r5_sparse_table_guidance_requires_correct_min_values()


if __name__ == "__main__":
    run_all()
    print("data_structure_repair_guidance: PASS")
