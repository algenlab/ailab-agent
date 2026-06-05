"""DSL-era regression tests for legacy R7 residual repair guidance.

R7 originally accumulated many family-specific prompt snippets.  In the DSL
architecture, repair context is intentionally small: classify the failure,
preserve the raw error, and let the next generation fix Python DSL code.
"""

from __future__ import annotations

from algolab.generation.repair import build_solution_repair_prompt
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.process_validator import validate_process
from algolab.verification.repair_context import build_repair_context


def _guidance_for(message: str) -> tuple[list[dict], str]:
    context = build_repair_context([message])
    prompt = build_solution_repair_prompt(
        request_prompt="生成算法轨迹 Python DSL。",
        previous={"variants": [{"id": "v", "tracker_code": ""}]},
        errors=[message],
        repair_context=context,
    )
    return context, prompt


def _assert_context(message: str, *, failure_type: str, category: str) -> dict:
    context, prompt = _guidance_for(message)
    item = context[0]
    assert item["failure_type"] == failure_type, item
    assert item["repair_category"] == category, item
    assert item["family"] == ""
    assert item["family_guidance"] == []
    assert message in prompt
    return item


def _assert_legacy_generation(message: str) -> dict:
    item = _assert_context(message, failure_type="generation", category="generation")
    assert "返回完整 JSON" in item["repair_instruction"]
    return item


def _schema_valid_trace(algorithm: str = "family contract legacy") -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": algorithm,
            "input_data": {"items": [1]},
            "result": 1,
            "pseudocode": ["execute DSL"],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "items"}],
                    "state": {"items": [1], "family_contract": {"family": "data_structure"}},
                    "reason": "创建输入。",
                    "code_line": 1,
                }
            ],
        }
    )


def _assert_validate_process_accepts_schema_valid_trace(algorithm: str = "family contract legacy") -> None:
    errors, warnings = validate_process(_schema_valid_trace(algorithm))
    assert errors == []
    assert warnings == []


def test_r7_runtime_api_guidance_forbids_to_trace_result_and_private_add_stage():
    item = _assert_context(
        "trace 执行失败：TypeError: Tracer.to_trace() got an unexpected keyword argument 'result'; "
        "TypeError: Tracer._add() got an unexpected keyword argument 'stage'",
        failure_type="execution",
        category="execution",
    )
    assert "Python 异常" in item["repair_instruction"]


def test_r7_array_pointer_guidance_requires_submode_key_updates_and_compare_deps():
    _assert_legacy_generation("二分查找 失败：Array pointer contract 缺少 submode；failure_type=demo_state_jump")


def test_r7_binary_search_guidance_requires_closed_interval_template_without_state_jump():
    _assert_legacy_generation("闭区间二分查找 失败：第 3 步 二分 mid 应为 4; failure_type=demo_state_jump")


def test_r7_binary_answer_guidance_requires_initialization_phase_and_compare_before_every_move():
    _assert_legacy_generation("二分查找 失败：failure_type=demo_key_step_missing: 缺少 initialization 阶段")


def test_r7_dp_knapsack_guidance_requires_loop_keys_deps_and_direction():
    _assert_legacy_generation("0-1背包动态规划 失败：DP contract state 缺少循环变量；DP contract 缺少关键更新")


def test_r7_bounded_knapsack_guidance_allows_incremental_candidate_but_requires_final_max():
    _assert_legacy_generation("一维空间优化多重背包 失败：第 4 步多重背包 dp[5] 应为 6")


def test_r7_string_sliding_window_guidance_uses_single_text_window_contract():
    _assert_legacy_generation("滑动窗口 失败：Family contract string 缺少 text/pattern 指针")


def test_r7_tree_and_heap_residual_guidance_requires_current_node_and_heap_invariants():
    _assert_legacy_generation("树遍历 失败：Family contract tree 缺少 current node; heap_top 错误")


