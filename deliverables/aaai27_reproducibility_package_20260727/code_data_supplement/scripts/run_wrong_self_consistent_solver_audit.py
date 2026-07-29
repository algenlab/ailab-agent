#!/usr/bin/env python3
"""Audit wrong-but-self-consistent tracker executions against trusted expected results."""

from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.runtime.executor import results_equivalent
from algolab.runtime.sandbox import run_instrumented_trace
from algolab.pipeline import _try_materialize
from algolab.schemas.execution_record import ExecutionRecord, state_digest
from algolab.schemas.input import ProblemInput
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.execution_record_validator import validate_execution_record


DEFAULT_REPORT = (
    ROOT
    / "output/experiments/algotutorgen_full_200_20260706"
    / "algolab_full_final/llm_benchmark_report.json"
)
DEFAULT_ARTIFACT_DIR = (
    ROOT
    / "output/experiments/algotutorgen_full_200_20260706"
    / "algolab_full"
)
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "output/experiments/plan3_20260725"
    / "wrong_self_consistent_solver_audit"
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mutated_compare(op: ast.cmpop) -> ast.cmpop | None:
    swaps: dict[type[ast.cmpop], type[ast.cmpop]] = {
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.Is: ast.IsNot,
        ast.IsNot: ast.Is,
        ast.In: ast.NotIn,
        ast.NotIn: ast.In,
    }
    replacement = swaps.get(type(op))
    return replacement() if replacement is not None else None


class _CompareMutator(ast.NodeTransformer):
    def __init__(self, node_index: int, op_index: int) -> None:
        self.node_index = node_index
        self.op_index = op_index
        self.current = -1

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.current += 1
        node = self.generic_visit(node)
        if self.current == self.node_index:
            replacement = _mutated_compare(node.ops[self.op_index])
            if replacement is not None:
                node.ops[self.op_index] = replacement
        return node


class _OmitStatementMutator(ast.NodeTransformer):
    def __init__(self, lineno: int, col_offset: int) -> None:
        self.location = (lineno, col_offset)

    def _replace(self, node: ast.stmt) -> ast.stmt:
        if (node.lineno, node.col_offset) == self.location:
            return ast.copy_location(ast.Pass(), node)
        return node

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        return self._replace(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:
        return self._replace(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.AST:
        return self._replace(node)

    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        if _is_update_call(node.value):
            return self._replace(node)
        return self.generic_visit(node)


class _WrongReturnMutator(ast.NodeTransformer):
    def __init__(self, delta: int) -> None:
        self.delta = delta
        self.changed = False

    def visit_Call(self, node: ast.Call) -> ast.AST:
        node = self.generic_visit(node)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "result"
            and node.args
        ):
            node.args[0] = ast.Call(
                func=ast.Name(id="algolab_mutate_result", ctx=ast.Load()),
                args=[node.args[0], ast.Constant(self.delta)],
                keywords=[],
            )
            self.changed = True
        return node


def _is_update_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        in {
            "add",
            "append",
            "decrement",
            "discard",
            "increment",
            "insert",
            "move",
            "pop",
            "push",
            "relax",
            "remove",
            "set",
            "swap",
            "union",
            "update",
        }
    )


def _wrong_result_helper() -> ast.FunctionDef:
    helper = ast.parse(
        '''def algolab_mutate_result(value, delta):
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + delta
    if isinstance(value, str):
        return value + "#mutant" + str(delta)
    if isinstance(value, list):
        return list(value) + [delta]
    if isinstance(value, tuple):
        return list(value) + [delta]
    if isinstance(value, dict):
        mutated = dict(value)
        mutated["mutant_marker"] = delta
        return mutated
    if value is None:
        return delta
    return [value, delta]
'''
    ).body[0]
    assert isinstance(helper, ast.FunctionDef)
    return helper


def _unparse(tree: ast.AST) -> str:
    ast.fix_missing_locations(tree)
    return ast.unparse(tree).rstrip() + "\n"


