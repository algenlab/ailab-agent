"""Regression tests for P0-P2 DSL primitives."""

from __future__ import annotations

from algolab.compiler.scene_compiler import compile_scene
from algolab.runtime.dsl import TraceSession
from algolab.runtime.executor import execute_variant, results_equivalent, to_jsonable
from algolab.runtime.sandbox import run_function
from algolab.schemas.semantic_trace import SemanticTrace, SolutionVariant
from algolab.verification.repair_context import classify_repair_error
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace


def _validated_scene(raw_trace: dict):
    trace = SemanticTrace.model_validate(raw_trace)
    errors, _warnings = validate_trace(trace)
    assert errors == []
    return compile_scene(trace)


def test_dsl_map_counter_emit_valid_map_targets_and_scene_objects():
    sess = TraceSession("map counter primitives", {"nums": [1, 2, 1]}, max_events=80)

    dist = sess.map("dist", {"A": 0})
    assert dist.get("A") == 0
    assert dist.get("Z", 99) == 99
    dist["B"] = 1
    assert dist.contains("B") is True
    dist.highlight("B", role="visited")

    counts = sess.counter("prefix_counts", {0: 1})
    assert counts.get(0) == 1
    counts.inc(3)
    counts.inc(0)
    counts.dec(3)

    sess.result({"dist": dist.to_dict(), "counts": counts.to_dict()})
    scene = _validated_scene(sess.to_trace())

    object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
    assert "dist[B]" in object_ids
    assert "prefix_counts[0]" in object_ids
    assert "prefix_counts[3]" in object_ids
    assert scene.result == {"dist": {"A": 0, "B": 1}, "counts": {0: 2, 3: 0}}


def test_dsl_array_swap_and_range_highlight_use_existing_slice_targets():
    sess = TraceSession("array swap range", {"nums": [3, 1, 2]}, max_events=80)

    arr = sess.array("nums", [3, 1, 2])
    arr.swap(0, 2)
    arr.highlight_range(0, 2, role="window")

    sess.result(arr.to_list())
    scene = _validated_scene(sess.to_trace())

    object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
    assert scene.result == [2, 1, 3]
    assert "nums[0:3]" in object_ids
    assert any(
        frame.operation == "set"
        and any(mark.target == "nums[0]" and mark.role == "swap" for mark in frame.marks)
        for frame in scene.frames
    )


def test_dsl_range_structures_reuse_existing_range_visual_state_shapes():
    sess = TraceSession("range structure primitives", {"nums": [1, 3, 5]}, max_events=120)

    bit = sess.fenwick("bit", [1, 3, 5])
    before_bit = bit.range_sum(0, 2)
    bit.add(1, -1)
    after_bit = bit.range_sum(0, 2)

    seg = sess.segment_tree("segment_tree", [1, 3, 5])
    before_seg = seg.query(0, 2)
    seg.update(1, 2)
    after_seg = seg.query(0, 2)

    sess.result({
        "bit": {"before": before_bit, "after": after_bit},
        "segment_tree": {"before": before_seg, "after": after_seg},
    })
    scene = _validated_scene(sess.to_trace())

    frame_patterns = [
        pattern["pattern"]
        for frame in scene.frames
        for pattern in frame.evidence.get("visual_patterns", [])
    ]
    assert scene.result == {
        "bit": {"before": 9, "after": 8},
        "segment_tree": {"before": 9, "after": 8},
    }
    assert "range_structure" in frame_patterns
    assert "range_query_path" in frame_patterns
    assert "range_update_path" in frame_patterns


