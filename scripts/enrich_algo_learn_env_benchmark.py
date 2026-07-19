"""Enrich AlgoLearnEnv benchmark cases with per-case teaching metadata.

The script only changes learning/environment fields in the exported JSON file.
Solver, tracker, verifier, sample inputs, and expected answers are locked.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import chat_json_with_metadata, llm_config


PROMPT_VERSION = "algo-learn-env-enrichment-v2"
DEFAULT_INPUT = ROOT / "benchmark" / "algo_learn_env_benchmark.json"
DEFAULT_OUTPUT = DEFAULT_INPUT
DEFAULT_OUTPUT_DIR = ROOT / "output" / "experiments" / "benchmark_enrichment_deepseek_v4pro_20260704"

LOCKED_FIELDS = {
    "id",
    "algorithm_id",
    "title",
    "family",
    "family_id",
    "subfamily_id",
    "difficulty",
    "dataset_source",
    "gate_layer",
    "support_level",
    "process_profile",
    "oracle_type",
    "oracle_risk",
    "oracle_notes",
    "oracle_reference",
    "demo_required",
    "reference_solver",
    "variant_name",
    "strategy",
    "time_complexity",
    "space_complexity",
    "expected_layouts",
    "samples",
    "code",
    "tracker_code",
    "verifier_code",
}

ENRICHMENT_FIELDS = {
    "real_world_context",
    "problem",
    "learning_objectives",
    "input_generator",
    "trace_oracle",
    "required_views",
    "view_rationale",
    "interaction_tasks",
    "assessment_rubric",
    "common_misconceptions",
    "hint_policy",
    "stage2_visual_brief",
}

OLD_INTERACTION_TEMPLATE = [
    "predict_next_state",
    "identify_active_invariant",
    "modify_input_and_rerun",
]

SCENE_MARKERS = {
    "场景",
    "平台",
    "系统",
    "用户",
    "订单",
    "库存",
    "排班",
    "物流",
    "配送",
    "仓库",
    "门店",
    "医院",
    "诊室",
    "学校",
    "课堂",
    "学生",
    "教师",
    "课程",
    "交通",
    "路线",
    "地图",
    "城市",
    "园区",
    "工厂",
    "车站",
    "票务",
    "会议",
    "餐厅",
    "银行",
    "风控",
    "客服",
    "日志",
    "传感器",
    "实验",
    "比赛",
    "广告",
    "电商",
    "财务",
    "停车",
    "影院",
    "机器人",
}

GENERIC_TRACE_ORACLES = {
    "semantic-trace schema + solve/trace/verifier result equivalence",
}

STATE_TOKENS_BY_PROFILE = {
    "dp": ["dp", "state", "index", "i", "j", "transition", "base"],
    "two_pointer": ["left", "right", "window", "pointer", "sum", "count"],
    "sliding_window": ["left", "right", "window", "count", "freq", "best"],
    "binary_search": ["left", "right", "mid", "lo", "hi", "target"],
    "graph_bfs": ["queue", "visited", "node", "edge", "distance", "level"],
    "graph_dfs": ["stack", "visited", "node", "edge", "parent", "depth"],
    "topological": ["indegree", "queue", "order", "edge", "node"],
    "union_find": ["parent", "rank", "root", "component", "union", "find"],
    "tree": ["node", "root", "left", "right", "path", "depth"],
    "trie": ["node", "prefix", "char", "children", "word"],
    "monotonic_stack": ["stack", "top", "index", "height", "temperature"],
    "heap": ["heap", "top", "push", "pop", "priority"],
    "greedy": ["choice", "current", "best", "interval", "profit"],
    "prefix_sum": ["prefix", "sum", "count", "index", "range"],
    "backtracking": ["path", "choice", "depth", "used", "candidate"],
    "sort": ["pivot", "left", "right", "order", "swap"],
    "linked_list": ["head", "prev", "curr", "next", "fast", "slow"],
}


@dataclass(frozen=True)
class EnrichmentResult:
    case_id: str
    ok: bool
    case: dict[str, Any] | None
    enrichment: dict[str, Any] | None
    attempts: int
    errors: list[str]
    model_calls: list[dict[str, Any]]
    duration_s: float


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_completed(path: Path) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return completed
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no} 不是合法 JSONL：{exc}") from exc
        case_id = row.get("case_id")
        if isinstance(case_id, str) and row.get("ok") and isinstance(row.get("case"), dict):
            completed[case_id] = row
    return completed


def append_jsonl(path: Path, payload: Any, lock: threading.Lock) -> None:
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def trim_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...<truncated>"


def sample_input_keys(case: dict[str, Any]) -> list[str]:
    keys: set[str] = set()
    for sample in case.get("samples") or []:
        input_data = sample.get("input_data") if isinstance(sample, dict) else None
        if isinstance(input_data, dict):
            keys.update(str(key) for key in input_data.keys())
    return sorted(keys)


def state_tokens_for_case(case: dict[str, Any]) -> list[str]:
    tokens = set(sample_input_keys(case))
    profile = str(case.get("process_profile") or case.get("family_id") or "")
    family_id = str(case.get("family_id") or "")
    layouts = [str(item) for item in case.get("expected_layouts") or []]
    for source in [profile, family_id, *layouts]:
        lowered = source.lower()
        for key, values in STATE_TOKENS_BY_PROFILE.items():
            if key in lowered:
                tokens.update(values)
    tokens.update(["state", "answer", "expected", "trace"])
    return sorted(token for token in tokens if token)


def compact_case_for_prompt(case: dict[str, Any]) -> dict[str, Any]:
    keep = {
        key: case.get(key)
        for key in [
            "id",
            "algorithm_id",
            "title",
            "problem",
            "family",
            "family_id",
            "subfamily_id",
            "difficulty",
            "gate_layer",
            "support_level",
            "process_profile",
            "input_contract",
            "strategy",
            "time_complexity",
            "space_complexity",
            "expected_layouts",
            "required_views",
            "learning_objectives",
        ]
        if key in case
    }
    keep["input_keys"] = sample_input_keys(case)
    keep["state_tokens"] = state_tokens_for_case(case)
    keep["samples"] = (case.get("samples") or [])[:3]
    keep["code_excerpt"] = trim_text(str(case.get("code") or ""), 900)
    keep["tracker_code_excerpt"] = trim_text(str(case.get("tracker_code") or ""), 1200)
    keep["verifier_code_excerpt"] = trim_text(str(case.get("verifier_code") or ""), 700)
    return keep


def system_prompt() -> str:
    return """你是算法教学环境 benchmark designer。直接输出严格 JSON，不要 markdown，不要解释。
