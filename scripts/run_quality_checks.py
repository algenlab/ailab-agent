"""Run all local quality checks."""

from __future__ import annotations

import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def compile_all():
    files = [*Path("algolab").rglob("*.py"), Path("cli.py"), Path("app.py")]
    for file in files:
        py_compile.compile(str(file), doraise=True)


def main():
    compile_all()
    from tests.offline_regression import run_all as run_offline
    from tests.benchmark_regression import run_all as run_benchmark
    from tests.browser_smoke import run_all as run_browser

    run_offline()
    run_benchmark()
    run_browser()
    print("quality_checks: PASS")


if __name__ == "__main__":
    main()
