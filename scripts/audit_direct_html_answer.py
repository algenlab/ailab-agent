"""Audit answer correctness for direct-HTML baseline artifacts."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.runtime.executor import canonical


ANSWER_LABEL_RE = re.compile(
    r"(最终\s*(?:答案|输出|结果)|最终[^。；;\n]{0,24}(?:为|是|得到)|成功找到答案|答案|输出|结果|返回|final\s+answer|answer|result)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class AnswerCandidate:
    value: Any
    raw: str
    method: str
    confidence: str
    position: int


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_stack: list[str] = []
        self._script_depth = 0
        self.parts: list[str] = []
        self.script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "style":
            self._skip_stack.append(tag.lower())
        if tag.lower() == "script":
            self._script_depth += 1
        if tag.lower() in {"br", "p", "div", "section", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")
        for name, value in attrs:
            if name.lower() in {"id", "class", "aria-label"} and value and ANSWER_LABEL_RE.search(value):
                self.parts.append(f"\n{value}: ")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack and tag.lower() == self._skip_stack[-1]:
            self._skip_stack.pop()
        if tag.lower() == "script" and self._script_depth:
            self._script_depth -= 1
        if tag.lower() in {"p", "div", "section", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._script_depth:
            self.script_parts.append(data)
            return
        if self._skip_stack:
            return
        if data.strip():
            self.parts.append(data)


def _js_string_literals(script: str) -> list[str]:
    strings: list[str] = []
    index = 0
    while index < len(script):
        quote = script[index]
        if quote not in {"'", '"', "`"}:
            index += 1
            continue
        start = index
        index += 1
        escaped = False
        body: list[str] = []
        while index < len(script):
            ch = script[index]
            if escaped:
                body.append("\\" + ch)
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                raw_body = "".join(body)
                if quote == "`":
                    value = re.sub(r"\$\{[^}]*\}", " ", raw_body)
                    value = value.replace("\\n", "\n").replace("\\t", "\t")
                else:
                    try:
                        value = ast.literal_eval(script[start : index + 1])
                    except (SyntaxError, ValueError):
                        value = raw_body
                if isinstance(value, str) and value.strip():
                    strings.append(value)
                break
            else:
                body.append(ch)
            index += 1
        index += 1
    return strings


def html_to_searchable_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html or "")
    script_text = "\n".join(_js_string_literals("\n".join(parser.script_parts)))
    text = unescape(" ".join(parser.parts) + "\n" + script_text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def _balanced_literal(text: str, start: int) -> tuple[str, int] | None:
    opener = text[start]
    closer = {"[": "]", "{": "}"}[opener]
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in {"'", '"'}:
            quote = ch
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : index + 1], index + 1
    return None


def _loads_literal(raw: str) -> Any:
    cleaned = raw.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    return ast.literal_eval(cleaned)


def _candidate_values(context: str, *, offset: int, expected: Any) -> list[AnswerCandidate]:
    candidates: list[AnswerCandidate] = []
    masked = list(context)
    for index, ch in enumerate(context):
        if ch not in "[{":
            continue
        literal = _balanced_literal(context, index)
        if not literal:
            continue
        raw, end = literal
        before = context[index - 1] if index > 0 else ""
        after = context[end] if end < len(context) else ""
        if re.match(r"[\w.]", before or "") or re.match(r"[\w.]", after or ""):
            continue
        try:
            value = _loads_literal(raw)
        except (SyntaxError, ValueError, TypeError):
            continue
        candidates.append(
            AnswerCandidate(value=value, raw=raw, method="label_literal", confidence="high", position=offset + index)
        )
        for pos in range(index, end):
            masked[pos] = " "

    fallback_context = "".join(masked)
    for match in re.finditer(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])", fallback_context):
        raw = match.group(0)
        before = fallback_context[: match.start()].rstrip()[-1:]
        after = fallback_context[match.end() :].lstrip()[:1]
        if before in {"+", "-", "*", "/", "<"} or after in {"+", "-", "*", "/", "=", ">"}:
            continue
        value: Any = float(raw) if "." in raw else int(raw)
        candidates.append(
            AnswerCandidate(value=value, raw=raw, method="label_number", confidence="high", position=offset + match.start())
        )

    for match in re.finditer(r"\b(true|false|True|False)\b|(?<![\w])(是|否)(?![\w])", fallback_context):
        raw = match.group(0)
        value = raw.lower() == "true" or raw == "是"
        candidates.append(
            AnswerCandidate(value=value, raw=raw, method="label_bool", confidence="high", position=offset + match.start())
        )

    if isinstance(expected, str):
        for match in re.finditer(r"['\"]([^'\"]+)['\"]", fallback_context):
            candidates.append(
                AnswerCandidate(
                    value=match.group(1),
                    raw=match.group(0),
                    method="label_quoted_string",
                    confidence="medium",
                    position=offset + match.start(),
                )
            )
    return candidates


def extract_answer_candidates(html: str, expected: Any) -> list[AnswerCandidate]:
    text = html_to_searchable_text(html)
    candidates: list[AnswerCandidate] = []
    for match in ANSWER_LABEL_RE.finditer(text):
        raw_label = match.group(0)
        if raw_label.isascii():
            before = text[max(0, match.start() - 1) : match.start()]
            after = text[match.end() : match.end() + 1]
            if re.match(r"[\w.-]", before or "") or re.match(r"[\w.-]", after or ""):
                continue
        context = text[match.end() : match.end() + 420]
        context = re.sub(r"^\s*(?:JSON|json)?\s*(?:是|为|=|:|：|->|=>|，|,|。|\s)+", "", context)
        candidates.extend(_candidate_values(context, offset=match.end(), expected=expected))
    candidates.sort(key=lambda item: item.position)
    deduped: list[AnswerCandidate] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = (item.raw, canonical(item.value))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def audit_html_answer(html: str, expected: Any) -> dict[str, Any]:
    candidates = extract_answer_candidates(html, expected)
    if not candidates:
        return {
            "status": "answer_missing",
            "expected": expected,
            "extracted_answer": None,
            "raw_answer": "",
            "extraction_method": "",
            "extraction_confidence": "none",
        }

    expected_key = canonical(expected)
    for candidate in reversed(candidates):
        if canonical(candidate.value) == expected_key:
            return {
                "status": "answer_match",
                "expected": expected,
                "extracted_answer": candidate.value,
                "raw_answer": candidate.raw,
                "extraction_method": candidate.method,
                "extraction_confidence": candidate.confidence,
            }

    candidate = candidates[-1]
    return {
        "status": "answer_mismatch",
        "expected": expected,
        "extracted_answer": candidate.value,
        "raw_answer": candidate.raw,
        "extraction_method": candidate.method,
        "extraction_confidence": candidate.confidence,
    }


def _resolve_html_path(path_value: str, *, report_path: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path.exists():
        return path
    candidate = report_path.parent / path
    if candidate.exists():
        return candidate
    return ROOT / path


def _expected_visible_to_model(report: dict[str, Any], override: bool | None) -> bool | None:
    if override is not None:
        return override
    config = report.get("config") or {}
    if "expected_visible_to_model" in config:
        return bool(config["expected_visible_to_model"])
    condition = str(config.get("benchmark_condition") or "")
    baseline = str(config.get("baseline") or "")
    if condition == "direct_html_baseline" or baseline == "direct_html_baseline":
        return True
    if "no_expected" in condition or "no_expected" in baseline:
        return False
    return None


def audit_report(report_path: Path, *, expected_visible_to_model: bool | None = None) -> dict[str, Any]:
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    results = list(report.get("results") or [])
    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for item in results:
        if not item.get("ok") or not item.get("html"):
            continue
        html_path = _resolve_html_path(str(item["html"]), report_path=report_path)
        if not html_path.exists():
            row = {
                "case_id": item.get("case_id"),
                "sample_index": item.get("sample_index"),
                "status": "html_missing",
                "html": str(html_path),
                "expected": item.get("expected"),
                "extracted_answer": None,
                "raw_answer": "",
                "extraction_method": "",
                "extraction_confidence": "none",
            }
        else:
            audit = audit_html_answer(html_path.read_text(encoding="utf-8"), item.get("expected"))
            row = {
                "case_id": item.get("case_id"),
                "sample_index": item.get("sample_index"),
                "family": item.get("family"),
                "title": item.get("title"),
                "html": str(html_path),
                **audit,
            }
        status_counts[str(row["status"])] += 1
        rows.append(row)

    audited_html = len(rows)
    match_count = status_counts.get("answer_match", 0)
    found_count = audited_html - status_counts.get("answer_missing", 0) - status_counts.get("html_missing", 0)
    visible = _expected_visible_to_model(report, expected_visible_to_model)
    return {
        "kind": "direct_html_answer_audit",
        "source_report": str(report_path),
        "condition": (report.get("config") or {}).get("benchmark_condition"),
        "expected_visible_to_model": visible,
        "prompt_leakage_note": (
            "旧 direct_html_baseline prompt 暴露 expected；该审计只能说明页面是否展示了 expected 一致答案。"
            if visible is True
            else "该条件未向模型暴露 expected，可作为 direct_html baseline answer correctness 口径。"
            if visible is False
            else "无法从 report 判断模型是否可见 expected。"
        ),
        "total_results": len(results),
        "browser_passed": sum(1 for item in results if item.get("ok")),
        "audited_html": audited_html,
        "status_counts": dict(status_counts),
        "visible_answer_found_rate": found_count / audited_html if audited_html else 0.0,
        "visible_answer_match_rate": match_count / audited_html if audited_html else 0.0,
        "rows": rows,
    }


def write_audit_outputs(summary: dict[str, Any], output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "direct_html_answer_audit.json"
    md_path = output_dir / "direct_html_answer_audit.md"
    csv_path = output_dir / "direct_html_answer_audit.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = list(summary.get("rows") or [])
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "case_id",
                "sample_index",
                "family",
                "status",
                "expected",
                "extracted_answer",
                "raw_answer",
                "extraction_method",
                "extraction_confidence",
                "html",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if key in {"expected", "extracted_answer"} else row.get(key, "") for key in writer.fieldnames})

    status_counts = summary.get("status_counts") or {}
    lines = [
        "# Direct HTML Answer Audit",
        "",
        f"- source_report: `{summary.get('source_report')}`",
        f"- condition: `{summary.get('condition')}`",
        f"- expected_visible_to_model: `{summary.get('expected_visible_to_model')}`",
        f"- total_results: {summary.get('total_results')}",
        f"- browser_passed: {summary.get('browser_passed')}",
        f"- audited_html: {summary.get('audited_html')}",
        f"- visible_answer_found_rate: {summary.get('visible_answer_found_rate'):.4f}",
        f"- visible_answer_match_rate: {summary.get('visible_answer_match_rate'):.4f}",
        f"- status_counts: `{json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}`",
        "",
        summary.get("prompt_leakage_note") or "",
        "",
        "## Non-Matches",
        "",
        "| case_id | sample | status | expected | extracted |",
        "|---|---:|---|---|---|",
    ]
    for row in rows:
        if row.get("status") == "answer_match":
            continue
        lines.append(
            "| {case_id} | {sample_index} | {status} | `{expected}` | `{extracted}` |".format(
                case_id=row.get("case_id"),
                sample_index=row.get("sample_index"),
                status=row.get("status"),
                expected=json.dumps(row.get("expected"), ensure_ascii=False),
                extracted=json.dumps(row.get("extracted_answer"), ensure_ascii=False),
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit direct HTML baseline visible answer correctness")
    parser.add_argument("--report", type=Path, required=True, help="llm_benchmark_report.json for direct HTML baseline")
    parser.add_argument("--output-dir", type=Path, default=None, help="目录；默认写到 report 同目录")
    parser.add_argument(
        "--expected-visible-to-model",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖 report 推断出的 expected 是否暴露给模型",
    )
    args = parser.parse_args()
    summary = audit_report(args.report, expected_visible_to_model=args.expected_visible_to_model)
    output_dir = args.output_dir or args.report.parent
    json_path, md_path, csv_path = write_audit_outputs(summary, output_dir)
    print(
        "direct_html_answer_audit: "
        f"audited={summary['audited_html']} "
        f"match_rate={summary['visible_answer_match_rate']:.4f} "
        f"found_rate={summary['visible_answer_found_rate']:.4f} "
        f"expected_visible_to_model={summary['expected_visible_to_model']}"
    )
    print(f"json: {json_path}")
    print(f"md: {md_path}")
    print(f"csv: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
