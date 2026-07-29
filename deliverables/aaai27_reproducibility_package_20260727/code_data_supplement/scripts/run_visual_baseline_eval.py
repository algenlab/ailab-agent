"""Run same-rubric visual quality evaluation for baseline screenshots."""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_vision_with_metadata, parse_json_content, vlm_config
from scripts.run_stage2_visual_eval import (
    STAGE2_EXTERNAL_PASS_THRESHOLD,
    STAGE2_EXTERNAL_SCORE_FIELDS,
    _short_string_list,
    clamp_score,
    host_path,
    repo_path,
    summarize_model_usage,
)


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_report_results(report_path: Path) -> dict[str, dict[str, Any]]:
    report = load_json(report_path)
    results = report.get("results")
    if not isinstance(results, list):
        raise ValueError(f"{report_path} missing results list")
    by_case: dict[str, dict[str, Any]] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("case_id") or "")
        if case_id:
            by_case[case_id] = row
    return by_case


def records_from_manifest(manifest_path: Path, report_path: Path, condition: str) -> list[dict[str, Any]]:
    manifest = load_json(manifest_path)
    by_case = load_report_results(report_path)
    records: list[dict[str, Any]] = []
    for item in manifest.get("screenshots") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("condition") or "") != condition:
            continue
        if str(item.get("viewport") or "desktop") != "desktop":
            continue
        case_id = str(item.get("case_id") or "")
        source = by_case.get(case_id, {})
        screenshot = host_path(item.get("screenshot"))
        screenshot_path = Path(screenshot)
        screenshot_bytes = screenshot_path.stat().st_size if screenshot_path.exists() else int(item.get("bytes") or 0)
        if not screenshot or not screenshot_path.exists() or screenshot_bytes <= 0:
            continue
        html = host_path(item.get("html"))
        browser_errors = [str(error) for error in (item.get("errors") or []) if str(error).strip()]
        records.append(
            {
                "condition": condition,
                "case_id": case_id,
                "problem_title": str(source.get("title") or item.get("title") or case_id),
                "problem_description": str(source.get("problem_description") or source.get("input_contract") or source.get("title") or item.get("title") or case_id),
                "html": html,
                "html_repo_path": repo_path(html),
                "screenshot": screenshot,
                "screenshot_repo_path": repo_path(screenshot),
                "screenshot_bytes": screenshot_bytes,
                "viewport": str(item.get("viewport") or "desktop"),
                "browser_ok": item.get("ok") is True,
                "browser_errors": browser_errors,
                "source_ok": bool(source.get("ok", item.get("source_ok", True))),
                "family": str(source.get("family") or item.get("family") or ""),
                "case_set": str(source.get("case_set") or item.get("case_set") or ""),
                "case_style": str(source.get("case_style") or item.get("case_style") or ""),
            }
        )
    return sorted(records, key=lambda row: row["case_id"])


def build_visual_prompt(record: dict[str, Any], condition_label: str) -> tuple[str, str]:
    system = (
        "你是算法可视化与数字学习资源的外部评审员。"
        "请结合 Munzner nested model、LORI learning-object review 和 Mayer multimedia learning principles "
        "评价一个算法教学页面截图。只根据截图和题目描述评分，不读取源码，不判断最终算法答案正确性。"
        "重要边界：不要把抽象算法题强行按生活场景扣分；抽象题如果视觉编码准确对应题目实体、数据结构、状态和过程，也应获得高题面贴合分。"
        "只输出一个可 json.loads 解析的 JSON 对象，不要 markdown。"
    )
    user = json.dumps(
        {
            "task": "external_visual_quality_review_same_rubric",
            "condition": condition_label,
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
                    "同一套标准用于系统和 baseline，不因 condition 名称调整分数",
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
                "html": record.get("html_repo_path") or record.get("html"),
                "screenshot": record.get("screenshot_repo_path") or record.get("screenshot"),
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return system, user


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    scores = {field: clamp_score(raw_scores.get(field)) for field in STAGE2_EXTERNAL_SCORE_FIELDS}
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, round(float(confidence), 3)))
    framework_notes = payload.get("framework_notes") if isinstance(payload.get("framework_notes"), dict) else {}
    return {
        "ok": True,
        "scores": scores,
        "overall_score": round(sum(scores.values()) / len(scores), 3),
        "framework_notes": {
            "Munzner": str(framework_notes.get("Munzner") or "")[:500],
            "LORI": str(framework_notes.get("LORI") or "")[:500],
            "Mayer": str(framework_notes.get("Mayer") or "")[:500],
        },
        "strengths": _short_string_list(payload.get("strengths")),
        "weaknesses": _short_string_list(payload.get("weaknesses")),
        "recommendation": str(payload.get("recommendation") or "")[:500],
        "confidence": confidence,
    }


def visual_ok(result: dict[str, Any]) -> bool:
    scores = result.get("scores") if isinstance(result.get("scores"), dict) else {}
    return result.get("ok") is True and all(
        int(scores.get(field) or 0) >= STAGE2_EXTERNAL_PASS_THRESHOLD
        for field in STAGE2_EXTERNAL_SCORE_FIELDS
    )


