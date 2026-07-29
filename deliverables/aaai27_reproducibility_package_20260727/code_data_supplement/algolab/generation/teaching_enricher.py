"""LLM-backed teaching overlay for validated semantic traces.

The overlay is intentionally read-only with respect to SemanticTrace facts:
LLM output can enrich SceneGraph ``teaching`` and ``interaction`` fields, but
cannot change operations, targets, dependencies, states, code lines, or result.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from algolab.schemas.scene_graph import SceneGraph
from algolab.schemas.semantic_trace import Interaction, SemanticEvent, SemanticTrace, TeachingStep
from algolab.generation.language import english_output_requirement, normalize_output_language


MAX_TEACHING_FRAMES: int | None = 30
RETRY_TEACHING_FRAMES = 3
MAX_STATE_CHARS = 1600
MAX_VALUE_CHARS = 320


TEACHING_SYSTEM_PROMPT = """你是 AlgoLab 的算法教学增强器。

你会收到一个已经通过验证的 SemanticTrace 摘要。trace 是事实来源。
只输出 JSON，不要 markdown，不要解释。

你只能补充每个 step 的 teaching 和 interaction：
- teaching 字段只允许 what/why/formula/invariant/common_mistake/hint。
- interaction 字段只允许 type/prompt/options/answer/explanation/wrong_explanation/option_explanations。
- frames 数组中的每一项只能包含 step、teaching、interaction 三个顶层字段。
- 不要修改、复述或发明 op、targets、deps、state、result、code_line。
- interaction 的答案必须能由当前 frame 的 state、before、after、value、deps、targets、reason、next_summary 或 teaching 直接推出。

teaching 规则：
- 所有收到的 frame 都尽量补 teaching。
- what 说明当前操作，why 说明为什么这样做。
- 若 frame 有 deps/before/after/value/state_diff，优先写 formula 或 invariant。
- hint 必须引导学生看 targets/deps/state 中的具体对象或变量，不要只写“请观察当前步骤”。
- common_mistake 不能写成泛泛提醒，必须指出初学者在本步最可能混淆的对象、边界、依赖、更新方向或答案含义。
- 字段应短而具体；不要为了变短省略关键变量、依赖对象、状态变化或转移依据。

interaction 规则：
- 不要求每个 frame 都有 interaction。
- interaction 是预测检查点，学生应该先预测当前或下一步状态，再查看反馈。
- 关键学习帧必须优先生成 interaction，除非无法从当前 frame 事实推出唯一答案。
- 关键学习帧包括：
  1. key_learning_frame=true 的帧。
  2. role 是 answer 的帧。
  3. op 是 compare、set、move、push、pop、link、unlink 的帧。
  4. 有 deps 的帧。
  5. 有 before/after/state_diff/value 的状态转移帧。
  6. targets 指向 answer、ans、result、dp、dist、low、dfn、parent、stack、queue、window、mid、left、right 的帧。
  7. reason 表示分支选择、边界移动、松弛、转移、入队、出队、更新答案的帧。
- 如果关键学习帧数量 <= 8，关键学习帧尽量全部生成 interaction。
- 如果关键学习帧数量 > 8，至少选择 8 个最有教学价值的关键学习帧生成 interaction。
- 覆盖必须包含：首个关键转移帧、至少一个分支/比较帧、至少一个 deps 依赖帧、答案帧。
- 答案帧也必须优先生成 checkpoint，可以让学生预测最终 answer/result，或判断此后是否还会更新状态。
- 非关键帧、纯 enter/exit、纯说明帧、重复机械帧可以填 null。
- 不要为了提高数量生成无意义问题。

interaction 类型选择：
- choice：用于“下一步会选哪个 / 为什么移动哪边 / 哪个依赖来源正确”。
- input：用于“当前 dp/dist/answer/mid/low/dfn 变成几”这类确定值。
- judge：用于“这个说法是否正确 / 这个不变量是否仍成立”。