def generate_mutation_candidates(source: str) -> list[dict[str, Any]]:
    """Return deterministic source mutants ordered by preferred mutation class."""

    tree = ast.parse(source)
    candidates: list[dict[str, Any]] = []
    compare_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)]
    for node_index, node in enumerate(compare_nodes):
        for op_index, op in enumerate(node.ops):
            replacement = _mutated_compare(op)
            if replacement is None:
                continue
            mutated = _CompareMutator(node_index, op_index).visit(deepcopy(tree))
            old_name = type(op).__name__
            new_name = type(replacement).__name__
            mutation_id = (
                f"comparison_boundary-L{node.lineno}C{node.col_offset}-"
                f"O{op_index}-{old_name}-to-{new_name}"
            )
            candidates.append(
                {
                    "mutation_id": mutation_id,
                    "mutation_kind": "comparison_boundary",
                    "location": {"line": node.lineno, "column": node.col_offset},
                    "description": f"{old_name} -> {new_name}",
                    "source": _unparse(mutated),
                }
            )

    update_nodes: list[ast.stmt] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            update_nodes.append(node)
        elif isinstance(node, ast.Expr) and _is_update_call(node.value):
            update_nodes.append(node)
    update_nodes.sort(key=lambda node: (node.lineno, node.col_offset, type(node).__name__))
    for node in update_nodes:
        mutated = _OmitStatementMutator(node.lineno, node.col_offset).visit(deepcopy(tree))
        candidates.append(
            {
                "mutation_id": f"omitted_update-L{node.lineno}C{node.col_offset}-{type(node).__name__}",
                "mutation_kind": "omitted_update",
                "location": {"line": node.lineno, "column": node.col_offset},
                "description": f"omit {type(node).__name__}",
                "source": _unparse(mutated),
            }
        )

    for delta in (1, 2):
        mutator = _WrongReturnMutator(delta)
        mutated = mutator.visit(deepcopy(tree))
        if not mutator.changed:
            continue
        assert isinstance(mutated, ast.Module)
        mutated.body.insert(0, _wrong_result_helper())
        candidates.append(
            {
                "mutation_id": f"wrong_return-delta-{delta}",
                "mutation_kind": "wrong_return",
                "location": {"line": 0, "column": 0},
                "description": f"mutate submitted result with delta {delta}",
                "source": _unparse(mutated),
            }
        )
    return candidates


def _run_once(source: str, input_data: Any, *, timeout_s: int) -> dict[str, Any]:
    bundle = run_instrumented_trace(source, input_data, mode="atomic", timeout_s=timeout_s)
    trace = SemanticTrace.model_validate(bundle["trace"])
    record = ExecutionRecord.model_validate(bundle["execution_record"])
    validation = validate_execution_record(record, trace)
    return {
        "trace": trace,
        "record": record,
        "validation": validation,
        "replay_digest": state_digest(
            {
                "trace": trace.model_dump(mode="json"),
                "result": record.result,
            }
        ),
    }


