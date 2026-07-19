"""Polish AlgoLearnEnv problem wording without changing executable fields."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
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


PROMPT_VERSION = "algo-learn-env-problem-polish-v1"
DEFAULT_INPUT = ROOT / "benchmark" / "algo_learn_env_benchmark.json"
DEFAULT_OUTPUT = DEFAULT_INPUT
DEFAULT_OUTPUT_DIR = ROOT / "output" / "experiments" / "benchmark_problem_polish_deepseek_v4pro_20260705"

BANNED_START_RE = re.compile(r"^(给定|输入|判断|返回|计算|请计算|请判断|请返回|实现|编写)")

SCENE_MARKERS = [
    "平台",
    "系统",
    "用户",
    "订单",
    "库存",
    "配送",
    "仓库",
    "门店",
    "医院",
    "学校",
    "课堂",
    "课程",
    "交通",
    "路线",
    "地图",
    "城市",
    "园区",
    "工厂",
    "车站",
    "票",
    "会议",
    "餐厅",
    "银行",
    "风控",
    "客服",
    "日志",
    "传感",
    "实验",
    "比赛",
    "广告",
    "电商",
    "财务",
    "停车",
    "影院",
    "机器人",
    "音乐",
    "健身",
    "物流",
    "排班",
    "业务",
    "运营",
    "社区",
    "街道",
    "房屋",
    "项目",
    "任务",
    "团队",
    "游客",
    "图书",
    "商品",
    "游戏",
    "学生",
    "老师",
    "患者",
    "车辆",
    "航班",
    "员工",
    "文件",
    "服务",
    "网络",
    "设备",
    "监控",
    "预算",
    "活动",
    "餐饮",
    "座位",
    "货架",
    "快递",
    "招聘",
    "考勤",
    "基因",
    "DNA",
    "物业",
    "设计师",
    "探险",
    "农场",
    "温室",
    "联赛",
    "技能",
    "市政府",
    "灯柱",
    "交易",
    "地块",
    "集装箱",
    "货物",
    "短信",
    "密码",
    "组织",
    "顾客",
    "摊主",
    "矿场",
    "石料",
]

LOCKED_FIELDS_EXCEPT_PROBLEM = {
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
    "input_contract",
    "real_world_context",
    "learning_objectives",
    "input_generator",
    "reference_solver",
    "trace_oracle",
    "required_views",
    "view_rationale",
    "interaction_tasks",
    "assessment_rubric",
    "common_misconceptions",
    "hint_policy",
    "stage2_visual_brief",
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


@dataclass(frozen=True)
class PolishResult:
    case_id: str
    ok: bool
    problem: str | None
    attempts: int
    errors: list[str]
    model_calls: list[dict[str, Any]]
    duration_s: float


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_input_keys(case: dict[str, Any]) -> list[str]:
    keys: set[str] = set()
    for sample in case.get("samples") or []:
        input_data = sample.get("input_data") if isinstance(sample, dict) else None
        if isinstance(input_data, dict):
            keys.update(str(key) for key in input_data)
    return sorted(keys)


def weak_reasons(case: dict[str, Any]) -> list[str]:
    problem = str(case.get("problem") or "").strip()
    context = case.get("real_world_context") if isinstance(case.get("real_world_context"), dict) else {}
    visual = case.get("stage2_visual_brief") if isinstance(case.get("stage2_visual_brief"), dict) else {}
    text = " ".join(
        [
            problem,
            str(context.get("domain") or ""),
            str(context.get("scenario") or ""),
            str(visual.get("setting") or ""),
        ]
    )
    reasons: list[str] = []
    if BANNED_START_RE.search(problem):
        reasons.append("algorithmic_start")
    if not any(marker in text for marker in SCENE_MARKERS):
        reasons.append("weak_scene_marker")
    if "LeetCode" in problem or "leetcode" in problem.lower():
        reasons.append("leetcode_residue")
    return reasons


def system_prompt() -> str:
    return """你是算法学习环境 benchmark 的中文题面编辑。只输出严格 JSON，不要 markdown。