def test_dsl_flow_network_and_intervals_reuse_renderer_state_shapes():
    sess = TraceSession("flow and intervals", {}, max_events=120)

    net = sess.flow_network(
        "graph",
        {"S": ["A"], "A": ["T"], "T": []},
        {"S->A": 3, "A->T": 2},
        source="S",
        sink="T",
    )
    assert net.residual("S", "A") == 3
    net.highlight_path(["S", "A", "T"])
    net.augment(["S", "A", "T"], 2)

    intervals = sess.intervals("intervals", [[1, 3], [2, 4], [7, 9]])
    intervals.sort()
    intervals.highlight(0, role="current")
    intervals.set(0, [1, 4])

    sess.result({"max_flow": 2, "intervals": intervals.to_list()})
    scene = _validated_scene(sess.to_trace())

    flow_edges = [
        obj
        for frame in scene.frames
        for obj in frame.objects
        if obj.type.value == "edge" and obj.id == "edge:S->A"
    ]
    object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
    frame_patterns = [
        pattern["pattern"]
        for frame in scene.frames
        for pattern in frame.evidence.get("visual_patterns", [])
    ]

    assert any(edge.meta.get("capacity") == 3 and edge.meta.get("flow") == 2 for edge in flow_edges)
    assert "network_flow_edge_label" in frame_patterns
    assert "network_flow_augmenting_path" in frame_patterns
    assert "intervals[0][0]" in object_ids
    assert scene.result == {"max_flow": 2, "intervals": [[1, 4], [2, 4], [7, 9]]}


def test_dsl_trie_nodes_only_snapshot_compiles_without_fake_node_names():
    sess = TraceSession("trie snapshot", {"words": ["apple", "app", "ape", "bat"], "prefix": "ap"}, max_events=120)

    trie = sess.trie("trie")
    for word in ["apple", "app", "ape", "bat"]:
        trie.insert(word)
    answer = trie.prefix_count("ap")
    sess.result(answer)

    trace = SemanticTrace.model_validate(sess.to_trace())
    errors, warnings = validate_trace(trace)
    assert errors == []
    scene = compile_scene(trace)
    scene_errors, scene_warnings = validate_scene(scene)

    object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
    assert scene.result == 3
    assert "node:nodes" not in object_ids
    assert "node:0" in object_ids
    assert "node:1" in object_ids
    assert scene_errors == []
    assert not any("不存在的 node" in warning for warning in scene_warnings), scene_warnings


def test_executor_to_jsonable_converts_tuple_key_memo_state():
    value = {"memo": {(0, True, False): 1}, "nested": [{"k": {(1, False): 2}}]}

    converted = to_jsonable(value)

    assert converted == {"memo": {"(0, True, False)": 1}, "nested": [{"k": {"(1, False)": 2}}]}


def test_scene_compiler_synthesizes_missing_edge_endpoint_nodes():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "edge endpoint compat",
            "input_data": {},
            "result": 1,
            "pseudocode": [],
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "edge:A->B"}],
                    "state": {"dist": {"A": 0, "B": 1}},
                    "role": "current",
                    "reason": "检查 A 到 B 的边",
                    "code_line": 1,
                }
            ],
        }
    )

    scene = compile_scene(trace)
    scene_errors, scene_warnings = validate_scene(scene)
    object_ids = {obj.id for frame in scene.frames for obj in frame.objects}

    assert "edge:A->B" in object_ids
    assert "node:A" in object_ids
    assert "node:B" in object_ids
    assert scene_errors == []
    assert not any("source 不在对象集合" in warning or "target 不在对象集合" in warning for warning in scene_warnings)


def test_sandbox_allows_scalar_numeric_dunder_compatibility():
    code = """
def trace(input_data):
    sess = TraceSession("scalar compat", input_data)
    value = sess.scalar("value", input_data["value"])
    answer = value.__int__()
    sess.result(answer)
    return sess.to_trace()
"""

    raw = run_function(code, "trace", {"value": 4})

    assert raw["result"] == 4


def test_dsl_accepts_default_session_and_table_dimensions():
    sess = TraceSession()
    table = sess.table("dp", 2, 3)
    table[1, 2] = 5
    sess.result(table[1, 2])
    trace = SemanticTrace.model_validate(sess.to_trace())

    assert trace.input_data is None
    assert trace.result == 5
    assert trace.events[0].state["dp"] == [[0, 0, 0], [0, 0, 0]]


def test_executor_normalizes_inverse_bipartite_matching_result():
    assert results_equivalent({"L1": "R2", "L2": "R1"}, {"R1": "L2", "R2": "L1"})

    variant = SolutionVariant(
        id="matching",
        name="matching",
        strategy="inverse trace result compatibility",
        code="def solve(input_data):\n    return {'L1': 'R2', 'L2': 'R1'}\n",
        tracker_code=(
            "def trace(input_data):\n"
            "    sess = TraceSession('matching', input_data)\n"
            "    sess.result({'R1': 'L2', 'R2': 'L1'})\n"
            "    return sess.to_trace()\n"
        ),
    )

    executed = execute_variant(variant, {})

    assert executed.result == {"L1": "R2", "L2": "R1"}
    assert executed.trace is not None
    assert executed.trace.result == {"L1": "R2", "L2": "R1"}


