"""Repair context helpers for validation and benchmark failures."""

from __future__ import annotations

import json
import re
from typing import Any

from algolab.schemas.input import ProblemInput
from algolab.verification.process_validator import process_failure_type_for_message


STEP_RE = re.compile(r"第\s*(\d+)\s*(?:步|帧|个事件)")
TARGET_PATTERNS = (
    re.compile(r"(?<![\w.])([A-Za-z_][\w]*(?:\[[^\]\s]+\])+)(?![\w.\[])"),
    re.compile(r"\b([A-Za-z_][\w]*:[^\s，,；;]+)\b"),
    re.compile(r"(?:target|对象|格式|转移|依赖|引用|写入|指向)[^：:]*[：:]\s*([A-Za-z_][\w]*(?:\[\d+\])?(?:\[[^\]]+\])?)"),
)
DEMO_FAILURE_TYPES = {
    "demo_missing_reason",
    "demo_missing_deps",
    "demo_missing_state",
    "demo_state_jump",
    "demo_algorithm_mismatch",
    "demo_key_step_missing",
}
FORBIDDEN_REPAIR_ACTIONS = (
    "不要生成 HTML、CSS、JS 或 renderer 代码。",
    "不要绕过 SemanticTrace、SceneGraph、process validator 或 demo readiness。",
    "不要只改最终答案来掩盖错误过程。",
)
FAMILY_REPAIR_GUIDANCE: dict[str, tuple[str, ...]] = {
    "dynamic_programming": (
        "保持 dp_contract；初始化、每个关键 set、deps、value、formula 和 answer_position 必须可复核。",
        "小规模 DP 不要抽样跳过关键状态；补齐真实循环中的每个关键转移。",
    ),
    "graph": (
        "保持 graph_contract；frontier、visited/dist/parent、边检查或 relax 必须逐步记录。",
        "首次访问、松弛、拓扑入度、MST 选边和网络流增广都必须提供来源 deps。",
    ),
    "string": (
        "保持 family_contract；记录 text/pattern 指针和 pi/z/radius/hash/窗口表项。",
        "失配回退、中心扩展或窗口收缩必须写入 state 和 reason，不能只用自然语言。",
    ),
    "tree": (
        "保持 family_contract；记录 tree、frame:* enter/exit、current、return_values 或 aggregate。",
        "递归返回、LCA/直径/树形 DP 聚合必须用 deps 或 state 说明来自哪个子树。",
    ),
    "backtracking": (
        "保持 family_contract；记录 choose、enter、record、undo 以及 path/used 连续变化。",
        "撤销不能跳步；递归树或 frame 必须能解释当前分支和回退原因。",
    ),
    "array_pointer": (
        "保持 array_contract；记录 left/right/mid、窗口边界、比较值和移动原因。",
        "二分 mid 必须来自当前窗口；滑窗和前缀/差分状态不能无解释跳变。",
    ),
    "data_structure": (
        "保持对应 hash/sorting/heap/trie/linked_list/union_find contract 或 state 证据。",
        "push/pop/link/unlink/union/find 等结构变化必须有 before/after 或可复原 state。",
    ),
    "unknown": ("先修复 schema、target、deps、state、reason 和结果一致性，再考虑算法族细节。",),
}
CATEGORY_REPAIR_GUIDANCE: dict[str, str] = {
    "answer_correctness": "修复 solve、trace.result、verify 和 expected 的一致性；不要只改 trace.result。",
    "trace_schema": "修复 semantic-trace-v1 顶层和事件字段，使用 op/targets/state/code_line。",
    "trace_step_jump": "补齐缺失中间状态或解释跳变原因，关键过程不能直接从初始化跳到答案。",
    "target_or_deps": "修复 target/deps，使其指向 state 中可渲染、可解析的真实对象。",
    "process_invariant": "修复算法过程和不变量；指定 step 的 state、deps、value 必须与算法转移一致。",
    "coverage": "补齐关键步骤覆盖；小输入必须记录初始化、主循环、关键转移/访问和答案。",
    "demo_readiness": "补齐 reason、state、deps、阶段和教学证据，让页面能讲清当前步骤。",
    "scene_binding": "修复 state/targets/marks，使 SceneGraph 能绑定可见对象。",
    "execution": "修复 Python 执行错误、超时或死循环，优先用有界标准模板。",
    "generation": "返回完整 JSON，保持题目语义和已有正确部分，只修失败原因。",
}


