"""Run a frozen Direct HTML + HTMLCure repair baseline.

HTMLCure receives only the public task specification and its own browser/VLM
evidence. The AlgoTutorGen behavior audit is intentionally run afterwards by
``run_interaction_semantic_eval.py`` and is never exposed to the repair loop.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import api_settings


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_rows(report_path: Path) -> dict[str, dict[str, Any]]:
    report = _read_json(report_path)
    rows = report.get("results") or report.get("records") or []
    return {
        str(row["case_id"]): row
        for row in rows
        if row.get("case_id") and row.get("ok") and row.get("html")
    }


def _public_query(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Create a self-contained interactive algorithm tutoring webpage for the following concrete task.",
            f"Title: {row.get('title') or row.get('case_id')}",
            f"Algorithm family: {row.get('family') or ''}",
            f"Problem: {row.get('problem') or row.get('description') or row.get('title') or ''}",
            f"Concrete input JSON: {json.dumps(row.get('input_data'), ensure_ascii=False)}",
            f"Expected output JSON: {json.dumps(row.get('expected'), ensure_ascii=False)}",
            "Required user-facing behavior:",
            "- visibly show the final answer and a step-by-step algorithm state timeline;",
            "- provide a learner prediction/checkpoint interaction;",
            "- provide distinct correct and incorrect feedback;",
            "- provide hint and show-answer actions;",
            "- append learner attempts to a visible learning log;",
            "- keep the authoritative final answer unchanged during interaction.",
            "Repair the supplied webpage using general browser evidence. Preserve correct existing behavior.",
        ]
    )


def _serialize_iteration(item: Any) -> dict[str, Any]:
    return {
        "iteration": item.iteration,
        "strategy": item.strategy,
        "score_before": item.score_before,
        "score_after": item.score_after,
        "delta": item.delta,
        "elapsed_s": round(item.elapsed_s, 3),
        "success": item.success,
        "n_candidates": item.n_candidates,
        "error": item.error,
        "composite_before": item.composite_before,
        "composite_after": item.composite_after,
        "dim_deltas": item.dim_deltas,
    }


def _cleanup_case_workspace(workspace: Path, case_id: str) -> None:
    """Remove regenerable screenshots after the durable case trace is written."""
    reports_dir = workspace / "reports"
    for report_dir in reports_dir.glob(f"{case_id}_*"):
        if report_dir.is_dir():
            shutil.rmtree(report_dir, ignore_errors=True)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    htmlcure_root = args.htmlcure_root.resolve()
    sys.path.insert(0, str(htmlcure_root))

    from htmleval import build_pipeline
    from htmleval.core.context import EvalContext
    from htmlrefine.core.config import (
        AgentConfig,
        AppConfig,
        EvaluatorConfig,
        ProcessingConfig,
        RepairConfig,
    )
    from htmlrefine.data_pipeline.repair.engine import RepairEngine

    settings = api_settings()
    if not settings["api_key"]:
        raise RuntimeError("No API key is configured in the project API settings")

    source_report = _repo_path(args.direct_report)
    rows_by_id = _source_rows(source_report)
    manifest = _read_json(_repo_path(args.manifest))
    selected = manifest.get("cases") or []
    case_ids = [str(item["case_id"] if isinstance(item, dict) else item) for item in selected]
    if args.case:
        wanted = set(args.case)
        case_ids = [case_id for case_id in case_ids if case_id in wanted]
    if args.num_shards > 1:
        case_ids = [
            case_id for index, case_id in enumerate(case_ids)
            if index % args.num_shards == args.shard_id
        ]
    if args.max_cases > 0:
        case_ids = case_ids[: args.max_cases]
    missing = [case_id for case_id in case_ids if case_id not in rows_by_id]
    if missing:
        raise ValueError(f"Cases missing from Direct report: {missing}")

    output_dir = _repo_path(args.output_dir)
    html_dir = output_dir / "html"
    trace_dir = output_dir / "traces"
    workspace = output_dir / "htmlcure_workspace"
    for path in (html_dir, trace_dir, workspace):
        path.mkdir(parents=True, exist_ok=True)

    config = AppConfig(
        agent=AgentConfig(
            base_url=settings["base_url"],
            api_key=settings["api_key"],
            model=args.repair_model,
        ),
        evaluator=EvaluatorConfig(
            base_url=settings["base_url"],
            api_key=settings["api_key"],
            model=args.evaluator_model,
            max_screenshots=args.max_screenshots,
        ),
        processing=ProcessingConfig(
            concurrency=1,
            browser_pool_size=1,
            skip_agent_phase=True,
            skip_vision_phase=args.fast,
            record_timeout=args.record_timeout,
        ),
        repair=RepairConfig(
            base_url=settings["base_url"],
            api_key=settings["api_key"],
            model=args.repair_model,
            max_iterations=args.max_iterations,
            improvement_threshold=args.improvement_threshold,
            strategies=[
                "bug_fix",
                "feature_complete",
                "visual_enhance",
                "holistic_rewrite",
                "fix_playability",
                "fix_interaction",
                "enhance_interaction",
                "refine_functionality",
                "code_cleanup",
                "polish_visual",
                "visual_enrichment",
            ],
            n_candidates=args.candidates,
            # DeepSeek-V4-Pro is text-only on the experiment endpoint. HTMLCure
            # still supplies browser/VLM findings as text, but not raw images.
            vision_in_repair=False,
            contrastive_feedback=False,
            visual_enrichment=False,
        ),
        workspace=str(workspace),
    )
    config.ensure_dirs()
    pipeline = build_pipeline(config)
    engine = RepairEngine(config.repair)

    completed: list[dict[str, Any]] = []
    started = time.time()
    for index, case_id in enumerate(case_ids, 1):
        trace_path = trace_dir / f"{case_id}.json"
        if trace_path.exists():
            try:
                completed.append(_read_json(trace_path))
                print(f"HTMLCURE {index}/{len(case_ids)} {case_id} cached", flush=True)
                continue
            except Exception:
                pass
        row = rows_by_id[case_id]
        source_html = _repo_path(str(row["html"]))
        original_html = source_html.read_text(encoding="utf-8", errors="ignore")
        query = _public_query(row)
        case_started = time.time()
        print(f"HTMLCURE {index}/{len(case_ids)} {case_id} initial_eval", flush=True)
        try:
            initial_ctx = EvalContext(
                query=query,
                response=original_html,
                game_id=case_id,
                variant="original",
                title=str(row.get("title") or case_id),
            )
            initial_ctx = await pipeline.evaluate(initial_ctx)
            print(
                f"HTMLCURE {index}/{len(case_ids)} {case_id} repair score={initial_ctx.total_score}",
                flush=True,
            )
            result = await engine.repair(
                initial_ctx,
                pipeline,
                config,
                max_iterations=args.max_iterations,
            )
            output_html = html_dir / f"direct_htmlcure_{case_id}_0.html"
            output_html.write_text(result.best_html, encoding="utf-8")
            artifact_path = output_html.with_suffix(".json")
            artifact_path.write_text(
                json.dumps(
                    {
                        "kind": "direct_htmlcure_artifact",
                        "case_id": case_id,
                        "source_html": str(source_html),
                        "htmlcure_commit": args.htmlcure_commit,
                        "original_score": result.original_score,
                        "final_score": result.final_score,
                        "improvement": result.improvement,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            repair_calls = sum(item.n_candidates for item in result.iterations)
            record = {
                **row,
                "condition": "direct_htmlcure",
                "baseline": "direct_html_plus_htmlcure",
                "ok": True,
                "html": str(output_html.relative_to(ROOT)),
                "json": str(artifact_path.relative_to(ROOT)),
                "source_html": str(source_html.relative_to(ROOT)),
                "duration_s": round(time.time() - case_started, 3),
                "htmlcure_original_score": result.original_score,
                "htmlcure_final_score": result.final_score,
                "htmlcure_improvement": result.improvement,
                "htmlcure_evidence_quality": result.evidence_quality,
                "htmlcure_converged": result.converged,
                "htmlcure_repair_llm_calls": repair_calls,
                "htmlcure_iterations": [_serialize_iteration(item) for item in result.iterations],
            }
        except Exception as exc:
            output_html = html_dir / f"direct_htmlcure_{case_id}_0.html"
            shutil.copyfile(source_html, output_html)
            record = {
                **row,
                "condition": "direct_htmlcure",
                "baseline": "direct_html_plus_htmlcure",
                "ok": True,
                "html": str(output_html.relative_to(ROOT)),
                "json": "",
                "source_html": str(source_html.relative_to(ROOT)),
                "duration_s": round(time.time() - case_started, 3),
                "htmlcure_error": f"{type(exc).__name__}: {exc}",
                "htmlcure_fallback_to_original": True,
            }
            logging.exception("HTMLCure failed for %s; preserving original HTML", case_id)
        completed.append(record)
        trace_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _cleanup_case_workspace(workspace, case_id)
        partial = {
            "kind": "direct_htmlcure_baseline_report",
            "created_at": datetime.now().astimezone().isoformat(),
            "source_report": str(source_report.relative_to(ROOT)),
            "manifest": str(_repo_path(args.manifest).relative_to(ROOT)),
            "htmlcure_root": str(htmlcure_root),
            "htmlcure_commit": args.htmlcure_commit,
            "mode": "fast" if args.fast else "full",
            "repair_model": args.repair_model,
            "evaluator_model": args.evaluator_model,
            "max_iterations": args.max_iterations,
            "n_candidates": args.candidates,
            "shard_id": args.shard_id,
            "num_shards": args.num_shards,
            "vision_in_repair": False,
            "browser_use_agent": False,
            "duration_s": round(time.time() - started, 3),
            "results": completed,
        }
        (output_dir / "llm_benchmark_report.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return partial


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--htmlcure-root", type=Path, required=True)
    parser.add_argument("--htmlcure-commit", required=True)
    parser.add_argument("--direct-report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--repair-model", default="DeepSeek-V4-Pro")
    parser.add_argument("--evaluator-model", default="gemini-3-flash-preview")
    parser.add_argument("--max-iterations", type=int, default=2)
    parser.add_argument("--candidates", type=int, default=1)
    parser.add_argument("--max-screenshots", type=int, default=8)
    parser.add_argument("--improvement-threshold", type=float, default=2.0)
    parser.add_argument("--record-timeout", type=int, default=600)
    parser.add_argument("--fast", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.num_shards < 1 or not 0 <= args.shard_id < args.num_shards:
        raise SystemExit("--shard-id must be in [0, --num-shards)")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    report = asyncio.run(_run(args))
    print(
        json.dumps(
            {
                "completed": len(report["results"]),
                "output_dir": str(_repo_path(args.output_dir)),
                "duration_s": report["duration_s"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