def evaluate_record(record: dict[str, Any], *, condition_label: str, model: str | None, retries: int) -> dict[str, Any]:
    screenshot_path = Path(str(record.get("screenshot") or ""))
    if not screenshot_path.exists():
        return {
            "ok": False,
            "failure_type": "visual_eval_error",
            "error": f"screenshot does not exist: {screenshot_path}",
            "model_calls": [],
        }
    image_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
    system, base_user = build_visual_prompt(record, condition_label)
    model_calls: list[dict[str, Any]] = []
    raw_response = ""
    last_error = ""
    for attempt in range(max(0, retries) + 1):
        user = base_user
        if attempt:
            user = base_user + "\n\n上一轮输出无法解析或字段不合规。现在只返回一个紧凑 JSON 对象，不要 markdown。"
        started = time.perf_counter()
        try:
            response = chat_vision_with_metadata(system, user, image_b64, model)
            raw_response = str(response.get("content") or "")
            model_call = dict(response.get("model_call") or {})
            if model_call:
                model_calls.append(model_call)
            payload = parse_json_content(raw_response)
            if not isinstance(payload, dict):
                raise ValueError("visual VLM JSON must be an object")
            normalized = normalize_payload(payload)
            normalized["model_call"] = model_call
            normalized["model_calls"] = model_calls
            normalized["raw_response"] = raw_response[:4000]
            return normalized
        except Exception as exc:
            last_error = str(exc)
            if not model_calls:
                model_calls.append(
                    {
                        "kind": "visual_baseline_eval",
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
        "failure_type": "visual_eval_error",
        "error": last_error,
        "model_calls": model_calls,
        "raw_response": raw_response[:4000],
    }


def run_visual_review(
    records: list[dict[str, Any]],
    *,
    output_dir: Path,
    condition_label: str,
    model: str | None,
    max_cases: int,
    concurrency: int,
    retries: int,
    force: bool,
) -> list[dict[str, Any]]:
    selected = records[: max_cases or len(records)]
    case_dir = output_dir / "visual_cases"
    case_dir.mkdir(parents=True, exist_ok=True)

    def run_one(record: dict[str, Any]) -> dict[str, Any]:
        case_id = record["case_id"]
        case_path = case_dir / f"{case_id}.json"
        if case_path.exists() and not force:
            cached = load_json(case_path)
            cached.update(
                {
                    "condition": condition_label,
                    "problem_title": record["problem_title"],
                    "html": record["html"],
                    "html_repo_path": record["html_repo_path"],
                    "screenshot": record["screenshot"],
                    "screenshot_repo_path": record["screenshot_repo_path"],
                    "screenshot_bytes": record.get("screenshot_bytes"),
                    "browser_ok": record.get("browser_ok") is True,
                    "browser_errors": list(record.get("browser_errors") or []),
                    "source_ok": record.get("source_ok") is True,
                    "visual_ok": visual_ok(cached),
                }
            )
            write_json(case_path, cached)
            return cached
        started = time.perf_counter()
        result = evaluate_record(record, condition_label=condition_label, model=model, retries=retries)
        result = {
            **result,
            "case_id": case_id,
            "condition": condition_label,
            "problem_title": record["problem_title"],
            "html": record["html"],
            "html_repo_path": record["html_repo_path"],
            "screenshot": record["screenshot"],
            "screenshot_repo_path": record["screenshot_repo_path"],
            "screenshot_bytes": record.get("screenshot_bytes"),
            "browser_ok": record.get("browser_ok") is True,
            "browser_errors": list(record.get("browser_errors") or []),
            "source_ok": record.get("source_ok") is True,
            "visual_ok": visual_ok(result),
            "elapsed_wall_s": round(time.perf_counter() - started, 3),
        }
        write_json(case_path, result)
        return result

    if concurrency <= 1:
        return [run_one(record) for record in selected]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {executor.submit(run_one, record): record["case_id"] for record in selected}
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: str(item.get("case_id") or ""))


def summarize_visual(results: list[dict[str, Any]], total_available: int) -> dict[str, Any]:
    ok_results = [result for result in results if result.get("ok") is True and isinstance(result.get("scores"), dict)]
    failed = [result for result in results if result.get("ok") is not True]
    browser_ok_count = sum(1 for result in results if result.get("browser_ok") is True)
    browser_error_cases = [
        {
            "case_id": result.get("case_id"),
            "errors": list(result.get("browser_errors") or []),
        }
        for result in results
        if result.get("browser_ok") is not True
    ]
    source_ok_count = sum(1 for result in results if result.get("source_ok") is True)
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
    all_pass = [result for result in ok_results if visual_ok(result)]
    return {
        "evaluated": len(results),
        "total_available": total_available,
        "ok": len(ok_results),
        "failed": len(failed),
        "source_generation_ok": source_ok_count,
        "browser_ok": browser_ok_count,
        "browser_error_count": len(results) - browser_ok_count,
        "browser_error_cases": browser_error_cases,
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
        "vlm_config": vlm_config(model=None),
        "external_frameworks": {
            "Munzner_nested_model": "problem/task and visual encoding fit",
            "LORI": "learning-object content, alignment, design, usability",
            "Mayer_multimedia_learning": "signaling, spatial contiguity, coherence",
        },
    }


