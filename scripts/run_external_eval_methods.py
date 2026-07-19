"""Run external-framework evaluation for generated algorithm learning pages.

This script is intentionally separate from the internal interaction-semantic
evaluator. It maps existing black-box browser audit evidence into established
evaluation frames:

* Naps et al. learner engagement taxonomy for algorithm visualization.
* TRAKLA2-style automatic assessment checks for algorithm simulation exercises.
* LORI/MERLOT-style anonymous peer review for learning-object quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_json_with_metadata, llm_config
from scripts.audit_direct_html_answer import html_to_searchable_text


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

NAPS_LEVELS = {
    "no_viewing": 0,
    "viewing": 1,
    "responding": 2,
    "changing": 3,
    "constructing": 4,
    "presenting": 5,
}

TRAKLA2_COMPONENTS = [
    "executable_page",
    "model_answer_visible",
    "learner_action_reachable",
    "bidirectional_feedback",
    "answer_oracle_available",
    "learning_log",
    "mutation_free",
]

EXTERNAL_REVIEW_SCORE_KEYS = [
    "content_quality",
    "learning_goal_alignment",
    "feedback_adaptation",
    "interaction_usability",
    "presentation_design",
    "teaching_effectiveness",
    "ease_of_use",
]

METHOD_SOURCES = {
    "naps_engagement_taxonomy": {
        "label": "Naps et al. learner engagement taxonomy",
        "url": "https://users.cs.duke.edu/~rodger/jflappapers/Naps2002.pdf",
        "note": "Engagement levels: no viewing, viewing, responding, changing, constructing, presenting.",
    },
    "trakla2": {
        "label": "TRAKLA2 automatic assessment for visual algorithm simulation exercises",
        "url": "https://research.aalto.fi/en/publications/visual-algorithm-simulation-exercise-system-with-automatic-assess/",
        "note": "Used here as a style of model-solution and automatic-feedback evaluation.",
    },
    "merlot": {
        "label": "MERLOT peer review rubric",
        "url": "https://info.merlot.org/merlothelp/MERLOT_Peer_Review_Information.htm",
        "note": "MERLOT peer reviews focus on content quality, potential effectiveness as a teaching tool, and ease of use.",
    },
    "lori": {
        "label": "Learning Object Review Instrument",
        "url": "https://edutechwiki.unige.ch/en/Learning_Object_Review_Instrument",
        "note": "Used as a learning-object quality rubric with rating scales and comments.",
    },
}


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_depth > 0:
            self._skip_depth += 1
            return
        tag_lower = tag.lower()
        attrs_map = {name.lower(): (value or "") for name, value in attrs}
        classes = attrs_map.get("class", "").lower()
        node_id = attrs_map.get("id", "").lower()
        hidden = attrs_map.get("hidden") is not None or attrs_map.get("aria-hidden", "").lower() == "true"
        debug_like = any(
            token in f"{node_id} {classes}"
            for token in ("debug", "drawer", "raw", "artifact", "validation", "schema", "shader")
        )
        if tag_lower in {"script", "style", "template", "noscript"} or hidden or debug_like:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self.parts.append(text)


def visible_html_text(html: str) -> str:
    parser = _VisibleTextParser()
    try:
        parser.feed(html or "")
    except Exception:
        return html_to_searchable_text(html or "")
    return _compact_text(" ".join(parser.parts), limit=200000)


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 1
    return max(1, min(5, score))


def normalize_blind_label(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"A", "B", "TIE"}:
        return text
    if text in {"DRAW", "EQUAL", "NONE"}:
        return "TIE"
    return "TIE"


def normalize_scores(raw_scores: Any) -> dict[str, int]:
    data = raw_scores if isinstance(raw_scores, dict) else {}
    return {key: clamp_score(data.get(key)) for key in EXTERNAL_REVIEW_SCORE_KEYS}


def normalize_external_review_result(raw: dict[str, Any], *, blind_map: dict[str, str]) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    raw_scores = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    winner_label = normalize_blind_label(data.get("winner"))
    winner = "tie" if winner_label == "TIE" else blind_map.get(winner_label, "tie")
    conditions: dict[str, Any] = {}
    for blind_label, condition in blind_map.items():
        conditions[condition] = {
            "blind_label": blind_label,
            "scores": normalize_scores(raw_scores.get(blind_label)),
            "summary": str(
                data.get(f"{blind_label}_summary")
                or data.get(f"{blind_label.lower()}_summary")
                or ""
            )[:800],
        }
    return {
        "winner": winner,
        "blind_map": dict(blind_map),
        "conditions": conditions,
        "rationale": str(data.get("rationale") or "")[:1200],
        "raw": data,
    }


def html_feature_flags(html_path: Path) -> dict[str, bool]:
    if not html_path.exists():
        return {
            "input_change_supported": False,
            "construction_supported": False,
            "presentation_supported": False,
        }
    try:
        html = html_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {
            "input_change_supported": False,
            "construction_supported": False,
            "presentation_supported": False,
        }
    text = html_to_searchable_text(html).lower()
    raw = html.lower()
    input_change_terms = [
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
    ]
    construction_terms = [
        "construct your own",
        "build your own",
        "create visualization",
        "draw the",
        "构建自己的",
        "自己构建",
        "绘制算法",
        "创建可视化",
    ]
    presentation_terms = [
        "present to",
        "share your explanation",
        "peer review",
        "class presentation",
        "展示给",
        "向同学展示",
        "同伴评审",
    ]
    has_free_input = bool(re.search(r"<textarea|<input", raw))
    return {
        "input_change_supported": has_free_input and any(term in text for term in input_change_terms),
        "construction_supported": any(term in text for term in construction_terms),
        "presentation_supported": any(term in text for term in presentation_terms),
    }


def naps_level_from_features(features: dict[str, Any]) -> dict[str, Any]:
    if not features.get("page_load_ok"):
        level = "no_viewing"
        reasons = ["page did not load"]
    elif features.get("presentation_supported"):
        level = "presenting"
        reasons = ["artifact supports presenting or peer sharing"]
    elif features.get("construction_supported"):
        level = "constructing"
        reasons = ["artifact supports learner construction of a visualization or artifact"]
    elif features.get("input_change_supported"):
        level = "changing"
        reasons = ["artifact appears to support learner input changes and rerun"]
    elif (
        features.get("interaction_reachable")
        and features.get("correct_feedback_ok")
        and features.get("wrong_feedback_ok")
    ):
        level = "responding"
        reasons = ["learner can respond and receive both correct and wrong feedback"]
    else:
        level = "viewing"
        reasons = ["artifact is viewable but does not meet responding/changing criteria"]
    return {
        "level": level,
        "score": NAPS_LEVELS[level],
        "reasons": reasons,
    }


def trakla2_style_scores(record: dict[str, Any]) -> dict[str, Any]:
    components = {
        "executable_page": bool(record.get("page_load_ok")),
        "model_answer_visible": bool(record.get("visible_answer_match")),
        "learner_action_reachable": bool(record.get("interaction_reachable")),
        "bidirectional_feedback": bool(record.get("correct_feedback_ok") and record.get("wrong_feedback_ok")),
        "answer_oracle_available": bool(record.get("show_answer_ok")),
        "learning_log": bool(record.get("learning_log_ok")),
        "mutation_free": bool(record.get("mutation_free_ok")),
    }
    return {
        "components": components,
        "score": sum(1 for value in components.values() if value),
        "max_score": len(components),
        "core_pass": all(components.values()),
    }


def external_machine_record(record: dict[str, Any]) -> dict[str, Any]:
    html_path = _repo_path(str(record.get("html") or ""))
    flags = {
        key: bool(record.get(key))
        for key in MACHINE_BOOL_KEYS
    }
    flags.update(html_feature_flags(html_path))
    return {
        "condition": record.get("condition"),
        "case_id": record.get("case_id"),
        "title": record.get("title"),
        "family": record.get("family"),
        "html": record.get("html"),
        "naps_engagement": naps_level_from_features(flags),
        "trakla2_style": trakla2_style_scores(record),
        "feature_flags": flags,
    }


def summarize_external_machine(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("condition"))].append(record)

    summary: dict[str, dict[str, Any]] = {}
    for condition, rows in sorted(grouped.items()):
        level_counts = Counter(row["naps_engagement"]["level"] for row in rows)
        component_counts = {
            key: sum(1 for row in rows if row["trakla2_style"]["components"].get(key))
            for key in TRAKLA2_COMPONENTS
        }
        total = len(rows)
        avg_naps = sum(row["naps_engagement"]["score"] for row in rows) / total if total else 0.0
        avg_trakla = sum(row["trakla2_style"]["score"] for row in rows) / total if total else 0.0
        core_pass = sum(1 for row in rows if row["trakla2_style"]["core_pass"])
        summary[condition] = {
            "total": total,
            "naps_level_counts": dict(level_counts),
            "avg_naps_score": round(avg_naps, 3),
            "trakla2_core_pass": core_pass,
            "trakla2_core_pass_rate": core_pass / total if total else 0.0,
            "avg_trakla2_score": round(avg_trakla, 3),
            "trakla2_component_counts": component_counts,
        }
    return summary


def _compact_text(text: str, *, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    return compact[:limit]


def compact_page_evidence(record: dict[str, Any]) -> dict[str, Any]:
    html_path = _repo_path(str(record.get("html") or ""))
    text = str(record.get("rendered_text") or record.get("rendered_text_excerpt") or "").strip()
    if not text and html_path.exists():
        try:
            text = visible_html_text(html_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            text = ""
    snippets: list[str] = []
    for pattern in [
        r"(?i)(checkpoint|quiz|hint|feedback|learning log|answer|prediction|rubric).{0,180}",
        r"(检查点|预测|提示|反馈|学习日志|答案|最终输出|讲解).{0,180}",
    ]:
        for match in re.finditer(pattern, text):
            snippet = _compact_text(match.group(0), limit=240)
            if snippet and snippet not in snippets:
                snippets.append(snippet)
            if len(snippets) >= 8:
                break
        if len(snippets) >= 8:
            break
    return {
        "title": record.get("title"),
        "behavior_audit": {key: bool(record.get(key)) for key in MACHINE_BOOL_KEYS},
        "text_excerpt": _compact_text(text, limit=2600),
        "interaction_snippets": snippets,
    }


def blind_labels_for_case(case_id: str, *, order: str = "frozen") -> dict[str, str]:
    digest = hashlib.sha256(case_id.encode("utf-8")).hexdigest()
    if int(digest[:8], 16) % 2 == 0:
        labels = {"A": "algolab_full", "B": "direct_html"}
    else:
        labels = {"A": "direct_html", "B": "algolab_full"}
    if order == "swapped":
        return {"A": labels["B"], "B": labels["A"]}
    if order != "frozen":
        raise ValueError(f"unknown blind order: {order}")
    return labels


def build_external_review_prompt(
    *,
    case_id: str,
    title: str,
    input_data: Any,
    expected: Any,
    blind_map: dict[str, str],
    evidence_by_condition: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    system = (
        "你是匿名教育资源同行评审员。请使用外部学习对象评价框架 LORI 和 MERLOT 的口径，"
        "比较两个同一算法题的交互式学习页面。你不知道哪个系统生成了页面。"
        "不要奖励某个系统的内部字段、框架名或自称；只根据页面文本、黑盒行为审计和学习材料证据评分。"
        "只输出 JSON 对象。"
    )
    artifacts = {}
    for label, condition in blind_map.items():
        artifacts[label] = evidence_by_condition[condition]
    user = json.dumps(
        {
            "task": "anonymous_lori_merlot_learning_object_review",
            "rubric": {
                "content_quality": "1-5: 内容是否准确、完整、没有明显算法或概念错误。",
                "learning_goal_alignment": "1-5: 页面讲解、练习和答案是否对齐题目与学习目标。",
                "feedback_adaptation": "1-5: 是否有有用的提示、正误反馈、纠错说明或适应性支持。",
                "interaction_usability": "1-5: 交互控件是否可达、行为清楚、不会进入死状态。",
                "presentation_design": "1-5: 信息层次、可读性、视觉组织和状态可见性。",
                "teaching_effectiveness": "1-5: 作为教学工具的潜在有效性，参考 MERLOT 的教学有效性维度。",
                "ease_of_use": "1-5: 学生和教师使用时是否容易理解、导航和操作。",
            },
            "required_json_schema": {
                "winner": "A | B | tie",
                "scores": {
                    "A": {key: "integer 1-5" for key in EXTERNAL_REVIEW_SCORE_KEYS},
                    "B": {key: "integer 1-5" for key in EXTERNAL_REVIEW_SCORE_KEYS},
                },
                "A_summary": "one short Chinese sentence",
                "B_summary": "one short Chinese sentence",
                "rationale": "2-4 concise Chinese sentences",
            },
            "case": {
                "case_id": case_id,
                "title": title,
                "input_data": input_data,
                "expected": expected,
            },
            "artifacts": artifacts,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return system, user


def run_external_review_pair(
    *,
    case_id: str,
    algolab_record: dict[str, Any],
    direct_record: dict[str, Any],
    model: str | None,
    blind_order: str = "frozen",
) -> dict[str, Any]:
    blind_map = blind_labels_for_case(case_id, order=blind_order)
    evidence_by_condition = {
        "algolab_full": compact_page_evidence(algolab_record),
        "direct_html": compact_page_evidence(direct_record),
    }
    system, user = build_external_review_prompt(
        case_id=case_id,
        title=str(algolab_record.get("title") or direct_record.get("title") or case_id),
        input_data=algolab_record.get("input_data") or direct_record.get("input_data"),
        expected=algolab_record.get("expected") or direct_record.get("expected"),
        blind_map=blind_map,
        evidence_by_condition=evidence_by_condition,
    )
    response = chat_json_with_metadata(system, user, model=model, kind="external_lori_merlot_review")
    normalized = normalize_external_review_result(response["content"], blind_map=blind_map)
    normalized["case_id"] = case_id
    normalized["model_calls"] = response.get("model_calls") or []
    return normalized


def summarize_external_reviews(pair_reviews: list[dict[str, Any]]) -> dict[str, Any]:
    grouped_scores: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    winner_counts = Counter()
    usage = {
        "calls": 0,
        "usage_available_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    for review in pair_reviews:
        winner_counts[str(review.get("winner") or "tie")] += 1
        for condition, item in (review.get("conditions") or {}).items():
            for key, value in (item.get("scores") or {}).items():
                grouped_scores[condition][key].append(clamp_score(value))
        for call in review.get("model_calls") or []:
            usage["calls"] += 1
            if call.get("usage_available"):
                usage["usage_available_calls"] += 1
                usage["prompt_tokens"] += int(call.get("prompt_tokens") or 0)
                usage["completion_tokens"] += int(call.get("completion_tokens") or 0)
                usage["total_tokens"] += int(call.get("total_tokens") or 0)

    score_summary: dict[str, dict[str, Any]] = {}
    for condition, by_key in grouped_scores.items():
        score_summary[condition] = {
            f"avg_{key}": round(sum(values) / len(values), 3) if values else None
            for key, values in by_key.items()
        }
        all_values = [value for values in by_key.values() for value in values]
        score_summary[condition]["avg_overall"] = round(sum(all_values) / len(all_values), 3) if all_values else None
    return {
        "score_summary": score_summary,
        "winner_counts": dict(winner_counts),
        "token_usage": usage,
    }


def load_machine_records(machine_report: Path, *, cases: set[str] | None = None, max_cases: int = 0) -> list[dict[str, Any]]:
    report = json.loads(machine_report.read_text(encoding="utf-8"))
    wanted = set(cases or set())
    records = [
        record
        for record in report.get("records") or []
        if record.get("condition") in {"algolab_full", "direct_html"}
        and (not wanted or record.get("case_id") in wanted)
    ]
    if max_cases:
        case_order: list[str] = []
        for record in records:
            case_id = str(record.get("case_id"))
            if case_id not in case_order:
                case_order.append(case_id)
        allowed = set(case_order[:max_cases])
        records = [record for record in records if record.get("case_id") in allowed]
    return records


def pair_records(records: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    by_case: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        by_case[str(record.get("case_id"))][str(record.get("condition"))] = record
    pairs = []
    for case_id, rows in by_case.items():
        if "algolab_full" in rows and "direct_html" in rows:
            pairs.append((case_id, rows["algolab_full"], rows["direct_html"]))
    return pairs


def write_reports(
    *,
    output_dir: Path,
    machine_records: list[dict[str, Any]],
    external_records: list[dict[str, Any]],
    pair_reviews: list[dict[str, Any]],
    execution: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    machine_summary = summarize_external_machine(external_records)
    review_summary = summarize_external_reviews(pair_reviews)
    report = {
        "kind": "external_eval_methods_report",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "method_sources": METHOD_SOURCES,
        "execution": execution,
        "llm": llm_config(),
        "machine_summary": machine_summary,
        "external_review_summary": review_summary,
        "external_records": external_records,
        "pair_reviews": pair_reviews,
        "source_machine_record_count": len(machine_records),
    }
    json_path = output_dir / "external_eval_methods_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# External Evaluation Methods Report",
        "",
        f"- created_at: `{report['created_at']}`",
        f"- json: `{json_path.relative_to(ROOT)}`",
        f"- source records: `{len(machine_records)}`",
        "",
        "## External Machine Summary",
        "",
        "| Condition | Total | Avg Naps | Naps Levels | TRAKLA2 Core Pass | Avg TRAKLA2 |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for condition, item in machine_summary.items():
        levels = ", ".join(f"{key}:{value}" for key, value in sorted(item["naps_level_counts"].items()))
        lines.append(
            f"| {condition} | {item['total']} | {item['avg_naps_score']} | {levels} | "
            f"{item['trakla2_core_pass']} ({item['trakla2_core_pass_rate']:.3f}) | {item['avg_trakla2_score']} |"
        )
    if pair_reviews:
        lines.extend(
            [
                "",
                "## Anonymous LORI/MERLOT Review",
                "",
                "| Condition | Overall | Content | Goal Align | Feedback | Interaction | Presentation | Teaching | Ease |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        scores = review_summary["score_summary"]
        for condition, item in sorted(scores.items()):
            lines.append(
                f"| {condition} | {item.get('avg_overall')} | {item.get('avg_content_quality')} | "
                f"{item.get('avg_learning_goal_alignment')} | {item.get('avg_feedback_adaptation')} | "
                f"{item.get('avg_interaction_usability')} | {item.get('avg_presentation_design')} | "
                f"{item.get('avg_teaching_effectiveness')} | {item.get('avg_ease_of_use')} |"
            )
        winners = review_summary["winner_counts"]
        lines.extend(
            [
                "",
                "Winner counts:",
                f"- algolab_full: `{winners.get('algolab_full', 0)}`",
                f"- direct_html: `{winners.get('direct_html', 0)}`",
                f"- tie: `{winners.get('tie', 0)}`",
                "",
                "Token usage:",
                f"- calls: `{review_summary['token_usage']['calls']}`",
                f"- total_tokens: `{review_summary['token_usage']['total_tokens']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Method Sources",
            "",
            *[f"- {item['label']}: {item['url']}" for item in METHOD_SOURCES.values()],
            "",
        ]
    )
    (output_dir / "external_eval_methods_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--llm-review", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--blind-order", choices=["frozen", "swapped"], default="frozen")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    machine_report = _repo_path(args.machine_report)
    output_dir = _repo_path(args.output_dir)
    records = load_machine_records(machine_report, cases=set(args.case), max_cases=int(args.max_cases or 0))
    external_records = [external_machine_record(record) for record in records]
    pairs = pair_records(records)
    pair_reviews: list[dict[str, Any]] = []

    review_dir = output_dir / "_lori_merlot_cases"
    if args.llm_review:
        review_dir.mkdir(parents=True, exist_ok=True)

        def run_or_load(pair: tuple[str, dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
            case_id, algolab_record, direct_record = pair
            shard_path = review_dir / f"{case_id}.json"
            if shard_path.exists() and not args.force:
                return json.loads(shard_path.read_text(encoding="utf-8"))
            print(f"EXTERNAL_REVIEW_START {case_id}", flush=True)
            review = run_external_review_pair(
                case_id=case_id,
                algolab_record=algolab_record,
                direct_record=direct_record,
                model=args.model,
                blind_order=args.blind_order,
            )
            shard_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"EXTERNAL_REVIEW_DONE {case_id} winner={review.get('winner')}", flush=True)
            return review

        if args.concurrency <= 1:
            pair_reviews = [run_or_load(pair) for pair in pairs]
        else:
            with ThreadPoolExecutor(max_workers=max(1, int(args.concurrency))) as executor:
                futures = {executor.submit(run_or_load, pair): pair[0] for pair in pairs}
                for future in as_completed(futures):
                    pair_reviews.append(future.result())
            pair_reviews.sort(key=lambda item: str(item.get("case_id")))

    report = write_reports(
        output_dir=output_dir,
        machine_records=records,
        external_records=external_records,
        pair_reviews=pair_reviews,
        execution={
            "machine_report": str(machine_report.relative_to(ROOT)),
            "case_count": len(pairs),
            "llm_review": bool(args.llm_review),
            "model": args.model,
            "concurrency": int(args.concurrency),
            "blind_order": args.blind_order,
        },
    )
    print(
        json.dumps(
            {
                "output_dir": str(output_dir.relative_to(ROOT)),
                "machine_summary": report["machine_summary"],
                "external_review_summary": report["external_review_summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
