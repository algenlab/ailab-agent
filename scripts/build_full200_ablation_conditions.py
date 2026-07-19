"""Build paired full-200 component and no-repair ablation reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_component_ablation_artifacts import VARIANTS, export_variant, load_artifact
from scripts.run_interaction_semantic_eval import MACHINE_BOOL_KEYS, summarize_condition_results
from scripts.run_no_scenegraph_compiler_ablation import render_trace_only_html


def _norm(path: str | Path) -> str:
    return str((ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve())


def build_variant_report(source_report: dict[str, Any], manifest: dict[str, Any], variant: str) -> dict[str, Any]:
    source_by_path = {_norm(row.get("json") or ""): row for row in source_report.get("results") or [] if row.get("json")}
    results = []
    for export in manifest.get("exports") or []:
        if export.get("variant") != variant:
            continue
        source = source_by_path.get(_norm(export.get("source_artifact") or ""))
        if source is None:
            raise ValueError(f"missing source row for {export.get('source_artifact')}")
        results.append(
            {
                **source,
                "condition": variant,
                "ablation": variant,
                "json": export.get("json"),
                "html": export.get("html"),
                "component_counts": export.get("counts") or {},
            }
        )
    results.sort(key=lambda row: str(row.get("case_id")))
    passed = sum(row.get("ok") is True for row in results)
    return {
        "kind": "llm_benchmark_report",
        "condition": variant,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "results": results,
    }


def build_no_repair_report(primary_report: dict[str, Any], final_report: dict[str, Any]) -> dict[str, Any]:
    primary = {str(row.get("case_id")): row for row in primary_report.get("results") or []}
    final = {str(row.get("case_id")): row for row in final_report.get("results") or []}
    if set(primary) != set(final):
        raise ValueError("primary and final case IDs differ")
    results = []
    for case_id in sorted(final):
        row = dict(primary[case_id])
        row["condition"] = "no_repair"
        row["ablation"] = "no_repair"
        row["generation_failed"] = row.get("ok") is not True
        if row["generation_failed"]:
            row["html"] = ""
            row["json"] = ""
        results.append(row)
    passed = sum(row.get("ok") is True for row in results)
    return {
        "kind": "llm_benchmark_report",
        "condition": "no_repair",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "results": results,
    }


def build_no_repair_machine_report(
    no_repair_report: dict[str, Any],
    final_machine_report: dict[str, Any],
) -> dict[str, Any]:
    machine_by_case = {
        str(row.get("case_id")): row
        for row in final_machine_report.get("records") or []
        if row.get("condition") == "algolab_full"
    }
    records = []
    for source in no_repair_report.get("results") or []:
        case_id = str(source.get("case_id"))
        if source.get("generation_failed"):
            record = {**source, "condition": "no_repair"}
            for key in MACHINE_BOOL_KEYS:
                record[key] = False
            record["machine_ok"] = False
            record["console_page_errors"] = [str(source.get("error") or "generation failed")]
        else:
            if case_id not in machine_by_case:
                raise ValueError(f"missing final machine record for {case_id}")
            record = {**machine_by_case[case_id], "condition": "no_repair"}
        records.append(record)
    records.sort(key=lambda row: str(row.get("case_id")))
    return {
        "kind": "interaction_semantic_eval_report",
        "summary": summarize_condition_results(records),
        "records": records,
        "pair_judges": [],
        "derived_from_final_machine_report": True,
    }


def build_conditions(
    source_report_path: Path,
    primary_report_path: Path,
    output_dir: Path,
    *,
    final_machine_report_path: Path | None = None,
) -> dict[str, Any]:
    source_report = json.loads(source_report_path.read_text(encoding="utf-8"))
    primary_report = json.loads(primary_report_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    exports = []
    for row in source_report.get("results") or []:
        if row.get("ok") is not True or not row.get("json"):
            continue
        artifact_path = Path(str(row["json"]))
        if not artifact_path.is_absolute():
            artifact_path = ROOT / artifact_path
        artifact = load_artifact(artifact_path)
        for name in ("full", "no_teaching", "no_interaction", "no_teaching_interaction"):
            exports.append(export_variant(artifact_path, artifact, VARIANTS[name], output_dir / "components", html=True))
        trace_dir = output_dir / "no_scenegraph_compiler"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_html = trace_dir / f"{artifact_path.stem}.html"
        trace_json = trace_html.with_suffix(".json")
        trace_html.write_text(
            render_trace_only_html(
                title=str(row.get("title") or row.get("case_id")),
                input_data=row.get("input_data"),
                expected=row.get("expected"),
                variants=artifact.variants,
                checks=artifact.validation.checks,
                warnings=artifact.validation.warnings,
            ),
            encoding="utf-8",
        )
        trace_json.write_text(json.dumps({"kind": "trace_only", "case_id": row.get("case_id")}, ensure_ascii=False), encoding="utf-8")
        exports.append(
            {
                "source_artifact": str(artifact_path),
                "variant": "no_scenegraph_compiler",
                "json": str(trace_json),
                "html": str(trace_html),
                "counts": {},
            }
        )
    manifest = {"kind": "full200_ablation_manifest", "total_exports": len(exports), "exports": exports}
    (output_dir / "ablation_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    reports = {}
    for variant in ("full", "no_teaching", "no_interaction", "no_teaching_interaction", "no_scenegraph_compiler"):
        report = build_variant_report(source_report, manifest, variant)
        report_path = output_dir / variant / "llm_benchmark_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        reports[variant] = str(report_path)
    no_repair = build_no_repair_report(primary_report, source_report)
    no_repair_path = output_dir / "no_repair" / "llm_benchmark_report.json"
    no_repair_path.parent.mkdir(parents=True, exist_ok=True)
    no_repair_path.write_text(json.dumps(no_repair, ensure_ascii=False, indent=2), encoding="utf-8")
    reports["no_repair"] = str(no_repair_path)
    if final_machine_report_path is not None:
        final_machine = json.loads(final_machine_report_path.read_text(encoding="utf-8"))
        no_repair_machine = build_no_repair_machine_report(no_repair, final_machine)
        machine_path = output_dir / "no_repair" / "interaction_semantic_eval_report.json"
        machine_path.write_text(json.dumps(no_repair_machine, ensure_ascii=False, indent=2), encoding="utf-8")
        reports["no_repair_machine"] = str(machine_path)
    return {"manifest": str(output_dir / "ablation_manifest.json"), "reports": reports}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--primary-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--final-machine-report", type=Path, default=None)
    args = parser.parse_args()
    source = args.source_report if args.source_report.is_absolute() else ROOT / args.source_report
    primary = args.primary_report if args.primary_report.is_absolute() else ROOT / args.primary_report
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    machine = None
    if args.final_machine_report is not None:
        machine = args.final_machine_report if args.final_machine_report.is_absolute() else ROOT / args.final_machine_report
    result = build_conditions(source, primary, output, final_machine_report_path=machine)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
