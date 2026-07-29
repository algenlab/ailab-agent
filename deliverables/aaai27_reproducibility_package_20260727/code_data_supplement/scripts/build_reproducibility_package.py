"""Build the AlgoLab reproducibility package manifest.

The package is deterministic: it records commands, dataset inputs, output
locations, and LLM configuration knobs without calling the LLM or reading
secrets. It is intended as the handoff artifact for rerunning local quality
checks and separating deterministic benchmark evidence from live LLM runs.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_evaluation_manifest import build_manifest


PYTHON = "python3"
QUALITY_CHECKS = f"{PYTHON} scripts/run_quality_checks.py"
BROWSER_SMOKE_CONTAINER = "bash scripts/run_browser_smoke_container.sh"


def build_reproducibility_package() -> dict[str, Any]:
    manifest = build_manifest()
    return {
        "schema_version": "reproducibility-package-v1",
        "description": "AlgoLab deterministic and LLM benchmark reproducibility package.",
        "environment": environment_block(),
        "model_config": model_config_block(),
        "commands": command_block(),
        "benchmark_modes": benchmark_modes_block(),
        "output_paths": output_paths_block(),
        "sample_inputs": sample_inputs(manifest),
    }


def environment_block() -> dict[str, Any]:
    return {
        "python": PYTHON,
        "project_root": str(ROOT),
        "platform": platform.platform(),
        "quality_check_entrypoint": "scripts/run_quality_checks.py",
        "browser_smoke_entrypoint": "scripts/run_browser_smoke_container.sh",
        "notes": [
            "Run commands from the project root.",
            "Use the pinned Python interpreter shown here for every Python command.",
            "Run lightweight local quality checks on the host; use the Playwright container only for explicit browser evidence.",
            "Deterministic checks do not require network or LLM credentials.",
        ],
    }


def model_config_block() -> dict[str, Any]:
    return {
        "secret_policy": "Do not commit API keys. Configure live LLM runs via environment variables or ignored local settings files.",
        "env_vars": [
            "ALGOLAB_LLM_BASE_URL",
            "ALGOLAB_LLM_API_KEY",
            "ALGOLAB_LLM_MODEL",
            "ALGOLAB_LLM_TIMEOUT_S",
            "ALGOLAB_LLM_MAX_TOKENS",
            "ALGOLAB_LLM_JSON_RETRIES",
            "ALGOLAB_LLM_SETTINGS_FILE",
        ],
        "local_settings_files": [
            "api_settings.json",
            "api_settings.yaml",
            "api_settings.yml",
            ".algolab_api_settings.json",
            ".algolab_api_settings.yaml",
            ".algolab_api_settings.yml",
        ],
        "deterministic_mode": {
            "requires_llm": False,
            "model_config_recorded_as": "not_applicable",
        },
        "llm_mode": {
            "requires_llm": True,
            "model_config_recorded_in": "output/llm_benchmark/llm_benchmark_report.json",
        },
    }


def command_block() -> dict[str, str]:
    return {
        "deterministic_quality_check": QUALITY_CHECKS,
        "browser_smoke_container": BROWSER_SMOKE_CONTAINER,
        "host_current_regression": f"{PYTHON} -m tests.benchmark_regression",
        "build_evaluation_manifest": f"{PYTHON} scripts/build_evaluation_manifest.py --output-dir output/evaluation",
        "build_demo_dashboard": f"{PYTHON} scripts/build_demo_dashboard.py --output-dir output/dashboard --style both",
        "build_evaluation_report_deterministic": (
            f"{PYTHON} scripts/build_evaluation_report.py "
            "--output-dir output/evaluation "
            "--manifest output/evaluation/evaluation_manifest.json "
            "--dashboard output/dashboard/dashboard.json"
        ),
        "llm_benchmark": (
            f"{PYTHON} scripts/run_llm_benchmark.py "
            "--output-dir output/llm_benchmark --condition algolab_full"
        ),
        "llm_benchmark_with_browser_smoke": (
            f"{PYTHON} scripts/run_llm_benchmark.py "
            "--output-dir output/llm_benchmark --condition algolab_full --browser-smoke"
        ),
        "build_evaluation_report_with_llm": (
            f"{PYTHON} scripts/build_evaluation_report.py "
            "--output-dir output/evaluation "
            "--manifest output/evaluation/evaluation_manifest.json "
            "--dashboard output/dashboard/dashboard.json "
            "--llm-report output/llm_benchmark/llm_benchmark_report.json"
        ),
    }


def benchmark_modes_block() -> dict[str, Any]:
    commands = command_block()
    return {
        "deterministic": {
            "calls_llm": False,
            "source": "benchmark/cases.py",
            "entrypoints": [
                "scripts/run_quality_checks.py",
                "scripts/build_evaluation_manifest.py",
                "scripts/build_demo_dashboard.py",
                "scripts/build_evaluation_report.py",
            ],
            "quality_command": commands["deterministic_quality_check"],
            "output_paths": [
                "output/dashboard/dashboard.json",
                "output/dashboard/index.html",
                "output/evaluation/evaluation_manifest.json",
                "output/evaluation/evaluation_report.json",
            ],
        },
        "llm": {
            "calls_llm": True,
            "source": "scripts/run_llm_benchmark.py",
            "entrypoints": [
                "scripts/run_llm_benchmark.py",
                "scripts/check_benchmark_html.py",
                "scripts/build_evaluation_report.py",
            ],
            "quality_command": commands["llm_benchmark"],
            "output_paths": [
                "output/llm_benchmark/llm_benchmark_report.json",
                "output/llm_benchmark/llm_benchmark_report.md",
                "output/llm_benchmark/llm_<case_id>_<sample_index>.json",
                "output/llm_benchmark/llm_<case_id>_<sample_index>.html",
            ],
        },
    }


def output_paths_block() -> dict[str, Any]:
    return {
        "dashboard": {
            "json": "output/dashboard/dashboard.json",
            "html": "output/dashboard/index.html",
            "demos": "output/dashboard/demos/<case_id>/",
        },
        "evaluation": {
            "manifest": "output/evaluation/evaluation_manifest.json",
            "report": "output/evaluation/evaluation_report.json",
            "case_csv": "output/evaluation/evaluation_cases.csv",
            "sample_csv": "output/evaluation/evaluation_samples.csv",
            "condition_csv": "output/evaluation/evaluation_condition_summary.csv",
            "failure_type_csv": "output/evaluation/evaluation_failure_types.csv",
        },
        "llm_benchmark": {
            "report_json": "output/llm_benchmark/llm_benchmark_report.json",
            "report_md": "output/llm_benchmark/llm_benchmark_report.md",
            "case_artifacts": "output/llm_benchmark/llm_<case_id>_<sample_index>.json",
            "case_html": "output/llm_benchmark/llm_<case_id>_<sample_index>.html",
        },
    }


def sample_inputs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in manifest.get("cases", []):
        for sample in case.get("samples", []):
            paths = sample.get("artifact_paths") or {}
            rows.append(
                {
                    "case_id": case["id"],
                    "title": case["title"],
                    "family": case["family"],
                    "suite": case["suite"],
                    "sample_index": sample.get("index"),
                    "input_data": sample.get("input_data"),
                    "expected": sample.get("expected"),
                    "output_paths": {
                        "artifact_json": paths.get("json") or case.get("artifact_paths", {}).get("artifact_json", ""),
                        "html": paths.get("html") or case.get("artifact_paths", {}).get("html", ""),
                    },
                }
            )
    return rows


def write_reproducibility_package(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    package = build_reproducibility_package()
    json_path = output_dir / "reproducibility_package.json"
    json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "README.md").write_text(render_readme(package), encoding="utf-8")
    (output_dir / "commands.sh").write_text(render_commands(package), encoding="utf-8")
    return json_path


def render_readme(package: dict[str, Any]) -> str:
    commands = package["commands"]
    modes = package["benchmark_modes"]
    lines = [
        "# AlgoLab Reproducibility Package",
        "",
        "## 环境",
        "",
        f"- Python: `{package['environment']['python']}`",
        f"- Project root: `{package['environment']['project_root']}`",
        "- LLM secrets must stay in environment variables or ignored local settings files.",
        "",
        "## 确定性质量检查",
        "",
        "deterministic benchmark 不调用 LLM，固定使用 `benchmark/cases.py` 中的本地样例数据。",
        "",
        f"```bash\n{commands['deterministic_quality_check']}\n```",
        "",
        "## LLM benchmark",
        "",
        "LLM benchmark 调用模型并把模型配置、repair 轮次、失败分类写入 report；它与 deterministic benchmark 分开运行。",
        "",
        f"```bash\n{commands['llm_benchmark']}\n```",
        "",
        "## deterministic benchmark",
        "",
        f"- Source: `{modes['deterministic']['source']}`",
        f"- Calls LLM: `{modes['deterministic']['calls_llm']}`",
        "",
        "## 输出路径",
        "",
    ]
    for group, paths in package["output_paths"].items():
        lines.append(f"### {group}")
        for name, path in paths.items():
            lines.append(f"- {name}: `{path}`")
        lines.append("")
    lines.extend(
        [
            "## 样例输入",
            "",
            f"- Recorded samples: {len(package['sample_inputs'])}",
            "- Full structured list is in `reproducibility_package.json`.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_commands(package: dict[str, Any]) -> str:
    commands = package["commands"]
    ordered = [
        "deterministic_quality_check",
        "build_evaluation_manifest",
        "build_demo_dashboard",
        "build_evaluation_report_deterministic",
        "llm_benchmark",
        "build_evaluation_report_with_llm",
    ]
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Run from the AlgoLab project root.",
    ]
    for key in ordered:
        lines.extend(["", f"# {key}", commands[key]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 AlgoLab 可复现包 manifest")
    parser.add_argument("--output-dir", type=Path, default=Path("output/reproducibility"), help="输出目录")
    args = parser.parse_args()
    path = write_reproducibility_package(args.output_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