def test_dsl_accepts_deepseek_natural_api_aliases():
    sess = TraceSession("deepseek api aliases", {}, max_events=120)

    with sess.step("处理第 1 个数 1", node="A"):
        sess.note("自然语言阶段标题不应该污染 target id")

    arr = sess.array("disc", [0], reason="创建发现时间数组")
    arr[0] = 1

    dist = sess.map("dist", {"A": 0, "B": 2})
    assert dist.pop("B") == 2
    assert "B" not in dist
    dist.clear()
    assert dist.to_dict() == {}

    bit = sess.fenwick("bit", [1, 3, 5])
    bit.update_all(1, 2)
    assert bit.range_sum(0, 2) == 11

    linked = sess.linked_list("list", [1, 2, 3])
    assert linked.node_at(1) == 1

    net = sess.flow_network(
        "net",
        nodes=["S", "A", "T"],
        edges=[("S", "A"), ("A", "T")],
        capacities={("S", "A"): 3, ("A", "T"): 2},
        source="S",
        sink="T",
    )
    assert net.residual("S", "A") == 3

    net2 = sess.flow_network(
        "net2",
        ["S", "T"],
        [("S", "T")],
        {("S", "T"): 1},
        source="S",
        sink="T",
    )
    net2.set_capacity("S", "T", 2)
    assert net2.residual("S", "T") == 2

    sess.result({"dist": dist.to_dict(), "bit": bit.range_sum(0, 2)})
    trace = SemanticTrace.model_validate(sess.to_trace())
    errors, warnings = validate_trace(trace)

    assert errors == []
    assert not any("target 含空格" in warning for warning in warnings), warnings
    compile_scene(trace)


def test_dsl_accepts_deepseek_container_aliases_and_safe_json_import():
    sess = TraceSession("deepseek container aliases", {}, max_events=120)

    graph = sess.graph("graph", ["A", "B"], [("A", "B")], positions={"A": [0, 0], "B": [1, 0]})
    graph.highlight_edge("A", "B")
    graph.clear_highlight_node("A")
    graph.clear_highlight_edge("A", "B")

    linked = sess.linked_list("list", [1, 2, 3])
    assert linked.get_next(0) == 1
    assert linked.next_id(0) == 1
    assert linked.get_value(1) == 2

    hull = sess.stack("hull", [0, 1, 2])
    assert hull.pop_left() == 2
    assert hull.popleft() == 1

    sess.result({"next": linked.get_next(0), "hull": hull.peek()})
    _validated_scene(sess.to_trace())

    code = "import json\n\ndef verify(input_data):\n    return json.loads(json.dumps(input_data))['value']\n"
    assert run_function(code, "verify", {"value": 3}) == 3
    assert run_function("def solve(input_data):\n    return bin(input_data['value'])\n", "solve", {"value": 5}) == "0b101"
    assert run_function("def solve(input_data):\n    q = deque([input_data['value']])\n    return q.popleft()\n", "solve", {"value": 6}) == 6

    class_code = (
        "class Box:\n"
        "    def __init__(self, value):\n"
        "        self.value = value\n"
        "\n"
        "def solve(input_data):\n"
        "    return Box(input_data['value']).value\n"
    )
    assert run_function(class_code, "solve", {"value": 5}) == 5

    alias_code = (
        "def trace(input_data):\n"
        "    session = TraceSession('alias smoke', input_data)\n"
        "    def helper():\n"
        "        sess.note('uses short alias')\n"
        "    helper()\n"
        "    sess.result(input_data['value'])\n"
        "    return session.to_trace()\n"
    )
    alias_trace = run_function(alias_code, "trace", {"value": 7})
    assert alias_trace["result"] == 7

    global_alias_code = (
        "def helper(value):\n"
        "    sess.note('global helper alias')\n"
        "    return value\n"
        "\n"
        "def trace(input_data):\n"
        "    session = TraceSession('global alias smoke', input_data)\n"
        "    answer = helper(input_data['value'])\n"
        "    sess.result(answer)\n"
        "    return session.to_trace()\n"
    )
    global_alias_trace = run_function(global_alias_code, "trace", {"value": 8})
    assert global_alias_trace["result"] == 8

    injected_session_code = (
        "def trace(input_data, sess):\n"
        "    sess.note('external session')\n"
        "    sess.result(input_data['value'])\n"
        "    return sess.to_trace()\n"
    )
    injected_trace = run_function(injected_session_code, "trace", {"value": 9})
    assert injected_trace["result"] == 9


