"""Evaluate Stage2 Creative Visual artifacts.

This script treats Stage2 as a visualization enhancement layer. It summarizes
deterministic browser/layout gates from the Stage2 final report and can run an
optional VLM salience/readability review on the selected final screenshots.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_vision_with_metadata, parse_json_content, vlm_config
from scripts.creative_quality_gate import (
    ALGORITHM_READABILITY_THRESHOLD,
    SCENARIO_SALIENCE_THRESHOLD,
    evaluate_creative_scenario_with_vlm,
)


BOOL_FIELDS = (
    "creative_ok",
    "browser_smoke_ok",
    "strict_visual_quality_ok",
    "creative_quality_ok",
    "initial_creative_quality_ok",
    "initial_stage_visual_quality_ok",
    "last_creative_quality_ok",
    "last_stage_visual_quality_ok",
)

INT_FIELDS = (
    "creative_quality_score",
    "initial_creative_quality_score",
    "last_creative_quality_score",
    "stage_overlap_count",
    "stage_permitted_overlap_count",
    "stage_clipped_count",
    "stage_text_occlusion_count",
    "initial_stage_overlap_count",
    "initial_stage_permitted_overlap_count",
    "initial_stage_clipped_count",
    "initial_stage_text_occlusion_count",
)

STAGE2_EXTERNAL_SCORE_FIELDS = (
    "problem_visual_alignment",
    "algorithm_state_readability",
    "process_transition_clarity",
    "instructional_visual_design",
)

STAGE2_EXTERNAL_PASS_THRESHOLD = 3


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def host_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("/work/"):
        return str(ROOT / text[len("/work/") :])
    path = Path(text)
    if path.is_absolute():
        return str(path)
    return str(ROOT / path)


def repo_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("/work/"):
        text = text[len("/work/") :]
    path = Path(text)
    if path.is_absolute():
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)
    return str(path)


def final_quality_gate(row: dict[str, Any]) -> dict[str, Any]:
    reports = row.get("creative_quality_reports")
    if not isinstance(reports, list):
        return {}
    for item in reversed(reports):
        if not isinstance(item, dict):
            continue
        gate = item.get("gate")
        if isinstance(gate, dict):
            return gate
    return {}


def final_playwright(row: dict[str, Any]) -> dict[str, Any]:
    gate = final_quality_gate(row)
    playwright = gate.get("playwright") if isinstance(gate.get("playwright"), dict) else {}
    return dict(playwright or {})


def selected_screenshot(row: dict[str, Any]) -> str:
    playwright = final_playwright(row)
    return host_path(playwright.get("screenshot"))


def selected_html(row: dict[str, Any]) -> str:
    return host_path(row.get("html_host_path") or row.get("html"))


def _numeric_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(field)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def numeric_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = _numeric_values(rows, field)
    if not values:
        return {"count": 0, "min": None, "avg": None, "max": None, "sum": None}
    return {
        "count": len(values),
        "min": min(values),
        "avg": round(sum(values) / len(values), 3),
        "max": max(values),
        "sum": round(sum(values), 3),
    }


def count_true(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if row.get(field) is True)


def audited_frame_counts(rows: list[dict[str, Any]]) -> list[int]:
    counts: list[int] = []
    for row in rows:
        count = final_playwright(row).get("stage_audited_frame_count")
        if isinstance(count, int):
            counts.append(count)
    return counts


def compact_record(row: dict[str, Any]) -> dict[str, Any]:
    gate = final_quality_gate(row)
    playwright = final_playwright(row)
    screenshot = host_path(playwright.get("screenshot"))
    html = selected_html(row)
    screenshot_exists = bool(screenshot and Path(screenshot).exists() and Path(screenshot).stat().st_size > 0)
    html_exists = bool(html and Path(html).exists())
    return {
        "case_id": str(row.get("case_id") or ""),
        "problem_title": str(row.get("problem_title") or ""),
        "problem_description": str(row.get("problem_description") or ""),
        "stage2_selection": str(row.get("stage2_selection") or ""),
        "html": html,
        "html_repo_path": repo_path(row.get("html_host_path") or row.get("html")),
        "screenshot": screenshot,
        "screenshot_repo_path": repo_path(playwright.get("screenshot")),
        "screenshot_exists": screenshot_exists,
        "html_exists": html_exists,
        "creative_ok": bool(row.get("creative_ok")),
        "browser_smoke_ok": bool(row.get("browser_smoke_ok")),
        "strict_visual_quality_ok": bool(row.get("strict_visual_quality_ok")),
        "creative_quality_ok": bool(row.get("creative_quality_ok")),
        "creative_quality_score": row.get("creative_quality_score"),
        "initial_creative_quality_ok": bool(row.get("initial_creative_quality_ok")),
        "initial_creative_quality_score": row.get("initial_creative_quality_score"),
        "initial_stage_visual_quality_ok": bool(row.get("initial_stage_visual_quality_ok")),
        "initial_stage_overlap_count": row.get("initial_stage_overlap_count"),
        "initial_stage_clipped_count": row.get("initial_stage_clipped_count"),
        "initial_stage_text_occlusion_count": row.get("initial_stage_text_occlusion_count"),
        "stage_visual_quality_ok": bool(row.get("stage_visual_quality_ok")),
        "stage_overlap_count": int(row.get("stage_overlap_count") or 0),
        "stage_permitted_overlap_count": int(row.get("stage_permitted_overlap_count") or 0),
        "stage_clipped_count": int(row.get("stage_clipped_count") or 0),
        "stage_text_occlusion_count": int(row.get("stage_text_occlusion_count") or 0),
        "stage_audited_frame_count": playwright.get("stage_audited_frame_count"),
        "creative_quality_hard_failures": list(row.get("creative_quality_hard_failures") or []),
        "creative_quality_soft_failures": list(row.get("creative_quality_soft_failures") or []),
        "final_gate_score": gate.get("score"),
        "final_gate_hard_failures": list(gate.get("hard_failures") or []),
        "final_gate_soft_failures": list(gate.get("soft_failures") or []),
    }


def build_manifest(records: list[dict[str, Any]], source_report: Path) -> dict[str, Any]:
    screenshots = []
    for record in records:
        screenshots.append(
            {
                "condition": "stage2_creative",
                "case_id": record["case_id"],
                "target_id": f"stage2_creative:{record['case_id']}:0",
                "title": record["problem_title"],
                "kind": "page",
                "viewport": "desktop",
                "phase": "stage2_creative_final",
                "html": record["html"],
                "html_repo_path": record["html_repo_path"],
                "screenshot": record["screenshot"],
                "screenshot_repo_path": record["screenshot_repo_path"],
                "stage2_selection": record["stage2_selection"],
                "ok": record["screenshot_exists"] and record["html_exists"],
            }
        )
    return {
        "schema_version": "stage2-creative-screenshot-manifest-v1",
        "created_at": now_iso(),
        "condition": "stage2_creative",
        "source_report": str(source_report),
        "total": len(screenshots),
        "ok": all(item["ok"] for item in screenshots),
        "screenshots": screenshots,
    }


def summarize_machine(rows: list[dict[str, Any]], records: list[dict[str, Any]], source_report: dict[str, Any]) -> dict[str, Any]:
    total = len(rows)
    counts = {field: count_true(rows, field) for field in BOOL_FIELDS}
    rates = {field + "_rate": (counts[field] / total if total else 0.0) for field in BOOL_FIELDS}
    selection_counts = Counter(str(row.get("stage2_selection") or "") for row in rows)
    repaired_rows = [
        row
        for row in rows
        if row.get("initial_creative_quality_ok") is False and row.get("creative_quality_ok") is True
    ]
    score_delta_values = []
    for row in rows:
        initial = row.get("initial_creative_quality_score")
        final = row.get("creative_quality_score")
        if isinstance(initial, (int, float)) and isinstance(final, (int, float)):
            score_delta_values.append(float(final) - float(initial))
    frame_counts = audited_frame_counts(rows)
    missing_screenshots = [record["case_id"] for record in records if not record["screenshot_exists"]]
    missing_html = [record["case_id"] for record in records if not record["html_exists"]]
    return {
        "total": total,
        "scope": "Stage2 display-layer evaluation; not a Stage1 correctness gate.",
        "bool_counts": counts,
        "bool_rates": rates,
        "selection_counts": dict(selection_counts),
        "replaced_retry_cases": list(source_report.get("replaced_cases") or []),
        "repair_effect": {
            "initial_creative_quality_ok": counts.get("initial_creative_quality_ok", 0),
            "final_creative_quality_ok": counts.get("creative_quality_ok", 0),
            "repaired_from_initial_failure": len(repaired_rows),
            "creative_quality_repair_attempts": int((source_report.get("summary") or {}).get("creative_quality_repair_attempts") or 0),
            "layout_repair_attempts": int((source_report.get("summary") or {}).get("layout_repair_attempts") or 0),
            "avg_score_delta": round(sum(score_delta_values) / len(score_delta_values), 3) if score_delta_values else None,
            "max_score_delta": max(score_delta_values) if score_delta_values else None,
        },
        "numeric_summaries": {field: numeric_summary(rows, field) for field in INT_FIELDS},
        "layout_final_totals": {
            "stage_overlap_total": sum(int(row.get("stage_overlap_count") or 0) for row in rows),
            "stage_permitted_overlap_total": sum(int(row.get("stage_permitted_overlap_count") or 0) for row in rows),
            "stage_clipped_total": sum(int(row.get("stage_clipped_count") or 0) for row in rows),
            "stage_text_occlusion_total": sum(int(row.get("stage_text_occlusion_count") or 0) for row in rows),
        },
        "layout_initial_totals": {
            "initial_stage_overlap_total": sum(int(row.get("initial_stage_overlap_count") or 0) for row in rows),
            "initial_stage_permitted_overlap_total": sum(int(row.get("initial_stage_permitted_overlap_count") or 0) for row in rows),
            "initial_stage_clipped_total": sum(int(row.get("initial_stage_clipped_count") or 0) for row in rows),
            "initial_stage_text_occlusion_total": sum(int(row.get("initial_stage_text_occlusion_count") or 0) for row in rows),
        },
        "frame_audit": {
            "count": len(frame_counts),
            "min": min(frame_counts) if frame_counts else None,
            "avg": round(sum(frame_counts) / len(frame_counts), 3) if frame_counts else None,
            "max": max(frame_counts) if frame_counts else None,
            "total_audited_frames": sum(frame_counts),
        },
        "artifact_integrity": {
            "missing_screenshots": missing_screenshots,
            "missing_html": missing_html,
            "all_selected_screenshots_exist": not missing_screenshots,
            "all_selected_html_exist": not missing_html,
        },
        "source_stage2_summary": source_report.get("summary") or {},
    }


def stage2_vlm_ok(result: dict[str, Any]) -> bool:
    return (
        result.get("ok") is True
        and float(result.get("scenario_salience_score") or 0.0) >= SCENARIO_SALIENCE_THRESHOLD
        and float(result.get("algorithm_readability_score") or 0.0) >= ALGORITHM_READABILITY_THRESHOLD
        and not bool(result.get("is_generic_algorithm_visual"))
        and result.get("algorithm_state_visible") is not False
    )


def summarize_model_usage(results: list[dict[str, Any]]) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    for result in results:
        calls.extend(call for call in result.get("model_calls") or [] if isinstance(call, dict))
    usage_calls = [call for call in calls if call.get("usage_available") is True]
    usage_available = len(calls) > 0 and len(calls) == len(usage_calls)
    return {
        "call_count": len(calls),
        "usage_available": usage_available,
        "usage_available_count": len(usage_calls),
        "prompt_tokens": sum(int(call.get("prompt_tokens") or 0) for call in usage_calls),
        "completion_tokens": sum(int(call.get("completion_tokens") or 0) for call in usage_calls),
        "total_tokens": sum(int(call.get("total_tokens") or 0) for call in usage_calls),
        "duration_s": round(sum(float(call.get("duration_s") or 0.0) for call in calls), 3),
    }


def summarize_vlm(results: list[dict[str, Any]], total_available: int) -> dict[str, Any]:
    ok_results = [result for result in results if result.get("ok") is True]
    gate_ok = [result for result in results if result.get("stage2_vlm_ok") is True]
    failed = [result for result in results if result.get("ok") is not True]
    generic = [result for result in ok_results if result.get("is_generic_algorithm_visual")]
    scenario_ok = [
        result
        for result in ok_results
        if float(result.get("scenario_salience_score") or 0.0) >= SCENARIO_SALIENCE_THRESHOLD
        and not bool(result.get("is_generic_algorithm_visual"))
    ]
    readability_ok = [
        result
        for result in ok_results
        if float(result.get("algorithm_readability_score") or 0.0) >= ALGORITHM_READABILITY_THRESHOLD
        and result.get("algorithm_state_visible") is not False
    ]
    state_visible = [result for result in ok_results if result.get("algorithm_state_visible") is not False]

    def avg(field: str) -> float | None:
        values = [float(result[field]) for result in ok_results if isinstance(result.get(field), (int, float))]
        return round(sum(values) / len(values), 3) if values else None

    return {
        "evaluated": len(results),
        "total_available": total_available,
        "ok": len(ok_results),
        "failed": len(failed),
        "stage2_vlm_ok": len(gate_ok),
        "stage2_vlm_ok_rate_on_evaluated": len(gate_ok) / len(results) if results else 0.0,
        "scenario_salience_ok": len(scenario_ok),
        "scenario_salience_ok_rate_on_evaluated": len(scenario_ok) / len(results) if results else 0.0,
        "algorithm_readability_ok": len(readability_ok),
        "algorithm_readability_ok_rate_on_evaluated": len(readability_ok) / len(results) if results else 0.0,
        "avg_scenario_salience_score": avg("scenario_salience_score"),
        "avg_algorithm_readability_score": avg("algorithm_readability_score"),
        "generic_algorithm_visual_count": len(generic),
        "non_generic_visual_count": len(ok_results) - len(generic),
        "algorithm_state_visible_count": len(state_visible),
        "algorithm_state_not_visible_count": sum(1 for result in ok_results if result.get("algorithm_state_visible") is False),
        "low_salience_cases": [
            result["case_id"]
            for result in ok_results
            if float(result.get("scenario_salience_score") or 0.0) < SCENARIO_SALIENCE_THRESHOLD
        ],
        "low_readability_cases": [
            result["case_id"]
            for result in ok_results
            if float(result.get("algorithm_readability_score") or 0.0) < ALGORITHM_READABILITY_THRESHOLD
        ],
        "failed_cases": [{"case_id": result.get("case_id"), "error": result.get("error")} for result in failed],
        "model_usage": summarize_model_usage(results),
        "vlm_config": vlm_config(),
        "thresholds": {
            "scenario_salience": SCENARIO_SALIENCE_THRESHOLD,
            "algorithm_readability": ALGORITHM_READABILITY_THRESHOLD,
        },
    }


def clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(5, score))


def build_external_visual_prompt(record: dict[str, Any]) -> tuple[str, str]:
    """Build an external-framework VLM review prompt for Stage2 screenshots."""

    system = (
        "你是算法可视化与数字学习资源的外部评审员。"
        "请结合 Munzner nested model、LORI learning-object review 和 Mayer multimedia learning principles "
        "评价一个 Stage2 Creative Visual 截图。只根据截图和题目描述评分，不读取源码，不判断最终算法答案正确性。"
        "重要边界：不要把抽象算法题强行按生活场景扣分；抽象题如果视觉编码准确对应题目实体、数据结构、状态和过程，也应获得高题面贴合分。"
        "只输出一个可 json.loads 解析的 JSON 对象，不要 markdown。"
    )
    user = json.dumps(
        {
            "task": "external_stage2_visual_quality_review",
            "external_frameworks": {
                "Munzner_nested_model": "关注 domain problem / data abstraction / visual encoding 是否匹配，即题面任务、算法对象和视觉映射是否一致。",
                "LORI": "关注学习对象的内容质量、学习目标对齐、展示设计和易用性。",
                "Mayer_multimedia_learning": "关注 signaling、spatial contiguity、coherence 等教学视觉设计原则。",
            },
            "rubric": {
                "problem_visual_alignment": "1-5：题面实体、输入结构、目标输出和视觉对象/隐喻的贴合度。抽象算法允许用准确的数据结构/几何/图/表格编码获得高分。",
                "algorithm_state_readability": "1-5：当前算法状态、指针/窗口/队列/栈/DP/路径/边界/候选集是否清楚可读。",
                "process_transition_clarity": "1-5：截图是否能表达算法过程变化，或通过帧控件、轨迹、高亮、前后状态暗示下一步/当前步变化。",
                "instructional_visual_design": "1-5：视觉是否有教学性，包括高亮、标签、分组、解释邻近、减少干扰、信息层次清楚。",
            },
            "score_policy": {
                "range": "integer 1-5",
                "do_not_score": [
                    "不要评价最终答案是否正确",
                    "不要因为不是生活场景就降低 problem_visual_alignment",
                    "不要奖励装饰性美观超过教学清晰度",
                ],
            },
            "required_json_schema": {
                "scores": {field: "integer 1-5" for field in STAGE2_EXTERNAL_SCORE_FIELDS},
                "framework_notes": {
                    "Munzner": "one short Chinese sentence",
                    "LORI": "one short Chinese sentence",
                    "Mayer": "one short Chinese sentence",
                },
                "strengths": ["up to 3 concrete visible strengths"],
                "weaknesses": ["up to 3 concrete visible weaknesses"],
                "recommendation": "one short Chinese sentence for improving this visual",
                "confidence": "number 0-1",
            },
            "case": {
                "case_id": record.get("case_id"),
                "title": record.get("problem_title"),
                "problem_description": record.get("problem_description"),
                "html": record.get("html"),
                "screenshot": record.get("screenshot"),
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return system, user


def normalize_external_visual_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    raw_scores = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    scores = {field: clamp_score(raw_scores.get(field)) for field in STAGE2_EXTERNAL_SCORE_FIELDS}
    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, round(float(confidence), 3)))
    framework_notes = data.get("framework_notes") if isinstance(data.get("framework_notes"), dict) else {}
    return {
        "ok": True,
        "scores": scores,
        "overall_score": round(sum(scores.values()) / len(scores), 3),
        "framework_notes": {
            "Munzner": str(framework_notes.get("Munzner") or "")[:500],
            "LORI": str(framework_notes.get("LORI") or "")[:500],
            "Mayer": str(framework_notes.get("Mayer") or "")[:500],
        },
        "strengths": _short_string_list(data.get("strengths")),
        "weaknesses": _short_string_list(data.get("weaknesses")),
        "recommendation": str(data.get("recommendation") or "")[:500],
        "confidence": confidence,
    }


def _short_string_list(value: Any, *, limit: int = 4) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text[:220])
    return result[:limit]


def external_visual_ok(result: dict[str, Any]) -> bool:
    scores = result.get("scores") if isinstance(result.get("scores"), dict) else {}
    return result.get("ok") is True and all(
        int(scores.get(field) or 0) >= STAGE2_EXTERNAL_PASS_THRESHOLD
        for field in STAGE2_EXTERNAL_SCORE_FIELDS
    )


def evaluate_external_visual_record(
    record: dict[str, Any],
    *,
    model: str | None,
    retries: int,
) -> dict[str, Any]:
    screenshot_path = Path(str(record.get("screenshot") or ""))
    if not screenshot_path.exists():
        return {
            "ok": False,
            "failure_type": "external_vlm_eval_error",
            "error": f"screenshot does not exist: {screenshot_path}",
            "model_calls": [],
        }
    image_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
    system, base_user = build_external_visual_prompt(record)
    raw_response = ""
    model_calls: list[dict[str, Any]] = []
    last_error = ""
    for attempt in range(max(0, retries) + 1):
        user = base_user
        if attempt:
            user = "\n\n".join(
                [
                    base_user,
                    "上一轮输出无法解析或字段不合规。现在只返回一个紧凑 JSON 对象，不要 markdown。",
                ]
            )
        started = time.perf_counter()
        try:
            response = chat_vision_with_metadata(system, user, image_b64, model)
            raw_response = str(response.get("content") or "")
            model_call = dict(response.get("model_call") or {})
            if model_call:
                model_calls.append(model_call)
            payload = parse_json_content(raw_response)
            if not isinstance(payload, dict):
                raise ValueError("external visual VLM JSON must be an object")
            normalized = normalize_external_visual_payload(payload)
            normalized["model_call"] = model_call
            normalized["model_calls"] = model_calls
            normalized["raw_response"] = raw_response[:4000]
            return normalized
        except Exception as exc:
            last_error = str(exc)
            if not model_calls:
                model_calls.append(
                    {
                        "kind": "stage2_external_visual_eval",
                        "model": vlm_config(model)["model"],
                        "started_at": now_iso(),
                        "ended_at": now_iso(),
                        "duration_s": round(time.perf_counter() - started, 3),
                        "usage_available": False,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                    }
                )
    return {
        "ok": False,
        "failure_type": "external_vlm_eval_error",
        "error": last_error,
        "model_calls": model_calls,
        "raw_response": raw_response[:4000],
    }


def summarize_external_visual(results: list[dict[str, Any]], total_available: int) -> dict[str, Any]:
    ok_results = [result for result in results if result.get("ok") is True and isinstance(result.get("scores"), dict)]
    failed = [result for result in results if result.get("ok") is not True]
    dimension_pass_counts = {
        field: sum(1 for result in ok_results if int(result["scores"].get(field) or 0) >= STAGE2_EXTERNAL_PASS_THRESHOLD)
        for field in STAGE2_EXTERNAL_SCORE_FIELDS
    }
    dimension_strong_counts = {
        field: sum(1 for result in ok_results if int(result["scores"].get(field) or 0) >= 4)
        for field in STAGE2_EXTERNAL_SCORE_FIELDS
    }
    avg_scores = {
        field: round(sum(int(result["scores"].get(field) or 0) for result in ok_results) / len(ok_results), 3)
        if ok_results
        else None
        for field in STAGE2_EXTERNAL_SCORE_FIELDS
    }
    overall_values = [
        float(result.get("overall_score"))
        for result in ok_results
        if isinstance(result.get("overall_score"), (int, float))
    ]
    all_dimension_values = [
        int(result["scores"].get(field) or 0)
        for result in ok_results
        for field in STAGE2_EXTERNAL_SCORE_FIELDS
    ]
    all_pass = [result for result in ok_results if external_visual_ok(result)]
    return {
        "evaluated": len(results),
        "total_available": total_available,
        "ok": len(ok_results),
        "failed": len(failed),
        "score_fields": list(STAGE2_EXTERNAL_SCORE_FIELDS),
        "pass_threshold": STAGE2_EXTERNAL_PASS_THRESHOLD,
        "all_dimensions_pass": len(all_pass),
        "all_dimensions_pass_rate_on_evaluated": len(all_pass) / len(results) if results else 0.0,
        "avg_scores": avg_scores,
        "overall_avg_score": round(sum(overall_values) / len(overall_values), 3)
        if overall_values
        else (round(sum(all_dimension_values) / len(all_dimension_values), 3) if all_dimension_values else None),
        "dimension_pass_counts": dimension_pass_counts,
        "dimension_pass_rates": {
            field: dimension_pass_counts[field] / len(results) if results else 0.0
            for field in STAGE2_EXTERNAL_SCORE_FIELDS
        },
        "dimension_strong_counts": dimension_strong_counts,
        "low_score_cases": {
            field: [
                result["case_id"]
                for result in ok_results
                if int(result["scores"].get(field) or 0) < STAGE2_EXTERNAL_PASS_THRESHOLD
            ]
            for field in STAGE2_EXTERNAL_SCORE_FIELDS
        },
        "failed_cases": [{"case_id": result.get("case_id"), "error": result.get("error")} for result in failed],
        "model_usage": summarize_model_usage(results),
        "vlm_config": vlm_config(),
        "external_frameworks": {
            "Munzner_nested_model": "problem/task and visual encoding fit",
            "LORI": "learning-object content, alignment, design, usability",
            "Mayer_multimedia_learning": "signaling, spatial contiguity, coherence",
        },
    }


def run_external_visual_review(
    records: list[dict[str, Any]],
    *,
    output_dir: Path,
    model: str | None,
    max_cases: int,
    concurrency: int,
    retries: int,
    force: bool,
) -> list[dict[str, Any]]:
    selected = records[: max_cases or len(records)]
    shard_dir = output_dir / "external_visual_cases"
    shard_dir.mkdir(parents=True, exist_ok=True)

    def run_one(record: dict[str, Any]) -> dict[str, Any]:
        case_id = record["case_id"]
        shard_path = shard_dir / f"{case_id}.json"
        if shard_path.exists() and not force:
            return load_json(shard_path)
        started = time.perf_counter()
        result = evaluate_external_visual_record(record, model=model, retries=retries)
        result = {
            **result,
            "case_id": case_id,
            "problem_title": record["problem_title"],
            "stage2_selection": record["stage2_selection"],
            "html": record["html"],
            "screenshot": record["screenshot"],
            "stage2_external_visual_ok": external_visual_ok(result),
            "elapsed_wall_s": round(time.perf_counter() - started, 3),
        }
        write_json(shard_path, result)
        return result

    if concurrency <= 1:
        return [run_one(record) for record in selected]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {executor.submit(run_one, record): record["case_id"] for record in selected}
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: str(item.get("case_id") or ""))


def run_vlm_salience(
    records: list[dict[str, Any]],
    *,
    output_dir: Path,
    model: str | None,
    max_cases: int,
    concurrency: int,
    retries: int,
    force: bool,
) -> list[dict[str, Any]]:
    selected = records[: max_cases or len(records)]
    shard_dir = output_dir / "vlm_salience_cases"
    shard_dir.mkdir(parents=True, exist_ok=True)

    def run_one(record: dict[str, Any]) -> dict[str, Any]:
        case_id = record["case_id"]
        shard_path = shard_dir / f"{case_id}.json"
        if shard_path.exists() and not force:
            return load_json(shard_path)
        started = time.perf_counter()
        try:
            result = evaluate_creative_scenario_with_vlm(
                screenshot_path=Path(record["screenshot"]),
                problem_description=record["problem_description"] or record["problem_title"],
                case_id=case_id,
                html_path=Path(record["html"]) if record.get("html") else None,
                model=model,
                retries=retries,
            )
        except Exception as exc:
            result = {
                "ok": False,
                "failure_type": "vlm_eval_error",
                "error": str(exc),
                "model_calls": [],
            }
        result = {
            **result,
            "case_id": case_id,
            "problem_title": record["problem_title"],
            "stage2_selection": record["stage2_selection"],
            "html": record["html"],
            "screenshot": record["screenshot"],
            "stage2_vlm_ok": stage2_vlm_ok(result),
            "elapsed_wall_s": round(time.perf_counter() - started, 3),
        }
        write_json(shard_path, result)
        return result

    if concurrency <= 1:
        return [run_one(record) for record in selected]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {executor.submit(run_one, record): record["case_id"] for record in selected}
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: str(item.get("case_id") or ""))


def build_report(
    *,
    stage2_report_path: Path,
    output_dir: Path,
    run_vlm: bool,
    run_external_vlm: bool,
    vlm_model: str | None,
    vlm_max_cases: int,
    concurrency: int,
    vlm_retries: int,
    force_vlm: bool,
) -> dict[str, Any]:
    source_report = load_json(stage2_report_path)
    rows = [row for row in source_report.get("results") or [] if isinstance(row, dict)]
    records = [compact_record(row) for row in rows]
    manifest = build_manifest(records, stage2_report_path)
    manifest_path = output_dir / "stage2_screenshot_manifest.json"
    write_json(manifest_path, manifest)
    machine_summary = summarize_machine(rows, records, source_report)
    vlm_results: list[dict[str, Any]] = []
    vlm_summary: dict[str, Any] | None = None
    external_visual_results: list[dict[str, Any]] = []
    external_visual_summary: dict[str, Any] | None = None
    if run_vlm:
        vlm_results = run_vlm_salience(
            records,
            output_dir=output_dir,
            model=vlm_model,
            max_cases=vlm_max_cases,
            concurrency=concurrency,
            retries=vlm_retries,
            force=force_vlm,
        )
        vlm_summary = summarize_vlm(vlm_results, total_available=len(records))
    if run_external_vlm:
        external_visual_results = run_external_visual_review(
            records,
            output_dir=output_dir,
            model=vlm_model,
            max_cases=vlm_max_cases,
            concurrency=concurrency,
            retries=vlm_retries,
            force=force_vlm,
        )
        external_visual_summary = summarize_external_visual(external_visual_results, total_available=len(records))
    report = {
        "kind": "stage2_visual_eval_report",
        "schema_version": "stage2-visual-eval-v1",
        "created_at": now_iso(),
        "source_report": str(stage2_report_path),
        "screenshot_manifest": str(manifest_path),
        "condition": "stage2_creative",
        "machine_summary": machine_summary,
        "vlm_salience_summary": vlm_summary,
        "external_visual_summary": external_visual_summary,
        "records": records,
        "vlm_salience_results": vlm_results,
        "external_visual_results": external_visual_results,
    }
    write_outputs(report, output_dir)
    return report


def fmt_rate(count: int, total: int) -> str:
    return f"{count}/{total} ({count / total:.3f})" if total else "0/0 (0.000)"


def write_outputs(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "stage2_visual_eval_report.json"
    write_json(json_path, report)
    machine = report["machine_summary"]
    total = int(machine["total"])
    bool_counts = machine["bool_counts"]
    layout_final = machine["layout_final_totals"]
    layout_initial = machine["layout_initial_totals"]
    repair = machine["repair_effect"]
    frame = machine["frame_audit"]
    lines = [
        "# Stage2 Creative Visual Evaluation",
        "",
        f"- created_at: `{report['created_at']}`",
        f"- source_report: `{repo_path(report['source_report'])}`",
        f"- screenshot_manifest: `{repo_path(report['screenshot_manifest'])}`",
        "- scope: Stage2 is evaluated as a display-layer creative visualization shell, not as the Stage1 algorithm correctness gate.",
        "",
        "## Machine Visual Gates",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| creative_ok | {fmt_rate(bool_counts['creative_ok'], total)} |",
        f"| browser_smoke_ok | {fmt_rate(bool_counts['browser_smoke_ok'], total)} |",
        f"| strict_visual_quality_ok | {fmt_rate(bool_counts['strict_visual_quality_ok'], total)} |",
        f"| creative_quality_ok | {fmt_rate(bool_counts['creative_quality_ok'], total)} |",
        f"| selected screenshots exist | {fmt_rate(total - len(machine['artifact_integrity']['missing_screenshots']), total)} |",
        f"| selected HTML files exist | {fmt_rate(total - len(machine['artifact_integrity']['missing_html']), total)} |",
        "",
        "## Repair Effect",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| initial creative_quality_ok | {fmt_rate(repair['initial_creative_quality_ok'], total)} |",
        f"| final creative_quality_ok | {fmt_rate(repair['final_creative_quality_ok'], total)} |",
        f"| repaired from initial failure | {repair['repaired_from_initial_failure']} |",
        f"| creative quality repair attempts | {repair['creative_quality_repair_attempts']} |",
        f"| average quality score delta | {repair['avg_score_delta']} |",
        "",
        "## Layout Audit",
        "",
        "| Metric | Initial | Final |",
        "|---|---:|---:|",
        f"| overlap total | {layout_initial['initial_stage_overlap_total']} | {layout_final['stage_overlap_total']} |",
        f"| clipped total | {layout_initial['initial_stage_clipped_total']} | {layout_final['stage_clipped_total']} |",
        f"| text occlusion total | {layout_initial['initial_stage_text_occlusion_total']} | {layout_final['stage_text_occlusion_total']} |",
        f"| permitted overlap total | {layout_initial['initial_stage_permitted_overlap_total']} | {layout_final['stage_permitted_overlap_total']} |",
        "",
        f"- audited frame count: `{frame['count']}` cases, avg `{frame['avg']}`, total frames `{frame['total_audited_frames']}`.",
        f"- selection counts: `{json.dumps(machine['selection_counts'], ensure_ascii=False, sort_keys=True)}`.",
    ]
    vlm = report.get("vlm_salience_summary")
    if vlm:
        lines.extend(
            [
                "",
                "## VLM Salience Review",
                "",
                "| Metric | Result |",
                "|---|---:|",
                f"| evaluated | {vlm['evaluated']}/{vlm['total_available']} |",
                f"| valid VLM responses | {fmt_rate(vlm['ok'], vlm['evaluated'])} |",
                f"| strict creative-scene gate | {fmt_rate(vlm['stage2_vlm_ok'], vlm['evaluated'])} |",
                f"| scenario salience ok | {fmt_rate(vlm['scenario_salience_ok'], vlm['evaluated'])} |",
                f"| algorithm readability ok | {fmt_rate(vlm['algorithm_readability_ok'], vlm['evaluated'])} |",
                f"| avg scenario salience | {vlm['avg_scenario_salience_score']} |",
                f"| avg algorithm readability | {vlm['avg_algorithm_readability_score']} |",
                f"| generic visual count | {vlm['generic_algorithm_visual_count']} |",
                f"| state-not-visible count | {vlm['algorithm_state_not_visible_count']} |",
                "",
                "Interpretation: the strict creative-scene gate requires both visible non-generic scene grounding and readable algorithm state. It is a visual salience metric, not a correctness metric.",
                "",
                "Token / time:",
                f"- calls: `{vlm['model_usage']['call_count']}`",
                f"- total_tokens: `{vlm['model_usage']['total_tokens']}`",
                f"- duration_s: `{vlm['model_usage']['duration_s']}`",
            ]
        )
        if vlm["low_salience_cases"]:
            lines.append(f"- low salience cases: `{', '.join(vlm['low_salience_cases'][:20])}`")
        if vlm["failed_cases"]:
            lines.append(f"- failed VLM cases: `{json.dumps(vlm['failed_cases'][:10], ensure_ascii=False)}`")
    external = report.get("external_visual_summary")
    if external:
        avg_scores = external["avg_scores"]
        pass_counts = external["dimension_pass_counts"]
        strong_counts = external["dimension_strong_counts"]
        lines.extend(
            [
                "",
                "## External Stage2 Visual Review",
                "",
                "This is the main VLM-based Stage2 visual-quality review. It uses external visualization and learning-object frames: Munzner nested model, LORI, and Mayer multimedia learning principles.",
                "",
                "| Metric | Avg Score | Pass >=3 | Strong >=4 |",
                "|---|---:|---:|---:|",
                f"| problem_visual_alignment | {avg_scores['problem_visual_alignment']} | {fmt_rate(pass_counts['problem_visual_alignment'], external['evaluated'])} | {fmt_rate(strong_counts['problem_visual_alignment'], external['evaluated'])} |",
                f"| algorithm_state_readability | {avg_scores['algorithm_state_readability']} | {fmt_rate(pass_counts['algorithm_state_readability'], external['evaluated'])} | {fmt_rate(strong_counts['algorithm_state_readability'], external['evaluated'])} |",
                f"| process_transition_clarity | {avg_scores['process_transition_clarity']} | {fmt_rate(pass_counts['process_transition_clarity'], external['evaluated'])} | {fmt_rate(strong_counts['process_transition_clarity'], external['evaluated'])} |",
                f"| instructional_visual_design | {avg_scores['instructional_visual_design']} | {fmt_rate(pass_counts['instructional_visual_design'], external['evaluated'])} | {fmt_rate(strong_counts['instructional_visual_design'], external['evaluated'])} |",
                "",
                f"- evaluated: `{external['evaluated']}/{external['total_available']}`",
                f"- valid VLM responses: `{fmt_rate(external['ok'], external['evaluated'])}`",
                f"- all four dimensions pass: `{fmt_rate(external['all_dimensions_pass'], external['evaluated'])}`",
                f"- overall average score: `{external['overall_avg_score']}/5`",
                "- This review does not penalize abstract algorithm tasks for lacking a real-world scene when the visual encoding matches the problem.",
                "",
                "Token / time:",
                f"- calls: `{external['model_usage']['call_count']}`",
                f"- total_tokens: `{external['model_usage']['total_tokens']}`",
                f"- duration_s: `{external['model_usage']['duration_s']}`",
            ]
        )
        low_problem = external["low_score_cases"].get("problem_visual_alignment") or []
        if low_problem:
            lines.append(f"- low problem-visual alignment cases: `{', '.join(low_problem[:20])}`")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- json: `{repo_path(json_path)}`",
            f"- markdown: `{repo_path(output_dir / 'stage2_visual_eval_report.md')}`",
            f"- manifest: `{repo_path(output_dir / 'stage2_screenshot_manifest.json')}`",
            "",
        ]
    )
    (output_dir / "stage2_visual_eval_report.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage2-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-vlm", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--run-external-vlm",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run the external four-dimension Stage2 visual review.",
    )
    parser.add_argument("--vlm-model", default=None)
    parser.add_argument("--vlm-max-cases", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--vlm-retries", type=int, default=2)
    parser.add_argument("--force-vlm", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        stage2_report_path=(ROOT / args.stage2_report).resolve() if not args.stage2_report.is_absolute() else args.stage2_report,
        output_dir=(ROOT / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir,
        run_vlm=bool(args.run_vlm),
        run_external_vlm=bool(args.run_external_vlm),
        vlm_model=args.vlm_model,
        vlm_max_cases=max(0, int(args.vlm_max_cases or 0)),
        concurrency=max(1, int(args.concurrency or 1)),
        vlm_retries=max(0, int(args.vlm_retries or 0)),
        force_vlm=bool(args.force_vlm),
    )
    machine = report["machine_summary"]
    vlm = report.get("vlm_salience_summary")
    external = report.get("external_visual_summary")
    print(
        json.dumps(
            {
                "output_dir": repo_path(args.output_dir),
                "total": machine["total"],
                "creative_quality_ok": machine["bool_counts"]["creative_quality_ok"],
                "strict_visual_quality_ok": machine["bool_counts"]["strict_visual_quality_ok"],
                "layout_final_totals": machine["layout_final_totals"],
                "vlm_salience_summary": vlm,
                "external_visual_summary": external,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
