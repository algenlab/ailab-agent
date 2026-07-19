"""Run anonymous full-vs-ablation LORI/MERLOT paired reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_json_with_metadata, llm_config
from scripts.run_external_eval_methods import (
    build_external_review_prompt,
    compact_page_evidence,
    normalize_external_review_result,
    summarize_external_reviews,
)


def ablation_blind_map(case_id: str, condition: str, *, order: str = "frozen") -> dict[str, str]:
    digest = hashlib.sha256(f"{case_id}:{condition}".encode("utf-8")).hexdigest()
    if int(digest[:8], 16) % 2 == 0:
        labels = {"A": "full", "B": condition}
    else:
        labels = {"A": condition, "B": "full"}
    if order == "swapped":
        return {"A": labels["B"], "B": labels["A"]}
    if order != "frozen":
        raise ValueError(f"unknown blind order: {order}")
    return labels


def _path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_unique_records(path: Path, *, condition: str) -> dict[str, dict[str, Any]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    records: dict[str, dict[str, Any]] = {}
    for row in report.get("records") or []:
        if str(row.get("condition") or "") != condition:
            continue
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{path}: record missing case_id")
        if case_id in records:
            raise ValueError(f"{path}: duplicate case_id {case_id}")
        records[case_id] = row
    if len(records) != 200:
        raise ValueError(f"{path}: expected 200 records for {condition}, found {len(records)}")
    return records


def review_pair(
    *,
    case_id: str,
    full_record: dict[str, Any],
    ablation_record: dict[str, Any],
    condition: str,
    model: str | None,
    blind_order: str,
) -> dict[str, Any]:
    blind_map = ablation_blind_map(case_id, condition, order=blind_order)
    evidence = {
        "full": compact_page_evidence(full_record),
        condition: compact_page_evidence(ablation_record),
    }
    system, user = build_external_review_prompt(
        case_id=case_id,
        title=str(full_record.get("title") or ablation_record.get("title") or case_id),
        input_data=full_record.get("input_data") or ablation_record.get("input_data"),
        expected=full_record.get("expected") or ablation_record.get("expected"),
        blind_map=blind_map,
        evidence_by_condition=evidence,
    )
    response = chat_json_with_metadata(system, user, model=model, kind="ablation_lori_merlot_review")
    normalized = normalize_external_review_result(response["content"], blind_map=blind_map)
    normalized["case_id"] = case_id
    normalized["model_calls"] = response.get("model_calls") or []
    return normalized


def write_report(
    *,
    output_dir: Path,
    condition: str,
    model: str | None,
    blind_order: str,
    reviews: list[dict[str, Any]],
    full_report: Path,
    ablation_report: Path,
) -> dict[str, Any]:
    summary = summarize_external_reviews(reviews)
    report = {
        "kind": "ablation_pair_review_report",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "condition": condition,
        "model": model,
        "blind_order": blind_order,
        "llm": llm_config(),
        "sources": {"full": str(full_report), condition: str(ablation_report)},
        "pair_count": len(reviews),
        "summary": summary,
        "pair_reviews": reviews,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ablation_pair_review_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        f"# Full vs {condition} Paired Review",
        "",
        f"- pairs: `{len(reviews)}`",
        f"- model: `{model}`",
        f"- blind order: `{blind_order}`",
        f"- winners: `{json.dumps(summary['winner_counts'], ensure_ascii=False)}`",
        "",
        "## Mean Scores",
        "",
        "| Condition | Overall | Content | Goal | Feedback | Interaction | Presentation | Teaching | Ease |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, scores in sorted(summary["score_summary"].items()):
        lines.append(
            f"| {name} | {scores.get('avg_overall')} | {scores.get('avg_content_quality')} | "
            f"{scores.get('avg_learning_goal_alignment')} | {scores.get('avg_feedback_adaptation')} | "
            f"{scores.get('avg_interaction_usability')} | {scores.get('avg_presentation_design')} | "
            f"{scores.get('avg_teaching_effectiveness')} | {scores.get('avg_ease_of_use')} |"
        )
    (output_dir / "ablation_pair_review_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-report", type=Path, required=True)
    parser.add_argument("--ablation-report", type=Path, required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="DeepSeek-V4-Pro")
    parser.add_argument("--blind-order", choices=["frozen", "swapped"], default="frozen")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    full_path = _path(args.full_report)
    ablation_path = _path(args.ablation_report)
    output_dir = _path(args.output_dir)
    full = load_unique_records(full_path, condition="algolab_full")
    ablation = load_unique_records(ablation_path, condition=args.condition)
    if set(full) != set(ablation):
        raise ValueError("full and ablation reports do not contain identical case IDs")

    cache_dir = output_dir / "_cases"
    cache_dir.mkdir(parents=True, exist_ok=True)

    def run_or_load(case_id: str) -> dict[str, Any]:
        cache_path = cache_dir / f"{case_id}.json"
        if cache_path.exists() and not args.force:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"ABLATION_REVIEW_START condition={args.condition} case={case_id}", flush=True)
        review = review_pair(
            case_id=case_id,
            full_record=full[case_id],
            ablation_record=ablation[case_id],
            condition=args.condition,
            model=args.model,
            blind_order=args.blind_order,
        )
        cache_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"ABLATION_REVIEW_DONE condition={args.condition} case={case_id} winner={review.get('winner')}",
            flush=True,
        )
        return review

    reviews: list[dict[str, Any]] = []
    case_ids = sorted(full)
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {executor.submit(run_or_load, case_id): case_id for case_id in case_ids}
        for future in as_completed(futures):
            reviews.append(future.result())
    reviews.sort(key=lambda row: str(row.get("case_id") or ""))
    if len(reviews) != 200 or len({row["case_id"] for row in reviews}) != 200:
        raise ValueError("ablation review did not produce 200 unique pairs")
    report = write_report(
        output_dir=output_dir,
        condition=args.condition,
        model=args.model,
        blind_order=args.blind_order,
        reviews=reviews,
        full_report=full_path,
        ablation_report=ablation_path,
    )
    print(json.dumps({"condition": args.condition, "pairs": len(reviews), "summary": report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
