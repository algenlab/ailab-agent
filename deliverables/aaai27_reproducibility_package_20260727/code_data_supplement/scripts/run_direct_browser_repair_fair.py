"""Run a fair, adaptive Direct-BrowserRepair budget experiment.

Each task starts from the same frozen Direct page. A repair call is made only
after a real browser inspection, successful pages stop immediately, and the
best audited artifact is retained for every repair budget.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import json
import os
import queue
import statistics
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.language import english_only_errors, english_output_requirement, normalize_output_language
from benchmark.cases import BenchmarkCase, benchmark_cases
from llm_client import _model_name, chat_text_with_metadata, llm_config
from scripts.build_browser_repair_feedback import collect_browser_feedback_with_browser
from scripts.run_direct_browser_repair_baseline import (
    FEEDBACK_FIELDS,
    _display_path,
    _initial_attempt,
    _repo_path,
    _safe_feedback,
    _sha256_text,
    _write_json,
    external_resource_urls,
)
from scripts.run_direct_html_baseline import _system_prompt, extract_html
from scripts.run_interaction_semantic_eval import MACHINE_BOOL_KEYS, audit_browser_record
from scripts.run_llm_benchmark import ENGLISH_CASE_OVERRIDES_PATH, apply_case_overrides, load_case_overrides


DEFAULT_SOURCE_REPORT = ROOT / "output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json"
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/direct_browser_repair_fair_20260723"
DEFAULT_CONCURRENCY = 32
DEFAULT_BROWSER_WORKERS = 8
DEFAULT_REPAIR_BUDGETS = (0, 1, 2, 3, 5)
DEFAULT_REPAIR_MAX_TOKENS = 32768
DEFAULT_API_TIMEOUT_S = 1800
DEFAULT_BROWSER_TIMEOUT_MS = 120000
DEFAULT_API_RETRIES = 5
DEFAULT_TOKEN_TARGET = 300000


def build_fair_repair_prompt(
    *,
    title: str,
    problem: str,
    family: str,
    strategy: str,
    input_data: Any,
    expected: Any,
    previous_html: str,
    feedback: dict[str, Any],
    repair_round: int,
    language: str = "zh",
) -> str:
    """Build a repair prompt using the complete prior artifact and generic feedback only."""
    safe_feedback = _safe_feedback(feedback)
    if normalize_output_language(language) == "en":
        return "\n".join(
            [
                f"This is browser-feedback repair round {repair_round} for a Direct HTML page.",
                "Return only one complete, self-contained repaired HTML file; do not use Markdown.",
                f"Title: {title}",
                f"Problem: {problem}",
                f"Algorithm family: {family}",
                f"Strategy hint: {strategy}",
                f"Input JSON: {json.dumps(input_data, ensure_ascii=False)}",
                f"Expected output JSON: {json.dumps(expected, ensure_ascii=False)}",
                "Generic observations collected from a real browser:",
                json.dumps(safe_feedback, ensure_ascii=False, indent=2),
                "Repair requirements:",
                "- Preserve a complete algorithm-tutoring page with visible steps, state, code, explanations, navigation, a timeline, prediction checkpoints, immediate feedback, hints, show-answer actions, and a visible learning log.",
                "- Keep the authoritative final result visible and keep all teaching content consistent with the concrete input and expected output.",
                "- Fix browser errors and controls that do not produce a visible state change.",
                "- Work fully offline: inline all CSS and JavaScript and load no external resources.",
                "- Preserve useful content from the prior page. Do not shorten or replace a working section merely to reduce output length.",
                "- " + english_output_requirement(),
                "Complete previous HTML (preserve all necessary content):",
                previous_html,
            ]
        )
    return "\n".join(
        [
            f"这是 Direct HTML 的第 {repair_round} 次浏览器反馈修复。",
            "只输出一个完整、可离线运行的单文件 HTML，不要 Markdown。",
            f"题目：{title}",
            f"描述：{problem}",
            f"算法族：{family}",
            f"策略提示：{strategy}",
            f"输入 JSON：{json.dumps(input_data, ensure_ascii=False)}",
            f"期望输出 JSON：{json.dumps(expected, ensure_ascii=False)}",
            "真实浏览器收集的通用观察：",
            json.dumps(safe_feedback, ensure_ascii=False, indent=2),
            "修复要求：",
            "1. 保持完整的算法教学页面：可见步骤、状态、代码、解释、前后导航、时间线、预测问题、即时反馈、提示、显示答案和学习记录。",
            "2. 明确展示最终返回值，并保证教学内容与给定输入和期望输出一致。",
            "3. 修复浏览器错误和点击后没有可见变化的控件。",
            "4. 页面必须完全离线运行；CSS 和 JavaScript 全部内联，不加载任何外部资源。",
            "5. 保留上一版中已经有效的内容，不要为了缩短输出而删除或替换正常工作的部分。",
            "完整上一版 HTML（必须保留所有必要内容）：",
            previous_html,
        ]
    )


def machine_score(audit: dict[str, Any]) -> int:
    return sum(audit.get(key) is True for key in MACHINE_BOOL_KEYS)


def choose_best_attempt(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    if not attempts:
        return {}
    return min(
        attempts,
        key=lambda attempt: (
            -machine_score(attempt.get("audit") or {}),
            int(attempt.get("call_index") or 10**9),
        ),
    )


def machine_transition(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_ok = before.get("machine_ok") is True
    after_ok = after.get("machine_ok") is True
    return {
        "overall": ("pass" if before_ok else "fail") + "_to_" + ("pass" if after_ok else "fail"),
        "before_score": machine_score(before),
        "after_score": machine_score(after),
        "fail_to_pass": [key for key in MACHINE_BOOL_KEYS if before.get(key) is not True and after.get(key) is True],
        "pass_to_fail": [key for key in MACHINE_BOOL_KEYS if before.get(key) is True and after.get(key) is not True],
    }


def run_repair_policy(
    *,
    initial_attempt: dict[str, Any],
    repair_budget: int,
    audit_attempt: Callable[[dict[str, Any]], dict[str, Any]],
    collect_feedback: Callable[[dict[str, Any]], dict[str, Any]],
    repair_attempt: Callable[[dict[str, Any], dict[str, Any], int], dict[str, Any]],
) -> dict[str, Any]:
    if repair_budget < 0:
        raise ValueError("repair_budget must be >= 0")
    attempts = [initial_attempt]
    transitions: list[dict[str, Any]] = []
    initial_attempt["audit"] = audit_attempt(initial_attempt)
    if initial_attempt["audit"].get("machine_ok") is True:
        return {
            "attempts": attempts,
            "best_attempt": initial_attempt,
            "final_attempt": initial_attempt,
            "repair_calls_used": 0,
            "stop_reason": "machine_ok",
            "transitions": transitions,
        }
    for repair_round in range(1, repair_budget + 1):
        previous = attempts[-1]
        feedback = collect_feedback(previous)
        previous["feedback_data"] = feedback
        current = repair_attempt(previous, feedback, repair_round)
        current["audit"] = audit_attempt(current)
        transition = machine_transition(previous["audit"], current["audit"])
        transition.update(
            {
                "repair_round": repair_round,
                "from_call_index": int(previous.get("call_index") or repair_round),
                "to_call_index": int(current.get("call_index") or repair_round + 1),
            }
        )
        transitions.append(transition)
        attempts.append(current)
        if current["audit"].get("machine_ok") is True:
            return {
                "attempts": attempts,
                "best_attempt": choose_best_attempt(attempts),
                "final_attempt": current,
                "repair_calls_used": repair_round,
                "stop_reason": "machine_ok",
                "transitions": transitions,
            }
    return {
        "attempts": attempts,
        "best_attempt": choose_best_attempt(attempts),
        "final_attempt": attempts[-1],
        "repair_calls_used": repair_budget,
        "stop_reason": "repair_budget_exhausted",
        "transitions": transitions,
    }


@dataclass
class _BrowserJob:
    kind: str
    payload: dict[str, Any]
    done: threading.Event = field(default_factory=threading.Event)
    result: dict[str, Any] | None = None
    error: BaseException | None = None


class BrowserPool:
    """Run Playwright only inside dedicated worker threads and reuse browsers."""

    def __init__(self, workers: int, *, timeout_ms: int) -> None:
        self.workers = max(1, workers)
        self.timeout_ms = timeout_ms
        self.jobs: queue.Queue[_BrowserJob | None] = queue.Queue()
        self.threads = [
            threading.Thread(target=self._worker, name=f"browser-worker-{index + 1}", daemon=True)
            for index in range(self.workers)
        ]
        for thread in self.threads:
            thread.start()

    def _worker(self) -> None:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executable = os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE", "")
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=executable if executable and Path(executable).exists() else None,
                args=["--no-sandbox"],
            )
            try:
                while True:
                    job = self.jobs.get()
                    if job is None:
                        return
                    try:
                        if job.kind == "audit":
                            job.result = audit_browser_record(browser, job.payload["row"])
                        elif job.kind == "feedback":
                            job.result = collect_browser_feedback_with_browser(
                                browser,
                                Path(job.payload["html_path"]),
                                screenshot_path=Path(job.payload["screenshot_path"]),
                                timeout_ms=self.timeout_ms,
                            )
                        else:
                            raise ValueError(f"unknown browser job: {job.kind}")
                    except BaseException as exc:
                        job.error = exc
                    finally:
                        job.done.set()
            finally:
                browser.close()

    def submit(self, kind: str, **payload: Any) -> dict[str, Any]:
        job = _BrowserJob(kind=kind, payload=payload)
        self.jobs.put(job)
        job.done.wait()
        if job.error is not None:
            raise RuntimeError(f"browser {kind} failed: {type(job.error).__name__}: {job.error}") from job.error
        return job.result or {}

    def close(self) -> None:
        for _ in self.threads:
            self.jobs.put(None)
        for thread in self.threads:
            thread.join()


def _write_attempt(attempt: dict[str, Any]) -> None:
    metadata_path = _repo_path(str(attempt["json"]))
    _write_json(metadata_path, attempt)


def _audit_attempt(
    browser_pool: BrowserPool,
    row: dict[str, Any],
    attempt: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(attempt.get("audit"), dict):
        return copy.deepcopy(attempt["audit"])
    audit_path = _repo_path(str(attempt["json"])).with_name(
        _repo_path(str(attempt["json"])).stem + ".machine.json"
    )
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    else:
        audit_row = {
            **{key: copy.deepcopy(value) for key, value in row.items() if key not in {"model_calls"}},
            "condition": "direct_html",
            "html": attempt["html"],
            "json": attempt["json"],
        }
        audit = browser_pool.submit("audit", row=audit_row)
        _write_json(audit_path, audit)
    compact = {
        key: copy.deepcopy(audit.get(key))
        for key in ["machine_ok", *MACHINE_BOOL_KEYS, "console_page_errors", "feedback_preview"]
        if key in audit
    }
    attempt["audit"] = compact
    attempt["audit_path"] = _display_path(audit_path)
    _write_attempt(attempt)
    return compact


def _collect_feedback(
    browser_pool: BrowserPool,
    attempt: dict[str, Any],
) -> dict[str, Any]:
    metadata_path = _repo_path(str(attempt["json"]))
    feedback_path = metadata_path.with_name(metadata_path.stem + ".feedback.json")
    screenshot_path = metadata_path.with_name(metadata_path.stem + ".png")
    if feedback_path.is_file():
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
    else:
        feedback = browser_pool.submit(
            "feedback",
            html_path=_repo_path(str(attempt["html"])),
            screenshot_path=screenshot_path,
        )
        _write_json(feedback_path, feedback)
    attempt["feedback"] = _display_path(feedback_path)
    attempt["screenshot"] = _display_path(screenshot_path)
    _write_attempt(attempt)
    return feedback


def _fair_repair_attempt(
    *,
    row: dict[str, Any],
    case: BenchmarkCase,
    previous: dict[str, Any],
    feedback: dict[str, Any],
    repair_round: int,
    output_dir: Path,
    model: str,
    language: str,
) -> dict[str, Any]:
    call_index = repair_round + 1
    case_dir = output_dir / "cases" / case.id
    html_path = case_dir / f"attempt_{call_index:02d}.html"
    metadata_path = case_dir / f"attempt_{call_index:02d}.json"
    prompt_path = case_dir / f"attempt_{call_index:02d}.prompt.txt"
    raw_path = case_dir / f"attempt_{call_index:02d}.raw.txt"
    if metadata_path.is_file() and html_path.is_file():
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    previous_html = _repo_path(str(previous["html"])).read_text(encoding="utf-8")
    prompt = build_fair_repair_prompt(
        title=case.title,
        problem=case.problem,
        family=case.family,
        strategy=case.strategy,
        input_data=row.get("input_data"),
        expected=row.get("expected"),
        previous_html=previous_html,
        feedback=feedback,
        repair_round=repair_round,
        language=language,
    )
    case_dir.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    started = time.time()
    response = chat_text_with_metadata(
        _system_prompt(language),
        prompt,
        model=model,
        kind="direct_browser_repair_fair",
    )
    raw = str(response.get("content") or "")
    raw_path.write_text(raw, encoding="utf-8")
    html = extract_html(raw)
    fallback = not bool(html)
    if fallback:
        html = previous_html
    language_errors = english_only_errors(html, label=f"{case.id} fair browser-repair HTML") if language == "en" else []
    if language_errors:
        raise ValueError("; ".join(language_errors))
    html_path.write_text(html, encoding="utf-8")
    attempt = {
        "call_index": call_index,
        "repair_round": repair_round,
        "kind": "direct_browser_repair_fair",
        "prompt": _display_path(prompt_path),
        "prompt_sha256": _sha256_text(prompt),
        "previous_html_sha256": previous.get("html_sha256"),
        "complete_previous_html_in_prompt": previous_html in prompt,
        "raw_response": _display_path(raw_path),
        "html": _display_path(html_path),
        "html_sha256": _sha256_text(html),
        "html_chars": len(html),
        "json": _display_path(metadata_path),
        "model_call": copy.deepcopy(response.get("model_call") or {}),
        "duration_s": round(time.time() - started, 3),
        "external_resource_urls": external_resource_urls(html),
        "fallback_to_previous_html": fallback,
    }
    _write_json(metadata_path, attempt)
    return attempt


def _cost_summary(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    initial = attempts[:1]
    repairs = attempts[1:]

    def total(group: list[dict[str, Any]], key: str) -> int:
        return sum(int((attempt.get("model_call") or {}).get(key) or 0) for attempt in group)

    return {
        "initial_prompt_tokens": total(initial, "prompt_tokens"),
        "initial_completion_tokens": total(initial, "completion_tokens"),
        "initial_total_tokens": total(initial, "total_tokens"),
        "repair_prompt_tokens": total(repairs, "prompt_tokens"),
        "repair_completion_tokens": total(repairs, "completion_tokens"),
        "repair_total_tokens": total(repairs, "total_tokens"),
        "repair_generation_seconds": round(
            sum(float((attempt.get("model_call") or {}).get("duration_s") or attempt.get("duration_s") or 0.0) for attempt in repairs),
            3,
        ),
    }


def run_case(
    row: dict[str, Any],
    *,
    case: BenchmarkCase,
    output_dir: Path,
    repair_budget: int,
    browser_pool: BrowserPool,
    model: str,
    language: str,
) -> dict[str, Any]:
    case_result_path = output_dir / "cases" / case.id / "case_result.json"
    if case_result_path.is_file():
        existing = json.loads(case_result_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete" and int(existing.get("repair_budget") or -1) >= repair_budget:
            return existing

    initial = _initial_attempt(
        row=row,
        case=case,
        output_dir=output_dir,
        model=model,
        language=language,
        force_regenerate=False,
    )
    if initial.get("source_kind") != "frozen_original_first_call":
        raise RuntimeError(f"{case.id}: frozen initial Direct artifact is missing")

    result = run_repair_policy(
        initial_attempt=initial,
        repair_budget=repair_budget,
        audit_attempt=lambda attempt: _audit_attempt(browser_pool, row, attempt),
        collect_feedback=lambda attempt: _collect_feedback(browser_pool, attempt),
        repair_attempt=lambda previous, feedback, repair_round: _fair_repair_attempt(
            row=row,
            case=case,
            previous=previous,
            feedback=feedback,
            repair_round=repair_round,
            output_dir=output_dir,
            model=model,
            language=language,
        ),
    )
    attempts = result["attempts"]
    best = result["best_attempt"]
    payload = {
        **{key: copy.deepcopy(value) for key, value in row.items() if key not in {"html", "json", "model_calls"}},
        "condition": "direct_browser_repair_fair",
        "baseline": "direct_browser_repair",
        "status": "complete",
        "repair_budget": repair_budget,
        "first_pass_machine_ok": attempts[0].get("audit", {}).get("machine_ok") is True,
        "final_machine_ok": best.get("audit", {}).get("machine_ok") is True,
        "repair_calls_used": result["repair_calls_used"],
        "stop_reason": result["stop_reason"],
        "best_call_index": int(best.get("call_index") or 0),
        "final_call_index": int(result["final_attempt"].get("call_index") or 0),
        "html": best.get("html", ""),
        "json": best.get("json", ""),
        "attempts": attempts,
        "transitions": result["transitions"],
        "cost": _cost_summary(attempts),
    }
    _write_json(case_result_path, payload)
    return payload


def _attempts_within_budget(row: dict[str, Any], repair_budget: int) -> list[dict[str, Any]]:
    return [
        attempt
        for attempt in row.get("attempts") or []
        if int(attempt.get("call_index") or 0) <= repair_budget + 1
    ]


def build_budget_report(
    *,
    results: list[dict[str, Any]],
    repair_budget: int,
    source_report: Path,
    model: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for source in sorted(results, key=lambda item: str(item.get("case_id") or "")):
        attempts = _attempts_within_budget(source, repair_budget)
        selected = choose_best_attempt(attempts)
        row = {
            **{key: copy.deepcopy(value) for key, value in source.items() if key not in {"attempts", "transitions", "cost", "html", "json"}},
            "condition": f"direct_browser_repair_budget_{repair_budget}",
            "baseline": "direct_browser_repair",
            "repair_budget": repair_budget,
            "selected_call_index": int(selected.get("call_index") or 0),
            "repair_calls_used": max(0, len(attempts) - 1),
            "html": selected.get("html", ""),
            "json": selected.get("json", ""),
            "ok": bool(selected.get("html")),
            "machine_ok": selected.get("audit", {}).get("machine_ok") is True,
            "model_calls": [copy.deepcopy(attempt.get("model_call") or {}) for attempt in attempts],
        }
        rows.append(row)
        records.append(
            {
                **row,
                **copy.deepcopy(selected.get("audit") or {}),
            }
        )
    condition = f"direct_browser_repair_budget_{repair_budget}"
    report = {
        "kind": "llm_benchmark_report",
        "condition": condition,
        "source_report": _display_path(source_report),
        "model": model,
        "repair_budget": repair_budget,
        "protocol": "early_stop_best_so_far",
        "total": len(rows),
        "passed": sum(row["ok"] for row in rows),
        "machine_ok": sum(row["machine_ok"] for row in rows),
        "results": rows,
    }
    audit_report = {
        "kind": "interaction_semantic_eval_report",
        "condition": condition,
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "summary": {
            condition: {
                "total": len(records),
                "machine_ok": sum(record.get("machine_ok") is True for record in records),
                **{
                    key: sum(record.get(key) is True for record in records)
                    for key in MACHINE_BOOL_KEYS
                },
            }
        },
        "records": records,
    }
    return report, audit_report


def _number_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "median": 0.0, "sum": 0.0}
    return {
        "mean": round(statistics.fmean(values), 3),
        "median": round(float(statistics.median(values)), 3),
        "sum": round(float(sum(values)), 3),
    }


def _write_transition_csv(output_dir: Path, results: list[dict[str, Any]]) -> None:
    path = output_dir / "per_task_transitions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "repair_round",
                "from_call_index",
                "to_call_index",
                "overall",
                "before_score",
                "after_score",
                "fail_to_pass",
                "pass_to_fail",
            ],
        )
        writer.writeheader()
        for row in sorted(results, key=lambda item: str(item.get("case_id") or "")):
            for transition in row.get("transitions") or []:
                writer.writerow(
                    {
                        "case_id": row.get("case_id"),
                        **{key: transition.get(key) for key in writer.fieldnames if key != "case_id"},
                        "fail_to_pass": ";".join(transition.get("fail_to_pass") or []),
                        "pass_to_fail": ";".join(transition.get("pass_to_fail") or []),
                    }
                )


def _write_frozen_initial_manifest(output_dir: Path, results: list[dict[str, Any]]) -> None:
    path = output_dir / "frozen_initial_manifest.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case_id", "source_kind", "source_html", "html", "html_sha256", "html_chars"],
        )
        writer.writeheader()
        for row in sorted(results, key=lambda item: str(item.get("case_id") or "")):
            initial = (row.get("attempts") or [{}])[0]
            writer.writerow(
                {
                    "case_id": row.get("case_id"),
                    **{key: initial.get(key) for key in writer.fieldnames if key != "case_id"},
                }
            )


def write_reports(
    *,
    output_dir: Path,
    source_report: Path,
    results: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    budgets: tuple[int, ...],
    model: str,
    config: dict[str, Any],
    started_at: str,
) -> dict[str, Any]:
    ordered = sorted(results, key=lambda row: str(row.get("case_id") or ""))
    repair_calls = [float(row.get("repair_calls_used") or 0) for row in ordered]
    repair_tokens = [float((row.get("cost") or {}).get("repair_total_tokens") or 0) for row in ordered]
    repair_seconds = [float((row.get("cost") or {}).get("repair_generation_seconds") or 0) for row in ordered]
    transitions = [transition for row in ordered for transition in row.get("transitions") or []]
    budget_rows = []
    for budget in budgets:
        report, audit = build_budget_report(
            results=ordered,
            repair_budget=budget,
            source_report=source_report,
            model=model,
        )
        budget_dir = output_dir / "budget_reports" / f"repair_budget_{budget}"
        audit_dir = output_dir / "machine_audits" / f"repair_budget_{budget}"
        _write_json(budget_dir / "llm_benchmark_report.json", report)
        _write_json(audit_dir / "interaction_semantic_eval_report.json", audit)
        budget_rows.append(
            {
                "repair_budget": budget,
                "machine_ok": report["machine_ok"],
                "total": report["total"],
                "success_rate": round(report["machine_ok"] / report["total"], 6) if report["total"] else 0.0,
                "actual_repair_calls": _number_summary(
                    [float(row.get("repair_calls_used") or 0) for row in report["results"]]
                ),
                "repair_tokens": _number_summary(
                    [
                        float(sum(int((call or {}).get("total_tokens") or 0) for call in (row.get("model_calls") or [])[1:]))
                        for row in report["results"]
                    ]
                ),
                "repair_generation_seconds": _number_summary(
                    [
                        float(
                            sum(
                                float((call or {}).get("duration_s") or 0.0)
                                for call in (row.get("model_calls") or [])[1:]
                            )
                        )
                        for row in report["results"]
                    ]
                ),
            }
        )
    ended_at = datetime.now().replace(microsecond=0)
    try:
        wall_clock_seconds = max(0.0, (ended_at - datetime.fromisoformat(started_at)).total_seconds())
    except ValueError:
        wall_clock_seconds = 0.0
    summary = {
        "kind": "direct_browser_repair_fair_report",
        "started_at": started_at,
        "ended_at": ended_at.isoformat(),
        "wall_clock_seconds": round(wall_clock_seconds, 3),
        "source_report": _display_path(source_report),
        "config": config,
        "protocol": {
            "frozen_initial_page": True,
            "real_browser_feedback_each_round": True,
            "early_stop_on_machine_ok": True,
            "best_so_far_retained": True,
            "budget_unit": "maximum repair calls after the frozen initial page",
            "hidden_machine_metrics_exposed_to_model": False,
            "complete_previous_html_in_prompt": True,
        },
        "total_requested": len(ordered) + len(errors),
        "complete": len(ordered),
        "infrastructure_errors": errors,
        "first_pass_machine_ok": sum(row.get("first_pass_machine_ok") is True for row in ordered),
        "final_best_so_far_machine_ok": sum(row.get("final_machine_ok") is True for row in ordered),
        "repair_calls": _number_summary(repair_calls),
        "repair_tokens": _number_summary(repair_tokens),
        "repair_generation_seconds": _number_summary(repair_seconds),
        "transitions": {
            name: sum(transition.get("overall") == name for transition in transitions)
            for name in ("fail_to_pass", "pass_to_fail", "fail_to_fail", "pass_to_pass")
        },
        "budgets": budget_rows,
        "results": ordered,
    }
    _write_json(output_dir / "fair_repair_report.json", summary)
    _write_transition_csv(output_dir, ordered)
    _write_frozen_initial_manifest(output_dir, ordered)
    lines = [
        "# Fair Direct-BrowserRepair Budget Experiment",
        "",
        f"- Frozen initial pages: `{summary['protocol']['frozen_initial_page']}`",
        f"- Complete cases: `{summary['complete']}/{summary['total_requested']}`",
        f"- Infrastructure errors: `{len(errors)}`",
        f"- First-pass Machine OK: `{summary['first_pass_machine_ok']}/{summary['complete']}`",
        f"- Final best-so-far Machine OK: `{summary['final_best_so_far_machine_ok']}/{summary['complete']}`",
        "",
        "| Repair budget | Machine OK | Success rate | Mean actual repairs | Median actual repairs | Mean repair tokens | Mean generation s |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in budget_rows:
        lines.append(
            f"| {row['repair_budget']} | {row['machine_ok']}/{row['total']} | {row['success_rate']:.1%} | "
            f"{row['actual_repair_calls']['mean']:.3f} | {row['actual_repair_calls']['median']:.3f} | "
            f"{row['repair_tokens']['mean']:.1f} | {row['repair_generation_seconds']['mean']:.1f} |"
        )
    (output_dir / "fair_repair_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--repair-budget", type=int, default=max(DEFAULT_REPAIR_BUDGETS))
    parser.add_argument("--budgets", default=",".join(map(str, DEFAULT_REPAIR_BUDGETS)))
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--browser-workers", type=int, default=DEFAULT_BROWSER_WORKERS)
    parser.add_argument("--model", default="")
    parser.add_argument("--browser-timeout-ms", type=int, default=DEFAULT_BROWSER_TIMEOUT_MS)
    parser.add_argument("--api-timeout-s", type=int, default=DEFAULT_API_TIMEOUT_S)
    parser.add_argument("--repair-max-tokens", type=int, default=DEFAULT_REPAIR_MAX_TOKENS)
    parser.add_argument("--api-retries", type=int, default=DEFAULT_API_RETRIES)
    parser.add_argument("--token-budget-target", type=int, default=DEFAULT_TOKEN_TARGET)
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--case-overrides", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repair_budget < 0:
        raise SystemExit("--repair-budget 必须 >= 0")
    budgets = tuple(sorted({int(value) for value in args.budgets.split(",") if value.strip()}))
    if not budgets or budgets[0] < 0 or budgets[-1] > args.repair_budget:
        raise SystemExit("--budgets 必须位于 0..repair-budget")
    source_report = _repo_path(args.source_report)
    output_dir = _repo_path(args.output_dir)
    source = json.loads(source_report.read_text(encoding="utf-8"))
    wanted = set(args.case)
    rows = [row for row in source.get("results") or [] if not wanted or row.get("case_id") in wanted]
    if args.max_cases > 0:
        rows = rows[: args.max_cases]
    language = normalize_output_language(args.language)
    override_path = args.case_overrides or (ENGLISH_CASE_OVERRIDES_PATH if language == "en" else None)
    overrides = load_case_overrides(override_path) if override_path else {}
    source_case_ids = {str(row.get("case_id") or "") for row in rows}
    cases = tuple(case for case in benchmark_cases() if case.id in source_case_ids)
    cases = apply_case_overrides(cases, overrides, require_all=language == "en")
    case_map = {case.id: case for case in cases}
    missing = sorted(source_case_ids - set(case_map))
    if missing:
        raise SystemExit("源报告包含未知 case：" + ", ".join(missing))
    model = args.model or str((source.get("config") or {}).get("model") or _model_name())
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().replace(microsecond=0).isoformat()
    config = {
        "model": model,
        "repair_budget": args.repair_budget,
        "budgets": budgets,
        "concurrency": args.concurrency,
        "browser_workers": args.browser_workers,
        "repair_max_tokens": args.repair_max_tokens,
        "api_timeout_s": args.api_timeout_s,
        "browser_timeout_ms": args.browser_timeout_ms,
        "api_retries": args.api_retries,
        "token_budget_target_per_case": args.token_budget_target,
    }
    previous_env = {
        key: os.environ.get(key)
        for key in (
            "ALGOLAB_LLM_MAX_TOKENS",
            "ALGOLAB_LLM_TIMEOUT_S",
            "ALGOLAB_LLM_API_RETRIES",
            "ALGOLAB_BROWSER_AUDIT_TIMEOUT_MS",
            "ALGOLAB_BLOCK_EXTERNAL_RESOURCES",
        )
    }
    os.environ["ALGOLAB_LLM_MAX_TOKENS"] = str(args.repair_max_tokens)
    os.environ["ALGOLAB_LLM_TIMEOUT_S"] = str(args.api_timeout_s)
    os.environ["ALGOLAB_LLM_API_RETRIES"] = str(args.api_retries)
    os.environ["ALGOLAB_BROWSER_AUDIT_TIMEOUT_MS"] = str(args.browser_timeout_ms)
    os.environ["ALGOLAB_BLOCK_EXTERNAL_RESOURCES"] = "1"
    effective_config = {**config, "llm": llm_config()}
    browser_pool = BrowserPool(args.browser_workers, timeout_ms=args.browser_timeout_ms)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
            futures = {
                executor.submit(
                    run_case,
                    row,
                    case=case_map[str(row["case_id"])],
                    output_dir=output_dir,
                    repair_budget=args.repair_budget,
                    browser_pool=browser_pool,
                    model=model,
                    language=language,
                ): str(row["case_id"])
                for row in rows
            }
            for future in concurrent.futures.as_completed(futures):
                case_id = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(
                        f"DONE {case_id} machine_ok={result.get('final_machine_ok')} repairs={result.get('repair_calls_used')}",
                        flush=True,
                    )
                except Exception as exc:
                    error = {
                        "case_id": case_id,
                        "category": "infrastructure_or_generation_error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                    errors.append(error)
                    print(f"ERROR {case_id} {error['error']}", flush=True)
                write_reports(
                    output_dir=output_dir,
                    source_report=source_report,
                    results=results,
                    errors=errors,
                    budgets=budgets,
                    model=model,
                    config=effective_config,
                    started_at=started_at,
                )
    finally:
        browser_pool.close()
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    final = write_reports(
        output_dir=output_dir,
        source_report=source_report,
        results=results,
        errors=errors,
        budgets=budgets,
        model=model,
        config=effective_config,
        started_at=started_at,
    )
    print(
        json.dumps(
            {
                "report": _display_path(output_dir / "fair_repair_report.json"),
                "complete": final["complete"],
                "errors": len(final["infrastructure_errors"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if final["complete"] == final["total_requested"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
