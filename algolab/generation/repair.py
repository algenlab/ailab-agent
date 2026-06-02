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
            "R1 SemanticTrace 修复 checklist：",
            "\n".join(_semantic_trace_repair_checklist(repair_context)),
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


def _semantic_trace_repair_checklist(repair_context: list[dict[str, Any]]) -> list[str]:
    categories = {str(item.get("repair_category") or "") for item in repair_context}
    messages = "\n".join(str(item.get("message") or "") for item in repair_context).lower()
    lines: list[str] = []
    if _has_json_generation_failure(messages):
        lines.extend(
            [
                "- JSON 解析失败、空内容或截断后必须进入紧凑修复：只输出 1 个 variant，保持题意和 expected 不变。",
                "- tracker_code 必须短：6-10 个 events，reason 和 pseudocode 都用短句，不要复制长代码、长注释或完整历史。",
                "- 不要输出 16000 tokens；必要时设置 policy=\"sampled\" 或 max_events=40，并只展示 create、1-2 个关键转移和 role=answer。",
                "- 仍然必须返回完整 JSON object，顶层第一个字符是 {，最后一个字符是 }。",
            ]
        )
    if categories & {"trace_schema", "target_or_deps"}:
        lines.extend(
            [
                "- tracker 必须使用 tracer = Tracer(input_data, algorithm=..., pseudocode=[...])，最后 return tracer.to_trace()。",
                "- 事件字段只用 op/targets；禁止旧字段 type/target、裸字符串 targets 和旧式 map target。",
                '- TargetRef.id 必须是字符串；不要把多个 target 塞进一个 id，例如 {"id": ["pointer:left", "pointer:right"]}，应拆成 {"id": "pointer:left"} 和 {"id": "pointer:right"}。',
                "- map target 的 key 不写 Python 引号：使用 indegree[A]、dist[B]，不要写 indegree['A']，不要写 dist[\"B\"]。",
                '- deps 为 {"id": ...} 结构由 Tracer 自动生成；不要手写旧 events、events.append 或旧 deps/targets 结构。',
                "- 保留顶层 input_data，result 必须与 solve(input_data) 一致。",
            ]
        )
    if "choose" in messages:
        lines.append(
            "- 不存在 tracer.choose()；选择用 tracer.push / tracer.mark / tracer.enter，撤销用 tracer.pop / tracer.unmark / tracer.exit。"
        )
    if "tracer.__init__" in messages or "missing 1 required positional argument: 'input_data'" in messages:
        lines.append("- 修复 Tracer 初始化：不要调用 Tracer()，必须传入 input_data。")
    if "to_trace()" in messages or "to_trace(result" in messages:
        lines.append("- Tracer.to_trace 不接受 result 参数；必须先调用 tracer.result(answer)，最后 return tracer.to_trace()。")
    if "tracer._add" in messages or "unexpected keyword argument 'stage'" in messages:
        lines.append("- 不要调用私有 tracer._add，也不要传 stage=；阶段信息写入 state['phase'] 或 teaching。")
    if "compare 缺少 deps/value" in messages:
        lines.append("- compare 事件必须带 deps 或 value；GCD/数学循环比较时 deps 指向 a/b/remainder，value 写当前比较或终止条件。")
    if not lines:
        lines.append("- 按结构化错误上下文修复，不要改动无关题意或生成 renderer 代码。")
    lines.append("- 不要生成 HTML、CSS、JS 或 renderer 代码。")
    return lines


def _has_json_generation_failure(messages: str) -> bool:
    return any(
        token in messages
        for token in (
            "llmjsonerror",
            "jsondecodeerror",
            "unterminated string",
            "模型返回内容不是合法 json",
            "模型返回空内容",
            "不是合法 json",
            "truncated",
            "截断",
            "空内容",
        )
    )