def test_dsl_accepts_deepseek_residual_aliases_from_full_benchmark():
    sess = TraceSession("deepseek residual aliases", {}, max_events=160)

    table = sess.table("dp", [[0, 1], [1, 2]])
    table.highlight((0, 1), role="current")
    table.highlight_range((0, 0), (1, 1), role="active")

    text = sess.string("n_str", "20")
    text.highlight(0)

    best = sess.scalar("best", 0)
    best.set(3, "update diameter")
    spaced = sess.scalar("rolling factor h", 1)
    spaced.set(2)
    scalar_children = sess.scalar("children", {"a": 1})
    assert "a" in scalar_children
    assert scalar_children["a"] == 1

    graph = sess.graph("graph", ["A"], [], directed=False)
    graph.add_edge("A", "B")
    graph.highlight("A")
    graph.highlight("A", "B")
    graph.highlight_edge("A", "B")
    empty_graph = sess.graph("empty_graph")
    empty_graph.add_edge("L1", "R1")
    with sess.step("relax edge", "A->B"):
        sess.note("step accepts extra positional context")

    linked = sess.linked_list("list", [1, 2])
    assert linked.next_of(0) == 1
    assert linked.next_map == {0: 1, 1: None}
    assert linked.node(0).next == 1
    linked.highlight([1, [2, None]], role="current")
    assert linked.next_of([1, [2, None]]) == 1

    stack = sess.stack("hull", [0, 1])
    stack.data.append(2)
    stack.push(3)
    assert stack.data == [0, 1, 2, 3]
    assert stack.items == [0, 1, 2, 3]
    assert stack.peek_all() == [0, 1, 2, 3]

    trie_tree = sess.tree("trie")
    trie_tree.set_node("root")
    sess._emit("mark", ["trie[root]"], role="current", reason="高亮根节点别名")

    trie = sess.trie("word_trie")
    trie.insert("app")
    assert trie.root == 0
    assert "a" in trie.root.children
    assert trie.root.children["a"].char == "a"
    assert trie.count_prefix("ap") == 1

    sess.result({
        "best": best.value,
        "next": linked.next_of(0),
        "stack": stack.data,
    })
    scene = _validated_scene(sess.to_trace())

    object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
    assert "dp[0][0]" in object_ids
    assert "dp[1][1]" in object_ids
    assert "n_str[0]" in object_ids
    assert "edge:A->B" in object_ids
    assert scene.result == {"best": 3, "next": 1, "stack": [0, 1, 2, 3]}

    trace = SemanticTrace.model_validate(sess.to_trace())
    errors, warnings = validate_trace(trace)
    assert errors == []
    assert not any("target 含空格" in warning for warning in warnings), warnings


def test_repair_context_guides_plain_list_dsl_shadowing():
    info = classify_repair_error("trace 执行失败：AttributeError: 'list' object has no attribute 'highlight'")

    assert info["failure_type"] == "execution"
    assert "TableObj" in info["repair_instruction"]


def test_scene_validator_does_not_treat_answer_dict_as_graph_nodes():
    sess = TraceSession("answer dict is not graph", {}, max_events=20)
    sess.result({"articulation": ["B"], "bridges": [["A", "B"]]})

    scene = compile_scene(SemanticTrace.model_validate(sess.to_trace()))
    errors, warnings = validate_scene(scene)

    assert errors == []
    assert not any("node:articulation" in warning or "node:bridges" in warning for warning in warnings), warnings


