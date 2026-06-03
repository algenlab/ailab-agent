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
    browser_smoke_html_paths,
    classify_failure,
    result_metadata,
)


def _system_prompt() -> str:
    return (
        "你是算法教学页面生成器。直接输出一个完整、可离线打开的单文件 HTML。"
        "不要输出 markdown。页面必须包含 id=title、id=counter、id=canvas、id=next、id=answer，"
        "并在无后端环境下展示算法步骤、当前状态和解释。"
    )


def _user_prompt(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    *,
    expected_visible_to_model: bool = True,
) -> str:
    lines = [
        f"题目：{case.title}",
        f"描述：{case.problem}",
        f"算法族：{case.family}",
        f"策略提示：{case.strategy}",
        f"输入 JSON：{json.dumps(sample.input_data, ensure_ascii=False)}",
    ]
    if expected_visible_to_model:
        lines.append(f"期望输出 JSON：{json.dumps(sample.expected, ensure_ascii=False)}")
    else:
        lines.append("标准答案不提供。请自行求解并在页面中清晰展示最终答案。")
    lines.extend(
        [
            "要求：",
            "1. 只生成 HTML，不调用外部资源。",
            "2. #counter 初始格式必须类似 1 / N。",
            "3. #canvas 必须有可见教学内容。",
            "4. #next 点击后应推进一步或保持最后一步。",
            "5. #answer 必须包含你自行求解得到的最终答案 JSON，和页面展示一致。",
            "6. 这是 direct_html_baseline，不要声称经过 AlgoLab SceneGraph 或机器 gate。",
        ]
    )
    return "\n".join(lines)


def _repair_prompt(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    *,
    previous_html: str,
    errors: list[str],
    expected_visible_to_model: bool,
) -> str:
    lines = [
        "上一版 direct HTML baseline 失败，请修复后重新输出完整单文件 HTML。",
        f"题目：{case.title}",
        f"描述：{case.problem}",
        f"算法族：{case.family}",
        f"策略提示：{case.strategy}",
        f"输入 JSON：{json.dumps(sample.input_data, ensure_ascii=False)}",
    ]
    if expected_visible_to_model:
        lines.append(f"期望输出 JSON：{json.dumps(sample.expected, ensure_ascii=False)}")
    else:
        lines.append("标准答案不提供。请自行求解并在页面中清晰展示最终答案。")
    lines.extend(
        [
            "失败信息：",
            *[f"- {error}" for error in errors],
            "修复要求：",
            "1. 只输出完整 HTML，不要输出 markdown。",
            "2. 必须包含 #title、#counter、#canvas、#next、#answer。",
            "3. #counter 格式类似 1 / N，#canvas 初始可见且非空。",
            "4. #answer 的 textContent 必须是最终答案 JSON，不能只写解释文字。",
            "5. 不调用外部资源，不要声称经过 AlgoLab SceneGraph 或机器 gate。",
            "上一版 HTML：",
            previous_html[-12000:],
        ]
    )
    return "\n".join(lines)