任务：只润色 problem 字段，让它更像真实生活/业务/教学场景中的学习任务，而不是算法题库描述。
硬约束：不能改变输入 schema、变量名、输出含义、算法目标、样例答案或难度。"""


def user_prompt(case: dict[str, Any], previous_errors: list[str] | None = None) -> str:
    context = case.get("real_world_context") if isinstance(case.get("real_world_context"), dict) else {}
    visual = case.get("stage2_visual_brief") if isinstance(case.get("stage2_visual_brief"), dict) else {}
    payload = {
        "instructions": [
            "重写为 80-180 个中文字符左右的 problem。",
            "第一句必须从具体角色、业务系统、场景对象或任务背景开始，禁止以“给定/输入/判断/返回/计算/请...”开头。",
            "必须原样保留所有顶层输入变量名。",
            "必须明确输出含义，但不要写成模板化的“输入：... 输出：...”。",
            "不要出现 LeetCode、题库、算法竞赛等字样。",
            "不要新增或删除任何输入字段，不要改变 expected 的语义。",
            "只返回 JSON：{\"problem\":\"...\"}",
        ],
        "case": {
            "id": case.get("id"),
            "title": case.get("title"),
            "family": case.get("family"),
            "difficulty": case.get("difficulty"),
            "input_keys": sample_input_keys(case),
            "current_problem": case.get("problem"),
            "input_contract": case.get("input_contract"),
            "strategy": case.get("strategy"),
            "sample_inputs": [
                sample.get("input_data")
                for sample in (case.get("samples") or [])[:2]
                if isinstance(sample, dict)
            ],
            "sample_expected": [
                sample.get("expected")
                for sample in (case.get("samples") or [])[:2]
                if isinstance(sample, dict)
            ],
            "real_world_context": {
                "domain": context.get("domain"),
                "scenario": context.get("scenario"),
                "entities": context.get("entities"),
            },
            "stage2_visual_brief": {
                "setting": visual.get("setting"),
                "objects": visual.get("objects"),
                "visual_metaphor": visual.get("visual_metaphor"),
            },
        },
    }
    if previous_errors:
        payload["previous_validation_errors"] = previous_errors
    return json.dumps(payload, ensure_ascii=False, indent=2)


def validate_problem(case: dict[str, Any], problem: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(problem, str):
        return ["problem must be a string"]
    text = problem.strip()
    if len(text) < 50:
        errors.append("problem 太短")
    if len(text) > 260:
        errors.append("problem 太长，应更简洁")
    if BANNED_START_RE.search(text):
        errors.append("problem 仍以题库式动词开头")
    if "LeetCode" in text or "leetcode" in text.lower():
        errors.append("problem 仍包含 LeetCode")
    missing_keys = [key for key in sample_input_keys(case) if key not in text]
    if missing_keys:
        errors.append(f"problem 缺少输入变量名：{', '.join(missing_keys)}")
    context = case.get("real_world_context") if isinstance(case.get("real_world_context"), dict) else {}
    visual = case.get("stage2_visual_brief") if isinstance(case.get("stage2_visual_brief"), dict) else {}
    scene_text = " ".join(
        [
            text,
            str(context.get("domain") or ""),
            str(context.get("scenario") or ""),
            str(visual.get("setting") or ""),
        ]
    )
    if not any(marker in scene_text for marker in SCENE_MARKERS):
        errors.append("problem/context 缺少可识别真实场景")
    return errors


def polish_one(case: dict[str, Any], *, model: str, max_attempts: int) -> PolishResult:
    started = time.perf_counter()
    previous_errors: list[str] = []
    calls: list[dict[str, Any]] = []
    last_problem: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = chat_json_with_metadata(
                system_prompt(),
                user_prompt(case, previous_errors or None),
                model=model,
                kind="benchmark_problem_polish",
            )
            calls.extend(response.get("model_calls") or [])
            content = response.get("content")
            problem = content.get("problem") if isinstance(content, dict) else None
            if isinstance(problem, str):
                last_problem = problem.strip()
            errors = validate_problem(case, problem)
            if errors:
                previous_errors = errors
                continue
            return PolishResult(
                case_id=str(case.get("id")),
                ok=True,
                problem=str(problem).strip(),
                attempts=attempt,
                errors=[],
                model_calls=calls,
                duration_s=time.perf_counter() - started,
            )
        except Exception as exc:  # noqa: BLE001
            previous_errors = [f"{type(exc).__name__}: {exc}"]
            if attempt < max_attempts:
                time.sleep(min(2 * attempt, 8))
    return PolishResult(
        case_id=str(case.get("id")),
        ok=False,
        problem=last_problem,
        attempts=max_attempts,
        errors=previous_errors,
        model_calls=calls,
        duration_s=time.perf_counter() - started,
    )


def load_completed(path: Path) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return completed
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("ok") and isinstance(row.get("case_id"), str) and isinstance(row.get("problem"), str):
            completed[row["case_id"]] = row
    return completed


def append_jsonl(path: Path, row: dict[str, Any], lock: threading.Lock) -> None:
    with lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def assert_locked_unchanged(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for old, new in zip(before, after):
        if old.get("id") != new.get("id"):
            errors.append(f"case order changed: {old.get('id')} -> {new.get('id')}")
            continue
        for field in sorted(LOCKED_FIELDS_EXCEPT_PROBLEM):
            if old.get(field) != new.get(field):
                errors.append(f"{old.get('id')} changed locked field {field}")
                break
    return errors


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    weak = [(case.get("id"), weak_reasons(case)) for case in cases if weak_reasons(case)]
    return {
        "cases": len(cases),
        "samples": sum(len(case.get("samples") or []) for case in cases),
        "weak_count": len(weak),
        "weak_cases": weak[:100],
        "problem_unique": len(Counter(case.get("problem") for case in cases)),
        "algorithmic_start_count": sum(bool(BANNED_START_RE.search(str(case.get("problem") or "").strip())) for case in cases),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=os.environ.get("ALGOLAB_LLM_MODEL") or "DeepSeek-V4-Pro")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--no-write-final", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "polished_cases.jsonl"
    failed_path = args.output_dir / "failed_cases.json"
    report_path = args.output_dir / "problem_polish_report.json"

    data = load_json(args.input)
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"{args.input} 缺少 cases 列表")
    selected_ids = set(args.case_id or [])
    weak_cases = [case for case in cases if weak_reasons(case) and (not selected_ids or case.get("id") in selected_ids)]
    completed = load_completed(jsonl_path) if args.resume else {}
    pending = [case for case in weak_cases if case.get("id") not in completed]

    print(json.dumps({"event": "config", "llm_config": llm_config(), "requested_model": args.model}, ensure_ascii=False))
    print(
        json.dumps(
            {
                "event": "start",
                "cases_total": len(cases),
                "weak_selected": len(weak_cases),
                "resume_completed": len(completed),
                "pending": len(pending),
                "workers": args.workers,
                "max_attempts": args.max_attempts,
            },
            ensure_ascii=False,
        )
    )

    lock = threading.Lock()
    failures: list[dict[str, Any]] = []
    if pending:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_case = {
                executor.submit(polish_one, case, model=args.model, max_attempts=args.max_attempts): case
                for case in pending
            }
            done = 0
            for future in concurrent.futures.as_completed(future_to_case):
                original = future_to_case[future]
                done += 1
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    result = PolishResult(
                        case_id=str(original.get("id")),
                        ok=False,
                        problem=None,
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
                    "old_problem": original.get("problem"),
                    "problem": result.problem,
                    "errors": result.errors,
                    "model_calls": result.model_calls,
                }
                if result.ok and result.problem:
                    completed[result.case_id] = row
                    append_jsonl(jsonl_path, row, lock)
                else:
                    failures.append(row)
                print(
                    json.dumps(
                        {
                            "event": "progress",
                            "case_id": result.case_id,
                            "ok": result.ok,
                            "done": done,
                            "pending_batch": len(pending),
                            "attempts": result.attempts,
                            "duration_s": round(result.duration_s, 3),
                            "errors": result.errors[:3],
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    missing = [case.get("id") for case in weak_cases if case.get("id") not in completed]
    for case_id in missing:
        if case_id not in {row.get("case_id") for row in failures}:
            failures.append({"case_id": case_id, "ok": False, "errors": ["missing completed polish"]})
    write_json(failed_path, failures)

    final_cases: list[dict[str, Any]] = []
    changed = 0
    for case in cases:
        case_id = str(case.get("id"))
        if case_id in completed:
            updated = dict(case)
            updated["problem"] = completed[case_id]["problem"]
            metadata = dict(updated.get("enrichment_metadata") or {})
            metadata["problem_polish"] = {
                "schema_version": "algo-learn-env-problem-polish-v1",
                "prompt_version": PROMPT_VERSION,
                "model": args.model,
                "generated_at": now_iso(),
                "attempts": completed[case_id]["attempts"],
            }
            updated["enrichment_metadata"] = metadata
            final_cases.append(updated)
            changed += 1
        else:
            final_cases.append(case)

    lock_errors = assert_locked_unchanged(cases, final_cases)
    report = {
        "schema_version": "algo-learn-env-problem-polish-report-v1",
        "generated_at": now_iso(),
        "prompt_version": PROMPT_VERSION,
        "model": args.model,
        "workers": args.workers,
        "max_attempts": args.max_attempts,
        "input": str(args.input),
        "output": str(args.output),
        "output_dir": str(args.output_dir),
        "weak_selected": len(weak_cases),
        "changed_cases": changed,
        "failed_cases": len(failures),
        "locked_field_errors": lock_errors,
        "before_summary": summarize(cases),
        "after_summary": summarize(final_cases),
    }
    write_json(report_path, report)

    if failures or lock_errors:
        print(json.dumps({"event": "not_written_due_to_failures", "failed": len(failures), "locked": len(lock_errors)}, ensure_ascii=False))
        print(json.dumps({"event": "report", "path": str(report_path)}, ensure_ascii=False))
        return 1

    if not args.no_write_final:
        output_data = dict(data)
        output_data["cases"] = final_cases
        output_data["problem_polish"] = {
            "schema_version": "algo-learn-env-problem-polish-v1",
            "prompt_version": PROMPT_VERSION,
            "model": args.model,
            "generated_at": now_iso(),
            "output_dir": str(args.output_dir),
            "changed_cases": changed,
        }
        if args.output.resolve() == args.input.resolve():
            backup = args.input.with_suffix(".pre_problem_polish.json")
            if not backup.exists():
                shutil.copy2(args.input, backup)
                print(json.dumps({"event": "backup", "path": str(backup)}, ensure_ascii=False))
        write_json(args.output, output_data)
        print(json.dumps({"event": "written", "path": str(args.output), "changed_cases": changed}, ensure_ascii=False))
    else:
        print(json.dumps({"event": "not_written", "reason": "no-write-final"}, ensure_ascii=False))
    print(json.dumps({"event": "report", "path": str(report_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
