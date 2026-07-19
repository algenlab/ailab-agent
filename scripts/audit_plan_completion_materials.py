"""Audit completed automated experiments and pending blind human-evaluation packages."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT_ROOT = ROOT / "output/experiments/algotutorgen_plan_completion_20260713"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _unique(rows: list[dict[str, Any]], key: str) -> bool:
    values = [str(row.get(key) or "") for row in rows]
    return bool(values) and all(values) and len(values) == len(set(values))


def _blank_except(rows: list[dict[str, Any]], allowed: set[str]) -> bool:
    return all(
        not str(value or "").strip()
        for row in rows
        for key, value in row.items()
        if key not in allowed
    )


def _refs_exist(root: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> bool:
    return all((root / str(row.get(field) or "")).exists() for row in rows for field in fields)


def _machine_result(report: dict[str, Any], condition: str) -> list[int]:
    summary = report.get("summary", {}).get(condition, {})
    return [int(summary.get("machine_ok", -1)), int(summary.get("total", -1))]


def _audit_automated_experiments(root: Path) -> tuple[dict[str, Any], dict[str, bool]]:
    main_report = _json(ROOT / "output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json")
    webgen_report = _json(ROOT / "output/external_baselines/webgen/audit_all200_sample0/report.json")
    htmlcure_report = _json(ROOT / "output/external_baselines/htmlcure_all200_sample0/behavior_audit/interaction_semantic_eval_report.json")
    repair_report = _json(root / "direct_browser_repair_5/budget_curve_report.json")
    direct_scene_report = _json(root / "nondegenerate_ablations/direct_to_scenegraph_50/machine_audit/interaction_semantic_eval_report.json")
    trace_html_report = _json(root / "nondegenerate_ablations/verified_trace_to_html_50/machine_audit/interaction_semantic_eval_report.json")
    cross_stage1_report = _json(root / "cross_model_50/machine_audit_stage1_corrected/interaction_semantic_eval_report.json")
    cross_direct_report = _json(root / "cross_model_50/machine_audit_direct/interaction_semantic_eval_report.json")
    heldout_stage1_report = _json(root / "heldout_40/machine_audit_stage1/interaction_semantic_eval_report.json")
    heldout_direct_report = _json(root / "heldout_40/machine_audit_direct/interaction_semantic_eval_report.json")
    fault_report = _json(root / "validator_fault_rerun/gate_fault_injection_report.json")
    long_trace_report = _json(root / "long_trace_scalability/long_trace_scalability_report.json")

    main_machine_ok = {
        "algotutorgen": _machine_result(main_report, "algolab_full"),
        "direct": _machine_result(main_report, "direct_html"),
        "webgen": [
            int(webgen_report.get("machine_audit", {}).get("overall", {}).get("machine_ok", -1)),
            int(webgen_report.get("machine_audit", {}).get("overall", {}).get("total", -1)),
        ],
        "htmlcure_strict": _machine_result(htmlcure_report, "direct_html"),
    }
    repair_rows = {str(row.get("call_budget")): row for row in repair_report.get("budgets") or []}
    browser_repair_machine_ok = {
        budget: [int(repair_rows.get(budget, {}).get("machine_ok", -1)), int(repair_rows.get(budget, {}).get("cases", -1))]
        for budget in ("1", "2", "3", "5")
    }
    nondegenerate = {
        "direct_to_scenegraph": {
            "algotutorgen": _machine_result(direct_scene_report, "algolab_full"),
            "ablation": _machine_result(direct_scene_report, "direct_html"),
        },
        "verified_trace_to_html": {
            "algotutorgen": _machine_result(trace_html_report, "algolab_full"),
            "ablation": _machine_result(trace_html_report, "direct_html"),
        },
    }
    cross_model = {
        "algotutorgen": _machine_result(cross_stage1_report, "cross_model_stage1"),
        "direct": _machine_result(cross_direct_report, "direct_html"),
    }
    heldout = {
        "algotutorgen": _machine_result(heldout_stage1_report, "heldout_stage1"),
        "direct": _machine_result(heldout_direct_report, "direct_html"),
    }
    fault_summary = fault_report.get("summary") or {}
    validator_faults = {
        "rejected": [
            int(fault_summary.get("overall", {}).get("rejected", -1)),
            int(fault_summary.get("overall", {}).get("injected", -1)),
        ],
        "clean_accepted": [
            int(fault_summary.get("controls", {}).get("accepted", -1)),
            int(fault_summary.get("controls", {}).get("total", -1)),
        ],
    }
    long_trace = {
        "materialized": [int(long_trace_report.get("passed", -1)), int(long_trace_report.get("total", -1))],
        "browser_passed": [int(long_trace_report.get("browser_passed", -1)), int(long_trace_report.get("total", -1))],
    }
    checks = {
        "main_machine_ok": main_machine_ok == {"algotutorgen": [198, 200], "direct": [98, 200], "webgen": [45, 200], "htmlcure_strict": [40, 200]},
        "browser_repair_curve": browser_repair_machine_ok == {"1": [106, 200], "2": [10, 200], "3": [15, 200], "5": [6, 200]} and all(int(repair_rows[budget].get("self_contained_ok", -1)) == 200 for budget in repair_rows),
        "direct_to_scenegraph": nondegenerate["direct_to_scenegraph"] == {"algotutorgen": [49, 50], "ablation": [1, 50]},
        "verified_trace_to_html": nondegenerate["verified_trace_to_html"] == {"algotutorgen": [49, 50], "ablation": [0, 50]},
        "cross_model": cross_model == {"algotutorgen": [31, 50], "direct": [1, 50]},
        "heldout": heldout == {"algotutorgen": [39, 40], "direct": [18, 40]},
        "validator_faults": validator_faults == {"rejected": [2246, 2400], "clean_accepted": [200, 200]},
        "long_trace": long_trace == {"materialized": [54, 54], "browser_passed": [52, 54]},
    }
    result = {
        "status": "complete" if all(checks.values()) else "audit_failed",
        "main_machine_ok": main_machine_ok,
        "browser_repair_machine_ok": browser_repair_machine_ok,
        "nondegenerate_ablations": nondegenerate,
        "cross_model": cross_model,
        "heldout": heldout,
        "validator_faults": validator_faults,
        "long_trace": long_trace,
        "checks": checks,
    }
    return result, checks


def _audit_evaluator_calibration(root: Path) -> tuple[dict[str, Any], dict[str, bool]]:
    package_root = root / "evaluator_calibration_final"
    manifest = _json(package_root / "package_manifest.json")
    key_rows = _json(package_root / "private_blind_key.json").get("pages") or []
    annotator_a = _csv(package_root / "annotator_a.csv")
    annotator_b = _csv(package_root / "annotator_b.csv")
    analysis = _json(package_root / "calibration_analysis_pending.json")
    method_counts = Counter(str(row.get("method") or "") for row in key_rows)
    family_count = len({str(row.get("family_id") or "") for row in key_rows})
    human_fields = {"human_machine_ok", "equivalent_ui_not_detected", "notes"}
    public_columns = set(annotator_a[0]) if annotator_a else set()
    checks = {
        "manifest_pending": manifest.get("task_count") == 30 and manifest.get("page_count") == 120,
        "key_unique": len(key_rows) == 120 and _unique(key_rows, "blind_id"),
        "method_balance": method_counts == Counter({"stage1": 30, "direct": 30, "webgen": 30, "htmlcure": 30}),
        "family_coverage": family_count == 23,
        "page_refs_exist": _refs_exist(package_root, key_rows, ("page_ref",)),
        "annotator_rows": len(annotator_a) == 120 and len(annotator_b) == 120,
        "annotator_ids_match": {row["blind_id"] for row in annotator_a} == {row["blind_id"] for row in annotator_b} == {row["blind_id"] for row in key_rows},
        "public_blinding": "method" not in public_columns and "condition" not in public_columns,
        "human_labels_blank": all(
            not str(row.get(field) or "").strip()
            for row in annotator_a + annotator_b
            for field in human_fields
        ),
        "analysis_pending": analysis.get("status") == "pending_human_labels" and analysis.get("complete_pairs") == 0,
    }
    result = {
        "status": "pending_human_labels",
        "tasks": manifest.get("task_count"),
        "pages": len(key_rows),
        "families": family_count,
        "method_counts": dict(sorted(method_counts.items())),
        "annotator_rows": {"a": len(annotator_a), "b": len(annotator_b)},
        "checks": checks,
    }
    return result, checks


def _audit_trace_correctness(root: Path) -> tuple[dict[str, Any], dict[str, bool]]:
    package_root = root / "trace_correctness_audit"
    manifest = _json(package_root / "package_manifest.json")
    key_rows = _json(package_root / "private_audit_key.json").get("items") or []
    reviewer_a = _csv(package_root / "reviewer_a.csv")
    reviewer_b = _csv(package_root / "reviewer_b.csv")
    analysis = _json(package_root / "analysis_pending.json")
    family_count = len({str(row.get("family_id") or "") for row in key_rows})
    label_fields = {
        "result_correct",
        "state_transition_correct",
        "dependency_correct",
        "explanation_aligned",
        "critical_error",
        "critical_error_type",
        "critical_error_frame",
        "notes",
    }
    checks = {
        "manifest_pending": manifest.get("status") == "pending_human_labels" and manifest.get("human_labels_present") is False,
        "key_unique": len(key_rows) == 40 and _unique(key_rows, "audit_id"),
        "family_coverage": family_count == 23,
        "item_and_page_refs_exist": _refs_exist(package_root, key_rows, ("item", "page")),
        "reviewer_rows": len(reviewer_a) == 40 and len(reviewer_b) == 40,
        "reviewer_ids_match": {row["audit_id"] for row in reviewer_a} == {row["audit_id"] for row in reviewer_b} == {row["audit_id"] for row in key_rows},
        "human_labels_blank": all(
            not str(row.get(field) or "").strip()
            for row in reviewer_a + reviewer_b
            for field in label_fields
        ),
        "analysis_pending": analysis.get("status") == "pending_human_labels" and analysis.get("agreed_cases") == 0,
    }
    result = {
        "status": "pending_human_labels",
        "items": len(key_rows),
        "families": family_count,
        "reviewer_rows": {"a": len(reviewer_a), "b": len(reviewer_b)},
        "checks": checks,
    }
    return result, checks


def _audit_human_study(root: Path) -> tuple[dict[str, Any], dict[str, bool]]:
    package_root = root / "human_study_protocols"
    manifest = _json(package_root / "package_manifest.json")
    expert_assignments = _csv(package_root / "expert_assignments.csv")
    expert_ratings = _csv(package_root / "expert_ratings.csv")
    expert_key = _json(package_root / "expert_private_key.json").get("rows") or []
    student_assignments = _csv(package_root / "student_assignments.csv")
    student_observations = _csv(package_root / "student_observations.csv")
    student_questionnaires = _csv(package_root / "student_questionnaires.csv")
    student_private = _json(package_root / "student_private_key.json")
    student_trials = student_private.get("trials") or []
    condition_codes = student_private.get("condition_codes") or {}
    analysis = _json(package_root / "human_study_analysis.json")

    public_columns = set(expert_assignments[0]) | set(expert_ratings[0]) | set(student_assignments[0]) | set(student_observations[0]) if expert_assignments and expert_ratings and student_assignments and student_observations else set()
    x_first_balance = Counter(str(mapping.get("X") or "") for mapping in condition_codes.values())
    trials_by_participant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in student_trials:
        trials_by_participant[str(row.get("participant_id") or "")].append(row)
    block_balance = all(
        len(rows) == 12
        and {str(row.get("condition_code") or "") for row in sorted(rows, key=lambda item: int(item["trial"]))[:6]} == {"X"}
        and {str(row.get("condition_code") or "") for row in sorted(rows, key=lambda item: int(item["trial"]))[6:]} == {"Y"}
        and all(str(row.get("condition") or "") == str(condition_codes[participant][str(row.get("condition_code") or "")]) for row in rows)
        for participant, rows in trials_by_participant.items()
    )
    checks = {
        "manifest_pending": manifest.get("status") == "pending_human_data",
        "expert_pair_count": len(expert_assignments) == len(expert_ratings) == len(expert_key) == 90,
        "expert_ids_match": {row["pair_id"] for row in expert_assignments} == {row["pair_id"] for row in expert_ratings} == {row["pair_id"] for row in expert_key},
        "expert_family_available": all(str(row.get("family_id") or "") for row in expert_key),
        "expert_page_refs_exist": _refs_exist(package_root, expert_assignments, ("page_a", "page_b")),
        "expert_labels_blank": _blank_except(expert_ratings, {"expert_id", "pair_id"}),
        "student_trial_count": len(student_assignments) == len(student_observations) == len(student_trials) == 288,
        "student_ids_match": {row["trial_id"] for row in student_assignments} == {row["trial_id"] for row in student_observations} == {row["trial_id"] for row in student_trials},
        "student_page_refs_exist": _refs_exist(package_root, student_assignments, ("page",)),
        "condition_codes_decodable": len(condition_codes) == 24 and all(set(mapping.values()) == {"algotutorgen", "direct"} for mapping in condition_codes.values()),
        "condition_order_balanced": x_first_balance == Counter({"algotutorgen": 12, "direct": 12}) and block_balance,
        "student_labels_blank": _blank_except(student_observations, {"participant_id", "trial_id"}),
        "questionnaires_blank": len(student_questionnaires) == 48 and _blank_except(student_questionnaires, {"participant_id", "condition_code"}),
        "public_blinding": "method" not in public_columns and "condition" not in public_columns,
        "analysis_pending": analysis.get("expert", {}).get("status") == "pending_human_data" and analysis.get("student", {}).get("status") == "pending_human_data",
    }
    result = {
        "status": "pending_human_data",
        "expert_pairs": len(expert_assignments),
        "expert_families": len({str(row.get("family_id") or "") for row in expert_key}),
        "student_trials": len(student_assignments),
        "students": len(condition_codes),
        "questionnaires": len(student_questionnaires),
        "x_first_balance": dict(sorted(x_first_balance.items())),
        "analysis_status": {
            "expert": analysis.get("expert", {}).get("status"),
            "student": analysis.get("student", {}).get("status"),
        },
        "checks": checks,
    }
    return result, checks


def audit_materials(experiment_root: Path) -> dict[str, Any]:
    automated, automated_checks = _audit_automated_experiments(experiment_root)
    calibration, calibration_checks = _audit_evaluator_calibration(experiment_root)
    trace, trace_checks = _audit_trace_correctness(experiment_root)
    human, human_checks = _audit_human_study(experiment_root)
    all_checks = {
        **{f"automated.{key}": value for key, value in automated_checks.items()},
        **{f"calibration.{key}": value for key, value in calibration_checks.items()},
        **{f"trace.{key}": value for key, value in trace_checks.items()},
        **{f"human.{key}": value for key, value in human_checks.items()},
    }
    passed = all(all_checks.values())
    return {
        "kind": "plan_md_final_completion_audit",
        "status": "automated_complete_human_pending" if passed else "audit_failed",
        "all_checks_passed": passed,
        "automated_experiments": automated,
        "evaluator_calibration": calibration,
        "trace_correctness": trace,
        "human_study": human,
        "checks": all_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    experiment_root = args.experiment_root if args.experiment_root.is_absolute() else ROOT / args.experiment_root
    output = args.output or experiment_root / "final_completion_audit.json"
    output = output if output.is_absolute() else ROOT / output
    result = audit_materials(experiment_root)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
