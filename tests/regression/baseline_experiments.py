"""Regression tests for baseline and ablation experiment runners."""

from __future__ import annotations

import argparse
import json
import os
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
        llm_max_tokens=0,
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


def _valid_direct_html(answer: str = "[0,1]") -> str:
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>直接 HTML</title></head>
<body>
  <h1 id="title">两数之和</h1>
  <p id="subtitle">direct HTML baseline</p>
  <strong id="top-result">{answer}</strong>
  <strong id="top-solution">哈希表法</strong>
  <section id="code"><div class="line active">1 def solve(input_data): return [0, 1]</div></section>
  <h2 id="step-title">初始化</h2>
  <p id="step-desc">创建数组和哈希表</p>
  <div id="op">create</div>
  <main id="canvas">数组 [2,7,11,15]，当前检查 i=0。</main>
  <button id="prev" onclick="go(0)">上一步</button>
  <button id="play">播放</button>
  <button id="next" onclick="go(1)">下一步</button>
  <input id="range" type="range" min="0" max="1" value="0" oninput="go(Number(this.value))">
  <div id="counter">1 / 2</div>
  <div id="timeline" aria-label="语义时间线">
    <button class="tick active" onclick="go(0)"><span class="tick-label">初始化</span><span class="tick-op">create</span></button>
    <button class="tick" onclick="go(1)"><span class="tick-label">返回</span><span class="tick-op">answer</span></button>
  </div>
  <section id="teaching">当前步骤：初始化。为什么：建立状态。</section>
  <section id="state">{{"i":0,"seen":{{}}}}</section>
  <section id="step-evidence">本步语义：create；状态变化：seen={{}}</section>
  <pre id="answer">{answer}</pre>
  <script>
    const steps = [
      {{title:'初始化', desc:'创建数组和哈希表', op:'create', canvas:'数组 [2,7,11,15]，当前检查 i=0。', state:'{{"i":0,"seen":{{}}}}', teaching:'当前步骤：初始化。为什么：建立状态。', evidence:'本步语义：create；状态变化：seen={{}}'}},
      {{title:'返回', desc:'找到答案', op:'answer', canvas:'答案下标 [0,1]', state:'{{"answer":[0,1]}}', teaching:'当前步骤：返回。为什么：2+7=9。', evidence:'本步语义：answer；状态变化：answer=[0,1]'}}
    ];
    function go(i) {{
      document.getElementById('range').value = String(i);
      document.getElementById('counter').textContent = `${{i + 1}} / ${{steps.length}}`;
      document.getElementById('step-title').textContent = steps[i].title;
      document.getElementById('step-desc').textContent = steps[i].desc;
      document.getElementById('op').textContent = steps[i].op;
      document.getElementById('canvas').textContent = steps[i].canvas;
      document.getElementById('state').textContent = steps[i].state;
      document.getElementById('teaching').textContent = steps[i].teaching;
      document.getElementById('step-evidence').textContent = steps[i].evidence;
      document.querySelectorAll('#timeline .tick').forEach((tick, idx) => tick.classList.toggle('active', idx === i));
    }}
  </script>
</body></html>"""


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
        return {"content": _valid_direct_html()}

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
    assert "AlgoLab-style" in hidden_prompt
    for required in ("#code", "#state", "#teaching", "#timeline", "#step-title", "#step-desc", "#prev", "#play", "#range"):
        assert required in hidden_prompt
    assert "裸 JSON" in hidden_prompt
    assert "不要包成" in hidden_prompt
    assert "题目最终返回值" in hidden_prompt
    assert "不是当前操作参数" in hidden_prompt
    assert "推荐骨架" not in hidden_prompt
    assert '<div id="canvas">' not in hidden_prompt
    assert 'class="visual-svg"' not in hidden_prompt
    assert "steps 数组" not in hidden_prompt
    assert "render(i)" not in hidden_prompt
    assert "输出要短" not in hidden_prompt
    assert "4-12" not in hidden_prompt


def test_direct_html_repair_prompt_discards_broken_html_for_missing_shell() -> None:
    case = _case("dijkstra_shortest_path")
    sample = case.samples[0]

    prompt = direct_html._repair_prompt(
        case,
        sample,
        previous_html="",
        errors=[
            "html_error: missing <html>",
            "html_error: missing #title",
            "html_error: missing #canvas",
        ],
        expected_visible_to_model=False,
    )

    assert "上一版可能没有可复用的 HTML" in prompt
    assert "从零重写" in prompt
    assert "题目最终返回值" in prompt
    assert "推荐骨架" not in prompt
    assert '<div id="canvas">' not in prompt
    assert 'class="visual-svg"' not in prompt
    assert "steps 数组" not in prompt
    assert "render(i)" not in prompt
    assert "输出要短" not in prompt
    assert "4-12" not in prompt


def test_direct_html_validation_rejects_canvas_id_on_svg_without_browser() -> None:
    html = _valid_direct_html().replace(
        '<main id="canvas">数组 [2,7,11,15]，当前检查 i=0。</main>',
        '<svg id="canvas"><text>数组 [2,7,11,15]，当前检查 i=0。</text></svg>',
    )

    errors = direct_html.validate_direct_html(html)

    assert "html_error: #canvas must be an HTMLElement text container, not <svg>" in errors


def test_direct_html_validation_requires_algolab_style_structure() -> None:
    legacy_html = """<!doctype html>
