"""Regression tests for LLM Direct Visual Renderer."""

from __future__ import annotations

import json
import re
from pathlib import Path

from algolab.generation.direct_visual_renderer import (
    build_artifact_digest,
    build_direct_visual_prompt,
    build_direct_visual_repair_prompt,
    build_direct_visual_stage_prompt,
    build_direct_visual_stage_repair_prompt,
    generate_direct_visual_html,
    generate_direct_visual_stage_shell_html,
    repair_direct_visual_html,
    repair_direct_visual_stage_shell_html,
)
from algolab.renderer.creative_direct import (
    CreativeDirectHtmlError,
    extract_html,
    extract_stage_assets,
    inject_artifact_json,
    render_direct_visual_html,
    render_direct_visual_stage_shell_html,
    sanitize_direct_visual_html,
    sanitize_direct_visual_stage_assets,
    save_direct_visual_html,
)
from tests.fixtures import fixture_artifact


GOOD_CREATIVE_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
body { margin: 0; font-family: sans-serif; }
#stage { min-height: 240px; border: 1px solid #ddd; }
</style>
</head>
<body>
<main id="app">
  <section id="stage" data-creative-stage="true"></section>
  <button id="prev">prev</button>
  <button id="next">next</button>
  <input id="range" type="range" min="0" value="0">
  <div id="counter"></div>
  <div id="explanation"></div>
</main>
<script>
const ARTIFACT = JSON.parse(document.getElementById("algolab-artifact").textContent);
let idx = 0;
function frames() {
  const scene = Object.values(ARTIFACT.scenes)[0];
  return scene.frames || [];
}
function verifiedResult() {
  const scene = Object.values(ARTIFACT.scenes)[0] || {};
  return (ARTIFACT.variants[0] || {}).result ?? scene.result ?? ARTIFACT.verifier_result ?? ARTIFACT.expected_result;
}
function renderFrame(index) {
  idx = Math.max(0, Math.min(index, frames().length - 1));
  const f = frames()[idx];
  document.getElementById("stage").textContent = `${f.title} ${JSON.stringify(f.state)} ${JSON.stringify(verifiedResult())}`;
  document.getElementById("counter").textContent = `${idx + 1} / ${frames().length}`;
  document.getElementById("explanation").textContent = f.description || f.operation || "";
}
function goFrame(index) { renderFrame(index); }
function nextFrame() { renderFrame(idx + 1); }
function prevFrame() { renderFrame(idx - 1); }
document.getElementById("next").onclick = nextFrame;
document.getElementById("prev").onclick = prevFrame;
document.getElementById("range").oninput = event => renderFrame(Number(event.target.value));
renderFrame(0);
</script>
</body>
</html>"""


GOOD_STAGE_FRAGMENT = """<style id="creative-stage-style">
.creative-rain-test { min-height: 220px; display: grid; place-items: center; }
</style>
<template id="creative-stage-template">
  <div class="creative-rain-test" data-visual="stage-template"></div>