def fmt_rate(count: int, total: int) -> str:
    return f"{count}/{total} ({count / total:.3f})" if total else "0/0 (0.000)"


def write_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "visual_baseline_eval_report.json"
    write_json(json_path, report)
    summary = report["visual_summary"]
    avg_scores = summary["avg_scores"]
    pass_counts = summary["dimension_pass_counts"]
    strong_counts = summary["dimension_strong_counts"]
    total = summary["evaluated"]
    lines = [
        "# Visual Baseline Evaluation",
        "",
        f"- created_at: `{report['created_at']}`",
        f"- condition: `{report['condition']}`",
        f"- screenshot_manifest: `{repo_path(report['screenshot_manifest'])}`",
        f"- source_report: `{repo_path(report['source_report'])}`",
        "",
        "## Same-Rubric External Visual Review",
        "",
        "| Metric | Avg Score | Pass >=3 | Strong >=4 |",
        "|---|---:|---:|---:|",
        f"| problem_visual_alignment | {avg_scores['problem_visual_alignment']} | {fmt_rate(pass_counts['problem_visual_alignment'], total)} | {fmt_rate(strong_counts['problem_visual_alignment'], total)} |",
        f"| algorithm_state_readability | {avg_scores['algorithm_state_readability']} | {fmt_rate(pass_counts['algorithm_state_readability'], total)} | {fmt_rate(strong_counts['algorithm_state_readability'], total)} |",
        f"| process_transition_clarity | {avg_scores['process_transition_clarity']} | {fmt_rate(pass_counts['process_transition_clarity'], total)} | {fmt_rate(strong_counts['process_transition_clarity'], total)} |",
        f"| instructional_visual_design | {avg_scores['instructional_visual_design']} | {fmt_rate(pass_counts['instructional_visual_design'], total)} | {fmt_rate(strong_counts['instructional_visual_design'], total)} |",
        "",
        f"- evaluated: `{summary['evaluated']}/{summary['total_available']}`",
        f"- source generation ok: `{fmt_rate(summary['source_generation_ok'], summary['evaluated'])}`",
        f"- browser/page-error free: `{fmt_rate(summary['browser_ok'], summary['evaluated'])}`",
        f"- valid VLM responses: `{fmt_rate(summary['ok'], summary['evaluated'])}`",
        f"- all four dimensions pass: `{fmt_rate(summary['all_dimensions_pass'], summary['evaluated'])}`",
        f"- overall average score: `{summary['overall_avg_score']}/5`",
        "",
        "Browser error cases retained for VLM screenshot scoring:",
        f"- count: `{summary['browser_error_count']}`",
        f"- cases: `{', '.join(str(item['case_id']) for item in summary['browser_error_cases']) or 'none'}`",
        "",
        "Token / time:",
        f"- calls: `{summary['model_usage']['call_count']}`",
        f"- total_tokens: `{summary['model_usage']['total_tokens']}`",
        f"- duration_s: `{summary['model_usage']['duration_s']}`",
        "",
        "## Outputs",
        "",
        f"- json: `{repo_path(json_path)}`",
        f"- markdown: `{repo_path(output_dir / 'visual_baseline_eval_report.md')}`",
        "",
    ]
    (output_dir / "visual_baseline_eval_report.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshot-manifest", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--condition", default="direct_html")
    parser.add_argument("--condition-label", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--vlm-model", default=None)
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--force", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = (ROOT / args.screenshot_manifest).resolve() if not args.screenshot_manifest.is_absolute() else args.screenshot_manifest
    source_report = (ROOT / args.source_report).resolve() if not args.source_report.is_absolute() else args.source_report
    output_dir = (ROOT / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    condition_label = str(args.condition_label or args.condition)
    records = records_from_manifest(manifest_path, source_report, args.condition)
    results = run_visual_review(
        records,
        output_dir=output_dir,
        condition_label=condition_label,
        model=args.vlm_model,
        max_cases=max(0, int(args.max_cases or 0)),
        concurrency=max(1, int(args.concurrency or 1)),
        retries=max(0, int(args.retries or 0)),
        force=bool(args.force),
    )
    summary = summarize_visual(results, total_available=len(records))
    report = {
        "kind": "visual_baseline_eval_report",
        "schema_version": "visual-baseline-eval-v1",
        "created_at": now_iso(),
        "condition": condition_label,
        "source_report": str(source_report),
        "screenshot_manifest": str(manifest_path),
        "records": records,
        "visual_results": results,
        "visual_summary": summary,
    }
    write_report(report, output_dir)
    print(
        json.dumps(
            {
                "output_dir": repo_path(output_dir),
                "condition": condition_label,
                "visual_summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