interaction 写法：
- 每个 frame 最多补一个 interaction。
- choice 最多 2 个 options。
- choice 的 answer 必须是 options 中的某一项原文，不要输出数字下标。
- judge 的 answer 必须输出 true/false 或 “正确”/“错误”；不要输出“是/否”、选项编号或解释句。
- prompt 要具体，优先 20-45 个汉字；复杂步骤允许更长。
- explanation 必须说明依据，优先 30-70 个汉字；复杂转移允许更长。
- wrong_explanation 必须解释为什么错，并明确指出错因来自误读 targets/deps/state、更新方向、边界条件、公式依赖或答案含义中的哪一类。
- option_explanations 优先覆盖每个错误选项；如果预算不足，至少覆盖最容易误选的错误选项。
- 不要为了变短省略关键变量、依赖对象、状态变化或转移依据。
- 如果不能从当前 frame 事实推出唯一答案，interaction 填 null。

输出预算规则：
- 优先压缩文字，不要丢掉关键 interaction。
- 如果预算不足，至少返回所有带 interaction 的关键帧，以及首帧和答案帧。
- 必须保证 JSON 完整闭合。

必须严格按这个格式输出：
{"frames":[{"step":0,"teaching":{"what":"...","why":"..."},"interaction":null}]}
"""

TEACHING_SYSTEM_PROMPT_EN = english_output_requirement() + "\n\n" + TEACHING_SYSTEM_PROMPT


class TeachingOverlayFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=0)
    teaching: TeachingStep | None = None
    interaction: Interaction | None = None


class TeachingOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frames: list[TeachingOverlayFrame] = Field(default_factory=list)


def select_teaching_events(trace: SemanticTrace, *, max_frames: int | None = MAX_TEACHING_FRAMES) -> list[SemanticEvent]:
    """Select a bounded set of high-value events for LLM teaching context."""

    if max_frames is None:
        return list(trace.events)
    if max_frames <= 0:
        return []
    if max_frames >= len(trace.events):
        return list(trace.events)
    scored = [(_event_score(trace, event), event.step, event) for event in trace.events]
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected_steps = {event.step for _score, _step, event in scored[:max_frames]}
    return [event for event in trace.events if event.step in selected_steps]


def build_trace_digest(
    trace: SemanticTrace,
    *,
    problem: str = "",
    code: str = "",
    max_frames: int | None = MAX_TEACHING_FRAMES,
) -> dict[str, Any]:
    """Build a compact prompt payload from a full trace."""

    selected = select_teaching_events(trace, max_frames=max_frames)
    frames: list[dict[str, Any]] = []
    for event in selected:
        prev_event = trace.events[event.step - 1] if event.step > 0 else None
        next_event = trace.events[event.step + 1] if event.step + 1 < len(trace.events) else None
        previous_state = prev_event.state if prev_event is not None else {}
        key_learning_reasons = key_learning_reasons_for_event(event)
        frames.append(
            {
                "step": event.step,
                "op": event.op.value,
                "targets": [target.id for target in event.targets],
                "deps": [dep.id for dep in event.deps],
                "role": event.role,
                "reason": event.reason,
                "value": _compact_value(event.value),
                "before": _compact_value(event.before),
                "after": _compact_value(event.after),
                "code_line": event.code_line,
                "state": _compact_value(event.state, max_chars=MAX_STATE_CHARS),
                "state_diff": _state_diff(previous_state, event.state),
                "prev_summary": _event_summary(prev_event),
                "next_summary": _event_summary(next_event),
                "key_learning_frame": bool(key_learning_reasons),
                "key_learning_reasons": key_learning_reasons,
            }
        )
    return {
        "problem": problem,
        "algorithm": trace.algorithm,
        "input_data": _compact_value(trace.input_data, max_chars=MAX_STATE_CHARS),
        "result": _compact_value(trace.result),
        "pseudocode": list(trace.pseudocode),
        "code": code,
        "trace_summary": {
            "total_events": len(trace.events),
            "selected_events": [event.step for event in selected],
        },
        "frames": frames,
    }


def generate_teaching_overlay(
    trace: SemanticTrace,
    *,
    problem: str = "",
    code: str = "",
    max_frames: int | None = MAX_TEACHING_FRAMES,
    chat_fn: Callable[..., dict[str, Any]] | None = None,
    language: str = "zh",
) -> TeachingOverlay:
    """Call the configured LLM and validate the strict teaching overlay schema."""

    if chat_fn is None:
        from llm_client import chat_json

        chat_fn = chat_json
    digest = build_trace_digest(trace, problem=problem, code=code, max_frames=max_frames)
    system_prompt = TEACHING_SYSTEM_PROMPT_EN if normalize_output_language(language) == "en" else TEACHING_SYSTEM_PROMPT
    raw = chat_fn(
        system_prompt,
        json.dumps(digest, ensure_ascii=False, separators=(",", ":")),
        kind="teaching",
    )
    return _overlay_from_raw(raw)


def apply_teaching_overlay(scene: SceneGraph, overlay: TeachingOverlay | dict[str, Any]) -> list[str]:
    """Apply a validated teaching overlay to a SceneGraph in place."""

    warnings: list[str] = []
    try:
        parsed = overlay if isinstance(overlay, TeachingOverlay) else _overlay_from_raw(overlay)
    except ValidationError as exc:
        return [f"teaching overlay schema invalid: {exc}"]

    frames_by_step = {frame.step: frame for frame in scene.frames}
    for item in parsed.frames:
        frame = frames_by_step.get(item.step)
        if frame is None:
            warnings.append(f"teaching overlay step not found: {item.step}")
            continue
        if item.teaching is not None:
            merged = dict(frame.teaching or {})
            for key, value in item.teaching.model_dump().items():
                if str(value or "").strip():
                    merged[key] = value
            frame.teaching = merged
        if item.interaction is not None and item.interaction.prompt.strip():
            if item.interaction.type == "choice" and not item.interaction.options:
                warnings.append(f"teaching overlay step {item.step} choice interaction missing options")
            else:
                frame.interaction = item.interaction.model_dump()
    return warnings


def enrich_scene_teaching(
    scene: SceneGraph,
    trace: SemanticTrace,
    *,
    problem: str = "",
    code: str = "",
    enabled: bool = True,
    max_frames: int | None = MAX_TEACHING_FRAMES,
    chat_fn: Callable[..., dict[str, Any]] | None = None,
    language: str = "zh",
) -> list[str]:
    """Best-effort SceneGraph teaching enrichment.

    Returns warnings instead of raising so the core artifact pipeline remains
    governed by trace/process/scene validation.
    """

    if not enabled:
        return []
    attempts = _teaching_attempt_frame_counts(max_frames)
    failures: list[str] = []
    for attempt_frames in attempts:
        try:
            overlay = generate_teaching_overlay(
                trace,
                problem=problem,
                code=code,
                max_frames=attempt_frames,
                chat_fn=chat_fn,
                language=language,
            )
            return apply_teaching_overlay(scene, overlay)
        except Exception as exc:  # pragma: no cover - exercised by integration callers.
            frame_label = "all" if attempt_frames is None else str(attempt_frames)
            failures.append(f"{frame_label} frames: {type(exc).__name__}: {exc}")
    return ["teaching enrichment skipped: " + " | ".join(failures)]


def compute_interaction_coverage(trace: SemanticTrace, scene: SceneGraph) -> dict[str, Any]:
    """Summarize whether high-value learning frames received interactions."""

    frame_by_step = {frame.step: frame for frame in scene.frames}
    total_frames = len(scene.frames)
    interaction_steps = {
        step
        for step, frame in frame_by_step.items()
        if isinstance(frame.interaction, dict) and str(frame.interaction.get("prompt") or "").strip()
    }
    key_learning_steps = [event.step for event in trace.events if key_learning_reasons_for_event(event)]
    key_learning_interaction_steps = [step for step in key_learning_steps if step in interaction_steps]
    deps_steps = [event.step for event in trace.events if event.deps]
    deps_interaction_steps = [step for step in deps_steps if step in interaction_steps]
    answer_steps = [event.step for event in trace.events if _is_answer_event(event)]
    return {
        "total_frames": total_frames,
        "interaction_frames": len(interaction_steps),
        "interaction_rate": _safe_rate(len(interaction_steps), total_frames),
        "key_learning_frames": len(key_learning_steps),
        "key_learning_interaction_frames": len(key_learning_interaction_steps),
        "key_learning_interaction_rate": _safe_rate(len(key_learning_interaction_steps), len(key_learning_steps)),
        "deps_frames": len(deps_steps),
        "deps_interaction_frames": len(deps_interaction_steps),
        "deps_frame_interaction_rate": _safe_rate(len(deps_interaction_steps), len(deps_steps)),
        "answer_frames": len(answer_steps),
        "answer_frame_interaction_present": bool(answer_steps) and any(step in interaction_steps for step in answer_steps),
        "missing_key_learning_steps": [step for step in key_learning_steps if step not in interaction_steps],
        "interaction_steps": sorted(interaction_steps),
        "key_learning_steps": key_learning_steps,
    }


def validate_teaching_contract(
    trace: SemanticTrace,
    scene: SceneGraph,
    *,
    min_key_learning_interactions: int = 3,
    max_key_learning_interactions: int = 8,
) -> tuple[list[str], list[str]]:
    """Validate the pedagogical layer without changing trace or scene facts.

    The contract is intentionally warning-oriented: algorithm correctness still
    comes from solve/trace/verifier gates, while these checks make missing or
    weak learning interventions visible to strict benchmark runs.
    """

    warnings: list[str] = []
    checks: list[str] = []
    frame_by_step = {frame.step: frame for frame in scene.frames}

    for event in trace.events:
        reasons = key_learning_reasons_for_event(event)
        if not reasons:
            continue
        frame = frame_by_step.get(event.step)
        if frame is None:
            warnings.append(f"teaching_contract step {event.step}: frame missing")
            continue
        teaching = frame.teaching if isinstance(frame.teaching, dict) else {}
        interaction = frame.interaction if isinstance(frame.interaction, dict) else None
        if not _teaching_has_core_explanation(teaching):
            warnings.append(f"teaching_contract step {event.step}: key learning frame 缺少 teaching.what/why")
        if _needs_rule_or_hint(event, reasons) and not _teaching_has_rule_or_hint(teaching):
            warnings.append(f"teaching_contract step {event.step}: key learning frame 缺少 formula/invariant/hint")
        if interaction is not None:
            warnings.extend(_validate_interaction_contract(event.step, interaction, teaching))

    coverage = compute_interaction_coverage(trace, scene)
    checks.append(
        "teaching_contract: key_learning_interaction_rate="
        f"{coverage['key_learning_interaction_rate']:.3f} "
        f"({coverage['key_learning_interaction_frames']}/{coverage['key_learning_frames']})"
    )
    checks.append(
        "teaching_contract: interaction_frames="
        f"{coverage['interaction_frames']}/{coverage['total_frames']}"
    )
    required_key_interactions = _required_key_learning_interactions(
        coverage["key_learning_frames"],
        floor=min_key_learning_interactions,
        cap=max_key_learning_interactions,
    )
    checks.append(
        "teaching_contract: required_key_learning_interactions="
        f"{required_key_interactions}"
    )
    if coverage["key_learning_interaction_frames"] < required_key_interactions:
        warnings.append(
            "teaching_contract: key learning prediction checkpoint 覆盖不足 "
            f"{coverage['key_learning_interaction_frames']}/{required_key_interactions} "
            f"(key_learning_frames={coverage['key_learning_frames']})"
        )
    if coverage["answer_frames"] and not coverage["answer_frame_interaction_present"]:
        warnings.append("teaching_contract: answer frame 缺少 prediction checkpoint")
    if coverage["deps_frames"] and coverage["deps_interaction_frames"] == 0:
        warnings.append("teaching_contract: deps frame 缺少 prediction checkpoint")
    return warnings, checks


def key_learning_reasons_for_event(event: SemanticEvent) -> list[str]:
    """Return reasons that make a trace event worth an interaction prompt."""

    reasons: list[str] = []
    if _is_answer_event(event):
        reasons.append("answer")
    if event.op.value in {"compare", "set", "move", "push", "pop", "link", "unlink"}:
        reasons.append("operation")
    if event.deps:
        reasons.append("deps")
    if event.before is not None or event.after is not None or event.value is not None:
        reasons.append("state_transition")
    if any(_interaction_target(target.id) for target in event.targets):
        reasons.append("important_target")
    if _reason_implies_decision(event.reason):
        reasons.append("decision_reason")
    return reasons


def _teaching_has_core_explanation(teaching: dict[str, Any]) -> bool:
    return bool(str(teaching.get("what") or "").strip() and str(teaching.get("why") or "").strip())


def _teaching_has_rule_or_hint(teaching: dict[str, Any]) -> bool:
    return any(str(teaching.get(key) or "").strip() for key in ("formula", "invariant", "hint"))


def _needs_rule_or_hint(event: SemanticEvent, reasons: list[str]) -> bool:
    return bool(event.deps or {"state_transition", "important_target", "decision_reason"} & set(reasons))


def _validate_interaction_contract(step: int, interaction: dict[str, Any], teaching: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    kind = str(interaction.get("type") or "choice")
    prompt = str(interaction.get("prompt") or "").strip()
    if kind not in {"choice", "input", "judge"}:
        warnings.append(f"teaching_contract step {step}: unknown interaction type {kind}")
    if not prompt:
        warnings.append(f"teaching_contract step {step}: interaction 缺少 prompt")
    if not _interaction_has_answer(interaction):
        warnings.append(f"teaching_contract step {step}: interaction 缺少 answer")
    if not str(interaction.get("explanation") or "").strip():
        warnings.append(f"teaching_contract step {step}: interaction 缺少正确反馈 explanation")
    if kind == "choice":
        warnings.extend(_validate_choice_interaction(step, interaction, teaching))
    elif kind == "input":
        if not _has_wrong_feedback(interaction, teaching):
            warnings.append(f"teaching_contract step {step}: input checkpoint 缺少错误反馈")
    elif kind == "judge":
        answer = interaction.get("answer")
        if not _is_bool_like_answer(answer):
            warnings.append(f"teaching_contract step {step}: judge answer 必须是布尔值或正确/错误")
        if not _has_wrong_feedback(interaction, teaching):
            warnings.append(f"teaching_contract step {step}: judge checkpoint 缺少错误反馈")
    return warnings


def _required_key_learning_interactions(key_learning_frames: int, *, floor: int, cap: int) -> int:
    if key_learning_frames <= 0:
        return 0
    return min(key_learning_frames, max(floor, min(key_learning_frames, cap)))


def _validate_choice_interaction(step: int, interaction: dict[str, Any], teaching: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    options = interaction.get("options")
    option_values = [str(option) for option in options] if isinstance(options, list) else []
    answer = str(interaction.get("answer") or "")
    if len(option_values) < 2:
        warnings.append(f"teaching_contract step {step}: choice 至少需要 2 个 options")
    if option_values and answer not in option_values:
        warnings.append(f"teaching_contract step {step}: choice answer 必须来自 options")
    if not _has_wrong_feedback(interaction, teaching, options=option_values, answer=answer):
        warnings.append(f"teaching_contract step {step}: choice checkpoint 缺少错误反馈")
    return warnings


def _interaction_has_answer(interaction: dict[str, Any]) -> bool:
    if "answer" not in interaction:
        return False
    value = interaction.get("answer")
    if value is None:
        return False
    return not (isinstance(value, str) and not value.strip())


def _has_wrong_feedback(
    interaction: dict[str, Any],
    teaching: dict[str, Any],
    *,
    options: list[str] | None = None,
    answer: str = "",
) -> bool:
    if str(interaction.get("wrong_explanation") or "").strip():
        return True
    if str(teaching.get("common_mistake") or "").strip():
        return True
    explanations = interaction.get("option_explanations")
    if not isinstance(explanations, dict):
        return False
    if not options:
        return any(str(value or "").strip() for value in explanations.values())
    wrong_options = [option for option in options if option != answer]
    return any(str(explanations.get(option) or "").strip() for option in wrong_options)


def _is_bool_like_answer(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    return str(value).strip().lower() in {"true", "false", "正确", "错误", "对", "错"}


def _teaching_attempt_frame_counts(max_frames: int | None) -> list[int | None]:
    if max_frames is None:
        return [None, RETRY_TEACHING_FRAMES]
    if max_frames <= 0:
        return [max_frames]
    primary = max_frames
    retry = min(RETRY_TEACHING_FRAMES, max(1, primary - 1))
    if retry == primary:
        return [primary]
    return [primary, retry]


def _event_score(trace: SemanticTrace, event: SemanticEvent) -> int:
    score = 0
    if event.step == 0:
        score += 10_000
    if event.step == len(trace.events) - 1:
        score += 9_000
    target_ids = [target.id for target in event.targets]
    if event.role == "answer" or any(_answer_like(target) for target in target_ids) or "answer" in event.state:
        score += 8_000
    if any(_important_target(target) for target in target_ids):
        score += 2_000
    if event.before is not None or event.after is not None:
        score += 1_500
    if event.deps:
        score += 900
    if event.op.value in {"set", "move", "compare", "link", "unlink", "push", "pop"}:
        score += 500
    if event.reason:
        score += 100
    return score


def _overlay_from_raw(raw: Any) -> TeachingOverlay:
    return TeachingOverlay.model_validate(_sanitize_overlay_payload(raw))


def _sanitize_overlay_payload(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return raw
    frames = raw.get("frames")
    if not isinstance(frames, list):
        return {"frames": []}
    cleaned_frames: list[dict[str, Any]] = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        cleaned: dict[str, Any] = {"step": frame.get("step")}
        teaching = _sanitize_teaching(frame.get("teaching"))
        if teaching is not None:
            cleaned["teaching"] = teaching
        interaction = _sanitize_interaction(frame.get("interaction"))
        if interaction is not None:
            cleaned["interaction"] = interaction
        cleaned_frames.append(cleaned)
    return {"frames": cleaned_frames}


def _sanitize_teaching(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    allowed = {"what", "why", "formula", "invariant", "common_mistake", "hint"}
    return {key: raw[key] for key in allowed if key in raw}


def _sanitize_interaction(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    allowed = {
        "type",
        "prompt",
        "options",
        "answer",
        "explanation",
        "wrong_explanation",
        "option_explanations",
    }
    cleaned = {key: raw[key] for key in allowed if key in raw}
    if "options" in cleaned and not isinstance(cleaned["options"], list):
        cleaned["options"] = []
    if isinstance(cleaned.get("options"), list):
        cleaned["options"] = [
            json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            if isinstance(item, (dict, list))
            else str(item)
            for item in cleaned["options"]
        ]
    interaction_type = str(cleaned.get("type") or "").strip().lower()
    if interaction_type not in {"choice", "input", "judge"}:
        if isinstance(cleaned.get("answer"), bool):
            interaction_type = "judge"
        elif len(cleaned.get("options") or []) >= 2:
            interaction_type = "choice"
        else:
            interaction_type = "input"
        cleaned["type"] = interaction_type
    if interaction_type == "choice" and len(cleaned.get("options") or []) < 2:
        cleaned["type"] = "input"
        cleaned.pop("options", None)
    if cleaned.get("type") == "choice":
        _normalize_choice_answer(cleaned)
    if cleaned.get("type") == "judge":
        _normalize_judge_answer(cleaned)
    if "option_explanations" in cleaned and not isinstance(cleaned["option_explanations"], dict):
        cleaned["option_explanations"] = {}
    elif isinstance(cleaned.get("option_explanations"), dict):
        cleaned["option_explanations"] = {
            str(key): str(value) for key, value in cleaned["option_explanations"].items()
        }
    return cleaned


def _normalize_choice_answer(interaction: dict[str, Any]) -> None:
    options = interaction.get("options")
    answer = interaction.get("answer")
    if not isinstance(options, list) or not options:
        return
    if not isinstance(answer, int) or isinstance(answer, bool):
        return
    if any(answer == option or str(answer) == str(option) for option in options):
        return
    if 0 <= answer < len(options):
        interaction["answer"] = options[answer]


def _normalize_judge_answer(interaction: dict[str, Any]) -> None:
    answer = interaction.get("answer")
    if isinstance(answer, bool):
        return
    text = str(answer).strip().lower()
    true_values = {"true", "正确", "对", "是", "yes", "y", "对的", "正确的"}
    false_values = {"false", "错误", "错", "否", "no", "n", "错的", "错误的", "不正确"}
    if text in true_values:
        interaction["answer"] = True
    elif text in false_values:
        interaction["answer"] = False


def _answer_like(target: str) -> bool:
    raw = str(target)
    return raw in {"answer", "ans", "result"} or raw.startswith(("answer[", "ans[", "result["))


def _is_answer_event(event: SemanticEvent) -> bool:
    target_ids = [target.id for target in event.targets]
    return event.role == "answer" or any(_answer_like(target) for target in target_ids) or "answer" in event.state


def _important_target(target: str) -> bool:
    raw = str(target)
    prefixes = ("answer", "ans", "result", "dist", "dp", "parent", "visited", "path")
    return raw in prefixes or raw.startswith(tuple(f"{prefix}[" for prefix in prefixes))


def _interaction_target(target: str) -> bool:
    raw = str(target)
    prefixes = (
        "answer",
        "ans",
        "result",
        "dp",
        "dist",
        "low",
        "dfn",
        "parent",
        "stack",
        "queue",
        "window",
        "mid",
        "left",
        "right",
    )
    return raw in prefixes or raw.startswith(tuple(f"{prefix}[" for prefix in prefixes))


def _reason_implies_decision(reason: str) -> bool:
    text = str(reason or "")
    keywords = (
        "分支",
        "选择",
        "边界",
        "移动",
        "松弛",
        "转移",
        "入队",
        "出队",
        "更新答案",
        "淘汰",
        "收缩",
        "扩张",
        "比较",
    )
    return any(keyword in text for keyword in keywords)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _event_summary(event: SemanticEvent | None) -> str:
    if event is None:
        return ""
    targets = ", ".join(target.id for target in event.targets[:3])
    parts = [f"step {event.step}", event.op.value]
    if targets:
        parts.append(targets)
    if event.reason:
        parts.append(event.reason)
    return " | ".join(parts)


def _state_diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    keys = sorted(set(previous) | set(current))
    for key in keys:
        before = previous.get(key, None)
        after = current.get(key, None)
        if _stable_json(before) == _stable_json(after):
            continue
        result[key] = {
            "before": _compact_value(before),
            "after": _compact_value(after),
        }
    return result


def _compact_value(value: Any, *, max_chars: int = MAX_VALUE_CHARS) -> Any:
    copied = deepcopy(value)
    text = _stable_json(copied)
    if len(text) <= max_chars:
        return copied
    if isinstance(copied, dict):
        compact: dict[str, Any] = {}
        for index, key in enumerate(sorted(copied, key=str)):
            if index >= 8:
                compact["..."] = f"{len(copied) - index} more keys"
                break
            compact[str(key)] = _compact_value(copied[key], max_chars=max(80, max_chars // 4))
        return compact
    if isinstance(copied, list):
        head = [_compact_value(item, max_chars=max(80, max_chars // 6)) for item in copied[:8]]
        if len(copied) > 8:
            head.append(f"... {len(copied) - 8} more items")
        return head
    return text[: max_chars - 20] + "...(truncated)"


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    except TypeError:
        return str(value)
