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
    prompt_profile: str = "hybrid_current",
    execution_mode: str = "atomic",
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
            "\n".join(
                _semantic_trace_repair_checklist(
                    repair_context,
                    prompt_profile=prompt_profile,
                    execution_mode=execution_mode,
                )
            ),
            "错误信息：",
            "\n".join(errors),
        ]
    )


def _family_repair_lines(repair_context: list[dict[str, Any]]) -> list[str]:
    lines = [
        "- 只修复 tracker_code / trace / verify 和 SemanticTrace 字段；code 仅用于页面展示，不参与执行。",
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


def _semantic_trace_repair_checklist(
    repair_context: list[dict[str, Any]],
    *,
    prompt_profile: str = "hybrid_current",
    execution_mode: str = "atomic",
) -> list[str]:
    categories = {str(item.get("repair_category") or "") for item in repair_context}
    messages = "\n".join(str(item.get("message") or "") for item in repair_context).lower()
    lines: list[str] = []
    if _has_json_generation_failure(messages):
        lines.extend(
            [
                "- JSON 解析失败、空内容或截断后必须进入紧凑修复：保持请求提示中要求的 variants 数量，不能降为 1；题意和 expected 不变。",
                "- tracker_code 必须紧凑，reason 和 pseudocode 都用短句，不要复制长代码、长注释或完整历史。",
                "- 不要输出 16000 tokens；保留完整必要过程，但删除与算法无关的冗余 note、注释和重复代码。",
                "- 仍然必须返回完整 JSON object，顶层第一个字符是 {，最后一个字符是 }。",
            ]
        )
    if categories & {"trace_schema", "target_or_deps"}:
        lines.extend(
            [
                "- tracker_code 必须使用 sess = TraceSession(...), 最后 return sess.to_trace()。",
                (
                    "- 除 sess.record(...) 的显式 claim 外，不要手写 events、targets、deps 或旧 SemanticTrace 字段；"
                    "每个 claim 必须包含 op、targets、before、after。"
                    if execution_mode == "decoupled"
                    else "- 不要手写 events、targets、deps 或旧 SemanticTrace 字段；只通过 DSL 对象操作自动 emit。"
                ),
                (
                    "- DSL 对象只能调用白名单方法；不得调用 API 表之外的属性或方法。"
                    if prompt_profile == "service_only"
                    else "- DSL 对象只能调用白名单方法；不要猜测 GraphObj.node、Trie node.children、LinkedList node.next 等自然对象 API。"
                ),
                "- map/dict 可视化用 sess.map(...)，不要手写旧式 map target。",
                "- trace 的 sess.result(answer) 必须与 expected 或 verifier 结果一致；结果和轨迹必须来自同一次执行。",
            ]
        )
    if "choose" in messages:
        lines.append(
            "- 不存在 choose()；选择过程用 DSL 容器 push/pop、highlight/unhighlight 或 with sess.step(...) 表达。"
        )
    if "tracer.__init__" in messages or "missing 1 required positional argument: 'input_data'" in messages:
        lines.append("- 修复 TraceSession 初始化：不要调用旧 Tracer；使用 sess = TraceSession(algorithm, input_data)。")
    if "to_trace()" in messages or "to_trace(result" in messages:
        lines.append("- sess.to_trace 不接受 result 参数；必须先调用 sess.result(answer)，最后 return sess.to_trace()。")
    if "tracer._add" in messages or "unexpected keyword argument 'stage'" in messages:
        lines.append("- 不要调用私有 _add/_emit，也不要生成 renderer 字段；阶段信息用 with sess.step(...) 或 sess.note(...)。")
    if "dsl 静态方法检查失败" in messages or "object has no attribute" in messages:
        lines.append("- 如果 DSL 方法不存在，必须改成 tracker_system API 表里的方法；不要换一种新名字继续猜。")
    if "demo_missing_state" in messages or "缺少可复原 state" in messages:
        lines.append("- 只补 tracker_code 中缺失的 state/snapshot/step，不要修改 solve_code/code、verifier_code 或最终答案。")
    if "solve 结果" in messages and "trace 结果" in messages and "不一致" in messages:
        lines.append("- solve 已可能正确时，优先只修改 tracker_code 的 sess.result(...) 或 trace 计算逻辑；不要重写已正确的 solve_code/code。")
    if "compare 缺少 deps/value" in messages:
        lines.append(
            "- compare 事件必须带 deps 或 value，内容应对应当前判断使用的状态与终止条件。"
            if prompt_profile == "service_only"
            else "- compare 事件必须带 deps 或 value；GCD/数学循环比较时 deps 指向 a/b/remainder，value 写当前比较或终止条件。"
        )
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
