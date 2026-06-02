"""Shared runners for external baseline and ablation experiments."""

from __future__ import annotations

import argparse
import concurrent.futures
import multiprocessing as mp
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from llm_client import _model_name
from scripts.run_llm_benchmark import (
    LLM_FAMILY_SETS_PATH,
    UNSEEN_FAMILY_CASES_PATH,
    BenchmarkCase,
    BenchmarkInput,
    UnseenBenchmarkCase,
    benchmark_condition,
    browser_smoke_html_paths,
    classify_failure,
    load_llm_family_sets,
    load_unseen_family_cases,
    result_metadata,
    selected_cases,
    selected_tasks,
    validate_llm_family_sets,
    validate_unseen_family_cases,
    write_report,
)


BaselineRunner = Callable[[BenchmarkCase | UnseenBenchmarkCase, BenchmarkInput, int, argparse.Namespace], dict[str, Any]]


def add_common_args(parser: argparse.ArgumentParser, *, condition: str) -> None:
    parser.add_argument("--case", action="append", default=[], help="只运行指定 case id，可重复传入")
    parser.add_argument("--sample", type=int, default=None, help="只运行指定 sample index；默认首个输入")
    parser.add_argument("--all-samples", action="store_true", help="运行每个 case 的所有输入")
    parser.add_argument("--solutions", type=int, default=1, help="每个输入请求的解法数量")
    parser.add_argument("--max-rounds", type=int, default=2, help="生成失败后的修复轮数")
    parser.add_argument("--timeout-s", type=int, default=1200, help="单个样例最大运行秒数；0 表示不限制")
    parser.add_argument("--strict-warnings", action=argparse.BooleanOptionalAction, default=True, help="有 warning 时判为失败")
    parser.add_argument("--browser-smoke", action=argparse.BooleanOptionalAction, default=False, help="对本次通过的 HTML 产物执行浏览器 smoke")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
    parser.add_argument("--fail-fast", action="store_true", help="遇到第一个失败立即退出")
    parser.add_argument("--write-each", action=argparse.BooleanOptionalAction, default=True, help="每个样例结束后立即写入当前 report")
    parser.add_argument("--concurrency", type=int, default=1, help="并发运行的样例数；每个样例仍有独立 timeout")
    parser.add_argument("--family", action="append", default=[], help="只运行指定 family_id 或中文 family 名，可重复传入")
    parser.add_argument(
        "--gate-layer",
        action="append",
        default=[],
        choices=["smoke", "family_core", "expansion", "property", "llm_eval"],
        help="只运行指定 gate layer，可重复传入",
    )
    parser.add_argument("--limit-per-family", type=int, default=0, help="每个 family 最多运行多少个样例；0 表示不限制")
    parser.add_argument(
        "--case-set",
        default="deterministic",
        choices=["deterministic", "unseen"],
        help="选择 deterministic fixture 或独立 unseen family case registry",
    )
    parser.add_argument("--family-sets", type=Path, default=LLM_FAMILY_SETS_PATH, help="LLM benchmark family split 配置")
    parser.add_argument("--unseen-cases", type=Path, default=UNSEEN_FAMILY_CASES_PATH, help="unseen family case 配置")
    parser.set_defaults(condition=condition)


def prepare_common_args(args: argparse.Namespace) -> None:
    if args.limit_per_family < 0:
        raise SystemExit("--limit-per-family 不能为负数")
    args.family_sets_config = load_llm_family_sets(args.family_sets)
    family_set_errors = validate_llm_family_sets(args.family_sets_config)
    if family_set_errors:
        raise SystemExit("LLM family sets 配置无效：\n" + "\n".join(family_set_errors))
    args.unseen_cases_config = None
    if args.case_set == "unseen":
        args.unseen_cases_config = load_unseen_family_cases(args.unseen_cases)
        unseen_errors = validate_unseen_family_cases(args.unseen_cases_config)
        if unseen_errors:
            raise SystemExit("Unseen family cases 配置无效：\n" + "\n".join(unseen_errors))


