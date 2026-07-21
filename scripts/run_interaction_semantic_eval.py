"""Run interaction-semantic evaluation for AlgoTutorGen vs direct HTML.

The machine audit is browser-based and does not call an LLM. Optional LLM
judge calls are used only for subjective teaching/visual/process-alignment
ratings, never for correctness gating.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.runtime.executor import canonical
from llm_client import chat_json_with_metadata, llm_config
from scripts.audit_direct_html_answer import audit_html_answer, html_to_searchable_text


MACHINE_BOOL_KEYS = [
    "page_load_ok",
    "visible_answer_match",
    "interaction_reachable",
    "correct_feedback_ok",
    "wrong_feedback_ok",
    "hint_ok",
    "show_answer_ok",
    "learning_log_ok",
    "mutation_free_ok",
]

LLM_SCORE_KEYS = [
    "process_accuracy",
    "interaction_semantics",
    "teaching_alignment",
    "visual_clarity",
]


def clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 1
    return max(1, min(5, score))


def normalize_condition_name(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"algolab", "ours", "our", "algotutorgen", "algolab_full"}:
        return "algolab_full"
    if text in {"direct", "direct_html", "direct-html", "baseline"}:
        return "direct_html"
    if text in {"tie", "draw", "equal"}:
        return "tie"
    return text or "tie"


def normalize_scores(raw_scores: dict[str, Any] | None) -> dict[str, int]:
    raw_scores = raw_scores if isinstance(raw_scores, dict) else {}
    return {key: clamp_score(raw_scores.get(key)) for key in LLM_SCORE_KEYS}


def normalize_llm_judge_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize paired LLM judge output into stable per-condition scores."""

    data = raw if isinstance(raw, dict) else {}
    scores = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    algolab_scores = normalize_scores(
        scores.get("algolab")
        or scores.get("algolab_full")
        or data.get("algolab")
        or data.get("algolab_full")
    )
    direct_scores = normalize_scores(
        scores.get("direct_html")
        or scores.get("direct")
        or data.get("direct_html")
        or data.get("direct")
    )
    winner = normalize_condition_name(str(data.get("winner") or "tie"))
    if winner not in {"algolab_full", "direct_html", "tie"}:
        winner = "tie"
    return {
        "winner": winner,
        "algolab_full": {
            "scores": algolab_scores,
            "summary": str(data.get("algolab_summary") or data.get("ours_summary") or "")[:800],
        },
        "direct_html": {
            "scores": direct_scores,
            "summary": str(data.get("direct_summary") or data.get("baseline_summary") or "")[:800],
        },
        "rationale": str(data.get("rationale") or "")[:1200],
        "raw": data,
    }


def summarize_condition_results(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("condition") or "unknown")].append(record)

    summary: dict[str, dict[str, Any]] = {}
    for condition, rows in sorted(grouped.items()):
        item: dict[str, Any] = {"total": len(rows)}
        for key in ["machine_ok", *MACHINE_BOOL_KEYS]:
            item[key] = sum(1 for row in rows if row.get(key) is True)
            item[f"{key}_rate"] = item[key] / len(rows) if rows else 0.0
        for score_key in LLM_SCORE_KEYS:
            values = []
            for row in rows:
                judge = row.get("llm_judge") if isinstance(row.get("llm_judge"), dict) else {}
                scores = judge.get("scores") if isinstance(judge.get("scores"), dict) else {}
                if score_key in scores:
                    values.append(clamp_score(scores.get(score_key)))
            item[f"avg_{score_key}"] = round(sum(values) / len(values), 3) if values else None
        summary[condition] = item
    return summary


def load_report_rows(report_path: Path, *, condition: str) -> dict[str, dict[str, Any]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, Any]] = {}
    for item in report.get("results") or []:
        case_id = str(item.get("case_id") or "")
        if not case_id:
            continue
        rows[case_id] = {
            "condition": condition,
            "case_id": case_id,
            "title": item.get("title") or item.get("problem_title") or case_id,
            "family": item.get("family") or item.get("family_id") or "",
            "input_data": item.get("input_data"),
            "expected": item.get("expected"),
            "html": item.get("html"),
            "json": item.get("json"),
            "ok": item.get("ok"),
            "source_report": str(report_path.relative_to(ROOT) if report_path.is_absolute() else report_path),
        }
    return rows


def load_algolab_evidence(json_path: Path) -> dict[str, Any]:
    artifact = json.loads(json_path.read_text(encoding="utf-8"))
    frames: list[dict[str, Any]] = []
    for scene in (artifact.get("scenes") or {}).values():
        for frame in scene.get("frames") or []:
            if frame.get("interaction") or frame.get("teaching"):
                frames.append(
                    {
                        "step": frame.get("step"),
                        "title": frame.get("title"),
                        "operation": frame.get("operation"),
                        "state": frame.get("state"),
                        "interaction": frame.get("interaction"),
                        "teaching": frame.get("teaching"),
                        "evidence": {
                            "targets": ((frame.get("evidence") or {}).get("targets") or [])[:6],
                            "deps": ((frame.get("evidence") or {}).get("deps") or [])[:6],
                            "reason": (frame.get("evidence") or {}).get("reason"),
                        },
                    }
                )
            if len(frames) >= 8:
                break
        if frames:
            break
    return {
        "problem_title": artifact.get("problem_title"),
        "input_data": artifact.get("input_data"),
        "expected_result": artifact.get("expected_result"),
        "validation_checks": (artifact.get("validation") or {}).get("checks") or [],
        "sample_frames": frames,
    }


def compact_direct_html_evidence(html_path: Path) -> dict[str, Any]:
    html = html_path.read_text(encoding="utf-8")
    text = html_to_searchable_text(html)
    interesting = []
    for pattern in [
        r"(?i)(checkpoint|预测|思考|提示|正确答案|learning log|学习日志|反馈).{0,220}",
        r"(最终答案|最终输出|返回结果|答案).{0,160}",
    ]:
        for match in re.finditer(pattern, text):
            snippet = re.sub(r"\s+", " ", match.group(0)).strip()
            if snippet and snippet not in interesting:
                interesting.append(snippet)
            if len(interesting) >= 12:
                break
        if len(interesting) >= 12:
            break
    return {
        "text_excerpt": text[:3500],
        "interaction_snippets": interesting,
    }


