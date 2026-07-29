"""Generate solution variants and tracker code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_client import LLMJsonError, chat_json

from algolab.schemas.input import ProblemInput
from algolab.schemas.correctness import CorrectnessContract
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.validation import BuildArtifact
from algolab.schemas.visual_plan import VisualPlan
from algolab.generation.repair import build_solution_repair_prompt
from algolab.generation.language import output_language_requirement
from algolab.generation.execution_modes import load_execution_prompt
from algolab.verification.repair_context import build_repair_context


PROMPT_DIR = Path(__file__).parent / "prompts"


def _prompt_text(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def _chat_json(system_prompt: str, user_prompt: str, *, kind: str) -> dict[str, Any]:
    try:
        return chat_json(system_prompt, user_prompt, kind=kind)
    except TypeError as exc:
        if "unexpected keyword argument" in str(exc) and "kind" in str(exc):
            return chat_json(system_prompt, user_prompt)
        raise


def _build_user_prompt(request: ProblemInput) -> str:
    input_json = json.dumps(request.input_data, ensure_ascii=False, separators=(",", ":"))
    if request.output_language == "en":
        parts = [
            "Problem:",
            request.problem,
            "",
            "Concrete input JSON:",
            input_json,
            "",
            f"Required number of solution variants: {request.solution_count}",
            "",
            "Generation constraints:",
            f"- The variants array must contain exactly {request.solution_count} item(s).",
            "- Keep only instructionally meaningful trace events; a trace normally contains 30-60 key events.",
            "- Keep each reason concise and specific.",
            "- Return only the required JSON object without Markdown or extra fields.",
            "- Do not create learner checkpoints inside tracker_code. TraceSession has no checkpoint method; teaching interactions are added by a later stage.",
            "- " + output_language_requirement("en"),
        ]
        if request.strategy_hint:
            parts.extend(["", "Preferred solution strategy:", request.strategy_hint])
        if request.user_code:
            parts.extend(["", "User-provided code that may be instrumented as one variant:", request.user_code])
        if request.expected_result is not None:
            parts.extend(["", "Expected output:", json.dumps(request.expected_result, ensure_ascii=False)])
        return "\n".join(parts)
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
        "- 每个解法只保留教学必要步骤，trace 通常控制在 30-60 个关键事件。",
        "- reason 使用简短简体中文，单条尽量不超过 35 个字。",
        "- 不要输出额外说明、markdown 或无关字段。",
    ]
    if request.strategy_hint:
        parts.extend(["", "用户指定或偏好的解法思路：", request.strategy_hint])
    if request.user_code:
        parts.extend(["", "用户提供代码，可作为一个解法变体进行插桩：", request.user_code])
    if request.expected_result is not None:
        parts.extend(["", "用户给出的期望输出：", json.dumps(request.expected_result, ensure_ascii=False)])
    return "\n".join(parts)


def _domain_specific_generation_hints(request: ProblemInput) -> list[str]:
    """Removed: domain-specific hints are no longer used.

    The DSL-based architecture replaces per-algorithm hints with a generic
    DSL API exposed in tracker_system.txt. LLM writes natural Python with
    DSL hooks; schema and per-step state correctness are enforced by the
    DSL itself. Returns an empty list for compatibility with any caller.
    """
    return []


def generate_solution_spec(request: ProblemInput) -> dict[str, Any]:
    system = load_execution_prompt(
        "tracker_system.txt",
        request.prompt_profile,
        request.execution_mode,
    )
    requirement = output_language_requirement(request.output_language)
    if requirement:
        system = requirement + "\n\n" + system
    return normalize_solution_spec(_chat_json(system, _build_user_prompt(request), kind="generation"))


def _build_contract_user_prompt(request: ProblemInput) -> str:
    parts = [
        "题目：",
        request.problem,
        "",
        "具体输入 JSON：",
        json.dumps(request.input_data, ensure_ascii=False, separators=(",", ":")),
    ]
    if request.expected_result is not None:
        parts.extend(["", "用户给出的 expected：", json.dumps(request.expected_result, ensure_ascii=False)])
    if request.strategy_hint:
        parts.extend(["", "可选算法思路：", request.strategy_hint])
    parts.extend(
        [
            "",
            "请只返回 correctness-contract-v1 JSON。expected 优先；如果提供 oracle_code，它只能返回题目答案本身。",
        ]
    )
    return "\n".join(parts)


def generate_contract_candidate(request: ProblemInput) -> CorrectnessContract:
    raw = _chat_json(_prompt_text("contract_system.txt"), _build_contract_user_prompt(request), kind="generation")
    return normalize_contract_spec(raw)


def build_contract_with_repair(request: ProblemInput, max_rounds: int = 1) -> tuple[CorrectnessContract, list[dict[str, Any]]]:
    repair_log: list[dict[str, Any]] = []
    raw: Any = None
    last_errors: list[str] = []
    for round_idx in range(max_rounds + 1):
        if round_idx == 0:
            try:
                raw = _chat_json(_prompt_text("contract_system.txt"), _build_contract_user_prompt(request), kind="generation")
            except Exception as exc:
                raw = "{}"
                last_errors = [f"{type(exc).__name__}: {exc}"]
                repair_log.append({"round": round_idx, "status": "failed", "errors": last_errors})
                if round_idx >= max_rounds:
                    break
                raw = repair_contract_candidate(request, raw, last_errors)
                continue
        try:
            contract = normalize_contract_spec(raw)
            from algolab.verification.contract_validator import validate_contract

            report = validate_contract(contract, request)
            if report.release_gate.contract_ready:
                repair_log.append({"round": round_idx, "status": "ok", "errors": []})
                return contract, repair_log
            last_errors = [*report.errors, *report.release_gate.blocking_reasons]
        except Exception as exc:
            last_errors = [f"{type(exc).__name__}: {exc}"]
        repair_log.append({"round": round_idx, "status": "failed", "errors": last_errors})
        if round_idx >= max_rounds:
            break
        raw = repair_contract_candidate(request, raw, last_errors)
    raise ValueError("contract repair failed: " + "; ".join(last_errors))


def repair_contract_candidate(request: ProblemInput, previous: Any, errors: list[str]) -> dict[str, Any]:
    prompt = "\n\n".join(
        [
            _build_contract_user_prompt(request),
            "上一次 contract：",
            previous if isinstance(previous, str) else json.dumps(previous, ensure_ascii=False, indent=2),
            "错误信息：",
            "\n".join(errors),
            "请返回修复后的完整 correctness-contract-v1 JSON。",
        ]
    )
    return _chat_json(_prompt_text("contract_repair_system.txt"), prompt, kind="repair")


def normalize_contract_spec(raw: Any) -> CorrectnessContract:
    if not isinstance(raw, dict):
        raise ValueError(f"Contract 顶层必须是 JSON object，实际为 {type(raw).__name__}")
    data = dict(raw)
    data["schema_version"] = str(data.get("schema_version") or "correctness-contract-v1")
    data["input_schema"] = data.get("input_schema") or {}
    data["output_schema"] = str(data.get("output_schema") or "any")
    data["preconditions"] = _string_list(data.get("preconditions"))
    data["postconditions"] = _string_list(data.get("postconditions"))
    data["oracle_strategy"] = str(data.get("oracle_strategy") or "none")
    data["oracle_code"] = str(data.get("oracle_code") or "")
    data["test_cases"] = data.get("test_cases") or []
    data["metamorphic_relations"] = _string_list(data.get("metamorphic_relations"))
    data["process_invariants"] = _string_list(data.get("process_invariants"))
    return CorrectnessContract.model_validate(data)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def repair_solution_spec(request: ProblemInput, previous: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    repair_context = build_repair_context(errors, request=request, previous=previous)
    prompt = build_solution_repair_prompt(
        request_prompt=_build_user_prompt(request),
        previous=previous,
        errors=errors,
        repair_context=repair_context,
        prompt_profile=request.prompt_profile,
        execution_mode=request.execution_mode,
    )
    try:
        system = load_execution_prompt(
            "repair_system.txt",
            request.prompt_profile,
            request.execution_mode,
        )
        requirement = output_language_requirement(request.output_language)
        if requirement:
            system = requirement + "\n\n" + system
        repaired = normalize_solution_spec(_chat_json(system, prompt, kind="repair"))
        return _preserve_scope_locked_fields(previous, repaired, repair_context)
    except (LLMJsonError, ValueError) as exc:
        if not isinstance(exc, LLMJsonError) and "LLM 顶层输出必须是 JSON object" not in str(exc):
            raise
        label = "LLMJsonError" if isinstance(exc, LLMJsonError) else "ValueError"
        compact_errors = [*errors, f"{label}: {exc}"]
        compact_context = build_repair_context(compact_errors, request=request, previous=previous)
        compact_prompt = build_solution_repair_prompt(
            request_prompt=_build_user_prompt(request),
            previous=_compact_previous_for_json_retry(
                previous,
                expected_variant_count=request.solution_count,
            ),
            errors=compact_errors,
            repair_context=compact_context,
            prompt_profile=request.prompt_profile,
            execution_mode=request.execution_mode,
        )
        repaired = normalize_solution_spec(_chat_json(system, compact_prompt, kind="repair"))
        return _preserve_scope_locked_fields(previous, repaired, compact_context)


def _preserve_scope_locked_fields(
    previous: dict[str, Any],
    repaired: dict[str, Any],
    repair_context: list[dict[str, Any]],
) -> dict[str, Any]:
    categories = {str(item.get("repair_category") or "") for item in repair_context}
    scopes = {str(item.get("repair_scope") or "") for item in repair_context}
    tracker_only_scopes = {"tracker_only", "tracker_only_execution"}
    lock_code = categories == {"demo_state"} or (bool(scopes) and scopes <= tracker_only_scopes)
    lock_tracker = scopes == {"code_only"}
    lock_verifier = lock_code or lock_tracker
    if not lock_code and not lock_tracker and not lock_verifier:
        return repaired

    protected = dict(repaired)
    if lock_verifier and "verifier_code" in previous:
        protected["verifier_code"] = previous.get("verifier_code") or ""

    previous_variants = {
        str(item.get("id") or ""): item
        for item in previous.get("variants") or []
        if isinstance(item, dict)
    }
    locked_variants: list[dict[str, Any]] = []
    for index, variant in enumerate(protected.get("variants") or []):
        if not isinstance(variant, dict):
            locked_variants.append(variant)
            continue
        locked = dict(variant)
        previous_variant = previous_variants.get(str(variant.get("id") or ""))
        if previous_variant is None:
            previous_items = previous.get("variants") or []
            if index < len(previous_items) and isinstance(previous_items[index], dict):
                previous_variant = previous_items[index]
        if lock_code and previous_variant is not None and "code" in previous_variant:
            locked["code"] = previous_variant.get("code") or ""
        if lock_tracker and previous_variant is not None:
            previous_tracker = previous_variant.get("tracker_code")
            if previous_tracker is None:
                previous_tracker = previous_variant.get("trace_code")
            if previous_tracker is not None:
                locked["tracker_code"] = previous_tracker or ""
        locked_variants.append(locked)
    protected["variants"] = locked_variants
    return protected


def _compact_previous_for_json_retry(
    previous: dict[str, Any],
    *,
    expected_variant_count: int | None = None,
) -> dict[str, Any]:
    """Keep enough structure for repair while avoiding another oversized JSON response."""
    compact: dict[str, Any] = {
        "problem_title": str(previous.get("problem_title") or ""),
        "input_contract": str(previous.get("input_contract") or ""),
    }
    variants: list[dict[str, Any]] = []
    for item in previous.get("variants") or []:
        if not isinstance(item, dict):
            continue
        variants.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "strategy": str(item.get("strategy") or "")[:500],
                "time_complexity": str(item.get("time_complexity") or ""),
                "space_complexity": str(item.get("space_complexity") or ""),
                "code": _truncate_previous_code(str(item.get("code") or "")),
                "tracker_code": _truncate_previous_code(str(item.get("tracker_code") or item.get("trace_code") or "")),
            }
        )
    compact["variants"] = (
        variants[:expected_variant_count]
        if expected_variant_count is not None
        else variants
    )
    verifier_code = str(previous.get("verifier_code") or "")
    if verifier_code:
        compact["verifier_code"] = _truncate_previous_code(verifier_code, limit=1000)
    return compact


def _truncate_previous_code(value: str, *, limit: int = 1600) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n# ... 上轮代码已截断；本轮必须重写短 tracker_code，不能复制长代码。\n"


def generate_visual_plan_candidate(artifact: BuildArtifact, capabilities: dict[str, Any]) -> VisualPlan:
    raw = _chat_json(
        _prompt_text("visual_plan_system.txt"),
        _build_visual_plan_user_prompt(artifact, capabilities),
        kind="generation",
    )
    return normalize_visual_plan_spec(raw)


def normalize_visual_plan_spec(raw: Any) -> VisualPlan:
    if not isinstance(raw, dict):
        raise ValueError(f"VisualPlan 顶层必须是 JSON object，实际为 {type(raw).__name__}")
    data = dict(raw)
    data["schema_version"] = str(data.get("schema_version") or "visual-plan-v1")
    data["mode"] = str(data.get("mode") or "teaching")
    data["stage"] = str(data.get("stage") or "teaching_2d")
    data["metaphor"] = str(data.get("metaphor") or "")
    data["camera"] = data.get("camera") or {}
    data["animation"] = data.get("animation") or {}
    data["teaching"] = data.get("teaching") or {}
    data["layout_preferences"] = data.get("layout_preferences") or {}
    data["baseline_target"] = str(data.get("baseline_target") or "teaching_2d")
    return VisualPlan.model_validate(data)


def _build_visual_plan_user_prompt(artifact: BuildArtifact, capabilities: dict[str, Any]) -> str:
    scene_summary = {
        variant_id: {
            "algorithm": scene.algorithm,
            "frames": len(scene.frames),
            "layouts": sorted(
                {
                    str(obj.meta.get("layout"))
                    for frame in scene.frames
                    for obj in frame.objects
                    if obj.type.value == "container" and obj.meta.get("layout")
                }
            ),
        }
        for variant_id, scene in artifact.scenes.items()
    }
    payload = {
        "problem_title": artifact.problem_title,
        "input_data": artifact.input_data,
        "release_gate": artifact.validation.release_gate.model_dump(),
        "scene_summary": scene_summary,
        "capabilities": capabilities,
    }
    return "基于以下已验证 artifact 摘要输出 visual-plan-v1 JSON：\n" + json.dumps(
        payload, ensure_ascii=False, indent=2
    )


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
