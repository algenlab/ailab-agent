"""Measure trace and browser scaling on 18 tasks at three input sizes."""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.compiler.scene_compiler import compile_scene
from algolab.renderer.export import save_html
from algolab.runtime.executor import execute_variant, results_equivalent
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from algolab.verification.process_validator import validate_process
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace


DEFAULT_REPORT = ROOT / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/long_trace_scalability"
SIZE_NAMES = ("small", "medium", "large")


def _sorted_nums(n: int) -> list[int]:
    return [((index * 37) % (n * 3 + 7)) - n for index in range(n)]


def _bfs_distances(graph: dict[str, list[str]], start: str) -> dict[str, int]:
    result = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in graph[node]:
            if nxt not in result:
                result[nxt] = result[node] + 1
                queue.append(nxt)
    return result


def _dfs_order(graph: dict[str, list[str]], start: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    def visit(node: str) -> None:
        seen.add(node)
        result.append(node)
        for nxt in graph[node]:
            if nxt not in seen:
                visit(nxt)
    visit(start)
    return result


def _daily_temperatures(values: list[int]) -> list[int]:
    result = [0] * len(values)
    stack: list[int] = []
    for index, value in enumerate(values):
        while stack and values[stack[-1]] < value:
            previous = stack.pop()
            result[previous] = index - previous
        stack.append(index)
    return result


def _jobs_for_rank(rank: int) -> list[dict[str, Any]]:
    array_n = (8, 24, 64)[rank]
    broad_n = (12, 48, 160)[rank]
    graph_n = (8, 24, 64)[rank]
    search_n = (32, 256, 2048)[rank]
    prefix_n = (32, 96, 256)[rank]
    max_subarray_n = (8, 64, 192)[rank]
    text_n = (32, 192, 512)[rank]
    temperature_n = (8, 64, 192)[rank]
    nums = _sorted_nums(array_n)
    counting_nums = [((index * 11) % 23) for index in range(broad_n)]
    merge_nums = _sorted_nums(broad_n)
    search_nums = list(range(0, search_n * 2, 2))
    target = search_nums[-4]
    window_nums = [1 + (index % 5) for index in range(broad_n)]
    window_target = 11
    best_window = math.inf
    total = left = 0
    for right, value in enumerate(window_nums):
        total += value
        while total >= window_target:
            best_window = min(best_window, right - left + 1)
            total -= window_nums[left]
            left += 1
    prefix_nums = [index % 17 - 4 for index in range(prefix_n)]
    query = [prefix_n // 4, 3 * prefix_n // 4]
    names = [f"N{index}" for index in range(graph_n)]
    bfs_graph = {
        name: ([names[index + 1]] if index + 1 < graph_n else [])
        + ([names[index + 2]] if index + 2 < graph_n and index % 3 == 0 else [])
        for index, name in enumerate(names)
    }
    dfs_graph = {
        name: [names[index + 1]] if index + 1 < graph_n else []
        for index, name in enumerate(names)
    }
    topo_graph = copy.deepcopy(dfs_graph)
    weighted_graph = {
        name: ([[names[index + 1], 1]] if index + 1 < graph_n else [])
        + ([[names[index + 2], 3]] if index + 2 < graph_n else [])
        for index, name in enumerate(names)
    }
    max_nums = [((index * 13) % 19) - 7 for index in range(max_subarray_n)]
    best = current = max_nums[0]
    for value in max_nums[1:]:
        current = max(value, current + value)
        best = max(best, current)
    grid_dim = ((4, 5), (10, 12), (15, 18))[rank]
    unique_paths = math.comb(grid_dim[0] + grid_dim[1] - 2, grid_dim[0] - 1)
    edit_n = (3, 6, 9)[rank]
    word1 = "a" * edit_n + "b" * edit_n
    word2 = "a" * edit_n + "c" * edit_n
    pattern = "needle"
    text = "a" * (text_n - len(pattern)) + pattern
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    unique_text = "".join(alphabet[index % len(alphabet)] for index in range(text_n))
    temperatures = [50 + ((index * 7) % 41) for index in range(temperature_n)]
    tree_children = {
        names[index]: ([names[index + 1], None] if index + 1 < graph_n else [None, None])
        for index in range(graph_n)
    }
    union_n = (16, 96, 256)[rank]
    split = union_n // 2
    union_edges = [[index, index + 1] for index in range(split - 1)] + [
        [index, index + 1] for index in range(split, union_n - 1)
    ]
    return [
        {"case_id": "insertion_sort", "input_data": {"nums": nums}, "expected": sorted(nums)},
        {"case_id": "counting_sort_synthetic", "input_data": {"nums": counting_nums}, "expected": sorted(counting_nums)},
        {"case_id": "merge_sort_synthetic", "input_data": {"nums": merge_nums}, "expected": sorted(merge_nums)},
        {"case_id": "binary_search", "input_data": {"nums": search_nums, "target": target}, "expected": search_n - 4},
        {"case_id": "sliding_window_min_len", "input_data": {"nums": window_nums, "target": window_target}, "expected": 0 if best_window is math.inf else int(best_window)},
        {"case_id": "prefix_sum_range", "input_data": {"nums": prefix_nums, "query": query}, "expected": sum(prefix_nums[query[0]:query[1] + 1])},
        {"case_id": "graph_bfs", "input_data": {"graph": bfs_graph, "start": names[0]}, "expected": _bfs_distances(bfs_graph, names[0])},
        {"case_id": "graph_dfs_traversal", "input_data": {"graph": dfs_graph, "start": names[0]}, "expected": _dfs_order(dfs_graph, names[0])},
        {"case_id": "graph_topological_sort", "input_data": {"graph": topo_graph}, "expected": names},
        {"case_id": "dijkstra_shortest_path", "input_data": {"weighted_graph": weighted_graph, "start": names[0]}, "expected": {name: index for index, name in enumerate(names)}},
        {"case_id": "dp_max_subarray_full_core", "input_data": {"nums": max_nums}, "expected": best},
        {"case_id": "unique_paths", "input_data": {"m": grid_dim[0], "n": grid_dim[1]}, "expected": unique_paths},
        {"case_id": "edit_distance", "input_data": {"word1": word1, "word2": word2}, "expected": edit_n},
        {"case_id": "kmp", "input_data": {"text": text, "pattern": pattern}, "expected": text_n - len(pattern)},
        {"case_id": "string_sliding_window_unique", "input_data": {"text": unique_text}, "expected": min(text_n, len(alphabet))},
        {"case_id": "daily_temperatures", "input_data": {"temperatures": temperatures}, "expected": _daily_temperatures(temperatures)},
        {"case_id": "tree_max_depth_full_core", "input_data": {"tree": {"root": names[0], "children": tree_children}}, "expected": graph_n},
        {"case_id": "union_count_components_full_core", "input_data": {"n": union_n, "edges": union_edges}, "expected": 2},
    ]


def scalability_jobs() -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for rank, size in enumerate(SIZE_NAMES):
        for row in _jobs_for_rank(rank):
            jobs.append({**row, "size": size, "scale_rank": rank + 1})
    order = {case_id: index for index, case_id in enumerate(row["case_id"] for row in _jobs_for_rank(0))}
    jobs.sort(key=lambda row: (order[row["case_id"]], row["scale_rank"]))
    return jobs


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
    return round(statistics.mean(values), 3) if values else None


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for size in SIZE_NAMES:
        group = [row for row in rows if row.get("size") == size]
        passed = sum(row.get("ok") is True for row in group)
        summary[size] = {
            "total": len(group),
            "passed": passed,
            "pass_rate": passed / len(group) if group else 0.0,
            "avg_trace_events": _mean(group, "trace_events"),
            "avg_frames": _mean(group, "frames"),
            "avg_html_bytes": _mean(group, "html_bytes"),
            "avg_load_ms": _mean(group, "load_ms"),
            "avg_tti_proxy_ms": _mean(group, "tti_proxy_ms"),
            "avg_step_latency_ms": _mean(group, "avg_step_latency_ms"),
            "avg_js_heap_bytes": _mean(group, "js_heap_bytes"),
            "avg_clipped_elements": _mean(group, "clipped_elements"),
        }
    return summary


def _variant_for_replay(raw: dict[str, Any]) -> SolutionVariant:
    return SolutionVariant(
        id=str(raw.get("id") or "v1"),
        name=str(raw.get("name") or "variant"),
        strategy=str(raw.get("strategy") or ""),
        time_complexity=str(raw.get("time_complexity") or ""),
        space_complexity=str(raw.get("space_complexity") or ""),
        code=str(raw.get("code") or ""),
        tracker_code=str(raw.get("tracker_code") or raw.get("trace_code") or ""),
    )


def materialize_job(job: dict[str, Any], source_row: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    started = time.time()
    target_dir = output_dir / "artifacts" / str(job["case_id"])
    target_dir.mkdir(parents=True, exist_ok=True)
    html_path = target_dir / f"{job['size']}.html"
    try:
        source_path = Path(str(source_row["json"]))
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        source = json.loads(source_path.read_text(encoding="utf-8"))
        raw_variant = (source.get("variants") or [])[0]
        variant = execute_variant(
            _variant_for_replay(raw_variant),
            job["input_data"],
            case_id=job["case_id"],
            family_id=source_row.get("family_id"),
            subfamily_id=source_row.get("subfamily_id"),
        )
        if not results_equivalent(
            variant.result,
            job["expected"],
            case_id=job["case_id"],
            family_id=source_row.get("family_id"),
            subfamily_id=source_row.get("subfamily_id"),
        ):
            raise ValueError(f"result {variant.result!r} != expected {job['expected']!r}")
        assert variant.trace is not None
        trace_errors, trace_warnings = validate_trace(variant.trace)
        process_errors, process_warnings = validate_process(variant.trace)
        if trace_errors or process_errors:
            raise ValueError("; ".join([*trace_errors, *process_errors]))
        scene = compile_scene(variant.trace)
        scene_errors, scene_warnings = validate_scene(scene)
        if scene_errors:
            raise ValueError("; ".join(scene_errors))
        artifact = BuildArtifact(
            problem_title=str(source.get("problem_title") or source_row.get("title") or job["case_id"]),
            input_contract=str(source.get("input_contract") or "scalability replay"),
            input_data=job["input_data"],
            expected_result=job["expected"],
            verifier_result=None,
            variants=[variant],
            scenes={variant.id: scene},
            validation=ValidationReport(
                warnings=[*trace_warnings, *process_warnings, *scene_warnings],
                checks=["frozen solver/tracker replay passed", "trace/process/scene validation passed"],
                release_gate=ReleaseGate(
                    artifact_ready=True,
                    process_ready=True,
                    trace_ready=True,
                    visual_ready=True,
                    multi_solution_ready=False,
                    release_ready=False,
                    blocking_reasons=["scalability replay uses one frozen variant without verifier rerun"],
                ),
            ),
        )
        save_html(artifact, html_path)
        return {
            **job,
            "ok": True,
            "html": str(html_path.relative_to(ROOT)),
            "json": str(html_path.with_suffix(".json").relative_to(ROOT)),
            "trace_events": len(variant.trace.events),
            "frames": len(scene.frames),
            "html_bytes": html_path.stat().st_size,
            "materialize_ms": round((time.time() - started) * 1000, 3),
            "warnings": [*trace_warnings, *process_warnings, *scene_warnings],
        }
    except Exception as exc:
        return {
            **job,
            "ok": False,
            "html": "",
            "json": "",
            "trace_events": None,
            "frames": None,
            "html_bytes": None,
            "materialize_ms": round((time.time() - started) * 1000, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def measure_browser(browser: Any, row: dict[str, Any]) -> dict[str, Any]:
    if not row.get("ok"):
        return row
    html_path = ROOT / str(row["html"])
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text[:500]) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)[:500]))
    try:
        started = time.perf_counter()
        page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=60000)
        load_ms = (time.perf_counter() - started) * 1000
        tti_proxy_ms = page.evaluate(
            """async () => {
                const start = performance.now();
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                return performance.now() - start;
            }"""
        )
        frame_count = page.locator("#timeline .tick").count()
        indices = sorted({0, max(0, frame_count // 4), max(0, frame_count // 2), max(0, 3 * frame_count // 4), max(0, frame_count - 1)})
        step_latencies = []
        for index in indices:
            latency = page.evaluate(
                """index => {
                    const start = performance.now();
                    if (typeof go === 'function') go(index);
                    else {
                        const tick = document.querySelectorAll('#timeline .tick')[index];
                        if (tick) tick.click();
                    }
                    void document.body.offsetHeight;
                    return performance.now() - start;
                }""",
                index,
            )
            step_latencies.append(float(latency))
        crowding = page.evaluate(
            """() => {
                const visible = el => {
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                };
                const nodes = [...document.querySelectorAll('body *')].filter(visible);
                const clipped = nodes.filter(el => el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1).length;
                const heap = performance.memory && performance.memory.usedJSHeapSize || null;
                return {
                    dom_nodes: document.querySelectorAll('*').length,
                    visible_nodes: nodes.length,
                    clipped_elements: clipped,
                    body_scroll_width: document.documentElement.scrollWidth,
                    body_scroll_height: document.documentElement.scrollHeight,
                    viewport_width: innerWidth,
                    viewport_height: innerHeight,
                    horizontal_overflow_px: Math.max(0, document.documentElement.scrollWidth - innerWidth),
                    js_heap_bytes: heap,
                    timeline_ticks: document.querySelectorAll('#timeline .tick').length,
                    scene_objects: document.querySelectorAll('#canvas [data-object-id], #canvas .cell, #canvas .node, #canvas .edge').length
                };
            }"""
        )
        return {
            **row,
            "load_ms": round(load_ms, 3),
            "tti_proxy_ms": round(float(tti_proxy_ms), 3),
            "avg_step_latency_ms": round(statistics.mean(step_latencies), 3) if step_latencies else None,
            "max_step_latency_ms": round(max(step_latencies), 3) if step_latencies else None,
            "step_latency_samples_ms": [round(value, 3) for value in step_latencies],
            **crowding,
            "browser_errors": errors,
            "browser_ok": not errors,
        }
    except Exception as exc:
        return {**row, "browser_ok": False, "browser_errors": [*errors, f"{type(exc).__name__}: {exc}"]}
    finally:
        page.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--materialize-only", action="store_true")
    args = parser.parse_args()
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    source = json.loads(report_path.read_text(encoding="utf-8"))
    source_rows = {str(row.get("case_id")): row for row in source.get("results") or []}
    jobs = scalability_jobs()
    (output_dir / "scalability_inputs.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [materialize_job(job, source_rows[job["case_id"]], output_dir) for job in jobs]
    if not args.materialize_only:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            executable = __import__("os").environ.get("ALGOLAB_CHROMIUM_EXECUTABLE", "")
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=executable if executable and Path(executable).exists() else None,
                args=["--no-sandbox", "--enable-precise-memory-info"],
            )
            try:
                rows = [measure_browser(browser, row) for row in rows]
            finally:
                browser.close()
    summary = summarize_rows(rows)
    payload = {
        "kind": "long_trace_scalability_report",
        "created_at": datetime.now().astimezone().isoformat(),
        "source_report": str(report_path),
        "total": len(rows),
        "passed": sum(row.get("ok") is True for row in rows),
        "browser_passed": sum(row.get("browser_ok") is True for row in rows),
        "by_size": summary,
        "results": rows,
    }
    (output_dir / "long_trace_scalability_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "raw_records.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"total": len(rows), "passed": payload["passed"], "browser_passed": payload["browser_passed"], "by_size": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