def evaluate_mutant(
    source: str,
    *,
    input_data: Any,
    expected: Any,
    case_id: str = "",
    family_id: str = "",
    subfamily_id: str = "",
    timeout_s: int = 5,
) -> dict[str, Any]:
    context = {
        "case_id": case_id or None,
        "family_id": family_id or None,
        "subfamily_id": subfamily_id or None,
    }
    try:
        runs = [
            _run_once(source, input_data, timeout_s=timeout_s),
            _run_once(source, input_data, timeout_s=timeout_s),
        ]
    except Exception as exc:
        return {
            "executed_normally": False,
            "same_execution_binding": False,
            "prefix_replay_ok": False,
            "final_replay_ok": False,
            "deterministic_replay_ok": False,
            "oracle_mismatch": False,
            "release_rejected": False,
            "result": None,
            "error": str(exc),
        }

    validations = [run["validation"] for run in runs]
    results = [run["record"].result for run in runs]
    deterministic = (
        runs[0]["replay_digest"] == runs[1]["replay_digest"]
        and results_equivalent(results[0], results[1], **context)
    )
    oracle_mismatch = all(
        not results_equivalent(result, expected, **context) for result in results
    )
    same_binding = all(row.same_execution_binding for row in validations)
    prefix_ok = all(row.prefix_replay_ok for row in validations)
    final_ok = all(row.final_state_ok and row.result_binding_ok for row in validations)
    release = {
        "release_rejected": False,
        "oracle_gate_detected": False,
        "release_evaluation": "not_run_without_oracle_mismatch",
        "release_gate": None,
        "release_errors": [],
    }
    if oracle_mismatch:
        release = _evaluate_pipeline_release(
            source,
            input_data=input_data,
            expected=expected,
            case_id=case_id,
            family_id=family_id,
            subfamily_id=subfamily_id,
        )
    return {
        "executed_normally": True,
        "same_execution_binding": same_binding,
        "prefix_replay_ok": prefix_ok,
        "final_replay_ok": final_ok,
        "deterministic_replay_ok": deterministic,
        "oracle_mismatch": oracle_mismatch,
        "result": results[0],
        "run_ids": [run["record"].run_id for run in runs],
        "execution_validations": [row.model_dump(mode="json") for row in validations],
        "error": "",
        **release,
    }


def _evaluate_pipeline_release(
    source: str,
    *,
    input_data: Any,
    expected: Any,
    case_id: str,
    family_id: str,
    subfamily_id: str,
) -> dict[str, Any]:
    request = ProblemInput(
        problem=case_id or "mutant audit",
        input_data=input_data,
        expected_result=expected,
        solution_count=2,
        teaching_enrichment=False,
        case_id=case_id,
        family_id=family_id,
        subfamily_id=subfamily_id,
        execution_mode="atomic",
    )
    display_code = "def solve(input_data):\n    return None\n"
    spec = {
        "problem_title": case_id or "Mutant audit",
        "input_contract": "frozen audit input",
        "variants": [
            {
                "id": f"mutant_{index}",
                "name": f"Mutant {index}",
                "strategy": "deterministic source mutation",
                "code": display_code,
                "tracker_code": source,
            }
            for index in (1, 2)
        ],
    }
    try:
        artifact, errors = _try_materialize(request, spec)
    except Exception as exc:
        return {
            "release_rejected": False,
            "oracle_gate_detected": False,
            "release_evaluation": "pipeline_materialize",
            "release_gate": None,
            "release_errors": [f"pipeline materialize raised: {exc}"],
        }
    oracle_gate_detected = any("expected" in error and "不一致" in error for error in errors)
    return {
        "release_rejected": not artifact.validation.release_gate.release_ready,
        "oracle_gate_detected": oracle_gate_detected,
        "release_evaluation": "pipeline_materialize",
        "release_gate": artifact.validation.release_gate.model_dump(mode="json"),
        "release_errors": errors,
    }


def _is_applicable(row: dict[str, Any]) -> bool:
    return row.get("executed_normally") is True and row.get("oracle_mismatch") is True


def _prioritized_candidates(source: str) -> list[dict[str, Any]]:
    candidates = generate_mutation_candidates(source)
    by_kind = {
        kind: [row for row in candidates if row["mutation_kind"] == kind]
        for kind in ("comparison_boundary", "omitted_update", "wrong_return")
    }
    return (
        by_kind["comparison_boundary"][:4]
        + by_kind["omitted_update"][:4]
        + by_kind["wrong_return"]
    )