<html lang="zh-CN"><body>
  <h1 id="title">两数之和</h1>
  <div id="counter">1 / 1</div>
  <main id="canvas">旧 direct HTML baseline 教学内容</main>
  <pre id="answer">[0, 1]</pre>
  <button id="next">下一步</button>
</body></html>"""

    errors = direct_html.validate_direct_html(legacy_html)

    assert "html_error: missing #code" in errors
    assert "html_error: missing #state" in errors
    assert "html_error: missing #teaching" in errors
    assert "html_error: missing #timeline" in errors


def test_direct_html_validation_accepts_algolab_style_html() -> None:
    html = """<!doctype html>
<html lang="zh-CN"><body>
  <h1 id="title">两数之和</h1>
  <p id="subtitle">direct HTML baseline</p>
  <strong id="top-result">[0,1]</strong>
  <strong id="top-solution">哈希表法</strong>
  <section id="code">1 def solve(input_data): return [0, 1]</section>
  <h2 id="step-title">初始化</h2>
  <p id="step-desc">创建数组和哈希表</p>
  <div id="op">create</div>
  <main id="canvas">数组 [2,7,11,15]，当前检查 i=0。</main>
  <button id="prev">上一步</button>
  <button id="play">播放</button>
  <button id="next">下一步</button>
  <input id="range" type="range" min="0" max="1" value="0">
  <div id="counter">1 / 2</div>
  <div id="timeline" aria-label="语义时间线">
    <button class="tick"><span class="tick-label">初始化</span><span class="tick-op">create</span></button>
    <button class="tick"><span class="tick-label">返回</span><span class="tick-op">answer</span></button>
  </div>
  <section id="teaching">当前步骤：初始化。为什么：建立状态。</section>
  <section id="state">{"i":0,"seen":{}}</section>
  <section id="step-evidence">本步语义：create；状态变化：seen={}</section>
  <pre id="answer">[0,1]</pre>
