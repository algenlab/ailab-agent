"""Prepare a deterministic, method-blind human calibration package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_evaluator_calibration import METRICS


METHODS = ("stage1", "direct", "webgen", "htmlcure")


def blind_id(case_id: str, method: str, *, seed: int) -> str:
    digest = hashlib.sha256(f"{seed}:{case_id}:{method}".encode()).hexdigest()[:12].upper()
    return f"PAGE-{digest}"


def select_stratified_cases(
    candidates: list[dict[str, Any]],
    *,
    count: int,
    seed: int,
) -> list[dict[str, Any]]:
    if count > len(candidates):
        raise ValueError(f"requested {count} cases from only {len(candidates)} candidates")
    rng = random.Random(seed)
    remaining = list(candidates)
    rng.shuffle(remaining)
    selected: list[dict[str, Any]] = []
    covered_families: set[str] = set()
    covered_interactions: set[str] = set()
    covered_status: set[tuple[int, str]] = set()

    while len(selected) < count:
        def score(row: dict[str, Any]) -> tuple[int, str]:
            family = str(row.get("family_id") or "unknown")
            interaction = str(row.get("interaction_type") or "unknown")
            bits = str(row.get("status_bits") or "")
            value = 1000 * int(family not in covered_families)
            value += 100 * int(interaction not in covered_interactions)
            value += 10 * sum((index, bit) not in covered_status for index, bit in enumerate(bits))
            return value, str(row.get("case_id") or "")

        chosen = max(remaining, key=score)
        remaining.remove(chosen)
        selected.append(chosen)
        covered_families.add(str(chosen.get("family_id") or "unknown"))
        covered_interactions.add(str(chosen.get("interaction_type") or "unknown"))
        covered_status.update(enumerate(str(chosen.get("status_bits") or "")))
    return selected


def prepare_package(
    *,
    stage_direct_report: Path,
    webgen_report: Path,
    htmlcure_report: Path,
    stage_generation_report: Path,
    webgen_workspaces: Path,
    output_dir: Path,
    count: int = 30,
    seed: int = 20260713,
    excluded_cases: set[str] | None = None,
) -> dict[str, Any]:
    stage_direct = json.loads(stage_direct_report.read_text(encoding="utf-8"))
    webgen = json.loads(webgen_report.read_text(encoding="utf-8"))
    htmlcure = json.loads(htmlcure_report.read_text(encoding="utf-8"))
    generation = json.loads(stage_generation_report.read_text(encoding="utf-8"))

    method_rows = {
        "stage1": _index_records(stage_direct.get("records") or [], condition="algolab_full"),
        "direct": _index_records(stage_direct.get("records") or [], condition="direct_html"),
        "webgen": _index_records(webgen.get("results") or []),
        "htmlcure": _index_records(htmlcure.get("records") or []),
    }
    generation_rows = {str(row.get("case_id")): row for row in generation.get("results") or []}
    common = set.intersection(*(set(rows) for rows in method_rows.values()))
    candidates: list[dict[str, Any]] = []
    exclusions = set(excluded_cases or set())
    for case_id in sorted(common - exclusions):
        meta = generation_rows.get(case_id, {})
        stage_row = method_rows["stage1"][case_id]
        candidates.append(
            {
                "case_id": case_id,
                "title": stage_row.get("title") or meta.get("title") or case_id,
                "family": stage_row.get("family") or meta.get("family_id") or "unknown",
                "family_id": meta.get("family_id") or stage_row.get("family") or "unknown",
                "subfamily_id": meta.get("subfamily_id") or "",
                "interaction_type": _interaction_type(meta.get("json")),
                "status_bits": "".join("1" if method_rows[name][case_id].get("machine_ok") else "0" for name in METHODS),
            }
        )
    selected = select_stratified_cases(candidates, count=count, seed=seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    sources_dir = output_dir / "webgen_sources"
    pages_dir.mkdir(exist_ok=True)
    sources_dir.mkdir(exist_ok=True)
    key_rows: list[dict[str, Any]] = []
    annotation_rows: list[dict[str, Any]] = []
    for case in selected:
        case_id = str(case["case_id"])
        for method in METHODS:
            record = method_rows[method][case_id]
            page_id = blind_id(case_id, method, seed=seed)
            page_ref, page_status = _materialize_page(
                method=method,
                case_id=case_id,
                record=record,
                page_id=page_id,
                pages_dir=pages_dir,
                sources_dir=sources_dir,
                webgen_workspaces=webgen_workspaces,
            )
            key_rows.append(
                {
                    "blind_id": page_id,
                    "method": method,
                    "case_id": case_id,
                    "family_id": case["family_id"],
                    "interaction_type": case["interaction_type"],
                    "page_ref": page_ref,
                    "page_status": page_status,
                    **{metric: bool(record.get(metric)) for metric in METRICS},
                    "machine_ok": bool(record.get("machine_ok")),
                    "source_record": record,
                }
            )
            annotation_rows.append(
                {
                    "blind_id": page_id,
                    "case_id": case_id,
                    "title": case["title"],
                    "family": case["family"],
                    "interaction_type": case["interaction_type"],
                    "page_ref": page_ref,
                    **{metric: "" for metric in METRICS},
                    "human_machine_ok": "",
                    "equivalent_ui_not_detected": "",
                    "notes": "",
                }
            )

    rng = random.Random(seed + 1)
    rng.shuffle(annotation_rows)
    package = {
        "kind": "machine_evaluator_human_calibration_package",
        "seed": seed,
        "task_count": len(selected),
        "page_count": len(key_rows),
        "methods": list(METHODS),
        "selected_cases": selected,
        "human_labels_present": False,
        "status": "pending_human_labels",
        "excluded_cases": sorted(exclusions),
    }
    (output_dir / "package_manifest.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "private_blind_key.json").write_text(
        json.dumps({"pages": key_rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(output_dir / "annotator_a.csv", annotation_rows)
    _write_csv(output_dir / "annotator_b.csv", annotation_rows)
    _write_protocol(output_dir / "README.md", package)
    return package


def _index_records(records: list[dict[str, Any]], condition: str | None = None) -> dict[str, dict[str, Any]]:
    return {
        str(row["case_id"]): row
        for row in records
        if row.get("case_id") and (condition is None or row.get("condition") == condition)
    }


def _interaction_type(path_value: Any) -> str:
    if not path_value:
        return "unknown"
    path = Path(str(path_value))
    if not path.is_absolute():
        path = ROOT / path
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    counts: dict[str, int] = {}
    for scene in (artifact.get("scenes") or {}).values():
        for frame in scene.get("frames") or []:
            interaction = frame.get("interaction") or {}
            kind = str(interaction.get("type") or "")
            if kind:
                counts[kind] = counts.get(kind, 0) + 1
    return max(counts, key=counts.get) if counts else "unknown"


def _materialize_page(
    *,
    method: str,
    case_id: str,
    record: dict[str, Any],
    page_id: str,
    pages_dir: Path,
    sources_dir: Path,
    webgen_workspaces: Path,
) -> tuple[str, str]:
    if method != "webgen":
        source = Path(str(record.get("html") or ""))
        if not source.is_absolute():
            source = ROOT / source
        destination = pages_dir / f"{page_id}.html"
        if destination.exists() or destination.is_symlink():
            destination.unlink()
        if source.exists():
            destination.symlink_to(source.resolve())
            return str(destination.relative_to(pages_dir.parent)), "ready"
        return str(destination.relative_to(pages_dir.parent)), "missing_source"

    built_page = pages_dir / page_id / "index.html"
    if built_page.exists():
        return str(built_page.relative_to(pages_dir.parent)), "ready"
    source = webgen_workspaces / case_id
    destination = sources_dir / page_id
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    if source.exists():
        destination.symlink_to(source.resolve(), target_is_directory=True)
        return str(destination.relative_to(pages_dir.parent)), "requires_vite_build"
    return str(destination.relative_to(pages_dir.parent)), "missing_source"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["blind_id"])
        writer.writeheader()
        writer.writerows(rows)


def _write_protocol(path: Path, package: dict[str, Any]) -> None:
    path.write_text(
        "\n".join(
            [
                "# Machine Evaluator Human Calibration",
                "",
                f"- Tasks: {package['task_count']}",
                f"- Pages: {package['page_count']}",
                "- Status: pending_human_labels",
                "",
                "两名标注者分别使用 annotator_a.csv 和 annotator_b.csv，不得打开 private_blind_key.json。",
                "逐页执行九项功能；1 表示页面真实具备该功能，0 表示不具备。等价但 DOM/文案不同的 UI 仍按真实功能标注。",
                "WebGen 页面目录标记 requires_vite_build，须先构建到 pages/ 下再开始标注。",
                "完成后运行 scripts/analyze_evaluator_calibration.py；两人分歧必须由第三方裁决，不能自动填充。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-direct-report", type=Path, default=ROOT / "output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json")
    parser.add_argument("--webgen-report", type=Path, default=ROOT / "output/external_baselines/webgen/audit_all200_sample0/report.json")
    parser.add_argument("--htmlcure-report", type=Path, default=ROOT / "output/external_baselines/htmlcure_all200_sample0/behavior_audit/interaction_semantic_eval_report.json")
    parser.add_argument("--stage-generation-report", type=Path, default=ROOT / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json")
    parser.add_argument("--webgen-workspaces", type=Path, default=ROOT / "output/external_baselines/webgen/workspaces/WebGenAgent_external_baseline_all200_sample0_webgen_DeepSeek-V4-Pro_iter5_all200_sample0_budget5")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--exclude-case", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = prepare_package(
        stage_direct_report=args.stage_direct_report,
        webgen_report=args.webgen_report,
        htmlcure_report=args.htmlcure_report,
        stage_generation_report=args.stage_generation_report,
        webgen_workspaces=args.webgen_workspaces,
        output_dir=args.output_dir,
        count=args.count,
        seed=args.seed,
        excluded_cases=set(args.exclude_case),
    )
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
