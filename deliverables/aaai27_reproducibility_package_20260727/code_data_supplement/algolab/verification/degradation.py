"""Explicit degradation policy for reports and debug evidence."""

from __future__ import annotations

from typing import Any

from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.validation import DegradationEntry, ReleaseGate
from algolab.verification.demo_readiness import DEMO_FAILURE_TYPES
from algolab.verification.process_validator import (
    ProcessFamilyRegistration,
    process_validation_profile_for_family,
)


DEGRADATION_TYPES: tuple[str, ...] = (
    "answer_only",
    "schema_scene_only",
    "process_fallback",
    "process_uncovered",
    "demo_warn",
)

_PROCESS_DEGRADATIONS = {"process_fallback", "process_uncovered"}


def process_degradation_for_trace(trace: SemanticTrace, *, variant_id: str = "") -> DegradationEntry | None:
    profile = process_validation_profile_for_trace(trace)
    if profile.failure_type not in _PROCESS_DEGRADATIONS:
        return None
    return DegradationEntry(
        type=profile.failure_type,
        reason=f"{profile.label}：{profile.coverage_rule}",
        source="process_validation_registry",
        affected_variant=variant_id,
        blocking=False,
    )


def process_validation_profile_for_trace(trace: SemanticTrace) -> ProcessFamilyRegistration:
    direct = process_validation_profile_for_family(trace.algorithm)
    if direct.failure_type != "process_uncovered":
        return direct
    for hint in _trace_family_hints(trace):
        profile = process_validation_profile_for_family(hint)
        if profile.failure_type != "process_uncovered":
            return profile
    return direct


def release_state_degradations(
    *,
    gate: ReleaseGate,
    errors: list[str],
    verifier_available: bool,
    expected_available: bool,
) -> list[DegradationEntry]:
    entries: list[DegradationEntry] = []
    if gate.trace_ready and gate.visual_ready and not gate.process_ready:
        entries.append(
            DegradationEntry(
                type="schema_scene_only",
                reason="Trace 与 SceneGraph 可用，但缺少 expected、verifier 或多解法交叉校验，不能宣称强答案证据。",
                source="release_gate",
                blocking=True,
            )
        )
    if (expected_available or verifier_available) and not gate.artifact_ready and not _has_answer_mismatch(errors):
        entries.append(
            DegradationEntry(
                type="answer_only",
                reason="答案侧证据存在，但 trace、process 或 scene 未达到可发布要求，只能作为答案层证据。",
                source="release_gate",
                blocking=True,
            )
        )
    return entries


def demo_warning_degradation(*, reason: str, variant_id: str = "") -> DegradationEntry:
    return DegradationEntry(
        type="demo_warn",
        reason=reason,
        source="demo_readiness",
        affected_variant=variant_id,
        blocking=False,
    )


def degradation_type_for_failure_type(failure_type: str) -> str:
    if failure_type in _PROCESS_DEGRADATIONS:
        return failure_type
    if failure_type == "demo_warn" or failure_type in DEMO_FAILURE_TYPES:
        return "demo_warn"
    return ""


