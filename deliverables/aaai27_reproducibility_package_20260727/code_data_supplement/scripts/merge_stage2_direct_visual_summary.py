"""Merge Stage2-vs-Direct same-rubric visual results into the full experiment summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCORE_FIELDS = (
    "problem_visual_alignment",
    "algorithm_state_readability",
    "process_transition_clarity",
    "instructional_visual_design",
)


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def repo_path(path: Path | str) -> str:
    item = Path(path)
    if not item.is_absolute():
        return str(item)
    try:
        return str(item.relative_to(ROOT))
    except ValueError:
        return str(item)


def rate(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def count_metric(count: int, total: int) -> dict[str, Any]:
    return {"count": int(count), "total": int(total), "rate": rate(int(count), int(total))}


def score_delta(stage2_value: float | int | None, direct_value: float | int | None) -> float | None:
    if stage2_value is None or direct_value is None:
        return None
    return round(float(stage2_value) - float(direct_value), 3)


def build_visual_comparison(stage2_report: dict[str, Any], direct_report: dict[str, Any]) -> dict[str, Any]:
    stage2_summary = stage2_report["external_visual_summary"]
    direct_summary = direct_report["visual_summary"]
    stage2_machine = stage2_report["machine_summary"]
    stage2_total = int(stage2_summary["evaluated"])
    direct_total = int(direct_summary["evaluated"])
    avg_stage2 = stage2_summary["avg_scores"]
    avg_direct = direct_summary["avg_scores"]
    pass_stage2 = stage2_summary["dimension_pass_counts"]
    pass_direct = direct_summary["dimension_pass_counts"]
    strong_stage2 = stage2_summary["dimension_strong_counts"]
    strong_direct = direct_summary["dimension_strong_counts"]

    dimensions = {}
    for field in SCORE_FIELDS:
        dimensions[field] = {
            "stage2_avg": avg_stage2.get(field),
            "direct_avg": avg_direct.get(field),
            "delta_stage2_minus_direct": score_delta(avg_stage2.get(field), avg_direct.get(field)),
            "stage2_pass": count_metric(int(pass_stage2.get(field) or 0), stage2_total),
            "direct_pass": count_metric(int(pass_direct.get(field) or 0), direct_total),
            "stage2_strong_ge4": count_metric(int(strong_stage2.get(field) or 0), stage2_total),
            "direct_strong_ge4": count_metric(int(strong_direct.get(field) or 0), direct_total),
        }

    stage2_browser_ok = int((stage2_machine.get("bool_counts") or {}).get("browser_smoke_ok") or 0)
    direct_browser_ok = int(direct_summary.get("browser_ok") or 0)
    return {
        "scope": "same-rubric external visual review on desktop screenshots; Stage2 is a display-layer comparison, not the Stage1 correctness gate",
        "updated_at": now_iso(),
        "stage2_condition": stage2_report.get("condition"),
        "direct_condition": direct_report.get("condition"),
        "stage2_report": repo_path(stage2_report.get("source_report") or ""),
        "direct_report": repo_path(direct_report.get("source_report") or ""),
        "stage2_eval_report": "output/experiments/algotutorgen_full_200_20260706/stage2_eval/stage2_visual_eval_report.json",
        "direct_visual_eval_report": "output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/visual_baseline_eval_report.json",
        "coverage": {
            "stage2_evaluated": count_metric(stage2_total, int(stage2_summary["total_available"])),
            "direct_evaluated": count_metric(direct_total, int(direct_summary["total_available"])),
            "stage2_valid_vlm": count_metric(int(stage2_summary["ok"]), stage2_total),
            "direct_valid_vlm": count_metric(int(direct_summary["ok"]), direct_total),
            "stage2_browser_ok": count_metric(stage2_browser_ok, stage2_total),
            "direct_browser_ok": count_metric(direct_browser_ok, direct_total),
            "direct_browser_error_cases": direct_summary.get("browser_error_cases") or [],
        },
        "overall": {
            "stage2_avg_score": stage2_summary.get("overall_avg_score"),
            "direct_avg_score": direct_summary.get("overall_avg_score"),
            "delta_stage2_minus_direct": score_delta(
                stage2_summary.get("overall_avg_score"),
                direct_summary.get("overall_avg_score"),
            ),
            "stage2_all_dimensions_pass": count_metric(int(stage2_summary["all_dimensions_pass"]), stage2_total),
            "direct_all_dimensions_pass": count_metric(int(direct_summary["all_dimensions_pass"]), direct_total),
        },
        "dimensions": dimensions,
        "low_score_cases": {
            "stage2": stage2_summary.get("low_score_cases") or {},
            "direct": direct_summary.get("low_score_cases") or {},
        },
        "token_usage": {
            "stage2_external_visual": stage2_summary.get("model_usage") or {},
            "direct_visual_baseline": direct_summary.get("model_usage") or {},
        },
        "interpretation": (
            "Stage2 is stronger on overall visual score, all-dimension pass count, problem-visual alignment, "
            "instructional visual design, and browser/page-error-free rendering. Direct remains a strong visual baseline "
            "and slightly leads on average algorithm-state readability and process-transition clarity in static screenshots."
        ),
    }


def fmt_rate(metric: dict[str, Any]) -> str:
    return f"{metric['count']}/{metric['total']} ({metric['rate']:.3f})"


def fmt_delta(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.3f}"


def fmt_score(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return str(value)


def build_markdown_section(comparison: dict[str, Any]) -> str:
    coverage = comparison["coverage"]
    overall = comparison["overall"]
    dims = comparison["dimensions"]
    direct_errors = [str(item.get("case_id")) for item in coverage["direct_browser_error_cases"]]
    lines = [
        "## Stage2 vs Direct Same-Rubric Visual Evaluation",
        "",
        "这一节补齐 Direct baseline 的同口径四维视觉评估。两边都使用桌面截图、同一套 Munzner/LORI/Mayer-inspired rubric、同一 VLM 评分脚本；Direct 中 12 个有浏览器/pageerror 的页面没有被剔除，只要截图存在就纳入评分，并单独记录 browser/page-error-free 覆盖率。",
        "",
        "| Metric | Stage2 Creative | Direct HTML | Delta |",
        "|---|---:|---:|---:|",
        f"| Browser/page-error free | {fmt_rate(coverage['stage2_browser_ok'])} | {fmt_rate(coverage['direct_browser_ok'])} | {fmt_delta(coverage['stage2_browser_ok']['rate'] - coverage['direct_browser_ok']['rate'])} |",
        f"| Valid VLM responses | {fmt_rate(coverage['stage2_valid_vlm'])} | {fmt_rate(coverage['direct_valid_vlm'])} | {fmt_delta(coverage['stage2_valid_vlm']['rate'] - coverage['direct_valid_vlm']['rate'])} |",
        f"| All four dimensions pass | {fmt_rate(overall['stage2_all_dimensions_pass'])} | {fmt_rate(overall['direct_all_dimensions_pass'])} | {fmt_delta(overall['stage2_all_dimensions_pass']['rate'] - overall['direct_all_dimensions_pass']['rate'])} |",
        f"| Overall average score | {fmt_score(overall['stage2_avg_score'])}/5 | {fmt_score(overall['direct_avg_score'])}/5 | {fmt_delta(overall['delta_stage2_minus_direct'])} |",
        f"| Problem-visual alignment | {fmt_score(dims['problem_visual_alignment']['stage2_avg'])}/5 | {fmt_score(dims['problem_visual_alignment']['direct_avg'])}/5 | {fmt_delta(dims['problem_visual_alignment']['delta_stage2_minus_direct'])} |",
        f"| Algorithm-state readability | {fmt_score(dims['algorithm_state_readability']['stage2_avg'])}/5 | {fmt_score(dims['algorithm_state_readability']['direct_avg'])}/5 | {fmt_delta(dims['algorithm_state_readability']['delta_stage2_minus_direct'])} |",
        f"| Process-transition clarity | {fmt_score(dims['process_transition_clarity']['stage2_avg'])}/5 | {fmt_score(dims['process_transition_clarity']['direct_avg'])}/5 | {fmt_delta(dims['process_transition_clarity']['delta_stage2_minus_direct'])} |",
        f"| Instructional visual design | {fmt_score(dims['instructional_visual_design']['stage2_avg'])}/5 | {fmt_score(dims['instructional_visual_design']['direct_avg'])}/5 | {fmt_delta(dims['instructional_visual_design']['delta_stage2_minus_direct'])} |",
        "",
        "- 结论：Stage2 在整体视觉均分、四维全通过数量、题面-视觉贴合、教学视觉设计、浏览器无错率上领先；Direct HTML 视觉 baseline 本身很强，在静态截图下的算法状态可读性和过程清晰度均分略高。",
        f"- Direct browser/pageerror cases retained in scoring: {', '.join(direct_errors) if direct_errors else 'none'}.",
        f"- Direct visual baseline VLM usage: {comparison['token_usage']['direct_visual_baseline'].get('call_count')} calls, {comparison['token_usage']['direct_visual_baseline'].get('total_tokens')} tokens, {comparison['token_usage']['direct_visual_baseline'].get('duration_s')}s model duration.",
        f"- Direct visual baseline report: `{comparison['direct_visual_eval_report']}`.",
        "",
    ]
    return "\n".join(lines)


def upsert_markdown_line(markdown: str, section_header: str, prefix: str, new_line: str, after_prefix: str) -> str:
    if section_header not in markdown:
        return markdown.rstrip() + "\n" + new_line + "\n"
    start = markdown.index(section_header)
    end = markdown.find("\n## ", start + len(section_header))
    if end == -1:
        end = len(markdown)
    section = markdown[start:end]
    lines = [line for line in section.splitlines() if not line.startswith(prefix)]
    insert_at = len(lines)
    for idx, line in enumerate(lines):
        if line.startswith(after_prefix):
            insert_at = idx + 1
            break
    lines.insert(insert_at, new_line)
    return markdown[:start] + "\n".join(lines).rstrip() + "\n" + markdown[end:]


def upsert_key_path_lines(markdown: str, lines_to_add: list[str]) -> str:
    result = markdown
    for line in lines_to_add:
        key = line.split("`", 2)[1] if "`" in line else line
        prefix = f"- `{key}`:"
        result = upsert_markdown_line(result, "## Key Paths", prefix, line, "- `stage2_eval_manifest`:")
    return result


def replace_markdown_section(markdown: str, section: str) -> str:
    header = "## Stage2 vs Direct Same-Rubric Visual Evaluation"
    next_header = "## Machine Interaction Evaluation"
    if header in markdown:
        start = markdown.index(header)
        end = markdown.find("\n## ", start + len(header))
        if end == -1:
            end = len(markdown)
        return markdown[:start].rstrip() + "\n\n" + section.rstrip() + "\n\n" + markdown[end:].lstrip()
    if next_header not in markdown:
        return markdown.rstrip() + "\n\n" + section.rstrip() + "\n"
    idx = markdown.index(next_header)
    return markdown[:idx].rstrip() + "\n\n" + section.rstrip() + "\n\n" + markdown[idx:].lstrip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("output/experiments/algotutorgen_full_200_20260706/report/experiment_summary.json"),
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=Path("output/experiments/algotutorgen_full_200_20260706/report/experiment_summary.md"),
    )
    parser.add_argument(
        "--stage2-report",
        type=Path,
        default=Path("output/experiments/algotutorgen_full_200_20260706/stage2_eval/stage2_visual_eval_report.json"),
    )
    parser.add_argument(
        "--direct-visual-report",
        type=Path,
        default=Path("output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/visual_baseline_eval_report.json"),
    )
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    args = parse_args()
    summary_json = resolve(args.summary_json)
    summary_md = resolve(args.summary_md)
    stage2_report_path = resolve(args.stage2_report)
    direct_report_path = resolve(args.direct_visual_report)

    summary = load_json(summary_json)
    stage2_report = load_json(stage2_report_path)
    direct_report = load_json(direct_report_path)
    comparison = build_visual_comparison(stage2_report, direct_report)

    summary.setdefault("stage2_creative_visual", {}).setdefault("evaluation", {})[
        "direct_same_rubric_visual_baseline"
    ] = comparison
    summary.setdefault("paths", {})["direct_visual_eval_report"] = repo_path(direct_report_path)
    summary.setdefault("paths", {})["direct_visual_eval_manifest"] = repo_path(
        "output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/screenshots/report_html_screenshots.json"
    )
    direct_usage = comparison["token_usage"]["direct_visual_baseline"]
    token_usage = summary.setdefault("token_usage", {})
    token_usage["direct_visual_eval_calls"] = direct_usage.get("call_count")
    token_usage["direct_visual_eval_tokens"] = direct_usage.get("total_tokens")
    token_usage["direct_visual_eval_usage_available"] = direct_usage.get("usage_available")
    token_usage["direct_visual_eval_usage_available_count"] = direct_usage.get("usage_available_count")
    token_usage["direct_visual_eval_duration_s"] = direct_usage.get("duration_s")
    summary.setdefault("interpretation", {})[
        "stage2_vs_direct_visual"
    ] = comparison["interpretation"]
    write_json(summary_json, summary)

    section = build_markdown_section(comparison)
    markdown = summary_md.read_text(encoding="utf-8")
    markdown = replace_markdown_section(markdown, section)
    direct_usage = comparison["token_usage"]["direct_visual_baseline"]
    markdown = upsert_markdown_line(
        markdown,
        "## Token Usage",
        "- Direct visual baseline VLM review:",
        (
            "- Direct visual baseline VLM review: "
            f"{direct_usage.get('call_count')} calls, {direct_usage.get('total_tokens')} tokens "
            f"({direct_usage.get('usage_available_count')}/{direct_usage.get('call_count')} calls with usage), "
            f"{direct_usage.get('duration_s')}s model duration."
        ),
        "- Direct baseline generation:",
    )
    markdown = upsert_key_path_lines(
        markdown,
        [
            "- `direct_visual_eval_report`: `output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/visual_baseline_eval_report.json`",
            "- `direct_visual_eval_manifest`: `output/experiments/algotutorgen_full_200_20260706/direct_visual_eval/screenshots/report_html_screenshots.json`",
        ],
    )
    summary_md.write_text(markdown, encoding="utf-8")

    print(
        json.dumps(
            {
                "summary_json": repo_path(summary_json),
                "summary_md": repo_path(summary_md),
                "overall": comparison["overall"],
                "coverage": {
                    key: comparison["coverage"][key]
                    for key in (
                        "stage2_evaluated",
                        "direct_evaluated",
                        "stage2_browser_ok",
                        "direct_browser_ok",
                    )
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