</body></html>"""

    assert direct_html.validate_direct_html(html) == []


def test_direct_html_browser_check_rejects_canvas_id_on_svg(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    html = _valid_direct_html().replace(
        '<main id="canvas">数组 [2,7,11,15]，当前检查 i=0。</main>',
        '<svg id="canvas"><text>数组 [2,7,11,15]，当前检查 i=0。</text></svg>',
    )
    path = tmp_path / "bad_canvas.html"
    path.write_text(html, encoding="utf-8")

    result = direct_html.direct_html_browser_check(path)

    assert result["ok"] is False
    assert any("must be an HTMLElement text container" in error for error in result["errors"])


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
        return {"content": _valid_direct_html()}

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
        return {"content": _valid_direct_html()}

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


def test_direct_html_failure_writes_last_invalid_artifact(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="direct_html_no_expected")
    args.baseline = "direct_html_no_expected"
    args.direct_html_baseline = True
    args.expected_visible_to_model = False
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False

    def fake_chat_text_with_metadata(*_args, **_kwargs):
        llm_client.record_model_call(_model_call("direct_html"))
        return {"content": "<section>不是完整 HTML</section>"}

    original = direct_html.chat_text_with_metadata
    direct_html.chat_text_with_metadata = fake_chat_text_with_metadata
    try:
        result = direct_html.run_one_direct_html(case, sample, 0, args)
    finally:
        direct_html.chat_text_with_metadata = original

    assert result["ok"] is False
    failed_html = tmp_path / "direct_html_two_sum_0.failed.html"
    failed_json = tmp_path / "direct_html_two_sum_0.failed.json"
    assert failed_html.exists()
    assert failed_json.exists()
    assert result["failed_html"] == str(failed_html)
    assert "<section>不是完整 HTML</section>" in failed_html.read_text(encoding="utf-8")


def test_direct_html_failure_writes_raw_response_when_no_html_extracted(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="direct_html_no_expected")
    args.baseline = "direct_html_no_expected"
    args.direct_html_baseline = True
    args.expected_visible_to_model = False
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False

    def fake_chat_text_with_metadata(*_args, **_kwargs):
        llm_client.record_model_call(_model_call("direct_html"))
        return {"content": "不是 HTML，也没有 html 标签"}

    original = direct_html.chat_text_with_metadata
    direct_html.chat_text_with_metadata = fake_chat_text_with_metadata
    try:
        result = direct_html.run_one_direct_html(case, sample, 0, args)
    finally:
        direct_html.chat_text_with_metadata = original

    raw_text = tmp_path / "direct_html_two_sum_0.raw.txt"
    raw_json = tmp_path / "direct_html_two_sum_0.raw.json"
    assert result["ok"] is False
    assert raw_text.exists()
    assert raw_json.exists()
    assert result["raw_response"] == str(raw_text)
    assert "不是 HTML" in raw_text.read_text(encoding="utf-8")


def test_direct_html_runner_can_override_llm_max_tokens(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="direct_html_baseline")
    args.baseline = "direct_html_baseline"
    args.direct_html_baseline = True
    args.process_validator_enabled = False
    args.scenegraph_compiler_enabled = False
    args.trace_only_renderer_enabled = False
    args.llm_max_tokens = 65536
    old_max_tokens = os.environ.get("ALGOLAB_LLM_MAX_TOKENS")
    seen: list[str | None] = []

    def fake_chat_text_with_metadata(*_args, **_kwargs):
        seen.append(os.environ.get("ALGOLAB_LLM_MAX_TOKENS"))
        llm_client.record_model_call(_model_call("direct_html"))
        return {"content": _valid_direct_html()}

    original = direct_html.chat_text_with_metadata
    direct_html.chat_text_with_metadata = fake_chat_text_with_metadata
    try:
        result = direct_html.run_one_direct_html(case, sample, 0, args)
    finally:
        direct_html.chat_text_with_metadata = original
        if old_max_tokens is None:
            os.environ.pop("ALGOLAB_LLM_MAX_TOKENS", None)
        else:
            os.environ["ALGOLAB_LLM_MAX_TOKENS"] = old_max_tokens

    assert result["ok"] is True
    assert seen == ["65536"]


def test_direct_html_report_records_llm_max_tokens_override(tmp_path: Path):
    case = _case("two_sum")
    sample = case.samples[0]
    args = _args(tmp_path, condition="direct_html_no_expected")
    args.baseline = "direct_html_no_expected"
    args.direct_html_baseline = True
    args.expected_visible_to_model = False
    args.direct_html_repair_enabled = True
    args.direct_html_browser_repair_enabled = False
    args.direct_html_llm_max_tokens = 65536
    args.llm_max_tokens = 65536

    result = {
        "case_id": case.id,
        "title": case.title,
        "family": case.family,
        "sample_index": 0,
        "ok": True,
        "html": str(tmp_path / "direct_html_two_sum_0.html"),
        "expected": sample.expected,
        "duration_s": 1.0,
        "model_calls": [],
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    Path(result["html"]).write_text(_valid_direct_html(), encoding="utf-8")

    report_path = write_report(
        [result],
        tmp_path,
        args=args,
        started_at="2026-05-30T00:00:00",
        ended_at="2026-05-30T00:00:01",
    )

    config = json.loads(report_path.read_text(encoding="utf-8"))["config"]
    assert config["llm_max_tokens"] == 65536
    assert config["direct_html_llm_max_tokens"] == 65536


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
        test_direct_html_repair_prompt_discards_broken_html_for_missing_shell()
        test_direct_html_validation_requires_algolab_style_structure()
        test_direct_html_validation_accepts_algolab_style_html()
        test_direct_html_validation_rejects_canvas_id_on_svg_without_browser()
        test_direct_html_browser_check_rejects_canvas_id_on_svg(root / "bad_canvas")
        test_direct_html_repairs_invalid_html_with_max_rounds(root / "repair_html")
        test_direct_html_repairs_browser_smoke_failure_when_enabled(root / "repair_browser")
        test_direct_html_failure_writes_last_invalid_artifact(root / "failed_html")
        test_direct_html_failure_writes_raw_response_when_no_html_extracted(root / "raw_response")
        test_direct_html_runner_can_override_llm_max_tokens(root / "max_tokens")
        test_direct_html_report_records_llm_max_tokens_override(root / "report_max_tokens")
        test_no_process_validator_ablation_records_flag_and_restores_pipeline(root / "no_process")
        test_no_scenegraph_compiler_ablation_writes_trace_only_report_and_failure_types(root / "no_scene")


if __name__ == "__main__":
    run_all()
    print("baseline_experiments: PASS")
