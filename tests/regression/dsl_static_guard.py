"""Regression tests for static DSL method validation."""

from __future__ import annotations

from algolab.runtime.dsl_guard import DSLMethodError, validate_dsl_method_usage


def test_static_guard_rejects_unknown_method_on_dsl_object():
    code = """
def trace(input_data):
    sess = TraceSession("bad graph", input_data)
    graph = sess.graph("graph", ["A"], [])
    graph.node("A")
    sess.result(0)
    return sess.to_trace()
"""

    try:
        validate_dsl_method_usage(code, "trace")
    except DSLMethodError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected DSLMethodError")

    assert "GraphObj.node" in message
    assert "highlight_node" in message


def test_static_guard_rejects_unknown_factory_on_session():
    code = """
def trace(input_data):
    sess = TraceSession("bad factory", input_data)
    grid = sess.matrix("grid", [[1]])
    sess.result(0)
    return sess.to_trace()
"""

    try:
        validate_dsl_method_usage(code, "trace")
    except DSLMethodError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected DSLMethodError")

    assert "TraceSession.matrix" in message
    assert "table" in message


def test_static_guard_allows_known_dsl_methods_and_plain_python_objects():
    code = """
def trace(input_data):
    sess = TraceSession("good graph", input_data)
    graph = sess.graph("graph", ["A", "B"], [("A", "B")])
    graph.highlight_node("A")
    graph.highlight_edge("A", "B")
    graph.highlight("B")
    graph.update_edge("A", "B", weight=1)
    local = []
    local.append(1)
    sess.result(len(local))
    return sess.to_trace()
"""

    validate_dsl_method_usage(code, "trace")


def test_static_guard_allows_scalar_numeric_dunder_compatibility():
    code = """
def trace(input_data):
    sess = TraceSession("scalar dunder", input_data)
    value = sess.scalar("value", 3)
    answer = value.__int__()
    sess.result(answer)
    return sess.to_trace()
"""

    validate_dsl_method_usage(code, "trace")


def test_static_guard_allows_legacy_safe_aliases_seen_in_saved_artifacts():
    code = """
def trace(input_data):
    sess = TraceSession("legacy aliases", input_data)
    text = sess.string("text", "abc")
    text.highlight(0)
    text.unhighlight(0)
    linked = sess.linked_list("list", [1, 2])
    linked.set_next(0, None)
    linked.link(1, 0)
    sess.result(1)
    return sess.to_trace()
"""

    validate_dsl_method_usage(code, "trace")


def test_static_guard_rejects_trie_internal_node_api():
    code = """
def trace(input_data):
    sess = TraceSession("bad trie", input_data)
    trie = sess.trie("trie")
    trie.insert("app")
    node = trie.root
    answer = len(node.children)
    sess.result(answer)
    return sess.to_trace()
"""

    try:
        validate_dsl_method_usage(code, "trace")
    except DSLMethodError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected DSLMethodError")

    assert "TrieObj.root" in message
    assert "TrieNodeProxy.children" in message
    assert "prefix_count" in message


def test_static_guard_rejects_linked_node_proxy_api():
    code = """
def trace(input_data):
    sess = TraceSession("bad linked", input_data)
    linked = sess.linked_list("list", [1, 2])
    node = linked.node(0)
    nxt = node.next
    sess.result(nxt)
    return sess.to_trace()
"""

    try:
        validate_dsl_method_usage(code, "trace")
    except DSLMethodError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected DSLMethodError")

    assert "LinkedListObj.node" in message
    assert "LinkedNodeProxy.next" in message
    assert "get_next" in message


def test_static_guard_rejects_stack_internal_storage_api():
    code = """
def trace(input_data):
    sess = TraceSession("bad stack", input_data)
    stack = sess.stack("stack", [1, 2])
    stack.data.append(3)
    sess.result(stack.peek_all())
    return sess.to_trace()
"""

    try:
        validate_dsl_method_usage(code, "trace")
    except DSLMethodError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected DSLMethodError")

    assert "StackObj.data" in message
    assert "StackObj.peek_all" in message
    assert "push" in message


def run_all() -> None:
    test_static_guard_rejects_unknown_method_on_dsl_object()
    test_static_guard_rejects_unknown_factory_on_session()
    test_static_guard_allows_known_dsl_methods_and_plain_python_objects()
    test_static_guard_allows_scalar_numeric_dunder_compatibility()
    test_static_guard_allows_legacy_safe_aliases_seen_in_saved_artifacts()
    test_static_guard_rejects_trie_internal_node_api()
    test_static_guard_rejects_linked_node_proxy_api()
    test_static_guard_rejects_stack_internal_storage_api()


if __name__ == "__main__":
    run_all()
    print("dsl_static_guard: PASS")
