"""Small Python execution sandbox for generated solvers and trackers."""

from __future__ import annotations

import json
import math
import multiprocessing as mp
import queue
from typing import Any


class SandboxError(RuntimeError):
    """Raised when generated code cannot be executed safely."""


def safe_import(name: str, globals=None, locals=None, fromlist=(), level=0):
    allowed = {
        "bisect",
        "collections",
        "copy",
        "functools",
        "heapq",
        "itertools",
        "math",
    }
    root = name.split(".", 1)[0]
    if root not in allowed:
        raise ImportError(f"不允许导入模块：{name}")
    return __import__(name, globals, locals, fromlist, level)


def build_namespace() -> dict[str, Any]:
    import bisect
    import collections
    import copy
    import functools
    import heapq
    import itertools

    builtins = {
        "__import__": safe_import,
        "abs": abs,
        "all": all,
        "any": any,
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
        "bisect": bisect,
        "collections": collections,
        "copy": copy,
        "functools": functools,
        "heapq": heapq,
        "itertools": itertools,
        "math": math,
    }


def json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _worker(code: str, function_name: str, input_data: Any, queue: mp.Queue):
    try:
        namespace = build_namespace()
        exec(code, namespace)
        fn = namespace.get(function_name)
        if not callable(fn):
            raise SandboxError(f"代码必须定义 {function_name}(input_data)")
        queue.put(("ok", fn(json_clone(input_data))))
    except Exception as exc:  # pragma: no cover - executed in child process
        queue.put(("error", f"{type(exc).__name__}: {exc}"))


def run_function(code: str, function_name: str, input_data: Any, timeout_s: int = 5) -> Any:
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
