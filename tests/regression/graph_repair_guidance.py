"""Regression tests for graph repair guidance."""

from __future__ import annotations

from algolab.generation.repair import build_solution_repair_prompt
from algolab.verification.repair_context import build_repair_context


def _joined_guidance(message: str) -> str:
    context = build_repair_context([message])
    assert context[0]["family"] == "graph"
    assert context[0]["repair_category"] == "process_invariant"
    return "\n".join(
        [
            context[0]["repair_instruction"],
            *context[0]["family_guidance"],
            build_solution_repair_prompt(
                request_prompt="生成图算法轨迹 JSON。",
                previous={"variants": [{"id": "v", "tracker_code": ""}]},
                errors=[message],
                repair_context=context,
            ),
        ]
    )


def test_r4_dijkstra_repair_guidance_requires_relax_fields():
    guidance = _joined_guidance("第 4 步 Graph contract Dijkstra 缺少 relax 事件：edge:A->B")

    assert "old_dist" in guidance
    assert "new_dist" in guidance
    assert "edge:u->v" in guidance


def test_r4_kruskal_repair_guidance_requires_union_find_details():
    guidance = _joined_guidance("第 2 步 Graph contract Kruskal 缺少 union-find 选边证据")

    assert "union_find" in guidance
    assert "parent" in guidance
    assert "rank" in guidance or "size" in guidance


def test_r4_tarjan_repair_guidance_requires_component_pop_evidence():
    guidance = _joined_guidance("第 8 步 Graph contract Tarjan 缺少 component 弹栈事件")

    assert "dfn" in guidance
    assert "low" in guidance
    assert "stack" in guidance
    assert "component" in guidance


def test_r4_edmonds_karp_repair_guidance_requires_flow_update_evidence():
    guidance = _joined_guidance("第 6 步 Graph contract Edmonds-Karp 缺少 flow/capacity 更新")

    assert "augmenting_path" in guidance
    assert "bottleneck" in guidance
    assert "flow" in guidance
    assert "capacity" in guidance
    assert "flow[u->v]" in guidance
    assert "cap[u->v]" in guidance or "capacity[u->v]" in guidance
    assert "value=new_flow" in guidance
    assert "deps=" in guidance
    assert "state=" in guidance
    assert "before/after" in guidance
    assert "严格对齐" in guidance
    assert "中间节点" in guidance
    assert "守恒" in guidance
    assert "整条增广路径" in guidance
    assert "原始容量边" in guidance
    assert "非负" in guidance
    assert "反向残量边" in guidance
    assert "residual" in guidance
    assert "before=old_flow" not in guidance


def run_all() -> None:
    test_r4_dijkstra_repair_guidance_requires_relax_fields()
    test_r4_kruskal_repair_guidance_requires_union_find_details()
    test_r4_tarjan_repair_guidance_requires_component_pop_evidence()
    test_r4_edmonds_karp_repair_guidance_requires_flow_update_evidence()


if __name__ == "__main__":
    run_all()
    print("graph_repair_guidance: PASS")
