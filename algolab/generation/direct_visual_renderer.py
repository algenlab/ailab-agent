"""LLM Direct Visual Renderer generation utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from algolab.renderer.creative_direct import (
    CreativeDirectHtmlError,
    extract_html,
    extract_stage_assets,
    render_direct_visual_html,
    render_direct_visual_stage_shell_html,
    sanitize_direct_visual_html,
    sanitize_direct_visual_stage_assets,
)
from algolab.schemas.scene_graph import SceneFrame
from algolab.schemas.validation import BuildArtifact


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "direct_visual_renderer_system.txt"
STAGE_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "direct_visual_stage_system.txt"
REPAIR_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "direct_visual_repair_system.txt"
STAGE_REPAIR_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "direct_visual_stage_repair_system.txt"
MAX_SELECTED_FRAMES = 4
MAX_STATE_KEYS = 30
MAX_VALUE_CHARS = 900
MAX_REPAIR_HTML_CHARS = 60000


@dataclass
class DirectVisualRenderResult:
    creative_ok: bool
    html: str = ""
    raw_output: str = ""
    extracted_html: str = ""
    prompt: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    model_calls: list[dict[str, Any]] = field(default_factory=list)

    def report(self) -> dict[str, Any]:
        return {
            "creative_ok": self.creative_ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "model_calls": list(self.model_calls),
        }


ChatTextFn = Callable[[str, str], str | dict[str, Any]]


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def load_stage_system_prompt() -> str:
    return STAGE_PROMPT_PATH.read_text(encoding="utf-8")


def load_repair_system_prompt() -> str:
    return REPAIR_PROMPT_PATH.read_text(encoding="utf-8")


def load_stage_repair_system_prompt() -> str:
    return STAGE_REPAIR_PROMPT_PATH.read_text(encoding="utf-8")


def build_direct_visual_prompt(
    artifact: BuildArtifact,
    *,
    problem_description: str = "",
    max_selected_frames: int = MAX_SELECTED_FRAMES,
) -> str:
    """Build a compact prompt from a verified artifact."""

    digest = build_artifact_digest(
        artifact,
        problem_description=problem_description,
        max_selected_frames=max_selected_frames,
    )
    return "\n".join(
        [
            "Problem:",
            str(digest["problem"]),
            "",
            "Input JSON:",
            json.dumps(digest["input_data"], ensure_ascii=False),
            "",
            "Verified result JSON:",
            json.dumps(digest["result"], ensure_ascii=False),
            "",
            "Algorithm:",
            str(digest["algorithm"]),
            "",
            "Pseudocode:",
            json.dumps(digest["pseudocode"], ensure_ascii=False),
            "",
            "Release gate:",
            json.dumps(digest["release_gate"], ensure_ascii=False),
            "",
            "State key summary:",
            json.dumps(digest["state_key_summary"], ensure_ascii=False),
            "",
            "Trace summary:",
            json.dumps(digest["trace_summary"], ensure_ascii=False),
            "",
            "Selected frame examples:",
            json.dumps(digest["selected_frames"], ensure_ascii=False),
            "",
            "Runtime contract:",
            "最终 HTML 会被系统注入 <script type=\"application/json\" id=\"algolab-artifact\">。"
            "你的 JS 必须读取该节点，优先使用 artifact.frames 渲染所有帧，使用 artifact.result 显示验证答案。"
            "题目输入必须从 artifact.input_data 或 artifact.input 读取。"
            "artifact.scene 是首个 SceneGraph 的便捷别名，不是题目输入；不要把 artifact.scene 当作 tree/list/graph input。"
            "不要假设 artifact.scenes 是数组。"
            "不要在 prompt 中复制完整 artifact；运行时完整 artifact 会存在。",
            "",
            "Now generate a complete, self-contained, offline HTML creative visualization.",
        ]
    )


def build_direct_visual_stage_prompt(
    artifact: BuildArtifact,
    *,
    problem_description: str = "",
    max_selected_frames: int = MAX_SELECTED_FRAMES,
) -> str:
    """Build a prompt for stage-only generation inside the deterministic Creative Shell."""

    digest = build_artifact_digest(
        artifact,
        problem_description=problem_description,
        max_selected_frames=max_selected_frames,
    )
    return "\n".join(
        [
            "Problem:",
            str(digest["problem"]),
            "",
            "Input JSON:",
            json.dumps(digest["input_data"], ensure_ascii=False),
            "",
            "Verified result JSON:",
            json.dumps(digest["result"], ensure_ascii=False),
            "",
            "Algorithm:",
            str(digest["algorithm"]),
            "",
            "Pseudocode:",
            json.dumps(digest["pseudocode"], ensure_ascii=False),
            "",
            "Release gate:",
            json.dumps(digest["release_gate"], ensure_ascii=False),
            "",
            "State key summary:",
            json.dumps(digest["state_key_summary"], ensure_ascii=False),
            "",
            "Trace summary:",
            json.dumps(digest["trace_summary"], ensure_ascii=False),
            "",
            "Selected frame examples:",
            json.dumps(digest["selected_frames"], ensure_ascii=False),
            "",
            "Scenario grounding requirement:",
            "Problem is a visual design spec, not only a title. "
            "If it contains a concrete application story, the main stage must visibly instantiate that story. "
            "Use at least three domain-specific objects/labels/actions from Problem inside ctx.host and mark core scene objects with data-scenario-role. "
            "Generic algorithm visuals are invalid if they only show arrays/tables/graphs with variable names. "
            "Map the algorithm structure into the story: warehouse grids become shelf aisles with a robot and endpoints; "
            "temperature arrays become greenhouse forecast/ventilation views; graph shortest paths become city roads with rescue dispatch; "
            "interval bars become meeting-room booking windows; two-sum arrays become picking bins/order fulfillment slots. "
            "Keep trace/state/result semantics unchanged.",
            "",
            "Creative Shell contract:",
            "系统已经生成完整页面外壳。你只输出 stage 资产，不输出完整 HTML。"
            "Shell 会负责代码/伪代码、讲解、证据、交互、timeline、答案和切帧控件。"
            "你的 renderCreativeStage(ctx) 只向 ctx.host 绘制主视图。"
            "运行时完整 artifact 会通过 ctx.artifact/ctx.frames/ctx.frame/ctx.input/ctx.result 传入。"
            "题目输入只读 ctx.input；验证答案只读 ctx.result。"
            "不要使用 shell 保留 id，不要修改 artifact。",
            "",
            "Now return only the stage assets: <style>, <template>, and <script> with window.renderCreativeStage.",
        ]
    )


def build_direct_visual_repair_prompt(
    artifact: BuildArtifact,
    *,
    broken_html: str,
    failure_report: dict[str, Any],
    problem_description: str = "",
    max_html_chars: int = MAX_REPAIR_HTML_CHARS,
) -> str:
    digest = build_artifact_digest(artifact, problem_description=problem_description)
    return "\n".join(
        [
            "Problem:",
            str(digest["problem"]),
            "",
            "Input JSON:",
            json.dumps(digest["input_data"], ensure_ascii=False),
            "",
            "Verified result JSON:",
            json.dumps(digest["result"], ensure_ascii=False),
            "",
            "Trace summary:",
            json.dumps(digest["trace_summary"], ensure_ascii=False),
            "",
            "State key summary:",
            json.dumps(digest["state_key_summary"], ensure_ascii=False),
            "",
            "Selected frame examples:",
            json.dumps(digest["selected_frames"], ensure_ascii=False),
            "",
            "Browser/smoke failure report:",
            json.dumps(_compact_value(failure_report), ensure_ascii=False),
            "",
            "Runtime contract reminder:",
            "最终 HTML 会被系统注入 <script type=\"application/json\" id=\"algolab-artifact\">。"
            "题目输入只能从 artifact.input_data 或 artifact.input 读取。"
            "artifact.frames 是帧列表，artifact.result 是验证答案。"
            "artifact.scene 是 SceneGraph，不是题目输入；不要把 artifact.scene 当作 tree/list/graph input。",
            "",
            "Previous broken HTML:",
            _truncate_text(extract_html(broken_html) or broken_html, max_html_chars),
            "",
            "Now return the repaired complete self-contained HTML only.",
        ]
    )


def build_direct_visual_stage_repair_prompt(
    artifact: BuildArtifact,
    *,
    broken_stage: str,
    failure_report: dict[str, Any],
    problem_description: str = "",
    max_stage_chars: int = MAX_REPAIR_HTML_CHARS,
) -> str:
    digest = build_artifact_digest(artifact, problem_description=problem_description)
    assets = extract_stage_assets(broken_stage)
    previous_stage = assets.get("source") or broken_stage
    return "\n".join(
        [
            "Problem:",
            str(digest["problem"]),
            "",
            "Input JSON:",
            json.dumps(digest["input_data"], ensure_ascii=False),
            "",
            "Verified result JSON:",
            json.dumps(digest["result"], ensure_ascii=False),
            "",
            "Algorithm:",
            str(digest["algorithm"]),
            "",
            "Trace summary:",
            json.dumps(digest["trace_summary"], ensure_ascii=False),
            "",
            "State key summary:",
            json.dumps(digest["state_key_summary"], ensure_ascii=False),
            "",
            "Selected frame examples:",
            json.dumps(digest["selected_frames"], ensure_ascii=False),
            "",
            "Browser layout failure report:",
            json.dumps(_compact_value(failure_report), ensure_ascii=False),
            "",
            "Browser layout repair guidance:",
            "If a highlight/selection/range overlay causes overlap, convert it to a non-blocking outline, halo, underline, side band, or low-opacity layer with pointer-events:none."
            " Do not cover nodes, cells, bars, points, intervals, edges, or text with solid fill."
            "不要用实心填充覆盖节点、格子、柱子或文字。"
            " Give non-blocking overlays semantic class/data-visual names such as range-highlight, current-outline, selection-halo, or active-band; do not use opaque data-visual=\"true\"."
            " Mark background, plot areas, legends, and SVG groups as containers/backdrops, not as data marks."
            " Put labels in a side lane, label lane, legend, caption, or callout area instead of placing them on top of dense geometry."
            " Keep the viewBox/layout skeleton stable across frames; increase padding/margins before shrinking labels."
            " Use separate SVG groups for background, data marks, non-blocking highlights, and labels so the browser audit can distinguish them.",
            "",
            "Creative scenario repair guidance:",
            "If the failure report contains scenario_salience_low or generic_algorithm_visual, rebuild the main stage around the Problem story, not around a generic array/table/graph."
            " Use visible domain objects, labels, and actions from Problem as primary marks inside ctx.host."
            " Mark core story objects with data-scenario-role and keep algorithm state marks readable with data-visual/data-layout-role."
            "Do not change trace/state/result semantics; map the existing algorithm state into the scenario instead.",
            "",
            "Creative Shell repair contract:",
            "系统 shell 负责代码、讲解、交互、答案和 timeline。你只能修主视图 stage。"
            "必须只输出 <style>、可选 <template id=\"creative-stage-template\">、以及定义 window.renderCreativeStage(ctx) 的 <script>。"
            "不要输出完整 HTML，不要修改 artifact，不要重新求解算法，不要生成 shell 面板。"
            "修复重点是消除 browser audit 报告中的 overlap/clipping/text_occlusion。"
            "优先使用 SVG/HTML DOM，关键视觉元素和标签加 data-visual 或 data-layout-role，避免纯 canvas 内部不可审计对象。"
            "使用稳定布局骨架，切帧时重绘目标状态；不要使用复杂位移动画。",
            "",
            "Previous broken stage assets:",
            _truncate_text(previous_stage, max_stage_chars),
            "",
            "Now return only repaired stage assets.",
        ]
    )


def build_artifact_digest(
    artifact: BuildArtifact,
    *,
    problem_description: str = "",
    max_selected_frames: int = MAX_SELECTED_FRAMES,
) -> dict[str, Any]:
    first_variant = artifact.variants[0] if artifact.variants else None
    first_scene = artifact.scenes.get(first_variant.id) if first_variant is not None else None
    frames = list(first_scene.frames) if first_scene is not None else []
    selected_frames = [_frame_digest(frame) for frame in _select_frames(frames, max_selected_frames)]
    return {
        "problem": problem_description or artifact.problem_title,
        "problem_title": artifact.problem_title,
        "input_data": _compact_value(artifact.input_data),
        "result": _compact_value(_artifact_result(artifact)),
        "expected_result": _compact_value(artifact.expected_result),
        "algorithm": first_scene.algorithm if first_scene is not None else "",
        "pseudocode": list(first_scene.pseudocode)[:12] if first_scene is not None else [],
        "release_gate": artifact.validation.release_gate.model_dump(),
        "validation_summary": {
            "errors": artifact.validation.errors[:5],
            "warnings": artifact.validation.warnings[:5],
            "checks": artifact.validation.checks[:8],
        },
        "trace_summary": {
            "variant_count": len(artifact.variants),
            "scene_count": len(artifact.scenes),
            "frame_count": len(frames),
            "selected_steps": [item["step"] for item in selected_frames],
        },
        "state_key_summary": _state_key_summary(frames),
        "selected_frames": selected_frames,
    }


def generate_direct_visual_html(
    artifact: BuildArtifact,
    *,
    problem_description: str = "",
    model: str | None = None,
    chat_fn: ChatTextFn | None = None,
) -> DirectVisualRenderResult:
    """Generate sanitized Creative View HTML from a verified artifact."""

    system_prompt = load_system_prompt()
    user_prompt = build_direct_visual_prompt(artifact, problem_description=problem_description)
    raw_output = ""
    model_calls: list[dict[str, Any]] = []
    try:
        if chat_fn is None:
            from llm_client import chat_text_with_metadata

            response = chat_text_with_metadata(system_prompt, user_prompt, model=model, kind="direct_visual")
            raw_output = str(response.get("content") or "")
            model_calls = list(response.get("model_calls") or [])
        else:
            response = chat_fn(system_prompt, user_prompt)
            if isinstance(response, dict):
                raw_output = str(response.get("content") or "")
                model_calls = list(response.get("model_calls") or [])
            else:
                raw_output = str(response or "")
        extracted = extract_html(raw_output)
        errors = sanitize_direct_visual_html(extracted)
        if errors:
            return DirectVisualRenderResult(
                creative_ok=False,
                raw_output=raw_output,
                extracted_html=extracted,
                prompt=user_prompt,
                errors=errors,
                model_calls=model_calls,
            )
        html = render_direct_visual_html(artifact, extracted)
        return DirectVisualRenderResult(
            creative_ok=True,
            html=html,
            raw_output=raw_output,
            extracted_html=extracted,
            prompt=user_prompt,
            model_calls=model_calls,
        )
    except CreativeDirectHtmlError as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_html(raw_output),
            prompt=user_prompt,
            errors=[str(exc)],
            model_calls=model_calls,
        )
    except Exception as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_html(raw_output),
            prompt=user_prompt,
            errors=[f"{type(exc).__name__}: {exc}"],
            model_calls=model_calls,
        )


def generate_direct_visual_stage_shell_html(
    artifact: BuildArtifact,
    *,
    problem_description: str = "",
    model: str | None = None,
    chat_fn: ChatTextFn | None = None,
) -> DirectVisualRenderResult:
    """Generate a deterministic Creative Shell whose stage is produced by the LLM."""

    system_prompt = load_stage_system_prompt()
    user_prompt = build_direct_visual_stage_prompt(artifact, problem_description=problem_description)
    raw_output = ""
    model_calls: list[dict[str, Any]] = []
    try:
        if chat_fn is None:
            from llm_client import chat_text_with_metadata

            response = chat_text_with_metadata(system_prompt, user_prompt, model=model, kind="direct_visual_stage")
            raw_output = str(response.get("content") or "")
            model_calls = list(response.get("model_calls") or [])
        else:
            response = chat_fn(system_prompt, user_prompt)
            if isinstance(response, dict):
                raw_output = str(response.get("content") or "")
                model_calls = list(response.get("model_calls") or [])
            else:
                raw_output = str(response or "")
        errors = sanitize_direct_visual_stage_assets(raw_output)
        assets = extract_stage_assets(raw_output)
        if errors:
            return DirectVisualRenderResult(
                creative_ok=False,
                raw_output=raw_output,
                extracted_html=assets.get("source", ""),
                prompt=user_prompt,
                errors=errors,
                model_calls=model_calls,
            )
        html = render_direct_visual_stage_shell_html(artifact, raw_output)
        return DirectVisualRenderResult(
            creative_ok=True,
            html=html,
            raw_output=raw_output,
            extracted_html=assets.get("source", ""),
            prompt=user_prompt,
            model_calls=model_calls,
        )
    except CreativeDirectHtmlError as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_stage_assets(raw_output).get("source", ""),
            prompt=user_prompt,
            errors=[str(exc)],
            model_calls=model_calls,
        )
    except Exception as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_stage_assets(raw_output).get("source", ""),
            prompt=user_prompt,
            errors=[f"{type(exc).__name__}: {exc}"],
            model_calls=model_calls,
        )


def repair_direct_visual_html(
    artifact: BuildArtifact,
    *,
    broken_html: str,
    failure_report: dict[str, Any],
    problem_description: str = "",
    model: str | None = None,
    chat_fn: ChatTextFn | None = None,
) -> DirectVisualRenderResult:
    """Repair a generated Creative View HTML page after browser/smoke failures."""

    system_prompt = load_repair_system_prompt()
    user_prompt = build_direct_visual_repair_prompt(
        artifact,
        broken_html=broken_html,
        failure_report=failure_report,
        problem_description=problem_description,
    )
    raw_output = ""
    model_calls: list[dict[str, Any]] = []
    try:
        if chat_fn is None:
            from llm_client import chat_text_with_metadata

            response = chat_text_with_metadata(system_prompt, user_prompt, model=model, kind="direct_visual_repair")
            raw_output = str(response.get("content") or "")
            model_calls = list(response.get("model_calls") or [])
        else:
            response = chat_fn(system_prompt, user_prompt)
            if isinstance(response, dict):
                raw_output = str(response.get("content") or "")
                model_calls = list(response.get("model_calls") or [])
            else:
                raw_output = str(response or "")
        extracted = extract_html(raw_output)
        errors = sanitize_direct_visual_html(extracted)
        if errors:
            return DirectVisualRenderResult(
                creative_ok=False,
                raw_output=raw_output,
                extracted_html=extracted,
                prompt=user_prompt,
                errors=errors,
                model_calls=model_calls,
            )
        html = render_direct_visual_html(artifact, extracted)
        return DirectVisualRenderResult(
            creative_ok=True,
            html=html,
            raw_output=raw_output,
            extracted_html=extracted,
            prompt=user_prompt,
            model_calls=model_calls,
        )
    except CreativeDirectHtmlError as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_html(raw_output),
            prompt=user_prompt,
            errors=[str(exc)],
            model_calls=model_calls,
        )
    except Exception as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_html(raw_output),
            prompt=user_prompt,
            errors=[f"{type(exc).__name__}: {exc}"],
            model_calls=model_calls,
        )


def repair_direct_visual_stage_shell_html(
    artifact: BuildArtifact,
    *,
    broken_stage: str,
    failure_report: dict[str, Any],
    problem_description: str = "",
    model: str | None = None,
    chat_fn: ChatTextFn | None = None,
) -> DirectVisualRenderResult:
    """Repair only the LLM stage assets and rewrap them in the deterministic shell."""

    system_prompt = load_stage_repair_system_prompt()
    user_prompt = build_direct_visual_stage_repair_prompt(
        artifact,
        broken_stage=broken_stage,
        failure_report=failure_report,
        problem_description=problem_description,
    )
    raw_output = ""
    model_calls: list[dict[str, Any]] = []
    try:
        if chat_fn is None:
            from llm_client import chat_text_with_metadata

            response = chat_text_with_metadata(system_prompt, user_prompt, model=model, kind="direct_visual_stage_repair")
            raw_output = str(response.get("content") or "")
            model_calls = list(response.get("model_calls") or [])
        else:
            response = chat_fn(system_prompt, user_prompt)
            if isinstance(response, dict):
                raw_output = str(response.get("content") or "")
                model_calls = list(response.get("model_calls") or [])
            else:
                raw_output = str(response or "")
        errors = sanitize_direct_visual_stage_assets(raw_output)
        assets = extract_stage_assets(raw_output)
        if errors:
            return DirectVisualRenderResult(
                creative_ok=False,
                raw_output=raw_output,
                extracted_html=assets.get("source", ""),
                prompt=user_prompt,
                errors=errors,
                model_calls=model_calls,
            )
        html = render_direct_visual_stage_shell_html(artifact, raw_output)
        return DirectVisualRenderResult(
            creative_ok=True,
            html=html,
            raw_output=raw_output,
            extracted_html=assets.get("source", ""),
            prompt=user_prompt,
            model_calls=model_calls,
        )
    except CreativeDirectHtmlError as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_stage_assets(raw_output).get("source", ""),
            prompt=user_prompt,
            errors=[str(exc)],
            model_calls=model_calls,
        )
    except Exception as exc:
        return DirectVisualRenderResult(
            creative_ok=False,
            raw_output=raw_output,
            extracted_html=extract_stage_assets(raw_output).get("source", ""),
            prompt=user_prompt,
            errors=[f"{type(exc).__name__}: {exc}"],
            model_calls=model_calls,
        )


def _select_frames(frames: list[SceneFrame], limit: int) -> list[SceneFrame]:
    if limit <= 0 or not frames:
        return []
    candidates = {0, len(frames) // 2, len(frames) - 1}
    for frame in frames:
        text = " ".join(
            [
                frame.title,
                frame.description,
                str(frame.operation),
                json.dumps(frame.evidence.get("targets", []), ensure_ascii=False),
                json.dumps(frame.state.get("answer", ""), ensure_ascii=False),
                json.dumps(frame.state.get("result", ""), ensure_ascii=False),
            ]
        ).lower()
        if any(token in text for token in ("answer", "result", "答案", "返回")):
            candidates.add(frame.step)
        if frame.evidence.get("changes"):
            candidates.add(frame.step)
        if len(frame.evidence.get("targets") or []) + len(frame.evidence.get("deps") or []) >= 2:
            candidates.add(frame.step)
        if len(candidates) >= limit:
            break
    selected = [frames[index] for index in sorted(candidates) if 0 <= index < len(frames)]
    return selected[:limit]


def _artifact_result(artifact: BuildArtifact) -> Any:
    if artifact.variants:
        return artifact.variants[0].result
    if artifact.scenes:
        first_scene = next(iter(artifact.scenes.values()))
        return first_scene.result
    return artifact.verifier_result if artifact.verifier_result is not None else artifact.expected_result


def _frame_digest(frame: SceneFrame) -> dict[str, Any]:
    return {
        "step": frame.step,
        "title": frame.title,
        "operation": frame.operation,
        "description": frame.description,
        "code_line": frame.code_line,
        "state": _compact_value(frame.state),
        "evidence": _compact_value(_compact_evidence(frame.evidence)),
        "teaching": _compact_value(frame.teaching or {}),
        "interaction": _compact_value(frame.interaction or {}),
    }


def _compact_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    timeline = evidence.get("timeline") if isinstance(evidence.get("timeline"), dict) else {}
    return {
        "targets": evidence.get("targets") or [],
        "deps": evidence.get("deps") or [],
        "role": evidence.get("role") or "",
        "value": evidence.get("value"),
        "before": evidence.get("before"),
        "after": evidence.get("after"),
        "reason": evidence.get("reason") or "",
        "phase": timeline.get("phase", ""),
        "changes": (evidence.get("changes") or [])[:3],
        "visual_patterns": evidence.get("visual_patterns") or [],
    }


def _state_key_summary(frames: list[SceneFrame]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for frame in frames:
        for key, value in (frame.state or {}).items():
            row = rows.setdefault(
                key,
                {
                    "key": key,
                    "type": type(value).__name__,
                    "seen": 0,
                    "sample": _compact_value(value, max_chars=180),
                },
            )
            row["seen"] += 1
    return sorted(rows.values(), key=lambda item: (-int(item["seen"]), item["key"]))[:MAX_STATE_KEYS]


def _compact_value(value: Any, *, max_chars: int = MAX_VALUE_CHARS) -> Any:
    text = _stable_json(value)
    if len(text) <= max_chars:
        return value
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, key in enumerate(sorted(value, key=str)):
            if index >= 8:
                result["..."] = f"{len(value) - index} more keys"
                break
            result[str(key)] = _compact_value(value[key], max_chars=max(80, max_chars // 4))
        return result
    if isinstance(value, list):
        result = [_compact_value(item, max_chars=max(80, max_chars // 6)) for item in value[:8]]
        if len(value) > 8:
            result.append(f"... {len(value) - 8} more items")
        return result
    return text[: max(20, max_chars - 20)] + "...(truncated)"


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    except TypeError:
        return str(value)


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return text[:head] + "\n<!-- truncated for repair prompt -->\n" + text[-tail:]
