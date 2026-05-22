"""AlgoLab CLI: generate an interactive algorithm visualization artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from algolab.pipeline import artifact_summary, build_artifact
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput


def _read_text(value: str | None, file_value: str | None, default: str) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return value or default


def _read_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成可交互算法可视化页面")
    parser.add_argument("--problem", help="题目描述")
    parser.add_argument("--problem-file", help="题目描述文件")
    parser.add_argument("--input", help="输入 JSON 字符串或 JSON 文件路径")
    parser.add_argument("--strategy", default="", help="可选：指定解法思路，例如动态规划")
    parser.add_argument("--code-file", default="", help="可选：用户代码文件")
    parser.add_argument("--expected", default="", help="可选：期望输出 JSON 字符串或文件")
    parser.add_argument("--solutions", type=int, default=2, help="希望生成的解法数量")
    parser.add_argument("--output", default="output/algolab.html", help="输出 HTML 路径")
    args = parser.parse_args()

    default_problem = (
        "LeetCode 198. 打家劫舍。给定一个非负整数数组 nums，"
        "每个元素表示一间房屋的金额，不能偷相邻房屋，返回能偷到的最大金额。"
    )
    problem = _read_text(args.problem, args.problem_file, default_problem)
    input_data = _read_json(args.input, {"nums": [2, 7, 9, 3, 1]})
    expected = _read_json(args.expected, None) if args.expected else None
    user_code = Path(args.code_file).read_text(encoding="utf-8") if args.code_file else ""

    request = ProblemInput(
        problem=problem,
        input_data=input_data,
        strategy_hint=args.strategy,
        user_code=user_code,
        expected_result=expected,
        solution_count=args.solutions,
    )
    artifact = build_artifact(request)
    out = save_html(artifact, args.output)
    print(artifact_summary(artifact))
    print(f"HTML：{out}")
    print(f"JSON：{out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
