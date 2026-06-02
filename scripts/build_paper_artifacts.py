"""Build paper-facing tables, figure copies, and failure case notes."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def copy_figure(src: Path, dest: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"missing figure source: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def rate(passed: int, total: int) -> float | None:
    return round(passed / total, 6) if total else None


def table1_deterministic_gate_summary(dashboard: dict[str, Any], family_gate: dict[str, Any]) -> list[dict[str, Any]]:
    summary = family_gate.get("summary") or {}
    return [
        {
            "metric": "dashboard_generation",
            "passed": int(dashboard.get("passed") or 0),
            "total": int(dashboard.get("total") or 0),
            "rate": rate(int(dashboard.get("passed") or 0), int(dashboard.get("total") or 0)),
            "source": "output/aaai_dashboard_all/dashboard.json",
        },
        {
            "metric": "family_answer_gate",
            "passed": int(summary.get("answer_passed_samples") or 0),
            "total": int(summary.get("sample_count") or 0),
            "rate": summary.get("answer_pass_rate"),
            "source": "output/aaai_release_gate/family_release_gate.json",
        },
        {
            "metric": "family_process_gate",
            "passed": int(summary.get("process_passed_samples") or 0),
            "total": int(summary.get("sample_count") or 0),
            "rate": summary.get("process_pass_rate"),
            "source": "output/aaai_release_gate/family_release_gate.json",
        },
        {
            "metric": "demo_readiness_gate",
            "passed": int(summary.get("demo_ready_cases") or 0),
            "total": int(summary.get("demo_required_cases") or 0),
            "rate": summary.get("demo_readiness_pass_rate"),
            "source": "output/aaai_release_gate/family_release_gate.json",
        },
    ]


def table2_browser_screenshot_summary(
    deterministic_manifest: dict[str, Any],
    condition_manifest: dict[str, Any],
    direct_failure_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    deterministic = deterministic_manifest.get("screenshots") or []
    rows.append(
        {
            "source": "deterministic_phase17",
            "condition": "deterministic",
            "screenshots": len(deterministic),
            "ok": sum(1 for item in deterministic if item.get("ok")),
            "failed": sum(1 for item in deterministic if not item.get("ok")),
            "zero_byte": sum(1 for item in deterministic if int(item.get("bytes") or 0) <= 0),
        }
    )
    for condition, count in sorted((condition_manifest.get("condition_counts") or {}).items()):
        records = [item for item in condition_manifest.get("screenshots") or [] if item.get("condition") == condition]
        rows.append(
            {
                "source": "llm_condition_desktop",
                "condition": condition,
                "screenshots": count,
                "ok": sum(1 for item in records if item.get("ok")),
                "failed": sum(1 for item in records if not item.get("ok")),
                "zero_byte": sum(1 for item in records if int(item.get("bytes") or 0) <= 0),
            }
        )
    if direct_failure_manifest:
        records = direct_failure_manifest.get("screenshots") or []
        rows.append(
            {
                "source": "direct_html_failed_desktop",
                "condition": "direct_html_baseline",
                "screenshots": len(records),
                "ok": sum(1 for item in records if item.get("ok")),
                "failed": sum(1 for item in records if not item.get("ok")),
                "zero_byte": sum(1 for item in records if int(item.get("bytes") or 0) <= 0),
            }
        )
    return rows


def table4_unseen_family_summary(merged_llm: dict[str, Any]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for item in merged_llm.get("results") or []:
        if item.get("condition") != "unseen_algolab_full":
            continue
        family = str(item.get("family") or "unknown")
        row = rows.setdefault(
            family,
            {"family": family, "total": 0, "passed": 0, "failed": 0, "failure_types": {}},
        )
        row["total"] += 1
        if item.get("ok"):
            row["passed"] += 1
        else:
            failure_type = str(item.get("failure_type") or "unknown")
            row["failed"] += 1
            row["failure_types"][failure_type] = row["failure_types"].get(failure_type, 0) + 1
    result = []
    for row in sorted(rows.values(), key=lambda item: item["family"]):
        result.append(
            {
                "family": row["family"],
                "total": row["total"],
                "passed": row["passed"],
                "failed": row["failed"],
                "pass_rate": rate(row["passed"], row["total"]),
                "failure_types": json.dumps(row["failure_types"], ensure_ascii=False, sort_keys=True),
            }
        )
    return result


def table6_ablation_comparison(condition_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_condition = {row["condition"]: row for row in condition_rows}
    baseline = float(by_condition.get("algolab_full", {}).get("pass_rate") or 0.0)
    order = [
        "algolab_full",
        "direct_html_baseline",
        "no_process_validator",
        "no_scenegraph_compiler",
        "no_repair",
    ]
    rows = []
    for condition in order:
        row = by_condition.get(condition)
        if not row:
            continue
        pass_rate = float(row.get("pass_rate") or 0.0)
        rows.append(
            {
                "condition": condition,
                "kind": row.get("kind", ""),
                "total": row.get("total", ""),
                "passed": row.get("passed", ""),
                "failed": row.get("failed", ""),
                "pass_rate": pass_rate,
                "delta_vs_algolab_full": round(pass_rate - baseline, 6),
                "failure_types": row.get("failure_types", "{}"),
            }
        )
    return rows


def first_direct_failure_screenshot(manifest: dict[str, Any] | None) -> Path | None:
    if not manifest:
        return None
    for record in manifest.get("screenshots") or []:
        screenshot = Path(str(record.get("screenshot") or ""))
        if screenshot.exists() and int(record.get("bytes") or 0) > 0:
            return screenshot
    return None


def lowest_vlm_screenshot(vlm_report: dict[str, Any]) -> Path:
    candidates = []
    for result in vlm_report.get("results") or []:
        scores = result.get("scores")
        screenshot = Path(str(result.get("screenshot") or ""))
        if not isinstance(scores, dict) or not screenshot.exists():
            continue
        overall = scores.get("overall_teaching_quality")
        if overall is not None:
            candidates.append((int(overall), str(result.get("condition") or ""), str(result.get("case_id") or ""), screenshot))
    if not candidates:
        raise FileNotFoundError("no VLM screenshot with an overall score")
    candidates.sort()
    return candidates[0][3]


def vlm_issue_lookup(vlm_report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for result in vlm_report.get("results") or []:
        key = (str(result.get("condition") or ""), str(result.get("case_id") or ""))
        if key not in lookup:
            lookup[key] = result
    return lookup


def failure_screenshot_lookup(manifest: dict[str, Any] | None) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    if not manifest:
        return lookup
    for record in manifest.get("screenshots") or []:
        lookup[(str(record.get("condition") or ""), str(record.get("case_id") or ""))] = str(record.get("screenshot") or "")
    return lookup


def failure_case_markdown(merged_llm: dict[str, Any], vlm_report: dict[str, Any], direct_failure_manifest: dict[str, Any] | None) -> str:
    vlm_by_case = vlm_issue_lookup(vlm_report)
    failure_shots = failure_screenshot_lookup(direct_failure_manifest)
    failures = [item for item in merged_llm.get("results") or [] if not item.get("ok")]
    failures.sort(key=lambda item: (str(item.get("condition") or ""), str(item.get("failure_type") or ""), str(item.get("case_id") or "")))
    lines = [
        "# Failure Cases",
        "",
        "| Case | Family | Condition | Sample | Expected | Actual / Error | Failure Type | Repair | Artifact | Screenshot | VLM Issues | Reason |",
        "|---|---|---|---:|---|---|---|---|---|---|---|---|",
    ]
    for item in failures:
        condition = str(item.get("condition") or "")
        case_id = str(item.get("case_id") or "")
        vlm = vlm_by_case.get((condition, case_id), {})
        issues = "; ".join(issue.get("message", "") for issue in (vlm.get("issues") or [])[:2])
        errors = item.get("errors") if isinstance(item.get("errors"), list) else []
        actual = "; ".join(str(error) for error in errors[:2]) or str(item.get("error") or "")
        reason = actual[:140] or str(item.get("failure_type") or "unknown")
        repair = any(str(phase.get("phase", "")).startswith("repair_round_") for phase in item.get("phase_timings") or [])
        screenshot = str(vlm.get("screenshot") or failure_shots.get((condition, case_id), ""))
        lines.append(
            "| "
            + " | ".join(
                _md_cell(value)
                for value in [
                    case_id,
                    item.get("family", ""),
                    condition,
                    item.get("sample_index", ""),
                    json.dumps(item.get("expected", ""), ensure_ascii=False),
                    actual[:180],
                    item.get("failure_type", ""),
                    "yes" if repair else "no",
                    item.get("html", ""),
                    screenshot,
                    issues[:180],
                    reason,
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def write_readme(output_dir: Path) -> None:
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# AAAI Paper Artifacts",
                "",
                "This directory contains paper-facing tables, representative figures, and failure case notes generated from the E1-E9 experiment outputs.",
                "",
                "## Tables",
                "",
                "- `tables/table1_deterministic_gate_summary.csv`",
                "- `tables/table2_browser_screenshot_summary.csv`",
                "- `tables/table3_llm_condition_summary.csv`",
                "- `tables/table4_unseen_family_summary.csv`",
                "- `tables/table5_failure_type_distribution.csv`",
                "- `tables/table6_ablation_comparison.csv`",
                "- `tables/table7_vlm_teaching_quality_by_condition.csv`",
                "",
                "## Figures",
                "",
                "- `figures/figure1_dashboard_overview.png`",
                "- `figures/figure2_dp_formula_expanded.png`",
                "- `figures/figure3_graph_relax_path.png`",
                "- `figures/figure4_string_matching.png`",
                "- `figures/figure5_wrong_option_feedback.png`",
                "- `figures/figure6_direct_html_baseline_failure.png`",
                "- `figures/figure7_vlm_low_score_case.png`",
                "",
                "## Failure Cases",
                "",
                "- `failure_cases.md` lists representative failed cases with condition, failure type, artifact path, screenshot path, and VLM issues when available.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def build_paper_artifacts(
    *,
    output_dir: Path,
    evaluation_dir: Path,
    deterministic_screenshot_manifest: Path,
    condition_screenshot_manifest: Path,
    direct_failure_manifest: Path | None,
    dashboard_json: Path,
    family_gate_json: Path,
    merged_llm_report: Path,
    vlm_report: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    dashboard = load_json(dashboard_json)
    family_gate = load_json(family_gate_json)
    merged_llm = load_json(merged_llm_report)
    vlm = load_json(vlm_report)
    deterministic_manifest = load_json(deterministic_screenshot_manifest)
    condition_manifest = load_json(condition_screenshot_manifest)
    direct_failure = load_json(direct_failure_manifest) if direct_failure_manifest and direct_failure_manifest.exists() else None

    write_csv(tables_dir / "table1_deterministic_gate_summary.csv", table1_deterministic_gate_summary(dashboard, family_gate))
    write_csv(
        tables_dir / "table2_browser_screenshot_summary.csv",
        table2_browser_screenshot_summary(deterministic_manifest, condition_manifest, direct_failure),
    )
    shutil.copy2(evaluation_dir / "evaluation_condition_summary.csv", tables_dir / "table3_llm_condition_summary.csv")
    write_csv(tables_dir / "table4_unseen_family_summary.csv", table4_unseen_family_summary(merged_llm))
    shutil.copy2(evaluation_dir / "evaluation_failure_types.csv", tables_dir / "table5_failure_type_distribution.csv")
    write_csv(tables_dir / "table6_ablation_comparison.csv", table6_ablation_comparison(read_csv_rows(evaluation_dir / "evaluation_condition_summary.csv")))
    shutil.copy2(evaluation_dir / "evaluation_vlm_condition_summary.csv", tables_dir / "table7_vlm_teaching_quality_by_condition.csv")

    copy_figure(Path("output/aaai_screenshots_all/dashboard_index_desktop.png"), figures_dir / "figure1_dashboard_overview.png")
    copy_figure(Path("output/aaai_screenshots_all/phase17_interaction_formula_expanded_desktop.png"), figures_dir / "figure2_dp_formula_expanded.png")
    copy_figure(Path("output/aaai_screenshots_all/dijkstra_shortest_path_desktop.png"), figures_dir / "figure3_graph_relax_path.png")
    copy_figure(Path("output/aaai_screenshots_all/kmp_desktop.png"), figures_dir / "figure4_string_matching.png")
    copy_figure(Path("output/aaai_screenshots_all/phase17_interaction_wrong_feedback_desktop.png"), figures_dir / "figure5_wrong_option_feedback.png")
    direct_failure_screenshot = first_direct_failure_screenshot(direct_failure)
    if direct_failure_screenshot is None:
        raise FileNotFoundError("direct HTML failure screenshot manifest has no screenshot")
    copy_figure(direct_failure_screenshot, figures_dir / "figure6_direct_html_baseline_failure.png")
    copy_figure(lowest_vlm_screenshot(vlm), figures_dir / "figure7_vlm_low_score_case.png")

    (output_dir / "failure_cases.md").write_text(failure_case_markdown(merged_llm, vlm, direct_failure), encoding="utf-8")
    write_readme(output_dir)
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("output/aaai_paper_artifacts"))
    parser.add_argument("--evaluation-dir", type=Path, default=Path("output/aaai_evaluation"))
    parser.add_argument("--deterministic-screenshot-manifest", type=Path, default=Path("output/aaai_screenshots_all/phase17_screenshots.json"))
    parser.add_argument("--condition-screenshot-manifest", type=Path, default=Path("output/aaai_vlm_conditions/screenshots/report_html_screenshots.json"))
    parser.add_argument("--direct-failure-manifest", type=Path, default=Path("output/aaai_paper_artifacts/direct_html_failure_screenshots/report_html_screenshots.json"))
    parser.add_argument("--dashboard", type=Path, default=Path("output/aaai_dashboard_all/dashboard.json"))
    parser.add_argument("--family-gate", type=Path, default=Path("output/aaai_release_gate/family_release_gate.json"))
    parser.add_argument("--merged-llm-report", type=Path, default=Path("output/aaai_evaluation/merged_llm_benchmark_report.json"))
    parser.add_argument("--vlm-report", type=Path, default=Path("output/aaai_vlm_conditions/vlm_condition_scores.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = build_paper_artifacts(
        output_dir=args.output_dir,
        evaluation_dir=args.evaluation_dir,
        deterministic_screenshot_manifest=args.deterministic_screenshot_manifest,
        condition_screenshot_manifest=args.condition_screenshot_manifest,
        direct_failure_manifest=args.direct_failure_manifest,
        dashboard_json=args.dashboard,
        family_gate_json=args.family_gate,
        merged_llm_report=args.merged_llm_report,
        vlm_report=args.vlm_report,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
