"""Render and sanitize LLM-generated direct creative visualization HTML."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from algolab.schemas.validation import BuildArtifact


class CreativeDirectHtmlError(ValueError):
    """Raised when a direct creative HTML page violates the sandbox contract."""


RESERVED_STAGE_IDS = {
    "algolab-artifact",
    "app",
    "badges",
    "canvas",
    "code",
    "counter",
    "creative-stage-host",
    "creative-stage-template",
    "debug-artifact",
    "debug-state",
    "evidence",
    "explanation",
    "interaction",
    "next",
    "op",
    "play",
    "prev",
    "range",
    "stage",
    "state",
    "step-desc",
    "step-evidence",
    "step-title",
    "teaching",
    "timeline",
    "title",
    "top-result",
    "top-solution",
}


def extract_html(content: str) -> str:
    """Extract the HTML document from a model response."""

    text = (content or "").strip()
    if not text:
        return ""
    fenced = re.search(r"```(?:html)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    lower = text.lower()
    starts = [idx for idx in (lower.find("<!doctype"), lower.find("<html")) if idx >= 0]
    if starts:
        text = text[min(starts) :].strip()
    end_match = re.search(r"</html\s*>", text, flags=re.IGNORECASE)
    if end_match:
        text = text[: end_match.end()].strip()
    return text if "<" in text and ">" in text else ""


def sanitize_direct_visual_html(html: str) -> list[str]:
    """Return minimal structure errors for LLM-generated creative HTML.

    Browser smoke/screenshots are the primary quality gate. This sanitizer is
    intentionally permissive so valid HTML/SVG idioms are not rejected before
    the page is actually opened.
    """

    errors: list[str] = []
    text = html or ""
    lower = text.lower()
    if not text.strip():
        return ["empty_html"]
    if "<html" not in lower:
        errors.append("missing_html_tag")
    if "<script" not in lower:
        errors.append("missing_script_tag")
    if "<style" not in lower:
        errors.append("missing_style_tag")
    return sorted(set(errors))


def render_direct_visual_html(artifact: BuildArtifact, generated_html: str) -> str:
    """Validate a generated creative page and inject verified artifact JSON."""

    html = extract_html(generated_html)
    errors = sanitize_direct_visual_html(html)
    if errors:
        raise CreativeDirectHtmlError("; ".join(errors))
    return inject_artifact_json(html, artifact)


def render_direct_visual_stage_shell_html(artifact: BuildArtifact, generated_stage: str) -> str:
    """Wrap a generated stage-only renderer in the deterministic Creative Shell."""

    errors = sanitize_direct_visual_stage_assets(generated_stage)
    if errors:
        raise CreativeDirectHtmlError("; ".join(errors))
    assets = extract_stage_assets(generated_stage)
    return _creative_stage_shell_html(artifact, assets)


def save_direct_visual_html(artifact: BuildArtifact, generated_html: str, output_path: str | Path) -> Path:
    """Write sanitized creative HTML plus the verified artifact JSON sidecar."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_direct_visual_html(artifact, generated_html), encoding="utf-8")
    output.with_suffix(".json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return output


def save_direct_visual_stage_shell_html(
    artifact: BuildArtifact,
    generated_stage: str,
    output_path: str | Path,
) -> Path:
    """Write deterministic Creative Shell HTML plus the verified artifact JSON sidecar."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_direct_visual_stage_shell_html(artifact, generated_stage), encoding="utf-8")
    output.with_suffix(".json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return output


def inject_artifact_json(html: str, artifact: BuildArtifact) -> str:
    """Inject the verified artifact before generated runtime scripts execute."""

    without_existing = re.sub(
        r"<script\b(?=[^>]*\bid\s*=\s*['\"]algolab-artifact['\"])[^>]*>.*?</script>",
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    payload = json.dumps(_runtime_artifact_payload(artifact), ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    data_script = (
        '<script type="application/json" id="algolab-artifact" '
        f'data-source="verified-artifact">{payload}</script>\n'
    )
    first_script = re.search(r"<script\b", without_existing, flags=re.IGNORECASE)
    if first_script:
        return without_existing[: first_script.start()] + data_script + without_existing[first_script.start() :]
    body_close = re.search(r"</body\s*>", without_existing, flags=re.IGNORECASE)
    if body_close:
        return without_existing[: body_close.start()] + data_script + without_existing[body_close.start() :]
    return without_existing + "\n" + data_script


def extract_stage_assets(content: str) -> dict[str, str]:
    """Extract stage CSS, template markup and JavaScript from a model response."""

    text = _strip_fenced_text(content or "").strip()
    if re.search(r"<\s*html\b", text, flags=re.IGNORECASE):
        text = extract_html(text) or text
    css_blocks = re.findall(r"<\s*style\b[^>]*>(.*?)</\s*style\s*>", text, flags=re.IGNORECASE | re.DOTALL)
    script_blocks = re.findall(r"<\s*script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</\s*script\s*>", text, flags=re.IGNORECASE | re.DOTALL)
    template_match = re.search(
        r"<\s*template\b(?=[^>]*\bid\s*=\s*['\"]creative-stage-template['\"])[^>]*>(.*?)</\s*template\s*>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if template_match:
        template = template_match.group(1).strip()
    else:
        template = re.sub(r"<\s*style\b[^>]*>.*?</\s*style\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
        template = re.sub(r"<\s*script\b[^>]*>.*?</\s*script\s*>", "", template, flags=re.IGNORECASE | re.DOTALL)
        template = re.sub(r"<\s*/?\s*(?:!doctype|html|head|body)\b[^>]*>", "", template, flags=re.IGNORECASE)
        template = re.sub(r"<\s*template\b[^>]*>|</\s*template\s*>", "", template, flags=re.IGNORECASE).strip()
    return {
        "source": text,
        "css": "\n\n".join(block.strip() for block in css_blocks if block.strip()),
        "template": template,
        "script": "\n\n".join(block.strip() for block in script_blocks if block.strip()),
    }


def sanitize_direct_visual_stage_assets(content: str) -> list[str]:
    """Return minimal shell-contract violations for stage-only model output.

    The deterministic shell and Playwright smoke audit decide whether the page
    opens and renders correctly. Pre-render checks only catch cases that cannot
    be embedded as a Creative Stage at all.
    """

    text = _strip_fenced_text(content or "").strip()
    if not text:
        return ["empty_stage"]
    errors: list[str] = []
    assets = extract_stage_assets(text)
    if not assets["script"]:
        errors.append("missing_stage_script")
    if "renderCreativeStage" not in assets["script"] and "renderCreativeStage" not in text:
        errors.append("missing_render_creative_stage")
    template_ids = set(
        match.group(1) or match.group(2)
        for match in re.finditer(r"\bid\s*=\s*(?:['\"]([^'\"]+)['\"]|([^\s>]+))", assets["template"])
    )
    reserved = sorted(template_ids & RESERVED_STAGE_IDS)
    if reserved:
        errors.append("reserved_shell_id_in_stage_template:" + ",".join(reserved[:6]))
    return sorted(set(errors))


def _runtime_artifact_payload(artifact: BuildArtifact) -> dict[str, Any]:
    """Return the verified artifact plus read-only convenience aliases for LLM code."""

    payload = artifact.model_dump()
    payload.setdefault("input", payload.get("input_data"))
    variants = payload.get("variants") if isinstance(payload.get("variants"), list) else []
    scenes = payload.get("scenes") if isinstance(payload.get("scenes"), dict) else {}
    first_variant = variants[0] if variants and isinstance(variants[0], dict) else {}
    first_scene_id = str(first_variant.get("id") or "") if first_variant else ""
    first_scene = scenes.get(first_scene_id) if first_scene_id else None
    if not isinstance(first_scene, dict):
        first_scene = next((scene for scene in scenes.values() if isinstance(scene, dict)), {})

    if first_variant:
        payload.setdefault("variant", first_variant)
    if first_scene:
        payload.setdefault("scene", first_scene)
        payload.setdefault("frames", first_scene.get("frames") or [])
        scenes_with_alias = dict(scenes)
        scenes_with_alias.setdefault("0", first_scene)
        payload["scenes"] = scenes_with_alias

    result = None
    if first_variant:
        result = first_variant.get("result")
    if result is None and first_scene:
        result = first_scene.get("result")
    if result is None:
        result = payload.get("verifier_result", payload.get("expected_result"))
    payload.setdefault("result", result)
    return payload


def _strip_fenced_text(content: str) -> str:
    text = (content or "").strip()
    fenced = re.search(r"```(?:html|javascript|js)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


def _escape_html(value: Any) -> str:
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _json_script_payload(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _safe_script_body(value: str) -> str:
    return (value or "").replace("</script", "<\\/script")


def _creative_stage_shell_html(artifact: BuildArtifact, assets: dict[str, str]) -> str:
    payload = _json_script_payload(_runtime_artifact_payload(artifact))
    title = _escape_html(artifact.problem_title)
    stage_css = assets.get("css", "")
    stage_template = assets.get("template", "")
    stage_script = _safe_script_body(assets.get("script", ""))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Creative Shell</title>
<style>
:root {{
  --bg:#f6f7fb; --panel:#fff; --ink:#172033; --muted:#657085; --line:#d7deea;
  --blue:#2563eb; --green:#16a34a; --amber:#d97706; --red:#dc2626; --soft:#f8fafc;
  --shadow:0 1px 2px rgba(15,23,42,.08);
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif; }}
button,input {{ font:inherit; }}
button {{ cursor:pointer; }}
.creative-shell {{ min-height:100vh; display:grid; grid-template-rows:auto 1fr auto; }}
.topbar {{ background:#fff; border-bottom:1px solid var(--line); padding:10px 16px; display:grid; grid-template-columns:minmax(240px,1fr) minmax(260px,420px) auto; gap:12px; align-items:center; }}
h1 {{ margin:0; font-size:18px; letter-spacing:0; }}
.subtitle {{ margin:5px 0 0; color:var(--muted); font-size:13px; }}
.top-summary {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; min-width:0; }}
.summary-card {{ border:1px solid var(--line); border-radius:7px; background:#fbfdff; padding:7px 9px; min-width:0; }}
.summary-card span {{ display:block; color:var(--muted); font-size:11px; }}
.summary-card strong {{ display:block; margin-top:2px; font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.badges {{ display:flex; flex-wrap:wrap; justify-content:flex-end; gap:6px; }}
.badge,.chip {{ border:1px solid var(--line); border-radius:999px; padding:3px 8px; background:#fff; color:var(--muted); font-size:11px; }}
.badge.ok,.chip.ok {{ color:#166534; border-color:#bbf7d0; background:#f0fdf4; }}
.badge.warn,.chip.warn {{ color:#92400e; border-color:#fde68a; background:#fffbeb; }}
.workspace {{ display:grid; grid-template-columns:minmax(220px,270px) minmax(620px,1fr) minmax(300px,360px); gap:10px; padding:10px; align-items:start; }}
.col {{ display:grid; gap:10px; min-width:0; align-content:start; }}
.task-col {{ max-height:calc(100vh - 88px); overflow:auto; padding-right:2px; }}
.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); min-width:0; }}
.section {{ padding:10px; }}
.section h2 {{ margin:0 0 8px; color:#374151; font-size:12px; letter-spacing:.04em; text-transform:uppercase; }}
.hero {{ display:grid; grid-template-rows:auto minmax(470px,clamp(470px,64vh,720px)) auto auto; min-height:0; }}
.step-head {{ padding:10px 12px; border-bottom:1px solid var(--line); display:grid; grid-template-columns:1fr auto; gap:10px; }}
.step-head h2 {{ margin:0; font-size:16px; }}
.step-head p {{ margin:4px 0 0; color:var(--muted); font-size:12px; line-height:1.35; max-height:40px; overflow:auto; }}
.pill {{ border-radius:999px; border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8; padding:5px 10px; height:fit-content; font-size:12px; text-transform:uppercase; }}
#stage {{ position:relative; overflow:hidden; min-height:0; height:clamp(470px,64vh,720px); padding:12px; background:linear-gradient(180deg,#ffffff,#f8fafc); }}
#creative-stage-host {{ position:relative; width:100%; height:100%; min-height:430px; overflow:auto; border:1px solid #e2e8f0; border-radius:8px; background:#fff; }}
#creative-stage-host [data-layout-role="label"],#creative-stage-host .label,#creative-stage-host .edge-label,#creative-stage-host .value-label,#creative-stage-host .pointer-label,#creative-stage-host .caption {{ overflow-wrap:anywhere; word-break:break-word; }}
#creative-stage-host svg text {{ paint-order:stroke; stroke:#fff; stroke-width:3px; stroke-linejoin:round; }}
.stage-error {{ margin:12px; border:1px solid #fecaca; border-radius:7px; background:#fef2f2; color:#991b1b; padding:10px; font-size:12px; white-space:pre-wrap; }}
.fallback-stage {{ min-height:100%; display:grid; gap:12px; align-content:center; padding:18px; }}
.fallback-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:8px; }}
.fallback-tile {{ border:1px solid #dbeafe; border-radius:7px; background:#eff6ff; padding:10px; min-height:58px; overflow-wrap:anywhere; }}
.fallback-tile.hot {{ border-color:#f59e0b; background:#fffbeb; }}
.controls {{ border-top:1px solid var(--line); padding:8px 10px; display:grid; grid-template-columns:auto auto auto 1fr auto; gap:8px; align-items:center; }}
.controls button {{ border:1px solid var(--line); background:#fff; border-radius:6px; padding:6px 10px; }}
.controls .primary {{ border-color:var(--blue); background:var(--blue); color:#fff; }}
.range {{ width:100%; accent-color:var(--blue); }}
.counter {{ color:var(--muted); font-size:13px; min-width:86px; text-align:right; }}
.timeline {{ border-top:1px solid var(--line); display:flex; gap:6px; padding:8px 10px; overflow-x:auto; }}
.tick {{ position:relative; width:108px; min-width:108px; min-height:42px; border:1px solid var(--line); border-radius:7px; background:#fff; color:var(--muted); font-size:11px; text-align:left; padding:6px 7px 6px 12px; display:grid; gap:2px; align-content:center; }}
.tick::before {{ content:''; position:absolute; left:4px; top:8px; bottom:8px; width:3px; border-radius:999px; background:#cbd5e1; }}
.tick.keyframe::before {{ background:var(--amber); }}
.tick.active {{ background:#eff6ff; border-color:var(--blue); color:#1d4ed8; }}
.tick.active::before {{ background:var(--blue); }}
.tick-label,.tick-op {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; line-height:1.2; }}
.tick-label {{ color:#172033; font-size:12px; font-weight:700; }}
.tick-op {{ color:var(--muted); font-size:11px; }}
.tabs,.variant-compare {{ display:grid; gap:6px; max-height:160px; overflow:auto; padding-right:2px; }}
.tab,.variant-card {{ border:1px solid var(--line); border-radius:7px; background:#fff; padding:8px; text-align:left; }}
.tab.active,.variant-card.active {{ border-color:var(--blue); box-shadow:inset 3px 0 0 var(--blue); }}
.tab strong,.variant-card strong {{ display:block; font-size:13px; }}
.tab span,.variant-card span {{ display:block; margin-top:4px; color:var(--muted); font-size:12px; line-height:1.25; }}
.code {{ display:grid; gap:0; max-height:300px; overflow:auto; background:#101827; color:#dbeafe; border-radius:7px; }}
.line {{ display:grid; grid-template-columns:42px 1fr; gap:10px; padding:1px 10px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; line-height:1.55; }}
.lineno {{ color:#7f8ea3; text-align:right; }}
.line.active {{ background:#1d4ed8; color:#fff; }}
.pseudo {{ margin-top:8px; border:1px solid var(--line); border-radius:7px; background:#fbfdff; padding:8px; display:grid; gap:5px; }}
.pseudo-row {{ display:grid; grid-template-columns:24px 1fr; gap:7px; font-size:12px; color:#334155; }}
.pseudo-row.active {{ color:#1d4ed8; font-weight:700; }}
.state-row,.evidence-line,.change-row {{ display:grid; grid-template-columns:minmax(80px,120px) minmax(0,1fr); gap:8px; align-items:start; padding:5px 0; border-bottom:1px solid #eef2f7; font-size:12px; }}
.state-row:last-child,.evidence-line:last-child,.change-row:last-child {{ border-bottom:0; }}
code,pre {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
pre {{ margin:0; white-space:pre-wrap; overflow:auto; font-size:12px; line-height:1.4; }}
.jsonbox {{ max-height:150px; border:1px solid var(--line); border-radius:6px; padding:8px; background:#fbfdff; }}
.teaching {{ display:grid; gap:8px; }}
.teach-row,.evidence-block,.interaction {{ border:1px solid #e5e7eb; border-radius:7px; background:#fbfdff; padding:8px; font-size:12px; }}
.teach-row strong,.evidence-block strong,.interaction strong {{ display:block; margin-bottom:5px; color:#374151; }}
.teach-row p,.evidence-block p {{ margin:0; color:#4b5563; line-height:1.45; }}
.evidence-list {{ margin:4px 0 0 18px; padding:0; color:#4b5563; font-size:12px; }}
.interaction button {{ margin:7px 6px 0 0; border:1px solid #bfdbfe; border-radius:6px; background:#eff6ff; color:#1d4ed8; padding:6px 9px; }}
.interaction input {{ width:100%; margin-top:8px; padding:7px 8px; border:1px solid var(--line); border-radius:6px; }}
.feedback {{ margin-top:8px; padding:7px 8px; border-radius:6px; background:#f8fafc; color:#475569; }}
.feedback.correct {{ color:#166534; background:#f0fdf4; border:1px solid #bbf7d0; }}
.feedback.wrong {{ color:#991b1b; background:#fef2f2; border:1px solid #fecaca; }}
.feedback-source {{ display:block; margin-top:4px; color:#64748b; font-size:11px; }}
.debug-drawer {{ border-top:1px solid var(--line); background:#fff; padding:8px 12px; }}
.debug-grid {{ margin-top:8px; display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:10px; }}
@media (max-width:1180px) {{
  .workspace {{ grid-template-columns:1fr; }}
  .task-col {{ max-height:none; overflow:visible; }}
  .topbar {{ grid-template-columns:1fr; }}
  .badges {{ justify-content:flex-start; }}
}}
</style>
<style id="creative-stage-style">
{stage_css}
</style>
</head>
<body>
<div id="app" class="creative-shell" data-render-target="creative_stage_shell">
  <header class="topbar">
    <div><h1 id="title"></h1><p id="subtitle" class="subtitle"></p></div>
    <div class="top-summary" aria-label="当前任务摘要">
      <div class="summary-card"><span>验证输出</span><strong id="top-result"></strong></div>
      <div class="summary-card"><span>当前解法</span><strong id="top-solution"></strong></div>
    </div>
    <div id="badges" class="badges"></div>
  </header>
  <main class="workspace">
    <aside class="col task-col">
      <section id="code-panel" class="panel section"><h2>代码 / 伪代码</h2><div id="code" class="code"></div><div id="pseudocode" class="pseudo"></div></section>
      <section class="panel section"><h2>解法</h2><div id="tabs" class="tabs"></div></section>
      <section class="panel section"><h2>解法对比</h2><div id="variant-compare" class="variant-compare"></div></section>
    </aside>
    <section class="col">
      <div class="panel hero">
        <div class="step-head"><div><h2 id="step-title"></h2><p id="step-desc"></p></div><div id="op" class="pill"></div></div>
        <div id="stage" data-creative-stage="true"><div id="creative-stage-host"></div></div>
        <div class="controls">
          <button id="prev" type="button">上一步</button>
          <button id="play" class="primary" type="button">播放</button>
          <button id="next" type="button">下一步</button>
          <input id="range" class="range" type="range" min="0" value="0">
          <div id="counter" class="counter"></div>
        </div>
        <div id="timeline" class="timeline" aria-label="语义时间线"></div>
      </div>
    </section>
    <aside class="col teaching-col">
      <section id="teaching-panel" class="panel section"><h2>讲解</h2><div id="teaching"></div></section>
      <section id="step-evidence-panel" class="panel section"><h2>本步证据</h2><div id="step-evidence"></div></section>
      <section class="panel section"><h2>交互</h2><div id="interaction"></div></section>
      <section class="panel section"><h2>当前状态</h2><div id="state"></div></section>
    </aside>
  </main>
  <details id="debug-drawer" class="debug-drawer">
    <summary><span>Debug Drawer</span> <small>原始校验、状态和 artifact 证据</small></summary>
    <div class="debug-grid">
      <section class="panel section"><h2>raw validation report</h2><div id="debug-evidence"></div><pre id="debug-validation-json" class="jsonbox"></pre></section>
      <section class="panel section"><h2>raw state JSON</h2><div id="debug-state"></div></section>
      <section class="panel section"><h2>artifact JSON</h2><pre id="debug-artifact" class="jsonbox"></pre></section>
    </div>
  </details>
</div>
<script type="application/json" id="algolab-artifact" data-source="verified-artifact">{payload}</script>
<template id="creative-stage-template">
{stage_template}
</template>
<script id="creative-stage-user-script">
{stage_script}
</script>
<script>
(function() {{
  'use strict';
  const ARTIFACT = JSON.parse(document.getElementById('algolab-artifact').textContent || '{{}}');
  let variantIndex = 0;
  let stepIndex = 0;
  let timer = null;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
  const pretty = value => JSON.stringify(value, null, 2);
  const compact = value => {{
    try {{
      const text = JSON.stringify(value);
      return text && text.length > 140 ? text.slice(0, 137) + '...' : text;
    }} catch (_) {{
      return String(value ?? '');
    }}
  }};
  const variants = () => Array.isArray(ARTIFACT.variants) ? ARTIFACT.variants : [];
  const variant = () => variants()[variantIndex] || {{}};
  const scene = () => {{
    if (ARTIFACT.scene && Array.isArray(ARTIFACT.scene.frames)) return ARTIFACT.scene;
    const scenes = ARTIFACT.scenes || {{}};
    const byId = scenes[String(variant().id || '')];
    if (byId && Array.isArray(byId.frames)) return byId;
    return Object.values(scenes).find(item => item && Array.isArray(item.frames)) || {{}};
  }};
  const frames = () => Array.isArray(ARTIFACT.frames) && ARTIFACT.frames.length ? ARTIFACT.frames : (scene().frames || []);
  const frame = () => frames()[stepIndex] || {{}};
  const verifiedResult = () => variant().result ?? scene().result ?? ARTIFACT.result ?? ARTIFACT.verifier_result ?? ARTIFACT.expected_result;
  const inputData = () => ARTIFACT.input_data ?? ARTIFACT.input ?? scene().input_data;
  const textOr = (value, fallback='') => String(value ?? '').trim() || fallback;

  function boot() {{
    $('title').textContent = ARTIFACT.problem_title || '算法可视化';
    $('subtitle').textContent = 'Creative Shell：主视图由 LLM stage 绘制，代码、讲解、证据和交互来自验证 artifact。';
    renderBadges();
    renderVariants();
    selectVariant(0);
    $('prev').onclick = () => go(stepIndex - 1);
    $('next').onclick = () => go(stepIndex + 1);
    $('play').onclick = play;
    $('range').oninput = event => go(Number(event.target.value));
  }}
  function renderBadges() {{
    const gate = ARTIFACT.validation && ARTIFACT.validation.release_gate || {{}};
    const rows = [
      ['artifact', gate.artifact_ready],
      ['trace', gate.trace_ready],
      ['process', gate.process_ready],
      ['visual', gate.visual_ready],
      ['creative_stage', true],
    ];
    $('badges').innerHTML = rows.map(([label, ok]) => `<span class="badge ${{ok ? 'ok' : 'warn'}}">${{esc(label)}}：${{ok ? 'PASS' : 'CHECK'}}</span>`).join('');
  }}
  function renderVariants() {{
    const html = variants().map((item, index) => {{
      const active = index === variantIndex ? 'active' : '';
      return `<button type="button" class="tab ${{active}}" data-variant="${{index}}"><strong>${{esc(item.name || item.id || `解法 ${{index + 1}}`)}}</strong><span>${{esc(item.complexity || item.strategy || '')}}</span></button>`;
    }}).join('');
    $('tabs').innerHTML = html || '<p style="color:var(--muted);margin:0;font-size:12px;">无解法列表。</p>';
    $('tabs').querySelectorAll('[data-variant]').forEach(btn => btn.onclick = () => selectVariant(Number(btn.dataset.variant)));
    $('variant-compare').innerHTML = variants().map((item, index) => `<div class="variant-card ${{index === variantIndex ? 'active' : ''}}"><strong>${{esc(item.name || item.id || `解法 ${{index + 1}}`)}}</strong><span>result=${{esc(compact(item.result))}}</span><span>${{esc(item.complexity || '')}}</span></div>`).join('');
  }}
  function selectVariant(index) {{
    variantIndex = Math.max(0, Math.min(index, variants().length - 1));
    stepIndex = 0;
    stop();
    $('range').max = Math.max(0, frames().length - 1);
    renderVariants();
    renderEvidenceSummary();
    renderDebug();
    render();
  }}
  function go(index) {{
    const max = Math.max(0, frames().length - 1);
    stepIndex = Math.max(0, Math.min(Number(index) || 0, max));
    render();
  }}
  function render() {{
    const f = frame();
    $('step-title').textContent = frameTitle(f);
    $('step-desc').textContent = frameDescription(f);
    $('op').textContent = f.operation || '';
    $('top-result').textContent = compact(verifiedResult());
    $('top-solution').textContent = variant().name || variant().id || scene().algorithm || '';
    $('counter').textContent = frames().length ? `${{stepIndex + 1}} / ${{frames().length}}` : '0 / 0';
    $('range').value = stepIndex;
    renderTimeline();
    renderCode();
    renderPseudocode();
    renderTeaching(f);
    renderStepEvidence(f);
    renderInteraction(f.interaction || null);
    renderState(f.state || {{}});
    renderDebugState(f.state || {{}});
    renderStage(f);
  }}
  function frameTitle(f) {{
    return textOr(f.title, `第 ${{stepIndex + 1}} 步`);
  }}
  function frameDescription(f) {{
    return textOr(f.description, textOr(f.evidence && f.evidence.reason, '根据当前 trace 状态推进算法步骤。'));
  }}
  function renderTimeline() {{
    $('timeline').innerHTML = frames().map((f, index) => {{
      const meta = f.evidence && f.evidence.timeline || {{}};
      const label = textOr(meta.phase, textOr(meta.keyframe_label, `${{index + 1}} · ${{frameTitle(f)}}`));
      const op = textOr(meta.operation, f.operation || 'step');
      return `<button type="button" class="tick ${{index === stepIndex ? 'active' : ''}} ${{meta.keyframe ? 'keyframe' : ''}}" data-step="${{index}}" title="${{esc(label + ' · ' + op)}}"><span class="tick-label">${{esc(label)}}</span><span class="tick-op">${{esc(op)}}</span></button>`;
    }}).join('');
    $('timeline').querySelectorAll('[data-step]').forEach(btn => btn.onclick = () => go(Number(btn.dataset.step)));
  }}
  function renderCode() {{
    const code = String(variant().code || '');
    const active = Number(frame().code_line || (frame().evidence && frame().evidence.code_line) || 1);
    const lines = code ? code.split('\\n') : [];
    $('code').innerHTML = lines.length
      ? lines.map((line, i) => `<div class="line ${{i + 1 === active ? 'active' : ''}}"><span class="lineno">${{i + 1}}</span><span>${{esc(line) || ' '}}</span></div>`).join('')
      : '<div class="line"><span class="lineno">-</span><span>当前 artifact 没有代码文本，见伪代码。</span></div>';
  }}
  function renderPseudocode() {{
    const rows = Array.isArray(scene().pseudocode) ? scene().pseudocode : [];
    const active = Number(frame().code_line || 1);
    $('pseudocode').innerHTML = rows.length
      ? rows.map((line, i) => `<div class="pseudo-row ${{i + 1 === active ? 'active' : ''}}"><span>${{i + 1}}</span><span>${{esc(line)}}</span></div>`).join('')
      : '<div class="pseudo-row"><span>-</span><span>无伪代码。</span></div>';
  }}
  function renderTeaching(f) {{
    const teaching = f.teaching || {{}};
    const rows = [
      ['当前步骤', teaching.what || frameTitle(f)],
      ['为什么', teaching.why || frameDescription(f)],
      ['公式 / 规则', teaching.formula || ''],
      ['不变量', teaching.invariant || ''],
      ['常见错误', teaching.common_mistake || ''],
      ['提示', teaching.hint || ''],
    ].filter(([, value]) => String(value || '').trim());
    const changes = eventChangeRows(f);
    $('teaching').innerHTML = `<div class="teaching">${{rows.map(([label, value]) => `<div class="teach-row"><strong>${{esc(label)}}</strong><p>${{esc(value)}}</p></div>`).join('')}}${{changes.length ? `<div class="teach-row"><strong>状态变化摘要</strong>${{changes.slice(0, 5).map(renderChangeRow).join('')}}</div>` : ''}}</div>`;
  }}
  function renderStepEvidence(f) {{
    const evidence = f.evidence || {{}};
    const marks = Array.isArray(f.marks) ? f.marks : [];
    const targets = evidence.targets || marks.filter(m => m.role !== 'dependency').map(m => m.target);
    const deps = evidence.deps || marks.filter(m => m.role === 'dependency').map(m => m.target);
    const rows = [
      ['operation', evidence.operation || f.operation || ''],
      ['code_line', evidence.code_line || f.code_line || ''],
      ['targets', (targets || []).join(', ') || '无'],
      ['deps', (deps || []).join(', ') || '无'],
      ['role', evidence.role || ''],
      ['reason', evidence.reason || ''],
    ].filter(([, value]) => String(value ?? '').trim());
    let html = `<div class="evidence-block"><strong>本步语义</strong>${{rows.map(([label, value]) => evidenceLine(label, value)).join('')}}</div>`;
    const process = evidence.process || {{}};
    if (process.summary) html += `<div class="evidence-block"><strong>过程校验证据</strong>${{evidenceLine('status', process.status || '')}}${{evidenceLine('kind', process.kind || '')}}${{evidenceLine('summary', process.summary || '')}}</div>`;
    if (evidence.value !== undefined || evidence.before !== undefined || evidence.after !== undefined) {{
      html += `<div class="evidence-block"><strong>事件值</strong>${{evidence.value !== undefined ? evidenceLine('value', compact(evidence.value)) : ''}}${{evidence.before !== undefined ? evidenceLine('before', compact(evidence.before)) : ''}}${{evidence.after !== undefined ? evidenceLine('after', compact(evidence.after)) : ''}}</div>`;
    }}
    const changes = eventChangeRows(f);
    html += `<div class="evidence-block"><strong>状态变化摘要</strong>${{changes.length ? changes.slice(0, 6).map(renderChangeRow).join('') : '<p>本步没有可观测状态变化。</p>'}}</div>`;
    $('step-evidence').innerHTML = html;
  }}
  function evidenceLine(label, value) {{
    if (value === undefined || value === null || value === '') return '';
    return `<div class="evidence-line"><span>${{esc(label)}}</span><code>${{esc(value)}}</code></div>`;
  }}
  function eventChangeRows(f) {{
    const evidence = f.evidence || {{}};
    if (Array.isArray(evidence.changes) && evidence.changes.length) return evidence.changes.map(normalizeChangeRow);
    const fields = [];
    if (evidence.before !== undefined) fields.push(['before', evidence.before]);
    if (evidence.after !== undefined) fields.push(['after', evidence.after]);
    if (evidence.value !== undefined) fields.push(['value', evidence.value]);
    if (fields.length) {{
      const targets = Array.isArray(evidence.targets) && evidence.targets.length ? evidence.targets : ['state'];
      return targets.map((target, index) => normalizeChangeRow({{
        target,
        before: pickIndexedValue(evidence.before, index, targets.length),
        after: pickIndexedValue(evidence.after, index, targets.length),
        value: pickIndexedValue(evidence.value, index, targets.length),
        source:'event',
      }}));
    }}
    const previous = stepIndex > 0 ? frames()[stepIndex - 1] : null;
    return stateDiff(previous && previous.state || {{}}, f.state || {{}}).map(diff => normalizeChangeRow({{
      target:diff.key, before:diff.before, after:diff.after, kind:diff.kind, source:'state_diff',
    }}));
  }}
  function normalizeChangeRow(row) {{
    return {{ target:String(row && row.target !== undefined ? row.target : 'state'), before:row && row.before, after:row && row.after, value:row && row.value, kind:row && row.kind || '', source:row && row.source || '' }};
  }}
  function pickIndexedValue(value, index, total) {{
    if (Array.isArray(value) && total > 1 && index < value.length) return value[index];
    return value;
  }}
  function renderChangeRow(row) {{
    const parts = [];
    if (row.before !== undefined || row.after !== undefined) parts.push(`${{compact(row.before)}} -> ${{compact(row.after)}}`);
    if (row.value !== undefined) parts.push(`value=${{compact(row.value)}}`);
    const suffix = [row.kind, row.source === 'state_diff' ? 'state diff' : row.source].filter(Boolean).join(' · ');
    return `<div class="change-row"><span>${{esc(row.target)}}${{suffix ? ` · ${{esc(suffix)}}` : ''}}</span><code>${{esc(parts.join(' · ') || '已变化')}}</code></div>`;
  }}
  function stateDiff(prev, next) {{
    const keys = Array.from(new Set([...Object.keys(prev || {{}}), ...Object.keys(next || {{}})])).sort();
    return keys.map(key => {{
      const before = prev ? prev[key] : undefined;
      const after = next ? next[key] : undefined;
      if (stableJson(before) === stableJson(after)) return null;
      return {{ key, before, after, kind: before === undefined ? '新增' : after === undefined ? '删除' : '更新' }};
    }}).filter(Boolean);
  }}
  function stableJson(value) {{
    try {{ return JSON.stringify(value, Object.keys(value || {{}}).sort()); }} catch (_) {{ return String(value); }}
  }}
  function renderInteraction(interaction) {{
    if (!interaction) {{
      $('interaction').innerHTML = '<p style="color:var(--muted);margin:0;font-size:12px;">当前步骤没有交互题。</p>';
      return;
    }}
    const options = Array.isArray(interaction.options) ? interaction.options : [];
    const choiceHtml = interaction.type === 'choice' ? options.map(option => `<button type="button" data-option="${{esc(option)}}">${{esc(option)}}</button>`).join('') : '';
    const inputHtml = interaction.type === 'input' ? '<input id="free-answer" placeholder="输入答案"><button type="button" data-input-check="true">检查</button>' : '';
    const judgeHtml = interaction.type === 'judge' ? '<button type="button" data-judge="true">正确</button><button type="button" data-judge="false">错误</button>' : '';
    $('interaction').innerHTML = `<div class="interaction" data-interaction-type="${{esc(interaction.type || '')}}"><strong>${{esc(interaction.prompt || '思考题')}}</strong>${{choiceHtml}}${{inputHtml}}${{judgeHtml}}<div id="feedback" class="feedback"></div></div>`;
    $('interaction').querySelectorAll('[data-option]').forEach(btn => btn.onclick = () => checkAnswer(btn.dataset.option));
    const inputBtn = $('interaction').querySelector('[data-input-check]');
    if (inputBtn) inputBtn.onclick = () => checkAnswer(($('free-answer') && $('free-answer').value || '').trim());
    $('interaction').querySelectorAll('[data-judge]').forEach(btn => btn.onclick = () => checkAnswer(btn.dataset.judge === 'true'));
  }}
  function checkAnswer(value) {{
    const interaction = frame().interaction || {{}};
    const answer = interaction.answer;
    const ok = Array.isArray(answer) ? answer.map(String).includes(String(value)) : String(answer) === String(value);
    const explanations = interaction.option_explanations || {{}};
    const source = Object.prototype.hasOwnProperty.call(explanations, String(value)) ? 'interaction.option_explanations' : (ok ? 'interaction.explanation' : 'interaction.wrong_explanation / teaching');
    const msg = explanations[String(value)] || (ok ? interaction.explanation : interaction.wrong_explanation) || (frame().teaching && frame().teaching.common_mistake) || '';
    const node = $('feedback');
    node.className = `feedback ${{ok ? 'correct' : 'wrong'}}`;
    node.dataset.correct = ok ? 'true' : 'false';
    node.innerHTML = `${{ok ? '正确。' : '错误选项解释：'}}${{esc(msg)}}<span class="feedback-source">来源：${{esc(source)}}，只读当前 SceneGraph interaction / teaching。</span>`;
  }}
  function renderState(state) {{
    const entries = Object.entries(state || {{}});
    $('state').innerHTML = entries.length ? entries.map(([key, value]) => `<div class="state-row"><strong>${{esc(key)}}</strong><code>${{esc(compact(value))}}</code></div>`).join('') : '<p style="color:var(--muted);margin:0;font-size:12px;">当前步骤没有状态快照。</p>';
  }}
  function renderEvidenceSummary() {{
    const gate = ARTIFACT.validation && ARTIFACT.validation.release_gate || {{}};
    const rows = [
      ['artifact_ready', gate.artifact_ready],
      ['trace_ready', gate.trace_ready],
      ['process_ready', gate.process_ready],
      ['visual_ready', gate.visual_ready],
      ['release_ready', gate.release_ready],
    ];
    const node = $('debug-evidence');
    if (node) node.innerHTML = `<div class="evidence-block"><strong>Release gate</strong>${{rows.map(([k, v]) => `<span class="chip ${{v ? 'ok' : 'warn'}}">${{esc(k)}}：${{v ? 'PASS' : 'NO'}}</span>`).join(' ')}}</div>`;
  }}
  function renderDebug() {{
    $('debug-validation-json').textContent = pretty(ARTIFACT.validation || {{}});
    $('debug-artifact').textContent = pretty(ARTIFACT);
  }}
  function renderDebugState(state) {{
    const node = $('debug-state');
    if (node) node.innerHTML = `<div class="state-row"><strong>frame ${{stepIndex + 1}}</strong><pre>${{esc(pretty(state || {{}}))}}</pre></div>`;
  }}
  function renderStage(f) {{
    const host = $('creative-stage-host');
    host.innerHTML = '';
    host.dataset.frameIndex = String(stepIndex);
    const template = $('creative-stage-template');
    const ctx = Object.freeze({{
      host,
      artifact: ARTIFACT,
      variant: variant(),
      scene: scene(),
      frame: f,
      frames: frames(),
      frameIndex: stepIndex,
      input: inputData(),
      result: verifiedResult(),
      state: f.state || {{}},
      evidence: f.evidence || {{}},
      esc,
      compact,
      template: template ? template.innerHTML : '',
    }});
    try {{
      const renderer = window.renderCreativeStage || (window.creativeStage && window.creativeStage.render);
      if (typeof renderer !== 'function') throw new Error('renderCreativeStage is not defined');
      const rendered = renderer(ctx);
      if (rendered instanceof Node) {{
        host.appendChild(rendered);
      }} else if (typeof rendered === 'string' && !host.childElementCount && !host.textContent.trim()) {{
        host.innerHTML = rendered;
      }}
      if (!host.childElementCount && !host.textContent.trim()) renderDefaultStage(host, f);
      runCreativeStageLayoutGuard(host);
      host.dataset.stageRendered = 'true';
    }} catch (error) {{
      host.innerHTML = `<div class="stage-error">Creative stage error: ${{esc(error && error.message || error)}}</div>`;
      renderDefaultStage(host, f, true);
      runCreativeStageLayoutGuard(host);
      host.dataset.stageRendered = 'fallback';
    }}
  }}
  function runCreativeStageLayoutGuard(host) {{
    try {{
      const labelSelector = 'svg text,[data-layout-role="label"],[data-visual*="label"],.label,.edge-label,.value-label,.pointer-label,.caption,.axis-label';
      const labels = Array.from(host.querySelectorAll(labelSelector)).filter(node => {{
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.height > 2;
      }});
      const hostRect = host.getBoundingClientRect();
      labels.forEach(node => clampLabelIntoHost(node, hostRect));
      for (let pass = 0; pass < 3; pass += 1) {{
        let moved = false;
        for (let i = 0; i < labels.length; i += 1) {{
          for (let j = i + 1; j < labels.length; j += 1) {{
            const a = labels[i].getBoundingClientRect();
            const b = labels[j].getBoundingClientRect();
            const left = Math.max(a.left, b.left);
            const right = Math.min(a.right, b.right);
            const top = Math.max(a.top, b.top);
            const bottom = Math.min(a.bottom, b.bottom);
            const area = Math.max(0, right - left) * Math.max(0, bottom - top);
            const minArea = Math.max(1, Math.min(a.width * a.height, b.width * b.height));
            if (area / minArea > 0.12) {{
              shiftLabel(labels[j], 0, Math.min(28, Math.max(10, bottom - top + 5)));
              clampLabelIntoHost(labels[j], hostRect);
              moved = true;
            }}
          }}
        }}
        if (!moved) break;
      }}
    }} catch (_) {{}}
  }}
  function clampLabelIntoHost(node, hostRect) {{
    const rect = node.getBoundingClientRect();
    let dx = 0;
    let dy = 0;
    if (rect.left < hostRect.left + 4) dx = hostRect.left + 4 - rect.left;
    if (rect.right > hostRect.right - 4) dx = hostRect.right - 4 - rect.right;
    if (rect.top < hostRect.top + 4) dy = hostRect.top + 4 - rect.top;
    if (rect.bottom > hostRect.bottom - 4) dy = hostRect.bottom - 4 - rect.bottom;
    if (dx || dy) shiftLabel(node, dx, dy);
  }}
  function shiftLabel(node, dx, dy) {{
    const tag = String(node.tagName || '').toLowerCase();
    if (tag === 'text' && node.ownerSVGElement) {{
      const x = Number(node.getAttribute('x') || 0);
      const y = Number(node.getAttribute('y') || 0);
      if (Number.isFinite(x)) node.setAttribute('x', String(x + dx));
      if (Number.isFinite(y)) node.setAttribute('y', String(y + dy));
      return;
    }}
    const prevX = Number(node.dataset.layoutGuardX || 0);
    const prevY = Number(node.dataset.layoutGuardY || 0);
    const nextX = prevX + dx;
    const nextY = prevY + dy;
    node.dataset.layoutGuardX = String(nextX);
    node.dataset.layoutGuardY = String(nextY);
    if (getComputedStyle(node).position === 'static') node.style.position = 'relative';
    node.style.zIndex = node.style.zIndex || '3';
    node.style.transform = `translate(${{nextX}}px, ${{nextY}}px)`;
  }}
  function renderDefaultStage(host, f, append=false) {{
    const state = f.state || {{}};
    const evidence = f.evidence || {{}};
    const hot = new Set([...(evidence.targets || []), ...(evidence.deps || [])].map(String));
    const entries = Object.entries(state).slice(0, 18);
    const html = `<div class="fallback-stage"><div><h3>${{esc(frameTitle(f))}}</h3><p>${{esc(frameDescription(f))}}</p></div><div class="fallback-grid">${{entries.map(([key, value]) => `<div class="fallback-tile ${{hot.has(key) ? 'hot' : ''}}"><strong>${{esc(key)}}</strong><br><code>${{esc(compact(value))}}</code></div>`).join('')}}</div><div class="fallback-tile hot"><strong>验证答案</strong><br><code>${{esc(compact(verifiedResult()))}}</code></div></div>`;
    if (append) host.insertAdjacentHTML('beforeend', html);
    else host.innerHTML = html;
  }}
  function play() {{
    if (timer) return stop();
    $('play').textContent = '暂停';
    timer = setInterval(() => {{
      if (stepIndex >= frames().length - 1) return stop();
      go(stepIndex + 1);
    }}, 850);
  }}
  function stop() {{
    if (timer) clearInterval(timer);
    timer = null;
    $('play').textContent = '播放';
  }}
  window.algolabCreativeShell = {{ go, render, frames, frame, artifact: ARTIFACT }};
  boot();
}})();
</script>
</body>
</html>"""
