"""Run five-method teaching and visual auxiliary evaluation.

The experiment reuses the frozen Full-200 browser audits and page screenshots.
Machine-derived Naps/TRAKLA2-style metrics are computed locally. A single
blind multimodal rubric supplies LORI/MERLOT-informed teaching scores and the
same four visual dimensions used by the existing Stage2 visual evaluation.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_vision_with_metadata, parse_json_content
from scripts.run_external_eval_methods import (
    NAPS_LEVELS,
    html_feature_flags,
    naps_level_from_features,
    trakla2_style_scores,
)
from scripts.run_stage2_visual_eval import STAGE2_EXTERNAL_SCORE_FIELDS, clamp_score

TEACHING_SCORE_FIELDS = (
    "content_quality",
    "learning_goal_alignment",
    "feedback_adaptation",
    "interaction_usability",
    "presentation_design",
    "teaching_effectiveness",
    "ease_of_use",
)

VISUAL_SCORE_FIELDS = tuple(STAGE2_EXTERNAL_SCORE_FIELDS)
ALL_SCORE_FIELDS = (*TEACHING_SCORE_FIELDS, *VISUAL_SCORE_FIELDS)

METHOD_ORDER = (
    "algotutorgen_stage2",
    "direct_html",
    "webgen_agent",
    "htmlcure_strict",
    "browser_repair_1call",
)

METHOD_LABELS = {
    "algotutorgen_stage2": "AlgoTutorGen / Stage2",
    "direct_html": "Direct HTML",
    "webgen_agent": "WebGen-Agent",
    "htmlcure_strict": "Direct + HTMLCure (strict)",
    "browser_repair_1call": "Direct-BrowserRepair (1-call)",
}

MACHINE_BOOL_KEYS = (
    "page_load_ok",
    "visible_answer_match",
    "interaction_reachable",
    "correct_feedback_ok",
    "wrong_feedback_ok",
    "hint_ok",
    "show_answer_ok",
    "learning_log_ok",
    "mutation_free_ok",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _root_path(root: Path, value: Any) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else root / path


def _rows_by_case(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("case_id") or ""): row for row in rows if str(row.get("case_id") or "")}


def _screenshot_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _rows_by_case([row for row in manifest.get("screenshots") or [] if isinstance(row, dict)])


def _base_record(case: dict[str, Any], audit: dict[str, Any], *, condition: str) -> dict[str, Any]:
    record = {
        "condition": condition,
        "condition_label": METHOD_LABELS[condition],
        "case_id": str(case.get("id") or case.get("algorithm_id") or ""),
        "problem_title": str(case.get("title") or case.get("algorithm_id") or case.get("id") or ""),
        "problem_description": str(case.get("problem") or case.get("input_contract") or ""),
        "learning_objectives": list(case.get("learning_objectives") or []),
        "family": str(case.get("family") or ""),
    }
    record.update({key: bool(audit.get(key)) for key in MACHINE_BOOL_KEYS})
    record["machine_ok"] = all(record[key] for key in MACHINE_BOOL_KEYS)
    return record


def build_method_records(*, root: Path, output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    benchmark = load_json(root / "benchmark/algo_learn_env_benchmark.json")
    cases = [row for row in benchmark.get("cases") or [] if isinstance(row, dict)]

    main_audit = load_json(
        root
        / "output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine_rendered_text/interaction_semantic_eval_report.json"
    )
    main_rows = [row for row in main_audit.get("records") or [] if isinstance(row, dict)]
    algotutorgen = _rows_by_case([row for row in main_rows if row.get("condition") == "algolab_full"])
    direct = _rows_by_case([row for row in main_rows if row.get("condition") == "direct_html"])

    stage2_screens = _screenshot_map(
        load_json(
            root
            / "output/experiments/algotutorgen_full_200_20260706/stage2_eval/stage2_screenshot_manifest.json"
        )
    )
    direct_screens = _screenshot_map(
        load_json(
            root
            / "output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/screenshots/direct_html_screenshots.json"
        )
    )

    webgen_report = load_json(root / "output/external_baselines/webgen/audit_all200_sample0/report.json")
    webgen = _rows_by_case([row for row in webgen_report.get("results") or [] if isinstance(row, dict)])
    webgen_workspace = (
        root
        / "output/external_baselines/webgen/workspaces/"
        "WebGenAgent_external_baseline_all200_sample0_webgen_DeepSeek-V4-Pro_iter5_all200_sample0_budget5"
    )

    htmlcure_report = load_json(
        root
        / "output/external_baselines/htmlcure_all200_sample0/behavior_audit/interaction_semantic_eval_report.json"
    )
    htmlcure = _rows_by_case([row for row in htmlcure_report.get("records") or [] if isinstance(row, dict)])

    browser_report = load_json(
        root
        / "output/experiments/algotutorgen_plan_completion_20260713/direct_browser_repair_5/"
        "machine_audits/calls_1/interaction_semantic_eval_report.json"
    )
    browser_repair = _rows_by_case([row for row in browser_report.get("records") or [] if isinstance(row, dict)])

    grouped: dict[str, list[dict[str, Any]]] = {condition: [] for condition in METHOD_ORDER}
    for case in cases:
        case_id = str(case.get("id") or case.get("algorithm_id") or "")
        if not case_id:
            continue

        algo_audit = algotutorgen[case_id]
        algo_screen = stage2_screens[case_id]
        algo_record = _base_record(case, algo_audit, condition="algotutorgen_stage2")
        algo_record.update(
            {
                "html": str(_root_path(root, algo_audit.get("html"))),
                "visual_html": str(_root_path(root, algo_screen.get("html"))),
                "screenshot": str(_root_path(root, algo_screen.get("screenshot"))),
            }
        )
        grouped["algotutorgen_stage2"].append(algo_record)

        direct_audit = direct[case_id]
        direct_screen = direct_screens[case_id]
        direct_record = _base_record(case, direct_audit, condition="direct_html")
        direct_record.update(
            {
                "html": str(_root_path(root, direct_audit.get("html"))),
                "visual_html": str(_root_path(root, direct_screen.get("html"))),
                "screenshot": str(_root_path(root, direct_screen.get("screenshot"))),
            }
        )
        grouped["direct_html"].append(direct_record)

        web_audit = webgen[case_id]
        web_source_dir = webgen_workspace / case_id
        existing_web_screenshot = _root_path(root, web_audit.get("screenshot"))
        web_screenshot = (
            existing_web_screenshot
            if str(web_audit.get("screenshot") or "")
            else output_dir / "screenshots/webgen_agent" / f"{case_id}.png"
        )
        web_record = _base_record(case, web_audit, condition="webgen_agent")
        web_record.update(
            {
                "html": str(web_source_dir / "index.html"),
                "visual_html": str(web_source_dir / "index.html"),
                "source_dir": str(web_source_dir),
                "screenshot": str(web_screenshot),
            }
        )
        grouped["webgen_agent"].append(web_record)

        cure_audit = htmlcure[case_id]
        cure_record = _base_record(case, cure_audit, condition="htmlcure_strict")
        cure_record.update(
            {
                "html": str(_root_path(root, cure_audit.get("html"))),
                "visual_html": str(_root_path(root, cure_audit.get("html"))),
                "screenshot": str(output_dir / "screenshots/htmlcure_strict" / f"{case_id}.png"),
            }
        )
        grouped["htmlcure_strict"].append(cure_record)

        repair_audit = browser_repair[case_id]
        repair_html = _root_path(root, repair_audit.get("html"))
        repair_record = _base_record(case, repair_audit, condition="browser_repair_1call")
        repair_record.update(
            {
                "html": str(repair_html),
                "visual_html": str(repair_html),
                "screenshot": str(repair_html.with_suffix(".png")),
            }
        )
        grouped["browser_repair_1call"].append(repair_record)

    for condition in METHOD_ORDER:
        grouped[condition].sort(key=lambda row: str(row.get("case_id") or ""))
    return grouped


def missing_screenshot_counts(grouped: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        condition: sum(not Path(str(row.get("screenshot") or "")).exists() for row in grouped.get(condition, []))
        for condition in METHOD_ORDER
    }


def capture_static_html_screenshots(
    records: list[dict[str, Any]],
    *,
    wait_ms: int = 500,
) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    results: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        executable = str(os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE") or "").strip()
        launch_kwargs: dict[str, Any] = {"headless": True, "args": ["--no-sandbox"]}
        if executable:
            launch_kwargs["executable_path"] = executable
        browser = playwright.chromium.launch(**launch_kwargs)
        try:
            for record in records:
                case_id = str(record.get("case_id") or "")
                html_path = Path(str(record.get("html") or ""))
                screenshot_path = Path(str(record.get("screenshot") or ""))
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page = browser.new_page(viewport={"width": 1365, "height": 900})
                page.set_default_timeout(20_000)
                page.route(
                    "**/*",
                    lambda route: route.abort()
                    if route.request.url.startswith(("http://", "https://"))
                    else route.continue_(),
                )
                error = ""
                try:
                    page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded", timeout=20_000)
                    page.wait_for_timeout(max(0, int(wait_ms)))
                    try:
                        page.screenshot(path=str(screenshot_path), full_page=True)
                    except Exception:
                        page.screenshot(path=str(screenshot_path), full_page=False)
                    if not screenshot_path.exists() or screenshot_path.stat().st_size <= 0:
                        raise RuntimeError("screenshot file is empty")
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                finally:
                    page.close()
                results.append({"case_id": case_id, "ok": not error, "error": error})
        finally:
            browser.close()
    return results


def _wait_for_dev_server_url(log_path: Path, *, timeout_s: int = 90) -> str:
    pattern = re.compile(r"http://(?:localhost|127\.0\.0\.1):\d+/?")
    deadline = time.time() + max(1, timeout_s)
    while time.time() < deadline:
        text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
        match = pattern.search(text)
        if match:
            return match.group(0)
        time.sleep(0.5)
    raise TimeoutError("WebGen dev server URL did not appear")


def capture_webgen_workspace_screenshot(record: dict[str, Any]) -> dict[str, Any]:
    case_id = str(record.get("case_id") or "")
    screenshot_path = Path(str(record.get("screenshot") or ""))
    if screenshot_path.exists() and screenshot_path.stat().st_size > 0:
        return {"case_id": case_id, "ok": True, "error": "", "cached": True}

    workspace = Path(str(record.get("source_dir") or ""))
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = screenshot_path.with_suffix(".service.log")
    process: subprocess.Popen[str] | None = None
    log_handle = None
    error = ""
    try:
        if not workspace.exists():
            raise FileNotFoundError(f"WebGen workspace does not exist: {workspace}")
        install = subprocess.run(
            [
                "npm",
                "install",
                "--no-audit",
                "--no-fund",
                "--registry",
                "https://registry.npmjs.org",
                "--fetch-retries",
                "4",
                "--fetch-retry-maxtimeout",
                "60000",
            ],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=600,
        )
        if install.returncode != 0:
            raise RuntimeError("npm install failed: " + (install.stderr or install.stdout)[-1200:])
        log_handle = log_path.open("w", encoding="utf-8")
        process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "0"],
            cwd=workspace,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        url = _wait_for_dev_server_url(log_path)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executable = str(os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE") or "").strip()
            launch_kwargs: dict[str, Any] = {"headless": True, "args": ["--no-sandbox"]}
            if executable:
                launch_kwargs["executable_path"] = executable
            browser = playwright.chromium.launch(**launch_kwargs)
            try:
                page = browser.new_page(viewport={"width": 1365, "height": 900})
                page.set_default_timeout(60_000)
                try:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    except Exception:
                        pass
                    page.wait_for_timeout(1500)
                    try:
                        page.screenshot(path=str(screenshot_path), full_page=True)
                    except Exception:
                        page.screenshot(path=str(screenshot_path), full_page=False)
                finally:
                    page.close()
            finally:
                browser.close()
        if not screenshot_path.exists() or screenshot_path.stat().st_size <= 0:
            raise RuntimeError("WebGen screenshot file is empty")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if process is not None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except Exception:
                    pass
        if log_handle is not None:
            log_handle.close()
        shutil.rmtree(workspace / "node_modules", ignore_errors=True)
    return {"case_id": case_id, "ok": not error, "error": error, "cached": False}


def feature_flags_from_text(raw_text: str) -> dict[str, bool]:
    raw = str(raw_text or "")
    text = re.sub(r"\s+", " ", raw).lower()
    input_change_terms = (
        "modify input",
        "change input",
        "custom input",
        "rerun",
        "re-run",
        "run again",
        "重新运行",
        "修改输入",
        "自定义输入",
        "更改输入",
        "改变输入",
        "输入数据并运行",
    )
    construction_terms = (
        "construct your own",
        "build your own",
        "create visualization",
        "draw the",
        "构建自己的",
        "自己构建",
        "绘制算法",
        "创建可视化",
    )
    presentation_terms = (
        "present to",
        "share your explanation",
        "peer review",
        "class presentation",
        "展示给",
        "向同学展示",
        "同伴评审",
    )
    has_free_input = bool(re.search(r"<textarea\b|<input\b", raw, flags=re.I))
    return {
        "input_change_supported": has_free_input and any(term in text for term in input_change_terms),
        "construction_supported": any(term in text for term in construction_terms),
        "presentation_supported": any(term in text for term in presentation_terms),
    }


def source_text_from_dir(source_dir: Path) -> str:
    if not source_dir.exists():
        return ""
    parts: list[str] = []
    total_chars = 0
    allowed_suffixes = {".html", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue
        if "node_modules" in path.parts or "dist" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        parts.append(text)
        total_chars += len(text)
        if total_chars >= 500_000:
            break
    return "\n".join(parts)


def enrich_machine_metrics(record: dict[str, Any]) -> dict[str, Any]:
    source_dir_text = str(record.get("source_dir") or "").strip()
    if source_dir_text:
        feature_flags = feature_flags_from_text(source_text_from_dir(Path(source_dir_text)))
    else:
        html_path = Path(str(record.get("html") or ""))
        feature_flags = html_feature_flags(html_path)
    flags = {key: bool(record.get(key)) for key in MACHINE_BOOL_KEYS}
    flags.update(feature_flags)
    return {
        **record,
        "feature_flags": feature_flags,
        "naps_engagement": naps_level_from_features(flags),
        "trakla2_style": trakla2_style_scores(record),
    }


def build_multimodal_prompt(record: dict[str, Any]) -> tuple[str, str]:
    system = (
        "你是算法可视化与数字学习资源的匿名外部评审员。"
        "请结合 LORI、MERLOT、Munzner nested model 与 Mayer multimedia learning principles，"
        "评价一个算法教学页面。方法身份已经隐藏；不得猜测或依据方法名称调整分数。"
        "浏览器行为证据用于判断功能，截图用于判断内容呈现与视觉设计。"
        "只输出一个可由 json.loads 解析的 JSON 对象，不要 markdown。"
    )
    machine_evidence = {
        key: bool(record.get(key))
        for key in (
            "page_load_ok",
            "visible_answer_match",
            "interaction_reachable",
            "correct_feedback_ok",
            "wrong_feedback_ok",
            "hint_ok",
            "show_answer_ok",
            "learning_log_ok",
            "mutation_free_ok",
        )
    }
    payload = {
        "task": "blind_all_method_teaching_and_visual_review",
        "case": {
            "case_id": str(record.get("case_id") or ""),
            "title": str(record.get("problem_title") or ""),
            "problem_description": str(record.get("problem_description") or ""),
            "learning_objectives": list(record.get("learning_objectives") or []),
        },
        "machine_evidence": machine_evidence,
        "score_policy": {
            "range": "integer 1-5",
            "machine_evidence_is_authoritative_for_behavior": True,
            "do_not_infer_hidden_interactions_from_screenshot": True,
            "do_not_score_algorithm_correctness_beyond_visible_answer_evidence": True,
            "do_not_penalize_abstract_algorithms_for_lacking_a_real_world_metaphor": True,
        },
        "rubric": {
            "content_quality": "内容是否清楚、准确、完整，并与题目一致。",
            "learning_goal_alignment": "页面内容与给定学习目标是否一致。",
            "feedback_adaptation": "结合机器证据，正确/错误反馈、提示与显示答案是否支持学习。",
            "interaction_usability": "结合机器证据，学习者操作是否可达、清楚且可用。",
            "presentation_design": "信息层次、可读性、布局和视觉组织是否适合学习。",
            "teaching_effectiveness": "页面是否帮助理解算法状态、过程与关键决策。",
            "ease_of_use": "页面是否容易理解和操作。",
            "problem_visual_alignment": "题面实体、数据结构、目标和视觉编码是否贴合。",
            "algorithm_state_readability": "当前算法状态和关键变量是否清楚可读。",
            "process_transition_clarity": "页面是否清楚表达步骤变化或提供可理解的过程导航。",
            "instructional_visual_design": "高亮、标签、分组、邻近解释和信息层次是否有教学性。",
        },
        "required_json_schema": {
            "scores": {field: "integer 1-5" for field in ALL_SCORE_FIELDS},
            "strengths": ["up to 3 concrete visible strengths"],
            "weaknesses": ["up to 3 concrete weaknesses"],
            "recommendation": "one short Chinese sentence",
            "confidence": "number 0-1",
        },
    }
    return system, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _short_string_list(value: Any, *, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:300] for item in value if str(item).strip()][:limit]


def normalize_multimodal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    scores = {field: clamp_score(raw_scores.get(field)) for field in ALL_SCORE_FIELDS}
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, float(confidence)))
    teaching_values = [scores[field] for field in TEACHING_SCORE_FIELDS]
    visual_values = [scores[field] for field in VISUAL_SCORE_FIELDS]
    return {
        "ok": True,
        "scores": scores,
        "teaching_overall_score": round(sum(teaching_values) / len(teaching_values), 3),
        "visual_overall_score": round(sum(visual_values) / len(visual_values), 3),
        "strengths": _short_string_list(payload.get("strengths")),
        "weaknesses": _short_string_list(payload.get("weaknesses")),
        "recommendation": str(payload.get("recommendation") or "")[:500],
        "confidence": round(confidence, 3),
    }


def evaluate_multimodal_record(
    record: dict[str, Any],
    *,
    model: str | None,
    retries: int,
    chat_fn: Callable[[str, str, str, str | None], dict[str, Any]] = chat_vision_with_metadata,
) -> dict[str, Any]:
    screenshot_path = Path(str(record.get("screenshot") or ""))
    if not screenshot_path.exists() or screenshot_path.stat().st_size <= 0:
        if record.get("page_load_ok") is False:
            normalized = normalize_multimodal_payload(
                {
                    "scores": {field: 1 for field in ALL_SCORE_FIELDS},
                    "strengths": [],
                    "weaknesses": ["页面未能完成渲染，学习内容与视觉信息不可用。"],
                    "recommendation": "先修复页面渲染失败，再进行教学与视觉评价。",
                    "confidence": 1.0,
                }
            )
            return {
                **normalized,
                "scoring_mode": "deterministic_render_failure_floor",
                "failure_type": "machine_render_failure",
                "error": f"machine audit failed and screenshot does not exist: {screenshot_path}",
                "model_calls": [],
                "raw_response": "",
                "elapsed_wall_s": 0.0,
            }
        return {
            "ok": False,
            "failure_type": "missing_screenshot",
            "error": f"screenshot does not exist: {screenshot_path}",
            "model_calls": [],
        }
    image_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
    system, base_user = build_multimodal_prompt(record)
    model_calls: list[dict[str, Any]] = []
    raw_response = ""
    last_error = ""
    for attempt in range(max(0, int(retries)) + 1):
        user = base_user
        if attempt:
            user += "\n上一轮输出无法解析。现在只返回一个紧凑 JSON 对象，不要 markdown。"
        started = time.perf_counter()
        try:
            response = chat_fn(system, user, image_b64, model)
            raw_response = str(response.get("content") or "")
            model_call = dict(response.get("model_call") or {})
            if model_call:
                model_calls.append(model_call)
            payload = parse_json_content(raw_response)
            if not isinstance(payload, dict):
                raise ValueError("multimodal review response must be a JSON object")
            normalized = normalize_multimodal_payload(payload)
            return {
                **normalized,
                "model_call": model_call,
                "model_calls": model_calls,
                "raw_response": raw_response[:6000],
                "elapsed_wall_s": round(time.perf_counter() - started, 3),
            }
        except Exception as exc:
            last_error = str(exc)
    return {
        "ok": False,
        "failure_type": "multimodal_review_error",
        "error": last_error,
        "model_calls": model_calls,
        "raw_response": raw_response[:6000],
    }


def run_multimodal_reviews(
    records: list[dict[str, Any]],
    *,
    output_dir: Path,
    model: str | None,
    retries: int,
    concurrency: int,
    force: bool,
    evaluator: Callable[..., dict[str, Any]] = evaluate_multimodal_record,
) -> list[dict[str, Any]]:
    case_root = output_dir / "review_cases"

    def run_one(record: dict[str, Any]) -> dict[str, Any]:
        condition = str(record.get("condition") or "unknown")
        case_id = str(record.get("case_id") or "unknown")
        cache_path = case_root / condition / f"{case_id}.json"
        if cache_path.exists() and not force:
            return load_json(cache_path)
        result = evaluator(record, model=model, retries=retries)
        result = {
            **result,
            "condition": condition,
            "condition_label": str(record.get("condition_label") or METHOD_LABELS.get(condition) or condition),
            "case_id": case_id,
            "problem_title": str(record.get("problem_title") or ""),
            "screenshot": str(record.get("screenshot") or ""),
            "browser_ok": bool(record.get("page_load_ok")),
            "machine_ok": bool(record.get("machine_ok")),
        }
        write_json(cache_path, result)
        return result

    if max(1, int(concurrency)) == 1:
        results = []
        for index, record in enumerate(records, 1):
            results.append(run_one(record))
            if index == 1 or index % 10 == 0 or index == len(records):
                print(f"multimodal progress: {index}/{len(records)}", flush=True)
    else:
        results = []
        with ThreadPoolExecutor(max_workers=max(1, int(concurrency))) as executor:
            futures = [executor.submit(run_one, record) for record in records]
            for index, future in enumerate(as_completed(futures), 1):
                results.append(future.result())
                if index == 1 or index % 10 == 0 or index == len(records):
                    print(f"multimodal progress: {index}/{len(records)}", flush=True)
    order = {condition: index for index, condition in enumerate(METHOD_ORDER)}
    return sorted(
        results,
        key=lambda row: (order.get(str(row.get("condition") or ""), len(order)), str(row.get("case_id") or "")),
    )


def summarize_condition(records: list[dict[str, Any]], reviews: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    naps_counts = Counter(str(row.get("naps_engagement", {}).get("level") or "") for row in records)
    avg_naps = (
        sum(float(row.get("naps_engagement", {}).get("score") or 0) for row in records) / total
        if total
        else 0.0
    )
    avg_trakla = (
        sum(float(row.get("trakla2_style", {}).get("score") or 0) for row in records) / total
        if total
        else 0.0
    )
    trakla_core_pass = sum(bool(row.get("trakla2_style", {}).get("core_pass")) for row in records)
    valid = [row for row in reviews if row.get("ok") is True and isinstance(row.get("scores"), dict)]
    render_failure_floor = [
        row
        for row in valid
        if row.get("scoring_mode") == "deterministic_render_failure_floor"
    ]

    def avg_score(field: str) -> float | None:
        if not valid:
            return None
        return round(sum(int(row["scores"].get(field) or 0) for row in valid) / len(valid), 3)

    teaching_overall = [float(row["teaching_overall_score"]) for row in valid]
    visual_overall = [float(row["visual_overall_score"]) for row in valid]
    return {
        "total": total,
        "naps_level_counts": dict(sorted(naps_counts.items())),
        "avg_naps_score": round(avg_naps, 3),
        "trakla2_core_pass": trakla_core_pass,
        "trakla2_core_pass_rate": trakla_core_pass / total if total else 0.0,
        "avg_trakla2_score": round(avg_trakla, 3),
        "multimodal_evaluated": len(reviews),
        "multimodal_valid": len(valid),
        "multimodal_model_scored": len(valid) - len(render_failure_floor),
        "deterministic_render_failure_floor": len(render_failure_floor),
        "multimodal_failed": len(reviews) - len(valid),
        "avg_scores": {field: avg_score(field) for field in ALL_SCORE_FIELDS},
        "avg_teaching_overall": round(sum(teaching_overall) / len(teaching_overall), 3)
        if teaching_overall
        else None,
        "avg_visual_overall": round(sum(visual_overall) / len(visual_overall), 3)
        if visual_overall
        else None,
        "teaching_all_dimensions_pass": sum(
            all(int(row["scores"].get(field) or 0) >= 3 for field in TEACHING_SCORE_FIELDS)
            for row in valid
        ),
        "visual_all_dimensions_pass": sum(
            all(int(row["scores"].get(field) or 0) >= 3 for field in VISUAL_SCORE_FIELDS)
            for row in valid
        ),
    }


def summarize_model_usage(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    calls = [
        call
        for review in reviews
        for call in review.get("model_calls") or []
        if isinstance(call, dict)
    ]
    usage_calls = [call for call in calls if call.get("usage_available") is True]
    return {
        "call_count": len(calls),
        "usage_available_count": len(usage_calls),
        "prompt_tokens": sum(int(call.get("prompt_tokens") or 0) for call in usage_calls),
        "completion_tokens": sum(int(call.get("completion_tokens") or 0) for call in usage_calls),
        "total_tokens": sum(int(call.get("total_tokens") or 0) for call in usage_calls),
        "duration_s": round(sum(float(call.get("duration_s") or 0.0) for call in calls), 3),
    }


def build_report(
    grouped: dict[str, list[dict[str, Any]]],
    reviews: list[dict[str, Any]],
    *,
    model: str | None,
) -> dict[str, Any]:
    reviews_by_condition: dict[str, list[dict[str, Any]]] = {}
    for review in reviews:
        reviews_by_condition.setdefault(str(review.get("condition") or ""), []).append(review)
    methods: dict[str, Any] = {}
    ordered_conditions = [condition for condition in METHOD_ORDER if condition in grouped]
    ordered_conditions.extend(condition for condition in grouped if condition not in ordered_conditions)
    for condition in ordered_conditions:
        methods[condition] = {
            "label": METHOD_LABELS.get(condition, condition),
            "summary": summarize_condition(grouped[condition], reviews_by_condition.get(condition, [])),
        }
    return {
        "kind": "all_method_auxiliary_eval_report",
        "schema_version": "all-method-auxiliary-eval-v1",
        "created_at": now_iso(),
        "model": model,
        "method_order": ordered_conditions,
        "teaching_score_fields": list(TEACHING_SCORE_FIELDS),
        "visual_score_fields": list(VISUAL_SCORE_FIELDS),
        "methods": methods,
        "model_usage": summarize_model_usage(reviews),
        "review_count": len(reviews),
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_report(report: dict[str, Any], output_dir: Path) -> None:
    write_json(output_dir / "all_method_auxiliary_eval_report.json", report)
    lines = [
        "# All-Method Auxiliary Evaluation",
        "",
        f"- created_at: `{report['created_at']}`",
        f"- model: `{report.get('model')}`",
        "",
        "## Machine-derived teaching metrics",
        "",
        "| Method | Naps avg | TRAKLA2 core pass | TRAKLA2 avg |",
        "|---|---:|---:|---:|",
    ]
    for condition in report["method_order"]:
        item = report["methods"][condition]
        summary = item["summary"]
        lines.append(
            f"| {item['label']} | {_fmt(summary['avg_naps_score'])} | "
            f"{summary['trakla2_core_pass']}/{summary['total']} | {_fmt(summary['avg_trakla2_score'])} |"
        )
    lines.extend(
        [
            "",
            "## Multimodal teaching review",
            "",
            "| Method | Valid | Model-scored | Failure floor | Teaching overall | Content | Goal alignment | Feedback | Interaction | Presentation | Teaching effectiveness | Ease of use |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for condition in report["method_order"]:
        item = report["methods"][condition]
        summary = item["summary"]
        scores = summary["avg_scores"]
        lines.append(
            f"| {item['label']} | {summary['multimodal_valid']}/{summary['multimodal_evaluated']} | "
            f"{summary['multimodal_model_scored']} | {summary['deterministic_render_failure_floor']} | "
            f"{_fmt(summary['avg_teaching_overall'])} | {_fmt(scores['content_quality'])} | "
            f"{_fmt(scores['learning_goal_alignment'])} | {_fmt(scores['feedback_adaptation'])} | "
            f"{_fmt(scores['interaction_usability'])} | {_fmt(scores['presentation_design'])} | "
            f"{_fmt(scores['teaching_effectiveness'])} | {_fmt(scores['ease_of_use'])} |"
        )
    lines.extend(
        [
            "",
            "## Same-rubric visual review",
            "",
            "| Method | Valid | Model-scored | Failure floor | All dimensions >=3 | Overall | Alignment | State readability | Transition clarity | Instructional design |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for condition in report["method_order"]:
        item = report["methods"][condition]
        summary = item["summary"]
        scores = summary["avg_scores"]
        lines.append(
            f"| {item['label']} | {summary['multimodal_valid']}/{summary['multimodal_evaluated']} | "
            f"{summary['multimodal_model_scored']} | {summary['deterministic_render_failure_floor']} | "
            f"{summary['visual_all_dimensions_pass']}/{summary['multimodal_valid']} | "
            f"{_fmt(summary['avg_visual_overall'])} | {_fmt(scores['problem_visual_alignment'])} | "
            f"{_fmt(scores['algorithm_state_readability'])} | {_fmt(scores['process_transition_clarity'])} | "
            f"{_fmt(scores['instructional_visual_design'])} |"
        )
    usage = report["model_usage"]
    lines.extend(
        [
            "",
            "## Model usage",
            "",
            f"- calls: `{usage['call_count']}`",
            f"- total_tokens: `{usage['total_tokens']}`",
            f"- duration_s: `{usage['duration_s']}`",
            "",
        ]
    )
    (output_dir / "all_method_auxiliary_eval_report.md").write_text("\n".join(lines), encoding="utf-8")


def cached_reviews_for_records(records: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    for record in records:
        path = (
            output_dir
            / "review_cases"
            / str(record.get("condition") or "unknown")
            / f"{record.get('case_id')}.json"
        )
        if path.exists():
            reviews.append(load_json(path))
    return reviews


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output/experiments/all_method_auxiliary_eval_20260718",
    )
    parser.add_argument("--condition", action="append", choices=list(METHOD_ORDER), default=[])
    parser.add_argument("--capture-missing", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--run-multimodal", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--vlm-model", default="gemini-3-flash-preview")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--wait-ms", type=int, default=500)
    parser.add_argument("--force", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped = build_method_records(root=ROOT, output_dir=output_dir)

    capture_results: list[dict[str, Any]] = []
    if args.capture_missing:
        static_missing = [
            row
            for row in grouped["htmlcure_strict"]
            if not Path(str(row.get("screenshot") or "")).exists()
        ]
        if static_missing:
            capture_results.extend(capture_static_html_screenshots(static_missing, wait_ms=args.wait_ms))
        for row in grouped["webgen_agent"]:
            if not Path(str(row.get("screenshot") or "")).exists():
                capture_results.append(capture_webgen_workspace_screenshot(row))

    enriched = {
        condition: [enrich_machine_metrics(row) for row in rows]
        for condition, rows in grouped.items()
    }
    write_json(output_dir / "prepared_records.json", enriched)
    write_json(
        output_dir / "screenshot_capture_report.json",
        {
            "created_at": now_iso(),
            "results": capture_results,
            "missing_after_capture": missing_screenshot_counts(enriched),
        },
    )

    selected_conditions = args.condition or list(METHOD_ORDER)
    selected_records: list[dict[str, Any]] = []
    selected_grouped: dict[str, list[dict[str, Any]]] = {}
    for condition in selected_conditions:
        rows = enriched[condition]
        if args.max_cases:
            rows = rows[: max(0, int(args.max_cases))]
        selected_grouped[condition] = rows
        selected_records.extend(rows)

    if args.run_multimodal:
        reviews = run_multimodal_reviews(
            selected_records,
            output_dir=output_dir,
            model=args.vlm_model,
            retries=args.retries,
            concurrency=args.concurrency,
            force=args.force,
        )
    else:
        reviews = cached_reviews_for_records(selected_records, output_dir)

    report = build_report(selected_grouped, reviews, model=args.vlm_model)
    report["capture_results"] = capture_results
    report["missing_screenshots"] = missing_screenshot_counts(enriched)
    write_report(report, output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir.relative_to(ROOT)),
                "methods": {
                    condition: report["methods"][condition]["summary"]
                    for condition in report["method_order"]
                },
                "model_usage": report["model_usage"],
                "missing_screenshots": report["missing_screenshots"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
