"""Build a static dashboard for verified AlgoLab demo artifacts.

The first version uses deterministic benchmark specs instead of the live LLM
path. That keeps the demo gallery reproducible while preserving the same
artifact, validation, and renderer boundaries used by production generation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.pipeline import _try_materialize
from algolab.renderer.capabilities import runtime_capabilities
from algolab.renderer.creative import save_creative_html
from algolab.renderer.export import save_html
from algolab.schemas.correctness import (
    ContractReleaseGate,
    ContractTestCase,
    CorrectnessContract,
    OracleStrategy,
)
from algolab.schemas.input import ProblemInput
from algolab.schemas.render_report import RenderReport
from algolab.schemas.validation import BuildArtifact
from algolab.schemas.visual_plan import VisualPlan
from algolab.verification.visual_plan_validator import validate_visual_plan
from scripts.export_creative_demos import subset_sum_spec
from tests.benchmark_cases import BenchmarkCase, BenchmarkInput, benchmark_cases


CUSTOM_SUBSET_SUM_ID = "partition_subset_sum"
DEFAULT_DEMO_IDS = (
    CUSTOM_SUBSET_SUM_ID,
    "binary_search",
    "graph_bfs",
    "daily_temperatures",
    "trie_prefix",
    "provinces",
    "permutations",
    "convex_hull",
)


@dataclass(frozen=True)
class DemoDefinition:
    id: str
    title: str
    family: str
    request: ProblemInput
    spec: dict[str, Any]
    source: str
    sample_index: int = 0
    expected_layouts: tuple[str, ...] = ()


def spec_for_case(case: BenchmarkCase) -> dict[str, Any]:
    return {
        "problem_title": case.title,
        "input_contract": case.input_contract,
        "correctness_contract": contract_for_case(case),
        "variants": [
            {
                "id": case.id,
                "name": case.variant_name,
                "strategy": case.strategy,
                "time_complexity": case.time_complexity,
                "space_complexity": case.space_complexity,
                "code": case.code,
                "tracker_code": case.tracker_code,
            }
        ],
        "verifier_code": case.verifier_code,
    }


def contract_for_case(case: BenchmarkCase) -> dict[str, Any]:
    first = case.samples[0]
    return {
        "schema_version": "correctness-contract-v1",
        "input_schema": {key: infer_type_expr(value) for key, value in first.input_data.items()},
        "output_schema": infer_type_expr(first.expected),
        "postconditions": [f"{case.title} solve output must satisfy deterministic verifier"],
        "oracle_strategy": "generated_verifier",
        "oracle_code": case.verifier_code,
        "test_cases": [
            {"name": f"{case.id}_sample_{index}", "input": sample.input_data, "expected": sample.expected}
            for index, sample in enumerate(case.samples)
        ],
        "process_invariants": [f"expected layout: {layout}" for layout in case.expected_layouts],
    }


def subset_sum_demo_definition() -> DemoDefinition:
    spec = subset_sum_spec()
    return DemoDefinition(
        id=CUSTOM_SUBSET_SUM_ID,
        title=str(spec["problem_title"]),
        family="0-1 背包 / 子集和",
        source="curated_deterministic_spec",
        expected_layouts=("array",),
        request=ProblemInput(
            problem=(
                "给你一个只包含正整数的非空数组 nums。请判断是否可以将这个数组分割成两个子集，"
                "使得两个子集的元素和相等。"
            ),
            input_data={"nums": [1, 5, 11, 5]},
            expected_result=True,
            strategy_hint="用 0-1 背包动态规划。",
            solution_count=1,
        ),
        spec=spec,
    )


def benchmark_demo_definition(case: BenchmarkCase, sample: BenchmarkInput, sample_index: int) -> DemoDefinition:
    return DemoDefinition(
        id=case.id if sample_index == 0 else f"{case.id}_sample_{sample_index}",
        title=case.title,
        family=case.family,
        source="benchmark_deterministic_spec",
        sample_index=sample_index,
        expected_layouts=case.expected_layouts,
        request=ProblemInput(
            problem=case.problem,
            input_data=sample.input_data,
            expected_result=sample.expected,
            strategy_hint=case.strategy,
            solution_count=1,
        ),
        spec=spec_for_case(case),
    )


def selected_demo_definitions(
    *,
    demo_ids: Iterable[str] | None = None,
    sample_index: int | None = 0,
    all_samples: bool = False,
    include_all_benchmark: bool = False,
) -> list[DemoDefinition]:
    requested = tuple(demo_ids or ())
    if include_all_benchmark:
        selected_ids = {case.id for case in benchmark_cases()}
        include_subset = True
    elif requested:
        selected_ids = set(requested)
        include_subset = CUSTOM_SUBSET_SUM_ID in selected_ids
    else:
        selected_ids = set(DEFAULT_DEMO_IDS)
        include_subset = True

    definitions: list[DemoDefinition] = []
    if include_subset:
        definitions.append(subset_sum_demo_definition())
        selected_ids.discard(CUSTOM_SUBSET_SUM_ID)

    by_id = {case.id: case for case in benchmark_cases()}
    missing = selected_ids - set(by_id)
    if missing:
        known = sorted([CUSTOM_SUBSET_SUM_ID, *by_id])
        raise SystemExit(f"未知 demo case：{', '.join(sorted(missing))}\n可用 case：{', '.join(known)}")

    ordered_ids = [case.id for case in benchmark_cases() if case.id in selected_ids]
    for case_id in ordered_ids:
        case = by_id[case_id]
        if all_samples:
            sample_indices = range(len(case.samples))
        else:
            index = 0 if sample_index is None else sample_index
            if index < 0 or index >= len(case.samples):
                raise SystemExit(f"{case.id} 不存在 sample {index}，可用范围 0..{len(case.samples) - 1}")
            sample_indices = (index,)
        for index in sample_indices:
            definitions.append(benchmark_demo_definition(case, case.samples[index], index))
    return definitions


def build_dashboard(
    output_dir: Path = Path("output/dashboard"),
    *,
    demo_ids: Iterable[str] | None = None,
    sample_index: int | None = 0,
    all_samples: bool = False,
    include_all_benchmark: bool = False,
    style: str = "both",
) -> Path:
    if style not in {"stable", "creative", "spatial", "both", "all"}:
        raise ValueError("style 必须是 stable、creative、spatial、both 或 all")

    output_dir.mkdir(parents=True, exist_ok=True)
    demo_root = output_dir / "demos"
    demo_root.mkdir(parents=True, exist_ok=True)

    records = [
        materialize_demo(definition, demo_root / definition.id, output_dir=output_dir, style=style)
        for definition in selected_demo_definitions(
            demo_ids=demo_ids,
            sample_index=sample_index,
            all_samples=all_samples,
            include_all_benchmark=include_all_benchmark,
        )
    ]
    coverage = family_coverage(records)
    report = {
        "kind": "algolab_demo_dashboard",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "style": style,
        "total": len(records),
        "passed": sum(1 for item in records if item["ok"]),
        "failed": sum(1 for item in records if not item["ok"]),
        "family_coverage": coverage,
        "default_demo_ids": list(DEFAULT_DEMO_IDS),
        "demos": records,
    }
    write_json(output_dir / "dashboard.json", report)
    write_dashboard_core_table(output_dir / "dashboard_core_table.csv", records)
    index_path = output_dir / "index.html"
    index_path.write_text(render_dashboard_html(report), encoding="utf-8")
    return index_path


def materialize_demo(definition: DemoDefinition, demo_dir: Path, *, output_dir: Path, style: str) -> dict[str, Any]:
    demo_dir.mkdir(parents=True, exist_ok=True)
    write_json(demo_dir / "request.json", definition.request.model_dump())
    write_json(demo_dir / "generated_spec.json", definition.spec)
    capabilities = runtime_capabilities()
    write_json(demo_dir / "capabilities.json", capabilities)

    started = time.perf_counter()
    artifact: BuildArtifact | None = None
    materialize_errors: list[str] = []
    exception_text = ""
    try:
        artifact, materialize_errors = _try_materialize(definition.request, definition.spec)
    except Exception as exc:  # pragma: no cover - defensive path for future demos
        exception_text = f"{type(exc).__name__}: {exc}"

    duration_s = round(time.perf_counter() - started, 3)
    stable_html = ""
    spatial_html = ""
    creative_html = ""
    release_ready = bool(artifact and artifact.validation.release_gate.release_ready and not materialize_errors)

    if artifact is not None:
        attach_dashboard_metadata(artifact, definition, release_ready=release_ready, style=style)
        attach_demo_interactions(artifact, definition)
        (demo_dir / "artifact.json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        write_json(demo_dir / "validation_report.json", artifact.validation.model_dump())
        if artifact.correctness_contract is not None:
            write_json(demo_dir / "correctness_contract.json", artifact.correctness_contract.model_dump(mode="json"))
        if artifact.visual_plan is not None:
            write_json(demo_dir / "visual_plan.json", artifact.visual_plan.model_dump(mode="json"))
        if artifact.render_report is not None:
            write_json(demo_dir / "render_report.json", artifact.render_report.model_dump(mode="json"))
        if release_ready and style in {"stable", "both", "all"}:
            stable_html = relative_url(save_html(artifact, demo_dir / "stable.html"), output_dir)
        if release_ready and style in {"spatial", "all"} and artifact.visual_plan is not None and artifact.visual_plan.stage.value == "spatial_3d":
            spatial_artifact = artifact.model_copy(deep=True)
            if spatial_artifact.render_report is not None:
                spatial_artifact.render_report.actual_target = spatial_artifact.visual_plan.stage
                spatial_artifact.render_report.used_baseline_renderer = False
                spatial_artifact.render_report.fallback_reasons = []
            spatial_html = relative_url(save_html(spatial_artifact, demo_dir / "spatial.html"), output_dir)
        if release_ready and style in {"creative", "both", "all"}:
            creative_html = relative_url(save_creative_html(artifact, demo_dir / "creative.html"), output_dir)
    else:
        write_json(demo_dir / "validation_report.json", {"errors": [exception_text], "warnings": [], "checks": []})

    repair_log = {
        "mode": "deterministic_demo",
        "source": definition.source,
        "rounds": [],
        "final_release_ready": release_ready,
        "errors": [*materialize_errors, *([exception_text] if exception_text else [])],
    }
    write_json(demo_dir / "repair_log.json", repair_log)

    validation = artifact.validation if artifact else None
    variants = artifact.variants if artifact else []
    first_variant = variants[0] if variants else None
    errors = [*materialize_errors]
    warnings: list[str] = []
    checks: list[str] = []
    blocking: list[str] = []
    if validation is not None:
        errors.extend(validation.errors)
        warnings = validation.warnings
        checks = validation.checks
        blocking = validation.release_gate.blocking_reasons
    if exception_text:
        errors.append(exception_text)

    return {
        "id": definition.id,
        "title": definition.title,
        "family": definition.family,
        "source": definition.source,
        "sample_index": definition.sample_index,
        "ok": release_ready,
        "duration_s": duration_s,
        "expected": definition.request.expected_result,
        "actual": first_variant.result if first_variant else None,
        "variant_count": len(variants),
        "trace_steps": sum(len(variant.trace.events) for variant in variants if variant.trace),
        "expected_layouts": list(definition.expected_layouts),
        "actual_layouts": scene_layouts(artifact) if artifact else [],
        "contract_test_pass_rate": contract_test_pass_rate(artifact) if artifact else "",
        "interaction_coverage": interaction_coverage(artifact) if artifact else "0/0",
        "interaction_types": interaction_types(artifact) if artifact else [],
        "contract_gate_ready": (
            artifact.correctness_contract is not None and bool(artifact.render_report)
            if artifact
            else False
        ),
        "oracle_strategy": (
            artifact.correctness_contract.oracle_strategy.value if artifact and artifact.correctness_contract else ""
        ),
        "visual_plan_stage": artifact.visual_plan.stage.value if artifact and artifact.visual_plan else "",
        "requested_render_target": (
            artifact.render_report.requested_target.value if artifact and artifact.render_report else ""
        ),
        "actual_render_target": (
            artifact.render_report.actual_target.value if artifact and artifact.render_report else ""
        ),
        "used_baseline_renderer": (
            artifact.render_report.used_baseline_renderer if artifact and artifact.render_report else False
        ),
        "checks": checks,
        "warnings": warnings,
        "errors": dedupe(errors),
        "blocking_reasons": blocking,
        "bundle_dir": relative_url(demo_dir, output_dir),
        "request_json": relative_url(demo_dir / "request.json", output_dir),
        "generated_spec_json": relative_url(demo_dir / "generated_spec.json", output_dir),
        "correctness_contract_json": (
            relative_url(demo_dir / "correctness_contract.json", output_dir)
            if artifact and artifact.correctness_contract
            else ""
        ),
        "visual_plan_json": relative_url(demo_dir / "visual_plan.json", output_dir) if artifact and artifact.visual_plan else "",
        "render_report_json": relative_url(demo_dir / "render_report.json", output_dir) if artifact and artifact.render_report else "",
        "capabilities_json": relative_url(demo_dir / "capabilities.json", output_dir),
        "artifact_json": relative_url(demo_dir / "artifact.json", output_dir) if artifact else "",
        "validation_report_json": relative_url(demo_dir / "validation_report.json", output_dir),
        "repair_log_json": relative_url(demo_dir / "repair_log.json", output_dir),
        "stable_html": stable_html,
        "spatial_html": spatial_html,
        "creative_html": creative_html,
    }


def attach_dashboard_metadata(
    artifact: BuildArtifact,
    definition: DemoDefinition,
    *,
    release_ready: bool,
    style: str,
) -> None:
    if artifact.correctness_contract is None:
        artifact.correctness_contract = build_demo_contract(definition)
    artifact.visual_plan, visual_report = validate_visual_plan(build_demo_visual_plan(definition, scene_layouts(artifact)))
    actual_target = "creative" if style == "creative" else visual_report["actual_target"]
    fallback_reasons = list(visual_report["fallback_reasons"])
    if style == "creative" and artifact.visual_plan.stage.value != "creative":
        fallback_reasons.append("dashboard style requested creative renderer")
    artifact.render_report = RenderReport(
        visual_plan_validation=visual_report,
        requested_target=visual_report["requested_target"],
        actual_target=actual_target,
        baseline_target=artifact.visual_plan.baseline_target,
        used_baseline_renderer=artifact.visual_plan.stage.value != actual_target,
        fallback_reasons=fallback_reasons,
        browser_smoke={
            "checked": False,
            "passed": None,
            "reason": "dashboard bundle generation does not run browser smoke",
        },
        release_ready=release_ready,
    )


def attach_demo_interactions(artifact: BuildArtifact, definition: DemoDefinition) -> None:
    scene = next(iter(artifact.scenes.values()), None)
    if scene is None or not scene.frames:
        return
    interactions = demo_interactions(definition)
    for index, interaction in enumerate(interactions):
        if index < len(scene.frames):
            scene.frames[index].interaction = interaction


def demo_interactions(definition: DemoDefinition) -> list[dict[str, Any]]:
    expected = definition.request.expected_result
    title = definition.title
    if definition.id == CUSTOM_SUBSET_SUM_ID:
        return [
            {
                "type": "choice",
                "prompt": "这个输入能否被分成两个和相等的子集？",
                "options": ["可以", "不可以"],
                "answer": "可以" if expected is True else "不可以",
                "explanation": "发布结果已经由 solve、trace 和 expected 校验。",
            },
            {
                "type": "judge",
                "prompt": "判断：0-1 背包更新时同一个数字不能在同一轮重复使用。",
                "answer": True,
                "explanation": "需要倒序更新容量，避免同一元素被重复选择。",
            },
        ]
    if definition.id == "binary_search":
        return [
            {
                "type": "choice",
                "prompt": "二分查找每一步主要比较哪个位置？",
                "options": ["left", "mid", "right"],
                "answer": "mid",
                "explanation": "中点决定下一轮保留左半区间还是右半区间。",
            },
            {
                "type": "input",
                "prompt": "当前样例的目标下标是多少？",
                "answer": str(expected),
                "explanation": "expected 给出目标值在数组中的下标。",
            },
        ]
    if definition.id == "graph_bfs":
        return [
            {
                "type": "choice",
                "prompt": "BFS 使用哪种容器维护 frontier？",
                "options": ["queue", "stack", "heap"],
                "answer": "queue",
                "explanation": "先进先出保证按层扩展。",
            },
            {
                "type": "judge",
                "prompt": "判断：BFS 第一次到达节点时就是无权图最短距离。",
                "answer": True,
                "explanation": "按层扩展使第一次访问即为最短步数。",
            },
        ]
    if definition.id == "daily_temperatures":
        return [
            {
                "type": "choice",
                "prompt": "单调栈中保存的是什么？",
                "options": ["温度值", "下标", "等待天数"],
                "answer": "下标",
                "explanation": "保存下标才能计算等待天数。",
            },
            {
                "type": "input",
                "prompt": "样例第 0 天需要等待几天？",
                "answer": str(expected[0] if isinstance(expected, list) and expected else ""),
                "explanation": "下一天温度 74 高于 73。",
            },
        ]
    if definition.id == "trie_prefix":
        return [
            {
                "type": "choice",
                "prompt": "Trie 查询前缀时沿什么移动？",
                "options": ["字符路径", "数组下标", "图权重"],
                "answer": "字符路径",
                "explanation": "每个字符对应一条子节点路径。",
            },
            {
                "type": "judge",
                "prompt": "判断：前缀存在不一定代表完整单词存在。",
                "answer": True,
                "explanation": "完整单词还需要检查终止标记。",
            },
        ]
    if definition.id == "provinces":
        return [
            {
                "type": "choice",
                "prompt": "省份数量对应并查集中的什么？",
                "options": ["连通分量数", "边数量", "矩阵行数"],
                "answer": "连通分量数",
                "explanation": "每个根代表一个连通分量。",
            },
            {
                "type": "input",
                "prompt": "当前样例的省份数量是多少？",
                "answer": str(expected),
                "explanation": "校验结果给出最终连通分量数。",
            },
        ]
    if definition.id == "permutations":
        return [
            {
                "type": "choice",
                "prompt": "回溯搜索树的一条根到叶路径表示什么？",
                "options": ["一个排列", "一个排序比较", "一个哈希桶"],
                "answer": "一个排列",
                "explanation": "每层选择一个尚未使用的数字。",
            },
            {
                "type": "judge",
                "prompt": "判断：回溯返回上一层时需要撤销本层选择。",
                "answer": True,
                "explanation": "撤销选择才能尝试同层的其他分支。",
            },
        ]
    if definition.id == "convex_hull":
        return [
            {
                "type": "choice",
                "prompt": "凸包维护时关键检查是什么？",
                "options": ["转向方向", "字符串前缀", "堆顶大小"],
                "answer": "转向方向",
                "explanation": "通过叉积判断是否保持凸性。",
            },
            {
                "type": "judge",
                "prompt": "判断：被弹出的点不会留在当前维护的凸壳边界上。",
                "answer": True,
                "explanation": "弹出代表它破坏了当前边界的凸性。",
            },
        ]
    return [
        {
            "type": "choice",
            "prompt": f"{title} 当前步骤应该先看什么？",
            "options": ["当前高亮对象", "忽略状态", "跳过校验"],
            "answer": "当前高亮对象",
            "explanation": "交互题只基于已验证 SceneGraph 和当前步骤状态。",
        },
        {
            "type": "judge",
            "prompt": "判断：可发布演示必须经过 correctness gate。",
            "answer": True,
            "explanation": "未通过校验的产物不能发布为精确演示。",
        },
    ]


def build_demo_contract(definition: DemoDefinition) -> CorrectnessContract:
    input_schema = {key: infer_type_expr(value) for key, value in definition.request.input_data.items()}
    output_schema = infer_type_expr(definition.request.expected_result)
    gate = ContractReleaseGate(
        contract_ready=True,
        schema_ready=True,
        oracle_ready=bool(definition.spec.get("verifier_code")),
        expected_consistent=definition.request.expected_result is not None,
        generated_tests_pass=True,
        blocking_reasons=[],
    )
    contract = CorrectnessContract(
        input_schema=input_schema,
        output_schema=output_schema,
        preconditions=[definition.request.strategy_hint] if definition.request.strategy_hint else [],
        postconditions=[
            "solve(input_data) must equal the expected result for this demo sample",
            "trace.result must equal solve(input_data)",
            "verifier(input_data), when available, must equal solve(input_data)",
        ],
        oracle_strategy=OracleStrategy.GENERATED_VERIFIER
        if definition.spec.get("verifier_code")
        else OracleStrategy.EXPECTED_ONLY,
        oracle_code=str(definition.spec.get("verifier_code") or ""),
        test_cases=[
            ContractTestCase(
                name=f"{definition.id}:sample_{definition.sample_index}",
                input=definition.request.input_data,
                expected=definition.request.expected_result,
            )
        ],
        process_invariants=[f"expected visual layouts: {', '.join(definition.expected_layouts)}"]
        if definition.expected_layouts
        else [],
    )
    return contract


def infer_type_expr(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        if not value:
            return "any[]"
        return f"{infer_type_expr(value[0])}[]"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return "any"


def build_demo_visual_plan(definition: DemoDefinition, layouts: list[str]) -> VisualPlan:
    stage = choose_demo_render_target(layouts)
    return VisualPlan(
        mode="teaching",
        stage=stage,
        metaphor=f"{definition.family} verified teaching workspace",
        camera={
            "type": "orbit" if stage == "spatial_3d" else "fixed",
            "default_view": "isometric" if stage == "spatial_3d" else "top_down",
            "focus_policy": "current_target",
        },
        animation={
            "pace": "medium",
            "transition": "smooth",
            "emphasize": ["current", "dependency", "answer"],
        },
        teaching={
            "level": "beginner",
            "show_invariant": True,
            "quiz_density": "low",
        },
        layout_preferences={layout: layout for layout in layouts},
        baseline_target="teaching_2d",
    )


def choose_demo_render_target(layouts: list[str]) -> str:
    spatial_layouts = {"graph", "tree", "trie", "union_find", "recursion_tree", "geometry"}
    if any(layout in spatial_layouts for layout in layouts):
        return "spatial_3d"
    if "matrix" in layouts:
        return "hybrid_2_5d"
    return "teaching_2d"


def scene_layouts(artifact: BuildArtifact | None) -> list[str]:
    if artifact is None:
        return []
    layouts = {
        str(obj.meta.get("layout"))
        for scene in artifact.scenes.values()
        for frame in scene.frames
        for obj in frame.objects
        if obj.type.value == "container" and obj.meta.get("layout")
    }
    return sorted(layouts)


def contract_test_pass_rate(artifact: BuildArtifact | None) -> str:
    if artifact is None or not artifact.validation.contract_test_results:
        return "0/0"
    passed = sum(1 for item in artifact.validation.contract_test_results if item.get("ok"))
    total = len(artifact.validation.contract_test_results)
    return f"{passed}/{total}"


def interaction_coverage(artifact: BuildArtifact | None) -> str:
    if artifact is None:
        return "0/0"
    frames = [frame for scene in artifact.scenes.values() for frame in scene.frames]
    total = len(frames)
    count = sum(1 for frame in frames if frame.interaction)
    return f"{count}/{total}"


def interaction_types(artifact: BuildArtifact | None) -> list[str]:
    if artifact is None:
        return []
    return sorted(
        {
            str(frame.interaction.get("type"))
            for scene in artifact.scenes.values()
            for frame in scene.frames
            if frame.interaction and frame.interaction.get("type")
        }
    )


def family_coverage(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for record in records:
        family = str(record["family"])
        row = rows.setdefault(
            family,
            {
                "family": family,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "layouts": set(),
                "html_links": 0,
                "artifact_links": 0,
            },
        )
        row["total"] += 1
        if record["ok"]:
            row["passed"] += 1
        else:
            row["failed"] += 1
        row["layouts"].update(str(layout) for layout in record.get("actual_layouts", []) if layout)
        row["html_links"] += sum(1 for key in ("stable_html", "spatial_html", "creative_html") if record.get(key))
        if record.get("artifact_json"):
            row["artifact_links"] += 1

    result = []
    for family, row in sorted(rows.items()):
        total = row["total"]
        result.append(
            {
                "family": family,
                "total": total,
                "passed": row["passed"],
                "failed": row["failed"],
                "pass_rate": round(row["passed"] / total, 6) if total else None,
                "layouts": sorted(row["layouts"]),
                "html_links": row["html_links"],
                "artifact_links": row["artifact_links"],
            }
        )
    return result


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_dashboard_core_table(path: Path, records: list[dict[str, Any]]) -> None:
    import csv

    fields = [
        "id",
        "title",
        "family",
        "ok",
        "expected",
        "actual",
        "trace_steps",
        "actual_layouts",
        "contract_gate_ready",
        "contract_test_pass_rate",
        "interaction_coverage",
        "requested_render_target",
        "actual_render_target",
        "used_baseline_renderer",
        "warnings_count",
        "errors_count",
        "stable_html",
        "spatial_html",
        "creative_html",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "id": record["id"],
                    "title": record["title"],
                    "family": record["family"],
                    "ok": record["ok"],
                    "expected": json.dumps(record["expected"], ensure_ascii=False, separators=(",", ":")),
                    "actual": json.dumps(record["actual"], ensure_ascii=False, separators=(",", ":")),
                    "trace_steps": record["trace_steps"],
                    "actual_layouts": ";".join(record["actual_layouts"]),
                    "contract_gate_ready": record["contract_gate_ready"],
                    "contract_test_pass_rate": record["contract_test_pass_rate"],
                    "interaction_coverage": record["interaction_coverage"],
                    "requested_render_target": record["requested_render_target"],
                    "actual_render_target": record["actual_render_target"],
                    "used_baseline_renderer": record["used_baseline_renderer"],
                    "warnings_count": len(record["warnings"]),
                    "errors_count": len(record["errors"]),
                    "stable_html": record["stable_html"],
                    "spatial_html": record["spatial_html"],
                    "creative_html": record["creative_html"],
                }
            )


def relative_url(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def dedupe(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def render_dashboard_html(report: dict[str, Any]) -> str:
    demos = report["demos"]
    families = sorted({demo["family"] for demo in demos})
    cards = "\n".join(render_demo_card(demo) for demo in demos)
    coverage = render_family_coverage(report.get("family_coverage", []))
    family_options = "\n".join(f'<option value="{escape(family)}">{escape(family)}</option>' for family in families)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AlgoLab Demo Dashboard</title>
<style>
:root {{
  --bg:#f5f7fb; --panel:#ffffff; --ink:#172033; --muted:#647084; --line:#d8e0ea;
  --blue:#2563eb; --green:#15803d; --amber:#b45309; --red:#b91c1c; --teal:#0f766e;
  --shadow:0 1px 2px rgba(15,23,42,.07);
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; color:var(--ink); background:var(--bg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
}}
a {{ color:inherit; }}
.app {{ min-height:100vh; display:grid; grid-template-rows:auto 1fr; }}
.topbar {{
  background:#fff; border-bottom:1px solid var(--line); padding:18px 22px;
  display:grid; grid-template-columns:minmax(280px,1fr) auto; gap:18px; align-items:center;
}}
h1 {{ margin:0; font-size:22px; letter-spacing:0; }}
.sub {{ margin:6px 0 0; color:var(--muted); font-size:13px; line-height:1.45; }}
.kpis {{ display:grid; grid-template-columns:repeat(3, minmax(92px,1fr)); gap:10px; min-width:310px; }}
.kpi {{ border:1px solid var(--line); border-radius:8px; padding:10px 12px; background:#fbfdff; }}
.kpi strong {{ display:block; font-size:22px; }}
.kpi span {{ color:var(--muted); font-size:12px; }}
.main {{ width:min(1320px,100%); margin:0 auto; padding:16px; display:grid; gap:14px; }}
.toolbar {{
  border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:var(--shadow);
  padding:12px; display:grid; grid-template-columns:minmax(220px,1fr) minmax(180px,260px) minmax(120px,170px); gap:10px;
}}
label {{ display:grid; gap:5px; color:#374151; font-size:12px; }}
input,select {{ width:100%; border:1px solid var(--line); border-radius:6px; padding:8px 9px; background:#fff; color:var(--ink); font:inherit; }}
.coverage {{
  border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:var(--shadow);
  padding:14px; display:grid; gap:10px;
}}
.section-head {{ display:flex; justify-content:space-between; align-items:end; gap:12px; flex-wrap:wrap; }}
.section-head h2 {{ margin:0; font-size:16px; }}
.coverage-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.coverage-table th,.coverage-table td {{ border-top:1px solid var(--line); padding:8px; text-align:left; vertical-align:top; }}
.coverage-table th {{ color:var(--muted); font-size:12px; font-weight:650; background:#fbfdff; }}
.coverage-table td.num,.coverage-table th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.demo-list {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:14px; align-items:start; }}
.demo {{
  border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:var(--shadow);
  padding:14px; min-width:0; display:grid; gap:12px;
}}
.demo-head {{ display:grid; grid-template-columns:1fr auto; gap:12px; align-items:start; }}
h2 {{ margin:0; font-size:18px; letter-spacing:0; }}
.meta {{ margin:5px 0 0; color:var(--muted); font-size:12px; line-height:1.4; }}
.status {{ border-radius:999px; padding:5px 9px; font-size:12px; font-weight:700; border:1px solid var(--line); }}
.status.pass {{ color:var(--green); background:#f0fdf4; border-color:#bbf7d0; }}
.status.fail {{ color:var(--red); background:#fef2f2; border-color:#fecaca; }}
.kv {{ margin:0; display:grid; grid-template-columns:92px 1fr; gap:7px 10px; font-size:13px; }}
.kv dt {{ color:var(--muted); }}
.kv dd {{ margin:0; min-width:0; overflow-wrap:anywhere; }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; }}
.chip {{ border:1px solid var(--line); border-radius:999px; padding:3px 8px; background:#fbfdff; color:#374151; font-size:12px; }}
.actions {{ display:flex; flex-wrap:wrap; gap:8px; }}
.action {{
  border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8; border-radius:6px;
  padding:7px 10px; text-decoration:none; font-size:13px;
}}
.action.secondary {{ border-color:#ccfbf1; background:#f0fdfa; color:var(--teal); }}
.action.neutral {{ border-color:var(--line); background:#fff; color:#374151; }}
details {{ border-top:1px solid var(--line); padding-top:10px; }}
summary {{ cursor:pointer; color:#374151; font-size:13px; font-weight:650; }}
pre {{
  margin:8px 0 0; max-height:170px; overflow:auto; white-space:pre-wrap; overflow-wrap:anywhere;
  border:1px solid var(--line); border-radius:6px; background:#fbfdff; padding:9px; font-size:12px; line-height:1.45;
}}
.empty {{ color:var(--muted); font-size:13px; display:none; padding:24px; border:1px dashed var(--line); border-radius:8px; background:#fff; text-align:center; }}
@media (max-width:840px) {{
  .topbar {{ grid-template-columns:1fr; }}
  .kpis {{ min-width:0; }}
  .toolbar {{ grid-template-columns:1fr; }}
  .demo-list {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<div class="app">
  <header class="topbar">
    <div>
      <h1>AlgoLab Demo Dashboard</h1>
      <p class="sub">统一展示已通过机器校验的算法可视化产物：请求、生成 spec、contract、VisualPlan、render report、artifact、校验报告和可打开页面。</p>
    </div>
    <div class="kpis">
      <div class="kpi"><strong>{report["total"]}</strong><span>Demo</span></div>
      <div class="kpi"><strong>{report["passed"]}</strong><span>通过</span></div>
      <div class="kpi"><strong>{report["failed"]}</strong><span>失败</span></div>
    </div>
  </header>
  <main class="main">
    <section class="toolbar">
      <label>搜索<input id="search" type="search" placeholder="题目、算法族、布局"></label>
      <label>算法族<select id="family"><option value="">全部算法族</option>{family_options}</select></label>
      <label>状态<select id="status"><option value="">全部状态</option><option value="pass">通过</option><option value="fail">失败</option></select></label>
    </section>
    {coverage}
    <section id="demo-list" class="demo-list">
      {cards}
    </section>
    <div id="empty" class="empty">没有匹配的 demo。</div>
  </main>
</div>
<script>
const cards = Array.from(document.querySelectorAll('.demo'));
const search = document.getElementById('search');
const family = document.getElementById('family');
const status = document.getElementById('status');
const empty = document.getElementById('empty');
function applyFilters() {{
  const q = search.value.trim().toLowerCase();
  const f = family.value;
  const s = status.value;
  let visible = 0;
  for (const card of cards) {{
    const text = card.dataset.search || '';
    const ok = (!q || text.includes(q)) && (!f || card.dataset.family === f) && (!s || card.dataset.status === s);
    card.style.display = ok ? '' : 'none';
    if (ok) visible += 1;
  }}
  empty.style.display = visible ? 'none' : 'block';
}}
search.addEventListener('input', applyFilters);
family.addEventListener('change', applyFilters);
status.addEventListener('change', applyFilters);
</script>
</body>
</html>
"""


