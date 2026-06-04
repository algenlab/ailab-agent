"""Small Python execution sandbox for generated solvers and trackers."""

from __future__ import annotations

import ast
import builtins as py_builtins
import json
import math
import multiprocessing as mp
import queue
from typing import Any


class SandboxError(RuntimeError):
    """Raised when generated code cannot be executed safely."""


DANGEROUS_DUNDER_NAMES = {
    "__bases__",
    "__builtins__",
    "__class__",
    "__dict__",
    "__globals__",
    "__import__",
    "__mro__",
    "__subclasses__",
}


SAFE_DUNDER_NAMES = {
    "__bool__",
    "__float__",
    "__index__",
    "__int__",
    "__len__",
    "__str__",
}


def safe_import(name: str, globals=None, locals=None, fromlist=(), level=0):
    allowed = {
        "bisect",
        "collections",
        "copy",
        "functools",
        "heapq",
        "itertools",
        "json",
        "math",
    }
    root = name.split(".", 1)[0]
    if root not in allowed:
        raise ImportError(f"不允许导入模块：{name}")
    return __import__(name, globals, locals, fromlist, level)


def validate_code_safety(code: str) -> None:
    """Reject introspection patterns that can escape the restricted namespace."""

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise SandboxError(f"代码语法错误：{exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and _is_dunder_name(node.attr):
            raise SandboxError(f"禁止访问内部属性：{node.attr}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _is_dunder_name(node.value):
                raise SandboxError(f"禁止访问内部属性名：{node.value}")
            if "__" in node.value:
                raise SandboxError("禁止构造内部属性名")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            if _string_multiplier_can_build_dunder(node.left, node.right) or _string_multiplier_can_build_dunder(node.right, node.left):
                raise SandboxError("禁止构造内部属性名")


def _is_dunder_name(value: str) -> bool:
    if value in SAFE_DUNDER_NAMES:
        return False
    return value in DANGEROUS_DUNDER_NAMES or (value.startswith("__") and value.endswith("__"))


def _string_multiplier_can_build_dunder(left: ast.AST, right: ast.AST) -> bool:
    return (
        isinstance(left, ast.Constant)
        and left.value == "_"
        and isinstance(right, ast.Constant)
        and isinstance(right.value, int)
        and right.value >= 2
    )


def patch_trace_session_aliases(code: str, function_name: str) -> str:
    """Tolerate LLMs that initialize `session` but later use `sess`."""

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    changed = False
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != function_name:
            continue
        assigned_names = {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store)
        }
        loaded_names = {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
        }
        if "sess" not in loaded_names or "sess" in assigned_names:
            continue

        insert_at = None
        alias_source = ""
        for index, statement in enumerate(node.body):
            alias_source = _trace_session_assignment_name(statement)
            if not alias_source:
                continue
            insert_at = index + 1
            break

        if insert_at is None or not alias_source:
            continue
        node.body.insert(0, ast.Global(names=["sess"]))
        node.body.insert(
            insert_at + 1,
            ast.Assign(
                targets=[ast.Name(id="sess", ctx=ast.Store())],
                value=ast.Name(id=alias_source, ctx=ast.Load()),
            ),
        )
        changed = True

    if not changed:
        return code
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _trace_session_assignment_name(statement: ast.stmt) -> str:
    value: ast.AST | None = None
    targets: list[ast.expr] = []
    if isinstance(statement, ast.Assign):
        value = statement.value
        targets = list(statement.targets)
    elif isinstance(statement, ast.AnnAssign):
        value = statement.value
        targets = [statement.target]
    if not (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "TraceSession"
    ):
        return ""
    for target in targets:
        if isinstance(target, ast.Name):
            return target.id
    return ""


def build_namespace() -> dict[str, Any]:
    import bisect
    import collections
    import copy
    import functools
    import heapq
    import itertools

    from algolab.runtime.tracer import Tracer
    from algolab.runtime.dsl import (
        TraceSession,
        ArrayObj, StringObj, TableObj, ScalarObj, PointerObj,
        MapObj, CounterObj,
        HeapObj, StackObj, QueueObj, DequeObj,
        UnionFindObj, LinkedListObj, TrieObj,
        GraphObj, TreeObj, PointsObj,
        FenwickObj, SegmentTreeObj, FlowNetworkObj, IntervalObj,
    )

    builtins = {
        "__import__": safe_import,
        "__build_class__": py_builtins.__build_class__,
        "abs": abs,
        "all": all,
        "any": any,
        "bin": bin,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "Exception": Exception,
        "float": float,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "ord": ord,
        "pow": pow,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "ValueError": ValueError,
        "zip": zip,
    }
    return {
        "__builtins__": builtins,
        "__name__": "__algolab_sandbox__",
        "bisect": bisect,
        "collections": collections,
        "deque": collections.deque,
        "copy": copy,
        "functools": functools,
        "heapq": heapq,
        "itertools": itertools,
        "math": math,
        "Tracer": Tracer,
        "TraceSession": TraceSession,
        "ArrayObj": ArrayObj, "StringObj": StringObj, "TableObj": TableObj,
        "ScalarObj": ScalarObj, "PointerObj": PointerObj,
        "MapObj": MapObj, "CounterObj": CounterObj,
        "HeapObj": HeapObj, "StackObj": StackObj, "QueueObj": QueueObj,
        "DequeObj": DequeObj, "UnionFindObj": UnionFindObj,
        "LinkedListObj": LinkedListObj, "TrieObj": TrieObj,
        "GraphObj": GraphObj, "TreeObj": TreeObj, "PointsObj": PointsObj,
        "FenwickObj": FenwickObj, "SegmentTreeObj": SegmentTreeObj,
        "FlowNetworkObj": FlowNetworkObj, "IntervalObj": IntervalObj,
    }


def json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _worker(code: str, function_name: str, input_data: Any, queue: mp.Queue):
    try:
        code = patch_trace_session_aliases(code, function_name)
        validate_code_safety(code)
        namespace = build_namespace()
        exec(code, namespace)
        fn = namespace.get(function_name)
        if not callable(fn):
            raise SandboxError(f"代码必须定义 {function_name}(input_data)")
        queue.put(("ok", _call_generated(fn, function_name, json_clone(input_data), namespace)))
    except Exception as exc:  # pragma: no cover - executed in child process
        queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _call_generated(fn: Any, function_name: str, input_data: Any, namespace: dict[str, Any]) -> Any:
    if function_name != "trace":
        return fn(input_data)
    argcount = getattr(getattr(fn, "__code__", None), "co_argcount", 1)
    argnames = getattr(getattr(fn, "__code__", None), "co_varnames", ())
    if argcount >= 2 and len(argnames) >= 2 and argnames[1] in {"sess", "session", "trace_session", "tracer"}:
        session = namespace["TraceSession"]("算法可视化", input_data)
        namespace["sess"] = session
        return fn(input_data, session)
    return fn(input_data)


def run_function(code: str, function_name: str, input_data: Any, timeout_s: int = 30) -> Any:
    if not isinstance(code, str) or not code.strip():
        raise SandboxError(f"{function_name} 代码为空")

    result_queue: mp.Queue = mp.Queue(maxsize=1)
    process = mp.Process(target=_worker, args=(code, function_name, input_data, result_queue))
    process.start()
    try:
        status, payload = result_queue.get(timeout=timeout_s)
    except queue.Empty:
        process.terminate()
        process.join(1)
        raise SandboxError(f"{function_name} 执行超时：超过 {timeout_s} 秒")
    process.join(0.2)
    if process.is_alive():
        process.terminate()
        process.join(1)
    if status != "ok":
        raise SandboxError(f"{function_name} 执行失败：{payload}")
    return payload