</template>
<script>
window.renderCreativeStage = function(ctx) {
  const root = document.createElement('div');
  root.className = 'creative-rain-test';
  root.setAttribute('data-derived-visual-only', 'true');
  root.textContent = `${ctx.frame.title} ${ctx.compact(ctx.state)} ${ctx.compact(ctx.result)}`;
  ctx.host.appendChild(root);
};
</script>"""


def test_extract_html_handles_fenced_model_output():
    content = "说明\n```html\n<html><body>ok</body></html>\n```"
    assert extract_html(content) == "<html><body>ok</body></html>"


def test_sanitize_direct_visual_html_is_structure_only_by_default():
    errors = sanitize_direct_visual_html(
        '<html><head><style></style><script src="http://example.test/a.js"></script></head>'
        "<body><script>fetch('/x'); localStorage.setItem('x','1')</script></body></html>"
    )
    assert errors == []


def test_inject_artifact_json_before_generated_runtime_script():
    artifact = fixture_artifact()
    html = inject_artifact_json(GOOD_CREATIVE_HTML, artifact)
    data_index = html.index('id="algolab-artifact"')
    runtime_index = html.index('const ARTIFACT = JSON.parse')
    assert data_index < runtime_index
    assert "fixture" in html or artifact.problem_title in html


def test_injected_artifact_has_runtime_aliases_for_llm_direct_code():
    artifact = fixture_artifact()
    html = inject_artifact_json(GOOD_CREATIVE_HTML, artifact)
    match = re.search(r'<script type="application/json" id="algolab-artifact"[^>]*>(.*?)</script>', html)
    assert match
    payload = json.loads(match.group(1))
    assert payload["input"] == payload["input_data"]
    assert payload["frames"]
    assert payload["scene"]["frames"] == payload["frames"]
    assert payload["scenes"]["0"]["frames"] == payload["frames"]
    assert payload["result"] == artifact.variants[0].result


def test_render_direct_visual_html_writes_verified_artifact_data():
    artifact = fixture_artifact()
    html = render_direct_visual_html(artifact, GOOD_CREATIVE_HTML)
    assert 'id="algolab-artifact"' in html
    assert "renderFrame" in html
    assert artifact.problem_title in html


def test_stage_assets_extract_and_sanitize_stage_only_fragment():
    assets = extract_stage_assets(GOOD_STAGE_FRAGMENT)
    assert "creative-rain-test" in assets["css"]
    assert "creative-rain-test" in assets["template"]
    assert "renderCreativeStage" in assets["script"]
    assert sanitize_direct_visual_stage_assets(GOOD_STAGE_FRAGMENT) == []


def test_stage_assets_do_not_reject_urls_or_browser_api_strings_before_smoke_audit():
    fragment = GOOD_STAGE_FRAGMENT.replace(
        "ctx.host.appendChild(root);",
        "document.createElementNS('http://www.w3.org/2000/svg', 'svg');"
        "document.createElementNS('http://www.w3.org/1999/xhtml', 'body');"
        "const x = 'https://example.com/a.png';"
        "const y = typeof fetch === 'function';"
        "ctx.host.appendChild(root);",
    )
    assert sanitize_direct_visual_stage_assets(fragment) == []


def test_stage_assets_allow_full_document_wrapper_but_reject_reserved_shell_id():
    bad = GOOD_STAGE_FRAGMENT.replace('class="creative-rain-test"', 'id="counter"', 1)
    errors = sanitize_direct_visual_stage_assets("<html><body>" + bad + "</body></html>")
    assert any(error.startswith("reserved_shell_id_in_stage_template") for error in errors)
    assert sanitize_direct_visual_stage_assets("<html><body>" + GOOD_STAGE_FRAGMENT + "</body></html>") == []


def test_render_direct_visual_stage_shell_html_wraps_llm_stage_with_deterministic_panels():
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, GOOD_STAGE_FRAGMENT)
    assert 'data-render-target="creative_stage_shell"' in html
    assert 'id="creative-stage-host"' in html
    assert 'id="teaching-panel"' in html
    assert 'id="pseudocode"' in html
    assert 'window.renderCreativeStage' in html
    assert 'id="algolab-artifact"' in html
    assert artifact.problem_title in html


def test_render_direct_visual_html_raises_on_empty_html():
    artifact = fixture_artifact()
    try:
        render_direct_visual_html(artifact, "")
    except CreativeDirectHtmlError as exc:
        assert "empty_html" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected CreativeDirectHtmlError")


def test_build_direct_visual_prompt_includes_runtime_contract_and_selected_frames():
    artifact = fixture_artifact()
    prompt = build_direct_visual_prompt(artifact, problem_description="接雨水题目描述")
    assert "接雨水题目描述" in prompt
    assert "algolab-artifact" in prompt
    assert "Selected frame examples" in prompt
    digest = build_artifact_digest(artifact)
    assert digest["trace_summary"]["frame_count"] >= 1
    assert digest["selected_frames"]


def test_build_direct_visual_stage_prompt_limits_llm_to_stage_contract():
    artifact = fixture_artifact()
    prompt = build_direct_visual_stage_prompt(artifact, problem_description="接雨水题目描述")
    assert "接雨水题目描述" in prompt
    assert "Creative Shell contract" in prompt
    assert "renderCreativeStage" in prompt
    assert "只输出 stage 资产" in prompt


def test_generate_direct_visual_html_accepts_fake_chat_fn():
    artifact = fixture_artifact()

    def fake_chat(_system: str, user: str):
        assert "Runtime contract" in user
        return {"content": GOOD_CREATIVE_HTML, "model_calls": [{"kind": "direct_visual", "total_tokens": 3}]}

    result = generate_direct_visual_html(artifact, chat_fn=fake_chat)
    assert result.creative_ok
    assert 'id="algolab-artifact"' in result.html
    assert result.model_calls[0]["kind"] == "direct_visual"


def test_generate_direct_visual_stage_shell_html_accepts_fake_chat_fn():
    artifact = fixture_artifact()

    def fake_chat(system: str, user: str):
        assert "Creative Stage Renderer" in system
        assert "Creative Shell contract" in user
        return {"content": GOOD_STAGE_FRAGMENT, "model_calls": [{"kind": "direct_visual_stage", "total_tokens": 7}]}

    result = generate_direct_visual_stage_shell_html(artifact, chat_fn=fake_chat)
    assert result.creative_ok
    assert 'data-render-target="creative_stage_shell"' in result.html
    assert 'id="creative-stage-host"' in result.html
    assert result.model_calls[0]["kind"] == "direct_visual_stage"


def test_build_direct_visual_repair_prompt_includes_failure_and_runtime_contract():
    artifact = fixture_artifact()
    prompt = build_direct_visual_repair_prompt(
        artifact,
        broken_html="<html><body><script>const tree = artifact.scene;</script></body></html>",
        failure_report={"page_errors": ["Cannot read properties of undefined (reading 'forEach')"]},
    )
    assert "Cannot read properties" in prompt
    assert "artifact.input_data" in prompt
    assert "artifact.scene 是 SceneGraph" in prompt
    assert "Previous broken HTML" in prompt


def test_repair_direct_visual_html_accepts_fake_chat_fn():
    artifact = fixture_artifact()

    def fake_chat(_system: str, user: str):
        assert "Browser/smoke failure report" in user
        assert "artifact.scene 是 SceneGraph" in user
        return {"content": GOOD_CREATIVE_HTML, "model_calls": [{"kind": "direct_visual_repair", "total_tokens": 5}]}

    result = repair_direct_visual_html(
        artifact,
        broken_html="<html><body><script>const broken = artifact.scene.nodes;</script></body></html>",
        failure_report={"failure_categories": ["page_errors"]},
        chat_fn=fake_chat,
    )
    assert result.creative_ok
    assert 'id="algolab-artifact"' in result.html
    assert result.model_calls[0]["kind"] == "direct_visual_repair"


def test_build_direct_visual_stage_repair_prompt_targets_layout_only():
    artifact = fixture_artifact()
    prompt = build_direct_visual_stage_repair_prompt(
        artifact,
        broken_stage=GOOD_STAGE_FRAGMENT,
        failure_report={
            "stage_overlap_count": 2,
            "stage_layout_issues": [{"type": "overlap", "frame_index": 1, "a": "label A", "b": "label B"}],
        },
    )
    assert "Browser layout failure report" in prompt
    assert "Creative Shell repair contract" in prompt
    assert "只输出 <style>" in prompt
    assert "不要输出完整 HTML" in prompt
    assert "stage_overlap_count" in prompt


def test_repair_direct_visual_stage_shell_html_accepts_fake_chat_fn():
    artifact = fixture_artifact()

    def fake_chat(system: str, user: str):
        assert "Creative Stage 布局修复器" in system
        assert "Browser layout failure report" in user
        assert "Now return only repaired stage assets" in user
        return {"content": GOOD_STAGE_FRAGMENT, "model_calls": [{"kind": "direct_visual_stage_repair", "total_tokens": 9}]}

    result = repair_direct_visual_stage_shell_html(
        artifact,
        broken_stage=GOOD_STAGE_FRAGMENT,
        failure_report={"stage_overlap_count": 1, "stage_layout_issues": [{"type": "overlap"}]},
        chat_fn=fake_chat,
    )
    assert result.creative_ok
    assert 'data-render-target="creative_stage_shell"' in result.html
    assert 'id="creative-stage-host"' in result.html
    assert result.model_calls[0]["kind"] == "direct_visual_stage_repair"


def test_save_direct_visual_html_writes_html_and_sidecar(tmp_path: Path):
    artifact = fixture_artifact()
    path = save_direct_visual_html(artifact, GOOD_CREATIVE_HTML, tmp_path / "creative.html")
    assert path.exists()
    assert path.with_suffix(".json").exists()
    assert 'id="algolab-artifact"' in path.read_text(encoding="utf-8")
