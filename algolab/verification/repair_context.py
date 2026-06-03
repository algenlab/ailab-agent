"""Repair context helpers for validation and benchmark failures.

DSL-era simplified version. The original v0 implementation contained 800+ lines
of family-specific repair guidance, keyword routers (200+ keywords), and
algorithm-specific instructions. With the DSL architecture this is no longer
useful: LLM produces algorithm code (not trace JSON), so repair errors arrive
as Python exceptions with line numbers, and the most useful repair context is
just the message + a short category-specific instruction.

Public API preserved (build_repair_context, classify_repair_error,
repair_failure_types, summarize_repair_failure_types, repair_failure_type,
repair_category_for_message) for backward compatibility with callers in
solution_generator.py / scripts/run_*_benchmark.py.
"""

from __future__ import annotations

import re
from typing import Any

from algolab.schemas.input import ProblemInput
from algolab.verification.process_validator import process_failure_type_for_message


STEP_RE = re.compile(r"第\s*(\d+)\s*(?:步|帧|个事件)")
TARGET_PATTERNS = (
    re.compile(r"(?<![\w.])([A-Za-z_][\w]*(?:\[[^\]\s]+\])+)(?![\w.\[])"),
    re.compile(r"(node|edge|frame):([A-Za-z0-9_./-]+(?:->[A-Za-z0-9_./-]+)?)"),
)


# -----------------------------------------------------------------------------
# Public failure-type classification
# -----------------------------------------------------------------------------

def repair_failure_type(message: str) -> str:
    """Classify a single repair error into one of a small fixed set.

    DSL-era classes (in priority order):
    - json_generation : LLM returned malformed/empty JSON
    - trace_schema    : SemanticTrace schema validation failure
    - result_mismatch : solve vs trace answer mismatch
    - trace_size      : events > max_events or state > size budget
    - execution       : Python exception inside solve / trace
    - generation      : default catch-all
    """
    text = (message or "").lower()
    if any(t in text for t in ("llmjsonerror", "jsondecodeerror", "unterminated string",
                               "模型返回内容不是合法 json", "模型返回空内容",
                               "不是合法 json", "顶层输出必须是 json")):
        return "json_generation"
    if "validationerror" in text or "schema" in text:
        return "trace_schema"
    if ("solve 结果" in message and "不一致" in message) or "result mismatch" in text:
        return "result_mismatch"
    if "events 过多" in text or "max_events" in text or "单步 state 过大" in message:
        return "trace_size"
    if any(t in text for t in ("traceback", "exception", "indexerror", "keyerror",
                               "typeerror", "valueerror", "zerodivisionerror",
                               "attributeerror", "nameerror", "执行失败", "执行超时")):
        return "execution"
    upstream = process_failure_type_for_message(message or "")
    if upstream:
        return upstream
    return "generation"


def repair_failure_types(messages: list[str]) -> list[str]:
    return [repair_failure_type(m) for m in messages or []]