只重写教学/交互/可视化元数据；不能改变算法语义、输入 schema、样例 expected、代码、复杂度。
每题必须是真实生活或业务场景，problem 要保留全部输入变量名。每个字段都要专属，不能套模板。
交互任务必须围绕本题变量和 trace，可由 oracle/expected/verifier 自动评估。
所有字符串保持简洁，避免长篇解释。"""


def user_prompt(case: dict[str, Any], previous_errors: list[str] | None = None) -> str:
    compact = compact_case_for_prompt(case)
    schema = {
        "real_world_context": {
            "domain": "真实生活或业务领域，必须具体",
            "scenario": "1-2 句描述用户在什么场景下需要解决这个问题",
            "entities": ["题面中的真实对象，至少 3 个"],
            "why_algorithm_fits": "简述为什么该算法状态/策略适合这个场景",
        },
        "problem": "新的中文题面。必须保留 input_keys 中每个顶层变量名，并说明输出含义；不要改变输入 schema。",
        "learning_objectives": [
            "围绕本题状态和变量的目标 1",
            "围绕本题状态和变量的目标 2",
            "围绕本题状态和变量的目标 3",
        ],
        "input_generator": {
            "description": "如何生成本题输入，引用 input_keys",
            "parameters": ["可调参数或规模，至少 3 个"],
            "edge_cases": ["专属于本题的边界样例，至少 3 个"],
        },
        "trace_oracle": {
            "final_answer_check": "最终答案如何用 expected/verifier 判断",
            "step_state_checks": ["每一步要检查的具体状态字段或变量，至少 3 个"],
            "invariants": ["本算法在本题中的不变式，至少 3 个"],
        },
        "required_views": ["沿用或补充 expected_layouts 中的视图名，只输出字符串数组"],
        "view_rationale": [
            {"view": "视图名", "purpose": "该视图如何服务本题具体状态"},
        ],
        "interaction_tasks": [
            {
                "id": "task_1",
                "type": "predict_next_state",
                "prompt": "给学生的问题，必须包含本题变量名或状态名",
                "trace_anchor": ["state.xxx 或变量名，至少 2 个"],
                "oracle": "如何根据 trace/expected/verifier 自动判定",
                "feedback_correct": "答对后的短反馈",
                "feedback_wrong": "答错后提示观察哪个状态",
                "stage2_affordance": "Stage2 控件或可视化操作",
            }
        ],
        "assessment_rubric": {
            "auto_grading": ["可程序校验标准，至少 3 条"],
            "llm_judge_criteria": ["主观教学质量标准，至少 3 条"],
            "failure_cases": ["容易失败的回答模式，至少 2 条"],
        },
        "common_misconceptions": ["本题常见误解，至少 3 条"],
        "hint_policy": ["由浅入深提示，至少 3 条，必须引用本题变量或状态"],
        "stage2_visual_brief": {
            "setting": "具体可视化场景，不要抽象",
            "objects": ["画面对象，至少 3 个"],
            "layout_suggestion": "画面如何摆放主要视图",
            "animation_focus": ["每帧/每步动画强调什么，至少 3 个"],
            "learner_controls": ["学生可操作控件，至少 3 个"],
            "visual_metaphor": "把算法状态映射成生活对象的方式",
        },
    }
    instructions = [
        "请为下面这个 benchmark case 生成专属 enrichment JSON。",
        "你必须完整遵守 schema；字段名不能改变，不能增加无关顶层字段。",
        "interaction_tasks 至少 4 个，类型要覆盖 predict_next_state、identify_invariant、modify_input、explain_transition 或 find_counterexample 中至少 4 类。",
        "每个 interaction task 的 prompt、oracle、trace_anchor 必须引用本题 input_keys 或 state_tokens 中的具体词。",
        "problem 必须包含真实场景，不允许只写 LeetCode/算法题描述。",
        "required_views 必须是字符串数组，并且不能丢失 expected_layouts 中已有视图。",
        "每个数组只保留必要条目；interaction_tasks 正好 4 个；每个字符串尽量 15-45 个汉字。",
        "所有中文表述要服务教学和可视化，避免通用套话。",
        "只返回 JSON 对象。",
    ]
    if previous_errors:
        instructions.extend(
            [
                "上一轮输出没有通过校验。必须逐条修正以下问题：",
                json.dumps(previous_errors, ensure_ascii=False, indent=2),
            ]
        )
    payload = {
        "instructions": instructions,
        "required_schema": schema,
        "case": compact,
        "locked_fields_do_not_modify": sorted(LOCKED_FIELDS),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _is_nonempty_str(value: Any, min_len: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= min_len


def _is_str_list(value: Any, min_items: int = 1) -> bool:
    return isinstance(value, list) and len(value) >= min_items and all(_is_nonempty_str(item) for item in value)


def _list_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if value is not None else ""


def _contains_any(text: str, tokens: list[str] | set[str]) -> bool:
    return any(token and token in text for token in tokens)


def validate_enrichment(case: dict[str, Any], enrichment: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(enrichment, dict):
        return ["enrichment 必须是 JSON object"]

    missing = sorted(ENRICHMENT_FIELDS - enrichment.keys())
    if missing:
        errors.append(f"缺少顶层字段：{', '.join(missing)}")

    input_keys = sample_input_keys(case)
    state_tokens = state_tokens_for_case(case)

    context = enrichment.get("real_world_context")
    if not isinstance(context, dict):
        errors.append("real_world_context 必须是对象")
    else:
        for key in ["domain", "scenario", "why_algorithm_fits"]:
            min_len = 3 if key == "domain" else 8
            if not _is_nonempty_str(context.get(key), min_len):
                errors.append(f"real_world_context.{key} 太短或缺失")
        if not _is_str_list(context.get("entities"), 3):
            errors.append("real_world_context.entities 至少 3 个字符串")

    problem = enrichment.get("problem")
    if not _is_nonempty_str(problem, 50):
        errors.append("problem 至少 50 字，且必须是完整生活场景题面")
    else:
        missing_keys = [key for key in input_keys if key not in problem]
        if missing_keys:
            errors.append(f"problem 没有显式保留输入变量名：{', '.join(missing_keys)}")
        if "LeetCode" in problem or "leetcode" in problem.lower():
            errors.append("problem 不应再写成 LeetCode 风格题面")

    if not _is_str_list(enrichment.get("learning_objectives"), 3):
        errors.append("learning_objectives 至少 3 个字符串")
    elif len(enrichment["learning_objectives"]) > 5:
        errors.append("learning_objectives 最多 5 个，避免冗长")

    input_generator = enrichment.get("input_generator")
    if not isinstance(input_generator, dict):
        errors.append("input_generator 必须是对象")
    else:
        if not _is_nonempty_str(input_generator.get("description"), 20):
            errors.append("input_generator.description 太短")
        if not _is_str_list(input_generator.get("parameters"), 3):
            errors.append("input_generator.parameters 至少 3 个字符串")
        if not _is_str_list(input_generator.get("edge_cases"), 3):
            errors.append("input_generator.edge_cases 至少 3 个字符串")

    trace_oracle = enrichment.get("trace_oracle")
    if not isinstance(trace_oracle, dict):
        errors.append("trace_oracle 必须是对象")
    else:
        oracle_text = _list_text(trace_oracle)
        if oracle_text in GENERIC_TRACE_ORACLES or not _contains_any(oracle_text, state_tokens):
            errors.append("trace_oracle 必须引用本题具体变量或状态，不能是通用模板")
        if not _is_nonempty_str(trace_oracle.get("final_answer_check"), 20):
            errors.append("trace_oracle.final_answer_check 太短")
        if not _is_str_list(trace_oracle.get("step_state_checks"), 3):
            errors.append("trace_oracle.step_state_checks 至少 3 个字符串")
        if not _is_str_list(trace_oracle.get("invariants"), 3):
            errors.append("trace_oracle.invariants 至少 3 个字符串")

    required_views = enrichment.get("required_views")
    if not _is_str_list(required_views, 1):
        errors.append("required_views 必须是字符串数组")
    else:
        missing_views = [view for view in case.get("expected_layouts") or [] if view not in required_views]
        if missing_views:
            errors.append(f"required_views 不能丢失 expected_layouts：{', '.join(missing_views)}")

    view_rationale = enrichment.get("view_rationale")
    if not isinstance(view_rationale, list) or not view_rationale:
        errors.append("view_rationale 至少 1 项")
    elif not all(isinstance(item, dict) and _is_nonempty_str(item.get("view")) and _is_nonempty_str(item.get("purpose"), 12) for item in view_rationale):
        errors.append("view_rationale 每项必须包含 view/purpose")

    tasks = enrichment.get("interaction_tasks")
    if not isinstance(tasks, list) or len(tasks) < 4:
        errors.append("interaction_tasks 至少 4 个对象")
    elif tasks == OLD_INTERACTION_TEMPLATE or all(isinstance(item, str) for item in tasks):
        errors.append("interaction_tasks 不能使用旧字符串模板")
    else:
        types = set()
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"interaction_tasks[{index}] 必须是对象")
                continue
            for key in [
                "id",
                "type",
                "prompt",
                "trace_anchor",
                "oracle",
                "feedback_correct",
                "feedback_wrong",
                "stage2_affordance",
            ]:
                if key == "trace_anchor":
                    if not _is_str_list(task.get(key), 1):
                        errors.append(f"interaction_tasks[{index}].trace_anchor 至少 1 个字符串")
                elif not _is_nonempty_str(task.get(key), 8 if key != "id" else 3):
                    errors.append(f"interaction_tasks[{index}].{key} 太短或缺失")
            types.add(str(task.get("type") or ""))
        if len(types) < 4:
            errors.append("interaction_tasks 类型至少覆盖 4 类")

    rubric = enrichment.get("assessment_rubric")
    if not isinstance(rubric, dict):
        errors.append("assessment_rubric 必须是对象")
    else:
        if not _is_str_list(rubric.get("auto_grading"), 3):
            errors.append("assessment_rubric.auto_grading 至少 3 条")
        if not _is_str_list(rubric.get("llm_judge_criteria"), 3):
            errors.append("assessment_rubric.llm_judge_criteria 至少 3 条")
        if not _is_str_list(rubric.get("failure_cases"), 2):
            errors.append("assessment_rubric.failure_cases 至少 2 条")

    if not _is_str_list(enrichment.get("common_misconceptions"), 3):
        errors.append("common_misconceptions 至少 3 条")
    if not _is_str_list(enrichment.get("hint_policy"), 3):
        errors.append("hint_policy 至少 3 条")

    visual = enrichment.get("stage2_visual_brief")
    if not isinstance(visual, dict):
        errors.append("stage2_visual_brief 必须是对象")
    else:
        if not _is_nonempty_str(visual.get("setting"), 20):
            errors.append("stage2_visual_brief.setting 太短")
        if not _is_str_list(visual.get("objects"), 3):
            errors.append("stage2_visual_brief.objects 至少 3 个字符串")
        if not _is_nonempty_str(visual.get("layout_suggestion"), 20):
            errors.append("stage2_visual_brief.layout_suggestion 太短")
        if not _is_str_list(visual.get("animation_focus"), 3):
            errors.append("stage2_visual_brief.animation_focus 至少 3 个字符串")
        if not _is_str_list(visual.get("learner_controls"), 3):
            errors.append("stage2_visual_brief.learner_controls 至少 3 个字符串")
        if not _is_nonempty_str(visual.get("visual_metaphor"), 20):
            errors.append("stage2_visual_brief.visual_metaphor 太短")
    return errors


def normalize_enrichment(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    for key in ["enrichment", "metadata", "case"]:
        nested = payload.get(key)
        if isinstance(nested, dict) and ENRICHMENT_FIELDS.issubset(nested.keys()):
            return {field: nested[field] for field in ENRICHMENT_FIELDS}
    if ENRICHMENT_FIELDS.issubset(payload.keys()):
        return {field: payload[field] for field in ENRICHMENT_FIELDS}
    return payload


def merge_enrichment(case: dict[str, Any], enrichment: dict[str, Any], *, model: str, attempts: int) -> dict[str, Any]:
    updated = dict(case)
    for field in ENRICHMENT_FIELDS:
        if field == "required_views":
            original = [str(item) for item in case.get("required_views") or case.get("expected_layouts") or []]
            proposed = [str(item) for item in enrichment.get("required_views") or [] if isinstance(item, str)]
            merged: list[str] = []
            for value in [*original, *proposed]:
                if value and value not in merged:
                    merged.append(value)
            updated[field] = merged
        else:
            updated[field] = enrichment[field]
    updated["enrichment_metadata"] = {
        "schema_version": "algo-learn-env-enrichment-v1",
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "generated_at": _now_iso(),
        "attempts": attempts,
        "locked_fields_sha256": stable_hash({key: case.get(key) for key in sorted(LOCKED_FIELDS)}),
    }
    return updated


def assert_locked_fields_unchanged(original: dict[str, Any], updated: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in sorted(LOCKED_FIELDS):
        if stable_json(original.get(key)) != stable_json(updated.get(key)):
            errors.append(f"locked field changed: {original.get('id')}::{key}")
    return errors


def enrich_one(case: dict[str, Any], *, model: str, max_attempts: int) -> EnrichmentResult:
    started = time.perf_counter()
    previous_errors: list[str] = []
    model_calls: list[dict[str, Any]] = []
    last_enrichment: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = chat_json_with_metadata(
                system_prompt(),
                user_prompt(case, previous_errors if previous_errors else None),
                model=model,
                kind="benchmark_enrichment",
            )
            model_calls.extend(response.get("model_calls") or [])
            enrichment = normalize_enrichment(response["content"])
            if isinstance(enrichment, dict):
                last_enrichment = enrichment
            errors = validate_enrichment(case, enrichment)
            if errors:
                previous_errors = errors
                continue
            updated = merge_enrichment(case, enrichment, model=model, attempts=attempt)
            locked_errors = assert_locked_fields_unchanged(case, updated)
            if locked_errors:
                previous_errors = locked_errors
                continue
            return EnrichmentResult(
                case_id=str(case.get("id")),
                ok=True,
                case=updated,
                enrichment=enrichment,
                attempts=attempt,
                errors=[],
                model_calls=model_calls,
                duration_s=time.perf_counter() - started,
            )
        except Exception as exc:  # noqa: BLE001 - keep batch running and report per-case failures.
            previous_errors = [f"{type(exc).__name__}: {exc}"]
            if attempt < max_attempts:
                time.sleep(min(2.0 * attempt, 8.0))
                continue
    return EnrichmentResult(
        case_id=str(case.get("id")),
        ok=False,
        case=None,
        enrichment=last_enrichment,
        attempts=max_attempts,
        errors=previous_errors,
        model_calls=model_calls,
        duration_s=time.perf_counter() - started,
    )


def field_uniqueness(cases: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "problem",
        "learning_objectives",
        "input_generator",
        "trace_oracle",
        "required_views",
        "view_rationale",
        "interaction_tasks",
        "assessment_rubric",
        "common_misconceptions",
        "hint_policy",
        "stage2_visual_brief",
    ]
    stats: dict[str, Any] = {}
    for field in fields:
        counter = Counter(stable_json(case.get(field)) for case in cases)
        stats[field] = {
            "unique": len(counter),
            "top_duplicates": [
                {"count": count, "preview": value[:240]}
                for value, count in counter.most_common(5)
                if count > 1
            ],
        }
    return stats


def dataset_checks(cases: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    scene_case_count = 0
    rich_task_count = 0
    for case in cases:
        case_errors = validate_enrichment(case, {field: case.get(field) for field in ENRICHMENT_FIELDS})
        locked_hash = (case.get("enrichment_metadata") or {}).get("locked_fields_sha256")
        if locked_hash and locked_hash != stable_hash({key: case.get(key) for key in sorted(LOCKED_FIELDS)}):
            case_errors.append("enrichment_metadata.locked_fields_sha256 mismatch")
        if isinstance(case.get("real_world_context"), dict) and isinstance(case.get("stage2_visual_brief"), dict):
            scene_case_count += 1
        if isinstance(case.get("interaction_tasks"), list) and all(isinstance(item, dict) for item in case["interaction_tasks"]):
            rich_task_count += 1
        if case_errors:
            failures.append({"case_id": case.get("id"), "errors": case_errors})
    return {
        "total_cases": len(cases),
        "scene_case_count": scene_case_count,
        "rich_interaction_task_case_count": rich_task_count,
        "failure_count": len(failures),
        "failures": failures[:50],
        "field_uniqueness": field_uniqueness(cases),
    }


def build_report_markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    uniqueness = checks["field_uniqueness"]
    lines = [
        "# AlgoLearnEnv Benchmark Enrichment Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- model: {report['model']}",
        f"- prompt_version: {report['prompt_version']}",
        f"- workers: {report['workers']}",
        f"- cases_total: {report['cases_total']}",
        f"- cases_enriched: {report['cases_enriched']}",
        f"- cases_failed: {report['cases_failed']}",
        f"- scene_case_count: {checks['scene_case_count']}/{checks['total_cases']}",
        f"- rich_interaction_task_case_count: {checks['rich_interaction_task_case_count']}/{checks['total_cases']}",
        f"- validation_failure_count: {checks['failure_count']}",
        "",
        "## Field Uniqueness",
        "",
    ]
    for field, stat in uniqueness.items():
        lines.append(f"- {field}: unique={stat['unique']}/{checks['total_cases']}")
    if report.get("failed_cases"):
        lines.extend(["", "## Failed Cases", ""])
        for item in report["failed_cases"][:20]:
            lines.append(f"- {item['case_id']}: {'; '.join(item.get('errors') or [])}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=os.environ.get("ALGOLAB_LLM_MODEL") or "DeepSeek-V4-Pro")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--case-limit", type=int, default=0)
    parser.add_argument("--case-id", action="append", default=[], help="Only enrich selected case id; can be repeated.")
    parser.add_argument("--resume", action="store_true", help="Reuse successful rows in enriched_cases.jsonl.")
    parser.add_argument("--no-write-final", action="store_true", help="Do not write the final benchmark JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    enriched_jsonl = args.output_dir / "enriched_cases.jsonl"
    failed_path = args.output_dir / "failed_cases.json"
    report_json = args.output_dir / "enrichment_report.json"
    report_md = args.output_dir / "enrichment_report.md"

    data = load_json(args.input)
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{args.input} 缺少 cases 列表")

    selected_ids = set(args.case_id or [])
    selected_cases = [case for case in cases if not selected_ids or case.get("id") in selected_ids]
    if args.case_limit:
        selected_cases = selected_cases[: args.case_limit]
    if not selected_cases:
        raise ValueError("没有匹配的 case")

    completed = load_completed(enriched_jsonl) if args.resume else {}
    completed_cases: dict[str, dict[str, Any]] = {
        case_id: row["case"] for case_id, row in completed.items()
    }
    pending = [case for case in selected_cases if case.get("id") not in completed_cases]

    print(json.dumps({"event": "config", "llm_config": llm_config(), "requested_model": args.model}, ensure_ascii=False))
    print(
        json.dumps(
            {
                "event": "start",
                "input": str(args.input),
                "output": str(args.output),
                "output_dir": str(args.output_dir),
                "cases_total": len(cases),
                "selected": len(selected_cases),
                "resume_completed": len(completed_cases),
                "pending": len(pending),
                "workers": args.workers,
                "max_attempts": args.max_attempts,
            },
            ensure_ascii=False,
        )
    )

    jsonl_lock = threading.Lock()
    failed_rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    if pending:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_case = {
                executor.submit(enrich_one, case, model=args.model, max_attempts=args.max_attempts): case
                for case in pending
            }
            done_count = 0
            for future in concurrent.futures.as_completed(future_to_case):
                original = future_to_case[future]
                done_count += 1
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    result = EnrichmentResult(
                        case_id=str(original.get("id")),
                        ok=False,
                        case=None,
                        enrichment=None,
                        attempts=args.max_attempts,
                        errors=[f"{type(exc).__name__}: {exc}"],
                        model_calls=[],
                        duration_s=0.0,
                    )
                row = {
                    "case_id": result.case_id,
                    "ok": result.ok,
                    "attempts": result.attempts,
                    "duration_s": round(result.duration_s, 3),
                    "errors": result.errors,
                    "case": result.case,
                    "enrichment": result.enrichment,
                    "model_calls": result.model_calls,
                }
                if result.ok and result.case is not None:
                    completed_cases[result.case_id] = result.case
                    append_jsonl(enriched_jsonl, row, jsonl_lock)
                else:
                    failed_rows.append(row)
                print(
                    json.dumps(
                        {
                            "event": "progress",
                            "case_id": result.case_id,
                            "ok": result.ok,
                            "done": done_count,
                            "pending_batch": len(pending),
                            "attempts": result.attempts,
                            "duration_s": round(result.duration_s, 3),
                            "errors": result.errors[:3],
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    selected_id_set = {str(case.get("id")) for case in selected_cases}
    missing = sorted(case_id for case_id in selected_id_set if case_id not in completed_cases)
    if missing:
        failed_rows.extend(
            {"case_id": case_id, "ok": False, "errors": ["case missing from completed results"]}
            for case_id in missing
            if case_id not in {row.get("case_id") for row in failed_rows}
        )

    write_json(failed_path, failed_rows)
    if failed_rows:
        print(json.dumps({"event": "failed", "count": len(failed_rows), "path": str(failed_path)}, ensure_ascii=False))

    final_cases: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("id"))
        if case_id in selected_id_set:
            if case_id not in completed_cases:
                final_cases.append(case)
            else:
                final_cases.append(completed_cases[case_id])
        else:
            final_cases.append(case)

    check_cases = [case for case in final_cases if str(case.get("id")) in selected_id_set]
    checks = dataset_checks(check_cases)
    report = {
        "schema_version": "algo-learn-env-enrichment-report-v1",
        "generated_at": _now_iso(),
        "prompt_version": PROMPT_VERSION,
        "model": args.model,
        "workers": args.workers,
        "max_attempts": args.max_attempts,
        "duration_s": round(time.perf_counter() - started, 3),
        "input": str(args.input),
        "output": str(args.output),
        "output_dir": str(args.output_dir),
        "cases_total": len(cases),
        "cases_selected": len(selected_cases),
        "cases_enriched": len(completed_cases),
        "cases_failed": len(failed_rows),
        "failed_cases": failed_rows,
        "checks": checks,
    }
    write_json(report_json, report)
    report_md.write_text(build_report_markdown(report), encoding="utf-8")

    if not args.no_write_final and not failed_rows:
        output_data = dict(data)
        output_data["cases"] = final_cases
        output_data["enrichment"] = {
            "schema_version": "algo-learn-env-enrichment-v1",
            "prompt_version": PROMPT_VERSION,
            "model": args.model,
            "generated_at": _now_iso(),
            "output_dir": str(args.output_dir),
            "cases_enriched": len(completed_cases),
            "locked_fields": sorted(LOCKED_FIELDS),
        }
        if args.output.resolve() == args.input.resolve():
            backup = args.input.with_suffix(".pre_enrichment.json")
            if not backup.exists():
                shutil.copy2(args.input, backup)
                print(json.dumps({"event": "backup", "path": str(backup)}, ensure_ascii=False))
        write_json(args.output, output_data)
        print(json.dumps({"event": "written", "path": str(args.output), "cases": len(final_cases)}, ensure_ascii=False))
    elif failed_rows:
        print(json.dumps({"event": "not_written_due_to_failures", "failed_cases": len(failed_rows)}, ensure_ascii=False))
    else:
        print(json.dumps({"event": "not_written", "reason": "no-write-final"}, ensure_ascii=False))

    print(json.dumps({"event": "report", "json": str(report_json), "md": str(report_md)}, ensure_ascii=False))
    return 0 if not failed_rows and checks["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
