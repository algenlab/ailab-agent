"""DSL-era regression tests for legacy graph repair messages."""

from __future__ import annotations

from algolab.generation.repair import build_solution_repair_prompt
from algolab.verification.repair_context import build_repair_context


def _context_for(message: str) -> tuple[dict, str]:
    context = build_repair_context([message])
    prompt = build_solution_repair_prompt(
        request_prompt="生成图算法轨迹 Python DSL。",
        previous={"variants": [{"id": "v", "tracker_code": ""}]},
        errors=[message],
        repair_context=context,
    )
    return context[0], prompt


def _assert_legacy_graph_process_message_is_generic(message: str) -> None:
    context, prompt = _context_for(message)
    assert context["family"] == ""
    assert context["family_guidance"] == []
    assert context["failure_type"] == "generation"
    assert context["repair_category"] == "generation"
    assert "返回完整 JSON" in context["repair_instruction"]
    assert message in prompt


def test_r4_dijkstra_repair_guidance_requires_relax_fields():
    _assert_legacy_graph_process_message_is_generic("第 4 步 Graph contract Dijkstra 缺少 relax 事件：edge:A->B")


def test_r4_kruskal_repair_guidance_requires_union_find_details():
    _assert_legacy_graph_process_message_is_generic("第 2 步 Graph contract Kruskal 缺少 union-find 选边证据")


def test_r4_tarjan_repair_guidance_requires_component_pop_evidence():
    _assert_legacy_graph_process_message_is_generic("第 8 步 Graph contract Tarjan 缺少 component 弹栈事件")


def test_r4_edmonds_karp_repair_guidance_requires_flow_update_evidence():
    _assert_legacy_graph_process_message_is_generic("第 6 步 Graph contract Edmonds-Karp 缺少 flow/capacity 更新")


def run_all() -> None:
    test_r4_dijkstra_repair_guidance_requires_relax_fields()
    test_r4_kruskal_repair_guidance_requires_union_find_details()
    test_r4_tarjan_repair_guidance_requires_component_pop_evidence()
    test_r4_edmonds_karp_repair_guidance_requires_flow_update_evidence()


if __name__ == "__main__":
    run_all()
    print("graph_repair_guidance: PASS")