def audit_case(
    *,
    case_id: str,
    family_id: str,
    subfamily_id: str,
    source: str,
    input_data: Any,
    expected: Any,
    target_applicable: int = 2,
    max_attempts: int = 10,
    timeout_s: int = 5,
) -> dict[str, Any]:
    baseline = evaluate_mutant(
        source,
        input_data=input_data,
        expected=expected,
        case_id=case_id,
        family_id=family_id,
        subfamily_id=subfamily_id,
        timeout_s=timeout_s,
    )
    baseline_ok = (
        baseline["executed_normally"]
        and baseline["same_execution_binding"]
        and baseline["prefix_replay_ok"]
        and baseline["final_replay_ok"]
        and baseline["deterministic_replay_ok"]
        and not baseline["oracle_mismatch"]
    )
    attempts: list[dict[str, Any]] = []
    selected: list[str] = []
    if baseline_ok:
        for candidate in _prioritized_candidates(source)[:max_attempts]:
            evaluation = evaluate_mutant(
                candidate["source"],
                input_data=input_data,
                expected=expected,
                case_id=case_id,
                family_id=family_id,
                subfamily_id=subfamily_id,
                timeout_s=timeout_s,
            )
            row = {key: value for key, value in candidate.items() if key != "source"}
            row["source_sha256"] = _sha256_text(candidate["source"])
            row["mutated_source"] = candidate["source"]
            row.update(evaluation)
            row["applicable"] = _is_applicable(row)
            attempts.append(row)
            if row["applicable"]:
                selected.append(row["mutation_id"])
            if len(selected) >= target_applicable:
                break
    return {
        "case_id": case_id,
        "family_id": family_id,
        "subfamily_id": subfamily_id,
        "input_data": input_data,
        "expected": expected,
        "source_sha256": _sha256_text(source),
        "baseline": baseline,
        "baseline_ok": baseline_ok,
        "attempted_count": len(attempts),
        "applicable_count": len(selected),
        "selected_mutation_ids": selected,
        "attempts": attempts,
    }


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    proportion = successes / total
    denominator = 1.0 + z * z / total
    centre = (proportion + z * z / (2.0 * total)) / denominator
    half = (
        z
        * math.sqrt(proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total))
        / denominator
    )
    return (max(0.0, centre - half), min(1.0, centre + half))


def _rate_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    successes = sum(row.get(field) is True for row in rows)
    total = len(rows)
    low, high = wilson_interval(successes, total)
    return {
        "successes": successes,
        "total": total,
        "rate": successes / total if total else None,
        "wilson_ci_95": [low, high],
    }