def build_repair_context(
    errors: list[str],
    *,
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    family_hint = infer_repair_family(errors=errors, request=request, previous=previous)
    return [classify_repair_error(error, family_hint=family_hint) for error in errors]


def classify_repair_error(message: str, *, family_hint: str | None = None) -> dict[str, Any]:
    failure_type = repair_failure_type(message)
    repair_category = repair_category_for_message(message, failure_type)
    family = family_hint or infer_repair_family(errors=[message])
    return {
        "failure_type": failure_type,
        "repair_category": repair_category,
        "repair_instruction": CATEGORY_REPAIR_GUIDANCE.get(repair_category, CATEGORY_REPAIR_GUIDANCE["generation"]),
        "family": family,
        "family_guidance": list(FAMILY_REPAIR_GUIDANCE.get(family, FAMILY_REPAIR_GUIDANCE["unknown"])),
        "forbidden_actions": list(FORBIDDEN_REPAIR_ACTIONS),
        "step": _extract_step(message),
        "target": _extract_target(message),
        "message": message,
    }


def repair_failure_type(message: str) -> str:
    text = message.lower()
    explicit = _explicit_failure_type(text)
    if explicit:
        return _normalize_failure_type(explicit)
    if any(token in text for token in ("validationerror", "semantictrace", "schema", "field required")):
        return "schema_error"
    if "旧式 map target" in message or "target" in text or "引用了不存在" in message or "deps 未出现在 state" in message:
        return "target_error"
    process_type = process_failure_type_for_message(message)
    if process_type == "coverage_error":
        return "coverage_error"
    if process_type in {"process_invariant", "process_fallback", "process_uncovered"}:
        return "process_error"
    if "scene" in text or "layout" in text or "渲染" in message or "可见对象" in message or "帧" in message:
        return "scene_error"
    if "执行失败" in message or "sandbox" in text or "nameerror" in text or "syntaxerror" in text:
        return "execution_error"
    if "expected" in text or "verifier" in text or "结果" in message:
        return "correctness_error"
    return "generation_error"


def repair_failure_types(messages: list[str]) -> list[str]:
    result: list[str] = []
    for message in messages:
        failure_type = repair_failure_type(message)
        if failure_type not in result:
            result.append(failure_type)
    return result


def summarize_repair_failure_types(results: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        for failure_type in item.get("repair_failure_types") or []:
            if not isinstance(failure_type, str) or not failure_type:
                continue
            summary[failure_type] = summary.get(failure_type, 0) + 1
    return summary


def _explicit_failure_type(text: str) -> str:
    marker = "failure_type="
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    value = []
    for char in tail:
        if char.islower() or char == "_":
            value.append(char)
        else:
            break
    return "".join(value)


def _normalize_failure_type(value: str) -> str:
    if value == "process_invariant":
        return "process_error"
    if value in {"coverage_error", "schema_error", "target_error", "process_error", "scene_error"}:
        return value
    if value in DEMO_FAILURE_TYPES:
        return value
    return value or "generation_error"


def repair_category_for_message(message: str, failure_type: str | None = None) -> str:
    text = message.lower()
    failure = failure_type or repair_failure_type(message)
    if failure in DEMO_FAILURE_TYPES or "demo readiness" in text or "演示" in message:
        return "demo_readiness"
    if "跳步" in message or "跳变" in message or "state_jump" in text:
        return "trace_step_jump"
    if failure == "coverage_error":
        return "coverage"
    if failure == "schema_error":
        return "trace_schema"
    if failure == "target_error" or "deps" in text or "依赖" in message:
        return "target_or_deps"
    if failure in {"process_error", "process_invariant"}:
        return "process_invariant"
    if failure == "scene_error":
        return "scene_binding"
    if failure in {"execution_error", "timeout"}:
        return "execution"
    if failure in {"correctness_error", "answer_mismatch", "trace_result_mismatch"}:
        return "answer_correctness"
    if "expected" in text or "verifier" in text or "结果" in message or "trace.result" in text:
        return "answer_correctness"
    return "generation"


def infer_repair_family(
    *,
    errors: list[str],
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    if request is not None:
        parts.extend([request.problem, request.strategy_hint or ""])
    if previous is not None:
        parts.append(json.dumps(previous, ensure_ascii=False))
    parts.extend(errors)
    text = "\n".join(parts).lower()
    family_patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("dynamic_programming", ("dp", "动态规划", "不同路径", "背包", "lcs", "编辑距离", "状态压缩", "数位")),
        ("graph", ("graph", "图", "bfs", "dfs", "dijkstra", "bellman", "floyd", "拓扑", "mst", "kruskal", "tarjan", "network_flow", "网络流")),
        ("string", ("string", "字符串", "kmp", "rabin", "z algorithm", "manacher", "pattern", "text")),
        ("backtracking", ("backtracking", "回溯", "全排列", "permutation", "choose", "undo", "path", "used")),
        ("tree", ("tree", "二叉树", "树", "bst", "lca", "frame:dfs", "子树")),
        ("array_pointer", ("array_contract", "二分", "滑动窗口", "双指针", "前缀", "差分", "快慢指针")),
        ("data_structure", ("hash_contract", "sorting_contract", "heap", "trie", "linked_list", "union_find", "哈希", "堆", "链表", "并查集")),
    )
    for family, tokens in family_patterns:
        if any(token in text for token in tokens):
            return family
    return "unknown"


def _extract_step(message: str) -> int | None:
    match = STEP_RE.search(message)
    return int(match.group(1)) if match else None


def _extract_target(message: str) -> str:
    for pattern in TARGET_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1).strip("。.,，；;")
    return ""
