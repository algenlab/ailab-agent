"""Prepare and analyze expert/student human-study materials without fabricating labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CALIBRATION_KEY = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/evaluator_calibration_final/private_blind_key.json"
DEFAULT_CALIBRATION_ROOT = DEFAULT_CALIBRATION_KEY.parent
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/human_study_protocols"
EXPERT_METRICS = ("process_correctness", "teaching_clarity", "interaction_quality", "visual_clarity")


def _float(value: Any) -> float | None:
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 4) if values else None


def _boolean(value: Any) -> bool | None:
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot compute a quantile from no values")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _bootstrap_mean_ci(values: list[float], *, seed: int, draws: int) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    means = [statistics.mean(rng.choices(values, k=len(values))) for _ in range(draws)]
    return [round(_quantile(means, 0.025), 4), round(_quantile(means, 0.975), 4)]


def _bootstrap_paired_difference_ci(
    left: list[float],
    right: list[float],
    *,
    seed: int,
    draws: int,
) -> list[float] | None:
    if len(left) != len(right):
        raise ValueError("paired vectors must have equal length")
    if not left:
        return None
    differences = [a - b for a, b in zip(left, right)]
    rng = random.Random(seed)
    means = [statistics.mean(rng.choices(differences, k=len(differences))) for _ in range(draws)]
    return [round(_quantile(means, 0.025), 4), round(_quantile(means, 0.975), 4)]


def _holm_adjust(tests: dict[str, dict[str, Any] | None]) -> None:
    ordered = sorted(
        ((name, float(result["p_value"])) for name, result in tests.items() if result is not None),
        key=lambda item: item[1],
    )
    running = 0.0
    total = len(ordered)
    for index, (name, p_value) in enumerate(ordered):
        running = max(running, min(1.0, p_value * (total - index)))
        assert tests[name] is not None
        tests[name]["holm_adjusted_p"] = running


def _wilcoxon(left: list[float], right: list[float]) -> dict[str, Any] | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    differences = [a - b for a, b in zip(left, right)]
    nonzero = [value for value in differences if value != 0]
    if not nonzero:
        return {
            "n": len(left),
            "nonzero_pairs": 0,
            "statistic": 0.0,
            "p_value": 1.0,
            "positive_rank_sum": 0.0,
            "negative_rank_sum": 0.0,
            "rank_biserial": 0.0,
        }
    from scipy.stats import rankdata, wilcoxon
    result = wilcoxon(differences, zero_method="wilcox", alternative="two-sided")
    ranks = rankdata([abs(value) for value in nonzero], method="average")
    positive = float(sum(rank for rank, value in zip(ranks, nonzero) if value > 0))
    negative = float(sum(rank for rank, value in zip(ranks, nonzero) if value < 0))
    denominator = positive + negative
    return {
        "n": len(left),
        "nonzero_pairs": len(nonzero),
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "positive_rank_sum": positive,
        "negative_rank_sum": negative,
        "rank_biserial": (positive - negative) / denominator if denominator else 0.0,
    }


def _complete_expert_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if all(_float(row.get(f"{metric}_a")) is not None and _float(row.get(f"{metric}_b")) is not None for metric in EXPERT_METRICS)
        and {str(row.get("method_a") or ""), str(row.get("method_b") or "")} == {"algotutorgen", "direct"}
    ]


def _expert_scores(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[float]]]:
    scores: dict[str, dict[str, list[float]]] = {
        method: {metric: [] for metric in EXPERT_METRICS} for method in ("algotutorgen", "direct")
    }
    for row in rows:
        for side in ("a", "b"):
            method = str(row[f"method_{side}"])
            for metric in EXPERT_METRICS:
                value = _float(row[f"{metric}_{side}"])
                assert value is not None
                scores[method][metric].append(value)
    return scores


def _expert_sensitivity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = _expert_scores(rows)
    tests = {
        metric: _wilcoxon(scores["algotutorgen"][metric], scores["direct"][metric])
        for metric in EXPERT_METRICS
    }
    _holm_adjust(tests)
    return {
        "complete_pairs": len(rows),
        "by_method": {
            method: {metric: _mean(values) for metric, values in metrics.items()}
            for method, metrics in scores.items()
        },
        "paired_wilcoxon": tests,
    }


def analyze_expert_rows(
    rows: list[dict[str, Any]],
    *,
    seed: int = 20260713,
    bootstrap_draws: int = 10000,
) -> dict[str, Any]:
    complete = _complete_expert_rows(rows)
    if not complete:
        return {"status": "pending_human_data", "complete_pairs": 0, "required": "3 experts x 30 pairs"}
    scores = _expert_scores(complete)
    preferences: Counter[str] = Counter()
    for row in complete:
        preferred = str(row.get("preference") or "tie").strip().lower()
        if preferred == "a":
            preferred = str(row["method_a"])
        elif preferred == "b":
            preferred = str(row["method_b"])
        preferences[preferred if preferred in {"algotutorgen", "direct"} else "tie"] += 1
    by_method = {}
    for method, metrics in scores.items():
        by_method[method] = {}
        for metric_index, (metric, values) in enumerate(metrics.items()):
            by_method[method][metric] = {
                "mean": _mean(values),
                "bootstrap_ci_95": _bootstrap_mean_ci(
                    values,
                    seed=seed + metric_index + (100 if method == "direct" else 0),
                    draws=bootstrap_draws,
                ),
            }
    tests = {
        metric: _wilcoxon(scores["algotutorgen"][metric], scores["direct"][metric])
        for metric in EXPERT_METRICS
    }
    _holm_adjust(tests)
    paired_difference_ci = {
        metric: _bootstrap_paired_difference_ci(
            scores["algotutorgen"][metric],
            scores["direct"][metric],
            seed=seed + 1000 + metric_index,
            draws=bootstrap_draws,
        )
        for metric_index, metric in enumerate(EXPERT_METRICS)
    }
    by_expert = {
        expert_id: _expert_sensitivity([row for row in complete if str(row.get("expert_id") or "") == expert_id])
        for expert_id in sorted({str(row.get("expert_id") or "") for row in complete} - {""})
    }
    by_family = {
        family_id: _expert_sensitivity([row for row in complete if str(row.get("family_id") or "") == family_id])
        for family_id in sorted({str(row.get("family_id") or "") for row in complete} - {""})
    }
    return {
        "status": "complete",
        "complete_pairs": len(complete),
        "experts": len(by_expert),
        "by_method": by_method,
        "paired_difference_ci_95": paired_difference_ci,
        "preference_counts": dict(preferences),
        "paired_wilcoxon": tests,
        "by_expert": by_expert,
        "by_family": by_family,
    }


def score_sus(row: dict[str, Any]) -> float | None:
    provided = _float(row.get("sus_score"))
    if provided is not None and not 0.0 <= provided <= 100.0:
        raise ValueError(f"SUS score must be between 0 and 100, got {provided}")
    responses = [_float(row.get(f"sus_{item}")) for item in range(1, 11)]
    if any(value is None for value in responses):
        return round(provided, 4) if provided is not None else None
    numeric = [float(value) for value in responses if value is not None]
    if any(value < 1.0 or value > 5.0 for value in numeric):
        raise ValueError("SUS item responses must be between 1 and 5")
    calculated = sum(
        value - 1.0 if item % 2 else 5.0 - value
        for item, value in enumerate(numeric, 1)
    ) * 2.5
    if provided is not None and abs(provided - calculated) > 0.01:
        raise ValueError(f"provided SUS score {provided} does not match item score {calculated}")
    return round(provided if provided is not None else calculated, 4)


def _questionnaire_records(
    rows: list[dict[str, Any]],
    condition_codes: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        participant = str(row.get("participant_id") or "").strip()
        code = str(row.get("condition_code") or "").strip().upper()
        condition = str((condition_codes.get(participant) or {}).get(code) or "").lower()
        if not participant or condition not in {"algotutorgen", "direct"}:
            continue
        sus_score = score_sus(row)
        cognitive_load = _float(row.get("cognitive_load"))
        preference = str(row.get("preference") or "").strip()
        records.append({
            **row,
            "participant_id": participant,
            "condition": condition,
            "sus_score_value": sus_score,
            "cognitive_load_value": cognitive_load,
            "preference_value": preference,
        })
    return records


def _paired_participant_values(
    grouped: dict[str, dict[str, list[dict[str, Any]]]],
    value_key: str,
) -> tuple[list[float], list[float]]:
    left: list[float] = []
    right: list[float] = []
    for groups in grouped.values():
        left_values = [_float(row.get(value_key)) for row in groups.get("algotutorgen", [])]
        right_values = [_float(row.get(value_key)) for row in groups.get("direct", [])]
        left_complete = [float(value) for value in left_values if value is not None]
        right_complete = [float(value) for value in right_values if value is not None]
        if left_complete and right_complete:
            left.append(statistics.mean(left_complete))
            right.append(statistics.mean(right_complete))
    return left, right


def analyze_student_rows(
    rows: list[dict[str, Any]],
    *,
    questionnaire_rows: list[dict[str, Any]] | None = None,
    condition_codes: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    complete = []
    for row in rows:
        condition = str(row.get("condition") or "").strip().lower()
        correct = _float(row.get("correct"))
        time_s = _float(row.get("completion_time_s"))
        if condition in {"algotutorgen", "direct"} and correct is not None and time_s is not None:
            complete.append({**row, "condition": condition, "correct_value": correct, "time_value": time_s})
    if not complete:
        return {"status": "pending_human_data", "complete_trials": 0, "required": "20-30 students with both conditions"}
    questionnaires = _questionnaire_records(questionnaire_rows or [], condition_codes or {})
    by_condition: dict[str, Any] = {}
    for condition in ("algotutorgen", "direct"):
        group = [row for row in complete if row["condition"] == condition]
        questionnaire_group = [row for row in questionnaires if row["condition"] == condition]
        hint_values = [value for row in group if (value := _boolean(row.get("hint_used"))) is not None]
        answer_values = [value for row in group if (value := _boolean(row.get("show_answer_used"))) is not None]
        trial_cognitive_load = [value for row in group if (value := _float(row.get("cognitive_load"))) is not None]
        by_condition[condition] = {
            "trials": len(group),
            "accuracy": _mean([row["correct_value"] for row in group]),
            "mean_completion_time_s": _mean([row["time_value"] for row in group]),
            "mean_cognitive_load": _mean(trial_cognitive_load),
            "mean_trial_cognitive_load": _mean(trial_cognitive_load),
            "mean_questionnaire_cognitive_load": _mean([
                float(row["cognitive_load_value"])
                for row in questionnaire_group
                if row["cognitive_load_value"] is not None
            ]),
            "mean_sus_score": _mean([
                float(row["sus_score_value"])
                for row in questionnaire_group
                if row["sus_score_value"] is not None
            ]),
            "hint_use_rate": _mean([float(value) for value in hint_values]),
            "show_answer_use_rate": _mean([float(value) for value in answer_values]),
        }
    participant_conditions: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in complete:
        participant_conditions[str(row.get("participant_id"))][row["condition"]].append(row)
    paired = {
        participant: groups
        for participant, groups in participant_conditions.items()
        if groups.get("algotutorgen") and groups.get("direct")
    }
    paired_tests: dict[str, dict[str, Any] | None] = {}
    for key, value_key in (
        ("accuracy", "correct_value"),
        ("completion_time_s", "time_value"),
        ("trial_cognitive_load", "cognitive_load"),
    ):
        left, right = _paired_participant_values(paired, value_key)
        paired_tests[key] = _wilcoxon(left, right)
    questionnaire_by_participant: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in questionnaires:
        questionnaire_by_participant[row["participant_id"]][row["condition"]].append(row)
    for key, value_key in (
        ("sus_score", "sus_score_value"),
        ("questionnaire_cognitive_load", "cognitive_load_value"),
    ):
        left, right = _paired_participant_values(questionnaire_by_participant, value_key)
        paired_tests[key] = _wilcoxon(left, right)
    _holm_adjust(paired_tests)
    preferences: Counter[str] = Counter()
    for row in questionnaires:
        preferred = str(row.get("preference_value") or "").strip()
        if not preferred:
            continue
        code_mapping = condition_codes.get(row["participant_id"], {}) if condition_codes else {}
        normalized = str(code_mapping.get(preferred.upper()) or preferred).strip().lower()
        preferences[normalized if normalized in {"algotutorgen", "direct", "tie"} else "other"] += 1
    return {
        "status": "complete" if paired else "pending_human_data",
        "complete_trials": len(complete),
        "participants": len(participant_conditions),
        "participants_with_both_conditions": len(paired),
        "by_condition": by_condition,
        "paired_wilcoxon": paired_tests,
        "complete_questionnaires": sum(row["sus_score_value"] is not None for row in questionnaires),
        "preference_counts": dict(preferences),
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _opaque(prefix: str, value: str, seed: int) -> str:
    digest = hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()[:12].upper()
    return f"{prefix}-{digest}"


def prepare_protocol_package(*, calibration_key: Path, calibration_root: Path, output_dir: Path, seed: int = 20260713) -> dict[str, Any]:
    key = json.loads(calibration_key.read_text(encoding="utf-8"))
    pages = [row for row in key.get("pages") or [] if row.get("method") in {"stage1", "direct"}]
    by_case: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in pages:
        by_case[str(row["case_id"])][str(row["method"])] = row
    case_ids = sorted(case_id for case_id, methods in by_case.items() if set(methods) == {"stage1", "direct"})[:30]
    if len(case_ids) != 30:
        raise ValueError(f"expected 30 paired calibration cases, found {len(case_ids)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    page_dir = output_dir / "pages"
    page_dir.mkdir(exist_ok=True)
    page_refs: dict[tuple[str, str], str] = {}
    for case_id in case_ids:
        for method in ("stage1", "direct"):
            source = calibration_root / str(by_case[case_id][method]["page_ref"])
            page_id = _opaque("HUMANPAGE", f"{case_id}:{method}", seed)
            target = page_dir / f"{page_id}.html"
            shutil.copy2(source, target)
            page_refs[(case_id, method)] = str(target.relative_to(output_dir))

    rng = random.Random(seed)
    expert_assignments = []
    expert_key = []
    expert_ratings = []
    for expert_index in range(1, 4):
        ordered_cases = case_ids[:]
        rng.shuffle(ordered_cases)
        for trial, case_id in enumerate(ordered_cases, 1):
            methods = ["stage1", "direct"]
            if int(hashlib.sha256(f"{seed}:{expert_index}:{case_id}".encode()).hexdigest(), 16) % 2:
                methods.reverse()
            pair_id = _opaque("EXPERTPAIR", f"{expert_index}:{case_id}", seed)
            expert_assignments.append({"expert_id": f"E{expert_index}", "trial": trial, "pair_id": pair_id, "case_id": case_id, "page_a": page_refs[(case_id, methods[0])], "page_b": page_refs[(case_id, methods[1])]})
            family_id = str(by_case[case_id]["stage1"].get("family_id") or by_case[case_id]["direct"].get("family_id") or "")
            expert_key.append({"expert_id": f"E{expert_index}", "pair_id": pair_id, "case_id": case_id, "family_id": family_id, "method_a": "algotutorgen" if methods[0] == "stage1" else "direct", "method_b": "algotutorgen" if methods[1] == "stage1" else "direct"})
            expert_ratings.append({"expert_id": f"E{expert_index}", "pair_id": pair_id, **{f"{metric}_{side}": "" for metric in EXPERT_METRICS for side in ("a", "b")}, "preference": "", "confidence_1_5": "", "critical_error_a": "", "critical_error_b": "", "notes": ""})
    _write_csv(output_dir / "expert_assignments.csv", list(expert_assignments[0]), expert_assignments)
    _write_csv(output_dir / "expert_ratings.csv", list(expert_ratings[0]), expert_ratings)
    (output_dir / "expert_private_key.json").write_text(json.dumps({"rows": expert_key}, ensure_ascii=False, indent=2), encoding="utf-8")

    student_cases = case_ids[:12]
    student_assignments = []
    student_key = []
    student_observations = []
    condition_codes: dict[str, dict[str, str]] = {}
    for participant_index in range(1, 25):
        participant = f"S{participant_index:02d}"
        ordered_cases = student_cases[participant_index % len(student_cases):] + student_cases[:participant_index % len(student_cases)]
        first_method = "stage1" if participant_index % 2 else "direct"
        second_method = "direct" if first_method == "stage1" else "stage1"
        condition_codes[participant] = {
            "X": "algotutorgen" if first_method == "stage1" else "direct",
            "Y": "algotutorgen" if second_method == "stage1" else "direct",
        }
        for trial, case_id in enumerate(ordered_cases, 1):
            condition_code = "X" if trial <= 6 else "Y"
            method = first_method if condition_code == "X" else second_method
            trial_id = _opaque("STUDENTTRIAL", f"{participant}:{case_id}:{method}", seed)
            student_assignments.append({"participant_id": participant, "trial": trial, "trial_id": trial_id, "task_id": case_id, "page": page_refs[(case_id, method)]})
            student_key.append({"participant_id": participant, "trial": trial, "trial_id": trial_id, "condition_code": condition_code, "condition": "algotutorgen" if method == "stage1" else "direct"})
            student_observations.append({"participant_id": participant, "trial_id": trial_id, "correct": "", "completion_time_s": "", "cognitive_load": "", "hint_used": "", "show_answer_used": "", "notes": ""})
    _write_csv(output_dir / "student_assignments.csv", list(student_assignments[0]), student_assignments)
    _write_csv(output_dir / "student_observations.csv", list(student_observations[0]), student_observations)
    questionnaire_rows = [
        {"participant_id": f"S{index:02d}", "condition_code": code, **{f"sus_{item}": "" for item in range(1, 11)}, "sus_score": "", "cognitive_load": "", "preference": "", "notes": ""}
        for index in range(1, 25)
        for code in ("X", "Y")
    ]
    _write_csv(output_dir / "student_questionnaires.csv", list(questionnaire_rows[0]), questionnaire_rows)
    (output_dir / "student_private_key.json").write_text(json.dumps({"trials": student_key, "condition_codes": condition_codes}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "kind": "human_study_protocol_package",
        "status": "pending_human_data",
        "expert_pairs": len(expert_assignments),
        "experts_planned": 3,
        "student_trials": len(student_assignments),
        "students_planned": 24,
        "expert_tasks": 30,
        "student_tasks_per_participant": 12,
        "seed": seed,
        "private_files": ["expert_private_key.json", "student_private_key.json"],
    }
    (output_dir / "package_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--calibration-key", type=Path, default=DEFAULT_CALIBRATION_KEY)
    parser.add_argument("--calibration-root", type=Path, default=DEFAULT_CALIBRATION_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expert-ratings", type=Path)
    parser.add_argument("--expert-key", type=Path)
    parser.add_argument("--student-observations", type=Path)
    parser.add_argument("--student-questionnaires", type=Path)
    parser.add_argument("--student-key", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    if args.prepare:
        manifest = prepare_protocol_package(
            calibration_key=args.calibration_key if args.calibration_key.is_absolute() else ROOT / args.calibration_key,
            calibration_root=args.calibration_root if args.calibration_root.is_absolute() else ROOT / args.calibration_root,
            output_dir=output_dir,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    expert_path = args.expert_ratings or output_dir / "expert_ratings.csv"
    expert_rows = _read_csv(expert_path if expert_path.is_absolute() else ROOT / expert_path)
    expert_key_path = args.expert_key or output_dir / "expert_private_key.json"
    expert_key_path = expert_key_path if expert_key_path.is_absolute() else ROOT / expert_key_path
    if expert_key_path.exists():
        key_data = json.loads(expert_key_path.read_text(encoding="utf-8"))
        mapping = {row["pair_id"]: row for row in key_data.get("rows") or []}
        expert_rows = [{**row, **mapping.get(row.get("pair_id"), {})} for row in expert_rows]
    student_path = args.student_observations or output_dir / "student_observations.csv"
    student_rows = _read_csv(student_path if student_path.is_absolute() else ROOT / student_path)
    condition_codes: dict[str, dict[str, str]] = {}
    student_key_path = args.student_key or output_dir / "student_private_key.json"
    student_key_path = student_key_path if student_key_path.is_absolute() else ROOT / student_key_path
    if student_key_path.exists():
        key_data = json.loads(student_key_path.read_text(encoding="utf-8"))
        mapping = {row["trial_id"]: row for row in key_data.get("trials") or []}
        student_rows = [{**row, **mapping.get(row.get("trial_id"), {})} for row in student_rows]
        condition_codes = key_data.get("condition_codes") or {}
    questionnaire_path = args.student_questionnaires or output_dir / "student_questionnaires.csv"
    questionnaire_rows = _read_csv(questionnaire_path if questionnaire_path.is_absolute() else ROOT / questionnaire_path)
    result = {
        "expert": analyze_expert_rows(expert_rows),
        "student": analyze_student_rows(
            student_rows,
            questionnaire_rows=questionnaire_rows,
            condition_codes=condition_codes,
        ),
    }
    (output_dir / "human_study_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
