"""Fetch LeetCode China problem metadata for local benchmark alignment.

By default this script does not persist the official problem statement body.
Use --include-official-content only for private local experiments where a
verbatim cache is acceptable.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


LEETCODE_CN_GRAPHQL = "https://leetcode.cn/graphql/"
QUESTION_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    translatedTitle
    title
    titleSlug
    difficulty
    translatedContent
    topicTags { name slug translatedName }
  }
}
"""


class PlainTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "pre", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "pre", "li", "ul", "ol"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)

    def text(self) -> str:
        text = html.unescape("".join(self.parts))
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)


def strip_html(value: str) -> str:
    parser = PlainTextHTMLParser()
    parser.feed(value or "")
    return parser.text()


def extract_image_urls(value: str) -> list[str]:
    urls = re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", value or "", flags=re.IGNORECASE)
    return sorted(set(html.unescape(url) for url in urls))


def fetch_question(slug: str) -> dict[str, Any]:
    payload = json.dumps({"query": QUESTION_QUERY, "variables": {"titleSlug": slug}}).encode("utf-8")
    request = urllib.request.Request(
        LEETCODE_CN_GRAPHQL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 AlgoLab benchmark alignment probe",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to fetch {slug}: {exc}") from exc
    data = json.loads(raw)
    errors = data.get("errors")
    if errors:
        raise RuntimeError(f"leetcode graphql errors for {slug}: {errors}")
    question = (data.get("data") or {}).get("question")
    if not question:
        raise RuntimeError(f"leetcode question not found: {slug}")
    return question


def record_for_question(question: dict[str, Any], *, include_official_content: bool) -> dict[str, Any]:
    content_html = str(question.get("translatedContent") or "")
    content_text = strip_html(content_html)
    record: dict[str, Any] = {
        "source": "leetcode.cn",
        "url": f"https://leetcode.cn/problems/{question.get('titleSlug')}/description/",
        "questionFrontendId": question.get("questionFrontendId"),
        "title": question.get("title"),
        "translatedTitle": question.get("translatedTitle"),
        "titleSlug": question.get("titleSlug"),
        "difficulty": question.get("difficulty"),
        "topicTags": question.get("topicTags") or [],
        "image_urls": extract_image_urls(content_html),
        "official_content_available": bool(content_html),
        "official_content_html_sha256": hashlib.sha256(content_html.encode("utf-8")).hexdigest() if content_html else "",
        "official_content_text_chars": len(content_text),
        "official_content_text_preview": content_text[:180],
        "copyright_note": (
            "Official problem text is copyrighted by LeetCode/力扣. "
            "Use this metadata for alignment; prefer local paraphrased descriptions in benchmark source."
        ),
    }
    if include_official_content:
        record["official_content_html"] = content_html
        record["official_content_text"] = content_text
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", action="append", required=True, help="LeetCode titleSlug; repeatable")
    parser.add_argument("--output-dir", type=Path, default=Path("output/leetcode_problem_descriptions"))
    parser.add_argument(
        "--include-official-content",
        action="store_true",
        help="Persist official HTML/plain text in output JSON. Default stores only metadata, hash, and short preview.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for slug in args.slug:
        question = fetch_question(slug)
        record = record_for_question(question, include_official_content=bool(args.include_official_content))
        path = args.output_dir / f"{slug}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(
            {
                "slug": slug,
                "id": record.get("questionFrontendId"),
                "title": record.get("translatedTitle") or record.get("title"),
                "difficulty": record.get("difficulty"),
                "text_chars": record.get("official_content_text_chars"),
                "images": len(record.get("image_urls") or []),
                "path": str(path),
            }
        )
        print(f"fetched {slug}: {record.get('questionFrontendId')} {record.get('translatedTitle')}")
    summary = {
        "source": "leetcode.cn",
        "include_official_content": bool(args.include_official_content),
        "count": len(rows),
        "rows": rows,
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
