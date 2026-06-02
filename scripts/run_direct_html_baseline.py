"""Run the direct-HTML LLM baseline as an external experiment."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import _model_name, chat_text_with_metadata, clear_model_calls, consume_model_calls
from scripts.baseline_experiment_utils import add_common_args, run_benchmark
from scripts.run_llm_benchmark import (
    BenchmarkCase,
    BenchmarkInput,
    UnseenBenchmarkCase,
    benchmark_condition,
    classify_failure,
    result_metadata,
)


def _system_prompt() -> str:
    return (
        "你是算法教学页面生成器。直接输出一个完整、可离线打开的单文件 HTML。"
        "不要输出 markdown。页面必须包含 id=title、id=counter、id=canvas、id=next，"
        "并在无后端环境下展示算法步骤、当前状态和解释。"
    )


def _user_prompt(case: BenchmarkCase | UnseenBenchmarkCase, sample: BenchmarkInput) -> str:
    return "\n".join(
        [
            f"题目：{case.title}",
            f"描述：{case.problem}",
            f"算法族：{case.family}",
            f"策略提示：{case.strategy}",
            f"输入 JSON：{json.dumps(sample.input_data, ensure_ascii=False)}",
            f"期望输出 JSON：{json.dumps(sample.expected, ensure_ascii=False)}",
            "要求：",
            "1. 只生成 HTML，不调用外部资源。",
            "2. #counter 初始格式必须类似 1 / N。",
            "3. #canvas 必须有可见教学内容。",
            "4. #next 点击后应推进一步或保持最后一步。",
            "5. 这是 direct_html_baseline，不要声称经过 AlgoLab SceneGraph 或机器 gate。",
        ]
    )


def extract_html(content: str) -> str:
    text = (content or "").strip()
    fenced = re.search(r"```(?:html)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    start_candidates = [idx for idx in (text.lower().find("<!doctype"), text.lower().find("<html")) if idx >= 0]
    if start_candidates:
        text = text[min(start_candidates) :].strip()
    return text


def validate_direct_html(html: str) -> list[str]:
    errors: list[str] = []
    lower = html.lower()
    if "<html" not in lower:
        errors.append("html_error: missing <html>")
    for required in ('id="title"', "id='title'", "id=title"):
        if required in lower:
            break
    else:
        errors.append("html_error: missing #title")
    for required in ('id="counter"', "id='counter'", "id=counter"):
        if required in lower:
            break
    else:
        errors.append("html_error: missing #counter")
    for required in ('id="canvas"', "id='canvas'", "id=canvas"):
        if required in lower:
            break
    else:
        errors.append("html_error: missing #canvas")
    return errors


def run_one_direct_html(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started = time.time()
    clear_model_calls()
    output_stem = f"direct_html_{case.id}_{sample_index}"
    output_html = args.output_dir / f"{output_stem}.html"
    metadata = result_metadata(case, sample_index, args)
    try:
        response = chat_text_with_metadata(_system_prompt(), _user_prompt(case, sample), kind="direct_html")
        html = extract_html(str(response.get("content") or ""))
        errors = validate_direct_html(html)
        if errors:
            raise ValueError("; ".join(errors))
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html, encoding="utf-8")
        output_html.with_suffix(".json").write_text(
            json.dumps(
                {
                    "kind": "direct_html_baseline_artifact",
                    "case_id": case.id,
                    "sample_index": sample_index,
                    "condition": benchmark_condition(args),
                    "html": str(output_html),
                    "html_chars": len(html),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "baseline": "direct_html_baseline",
            "ok": True,
            "html": str(output_html),
            "json": str(output_html.with_suffix(".json")),
            "duration_s": round(time.time() - started, 3),
            "failure_type": "",
            "model_calls": consume_model_calls(),
        }
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        failure_type = "html_error" if "html_error" in message or "missing #" in message else classify_failure(message)
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "baseline": "direct_html_baseline",
            "ok": False,
            "error": message,
            "failure_type": failure_type,
            "duration_s": round(time.time() - started, 3),
            "model_calls": consume_model_calls(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 direct HTML baseline，不进入 AlgoLab 主发布链路")
    add_common_args(parser, condition="direct_html_baseline")
    args = parser.parse_args()
    args.baseline = "direct_html_baseline"
    args.direct_html_baseline = True
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False
    return run_benchmark(args, run_one_direct_html)


if __name__ == "__main__":
    raise SystemExit(main())
