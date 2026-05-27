"""Repair context helpers for validation and benchmark failures."""

from __future__ import annotations

import re
from typing import Any

from algolab.verification.process_validator import process_failure_type_for_message


STEP_RE = re.compile(r"第\s*(\d+)\s*(?:步|帧|个事件)")
TARGET_PATTERNS = (
    re.compile(r"(?<![\w.])([A-Za-z_][\w]*(?:\[[^\]\s]+\])+)(?![\w.\[])"),
    re.compile(r"\b([A-Za-z_][\w]*:[^\s，,；;]+)\b"),
    re.compile(r"(?:target|对象|格式|转移|依赖|引用|写入|指向)[^：:]*[：:]\s*([A-Za-z_][\w]*(?:\[\d+\])?(?:\[[^\]]+\])?)"),
)


def build_repair_context(errors: list[str]) -> list[dict[str, Any]]:
    return [classify_repair_error(error) for error in errors]


def classify_repair_error(message: str) -> dict[str, Any]:
    return {
        "failure_type": repair_failure_type(message),
        "step": _extract_step(message),
        "target": _extract_target(message),
        "message": message,
    }


def repair_failure_type(message: str) -> str:
    text = message.lower()
    explicit = _explicit_failure_type(text)
    if explicit:
        return _normalize_failure_type(explicit)
    process_type = process_failure_type_for_message(message)
    if process_type == "coverage_error":
        return "coverage_error"
    if process_type in {"process_invariant", "process_fallback", "process_uncovered"}:
        return "process_error"
    if any(token in text for token in ("validationerror", "semantictrace", "schema", "field required")):
        return "schema_error"
    if "旧式 map target" in message or "target" in text or "引用了不存在" in message or "deps 未出现在 state" in message:
        return "target_error"
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
    return value or "generation_error"


def _extract_step(message: str) -> int | None:
    match = STEP_RE.search(message)
    return int(match.group(1)) if match else None


def _extract_target(message: str) -> str:
    for pattern in TARGET_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1).strip("。.,，；;")
    return ""
