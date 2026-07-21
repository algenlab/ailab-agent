"""Create English-only Stage1 artifacts from existing verified Stage1 output.

The algorithm solutions, traces, scenes, and expected answers are reused. Only
human-readable strings are translated, after which the deterministic Stage1
renderer is run again and its fixed UI strings are localized.
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import re
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CJK_RE = re.compile(r"[\u3400-\u9fff]")
CJK_RUN_RE = re.compile(r"[\u3400-\u9fff]+")
PROTECTED_TOKEN_RE = re.compile(
    r"\$\{[^{}\n]+\}|O\([^()\n]+\)|[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]\n]+\]|\.[A-Za-z_][A-Za-z0-9_]*)|[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+"
)
PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "，": ", ",
        "。": ".",
        "：": ": ",
        "；": "; ",
        "？": "?",
        "！": "!",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "、": ", ",
        "…": "...",
        "—": "-",
        "→": "->",
    }
)
TRANSLATION_SYSTEM_PROMPT = """You translate generated algorithm-learning artifacts from Simplified Chinese to English.
Return one JSON object with exactly one field named translations. Its value must be a list of English strings in the
same order and with the same length as the input strings. Translate all human-readable Chinese into concise, natural
English. Preserve identifiers, numbers, formulas, JSON fragments, HTML fragments, Python/JavaScript syntax, escaped
characters, line breaks, and placeholders such as ${name}. If a string contains source code, change only Chinese
comments or Chinese string-message content and do not alter executable syntax. Never emit Chinese or any other CJK
character. Return JSON only, without Markdown or explanation."""
CRITICAL_RENDERER_TRANSLATIONS = {
    "上一步": "Previous",
    "下一步": "Next",
    "播放": "Play",
    "暂停": "Pause",
    "提交": "Submit",
    "提示": "Hint",
    "查看提示": "View hint",
    "查看答案": "Show answer",
    "显示答案": "Show answer",
    "正确": "Correct",
    "错误": "Incorrect",
    "错误选项解释": "Incorrect option explanation",
    "学习日志": "Learning log",
    "学习记录": "Learning record",
    "讲解": "Explanation",
    "交互": "Interaction",
    "当前状态": "Current state",
    "当前输出": "Current output",
    "当前解法": "Current solution",
    "学习目标": "Learning objectives",
    "代码": "Code",
    "解法": "Solution",
    "解法对比": "Solution comparison",
    "最终输出": "Final output",
    "答案": "Answer",
}
_CACHE_LOCK = threading.Lock()


def apply_translation_map(value: Any, translations: dict[str, str]) -> Any:
    """Return a structure-preserving copy with exact string translations applied."""

    if isinstance(value, dict):
        localized: dict[Any, Any] = {}
        for key, item in value.items():
            localized_key = translations.get(key, key) if isinstance(key, str) else key
            if localized_key in localized:
                raise ValueError(f"translation creates a duplicate mapping key: {localized_key!r}")
            localized[localized_key] = apply_translation_map(item, translations)
        return localized
    if isinstance(value, list):
        return [apply_translation_map(item, translations) for item in value]
    if isinstance(value, tuple):
        return [apply_translation_map(item, translations) for item in value]
    if isinstance(value, str):
        return translations.get(value, value)
    return value


def collect_cjk_strings(value: Any) -> list[str]:
    """Collect unique CJK-bearing string values in deterministic order."""

    found: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if isinstance(key, str) and CJK_RE.search(key):
                    found.add(key)
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
        elif isinstance(item, str) and CJK_RE.search(item):
            found.add(item)

    visit(value)
    return sorted(found)


def localize_renderer_text(text: str, translations: dict[str, str]) -> str:
    """Translate fixed renderer CJK runs while leaving HTML/JS structure intact."""

    localized = CJK_RUN_RE.sub(lambda match: translations.get(match.group(0), match.group(0)), text)
    return localized.translate(PUNCTUATION_TRANSLATION)


def translation_map_from_response(sources: list[str], payload: Any) -> dict[str, str]:
    """Validate a model response and pair translations with their source strings."""

    if not isinstance(payload, dict) or not isinstance(payload.get("translations"), list):
        raise ValueError("translation response must contain a translations list")
    translated = payload["translations"]
    if len(translated) != len(sources):
        raise ValueError(f"translation count mismatch: expected {len(sources)}, found {len(translated)}")
    mapping: dict[str, str] = {}
    for source, target in zip(sources, translated):
        text = str(target or "").strip()
        if not text:
            raise ValueError(f"empty translation for {source!r}")
        if CJK_RE.search(text):
            raise ValueError(f"translation still contains CJK for {source!r}: {text!r}")
        mapping[source] = text
    return mapping


def _assert_localized_string(source: str, localized: Any, *, path: str) -> None:
    if not isinstance(localized, str):
        raise ValueError(f"localized value changes string type at {path}")
    if not localized.strip():
        raise ValueError(f"localized value is empty at {path}")
    if CJK_RE.search(localized):
        raise ValueError(f"localized value still contains CJK at {path}")
    source_tokens = set(PROTECTED_TOKEN_RE.findall(source))
    localized_tokens = set(PROTECTED_TOKEN_RE.findall(localized))
    missing = source_tokens - localized_tokens
    if missing:
        raise ValueError(f"localized value drops protected token(s) at {path}: {sorted(missing)}")


def _assert_structure_preserved(source: Any, localized: Any, *, path: str) -> None:
    if type(source) is not type(localized):
        raise ValueError(
            f"localization changes value type at {path}: {type(source).__name__} -> {type(localized).__name__}"
        )
    if isinstance(source, dict):
        if len(source) != len(localized):
            raise ValueError(f"localization changes mapping size at {path}")
        for index, ((source_key, source_value), (localized_key, localized_value)) in enumerate(
            zip(source.items(), localized.items())
        ):
            _assert_structure_preserved(source_key, localized_key, path=f"{path}.<key:{index}>")
            _assert_structure_preserved(source_value, localized_value, path=f"{path}.{localized_key}")
        return
    if isinstance(source, list):
        if len(source) != len(localized):
            raise ValueError(f"localization changes list length at {path}")
        for index, (source_item, localized_item) in enumerate(zip(source, localized)):
            _assert_structure_preserved(source_item, localized_item, path=f"{path}[{index}]")
        return
    if isinstance(source, str):
        if CJK_RE.search(source):
            _assert_localized_string(source, localized, path=path)
        elif localized != source:
            raise ValueError(f"localization changes non-CJK string at {path}: {source!r} -> {localized!r}")
        return
    if localized != source:
        raise ValueError(f"localization changes semantic value at {path}: {source!r} -> {localized!r}")


def _assert_ast_preserved(source: Any, localized: Any, *, path: str) -> None:
    if type(source) is not type(localized):
        raise ValueError(f"localized Python semantics change node type at {path}")
    if isinstance(source, ast.AST):
        for field in source._fields:
            _assert_ast_preserved(
                getattr(source, field),
                getattr(localized, field),
                path=f"{path}.{field}",
            )
        return
    if isinstance(source, list):
        if len(source) != len(localized):
            raise ValueError(f"localized Python semantics change list length at {path}")
        for index, (source_item, localized_item) in enumerate(zip(source, localized)):
            _assert_ast_preserved(source_item, localized_item, path=f"{path}[{index}]")
        return
    if isinstance(source, str) and CJK_RE.search(source):
        _assert_localized_string(source, localized, path=path)
        return
    if localized != source:
        raise ValueError(f"localized Python semantics change value at {path}: {source!r} -> {localized!r}")


def _assert_python_semantics(source: str, localized: str, *, path: str) -> None:
    try:
        source_tree = ast.parse(source)
        localized_tree = ast.parse(localized)
    except SyntaxError as exc:
        raise ValueError(f"localized Python semantics are not parseable at {path}: {exc}") from exc
    _assert_ast_preserved(source_tree, localized_tree, path=path)


def assert_localization_preserves_semantics(source: Any, localized: Any) -> None:
    """Reject localized artifacts that change structure, machine values, or Python logic."""

    _assert_structure_preserved(source, localized, path="artifact")
    if not isinstance(source, dict) or not isinstance(localized, dict):
        return
    source_variants = source.get("variants") or []
    localized_variants = localized.get("variants") or []
    for index, (source_variant, localized_variant) in enumerate(zip(source_variants, localized_variants)):
        if not isinstance(source_variant, dict) or not isinstance(localized_variant, dict):
            continue
        for field in ("code", "tracker_code"):
            source_code = source_variant.get(field)
            localized_code = localized_variant.get(field)
            if isinstance(source_code, str) and isinstance(localized_code, str):
                _assert_python_semantics(
                    source_code,
                    localized_code,
                    path=f"artifact.variants[{index}].{field}",
                )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _root_path(value: Any) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else ROOT / path


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def chunk_strings(strings: list[str], *, max_chars: int) -> list[list[str]]:
    """Split strings into deterministic prompt-sized batches."""

    chunks: list[list[str]] = []
    current: list[str] = []
    current_chars = 0
    for source in strings:
        source_chars = len(source) + 16
        if current and current_chars + source_chars > max_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(source)
        current_chars += source_chars
    if current:
        chunks.append(current)
    return chunks


def _cache_payload(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": "stage1-english-translation-cache-v1", "translations": {}, "model_calls": []}
    payload = _load_json(path)
    if not isinstance(payload.get("translations"), dict):
        raise ValueError(f"invalid translation cache: {path}")
    payload.setdefault("model_calls", [])
    return payload


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    with _CACHE_LOCK:
        _write_json(path, payload)


def _translate_chunk(
    sources: list[str],
    *,
    model: str | None,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    from llm_client import chat_json_with_metadata

    user = json.dumps({"strings": sources}, ensure_ascii=False, separators=(",", ":"))
    last_error: Exception | None = None
    model_calls: list[dict[str, Any]] = []
    for _attempt in range(3):
        response = chat_json_with_metadata(
            TRANSLATION_SYSTEM_PROMPT,
            user,
            model=model,
            kind="stage1_english_localization",
        )
        model_calls.extend(response.get("model_calls") or [])
        try:
            return translation_map_from_response(sources, response.get("content")), model_calls
        except ValueError as exc:
            last_error = exc
            user = "\n\n".join(
                [
                    json.dumps({"strings": sources}, ensure_ascii=False, separators=(",", ":")),
                    f"The previous response failed validation: {exc}",
                    "Retry the complete batch. Keep the same order and length, and remove every CJK character.",
                ]
            )
    raise last_error or ValueError("translation batch failed")


def translate_strings(
    strings: list[str],
    *,
    cache_path: Path,
    concurrency: int,
    max_chars: int,
    model: str | None,
    force: bool = False,
) -> tuple[dict[str, str], list[dict[str, Any]], int]:
    """Translate strings with a persistent exact-string cache."""

    cache = _cache_payload(cache_path)
    cached = {} if force else {str(key): str(value) for key, value in cache["translations"].items()}
    unique = sorted(set(strings))
    missing = [source for source in unique if source not in cached or CJK_RE.search(cached[source])]
    chunks = chunk_strings(missing, max_chars=max_chars)
    new_calls: list[dict[str, Any]] = []
    if chunks:
        print(
            f"TRANSLATE strings={len(missing)} batches={len(chunks)} concurrency={concurrency}",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_index = {
                executor.submit(_translate_chunk, chunk, model=model): index
                for index, chunk in enumerate(chunks, start=1)
            }
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                mapping, calls = future.result()
                cached.update(mapping)
                new_calls.extend(calls)
                cache["translations"] = cached
                cache["model_calls"] = [*(cache.get("model_calls") or []), *calls]
                _write_cache(cache_path, cache)
                print(f"TRANSLATE batch={index}/{len(chunks)} ok strings={len(mapping)}", flush=True)
    result = {source: cached[source] for source in unique}
    return result, new_calls, len(chunks)


def _safe_renderer_translation(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9 _-]+", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Text"


def _assert_english_only(value: str, *, label: str) -> None:
    match = CJK_RE.search(value)
    if match:
        excerpt = value[max(0, match.start() - 60) : match.start() + 100].replace("\n", " ")
        raise ValueError(f"English-only gate failed for {label}: {excerpt}")


def _localized_report(
    source_report: dict[str, Any],
    translations: dict[str, str],
    *,
    source_report_path: Path,
    output_dir: Path,
    translated_artifacts: dict[str, dict[str, Any]],
    source_rows: list[dict[str, Any]],
    model_calls: list[dict[str, Any]],
    translation_batches: int,
) -> dict[str, Any]:
    report = apply_translation_map(source_report, translations)
    rows = report.get("results") or []
    source_by_case = {str(row.get("case_id") or ""): row for row in source_rows}
    for row in rows:
        case_id = str(row.get("case_id") or "")
        source_row = source_by_case[case_id]
        source_json = _root_path(source_row["json"])
        stem = source_json.stem
        row["html"] = _repo_relative(output_dir / f"{stem}.html")
        row["json"] = _repo_relative(output_dir / f"{stem}.json")
        row["language"] = "en"
        row["localization"] = {
            "source_stage": "Stage1",
            "source_json": _repo_relative(source_json),
            "source_json_sha256": _sha256(source_json),
            "algorithm_generation_reused": True,
            "solution_regenerated": False,
        }
        if case_id not in translated_artifacts:
            raise KeyError(f"missing translated artifact for {case_id}")
    report["kind"] = "llm_benchmark_report_stage1_english_localized"
    report["cached"] = True
    report["ended_at"] = datetime.now().replace(microsecond=0).isoformat()
    report["localization"] = {
        "schema_version": "stage1-english-localization-v1",
        "source_report": _repo_relative(source_report_path),
        "algorithm_generation_reused": True,
        "solution_regenerated": False,
        "translation_batches": translation_batches,
        "model_calls": model_calls,
    }
    return report


def build_localized_stage1(args: argparse.Namespace) -> dict[str, Any]:
    from algolab.renderer.export import render_html
    from algolab.schemas.validation import BuildArtifact

    source_report = _load_json(args.source_report)
    source_rows = [row for row in (source_report.get("results") or []) if isinstance(row, dict)]
    if not source_rows:
        raise ValueError(f"source report has no results: {args.source_report}")

    source_artifacts: dict[str, dict[str, Any]] = {}
    strings = collect_cjk_strings(source_report)
    for row in source_rows:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError("source report row is missing case_id")
        artifact_path = _root_path(row.get("json"))
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Stage1 JSON is missing for {case_id}: {artifact_path}")
        artifact = _load_json(artifact_path)
        source_artifacts[case_id] = artifact
        strings.extend(collect_cjk_strings(artifact))

    translations, calls, batches = translate_strings(
        strings,
        cache_path=args.translation_cache,
        concurrency=args.concurrency,
        max_chars=args.chunk_chars,
        model=args.model,
        force=args.force_translate,
    )
    translated_artifacts: dict[str, dict[str, Any]] = {}
    rendered: dict[str, str] = {}
    for case_id, artifact in source_artifacts.items():
        localized = apply_translation_map(artifact, translations)
        assert_localization_preserves_semantics(artifact, localized)
        serialized = json.dumps(localized, ensure_ascii=False)
        _assert_english_only(serialized, label=f"{case_id} translated Stage1 JSON")
        validated = BuildArtifact.model_validate(localized)
        translated_artifacts[case_id] = localized
        rendered[case_id] = render_html(validated)

    renderer_runs = sorted(
        {
            match.group(0)
            for html in rendered.values()
            for match in CJK_RUN_RE.finditer(html)
        }
    )
    renderer_translations, renderer_calls, renderer_batches = translate_strings(
        renderer_runs,
        cache_path=args.translation_cache,
        concurrency=args.concurrency,
        max_chars=args.chunk_chars,
        model=args.model,
        force=args.force_translate,
    )
    calls.extend(renderer_calls)
    batches += renderer_batches
    renderer_translations.update(CRITICAL_RENDERER_TRANSLATIONS)
    renderer_translations = {
        source: _safe_renderer_translation(target)
        for source, target in renderer_translations.items()
    }

    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True)
    source_by_case = {str(row["case_id"]): row for row in source_rows}
    for case_id, artifact in translated_artifacts.items():
        source_json = _root_path(source_by_case[case_id]["json"])
        stem = source_json.stem
        html = localize_renderer_text(rendered[case_id], renderer_translations)
        html = html.replace('lang="zh-CN"', 'lang="en"').replace('lang="zh"', 'lang="en"')
        _assert_english_only(html, label=f"{case_id} rendered Stage1 HTML")
        (args.output_dir / f"{stem}.html").write_text(html, encoding="utf-8")
        _write_json(args.output_dir / f"{stem}.json", artifact)

    report = _localized_report(
        source_report,
        translations,
        source_report_path=args.source_report,
        output_dir=args.output_dir,
        translated_artifacts=translated_artifacts,
        source_rows=source_rows,
        model_calls=calls,
        translation_batches=batches,
    )
    _write_json(args.output_dir / "llm_benchmark_report.json", report)
    return validate_localized_stage1(args.output_dir)


def validate_localized_stage1(output_dir: Path) -> dict[str, Any]:
    report_path = output_dir / "llm_benchmark_report.json"
    report = _load_json(report_path)
    rows = [row for row in (report.get("results") or []) if isinstance(row, dict)]
    if not rows:
        raise ValueError(f"localized Stage1 report has no results: {report_path}")
    for row in rows:
        case_id = str(row.get("case_id") or "")
        html = _root_path(row.get("html"))
        artifact_json = _root_path(row.get("json"))
        if not html.is_file() or html.stat().st_size <= 0:
            raise FileNotFoundError(f"localized Stage1 HTML is missing for {case_id}: {html}")
        if not artifact_json.is_file() or artifact_json.stat().st_size <= 0:
            raise FileNotFoundError(f"localized Stage1 JSON is missing for {case_id}: {artifact_json}")
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".html", ".json", ".md", ".txt"}:
            _assert_english_only(path.read_text(encoding="utf-8", errors="ignore"), label=str(path))
    return {
        "case_count": len(rows),
        "html_count": sum(1 for row in rows if _root_path(row.get("html")).is_file()),
        "json_count": sum(1 for row in rows if _root_path(row.get("json")).is_file()),
        "language": "en",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--translation-cache", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--chunk-chars", type=int, default=10_000)
    parser.add_argument("--model", default=None)
    parser.add_argument("--force-translate", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    for field in ("source_report", "output_dir", "translation_cache"):
        value = getattr(args, field)
        setattr(args, field, value if value.is_absolute() else ROOT / value)
    if not 1 <= args.concurrency <= 32:
        raise SystemExit("--concurrency must be between 1 and 32")
    if args.chunk_chars < 1000:
        raise SystemExit("--chunk-chars must be at least 1000")
    return args


def main() -> int:
    args = parse_args()
    summary = validate_localized_stage1(args.output_dir) if args.validate_only else build_localized_stage1(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
