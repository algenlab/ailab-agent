"""Build a deterministic V1 release gate evidence report.

The release gate does not call the LLM. It records the concrete commands and
static evidence that the V1 release criteria depend on, then the full
``scripts/run_quality_checks.py`` command verifies the executable/browser parts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_evaluation_manifest import build_manifest
from scripts.build_evaluation_report import build_evaluation_report
from tests.benchmark_cases import benchmark_cases


PYTHON = "/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
BROWSER_SMOKE_CONTAINER = "bash scripts/run_browser_smoke_container.sh"
CONTAINER_QUALITY_CHECKS = f"{BROWSER_SMOKE_CONTAINER} python scripts/run_quality_checks.py"
MIN_V1_SAMPLES = 80
MAX_V1_SAMPLES = 230
V1_GATE_LAYERS = {"smoke", "family_core"}
GOLDEN_BROWSER_CASES = ("unique_paths", "graph_bfs", "binary_search", "daily_temperatures")
DEBUG_DRAWER_SELECTORS = (
    "#debug-validation-json",
    "#debug-release",
    "#debug-state",
    "#debug-artifact",
)
DOCS_TO_CHECK = (
    "README.md",
    "SYSTEM_OVERVIEW.md",
    "docs/03_AI_CODING_GUIDE.md",
    "docs/06_EVALUATION_AND_BENCHMARK.md",
    "docs/07_ROADMAP_AND_TASKS.md",
    "benchmark/README.md",
)


def build_v1_release_gate_report() -> dict[str, Any]:
    manifest = build_manifest()
    benchmark = benchmark_cases()
    benchmark_sample_count = sum(len(case.samples) for case in benchmark)
    v1_gate_sample_count = sum(len(case.samples) for case in benchmark if case.gate_layer in V1_GATE_LAYERS)
    checks = {
        "deterministic_benchmark": deterministic_benchmark_check(
            manifest,
            benchmark_sample_count=benchmark_sample_count,
            v1_gate_sample_count=v1_gate_sample_count,
        ),
        "golden_browser_smoke": golden_browser_smoke_check(),
        "debug_drawer_evidence": debug_drawer_check(),
        "evaluation_failure_types": evaluation_failure_types_check(),
        "pinned_python_docs": pinned_python_docs_check(),
    }
    return {
        "schema_version": "v1-release-gate-v1",
        "description": "Deterministic evidence bundle for the AlgoLab V1 release gate.",
        "overall_ready": all(item["status"] == "pass" for item in checks.values()),
        "commands": {
            "quality_checks": CONTAINER_QUALITY_CHECKS,
            "browser_smoke": BROWSER_SMOKE_CONTAINER,
            "release_gate_report": f"{PYTHON} scripts/check_v1_release_gate.py --output-dir output/release_gate",
            "evaluation_manifest": f"{PYTHON} scripts/build_evaluation_manifest.py --output-dir output/evaluation",
            "evaluation_report": (
                f"{PYTHON} scripts/build_evaluation_report.py "
                "--output-dir output/evaluation "
                "--manifest output/evaluation/evaluation_manifest.json "
                "--dashboard output/dashboard/dashboard.json"
            ),
        },
        "checks": checks,
    }


def deterministic_benchmark_check(
    manifest: dict[str, Any],
    *,
    benchmark_sample_count: int,
    v1_gate_sample_count: int,
) -> dict[str, Any]:
    in_range = MIN_V1_SAMPLES <= v1_gate_sample_count <= MAX_V1_SAMPLES
    manifest_matches = manifest["summary"]["benchmark_case_count"] == len(benchmark_cases())
    return {
        "status": "pass" if in_range and manifest_matches else "fail",
        "benchmark_case_count": len(benchmark_cases()),
        "benchmark_sample_count": benchmark_sample_count,
        "v1_gate_layers": sorted(V1_GATE_LAYERS),
        "v1_gate_sample_count": v1_gate_sample_count,
        "required_sample_range": [MIN_V1_SAMPLES, MAX_V1_SAMPLES],
        "manifest_sample_count": manifest["summary"]["sample_count"],
        "covered_by": "scripts/run_quality_checks.py -> tests.benchmark_regression.run_all",
    }


def golden_browser_smoke_check() -> dict[str, Any]:
    return {
        "status": "pass",
        "required_cases": list(GOLDEN_BROWSER_CASES),
        "covered_by": "scripts/run_browser_smoke_container.sh -> tests.browser_smoke.run_all",
        "assertions": [
            "HTML loads without JavaScript errors.",
            "Golden pages have non-empty canvas content.",
            "Phase 8 screenshot regression checks required demo pages.",
        ],
    }


def debug_drawer_check() -> dict[str, Any]:
    return {
        "status": "pass",
        "required_selectors": list(DEBUG_DRAWER_SELECTORS),
        "covered_by": "tests.browser_smoke._check_page",
        "evidence": [
            "Debug Drawer exists and is collapsed by default.",
            "raw validation JSON includes checks and release_gate.",
            "release gate, raw state, and artifact JSON are visible after expanding.",
        ],
    }


def evaluation_failure_types_check() -> dict[str, Any]:
    synthetic_report = {
        "kind": "llm_benchmark_report",
        "config": {"benchmark_condition": "algolab_full"},
        "results": [
            {
                "case_id": "graph_bfs",
                "family": "BFS/DFS 基础图",
                "ok": False,
                "failure_type": "process_invariant",
            },
            {
                "case_id": "unique_paths",
                "family": "DP 基础",
                "ok": False,
                "errors": ["scene compiler disabled caused scene validator failure"],
            },
        ],
    }
    with tempfile.TemporaryDirectory() as directory:
        output_dir = Path(directory)
        manifest_path = output_dir / "evaluation_manifest.json"
        llm_path = output_dir / "llm_benchmark_report.json"
        manifest_path.write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
        llm_path.write_text(json.dumps(synthetic_report, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path = build_evaluation_report(output_dir=output_dir, manifest_path=manifest_path, llm_report_path=llm_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("failure_type_summary", {})
    expected = {"process_invariant": 1, "scene_error": 1}
    return {
        "status": "pass" if summary == expected else "fail",
        "synthetic_failure_type_summary": summary,
        "output_paths": [
            "output/evaluation/evaluation_failure_types.csv",
            "output/evaluation/evaluation_condition_summary.csv",
            "output/evaluation/evaluation_report.json",
        ],
        "covered_by": "scripts/build_evaluation_report.py",
    }


def pinned_python_docs_check() -> dict[str, Any]:
    disallowed: list[str] = []
    checked: list[str] = []
    pattern = re.compile(r"(?<![\w/.-])(python3|python)(?![\w/.-])")
    for relative in DOCS_TO_CHECK:
        path = ROOT / relative
        if not path.exists():
            continue
        checked.append(relative)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip().startswith("```"):
                continue
            if PYTHON in line:
                continue
            if "scripts/run_browser_smoke_container.sh python" in line:
                continue
            if pattern.search(line):
                disallowed.append(f"{relative}:{line_number}:{line.strip()}")
    return {
        "status": "pass" if not disallowed else "fail",
        "python": PYTHON,
        "checked_files": checked,
        "disallowed_commands": disallowed,
    }


def write_v1_release_gate_report(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_v1_release_gate_report()
    json_path = output_dir / "v1_release_gate.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "v1_release_gate.md").write_text(render_markdown(report), encoding="utf-8")
    return json_path


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# V1 Release Gate",
        "",
        f"- Overall ready: `{report['overall_ready']}`",
        f"- Quality command: `{report['commands']['quality_checks']}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "|---|---|---|",
    ]
    for name, check in report["checks"].items():
        evidence = check.get("covered_by") or ", ".join(check.get("output_paths", [])) or ""
        lines.append(f"| {name} | {check['status']} | {evidence} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 AlgoLab V1 发布门禁证据报告")
    parser.add_argument("--output-dir", type=Path, default=Path("output/release_gate"), help="输出目录")
    args = parser.parse_args()
    path = write_v1_release_gate_report(args.output_dir)
    report = json.loads(path.read_text(encoding="utf-8"))
    print(path)
    return 0 if report.get("overall_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
