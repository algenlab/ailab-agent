"""Prompt helpers for solution repair."""

from __future__ import annotations

import json
from typing import Any


def build_solution_repair_prompt(
    *,
    request_prompt: str,
    previous: dict[str, Any],
    errors: list[str],
    repair_context: list[dict[str, Any]],
) -> str:
    return "\n\n".join(
        [
            request_prompt,
            "上一次 JSON：",
            json.dumps(previous, ensure_ascii=False, indent=2),
            "结构化错误上下文：",
            json.dumps(repair_context, ensure_ascii=False, indent=2),
            "族级修复要求：",
            "\n".join(_family_repair_lines(repair_context)),
            "错误信息：",
            "\n".join(errors),
        ]
    )


def _family_repair_lines(repair_context: list[dict[str, Any]]) -> list[str]:
    lines = [
        "- 只修复 solve / trace / verify 和 SemanticTrace 字段；不要生成 HTML、CSS、JS 或 renderer 代码。",
        "- 保留每条 failure_type，不要在 repair 后吞掉原始失败分类。",
    ]
    seen: set[str] = set()
    for item in repair_context:
        category = str(item.get("repair_category") or "")
        family = str(item.get("family") or "")
        key = f"{family}:{category}"
        if key in seen:
            continue
        seen.add(key)
        instruction = str(item.get("repair_instruction") or "")
        if family or category or instruction:
            lines.append(f"- family={family or 'unknown'} category={category or 'generation'}：{instruction}")
        for guidance in item.get("family_guidance") or []:
            if isinstance(guidance, str) and guidance:
                lines.append(f"  - {guidance}")
    return lines
