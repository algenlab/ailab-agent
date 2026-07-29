"""Render verified SemanticTrace facts through free-form LLM HTML generation."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.cases import BenchmarkCase, benchmark_cases
from llm_client import _model_name, chat_text_with_metadata, llm_config
from scripts.run_direct_html_baseline import extract_html
from scripts.run_direct_browser_repair_baseline import (
    external_resource_urls,
    refresh_external_resource_annotations,
)
from scripts.run_direct_to_scenegraph_ablation import _display_path, _manifest_rows, _repo_path, _write_json


DEFAULT_SOURCE_REPORT = ROOT / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/nondegenerate_ablations/verified_trace_to_html_50"


def build_verified_trace_html_prompt(
    *,
    title: str,
    problem: str,
    family: str,
    strategy: str,
    input_data: Any,
    expected: Any,
    trace: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "Generate a polished self-contained single-file algorithm teaching HTML page. Output only HTML, without markdown.",
            f"Title: {title}",
            f"Problem: {problem}",
            f"Family: {family}",
            f"Strategy: {strategy}",
            f"Input JSON: {json.dumps(input_data, ensure_ascii=False)}",
            f"Expected result JSON: {json.dumps(expected, ensure_ascii=False)}",
            "The following verified semantic trace is the only source of algorithm facts. Preserve its result, event order, states, targets, dependencies, teaching, and checkpoint answers:",
            json.dumps(trace, ensure_ascii=False, indent=2),
            "Page requirements:",
            "- Show readable code, current step title and explanation, algorithm objects, state, evidence, a timeline, previous/play/next controls, and the final return value from first load.",
            "- Every key step must expose a grounded choice/input/judge checkpoint, submit action, correct and wrong feedback, hint, show-answer action, and an append-only learning log.",
            "- All navigation controls must visibly update the current step. Use inline CSS and JavaScript only, with no network resources.",
            "- The implementation and layout are otherwise free-form. Keep the document complete and offline runnable.",
        ]
    )


def _load_trace(row: dict[str, Any]) -> dict[str, Any]:
    artifact = json.loads(_repo_path(str(row.get("json") or "")).read_text(encoding="utf-8"))
    variants = artifact.get("variants") or []
    for variant in variants:
        trace = variant.get("trace")
        if isinstance(trace, dict) and trace.get("events"):
            return trace
    raise ValueError("source artifact has no verified SemanticTrace")


def run_one(row: dict[str, Any], *, case: BenchmarkCase, output_dir: Path, model: str) -> dict[str, Any]:
    case_dir = output_dir / "cases" / case.id
    result_path = case_dir / "result.json"
    if result_path.exists():
        existing = json.loads(result_path.read_text(encoding="utf-8"))
        if existing.get("html") and _repo_path(str(existing["html"])).exists():
            return existing
    case_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = case_dir / "prompt.txt"
    raw_path = case_dir / "response.txt"
    html_path = case_dir / "page.html"
    started = time.time()
    try:
        trace = _load_trace(row)
        prompt = build_verified_trace_html_prompt(
            title=case.title,
            problem=case.problem,
            family=case.family,
            strategy=case.strategy,
            input_data=row.get("input_data"),
            expected=row.get("expected"),
            trace=trace,
        )
        prompt_path.write_text(prompt, encoding="utf-8")
        response = chat_text_with_metadata(
            "You are an expert frontend engineer building offline algorithm teaching pages. Return only a complete HTML document.",
            prompt,
            model=model,
            kind="verified_trace_to_html",
        )
        raw = str(response.get("content") or "")
        raw_path.write_text(raw, encoding="utf-8")
        html = extract_html(raw)
        if not html:
            raise ValueError("model response did not contain HTML")
        html_path.write_text(html, encoding="utf-8")
        metadata_path = html_path.with_suffix(".json")
        _write_json(
            metadata_path,
            {
                "kind": "verified_trace_to_html_artifact",
                "case_id": case.id,
                "source_artifact": row.get("json"),
                "trace_events": len(trace.get("events") or []),
                "html_chars": len(html),
            },
        )
        result = {
            **{key: copy.deepcopy(value) for key, value in row.items() if key not in {"html", "json", "model_calls"}},
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            "condition": "verified_trace_to_html",
            "baseline": "verified_trace_to_html",
            "ok": True,
            "html": _display_path(html_path),
            "json": _display_path(metadata_path),
            "prompt": _display_path(prompt_path),
            "raw_response": _display_path(raw_path),
            "source_artifact": row.get("json"),
            "trace_events": len(trace.get("events") or []),
            "fixed_runtime_enabled": False,
            "verified_trace_present": True,
            "external_resource_urls": external_resource_urls(html),
            "duration_s": round(time.time() - started, 3),
            "model_calls": response.get("model_calls") or [],
        }
    except Exception as exc:
        result = {
            **{key: copy.deepcopy(value) for key, value in row.items() if key not in {"html", "json", "model_calls"}},
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            "condition": "verified_trace_to_html",
            "baseline": "verified_trace_to_html",
            "ok": False,
            "html": "",
            "json": "",
            "prompt": _display_path(prompt_path) if prompt_path.exists() else "",
            "raw_response": _display_path(raw_path) if raw_path.exists() else "",
            "source_artifact": row.get("json"),
            "fixed_runtime_enabled": False,
            "verified_trace_present": True,
            "duration_s": round(time.time() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
            "model_calls": [],
        }
    _write_json(result_path, result)
    return result


def _write_report(output_dir: Path, results: list[dict[str, Any]], *, source_report: Path, model: str, started_at: str) -> dict[str, Any]:
    ordered = sorted(results, key=lambda row: str(row.get("case_id") or ""))
    report = refresh_external_resource_annotations({
        "kind": "llm_benchmark_report",
        "condition": "verified_trace_to_html",
        "started_at": started_at,
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "source_report": _display_path(source_report),
        "config": {"model": model, "llm": llm_config(), "count": len(ordered), "seed": 20260713},
        "total": len(ordered),
        "passed": sum(1 for row in ordered if row.get("ok")),
        "failed": sum(1 for row in ordered if not row.get("ok")),
        "external_resource_cases": sum(1 for row in ordered if row.get("external_resource_urls")),
        "results": ordered,
    })
    _write_json(output_dir / "llm_benchmark_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--selection-manifest", type=Path, default=DEFAULT_OUTPUT_DIR.parent / "selected_cases_50.json")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--model", default="")
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    source_report = _repo_path(args.source_report)
    output_dir = _repo_path(args.output_dir)
    source = json.loads(source_report.read_text(encoding="utf-8"))
    selected = _manifest_rows(source.get("results") or [], _repo_path(args.selection_manifest), count=args.count, seed=args.seed)
    if args.case:
        wanted = set(args.case)
        selected = [row for row in selected if row.get("case_id") in wanted]
    case_map = {case.id: case for case in benchmark_cases()}
    model = args.model or str((source.get("config") or {}).get("model") or _model_name())
    started_at = datetime.now().isoformat(timespec="seconds")
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {
            executor.submit(run_one, row, case=case_map[str(row["case_id"])], output_dir=output_dir, model=model): str(row["case_id"])
            for row in selected
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            _write_report(output_dir, results, source_report=source_report, model=model, started_at=started_at)
            print(f"DONE {result['case_id']} ok={result.get('ok')}", flush=True)
    report = _write_report(output_dir, results, source_report=source_report, model=model, started_at=started_at)
    print(json.dumps({"report": _display_path(output_dir / "llm_benchmark_report.json"), "passed": report["passed"], "total": report["total"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
