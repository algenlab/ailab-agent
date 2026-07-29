"""AlgoLab Gradio UI.

新主入口：题目 + 输入 + 可选思路/代码 -> 可验证语义轨迹 -> scene graph -> 中文交互页面。
旧 pipeline 不再作为主入口。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent
GRADIO_TEMP_DIR = PROJECT_ROOT / ".gradio_cache"
GRADIO_TEMP_DIR.mkdir(exist_ok=True)
os.environ.setdefault("GRADIO_TEMP_DIR", str(GRADIO_TEMP_DIR))

import gradio as gr

from algolab.pipeline import artifact_summary, build_artifact
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput
from benchmark.cases import benchmark_cases


OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_PROBLEM = (
    "LeetCode 62. 不同路径。一个机器人位于 m x n 网格的左上角，"
    "每次只能向下或向右移动一步，返回到达右下角的不同路径数量。"
)
DEFAULT_INPUT_JSON = '{"m": 3, "n": 7}'
DEFAULT_STRATEGY = "动态规划和组合数学"
DEFAULT_EXPECTED_JSON = "28"
BENCHMARK_PLACEHOLDER = "选择 benchmark case"


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _preset_key(case_id: str, sample_index: int) -> str:
    return f"{case_id}::sample{sample_index}"


def benchmark_preset_choices() -> list[str]:
    choices = []
    for case in benchmark_cases():
        for index, sample in enumerate(case.samples):
            choices.append(f"{case.title} ({case.id}) - sample {index} -> {_json_text(sample.expected)}")
    return choices


def _benchmark_preset_map() -> dict[str, tuple[Any, Any]]:
    presets = {}
    for case in benchmark_cases():
        for index, sample in enumerate(case.samples):
            label = f"{case.title} ({case.id}) - sample {index} -> {_json_text(sample.expected)}"
            presets[label] = (case, sample)
    return presets


def load_benchmark_preset(choice: str):
    preset = _benchmark_preset_map().get(choice)
    if preset is None:
        return DEFAULT_PROBLEM, DEFAULT_INPUT_JSON, DEFAULT_STRATEGY, DEFAULT_EXPECTED_JSON, "", 2
    case, sample = preset
    return (
        case.problem,
        _json_text(sample.input_data),
        case.strategy,
        _json_text(sample.expected),
        "",
        1,
    )


def generate_lab(problem: str, input_json: str, strategy: str, user_code: str, expected_json: str, solutions: int):
    try:
        input_data = json.loads(input_json) if input_json.strip() else {}
    except Exception as exc:
        return f"输入 JSON 解析失败：{exc}", None, ""

    expected = None
    if expected_json.strip():
        try:
            expected = json.loads(expected_json)
        except Exception as exc:
            return f"期望输出 JSON 解析失败：{exc}", None, ""

    request = ProblemInput(
        problem=problem,
        input_data=input_data,
        strategy_hint=strategy,
        user_code=user_code,
        expected_result=expected,
        solution_count=int(solutions),
        teaching_enrichment=True,
    )

    try:
        artifact = build_artifact(request)
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = save_html(artifact, OUTPUT_DIR / "algolab.html")
        summary = artifact_summary(artifact)
        html = out.read_text(encoding="utf-8")
        return summary + f"\n\nHTML 已保存：{out}", str(out), html
    except Exception as exc:
        return f"生成失败：{exc}", None, ""


def build_ui():
    with gr.Blocks(title="AlgoLab") as demo:
        gr.Markdown("# AlgoLab\n输入算法题和数据，生成可验证的交互式算法可视化页面。")
        with gr.Row():
            with gr.Column(scale=1):
                benchmark = gr.Dropdown(
                    label="Benchmark case",
                    choices=benchmark_preset_choices(),
                    value=None,
                    info="选择 docs/benchmark_cases_list.md 中的样例后自动填入题目、输入、期望输出和思路。",
                )
                problem = gr.Textbox(label="题目描述", value=DEFAULT_PROBLEM, lines=7)
                input_json = gr.Textbox(label="输入 JSON", value=DEFAULT_INPUT_JSON, lines=5)
                strategy = gr.Textbox(label="可选：解法思路", value=DEFAULT_STRATEGY, lines=2)
                expected = gr.Textbox(label="可选：期望输出 JSON", value=DEFAULT_EXPECTED_JSON, lines=1)
                user_code = gr.Textbox(label="可选：用户代码", value="", lines=8)
                solutions = gr.Slider(label="解法数量", minimum=1, maximum=4, step=1, value=2)
                button = gr.Button("生成可视化页面", variant="primary")
            with gr.Column(scale=2):
                summary = gr.Textbox(label="构建结果", lines=10)
                html_file = gr.File(label="HTML 文件")
                preview = gr.HTML(label="页面预览")

        benchmark.change(
            load_benchmark_preset,
            inputs=[benchmark],
            outputs=[problem, input_json, strategy, expected, user_code, solutions],
        )
        button.click(
            generate_lab,
            inputs=[problem, input_json, strategy, user_code, expected, solutions],
            outputs=[summary, html_file, preview],
        )
    return demo


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7861, share=False)
