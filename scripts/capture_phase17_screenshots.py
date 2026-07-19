"""Capture real browser screenshots for Phase 17 renderer changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.compiler.scene_compiler import compile_scene
from algolab.renderer.export import save_html
from algolab.schemas.semantic_trace import SemanticTrace, SolutionVariant
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport
from scripts.build_demo_dashboard import build_dashboard


DEFAULT_PHASE17_CASES = (
    "unique_paths",
    "binary_search",
    "dijkstra_shortest_path",
    "kmp",
    "lca",
    "permutations",
    "segment_tree_range_sum",
    "edmonds_karp",
)
VIEWPORTS = {
    "desktop": {"width": 1365, "height": 900},
    "mobile": {"width": 390, "height": 820},
}


def capture_phase17_screenshots(
    *,
    output_dir: Path,
    dashboard_dir: Path,
    demo_ids: tuple[str, ...],
) -> Path:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    dashboard_index = build_dashboard(dashboard_dir, demo_ids=demo_ids, style="stable")
    dashboard = json.loads((dashboard_index.parent / "dashboard.json").read_text(encoding="utf-8"))
    html_targets = [("dashboard_index", dashboard_index)]
    for demo in dashboard.get("demos", []):
        stable_html = str(demo.get("stable_html") or "")
        if stable_html:
            html_targets.append((str(demo.get("id") or "demo"), dashboard_index.parent / stable_html))

    records: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for target_id, html_path in html_targets:
            for viewport_name, viewport in VIEWPORTS.items():
                records.append(
                    _capture_one(
                        browser,
                        target_id=target_id,
                        html_path=html_path,
                        viewport_name=viewport_name,
                        viewport=viewport,
                        output_dir=output_dir,
                    )
                )
        interaction_html = save_html(_interaction_learning_artifact(), output_dir / "phase17_interaction_learning.html")
        records.extend(_capture_interaction_sequence(browser, interaction_html, output_dir))
        browser.close()

    manifest = {
        "schema_version": "phase17-screenshot-manifest-v1",
        "dashboard": str(dashboard_index),
        "demo_ids": list(demo_ids),
        "viewports": VIEWPORTS,
        "screenshots": records,
        "interaction_screenshots": [record for record in records if record.get("kind") == "interaction"],
        "ok": all(record["ok"] for record in records),
    }
    manifest_path = output_dir / "phase17_screenshots.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if not manifest["ok"]:
        failures = [record for record in records if not record["ok"]]
        raise SystemExit("Phase 17 screenshot capture failed: " + json.dumps(failures, ensure_ascii=False))
    return manifest_path


def _capture_one(
    browser: Any,
    *,
    target_id: str,
    html_path: Path,
    viewport_name: str,
    viewport: dict[str, int],
    output_dir: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport=viewport)
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    screenshot_path = output_dir / f"{_safe_name(target_id)}_{viewport_name}.png"
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(500)
        body_text = page.locator("body").inner_text().strip()
        if page.locator("#canvas").count():
            canvas_text = page.locator("#canvas").inner_text().strip()
            if not canvas_text:
                errors.append("#canvas is empty")
        page.screenshot(path=str(screenshot_path), full_page=True)
        size = screenshot_path.stat().st_size if screenshot_path.exists() else 0
        if not body_text:
            errors.append("body text is empty")
        if size <= 0:
            errors.append("screenshot file is empty")
        return {
            "kind": "page",
            "target_id": target_id,
            "html": str(html_path),
            "viewport": viewport_name,
            "screenshot": str(screenshot_path),
            "bytes": size,
            "ok": not errors,
            "errors": errors,
        }
    except Exception as exc:
        return {
            "kind": "page",
            "target_id": target_id,
            "html": str(html_path),
            "viewport": viewport_name,
            "screenshot": str(screenshot_path),
            "bytes": 0,
            "ok": False,
            "errors": [f"{type(exc).__name__}: {exc}", *errors],
        }
    finally:
        page.close()


def _capture_interaction_sequence(
    browser: Any,
    interaction_html: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    records.extend(_capture_formula_and_regenerate_sequence(browser, interaction_html, output_dir))
    records.append(_capture_wrong_option_feedback(browser, interaction_html, output_dir))
    return records


def _interaction_learning_artifact() -> BuildArtifact:
    """Minimal fixture for browser-only interaction evidence."""

    traces = {
        "unique_paths": SemanticTrace.model_validate(
            {
                "algorithm": "不同路径",
                "input_data": {"m": 2, "n": 2},
                "result": 2,
                "pseudocode": ["初始化边界", "dp[i][j] = dp[i-1][j] + dp[i][j-1]"],
                "events": [
                    {
                        "step": 0,
                        "op": "create",
                        "targets": [{"id": "dp"}],
                        "state": {"dp": [[1, 1], [1, 0]], "answer": None},
                        "reason": "第一行和第一列都只有一种走法。",
                        "teaching": {
                            "what": "初始化 DP 边界",
                            "why": "只能向右或向下移动，所以边界格子没有分支。",
                            "invariant": "dp[i][j] 表示到达该格子的路径数。",
                            "hint": "先看第一行和第一列。",
                        },
                    },
                    {
                        "step": 1,
                        "op": "set",
                        "targets": [{"id": "dp[1][1]"}],
                        "deps": [{"id": "dp[0][1]"}, {"id": "dp[1][0]"}],
                        "value": 2,
                        "before": 0,
                        "after": 2,
                        "role": "answer",
                        "state": {"dp": [[1, 1], [1, 2]], "answer": 2},
                        "reason": "终点只能从上方或左方进入。",
                        "teaching": {
                            "what": "计算终点格子的路径数",
                            "why": "所有到达终点的路径最后一步必然来自上方或左方。",
                            "formula": "dp[1][1] = dp[0][1] + dp[1][0] = 1 + 1 = 2",
                            "invariant": "每个已填格子都等于其上方和左方路径数之和。",
                            "common_mistake": "不要把两个来源方向之外的格子也加进去。",
                            "hint": "只看 dp[0][1] 和 dp[1][0]。",
                        },
                        "interaction": {
                            "type": "input",
                            "prompt": "dp[1][1] 应该是多少？",
                            "answer": "2",
                            "explanation": "上方 1 条路径，左方 1 条路径，相加为 2。",
                            "wrong_explanation": "如果不是 2，通常是漏加了一个来源或多加了其他格子。",
                        },
                    },
                ],
            }
        ),
        "binary_search": SemanticTrace.model_validate(
            {
                "algorithm": "二分查找",
                "input_data": {"nums": [1, 3, 5, 7], "target": 5},
                "result": 2,
                "pseudocode": ["取 mid", "比较 nums[mid] 和 target", "收缩区间"],
                "events": [
                    {
                        "step": 0,
                        "op": "create",
                        "targets": [{"id": "nums"}],
                        "state": {"nums": [1, 3, 5, 7], "left": 0, "right": 3, "target": 5},
                        "reason": "搜索范围从整个有序数组开始。",
                    },
                    {
                        "step": 1,
                        "op": "compare",
                        "targets": [{"id": "nums[1]"}],
                        "deps": [{"id": "target"}],
                        "value": "3 < 5",
                        "state": {"nums": [1, 3, 5, 7], "left": 0, "right": 3, "mid": 1, "target": 5},
                        "reason": "nums[mid] 小于 target，目标只能在右半边。",
                        "teaching": {
                            "what": "比较 mid 与 target",
                            "why": "数组有序，mid 左侧都不可能等于更大的 target。",
                            "invariant": "如果 target 存在，它仍在 [left, right] 内。",
                            "common_mistake": "不要在 nums[mid] 偏小时继续保留左半边。",
                            "hint": "比较 nums[1]=3 和 target=5。",
                        },
                        "interaction": {
                            "type": "choice",
                            "prompt": "下一步应该保留哪一边？",
                            "options": ["保留左半边", "保留右半边"],
                            "answer": "保留右半边",
                            "explanation": "3 小于 5，目标只能在 mid 右侧。",
                            "wrong_explanation": "保留左半边会丢掉可能包含 target 的右侧区间。",
                            "option_explanations": {
                                "保留左半边": "错误选项解释：左半边的值都不大于 nums[mid]=3，无法包含 target=5。"
                            },
                        },
                    },
                ],
            }
        ),
    }
    variants = [
        SolutionVariant(
            id="unique_paths",
            name="不同路径",
            strategy="用 DP 公式解释状态转移。",
            time_complexity="O(mn)",
            space_complexity="O(mn)",
            code="def solve(input_data):\n    return 2",
            tracker_code="def trace(input_data):\n    return {}",
            result=traces["unique_paths"].result,
            trace=traces["unique_paths"],
        ),
        SolutionVariant(
            id="binary_search",
            name="二分查找",
            strategy="通过预测区间收缩方向检查理解。",
            time_complexity="O(log n)",
            space_complexity="O(1)",
            code="def solve(input_data):\n    return 2",
            tracker_code="def trace(input_data):\n    return {}",
            result=traces["binary_search"].result,
            trace=traces["binary_search"],
        ),
    ]
    return BuildArtifact(
        problem_title="交互学习检查点",
        input_contract="覆盖公式展开和错误选项反馈。",
        input_data={"fixture": "interaction_learning"},
        variants=variants,
        scenes={variant.id: compile_scene(traces[variant.id]) for variant in variants},
        validation=ValidationReport(
            checks=["interaction learning fixture"],
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                multi_solution_ready=True,
                release_ready=True,
            ),
        ),
    )


def _capture_formula_and_regenerate_sequence(browser: Any, html_path: Path, output_dir: Path) -> list[dict[str, Any]]:
    errors: list[str] = []
    page = browser.new_page(viewport=VIEWPORTS["desktop"])
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    records: list[dict[str, Any]] = []
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(500)
        if page.locator("#tabs .tab").filter(has_text="不同路径").count():
            page.locator("#tabs .tab").filter(has_text="不同路径").first.click()
            page.wait_for_timeout(100)
        formula_index = page.evaluate(
            "() => frames().findIndex(f => f.teaching && f.teaching.formula && (f.evidence?.targets || []).length)"
        )
        if int(formula_index) < 0:
            errors.append("no formula expansion frame")
        else:
            page.evaluate("(i) => go(i)", formula_index)
            page.wait_for_timeout(120)
        records.append(
            _record_screenshot(
                page,
                output_dir / "phase17_interaction_before_formula_desktop.png",
                target_id="interaction_formula_before",
                html_path=html_path,
                phase="before",
                errors=list(errors),
            )
        )
        teaching_text = page.locator("#teaching").inner_text()
        if "当前步骤" in teaching_text or "为什么" in teaching_text:
            errors.append("teaching panel repeats step title/why text")
        if page.locator("#interaction [data-learning-checkpoint]").count():
            if "常见错误" in teaching_text or "提示" in teaching_text:
                errors.append("teaching panel repeats hint/common mistake while interaction is present")
        if page.locator("#teaching .formula-expander summary").count():
            page.locator("#teaching .formula-expander summary").first.click()
            page.wait_for_timeout(120)
            if "只读当前 trace" not in page.locator("#teaching .formula-expander").first.inner_text():
                errors.append("formula expansion source text missing")
        else:
            errors.append("formula expander missing")
        records.append(
            _record_screenshot(
                page,
                output_dir / "phase17_interaction_formula_expanded_desktop.png",
                target_id="interaction_formula_expanded",
                html_path=html_path,
                phase="after_click",
                errors=list(errors),
            )
        )
        main_text = page.locator(".app > main").inner_text()
        for phrase in ("题目与输入", "修改输入", "输入重新生成", "系统校验"):
            if phrase in main_text:
                errors.append(f"removed main section still visible: {phrase}")
        records.append(
            _record_screenshot(
                page,
                output_dir / "phase17_interaction_compact_main_desktop.png",
                target_id="interaction_compact_main",
                html_path=html_path,
                phase="after_removed_sections_check",
                errors=list(errors),
            )
        )
    except Exception as exc:
        records.append(
            {
                "kind": "interaction",
                "target_id": "interaction_formula_sequence",
                "html": str(html_path),
                "viewport": "desktop",
                "phase": "exception",
                "screenshot": "",
                "bytes": 0,
                "ok": False,
                "errors": [f"{type(exc).__name__}: {exc}", *errors],
            }
        )
    finally:
        page.close()
    return records


def _capture_wrong_option_feedback(browser: Any, html_path: Path, output_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    page = browser.new_page(viewport=VIEWPORTS["desktop"])
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(500)
        if page.locator("#tabs .tab").filter(has_text="二分查找").count():
            page.locator("#tabs .tab").filter(has_text="二分查找").first.click()
            page.wait_for_timeout(100)
        choice = page.evaluate(
            """() => {
                const index = frames().findIndex(f => {
                    const interaction = f.interaction || {};
                    return interaction.type === 'choice'
                        && interaction.option_explanations
                        && Object.keys(interaction.option_explanations).length;
                });
                if (index < 0) return { index };
                const interaction = frames()[index].interaction;
                const wrong = (interaction.options || []).find(option => String(option) !== String(interaction.answer));
                return { index, wrong, explanation: interaction.option_explanations[String(wrong)] || '' };
            }"""
        )
        if int(choice.get("index", -1)) < 0 or not choice.get("wrong"):
            errors.append("no choice interaction with option explanation")
        else:
            page.evaluate("(i) => go(i)", choice["index"])
            page.wait_for_timeout(100)
            page.locator("#interaction button").filter(has_text=str(choice["wrong"])).first.click()
            page.wait_for_timeout(120)
            feedback = page.locator("#feedback").inner_text()
            source = page.locator("#feedback").get_attribute("data-source")
            if "错误选项解释" not in feedback:
                errors.append("wrong option feedback missing")
            if feedback.count("错误选项解释") > 1:
                errors.append("wrong option feedback repeats explanation prefix")
            if str(choice.get("explanation") or "") not in feedback:
                errors.append("option explanation text missing")
            if source != "interaction.option_explanations":
                errors.append(f"wrong feedback source: {source}")
            frame_status = page.locator("#learning-log-frame").inner_text()
            if "已提交" not in frame_status or "需要订正" not in frame_status:
                errors.append(f"learning frame status missing wrong answer state: {frame_status}")
            if page.locator("details[data-learning-log] summary").count():
                page.locator("details[data-learning-log] summary").first.click()
                page.wait_for_timeout(120)
                preview = page.locator("#learning-log-preview").inner_text()
                if "提交错误" not in preview:
                    errors.append("learning log preview missing submit error event")
            else:
                errors.append("learning log details missing")
        return _record_screenshot(
            page,
            output_dir / "phase17_interaction_wrong_feedback_desktop.png",
            target_id="interaction_wrong_feedback",
            html_path=html_path,
            phase="error_feedback",
            errors=errors,
        )
    except Exception as exc:
        return {
            "kind": "interaction",
            "target_id": "interaction_wrong_feedback",
            "html": str(html_path),
            "viewport": "desktop",
            "phase": "exception",
            "screenshot": "",
            "bytes": 0,
            "ok": False,
            "errors": [f"{type(exc).__name__}: {exc}", *errors],
        }
    finally:
        page.close()


def _record_screenshot(
    page: Any,
    screenshot_path: Path,
    *,
    target_id: str,
    html_path: Path,
    phase: str,
    errors: list[str],
) -> dict[str, Any]:
    page.screenshot(path=str(screenshot_path), full_page=True)
    size = screenshot_path.stat().st_size if screenshot_path.exists() else 0
    body_text = page.locator("body").inner_text().strip()
    record_errors = list(errors)
    if not body_text:
        record_errors.append("body text is empty")
    if size <= 0:
        record_errors.append("screenshot file is empty")
    return {
        "kind": "interaction",
        "target_id": target_id,
        "html": str(html_path),
        "viewport": "desktop",
        "phase": phase,
        "screenshot": str(screenshot_path),
        "bytes": size,
        "ok": not record_errors,
        "errors": record_errors,
    }


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "page"


def main() -> int:
    parser = argparse.ArgumentParser(description="为 Phase 17 renderer 变更生成真实浏览器截图")
    parser.add_argument("--output-dir", type=Path, default=Path("output/phase17_screenshots"))
    parser.add_argument("--dashboard-dir", type=Path, default=Path("output/phase17_dashboard"))
    parser.add_argument("--case", action="append", default=[], help="指定 demo case id，可重复传入")
    args = parser.parse_args()

    demo_ids = tuple(args.case or DEFAULT_PHASE17_CASES)
    manifest_path = capture_phase17_screenshots(
        output_dir=args.output_dir,
        dashboard_dir=args.dashboard_dir,
        demo_ids=demo_ids,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
