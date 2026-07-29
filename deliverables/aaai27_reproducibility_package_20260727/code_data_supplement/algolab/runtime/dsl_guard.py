"""Static checks for generated code that uses the AlgoLab DSL.

The guard is intentionally narrow: it only reasons about variables that are
clearly assigned from TraceSession factories. Plain Python locals are ignored.
This turns invented DSL calls such as ``graph.node(...)`` into a precise repair
signal before sandbox execution reaches a generic AttributeError.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from algolab.runtime import dsl


class DSLMethodError(ValueError):
    """Raised when generated tracker_code calls a non-existent DSL method."""


_FACTORY_TO_CLASS: dict[str, type[Any]] = {
    "array": dsl.ArrayObj,
    "string": dsl.StringObj,
    "table": dsl.TableObj,
    "scalar": dsl.ScalarObj,
    "map": dsl.MapObj,
    "counter": dsl.CounterObj,
    "pointer": dsl.PointerObj,
    "heap": dsl.HeapObj,
    "stack": dsl.StackObj,
    "queue": dsl.QueueObj,
    "deque": dsl.DequeObj,
    "union_find": dsl.UnionFindObj,
    "linked_list": dsl.LinkedListObj,
    "trie": dsl.TrieObj,
    "graph": dsl.GraphObj,
    "tree": dsl.TreeObj,
    "points": dsl.PointsObj,
    "fenwick": dsl.FenwickObj,
    "segment_tree": dsl.SegmentTreeObj,
    "flow_network": dsl.FlowNetworkObj,
    "intervals": dsl.IntervalObj,
}

_ALLOWED_ATTRIBUTES: dict[type[Any], set[str]] = {
    dsl.TraceSession: {
        *_FACTORY_TO_CLASS.keys(),
        "step",
        "note",
        "record",
        "result",
        "to_trace",
    },
    dsl.ArrayObj: {
        "append",
        "highlight",
        "highlight_range",
        "pop",
        "swap",
        "to_list",
        "unhighlight",
    },
    dsl.StringObj: {"compare", "highlight", "highlight_range", "unhighlight"},
    dsl.TableObj: {"highlight", "highlight_range", "rows"},
    dsl.ScalarObj: {"__bool__", "__float__", "__index__", "__int__", "__str__", "get", "set", "value"},
    dsl.MapObj: {"clear", "contains", "get", "highlight", "pop", "set", "to_dict"},
    dsl.CounterObj: {
        "clear",
        "contains",
        "dec",
        "get",
        "highlight",
        "inc",
        "most_common",
        "pop",
        "set",
        "to_dict",
    },
    dsl.PointerObj: {"deref", "idx", "move", "set"},
    dsl.HeapObj: {"empty", "peek", "pop", "push"},
    dsl.StackObj: {"empty", "peek", "pop", "push"},
    dsl.QueueObj: {"append", "appendleft", "empty", "peek", "pop", "popleft", "push", "shift"},
    dsl.DequeObj: {
        "append",
        "appendleft",
        "empty",
        "pop",
        "pop_left",
        "pop_right",
        "popleft",
        "push",
        "push_left",
        "push_right",
        "shift",
    },
    dsl.UnionFindObj: {"find", "union"},
    dsl.LinkedListObj: {
        "get_next",
        "get_value",
        "highlight",
        "insert_after",
        "link",
        "remove",
        "reverse_link",
        "set_next",
        "set_head",
    },
    dsl.LinkedNodeProxy: set(),
    dsl.TrieObj: {"count_prefix", "insert", "prefix_count", "search"},
    dsl.TrieNodeProxy: set(),
    dsl.GraphObj: {
        "add_edge",
        "highlight",
        "highlight_edge",
        "highlight_node",
        "update_edge",
    },
    dsl.TreeObj: {"frame", "highlight_node"},
    dsl.PointsObj: {"add_segment", "highlight", "remove_segment"},
    dsl.FenwickObj: {"add", "prefix_sum", "range_sum", "to_list", "update"},
    dsl.SegmentTreeObj: {"query", "range_sum", "to_list", "update"},
    dsl.FlowNetworkObj: {"augment", "flow_value", "highlight_path", "neighbors", "residual"},
    dsl.IntervalObj: {"append", "highlight", "overlaps", "set", "sort", "to_list"},
}


@dataclass(frozen=True)
class _Finding:
    lineno: int
    object_type: str
    method: str
    allowed: tuple[str, ...]


def validate_dsl_method_usage(code: str, function_name: str = "trace") -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return
    checker = _DSLMethodChecker(function_name)
    checker.visit(tree)
    if checker.findings:
        raise DSLMethodError(_format_findings(checker.findings))


class _DSLMethodChecker(ast.NodeVisitor):
    def __init__(self, function_name: str) -> None:
        self.function_name = function_name
        self._inside_target_function = False
        self._env: dict[str, type[Any]] = {}
        self.findings: list[_Finding] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if node.name != self.function_name:
            return None
        previous = self._inside_target_function
        previous_env = dict(self._env)
        self._inside_target_function = True
        self._env = {}
        self.generic_visit(node)
        self._env = previous_env
        self._inside_target_function = previous
        return None

    def visit_Assign(self, node: ast.Assign) -> Any:
        if self._inside_target_function:
            self._record_assignment(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if self._inside_target_function and node.value is not None:
            self._record_assignment([node.target], node.value)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> Any:
        if self._inside_target_function:
            for item in node.items:
                self.visit(item.context_expr)
                if item.optional_vars is not None:
                    self.visit(item.optional_vars)
            for statement in node.body:
                self.visit(statement)
            return None
        self.generic_visit(node)
        return None

    def visit_Call(self, node: ast.Call) -> Any:
        if self._inside_target_function and isinstance(node.func, ast.Attribute):
            self._check_attribute_call(node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if self._inside_target_function:
            self._check_attribute_access(node)
        self.generic_visit(node)

    def _record_assignment(self, targets: list[ast.expr], value: ast.AST) -> None:
        assigned_type = self._type_from_value(value)
        for target in targets:
            for name in _assigned_names(target):
                if assigned_type is None:
                    self._env.pop(name, None)
                else:
                    self._env[name] = assigned_type

    def _type_from_value(self, value: ast.AST) -> type[Any] | None:
        if _is_trace_session_call(value):
            return dsl.TraceSession
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
        ):
            owner_type = self._env.get(value.func.value.id)
            if owner_type is dsl.TraceSession:
                return _FACTORY_TO_CLASS.get(value.func.attr)
            if owner_type is dsl.LinkedListObj and value.func.attr in {"node", "node_at", "node_proxy"}:
                return dsl.LinkedNodeProxy
            if owner_type is dsl.TrieObj and value.func.attr in {"node"}:
                return dsl.TrieNodeProxy
        if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
            owner_type = self._env.get(value.value.id)
            if owner_type is dsl.TrieObj and value.attr == "root":
                return dsl.TrieNodeProxy
        return None

    def _check_attribute_call(self, node: ast.Call) -> None:
        attr = node.func
        if not isinstance(attr.value, ast.Name):
            return
        owner_type = self._env.get(attr.value.id)
        if owner_type is None:
            return
        if attr.attr not in _allowed_attributes(owner_type):
            self.findings.append(
                _Finding(
                    lineno=getattr(node, "lineno", 0),
                    object_type=owner_type.__name__,
                    method=attr.attr,
                    allowed=_suggestions(owner_type, attr.attr),
                )
            )

    def _check_attribute_access(self, node: ast.Attribute) -> None:
        if not isinstance(node.value, ast.Name):
            return
        owner_type = self._env.get(node.value.id)
        if owner_type is None:
            return
        if node.attr not in _allowed_attributes(owner_type):
            self.findings.append(
                _Finding(
                    lineno=getattr(node, "lineno", 0),
                    object_type=owner_type.__name__,
                    method=node.attr,
                    allowed=_suggestions(owner_type, node.attr),
                )
            )


def _is_trace_session_call(value: ast.AST) -> bool:
    return isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "TraceSession"


def _assigned_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for item in target.elts:
            names.extend(_assigned_names(item))
        return names
    return []


def _allowed_attributes(cls: type[Any]) -> set[str]:
    return set(_ALLOWED_ATTRIBUTES.get(cls, set()))


def _suggestions(cls: type[Any], method: str) -> tuple[str, ...]:
    allowed = sorted(_allowed_attributes(cls))
    preferred = [name for name in allowed if method in name or name in method]
    if cls is dsl.GraphObj:
        preferred.extend(["highlight_node", "highlight_edge", "update_edge"])
    if cls is dsl.TrieObj:
        preferred.extend(["insert", "search", "prefix_count", "count_prefix"])
    if cls is dsl.TrieNodeProxy:
        preferred.extend(["prefix_count", "count_prefix"])
    if cls is dsl.LinkedListObj:
        preferred.extend(["get_next", "get_value", "reverse_link", "set_head", "highlight"])
    if cls is dsl.LinkedNodeProxy:
        preferred.extend(["get_next", "get_value", "reverse_link", "set_head"])
    if cls is dsl.StackObj:
        preferred.extend(["push", "pop", "peek"])
    if cls is dsl.TraceSession:
        preferred.extend(["array", "table", "graph", "trie", "linked_list"])
    result: list[str] = []
    for name in preferred + allowed:
        if name not in result:
            result.append(name)
        if len(result) >= 8:
            break
    return tuple(result)


def _format_findings(findings: list[_Finding]) -> str:
    parts = ["DSL 静态方法检查失败："]
    for finding in findings[:5]:
        allowed = ", ".join(finding.allowed)
        parts.append(
            f"第 {finding.lineno} 行调用了不存在的 {finding.object_type}.{finding.method}；"
            f"只能调用该 DSL 对象的白名单方法。建议改用：{allowed}"
        )
    return "\n".join(parts)
