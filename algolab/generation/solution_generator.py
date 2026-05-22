"""Generate solution variants and tracker code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_client import chat_json

from algolab.schemas.input import ProblemInput
from algolab.schemas.semantic_trace import SolutionVariant


PROMPT_DIR = Path(__file__).parent / "prompts"


def _prompt_text(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def _build_user_prompt(request: ProblemInput) -> str:
    input_json = json.dumps(request.input_data, ensure_ascii=False, separators=(",", ":"))
    parts = [
        "题目：",
        request.problem,
        "",
        "具体输入 JSON：",
        input_json,
        "",
        f"希望生成解法数量：{request.solution_count}",
        "",
        "生成规模要求：",
        f"- variants 数量必须严格等于 {request.solution_count}。",
        "- 每个解法只保留教学必要步骤，trace 通常控制在 6-12 个关键事件。",
        "- reason 使用简短简体中文，单条尽量不超过 35 个字。",
        "- state 只保留当前可视化必要变量，不要反复塞入无关大对象。",
        "- 不要输出额外说明、markdown 或无关字段。",
    ]
    if request.strategy_hint:
        parts.extend(["", "用户指定或偏好的解法思路：", request.strategy_hint])
    if request.user_code:
        parts.extend(["", "用户提供代码，可作为一个解法变体进行插桩：", request.user_code])
    if request.expected_result is not None:
        parts.extend(["", "用户给出的期望输出：", json.dumps(request.expected_result, ensure_ascii=False)])
    return "\n".join(parts)


def generate_solution_spec(request: ProblemInput) -> dict[str, Any]:
    return normalize_solution_spec(chat_json(_prompt_text("tracker_system.txt"), _build_user_prompt(request)))


def repair_solution_spec(request: ProblemInput, previous: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    prompt = "\n\n".join(
        [
            _build_user_prompt(request),
            "上一次 JSON：",
            json.dumps(previous, ensure_ascii=False, indent=2),
            "错误信息：",
            "\n".join(errors),
        ]
    )
    return normalize_solution_spec(chat_json(_prompt_text("repair_system.txt"), prompt))


def normalize_solution_spec(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        spec = dict(raw)
    elif isinstance(raw, list):
        spec = {"variants": raw}
    else:
        raise ValueError(f"LLM 顶层输出必须是 JSON object，实际为 {type(raw).__name__}")
    variants = spec.get("variants")
    if isinstance(variants, dict):
        spec["variants"] = [variants]
    elif isinstance(variants, list):
        spec["variants"] = [item for item in variants if isinstance(item, dict)]
    else:
        spec["variants"] = []
    spec["problem_title"] = str(spec.get("problem_title") or "算法可视化实验")
    spec["input_contract"] = str(spec.get("input_contract") or "")
    spec["verifier_code"] = str(spec.get("verifier_code") or "")
    return spec


def parse_variants(spec: dict[str, Any]) -> list[SolutionVariant]:
    variants = []
    for item in spec.get("variants") or []:
        variants.append(
            SolutionVariant(
                id=str(item.get("id") or f"variant_{len(variants)}"),
                name=str(item.get("name") or item.get("id") or f"解法 {len(variants) + 1}"),
                strategy=str(item.get("strategy") or ""),
                time_complexity=str(item.get("time_complexity") or ""),
                space_complexity=str(item.get("space_complexity") or ""),
                code=str(item.get("code") or ""),
                tracker_code=str(item.get("tracker_code") or item.get("trace_code") or ""),
            )
        )
    return variants