def test_r7_trace_size_guidance_focuses_on_single_event_state_budget():
    item = _assert_context("trace 执行失败：单步 state 过大，请只保留可视化必要变量", failure_type="trace_size", category="trace_size")
    assert "精简单步 state" in item["repair_instruction"]


def test_r7_data_structure_guidance_covers_trie_linked_heap_union_find_and_range():
    _assert_legacy_generation("Trie/linked_list/heap/union_find/range_structure legacy contract guidance")


def test_r7_scene_and_range_guidance_handles_trie_node_none_and_segment_tree_mark_evidence():
    _assert_legacy_generation("scene warning: node None; segment_tree mark 缺少可见 state")


def test_r7_scene_guidance_requires_state_struct_for_every_node_ref():
    item = _assert_legacy_generation("第 5 步引用了不存在的 target：node:root")
    assert item["targets"] == ["node:root"]


def test_r7_trie_guidance_requires_char_target_or_state_for_each_path_step():
    _assert_legacy_generation("Trie 失败：缺少 words[0][1] 可见 state")


def test_r7_range_contract_guidance_and_validator_recognize_update_event():
    _assert_legacy_generation("Range contract 缺少 update event")
    _assert_validate_process_accepts_schema_valid_trace("range structure family contract")


def test_r7_invalid_target_guidance_rewrites_input_and_result_index_targets():
    item = _assert_legacy_generation("第 1 步引用了不存在的索引 target：input_data[0]; result[0]")
    assert item["targets"] == ["input_data[0]", "result[0]"]


def test_r7_linked_list_guidance_requires_next_prev_in_node_meta_and_state():
    _assert_legacy_generation("linked_list 失败：node meta 缺少 next/prev")


def test_r7_linked_list_execution_guidance_initializes_next_node_name():
    item = _assert_context("trace 执行失败：NameError: name 'next_node' is not defined", failure_type="execution", category="execution")
    assert item["step"] is None


def test_r7_family_contract_accepts_union_find_family_instead_of_unsupported():
    _assert_validate_process_accepts_schema_valid_trace("union_find family contract")


def test_r7_family_contract_accepts_data_structure_range_contract_instead_of_unsupported():
    _assert_validate_process_accepts_schema_valid_trace("data_structure range contract")


def run_all() -> None:
    test_r7_runtime_api_guidance_forbids_to_trace_result_and_private_add_stage()
    test_r7_array_pointer_guidance_requires_submode_key_updates_and_compare_deps()
    test_r7_binary_search_guidance_requires_closed_interval_template_without_state_jump()
    test_r7_binary_answer_guidance_requires_initialization_phase_and_compare_before_every_move()
    test_r7_dp_knapsack_guidance_requires_loop_keys_deps_and_direction()
    test_r7_bounded_knapsack_guidance_allows_incremental_candidate_but_requires_final_max()
    test_r7_string_sliding_window_guidance_uses_single_text_window_contract()
    test_r7_tree_and_heap_residual_guidance_requires_current_node_and_heap_invariants()
    test_r7_trace_size_guidance_focuses_on_single_event_state_budget()
    test_r7_data_structure_guidance_covers_trie_linked_heap_union_find_and_range()
    test_r7_scene_and_range_guidance_handles_trie_node_none_and_segment_tree_mark_evidence()
    test_r7_scene_guidance_requires_state_struct_for_every_node_ref()
    test_r7_trie_guidance_requires_char_target_or_state_for_each_path_step()
    test_r7_range_contract_guidance_and_validator_recognize_update_event()
    test_r7_invalid_target_guidance_rewrites_input_and_result_index_targets()
    test_r7_linked_list_guidance_requires_next_prev_in_node_meta_and_state()
    test_r7_linked_list_execution_guidance_initializes_next_node_name()
    test_r7_family_contract_accepts_union_find_family_instead_of_unsupported()
    test_r7_family_contract_accepts_data_structure_range_contract_instead_of_unsupported()


if __name__ == "__main__":
    run_all()
    print("r7_residual_repair_guidance: PASS")