def build_llm_judge_prompt(
    *,
    case_id: str,
    title: str,
    input_data: Any,
    expected: Any,
    algolab_evidence: dict[str, Any],
    direct_evidence: dict[str, Any],
    algolab_machine: dict[str, Any],
    direct_machine: dict[str, Any],
) -> tuple[str, str]:
    system = (
        "你是算法教学环境评估员。你要比较两个同一题目的交互式算法学习页面："
        "AlgoTutorGen 和 Direct HTML baseline。请严格依据给出的机器审计证据、页面文本和结构化片段评分。"
        "不要因为页面看起来更华丽就给过程准确性高分；过程准确性和交互语义必须基于状态、答案、反馈、hint 是否与题目和当前步骤一致。"
        "只输出 JSON 对象。"
    )
    user = json.dumps(
        {
            "task": "paired_algorithm_learning_environment_judgment",
            "rubric": {
                "process_accuracy": "1-5: 算法过程、状态、最终答案是否可信；有结构化 trace/oracle 证据可加分，明显自相矛盾扣分。",
                "interaction_semantics": "1-5: checkpoint/quiz/hint/feedback 是否绑定到当前算法状态，正误反馈是否有语义依据。",
                "teaching_alignment": "1-5: 讲解是否逐步对齐当前状态、覆盖关键不变量/常见误区。",
                "visual_clarity": "1-5: 页面可读性、状态可见性、信息层次；这是主观视觉分，不等同 correctness。",
            },
            "required_json_schema": {
                "winner": "algolab_full | direct_html | tie",
                "scores": {
                    "algolab": {
                        "process_accuracy": "integer 1-5",
                        "interaction_semantics": "integer 1-5",
                        "teaching_alignment": "integer 1-5",
                        "visual_clarity": "integer 1-5",
                    },
                    "direct_html": {
                        "process_accuracy": "integer 1-5",
                        "interaction_semantics": "integer 1-5",
                        "teaching_alignment": "integer 1-5",
                        "visual_clarity": "integer 1-5",
                    },
                },
                "algolab_summary": "one short Chinese sentence",
                "direct_summary": "one short Chinese sentence",
                "rationale": "2-4 concise Chinese sentences",
            },
            "case": {
                "case_id": case_id,
                "title": title,
                "input_data": input_data,
                "expected": expected,
            },
            "machine_audit": {
                "algolab_full": algolab_machine,
                "direct_html": direct_machine,
            },
            "algolab_evidence": algolab_evidence,
            "direct_html_evidence": direct_evidence,
        },
        ensure_ascii=False,
        indent=2,
    )
    return system, user


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        return ROOT / p
    if p.exists():
        return p
    host_root = os.environ.get("ALGOLAB_HOST_PROJECT_ROOT", "").strip()
    if host_root:
        try:
            return ROOT / p.relative_to(Path(host_root))
        except ValueError:
            pass
    return p


def _html_artifact_path(row: dict[str, Any]) -> Path | None:
    reference = str(row.get("html") or "").strip()
    if not reference:
        return None
    path = _repo_path(reference)
    return path if path.is_file() else None


def _answer_match_from_html(html_path: Path, expected: Any) -> bool:
    if expected is None or not html_path.is_file():
        return False
    try:
        return audit_html_answer(html_path.read_text(encoding="utf-8"), expected).get("status") == "answer_match"
    except Exception:
        return False


