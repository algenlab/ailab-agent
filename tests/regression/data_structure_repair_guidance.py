"""DSL-era regression tests for legacy DP/data-structure repair messages."""

from __future__ import annotations

from algolab.generation.repair import build_solution_repair_prompt
from algolab.verification.repair_context import build_repair_context


def _context_for(message: str) -> tuple[dict, str]:
    context = build_repair_context([message])
    prompt = build_solution_repair_prompt(
        request_prompt="生成算法轨迹 Python DSL。",
        previous={"variants": [{"id": "v", "tracker_code": ""}]},
        errors=[message],
        repair_context=context,
    )
    return context[0], prompt


def _assert_legacy_process_message_is_generic(message: str) -> None:
    context, prompt = _context_for(message)
    assert context["family"] == ""
    assert context["family_guidance"] == []
    assert context["failure_type"] == "generation"
    assert context["repair_category"] == "generation"
    assert "返回完整 JSON" in context["repair_instruction"]
    assert message in prompt


def _assert_explicit_demo_marker_is_generic(message: str) -> None:
    _assert_legacy_process_message_is_generic(message)


def test_r5_dp_demo_key_step_guidance_requires_key_set_evidence():
    _assert_explicit_demo_marker_is_generic("failure_type=demo_key_step_missing: DP 小表缺少关键 set 事件")


def test_r5_dp_answer_position_guidance_requires_answer_target_reference():
    _assert_legacy_process_message_is_generic("DP contract 答案位置未明确：role=answer 事件必须引用 dp[11]")


def test_r5_complete_knapsack_guidance_requires_canonical_min_transition():
    _assert_legacy_process_message_is_generic("第 2 步 dp[2] 不满足完全背包转移")


def test_r5_complete_knapsack_guidance_requires_formula_on_every_dp_set():
    _assert_legacy_process_message_is_generic("第 35 步 DP contract 转移事件缺少可复原公式")


def test_r5_state_compression_guidance_requires_formula_and_expected_targets():
    _assert_legacy_process_message_is_generic(
        "状态压缩动态规划：DP contract 转移事件缺少可复原公式; DP contract 缺少关键更新：dp[0][0], dp[0][1], dp[0][2]"
    )


def test_r5_trie_prefix_count_guidance_distinguishes_query_from_insert_count():
    _assert_legacy_process_message_is_generic("Trie prefix_count 错误：query prefix count 与插入节点 count 混淆")


def test_r5_trie_guidance_rejects_loose_count_index_targets():
    context, _prompt = _context_for("第 1 步引用了不存在的索引 target：count[0]; 第 8 步引用了不存在的索引 target：is_end[5]")
    assert context["failure_type"] == "generation"
    assert context["targets"] == ["count[0]", "is_end[5]"]


def test_r5_monotonic_stack_guidance_requires_answer_write_after_pop():
    _assert_explicit_demo_marker_is_generic("failure_type=demo_algorithm_mismatch: 单调栈 pop 后没有写 answer target")


def test_r5_monotonic_stack_guidance_requires_popped_and_current_deps():
    _assert_explicit_demo_marker_is_generic("failure_type=demo_missing_deps: step 5 单调栈 pop 缺少被弹元素和当前元素 deps")


def test_r5_backtracking_guidance_requires_choose_record_undo_ops():
    _assert_legacy_process_message_is_generic("回溯缺 choose / undo，permutation path/used 跳变")


def test_r5_backtracking_guidance_requires_recursion_tree_and_record_event():
    _assert_legacy_process_message_is_generic("Family contract backtracking 缺少 recursion_tree/search_tree state; Family contract backtracking 缺少 record 事件")


def test_r5_backtracking_demo_guidance_requires_enter_and_exit_frames():
    _assert_explicit_demo_marker_is_generic(
        "failure_type=demo_key_step_missing: 回溯演示缺少选择进入帧; failure_type=demo_state_jump: 回溯演示缺少返回/撤销帧"
    )


def test_r5_backtracking_guidance_rejects_answer_expected_event_token():
    _assert_legacy_process_message_is_generic("Family contract backtracking 缺少关键事件：answer")


def test_r5_sparse_table_guidance_requires_st_cell_set_events():
    _assert_explicit_demo_marker_is_generic("failure_type=demo_key_step_missing: DP 演示缺少状态转移写入帧，稀疏表 sparse_table")


def test_r5_sparse_table_guidance_requires_correct_min_values():
    _assert_legacy_process_message_is_generic("第 0 步稀疏表 st[1][0] 应为 2; 第 6 步稀疏表 st[2][0] 应为 2")


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
