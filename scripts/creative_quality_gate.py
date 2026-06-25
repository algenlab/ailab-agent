"""Unified quality gate for Stage2 Creative View HTML."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_vision_with_metadata, parse_json_content, vlm_config


SCENARIO_SALIENCE_THRESHOLD = 3.5
ALGORITHM_READABILITY_THRESHOLD = 3.0
MAX_REPAIR_BRIEF_CHARS = 1800

VisionJudgeFn = Callable[[str, str, str, str | None], dict[str, Any]]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def normalize_creative_vlm_payload(payload: dict[str, Any], *, model: str | None = None) -> dict[str, Any]:
    """Normalize the strict JSON shape returned by the creative VLM judge."""

    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    scenario_score = _score_value(
        payload.get("scenario_salience_score", scores.get("scenario_salience")),
        field="scenario_salience_score",
    )
    readability_score = _score_value(
        payload.get("algorithm_readability_score", scores.get("algorithm_readability")),
        field="algorithm_readability_score",
    )
    return {
        "ok": True,
        "failure_type": "",
        "scenario_salience_score": scenario_score,
        "algorithm_readability_score": readability_score,
        "is_generic_algorithm_visual": bool(payload.get("is_generic_algorithm_visual", False)),
        "algorithm_state_visible": bool(payload.get("algorithm_state_visible", True)),
        "scenario_objects_visible": _string_list(payload.get("scenario_objects_visible")),
        "issues": _issue_list(payload.get("issues")),
        "repair_advice": str(payload.get("repair_advice") or "")[:600],
        "confidence": _confidence(payload.get("confidence", 0.0)),
        "judge_model": vlm_config(model)["model"],
        "model_call": dict(payload.get("model_call") or {}),
        "model_calls": list(payload.get("model_calls") or []),
        "raw_response": str(payload.get("raw_response") or ""),
    }


def evaluate_creative_scenario_with_vlm(
    *,
    screenshot_path: Path,
    problem_description: str,
    case_id: str,
    html_path: Path | None = None,
    model: str | None = None,
    judge_call: VisionJudgeFn = chat_vision_with_metadata,
    retries: int = 1,
) -> dict[str, Any]:
    """Ask a VLM whether the Creative Stage visibly instantiates the problem story."""

    if not screenshot_path.exists():
        return _vlm_failure(
            error=f"screenshot does not exist: {screenshot_path}",
            model=model,
            model_calls=[],
            raw_response="",
        )
    image_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
    system_prompt = (
        "你是算法可视化 Stage2 Creative View 的严格视觉评审。"
        "你只根据截图和题目描述判断主视图是否真正把题目应用场景可视化，"
        "同时确认算法状态仍清楚。只返回一个可 json.loads 解析的 JSON 对象。"
    )
    user_prompt = _creative_vlm_user_prompt(
        case_id=case_id,
        problem_description=problem_description,
        html_path=html_path,
    )
    raw_response = ""
    model_calls: list[dict[str, Any]] = []
    last_error = ""
    for attempt in range(max(0, retries) + 1):
        prompt = user_prompt
        if attempt:
            prompt = "\n\n".join(
                [
                    user_prompt,
                    "上一轮输出无法解析或字段不合规。现在只返回一个紧凑 JSON 对象，不要 markdown。",
                ]
            )
        started_at = now_iso()
        started = time.perf_counter()
        try:
            response = judge_call(system_prompt, prompt, image_b64, model)
            raw_response = str(response.get("content") or "")
            model_call = dict(response.get("model_call") or {})
            if not model_call:
                model_call = {
                    "kind": "vlm_eval",
                    "model": vlm_config(model)["model"],
                    "started_at": started_at,
                    "ended_at": now_iso(),
                    "duration_s": round(time.perf_counter() - started, 3),
                    "usage_available": False,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                }
            model_calls.append(model_call)
            payload = parse_json_content(raw_response)
            if not isinstance(payload, dict):
                raise ValueError("VLM JSON must be an object")
            normalized = normalize_creative_vlm_payload(payload, model=model)
            normalized["model_call"] = model_call
            normalized["model_calls"] = model_calls
            normalized["raw_response"] = raw_response[:4000]
            return normalized
        except Exception as exc:
            last_error = str(exc)
    return _vlm_failure(error=last_error, model=model, model_calls=model_calls, raw_response=raw_response)


def build_creative_quality_report(
    *,
    playwright_row: dict[str, Any],
    problem_description: str = "",
    vlm_result: dict[str, Any] | None = None,
    require_vlm: bool = False,
    scenario_threshold: float = SCENARIO_SALIENCE_THRESHOLD,
    algorithm_threshold: float = ALGORITHM_READABILITY_THRESHOLD,
) -> dict[str, Any]:
    """Merge deterministic browser checks and optional VLM checks into one gate report."""

    row = dict(playwright_row or {})
    vlm = _normalize_vlm_result(vlm_result)
    hard_failures = _playwright_hard_failures(row)
    soft_failures: list[str] = []
    if require_vlm:
        if not vlm.get("ok"):
            hard_failures.append(str(vlm.get("failure_type") or "vlm_eval_error"))
        else:
            if float(vlm.get("scenario_salience_score") or 0.0) < scenario_threshold:
                soft_failures.append("scenario_salience_low")
            if float(vlm.get("algorithm_readability_score") or 0.0) < algorithm_threshold:
                soft_failures.append("algorithm_readability_low")
            if vlm.get("is_generic_algorithm_visual"):
                soft_failures.append("generic_algorithm_visual")
            if vlm.get("algorithm_state_visible") is False:
                soft_failures.append("algorithm_state_not_visible")

    hard_failures = _dedupe(hard_failures)
    soft_failures = _dedupe(soft_failures)
    report = {
        "kind": "creative_quality_gate",
        "schema_version": "creative-quality-gate-v1",
        "created_at": now_iso(),
        "case_id": row.get("case_id", ""),
        "html": row.get("html", ""),
        "problem_description": problem_description,
        "creative_quality_ok": not hard_failures and not soft_failures,
        "hard_failures": hard_failures,
        "soft_failures": soft_failures,
        "playwright": _compact_playwright_row(row),
        "vlm": vlm,
        "require_vlm": require_vlm,
        "thresholds": {
            "scenario_salience": scenario_threshold,
            "algorithm_readability": algorithm_threshold,
        },
    }
    report["score"] = creative_quality_score(report)
    report["repair_brief"] = _repair_brief(report)
    return report


def run_creative_quality_gate(
    html_path: Path,
    output_dir: Path,
    *,
    problem_description: str = "",
    wait_ms: int = 300,
    stage_audit_max_frames: int = 4,
    enable_vlm: bool = False,
    vlm_model: str | None = None,
    vlm_retries: int = 1,
) -> dict[str, Any]:
    """Run Playwright and optional VLM checks for one Creative View HTML file."""

    from scripts.audit_creative_visual_renderer import audit_html_path

    output_dir.mkdir(parents=True, exist_ok=True)
    browser_dir = output_dir / "browser"
    browser_dir.mkdir(parents=True, exist_ok=True)
    playwright_row = audit_html_path(
        html_path,
        browser_dir,
        wait_ms=wait_ms,
        require_stage_visual_quality=True,
        stage_audit_max_frames=stage_audit_max_frames,
    )
    vlm_result: dict[str, Any] | None = None
    if enable_vlm:
        screenshot = Path(str(playwright_row.get("screenshot") or ""))
        vlm_result = evaluate_creative_scenario_with_vlm(
            screenshot_path=screenshot,
            problem_description=problem_description,
            case_id=str(playwright_row.get("case_id") or html_path.stem),
            html_path=html_path,
            model=vlm_model,
            retries=vlm_retries,
        )
    report = build_creative_quality_report(
        playwright_row=playwright_row,
        problem_description=problem_description,
        vlm_result=vlm_result,
        require_vlm=enable_vlm,
    )
    (output_dir / "creative_quality_gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def compact_creative_quality_report(report: dict[str, Any]) -> dict[str, Any]:
    """Return the failure subset that is useful for LLM repair prompts."""

    playwright = report.get("playwright") if isinstance(report.get("playwright"), dict) else {}
    vlm = report.get("vlm") if isinstance(report.get("vlm"), dict) else {}
    return {
        "kind": "creative_quality_gate",
        "creative_quality_ok": bool(report.get("creative_quality_ok")),
        "score": int(report.get("score") or 0),
        "hard_failures": list(report.get("hard_failures") or []),
        "soft_failures": list(report.get("soft_failures") or []),
        "repair_brief": str(report.get("repair_brief") or "")[:MAX_REPAIR_BRIEF_CHARS],
        "playwright": playwright,
        "vlm": {
            key: vlm.get(key)
            for key in (
                "ok",
                "failure_type",
                "scenario_salience_score",
                "algorithm_readability_score",
                "is_generic_algorithm_visual",
                "algorithm_state_visible",
                "scenario_objects_visible",
                "issues",
                "repair_advice",
                "confidence",
                "judge_model",
                "error",
            )
            if key in vlm
        },
    }


def creative_quality_score(report: dict[str, Any]) -> int:
    """Higher is better. Used to keep the best candidate during repair loops."""

    if "playwright" in report or "vlm" in report:
        playwright = report.get("playwright") if isinstance(report.get("playwright"), dict) else {}
        vlm = report.get("vlm") if isinstance(report.get("vlm"), dict) else {}
        hard_failures = list(report.get("hard_failures") or [])
        soft_failures = list(report.get("soft_failures") or [])
    else:
        playwright = _compact_playwright_row(report)
        vlm = {}
        hard_failures = _playwright_hard_failures(report)
        soft_failures = []
    score = 100
    if hard_failures:
        score -= min(55, 18 * len(hard_failures))
    if soft_failures:
        score -= min(35, 15 * len(soft_failures))
    if not playwright.get("browser_smoke_ok", False):
        score -= 18
    if not playwright.get("stage_visual_quality_ok", False):
        score -= 14
    score -= min(22, int(playwright.get("stage_clipped_count") or 0) * 8)
    score -= min(18, int(playwright.get("stage_overlap_count") or 0) * 3)
    score -= min(18, int(playwright.get("stage_text_occlusion_count") or 0) * 5)
    if vlm.get("ok"):
        scenario = float(vlm.get("scenario_salience_score") or 0.0)
        readability = float(vlm.get("algorithm_readability_score") or 0.0)
        score -= max(0, int(round((5 - scenario) * 6)))
        score -= max(0, int(round((5 - readability) * 4)))
        if vlm.get("is_generic_algorithm_visual"):
            score -= 25
        if vlm.get("algorithm_state_visible") is False:
            score -= 12
    elif report.get("require_vlm"):
        score -= 25
    return max(0, min(100, int(score)))


def is_better_creative_quality_report(candidate: dict[str, Any], incumbent: dict[str, Any] | None) -> bool:
    if incumbent is None:
        return True
    return creative_quality_score(candidate) > creative_quality_score(incumbent)


def _creative_vlm_user_prompt(*, case_id: str, problem_description: str, html_path: Path | None) -> str:
    return "\n".join(
        [
            f"case_id: {case_id}",
            f"html: {html_path or ''}",
            "题目/创意场景描述:",
            problem_description or "(未提供)",
            "",
            "请评估截图中的主舞台，不评价外壳面板本身。重点判断：",
            "1. 场景是否一眼可见，是否有题目描述中的业务对象、标签和动作。",
            "2. 是否只是普通数组/表格/图结构加少量文字或 emoji。",
            "3. 算法当前状态、路径/窗口/队列/匹配/DP 等信息是否仍然清楚。",
            "",
            "只返回 JSON，字段固定如下：",
            "{",
            '  "scenario_salience_score": 1-5,',
            '  "algorithm_readability_score": 1-5,',
            '  "is_generic_algorithm_visual": true|false,',
            '  "algorithm_state_visible": true|false,',
            '  "scenario_objects_visible": ["不超过6个可见场景对象或动作"],',
            '  "issues": ["不超过4条具体问题"],',
            '  "repair_advice": "一句给生成器的修复建议",',
            '  "confidence": 0-1',
            "}",
        ]
    )


def _normalize_vlm_result(vlm_result: dict[str, Any] | None) -> dict[str, Any]:
    if not vlm_result:
        return {"ok": False, "failure_type": "vlm_skipped", "status": "skipped"}
    result = dict(vlm_result)
    if result.get("ok") is True and "scenario_salience_score" in result:
        return result
    if result.get("ok") is False:
        result.setdefault("failure_type", "vlm_eval_error")
        return result
    try:
        return normalize_creative_vlm_payload(result, model=str(result.get("judge_model") or "") or None)
    except Exception as exc:
        return {
            "ok": False,
            "failure_type": "vlm_eval_error",
            "error": str(exc),
            "raw_response": str(result.get("raw_response") or "")[:4000],
        }


def _playwright_hard_failures(row: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    failures.extend(str(item) for item in (row.get("failure_categories") or []) if str(item))
    for key in ("page_load_ok", "visual_non_empty", "frame_switch_ok", "main_area_not_blank", "screenshot_non_empty"):
        if row.get(key) is False:
            failures.append(key)
    if row.get("trace_mutation_detected"):
        failures.append("trace_mutation_detected")
    if int(row.get("console_error_count") or 0) > 0:
        failures.append("console_errors")
    if int(row.get("page_error_count") or 0) > 0:
        failures.append("page_errors")
    if row.get("stage_visual_quality_ok") is False:
        failures.append("stage_visual_quality_ok")
    if row.get("failure_reason"):
        failures.append(str(row.get("failure_reason")))
    return _dedupe(failures)


def _compact_playwright_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "case_id",
        "html",
        "creative_ok",
        "browser_smoke_ok",
        "page_load_ok",
        "console_error_count",
        "page_error_count",
        "visual_non_empty",
        "frame_switch_ok",
        "range_control_ok",
        "trace_mutation_detected",
        "main_area_not_blank",
        "screenshot_non_empty",
        "stage_visual_quality_ok",
        "strict_visual_quality_ok",
        "stage_audited_frame_count",
        "stage_audited_frames",
        "stage_overlap_count",
        "stage_permitted_overlap_count",
        "stage_clipped_count",
        "stage_text_occlusion_count",
        "stage_layout_issues",
        "stage_permitted_layout_issues",
        "stage_layout_frame_reports",
        "console_errors",
        "page_errors",
        "failure_categories",
        "failure_reason",
        "screenshot",
    ]
    return {key: row.get(key) for key in keys if key in row}


def _repair_brief(report: dict[str, Any]) -> str:
    lines = [
        f"creative_quality_ok={bool(report.get('creative_quality_ok'))}",
        f"score={report.get('score')}",
    ]
    hard = report.get("hard_failures") or []
    soft = report.get("soft_failures") or []
    if hard:
        lines.append("hard_failures: " + ", ".join(str(item) for item in hard))
    if soft:
        lines.append("soft_failures: " + ", ".join(str(item) for item in soft))
    playwright = report.get("playwright") or {}
    if playwright:
        lines.append(
            "playwright: "
            f"browser={playwright.get('browser_smoke_ok')} "
            f"stage={playwright.get('stage_visual_quality_ok')} "
            f"overlap={playwright.get('stage_overlap_count', 0)} "
            f"clipped={playwright.get('stage_clipped_count', 0)} "
            f"text_occlusion={playwright.get('stage_text_occlusion_count', 0)} "
            f"screenshot={playwright.get('screenshot', '')}"
        )
        issues = playwright.get("stage_layout_issues") or []
        if issues:
            lines.append("layout_issues: " + json.dumps(issues[:6], ensure_ascii=False))
    vlm = report.get("vlm") or {}
    if vlm and vlm.get("status") != "skipped":
        lines.append(
            "vlm: "
            f"ok={vlm.get('ok')} "
            f"scenario={vlm.get('scenario_salience_score')} "
            f"algorithm={vlm.get('algorithm_readability_score')} "
            f"generic={vlm.get('is_generic_algorithm_visual')} "
            f"objects={', '.join(str(item) for item in (vlm.get('scenario_objects_visible') or [])[:6])}"
        )
        if vlm.get("issues"):
            lines.append("vlm_issues: " + "; ".join(str(item) for item in (vlm.get("issues") or [])[:4]))
        if vlm.get("repair_advice"):
            lines.append("vlm_repair_advice: " + str(vlm.get("repair_advice")))
        if vlm.get("error"):
            lines.append("vlm_error: " + str(vlm.get("error")))
    return "\n".join(lines)[:MAX_REPAIR_BRIEF_CHARS]


def _vlm_failure(
    *,
    error: str,
    model: str | None,
    model_calls: list[dict[str, Any]],
    raw_response: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "failure_type": "vlm_eval_error",
        "error": error,
        "judge_model": vlm_config(model)["model"],
        "model_call": model_calls[-1] if model_calls else {},
        "model_calls": model_calls,
        "raw_response": raw_response[:4000],
    }


def _score_value(value: Any, *, field: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number from 1 to 5")
    score = float(value)
    if score < 1 or score > 5:
        raise ValueError(f"{field} must be a number from 1 to 5")
    return int(score) if float(score).is_integer() else round(score, 2)


def _confidence(value: Any) -> float:
    if not isinstance(value, (int, float)):
        return 0.0
    return max(0.0, min(1.0, round(float(value), 3)))


def _string_list(value: Any, *, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:80] for item in value if str(item).strip()][:limit]


def _issue_list(value: Any, *, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    issues: list[str] = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("message") or item.get("issue") or item.get("text") or "").strip()
        else:
            text = str(item).strip()
        if text:
            issues.append(text[:180])
    return issues[:limit]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def collect_html_paths(html_dir: Path, pattern: str) -> list[Path]:
    return sorted(path for path in html_dir.glob(pattern) if path.is_file() and path.suffix.lower() == ".html")


def _write_cli_report(reports: list[dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for item in reports if item.get("creative_quality_ok"))
    report = {
        "schema_version": "creative-quality-gate-report-v1",
        "created_at": now_iso(),
        "summary": {
            "total": len(reports),
            "creative_quality_ok": passed,
            "failed": len(reports) - passed,
            "creative_quality_ok_rate": passed / len(reports) if reports else 0.0,
        },
        "results": reports,
    }
    json_path = output_dir / "creative_quality_gate_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = output_dir / "creative_quality_gate_report.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "creative_quality_ok",
                "score",
                "hard_failures",
                "soft_failures",
                "html",
            ],
        )
        writer.writeheader()
        for item in reports:
            writer.writerow(
                {
                    "case_id": item.get("case_id", ""),
                    "creative_quality_ok": item.get("creative_quality_ok", False),
                    "score": item.get("score", 0),
                    "hard_failures": "; ".join(item.get("hard_failures") or []),
                    "soft_failures": "; ".join(item.get("soft_failures") or []),
                    "html": item.get("html", ""),
                }
            )
    return json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", action="append", type=Path, default=[], help="HTML file to audit; repeatable")
    parser.add_argument("--html-dir", type=Path, default=None, help="Directory containing Creative View HTML files")
    parser.add_argument("--html-glob", default="*_creative_stage.html")
    parser.add_argument("--output-dir", type=Path, default=Path("output/creative_quality_gate"))
    parser.add_argument("--problem", default="", help="Problem/story description used by the VLM gate")
    parser.add_argument("--wait-ms", type=int, default=300)
    parser.add_argument("--stage-audit-max-frames", type=int, default=4)
    parser.add_argument("--enable-vlm", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--vlm-model", default=None)
    parser.add_argument("--fail-on-violations", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = [path.resolve() for path in args.html]
    if args.html_dir:
        paths.extend(collect_html_paths(args.html_dir.resolve(), args.html_glob))
    paths = sorted(dict.fromkeys(paths))
    if not paths:
        raise SystemExit("no HTML files provided")
    output_dir = args.output_dir.resolve()
    reports = []
    for index, html_path in enumerate(paths, start=1):
        case_output_dir = output_dir / html_path.stem
        print(f"CREATIVE_QUALITY {index}/{len(paths)} {html_path.name}", flush=True)
        reports.append(
            run_creative_quality_gate(
                html_path,
                case_output_dir,
                problem_description=args.problem,
                wait_ms=int(args.wait_ms),
                stage_audit_max_frames=int(args.stage_audit_max_frames),
                enable_vlm=bool(args.enable_vlm),
                vlm_model=args.vlm_model,
            )
        )
    report_path = _write_cli_report(reports, output_dir)
    summary = json.loads(report_path.read_text(encoding="utf-8"))["summary"]
    print(json.dumps({"report": str(report_path), "summary": summary}, ensure_ascii=False, indent=2))
    if args.fail_on_violations and summary["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
