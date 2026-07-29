"""Translate the fixed 23 gallery cases while preserving inputs and answers."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_json  # noqa: E402
from scripts.build_method_artifact_gallery import selected_case_ids  # noqa: E402


SOURCE = ROOT / "benchmark/algo_learn_env_benchmark.json"
TARGET = ROOT / "benchmark/english_method_samples.json"
CJK_RE = re.compile(r"[\u3400-\u9fff]")

TRANSLATED_FIELDS = (
    "title",
    "family",
    "problem",
    "strategy",
    "input_contract",
    "variant_name",
    "time_complexity",
    "space_complexity",
    "learning_objectives",
    "interaction_tasks",
)

SYSTEM_PROMPT = """You translate algorithm benchmark metadata into natural academic English.
Return one JSON object only. Preserve identifiers, variable names, JSON paths, formulas, numbers, code fragments,
oracle semantics, and list/object structure exactly. Translate every human-readable string into English. Do not emit
Chinese or any CJK character. Do not add or remove tasks and do not change algorithm meaning."""


def _translation_payload(case: dict[str, Any]) -> dict[str, Any]:
    return {field: case.get(field) for field in TRANSLATED_FIELDS}


def _translate_case(case: dict[str, Any]) -> dict[str, Any]:
    user = json.dumps(
        {
            "case_id": case["id"],
            "instruction": "Translate all human-readable strings. Keep JSON structure and technical tokens stable.",
            "source": _translation_payload(case),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    response = chat_json(SYSTEM_PROMPT, user, kind="english_case_translation")
    translated = response.get("source") if isinstance(response.get("source"), dict) else response
    if set(translated) != set(TRANSLATED_FIELDS):
        missing = sorted(set(TRANSLATED_FIELDS) - set(translated))
        extra = sorted(set(translated) - set(TRANSLATED_FIELDS))
        raise ValueError(f"{case['id']}: translation fields mismatch missing={missing} extra={extra}")
    serialized = json.dumps(translated, ensure_ascii=False)
    if CJK_RE.search(serialized):
        raise ValueError(f"{case['id']}: translated metadata still contains CJK")
    return translated


def _public_case(case: dict[str, Any], translated: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "algorithm_id": case.get("algorithm_id", case["id"]),
        "title": translated["title"],
        "family": translated["family"],
        "family_id": case["family_id"],
        "subfamily_id": case["subfamily_id"],
        "gate_layer": case["gate_layer"],
        "support_level": case["support_level"],
        "process_profile": case["process_profile"],
        "difficulty": case.get("difficulty", "medium"),
        "problem": translated["problem"],
        "strategy": translated["strategy"],
        "input_contract": translated["input_contract"],
        "variant_name": translated["variant_name"],
        "time_complexity": translated["time_complexity"],
        "space_complexity": translated["space_complexity"],
        "learning_objectives": translated["learning_objectives"],
        "required_views": list(case.get("required_views") or []),
        "interaction_tasks": translated["interaction_tasks"],
        "samples": case["samples"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / "output/experiments/english_method_samples_20260719/case_translation_cache",
    )
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in source["cases"]}
    ids = selected_case_ids()
    cases = [by_id[case_id] for case_id in ids]
    translated_by_id: dict[str, dict[str, Any]] = {}
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    pending: list[dict[str, Any]] = []
    for case in cases:
        cache_path = args.cache_dir / f"{case['id']}.json"
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if set(cached) == set(TRANSLATED_FIELDS) and CJK_RE.search(json.dumps(cached, ensure_ascii=False)) is None:
                translated_by_id[case["id"]] = cached
                print(f"CACHED {case['id']}", flush=True)
                continue
        pending.append(case)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {executor.submit(_translate_case, case): case["id"] for case in pending}
        for future in concurrent.futures.as_completed(futures):
            case_id = futures[future]
            translated_by_id[case_id] = future.result()
            (args.cache_dir / f"{case_id}.json").write_text(
                json.dumps(translated_by_id[case_id], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"TRANSLATED {case_id}", flush=True)

    payload = {
        "schema_version": "english-method-samples-v1",
        "language": "en",
        "selection_rule": "The same fixed 23 family-representative cases used by the five-method artifact gallery.",
        "cases": [_public_case(case, translated_by_id[case["id"]]) for case in cases],
    }
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if CJK_RE.search(serialized):
        raise ValueError("final English case subset contains CJK")
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(serialized, encoding="utf-8")
    print(f"Wrote {len(cases)} English cases to {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
