"""Prepare a stratified independent audit package for SemanticTrace keyframes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_trace_correctness_audit import DIMENSIONS
from scripts.prepare_evaluator_calibration import select_stratified_cases


def select_keyframe_indices(frames: list[dict[str, Any]], *, count: int = 3) -> list[int]:
    if not frames or count <= 0:
        return []
    if len(frames) <= count:
        return list(range(len(frames)))
    first, last = 0, len(frames) - 1
    middle_candidates = list(range(1, last))

    def score(index: int) -> tuple[int, int]:
        frame = frames[index]
        evidence = frame.get("evidence") or {}
        semantic = int(bool(frame.get("interaction"))) * 100
        semantic += int(bool(evidence.get("deps"))) * 50
        semantic += int(bool(evidence.get("changes"))) * 25
        distance = -abs(index - len(frames) // 2)
        return semantic, distance

    selected = {first, last}
    for index in sorted(middle_candidates, key=score, reverse=True):
        selected.add(index)
        if len(selected) >= count:
            break
    return sorted(selected)


def prepare_trace_audit(
    *,
    generation_report: Path,
    output_dir: Path,
    count: int = 40,
    seed: int = 20260713,
) -> dict[str, Any]:
    report = json.loads(generation_report.read_text(encoding="utf-8"))
    candidates = [
        {
            "case_id": str(row.get("case_id") or ""),
            "title": row.get("title") or row.get("case_id"),
            "family_id": row.get("family_id") or "unknown",
            "subfamily_id": row.get("subfamily_id") or "",
            "interaction_type": "unknown",
            "status_bits": "1" if row.get("ok") else "0",
            "json": row.get("json"),
            "html": row.get("html"),
            "expected": row.get("expected"),
            "input_data": row.get("input_data"),
        }
        for row in report.get("results") or []
        if row.get("case_id") and row.get("json")
    ]
    selected = select_stratified_cases(candidates, count=count, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    items_dir = output_dir / "items"
    pages_dir = output_dir / "pages"
    items_dir.mkdir(exist_ok=True)
    pages_dir.mkdir(exist_ok=True)
    key_rows: list[dict[str, Any]] = []
    annotation_rows: list[dict[str, Any]] = []

    for row in selected:
        case_id = str(row["case_id"])
        artifact_path = _repo_path(row["json"])
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        variant = next((item for item in artifact.get("variants") or [] if item.get("trace")), None)
        if variant is None:
            raise ValueError(f"{case_id}: no materialized trace")
        trace = variant["trace"]
        scene = (artifact.get("scenes") or {}).get(str(variant.get("id")))
        if scene is None:
            scene = next(iter((artifact.get("scenes") or {}).values()), None)
        if scene is None:
            raise ValueError(f"{case_id}: no scene")
        frames = list(scene.get("frames") or [])
        indices = select_keyframe_indices(frames, count=3)
        audit_id = _audit_id(case_id, seed=seed)
        selected_frames = []
        for index in indices:
            frame = frames[index]
            event = trace.get("events", [])[index] if index < len(trace.get("events") or []) else None
            selected_frames.append({"frame_index": index, "frame": frame, "trace_event": event})
        item_path = items_dir / f"{audit_id}.json"
        item_path.write_text(
            json.dumps(
                {
                    "audit_id": audit_id,
                    "case_id": case_id,
                    "title": row["title"],
                    "family_id": row["family_id"],
                    "input_data": artifact.get("input_data"),
                    "expected_result": artifact.get("expected_result"),
                    "trace_result": trace.get("result"),
                    "algorithm": trace.get("algorithm"),
                    "pseudocode": trace.get("pseudocode"),
                    "keyframes": selected_frames,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        html_source = _repo_path(row.get("html"))
        html_dest = pages_dir / f"{audit_id}.html"
        if html_dest.exists() or html_dest.is_symlink():
            html_dest.unlink()
        if html_source.exists():
            html_dest.symlink_to(html_source.resolve())
        key_rows.append(
            {
                "audit_id": audit_id,
                "case_id": case_id,
                "family_id": row["family_id"],
                "subfamily_id": row["subfamily_id"],
                "item": str(item_path.relative_to(output_dir)),
                "page": str(html_dest.relative_to(output_dir)),
                "keyframe_indices": indices,
                "source_artifact": str(artifact_path),
            }
        )
        annotation_rows.append(
            {
                "audit_id": audit_id,
                "case_id": case_id,
                "family_id": row["family_id"],
                "item": str(item_path.relative_to(output_dir)),
                "page": str(html_dest.relative_to(output_dir)),
                **{dimension: "" for dimension in DIMENSIONS},
                "critical_error_type": "",
                "critical_error_frame": "",
                "notes": "",
            }
        )

    random.Random(seed + 1).shuffle(annotation_rows)
    manifest = {
        "kind": "independent_trace_correctness_audit_package",
        "seed": seed,
        "case_count": len(key_rows),
        "family_count": len({row["family_id"] for row in key_rows}),
        "reviewers_required": 2,
        "status": "pending_human_labels",
        "human_labels_present": False,
    }
    (output_dir / "package_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "private_audit_key.json").write_text(json.dumps({"items": key_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(output_dir / "reviewer_a.csv", annotation_rows)
    _write_csv(output_dir / "reviewer_b.csv", annotation_rows)
    _write_readme(output_dir / "README.md", manifest)
    return manifest


def _audit_id(case_id: str, *, seed: int) -> str:
    return "TRACE-" + hashlib.sha256(f"{seed}:{case_id}".encode()).hexdigest()[:12].upper()


def _repo_path(value: Any) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else ROOT / path


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["audit_id"])
        writer.writeheader()
        writer.writerows(rows)


def _write_readme(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(
        "\n".join(
            [
                "# Independent SemanticTrace Audit",
                "",
                f"- Cases: {manifest['case_count']}",
                f"- Families: {manifest['family_count']}",
                "- Status: pending_human_labels",
                "",
                "两名算法评审者独立检查每题的初始、中间关键和终止帧。",
                "result/state/dependency/explanation 四列填 1 表示正确；critical_error 填 1 表示存在会改变算法事实或教学结论的严重错误。",
                "分歧必须人工裁决；不得使用 LLM 自动补全或替代专家标签。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-report", type=Path, default=ROOT / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260713)
    args = parser.parse_args()
    result = prepare_trace_audit(
        generation_report=args.generation_report,
        output_dir=args.output_dir,
        count=args.count,
        seed=args.seed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