def degradation_entries_for_result(item: dict[str, Any]) -> list[DegradationEntry]:
    entries: list[DegradationEntry] = []
    for raw in item.get("degradations") or []:
        if isinstance(raw, dict):
            entry_type = str(raw.get("type") or "")
            if entry_type in DEGRADATION_TYPES:
                entries.append(
                    DegradationEntry(
                        type=entry_type,  # type: ignore[arg-type]
                        reason=str(raw.get("reason") or raw.get("message") or entry_type),
                        source=str(raw.get("source") or "llm_benchmark_result"),
                        affected_variant=str(raw.get("affected_variant") or raw.get("variant_id") or ""),
                        blocking=bool(raw.get("blocking", False)),
                    )
                )
    explicit_type = str(item.get("degradation_type") or "")
    if explicit_type in DEGRADATION_TYPES:
        entries.append(
            DegradationEntry(
                type=explicit_type,  # type: ignore[arg-type]
                reason=str(item.get("degradation_reason") or explicit_type),
                source="llm_benchmark_result",
                blocking=not bool(item.get("ok", False)),
            )
        )
    for message in _result_messages(item):
        failure_type = _failure_type_from_message(message)
        degradation_type = degradation_type_for_failure_type(failure_type)
        if degradation_type:
            entries.append(
                DegradationEntry(
                    type=degradation_type,  # type: ignore[arg-type]
                    reason=message,
                    source="failure_type",
                    blocking=not bool(item.get("ok", False)),
                )
            )
    gate = item.get("release_gate") if isinstance(item.get("release_gate"), dict) else {}
    if gate and gate.get("trace_ready") and gate.get("visual_ready") and not gate.get("process_ready"):
        entries.append(
            DegradationEntry(
                type="schema_scene_only",
                reason="LLM result release_gate 显示 trace/visual ready，但缺少 process_ready。",
                source="release_gate",
                blocking=not bool(item.get("ok", False)),
            )
        )
    return dedupe_degradations(entries)


def empty_degradation_counts() -> dict[str, int]:
    return {name: 0 for name in DEGRADATION_TYPES}


def count_degradations(entries: list[DegradationEntry]) -> dict[str, int]:
    counts = empty_degradation_counts()
    for entry in entries:
        counts[entry.type] += 1
    return counts


def dedupe_degradations(entries: list[DegradationEntry]) -> list[DegradationEntry]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[DegradationEntry] = []
    for entry in entries:
        key = (entry.type, entry.reason, entry.source, entry.affected_variant)
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


def _trace_family_hints(trace: SemanticTrace) -> list[str]:
    hints: list[str] = []
    for event in trace.events:
        state = event.state or {}
        if "dp_contract" in state:
            hints.append("dp")
        if "array_contract" in state:
            hints.append("array_pointer")
        if "hash_contract" in state:
            hints.append("hash")
        if "sorting_contract" in state:
            hints.append("sorting")
        if "greedy_contract" in state:
            hints.append("greedy")
        graph_contract = state.get("graph_contract")
        if isinstance(graph_contract, dict):
            hints.append(_graph_contract_hint(graph_contract))
        family_contract = state.get("family_contract")
        if isinstance(family_contract, dict):
            family = family_contract.get("family") or family_contract.get("submode")
            if family:
                hints.append(str(family))
        if "union_find" in state or "dsu" in state:
            hints.append("union_find")
        if "segment_tree" in state or "fenwick" in state:
            hints.append("range_structure")
        if "points" in state and "hull" in state:
            hints.append("geometry")
    return hints


def _graph_contract_hint(contract: dict[str, Any]) -> str:
    submode = str(contract.get("submode") or contract.get("family") or "").lower()
    if submode in {"dijkstra", "bellman_ford", "bellman-ford", "floyd_warshall", "zero_one_bfs", "mst"}:
        return "shortest_path_mst"
    if submode in {
        "tarjan",
        "scc",
        "articulation_bridges",
        "bipartite_matching",
        "edmonds_karp",
        "flow",
    }:
        return "advanced_graph"
    return "bfs"


def _result_messages(item: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for key in ("errors", "warnings"):
        values = item.get(key)
        if isinstance(values, list):
            messages.extend(str(value) for value in values)
    if item.get("failure_type"):
        messages.append(f"failure_type={item['failure_type']}: result failure")
    if item.get("error"):
        messages.append(str(item["error"]))
    return messages


def _failure_type_from_message(message: str) -> str:
    marker = "failure_type="
    if marker not in message:
        return ""
    return message.split(marker, 1)[1].split(":", 1)[0].split(";", 1)[0].strip()


def _has_answer_mismatch(errors: list[str]) -> bool:
    text = "\n".join(errors).lower()
    return "answer_mismatch" in text or "expected" in text or "verifier" in text or "结果" in text
