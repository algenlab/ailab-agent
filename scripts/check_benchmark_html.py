"""Run browser smoke checks for an existing LLM benchmark output directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_llm_benchmark import browser_smoke_html_paths


def html_paths_from_report(report_path: Path) -> list[Path]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    paths: list[Path] = []
    for item in report.get("results") or []:
        if item.get("ok") and item.get("html"):
            paths.append(Path(item["html"]))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="检查已有 benchmark HTML，不调用 LLM")
    parser.add_argument("output_dir", type=Path, help="包含 llm_benchmark_report.json 的输出目录")
    parser.add_argument("--require-count", type=int, default=0, help="要求检查到的 HTML 数量")
    args = parser.parse_args()

    report_path = args.output_dir / "llm_benchmark_report.json"
    if not report_path.exists():
        raise SystemExit(f"找不到报告文件：{report_path}")

    html_paths = html_paths_from_report(report_path)
    if args.require_count and len(html_paths) != args.require_count:
        raise SystemExit(f"HTML 数量不匹配：期望 {args.require_count}，实际 {len(html_paths)}")

    checks = browser_smoke_html_paths(html_paths)
    passed = sum(1 for item in checks if item.get("ok"))
    for item in checks:
        status = "PASS" if item.get("ok") else "FAIL"
        print(f"{status} {item.get('html')} counter={item.get('counter', '')} canvas_chars={item.get('canvas_chars', 0)}")
        if item.get("errors"):
            print("; ".join(item["errors"]))
    print(f"benchmark_html_smoke: {passed}/{len(checks)} PASS")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
