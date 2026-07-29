"""Build a public, case-centric sample gallery for the five evaluated methods.

The source experiments live under the ignored ``output/`` tree.  This script
copies a deterministic, sanitized subset into ``artifacts/`` so GitHub readers
can inspect real pages, screenshots, WebGen source code, and evaluation
summaries without access to the full experiment workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_all_method_auxiliary_eval import (  # noqa: E402
    MACHINE_BOOL_KEYS,
    METHOD_LABELS,
    METHOD_ORDER,
    build_method_records,
)


DEFAULT_AUXILIARY_DIR = ROOT / "output/experiments/all_method_auxiliary_eval_20260718"
DEFAULT_TARGET = ROOT / "artifacts/method_comparison_samples"
SCHEMA_VERSION = "method-artifact-gallery-v1"

SELECTED_CASES: tuple[dict[str, str], ...] = (
    {"family": "BFS/DFS 基础图", "case_id": "graph_topological_sort"},
    {"family": "DP 核心扩展", "case_id": "complete_knapsack_coin_change"},
    {"family": "Trie", "case_id": "trie_prefix"},
    {"family": "一维 DP", "case_id": "house_robber"},
    {"family": "二分", "case_id": "binary_search"},
    {"family": "二维 DP", "case_id": "unique_paths"},
    {"family": "几何 / 扫描线", "case_id": "convex_hull"},
    {"family": "区间结构", "case_id": "segment_tree_range_sum"},
    {"family": "哈希表 / map", "case_id": "two_sum"},
    {"family": "回溯 / 递归", "case_id": "permutations"},
    {"family": "图高级", "case_id": "articulation_bridges"},
    {"family": "堆 / TopK / Huffman", "case_id": "kth_largest"},
    {"family": "字符串高级算法", "case_id": "kmp"},
    {"family": "并查集", "case_id": "provinces"},
    {"family": "排序", "case_id": "insertion_sort"},
    {"family": "数学与位运算", "case_id": "fast_power_mod"},
    {"family": "数组指针 / 窗口 / 前缀", "case_id": "two_pointer_pair_sum"},
    {"family": "最短路 / MST", "case_id": "dijkstra_shortest_path"},
    {"family": "栈 / 队列 / 单调栈", "case_id": "daily_temperatures"},
    {"family": "树 / BST / LCA", "case_id": "lca"},
    {"family": "树形 DP", "case_id": "tree_max_independent_set"},
    {"family": "贪心", "case_id": "merge_intervals"},
    {"family": "链表与缓存", "case_id": "reverse_linked_list"},
)

METHOD_DESCRIPTIONS = {
    "algotutorgen_stage2": "AlgoTutorGen 的验证链路与 Stage2 视觉增强产物。",
    "direct_html": "模型直接生成完整 HTML 的基线。",
    "webgen_agent": "WebGen-Agent 生成的前端项目源码与审计截图。",
    "htmlcure_strict": "Direct HTML 经 HTMLCure 修复后的 strict 结果。",
    "browser_repair_1call": "Direct HTML 使用一次通用浏览器反馈修复后的结果。",
}

MACHINE_LABELS = {
    "page_load_ok": "Load",
    "visible_answer_match": "Answer",
    "interaction_reachable": "Interaction",
    "correct_feedback_ok": "Correct FB",
    "wrong_feedback_ok": "Wrong FB",
    "hint_ok": "Hint",
    "show_answer_ok": "Show",
    "learning_log_ok": "Log",
    "mutation_free_ok": "Mutation-free",
}

WEBGEN_IGNORE = shutil.ignore_patterns(
    "node_modules",
    "dist",
    "build",
    ".git",
    ".vite",
    ".cache",
    "coverage",
    "__pycache__",
    "*.log",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def require_file(path: Path, label: str) -> Path:
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"{label} missing or empty: {path}")
    return path


def require_dir(path: Path, label: str) -> Path:
    if not path.is_dir():
        raise FileNotFoundError(f"{label} directory missing: {path}")
    return path


def repo_relative(path: Path, *, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"source path is outside repository: {resolved}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_case_ids() -> tuple[str, ...]:
    return tuple(row["case_id"] for row in SELECTED_CASES)


def _load_benchmark_cases(root: Path) -> dict[str, dict[str, Any]]:
    benchmark = load_json(root / "benchmark/algo_learn_env_benchmark.json")
    rows = [row for row in benchmark.get("cases") or [] if isinstance(row, dict)]
    return {str(row.get("id") or ""): row for row in rows if str(row.get("id") or "")}


def _public_case_payload(case: dict[str, Any]) -> dict[str, Any]:
    samples = [row for row in case.get("samples") or [] if isinstance(row, dict)]
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": str(case.get("id") or ""),
        "algorithm_id": str(case.get("algorithm_id") or case.get("id") or ""),
        "title": str(case.get("title") or case.get("id") or ""),
        "family": str(case.get("family") or ""),
        "difficulty": str(case.get("difficulty") or ""),
        "problem": str(case.get("problem") or ""),
        "strategy": str(case.get("strategy") or ""),
        "input_contract": str(case.get("input_contract") or ""),
        "time_complexity": str(case.get("time_complexity") or ""),
        "space_complexity": str(case.get("space_complexity") or ""),
        "learning_objectives": list(case.get("learning_objectives") or []),
        "required_views": list(case.get("required_views") or []),
        "interaction_tasks": list(case.get("interaction_tasks") or []),
        "sample": samples[0] if samples else None,
    }


def _review_payload(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(review.get("ok")),
        "browser_ok": bool(review.get("browser_ok")),
        "teaching_overall_score": review.get("teaching_overall_score"),
        "visual_overall_score": review.get("visual_overall_score"),
        "scores": dict(review.get("scores") or {}),
        "strengths": list(review.get("strengths") or []),
        "weaknesses": list(review.get("weaknesses") or []),
        "recommendation": str(review.get("recommendation") or ""),
        "confidence": review.get("confidence"),
    }


def _copy_webgen_source(source: Path, destination: Path) -> None:
    require_dir(source, "WebGen source")
    shutil.copytree(source, destination, ignore=WEBGEN_IGNORE)
    require_file(destination / "index.html", "WebGen index.html")
    require_file(destination / "package.json", "WebGen package.json")


def _artifact_files(
    *,
    method: str,
    record: dict[str, Any],
    method_dir: Path,
    root: Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    screenshot_source = require_file(Path(str(record.get("screenshot") or "")), "screenshot")
    screenshot_target = method_dir / "screenshot.png"
    shutil.copy2(screenshot_source, screenshot_target)

    files = {"screenshot": "screenshot.png"}
    checksums = {"screenshot_sha256": sha256_file(screenshot_target)}
    provenance = {"screenshot": repo_relative(screenshot_source, root=root)}

    if method == "webgen_agent":
        source_dir = require_dir(Path(str(record.get("source_dir") or "")), "WebGen source")
        _copy_webgen_source(source_dir, method_dir / "source")
        files["source_entry"] = "source/index.html"
        files["source_package"] = "source/package.json"
        provenance["source_dir"] = repo_relative(source_dir, root=root)
        checksums["source_entry_sha256"] = sha256_file(method_dir / "source/index.html")
    else:
        page_source = require_file(
            Path(str(record.get("visual_html") or record.get("html") or "")),
            "HTML page",
        )
        page_target = method_dir / "page.html"
        shutil.copy2(page_source, page_target)
        files["page"] = "page.html"
        provenance["page"] = repo_relative(page_source, root=root)
        checksums["page_sha256"] = sha256_file(page_target)

    original_html = Path(str(record.get("html") or ""))
    if original_html.is_file():
        provenance["machine_audit_html"] = repo_relative(original_html, root=root)
    return files, checksums, provenance


def _method_audit(
    *,
    method: str,
    record: dict[str, Any],
    review: dict[str, Any],
    files: dict[str, str],
    checksums: dict[str, str],
    provenance: dict[str, str],
) -> dict[str, Any]:
    machine_metrics = {key: bool(record.get(key)) for key in MACHINE_BOOL_KEYS}
    return {
        "schema_version": SCHEMA_VERSION,
        "condition": method,
        "condition_label": METHOD_LABELS[method],
        "case_id": str(record.get("case_id") or ""),
        "problem_title": str(record.get("problem_title") or ""),
        "family": str(record.get("family") or ""),
        "machine_metrics": machine_metrics,
        "machine_ok": all(machine_metrics.values()),
        "auxiliary_review": _review_payload(review),
        "files": files,
        "checksums": checksums,
        "provenance": provenance,
    }


def _status(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _case_readme(
    *,
    case: dict[str, Any],
    audits: dict[str, dict[str, Any]],
) -> str:
    sample = case.get("sample") or {}
    lines = [
        f"# {case['title']}",
        "",
        f"- 案例 ID：`{case['case_id']}`",
        f"- 算法家族：{case['family']}",
        f"- 难度：{case.get('difficulty') or '未标注'}",
        f"- 时间复杂度：`{case.get('time_complexity') or '未标注'}`",
        f"- 空间复杂度：`{case.get('space_complexity') or '未标注'}`",
        "",
        case.get("problem") or "",
        "",
        "## 抽样输入",
        "",
        "```json",
        json.dumps(sample, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 九项机器判定",
        "",
    ]
    headers = ["方法", *(MACHINE_LABELS[key] for key in MACHINE_BOOL_KEYS), "Machine OK"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for method in METHOD_ORDER:
        audit = audits[method]
        metrics = audit["machine_metrics"]
        values = [METHOD_LABELS[method], *(_status(metrics[key]) for key in MACHINE_BOOL_KEYS), _status(audit["machine_ok"])]
        lines.append("| " + " | ".join(values) + " |")

    lines.extend(["", "## 五种方法的真实产物", ""])
    for method in METHOD_ORDER:
        audit = audits[method]
        review = audit["auxiliary_review"]
        method_dir = method
        if method == "webgen_agent":
            entry = f"[{METHOD_LABELS[method]} 源码入口]({method_dir}/source/index.html)"
            extra = f" · [package.json]({method_dir}/source/package.json)"
        else:
            entry = f"[打开 {METHOD_LABELS[method]} HTML]({method_dir}/page.html)"
            extra = ""
        lines.extend(
            [
                f"### {METHOD_LABELS[method]}",
                "",
                f"{entry}{extra} · [审计摘要]({method_dir}/audit.json)",
                "",
                f"- Machine OK：**{_status(audit['machine_ok'])}**",
                f"- 教学总分：{review.get('teaching_overall_score')}",
                f"- 视觉总分：{review.get('visual_overall_score')}",
                "",
                f"![{case['case_id']} - {METHOD_LABELS[method]}]({method_dir}/screenshot.png)",
                "",
            ]
        )
    return "\n".join(lines)


def _root_readme(manifest: dict[str, Any]) -> str:
    lines = [
        "# 五方法产物对比样例库",
        "",
        "本目录从已完成的 Full-200 实验中抽取真实产物，用于在 GitHub 中快速横向查看。",
        "抽样采用“一类算法家族一个典型案例”：覆盖全部 23 个家族、23 个案例、5 种方法，共 115 组方法产物。",
        "",
        "> 本目录是实验产物展示，不替代完整统计结果。完整数字以 `docs/EXPERIMENT_RESULTS.md` 和 `docs/EXPERIMENT_RESULTS_DETAILED.md` 为准。",
        "",
        "## 五种方法",
        "",
        "| 方法 | 说明 | 每例保存内容 |",
        "| --- | --- | --- |",
    ]
    for method in METHOD_ORDER:
        contents = "源码、截图、审计摘要" if method == "webgen_agent" else "HTML、截图、审计摘要"
        lines.append(f"| {METHOD_LABELS[method]} | {METHOD_DESCRIPTIONS[method]} | {contents} |")

    lines.extend(
        [
            "",
            "## 如何阅读",
            "",
            "- 点击案例进入同一输入下的五方法对比页。",
            "- `page.html` 是实际用于视觉评审的页面；WebGen-Agent 因为是前端工程，保存在 `source/`。",
            "- `screenshot.png` 是实验使用的真实截图。",
            "- `audit.json` 包含九项机器判定、Machine OK、教学/视觉评分摘要和来源哈希。",
            "- Machine OK 只有在九项判定全部通过时才为 PASS。",
            "",
            "## 案例索引",
            "",
        ]
    )
    headers = ["家族", "案例", *(METHOD_LABELS[method] for method in METHOD_ORDER)]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for case in manifest["cases"]:
        statuses = [_status(case["methods"][method]["machine_ok"]) for method in METHOD_ORDER]
        case_link = f"[{case['title']}](cases/{case['case_id']}/README.md)"
        lines.append("| " + " | ".join([case["family"], case_link, *statuses]) + " |")

    lines.extend(
        [
            "",
            "## 重新生成",
            "",
            "源实验目录存在时，在仓库根目录运行：",
            "",
            "```bash",
            "TMPDIR=/tmp python3 scripts/build_method_artifact_gallery.py",
            "```",
            "",
            "只验证已提交目录：",
            "",
            "```bash",
            "TMPDIR=/tmp python3 scripts/build_method_artifact_gallery.py --validate-only",
            "```",
        ]
    )
    return "\n".join(lines)


def build_gallery(
    *,
    root: Path = ROOT,
    target: Path = DEFAULT_TARGET,
    auxiliary_dir: Path = DEFAULT_AUXILIARY_DIR,
) -> dict[str, int]:
    root = root.resolve()
    target = target.resolve()
    auxiliary_dir = auxiliary_dir.resolve()
    require_file(root / "benchmark/algo_learn_env_benchmark.json", "benchmark")
    require_dir(auxiliary_dir / "review_cases", "auxiliary review cases")

    benchmark_cases = _load_benchmark_cases(root)
    benchmark_families = {str(row.get("family") or "") for row in benchmark_cases.values()}
    selected_families = {row["family"] for row in SELECTED_CASES}
    if len(SELECTED_CASES) != 23 or len(selected_families) != 23:
        raise ValueError("selection must contain exactly 23 unique families")
    if selected_families != benchmark_families:
        missing = sorted(benchmark_families - selected_families)
        extra = sorted(selected_families - benchmark_families)
        raise ValueError(f"selection family mismatch: missing={missing}, extra={extra}")

    grouped = build_method_records(root=root, output_dir=auxiliary_dir)
    method_rows = {
        method: {str(row.get("case_id") or ""): row for row in grouped[method]}
        for method in METHOD_ORDER
    }

    if target.exists():
        shutil.rmtree(target)
    (target / "cases").mkdir(parents=True)

    source_report = load_json(auxiliary_dir / "all_method_auxiliary_eval_report.json")
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_report": repo_relative(auxiliary_dir / "all_method_auxiliary_eval_report.json", root=root),
        "source_report_created_at": source_report.get("created_at"),
        "selection_strategy": "one representative case from each of the 23 benchmark families",
        "method_order": list(METHOD_ORDER),
        "methods": [
            {
                "condition": method,
                "label": METHOD_LABELS[method],
                "description": METHOD_DESCRIPTIONS[method],
            }
            for method in METHOD_ORDER
        ],
        "cases": [],
    }

    for selected in SELECTED_CASES:
        case_id = selected["case_id"]
        if case_id not in benchmark_cases:
            raise KeyError(f"selected case not found in benchmark: {case_id}")
        benchmark_case = benchmark_cases[case_id]
        actual_family = str(benchmark_case.get("family") or "")
        if actual_family != selected["family"]:
            raise ValueError(
                f"family mismatch for {case_id}: expected {selected['family']}, got {actual_family}"
            )

        case_payload = _public_case_payload(benchmark_case)
        case_dir = target / "cases" / case_id
        case_dir.mkdir(parents=True)
        write_json(case_dir / "case.json", case_payload)

        audits: dict[str, dict[str, Any]] = {}
        manifest_methods: dict[str, Any] = {}
        for method in METHOD_ORDER:
            if case_id not in method_rows[method]:
                raise KeyError(f"missing method record: {method}/{case_id}")
            record = method_rows[method][case_id]
            review_path = auxiliary_dir / "review_cases" / method / f"{case_id}.json"
            review = load_json(require_file(review_path, "auxiliary review"))
            method_dir = case_dir / method
            method_dir.mkdir()
            files, checksums, provenance = _artifact_files(
                method=method,
                record=record,
                method_dir=method_dir,
                root=root,
            )
            audit = _method_audit(
                method=method,
                record=record,
                review=review,
                files=files,
                checksums=checksums,
                provenance=provenance,
            )
            write_json(method_dir / "audit.json", audit)
            audits[method] = audit
            manifest_methods[method] = {
                "machine_ok": audit["machine_ok"],
                "artifact_dir": f"cases/{case_id}/{method}",
                "screenshot": f"cases/{case_id}/{method}/screenshot.png",
                "entry": (
                    f"cases/{case_id}/{method}/source/index.html"
                    if method == "webgen_agent"
                    else f"cases/{case_id}/{method}/page.html"
                ),
                "audit": f"cases/{case_id}/{method}/audit.json",
            }

        write_text(case_dir / "README.md", _case_readme(case=case_payload, audits=audits))
        manifest["cases"].append(
            {
                "case_id": case_id,
                "title": case_payload["title"],
                "family": case_payload["family"],
                "case_metadata": f"cases/{case_id}/case.json",
                "comparison": f"cases/{case_id}/README.md",
                "methods": manifest_methods,
            }
        )

    write_json(target / "manifest.json", manifest)
    write_text(target / "README.md", _root_readme(manifest))
    return validate_gallery(target)


def _local_markdown_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    links = []
    for raw in re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", text):
        target = unquote(raw.split("#", 1)[0].strip())
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        links.append(target)
    return links


def _validate_markdown_links(path: Path) -> list[str]:
    errors = []
    for link in _local_markdown_links(path):
        resolved = (path.parent / link).resolve()
        if not resolved.exists():
            errors.append(f"broken link in {path}: {link}")
    return errors


def validate_gallery(target: Path = DEFAULT_TARGET) -> dict[str, int]:
    target = target.resolve()
    errors: list[str] = []
    manifest_path = target / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"gallery manifest missing: {manifest_path}")
    manifest = load_json(manifest_path)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected gallery schema_version")
    if manifest.get("method_order") != list(METHOD_ORDER):
        errors.append("method_order does not match the five evaluated methods")

    cases = [row for row in manifest.get("cases") or [] if isinstance(row, dict)]
    families = {str(row.get("family") or "") for row in cases}
    if len(cases) != 23:
        errors.append(f"expected 23 cases, found {len(cases)}")
    if len(families) != 23:
        errors.append(f"expected 23 families, found {len(families)}")
    if {str(row.get("case_id") or "") for row in cases} != set(selected_case_ids()):
        errors.append("manifest case IDs do not match the frozen selection")

    root_readme = target / "README.md"
    if not root_readme.is_file():
        errors.append("root README.md missing")
    else:
        errors.extend(_validate_markdown_links(root_readme))

    method_artifact_count = 0
    for case in cases:
        case_id = str(case.get("case_id") or "")
        case_dir = target / "cases" / case_id
        case_readme = case_dir / "README.md"
        case_json = case_dir / "case.json"
        if not case_readme.is_file():
            errors.append(f"missing case README: {case_id}")
        else:
            errors.extend(_validate_markdown_links(case_readme))
        if not case_json.is_file():
            errors.append(f"missing case metadata: {case_id}")

        manifest_methods = case.get("methods") or {}
        if set(manifest_methods) != set(METHOD_ORDER):
            errors.append(f"method set mismatch: {case_id}")
        for method in METHOD_ORDER:
            method_artifact_count += 1
            method_dir = case_dir / method
            screenshot = method_dir / "screenshot.png"
            audit_path = method_dir / "audit.json"
            if not screenshot.is_file() or screenshot.stat().st_size <= 0:
                errors.append(f"missing screenshot: {case_id}/{method}")
            if not audit_path.is_file():
                errors.append(f"missing audit: {case_id}/{method}")
                continue
            audit_text = audit_path.read_text(encoding="utf-8")
            if "/ssd1/" in audit_text or "/home/" in audit_text:
                errors.append(f"absolute path leaked into audit: {case_id}/{method}")
            audit = json.loads(audit_text)
            metrics = audit.get("machine_metrics") or {}
            if set(metrics) != set(MACHINE_BOOL_KEYS):
                errors.append(f"incomplete machine metrics: {case_id}/{method}")
            if bool(audit.get("machine_ok")) != all(bool(metrics.get(key)) for key in MACHINE_BOOL_KEYS):
                errors.append(f"machine_ok mismatch: {case_id}/{method}")

            if method == "webgen_agent":
                source = method_dir / "source"
                if not (source / "index.html").is_file():
                    errors.append(f"missing WebGen index: {case_id}")
                if not (source / "package.json").is_file():
                    errors.append(f"missing WebGen package: {case_id}")
                source_files = [
                    path
                    for path in source.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".css"}
                ]
                if not source_files:
                    errors.append(f"missing WebGen implementation source: {case_id}")
            else:
                page = method_dir / "page.html"
                if not page.is_file() or page.stat().st_size <= 0:
                    errors.append(f"missing HTML page: {case_id}/{method}")

    for path in target.rglob("*"):
        if path.is_file() and path.stat().st_size >= 100 * 1024 * 1024:
            errors.append(f"file exceeds GitHub 100 MB limit: {path}")

    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:50])
        suffix = "" if len(errors) <= 50 else f"\n- ... {len(errors) - 50} more errors"
        raise ValueError(f"gallery validation failed ({len(errors)} errors):\n{preview}{suffix}")
    return {
        "case_count": len(cases),
        "family_count": len(families),
        "method_artifact_count": method_artifact_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--auxiliary-dir", type=Path, default=DEFAULT_AUXILIARY_DIR)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        summary = validate_gallery(args.target)
    else:
        summary = build_gallery(target=args.target, auxiliary_dir=args.auxiliary_dir)
    print(
        "method_artifact_gallery: PASS "
        f"cases={summary['case_count']} "
        f"families={summary['family_count']} "
        f"method_artifacts={summary['method_artifact_count']}"
    )


if __name__ == "__main__":
    main()
