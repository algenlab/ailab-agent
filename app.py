"""English Gradio entry point for the verified AlgoTutorGen pipeline."""

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
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_PROBLEM = (
    "A robot starts in the top-left cell of an m by n grid and may move only "
    "right or down. Return the number of distinct paths to the bottom-right cell."
)
DEFAULT_INPUT_JSON = '{"m": 3, "n": 7}'
DEFAULT_STRATEGY = "Dynamic programming and combinatorics"
DEFAULT_EXPECTED_JSON = "28"
ENGLISH_BENCHMARK_PATH = PROJECT_ROOT / "benchmark" / "english_method_samples.json"


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _english_benchmark_cases() -> list[dict[str, Any]]:
    payload = json.loads(ENGLISH_BENCHMARK_PATH.read_text(encoding="utf-8"))
    return payload.get("cases", [])


def benchmark_preset_choices() -> list[str]:
    choices = []
    for case in _english_benchmark_cases():
        for sample in case.get("samples", []):
            index = int(sample.get("index", 0))
            choices.append(
                f"{case['title']} ({case['id']}) - sample {index} "
                f"-> {_json_text(sample.get('expected'))}"
            )
    return choices


def _benchmark_preset_map() -> dict[str, tuple[Any, Any]]:
    presets = {}
    for case in _english_benchmark_cases():
        for sample in case.get("samples", []):
            index = int(sample.get("index", 0))
            label = (
                f"{case['title']} ({case['id']}) - sample {index} "
                f"-> {_json_text(sample.get('expected'))}"
            )
            presets[label] = (case, sample)
    return presets


def load_benchmark_preset(choice: str):
    preset = _benchmark_preset_map().get(choice)
    if preset is None:
        return DEFAULT_PROBLEM, DEFAULT_INPUT_JSON, DEFAULT_STRATEGY, DEFAULT_EXPECTED_JSON, "", 2
    case, sample = preset
    return (
        case["problem"],
        _json_text(sample.get("input_data", {})),
        case.get("strategy", ""),
        _json_text(sample.get("expected")),
        "",
        1,
    )


def generate_lab(problem: str, input_json: str, strategy: str, user_code: str, expected_json: str, solutions: int):
    try:
        input_data = json.loads(input_json) if input_json.strip() else {}
    except Exception as exc:
        return f"Input JSON could not be parsed: {exc}", None, ""

    expected = None
    if expected_json.strip():
        try:
            expected = json.loads(expected_json)
        except Exception as exc:
            return f"Expected-output JSON could not be parsed: {exc}", None, ""

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
        return summary + f"\n\nHTML saved to: {out}", str(out), html
    except Exception:
        return "Generation failed. Check the input and local runtime log, then retry.", None, ""


def build_ui():
    with gr.Blocks(title="AlgoTutorGen") as demo:
        gr.Markdown(
            "# AlgoTutorGen\n"
            "Turn a concrete algorithm problem and input into a verifiable, "
            "interactive teaching page."
        )
        with gr.Row():
            with gr.Column(scale=1):
                benchmark = gr.Dropdown(
                    label="Benchmark case",
                    choices=benchmark_preset_choices(),
                    value=None,
                    info="Choose one of the released English cases to fill in the task and sample.",
                )
                problem = gr.Textbox(label="Problem", value=DEFAULT_PROBLEM, lines=7)
                input_json = gr.Textbox(label="Input JSON", value=DEFAULT_INPUT_JSON, lines=5)
                strategy = gr.Textbox(label="Optional strategy hint", value=DEFAULT_STRATEGY, lines=2)
                expected = gr.Textbox(label="Optional expected-output JSON", value=DEFAULT_EXPECTED_JSON, lines=1)
                user_code = gr.Textbox(label="Optional user code", value="", lines=8)
                solutions = gr.Slider(label="Number of solutions", minimum=1, maximum=4, step=1, value=2)
                button = gr.Button("Generate teaching page", variant="primary")
            with gr.Column(scale=2):
                summary = gr.Textbox(label="Build result", lines=10)
                html_file = gr.File(label="HTML file")
                preview = gr.HTML(label="Page preview")

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
