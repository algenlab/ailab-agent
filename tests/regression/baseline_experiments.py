"""Regression tests for baseline and ablation experiment runners."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import algolab.pipeline as pipeline
import llm_client
from scripts.run_llm_benchmark import browser_smoke_html_paths, write_report
from scripts import run_direct_html_baseline as direct_html
from scripts import run_no_process_validator_ablation as no_process
from scripts import run_no_scenegraph_compiler_ablation as no_scene
from tests.benchmark_cases import benchmark_cases
from tests.regression.helpers import spec_for_case


def _args(tmp_path: Path, *, condition: str) -> argparse.Namespace:
    return argparse.Namespace(
        case=[],
        sample=None,
        all_samples=False,
        solutions=1,
        max_rounds=0,
        timeout_s=30,
        strict_warnings=True,
        browser_smoke=False,
        write_each=True,
        concurrency=1,
        family=[],
        gate_layer=[],
        limit_per_family=0,
        case_set="deterministic",
        family_sets=Path("benchmark/llm_family_sets.json"),
        unseen_cases=Path("benchmark/unseen_family_cases.json"),
        condition=condition,
        output_dir=tmp_path,
    )


def _model_call(kind: str) -> dict:
    return {
        "kind": kind,
        "model": "fake-model",
        "started_at": "2026-05-30T00:00:00",
        "ended_at": "2026-05-30T00:00:01",
        "duration_s": 1.0,
        "usage_available": True,
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
    }


def _case(case_id: str):
    return next(case for case in benchmark_cases() if case.id == case_id)


def test_direct_html_baseline_writes_html_and_runs_browser_smoke(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="direct_html_baseline")
    args.baseline = "direct_html_baseline"
    args.direct_html_baseline = True
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False

    def fake_chat_text_with_metadata(*_args, **_kwargs):
        llm_client.record_model_call(_model_call("direct_html"))
        return {
            "content": """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>直接 HTML</title></head>
<body>
  <h1 id="title">两数之和</h1>
  <div id="counter">1 / 1</div>
  <main id="canvas">直接 HTML baseline 教学内容</main>
  <button id="next" onclick="document.getElementById('canvas').textContent='完成'">下一步</button>
</body></html>"""
        }

    original = direct_html.chat_text_with_metadata
    direct_html.chat_text_with_metadata = fake_chat_text_with_metadata
    try:
        result = direct_html.run_one_direct_html(case, sample, 0, args)
    finally:
        direct_html.chat_text_with_metadata = original

    assert result["ok"] is True
    assert result["baseline"] == "direct_html_baseline"
    assert Path(result["html"]).exists()
    checks = browser_smoke_html_paths([Path(result["html"])])
    assert checks and checks[0]["ok"] is True

    report_path = write_report(
        [result],
        tmp_path,
        args=args,
        started_at="2026-05-30T00:00:00",
        ended_at="2026-05-30T00:00:01",
        browser_checks=checks,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["config"]["benchmark_condition"] == "direct_html_baseline"
    assert report["config"]["direct_html_baseline"] is True
    assert report["browser_smoke"][0]["ok"] is True


def test_direct_html_prompt_can_hide_expected_output() -> None:
    case = _case("two_sum")
    sample = case.samples[0]

    visible_prompt = direct_html._user_prompt(case, sample, expected_visible_to_model=True)
    hidden_prompt = direct_html._user_prompt(case, sample, expected_visible_to_model=False)

    assert "期望输出 JSON" in visible_prompt
    assert json.dumps(sample.expected, ensure_ascii=False) in visible_prompt
    assert "期望输出 JSON" not in hidden_prompt
    assert json.dumps(sample.expected, ensure_ascii=False) not in hidden_prompt
    assert "请自行求解" in hidden_prompt
    assert "#answer" in hidden_prompt


def test_direct_html_repairs_invalid_html_with_max_rounds(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="direct_html_no_expected")
    args.baseline = "direct_html_no_expected"
    args.direct_html_baseline = True
    args.expected_visible_to_model = False
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False
    args.max_rounds = 1
    calls: list[str] = []

    def fake_chat_text_with_metadata(_system, user, **_kwargs):
        calls.append(user)
        llm_client.record_model_call(_model_call("direct_html"))
        if len(calls) == 1:
            return {"content": "这不是 HTML"}
        return {
            "content": """<!doctype html>
<html lang="zh-CN"><body>
  <h1 id="title">两数之和</h1>
  <div id="counter">1 / 1</div>
  <main id="canvas">完成</main>
  <pre id="answer">[0, 1]</pre>
  <button id="next">下一步</button>
