"""Prepare and analyze Plan-2 five-method visual human calibration."""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import html
import json
import math
import random
import secrets
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

METHODS = (
    "algotutorgen_stage2",
    "direct_html",
    "webgen_agent",
    "htmlcure_strict",
    "browser_repair_1call",
)
VISUAL_METRICS = (
    "problem_visual_alignment",
    "algorithm_state_readability",
    "process_transition_clarity",
    "instructional_visual_design",
)
DEFAULT_PREPARED_RECORDS = (
    ROOT / "output/experiments/all_method_auxiliary_eval_20260718/prepared_records.json"
)
DEFAULT_REVIEW_ROOT = ROOT / "output/experiments/all_method_auxiliary_eval_20260718/review_cases"
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/plan2_20260722/p1_visual_human_calibration"


def blind_page_id(case_id: str, method: str, *, secret: bytes | str) -> str:
    secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not secret_bytes:
        raise ValueError("blind ID secret must not be empty")
    digest = hmac.new(
        secret_bytes,
        f"{case_id}\0{method}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:14].upper()
    return f"VIS-{digest}"


def default_private_key_path(output_dir: Path) -> Path:
    return output_dir.parent / "private_keys" / f"{output_dir.name}_blind_key.json"


def select_stratified_cases(
    candidates: list[dict[str, Any]],
    *,
    count: int,
    seed: int,
) -> list[dict[str, Any]]:
    if count > len(candidates):
        raise ValueError(f"requested {count} cases from only {len(candidates)} candidates")
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_family[str(row.get("family") or "unknown")].append(row)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for family in sorted(by_family, key=lambda value: _seeded_order(seed, value))[:count]:
        chosen = min(
            by_family[family],
            key=lambda row: _seeded_order(seed, str(row.get("case_id") or "")),
        )
        selected.append(chosen)
        selected_ids.add(str(chosen.get("case_id") or ""))
    remaining = [
        row for row in candidates if str(row.get("case_id") or "") not in selected_ids
    ]
    remaining.sort(key=lambda row: _seeded_order(seed, str(row.get("case_id") or "")))
    selected.extend(remaining[: max(0, count - len(selected))])
    return sorted(selected, key=lambda row: str(row.get("case_id") or ""))


def calibration_status(
    reviewer_a: list[dict[str, Any]],
    reviewer_b: list[dict[str, Any]],
    *,
    expected_ids: set[str],
) -> str:
    rows_a = _rating_map(reviewer_a)
    rows_b = _rating_map(reviewer_b)
    for blind_id in expected_ids:
        for rows in (rows_a, rows_b):
            row = rows.get(blind_id)
            if row is None or any(_score(row.get(metric), allow_blank=True) is None for metric in VISUAL_METRICS):
                return "pending_human_labels"
    return "complete"


def analyze_ratings(
    key_rows: list[dict[str, Any]],
    reviewer_a: list[dict[str, Any]],
    reviewer_b: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_ids = {str(row.get("blind_id") or "") for row in key_rows}
    status = calibration_status(reviewer_a, reviewer_b, expected_ids=expected_ids)
    rows_a = _rating_map(reviewer_a)
    rows_b = _rating_map(reviewer_b)
    if status != "complete":
        complete_a = sum(_row_complete(rows_a.get(blind_id)) for blind_id in expected_ids)
        complete_b = sum(_row_complete(rows_b.get(blind_id)) for blind_id in expected_ids)
        return {
            "kind": "plan2_visual_human_calibration_analysis",
            "status": status,
            "expected_pages": len(expected_ids),
            "complete_pages": {"reviewer_a": complete_a, "reviewer_b": complete_b},
            "required": "two complete 1-5 rating sheets; no model-generated human labels",
        }

    key = {str(row["blind_id"]): row for row in key_rows}
    merged: list[dict[str, Any]] = []
    for blind_id in sorted(expected_ids):
        item = key[blind_id]
        scores_a = {metric: int(_score(rows_a[blind_id][metric])) for metric in VISUAL_METRICS}
        scores_b = {metric: int(_score(rows_b[blind_id][metric])) for metric in VISUAL_METRICS}
        human = {
            metric: (scores_a[metric] + scores_b[metric]) / 2.0 for metric in VISUAL_METRICS
        }
        vlm = {
            metric: float((item.get("vlm_scores") or {}).get(metric) or 0)
            for metric in VISUAL_METRICS
        }
        merged.append(
            {
                **item,
                "reviewer_a": scores_a,
                "reviewer_b": scores_b,
                "human": human,
                "human_overall": statistics.mean(human.values()),
                "vlm": vlm,
                "vlm_overall": statistics.mean(vlm.values()),
            }
        )

    human_vlm = {}
    for metric in (*VISUAL_METRICS, "overall"):
        human_values = [
            row["human_overall"] if metric == "overall" else row["human"][metric]
            for row in merged
        ]
        vlm_values = [
            row["vlm_overall"] if metric == "overall" else row["vlm"][metric]
            for row in merged
        ]
        human_vlm[metric] = _spearman(human_values, vlm_values)

    threshold_rows = []
    confusion = Counter()
    for row in merged:
        human_pass = all(row["human"][metric] >= 3 for metric in VISUAL_METRICS)
        vlm_pass = all(row["vlm"][metric] >= 3 for metric in VISUAL_METRICS)
        confusion[(human_pass, vlm_pass)] += 1
        threshold_rows.append(human_pass == vlm_pass)

    by_case_method = {
        (str(row["case_id"]), str(row["method"])): row for row in merged
    }
    paired_preference = {}
    case_ids = sorted({str(row["case_id"]) for row in merged})
    for baseline in METHODS[1:]:
        counts = Counter()
        differences = []
        for case_id in case_ids:
            pvcr = by_case_method.get((case_id, "algotutorgen_stage2"))
            other = by_case_method.get((case_id, baseline))
            if pvcr is None or other is None:
                continue
            difference = float(pvcr["human_overall"] - other["human_overall"])
            differences.append(difference)
            counts["pvcr_preferred" if difference > 0 else "baseline_preferred" if difference < 0 else "tie"] += 1
        paired_preference[baseline] = {
            "paired_cases": len(differences),
            "pvcr_preferred": counts["pvcr_preferred"],
            "baseline_preferred": counts["baseline_preferred"],
            "tie": counts["tie"],
            "mean_pvcr_minus_baseline": round(statistics.mean(differences), 4)
            if differences
            else None,
        }

    inter_rater = {}
    for metric in VISUAL_METRICS:
        values_a = [int(row["reviewer_a"][metric]) for row in merged]
        values_b = [int(row["reviewer_b"][metric]) for row in merged]
        inter_rater[metric] = {
            "n": len(values_a),
            "exact_agreement": _ratio(sum(a == b for a, b in zip(values_a, values_b)), len(values_a)),
            "within_one_agreement": _ratio(
                sum(abs(a - b) <= 1 for a, b in zip(values_a, values_b)), len(values_a)
            ),
            "quadratic_weighted_kappa": _quadratic_weighted_kappa(values_a, values_b),
            "spearman": _spearman(values_a, values_b),
        }
    return {
        "kind": "plan2_visual_human_calibration_analysis",
        "status": "complete",
        "page_count": len(merged),
        "case_count": len(case_ids),
        "method_count": len({str(row["method"]) for row in merged}),
        "human_vlm_spearman": human_vlm,
        "all_ge_3_agreement": {
            "agreement_rate": _ratio(sum(threshold_rows), len(threshold_rows)),
            "human_pass_vlm_pass": confusion[(True, True)],
            "human_pass_vlm_fail": confusion[(True, False)],
            "human_fail_vlm_pass": confusion[(False, True)],
            "human_fail_vlm_fail": confusion[(False, False)],
        },
        "paired_preference": paired_preference,
        "inter_rater": inter_rater,
    }


def prepare_package(
    *,
    prepared_records_path: Path,
    review_root: Path,
    output_dir: Path,
    private_key_path: Path | None = None,
    count: int,
    seed: int,
) -> dict[str, Any]:
    prepared = json.loads(prepared_records_path.read_text(encoding="utf-8"))
    indexes = {
        method: {
            str(row.get("case_id") or ""): row
            for row in prepared.get(method) or []
            if str(row.get("case_id") or "")
        }
        for method in METHODS
    }
    common = set.intersection(*(set(indexes[method]) for method in METHODS))
    candidates = []
    for case_id in sorted(common):
        source = indexes["algotutorgen_stage2"][case_id]
        if not all(Path(str(indexes[method][case_id].get("screenshot") or "")).is_file() for method in METHODS):
            continue
        if not all((review_root / method / f"{case_id}.json").is_file() for method in METHODS):
            continue
        candidates.append(
            {
                "case_id": case_id,
                "family": str(source.get("family") or "unknown"),
                "problem_title": str(source.get("problem_title") or case_id),
                "problem_description": str(source.get("problem_description") or ""),
            }
        )
    selected = select_stratified_cases(candidates, count=count, seed=seed)
    private_key_path = private_key_path or default_private_key_path(output_dir)
    output_resolved = output_dir.resolve()
    private_resolved = private_key_path.resolve()
    if private_resolved == output_resolved or output_resolved in private_resolved.parents:
        raise ValueError("private blind key must be outside the public review directory")
    existing_manifest = _compatible_existing_visual_package(
        output_dir=output_dir,
        private_key_path=private_key_path,
        selected=selected,
        seed=seed,
    )
    if existing_manifest is not None:
        return existing_manifest
    blind_secret = secrets.token_bytes(32)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir()
    (output_dir / "private_blind_key.json").unlink(missing_ok=True)
    key_rows = []
    public_rows = []
    for case in selected:
        case_id = str(case["case_id"])
        for method in METHODS:
            record = indexes[method][case_id]
            blind_id = blind_page_id(case_id, method, secret=blind_secret)
            source_image = Path(str(record.get("screenshot") or ""))
            image_path = pages_dir / f"{blind_id}.png"
            page_path = pages_dir / f"{blind_id}.html"
            shutil.copy2(source_image, image_path)
            page_path.write_text(
                _review_page_html(
                    blind_id=blind_id,
                    title=case["problem_title"],
                    description=case["problem_description"],
                    image_name=image_path.name,
                ),
                encoding="utf-8",
            )
            review = json.loads((review_root / method / f"{case_id}.json").read_text(encoding="utf-8"))
            vlm_scores = {
                metric: int((review.get("scores") or {}).get(metric) or 0)
                for metric in VISUAL_METRICS
            }
            key_rows.append(
                {
                    "blind_id": blind_id,
                    "case_id": case_id,
                    "family": case["family"],
                    "method": method,
                    "page_ref": str(page_path.relative_to(output_dir)),
                    "source_screenshot": str(source_image),
                    "vlm_scores": vlm_scores,
                }
            )
            public_rows.append(
                {
                    "blind_id": blind_id,
                    "problem_title": case["problem_title"],
                    "page_ref": str(page_path.relative_to(output_dir)),
                    **{metric: "" for metric in VISUAL_METRICS},
                    "notes": "",
                }
            )
    rows_a = list(public_rows)
    rows_b = list(public_rows)
    random.Random(seed + 1).shuffle(rows_a)
    random.Random(seed + 2).shuffle(rows_b)
    _write_csv(output_dir / "reviewer_a.csv", rows_a)
    _write_csv(output_dir / "reviewer_b.csv", rows_b)
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key_path.write_text(
        json.dumps(
            {
                "schema_version": "plan2-visual-blind-key-v1",
                "blind_id_scheme": "hmac-sha256-secret-v1",
                "blind_hmac_secret_hex": blind_secret.hex(),
                "pages": key_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    private_key_path.chmod(0o600)
    manifest = {
        "kind": "plan2_five_method_visual_human_calibration",
        "status": "pending_human_labels",
        "human_labels_present": False,
        "reviewers_required": 2,
        "case_count": len(selected),
        "family_count": len({row["family"] for row in selected}),
        "method_count": len(METHODS),
        "page_count": len(key_rows),
        "metrics": list(VISUAL_METRICS),
        "rating_scale": "integer 1-5",
        "threshold": "All four dimensions >= 3",
        "blind_id_scheme": "hmac-sha256-secret-v1",
        "private_mapping_separated": True,
        "seed": seed,
    }
    (output_dir / "package_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "README.md").write_text(_protocol_readme(manifest), encoding="utf-8")
    return manifest


def _compatible_existing_visual_package(
    *,
    output_dir: Path,
    private_key_path: Path,
    selected: list[dict[str, Any]],
    seed: int,
) -> dict[str, Any] | None:
    manifest_path = output_dir / "package_manifest.json"
    reviewer_a_path = output_dir / "reviewer_a.csv"
    reviewer_b_path = output_dir / "reviewer_b.csv"
    pages_dir = output_dir / "pages"
    public_paths = (manifest_path, reviewer_a_path, reviewer_b_path)
    any_existing = (
        any(path.exists() for path in public_paths)
        or private_key_path.exists()
        or (pages_dir.is_dir() and any(pages_dir.iterdir()))
    )
    if not any_existing:
        return None
    if not all(path.is_file() for path in public_paths) or not private_key_path.is_file():
        raise FileExistsError(
            f"refusing to overwrite partial visual human-review package: {output_dir}"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key_data = json.loads(private_key_path.read_text(encoding="utf-8"))
    key_rows = list(key_data.get("pages") or [])
    expected_pairs = {
        (str(case.get("case_id") or ""), method)
        for case in selected
        for method in METHODS
    }
    actual_pairs = {
        (str(row.get("case_id") or ""), str(row.get("method") or ""))
        for row in key_rows
    }
    expected_blind_ids = {str(row.get("blind_id") or "") for row in key_rows}
    reviewer_a = _read_csv(reviewer_a_path)
    reviewer_b = _read_csv(reviewer_b_path)
    ids_a = [str(row.get("blind_id") or "") for row in reviewer_a]
    ids_b = [str(row.get("blind_id") or "") for row in reviewer_b]
    referenced_pages = [output_dir / str(row.get("page_ref") or "") for row in key_rows]
    compatible = (
        manifest.get("kind") == "plan2_five_method_visual_human_calibration"
        and manifest.get("seed") == seed
        and manifest.get("case_count") == len(selected)
        and manifest.get("method_count") == len(METHODS)
        and manifest.get("page_count") == len(expected_pairs)
        and key_data.get("schema_version") == "plan2-visual-blind-key-v1"
        and actual_pairs == expected_pairs
        and len(expected_blind_ids) == len(expected_pairs)
        and len(ids_a) == len(set(ids_a)) == len(expected_pairs)
        and len(ids_b) == len(set(ids_b)) == len(expected_pairs)
        and set(ids_a) == expected_blind_ids
        and set(ids_b) == expected_blind_ids
        and all(path.is_file() for path in referenced_pages)
    )
    if not compatible:
        raise FileExistsError(
            f"refusing to overwrite existing visual human-review package with a different protocol: {output_dir}"
        )
    return manifest


def _review_page_html(*, blind_id: str, title: str, description: str, image_name: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(blind_id)}</title><style>
body{{margin:0;background:#f3f4f6;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1480px;margin:0 auto;padding:20px}}header{{background:#fff;border:1px solid #d1d5db;border-radius:10px;padding:16px;margin-bottom:14px}}
h1{{font-size:20px;margin:0 0 8px}}p{{margin:0;color:#4b5563;line-height:1.6}}img{{display:block;width:100%;height:auto;background:#fff;border:1px solid #d1d5db;border-radius:10px}}
</style></head><body><main><header><h1>{html.escape(str(title))}</h1><p>{html.escape(str(description))}</p></header><img src="{html.escape(image_name)}" alt="anonymous algorithm visualization"></main></body></html>"""


def _protocol_readme(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Plan-2 五方法视觉人工校准",
            "",
            "- 状态：`pending_human_labels`",
            f"- {manifest['case_count']} 题 × {manifest['method_count']} 方法 = {manifest['page_count']} 个匿名页面",
            f"- 覆盖 {manifest['family_count']} 个算法族；两名评审者独立评分",
            "",
            "两位评审者分别使用 reviewer_a.csv 和 reviewer_b.csv；方法映射由实验协调者另行保管，不放在本评审目录中。",
            "每项只填 1–5 的整数：",
            "",
            "- problem_visual_alignment：题面实体、数据结构、目标输出与视觉编码是否贴合。",
            "- algorithm_state_readability：指针、窗口、队列、栈、DP、路径等当前状态是否清楚。",
            "- process_transition_clarity：高亮、轨迹、帧控件或前后状态是否清楚表达变化。",
            "- instructional_visual_design：标签、分组、解释邻近和信息层次是否有利于教学。",
            "",
            "预先约定的异常页面规则：空白页、全白截图、图片无法加载或页面渲染失败时，四项均记 1 分，并在 notes 填写 `render_failure`。若仅有部分内容可见，则只按实际可见内容评分，不推测未显示的设计，并在 notes 说明缺失部分。",
            "",
            "不要评价最终算法答案正确性，也不要根据页面风格猜测方法。完成后运行本脚本的分析模式；不得用模型补写人工标签。",
            "",
        ]
    )


def _rating_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        blind_id = str(row.get("blind_id") or "")
        if blind_id:
            result[blind_id] = row
    return result


def _score(value: Any, *, allow_blank: bool = False) -> int | None:
    text = str(value or "").strip()
    if not text and allow_blank:
        return None
    try:
        number = int(text)
    except ValueError as exc:
        raise ValueError(f"visual score must be an integer 1-5, got {value!r}") from exc
    if number < 1 or number > 5:
        raise ValueError(f"visual score must be in 1-5, got {number}")
    return number


def _row_complete(row: dict[str, Any] | None) -> bool:
    if row is None:
        return False
    try:
        return all(_score(row.get(metric), allow_blank=True) is not None for metric in VISUAL_METRICS)
    except ValueError:
        return False


def _spearman(left: list[float], right: list[float]) -> dict[str, Any] | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    if len(set(left)) < 2 or len(set(right)) < 2:
        return {"n": len(left), "rho": None, "p_value": None, "reason": "constant_vector"}
    from scipy.stats import spearmanr

    result = spearmanr(left, right)
    return {"n": len(left), "rho": round(float(result.statistic), 6), "p_value": float(result.pvalue)}


def _quadratic_weighted_kappa(left: list[int], right: list[int]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    size = 5
    observed = [[0.0] * size for _ in range(size)]
    left_counts = [0.0] * size
    right_counts = [0.0] * size
    for a, b in zip(left, right):
        observed[a - 1][b - 1] += 1
        left_counts[a - 1] += 1
        right_counts[b - 1] += 1
    total = float(len(left))
    observed_weighted = 0.0
    expected_weighted = 0.0
    for i in range(size):
        for j in range(size):
            weight = ((i - j) / (size - 1)) ** 2
            observed_weighted += weight * observed[i][j] / total
            expected_weighted += weight * (left_counts[i] * right_counts[j]) / (total * total)
    if expected_weighted == 0:
        return 1.0 if observed_weighted == 0 else None
    return round(1.0 - observed_weighted / expected_weighted, 6)


def _ratio(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator, 12) if denominator else None


def _seeded_order(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["blind_id"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--prepared-records", type=Path, default=DEFAULT_PREPARED_RECORDS)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--reviewer-a", type=Path)
    parser.add_argument("--reviewer-b", type=Path)
    parser.add_argument("--private-key", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    if args.prepare:
        manifest = prepare_package(
            prepared_records_path=args.prepared_records,
            review_root=args.review_root,
            output_dir=output_dir,
            private_key_path=args.private_key,
            count=args.count,
            seed=args.seed,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    key_path = args.private_key or default_private_key_path(output_dir)
    key_data = json.loads(key_path.read_text(encoding="utf-8"))
    reviewer_a = _read_csv(args.reviewer_a or output_dir / "reviewer_a.csv")
    reviewer_b = _read_csv(args.reviewer_b or output_dir / "reviewer_b.csv")
    result = analyze_ratings(list(key_data.get("pages") or []), reviewer_a, reviewer_b)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "human_calibration_analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