def _compact_for_dom(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if isinstance(value, (dict, list)) else str(value)
    return text[:77] + "..." if len(text) > 80 else text


def _squash_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _expected_matches_text(text: str, expected: Any) -> bool:
    if expected is None:
        return False
    haystack = _squash_text(text)
    if not haystack:
        return False
    needles = {
        _squash_text(canonical(expected)),
        _squash_text(_compact_for_dom(expected)),
        _squash_text(json.dumps(expected, ensure_ascii=False)),
    }
    if isinstance(expected, dict):
        needles.update(_squash_text(f"{key}:{value}") for key, value in expected.items())
        return all(needle in haystack for needle in needles if ":" in needle) or any(
            needle and needle in haystack for needle in needles
        )
    return any(needle and needle in haystack for needle in needles)


def _answer_match_from_dom(page: Any, expected: Any) -> bool:
    if expected is None:
        return False
    try:
        text = page.evaluate(
            """() => {
                const selectors = ['#answer', '#top-result', '.answer-badge', '[data-answer-like="true"]'];
                const parts = [];
                for (const selector of selectors) {
                    for (const node of document.querySelectorAll(selector)) {
                        parts.push(node.textContent || '');
                    }
                }
                try {
                    if (typeof ARTIFACT !== 'undefined' && ARTIFACT) {
                        parts.push(JSON.stringify(ARTIFACT.expected_result));
                        const variant = ARTIFACT.variants && ARTIFACT.variants[0];
                        if (variant) parts.push(JSON.stringify(variant.result));
                    }
                } catch (error) {}
                parts.push(document.body ? document.body.innerText : '');
                return parts.join('\\n');
            }"""
        )
    except Exception:
        return False
    return _expected_matches_text(str(text), expected)


def _canon_text(value: Any) -> str:
    return canonical(value)


def _text(page: Any, selector: str) -> str:
    loc = page.locator(selector)
    if loc.count() == 0:
        return ""
    try:
        return loc.first.inner_text().strip()
    except Exception:
        return ""


def _visible(page: Any, selector: str) -> int:
    loc = page.locator(selector)
    total = loc.count()
    count = 0
    for index in range(total):
        try:
            if loc.nth(index).is_visible():
                count += 1
        except Exception:
            pass
    return count


def _first_visible_locator(page: Any, selectors: list[str]) -> Any | None:
    for selector in selectors:
        loc = page.locator(selector)
        total = loc.count()
        for index in range(total):
            item = loc.nth(index)
            try:
                if item.is_visible():
                    return item
            except Exception:
                pass
    return None


def _click_first_visible(page: Any, selectors: list[str], *, timeout: int = 1500) -> bool:
    loc = _first_visible_locator(page, selectors)
    if loc is None:
        return False
    try:
        loc.click(timeout=timeout)
        page.wait_for_timeout(150)
        return True
    except Exception:
        return False


def _click_text(page: Any, text: str) -> bool:
    loc = page.locator("button").filter(has_text=text)
    if loc.count() == 0:
        return False
    try:
        loc.first.click(timeout=1500)
        page.wait_for_timeout(150)
        return True
    except Exception:
        return False


def _click_text_any(page: Any, labels: tuple[str, ...]) -> bool:
    return any(_click_text(page, label) for label in labels)


ALGOLAB_HINT_LABELS = ("提示", "Hint")
ALGOLAB_SHOW_ANSWER_LABELS = ("查看答案", "Show answer", "View answer")
ALGOLAB_CORRECT_LABELS = ("正确", "Correct", "True")
ALGOLAB_INCORRECT_LABELS = ("错误", "Incorrect", "False")


CHECKPOINT_SELECTORS = [
    ".interaction[data-learning-checkpoint='prediction']",
    ".checkpoint",
    "#checkpoint-container .checkpoint",
    "#checkpoint-container:not(:empty)",
    ".checkpoint-card.visible",
    ".checkpoint-card",
    ".checkpoint-container",
    ".checkpoint-section",
    "#checkpoint-section",
    ".checkpoint-box",
    "#checkpoint-area:not(.hidden-cp)",
    ".checkpoint-area:not(.hidden-cp)",
    ".checkpoint-area",
]


CHECKPOINT_CONTROL_SELECTORS = [
    ".interaction[data-learning-checkpoint='prediction'] input",
    ".interaction[data-learning-checkpoint='prediction'] button",
    ".checkpoint input",
    ".checkpoint button",
    "#checkpoint-container input",
    "#checkpoint-container button",
    ".checkpoint-card input",
    ".checkpoint-card button",
    ".checkpoint-container input",
    ".checkpoint-container button",
    ".checkpoint-section input",
    ".checkpoint-section button",
    "#checkpoint-section input",
    "#checkpoint-section button",
    ".checkpoint-box input",
    ".checkpoint-box button",
    "#checkpoint-area input",
    "#checkpoint-area button",
    ".checkpoint-area input",
    ".checkpoint-area button",
]


def _checkpoint_prompt_valid(page: Any) -> bool:
    prompt = " ".join(
        part
        for part in [
            _text(page, "#checkpoint-question"),
            _text(page, "#cp-question"),
            _text(page, ".checkpoint-question"),
            _text(page, ".cp-question"),
            _text(page, ".checkpoint-area .question"),
            _text(page, ".checkpoint-card h4"),
        ]
        if part
    )
    if not prompt:
        return True
    return not any(marker in prompt for marker in ["暂无", "无检测", "无检查", "没有检查点", "观察算法状态变化"])


def _checkpoint_reachable_now(page: Any) -> bool:
    if _visible(page, ".interaction[data-learning-checkpoint='prediction']"):
        return any(
            _visible(page, selector)
            for selector in [
                ".interaction[data-learning-checkpoint='prediction'] input",
                ".interaction[data-learning-checkpoint='prediction'] button",
                "#interaction .checkpoint-option",
                "#interaction .checkpoint-actions button",
            ]
        )
    if not any(_visible(page, selector) for selector in CHECKPOINT_SELECTORS[1:]):
        return False
    if not _checkpoint_prompt_valid(page):
        return False
    return any(
        _visible(page, selector)
        for selector in [
            ".checkpoint input",
            "#checkpoint-container input",
            "#checkpoint-container button.checkpoint-option",
            "#checkpoint-container button.opt-btn",
            "#checkpoint-section input",
            ".checkpoint-box input",
            "#checkpoint-area input",
            ".checkpoint-area input",
            ".checkpoint-card.visible input",
            ".checkpoint-card.visible .checkpoint-options button",
            ".checkpoint-container input",
            ".checkpoint-container .checkpoint-option",
            ".checkpoint-section input",
            ".checkpoint-section .checkpoint-options button",
            ".checkpoint-section .cp-options button",
            ".cp-options button",
            ".option-btn",
            ".checkpoint .checkpoint-option",
            "#checkpoint-container .checkpoint-option",
            "#checkpoint-options button",
            ".checkpoint-options button",
            ".options .opt-btn",
            ".opt-btn",
        ]
    )


def _find_checkpoint(page: Any, *, max_steps: int) -> bool:
    if _checkpoint_reachable_now(page):
        return True
    steps = max(1, min(max_steps or 80, 120))
    for _ in range(steps):
        if page.locator("#next").count() == 0:
            break
        try:
            page.locator("#next").click(timeout=1500)
            page.wait_for_timeout(50)
        except Exception:
            break
        if _checkpoint_reachable_now(page):
            return True
    return False


def _snapshot_answer(page: Any) -> str:
    return page.evaluate(
        """() => {
            const answer = document.querySelector('#answer');
            const top = document.querySelector('#top-result');
            const badge = document.querySelector('.answer-badge');
            return [answer && answer.textContent, top && top.textContent, badge && badge.textContent]
                .filter(Boolean).join(' | ').trim();
        }"""
    )


def _learning_log_text(page: Any) -> str:
    return " ".join(
        part
        for part in [
            _text(page, "#learning-log-frame"),
            _text(page, "#learning-log-preview"),
            _text(page, "#learning-log"),
            _text(page, "#log"),
            _text(page, "#learning-log-entries"),
            _text(page, ".learning-log"),
            _text(page, ".log-entry"),
        ]
        if part
    )


def _feedback_text(page: Any) -> str:
    return " ".join(
        part
        for part in [
            _text(page, "#feedback"),
            _text(page, "#checkpoint-feedback"),
            _text(page, "#cp-feedback"),
            _text(page, ".checkpoint-feedback.show"),
            _text(page, ".checkpoint-feedback"),
            _text(page, ".cp-feedback"),
            _text(page, ".feedback-area"),
            _text(page, ".feedback.show"),
            _text(page, ".feedback"),
            _alert_text(page),
        ]
        if part
    ).strip()


def _install_alert_capture(page: Any) -> None:
    try:
        page.evaluate(
            """() => {
                window.__semanticEvalAlerts = [];
                window.alert = (message) => {
                    window.__semanticEvalAlerts.push(String(message || ''));
                };
            }"""
        )
    except Exception:
        pass


def _alert_text(page: Any) -> str:
    try:
        value = page.evaluate("() => (window.__semanticEvalAlerts || []).join(' ')")
        return str(value or "")
    except Exception:
        return ""


def _algo_answer(page: Any) -> str:
    try:
        return str(
            page.evaluate(
                """() => {
                    if (typeof frame === 'function') {
                        const f = frame();
                        return f && f.interaction ? String(f.interaction.answer ?? '') : '';
                    }
                    return '';
                }"""
            )
        )
    except Exception:
        return ""


def _exercise_algolab(page: Any) -> dict[str, Any]:
    answer_before = _snapshot_answer(page)
    log_before = _learning_log_text(page)
    answer = _algo_answer(page)
    correct_feedback = ""
    wrong_feedback = ""
    correct_ok = False
    wrong_ok = False

    if _visible(page, "#free-answer"):
        page.locator("#free-answer").fill("__definitely_wrong__", timeout=1500)
        page.locator(".checkpoint-input-row button").first.click(timeout=1500)
        page.wait_for_timeout(200)
        wrong_feedback = _feedback_text(page)
        wrong_ok = bool(wrong_feedback)
        page.locator("#free-answer").fill(answer, timeout=1500)
        page.locator(".checkpoint-input-row button").first.click(timeout=1500)
        page.wait_for_timeout(200)
        correct_feedback = _feedback_text(page)
        correct_ok = bool(correct_feedback)
    elif _visible(page, "#interaction .checkpoint-option"):
        options = page.locator("#interaction .checkpoint-option")
        correct_index = -1
        for index in range(options.count()):
            value = options.nth(index).get_attribute("data-option") or ""
            if value == answer:
                correct_index = index
                break
        wrong_index = 0 if correct_index != 0 else (1 if options.count() > 1 else -1)
        if wrong_index >= 0:
            options.nth(wrong_index).click(timeout=1500)
            page.wait_for_timeout(200)
            wrong_feedback = _feedback_text(page)
            wrong_ok = bool(wrong_feedback)
        if correct_index >= 0:
            options.nth(correct_index).click(timeout=1500)
            page.wait_for_timeout(200)
            correct_feedback = _feedback_text(page)
            correct_ok = bool(correct_feedback)
    elif _visible(page, "#interaction .checkpoint-actions button"):
        answer_bool = answer.lower() in {"true", "正确", "yes", "1"}
        wrong_labels = ALGOLAB_INCORRECT_LABELS if answer_bool else ALGOLAB_CORRECT_LABELS
        correct_labels = ALGOLAB_CORRECT_LABELS if answer_bool else ALGOLAB_INCORRECT_LABELS
        wrong_ok = _click_text_any(page, wrong_labels)
        wrong_feedback = _feedback_text(page)
        correct_ok = _click_text_any(page, correct_labels)
        correct_feedback = _feedback_text(page)

    hint_ok = _click_text_any(page, ALGOLAB_HINT_LABELS) and bool(_feedback_text(page))
    show_answer_ok = _click_text_any(page, ALGOLAB_SHOW_ANSWER_LABELS) and bool(_feedback_text(page))
    log_after = _learning_log_text(page)
    answer_after = _snapshot_answer(page)
    correct_semantic_ok, wrong_semantic_ok = _feedback_semantics(correct_feedback, wrong_feedback)
    return {
        "correct_feedback_ok": correct_ok and correct_semantic_ok,
        "wrong_feedback_ok": wrong_ok and wrong_semantic_ok,
        "hint_ok": hint_ok,
        "show_answer_ok": show_answer_ok,
        "learning_log_ok": bool(log_after) and log_after != log_before,
        "mutation_free_ok": answer_before == answer_after,
        "feedback_preview": {
            "correct": correct_feedback[:240],
            "wrong": wrong_feedback[:240],
            "log": log_after[:240],
        },
    }


def _feedback_is_correct(text: str) -> bool:
    compact = str(text or "")
    lower = compact.lower()
    if "✅" in compact:
        return True
    if any(marker in compact for marker in ["不正确", "错了", "❌"]) or any(
        marker in lower for marker in ["incorrect", "wrong answer", "try again"]
    ):
        return False
    if re.search(r"(^|[\s。；;！!])错误[：:。；;！!]", compact):
        return False
    return any(marker in compact for marker in ["正确", "答对", "很好"]) or any(
        marker in lower for marker in ["correct", "well done"]
    )


def _feedback_is_wrong(text: str) -> bool:
    compact = str(text or "")
    lower = compact.lower()
    return (
        any(marker in compact for marker in ["不正确", "错了", "❌", "✗", "×"])
        or any(marker in lower for marker in ["incorrect", "wrong answer", "try again"])
        or bool(re.search(r"(^|[\s。；;！!])错误[：:。；;！!]", compact))
    )


def _feedback_semantics(correct_feedback: str, wrong_feedback: str) -> tuple[bool, bool]:
    """Validate that feedback text agrees with the answer direction that triggered it."""

    return _feedback_is_correct(correct_feedback), _feedback_is_wrong(wrong_feedback)


def _direct_checkpoint_data(page: Any) -> dict[str, Any]:
    try:
        data = page.evaluate(
            """() => {
                const out = {};
                const area = document.querySelector('#checkpoint-area');
                if (area && area.dataset) {
                    if (area.dataset.cpAnswer !== undefined) out.answer = area.dataset.cpAnswer;
                    if (area.dataset.cpHint !== undefined) out.hint = area.dataset.cpHint;
                }
                try {
                    if (typeof currentCpData !== 'undefined' && currentCpData) {
                        if (currentCpData.answer !== undefined) out.answer = currentCpData.answer;
                        if (currentCpData.correct !== undefined) out.correctIndex = currentCpData.correct;
                        if (Array.isArray(currentCpData.options)) out.options = currentCpData.options;
                    }
                } catch (error) {}
                try {
                    const checked = document.querySelector('input[type="radio"][data-correct="true"]');
                    if (checked) out.correctValue = checked.value;
                } catch (error) {}
                return out;
            }"""
        )
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _submit_direct_checkpoint(page: Any) -> bool:
    return _click_first_visible(
        page,
        [
            ".checkpoint .submit-btn",
            ".checkpoint button.submit-btn",
            "#checkpoint-submit",
            "#submit-checkpoint",
            "#cp-submit",
            ".btn-submit",
            ".cp-submit",
            ".cp-submit",
            ".checkpoint-card #checkpoint-submit",
            ".checkpoint-container #checkpoint-submit",
            ".checkpoint-section #cp-submit",
            "#checkpoint-section button",
            "#checkpoint-area button.cp-submit",
        ],
    ) or _click_text(page, "提交")


def _exercise_direct_text_input(page: Any, checkpoint_data: dict[str, Any]) -> tuple[bool, bool, str, str]:
    input_loc = _first_visible_locator(
        page,
        [
            "#cp-input",
            "#checkpoint-input",
            ".checkpoint-area input[type='text']",
            ".checkpoint-input",
            ".checkpoint-card input[type='text']",
            ".checkpoint-container input[type='text']",
            ".checkpoint input[type='text']",
            "#checkpoint-section input[type='text']",
            ".checkpoint-box input[type='text']",
        ],
    )
    if input_loc is None:
        return False, False, "", ""
    answer = str(checkpoint_data.get("answer") or "")
    wrong_feedback = ""
    correct_feedback = ""
    wrong_ok = False
    correct_ok = False
    try:
        input_loc.fill("__definitely_wrong__", timeout=1500)
        if _submit_direct_checkpoint(page):
            wrong_feedback = _feedback_text(page)
            wrong_ok = bool(wrong_feedback) and (_feedback_is_wrong(wrong_feedback) or not answer)
    except Exception:
        pass
    if answer:
        try:
            input_loc.fill(answer, timeout=1500)
            if _submit_direct_checkpoint(page):
                correct_feedback = _feedback_text(page)
                correct_ok = bool(correct_feedback) and (_feedback_is_correct(correct_feedback) or answer in correct_feedback)
        except Exception:
            pass
    return correct_ok, wrong_ok, correct_feedback, wrong_feedback


def _mark_direct_option_buttons(page: Any) -> int:
    try:
        return int(
            page.evaluate(
                """() => {
                    const optionContainers = Array.from(document.querySelectorAll(
                        '#checkpoint-options, .checkpoint-options, .options, #cp-options, .cp-options'
                    ));
                    let index = 0;
                    for (const node of document.querySelectorAll('[data-semantic-eval-option]')) {
                        delete node.dataset.semanticEvalOption;
                    }
                    const blocked = /(提交|提示|答案|显示|查看|reveal|hint|submit)/i;
                    for (const container of optionContainers) {
                        const rect = container.getBoundingClientRect();
                        const visible = rect.width > 0 && rect.height > 0 && getComputedStyle(container).display !== 'none';
                        if (!visible) continue;
                        for (const button of container.querySelectorAll('button, .checkpoint-option, .opt-btn, .option-btn')) {
                            const text = (button.textContent || '').trim();
                            const idClass = `${button.id || ''} ${button.className || ''} ${text}`;
                            const brect = button.getBoundingClientRect();
                            const bvisible = brect.width > 0 && brect.height > 0 && getComputedStyle(button).display !== 'none';
                            if (!bvisible || blocked.test(idClass)) continue;
                            button.dataset.semanticEvalOption = String(index++);
                        }
                    }
                    return index;
                }"""
            )
        )
    except Exception:
        return 0


def _click_direct_option_button(page: Any, index: int) -> bool:
    selector = f'[data-semantic-eval-option="{index}"]'
    loc = page.locator(selector)
    if loc.count() == 0:
        return False
    try:
        loc.first.click(timeout=1500)
        page.wait_for_timeout(200)
        return True
    except Exception:
        return False


def _restore_direct_checkpoint(page: Any) -> bool:
    try:
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        _install_alert_capture(page)
        return _find_checkpoint(page, max_steps=80)
    except Exception:
        return False


def _exercise_direct_buttons(page: Any) -> tuple[bool, bool, str, str]:
    option_count = _mark_direct_option_buttons(page)
    if option_count == 0:
        return False, False, "", ""

    correct_feedback = ""
    wrong_feedback = ""
    correct_ok = False
    wrong_ok = False
    for index in range(min(option_count, 8)):
        if index > 0 and not _restore_direct_checkpoint(page):
            break
        _mark_direct_option_buttons(page)
        if not _click_direct_option_button(page, index):
            continue
        feedback = _feedback_text(page)
        if not feedback or (not _feedback_is_correct(feedback) and not _feedback_is_wrong(feedback)):
            _submit_direct_checkpoint(page)
            feedback = _feedback_text(page)
        if not feedback:
            continue
        if _feedback_is_correct(feedback):
            correct_ok = True
            correct_feedback = feedback
        if _feedback_is_wrong(feedback):
            wrong_ok = True
            wrong_feedback = feedback
        if correct_ok and wrong_ok:
            break
    return correct_ok, wrong_ok, correct_feedback, wrong_feedback


def _visible_input_value(page: Any) -> str:
    loc = _first_visible_locator(
        page,
        [
            "#cp-input",
            "#checkpoint-input",
            ".checkpoint-area input[type='text']",
            ".checkpoint-input",
            ".checkpoint-card input[type='text']",
            ".checkpoint-container input[type='text']",
            ".checkpoint input[type='text']",
            "#checkpoint-section input[type='text']",
            ".checkpoint-box input[type='text']",
        ],
    )
    if loc is None:
        return ""
    try:
        return str(loc.input_value(timeout=1500) or "")
    except Exception:
        return ""


def _answer_from_feedback_text(text: str) -> str:
    compact = str(text or "").strip()
    for pattern in [
        r"(?:答案|正确答案)[：:]\s*([^。；;\n]+)",
        r"correct answer[：:]\s*([^。；;\n]+)",
    ]:
        match = re.search(pattern, compact, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().strip("。")
    return ""


def _probe_direct_auxiliary_controls(page: Any) -> tuple[bool, bool, str]:
    hint_ok = False
    show_answer_ok = False
    shown_answer = ""
    if (
        _click_first_visible(
            page,
            [
                ".hint-btn",
                ".btn-hint",
                ".cp-hint",
                "#checkpoint-hint",
                "#hint-checkpoint",
                "#cp-hint",
            ],
        )
        or _click_text(page, "提示")
    ):
        hint_ok = bool(_feedback_text(page))

    _restore_direct_checkpoint(page)
    if (
        _click_first_visible(
            page,
            [
                ".show-answer-btn",
                ".btn-show-answer",
                ".cp-show-answer",
                "#checkpoint-show-answer",
                "#checkpoint-reveal",
                "#checkpoint-show",
                "#checkpoint-show-answer",
                "#show-answer-checkpoint",
                "#cp-show-answer",
            ],
        )
        or _click_text(page, "显示答案")
        or _click_text(page, "查看答案")
    ):
        feedback = _feedback_text(page)
        shown_answer = _visible_input_value(page) or _answer_from_feedback_text(feedback)
        show_answer_ok = bool(feedback or shown_answer)

    _restore_direct_checkpoint(page)
    return hint_ok, show_answer_ok, shown_answer


def _radio_count(page: Any) -> int:
    return page.locator("input[type='radio']").count()


def _check_radio_by_index(page: Any, index: int) -> bool:
    radios = page.locator("input[type='radio']")
    if index < 0 or index >= radios.count():
        return False
    try:
        radios.nth(index).check(timeout=1500)
        return True
    except Exception:
        return False


def _check_radio_by_value(page: Any, value: Any) -> bool:
    value_text = str(value)
    radios = page.locator("input[type='radio']")
    for index in range(radios.count()):
        radio = radios.nth(index)
        try:
            if str(radio.get_attribute("value") or "") == value_text:
                radio.check(timeout=1500)
                return True
        except Exception:
            pass
    return False


def _exercise_direct_radios(page: Any, checkpoint_data: dict[str, Any]) -> tuple[bool, bool, str, str]:
    radios = page.locator("input[type='radio']")
    if radios.count() == 0:
        return False, False, "", ""

    correct_feedback = ""
    wrong_feedback = ""
    correct_ok = False
    wrong_ok = False

    correct_inputs = page.locator("input[type='radio'][data-correct='true']")
    wrong_inputs = page.locator("input[type='radio'][data-correct='false']")
    if wrong_inputs.count() > 0:
        try:
            wrong_inputs.first.check(timeout=1500)
            if _submit_direct_checkpoint(page):
                wrong_feedback = _feedback_text(page)
                wrong_ok = bool(wrong_feedback) and (_feedback_is_wrong(wrong_feedback) or not _feedback_is_correct(wrong_feedback))
        except Exception:
            pass
    if correct_inputs.count() > 0:
        try:
            correct_inputs.first.check(timeout=1500)
            if _submit_direct_checkpoint(page):
                correct_feedback = _feedback_text(page)
                correct_ok = bool(correct_feedback) and (_feedback_is_correct(correct_feedback) or not _feedback_is_wrong(correct_feedback))
        except Exception:
            pass
        return correct_ok, wrong_ok, correct_feedback, wrong_feedback

    correct_index = checkpoint_data.get("correctIndex")
    if correct_index is not None:
        try:
            correct_index_int = int(correct_index)
        except (TypeError, ValueError):
            correct_index_int = -1
        wrong_index = 0 if correct_index_int != 0 else (1 if _radio_count(page) > 1 else -1)
        if wrong_index >= 0 and _check_radio_by_index(page, wrong_index) and _submit_direct_checkpoint(page):
            wrong_feedback = _feedback_text(page)
            wrong_ok = bool(wrong_feedback) and (_feedback_is_wrong(wrong_feedback) or not _feedback_is_correct(wrong_feedback))
        if _check_radio_by_value(page, correct_index_int) and _submit_direct_checkpoint(page):
            correct_feedback = _feedback_text(page)
            correct_ok = bool(correct_feedback) and (_feedback_is_correct(correct_feedback) or not _feedback_is_wrong(correct_feedback))
        return correct_ok, wrong_ok, correct_feedback, wrong_feedback

    for index in range(min(radios.count(), 6)):
        if not _check_radio_by_index(page, index):
            continue
        if not _submit_direct_checkpoint(page):
            continue
        feedback = _feedback_text(page)
        if not feedback:
            continue
        if _feedback_is_correct(feedback):
            correct_ok = True
            correct_feedback = feedback
        elif _feedback_is_wrong(feedback):
            wrong_ok = True
            wrong_feedback = feedback
        if correct_ok and wrong_ok:
            break
    return correct_ok, wrong_ok, correct_feedback, wrong_feedback


def _exercise_direct(page: Any) -> dict[str, Any]:
    answer_before = _snapshot_answer(page)
    log_before = _learning_log_text(page)
    checkpoint_data = _direct_checkpoint_data(page)
    correct_feedback = ""
    wrong_feedback = ""
    correct_ok = False
    wrong_ok = False
    hint_ok, show_answer_ok, shown_answer = _probe_direct_auxiliary_controls(page)
    checkpoint_data = _direct_checkpoint_data(page)
    if shown_answer and not checkpoint_data.get("answer"):
        checkpoint_data["answer"] = shown_answer
    text_result = _exercise_direct_text_input(page, checkpoint_data)
    if text_result[0] or text_result[1]:
        correct_ok, wrong_ok, correct_feedback, wrong_feedback = text_result
    else:
        radio_result = _exercise_direct_radios(page, checkpoint_data)
        correct_ok, wrong_ok, correct_feedback, wrong_feedback = radio_result
        if not (correct_ok or wrong_ok):
            button_result = _exercise_direct_buttons(page)
            correct_ok, wrong_ok, correct_feedback, wrong_feedback = button_result
    log_after = _learning_log_text(page)
    if not correct_ok and _feedback_is_correct(log_after):
        correct_ok = True
        correct_feedback = correct_feedback or log_after
    if not wrong_ok and _feedback_is_wrong(log_after):
        wrong_ok = True
        wrong_feedback = wrong_feedback or log_after
    answer_after = _snapshot_answer(page)
    return {
        "correct_feedback_ok": correct_ok and bool(correct_feedback),
        "wrong_feedback_ok": wrong_ok and bool(wrong_feedback),
        "hint_ok": hint_ok,
        "show_answer_ok": show_answer_ok,
        "learning_log_ok": bool(log_after) and log_after != log_before,
        "mutation_free_ok": answer_before == answer_after,
        "feedback_preview": {
            "correct": correct_feedback[:240],
            "wrong": wrong_feedback[:240],
            "log": log_after[:240],
        },
    }


def audit_browser_record(browser: Any, row: dict[str, Any]) -> dict[str, Any]:
    html_path = _html_artifact_path(row)
    if html_path is None:
        return {
            **row,
            "html": str(row.get("html") or ""),
            "page_load_ok": False,
            "visible_answer_match": False,
            "interaction_reachable": False,
            "correct_feedback_ok": False,
            "wrong_feedback_ok": False,
            "hint_ok": False,
            "show_answer_ok": False,
            "learning_log_ok": False,
            "mutation_free_ok": False,
            "machine_ok": False,
            "console_page_errors": ["MissingHtmlArtifact: report row has no existing HTML file"],
        }
    expected = row.get("expected")
    errors: list[str] = []
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    page.set_default_timeout(2000)
    if os.environ.get("ALGOLAB_BLOCK_EXTERNAL_RESOURCES") == "1":
        page.route(
            re.compile(r"^https?://"),
            lambda route: route.abort(),
        )
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        _install_alert_capture(page)
        load_errors = errors
        if os.environ.get("ALGOLAB_BLOCK_EXTERNAL_RESOURCES") == "1":
            load_errors = [error for error in errors if "Failed to load resource: net::ERR_FAILED" not in error]
        page_load_ok = bool(_text(page, "body")) and not load_errors
        visible_answer_match = _answer_match_from_html(html_path, expected) or _answer_match_from_dom(page, expected)
        max_steps = 0
        if row.get("condition") == "algolab_full" and row.get("json"):
            try:
                artifact = json.loads(_repo_path(str(row["json"])).read_text(encoding="utf-8"))
                scene = next(iter((artifact.get("scenes") or {}).values()), {})
                max_steps = len(scene.get("frames") or [])
            except Exception:
                max_steps = 0
        interaction_reachable = _find_checkpoint(page, max_steps=max_steps or 80)
        exercise = (
            _exercise_algolab(page)
            if row.get("condition") == "algolab_full"
            else _exercise_direct(page)
        ) if interaction_reachable else {
            "correct_feedback_ok": False,
            "wrong_feedback_ok": False,
            "hint_ok": False,
            "show_answer_ok": False,
            "learning_log_ok": False,
            "mutation_free_ok": False,
            "feedback_preview": {},
        }
        record = {
            **row,
            "html": str(html_path.relative_to(ROOT)),
            "page_load_ok": page_load_ok,
            "visible_answer_match": visible_answer_match,
            "interaction_reachable": interaction_reachable,
            **exercise,
            "console_page_errors": errors,
        }
        record["machine_ok"] = all(record.get(key) is True for key in MACHINE_BOOL_KEYS)
        return record
    except Exception as exc:
        record = {
            **row,
            "html": str(html_path),
            "page_load_ok": False,
            "visible_answer_match": False,
            "interaction_reachable": False,
            "correct_feedback_ok": False,
            "wrong_feedback_ok": False,
            "hint_ok": False,
            "show_answer_ok": False,
            "learning_log_ok": False,
            "mutation_free_ok": False,
            "machine_ok": False,
            "console_page_errors": [*errors, f"{type(exc).__name__}: {exc}"],
        }
        return record
    finally:
        page.close()


def pair_rows(
    algolab_report: Path,
    direct_report: Path,
    *,
    cases: set[str],
    max_cases: int,
    shard_id: int = 0,
    num_shards: int = 1,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    algolab = load_report_rows(algolab_report, condition="algolab_full")
    direct = load_report_rows(direct_report, condition="direct_html")
    case_ids = [case_id for case_id in algolab if case_id in direct]
    if cases:
        case_ids = [case_id for case_id in case_ids if case_id in cases]
    if num_shards > 1:
        case_ids = [
            case_id for index, case_id in enumerate(case_ids)
            if index % num_shards == shard_id
        ]
    if max_cases > 0:
        case_ids = case_ids[:max_cases]
    pairs = []
    for case_id in case_ids:
        algolab_row = algolab[case_id]
        direct_row = direct[case_id]
        if algolab_row.get("expected") is None:
            try:
                artifact = json.loads(_repo_path(str(algolab_row["json"])).read_text(encoding="utf-8"))
                algolab_row["expected"] = artifact.get("expected_result")
            except Exception:
                pass
        direct_row["expected"] = direct_row.get("expected", algolab_row.get("expected"))
        pairs.append((algolab_row, direct_row))
    return pairs


def run_llm_pair_judge(
    *,
    algolab_record: dict[str, Any],
    direct_record: dict[str, Any],
    model: str | None,
) -> dict[str, Any]:
    algolab_json = _repo_path(str(algolab_record.get("json") or ""))
    direct_html = _repo_path(str(direct_record.get("html") or ""))
    system, user = build_llm_judge_prompt(
        case_id=str(algolab_record.get("case_id")),
        title=str(algolab_record.get("title") or direct_record.get("title") or algolab_record.get("case_id")),
        input_data=algolab_record.get("input_data") or direct_record.get("input_data"),
        expected=algolab_record.get("expected") or direct_record.get("expected"),
        algolab_evidence=load_algolab_evidence(algolab_json),
        direct_evidence=compact_direct_html_evidence(direct_html),
        algolab_machine={key: algolab_record.get(key) for key in ["machine_ok", *MACHINE_BOOL_KEYS]},
        direct_machine={key: direct_record.get(key) for key in ["machine_ok", *MACHINE_BOOL_KEYS]},
    )
    response = chat_json_with_metadata(system, user, model=model, kind="interaction_semantic_judge")
    normalized = normalize_llm_judge_result(response["content"])
    normalized["model_calls"] = response.get("model_calls") or []
    return normalized


def write_reports(output_dir: Path, records: list[dict[str, Any]], pair_judges: list[dict[str, Any]]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_condition_results(records)
    report = {
        "kind": "interaction_semantic_eval_report",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "summary": summary,
        "llm": llm_config(),
        "records": records,
        "pair_judges": pair_judges,
    }
    json_path = output_dir / "interaction_semantic_eval_report.json"
    md_path = output_dir / "interaction_semantic_eval_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Interaction Semantic Evaluation Report",
        "",
        f"- created_at: `{report['created_at']}`",
        f"- json: `{json_path.relative_to(ROOT)}`",
        "",
        "## Condition Summary",
        "",
        "| Condition | Total | Machine OK | Visible Answer | Interaction | Correct FB | Wrong FB | Hint | Show Answer | Log | Mutation-free | Process | Interact Sem | Teaching | Visual |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, item in summary.items():
        lines.append(
            f"| {condition} | {item['total']} | {item['machine_ok']} | {item['visible_answer_match']} | "
            f"{item['interaction_reachable']} | {item['correct_feedback_ok']} | {item['wrong_feedback_ok']} | "
            f"{item['hint_ok']} | {item['show_answer_ok']} | {item['learning_log_ok']} | {item['mutation_free_ok']} | "
            f"{item.get('avg_process_accuracy')} | {item.get('avg_interaction_semantics')} | "
            f"{item.get('avg_teaching_alignment')} | {item.get('avg_visual_clarity')} |"
        )
    lines.extend(
        [
            "",
            "## Case Records",
            "",
            "| Case | Condition | Machine OK | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for record in records:
        lines.append(
            f"| {record.get('case_id')} | {record.get('condition')} | {record.get('machine_ok')} | "
            f"{record.get('visible_answer_match')} | {record.get('interaction_reachable')} | "
            f"{record.get('correct_feedback_ok')} | {record.get('wrong_feedback_ok')} | {record.get('hint_ok')} | "
            f"{record.get('show_answer_ok')} | {record.get('learning_log_ok')} | {record.get('mutation_free_ok')} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algolab-report", type=Path, required=True)
    parser.add_argument("--direct-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--machine-report", type=Path, default=None, help="Reuse records from a previous machine audit JSON.")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--llm-judge", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--direct-only", action="store_true")
    parser.add_argument("--algolab-only", action="store_true")
    parser.add_argument("--algolab-condition", default="algolab_full")
    parser.add_argument("--direct-condition", default="direct_html")
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    return parser.parse_args()


def audit_condition_names(*, algolab_only: bool, direct_only: bool) -> tuple[str, ...]:
    if algolab_only and direct_only:
        raise ValueError("algolab_only and direct_only are mutually exclusive")
    if algolab_only:
        return ("algolab_full",)
    if direct_only:
        return ("direct_html",)
    return ("algolab_full", "direct_html")


def output_condition_name(
    source_condition: str,
    *,
    algolab_condition: str,
    direct_condition: str,
) -> str:
    if source_condition == "algolab_full":
        return algolab_condition
    if source_condition == "direct_html":
        return direct_condition
    raise ValueError(f"unsupported audit source condition: {source_condition}")


def main() -> int:
    args = parse_args()
    algolab_report = _repo_path(args.algolab_report)
    direct_report = _repo_path(args.direct_report)
    output_dir = _repo_path(args.output_dir)
    if args.num_shards < 1 or not 0 <= args.shard_id < args.num_shards:
        raise SystemExit("--shard-id must be in [0, --num-shards)")
    if args.algolab_only and args.direct_only:
        raise SystemExit("--algolab-only and --direct-only are mutually exclusive")
    if (args.direct_only or args.algolab_only) and args.llm_judge:
        raise SystemExit("single-condition audit cannot be combined with --llm-judge")
    pairs = pair_rows(
        algolab_report,
        direct_report,
        cases=set(args.case),
        max_cases=int(args.max_cases or 0),
        shard_id=args.shard_id,
        num_shards=args.num_shards,
    )
    records: list[dict[str, Any]] = []
    pair_judges: list[dict[str, Any]] = []

    if args.machine_report:
        machine_report = json.loads(_repo_path(args.machine_report).read_text(encoding="utf-8"))
        wanted_cases = {algolab_row["case_id"] for algolab_row, _ in pairs}
        for record in machine_report.get("records") or []:
            if record.get("case_id") in wanted_cases and record.get("condition") in {"algolab_full", "direct_html"}:
                reused = dict(record)
                reused["condition"] = output_condition_name(
                    str(record["condition"]),
                    algolab_condition=args.algolab_condition,
                    direct_condition=args.direct_condition,
                )
                records.append(reused)
    elif args.no_browser:
        for algolab_row, direct_row in pairs:
            conditions = audit_condition_names(algolab_only=args.algolab_only, direct_only=args.direct_only)
            rows = tuple(algolab_row if condition == "algolab_full" else direct_row for condition in conditions)
            for row in rows:
                html_path = _html_artifact_path(row)
                record = {
                    **row,
                    "page_load_ok": html_path is not None,
                    "visible_answer_match": _answer_match_from_html(html_path, row.get("expected")) if html_path else False,
                    "interaction_reachable": False,
                    "correct_feedback_ok": False,
                    "wrong_feedback_ok": False,
                    "hint_ok": False,
                    "show_answer_ok": False,
                    "learning_log_ok": False,
                    "mutation_free_ok": False,
                }
                record["machine_ok"] = all(record.get(key) is True for key in MACHINE_BOOL_KEYS)
                record["condition"] = output_condition_name(
                    condition,
                    algolab_condition=args.algolab_condition,
                    direct_condition=args.direct_condition,
                )
                records.append(record)
    else:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            executable = os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE", "")
            browser = p.chromium.launch(
                headless=True,
                executable_path=executable if executable and Path(executable).exists() else None,
                args=["--no-sandbox"],
            )
            try:
                for algolab_row, direct_row in pairs:
                    if not args.direct_only:
                        print(f"SEMANTIC_BROWSER {algolab_row['case_id']} algolab_full", flush=True)
                        record = audit_browser_record(browser, algolab_row)
                        record["condition"] = args.algolab_condition
                        records.append(record)
                    if not args.algolab_only:
                        print(f"SEMANTIC_BROWSER {direct_row['case_id']} direct_html", flush=True)
                        record = audit_browser_record(browser, direct_row)
                        record["condition"] = args.direct_condition
                        records.append(record)
            finally:
                browser.close()

    by_key = {(row.get("condition"), row.get("case_id")): row for row in records}
    if args.llm_judge:
        for algolab_row, direct_row in pairs:
            algolab_record = by_key[(args.algolab_condition, algolab_row["case_id"])]
            direct_record = by_key[(args.direct_condition, direct_row["case_id"])]
            judge = run_llm_pair_judge(
                algolab_record=algolab_record,
                direct_record=direct_record,
                model=args.model,
            )
            pair_judges.append({"case_id": algolab_row["case_id"], **judge})
            algolab_record["llm_judge"] = judge["algolab_full"]
            direct_record["llm_judge"] = judge["direct_html"]

    report = write_reports(output_dir, records, pair_judges)
    summary = report["summary"]
    print(json.dumps({"summary": summary, "output_dir": str(output_dir.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