def test_repair_context_guides_linked_list_trace_result_mismatch():
    info = classify_repair_error("三指针迭代反转 失败：solve 结果 [2, 1] 与 trace 结果 [] 不一致")

    assert info["failure_type"] == "result_mismatch"
    assert "新 head" in info["repair_instruction"]


def test_repair_context_guides_geometry_point_index_mixup():
    info = classify_repair_error("Andrew 单调链 失败：trace 执行失败：TypeError: list indices must be integers or slices, not list")
    range_info = classify_repair_error("Andrew 单调链 失败：trace 执行失败：TypeError: list indices must be integers or slices, not range")

    assert info["failure_type"] == "execution"
    assert "点索引" in info["repair_instruction"]
    assert "点索引" in range_info["repair_instruction"]


def test_repair_context_guides_tarjan_missing_node_initialization():
    info = classify_repair_error("DFS Tarjan 割点与桥 失败：trace 执行失败：KeyError: 'A'")

    assert info["failure_type"] == "execution"
    assert "disc" in info["repair_instruction"]


def test_repair_context_guides_kruskal_edge_tuple_unpacking():
    info = classify_repair_error(
        "Kruskal 算法 失败：trace 执行失败：ValueError: dictionary update sequence element #0 has length 1; 2 is required"
    )

    assert info["failure_type"] == "execution"
    assert "for u, v, w in edges" in info["repair_instruction"]
    assert "dict(edge)" in info["repair_instruction"]


def test_repair_context_guides_digit_dp_and_trie_trace_mismatch():
    digit = classify_repair_error("逐位前缀计数 失败：结果 10 与 expected 18 不一致")
    digit_title = classify_repair_error("数位DP - 逐位处理前缀 失败：结果 10 与 expected 18 不一致")
    trie = classify_repair_error("Trie 前缀计数 失败：solve 结果 3 与 trace 结果 0 不一致")

    assert "1..n" in digit["repair_instruction"]
    assert "1..n" in digit_title["repair_instruction"]
    assert "prefix_count" in trie["repair_instruction"]


def test_repair_context_guides_tree_diameter_edge_height_mismatch():
    info = classify_repair_error(
        "后序递归聚合高度计算直径 失败：结果 1 与 expected 3 不一致"
    )

    assert info["failure_type"] == "result_mismatch"
    assert "height[child] + 1" in info["repair_instruction"]
    assert "边数" in info["repair_instruction"]


def test_dsl_accepts_deepseek_scalar_rebind_and_tree_node_helpers():
    sess = TraceSession("deepseek scalar tree helpers", {}, max_events=120)

    current_next = sess.scalar("next", 1)
    rebound_next = sess.scalar("next", 2)
    assert rebound_next is current_next
    assert current_next.value == 2
    assert current_next.get() == 2

    tree = sess.tree("trie")
    tree.set_node("root", label="root", meta={"prefix_count": 2})
    tree.set_node("a", value={"prefix_count": 1})
    tree.link("root", "a")
    tree.highlight_node("a")

    sess.result(current_next.value)
    scene = _validated_scene(sess.to_trace())
    object_ids = {obj.id for frame in scene.frames for obj in frame.objects}

    assert "node:root" in object_ids
    assert "node:a" in object_ids


def test_dsl_accepts_empty_array_factory_and_linked_list_noop_on_missing_node():
    sess = TraceSession("deepseek defensive linked list", {}, max_events=120)

    empty = sess.array("answer")
    assert empty.to_list() == []

    linked = sess.linked_list("list", [1, 2])
    linked.reverse_link(None, 0)
    linked.reverse_link(99, None)

    sess.result(empty.to_list())
    _validated_scene(sess.to_trace())


def test_dsl_to_trace_backfills_initialization_and_answer_frames():
    sess = TraceSession("minimal trace backfill", {"value": 3}, max_events=20)

    sess.note("只解释但没有显式 create")
    sess.result(3)
    trace = SemanticTrace.model_validate(sess.to_trace())
    errors, _warnings = validate_trace(trace)

    assert errors == []
    assert trace.events[0].op.value == "create"
    assert trace.events[0].targets[0].id == "input"
    assert trace.events[-1].role == "answer"
    assert "answer" in trace.events[-1].state
    compile_scene(trace)