def extract_html(content: str) -> str:
    text = (content or "").strip()
    fenced = re.search(r"```(?:html)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    start_candidates = [idx for idx in (text.lower().find("<!doctype"), text.lower().find("<html")) if idx >= 0]
    if start_candidates:
        text = text[min(start_candidates) :].strip()
    return text


def _has_id(html_lower: str, node_id: str) -> bool:
    for required in (f'id="{node_id}"', f"id='{node_id}'", f"id={node_id}"):
        if required in html_lower:
            return True
    return False


def validate_direct_html(html: str) -> list[str]:
    errors: list[str] = []
    lower = html.lower()
    if "<html" not in lower:
        errors.append("html_error: missing <html>")
    for node_id in ("title", "counter", "canvas"):
        if not _has_id(lower, node_id):
            errors.append(f"html_error: missing #{node_id}")
    return errors


def _browser_validation_errors(output_html: Path) -> list[str]:
    checks = browser_smoke_html_paths([output_html])
    if checks and checks[0].get("ok") is True:
        return []
    check = checks[0] if checks else {"errors": ["browser smoke failed"]}
    errors = check.get("errors") or ["browser smoke failed"]
    return [f"browser_error: {error}" for error in errors]


def _failure_type_from_errors(errors: list[str]) -> str:
    message = "; ".join(errors)
    if "browser_error" in message:
        return "browser"
    if "html_error" in message or "missing #" in message:
        return "html_error"
    return classify_failure(message)


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
    expected_visible = bool(getattr(args, "expected_visible_to_model", True))
    baseline = str(getattr(args, "baseline", "direct_html_baseline"))
    max_rounds = max(0, int(getattr(args, "max_rounds", 0) or 0))
    browser_repair_enabled = bool(getattr(args, "browser_smoke", False) and max_rounds > 0)
    previous_html = ""
    last_errors: list[str] = []
    repair_rounds = 0
    phase_timings: list[dict[str, Any]] = []
    try:
        for attempt in range(max_rounds + 1):
            attempt_started = time.time()
            if attempt == 0:
                user_prompt = _user_prompt(case, sample, expected_visible_to_model=expected_visible)
                kind = "direct_html"
            else:
                repair_rounds += 1
                user_prompt = _repair_prompt(
                    case,
                    sample,
                    previous_html=previous_html,
                    errors=last_errors,
                    expected_visible_to_model=expected_visible,
                )
                kind = "direct_html_repair"
            response = chat_text_with_metadata(_system_prompt(), user_prompt, kind=kind)
            html = extract_html(str(response.get("content") or ""))
            previous_html = html
            errors = validate_direct_html(html)
            if not errors:
                output_html.parent.mkdir(parents=True, exist_ok=True)
                output_html.write_text(html, encoding="utf-8")
                if browser_repair_enabled:
                    errors = _browser_validation_errors(output_html)
            last_errors = errors
            if attempt > 0:
                phase_timings.append(
                    {
                        "phase": f"repair_round_{attempt}",
                        "duration_s": round(time.time() - attempt_started, 3),
                        "errors": errors,
                    }
                )
            if not errors:
                output_html.with_suffix(".json").write_text(
                    json.dumps(
                        {
                            "kind": "direct_html_baseline_artifact",
                            "case_id": case.id,
                            "sample_index": sample_index,
                            "condition": benchmark_condition(args),
                            "html": str(output_html),
                            "html_chars": len(html),
                            "direct_html_repair_rounds": repair_rounds,
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
                    "baseline": baseline,
                    "expected_visible_to_model": expected_visible,
                    "direct_html_repair_enabled": max_rounds > 0,
                    "direct_html_browser_repair_enabled": browser_repair_enabled,
                    "direct_html_repair_attempted": repair_rounds > 0,
                    "direct_html_repair_rounds": repair_rounds,
                    "ok": True,
                    "html": str(output_html),
                    "json": str(output_html.with_suffix(".json")),
                    "duration_s": round(time.time() - started, 3),
                    "failure_type": "",
                    "phase_timings": phase_timings,
                    "model_calls": consume_model_calls(),
                }
        raise ValueError("; ".join(last_errors or ["direct_html generation failed"]))
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        failure_type = _failure_type_from_errors(last_errors) if last_errors else (
            "html_error" if "html_error" in message or "missing #" in message else classify_failure(message)
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
            "baseline": str(getattr(args, "baseline", "direct_html_baseline")),
            "expected_visible_to_model": bool(getattr(args, "expected_visible_to_model", True)),
            "direct_html_repair_enabled": max_rounds > 0,
            "direct_html_browser_repair_enabled": browser_repair_enabled,
            "direct_html_repair_attempted": repair_rounds > 0,
            "direct_html_repair_rounds": repair_rounds,
            "ok": False,
            "error": message,
            "failure_type": failure_type,
            "repair_failure_types": [failure_type] if repair_rounds > 0 else [],
            "phase_timings": phase_timings,
            "duration_s": round(time.time() - started, 3),
            "model_calls": consume_model_calls(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 direct HTML baseline，不进入 AlgoLab 主发布链路")
    add_common_args(parser, condition="direct_html_baseline")
    parser.add_argument(
        "--hide-expected",
        action="store_false",
        dest="expected_visible_to_model",
        default=True,
        help="不把 expected output 暴露给 direct HTML baseline；用于公平 answer correctness 条件。",
    )
    args = parser.parse_args()
    if not args.expected_visible_to_model:
        args.condition = "direct_html_no_expected"
    args.baseline = "direct_html_baseline" if args.expected_visible_to_model else "direct_html_no_expected"
    args.direct_html_baseline = True
    args.direct_html_repair_enabled = args.max_rounds > 0
    args.direct_html_browser_repair_enabled = bool(args.browser_smoke and args.max_rounds > 0)
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False
    return run_benchmark(args, run_one_direct_html)


if __name__ == "__main__":
    raise SystemExit(main())
