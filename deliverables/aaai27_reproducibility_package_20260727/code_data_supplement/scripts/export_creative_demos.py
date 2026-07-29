"""Export a few creative-mode demo pages from verified artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.pipeline import _try_materialize
from algolab.renderer.creative import save_creative_html
from algolab.schemas.input import ProblemInput
from algolab.schemas.validation import BuildArtifact


def load_artifact(path: str | Path) -> BuildArtifact:
    return BuildArtifact.model_validate_json(Path(path).read_text(encoding="utf-8"))


def subset_sum_artifact() -> BuildArtifact:
    request = ProblemInput(
        problem=(
            "给你一个只包含正整数的非空数组 nums。请判断是否可以将这个数组分割成两个子集，"
            "使得两个子集的元素和相等。"
        ),
        input_data={"nums": [1, 5, 11, 5]},
        expected_result=True,
        strategy_hint="用 0-1 背包动态规划。",
        solution_count=1,
    )
    artifact, errors = _try_materialize(request, subset_sum_spec())
    if errors or not artifact.validation.release_gate.release_ready:
        raise RuntimeError("分割等和子集 demo 生成失败：\n" + "\n".join(errors))
    return artifact


def subset_sum_spec() -> dict:
    code = r'''
def solve(input_data):
    nums = input_data["nums"]
    total = sum(nums)
    if total % 2:
        return False
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:
        for j in range(target, num - 1, -1):
            dp[j] = dp[j] or dp[j - num]
    return dp[target]
'''.strip()
    tracker_code = r'''
def trace(input_data):
    nums = input_data["nums"]
    total = sum(nums)
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True
    events = [
        {
            "step": 0,
            "op": "create",
            "targets": [{"id": "nums"}, {"id": "dp"}],
            "state": {"nums": nums[:], "target": target, "dp": dp[:], "processed": 0},
            "role": "current",
            "reason": "把一半总和作为背包容量，dp[j] 表示容量 j 是否可达。",
            "code_line": 6,
        }
    ]
    for i, num in enumerate(nums):
        changed = []
        for j in range(target, num - 1, -1):
            old = dp[j]
            dp[j] = dp[j] or dp[j - num]
            if dp[j] != old:
                changed.append(j)
        focus = changed[-1] if changed else min(num, target)
        events.append(
            {
                "step": len(events),
                "op": "set",
                "targets": [{"id": f"nums[{i}]"}, {"id": f"dp[{focus}]"}],
                "deps": [{"id": f"dp[{max(0, focus - num)}]"}],
                "state": {"nums": nums[:], "target": target, "i": i, "num": num, "dp": dp[:], "processed": i + 1},
                "role": "current" if not dp[target] else "answer",
                "reason": f"尝试放入重量 {num} 的物品，更新所有能被它点亮的容量槽。",
                "code_line": 10,
            }
        )
    result = dp[target]
    events.append(
        {
            "step": len(events),
            "op": "mark",
            "targets": [{"id": f"dp[{target}]"}],
            "state": {"nums": nums[:], "target": target, "dp": dp[:], "result": result, "processed": len(nums)},
            "role": "answer",
            "reason": "目标容量被点亮，说明存在一个子集和为总和的一半。",
            "code_line": 12,
        }
    )
    return {
        "schema_version": "semantic-trace-v1",
        "algorithm": "分割等和子集 · 0-1 背包",
        "input_data": input_data,
        "result": result,
        "pseudocode": ["target = sum(nums) / 2", "倒序更新 dp[j]", "检查 dp[target]"],
        "events": events,
    }
'''.strip()
    verifier_code = r'''
def verify(input_data):
    nums = input_data["nums"]
    total = sum(nums)
    if total % 2:
        return False
    target = total // 2
    reachable = {0}
    for num in nums:
        reachable |= {x + num for x in list(reachable) if x + num <= target}
    return target in reachable
'''.strip()
    return {
        "problem_title": "分割等和子集",
        "input_contract": "输入 JSON：{\"nums\": 正整数数组}。",
        "variants": [
            {
                "id": "partition_knapsack",
                "name": "0-1 背包动态规划",
                "strategy": "把每个数字当成物品，容量为总和的一半，判断目标容量是否可达。",
                "time_complexity": "O(n * target)",
                "space_complexity": "O(target)",
                "code": code,
                "tracker_code": tracker_code,
            }
        ],
        "verifier_code": verifier_code,
    }


def export_demos(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    demos = [
        ("creative_partition_bag.html", subset_sum_artifact()),
        ("creative_graph_bfs.html", load_artifact("output/llm_benchmark_all_samples1/llm_graph_bfs_0.json")),
        ("creative_daily_temperatures.html", load_artifact("output/llm_benchmark_all_samples1/llm_daily_temperatures_0.json")),
        ("creative_convex_hull.html", load_artifact("output/llm_benchmark_all_samples1/llm_convex_hull_0.json")),
    ]
    paths = []
    for filename, artifact in demos:
        paths.append(save_creative_html(artifact, output_dir / filename))
    return paths


def main() -> int:
    output_dir = Path("output/creative_demos")
    paths = export_demos(output_dir)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
