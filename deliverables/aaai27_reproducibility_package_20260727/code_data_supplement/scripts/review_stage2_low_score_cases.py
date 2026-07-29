"""Playwright review for low-scored Stage2 creative-visual cases."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_CASES = (
    "dp_max_subarray_full_transfer",
    "lca",
    "stack_valid_parentheses_full_edge",
    "two_pointer_pair_sum",
)

KNOWN_ROOT_CAUSES = {
    "dp_max_subarray_full_transfer": (
        "renderCreativeStage searches .creative-stage-container after the shell has cleared the host; "
        "when it is missing the renderer creates an empty container and returns, so no SVG is rendered."
    ),
    "lca": (
        "inputTree.nodes is a list of node objects, but the stage script keys adj by those objects while "
        "edges use string ids; adj.get(u) is undefined and .push throws."
    ),
    "stack_valid_parentheses_full_edge": (
        "The renderer appends a DocumentFragment clone to the host and then queries the already-moved "
        "fragment; resultCorrect/resultIncorrect are null and .style access throws."
    ),
    "two_pointer_pair_sum": (
        "The SVG create(tag, attrs) helper ignores the third text argument used by every text element, "
        "so cards and pointer labels render without values."
    ),
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def repo_path(path: Path | str) -> str:
    path_obj = Path(path)
    if path_obj.is_absolute():
        try:
            return str(path_obj.relative_to(ROOT))
        except ValueError:
            return str(path_obj)
    return str(path_obj)


def host_path(value: Any) -> Path:
    text = str(value or "").strip()
    if text.startswith("/work/"):
        return ROOT / text[len("/work/") :]
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def compact_text(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def collect_records(report: dict[str, Any], cases: list[str]) -> dict[str, dict[str, Any]]:
    wanted = set(cases)
    records: dict[str, dict[str, Any]] = {}
    for row in report.get("records") or []:
        case_id = str(row.get("case_id") or "")
        if case_id in wanted:
            records[case_id] = dict(row)
    external = {
        str(row.get("case_id") or ""): dict(row)
        for row in report.get("external_visual_results") or []
        if str(row.get("case_id") or "") in wanted
    }
    for case_id, row in records.items():
        row["external_visual_review"] = external.get(case_id, {})
    return records


def frame_indices(total: int, limit: int | None) -> list[int]:
    if total <= 0:
        return [0]
    if limit is None or limit <= 0 or total <= limit:
        return list(range(total))
    raw = [0, 1, total // 2, total - 1]
    result: list[int] = []
    for index in raw:
        if 0 <= index < total and index not in result:
            result.append(index)
    cursor = 0
    while len(result) < limit and cursor < total:
        if cursor not in result:
            result.append(cursor)
        cursor += max(1, total // max(1, limit))
    return sorted(result[:limit])


def input_tokens_from_artifact(artifact: dict[str, Any]) -> list[str]:
    tokens: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, (int, float, str, bool)):
            text = str(value)
            if text and text not in tokens:
                tokens.append(text)

    visit(artifact.get("input_data") or artifact.get("input") or {})
    result = artifact.get("verifier_result", artifact.get("expected_result", artifact.get("result")))
    visit(result)
    return [token for token in tokens if token and len(token) <= 24]


def audit_one_case(
    browser: Any,
    case_id: str,
    row: dict[str, Any],
    output_dir: Path,
    wait_ms: int,
    max_screenshots_per_case: int,
    frame_limit: int | None,
) -> dict[str, Any]:
    html_path = host_path(row.get("html_repo_path") or row.get("html"))
    screenshot_dir = output_dir / "screenshots" / case_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page = browser.new_page(viewport={"width": 1365, "height": 900}, device_scale_factor=1)
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    result: dict[str, Any] = {
        "case_id": case_id,
        "html": str(html_path),
        "html_repo_path": repo_path(html_path),
        "page_load_ok": False,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "frame_reports": [],
        "screenshots": [],
        "external_scores": (row.get("external_visual_review") or {}).get("scores") or {},
        "external_weaknesses": (row.get("external_visual_review") or {}).get("weaknesses") or [],
        "likely_root_cause": KNOWN_ROOT_CAUSES.get(case_id, ""),
        "previous_machine_gate": {
            "creative_ok": bool(row.get("creative_ok")),
            "browser_smoke_ok": bool(row.get("browser_smoke_ok")),
            "strict_visual_quality_ok": bool(row.get("strict_visual_quality_ok")),
            "creative_quality_ok": bool(row.get("creative_quality_ok")),
            "stage_audited_frame_count": row.get("stage_audited_frame_count"),
            "final_gate_hard_failures": list(row.get("final_gate_hard_failures") or []),
            "final_gate_soft_failures": list(row.get("final_gate_soft_failures") or []),
        },
    }
    try:
        page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=30_000)
        page.wait_for_timeout(wait_ms)
        artifact = page.evaluate(GET_ARTIFACT_JS)
        tokens = input_tokens_from_artifact(artifact)
        total_frames = int(page.evaluate(FRAME_COUNT_JS) or 1)
        indices = frame_indices(total_frames, frame_limit)
        result["page_load_ok"] = True
        result["total_frames"] = total_frames
        result["checked_frames"] = indices
        result["input_tokens"] = tokens
        screenshot_count = 0
        for index in indices:
            metrics = page.evaluate(AUDIT_FRAME_JS, {"frameIndex": index, "tokens": tokens, "waitMs": wait_ms})
            result["frame_reports"].append(metrics)
            should_capture = bool(
                index in {0, total_frames - 1}
                or metrics.get("stage_error_present")
                or metrics.get("main_visual_blank")
                or metrics.get("input_token_coverage", 1) < 0.5
                or metrics.get("fallback_rendering")
            )
            if should_capture and screenshot_count < max_screenshots_per_case:
                screenshot_path = screenshot_dir / f"{case_id}_frame_{index:03d}.png"
                stage = page.locator("#creative-stage-host")
                try:
                    stage.screenshot(path=str(screenshot_path), timeout=10_000)
                except Exception:
                    page.screenshot(path=str(screenshot_path), full_page=False)
                metrics["screenshot"] = str(screenshot_path)
                metrics["screenshot_repo_path"] = repo_path(screenshot_path)
                result["screenshots"].append(
                    {
                        "frame_index": index,
                        "path": str(screenshot_path),
                        "repo_path": repo_path(screenshot_path),
                    }
                )
                screenshot_count += 1
    except Exception as exc:  # pragma: no cover - browser-only path
        result["failure_reason"] = f"{type(exc).__name__}: {exc}"
    finally:
        page.close()

    summarize_case(result)
    return result


def summarize_case(row: dict[str, Any]) -> None:
    frames = row.get("frame_reports") or []
    stage_error_frames = [item for item in frames if item.get("stage_error_present")]
    fallback_frames = [item for item in frames if item.get("fallback_rendering")]
    blank_frames = [item for item in frames if item.get("main_visual_blank")]
    low_token_frames = [item for item in frames if item.get("input_token_coverage", 1) < 0.5]
    empty_text_frames = [
        item
        for item in frames
        if item.get("non_background_shape_count", 0) > 0
        and item.get("stage_text_char_count", 0) == 0
        and item.get("expected_token_count", 0) > 0
    ]
    row["issue_flags"] = {
        "visible_stage_error": bool(stage_error_frames),
        "fallback_rendering": bool(fallback_frames),
        "main_visual_blank": bool(blank_frames),
        "input_value_mapping_missing": bool(low_token_frames or empty_text_frames),
    }
    row["problem_frame_indices"] = sorted(
        {
            int(item.get("frame_index", 0))
            for item in [*stage_error_frames, *fallback_frames, *blank_frames, *low_token_frames, *empty_text_frames]
        }
    )
    row["confirmed_issue"] = any(row["issue_flags"].values()) or bool(row.get("page_errors")) or bool(row.get("failure_reason"))
    row["playwright_conclusion"] = conclusion_for_case(row)


def conclusion_for_case(row: dict[str, Any]) -> str:
    flags = row.get("issue_flags") or {}
    case_id = row.get("case_id")
    if row.get("failure_reason"):
        return f"Playwright could not load or audit the page: {compact_text(row.get('failure_reason'))}"
    if flags.get("visible_stage_error"):
        messages = [
            compact_text(item.get("stage_error_text"))
            for item in row.get("frame_reports", [])
            if item.get("stage_error_present")
        ]
        detail = messages[0] if messages else "visible stage error"
        return f"Playwright confirmed visible Creative Stage runtime error: {detail}"
    if flags.get("main_visual_blank"):
        return "Playwright confirmed the Creative Stage host is effectively blank: no meaningful shapes or text are rendered."
    if flags.get("input_value_mapping_missing"):
        return "Playwright confirmed visual value mapping is missing or too weak: stage shapes render, but input/result tokens are absent from the stage text."
    if row.get("page_errors") or row.get("console_errors"):
        return "Playwright found browser console/page errors."
    return f"Playwright did not reproduce a hard browser issue for {case_id}; low VLM score is mostly subjective visual-quality feedback."


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    rows = payload["cases"]
    lines: list[str] = [
        "# Stage2 Low-score Case Playwright Review",
        "",
        f"- created_at: `{payload['created_at']}`",
        f"- source_report: `{payload['source_report']}`",
        f"- command: `{payload['command']}`",
        "",
        "## Summary",
        "",
        f"- reviewed cases: `{payload['summary']['total']}`",
        f"- Playwright-confirmed residual issues: `{payload['summary']['confirmed_issues']}`",
        f"- visible `.stage-error`: `{payload['summary']['visible_stage_error']}`",
        f"- blank main visual: `{payload['summary']['main_visual_blank']}`",
        f"- missing value mapping: `{payload['summary']['input_value_mapping_missing']}`",
        "",
        "说明：这些检查打开真实 HTML，逐帧读取 DOM，并保存问题帧截图；它们不是 VLM 二次打分。",
        "",
        "## Case Findings",
        "",
        "| Case | Playwright conclusion | Issue frames | Evidence |",
        "|---|---|---:|---|",
    ]
    for row in rows:
        evidence = ", ".join(f"`{item['repo_path']}`" for item in row.get("screenshots", [])[:3]) or ""
        lines.append(
            "| "
            + str(row.get("case_id"))
            + " | "
            + compact_text(row.get("playwright_conclusion"), 260).replace("|", "\\|")
            + " | "
            + str(row.get("problem_frame_indices") or [])
            + " | "
            + evidence.replace("|", "\\|")
            + " |"
        )
    lines.extend(["", "## Details", ""])
    for row in rows:
        flags = row.get("issue_flags") or {}
        lines.extend(
            [
                f"### {row.get('case_id')}",
                "",
                f"- HTML: `{row.get('html_repo_path')}`",
                f"- previous machine gate: `{json.dumps(row.get('previous_machine_gate') or {}, ensure_ascii=False)}`",
                f"- issue_flags: `{json.dumps(flags, ensure_ascii=False)}`",
                f"- conclusion: {row.get('playwright_conclusion')}",
            ]
        )
        if row.get("likely_root_cause"):
            lines.append(f"- likely_root_cause: {row.get('likely_root_cause')}")
        if row.get("external_weaknesses"):
            lines.append("- VLM weaknesses:")
            for weakness in row["external_weaknesses"]:
                lines.append(f"  - {weakness}")
        frame_reports = row.get("frame_reports") or []
        problem_frames = [item for item in frame_reports if int(item.get("frame_index", 0)) in set(row.get("problem_frame_indices") or [])]
        if problem_frames:
            lines.append("- Playwright frame evidence:")
            for item in problem_frames[:8]:
                lines.append(
                    "  - "
                    + f"frame `{item.get('frame_index')}`: "
                    + f"stage_error={item.get('stage_error_present')}, "
                    + f"fallback={item.get('fallback_rendering')}, "
                    + f"blank={item.get('main_visual_blank')}, "
                    + f"shapes={item.get('non_background_shape_count')}, "
                    + f"text_chars={item.get('stage_text_char_count')}, "
                    + f"token_coverage={item.get('input_token_coverage')}"
                )
                if item.get("stage_error_text"):
                    lines.append(f"    - stage_error_text: `{compact_text(item.get('stage_error_text'), 240)}`")
                if item.get("missing_input_tokens"):
                    lines.append(f"    - missing_input_tokens: `{item.get('missing_input_tokens')}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


GET_ARTIFACT_JS = r"""() => {
  try {
    return JSON.parse(document.getElementById('algolab-artifact')?.textContent || '{}');
  } catch (_) {
    return {};
  }
}"""


FRAME_COUNT_JS = r"""() => {
  try {
    if (window.algolabCreativeShell && typeof window.algolabCreativeShell.frames === 'function') {
      const frames = window.algolabCreativeShell.frames();
      if (Array.isArray(frames) && frames.length) return frames.length;
    }
    const artifact = JSON.parse(document.getElementById('algolab-artifact')?.textContent || '{}');
    const firstScene = Object.values(artifact.scenes || {})[0] || artifact.scene || {};
    return (artifact.frames || firstScene.frames || []).length || 1;
  } catch (_) {
    return 1;
  }
}"""


AUDIT_FRAME_JS = r"""async (opts) => {
  const options = opts || {};
  const targetFrame = Number(options.frameIndex || 0);
  const waitMs = Math.max(0, Number(options.waitMs || 0));
  const tokens = Array.isArray(options.tokens) ? options.tokens.map(String).filter(Boolean) : [];
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const nextPaint = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  function go(index) {
    if (window.algolabCreativeShell && typeof window.algolabCreativeShell.go === 'function') {
      window.algolabCreativeShell.go(index);
      return true;
    }
    const range = document.querySelector('#range');
    if (range) {
      range.value = String(index);
      range.dispatchEvent(new Event('input', { bubbles: true }));
      range.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }
    return false;
  }
  function visible(node) {
    if (!node || !(node instanceof Element)) return false;
    const style = getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity || 1) < 0.05) return false;
    const rect = node.getBoundingClientRect();
    return rect.width > 2 && rect.height > 2;
  }
  function rectOf(node) {
    const rect = node.getBoundingClientRect();
    return {
      x: Math.round(rect.x * 10) / 10,
      y: Math.round(rect.y * 10) / 10,
      width: Math.round(rect.width * 10) / 10,
      height: Math.round(rect.height * 10) / 10,
    };
  }
  function isBackgroundShape(node, hostRect) {
    const tag = String(node.tagName || '').toLowerCase();
    if (tag !== 'rect') return false;
    const rect = node.getBoundingClientRect();
    const areaRatio = (rect.width * rect.height) / Math.max(1, hostRect.width * hostRect.height);
    const fill = String(node.getAttribute('fill') || getComputedStyle(node).fill || '').toLowerCase();
    return areaRatio > 0.55 && /#fff|white|#f7|#f8|#f9|rgb\(24[0-9]|rgb\(25[0-5]/.test(fill);
  }
  function textOf(node) {
    return String(node && (node.innerText || node.textContent) || '').replace(/\s+/g, ' ').trim();
  }
  go(targetFrame);
  await nextPaint();
  if (waitMs) await sleep(waitMs);
  await nextPaint();

  const host = document.querySelector('#creative-stage-host');
  const hostRect = host ? host.getBoundingClientRect() : { width: 0, height: 0 };
  const stageText = textOf(host);
  const stageErrors = host ? Array.from(host.querySelectorAll('.stage-error')).filter(visible).map(textOf) : [];
  const shapes = host ? Array.from(host.querySelectorAll('svg rect,svg circle,svg ellipse,svg path,svg polygon,svg line,svg polyline')).filter(visible) : [];
  const nonBackgroundShapes = shapes.filter(node => !isBackgroundShape(node, hostRect));
  const svgTexts = host ? Array.from(host.querySelectorAll('svg text, [data-layout-role="label"], .label, .value-label, .pointer-label, .caption')) : [];
  const nonEmptySvgTexts = svgTexts.map(textOf).filter(Boolean);
  const semanticNodes = host ? Array.from(host.querySelectorAll('[data-scenario-role],[data-visual],[data-derived-visual-only],[data-layout-role]')).filter(visible) : [];
  const expected = tokens.filter(token => token && !['true', 'false'].includes(token.toLowerCase()));
  const foundTokens = expected.filter(token => stageText.includes(token));
  const missingTokens = expected.filter(token => !stageText.includes(token));
  const tokenCoverage = expected.length ? foundTokens.length / expected.length : 1;
  const mainVisualBlank = Boolean(
    host
    && !stageErrors.length
    && nonBackgroundShapes.length === 0
    && semanticNodes.length === 0
    && stageText.length < 8
  );
  return {
    frame_index: targetFrame,
    counter_text: textOf(document.querySelector('#counter')),
    host_visible: Boolean(host && visible(host)),
    host_box: host ? rectOf(host) : null,
    host_child_count: host ? host.childElementCount : 0,
    rendered_mode: host ? String(host.dataset.stageRendered || '') : '',
    fallback_rendering: Boolean(host && host.dataset.stageRendered === 'fallback'),
    stage_error_present: stageErrors.length > 0,
    stage_error_text: stageErrors.join(' | '),
    stage_text_char_count: stageText.length,
    stage_text_excerpt: stageText.slice(0, 240),
    shape_count: shapes.length,
    non_background_shape_count: nonBackgroundShapes.length,
    semantic_node_count: semanticNodes.length,
    svg_text_node_count: svgTexts.length,
    non_empty_svg_text_count: nonEmptySvgTexts.length,
    expected_token_count: expected.length,
    found_input_tokens: foundTokens,
    missing_input_tokens: missingTokens,
    input_token_coverage: Math.round(tokenCoverage * 1000) / 1000,
    main_visual_blank: mainVisualBlank,
  };
}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "output/experiments/algotutorgen_full_200_20260706/stage2_eval/stage2_visual_eval_report.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output/experiments/algotutorgen_full_200_20260706/stage2_eval/playwright_low_score_review",
    )
    parser.add_argument("--case", action="append", dest="cases", default=[])
    parser.add_argument("--wait-ms", type=int, default=350)
    parser.add_argument("--max-screenshots-per-case", type=int, default=8)
    parser.add_argument(
        "--frame-limit",
        type=int,
        default=0,
        help="Limit checked frames per case. 0 means all frames.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_path = args.report.resolve()
    output_dir = args.output_dir.resolve()
    cases = args.cases or list(DEFAULT_CASES)
    report = load_json(report_path)
    records = collect_records(report, cases)
    missing = [case_id for case_id in cases if case_id not in records]
    if missing:
        raise SystemExit(f"missing cases in report: {', '.join(missing)}")

    from playwright.sync_api import sync_playwright

    rows: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for case_id in cases:
                rows.append(
                    audit_one_case(
                        browser,
                        case_id,
                        records[case_id],
                        output_dir,
                        args.wait_ms,
                        args.max_screenshots_per_case,
                        None if args.frame_limit <= 0 else args.frame_limit,
                    )
                )
        finally:
            browser.close()

    summary = {
        "total": len(rows),
        "confirmed_issues": sum(1 for row in rows if row.get("confirmed_issue")),
        "visible_stage_error": sum(1 for row in rows if (row.get("issue_flags") or {}).get("visible_stage_error")),
        "fallback_rendering": sum(1 for row in rows if (row.get("issue_flags") or {}).get("fallback_rendering")),
        "main_visual_blank": sum(1 for row in rows if (row.get("issue_flags") or {}).get("main_visual_blank")),
        "input_value_mapping_missing": sum(
            1 for row in rows if (row.get("issue_flags") or {}).get("input_value_mapping_missing")
        ),
    }
    payload = {
        "schema_version": "stage2-low-score-playwright-review-v1",
        "created_at": now_iso(),
        "source_report": repo_path(report_path),
        "command": " ".join(sys.argv),
        "summary": summary,
        "cases": rows,
    }
    json_path = output_dir / "stage2_low_score_playwright_review.json"
    md_path = output_dir / "stage2_low_score_playwright_review.md"
    write_json(json_path, payload)
    write_markdown(md_path, payload)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
