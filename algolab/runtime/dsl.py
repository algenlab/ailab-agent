"""Tracer DSL v0 - PoC implementation.

Design goal: LLM writes algorithm code that *looks like normal Python*; the DSL
captures every state mutation and produces a SemanticTrace JSON that is fully
compatible with the existing renderer.

LLM responsibility shrinks from "produce a 50+ event JSON with consistent
target ids, deps, state snapshots" to "write the algorithm using these objects".
Schema correctness is enforced *by the API*, not by prompt rules.

Output is a dict with the same shape as algolab.schemas.semantic_trace.SemanticTrace.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Iterator


_UNSET = object()


def _safe_frame_label(label: Any) -> str:
    text = str(label).strip() or "step"
    return "_".join(text.split())


def _edge_key(edge: Any) -> str:
    if isinstance(edge, str):
        return edge
    if isinstance(edge, (list, tuple)) and len(edge) >= 2:
        return f"{edge[0]}->{edge[1]}"
    return str(edge)


def _graph_from_nodes_edges(nodes: list[Any], edges: list[Any]) -> dict[Any, list[Any]]:
    graph = {node: [] for node in nodes}
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) < 2:
            continue
        src, dst = edge[0], edge[1]
        graph.setdefault(src, []).append(dst)
        graph.setdefault(dst, [])
    return graph


def _capacity_dict(capacity: dict[Any, Any] | None) -> dict[str, int]:
    return {_edge_key(edge): int(value) for edge, value in dict(capacity or {}).items()}


def _container_name(container: Any) -> str:
    if container is None:
        return "None"
    return str(getattr(container, "name", container))


def _table_cell(value: Any, *, default_col: int = 0) -> tuple[int, int]:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2:
            return int(value[0]), int(value[1])
        if len(value) == 1:
            return int(value[0]), default_col
    return int(value), default_col


def _event_is_answer(event: dict[str, Any]) -> bool:
    if event.get("role") == "answer":
        return True
    state = event.get("state")
    return isinstance(state, dict) and "answer" in state


class TraceSession:
    """The single object the algorithm code interacts with.

    Holds the running event log and the current snapshot of every named object.
    Each high-level object (Array, String, Table, Pointer, ...) calls back into
    `_emit_*` to record an event without the algorithm code ever touching a
    target id string.
    """

    def __init__(
        self,
        algorithm: str = "算法可视化",
        input_data: Any = None,
        *,
        max_events: int | None = None,
        pseudocode: list[str] | None = None,
    ) -> None:
        if not isinstance(algorithm, str) and input_data is None:
            input_data = algorithm
            algorithm = "算法可视化"
        self.algorithm = algorithm
        self.input_data = deepcopy(input_data)
        self.max_events = max_events
        self.pseudocode = list(pseudocode or [])
        self._events: list[dict[str, Any]] = []
        self._snapshot: dict[str, Any] = {}
        self._objects: dict[str, Any] = {}
        self._result: Any = None

    # ----- factory methods --------------------------------------------------

    def array(self, name: str, values: list[Any] | None = None, *_args: Any, reason: str = "", **_kwargs: Any) -> "ArrayObj":
        seq = list(values or [])
        obj = ArrayObj(self, name, seq)
        self._register(name, obj, deepcopy(seq))
        self._emit("create", [name], state_override={name: list(seq)},
                   reason=reason or f"创建数组 {name}")
        return obj

    def string(self, name: str, text: str, *, reason: str = "", **_kwargs: Any) -> "StringObj":
        obj = StringObj(self, name, str(text))
        self._register(name, obj, str(text))
        self._emit("create", [name], state_override={name: str(text)},
                   reason=reason or f"创建字符串 {name}")
        return obj

    def table(self, name: str, rows: list[list[Any]] | int, *args: Any, reason: str = "", **_kwargs: Any) -> "TableObj":
        if isinstance(rows, int):
            cols = int(args[0]) if args and isinstance(args[0], int) else int(_kwargs.get("cols") or _kwargs.get("columns") or rows)
            fill = _kwargs.get("fill", _kwargs.get("value", 0))
            data = [[deepcopy(fill) for _ in range(cols)] for _ in range(rows)]
        else:
            data = [list(r) for r in rows]
        obj = TableObj(self, name, data)
        self._register(name, obj, deepcopy(data))
        self._emit("create", [name], state_override={name: deepcopy(data)},
                   reason=reason or f"创建二维表 {name}")
        return obj

    def scalar(self, name: str, value: Any, *, reason: str = "", **_kwargs: Any) -> "ScalarObj":
        existing = self._objects.get(name)
        if isinstance(existing, ScalarObj):
            existing.set(value, reason=reason or f"重设变量 {name} = {value}")
            return existing
        obj = ScalarObj(self, name, value)
        self._register(name, obj, deepcopy(value))
        self._emit("create", [name], state_override={name: deepcopy(value)},
                   reason=reason or f"创建变量 {name}")
        return obj

    def map(self, name: str, items: dict[Any, Any] | None = None, *, reason: str = "", **_kwargs: Any) -> "MapObj":
        data = dict(items or {})
        obj = MapObj(self, name, data)
        self._register(name, obj, deepcopy(data))
        self._emit("create", [name], state_override={name: deepcopy(data)},
                   reason=reason or f"创建映射 {name}")
        return obj

    def counter(self, name: str, items: dict[Any, int] | None = None, *, reason: str = "", **_kwargs: Any) -> "CounterObj":
        data = {key: int(value) for key, value in dict(items or {}).items()}
        obj = CounterObj(self, name, data)
        self._register(name, obj, deepcopy(data))
        self._emit("create", [name], state_override={name: deepcopy(data)},
                   reason=reason or f"创建计数器 {name}")
        return obj

    def pointer(self, name: str, on: Any = None, idx: Any = None,
                role: str = "current", *, reason: str = "", **_kwargs: Any) -> "PointerObj":
        if idx is None and on is not None and not hasattr(on, "name"):
            idx, on = on, None
        elif idx is None and on is not None:
            idx = 0
        existing = self._objects.get(name)
        if isinstance(existing, PointerObj):
            existing.move(idx, on=on, reason=reason or f"重用指针 {name} -> {_container_name(on)}[{idx}]")
            return existing
        obj = PointerObj(self, name, on, idx, role)
        self._register(name, obj, idx)
        self._emit("create", [name], state_override={name: idx}, role=role,
                   reason=reason or f"创建指针 {name} -> {_container_name(on)}[{idx}]")
        return obj

    def graph(
        self,
        name: str,
        nodes: list[Any] | None = None,
        edges: list[tuple] | None = None,
        directed: bool = False,
        *,
        reason: str = "",
        **_kwargs: Any,
    ) -> "GraphObj":
        obj = GraphObj(self, name, list(nodes or []), list(edges or []), directed)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._emit("create", [name], state_override={name: snap},
                   reason=reason or f"创建图 {name}")
        return obj

    def tree(self, name: str = "frame") -> "TreeObj":
        """Used for recursion call stacks via tree.frame() context manager."""
        obj = TreeObj(self, name)
        self._register(name, obj, [])
        self._emit("create", [name], state_override={name: []},
                   reason=f"创建递归栈 {name}")
        return obj

    def heap(self, name: str, items: list[Any] | None = None) -> "HeapObj":
        import heapq
        seq = list(items or [])
        heapq.heapify(seq)
        obj = HeapObj(self, name, seq)
        self._register(name, obj, list(seq))
        self._emit("create", [name], state_override={name: list(seq)},
                   reason=f"创建小根堆 {name}")
        return obj

    def stack(self, name: str, items: list[Any] | None = None) -> "StackObj":
        seq = list(items or [])
        obj = StackObj(self, name, seq)
        self._register(name, obj, list(seq))
        self._emit("create", [name], state_override={name: list(seq)},
                   reason=f"创建栈 {name}")
        return obj

    def queue(self, name: str, items: list[Any] | None = None) -> "QueueObj":
        seq = list(items or [])
        existing = self._objects.get(name)
        if isinstance(existing, QueueObj):
            existing.reset(seq, reason=f"重置队列 {name}")
            return existing
        obj = QueueObj(self, name, seq)
        self._register(name, obj, list(seq))
        self._emit("create", [name], state_override={name: list(seq)},
                   reason=f"创建队列 {name}")
        return obj

    def deque(self, name: str, items: list[Any] | None = None) -> "DequeObj":
        seq = list(items or [])
        obj = DequeObj(self, name, seq)
        self._register(name, obj, list(seq))
        self._emit("create", [name], state_override={name: list(seq)},
                   reason=f"创建双端队列 {name}")
        return obj

    def union_find(self, name: str, n: int) -> "UnionFindObj":
        obj = UnionFindObj(self, name, n)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._emit("create", [name], state_override={name: snap},
                   reason=f"创建并查集 {name} (n={n})")
        return obj

    def linked_list(self, name: str, values: list[Any], doubly: bool = False) -> "LinkedListObj":
        obj = LinkedListObj(self, name, values, doubly=doubly)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._emit("create", [name], state_override={name: snap},
                   reason=f"创建{'双向' if doubly else '单向'}链表 {name}")
        return obj

    def trie(self, name: str = "trie", *_args: Any, reason: str = "", **_kwargs: Any) -> "TrieObj":
        obj = TrieObj(self, name)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._emit("create", [name], state_override={name: snap},
                   reason=reason or f"创建 Trie {name}")
        return obj

    def points(self, name: str, points: list[tuple]) -> "PointsObj":
        obj = PointsObj(self, name, points)
        self._register(name, obj, [list(p) for p in points])
        self._emit("create", [name], state_override={name: [list(p) for p in points]},
                   reason=f"创建点集 {name} ({len(points)} 个点)")
        return obj

    def fenwick(self, name: str, values: list[int], *, reason: str = "", **_kwargs: Any) -> "FenwickObj":
        obj = FenwickObj(self, name, values)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._snapshot["nums"] = list(obj._values)
        self._emit("create", [name], state_override={name: snap, "nums": list(obj._values)},
                   reason=reason or f"创建树状数组 {name}")
        return obj

    def segment_tree(self, name: str, values: list[int], *, reason: str = "", **_kwargs: Any) -> "SegmentTreeObj":
        obj = SegmentTreeObj(self, name, values)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._snapshot["nums"] = list(obj._values)
        self._emit("create", [name], state_override={name: snap, "nums": list(obj._values)},
                   reason=reason or f"创建线段树 {name}")
        return obj

    def flow_network(
        self,
        name: str,
        graph: dict[Any, list[Any]] | list[Any] | None = None,
        capacity: dict[Any, Any] | list[Any] | None = None,
        *args: Any,
        nodes: list[Any] | None = None,
        edges: list[Any] | None = None,
        capacities: dict[Any, Any] | None = None,
        source: Any | None = None,
        sink: Any | None = None,
        reason: str = "",
        **_kwargs: Any,
    ) -> "FlowNetworkObj":
        cap_input: dict[Any, Any] | None = capacities
        if args:
            if nodes is None and edges is None and isinstance(graph, list) and isinstance(capacity, list):
                nodes = graph
                edges = capacity
                cap_input = args[0] if isinstance(args[0], dict) else cap_input
            elif cap_input is None and isinstance(args[0], dict):
                cap_input = args[0]
        if nodes is not None or edges is not None:
            graph_data = _graph_from_nodes_edges(list(nodes or []), list(edges or []))
            capacity_data = _capacity_dict(cap_input)
        else:
            graph_data = dict(graph or {}) if isinstance(graph, dict) else {}
            capacity_data = _capacity_dict(capacity if isinstance(capacity, dict) else cap_input)
        obj = FlowNetworkObj(self, name, graph_data, capacity_data, source=source, sink=sink)
        state = obj._state()
        self._register(name, obj, deepcopy(state[name]))
        for key, value in state.items():
            self._snapshot[key] = deepcopy(value)
        self._emit("create", [name], state_override=state,
                   reason=reason or f"创建网络流图 {name}")
        return obj

    def intervals(self, name: str, intervals: list[list[Any]] | list[tuple[Any, Any]]) -> "IntervalObj":
        rows = [list(item) for item in intervals]
        obj = IntervalObj(self, name, rows)
        self._register(name, obj, deepcopy(rows))
        self._emit("create", [name], state_override={name: deepcopy(rows)},
                   reason=f"创建区间集合 {name}")
        return obj

    # ----- narration --------------------------------------------------------

    @contextmanager
    def step(self, label: str, *args: Any, **_kwargs: Any) -> Iterator[None]:
        """Phase boundary; emits enter/exit and groups events.

        Uses frame: prefix (already whitelisted by trace_validator) with a
        phase/ subspace to distinguish from explicit recursion frames.
        """
        if args:
            label = " ".join(str(part) for part in (label, *args) if part is not None)
        target = f"frame:phase/{_safe_frame_label(label)}"
        self._emit("enter", [target], reason=str(label))
        try:
            yield
        finally:
            self._emit("exit", [target], reason=str(label))

    def note(self, text: str, *, target: str | None = None) -> None:
        self._emit("explain", [target] if target else [], reason=text)

    # ----- termination ------------------------------------------------------

    def result(self, value: Any) -> None:
        self._result = deepcopy(value)

    def to_trace(self) -> dict[str, Any]:
        events = [deepcopy(event) for event in self._events]
        if not any(event.get("op") == "create" for event in events):
            events.insert(0, self._synthetic_event(
                "create",
                ["input"],
                reason="初始化输入",
                state={"input": deepcopy(self.input_data)},
            ))
        if self._result is not None and not any(_event_is_answer(event) for event in events):
            state = deepcopy(self._snapshot)
            state["answer"] = deepcopy(self._result)
            events.append(self._synthetic_event(
                "mark",
                ["answer"],
                value=deepcopy(self._result),
                role="answer",
                reason="返回最终答案",
                state=state,
            ))
        for i, ev in enumerate(events):
            ev["step"] = i
        return {
            "schema_version": "semantic-trace-v1",
            "algorithm": self.algorithm,
            "input_data": deepcopy(self.input_data),
            "result": deepcopy(self._result),
            "pseudocode": list(self.pseudocode),
            "events": events,
        }

    def _synthetic_event(
        self,
        op: str,
        targets: list[str],
        *,
        value: Any = None,
        role: str = "",
        reason: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "step": 0,
            "op": op,
            "targets": [{"id": target} for target in targets],
            "value": deepcopy(value),
            "before": None,
            "after": None,
            "deps": [],
            "role": role,
            "reason": reason,
            "state": deepcopy(state),
            "code_line": 1,
            "teaching": None,
            "interaction": None,
        }

    # ----- internal: emit helpers ------------------------------------------

    def _register(self, name: str, obj: Any, init_value: Any) -> None:
        self._objects[name] = obj
        self._snapshot[name] = deepcopy(init_value)

    def _update_snapshot(self, name: str, new_value: Any) -> None:
        self._snapshot[name] = deepcopy(new_value)

    def _emit(
        self,
        op: str,
        targets: list[str],
        *,
        value: Any = None,
        before: Any = None,
        after: Any = None,
        deps: list[str] | None = None,
        role: str = "",
        reason: str = "",
        state_override: dict[str, Any] | None = None,
        code_line: int = 1,
    ) -> None:
        state = deepcopy(self._snapshot)
        if state_override:
            for k, v in state_override.items():
                state[k] = deepcopy(v)
        # Defensive default: never emit an event with empty reason — demo
        # readiness validators expect every key event to carry a reason.
        if not (reason or "").strip():
            target_summary = " ".join(targets) if targets else ""
            reason = f"{op} {target_summary}".strip() or op
        self._events.append({
            "step": len(self._events),
            "op": op,
            "targets": [{"id": t} for t in targets],
            "value": deepcopy(value),
            "before": deepcopy(before),
            "after": deepcopy(after),
            "deps": [{"id": d} for d in (deps or [])],
            "role": str(role or ""),
            "reason": reason,
            "state": state,
            "code_line": int(code_line or 1),
            "teaching": None,
            "interaction": None,
        })


# =============================================================================
# Object types
# =============================================================================


class ArrayObj:
    def __init__(self, session: TraceSession, name: str, values: list[Any]) -> None:
        self._session = session
        self.name = name
        self._values = list(values)

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, idx: int) -> Any:
        return self._values[idx]

    def __setitem__(self, idx: int, value: Any) -> None:
        if idx == len(self._values):
            self.append(value)
            return
        before = self._values[idx]
        self._values[idx] = value
        self._session._update_snapshot(self.name, self._values)
        self._session._emit(
            "set", [f"{self.name}[{idx}]"],
            value=value, before=before, after=value,
            reason=f"{self.name}[{idx}] = {value}",
        )

    def highlight(self, idx: int, role: str = "current", reason: str = "") -> None:
        self._session._emit("mark", [f"{self.name}[{idx}]"], role=role,
                            reason=reason or f"高亮 {self.name}[{idx}]")

    def unhighlight(self, idx: int) -> None:
        self._session._emit("unmark", [f"{self.name}[{idx}]"],
                            reason=f"取消高亮 {self.name}[{idx}]")

    def compare(self, i: int, j: int, reason: str = "") -> bool:
        self._session._emit(
            "compare",
            [f"{self.name}[{i}]", f"{self.name}[{j}]"],
            value={"left": self._values[i], "right": self._values[j],
                   "equal": self._values[i] == self._values[j]},
            reason=reason or f"比较 {self.name}[{i}]={self._values[i]} 与 {self.name}[{j}]={self._values[j]}",
        )
        return self._values[i] == self._values[j]

    def swap(self, i: int, j: int, *, reason: str = "") -> None:
        before = {i: self._values[i], j: self._values[j]}
        self._values[i], self._values[j] = self._values[j], self._values[i]
        after = {i: self._values[i], j: self._values[j]}
        self._session._update_snapshot(self.name, self._values)
        self._session._emit(
            "set", [f"{self.name}[{i}]", f"{self.name}[{j}]"],
            value={"operation": "swap", "i": i, "j": j},
            before=before,
            after=after,
            role="swap",
            reason=reason or f"交换 {self.name}[{i}] 与 {self.name}[{j}]",
        )

    def highlight_range(self, start: int, end: int, role: str = "current",
                        *, inclusive: bool = True, reason: str = "") -> None:
        stop = end + 1 if inclusive else end
        self._session._emit(
            "mark", [f"{self.name}[{start}:{stop}]"], role=role,
            reason=reason or f"高亮 {self.name}[{start}:{end}]",
        )

    def to_list(self) -> list[Any]:
        return list(self._values)

    def max(self) -> Any:
        return max(self._values) if self._values else None

    # Aliases for natural Python list semantics
    def append(self, value: Any, *, reason: str = "", **_kwargs: Any) -> None:
        idx = len(self._values)
        self._values.append(value)
        self._session._update_snapshot(self.name, self._values)
        self._session._emit(
            "set", [f"{self.name}[{idx}]"],
            value=value, before=None, after=value,
            reason=reason or f"{self.name}.append({value})",
        )

    def pop(self, *, reason: str = "") -> Any:
        if not self._values:
            return None
        idx = len(self._values) - 1
        value = self._values.pop()
        self._session._update_snapshot(self.name, self._values)
        self._session._emit(
            "set", [f"{self.name}[{idx}]"],
            value=None, before=value, after=None,
            reason=reason or f"{self.name}.pop() -> {value}",
        )
        return value


class StringObj:
    def __init__(self, session: TraceSession, name: str, text: str) -> None:
        self._session = session
        self.name = name
        self._text = text

    def __len__(self) -> int:
        return len(self._text)

    def __getitem__(self, idx: int) -> str:
        return self._text[idx]

    def highlight(self, idx: int, role: str = "current", reason: str = "") -> None:
        self._session._emit("mark", [f"{self.name}[{idx}]"], role=role,
                            reason=reason or f"高亮 {self.name}[{idx}]='{self._text[idx]}'")

    def highlight_range(self, start: int, end: int, role: str = "current",
                        *, inclusive: bool = True, reason: str = "", **_kwargs: Any) -> None:
        stop = end + 1 if inclusive else end
        self._session._emit(
            "mark", [f"{self.name}[{start}:{stop}]"], role=role,
            reason=reason or f"高亮 {self.name}[{start}:{end}]",
        )

    def unhighlight(self, idx: int, reason: str = "") -> None:
        self._session._emit(
            "unmark", [f"{self.name}[{idx}]"],
            reason=reason or f"取消高亮 {self.name}[{idx}]",
        )

    def compare(self, i: int, j: int, reason: str = "") -> bool:
        equal = self._text[i] == self._text[j] if 0 <= i < len(self._text) and 0 <= j < len(self._text) else False
        self._session._emit(
            "compare",
            [f"{self.name}[{i}]", f"{self.name}[{j}]"],
            value={"left": self._text[i] if 0 <= i < len(self._text) else None,
                   "right": self._text[j] if 0 <= j < len(self._text) else None,
                   "equal": equal},
            reason=reason or f"比较 {self.name}[{i}] 与 {self.name}[{j}]",
        )
        return equal


class TableObj:
    def __init__(self, session: TraceSession, name: str, rows: list[list[Any]]) -> None:
        self._session = session
        self.name = name
        self._rows = [list(r) for r in rows]

    def __getitem__(self, key: tuple) -> Any:
        i, j = key
        return self._rows[i][j]

    def __setitem__(self, key: tuple, value: Any) -> None:
        i, j = key
        before = self._rows[i][j]
        self._rows[i][j] = value
        self._session._update_snapshot(self.name, self._rows)
        self._session._emit(
            "set", [f"{self.name}[{i}][{j}]"],
            value=value, before=before, after=value,
            reason=f"{self.name}[{i}][{j}] = {value}",
        )

    def rows(self) -> list[list[Any]]:
        return [list(r) for r in self._rows]

    def highlight_cell(self, row: int, col: int, role: str = "current", reason: str = "", **kwargs: Any) -> None:
        if kwargs.get("active") is False:
            role = "inactive"
        self._session._emit(
            "mark", [f"{self.name}[{row}][{col}]"],
            role=role,
            reason=reason or f"高亮 {self.name}[{row}][{col}]",
        )

    def highlight(
        self,
        row: Any,
        col: Any = None,
        role: str = "current",
        reason: str = "",
        **kwargs: Any,
    ) -> None:
        if col is None:
            row, col = _table_cell(row)
        return self.highlight_cell(int(row), int(col), role=role, reason=reason, **kwargs)

    def highlight_range(
        self,
        start: Any,
        end: Any,
        role: str = "current",
        reason: str = "",
        **kwargs: Any,
    ) -> None:
        if kwargs.get("active") is False:
            role = "inactive"
        start_row, start_col = _table_cell(start, default_col=0)
        end_row, end_col = _table_cell(end, default_col=len(self._rows[0]) - 1 if self._rows else 0)
        row_lo, row_hi = sorted((start_row, end_row))
        col_lo, col_hi = sorted((start_col, end_col))
        targets: list[str] = []
        for row in range(row_lo, row_hi + 1):
            if row < 0 or row >= len(self._rows):
                continue
            for col in range(col_lo, col_hi + 1):
                if 0 <= col < len(self._rows[row]):
                    targets.append(f"{self.name}[{row}][{col}]")
        if not targets:
            targets = [self.name]
        self._session._emit(
            "mark",
            targets,
            role=role,
            reason=reason or f"高亮 {self.name}[{row_lo}:{row_hi + 1}][{col_lo}:{col_hi + 1}]",
        )


class ScalarObj:
    def __init__(self, session: TraceSession, name: str, value: Any) -> None:
        self._session = session
        self.name = name
        self._value = value

    @property
    def value(self) -> Any:
        return self._value

    def __contains__(self, item: Any) -> bool:
        try:
            return item in self._value
        except TypeError:
            return False

    def __getitem__(self, key: Any) -> Any:
        return self._value[key]

    def __bool__(self) -> bool:
        return bool(self._value)

    def __int__(self) -> int:
        return int(self._value)

    def __float__(self) -> float:
        return float(self._value)

    def __index__(self) -> int:
        return int(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def get(self, default: Any = None, *, reason: str = "") -> Any:
        self._session._emit(
            "compare", [self.name],
            value=self._value if self._value is not None else default,
            reason=reason or f"读取变量 {self.name}",
        )
        return self._value if self._value is not None else default

    def set(self, value: Any, *args: Any, reason: str = "") -> None:
        if args and not reason:
            reason = " ".join(str(arg) for arg in args if arg is not None)
        before = self._value
        self._value = value
        self._session._update_snapshot(self.name, value)
        self._session._emit(
            "set", [self.name], value=value, before=before, after=value,
            reason=reason or f"{self.name} = {value}",
        )


class MapObj:
    def __init__(self, session: TraceSession, name: str, items: dict[Any, Any]) -> None:
        self._session = session
        self.name = name
        self._items = dict(items)

    def __contains__(self, key: Any) -> bool:
        return self.contains(key)

    def __getitem__(self, key: Any) -> Any:
        return self._items[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.set(key, value)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    def _target(self, key: Any) -> str:
        return f"{self.name}[{key}]"

    def get(self, key: Any, default: Any = None, *, reason: str = "") -> Any:
        exists = key in self._items
        value = self._items.get(key, default)
        target = self._target(key) if exists else self.name
        self._session._emit(
            "compare", [target],
            value={"key": key, "exists": exists, "value": value},
            reason=reason or f"查询 {self.name}[{key}]",
        )
        return value

    def contains(self, key: Any, *, reason: str = "") -> bool:
        exists = key in self._items
        target = self._target(key) if exists else self.name
        self._session._emit(
            "compare", [target],
            value={"key": key, "exists": exists},
            reason=reason or f"检查 {self.name} 是否包含 {key}",
        )
        return exists

    def set(self, key: Any, value: Any, *, reason: str = "") -> None:
        before = self._items.get(key)
        self._items[key] = value
        self._session._update_snapshot(self.name, self._items)
        self._session._emit(
            "set", [self._target(key)],
            value=value, before=before, after=value,
            reason=reason or f"{self.name}[{key}] = {value}",
        )

    def delete(self, key: Any, *, reason: str = "") -> None:
        if key not in self._items:
            return
        before = self._items.pop(key)
        self._session._update_snapshot(self.name, self._items)
        self._session._emit(
            "set", [self._target(key)],
            value=None, before=before, after=None,
            reason=reason or f"删除 {self.name}[{key}]",
        )

    def pop(self, key: Any, default: Any = None, *, reason: str = "") -> Any:
        if key not in self._items:
            self._session._emit(
                "compare", [self.name],
                value={"key": key, "exists": False, "value": default},
                reason=reason or f"{self.name}.pop({key}) 未命中",
            )
            return default
        before = self._items.pop(key)
        self._session._update_snapshot(self.name, self._items)
        self._session._emit(
            "set", [self._target(key)],
            value=default, before=before, after=None,
            reason=reason or f"{self.name}.pop({key}) -> {before}",
        )
        return before

    def clear(self, *, reason: str = "") -> None:
        before = dict(self._items)
        self._items.clear()
        self._session._update_snapshot(self.name, self._items)
        self._session._emit(
            "set", [self.name],
            before=before,
            after={},
            reason=reason or f"清空 {self.name}",
        )

    def highlight(self, key: Any, role: str = "current", reason: str = "") -> None:
        target = self._target(key) if key in self._items else self.name
        self._session._emit("mark", [target], role=role,
                            reason=reason or f"高亮 {self.name}[{key}]")

    def keys(self):
        return self._items.keys()

    def values(self):
        return self._items.values()

    def items(self):
        return self._items.items()

    def to_dict(self) -> dict[Any, Any]:
        return dict(self._items)


class CounterObj(MapObj):
    def __init__(self, session: TraceSession, name: str, items: dict[Any, int]) -> None:
        super().__init__(session, name, {key: int(value) for key, value in items.items()})

    def inc(self, key: Any, delta: int = 1, *, reason: str = "") -> int:
        before = int(self._items.get(key, 0))
        after = before + int(delta)
        self._items[key] = after
        self._session._update_snapshot(self.name, self._items)
        self._session._emit(
            "set", [self._target(key)],
            value=after, before=before, after=after,
            reason=reason or f"{self.name}[{key}] += {delta}",
        )
        return after

    def dec(self, key: Any, delta: int = 1, *, reason: str = "") -> int:
        return self.inc(key, -int(delta), reason=reason or f"{self.name}[{key}] -= {delta}")

    def most_common(self, n: int | None = None) -> list[tuple[Any, int]]:
        items = sorted(self._items.items(), key=lambda item: (-item[1], str(item[0])))
        return items if n is None else items[:n]


class PointerObj:
    def __init__(self, session: TraceSession, name: str,
                 on: Any, idx: Any, role: str = "current") -> None:
        self._session = session
        self.name = name
        self._on = on
        self._idx = idx
        self._role = role

    @property
    def idx(self) -> Any:
        return self._idx

    def move(self, new_idx: Any, *, on: Any = _UNSET, reason: str = "") -> None:
        before = self._idx
        if on is not _UNSET:
            self._on = on
        self._idx = new_idx
        self._session._update_snapshot(self.name, new_idx)
        container = _container_name(self._on)
        self._session._emit(
            "move", [self.name],
            value={"on": container, "idx": new_idx},
            before=before, after=new_idx,
            role=self._role,
            reason=reason or f"{self.name} 移动到 {container}[{new_idx}]",
        )

    def deref(self) -> Any:
        if self._on is None:
            return self._idx
        if isinstance(self._on, LinkedListObj):
            return self._on.get_value(self._idx)
        return self._on[self._idx]

    # Aliases for natural Python semantics
    def set(self, new_idx: Any, *, reason: str = "") -> None:
        return self.move(new_idx, reason=reason)

    def to(self, new_idx: Any, *, reason: str = "") -> None:
        return self.move(new_idx, reason=reason)

    def move_to(self, new_idx: Any, *, reason: str = "") -> None:
        return self.move(new_idx, reason=reason)

    def unbind(self, *, reason: str = "") -> None:
        return self.move(None, on=None, reason=reason or f"{self.name} 置为空指针")


class GraphObj:
    def __init__(self, session: TraceSession, name: str, nodes: list[Any],
                 edges: list[tuple], directed: bool) -> None:
        self._session = session
        self.name = name
        self._nodes = list(nodes)
        # edges as list of dicts so we can carry weights/capacity
        self._edges: list[dict[str, Any]] = []
        for e in edges:
            if len(e) == 2:
                u, v = e
                self._edges.append({"u": u, "v": v})
            elif len(e) == 3:
                u, v, w = e
                self._edges.append({"u": u, "v": v, "weight": w})
        self._directed = directed

    def _snap(self) -> dict[str, Any]:
        return {
            "nodes": list(self._nodes),
            "edges": deepcopy(self._edges),
            "directed": self._directed,
        }

    def highlight_node(self, node: Any, role: str = "current", reason: str = "") -> None:
        self._session._emit("mark", [f"node:{node}"], role=role,
                            reason=reason or f"高亮节点 {node}")

    def highlight_edge(self, u: Any, v: Any, role: str = "path", reason: str = "") -> None:
        self._session._emit("mark", [f"edge:{u}->{v}"], role=role,
                            reason=reason or f"高亮边 {u}->{v}")

    def highlight(self, u: Any, v: Any = None, role: str = "current", reason: str = "") -> None:
        if v is None:
            return self.highlight_node(u, role=role, reason=reason)
        return self.highlight_edge(u, v, role=role, reason=reason)

    def add_edge(self, u: Any, v: Any, weight: Any = None, *, reason: str = "", **attrs: Any) -> None:
        if u not in self._nodes:
            self._nodes.append(u)
        if v not in self._nodes:
            self._nodes.append(v)
        edge = {"u": u, "v": v}
        if weight is not None:
            edge["weight"] = weight
        edge.update(attrs)
        existing = next((item for item in self._edges if item.get("u") == u and item.get("v") == v), None)
        if existing is None:
            self._edges.append(edge)
        else:
            existing.update(edge)
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "link",
            [f"edge:{u}->{v}"],
            deps=[f"node:{u}", f"node:{v}"],
            value=edge,
            reason=reason or f"添加边 {u}->{v}",
        )

    def update_edge(self, u: Any, v: Any, *, reason: str = "", **attrs: Any) -> None:
        for e in self._edges:
            if e["u"] == u and e["v"] == v:
                e.update(attrs)
                break
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"edge:{u}->{v}"], value=attrs,
            reason=reason or f"更新边 {u}->{v} {attrs}",
        )

    def unhighlight_node(self, node: Any, *, reason: str = "") -> None:
        self._session._emit("unmark", [f"node:{node}"],
                            reason=reason or f"取消高亮节点 {node}")

    def clear_highlight_node(self, node: Any, *, reason: str = "") -> None:
        return self.unhighlight_node(node, reason=reason or f"清除节点 {node} 高亮")

    def unhighlight_edge(self, u: Any, v: Any, *, reason: str = "") -> None:
        self._session._emit("unmark", [f"edge:{u}->{v}"],
                            reason=reason or f"取消高亮边 {u}->{v}")

    def clear_highlight_edge(self, u: Any, v: Any, *, reason: str = "") -> None:
        return self.unhighlight_edge(u, v, reason=reason or f"清除边 {u}->{v} 高亮")


class TreeObj:
    """Recursion-call frame stack."""

    def __init__(self, session: TraceSession, name: str) -> None:
        self._session = session
        self.name = name
        self._stack: list[str] = []
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[list[str]] = []

    def _snap(self) -> Any:
        if not self._nodes:
            return list(self._stack)
        return {
            "nodes": list(self._nodes.values()),
            "edges": [edge[:] for edge in self._edges],
            "stack": list(self._stack),
        }

    @contextmanager
    def frame(self, label: str, *, reason: str = "") -> Iterator[None]:
        self._stack.append(label)
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "enter", [f"frame:{_safe_frame_label(label)}"],
            reason=reason or f"进入 {label}",
        )
        try:
            yield
        finally:
            self._stack.pop()
            self._session._update_snapshot(self.name, self._snap())
            self._session._emit(
                "exit", [f"frame:{_safe_frame_label(label)}"],
                reason=f"退出 {label}",
            )

    def set_node(
        self,
        node_id: Any,
        value: Any = None,
        *,
        label: str | None = None,
        meta: dict[str, Any] | None = None,
        reason: str = "",
        **attrs: Any,
    ) -> None:
        node_key = str(node_id)
        node = {"id": node_key, "label": label or node_key}
        if value is not None:
            node["value"] = value
        combined_meta = dict(meta or {})
        combined_meta.update(attrs)
        if combined_meta:
            node["meta"] = combined_meta
        self._nodes[node_key] = node
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"node:{node_key}"],
            value=value if value is not None else combined_meta,
            state_override={self.name: self._snap()},
            reason=reason or f"设置树节点 {node_key}",
        )

    def link(self, parent: Any, child: Any, *, reason: str = "") -> None:
        src, dst = str(parent), str(child)
        edge = [src, dst]
        if edge not in self._edges:
            self._edges.append(edge)
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "link", [f"edge:{src}->{dst}"],
            deps=[f"node:{src}", f"node:{dst}"],
            state_override={self.name: self._snap()},
            reason=reason or f"连接树边 {src}->{dst}",
        )

    def highlight_node(self, node_id: Any, role: str = "current", reason: str = "") -> None:
        node_key = str(node_id)
        self._session._emit(
            "mark", [f"node:{node_key}"],
            role=role,
            state_override={self.name: self._snap()},
            reason=reason or f"高亮树节点 {node_key}",
        )


# =============================================================================
# v1 additions: Heap / Stack / Queue / Deque / UnionFind / LinkedList / Trie / Points
# =============================================================================


class HeapObj:
    """Min-heap by default. Mirrors heapq semantics so LLM-written code stays natural."""

    def __init__(self, session: TraceSession, name: str, items: list[Any]) -> None:
        self._session = session
        self.name = name
        self._items = list(items)

    def __len__(self) -> int:
        return len(self._items)

    def push(self, value: Any, *, reason: str = "") -> None:
        import heapq
        heapq.heappush(self._items, value)
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "push", [self.name], value=value,
            reason=reason or f"{self.name} 入堆 {value}",
        )

    def pop(self, *, reason: str = "") -> Any:
        import heapq
        if not self._items:
            return None
        value = heapq.heappop(self._items)
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "pop", [self.name], value=value,
            reason=reason or f"{self.name} 出堆 {value}",
        )
        return value

    def peek(self) -> Any:
        return self._items[0] if self._items else None

    def empty(self) -> bool:
        return not self._items


class StackObj:
    def __init__(self, session: TraceSession, name: str, items: list[Any]) -> None:
        self._session = session
        self.name = name
        self._items = list(items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    @property
    def data(self) -> list[Any]:
        return self._items

    @property
    def items(self) -> list[Any]:
        return self._items

    def push(self, value: Any, *, reason: str = "") -> None:
        self._items.append(value)
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "push", [self.name], value=value,
            reason=reason or f"{self.name} 入栈 {value}",
        )

    def pop(self, *, reason: str = "") -> Any:
        if not self._items:
            return None
        value = self._items.pop()
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "pop", [self.name], value=value,
            reason=reason or f"{self.name} 出栈 {value}",
        )
        return value

    def peek(self, index: int = -1) -> Any:
        if not self._items:
            return None
        return self._items[index]

    def peek_all(self) -> list[Any]:
        return list(self._items)

    def empty(self) -> bool:
        return not self._items

    def pop_left(self, *, reason: str = "") -> Any:
        return self.pop(reason=reason or f"{self.name}.pop_left()")

    def popleft(self, *, reason: str = "") -> Any:
        return self.pop(reason=reason or f"{self.name}.popleft()")


class QueueObj:
    """FIFO queue. Use append + popleft semantics."""

    def __init__(self, session: TraceSession, name: str, items: list[Any]) -> None:
        from collections import deque
        self._session = session
        self.name = name
        self._items = deque(items)

    def __len__(self) -> int:
        return len(self._items)

    def push(self, value: Any, *, reason: str = "") -> None:
        self._items.append(value)
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "push", [self.name], value=value,
            reason=reason or f"{self.name} 入队 {value}",
        )

    def reset(self, items: list[Any] | None = None, *, reason: str = "") -> None:
        from collections import deque
        before = list(self._items)
        self._items = deque(items or [])
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "set", [self.name],
            before=before,
            after=list(self._items),
            reason=reason or f"重置队列 {self.name}",
        )

    def pop(self, *, reason: str = "") -> Any:
        if not self._items:
            return None
        value = self._items.popleft()
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "pop", [self.name], value=value,
            reason=reason or f"{self.name} 出队 {value}",
        )
        return value

    def peek(self) -> Any:
        return self._items[0] if self._items else None

    def empty(self) -> bool:
        return len(self._items) == 0

    # Aliases for natural Python / JS / collections.deque semantics
    def append(self, value: Any, *, reason: str = "") -> None:
        return self.push(value, reason=reason)

    def appendleft(self, value: Any, *, reason: str = "") -> None:
        # Pure FIFO does not support appendleft; record as push for visualization.
        return self.push(value, reason=reason)

    def popleft(self, *, reason: str = "") -> Any:
        return self.pop(reason=reason)

    def shift(self, *, reason: str = "") -> Any:
        return self.pop(reason=reason)


class DequeObj:
    """Double-ended queue with explicit left/right operations."""

    def __init__(self, session: TraceSession, name: str, items: list[Any]) -> None:
        from collections import deque
        self._session = session
        self.name = name
        self._items = deque(items)

    def __len__(self) -> int:
        return len(self._items)

    def push_left(self, value: Any, *, reason: str = "") -> None:
        self._items.appendleft(value)
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "push", [self.name], value={"side": "left", "value": value},
            reason=reason or f"{self.name} 左入 {value}",
        )

    def push_right(self, value: Any, *, reason: str = "") -> None:
        self._items.append(value)
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "push", [self.name], value={"side": "right", "value": value},
            reason=reason or f"{self.name} 右入 {value}",
        )

    def pop_left(self, *, reason: str = "") -> Any:
        if not self._items:
            return None
        value = self._items.popleft()
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "pop", [self.name], value={"side": "left", "value": value},
            reason=reason or f"{self.name} 左出 {value}",
        )
        return value

    def pop_right(self, *, reason: str = "") -> Any:
        if not self._items:
            return None
        value = self._items.pop()
        self._session._update_snapshot(self.name, list(self._items))
        self._session._emit(
            "pop", [self.name], value={"side": "right", "value": value},
            reason=reason or f"{self.name} 右出 {value}",
        )
        return value

    def empty(self) -> bool:
        return len(self._items) == 0

    # Aliases for natural collections.deque / Python list semantics
    def appendleft(self, value: Any, *, reason: str = "") -> None:
        return self.push_left(value, reason=reason)

    def append(self, value: Any, *, reason: str = "") -> None:
        return self.push_right(value, reason=reason)

    def push(self, value: Any, *, reason: str = "") -> None:
        return self.push_right(value, reason=reason)

    def popleft(self, *, reason: str = "") -> Any:
        return self.pop_left(reason=reason)

    def pop(self, *, reason: str = "") -> Any:
        return self.pop_right(reason=reason)

    def shift(self, *, reason: str = "") -> Any:
        return self.pop_left(reason=reason)


class UnionFindObj:
    """Disjoint-set with path compression. Each find/union emits an event."""

    def __init__(self, session: TraceSession, name: str, n: int) -> None:
        self._session = session
        self.name = name
        self._parent = list(range(n))
        self._rank = [0] * n

    def _snap(self) -> dict[str, Any]:
        return {"parent": list(self._parent), "rank": list(self._rank)}

    def find(self, x: int, *, reason: str = "") -> int:
        path = [x]
        while self._parent[path[-1]] != path[-1]:
            path.append(self._parent[path[-1]])
        root = path[-1]
        for node in path[:-1]:
            self._parent[node] = root
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [self.name], value={"x": x, "root": root, "path": path},
            reason=reason or f"find({x}) -> {root}",
        )
        return root

    def union(self, x: int, y: int, *, reason: str = "") -> bool:
        rx = self._find_silent(x)
        ry = self._find_silent(y)
        if rx == ry:
            self._session._emit(
                "compare", [self.name],
                value={"x": x, "y": y, "same_root": True, "root": rx},
                reason=reason or f"{x}, {y} 已在同一集合 (root={rx})",
            )
            return False
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "link", [self.name],
            value={"x": x, "y": y, "new_root": rx, "merged": [x, y]},
            reason=reason or f"union({x},{y}) 合并为 root={rx}",
        )
        return True

    def _find_silent(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x


class LinkedNodeProxy(int):
    def __new__(cls, linked_list: "LinkedListObj", node_id: int):
        obj = int.__new__(cls, node_id)
        obj._linked_list = linked_list
        return obj

    @property
    def _data(self) -> dict[str, Any] | None:
        return next((node for node in self._linked_list._nodes if node.get("id") == int(self)), None)

    @property
    def id(self) -> int:
        return int(self)

    @property
    def value(self) -> Any:
        node = self._data
        return None if node is None else node.get("value")

    @property
    def next(self) -> Any:
        node = self._data
        next_id = None if node is None else node.get("next")
        return None if next_id is None else self._linked_list.node_proxy(next_id)

    @property
    def prev(self) -> Any:
        node = self._data
        prev_id = None if node is None else node.get("prev")
        return None if prev_id is None else self._linked_list.node_proxy(prev_id)


class LinkedListObj:
    """Singly or doubly linked list, kept as a list of (id, value, next, prev?)."""

    def __init__(self, session: TraceSession, name: str, values: list[Any],
                 doubly: bool = False) -> None:
        self._session = session
        self.name = name
        self.doubly = doubly
        self._nodes: list[dict[str, Any]] = []
        for i, v in enumerate(values):
            node = {"id": i, "value": v, "next": (i + 1 if i + 1 < len(values) else None)}
            if doubly:
                node["prev"] = i - 1 if i > 0 else None
            self._nodes.append(node)
        self._head = 0 if values else None
        self._next_id = len(values)

    def _snap(self) -> dict[str, Any]:
        return {
            "head": self._head,
            "doubly": self.doubly,
            "nodes": deepcopy(self._nodes),
        }

    def _node_id(self, node_ref: Any) -> Any:
        if any(node.get("id") == node_ref for node in self._nodes):
            return node_ref
        if isinstance(node_ref, dict):
            if node_ref.get("id") not in (None, ""):
                return node_ref.get("id")
            if "value" in node_ref:
                node_ref = node_ref.get("value")
        elif isinstance(node_ref, (list, tuple)) and node_ref:
            node_ref = node_ref[0]
        for node in self._nodes:
            if node.get("value") == node_ref:
                return node.get("id")
        return node_ref

    def node_proxy(self, node_id: Any) -> LinkedNodeProxy:
        return LinkedNodeProxy(self, int(self._node_id(node_id)))

    def insert_after(self, node_id: int, value: Any, *, reason: str = "") -> int:
        node_id = self._node_id(node_id)
        new_id = self._next_id
        self._next_id += 1
        target = next(n for n in self._nodes if n["id"] == node_id)
        new_node = {"id": new_id, "value": value, "next": target["next"]}
        if self.doubly:
            new_node["prev"] = node_id
            if target["next"] is not None:
                nxt = next(n for n in self._nodes if n["id"] == target["next"])
                nxt["prev"] = new_id
        target["next"] = new_id
        self._nodes.append(new_node)
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "link", [f"node:{new_id}"], value={"after": node_id, "value": value},
            reason=reason or f"在节点 {node_id} 后插入 {value}",
        )
        return new_id

    def remove(self, node_id: int, *, reason: str = "") -> None:
        node_id = self._node_id(node_id)
        target = next(n for n in self._nodes if n["id"] == node_id)
        prev_node = next((n for n in self._nodes if n["next"] == node_id), None)
        if prev_node is not None:
            prev_node["next"] = target["next"]
        else:
            self._head = target["next"]
        if self.doubly and target["next"] is not None:
            nxt = next(n for n in self._nodes if n["id"] == target["next"])
            nxt["prev"] = target.get("prev")
        self._nodes = [n for n in self._nodes if n["id"] != node_id]
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "unlink", [f"node:{node_id}"],
            reason=reason or f"删除节点 {node_id}",
        )

    def reverse_link(self, node_id: int, new_next: Any, *, reason: str = "") -> None:
        """For reverse-linked-list and similar pointer-flipping algorithms."""
        node_id = self._node_id(node_id)
        new_next = self._node_id(new_next) if new_next is not None else None
        target = next((n for n in self._nodes if n["id"] == node_id), None)
        if target is None:
            self._session._emit(
                "compare", [self.name],
                value={"node_id": node_id, "next": new_next, "exists": False},
                reason=reason or f"跳过不存在的节点 {node_id}",
            )
            return
        target["next"] = new_next
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"node:{node_id}"], value={"next": new_next},
            reason=reason or f"节点 {node_id}.next = {new_next}",
        )

    def set_head(self, node_id: Any, *, reason: str = "") -> None:
        node_id = self._node_id(node_id) if node_id is not None else None
        before = self._head
        self._head = node_id
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"{self.name}.head"], value=node_id, before=before, after=node_id,
            reason=reason or f"head -> {node_id}",
        )

    def highlight(self, node_id: int, role: str = "current", reason: str = "", **kwargs: Any) -> None:
        node_id = self._node_id(node_id)
        if kwargs.get("active") is False:
            role = "inactive"
        self._session._emit("mark", [f"node:{node_id}"], role=role,
                            reason=reason or f"高亮节点 {node_id}")

    def node_at(self, index: int, *, reason: str = "") -> Any:
        current = self._head
        steps = 0
        while current is not None and steps < index:
            node = next((n for n in self._nodes if n["id"] == current), None)
            current = None if node is None else node.get("next")
            steps += 1
        target = f"node:{current}" if current is not None else self.name
        self._session._emit(
            "mark", [target],
            value=current,
            role="current",
            reason=reason or f"{self.name}.node_at({index}) -> {current}",
        )
        return None if current is None else self.node_proxy(current)

    def node(self, index: int, *, reason: str = "") -> Any:
        return self.node_at(index, reason=reason or f"{self.name}.node({index})")

    def get_next(self, node_id: int, *, reason: str = "") -> Any:
        node_id = self._node_id(node_id)
        node = next((n for n in self._nodes if n["id"] == node_id), None)
        next_id = None if node is None else node.get("next")
        target = f"node:{node_id}" if node is not None else self.name
        self._session._emit(
            "compare", [target],
            value={"next": next_id},
            role="current",
            reason=reason or f"{self.name}.get_next({node_id}) -> {next_id}",
        )
        return next_id

    def next_id(self, node_id: int, *, reason: str = "") -> Any:
        return self.get_next(node_id, reason=reason or f"{self.name}.next_id({node_id})")

    def next_of(self, node_id: int, *, reason: str = "") -> Any:
        return self.get_next(node_id, reason=reason or f"{self.name}.next_of({node_id})")

    @property
    def next_map(self) -> dict[Any, Any]:
        return {node.get("id"): node.get("next") for node in self._nodes}

    def get_value(self, node_id: int, *, reason: str = "") -> Any:
        node_id = self._node_id(node_id)
        node = next((n for n in self._nodes if n["id"] == node_id), None)
        value = None if node is None else node.get("value")
        target = f"node:{node_id}" if node is not None else self.name
        self._session._emit(
            "compare", [target],
            value={"value": value},
            role="current",
            reason=reason or f"{self.name}.get_value({node_id}) -> {value}",
        )
        return value

    def get(self, node_id: int, default: Any = None, *, reason: str = "") -> Any:
        value = self.get_value(node_id, reason=reason or f"{self.name}.get({node_id})")
        return default if value is None else value

    # Aliases for natural list/linked-list semantics
    def link(self, node_id: int, new_next: Any, *, reason: str = "") -> None:
        return self.reverse_link(node_id, new_next, reason=reason)

    def set_next(self, node_id: int, new_next: Any, *, reason: str = "") -> None:
        return self.reverse_link(node_id, new_next, reason=reason)

    def head(self, node_id: Any, *, reason: str = "") -> None:
        return self.set_head(node_id, reason=reason)


class TrieNodeProxy(int):
    def __new__(cls, trie: "TrieObj", node_id: int):
        obj = int.__new__(cls, node_id)
        obj._trie = trie
        return obj

    @property
    def _data(self) -> dict[str, Any]:
        return self._trie._nodes[int(self)]

    @property
    def id(self) -> int:
        return int(self)

    @property
    def char(self) -> str:
        return str(self._data.get("char", ""))

    @property
    def children(self) -> dict[str, "TrieNodeProxy"]:
        return {ch: self._trie.node(child_id) for ch, child_id in self._data.get("children", {}).items()}

    @property
    def terminal(self) -> bool:
        return bool(self._data.get("terminal"))

    @property
    def count(self) -> int:
        return int(self._data.get("count") or 0)


class TrieObj:
    """Trie with insert/search/prefix_count operations."""

    def __init__(self, session: TraceSession, name: str) -> None:
        self._session = session
        self.name = name
        # nodes: list of dicts {id, char, children: {char: id}, terminal: bool, count: int}
        self._nodes: list[dict[str, Any]] = [
            {"id": 0, "char": "", "children": {}, "terminal": False, "count": 0}
        ]
        self._next_id = 1

    def _snap(self) -> dict[str, Any]:
        return {"nodes": deepcopy(self._nodes)}

    @property
    def root(self) -> TrieNodeProxy:
        return self.node(0)

    def node(self, node_id: int) -> TrieNodeProxy:
        return TrieNodeProxy(self, int(node_id))

    def insert(self, word: str, *, reason: str = "") -> None:
        cur = 0
        for ch in word:
            self._nodes[cur]["count"] += 1
            children = self._nodes[cur]["children"]
            if ch not in children:
                new_id = self._next_id
                self._next_id += 1
                self._nodes.append({
                    "id": new_id, "char": ch, "children": {},
                    "terminal": False, "count": 0,
                })
                children[ch] = new_id
                self._session._update_snapshot(self.name, self._snap())
                self._session._emit(
                    "create", [f"node:{new_id}"],
                    value={"char": ch, "parent": cur},
                    reason=f"创建节点 '{ch}' (id={new_id})",
                )
            cur = children[ch]
        self._nodes[cur]["count"] += 1
        self._nodes[cur]["terminal"] = True
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"node:{cur}"], value={"terminal": True, "word": word},
            reason=reason or f"插入 '{word}' 完成",
        )

    def search(self, word: str, *, reason: str = "") -> bool:
        cur = 0
        for ch in word:
            self._session._emit(
                "mark", [f"node:{cur}"], role="visit",
                reason=f"在节点 {cur} 查找 '{ch}'",
            )
            children = self._nodes[cur]["children"]
            if ch not in children:
                self._session._emit(
                    "explain", [], reason=f"未找到 '{ch}'，'{word}' 不存在",
                )
                return False
            cur = children[ch]
        result = self._nodes[cur]["terminal"]
        self._session._emit(
            "explain", [f"node:{cur}"],
            reason=reason or f"'{word}' {'找到' if result else '前缀存在但非完整词'}",
        )
        return result

    def prefix_count(self, prefix: str, *, reason: str = "") -> int:
        cur = 0
        for ch in prefix:
            children = self._nodes[cur]["children"]
            if ch not in children:
                self._session._emit(
                    "explain", [], reason=f"前缀 '{prefix}' 不存在 → 0",
                )
                return 0
            cur = children[ch]
        cnt = self._nodes[cur]["count"]
        self._session._emit(
            "explain", [f"node:{cur}"],
            reason=reason or f"前缀 '{prefix}' 共 {cnt} 个词",
        )
        return cnt

    def count_prefix(self, prefix: str, *, reason: str = "") -> int:
        return self.prefix_count(prefix, reason=reason or f"count_prefix('{prefix}')")


class PointsObj:
    """2D points / polylines for geometry algorithms."""

    def __init__(self, session: TraceSession, name: str, points: list[tuple]) -> None:
        self._session = session
        self.name = name
        self._points = [list(p) for p in points]

    def __len__(self) -> int:
        return len(self._points)

    def __getitem__(self, idx: int) -> list:
        return list(self._points[idx])

    def highlight(self, idx: int, role: str = "current", reason: str = "") -> None:
        self._session._emit(
            "mark", [f"{self.name}[{idx}]"], role=role,
            reason=reason or f"高亮点 {idx}={tuple(self._points[idx])}",
        )

    def add_segment(self, i: int, j: int, role: str = "edge", reason: str = "") -> None:
        self._session._emit(
            "link", [f"{self.name}[{i}]->{j}"], role=role,
            value={"from": list(self._points[i]), "to": list(self._points[j])},
            reason=reason or f"连线 {i}->{j}",
        )

    def remove_segment(self, i: int, j: int, *, reason: str = "") -> None:
        self._session._emit(
            "unlink", [f"{self.name}[{i}]->{j}"],
            reason=reason or f"移除线段 {i}->{j}",
        )


class FenwickObj:
    """Fenwick tree / Binary Indexed Tree for prefix and range sums."""

    def __init__(self, session: TraceSession, name: str, values: list[int]) -> None:
        self._session = session
        self.name = name
        self._values = list(values)
        self._bit = [0] * (len(values) + 1)
        for i, value in enumerate(values):
            j = i + 1
            while j < len(self._bit):
                self._bit[j] += value
                j += j & -j

    def _snap(self) -> list[int]:
        return list(self._bit)

    def prefix_sum(self, count: int, *, reason: str = "") -> int:
        total = 0
        j = min(max(int(count), 0), len(self._bit) - 1)
        path: list[str] = []
        while j > 0:
            total += self._bit[j]
            path.append(f"bit[{j}]" if self.name == "bit" else f"{self.name}[{j}]")
            j -= j & -j
        target = path[-1] if path else self.name
        self._session._emit(
            "mark", [target],
            value=total,
            deps=path,
            role="current",
            state_override={self.name: self._snap(), "nums": list(self._values), "query_path": path},
            reason=reason or f"{self.name}.prefix_sum({count}) = {total}",
        )
        return total

    def range_sum(self, left: int, right: int, *, reason: str = "") -> int:
        right_sum = self.prefix_sum(right + 1, reason=reason or f"查询右端前缀 {right + 1}")
        left_sum = self.prefix_sum(left, reason=reason or f"查询左端前缀 {left}")
        result = right_sum - left_sum
        self._session._emit(
            "set", ["answer"],
            value=result,
            deps=[self.name],
            role="current",
            state_override={self.name: self._snap(), "nums": list(self._values), "query": [left, right], "query_path": [self.name]},
            reason=reason or f"区间 [{left},{right}] 和 = {right_sum} - {left_sum}",
        )
        return result

    def add(self, index: int, delta: int, *, reason: str = "") -> None:
        if not (0 <= index < len(self._values)):
            return
        self._values[index] += delta
        self._session._update_snapshot("nums", list(self._values))
        j = index + 1
        path: list[str] = []
        while j < len(self._bit):
            before = self._bit[j]
            self._bit[j] += delta
            target = f"{self.name}[{j}]"
            path.append(target)
            self._session._update_snapshot(self.name, self._snap())
            self._session._emit(
                "set", [target],
                value=self._bit[j], before=before, after=self._bit[j],
                deps=[f"nums[{index}]"],
                role="current",
                state_override={self.name: self._snap(), "nums": list(self._values), "update_path": list(path)},
                reason=reason or f"{self.name}[{j}] 加上 delta={delta}",
            )
            j += j & -j

    def update(self, index: int, value: int, *, reason: str = "") -> None:
        if not (0 <= index < len(self._values)):
            return
        self.add(index, value - self._values[index], reason=reason or f"更新 {index} 为 {value}")

    def update_all(self, index: int, delta: int, *, reason: str = "") -> None:
        self.add(index, delta, reason=reason or f"从 {index} 开始更新 BIT 路径，delta={delta}")

    def to_list(self) -> list[int]:
        return list(self._bit)


class SegmentTreeObj:
    """Segment tree for range sums, rendered through the existing tree layout."""

    def __init__(self, session: TraceSession, name: str, values: list[int]) -> None:
        self._session = session
        self.name = name
        self._values = list(values)

    def _node_id(self, idx: int, left: int, right: int) -> str:
        return f"seg_{idx}_{left}_{right}"

    def _snap(self) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[list[str]] = []
        if not self._values:
            return {"nodes": nodes, "edges": edges}

        def build(idx: int, left: int, right: int) -> tuple[str, int]:
            node_id = self._node_id(idx, left, right)
            if left == right:
                total = self._values[left]
            else:
                mid = (left + right) // 2
                left_id, left_sum = build(idx * 2, left, mid)
                right_id, right_sum = build(idx * 2 + 1, mid + 1, right)
                edges.append([node_id, left_id])
                edges.append([node_id, right_id])
                total = left_sum + right_sum
            nodes.append({"id": node_id, "label": f"[{left},{right}]={total}", "meta": {"l": left, "r": right, "sum": total}})
            return node_id, total

        build(1, 0, len(self._values) - 1)
        return {"nodes": nodes, "edges": edges}

    def query(self, left: int, right: int, *, reason: str = "") -> int:
        if not self._values:
            return 0
        path: list[str] = []
        covered: list[str] = []

        def walk(idx: int, lo: int, hi: int) -> int:
            node_ref = f"node:{self._node_id(idx, lo, hi)}"
            path.append(node_ref)
            if right < lo or hi < left:
                return 0
            if left <= lo and hi <= right:
                covered.append(node_ref)
                return sum(self._values[lo:hi + 1])
            mid = (lo + hi) // 2
            return walk(idx * 2, lo, mid) + walk(idx * 2 + 1, mid + 1, hi)

        result = walk(1, 0, len(self._values) - 1)
        targets = covered or path[:1] or [self.name]
        self._session._emit(
            "mark", targets,
            value=result,
            deps=["query[0]", "query[1]"],
            role="current",
            state_override={self.name: self._snap(), "nums": list(self._values), "query": [left, right], "query_path": path, "cover_path": covered},
            reason=reason or f"查询线段树区间 [{left},{right}]",
        )
        return result

    def range_sum(self, left: int, right: int, *, reason: str = "") -> int:
        return self.query(left, right, reason=reason)

    def update(self, index: int, value: int, *, reason: str = "") -> None:
        if not (0 <= index < len(self._values)):
            return
        before = self._values[index]
        self._values[index] = value
        self._session._update_snapshot("nums", list(self._values))
        path: list[str] = []
        if self._values:
            idx, lo, hi = 1, 0, len(self._values) - 1
            while True:
                path.append(f"node:{self._node_id(idx, lo, hi)}")
                if lo == hi:
                    break
                mid = (lo + hi) // 2
                if index <= mid:
                    idx, hi = idx * 2, mid
                else:
                    idx, lo = idx * 2 + 1, mid + 1
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", path or [self.name],
            value=value, before=before, after=value,
            deps=[f"nums[{index}]"],
            role="current",
            state_override={self.name: self._snap(), "nums": list(self._values), "update": [index, value], "update_path": path},
            reason=reason or f"更新线段树位置 {index}: {before} -> {value}",
        )

    def to_list(self) -> list[int]:
        return list(self._values)


class FlowNetworkObj:
    """Flow network helper that exposes capacity/flow/residual state."""

    def __init__(
        self,
        session: TraceSession,
        name: str,
        graph: dict[Any, list[Any]],
        capacity: dict[str, int],
        *,
        source: Any | None = None,
        sink: Any | None = None,
    ) -> None:
        self._session = session
        self.name = name
        self._graph = {str(node): [str(v) for v in neighbors] for node, neighbors in graph.items()}
        self._capacity = {str(edge): int(value) for edge, value in capacity.items()}
        self._flow = {edge: 0 for edge in self._capacity}
        self.source = None if source is None else str(source)
        self.sink = None if sink is None else str(sink)

    def _residuals(self) -> dict[str, int]:
        residual = {edge: cap - self._flow.get(edge, 0) for edge, cap in self._capacity.items()}
        for edge, flow in self._flow.items():
            if "->" in edge and flow > 0:
                u, v = edge.split("->", 1)
                residual[f"{v}->{u}"] = flow
        return residual

    def _state(self, *, path: list[str] | None = None) -> dict[str, Any]:
        state = {
            self.name: deepcopy(self._graph),
            "capacity": dict(self._capacity),
            "cap": dict(self._capacity),
            "flow": dict(self._flow),
            "residual": self._residuals(),
        }
        if self.source is not None:
            state["source"] = self.source
        if self.sink is not None:
            state["sink"] = self.sink
        if path:
            state["augmenting_path"] = list(path)
            state["augmenting_edges"] = [f"{u}->{v}" for u, v in zip(path, path[1:])]
        return state

    def _publish(self) -> None:
        for key, value in self._state().items():
            self._session._update_snapshot(key, value)

    def residual(self, u: Any, v: Any, *, reason: str = "") -> int:
        src, dst = str(u), str(v)
        key = f"{src}->{dst}"
        value = self._residuals().get(key, 0)
        self._session._emit(
            "compare", [f"edge:{src}->{dst}"],
            value=value,
            deps=[f"cap[{key}]", f"flow[{key}]"],
            role="candidate",
            state_override=self._state(),
            reason=reason or f"检查残量 {src}->{dst} = {value}",
        )
        return value

    def neighbors(self, u: Any) -> list[str]:
        node = str(u)
        result = list(self._graph.get(node, []))
        for edge, value in self._residuals().items():
            if value <= 0 or "->" not in edge:
                continue
            src, dst = edge.split("->", 1)
            if src == node and dst not in result:
                result.append(dst)
        return result

    def set_capacity(self, u: Any, v: Any, capacity: int, *, reason: str = "") -> None:
        src, dst = str(u), str(v)
        key = f"{src}->{dst}"
        before = self._capacity.get(key)
        self._capacity[key] = int(capacity)
        self._flow.setdefault(key, 0)
        self._graph.setdefault(src, [])
        if dst not in self._graph[src]:
            self._graph[src].append(dst)
        self._graph.setdefault(dst, [])
        self._publish()
        self._session._emit(
            "set", [f"edge:{src}->{dst}"],
            value={"capacity": int(capacity)},
            before=before,
            after=int(capacity),
            state_override=self._state(),
            reason=reason or f"设置容量 {src}->{dst} = {capacity}",
        )

    def highlight_path(self, path: list[Any], role: str = "path", reason: str = "") -> None:
        nodes = [str(item) for item in path]
        targets = [f"edge:{u}->{v}" for u, v in zip(nodes, nodes[1:])]
        self._session._emit(
            "mark", targets or [self.name],
            role=role,
            state_override=self._state(path=nodes),
            reason=reason or f"高亮增广路径 {' -> '.join(nodes)}",
        )

    def augment(self, path: list[Any] | list[tuple[Any, Any]], amount: int, *, reason: str = "") -> None:
        pairs = _flow_path_pairs(path)
        nodes = [pairs[0][0], *[v for _u, v in pairs]] if pairs else []
        for src, dst in pairs:
            key = f"{src}->{dst}"
            reverse = f"{dst}->{src}"
            if key in self._capacity:
                before = self._flow.get(key, 0)
                self._flow[key] = before + amount
                target_key = key
            elif reverse in self._capacity:
                before = self._flow.get(reverse, 0)
                self._flow[reverse] = before - amount
                target_key = reverse
            else:
                continue
            self._publish()
            self._session._emit(
                "set", [f"flow[{target_key}]"],
                value=self._flow[target_key],
                before=before,
                after=self._flow[target_key],
                deps=[f"edge:{src}->{dst}", f"cap[{target_key}]"],
                role="answer",
                state_override=self._state(path=nodes),
                reason=reason or f"沿 {src}->{dst} 增广 {amount}",
            )

    def flow_value(self) -> int:
        if self.source is None:
            return sum(max(0, value) for value in self._flow.values())
        prefix = f"{self.source}->"
        return sum(value for edge, value in self._flow.items() if edge.startswith(prefix))


class IntervalObj:
    """List of [start, end] intervals with small visual hooks."""

    def __init__(self, session: TraceSession, name: str, intervals: list[list[Any]]) -> None:
        self._session = session
        self.name = name
        self._intervals = [list(item) for item in intervals]

    def __len__(self) -> int:
        return len(self._intervals)

    def __getitem__(self, idx: int) -> list[Any]:
        return list(self._intervals[idx])

    def _snap(self) -> list[list[Any]]:
        return [list(item) for item in self._intervals]

    def sort(self, *, reason: str = "") -> None:
        before = self._snap()
        self._intervals.sort(key=lambda item: (item[0], item[1] if len(item) > 1 else item[0]))
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [self.name],
            before=before,
            after=self._snap(),
            reason=reason or f"按起点排序区间 {self.name}",
        )

    def append(self, interval: list[Any] | tuple[Any, Any], *, reason: str = "") -> None:
        idx = len(self._intervals)
        row = list(interval)
        self._intervals.append(row)
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"{self.name}[{idx}]"],
            value=row,
            before=None,
            after=row,
            reason=reason or f"{self.name}.append({row})",
        )

    def set(self, idx: int, interval: list[Any] | tuple[Any, Any], *, reason: str = "") -> None:
        before = list(self._intervals[idx])
        row = list(interval)
        self._intervals[idx] = row
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"{self.name}[{idx}]"],
            value=row,
            before=before,
            after=row,
            reason=reason or f"{self.name}[{idx}] = {row}",
        )

    def overlaps(self, i: int, j: int, *, reason: str = "") -> bool:
        a, b = self._intervals[i], self._intervals[j]
        result = not (a[1] < b[0] or b[1] < a[0])
        self._session._emit(
            "compare", [f"{self.name}[{i}]", f"{self.name}[{j}]"],
            value={"overlap": result},
            reason=reason or f"判断区间 {a} 与 {b} 是否重叠",
        )
        return result

    def highlight(self, idx: int, role: str = "current", reason: str = "") -> None:
        self._session._emit("mark", [f"{self.name}[{idx}]"], role=role,
                            reason=reason or f"高亮区间 {self.name}[{idx}]")

    def to_list(self) -> list[list[Any]]:
        return self._snap()


def _flow_path_pairs(path: list[Any] | list[tuple[Any, Any]]) -> list[tuple[str, str]]:
    if not path:
        return []
    if all(isinstance(item, (list, tuple)) and len(item) >= 2 for item in path):
        return [(str(item[0]), str(item[1])) for item in path]  # type: ignore[index]
    nodes = [str(item) for item in path]
    return [(u, v) for u, v in zip(nodes, nodes[1:])]
