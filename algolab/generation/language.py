"""Shared output-language requirements for generated learning artifacts."""

from __future__ import annotations

import re
from typing import Any


CJK_RE = re.compile(r"[\u3400-\u9fff]")
SUPPORTED_OUTPUT_LANGUAGES = ("zh", "en")


def normalize_output_language(value: str | None) -> str:
    language = str(value or "zh").strip().lower()
    if language not in SUPPORTED_OUTPUT_LANGUAGES:
        raise ValueError(f"unsupported output language: {value!r}")
    return language


def english_output_requirement() -> str:
    return (
        "English only. Every user-facing string must be written in natural English, including the user interface, "
        "titles, explanations, checkpoint prompts, correct and incorrect feedback, hints, revealed answers, "
        "learning log entries, timeline labels, accessibility labels, and code comments. Do not emit Chinese or "
        "other CJK characters anywhere in HTML, CSS, JavaScript, JSON, Markdown, or source-code text."
    )


def output_language_requirement(language: str | None) -> str:
    return english_output_requirement() if normalize_output_language(language) == "en" else ""


def contains_cjk(value: Any) -> bool:
    return CJK_RE.search(str(value or "")) is not None


def english_only_errors(value: Any, *, label: str = "artifact") -> list[str]:
    if not contains_cjk(value):
        return []
    match = CJK_RE.search(str(value or ""))
    excerpt = str(value or "")[max(0, match.start() - 24) : match.start() + 48] if match else ""
    return [f"english_only_violation: {label} contains CJK text near {excerpt!r}"]


def scrub_cjk_strings(value: Any) -> Any:
    """Remove residual non-English diagnostics from a verified runtime payload.

    Generated teaching content is expected to be English already. This final
    boundary mainly handles internal validator messages that are not part of
    the learner-facing contract but would otherwise leak into embedded JSON.
    """

    if isinstance(value, dict):
        return {str(key): scrub_cjk_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_cjk_strings(item) for item in value]
    if isinstance(value, tuple):
        return [scrub_cjk_strings(item) for item in value]
    if isinstance(value, str) and contains_cjk(value):
        return "Internal non-English diagnostic omitted."
    return value
