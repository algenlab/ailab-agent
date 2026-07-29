"""Evaluate browser screenshots with an offline VLM teaching-quality rubric."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import LLMJsonError, chat_vision_with_metadata, parse_json_content, vlm_config


RUBRIC_PATH = ROOT / "benchmark" / "vlm_screenshot_rubric.json"
SYSTEM_PROMPT_PATH = ROOT / "algolab" / "generation" / "prompts" / "vlm_screenshot_judge_system.txt"
USER_PROMPT_PATH = ROOT / "algolab" / "generation" / "prompts" / "vlm_screenshot_judge_user.txt"
SCORE_FIELDS = (
    "layout_readability",
    "algorithm_state_visibility",
    "teaching_explanation",
    "interaction_affordance",
    "evidence_alignment",
    "overall_teaching_quality",
)
ISSUE_SEVERITIES = {"low", "medium", "high"}
ISSUE_CATEGORIES = {"layout", "state", "explanation", "interaction", "evidence", "other"}


JudgeCall = Callable[[str, str, str, str | None], dict[str, Any]]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def screenshot_type(record: dict[str, Any]) -> str:
    if record.get("kind") == "interaction":
        return "interaction"
    if record.get("target_id") == "dashboard_index":
        return "dashboard"
    return "page"


def case_id_for(record: dict[str, Any]) -> str:
    return str(record.get("case_id") or record.get("target_id") or Path(str(record.get("screenshot", ""))).stem)


def prompt_metadata(
    *,
    rubric_path: Path = RUBRIC_PATH,
    system_prompt_path: Path = SYSTEM_PROMPT_PATH,
    user_prompt_path: Path = USER_PROMPT_PATH,
    judge_model: str | None = None,
) -> dict[str, Any]:
    rubric = load_json(rubric_path)
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    user_prompt = user_prompt_path.read_text(encoding="utf-8")
    return {
        "prompt_version": "vlm-screenshot-judge-2026-05-30",
        "prompt_hash": text_sha256(system_prompt + "\n---USER---\n" + user_prompt),
        "prompt_files": {
            "system": str(system_prompt_path),
            "user": str(user_prompt_path),
        },
        "rubric_version": str(rubric.get("rubric_version") or rubric.get("schema_version") or ""),
        "rubric_hash": file_sha256(rubric_path),
        "rubric_path": str(rubric_path),
        "judge_model": vlm_config(judge_model)["model"],
    }


def build_user_prompt(template: str, record: dict[str, Any], condition: str, rubric: dict[str, Any]) -> str:
    replacements = {
        "condition": condition,
        "case_id": case_id_for(record),
        "screenshot": str(record.get("screenshot") or ""),
        "viewport": str(record.get("viewport") or ""),
        "screenshot_type": screenshot_type(record),
        "html": str(record.get("html") or ""),
        "phase": str(record.get("phase") or ""),
        "rubric_version": str(rubric.get("rubric_version") or ""),
        "rubric_json": json.dumps(rubric, ensure_ascii=False, indent=2),
    }
    prompt = template
    for key, value in replacements.items():
        prompt = prompt.replace("{{" + key + "}}", value)
    return prompt


def normalize_model_call(model_call: dict[str, Any] | None, *, model: str | None = None) -> dict[str, Any]:
    call = dict(model_call or {})
    call.setdefault("kind", "vlm_eval")
    call.setdefault("model", vlm_config(model)["model"])
    call.setdefault("started_at", "")
    call.setdefault("ended_at", "")
    call.setdefault("duration_s", 0.0)
    if call.get("usage_available") is True:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if not isinstance(call.get(key), int):
                call["usage_available"] = False
                break
    if call.get("usage_available") is not True:
        call["usage_available"] = False
        call["prompt_tokens"] = None
        call["completion_tokens"] = None
        call["total_tokens"] = None
    return call


def validate_scores(payload: dict[str, Any]) -> dict[str, int]:
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("VLM JSON missing scores object")
    normalized: dict[str, int] = {}
    for field in SCORE_FIELDS:
        value = scores.get(field)
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"VLM score {field} must be an integer from 1 to 5")
        normalized[field] = value
    return normalized


def validate_issues(payload: dict[str, Any]) -> list[dict[str, str]]:
    issues = payload.get("issues", [])
    if not isinstance(issues, list):
        raise ValueError("VLM JSON issues must be a list")
    normalized: list[dict[str, str]] = []
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError(f"VLM issue #{index} must be an object")
        severity = str(issue.get("severity") or "").strip()
        category = str(issue.get("category") or "").strip()
        message = str(issue.get("message") or "").strip()
        if severity not in ISSUE_SEVERITIES:
            raise ValueError(f"VLM issue #{index} has invalid severity")
        if category not in ISSUE_CATEGORIES:
            raise ValueError(f"VLM issue #{index} has invalid category")
        if not message:
            raise ValueError(f"VLM issue #{index} missing message")
        normalized.append({"severity": severity, "category": category, "message": message[:240]})
    return normalized


def validate_confidence(payload: dict[str, Any]) -> float:
    value = payload.get("confidence")
    if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
        raise ValueError("VLM confidence must be a number from 0 to 1")
    return float(value)


def validate_caption(payload: dict[str, Any]) -> str:
    caption = str(payload.get("suggested_caption") or "").strip()
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", caption)
    english_words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", caption)
    if cjk_chars and len(cjk_chars) > 50:
        raise ValueError("VLM suggested_caption is too long")
    if not cjk_chars and len(english_words) > 30:
        raise ValueError("VLM suggested_caption is too long")
    return caption


def success_result(
    payload: dict[str, Any],
    *,
    record: dict[str, Any],
    condition: str,
    judge_model: str | None,
    model_call: dict[str, Any],
    model_calls: list[dict[str, Any]] | None,
    prompt_info: dict[str, Any],
) -> dict[str, Any]:
    scores = validate_scores(payload)
    confidence = validate_confidence(payload)
    issues = validate_issues(payload)
    caption = validate_caption(payload)
    normalized_call = normalize_model_call(model_call, model=judge_model)
    return {
        "ok": True,
        "failure_type": "",
        "case_id": case_id_for(record),
        "condition": condition,
        "screenshot": str(record.get("screenshot") or ""),
        "viewport": str(record.get("viewport") or ""),
        "kind": str(record.get("kind") or ""),
        "screenshot_type": screenshot_type(record),
        "html": str(record.get("html") or ""),
        "phase": str(record.get("phase") or ""),
        "scores": scores,
        "confidence": confidence,
        "issues": issues,
        "suggested_caption": caption,
        "judge_model": vlm_config(judge_model)["model"],
        "model_call": normalized_call,
        "model_calls": model_calls or [normalized_call],
        "prompt_version": prompt_info["prompt_version"],
        "prompt_hash": prompt_info["prompt_hash"],
        "rubric_version": prompt_info["rubric_version"],
        "rubric_hash": prompt_info["rubric_hash"],
        "raw_response": json.dumps(payload, ensure_ascii=False),
    }


def failure_result(
    *,
    record: dict[str, Any],
    condition: str,
    judge_model: str | None,
    error: str,
    model_call: dict[str, Any] | None,
    model_calls: list[dict[str, Any]] | None,
    prompt_info: dict[str, Any],
    raw_response: str = "",
) -> dict[str, Any]:
    normalized_call = normalize_model_call(model_call, model=judge_model)
    return {
        "ok": False,
        "failure_type": "vlm_eval_error",
        "case_id": case_id_for(record),
        "condition": condition,
        "screenshot": str(record.get("screenshot") or ""),
        "viewport": str(record.get("viewport") or ""),
        "kind": str(record.get("kind") or ""),
        "screenshot_type": screenshot_type(record),
        "html": str(record.get("html") or ""),
        "phase": str(record.get("phase") or ""),
        "scores": None,
        "confidence": 0.0,
        "issues": [],
        "suggested_caption": "",
        "judge_model": vlm_config(judge_model)["model"],
        "model_call": normalized_call,
        "model_calls": model_calls or [normalized_call],
        "prompt_version": prompt_info["prompt_version"],
        "prompt_hash": prompt_info["prompt_hash"],
        "rubric_version": prompt_info["rubric_version"],
        "rubric_hash": prompt_info["rubric_hash"],
        "error": error,
        "raw_response": raw_response[:4000],
    }


def evaluate_screenshot_record(
    record: dict[str, Any],
    *,
    condition: str,
    rubric: dict[str, Any],
    system_prompt: str,
    user_prompt_template: str,
    prompt_info: dict[str, Any],
    judge_model: str | None = None,
    judge_call: JudgeCall = chat_vision_with_metadata,
    retries: int = 0,
) -> dict[str, Any]:
    screenshot_path = Path(str(record.get("screenshot") or ""))
    if not screenshot_path.exists():
        return failure_result(
            record=record,
            condition=condition,
            judge_model=judge_model,
            error=f"screenshot does not exist: {screenshot_path}",
            model_call=None,
            model_calls=None,
            prompt_info=prompt_info,
        )
    image_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
    base_user_prompt = build_user_prompt(user_prompt_template, record, condition, rubric)
    raw_response = ""
    last_error = ""
    last_model_call: dict[str, Any] | None = None
    model_calls: list[dict[str, Any]] = []
    for attempt in range(max(0, retries) + 1):
        user_prompt = base_user_prompt
        if attempt:
            user_prompt = "\n\n".join(
                [
                    base_user_prompt,
                    "Previous VLM response was invalid. Return one compact strict JSON object only.",
                    "Use integer scores from 1 to 5, confidence from 0 to 1, and suggested_caption with at most 30 English words or 50 Chinese characters.",
                ]
            )
        start = time.perf_counter()
        started_at = now_iso()
        try:
            response = judge_call(system_prompt, user_prompt, image_b64, judge_model)
            raw_response = str(response.get("content") or "")
            last_model_call = normalize_model_call(response.get("model_call"), model=judge_model)
            model_calls.append(last_model_call)
            payload = parse_json_content(raw_response)
            if not isinstance(payload, dict):
                raise ValueError("VLM JSON must be an object")
            return success_result(
                payload,
                record=record,
                condition=condition,
                judge_model=judge_model,
                model_call=last_model_call,
                model_calls=model_calls,
                prompt_info=prompt_info,
            )
        except Exception as exc:
            last_error = str(exc)
            if last_model_call is None or len(model_calls) <= attempt:
                last_model_call = {
                    "kind": "vlm_eval",
                    "model": vlm_config(judge_model)["model"],
                    "started_at": started_at,
                    "ended_at": now_iso(),
                    "duration_s": round(time.perf_counter() - start, 3),
                    "usage_available": False,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                }
                model_calls.append(last_model_call)
    return failure_result(
        record=record,
        condition=condition,
        judge_model=judge_model,
        error=last_error,
        model_call=last_model_call,
        model_calls=model_calls,
        prompt_info=prompt_info,
        raw_response=raw_response,
    )


def screenshot_records_from_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = manifest.get("screenshots")
    if not isinstance(records, list):
        raise ValueError("manifest.screenshots must be a list")
    return [record for record in records if isinstance(record, dict)]


def summarize_model_usage(results: list[dict[str, Any]]) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    for result in results:
        result_calls = result.get("model_calls")
        if isinstance(result_calls, list):
            calls.extend(call for call in result_calls if isinstance(call, dict))
        elif isinstance(result.get("model_call"), dict):
            calls.append(result["model_call"])
    call_count = len(calls)
    usage_calls = [call for call in calls if call.get("usage_available") is True]
    all_usage_available = call_count > 0 and len(usage_calls) == call_count
    duration_s = round(sum(float(call.get("duration_s") or 0.0) for call in calls), 3)
    total_tokens = sum(int(call["total_tokens"]) for call in usage_calls) if all_usage_available else None
    return {
        "usage_available": all_usage_available,
        "usage_available_rate": (len(usage_calls) / call_count) if call_count else 0.0,
        "call_count": call_count,
        "prompt_tokens": sum(int(call["prompt_tokens"]) for call in usage_calls) if all_usage_available else None,
        "completion_tokens": sum(int(call["completion_tokens"]) for call in usage_calls) if all_usage_available else None,
        "total_tokens": total_tokens,
        "duration_s": duration_s,
        "avg_duration_s": (duration_s / call_count) if call_count else 0.0,
        "avg_total_tokens": (total_tokens / call_count) if all_usage_available and call_count else None,
        "estimated_cost": None,
        "cost_estimation_available": False,
        "pricing_source": "",
    }


def score_averages(results: list[dict[str, Any]]) -> dict[str, float | None]:
    ok_results = [result for result in results if result.get("ok") and isinstance(result.get("scores"), dict)]
    averages: dict[str, float | None] = {}
    for field in SCORE_FIELDS:
        values = [int(result["scores"][field]) for result in ok_results]
        averages[field] = (sum(values) / len(values)) if values else None
    return averages


def summarize_results(results: list[dict[str, Any]], condition: str) -> dict[str, Any]:
    ok_results = [result for result in results if result.get("ok")]
    failed_results = [result for result in results if not result.get("ok")]
    failure_types: dict[str, int] = {}
    for result in failed_results:
        failure_type = str(result.get("failure_type") or "unknown")
        failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
    low_score_results = [
        result
        for result in ok_results
        if isinstance(result.get("scores"), dict) and any(int(result["scores"][field]) <= 2 for field in SCORE_FIELDS)
    ]
    high_confidence_issue_results = [
        result
        for result in ok_results
        if float(result.get("confidence") or 0.0) >= 0.7 and result.get("issues")
    ]
    return {
        "condition": condition,
        "total": len(results),
        "passed": len(ok_results),
        "failed": len(failed_results),
        "pass_rate": (len(ok_results) / len(results)) if results else 0.0,
        "failure_types": failure_types,
        "score_averages": score_averages(results),
        "low_score_count": len(low_score_results),
        "low_score_screenshots": [result["screenshot"] for result in low_score_results],
        "high_confidence_issue_count": len(high_confidence_issue_results),
        "high_confidence_issues": [
            {
                "case_id": result["case_id"],
                "screenshot": result["screenshot"],
                "issues": result["issues"],
            }
            for result in high_confidence_issue_results
        ],
        "model_usage": summarize_model_usage(results),
    }


def build_report(
    *,
    manifest_path: Path,
    condition: str,
    rubric_path: Path = RUBRIC_PATH,
    system_prompt_path: Path = SYSTEM_PROMPT_PATH,
    user_prompt_path: Path = USER_PROMPT_PATH,
    judge_model: str | None = None,
    judge_call: JudgeCall = chat_vision_with_metadata,
    progress: bool = False,
    retries: int = 0,
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    rubric = load_json(rubric_path)
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    user_prompt_template = user_prompt_path.read_text(encoding="utf-8")
    prompt_info = prompt_metadata(
        rubric_path=rubric_path,
        system_prompt_path=system_prompt_path,
        user_prompt_path=user_prompt_path,
        judge_model=judge_model,
    )
    records = screenshot_records_from_manifest(manifest)
    results = []
    for index, record in enumerate(records, start=1):
        if progress:
            print(
                f"[{index}/{len(records)}] vlm_eval {case_id_for(record)} {record.get('viewport', '')} {screenshot_type(record)}",
                flush=True,
            )
        results.append(
            evaluate_screenshot_record(
                record,
                condition=condition,
                rubric=rubric,
                system_prompt=system_prompt,
                user_prompt_template=user_prompt_template,
                prompt_info=prompt_info,
                judge_model=judge_model,
                judge_call=judge_call,
                retries=retries,
            )
        )
    summary = summarize_results(results, condition)
    return {
        "schema_version": "vlm-screenshot-scores-v1",
        "created_at": now_iso(),
        "manifest": str(manifest_path),
        "condition": condition,
        "config": vlm_config(judge_model),
        **prompt_info,
        "summary": summary,
        "results": results,
    }


def write_scores_csv(report: dict[str, Any], path: Path) -> None:
    fields = [
        "condition",
        "case_id",
        "viewport",
        "kind",
        "screenshot_type",
        "screenshot",
        "ok",
        "failure_type",
        *SCORE_FIELDS,
        "confidence",
        "issue_count",
        "suggested_caption",
        "judge_model",
        "usage_available",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "duration_s",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for result in report["results"]:
            scores = result.get("scores") or {}
            model_call = result.get("model_call") or {}
            row = {
                "condition": result.get("condition", ""),
                "case_id": result.get("case_id", ""),
                "viewport": result.get("viewport", ""),
                "kind": result.get("kind", ""),
                "screenshot_type": result.get("screenshot_type", ""),
                "screenshot": result.get("screenshot", ""),
                "ok": result.get("ok", False),
                "failure_type": result.get("failure_type", ""),
                "confidence": result.get("confidence", 0.0),
                "issue_count": len(result.get("issues") or []),
                "suggested_caption": result.get("suggested_caption", ""),
                "judge_model": result.get("judge_model", ""),
                "usage_available": model_call.get("usage_available", False),
                "prompt_tokens": model_call.get("prompt_tokens"),
                "completion_tokens": model_call.get("completion_tokens"),
                "total_tokens": model_call.get("total_tokens"),
                "duration_s": model_call.get("duration_s", 0.0),
                "error": result.get("error", ""),
            }
            for field in SCORE_FIELDS:
                row[field] = scores.get(field)
            writer.writerow(row)


def summary_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    results = report["results"]
    groups: list[tuple[str, list[dict[str, Any]]]] = [("all", results)]
    for viewport in sorted({str(result.get("viewport") or "") for result in results if result.get("viewport")}):
        groups.append((f"viewport:{viewport}", [result for result in results if result.get("viewport") == viewport]))
    for screenshot_kind in sorted({str(result.get("screenshot_type") or "") for result in results if result.get("screenshot_type")}):
        groups.append((f"type:{screenshot_kind}", [result for result in results if result.get("screenshot_type") == screenshot_kind]))
    for group, group_results in groups:
        group_summary = summarize_results(group_results, report["condition"])
        row = {
            "condition": report["condition"],
            "group": group,
            "total": group_summary["total"],
            "passed": group_summary["passed"],
            "failed": group_summary["failed"],
            "pass_rate": group_summary["pass_rate"],
            "low_score_count": group_summary["low_score_count"],
            "high_confidence_issue_count": group_summary["high_confidence_issue_count"],
            "failure_types": json.dumps(group_summary["failure_types"], ensure_ascii=False, sort_keys=True),
        }
        for field, value in group_summary["score_averages"].items():
            row[f"avg_{field}"] = value
        rows.append(row)
    return rows


def write_summary_csv(report: dict[str, Any], path: Path) -> None:
    rows = summary_rows(report)
    fields = [
        "condition",
        "group",
        "total",
        "passed",
        "failed",
        "pass_rate",
        "low_score_count",
        "high_confidence_issue_count",
        "failure_types",
        *(f"avg_{field}" for field in SCORE_FIELDS),
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "vlm_screenshot_scores.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_scores_csv(report, output_dir / "vlm_screenshot_scores.csv")
    write_summary_csv(report, output_dir / "vlm_screenshot_summary.csv")
    return json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--rubric", type=Path, default=RUBRIC_PATH)
    parser.add_argument("--system-prompt", type=Path, default=SYSTEM_PROMPT_PATH)
    parser.add_argument("--user-prompt", type=Path, default=USER_PROMPT_PATH)
    parser.add_argument("--retries", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        manifest_path=args.manifest,
        condition=args.condition,
        rubric_path=args.rubric,
        system_prompt_path=args.system_prompt,
        user_prompt_path=args.user_prompt,
        judge_model=args.model,
        progress=True,
        retries=args.retries,
    )
    path = write_report(report, args.output_dir)
    print(path)


if __name__ == "__main__":
    main()
