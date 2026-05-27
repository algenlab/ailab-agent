"""Generate solution variants and tracker code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_client import chat_json

from algolab.schemas.input import ProblemInput
from algolab.schemas.correctness import CorrectnessContract
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.validation import BuildArtifact
from algolab.schemas.visual_plan import VisualPlan
from algolab.verification.repair_context import build_repair_context


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
    raw = chat_json(_prompt_text("contract_system.txt"), _build_contract_user_prompt(request))
    return normalize_contract_spec(raw)


def build_contract_with_repair(request: ProblemInput, max_rounds: int = 1) -> tuple[CorrectnessContract, list[dict[str, Any]]]:
    repair_log: list[dict[str, Any]] = []
    raw: Any = None
    last_errors: list[str] = []
    for round_idx in range(max_rounds + 1):
        if round_idx == 0:
            try:
                raw = chat_json(_prompt_text("contract_system.txt"), _build_contract_user_prompt(request))
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
    return chat_json(_prompt_text("contract_repair_system.txt"), prompt)


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
    repair_context = build_repair_context(errors)
    prompt = "\n\n".join(
        [
            _build_user_prompt(request),
            "上一次 JSON：",
            json.dumps(previous, ensure_ascii=False, indent=2),
            "结构化错误上下文：",
            json.dumps(repair_context, ensure_ascii=False, indent=2),
            "错误信息：",
            "\n".join(errors),
        ]
    )
    return normalize_solution_spec(chat_json(_prompt_text("repair_system.txt"), prompt))


def generate_visual_plan_candidate(artifact: BuildArtifact, capabilities: dict[str, Any]) -> VisualPlan:
    raw = chat_json(_prompt_text("visual_plan_system.txt"), _build_visual_plan_user_prompt(artifact, capabilities))
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
