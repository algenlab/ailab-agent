"""PoC 1: Manacher palindrome.

The hardest string algorithm in the benchmark — center/right maintenance,
character symmetry, and per-position expansion. Notoriously bug-prone in
trace JSON form because the contract between p[], center, right, and the
expanded string is intricate.

LLM responsibility (this file): write the algorithm naturally with the DSL.
DSL responsibility: emit a SemanticTrace JSON that is schema-compatible.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from poc_tracer.dsl import TraceSession  # noqa: E402


def solve(input_data: dict) -> str:
    """Reference implementation (pure Python, no DSL)."""
    s = input_data["s"]
    t_text = "#" + "#".join(s) + "#"
    n = len(t_text)
    p = [0] * n
    center = 0
    right = 0
    best = 0
    for i in range(n):
        if i < right:
            p[i] = min(right - i, p[2 * center - i])
        while (i - p[i] - 1 >= 0 and i + p[i] + 1 < n
               and t_text[i - p[i] - 1] == t_text[i + p[i] + 1]):
            p[i] += 1
        if i + p[i] > right:
            center = i
            right = i + p[i]
        if p[i] > p[best]:
            best = i
    radius = p[best]
    start = (best - radius) // 2
    return s[start:start + radius]


def trace(input_data: dict) -> dict:
    """Same algorithm, instrumented via the DSL.

    Notice this reads exactly like normal Python — no target ids, no schema
    juggling, no manual deepcopy of state.
    """
    s = input_data["s"]
    t_text = "#" + "#".join(s) + "#"
    n = len(t_text)

    sess = TraceSession(
        algorithm="Manacher 回文",
        input_data=input_data,
        max_events=80,
        pseudocode=[
            "构造 t = #...# 把奇偶情况统一",
            "对每个 i：先用对称点初始化 p[i]",
            "再两侧暴力扩展",
            "若超出右边界则更新 center/right",
            "答案 = max(p[i]) 对应的子串",
        ],
    )

    t_obj = sess.string("t", t_text)
    p_obj = sess.array("p", [0] * n)
    center = sess.scalar("center", 0)
    right = sess.scalar("right", 0)

    best = 0
    for i in range(n):
        with sess.step(f"i={i}  t[i]='{t_text[i]}'"):
            if i < right.value:
                mirror = 2 * center.value - i
                init_val = min(right.value - i, p_obj[mirror])
                if init_val > 0:
                    sess.note(
                        f"对称初始化：mirror={mirror}, p[{i}] = min(right-i={right.value - i}, p[mirror]={p_obj[mirror]}) = {init_val}"
                    )
                p_obj[i] = init_val
            else:
                if p_obj[i] != 0:
                    p_obj[i] = 0

            while (i - p_obj[i] - 1 >= 0 and i + p_obj[i] + 1 < n
                   and t_text[i - p_obj[i] - 1] == t_text[i + p_obj[i] + 1]):
                t_obj.compare(i - p_obj[i] - 1, i + p_obj[i] + 1,
                              reason="左右匹配，扩展")
                p_obj[i] = p_obj[i] + 1

            if i + p_obj[i] > right.value:
                center.set(i, reason=f"中心右移到 {i}")
                right.set(i + p_obj[i], reason=f"右边界扩展到 {i + p_obj[i]}")

            if p_obj[i] > p_obj[best]:
                best = i

    radius = p_obj[best]
    start = (best - radius) // 2
    answer = s[start:start + radius]
    sess.result(answer)
    return sess.to_trace()


if __name__ == "__main__":
    import json

    case = {"s": "babad"}
    expected = solve(case)
    raw_trace = trace(case)

    print(f"=== Manacher PoC ===")
    print(f"input: {case}")
    print(f"solve result: {expected!r}")
    print(f"trace result: {raw_trace['result']!r}")
    print(f"events: {len(raw_trace['events'])}")

    sys.path.insert(0, str(ROOT))
    from algolab.schemas.semantic_trace import SemanticTrace
    validated = SemanticTrace.model_validate(raw_trace)
    print(f"schema OK, algorithm={validated.algorithm}")

    print("\nFirst 5 events:")
    for ev in raw_trace["events"][:5]:
        print(f"  step={ev['step']:>2} op={ev['op']:<7} targets={[t['id'] for t in ev['targets']]} reason={ev['reason'][:60]}")

    print("\nLast 3 events:")
    for ev in raw_trace["events"][-3:]:
        print(f"  step={ev['step']:>2} op={ev['op']:<7} targets={[t['id'] for t in ev['targets']]} reason={ev['reason'][:60]}")

    out_path = Path(__file__).parent / "manacher_trace.json"
    out_path.write_text(json.dumps(raw_trace, ensure_ascii=False, indent=2))
    print(f"\nfull trace written to: {out_path}")
