"""Run the benchmark through the real LLM generation path.

This script intentionally does not cache model outputs. Every case calls
build_artifact(), which calls the configured LLM generator and repair loop.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing as mp
import queue
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.solution_generator import generate_solution_spec, repair_solution_spec
from algolab.pipeline import BuildError, _try_materialize
from algolab.renderer.export import save_html
from algolab.schemas.input import ProblemInput
from algolab.schemas.validation import BuildArtifact
from llm_client import _model_name, llm_config
from tests.benchmark_cases import BenchmarkCase, BenchmarkInput, benchmark_cases


def selected_cases(ids: set[str] | None = None) -> tuple[BenchmarkCase, ...]:
    cases = benchmark_cases()
    if not ids:
        return cases
    found = tuple(case for case in cases if case.id in ids)
    missing = ids - {case.id for case in found}
    if missing:
        raise SystemExit(f"未知 benchmark case：{', '.join(sorted(missing))}")
    return found


def selected_samples(case: BenchmarkCase, args: argparse.Namespace) -> tuple[tuple[int, BenchmarkInput], ...]:
    if args.sample is not None:
        if args.sample < 0 or args.sample >= len(case.samples):
            raise SystemExit(f"{case.id} 不存在 sample {args.sample}，可用范围 0..{len(case.samples) - 1}")
        return ((args.sample, case.samples[args.sample]),)
    samples = case.samples if args.all_samples else case.samples[:1]
    return tuple(enumerate(samples))


def make_request(case: BenchmarkCase, sample: BenchmarkInput, *, solutions: int) -> ProblemInput:
    return ProblemInput(
        problem=case.problem,
        input_data=sample.input_data,
        strategy_hint=case.strategy,
        expected_result=sample.expected,
        solution_count=solutions,
    )


ProgressCallback = Callable[[dict[str, Any]], None]


def run_one(
    case: BenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    started = time.time()
    request = make_request(case, sample, solutions=args.solutions)
    output_stem = f"llm_{case.id}_{sample_index}"
    output_html = args.output_dir / f"{output_stem}.html"
    phase_log: list[dict[str, Any]] = []

    def record_progress(event: dict[str, Any]) -> None:
        phase_log.append(event)
        if progress is not None:
            progress(event)

    try:
        artifact = build_artifact_timed(
            request,
            max_rounds=args.max_rounds,
            progress=record_progress,
            strict_warnings=args.strict_warnings,
        )
        strict_warning_errors: list[str] = []
        if args.strict_warnings and artifact.validation.warnings:
            strict_warning_errors = [f"严格模式拒绝 warning：{warning}" for warning in artifact.validation.warnings]
        timed_phase("render", record_progress, lambda: save_html(artifact, output_html))
        variants = [
            {
                "id": variant.id,
                "name": variant.name,
                "result": variant.result,
                "steps": len(variant.trace.events) if variant.trace else 0,
            }
            for variant in artifact.variants
        ]
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "ok": artifact.validation.release_gate.release_ready and not strict_warning_errors,
            "release_gate": artifact.validation.release_gate.model_dump(),
            "checks": artifact.validation.checks,
            "warnings": artifact.validation.warnings,
            "errors": [*artifact.validation.errors, *strict_warning_errors],
            "variants": variants,
            "html": str(output_html),
            "json": str(output_html.with_suffix(".json")),
            "phase_timings": completed_phase_timings(phase_log),
            "last_phase": last_phase(phase_log) or "done",
            "duration_s": round(time.time() - started, 3),
            "failure_type": "",
        }
    except Exception as exc:
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "failure_type": classify_failure(f"{type(exc).__name__}: {exc}"),
            "phase_timings": completed_phase_timings(phase_log),
            "last_phase": last_phase(phase_log),
            "duration_s": round(time.time() - started, 3),
        }


def build_artifact_timed(
    request: ProblemInput,
    max_rounds: int = 2,
    progress: ProgressCallback | None = None,
    strict_warnings: bool = False,
) -> BuildArtifact:
    spec = timed_phase("generate", progress, lambda: generate_solution_spec(request))
    last_errors: list[str] = []

    for round_idx in range(max_rounds + 1):
        artifact, errors = timed_phase(
            f"materialize_round_{round_idx}",
            progress,
            lambda spec=spec: _try_materialize(request, spec),
        )
        if artifact.validation.release_gate.release_ready and (not strict_warnings or not artifact.validation.warnings):
            return artifact
        last_errors = errors or []
        if artifact.validation.release_gate.release_ready and strict_warnings and artifact.validation.warnings:
            last_errors = [f"严格模式拒绝 warning：{warning}" for warning in artifact.validation.warnings]
        if round_idx < max_rounds:
            spec = timed_phase(
                f"repair_round_{round_idx}",
                progress,
                lambda spec=spec, errors=last_errors: repair_solution_spec(request, spec, errors),
            )

    raise BuildError("没有生成可发布产物：\n" + "\n".join(last_errors))


def timed_phase(name: str, progress: ProgressCallback | None, fn: Callable[[], Any]) -> Any:
    emit_progress(progress, {"type": "progress", "event": "start", "phase": name, "at": round(time.time(), 3)})
    started = time.time()
    status = "ok"
    try:
        return fn()
    except Exception:
        status = "error"
        raise
    finally:
        emit_progress(
            progress,
            {
                "type": "progress",
                "event": "end",
                "phase": name,
                "status": status,
                "duration_s": round(time.time() - started, 3),
                "at": round(time.time(), 3),
            },
        )


def emit_progress(progress: ProgressCallback | None, event: dict[str, Any]) -> None:
    if progress is None:
        return
    try:
        progress(event)
    except Exception:
        return


def completed_phase_timings(phase_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "phase": event["phase"],
            "duration_s": event["duration_s"],
            "status": event.get("status", ""),
        }
        for event in phase_log
        if event.get("event") == "end" and "duration_s" in event
    ]


def average_duration(results: list[dict[str, Any]]) -> float:
    durations = [float(item.get("duration_s") or 0) for item in results]
    return round(sum(durations) / len(durations), 3) if durations else 0.0


def summarize_phase_timings(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    phases: dict[str, list[float]] = {}
    for item in results:
        for phase in item.get("phase_timings") or []:
            name = phase.get("phase")
            duration = phase.get("duration_s")
            if isinstance(name, str) and isinstance(duration, (int, float)):
                phases.setdefault(name, []).append(float(duration))
    return {
        name: {
            "count": len(values),
            "avg_s": round(sum(values) / len(values), 3),
            "max_s": round(max(values), 3),
        }
        for name, values in sorted(phases.items())
        if values
    }


def last_phase(phase_log: list[dict[str, Any]]) -> str:
    for event in reversed(phase_log):
        phase = event.get("phase")
        if isinstance(phase, str):
            suffix = "中" if event.get("event") == "start" else event.get("status", "")
            return f"{phase}:{suffix}" if suffix else phase
    return ""


def last_phase_elapsed_s(phase_log: list[dict[str, Any]], now: float | None = None) -> float:
    now = now or time.time()
    active: dict[str, float] = {}
    for event in phase_log:
        phase = event.get("phase")
        if not isinstance(phase, str):
            continue
        if event.get("event") == "start" and isinstance(event.get("at"), (int, float)):
            active[phase] = float(event["at"])
        elif event.get("event") == "end":
            active.pop(phase, None)
    if not active:
        return 0.0
    _phase, started_at = next(reversed(active.items()))
    return round(max(0.0, now - started_at), 3)


def _run_one_worker(case: BenchmarkCase, sample: BenchmarkInput, sample_index: int, args: argparse.Namespace, queue: mp.Queue):
    def progress(event: dict[str, Any]) -> None:
        queue.put({"type": "progress", "event": event})

    queue.put({"type": "result", "result": run_one(case, sample, sample_index, args, progress=progress)})


def run_one_with_timeout(case: BenchmarkCase, sample: BenchmarkInput, sample_index: int, args: argparse.Namespace) -> dict[str, Any]:
    if args.timeout_s <= 0:
        return run_one(case, sample, sample_index, args)
    started = time.time()
    result_queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_run_one_worker, args=(case, sample, sample_index, args, result_queue))
    process.start()
    phase_log: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    deadline = time.time() + args.timeout_s
    while process.is_alive() and time.time() < deadline:
        process.join(min(1.0, max(0.0, deadline - time.time())))
        result = drain_worker_queue(result_queue, phase_log) or result
    result = drain_worker_queue(result_queue, phase_log) or result
    if result is not None:
        return result
    if process.is_alive():
        process.terminate()
        process.join(2)
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "ok": False,
            "error": f"TimeoutError: LLM benchmark 超过 {args.timeout_s} 秒",
            "failure_type": "timeout",
            "phase_timings": completed_phase_timings(phase_log),
            "last_phase": last_phase(phase_log),
            "last_phase_elapsed_s": last_phase_elapsed_s(phase_log),
            "duration_s": round(time.time() - started, 3),
        }
    return {
        "case_id": case.id,
        "title": case.title,
        "family": case.family,
        "sample_index": sample_index,
        "input_data": sample.input_data,
        "expected": sample.expected,
        "model": _model_name(),
        "ok": False,
        "error": "RuntimeError: LLM benchmark 子进程无返回",
        "failure_type": "runner_error",
        "phase_timings": completed_phase_timings(phase_log),
        "last_phase": last_phase(phase_log),
        "last_phase_elapsed_s": last_phase_elapsed_s(phase_log),
        "duration_s": round(time.time() - started, 3),
    }


def drain_worker_queue(result_queue: mp.Queue, phase_log: list[dict[str, Any]]) -> dict[str, Any] | None:
    result: dict[str, Any] | None = None
    while True:
        try:
            item = result_queue.get_nowait()
        except queue.Empty:
            break
        if not isinstance(item, dict):
            continue
        if item.get("type") == "progress" and isinstance(item.get("event"), dict):
            phase_log.append(item["event"])
        elif item.get("type") == "result" and isinstance(item.get("result"), dict):
            result = item["result"]
    return result


def classify_failure(message: str) -> str:
    text = message.lower()
    if "algolab_llm_api_key" in text or "api_key" in text or "环境变量" in message or "api key" in text:
        return "configuration"
    if "timeout" in text or "超时" in message or "超过" in message:
        return "timeout"
    if "严格模式拒绝 warning" in message or "warning" in text:
        return "visual_warning"
    if "process" in text or "invariant" in text or "背包" in message or "dp[" in message or "bfs" in text or "dijkstra" in text or "kmp" in text or "lca" in text or "tarjan" in text:
        return "process_invariant"
    if "scene" in text or "layout" in text or "渲染" in message or "视觉" in message:
        return "visual_scene"
    if "verifier" in text or "expected" in text or "结果" in message:
        return "correctness"
    if "执行失败" in message or "sandbox" in text or "nameerror" in text or "syntaxerror" in text:
        return "execution"
    if "validation error" in text or "semantictrace" in text or "schema" in text:
        return "trace_schema"
    if "js errors" in text or "browser" in text:
        return "browser"
    return "generation"


def summarize_failures(results: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        if item.get("ok"):
            continue
        failure_type = item.get("failure_type") or classify_failure(item.get("error") or "; ".join(item.get("errors", [])))
        item["failure_type"] = failure_type
        summary[failure_type] = summary.get(failure_type, 0) + 1
    return summary


def browser_smoke_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    html_paths = [Path(item["html"]) for item in results if item.get("ok") and item.get("html")]
    return browser_smoke_html_paths(html_paths)


def browser_smoke_html_paths(html_paths: list[Path]) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    checked: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for path in html_paths:
            checked.append(_check_html_path(browser, path))
        browser.close()
    return checked


def _check_html_path(browser: Any, path: Path) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        page.goto(path.resolve().as_uri())
        page.wait_for_timeout(300)
        title = page.locator("#title").inner_text().strip()
        counter = page.locator("#counter").inner_text().strip()
        canvas_text = page.locator("#canvas").inner_text().strip()
        ok = bool(title and "/" in counter and canvas_text and not errors)
        return {
            "html": str(path),
            "ok": ok,
            "title": title,
            "counter": counter,
            "canvas_chars": len(canvas_text),
            "errors": errors,
        }
    except Exception as exc:
        return {"html": str(path), "ok": False, "errors": [f"{type(exc).__name__}: {exc}"]}
    finally:
        page.close()


def write_report(
    results: list[dict[str, Any]],
    output_dir: Path,
    *,
    args: argparse.Namespace,
    started_at: str,
    ended_at: str,
    browser_checks: list[dict[str, Any]] | None = None,
) -> Path:
    passed = sum(1 for item in results if item.get("ok"))
    total = len(results)
    failure_summary = summarize_failures(results)
    phase_summary = summarize_phase_timings(results)
    report = {
        "kind": "llm_benchmark_report",
        "cached": False,
        "started_at": started_at,
        "ended_at": ended_at,
        "config": {
            "cases": args.case,
            "sample": args.sample,
            "all_samples": args.all_samples,
            "solutions": args.solutions,
            "max_rounds": args.max_rounds,
            "timeout_s": args.timeout_s,
            "strict_warnings": args.strict_warnings,
            "browser_smoke": args.browser_smoke,
            "write_each": args.write_each,
            "concurrency": getattr(args, "concurrency", 1),
            "llm": llm_config(),
            "model": _model_name(),
        },
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0,
        "avg_duration_s": average_duration(results),
        "failure_summary": failure_summary,
        "phase_summary": phase_summary,
        "browser_smoke": browser_checks or [],
        "results": results,
    }
    path = output_dir / "llm_benchmark_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = output_dir / "llm_benchmark_report.md"
    lines = [
        "# LLM Benchmark Report",
        "",
        f"- 缓存：未使用",
        f"- 模型：{_model_name()}",
        f"- 总数：{total}",
        f"- 通过：{passed}",
        f"- 失败：{total - passed}",
        f"- 通过率：{passed / total:.2%}" if total else "- 通过率：N/A",
        f"- 平均耗时：{average_duration(results)}s/case",
        f"- 严格 warning：{'开启' if args.strict_warnings else '关闭'}",
        f"- 浏览器检查：{'开启' if args.browser_smoke else '关闭'}",
        "",
        "| Case | Sample | Family | Status | Failure | Duration | Last Phase | Artifact |",
        "|---|---:|---|---|---|---:|---|---|",
    ]
    for item in results:
        status = "PASS" if item.get("ok") else "FAIL"
        artifact = item.get("html", "")
        failure = item.get("failure_type", "")
        last = item.get("last_phase", "")
        elapsed = item.get("last_phase_elapsed_s")
        last_phase_text = f"{last} ({elapsed}s)" if elapsed else str(last)
        lines.append(
            f"| {item['case_id']} | {item['sample_index']} | {item['family']} | {status} | "
            f"{failure} | {item.get('duration_s', 0)}s | {last_phase_text} | {artifact} |"
        )
    if phase_summary:
        lines.extend(["", "## Phase Timings", "", "| Phase | Count | Avg | Max |", "|---|---:|---:|---:|"])
        for phase, stat in phase_summary.items():
            lines.append(f"| {phase} | {stat['count']} | {stat['avg_s']}s | {stat['max_s']}s |")
    if browser_checks:
        lines.extend(["", "## Browser Smoke", "", "| HTML | Status | Canvas Chars |", "|---|---|---:|"])
        for item in browser_checks:
            lines.append(f"| {item.get('html', '')} | {'PASS' if item.get('ok') else 'FAIL'} | {item.get('canvas_chars', 0)} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="运行真实 LLM 生成 benchmark，不使用缓存")
    parser.add_argument("--case", action="append", default=[], help="只运行指定 case id，可重复传入")
    parser.add_argument("--sample", type=int, default=None, help="只运行指定 sample index；默认首个输入，配合 --all-samples 时不使用")
    parser.add_argument("--all-samples", action="store_true", help="运行每个 case 的所有输入；默认只跑首个输入")
    parser.add_argument("--solutions", type=int, default=1, help="每个输入请求的解法数量；benchmark 默认用 1 个解法降低模型超时")
    parser.add_argument("--max-rounds", type=int, default=2, help="生成失败后的修复轮数")
    parser.add_argument("--timeout-s", type=int, default=1200, help="单个样例最大运行秒数；0 表示不限制")
    parser.add_argument("--strict-warnings", action=argparse.BooleanOptionalAction, default=True, help="有 warning 时判为失败")
    parser.add_argument("--browser-smoke", action=argparse.BooleanOptionalAction, default=False, help="对本次通过的 HTML 产物执行浏览器 smoke")
    parser.add_argument("--output-dir", type=Path, default=Path("output/llm_benchmark"), help="输出目录")
    parser.add_argument("--fail-fast", action="store_true", help="遇到第一个失败立即退出")
    parser.add_argument("--write-each", action=argparse.BooleanOptionalAction, default=True, help="每个样例结束后立即写入当前 report")
    parser.add_argument("--concurrency", type=int, default=1, help="并发运行的样例数；每个样例仍有独立 timeout")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")
    results: list[dict[str, Any]] = []
    cases = selected_cases(set(args.case) if args.case else None)
    tasks = [
        (case, sample_index, sample)
        for case in cases
        for sample_index, sample in selected_samples(case, args)
    ]

    def handle_result(result: dict[str, Any]) -> bool:
        results.append(result)
        if args.write_each:
            write_report(
                results,
                args.output_dir,
                args=args,
                started_at=started_at,
                ended_at=datetime.now().isoformat(timespec="seconds"),
            )
        status = "PASS" if result.get("ok") else "FAIL"
        print(f"{status} {result['case_id']}[{result['sample_index']}] {result.get('duration_s')}s", flush=True)
        if not result.get("ok"):
            print(result.get("error") or "; ".join(result.get("errors", [])), flush=True)
            return False
        return True

    if args.concurrency > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_task = {}
            for case, sample_index, sample in tasks:
                print(f"RUN {case.id}[{sample_index}] expected={sample.expected!r}", flush=True)
                future = executor.submit(run_one_with_timeout, case, sample, sample_index, args)
                future_to_task[future] = (case, sample_index)
            for future in concurrent.futures.as_completed(future_to_task):
                result = future.result()
                ok = handle_result(result)
                if not ok and args.fail_fast:
                    for pending in future_to_task:
                        pending.cancel()
                    browser_checks = browser_smoke_results(results) if args.browser_smoke else []
                    write_report(
                        results,
                        args.output_dir,
                        args=args,
                        started_at=started_at,
                        ended_at=datetime.now().isoformat(timespec="seconds"),
                        browser_checks=browser_checks,
                    )
                    return 1
    else:
        for case, sample_index, sample in tasks:
            print(f"RUN {case.id}[{sample_index}] expected={sample.expected!r}", flush=True)
            result = run_one_with_timeout(case, sample, sample_index, args)
            if not handle_result(result):
                if args.fail_fast:
                    browser_checks = browser_smoke_results(results) if args.browser_smoke else []
                    write_report(
                        results,
                        args.output_dir,
                        args=args,
                        started_at=started_at,
                        ended_at=datetime.now().isoformat(timespec="seconds"),
                        browser_checks=browser_checks,
                    )
                    return 1
    browser_checks = browser_smoke_results(results) if args.browser_smoke else []
    report_path = write_report(
        results,
        args.output_dir,
        args=args,
        started_at=started_at,
        ended_at=datetime.now().isoformat(timespec="seconds"),
        browser_checks=browser_checks,
    )
    passed = sum(1 for item in results if item.get("ok"))
    print(f"llm_benchmark: {passed}/{len(results)} PASS")
    print(f"report: {report_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