def test_dsl_accepts_final_deepseek_container_idioms():
    sess = TraceSession("deepseek final idioms", {}, max_events=120)

    extra_array = sess.array("extra", [], "ignored")
    assert extra_array.to_list() == []

    table = sess.table("dist", [[0, 1], [2, 3]])
    table.highlight_cell(1, 1, active=True)
    labeled_table = sess.table("labeled", [[1]], ["value"])
    labeled_table.highlight_cell(0, 0, role=1)

    arr = sess.array("nums", [3, 2, 1])
    arr.append(0, label="tail")
    ptr = sess.pointer("j_ptr", arr, 2)
    rebound_ptr = sess.pointer("j_ptr", arr, 1)
    assert rebound_ptr is ptr
    assert ptr.idx == 1
    ptr.move_to(0)
    assert ptr.idx == 0
    default_ptr = sess.pointer("default_ptr", arr)
    assert default_ptr.idx == 0
    default_ptr.unbind()
    assert default_ptr.idx is None

    first_queue = sess.queue("frontier", ["S"])
    rebound_queue = sess.queue("frontier", ["T"])
    assert rebound_queue is first_queue
    assert rebound_queue.pop() == "T"

    linked = sess.linked_list("list", [1, 2])
    linked.highlight(0, active=True)
    assert linked.get(1) == 2
    assert linked.node(0) == 0
    null_ptr = sess.pointer("prev", None)
    assert null_ptr.idx is None
    curr_ptr = sess.pointer("curr", linked, 0)
    assert curr_ptr.deref() == 1
    rebound_null_ptr = sess.pointer("prev", linked, 1)
    assert rebound_null_ptr is null_ptr
    assert rebound_null_ptr.deref() == 2

    stack = sess.stack("hull", [0, 1, 2])
    assert stack[-1] == 2
    assert stack.peek(-2) == 1

    trie = sess.trie("trie", {"ignored": True})
    assert trie.root == 0
    trie.insert("app")
    assert trie.prefix_count("ap") == 1

    text = sess.string("pattern", "abab")
    text.highlight_range(0, 1)

    first_temp = sess.scalar("next", 1)
    second_temp = sess.array("next", [2])
    assert first_temp.name == second_temp.name == "next"

    sess.result(1)
    _validated_scene(sess.to_trace())


def run_all() -> None:
    test_dsl_map_counter_emit_valid_map_targets_and_scene_objects()
    test_dsl_array_swap_and_range_highlight_use_existing_slice_targets()
    test_dsl_range_structures_reuse_existing_range_visual_state_shapes()
    test_dsl_flow_network_and_intervals_reuse_renderer_state_shapes()
    test_dsl_trie_nodes_only_snapshot_compiles_without_fake_node_names()
    test_executor_to_jsonable_converts_tuple_key_memo_state()
    test_scene_compiler_synthesizes_missing_edge_endpoint_nodes()
    test_sandbox_allows_scalar_numeric_dunder_compatibility()
    test_dsl_accepts_default_session_and_table_dimensions()
    test_executor_normalizes_inverse_bipartite_matching_result()
    test_dsl_accepts_deepseek_natural_api_aliases()
    test_dsl_accepts_deepseek_container_aliases_and_safe_json_import()
    test_dsl_accepts_deepseek_scalar_rebind_and_tree_node_helpers()
    test_dsl_accepts_empty_array_factory_and_linked_list_noop_on_missing_node()
    test_dsl_to_trace_backfills_initialization_and_answer_frames()
    test_dsl_accepts_final_deepseek_container_idioms()
    test_dsl_accepts_deepseek_residual_aliases_from_full_benchmark()
    test_repair_context_guides_plain_list_dsl_shadowing()
    test_scene_validator_does_not_treat_answer_dict_as_graph_nodes()
    test_repair_context_guides_linked_list_trace_result_mismatch()
    test_repair_context_guides_geometry_point_index_mixup()
    test_repair_context_guides_tarjan_missing_node_initialization()
    test_repair_context_guides_kruskal_edge_tuple_unpacking()
    test_repair_context_guides_digit_dp_and_trie_trace_mismatch()
    test_repair_context_guides_tree_diameter_edge_height_mismatch()


if __name__ == "__main__":
    run_all()
    print("dsl_p0_p2_primitives: PASS")