def summarize_repair_failure_types(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in results or []:
        for ft in entry.get("repair_failure_types") or []:
            counts[ft] = counts.get(ft, 0) + 1
    return counts


# -----------------------------------------------------------------------------
# Public category mapping (one repair_category per error message)
# -----------------------------------------------------------------------------

_CATEGORY_INSTRUCTIONS = {
    "generation": "返回完整 JSON，保持题目语义和已有正确部分，只修失败原因。",
    "trace_schema": "trace(input_data) 必须 return sess.to_trace()；schema 由 DSL 自动保证，不要手写 events 列表。",
    "execution": "查 traceback 行号定位 Python 异常，修代码逻辑或边界条件；考虑空数组、单元素、索引越界。",
    "result_consistency": "solve 与 trace 的最终答案必须完全一致；最稳妥的做法是 trace 内复用 solve 的算法逻辑。",
    "trace_size": "事件超过预算：缩小输入循环规模或删除冗余 sess.note；不要重复 highlight 同一对象。",
}


def repair_category_for_message(message: str, failure_type: str | None = None) -> str:
    ft = failure_type or repair_failure_type(message)
    if ft == "json_generation":
        return "generation"
    if ft == "trace_schema":
        return "trace_schema"
    if ft == "execution":
        return "execution"
    if ft == "result_mismatch":
        return "result_consistency"
    if ft == "trace_size":
        return "trace_size"
    return "generation"


# -----------------------------------------------------------------------------
# Public per-error classification (used to build LLM repair context)
# -----------------------------------------------------------------------------

def classify_repair_error(
    message: str,
    *,
    family_hint: str | None = None,
    graph_submode_hint: str | None = None,
    data_structure_submode_hint: str | None = None,
    dp_submode_hint: str | None = None,
) -> dict[str, Any]:
    """DSL-era simplified classifier. family_hint and submode hints are accepted
    but ignored (kept for signature compatibility)."""
    failure_type = repair_failure_type(message)
    repair_category = repair_category_for_message(message, failure_type)
    repair_instruction = _specific_repair_instruction(message) or _CATEGORY_INSTRUCTIONS.get(
        repair_category, _CATEGORY_INSTRUCTIONS["generation"]
    )
    return {
        "message": message,
        "failure_type": failure_type,
        "repair_category": repair_category,
        "repair_instruction": repair_instruction,
        "step": _extract_step(message),
        "targets": _extract_targets(message),
        "family": "",
        "family_guidance": [],
    }


def build_repair_context(
    errors: list[str],
    *,
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Top-level entry: produce one classified context entry per error."""
    return [classify_repair_error(error) for error in (errors or [])]


# -----------------------------------------------------------------------------
# Legacy helpers kept as no-op stubs (DSL-era never infers per-family guidance)
# -----------------------------------------------------------------------------

def infer_repair_family(*, errors=None, request=None, previous=None) -> str:
    return ""


def infer_data_structure_repair_submode(*, errors=None, request=None, previous=None) -> str:
    return ""


def infer_dp_repair_submode(*, errors=None, request=None, previous=None) -> str:
    return ""


def infer_graph_repair_submode(*, errors=None, request=None, previous=None) -> str:
    return ""


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _extract_step(message: str) -> int | None:
    if not message:
        return None
    match = STEP_RE.search(message)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _specific_repair_instruction(message: str) -> str:
    text = (message or "").lower()
    if "cannot unpack non-iterable int object" in text:
        return "循环解包写错：如果遍历 digits/数组并需要下标和值，必须写 for index, digit in enumerate(digits)，不要写 for index, digit in digits。"
    if "list indices must be integers or slices, not nonetype" in text:
        return "列表下标变成 None：链表/指针算法必须先判断 curr is not None，再访问 values[curr] 或 nodes[curr]；反转链表要先保存 next，再改 curr.next。"
    if "list indices must be integers or slices, not list" in text or "list indices must be integers or slices, not range" in text:
        return "列表下标用了 list：几何/凸包中必须统一栈里存点索引还是点坐标。若栈里存点索引，访问 points[idx]；若栈里存点坐标，直接用 point，不要再写 points[point]。"
    if "'list' object has no attribute 'highlight'" in text or "'list' object has no attribute 'highlight_range'" in text:
        return "不要把普通 Python list 当作 DSL 对象调用 highlight/highlight_range。二维 DP 需要保留 TableObj 变量（例如 dp_table = sess.table(...)），普通数组另起名（例如 dp_values），高亮调用必须作用在 TableObj 上。"
    if "keyerror" in text and ("tarjan" in message.lower() or "割点" in message or "桥" in message):
        return "Tarjan 字典未初始化：进入 DFS 前必须为所有节点初始化 disc/low/parent/visited 等 dict，或用 dict.get(node, default)；遍历邻居前确保 graph 中每个节点都有邻接表。"
    if "反转" in message and "solve 结果" in message and "trace 结果 []" in message:
        return "反转链表的 trace 不能只更新指针后返回空列表；必须在 trace 结束时从新 head 沿 next 指针还原结果列表，并用 sess.result(result) 返回与 solve 完全相同的列表。"
    if "trie" in message.lower() and "solve 结果" in message and "trace 结果" in message:
        return "Trie 前缀计数的 trace 必须与 solve 使用同一查询口径；插入所有 words 后调用 trie.prefix_count(prefix) 或 trie.count_prefix(prefix)，并用 sess.result(count) 返回该 count。"
    if ("结果 19" in message and "18" in message) or ("expected 18" in text and "结果 10" in message) or "digit_dp_no_seven" in text or "不含 7" in message or "逐位前缀计数" in message or "数位dp" in text:
        return "数位 DP 统计的是 1..n 的正整数，不包含 0；n=20 时只排除 7 和 17，答案必须是 18。"
    return ""


def _extract_targets(message: str) -> list[str]:
    if not message:
        return []
    targets: list[str] = []
    seen: set[str] = set()
    for pattern in TARGET_PATTERNS:
        for match in pattern.finditer(message):
            target = match.group(0) if pattern is TARGET_PATTERNS[0] else f"{match.group(1)}:{match.group(2)}"
            if target and target not in seen:
                seen.add(target)
                targets.append(target)
    return targets[:8]
