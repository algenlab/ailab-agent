"""Build and validate the English-only five-method artifact gallery."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


CJK_RE = re.compile(r"[\u3400-\u9fff]")
LOCAL_PATH_RE = re.compile(r"(?:file://)?/(?:ssd1|home|tmp)/[^\s\"']+")
TEXT_SUFFIXES = {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".css", ".txt"}
MACHINE_BOOL_KEYS = (
    "page_load_ok",
    "visible_answer_match",
    "interaction_reachable",
    "correct_feedback_ok",
    "wrong_feedback_ok",
    "hint_ok",
    "show_answer_ok",
    "learning_log_ok",
    "mutation_free_ok",
)
METHOD_ORDER = (
    "algotutorgen_stage1",
    "algotutorgen_stage2",
    "direct_html",
    "webgen_agent",
    "htmlcure_strict",
    "browser_repair_1call",
)
METHOD_LABELS = {
    "algotutorgen_stage1": "AlgoTutorGen / Stage1",
    "algotutorgen_stage2": "AlgoTutorGen / Stage2",
    "direct_html": "Direct HTML",
    "webgen_agent": "WebGen-Agent",
    "htmlcure_strict": "Direct + HTMLCure (strict)",
    "browser_repair_1call": "Direct-BrowserRepair (1 call)",
}
METHOD_DESCRIPTIONS = {
    "algotutorgen_stage1": "The existing verified Stage1 solution, trace, teaching interactions, and deterministic visualization localized into English without regenerating the solution.",
    "algotutorgen_stage2": "A newly generated English Stage2 visual page built from the verified AlgoTutorGen result; its nine machine checks come from the paired Stage1 interaction page.",
    "direct_html": "A model directly generates the complete interactive HTML page.",
    "webgen_agent": "WebGen-Agent produces a complete frontend project through its iterative workflow.",
    "htmlcure_strict": "HTMLCure repairs the independently generated Direct HTML page under its strict setting.",
    "browser_repair_1call": "An independent one-call Direct-BrowserRepair budget run with no prior browser-feedback repair call.",
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


def assert_english_only_tree(root: Path) -> None:
    violations: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = CJK_RE.search(text)
        if match:
            excerpt = text[max(0, match.start() - 30) : match.start() + 60].replace("\n", " ")
            violations.append(f"{path.relative_to(root)}: {excerpt}")
    if violations:
        raise ValueError("English-only gate failed:\n" + "\n".join(violations[:50]))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _root_path(value: Any) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else ROOT / path


def _rows(path: Path, key: str = "results") -> list[dict[str, Any]]:
    data = _load(path)
    return [row for row in (data.get(key) or data.get("records") or []) if isinstance(row, dict)]


def _by_case(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("case_id") or ""): row for row in rows if str(row.get("case_id") or "")}


def _audit_by_case(path: Path, *, condition: str | None = None) -> dict[str, dict[str, Any]]:
    rows = _rows(path, key="records")
    if condition is not None:
        rows = [row for row in rows if str(row.get("condition") or "") == condition]
    return _by_case(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, label: str) -> Path:
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"{label} is missing or empty: {path}")
    return path


def _machine_payload(row: dict[str, Any]) -> dict[str, bool]:
    return {key: bool(row.get(key)) for key in MACHINE_BOOL_KEYS}


def _sanitize_public_text(value: Any) -> str:
    text = str(value or "")
    return LOCAL_PATH_RE.sub(
        lambda match: "file://<local-path>" if match.group(0).startswith("file://") else "<local-path>",
        text,
    )


def _machine_diagnostics(row: dict[str, Any]) -> dict[str, Any]:
    """Keep concise browser evidence needed to interpret failed machine checks."""

    diagnostics: dict[str, Any] = {}
    errors = row.get("console_page_errors")
    if isinstance(errors, list):
        diagnostics["console_page_errors"] = [_sanitize_public_text(error) for error in errors]
    preview = row.get("feedback_preview")
    if isinstance(preview, dict):
        diagnostics["feedback_preview"] = {
            str(key): _sanitize_public_text(value)
            for key, value in preview.items()
        }
    return diagnostics


def _case_readme(case: dict[str, Any], audits: dict[str, dict[str, Any]]) -> str:
    sample = (case.get("samples") or [{}])[0]
    lines = [
        f"# {case['title']}",
        "",
        f"- Case ID: `{case['id']}`",
        f"- Algorithm family: {case['family']}",
        f"- Difficulty: {case.get('difficulty') or 'not specified'}",
        f"- Time complexity: `{case.get('time_complexity') or 'not specified'}`",
        f"- Space complexity: `{case.get('space_complexity') or 'not specified'}`",
        "",
        str(case.get("problem") or ""),
        "",
        "## Fixed input and expected answer",
        "",
        "```json",
        json.dumps(sample, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Nine machine checks",
        "",
        "Machine OK means that all nine browser checks pass for the evaluated interaction page.",
        "The AlgoTutorGen / Stage2 row reuses the checks from its paired Stage1 interaction page; it is not a separate audit of the saved Stage2 visualization page.",
        "",
        "| Method | Load | Answer | Interaction | Correct feedback | Wrong feedback | Hint | Show answer | Learning log | Mutation-free | Machine OK |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for method in METHOD_ORDER:
        audit = audits[method]
        metrics = audit["machine_metrics"]
        values = ["PASS" if metrics[key] else "FAIL" for key in MACHINE_BOOL_KEYS]
        values.append("PASS" if audit["machine_ok"] else "FAIL")
        lines.append("| " + " | ".join([METHOD_LABELS[method], *values]) + " |")
    lines.extend(["", "## Generated artifacts", ""])
    for method in METHOD_ORDER:
        if method == "webgen_agent":
            link = f"[{METHOD_LABELS[method]} source entry]({method}/source/index.html)"
        elif method == "algotutorgen_stage1":
            link = (
                f"[Open {METHOD_LABELS[method]} page]({method}/page.html)"
                f" · [Structured Stage1 JSON]({method}/artifact.json)"
            )
        else:
            link = f"[Open {METHOD_LABELS[method]} page]({method}/page.html)"
        lines.extend(
            [
                f"### {METHOD_LABELS[method]}",
                "",
                f"{link} · [Machine audit]({method}/audit.json)",
                "",
                f"![{case['id']} - {METHOD_LABELS[method]}]({method}/screenshot.png)",
                "",
            ]
        )
    return "\n".join(lines)


def _root_readme(manifest: dict[str, Any]) -> str:
    lines = [
        "# English Method Artifact Gallery: Stage1 and Stage2",
        "",
        "This directory contains English-only artifacts for the same fixed 23 cases and five comparison methods as the original gallery.",
        "AlgoTutorGen contributes both its Stage1 and Stage2 views, so the collection contains 138 saved artifact views in total.",
        "The Stage1 solution, trace, scenes, inputs, and expected answers are reused; only human-readable text is localized into English.",
        "",
        "## Methods and AlgoTutorGen stages",
        "",
        "| Method | Description | Saved artifact |",
        "| --- | --- | --- |",
    ]
    for method in METHOD_ORDER:
        if method == "webgen_agent":
            saved = "source project, screenshot, and audit"
        elif method == "algotutorgen_stage1":
            saved = "HTML page, structured build JSON, screenshot, and audit"
        else:
            saved = "HTML page, screenshot, and audit"
        lines.append(f"| {METHOD_LABELS[method]} | {METHOD_DESCRIPTIONS[method]} | {saved} |")
    lines.extend(
        [
            "",
            "## Case index",
            "",
            "| Family | Case | Stage1 | Stage2 | Direct HTML | WebGen-Agent | HTMLCure | BrowserRepair |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in manifest["cases"]:
        statuses = ["PASS" if case["methods"][method]["machine_ok"] else "FAIL" for method in METHOD_ORDER]
        lines.append(
            "| "
            + " | ".join(
                [case["family"], f"[{case['title']}](cases/{case['case_id']}/README.md)", *statuses]
            )
            + " |"
        )
    return "\n".join(lines)


def build_gallery(args: argparse.Namespace) -> dict[str, int]:
    cases = [row for row in (_load(args.cases).get("cases") or []) if isinstance(row, dict)]
    if len(cases) != 23 or len({row["id"] for row in cases}) != 23:
        raise ValueError("English case registry must contain exactly 23 unique cases")

    stage1 = _by_case(_rows(args.stage1_report))
    stage2 = _by_case(_rows(args.stage2_report))
    direct = _by_case(_rows(args.direct_report))
    htmlcure = _by_case(_rows(args.htmlcure_report))
    browser = _by_case(_rows(args.browser_report))
    stage1_audit = _audit_by_case(args.stage1_audit, condition=args.algolab_condition)
    main_direct_audit = _audit_by_case(args.main_audit, condition=args.direct_condition)
    webgen_audit = _by_case(_rows(args.webgen_audit))
    htmlcure_audit = _audit_by_case(args.htmlcure_audit, condition=args.htmlcure_condition)
    browser_audit = _audit_by_case(args.browser_audit, condition=args.browser_condition)

    if args.target.exists():
        shutil.rmtree(args.target)
    (args.target / "cases").mkdir(parents=True)
    manifest_cases: list[dict[str, Any]] = []

    for case in cases:
        case_id = str(case["id"])
        case_dir = args.target / "cases" / case_id
        _write_json(case_dir / "case.json", case)
        method_sources = {
            "algotutorgen_stage1": (
                _root_path(stage1[case_id]["html"]),
                stage1_audit[case_id],
                _root_path(stage1[case_id]["json"]),
            ),
            "algotutorgen_stage2": (
                _root_path(stage2[case_id]["html"]),
                stage1_audit[case_id],
                None,
            ),
            "direct_html": (_root_path(direct[case_id]["html"]), main_direct_audit[case_id], None),
            "htmlcure_strict": (_root_path(htmlcure[case_id]["html"]), htmlcure_audit[case_id], None),
            "browser_repair_1call": (_root_path(browser[case_id]["html"]), browser_audit[case_id], None),
        }
        audits: dict[str, dict[str, Any]] = {}
        method_manifest: dict[str, dict[str, Any]] = {}
        for method, (page_source, audit_row, artifact_source) in method_sources.items():
            method_dir = case_dir / method
            method_dir.mkdir(parents=True)
            page_source = _require_file(page_source, f"{method} page for {case_id}")
            screenshot_source = _require_file(
                args.screenshots / method / f"{case_id}.png",
                f"{method} screenshot for {case_id}",
            )
            shutil.copy2(page_source, method_dir / "page.html")
            shutil.copy2(screenshot_source, method_dir / "screenshot.png")
            if artifact_source is not None:
                artifact_source = _require_file(artifact_source, f"{method} structured artifact for {case_id}")
                shutil.copy2(artifact_source, method_dir / "artifact.json")
            metrics = _machine_payload(audit_row)
            checks_apply_to_saved_page = method != "algotutorgen_stage2"
            files = {"page": "page.html", "screenshot": "screenshot.png"}
            checksums = {
                "page_sha256": _sha256(method_dir / "page.html"),
                "screenshot_sha256": _sha256(method_dir / "screenshot.png"),
            }
            if artifact_source is not None:
                files["artifact"] = "artifact.json"
                checksums["artifact_sha256"] = _sha256(method_dir / "artifact.json")
            audit = {
                "schema_version": "english-method-artifact-v1",
                "condition": method,
                "condition_label": METHOD_LABELS[method],
                "case_id": case_id,
                "problem_title": case["title"],
                "family": case["family"],
                "language": "en",
                "machine_metrics": metrics,
                "machine_ok": all(metrics.values()),
                "machine_diagnostics": _machine_diagnostics(audit_row),
                "machine_checks_apply_to_saved_page": checks_apply_to_saved_page,
                "machine_evidence_source": (
                    "saved_page" if checks_apply_to_saved_page else "paired_algotutorgen_stage1"
                ),
                "files": files,
                "checksums": checksums,
            }
            _write_json(method_dir / "audit.json", audit)
            audits[method] = audit
            method_manifest[method] = {
                "machine_ok": audit["machine_ok"],
                "entry": f"cases/{case_id}/{method}/page.html",
                "screenshot": f"cases/{case_id}/{method}/screenshot.png",
                "audit": f"cases/{case_id}/{method}/audit.json",
            }
            if artifact_source is not None:
                method_manifest[method]["artifact"] = f"cases/{case_id}/{method}/artifact.json"

        web_method = "webgen_agent"
        web_dir = case_dir / web_method
        source_dir = args.webgen_workspace / case_id
        if not source_dir.is_dir():
            raise FileNotFoundError(f"WebGen source directory is missing: {source_dir}")
        shutil.copytree(source_dir, web_dir / "source", ignore=WEBGEN_IGNORE)
        _require_file(web_dir / "source/index.html", f"WebGen index for {case_id}")
        web_shot = _require_file(_root_path(webgen_audit[case_id].get("screenshot")), f"WebGen screenshot for {case_id}")
        shutil.copy2(web_shot, web_dir / "screenshot.png")
        metrics = _machine_payload(webgen_audit[case_id])
        web_audit_payload = {
            "schema_version": "english-method-artifact-v1",
            "condition": web_method,
            "condition_label": METHOD_LABELS[web_method],
            "case_id": case_id,
            "problem_title": case["title"],
            "family": case["family"],
            "language": "en",
            "machine_metrics": metrics,
            "machine_ok": all(metrics.values()),
            "machine_diagnostics": _machine_diagnostics(webgen_audit[case_id]),
            "files": {"source_entry": "source/index.html", "screenshot": "screenshot.png"},
            "checksums": {
                "source_entry_sha256": _sha256(web_dir / "source/index.html"),
                "screenshot_sha256": _sha256(web_dir / "screenshot.png"),
            },
        }
        _write_json(web_dir / "audit.json", web_audit_payload)
        audits[web_method] = web_audit_payload
        method_manifest[web_method] = {
            "machine_ok": web_audit_payload["machine_ok"],
            "entry": f"cases/{case_id}/{web_method}/source/index.html",
            "screenshot": f"cases/{case_id}/{web_method}/screenshot.png",
            "audit": f"cases/{case_id}/{web_method}/audit.json",
        }
        _write_text(case_dir / "README.md", _case_readme(case, audits))
        manifest_cases.append(
            {
                "case_id": case_id,
                "title": case["title"],
                "family": case["family"],
                "comparison": f"cases/{case_id}/README.md",
                "case_metadata": f"cases/{case_id}/case.json",
                "methods": {method: method_manifest[method] for method in METHOD_ORDER},
            }
        )

    manifest = {
        "schema_version": "english-method-artifact-gallery-v2",
        "language": "en",
        "selection_rule": "The same fixed 23 family-representative cases as the original five-method gallery, with both AlgoTutorGen Stage1 and Stage2 views retained.",
        "case_count": len(manifest_cases),
        "comparison_method_count": 5,
        "artifact_view_count": len(METHOD_ORDER),
        "method_order": list(METHOD_ORDER),
        "method_artifact_count": len(manifest_cases) * len(METHOD_ORDER),
        "cases": manifest_cases,
    }
    _write_json(args.target / "manifest.json", manifest)
    _write_text(args.target / "README.md", _root_readme(manifest))
    return validate_gallery(args.target)


def validate_gallery(target: Path) -> dict[str, int]:
    manifest = _load(target / "manifest.json")
    cases = manifest.get("cases") or []
    if len(cases) != 23:
        raise ValueError(f"expected 23 cases, found {len(cases)}")
    count = 0
    for case in cases:
        case_id = str(case["case_id"])
        for method in METHOD_ORDER:
            method_dir = target / "cases" / case_id / method
            _require_file(method_dir / "audit.json", f"{method} audit for {case_id}")
            _require_file(method_dir / "screenshot.png", f"{method} screenshot for {case_id}")
            if method == "webgen_agent":
                _require_file(method_dir / "source/index.html", f"WebGen source for {case_id}")
            else:
                _require_file(method_dir / "page.html", f"{method} page for {case_id}")
            if method == "algotutorgen_stage1":
                _require_file(method_dir / "artifact.json", f"Stage1 structured artifact for {case_id}")
            count += 1
    assert_english_only_tree(target)
    return {"case_count": len(cases), "method_artifact_count": count}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "benchmark/english_method_samples.json")
    parser.add_argument("--stage1-report", type=Path, required=True)
    parser.add_argument("--stage2-report", type=Path, required=True)
    parser.add_argument("--direct-report", type=Path, required=True)
    parser.add_argument("--stage1-audit", type=Path, required=True)
    parser.add_argument("--main-audit", type=Path, required=True)
    parser.add_argument("--webgen-workspace", type=Path, required=True)
    parser.add_argument("--webgen-audit", type=Path, required=True)
    parser.add_argument("--htmlcure-report", type=Path, required=True)
    parser.add_argument("--htmlcure-audit", type=Path, required=True)
    parser.add_argument("--browser-report", type=Path, required=True)
    parser.add_argument("--browser-audit", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--target", type=Path, default=ROOT / "artifacts/method_comparison_samples_en")
    parser.add_argument("--algolab-condition", default="algotutorgen_stage1")
    parser.add_argument("--direct-condition", default="direct_html")
    parser.add_argument("--htmlcure-condition", default="htmlcure_strict")
    parser.add_argument("--browser-condition", default="browser_repair_1call")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    for field in (
        "cases",
        "stage1_report",
        "stage2_report",
        "direct_report",
        "stage1_audit",
        "main_audit",
        "webgen_workspace",
        "webgen_audit",
        "htmlcure_report",
        "htmlcure_audit",
        "browser_report",
        "browser_audit",
        "screenshots",
        "target",
    ):
        value = getattr(args, field)
        setattr(args, field, value if value.is_absolute() else ROOT / value)
    return args


def main() -> int:
    args = parse_args()
    summary = validate_gallery(args.target) if args.validate_only else build_gallery(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
