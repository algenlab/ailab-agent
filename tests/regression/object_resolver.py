"""Regression tests for shared state object resolution."""

from __future__ import annotations

from algolab.compiler.object_resolver import known_target_ids, resolve_basic_state_objects


def test_shared_resolver_handles_basic_state_shapes():
    objects = resolve_basic_state_objects(
        {
            "st": [[5, 2, 7, 3, 6, 1], [2, 2, 3, 3, 1], [2, 2, 1]],
            "nums": [5, 2, 7],
            "words": ["ab", "c"],
            "seen": {"a": 1, "b": 2},
        }
    )

    ids = known_target_ids(objects)

    assert "st" in ids
    assert "st[2][1]" in ids
    assert "nums[2]" in ids
    assert "words[0][1]" in ids
    assert "seen[a]" in ids


def run_all() -> None:
    test_shared_resolver_handles_basic_state_shapes()


if __name__ == "__main__":
    run_all()
    print("object_resolver: PASS")