def build_report(
    cases: list[dict[str, Any]],
    selection_attempts: list[dict[str, Any]],
    screened_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    screened_cases = list(screened_cases if screened_cases is not None else cases)
    applicable = [
        attempt
        for case in cases
        for attempt in case["attempts"]
        if attempt["applicable"]
    ]
    analysis_attempts = [attempt for case in cases for attempt in case["attempts"]]
    all_attempts = [attempt for case in screened_cases for attempt in case["attempts"]]
    internally_consistent = [
        {
            **row,
            "internal_consistency": all(
                row.get(field) is True
                for field in (
                    "same_execution_binding",
                    "prefix_replay_ok",
                    "final_replay_ok",
                    "deterministic_replay_ok",
                )
            ),
        }
        for row in applicable
    ]
    kind_counts: dict[str, int] = {}
    for row in applicable:
        kind = str(row["mutation_kind"])
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    return {
        "kind": "wrong_but_self_consistent_solver_audit",
        "schema_version": "wrong-self-consistent-audit-v1",
        "task_count": len(cases),
        "family_count": len({case["family_id"] for case in cases}),
        "baseline_pass_count": sum(case["baseline_ok"] for case in cases),
        "screened_task_count": len(selection_attempts),
        "mutation_audited_task_count": len(screened_cases),
        "rejected_task_count": sum(
            attempt.get("accepted") is not True for attempt in selection_attempts
        ),
        "mutation_attempt_count": len(all_attempts),
        "analysis_mutation_attempt_count": len(analysis_attempts),
        "applicable_mutant_count": len(applicable),
        "screening_applicable_mutant_count": sum(
            attempt["applicable"] for attempt in all_attempts
        ),
        "not_applicable_count": sum(not attempt["applicable"] for attempt in all_attempts),
        "analysis_not_applicable_count": len(analysis_attempts) - len(applicable),
        "applicable_by_kind": kind_counts,
        "metrics": {
            "internal_consistency": _rate_summary(internally_consistent, "internal_consistency"),
            "oracle_mismatch": _rate_summary(applicable, "oracle_mismatch"),
            "oracle_gate_detection": _rate_summary(applicable, "oracle_gate_detected"),
            "release_rejection": _rate_summary(applicable, "release_rejected"),
        },
        "blocking_defect_count": sum(
            row["oracle_mismatch"]
            and (not row["release_rejected"] or not row["oracle_gate_detected"])
            for row in applicable
        ),
        "selection_attempts": selection_attempts,
        "cases": cases,
        "screened_cases": screened_cases,
    }


def _artifact_path(artifact_dir: Path, row: dict[str, Any]) -> Path:
    return artifact_dir / f"llm_{row['case_id']}_{int(row.get('sample_index') or 0)}.json"


def _load_tracker(artifact_dir: Path, row: dict[str, Any]) -> str:
    artifact = json.loads(_artifact_path(artifact_dir, row).read_text(encoding="utf-8"))
    variants = artifact.get("variants") or []
    if not variants or not str(variants[0].get("tracker_code") or "").strip():
        raise ValueError("artifact has no tracker_code")
    return str(variants[0]["tracker_code"])


def _candidate_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [row for row in report.get("results") or [] if row.get("ok") is True]
    return sorted(rows, key=lambda row: (str(row.get("family_id") or ""), str(row["case_id"])))


def _ordered_for_coverage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first: list[dict[str, Any]] = []
    rest: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        family = str(row.get("family_id") or "")
        if family not in seen:
            first.append(row)
            seen.add(family)
        else:
            rest.append(row)
    return first + rest


def run_audit(
    *,
    report_path: Path,
    artifact_dir: Path,
    target_cases: int,
    target_mutants_per_case: int,
) -> dict[str, Any]:
    source_report = json.loads(report_path.read_text(encoding="utf-8"))
    source_families = {
        str(row.get("family_id") or "") for row in source_report.get("results") or []
    }
    selected: list[dict[str, Any]] = []
    screened_cases: list[dict[str, Any]] = []
    selection_attempts: list[dict[str, Any]] = []
    covered: set[str] = set()
    extra_budget = target_cases - len(source_families)
    if extra_budget < 0:
        raise ValueError(
            f"target_cases={target_cases} cannot cover {len(source_families)} families"
        )
    pending = _ordered_for_coverage(_candidate_rows(source_report))
    for row in pending:
        family = str(row.get("family_id") or "")
        if len(selected) >= target_cases and source_families <= covered:
            break
        if family in covered and len(selected) - len(covered) >= extra_budget:
            continue
        try:
            source = _load_tracker(artifact_dir, row)
            case = audit_case(
                case_id=str(row["case_id"]),
                family_id=family,
                subfamily_id=str(row.get("subfamily_id") or ""),
                source=source,
                input_data=row["input_data"],
                expected=row["expected"],
                target_applicable=target_mutants_per_case,
            )
            accepted = case["baseline_ok"] and case["applicable_count"] == target_mutants_per_case
            reason = "accepted" if accepted else "baseline or applicable-mutant target failed"
        except Exception as exc:
            case = None
            accepted = False
            reason = str(exc)
        selection_attempts.append(
            {"case_id": row["case_id"], "family_id": family, "accepted": accepted, "reason": reason}
        )
        if case is not None:
            case["selected"] = accepted
            screened_cases.append(case)
        if accepted and case is not None:
            selected.append(case)
            covered.add(family)
        print(
            f"AUDIT {row['case_id']} family={family} accepted={accepted} "
            f"selected={len(selected)}/{target_cases} covered={len(covered)}/{len(source_families)}",
            flush=True,
        )
    if len(selected) != target_cases:
        raise RuntimeError(f"selected {len(selected)} cases, expected {target_cases}")
    if not source_families <= covered:
        missing = sorted(source_families - covered)
        raise RuntimeError(f"missing family coverage: {missing}")
    report = build_report(selected, selection_attempts, screened_cases)
    report["provenance"] = {
        "source_report": str(report_path),
        "source_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "artifact_dir": str(artifact_dir),
        "target_cases": target_cases,
        "target_mutants_per_case": target_mutants_per_case,
    }
    return report


def _write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "wrong_self_consistent_solver_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "case_ids": [case["case_id"] for case in report["cases"]],
        "screened_case_ids": [case["case_id"] for case in report["screened_cases"]],
        "family_ids": sorted({case["family_id"] for case in report["cases"]}),
        "source_report_sha256": report["provenance"]["source_report_sha256"],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (output_dir / "attempts.jsonl").open("w", encoding="utf-8") as handle:
        for case in report["screened_cases"]:
            for attempt in case["attempts"]:
                compact = {key: value for key, value in attempt.items() if key != "mutated_source"}
                compact.update(
                    {
                        "case_id": case["case_id"],
                        "family_id": case["family_id"],
                        "selected_case": case.get("selected") is True,
                    }
                )
                handle.write(json.dumps(compact, ensure_ascii=False) + "\n")
    source_dir = output_dir / "mutant_sources"
    source_dir.mkdir(exist_ok=True)
    for case in report["screened_cases"]:
        for attempt in case["attempts"]:
            filename = f"{case['case_id']}__{attempt['mutation_id']}.py".replace("/", "_")
            (source_dir / filename).write_text(attempt["mutated_source"], encoding="utf-8")
    with (output_dir / "applicable_mutants.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case_id",
                "family_id",
                "mutation_id",
                "mutation_kind",
                "same_execution_binding",
                "prefix_replay_ok",
                "final_replay_ok",
                "deterministic_replay_ok",
                "oracle_mismatch",
                "release_rejected",
            ]
        )
        for case in report["cases"]:
            for row in case["attempts"]:
                if row["applicable"]:
                    writer.writerow(
                        [
                            case["case_id"],
                            case["family_id"],
                            row["mutation_id"],
                            row["mutation_kind"],
                            row["same_execution_binding"],
                            row["prefix_replay_ok"],
                            row["final_replay_ok"],
                            row["deterministic_replay_ok"],
                            row["oracle_mismatch"],
                            row["release_rejected"],
                        ]
                    )
    lines = [
        "# Wrong-but-Self-Consistent Solver Audit",
        "",
        f"- Tasks: {report['task_count']}",
        f"- Families: {report['family_count']}",
        f"- Mutation attempts: {report['mutation_attempt_count']}",
        f"- Applicable mutants: {report['applicable_mutant_count']}",
        f"- Not applicable: {report['not_applicable_count']}",
        "",
        "| Metric | Passed | Rate | Wilson 95% CI |",
        "|---|---:|---:|---:|",
    ]
    for name, metric in report["metrics"].items():
        low, high = metric["wilson_ci_95"]
        lines.append(
            f"| {name} | {metric['successes']}/{metric['total']} | {metric['rate']:.4f} | "
            f"[{low:.4f}, {high:.4f}] |"
        )
    lines.extend(["", f"Blocking defects: {report['blocking_defect_count']}"])
    (output_dir / "wrong_self_consistent_solver_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-cases", type=int, default=30)
    parser.add_argument("--mutants-per-case", type=int, default=2)
    args = parser.parse_args()
    report = run_audit(
        report_path=args.source_report,
        artifact_dir=args.artifact_dir,
        target_cases=args.target_cases,
        target_mutants_per_case=args.mutants_per_case,
    )
    _write_outputs(args.output_dir, report)
    print(json.dumps({key: report[key] for key in (
        "task_count",
        "family_count",
        "mutation_attempt_count",
        "applicable_mutant_count",
        "blocking_defect_count",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
