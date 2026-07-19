"""Lightweight compatibility entry point for current regression checks.

Historically this module aggregated every benchmark-era regression.  The active
project direction now keeps daily checks focused on the teaching/interaction
contract and leaves large benchmark sweeps to explicit experiment scripts.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from tests.regression import teaching_enricher


def _teaching_tests() -> Iterator[tuple[str, Callable[[], None]]]:
    for name in sorted(dir(teaching_enricher)):
        if not name.startswith("test_"):
            continue
        candidate = getattr(teaching_enricher, name)
        if callable(candidate):
            yield name, candidate


def run_all() -> None:
    for _name, test in _teaching_tests():
        test()


if __name__ == "__main__":
    run_all()
    print("benchmark_regression: PASS")
