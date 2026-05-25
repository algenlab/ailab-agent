"""Build research evaluation metrics and a compact report.

This script consumes deterministic dashboard/manifest outputs and, when
available, a live LLM benchmark report. It keeps human teaching scores explicit:
without a human ratings CSV the score is reported as missing instead of being
estimated by an automatic proxy.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_evaluation_manifest import build_manifest


MetricValue = int | float | str | None


def build_evaluation_report(
    *,
    output_dir: Path,
    manifest_path: Path | None = None,
    dashboard_path: Path | None = None,
    llm_report_path: Path | None = None,
    human_ratings_path: Path | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_json_or_manifest(manifest_path)
    dashboard = _load_json(dashboard_path) if dashboard_path and dashboard_path.exists() else None
    llm_report = _load_json(llm_report_path) if llm_report_path and llm_report_path.exists() else None
    human_scores = _load_human_scores(human_ratings_path) if human_ratings_path and human_ratings_path.exists() else None

    metrics = compute_metrics(
        manifest=manifest,
        dashboard=dashboard,
        llm_report=llm_report,
        human_scores=human_scores,
    )
    case_rows = core_case_rows(manifest=manifest, dashboard=dashboard)
    comparisons = comparison_protocols()
    report = {
        "schema_version": "evaluation-report-v1",
        "inputs": {
            "manifest": str(manifest_path) if manifest_path else "generated_in_memory",
            "dashboard": str(dashboard_path) if dashboard_path else "",
            "llm_report": str(llm_report_path) if llm_report_path else "",
            "human_ratings": str(human_ratings_path) if human_ratings_path else "",
        },
        "dataset_summary": manifest["summary"],
        "metrics": metrics,
        "comparisons": comparisons,
        "core_case_rows": case_rows,
    }

    json_path = output_dir / "evaluation_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_metrics_csv(output_dir / "evaluation_metrics.csv", metrics)
    _write_comparisons_csv(output_dir / "evaluation_comparisons.csv", comparisons)
    _write_core_cases_csv(output_dir / "evaluation_core_cases.csv", case_rows)
    (output_dir / "evaluation_report.md").write_text(_render_markdown(report), encoding="utf-8")
    return json_path


def compute_metrics(
    *,
    manifest: dict[str, Any],
    dashboard: dict[str, Any] | None = None,
    llm_report: dict[str, Any] | None = None,
    human_scores: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        _generation_success_rate(dashboard, llm_report),
        _contract_pass_rate(dashboard),
        _correctness_gate_pass_rate(dashboard, llm_report),
        _repair_success_rate(llm_report),
        _visual_smoke_pass_rate(llm_report),
        _interaction_coverage(dashboard),
        _human_teaching_quality_score(human_scores),
        {
            "name": "dataset_case_count",
            "value": manifest["summary"]["case_count"],
            "numerator": manifest["summary"]["case_count"],
            "denominator": manifest["summary"]["case_count"],
            "source": "evaluation_manifest",
            "status": "ok",
            "note": "科研评估数据集 case 数。",
        },
    ]


def core_case_rows(*, manifest: dict[str, Any], dashboard: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    demo_by_id = {demo["id"]: demo for demo in (dashboard or {}).get("demos", [])}
    rows: list[dict[str, Any]] = []
    for case in manifest.get("cases", []):
        demo = demo_by_id.get(case["id"], {})
        rows.append(
            {
                "id": case["id"],
                "title": case["title"],
                "suite": case["suite"],
                "family": case["family"],
                "strata": ";".join(case["strata"]),
                "sample_count": case["sample_count"],
                "expected_layouts": ";".join(case["expected_layouts"]),
                "dashboard_ok": demo.get("ok", ""),
                "contract_ready": demo.get("contract_gate_ready", ""),
                "contract_test_pass_rate": demo.get("contract_test_pass_rate", ""),
                "interaction_coverage": demo.get("interaction_coverage", ""),
                "actual_render_target": demo.get("actual_render_target", ""),
            }
        )
    return rows


def comparison_protocols() -> list[dict[str, Any]]:
    return [
        {
            "baseline": "pure_llm_judge",
            "label": "纯 LLM judge",
            "comparison_question": "LLM 只判断答案/讲解是否正确时，能否达到 correctness gate 的可复核性。",
            "ours_condition": "solve/trace/verifier/contract/process/scene 全链路机器校验后发布。",
            "baseline_condition": "同一输入和模型输出交给 LLM judge 打分，不执行 sandbox、oracle 或 process invariant。",
            "primary_metrics": ["correctness_gate_pass_rate", "contract_pass_rate", "generation_success_rate"],
            "fairness_constraints": [
                "使用同一题目、输入和 expected。",
                "LLM judge 不能访问 AlgoLab 的 validation errors。",
                "报告必须区分 judge 通过和机器 gate 通过。",
            ],
            "expected_evidence": "per-case CSV 中记录 baseline_judge_result、gate_result、disagreement_reason。",
        },
        {
            "baseline": "code2video_manim",
            "label": "code2video / Manim 类系统",
            "comparison_question": "手写或生成视频/动画管线与可交互 verified runtime 在正确性证据和复用性上的差异。",
            "ours_condition": "同一 SceneGraph 输出 stable/spatial/creative 页面，并保留 contract、render report 和 artifact。",
            "baseline_condition": "对同一题目生成视频或 Manim 动画；若不能执行 correctness gate，标记为 no_machine_gate。",
            "primary_metrics": ["visual_smoke_pass_rate", "interaction_coverage", "human_teaching_quality_score"],
            "fairness_constraints": [
                "不要求 baseline 使用 AlgoLab renderer。",
                "必须记录是否有可执行 oracle 和过程 trace。",
                "视觉评分只比较最终教学产物，不把 AlgoLab 的内部 JSON 当成用户体验优势。",
            ],
            "expected_evidence": "每题保留 baseline artifact 路径、是否可交互、是否有机器正确性证据。",
        },
        {
            "baseline": "no_correctness_gate_renderer",
            "label": "无 correctness gate 的 renderer",
            "comparison_question": "去掉 correctness gate 后，生成成功率提升是否以错误发布风险为代价。",
            "ours_condition": "release_ready=false 时不发布精确演示。",
            "baseline_condition": "跳过 contract/process/scene gate，尽量渲染 LLM trace 或 deterministic trace。",
            "primary_metrics": ["generation_success_rate", "correctness_gate_pass_rate", "visual_smoke_pass_rate"],
            "fairness_constraints": [
                "renderer 能力保持一致，只改变 gate 策略。",
                "必须记录被 AlgoLab 阻断但 baseline 发布的样例。",
                "不得把概念视频兜底算作精确过程演示。",
            ],
            "expected_evidence": "核心表格中记录 blocked_by_gate、baseline_published、machine_detected_error。",
        },
    ]


def _generation_success_rate(dashboard: dict[str, Any] | None, llm_report: dict[str, Any] | None) -> dict[str, Any]:
    if llm_report:
        results = llm_report.get("results") or []
        total = len(results)
        generated = sum(1 for item in results if _phase_ok(item, "generate") or (item.get("ok") and not item.get("phase_timings")))
        return _rate_metric(
            "generation_success_rate",
            generated,
            total,
            "llm_benchmark_report",
            "LLM generate 阶段成功完成的样例占比。",
        )
    if dashboard:
        return _rate_metric(
            "generation_success_rate",
            int(dashboard.get("passed") or 0),
            int(dashboard.get("total") or 0),
            "demo_dashboard",
            "deterministic dashboard 中成功 materialize 的 demo 占比。",
        )
    return _missing_metric("generation_success_rate", "缺少 dashboard 或 LLM benchmark report。")


def _contract_pass_rate(dashboard: dict[str, Any] | None) -> dict[str, Any]:
    if not dashboard:
        return _missing_metric("contract_pass_rate", "缺少 dashboard report。")
    demos = dashboard.get("demos") or []
    passed = sum(1 for demo in demos if demo.get("contract_gate_ready"))
    return _rate_metric("contract_pass_rate", passed, len(demos), "demo_dashboard", "contract gate ready 的 demo 占比。")


def _correctness_gate_pass_rate(dashboard: dict[str, Any] | None, llm_report: dict[str, Any] | None) -> dict[str, Any]:
    if llm_report:
        return _rate_metric(
            "correctness_gate_pass_rate",
            int(llm_report.get("passed") or 0),
            int(llm_report.get("total") or 0),
            "llm_benchmark_report",
            "LLM benchmark release gate 通过率。",
        )
    if dashboard:
        return _rate_metric(
            "correctness_gate_pass_rate",
            int(dashboard.get("passed") or 0),
            int(dashboard.get("total") or 0),
            "demo_dashboard",
            "demo dashboard release gate 通过率。",
        )
    return _missing_metric("correctness_gate_pass_rate", "缺少 dashboard 或 LLM benchmark report。")


def _repair_success_rate(llm_report: dict[str, Any] | None) -> dict[str, Any]:
    if not llm_report:
        return _missing_metric("repair_success_rate", "缺少 LLM benchmark report；deterministic dashboard 不执行 repair。")
    repaired = []
    for item in llm_report.get("results") or []:
        if any(str(phase.get("phase", "")).startswith("repair_round_") for phase in item.get("phase_timings") or []):
            repaired.append(item)
    passed = sum(1 for item in repaired if item.get("ok"))
    return _rate_metric("repair_success_rate", passed, len(repaired), "llm_benchmark_report", "进入 repair 后最终通过的样例占比。")


def _visual_smoke_pass_rate(llm_report: dict[str, Any] | None) -> dict[str, Any]:
    if not llm_report:
        return _missing_metric("visual_smoke_pass_rate", "缺少包含 browser_smoke 的 LLM benchmark report。")
    checks = llm_report.get("browser_smoke") or []
    passed = sum(1 for item in checks if item.get("ok"))
    return _rate_metric("visual_smoke_pass_rate", passed, len(checks), "llm_benchmark_report", "浏览器 smoke 通过率。")


def _interaction_coverage(dashboard: dict[str, Any] | None) -> dict[str, Any]:
    if not dashboard:
        return _missing_metric("interaction_coverage", "缺少 dashboard report。")
    total_interactions = 0
    total_frames = 0
    for demo in dashboard.get("demos") or []:
        interactions, frames = _parse_fraction(str(demo.get("interaction_coverage") or "0/0"))
        total_interactions += interactions
        total_frames += frames
    return _rate_metric("interaction_coverage", total_interactions, total_frames, "demo_dashboard", "带交互题的 frame 占比。")


def _human_teaching_quality_score(human_scores: dict[str, Any] | None) -> dict[str, Any]:
    if not human_scores:
        return {
            "name": "human_teaching_quality_score",
            "value": None,
            "numerator": 0,
            "denominator": 0,
            "source": "human_ratings_csv",
            "status": "missing",
            "note": "未提供人工评分 CSV；不使用自动代理分冒充人工评分。",
        }
    return {
        "name": "human_teaching_quality_score",
        "value": human_scores["mean_score"],
        "numerator": human_scores["score_sum"],
        "denominator": human_scores["score_count"],
        "source": "human_ratings_csv",
        "status": "ok",
        "note": "人工评分均值；CSV 支持 score 或多个数值维度列。",
    }


def _rate_metric(name: str, numerator: int, denominator: int, source: str, note: str) -> dict[str, Any]:
    if denominator <= 0:
        return {
            "name": name,
            "value": None,
            "numerator": numerator,
            "denominator": denominator,
            "source": source,
            "status": "not_applicable",
            "note": note,
        }
    return {
        "name": name,
        "value": round(numerator / denominator, 6),
        "numerator": numerator,
        "denominator": denominator,
        "source": source,
        "status": "ok",
        "note": note,
    }


def _missing_metric(name: str, note: str) -> dict[str, Any]:
    return {
        "name": name,
        "value": None,
        "numerator": 0,
        "denominator": 0,
        "source": "",
        "status": "missing",
        "note": note,
    }


def _phase_ok(item: dict[str, Any], phase_name: str) -> bool:
    return any(phase.get("phase") == phase_name and phase.get("status") == "ok" for phase in item.get("phase_timings") or [])


def _parse_fraction(value: str) -> tuple[int, int]:
    left, sep, right = value.partition("/")
    if not sep:
        return 0, 0
    try:
        return int(left), int(right)
    except ValueError:
        return 0, 0


def _load_human_scores(path: Path) -> dict[str, Any]:
    scores: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if "score" in row and row["score"] not in {None, ""}:
                scores.append(float(row["score"]))
                continue
            for key, value in row.items():
                if key in {"case_id", "id", "rater", "notes"} or value in {None, ""}:
                    continue
                scores.append(float(value))
    score_sum = round(sum(scores), 6)
    return {
        "score_count": len(scores),
        "score_sum": score_sum,
        "mean_score": round(score_sum / len(scores), 6) if scores else None,
    }


def _write_metrics_csv(path: Path, metrics: list[dict[str, Any]]) -> None:
    fields = ["name", "value", "numerator", "denominator", "source", "status", "note"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(metrics)


def _write_comparisons_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "baseline",
        "label",
        "comparison_question",
        "ours_condition",
        "baseline_condition",
        "primary_metrics",
        "fairness_constraints",
        "expected_evidence",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["primary_metrics"] = ";".join(item["primary_metrics"])
            item["fairness_constraints"] = ";".join(item["fairness_constraints"])
            writer.writerow(item)


def _write_core_cases_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AlgoLab Evaluation Report",
        "",
        "## Dataset",
        "",
        f"- Cases: {report['dataset_summary']['case_count']}",
        f"- Samples: {report['dataset_summary']['sample_count']}",
        f"- ML demos: {report['dataset_summary']['ml_demo_count']}",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Numerator | Denominator | Status | Source |",
        "|---|---:|---:|---:|---|---|",
    ]
    for metric in report["metrics"]:
        value = "N/A" if metric["value"] is None else metric["value"]
        lines.append(
            f"| {metric['name']} | {value} | {metric['numerator']} | {metric['denominator']} | {metric['status']} | {metric['source']} |"
        )
    lines.extend(["", "## Comparisons", "", "| Baseline | Primary Metrics | Evidence |", "|---|---|---|"])
    for row in report["comparisons"]:
        metrics = ", ".join(row["primary_metrics"])
        lines.append(f"| {row['label']} | {metrics} | {row['expected_evidence']} |")
    return "\n".join(lines) + "\n"


def _load_json_or_manifest(path: Path | None) -> dict[str, Any]:
    if path and path.exists():
        return _load_json(path)
    return build_manifest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 AlgoLab 科研评估指标和报告")
    parser.add_argument("--output-dir", type=Path, default=Path("output/evaluation"), help="输出目录")
    parser.add_argument("--manifest", type=Path, default=Path("output/evaluation/evaluation_manifest.json"), help="evaluation manifest JSON")
    parser.add_argument("--dashboard", type=Path, default=Path("output/dashboard/dashboard.json"), help="dashboard JSON")
    parser.add_argument("--llm-report", type=Path, default=None, help="可选 llm_benchmark_report.json")
    parser.add_argument("--human-ratings", type=Path, default=None, help="可选人工教学质量评分 CSV")
    args = parser.parse_args()

    path = build_evaluation_report(
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        dashboard_path=args.dashboard,
        llm_report_path=args.llm_report,
        human_ratings_path=args.human_ratings,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
