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


class TraceSession:
    """The single object the algorithm code interacts with.

    Holds the running event log and the current snapshot of every named object.
    Each high-level object (Array, String, Table, Pointer, ...) calls back into
    `_emit_*` to record an event without the algorithm code ever touching a
    target id string.
    """

    def __init__(
        self,
        algorithm: str,
        input_data: Any,
        *,
        max_events: int | None = None,
        pseudocode: list[str] | None = None,
    ) -> None:
        self.algorithm = algorithm
        self.input_data = deepcopy(input_data)
        self.max_events = max_events
        self.pseudocode = list(pseudocode or [])
        self._events: list[dict[str, Any]] = []
        self._snapshot: dict[str, Any] = {}
        self._objects: dict[str, Any] = {}
        self._result: Any = None

    # ----- factory methods --------------------------------------------------

    def array(self, name: str, values: list[Any]) -> "ArrayObj":
        obj = ArrayObj(self, name, list(values))
        self._register(name, obj, deepcopy(list(values)))
        self._emit("create", [name], state_override={name: list(values)},
                   reason=f"创建数组 {name}")
        return obj

    def string(self, name: str, text: str) -> "StringObj":
        obj = StringObj(self, name, str(text))
        self._register(name, obj, str(text))
        self._emit("create", [name], state_override={name: str(text)},
                   reason=f"创建字符串 {name}")
        return obj

    def table(self, name: str, rows: list[list[Any]]) -> "TableObj":
        obj = TableObj(self, name, [list(r) for r in rows])
        self._register(name, obj, deepcopy(rows))
        self._emit("create", [name], state_override={name: deepcopy(rows)},
                   reason=f"创建二维表 {name}")
        return obj

    def scalar(self, name: str, value: Any) -> "ScalarObj":
        obj = ScalarObj(self, name, value)
        self._register(name, obj, deepcopy(value))
        self._emit("create", [name], state_override={name: deepcopy(value)},
                   reason=f"创建变量 {name}")
        return obj

    def pointer(self, name: str, on: "ArrayObj | StringObj", idx: int,
                role: str = "current") -> "PointerObj":
        obj = PointerObj(self, name, on, idx, role)
        self._register(name, obj, idx)
        self._emit("create", [name], state_override={name: idx}, role=role,
                   reason=f"创建指针 {name} -> {on.name}[{idx}]")
        return obj

    def graph(self, name: str, nodes: list[Any], edges: list[tuple],
              directed: bool = False) -> "GraphObj":
        obj = GraphObj(self, name, nodes, edges, directed)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._emit("create", [name], state_override={name: snap},
                   reason=f"创建图 {name}")
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

    def trie(self, name: str = "trie") -> "TrieObj":
        obj = TrieObj(self, name)
        snap = obj._snap()
        self._register(name, obj, snap)
        self._emit("create", [name], state_override={name: snap},
                   reason=f"创建 Trie {name}")
        return obj

    def points(self, name: str, points: list[tuple]) -> "PointsObj":
        obj = PointsObj(self, name, points)
        self._register(name, obj, [list(p) for p in points])
        self._emit("create", [name], state_override={name: [list(p) for p in points]},
                   reason=f"创建点集 {name} ({len(points)} 个点)")
        return obj

    # ----- narration --------------------------------------------------------

    @contextmanager
    def step(self, label: str) -> Iterator[None]:
        """Phase boundary; emits enter/exit and groups events."""
        self._emit("enter", [f"phase:{label}"], reason=label)
        try:
            yield
        finally:
            self._emit("exit", [f"phase:{label}"], reason=label)

    def note(self, text: str, *, target: str | None = None) -> None:
        self._emit("explain", [target] if target else [], reason=text)

    # ----- termination ------------------------------------------------------

    def result(self, value: Any) -> None:
        self._result = deepcopy(value)

    def to_trace(self) -> dict[str, Any]:
        events = self._events
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

    # ----- internal: emit helpers ------------------------------------------

    def _register(self, name: str, obj: Any, init_value: Any) -> None:
        if name in self._objects:
            raise ValueError(f"对象名重复：{name}")
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
        self._events.append({
            "step": len(self._events),
            "op": op,
            "targets": [{"id": t} for t in targets],
            "value": deepcopy(value),
            "before": deepcopy(before),
            "after": deepcopy(after),
            "deps": [{"id": d} for d in (deps or [])],
            "role": role or "",
            "reason": reason or "",
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

    def to_list(self) -> list[Any]:
        return list(self._values)

    def max(self) -> Any:
        return max(self._values) if self._values else None


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

    def unhighlight(self, idx: int) -> None:
        self._session._emit("unmark", [f"{self.name}[{idx}]"])

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


class ScalarObj:
    def __init__(self, session: TraceSession, name: str, value: Any) -> None:
        self._session = session
        self.name = name
        self._value = value

    @property
    def value(self) -> Any:
        return self._value

    def set(self, value: Any, *, reason: str = "") -> None:
        before = self._value
        self._value = value
        self._session._update_snapshot(self.name, value)
        self._session._emit(
            "set", [self.name], value=value, before=before, after=value,
            reason=reason or f"{self.name} = {value}",
        )


class PointerObj:
    def __init__(self, session: TraceSession, name: str,
                 on: "ArrayObj | StringObj", idx: int, role: str = "current") -> None:
        self._session = session
        self.name = name
        self._on = on
        self._idx = idx
        self._role = role

    @property
    def idx(self) -> int:
        return self._idx

    def move(self, new_idx: int, *, reason: str = "") -> None:
        before = self._idx
        self._idx = new_idx
        self._session._update_snapshot(self.name, new_idx)
        self._session._emit(
            "move", [self.name],
            value={"on": self._on.name, "idx": new_idx},
            before=before, after=new_idx,
            role=self._role,
            reason=reason or f"{self.name} 移动到 {self._on.name}[{new_idx}]",
        )

    def deref(self) -> Any:
        return self._on[self._idx]


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


class TreeObj:
    """Recursion-call frame stack."""

    def __init__(self, session: TraceSession, name: str) -> None:
        self._session = session
        self.name = name
        self._stack: list[str] = []

    @contextmanager
    def frame(self, label: str, *, reason: str = "") -> Iterator[None]:
        self._stack.append(label)
        self._session._update_snapshot(self.name, list(self._stack))
        self._session._emit(
            "enter", [f"frame:{label}"],
            reason=reason or f"进入 {label}",
        )
        try:
            yield
        finally:
            self._stack.pop()
            self._session._update_snapshot(self.name, list(self._stack))
            self._session._emit(
                "exit", [f"frame:{label}"],
                reason=f"退出 {label}",
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

    def peek(self) -> Any:
        return self._items[-1] if self._items else None

    def empty(self) -> bool:
        return not self._items


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

    def empty(self) -> bool:
        return len(self._items) == 0


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
            "set", [f"{self.name}[{x}]"], value={"root": root},
            reason=reason or f"find({x}) -> {root}",
        )
        return root

    def union(self, x: int, y: int, *, reason: str = "") -> bool:
        rx = self._find_silent(x)
        ry = self._find_silent(y)
        if rx == ry:
            self._session._emit(
                "compare", [f"{self.name}[{x}]", f"{self.name}[{y}]"],
                value={"same_root": True, "root": rx},
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
            "link", [f"{self.name}[{ry}]"], value={"new_root": rx, "merged": [x, y]},
            reason=reason or f"union({x},{y}) 合并为 root={rx}",
        )
        return True

    def _find_silent(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x


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

    def insert_after(self, node_id: int, value: Any, *, reason: str = "") -> int:
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
        target = next(n for n in self._nodes if n["id"] == node_id)
        target["next"] = new_next
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"node:{node_id}"], value={"next": new_next},
            reason=reason or f"节点 {node_id}.next = {new_next}",
        )

    def set_head(self, node_id: Any, *, reason: str = "") -> None:
        before = self._head
        self._head = node_id
        self._session._update_snapshot(self.name, self._snap())
        self._session._emit(
            "set", [f"{self.name}.head"], value=node_id, before=before, after=node_id,
            reason=reason or f"head -> {node_id}",
        )

    def highlight(self, node_id: int, role: str = "current", reason: str = "") -> None:
        self._session._emit("mark", [f"node:{node_id}"], role=role,
                            reason=reason or f"高亮节点 {node_id}")


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