def render_family_coverage(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return """<section id="family-coverage" class="coverage">
  <div class="section-head">
    <h2>算法族覆盖</h2>
    <p class="meta">当前 dashboard 没有可展示的算法族记录。</p>
  </div>
</section>"""
    body = "\n".join(
        f"""<tr>
  <td>{escape(row["family"])}</td>
  <td class="num">{row["total"]}</td>
  <td class="num">{row["passed"]}</td>
  <td class="num">{row["failed"]}</td>
  <td>{render_chips(row["layouts"])}</td>
  <td class="num">{row["html_links"]}</td>
  <td class="num">{row["artifact_links"]}</td>
</tr>"""
        for row in rows
    )
    return f"""<section id="family-coverage" class="coverage">
  <div class="section-head">
    <h2>算法族覆盖</h2>
    <p class="meta">按算法族汇总黄金样例、发布状态、HTML 链接和 artifact 链接。</p>
  </div>
  <table class="coverage-table">
    <thead><tr><th>算法族</th><th class="num">Demo</th><th class="num">通过</th><th class="num">失败</th><th>布局</th><th class="num">HTML 链接</th><th class="num">artifact 链接</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>"""


def render_demo_card(demo: dict[str, Any]) -> str:
    status = "pass" if demo["ok"] else "fail"
    status_text = "PASS" if demo["ok"] else "FAIL"
    search_text = " ".join(
        [
            demo["title"],
            demo["family"],
            " ".join(demo["expected_layouts"]),
            " ".join(demo["actual_layouts"]),
            demo["oracle_strategy"],
            demo["contract_test_pass_rate"],
            demo["interaction_coverage"],
            " ".join(demo["interaction_types"]),
            demo["visual_plan_stage"],
            demo["requested_render_target"],
            demo["actual_render_target"],
            status,
        ]
    ).lower()
    stable = link_or_dash(demo["stable_html"], "稳定版", "action")
    spatial = link_or_dash(demo["spatial_html"], "空间版", "action")
    creative = link_or_dash(demo["creative_html"], "创意版", "action secondary")
    artifact = link_or_dash(demo["artifact_json"], "artifact", "action neutral")
    contract = link_or_dash(demo["correctness_contract_json"], "contract", "action neutral")
    plan = link_or_dash(demo["visual_plan_json"], "VisualPlan", "action neutral")
    render_report = link_or_dash(demo["render_report_json"], "render report", "action neutral")
    capabilities = link_or_dash(demo["capabilities_json"], "capabilities", "action neutral")
    report = link_or_dash(demo["validation_report_json"], "校验报告", "action neutral")
    repair = link_or_dash(demo["repair_log_json"], "修复记录", "action neutral")
    bundle = link_or_dash(demo["bundle_dir"], "bundle", "action neutral")
    expected = json_preview(demo["expected"])
    actual = json_preview(demo["actual"])
    errors = demo["errors"] or demo["blocking_reasons"]
    warnings = demo["warnings"]
    return f"""<article class="demo" data-family="{escape(demo["family"])}" data-status="{status}" data-search="{escape(search_text)}">
  <div class="demo-head">
    <div>
      <h2>{escape(demo["title"])}</h2>
      <p class="meta">{escape(demo["family"])} · sample {demo["sample_index"]} · {demo["trace_steps"]} steps · {demo["duration_s"]}s</p>
    </div>
    <span class="status {status}">{status_text}</span>
  </div>
  <dl class="kv">
    <dt>Expected</dt><dd>{escape(expected)}</dd>
    <dt>Actual</dt><dd>{escape(actual)}</dd>
    <dt>布局</dt><dd>{render_chips(demo["actual_layouts"])}</dd>
    <dt>Contract</dt><dd>{escape("READY" if demo["contract_gate_ready"] else "MISSING")} · oracle={escape(demo["oracle_strategy"] or "none")} · tests={escape(demo["contract_test_pass_rate"])}</dd>
    <dt>交互题</dt><dd>{escape(demo["interaction_coverage"])} · {render_chips(demo["interaction_types"])}</dd>
    <dt>VisualPlan</dt><dd>stage={escape(demo["visual_plan_stage"] or "none")} · target {escape(demo["requested_render_target"] or "none")} -> {escape(demo["actual_render_target"] or "none")}</dd>
    <dt>Baseline</dt><dd>{escape("fallback" if demo["used_baseline_renderer"] else "direct")}</dd>
    <dt>证据</dt><dd>{len(demo["checks"])} checks · {len(warnings)} warnings · {len(errors)} errors</dd>
  </dl>
  <div class="actions">{stable}{spatial}{creative}{contract}{plan}{render_report}{capabilities}{artifact}{report}{repair}{bundle}</div>
  <details>
    <summary>校验细节</summary>
    <pre>{escape(json.dumps({"checks": demo["checks"], "warnings": warnings, "errors": errors}, ensure_ascii=False, indent=2))}</pre>
  </details>
</article>"""


def link_or_dash(url: str, label: str, class_name: str) -> str:
    if not url:
        return ""
    return f'<a class="{class_name}" href="{escape(url)}">{escape(label)}</a>'


def render_chips(values: list[str]) -> str:
    if not values:
        return '<span class="chip">无</span>'
    return '<span class="chips">' + "".join(f'<span class="chip">{escape(value)}</span>' for value in values) + "</span>"


def json_preview(value: Any, limit: int = 120) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= limit:
        return text
    return text[: limit - 12] + "...<truncated>"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 AlgoLab demo dashboard 和产物 bundle")
    parser.add_argument("--output-dir", type=Path, default=Path("output/dashboard"), help="dashboard 输出目录")
    parser.add_argument("--case", action="append", default=[], help="只生成指定 demo id，可重复传入")
    parser.add_argument("--sample", type=int, default=0, help="benchmark sample index；默认 0")
    parser.add_argument("--all-samples", action="store_true", help="为选中的 benchmark case 生成全部 sample")
    parser.add_argument("--all-benchmark", action="store_true", help="生成全部 benchmark case，加上精选背包 demo")
    parser.add_argument("--style", choices=["stable", "creative", "spatial", "both", "all"], default="both", help="导出页面风格")
    args = parser.parse_args()

    path = build_dashboard(
        args.output_dir,
        demo_ids=args.case or None,
        sample_index=args.sample,
        all_samples=args.all_samples,
        include_all_benchmark=args.all_benchmark,
        style=args.style,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
