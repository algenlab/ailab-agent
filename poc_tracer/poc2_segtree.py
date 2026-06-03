"""PoC 2: Segment tree (range-sum).

Tests the hardest range-structure operation: a tree visualized as both
a tree and an array, with deep recursion that needs to be readable as
a call stack. In the current system this is the family with the most
hand-written validators in process_families/tree_range_math.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from poc_tracer.dsl import TraceSession  # noqa: E402


def solve(input_data: dict) -> int:
    nums = list(input_data["nums"])
    queries = input_data["queries"]
    n = len(nums)
    tree = [0] * (4 * n)

    def build(node: int, l: int, r: int) -> None:
        if l == r:
            tree[node] = nums[l]
            return
        mid = (l + r) // 2
        build(2 * node, l, mid)
        build(2 * node + 1, mid + 1, r)
        tree[node] = tree[2 * node] + tree[2 * node + 1]

    def query(node: int, l: int, r: int, ql: int, qr: int) -> int:
        if qr < l or r < ql:
            return 0
        if ql <= l and r <= qr:
            return tree[node]
        mid = (l + r) // 2
        return (query(2 * node, l, mid, ql, qr)
                + query(2 * node + 1, mid + 1, r, ql, qr))

    build(1, 0, n - 1)
    results = [query(1, 0, n - 1, q[0], q[1]) for q in queries]
    return sum(results)


def trace(input_data: dict) -> dict:
    nums_list = list(input_data["nums"])
    queries = input_data["queries"]
    n = len(nums_list)

    sess = TraceSession(
        algorithm="线段树 区间求和",
        input_data=input_data,
        max_events=80,
        pseudocode=[
            "建树 build(node, l, r)：叶子写值，内部 = 左子+右子",
            "查询 query(node, l, r, ql, qr)：",
            "  - 完全包含返回该节点和",
            "  - 完全不交返回 0",
            "  - 否则递归左右子",
        ],
    )

    nums = sess.array("nums", nums_list)
    tree = sess.array("tree", [0] * (4 * n))
    frames = sess.tree("call_stack")

    def build(node: int, l: int, r: int) -> None:
        with frames.frame(f"build(node={node}, [{l},{r}])"):
            if l == r:
                tree[node] = nums[l]
                return
            mid = (l + r) // 2
            build(2 * node, l, mid)
            build(2 * node + 1, mid + 1, r)
            tree[node] = tree[2 * node] + tree[2 * node + 1]

    def query(node: int, l: int, r: int, ql: int, qr: int) -> int:
        with frames.frame(f"query(node={node}, [{l},{r}], target=[{ql},{qr}])"):
            if qr < l or r < ql:
                sess.note(f"区间 [{l},{r}] 与 [{ql},{qr}] 不相交，返回 0")
                return 0
            if ql <= l and r <= qr:
                sess.note(f"区间 [{l},{r}] 完全在 [{ql},{qr}] 内，直接取 tree[{node}]={tree[node]}")
                return tree[node]
            mid = (l + r) // 2
            left = query(2 * node, l, mid, ql, qr)
            right = query(2 * node + 1, mid + 1, r, ql, qr)
            return left + right

    with sess.step("阶段 1：建树"):
        build(1, 0, n - 1)

    total = 0
    for qi, q in enumerate(queries):
        with sess.step(f"阶段 2.{qi}：查询 [{q[0]},{q[1]}]"):
            total += query(1, 0, n - 1, q[0], q[1])

    sess.result(total)
    return sess.to_trace()


if __name__ == "__main__":
    import json

    case = {"nums": [1, 3, 5, 7, 9, 11], "queries": [[1, 3], [0, 5]]}
    expected = solve(case)
    raw_trace = trace(case)

    print(f"=== Segment Tree PoC ===")
    print(f"input: nums={case['nums']}, queries={case['queries']}")
    print(f"solve result: {expected}")
    print(f"trace result: {raw_trace['result']}")
    print(f"events: {len(raw_trace['events'])}")

    from algolab.schemas.semantic_trace import SemanticTrace
    validated = SemanticTrace.model_validate(raw_trace)
    print(f"schema OK, algorithm={validated.algorithm}")

    print("\nSample events:")
    for ev in raw_trace["events"][:6]:
        print(f"  step={ev['step']:>2} op={ev['op']:<7} targets={[t['id'] for t in ev['targets']]} reason={ev['reason'][:55]}")
    print("  ...")
    for ev in raw_trace["events"][-4:]:
        print(f"  step={ev['step']:>2} op={ev['op']:<7} targets={[t['id'] for t in ev['targets']]} reason={ev['reason'][:55]}")

    out_path = Path(__file__).parent / "segtree_trace.json"
    out_path.write_text(json.dumps(raw_trace, ensure_ascii=False, indent=2))
    print(f"\nfull trace: {out_path}")
