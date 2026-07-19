"""Stress teaching/runtime noninterference with randomized browser actions."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.teaching_enricher import apply_teaching_overlay
from algolab.schemas.scene_graph import SceneGraph


PURE_TEACHING_ACTIONS = {
    "hint",
    "show_answer",
    "submit_correct",
    "submit_wrong",
    "clear_learning_log",
}
NAVIGATION_ACTIONS = {"next", "prev", "timeline", "reset", "select_variant"}


def check_action_transition(
    action: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    violations: list[str] = []
    if before.get("artifact_hash") != after.get("artifact_hash"):
        violations.append("artifact_hash_changed")
    if action in PURE_TEACHING_ACTIONS:
        if before.get("current_state_hash") != after.get("current_state_hash"):
            violations.append("teaching_action_changed_current_algorithm_state")
        if before.get("current_step") != after.get("current_step"):
            violations.append("teaching_action_changed_current_step")
    elif action in NAVIGATION_ACTIONS:
        if after.get("target_state_hash") is not None and after.get("current_state_hash") != after.get("target_state_hash"):
            violations.append("navigation_state_differs_from_verified_target")
    else:
        violations.append("unknown_action")
    return {"ok": not violations, "violations": violations}


def _sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        return ROOT / candidate
    if candidate.exists():
        return candidate
    host_root = os.environ.get("ALGOLAB_HOST_PROJECT_ROOT", "").strip()
    if host_root:
        try:
            return ROOT / candidate.relative_to(Path(host_root))
        except ValueError:
            pass
    return candidate


def _report_rows(specs: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in specs:
        label, separator, raw_path = spec.partition("=")
        if not separator:
            raw_path = label
            label = Path(raw_path).parent.name
        path = _repo_path(raw_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("results") or []:
            html = _repo_path(str(row.get("html") or ""))
            artifact = _repo_path(str(row.get("json") or ""))
            rows.append(
                {
                    "dataset": label,
                    "case_id": str(row.get("case_id") or html.stem),
                    "html": html,
                    "artifact": artifact,
                    "source_ok": row.get("ok"),
                }
            )
    return rows


STRESS_JS = r"""
({sequences, minActions, maxActions, seed}) => {
  let rngState = seed >>> 0;
  const rand = () => {
    rngState = (Math.imul(rngState, 1664525) + 1013904223) >>> 0;
    return rngState / 4294967296;
  };
  const pick = xs => xs[Math.floor(rand() * xs.length) % xs.length];
  const hash = value => simpleHash(stableJson(value));
  const observation = () => ({
    artifact_hash: hash(ARTIFACT),
    current_state_hash: hash((frame() || {}).state || {}),
    current_step: stepIndex,
  });
  const violations = [];
  const actionCounts = {};
  let actionsExecuted = 0;
  const pure = new Set(['hint','show_answer','submit_correct','submit_wrong','clear_learning_log']);
  const noteViolation = (action, kind, before, after) => {
    if (violations.length < 50) violations.push({action, kind, before, after});
  };
  const runAction = action => {
    const before = observation();
    let targetHash = null;
    const f = frame() || {};
    const interaction = f.interaction || null;
    if (action === 'hint') showInteractionHint();
    else if (action === 'show_answer') revealInteractionAnswer();
    else if (action === 'clear_learning_log') clearLearningLog();
    else if (action === 'submit_correct' || action === 'submit_wrong') {
      if (!interaction) return false;
      const correct = action === 'submit_correct';
      if (interaction.type === 'choice') {
        const options = Array.isArray(interaction.options) ? interaction.options.map(String) : [];
        const answer = String(interaction.answer ?? '');
        const selected = correct ? answer : (options.find(value => value !== answer) ?? `${answer}__wrong`);
        checkChoice(encodeURIComponent(selected));
      } else if (interaction.type === 'input') {
        const node = $('free-answer');
        if (!node) return false;
        node.value = correct ? String(interaction.answer ?? '') : `${String(interaction.answer ?? '')}__wrong`;
        checkInput();
      } else if (interaction.type === 'judge') {
        const answer = interaction.answer;
        const expected = answer === true || String(answer).toLowerCase() === 'true' || String(answer) === '正确';
        checkJudge(correct ? expected : !expected);
      } else return false;
    } else if (action === 'next') {
      const target = Math.min(stepIndex + 1, frames().length - 1);
      targetHash = hash((frames()[target] || {}).state || {});
      go(target, 'stress-next');
    } else if (action === 'prev') {
      const target = Math.max(stepIndex - 1, 0);
      targetHash = hash((frames()[target] || {}).state || {});
      go(target, 'stress-prev');
    } else if (action === 'timeline') {
      const target = Math.floor(rand() * frames().length);
      targetHash = hash((frames()[target] || {}).state || {});
      go(target, 'stress-timeline');
    } else if (action === 'reset') {
      targetHash = hash((frames()[0] || {}).state || {});
      go(0, 'stress-reset');
    } else if (action === 'select_variant') {
      const targetVariant = Math.floor(rand() * ARTIFACT.variants.length);
      const targetScene = ARTIFACT.scenes[ARTIFACT.variants[targetVariant].id] || {frames:[]};
      targetHash = hash(((targetScene.frames || [])[0] || {}).state || {});
      selectVariant(targetVariant);
    } else return false;
    const after = observation();
    after.target_state_hash = targetHash;
    if (before.artifact_hash !== after.artifact_hash) noteViolation(action, 'artifact_hash_changed', before, after);
    if (pure.has(action)) {
      if (before.current_state_hash !== after.current_state_hash) noteViolation(action, 'teaching_state_changed', before, after);
      if (before.current_step !== after.current_step) noteViolation(action, 'teaching_step_changed', before, after);
    } else if (targetHash !== null && after.current_state_hash !== targetHash) {
      noteViolation(action, 'navigation_target_mismatch', before, after);
    }
    actionCounts[action] = (actionCounts[action] || 0) + 1;
    actionsExecuted += 1;
    return true;
  };
  const actionPool = ['hint','show_answer','submit_correct','submit_wrong','clear_learning_log','next','prev','timeline','reset','select_variant'];
  for (let sequence = 0; sequence < sequences; sequence += 1) {
    selectVariant(Math.floor(rand() * ARTIFACT.variants.length));
    const interactive = frames().map((f, i) => f && f.interaction ? i : -1).filter(i => i >= 0);
    go(interactive.length ? pick(interactive) : 0, 'stress-sequence-start');
    const length = minActions + Math.floor(rand() * (maxActions - minActions + 1));
    for (let index = 0; index < length; index += 1) {
      let action = pick(actionPool);
      if (!frame().interaction && ['hint','show_answer','submit_correct','submit_wrong'].includes(action)) action = pick(['next','prev','timeline','reset','select_variant','clear_learning_log']);
      runAction(action);
    }
  }
  return {sequences, actions_executed: actionsExecuted, action_counts: actionCounts, violations};
}
"""


def stress_page(page: Any, row: dict[str, Any], *, sequences: int, min_actions: int, max_actions: int, seed: int) -> dict[str, Any]:
    html = row["html"]
    result = {"dataset": row["dataset"], "case_id": row["case_id"], "html": str(html)}
    if not html.exists():
        return {**result, "ok": False, "error": "missing_html", "sequences": 0, "actions_executed": 0, "violations": []}
    try:
        page.goto(html.as_uri(), wait_until="load", timeout=120_000)
        page.wait_for_function("typeof go === 'function' && typeof frame === 'function'", timeout=30_000)
        stress = page.evaluate(
            STRESS_JS,
            {
                "sequences": sequences,
                "minActions": min_actions,
                "maxActions": max_actions,
                "seed": seed,
            },
        )
        return {**result, "ok": not stress["violations"], **stress}
    except Exception as exc:
        return {**result, "ok": False, "error": f"{type(exc).__name__}: {exc}", "sequences": 0, "actions_executed": 0, "violations": []}


def extract_teaching_overlay(raw_scene: dict[str, Any]) -> dict[str, Any]:
    frames = []
    for frame in raw_scene.get("frames") or []:
        item: dict[str, Any] = {"step": frame.get("step")}
        if isinstance(frame.get("teaching"), dict):
            item["teaching"] = copy.deepcopy(frame["teaching"])
        if isinstance(frame.get("interaction"), dict):
            item["interaction"] = copy.deepcopy(frame["interaction"])
        if len(item) > 1:
            frames.append(item)
    return {"frames": frames}


def _artifact_map_from_report(path: Path | None) -> dict[str, Path]:
    if path is None:
        return {}
    data = json.loads(_repo_path(path).read_text(encoding="utf-8"))
    return {
        str(row.get("case_id")): _repo_path(str(row.get("json")))
        for row in data.get("results") or []
        if row.get("case_id") and row.get("json")
    }


def overlay_audit(path: Path, *, cross_model_path: Path | None = None) -> dict[str, Any]:
    if not path.is_file():
        return {"artifact": str(path), "ok": False, "error": "missing_artifact"}
    data = json.loads(path.read_text(encoding="utf-8"))
    cross_data = (
        json.loads(cross_model_path.read_text(encoding="utf-8"))
        if cross_model_path is not None and cross_model_path.is_file()
        else None
    )
    scene_rows = []
    for variant_id, raw_scene in (data.get("scenes") or {}).items():
        base = SceneGraph.model_validate(raw_scene)
        state_before = _sha([frame.state for frame in base.frames])
        source_frames = raw_scene.get("frames") or []
        step = int(source_frames[0].get("step", 0)) if source_frames else 0
        variants = {
            "original_reapply": extract_teaching_overlay(raw_scene),
            "concise": {"frames": [{"step": step, "teaching": {"what": "简要说明", "why": "保持算法事实不变"}}]},
            "detailed": {"frames": [{"step": step, "teaching": {"what": "详细解释当前步骤", "why": "仅扩展教学说明，不修改算法状态", "hint": "观察当前状态"}}]},
            "schema_valid_random": {"frames": [{"step": step, "teaching": {"what": "随机合法文案", "why": "随机合法理由"}}]},
            "illegal_algorithm_write": {"frames": [{"step": step, "final_answer": "tampered", "state": {"answer": "tampered"}}]},
            "missing_step": {"frames": [{"step": 10**9, "teaching": {"what": "不存在帧", "why": "测试契约"}}]},
            "negative_step": {"frames": [{"step": -1, "teaching": {"what": "非法步骤", "why": "测试 schema"}}]},
        }
        if cross_data is not None:
            cross_scenes = cross_data.get("scenes") or {}
            cross_scene = cross_scenes.get(variant_id) or next(iter(cross_scenes.values()), None)
            if isinstance(cross_scene, dict):
                variants["cross_model"] = extract_teaching_overlay(cross_scene)
        outcomes = {}
        for name, overlay in variants.items():
            scene = SceneGraph.model_validate(copy.deepcopy(raw_scene))
            warnings = apply_teaching_overlay(scene, overlay)
            state_after = _sha([frame.state for frame in scene.frames])
            outcomes[name] = {
                "algorithm_state_unchanged": state_after == state_before,
                "warnings": warnings,
                "disposition": (
                    "schema_rejected"
                    if any("schema invalid" in warning for warning in warnings)
                    else "contract_rejected"
                    if warnings
                    else "accepted_or_sanitized"
                ),
            }
        scene_rows.append({"variant_id": variant_id, "overlays": outcomes})
    return {
        "artifact": str(path),
        "cross_model_artifact": str(cross_model_path) if cross_model_path is not None else "",
        "ok": bool(scene_rows) and all(
            outcome["algorithm_state_unchanged"]
            for scene in scene_rows
            for outcome in scene["overlays"].values()
        ),
        "scenes": scene_rows,
    }


def merge_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    results = [row for report in reports for row in report.get("results") or []]
    overlays = [row for report in reports for row in report.get("overlay_results") or []]
    summary = {
        "pages": len(results),
        "pages_passed": sum(row.get("ok") is True for row in results),
        "sequences": sum(int(row.get("sequences") or 0) for row in results),
        "actions": sum(int(row.get("actions_executed") or 0) for row in results),
        "violations": sum(len(row.get("violations") or []) for row in results),
        "overlay_artifacts": len(overlays),
        "overlay_artifacts_passed": sum(row.get("ok") is True for row in overlays),
    }
    return {
        "kind": "teaching_noninterference_stress",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "merged_shards": len(reports),
        "summary": summary,
        "results": sorted(results, key=lambda row: (str(row.get("dataset")), str(row.get("case_id")))),
        "overlay_results": sorted(overlays, key=lambda row: str(row.get("artifact"))),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", default=[], help="LABEL=llm_benchmark_report.json")
    parser.add_argument("--merge-input", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sequences", type=int, default=100)
    parser.add_argument("--min-actions", type=int, default=30)
    parser.add_argument("--max-actions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--skip-overlay-audit", action="store_true")
    parser.add_argument("--cross-model-report", type=Path)
    parser.add_argument("--overlay-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.merge_input:
        reports = [json.loads(_repo_path(path).read_text(encoding="utf-8")) for path in args.merge_input]
        report = merge_reports(reports)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        return 0 if report["summary"]["violations"] == 0 else 1
    if not args.report:
        raise SystemExit("--report is required unless --merge-input is used")
    rows = _report_rows(args.report)
    rows = [row for index, row in enumerate(rows) if index % args.shard_count == args.shard_index]
    if args.max_pages > 0:
        rows = rows[: args.max_pages]
    results: list[dict[str, Any]] = []
    if not args.overlay_only:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executable = os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE", "")
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=executable if executable and Path(executable).exists() else None,
                args=["--no-sandbox"],
            )
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            page.route("**/*", lambda route: route.continue_() if route.request.url.startswith("file:") else route.abort())
            try:
                for index, row in enumerate(rows):
                    print(f"NONINTERFERENCE {index + 1}/{len(rows)} {row['case_id']}", flush=True)
                    results.append(
                        stress_page(
                            page,
                            row,
                            sequences=args.sequences,
                            min_actions=args.min_actions,
                            max_actions=args.max_actions,
                            seed=args.seed + index,
                        )
                    )
            finally:
                browser.close()
    cross_model = _artifact_map_from_report(args.cross_model_report)
    overlays = (
        []
        if args.skip_overlay_audit
        else [
            overlay_audit(row["artifact"], cross_model_path=cross_model.get(row["case_id"]))
            for row in rows
        ]
    )
    actions = sum(int(row.get("actions_executed") or 0) for row in results)
    violations = sum(len(row.get("violations") or []) for row in results)
    report = {
        "kind": "teaching_noninterference_stress",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "config": {
            "sequences_per_page": args.sequences,
            "min_actions": args.min_actions,
            "max_actions": args.max_actions,
            "seed": args.seed,
            "shard_count": args.shard_count,
            "shard_index": args.shard_index,
        },
        "summary": {
            "pages": len(results),
            "pages_passed": sum(row.get("ok") is True for row in results),
            "sequences": sum(int(row.get("sequences") or 0) for row in results),
            "actions": actions,
            "violations": violations,
            "overlay_artifacts": len(overlays),
            "overlay_artifacts_passed": sum(row.get("ok") is True for row in overlays),
        },
        "results": results,
        "overlay_results": overlays,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if violations == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
