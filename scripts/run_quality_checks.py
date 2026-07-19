"""Run lightweight local quality checks for the active AlgoLab pipeline."""

from __future__ import annotations

import py_compile
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def compile_all():
    files = [*Path("algolab").rglob("*.py"), *Path("scripts").glob("*.py"), Path("cli.py"), Path("app.py")]
    with tempfile.TemporaryDirectory() as directory:
        cache_dir = Path(directory)
        for index, file in enumerate(files):
            if not file.exists():
                continue
            pyc_path = cache_dir / f"{index}_{file.name}.pyc"
            py_compile.compile(str(file), cfile=str(pyc_path), doraise=True)


def main():
    compile_all()
    from tests.benchmark_regression import run_all as run_benchmark

    run_benchmark()
    print("quality_checks: PASS")


if __name__ == "__main__":
    main()