</body></html>"""
        }

    original = direct_html.chat_text_with_metadata
    direct_html.chat_text_with_metadata = fake_chat_text_with_metadata
    try:
        result = direct_html.run_one_direct_html(case, sample, 0, args)
    finally:
        direct_html.chat_text_with_metadata = original

    assert result["ok"] is True
    assert result["direct_html_repair_attempted"] is True
    assert result["direct_html_repair_rounds"] == 1
    assert "期望输出 JSON" not in calls[1]
    assert "missing <html>" in calls[1]
    assert Path(result["html"]).exists()


def test_direct_html_repairs_browser_smoke_failure_when_enabled(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="direct_html_no_expected")
    args.baseline = "direct_html_no_expected"
    args.direct_html_baseline = True
    args.expected_visible_to_model = False
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False
    args.browser_smoke = True
    args.max_rounds = 1
    calls: list[str] = []
    smoke_calls = 0

    def fake_chat_text_with_metadata(_system, user, **_kwargs):
        calls.append(user)
        llm_client.record_model_call(_model_call("direct_html"))
        return {
            "content": """<!doctype html>
<html lang="zh-CN"><body>
  <h1 id="title">两数之和</h1>
  <div id="counter">1 / 1</div>
  <main id="canvas">完成</main>
  <pre id="answer">[0, 1]</pre>
  <button id="next">下一步</button>
</body></html>"""
        }

    def fake_browser_smoke_html_paths(paths):
        nonlocal smoke_calls
        smoke_calls += 1
        if smoke_calls == 1:
            return [{"html": str(paths[0]), "ok": False, "errors": ["pageerror: boom"]}]
        return [{"html": str(paths[0]), "ok": True, "errors": []}]

    original_chat = direct_html.chat_text_with_metadata
    original_smoke = direct_html.browser_smoke_html_paths
    direct_html.chat_text_with_metadata = fake_chat_text_with_metadata
    direct_html.browser_smoke_html_paths = fake_browser_smoke_html_paths
    try:
        result = direct_html.run_one_direct_html(case, sample, 0, args)
    finally:
        direct_html.chat_text_with_metadata = original_chat
        direct_html.browser_smoke_html_paths = original_smoke

    assert result["ok"] is True
    assert result["direct_html_repair_attempted"] is True
    assert result["direct_html_repair_rounds"] == 1
    assert smoke_calls == 2
    assert "pageerror: boom" in calls[1]


def test_no_process_validator_ablation_records_flag_and_restores_pipeline(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="no_process_validator")
    args.ablation = "no_process_validator"
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = True
    args.direct_html_baseline = False
    args.trace_only_renderer_enabled = False
    original_generate = no_process.generate_solution_spec
    original_pipeline_validate = pipeline.validate_process
    no_process.generate_solution_spec = lambda _request: spec_for_case(case)
    try:
        result = no_process.run_one_no_process_validator(case, sample, 0, args)
    finally:
        no_process.generate_solution_spec = original_generate

    assert pipeline.validate_process is original_pipeline_validate
    assert result["process_validator_enabled"] is False
    assert result["scenegraph_compiler_enabled"] is True
    assert Path(result["html"]).exists()
    report_path = write_report(
        [result],
        tmp_path,
        args=args,
        started_at="2026-05-30T00:00:00",
        ended_at="2026-05-30T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["config"]["process_validator_enabled"] is False
    assert report["config"]["scenegraph_compiler_enabled"] is True


def test_no_scenegraph_compiler_ablation_writes_trace_only_report_and_failure_types(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="no_scenegraph_compiler")
    args.ablation = "no_scenegraph_compiler"
    args.process_validator_enabled = True
    args.scenegraph_compiler_enabled = False
    args.direct_html_baseline = False
    args.trace_only_renderer_enabled = True
    original_generate = no_scene.generate_solution_spec
    no_scene.generate_solution_spec = lambda _request: spec_for_case(case)
    try:
        result = no_scene.run_one_no_scenegraph_compiler(case, sample, 0, args)
    finally:
        no_scene.generate_solution_spec = original_generate

    assert result["ok"] is True
    assert result["scenegraph_compiler_enabled"] is False
    assert result["trace_only_renderer_enabled"] is True
    assert "SceneGraph compiler disabled" in " ".join(result["checks"])
    assert Path(result["html"]).read_text(encoding="utf-8").count("trace-only renderer") >= 1

    failed = dict(result)
    failed["ok"] = False
    failed["failure_type"] = "scene_error"
    failed["error"] = "scene compiler disabled caused scene validator failure"
    report_path = write_report(
        [failed],
        tmp_path,
        args=args,
        started_at="2026-05-30T00:00:00",
        ended_at="2026-05-30T00:00:01",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["config"]["scenegraph_compiler_enabled"] is False
    assert report["config"]["trace_only_renderer_enabled"] is True
    assert report["failure_summary"] == {"scene_error": 1}


def run_all() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        test_direct_html_baseline_writes_html_and_runs_browser_smoke(root / "direct")
        test_direct_html_prompt_can_hide_expected_output()
        test_direct_html_repairs_invalid_html_with_max_rounds(root / "repair_html")
        test_direct_html_repairs_browser_smoke_failure_when_enabled(root / "repair_browser")
        test_no_process_validator_ablation_records_flag_and_restores_pipeline(root / "no_process")
        test_no_scenegraph_compiler_ablation_writes_trace_only_report_and_failure_types(root / "no_scene")


if __name__ == "__main__":
    run_all()
    print("baseline_experiments: PASS")
