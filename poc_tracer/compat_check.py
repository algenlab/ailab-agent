"""Compatibility check: feed PoC traces to the real executor pipeline checks.

Runs three guards on each PoC trace:
1) SemanticTrace.model_validate (schema)
2) executor._validate_trace_budget (per-event state size)
3) canonical(solve) == canonical(trace.result) (correctness gate)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algolab.runtime.executor import canonical, _validate_trace_budget  # noqa: E402
from algolab.schemas.semantic_trace import SemanticTrace  # noqa: E402

import poc1_manacher  # noqa: E402
import poc2_segtree  # noqa: E402
import poc3_edmonds_karp  # noqa: E402


CASES = [
    ("Manacher", poc1_manacher, {"s": "babad"}),
    ("Manacher-long", poc1_manacher, {"s": "abacdfgdcabba"}),
    ("Segtree", poc2_segtree, {"nums": [1, 3, 5, 7, 9, 11], "queries": [[1, 3], [0, 5]]}),
    ("Edmonds-Karp", poc3_edmonds_karp, {
        "nodes": ["s", "a", "b", "t"],
        "edges": [["s", "a", 3], ["s", "b", 2], ["a", "t", 2], ["a", "b", 1], ["b", "t", 3]],
        "source": "s", "sink": "t",
    }),
]


def check_one(name, mod, case):
    print(f"\n[{name}]")
    solve_result = mod.solve(case)
    raw = mod.trace(case)

    try:
        SemanticTrace.model_validate(raw)
        print(f"  schema           : OK")
    except Exception as e:
        print(f"  schema           : FAIL  {e}")
        return False

    try:
        _validate_trace_budget(raw)
        print(f"  trace budget     : OK   (events={len(raw['events'])})")
    except Exception as e:
        print(f"  trace budget     : FAIL  {e}")
        return False

    if canonical(case) != canonical(raw["input_data"]):
        print(f"  input_data match : FAIL")
        return False
    print(f"  input_data match : OK")

    if canonical(solve_result) != canonical(raw["result"]):
        print(f"  result match     : FAIL  solve={solve_result!r} trace={raw['result']!r}")
        return False
    print(f"  result match     : OK   ({solve_result!r})")
    return True


def main():
    print("=" * 60)
    print("Compatibility check vs algolab.runtime.executor")
    print("=" * 60)
    passed = 0
    for name, mod, case in CASES:
        if check_one(name, mod, case):
            passed += 1
    print(f"\n{'=' * 60}")
    print(f"PASSED {passed}/{len(CASES)}")
    print("=" * 60)
    return passed == len(CASES)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    sys.exit(0 if main() else 1)
