"""Export a compact AlgoLearnEnv benchmark JSON aligned with plan.md."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "benchmark" / "algo_learn_env_benchmark.json"
DEFAULT_OUTPUT = ROOT / "benchmark" / "algo_learn_env_benchmark_core.json"

PLAN_CORE_FIELDS = [
    "algorithm_id",
    "family",
    "difficulty",
    "learning_objectives",
    "input_generator",
    "reference_solver",
    "trace_oracle",
    "required_views",
    "interaction_tasks",
    "assessment_rubric",
]

CORE_CASE_FIELDS = [
    "id",
    "algorithm_id",
    "title",
    "problem",
    "family",
    "family_id",
    "subfamily_id",
    "difficulty",
    "input_contract",
    "learning_objectives",
    "input_generator",
    "reference_solver",
    "trace_oracle",
    "required_views",
    "interaction_tasks",
    "assessment_rubric",
    "samples",
    "code",
    "tracker_code",
    "verifier_code",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def compact_case(case: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in CORE_CASE_FIELDS if field not in case]
    if missing:
        raise ValueError(f"{case.get('id', '<unknown>')} missing core fields: {', '.join(missing)}")
    return {field: case[field] for field in CORE_CASE_FIELDS}


def validate_core(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return ["cases must be a non-empty list"]
    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"cases[{index}] is not an object")
            continue
        extra = [field for field in case if field not in CORE_CASE_FIELDS]
        missing = [field for field in CORE_CASE_FIELDS if field not in case]
        missing_plan = [field for field in PLAN_CORE_FIELDS if field not in case]
        if extra:
            errors.append(f"{case.get('id', index)} has non-core fields: {', '.join(extra)}")
        if missing:
            errors.append(f"{case.get('id', index)} missing fields: {', '.join(missing)}")
        if missing_plan:
            errors.append(f"{case.get('id', index)} missing plan fields: {', '.join(missing_plan)}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"cases[{index}] has invalid id")
        elif case_id in seen:
            errors.append(f"duplicate id: {case_id}")
        else:
            seen.add(case_id)
        samples = case.get("samples")
        if not isinstance(samples, list) or not samples:
            errors.append(f"{case.get('id', index)} has no samples")
        tasks = case.get("interaction_tasks")
        if not isinstance(tasks, list) or len(tasks) < 3:
            errors.append(f"{case.get('id', index)} has insufficient interaction_tasks")
    summary = data.get("summary") or {}
    if summary.get("case_count") != len(cases):
        errors.append("summary.case_count does not match cases length")
    sample_count = sum(len(case.get("samples") or []) for case in cases if isinstance(case, dict))
    if summary.get("sample_count") != sample_count:
        errors.append("summary.sample_count does not match sample total")
    return errors


def export_core(input_path: Path, output_path: Path) -> dict[str, Any]:
    full = load_json(input_path)
    full_cases = full.get("cases")
    if not isinstance(full_cases, list):
        raise ValueError(f"{input_path} does not contain a cases list")
    cases = [compact_case(case) for case in full_cases]
    summary = dict(full.get("summary") or {})
    summary.update(
        {
            "case_count": len(cases),
            "sample_count": sum(len(case["samples"]) for case in cases),
            "case_field_count": len(CORE_CASE_FIELDS),
            "included_fields": CORE_CASE_FIELDS,
            "plan_core_fields": PLAN_CORE_FIELDS,
            "full_case_field_count": len(full_cases[0]) if full_cases and isinstance(full_cases[0], dict) else None,
            "removed_extension_fields": sorted(
                set(full_cases[0].keys()) - set(CORE_CASE_FIELDS)
                if full_cases and isinstance(full_cases[0], dict)
                else []
            ),
        }
    )
    payload = {
        "schema_version": "algotutorgen-benchmark-core-v1",
        "description": (
            "Compact AlgoLearnEnv benchmark aligned with plan.md core task bundle. "
            "The full internal benchmark with Stage2/teaching extensions remains "
            "benchmark/algo_learn_env_benchmark.json."
        ),
        "source": {
            "full_benchmark": str(input_path),
            "generated_at": now_iso(),
            "generator": "scripts/export_algo_learn_env_core_benchmark.py",
        },
        "summary": summary,
        "cases": cases,
    }
    errors = validate_core(payload)
    if errors:
        raise ValueError("core benchmark validation failed:\n" + "\n".join(errors[:50]))
    write_json(output_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = export_core(args.input, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "cases": payload["summary"]["case_count"],
                "samples": payload["summary"]["sample_count"],
                "case_field_count": payload["summary"]["case_field_count"],
                "removed_extension_fields": len(payload["summary"]["removed_extension_fields"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