def timeout_result(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
    started: float,
) -> dict[str, Any]:
    return {
        "case_id": case.id,
        "title": case.title,
        "family": case.family,
        **result_metadata(case, sample_index, args),
        "sample_index": sample_index,
        "input_data": sample.input_data,
        "expected": sample.expected,
        "model": _model_name(),
        "condition": benchmark_condition(args),
        "ok": False,
        "error": f"TimeoutError: baseline experiment 超过 {args.timeout_s} 秒",
        "failure_type": "timeout",
        "duration_s": round(time.time() - started, 3),
        "model_calls": [],
    }


def _worker(
    runner: BaselineRunner,
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
    queue: mp.Queue,
) -> None:
    queue.put(runner(case, sample, sample_index, args))


def run_one_with_timeout(
    runner: BaselineRunner,
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if args.timeout_s <= 0:
        return runner(case, sample, sample_index, args)
    started = time.time()
    result_queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_worker, args=(runner, case, sample, sample_index, args, result_queue))
    process.start()
    deadline = time.time() + args.timeout_s
    result: dict[str, Any] | None = None
    while process.is_alive() and time.time() < deadline:
        process.join(min(1.0, max(0.0, deadline - time.time())))
        while not result_queue.empty():
            result = result_queue.get()
    while not result_queue.empty():
        result = result_queue.get()
    if result is not None:
        return result
    if process.is_alive():
        process.terminate()
        process.join(2)
    return timeout_result(case, sample, sample_index, args, started)


def _apply_browser_smoke_failures(results: list[dict[str, Any]], browser_checks: list[dict[str, Any]]) -> None:
    by_path = {str(item.get("html")): item for item in browser_checks}
    for result in results:
        html = str(result.get("html") or "")
        check = by_path.get(html)
        if not check or check.get("ok") is True:
            continue
        result["ok"] = False
        result["failure_type"] = "browser"
        result["error"] = "; ".join(str(item) for item in check.get("errors") or ["browser smoke failed"])


def run_benchmark(args: argparse.Namespace, runner: BaselineRunner) -> int:
    prepare_common_args(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")
    results: list[dict[str, Any]] = []
    cases = selected_cases(
        set(args.case) if args.case else None,
        families=set(args.family) if args.family else None,
        gate_layers=set(args.gate_layer) if args.gate_layer else None,
        family_sets=args.family_sets_config,
        case_set=args.case_set,
        unseen_cases_config=args.unseen_cases_config,
    )
    tasks = selected_tasks(cases, args)

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
                future = executor.submit(run_one_with_timeout, runner, case, sample, sample_index, args)
                future_to_task[future] = (case, sample_index)
            for future in concurrent.futures.as_completed(future_to_task):
                ok = handle_result(future.result())
                if not ok and args.fail_fast:
                    for pending in future_to_task:
                        pending.cancel()
                    break
    else:
        for case, sample_index, sample in tasks:
            print(f"RUN {case.id}[{sample_index}] expected={sample.expected!r}", flush=True)
            ok = handle_result(run_one_with_timeout(runner, case, sample, sample_index, args))
            if not ok and args.fail_fast:
                break

    browser_checks: list[dict[str, Any]] = []
    if args.browser_smoke:
        html_paths = [Path(item["html"]) for item in results if item.get("ok") and item.get("html")]
        browser_checks = browser_smoke_html_paths(html_paths)
        _apply_browser_smoke_failures(results, browser_checks)
    write_report(
        results,
        args.output_dir,
        args=args,
        started_at=started_at,
        ended_at=datetime.now().isoformat(timespec="seconds"),
        browser_checks=browser_checks,
    )
    passed = sum(1 for item in results if item.get("ok"))
    print(f"{benchmark_condition(args)}: {passed}/{len(results)} PASS", flush=True)
    print(f"report: {args.output_dir / 'llm_benchmark_report.json'}", flush=True)
    return 0 if passed == len(results) else 1
