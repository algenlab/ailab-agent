"""Creative storyboard renderer.

This renderer is intentionally separate from the conservative renderer in
``export.py``. It consumes the same verified BuildArtifact, then presents the
scene through reusable visual metaphors and selectable themes. Correctness
still comes from solve/trace/verifier/process checks; this layer only changes
how the already-validated state is staged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from algolab.schemas.validation import BuildArtifact


def save_creative_html(artifact: BuildArtifact, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_creative_html(artifact), encoding="utf-8")
    output.with_suffix(".json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return output


def render_creative_html(artifact: BuildArtifact) -> str:
    lab_json = artifact.model_dump_json().replace("</", "<\\/")
    title = _escape(artifact.problem_title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 创意演示</title>
<style>
:root {{
  --bg0:#10131f; --bg1:#182329; --panel:rgba(255,255,255,.9); --panel2:rgba(255,255,255,.72);
  --ink:#f8fafc; --ink2:#1f2937; --muted:#94a3b8; --line:rgba(255,255,255,.18);
  --a:#f59e0b; --b:#22c55e; --c:#38bdf8; --d:#f472b6; --bad:#ef4444;
  --stage-shadow:0 24px 80px rgba(0,0,0,.34);
  --radius:8px;
}}
[data-theme="cyber"] {{
  --bg0:#07111f; --bg1:#0b2438; --panel:rgba(7,17,31,.82); --panel2:rgba(15,23,42,.7);
  --ink:#e0f2fe; --ink2:#e0f2fe; --muted:#8ab7cc; --line:rgba(56,189,248,.24);
  --a:#38bdf8; --b:#34d399; --c:#818cf8; --d:#f472b6; --bad:#fb7185;
}}
[data-theme="pixel"] {{
  --bg0:#1f1b2e; --bg1:#27351f; --panel:rgba(255,250,220,.92); --panel2:rgba(255,250,220,.78);
  --ink:#fff7ed; --ink2:#2f2a1d; --muted:#9ca3af; --line:rgba(251,191,36,.32);
  --a:#fbbf24; --b:#84cc16; --c:#60a5fa; --d:#fb7185; --bad:#ef4444;
}}
[data-theme="whiteboard"] {{
  --bg0:#f7fafc; --bg1:#e5edf5; --panel:rgba(255,255,255,.96); --panel2:rgba(255,255,255,.84);
  --ink:#172033; --ink2:#172033; --muted:#64748b; --line:rgba(30,41,59,.16);
  --a:#2563eb; --b:#16a34a; --c:#0891b2; --d:#be185d; --bad:#dc2626;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; min-height:100vh; color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
  background:
    linear-gradient(135deg,var(--bg0),var(--bg1));
}}
button,input,select {{ font:inherit; }}
.app {{ min-height:100vh; display:grid; grid-template-rows:auto 1fr; }}
.top {{
  display:grid; grid-template-columns:minmax(260px,1fr) auto; gap:18px; align-items:center;
  padding:16px 22px; border-bottom:1px solid var(--line); backdrop-filter:blur(14px);
  background:linear-gradient(90deg,rgba(255,255,255,.08),rgba(255,255,255,.03));
}}
h1 {{ margin:0; font-size:22px; letter-spacing:0; }}
.sub {{ margin:5px 0 0; color:var(--muted); font-size:13px; }}
.toolbar {{ display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; }}
.theme-btn,.tool-btn {{
  border:1px solid var(--line); background:rgba(255,255,255,.1); color:var(--ink);
  border-radius:999px; padding:7px 11px; cursor:pointer;
}}
.theme-btn.active,.tool-btn.primary {{ border-color:var(--a); background:var(--a); color:#111827; }}
.layout {{ display:grid; grid-template-columns:minmax(0,1fr) 360px; gap:16px; padding:16px; min-height:0; }}
.stage {{
  position:relative; overflow:hidden; min-height:640px; border:1px solid var(--line); border-radius:var(--radius);
  background:
    linear-gradient(180deg,rgba(255,255,255,.12),rgba(255,255,255,.035)),
    repeating-linear-gradient(90deg,rgba(255,255,255,.035) 0 1px,transparent 1px 72px),
    repeating-linear-gradient(0deg,rgba(255,255,255,.025) 0 1px,transparent 1px 72px);
  box-shadow:var(--stage-shadow);
}}
.stage::before {{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:
    linear-gradient(120deg,transparent 0 18%,rgba(255,255,255,.12) 20%,transparent 22% 100%);
  opacity:.28; transform:translateX(-40%); animation:sweep 9s linear infinite;
}}
@keyframes sweep {{ to {{ transform:translateX(80%); }} }}
.stage-inner {{ position:relative; z-index:1; min-height:640px; padding:22px; display:grid; grid-template-rows:auto 1fr auto; gap:16px; }}
.scene-title {{ display:flex; align-items:start; justify-content:space-between; gap:14px; }}
.scene-title h2 {{ margin:0; font-size:25px; letter-spacing:0; }}
.scene-title p {{ margin:6px 0 0; color:var(--muted); max-width:780px; line-height:1.45; }}
.op-badge {{ border:1px solid var(--line); background:rgba(255,255,255,.12); border-radius:999px; padding:7px 12px; color:var(--ink); white-space:nowrap; }}
.metaphor {{ min-height:420px; display:grid; align-items:center; }}
.side {{ display:grid; gap:14px; align-content:start; min-width:0; }}
.panel {{
  border:1px solid var(--line); border-radius:var(--radius); background:var(--panel); color:var(--ink2);
  box-shadow:0 10px 30px rgba(0,0,0,.16); min-width:0;
}}
.panel h3 {{ margin:0; padding:12px 14px; border-bottom:1px solid rgba(15,23,42,.1); font-size:13px; letter-spacing:.04em; color:#334155; }}
.panel-body {{ padding:12px 14px; }}
pre {{ margin:0; white-space:pre-wrap; overflow:auto; font-size:12px; line-height:1.45; max-height:250px; }}
.controls {{ display:grid; grid-template-columns:auto auto auto 1fr auto; gap:9px; align-items:center; }}
.controls button {{
  border:1px solid var(--line); border-radius:7px; background:rgba(255,255,255,.14); color:var(--ink); padding:8px 12px; cursor:pointer;
}}
.controls .primary {{ background:var(--a); color:#111827; border-color:var(--a); font-weight:700; }}
.range {{ width:100%; accent-color:var(--a); }}
.counter {{ min-width:92px; text-align:right; color:var(--muted); font-size:13px; }}
.timeline {{ display:flex; gap:5px; overflow-x:auto; padding-bottom:2px; }}
.tick {{ width:28px; min-width:28px; height:28px; border:1px solid var(--line); border-radius:6px; background:rgba(255,255,255,.12); color:var(--ink); cursor:pointer; font-size:11px; }}
.tick.active {{ background:var(--a); color:#111827; border-color:var(--a); }}
.bag-world {{ display:grid; grid-template-columns:minmax(240px,1fr) minmax(280px,420px); gap:22px; align-items:center; }}
.items {{ display:flex; flex-wrap:wrap; gap:12px; align-content:center; }}
.item-card {{
  width:86px; min-height:110px; border:1px solid var(--line); border-radius:8px; padding:10px; text-align:center;
  background:linear-gradient(180deg,rgba(255,255,255,.22),rgba(255,255,255,.07));
  box-shadow:0 10px 24px rgba(0,0,0,.16); transform:translateY(0); transition:.28s ease;
}}
.item-card.active {{ border-color:var(--a); box-shadow:0 0 0 3px color-mix(in srgb,var(--a) 26%,transparent),0 18px 40px rgba(0,0,0,.26); transform:translateY(-10px) scale(1.04); }}
.item-icon {{ font-size:30px; line-height:1; margin-bottom:8px; }}
.item-name {{ font-weight:800; }}
.item-meta {{ color:var(--muted); font-size:12px; margin-top:6px; }}
.bag {{ min-height:330px; border:2px solid color-mix(in srgb,var(--a) 62%,white); border-radius:26px 26px 12px 12px; padding:18px; position:relative;
  background:linear-gradient(180deg,color-mix(in srgb,var(--a) 26%,transparent),rgba(255,255,255,.08)); box-shadow:inset 0 0 42px rgba(255,255,255,.12),0 22px 52px rgba(0,0,0,.28); }}
.bag::before {{ content:""; position:absolute; left:24%; right:24%; top:-34px; height:52px; border:4px solid color-mix(in srgb,var(--a) 70%,white); border-bottom:0; border-radius:999px 999px 0 0; }}
.bag.active {{ animation:bagPulse .9s ease-in-out infinite alternate; }}
@keyframes bagPulse {{ from {{ transform:scale(1); }} to {{ transform:scale(1.018); box-shadow:inset 0 0 48px rgba(255,255,255,.2),0 0 42px color-mix(in srgb,var(--a) 48%,transparent); }} }}
.bag-title {{ font-weight:900; font-size:19px; margin-bottom:12px; }}
.capacity-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(24px,1fr)); gap:6px; }}
.slot {{ height:28px; border:1px solid rgba(255,255,255,.2); border-radius:5px; background:rgba(255,255,255,.1); display:grid; place-items:center; font-size:10px; color:var(--muted); }}
.slot.on {{ background:linear-gradient(180deg,var(--b),color-mix(in srgb,var(--b) 50%,black)); color:#052e16; font-weight:800; }}
.meter {{ margin-top:14px; height:12px; background:rgba(255,255,255,.12); border-radius:999px; overflow:hidden; border:1px solid var(--line); }}
.meter > div {{ height:100%; background:linear-gradient(90deg,var(--b),var(--a)); transition:width .25s ease; }}
.graph-world,.geo-world {{ display:grid; place-items:center; }}
.svg-stage {{ width:min(920px,100%); min-height:440px; border:1px solid var(--line); border-radius:8px; background:rgba(255,255,255,.08); }}
.g-edge {{ stroke:rgba(255,255,255,.32); stroke-width:2; }}
.g-edge.hot {{ stroke:var(--a); stroke-width:4; filter:drop-shadow(0 0 8px var(--a)); }}
.g-node circle {{ fill:rgba(255,255,255,.12); stroke:rgba(255,255,255,.55); stroke-width:2; }}
.g-node.hot circle {{ fill:color-mix(in srgb,var(--a) 36%,transparent); stroke:var(--a); stroke-width:4; }}
.g-node.answer circle {{ fill:color-mix(in srgb,var(--b) 36%,transparent); stroke:var(--b); stroke-width:4; }}
.g-node text {{ fill:var(--ink); font-weight:800; }}
.queue-strip {{ margin-top:12px; display:flex; flex-wrap:wrap; gap:8px; justify-content:center; }}
.token {{ border:1px solid var(--line); border-radius:999px; background:rgba(255,255,255,.12); padding:7px 12px; color:var(--ink); font-weight:750; }}
.stack-world {{ display:grid; grid-template-columns:minmax(260px,1fr) minmax(220px,320px); gap:24px; align-items:end; }}
.bars {{ display:flex; align-items:end; gap:8px; min-height:330px; padding:18px; border:1px solid var(--line); border-radius:8px; background:rgba(255,255,255,.08); }}
.bar {{ width:42px; min-height:24px; border-radius:6px 6px 2px 2px; background:linear-gradient(180deg,var(--c),color-mix(in srgb,var(--c) 35%,black)); display:flex; align-items:flex-start; justify-content:center; padding-top:6px; color:#082f49; font-weight:900; transition:.25s ease; }}
.bar.hot {{ background:linear-gradient(180deg,var(--a),#f97316); transform:translateY(-8px); box-shadow:0 0 28px color-mix(in srgb,var(--a) 42%,transparent); }}
.stack-tower {{ min-height:330px; border:1px solid var(--line); border-radius:8px; display:flex; flex-direction:column-reverse; gap:8px; justify-content:flex-start; padding:14px; background:rgba(255,255,255,.08); }}
.stack-block {{ border:1px solid var(--line); border-radius:7px; padding:10px; text-align:center; background:linear-gradient(180deg,rgba(255,255,255,.22),rgba(255,255,255,.08)); font-weight:800; }}
.fallback-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; }}
.tile {{ border:1px solid var(--line); border-radius:8px; padding:12px; min-height:70px; background:rgba(255,255,255,.1); }}
.tile.hot {{ border-color:var(--a); box-shadow:0 0 26px color-mix(in srgb,var(--a) 34%,transparent); }}
.code {{ max-height:300px; background:#101827; color:#dbeafe; border-radius:7px; overflow:auto; }}
.line {{ display:grid; grid-template-columns:42px 1fr; gap:10px; padding:1px 10px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; line-height:1.55; }}
.lineno {{ color:#7f8ea3; text-align:right; }}
.line.active {{ background:#1d4ed8; color:#fff; }}
@media (max-width:1100px) {{
  .layout {{ grid-template-columns:1fr; }}
  .stage,.stage-inner {{ min-height:560px; }}
  .bag-world,.stack-world {{ grid-template-columns:1fr; }}
  .top {{ grid-template-columns:1fr; }}
  .toolbar {{ justify-content:flex-start; }}
}}
</style>
</head>
<body data-theme="fantasy">
<div class="app">
  <header class="top">
    <div><h1 id="title"></h1><p id="subtitle" class="sub"></p></div>
    <div class="toolbar">
      <button class="theme-btn active" data-theme-btn="fantasy">奇幻</button>
      <button class="theme-btn" data-theme-btn="cyber">赛博</button>
      <button class="theme-btn" data-theme-btn="pixel">像素</button>
      <button class="theme-btn" data-theme-btn="whiteboard">白板</button>
    </div>
  </header>
  <main class="layout">
    <section class="stage">
      <div class="stage-inner">
        <div class="scene-title">
          <div><h2 id="step-title"></h2><p id="step-desc"></p></div>
          <div id="op" class="op-badge"></div>
        </div>
        <div id="metaphor" class="metaphor"></div>
        <div>
          <div class="controls">
            <button id="prev">上一步</button>
            <button id="play" class="primary">播放</button>
            <button id="next">下一步</button>
            <input id="range" class="range" type="range" min="0" value="0">
            <div id="counter" class="counter"></div>
          </div>
          <div id="timeline" class="timeline"></div>
        </div>
      </div>
    </section>
    <aside class="side">
      <section class="panel"><h3>解法</h3><div id="variants" class="panel-body"></div></section>
      <section class="panel"><h3>当前状态</h3><div class="panel-body"><pre id="state"></pre></div></section>
      <section class="panel"><h3>输入 / 输出</h3><div class="panel-body"><pre id="io"></pre></div></section>
      <section class="panel"><h3>代码</h3><div class="panel-body"><div id="code" class="code"></div></div></section>
    </aside>
  </main>
</div>
<script>
const ARTIFACT = {lab_json};
let variantIndex = 0;
let stepIndex = 0;
let timer = null;
const $ = id => document.getElementById(id);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const pretty = x => JSON.stringify(x, null, 2);
const variant = () => ARTIFACT.variants[variantIndex];
const scene = () => ARTIFACT.scenes[variant().id];
const frames = () => scene().frames || [];
const frame = () => frames()[stepIndex] || null;

function boot() {{
  $('title').textContent = ARTIFACT.problem_title || '算法可视化实验';
  $('subtitle').textContent = '创意演示模式：正确性来自已校验 trace，视觉由通用 storyboard 渲染。';
  renderVariants();
  bindThemes();
  selectVariant(0);
}}
function bindThemes() {{
  document.querySelectorAll('[data-theme-btn]').forEach(btn => btn.onclick = () => {{
    document.body.dataset.theme = btn.dataset.themeBtn;
    document.querySelectorAll('[data-theme-btn]').forEach(x => x.classList.toggle('active', x === btn));
  }});
}}
function renderVariants() {{
  $('variants').innerHTML = ARTIFACT.variants.map((v,i)=>`<button class="tool-btn ${{i===variantIndex?'primary':''}}" onclick="selectVariant(${{i}})">${{esc(v.name || v.id)}}</button>`).join(' ');
}}
function selectVariant(i) {{
  variantIndex = i; stepIndex = 0; stop();
  renderVariants();
  $('range').max = Math.max(0, frames().length - 1);
  render();
}}
function go(i) {{
  stepIndex = Math.max(0, Math.min(i, frames().length - 1));
  render();
}}
function render() {{
  const f = frame();
  if (!f) return;
  $('step-title').textContent = f.title || `第 ${{stepIndex + 1}} 步`;
  $('step-desc').textContent = f.description || '';
  $('op').textContent = f.operation || '';
  $('counter').textContent = `${{stepIndex + 1}} / ${{frames().length}}`;
  $('range').value = stepIndex;
  $('state').textContent = pretty(f.state || {{}});
  $('io').textContent = `输入\\n${{pretty(ARTIFACT.input_data)}}\\n\\n输出\\n${{pretty(variant().result)}}`;
  renderCode(variant().code || '', f.code_line || 1);
  renderTimeline();
  $('metaphor').innerHTML = renderMetaphor(f);
}}
function renderTimeline() {{
  $('timeline').innerHTML = frames().map((f,i)=>`<button class="tick ${{i===stepIndex?'active':''}}" onclick="go(${{i}})">${{i+1}}</button>`).join('');
}}
function renderCode(code, active) {{
  const lines = String(code || '').split('\\n');
  $('code').innerHTML = lines.map((line,i)=>`<div class="line ${{i+1===active?'active':''}}"><span class="lineno">${{i+1}}</span><span>${{esc(line) || ' '}}</span></div>`).join('');
}}
function play() {{
  if (timer) return stop();
  $('play').textContent = '暂停';
  timer = setInterval(()=>{{ if(stepIndex >= frames().length - 1) return stop(); go(stepIndex + 1); }}, 950);
}}
function stop() {{ if (timer) clearInterval(timer); timer = null; $('play').textContent = '播放'; }}

function renderMetaphor(f) {{
  const s = f.state || {{}};
  const text = `${{ARTIFACT.problem_title}} ${{scene().algorithm || ''}}`.toLowerCase();
  if ((Array.isArray(s.dp) && Array.isArray(s.nums) && Number.isInteger(s.target)) || text.includes('背包') || text.includes('子集')) return renderBagWorld(f);
  if (s.graph || hasLayout(f, 'graph')) return renderGraphWorld(f);
  if (Array.isArray(s.temperatures) || (Array.isArray(s.stack) && (Array.isArray(s.ans) || Array.isArray(s.answer)))) return renderStackWorld(f);
  if (s.geometry || Array.isArray(s.points) || hasLayout(f, 'geometry')) return renderGeometryWorld(f);
  return renderFallbackWorld(f);
}}
function hasLayout(f, layout) {{ return (f.objects || []).some(o => o.type === 'container' && o.meta && o.meta.layout === layout); }}
function targetSet(f) {{ return new Set([...(f.marks || []).map(m=>m.target), ...((f.objects || []).filter(o=>o.role).map(o=>o.id))]); }}
function targetIds(f) {{ return new Set((f.marks || []).map(m=>m.target)); }}
function markRole(f, id) {{
  const m = (f.marks || []).find(x => x.target === id);
  return m ? m.role : '';
}}

function renderBagWorld(f) {{
  const s = f.state || {{}};
  const nums = Array.isArray(s.nums) ? s.nums : (Array.isArray(ARTIFACT.input_data.nums) ? ARTIFACT.input_data.nums : []);
  const dp = Array.isArray(s.dp) ? s.dp : [];
  const target = Number.isInteger(s.target) ? s.target : Math.max(0, dp.length - 1);
  const currentIndex = Number.isInteger(s.i) ? s.i : nums.findIndex(x => x === s.num);
  const currentNum = Number.isInteger(s.num) ? s.num : nums[currentIndex];
  const active = targetSet(f);
  const trueCount = dp.filter(Boolean).length;
  const slots = Array.from({{length: Math.max(1, Math.min(target + 1, 24))}}, (_,i) => {{
    const on = Boolean(dp[i]);
    return `<div class="slot ${{on?'on':''}}">${{i}}</div>`;
  }}).join('');
  const items = nums.map((n,i)=>`<div class="item-card ${{i===currentIndex || active.has('nums['+i+']') ? 'active' : ''}}"><div class="item-icon">${{i===currentIndex?'💎':'✦'}}</div><div class="item-name">物品 ${{i+1}}</div><div class="item-meta">重量 ${{esc(n)}} · 价值 ${{esc(n)}}</div></div>`).join('');
  const pct = dp.length ? Math.round(trueCount * 100 / dp.length) : 0;
  return `<div class="bag-world"><div><div class="items">${{items}}</div></div><div class="bag ${{currentNum!==undefined?'active':''}}"><div class="bag-title">容量圣袋 · 目标 ${{esc(target)}}</div><div class="capacity-grid">${{slots}}</div><div class="meter"><div style="width:${{pct}}%"></div></div><p style="color:var(--muted);line-height:1.45">当前尝试：${{currentNum===undefined?'初始化':('重量 '+currentNum)}}。绿色槽表示已经可达的容量和。</p></div></div>`;
}}

function renderGraphWorld(f) {{
  const s = f.state || {{}};
  const graph = s.graph || ARTIFACT.input_data.graph || {{}};
  const nodes = Object.keys(graph);
  for (const list of Object.values(graph)) for (const n of (Array.isArray(list) ? list : [])) if (!nodes.includes(String(n))) nodes.push(String(n));
  const marks = targetIds(f);
  const w=860,h=440,cx=w/2,cy=h/2,r=Math.min(w,h)*.36;
  const pos={{}};
  nodes.forEach((n,i)=>{{ const a=-Math.PI/2 + 2*Math.PI*i/Math.max(1,nodes.length); pos[n]=[cx+r*Math.cos(a),cy+r*Math.sin(a)]; }});
  let edges='';
  for (const [u, arr] of Object.entries(graph)) for (const v of (Array.isArray(arr) ? arr : [])) {{
    const a=pos[String(u)], b=pos[String(v)]; if(!a||!b) continue;
    const hot = marks.has(`edge:${{u}}->${{v}}`) ? 'hot' : '';
    edges += `<line class="g-edge ${{hot}}" x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"></line>`;
  }}
  const dist = s.dist || {{}};
  const nodeSvg = nodes.map(n => {{
    const p=pos[n]; const id='node:'+n; const role=markRole(f,id); const hot = marks.has(id) ? (role==='answer'?'answer':'hot') : '';
    const label = dist[n] === undefined ? n : `${{n}} · ${{dist[n]}}`;
    return `<g class="g-node ${{hot}}" transform="translate(${{p[0]}},${{p[1]}})"><circle r="30"></circle><text text-anchor="middle" dominant-baseline="central" font-size="13">${{esc(label)}}</text></g>`;
  }}).join('');
  const queue = Array.isArray(s.queue) ? s.queue : [];
  return `<div class="graph-world"><div><svg class="svg-stage" viewBox="0 0 ${{w}} ${{h}}">${{edges}}${{nodeSvg}}</svg><div class="queue-strip">${{queue.map(x=>`<span class="token">队列 ${{esc(x)}}</span>`).join('')}}</div></div></div>`;
}}

function renderStackWorld(f) {{
  const s = f.state || {{}};
  const temps = Array.isArray(s.temperatures) ? s.temperatures : [];
  const stack = Array.isArray(s.stack) ? s.stack : [];
  const active = targetIds(f);
  const maxVal = Math.max(1, ...temps);
  const bars = temps.map((t,i)=>`<div class="bar ${{active.has('temperatures['+i+']')?'hot':''}}" style="height:${{Math.max(34, t/maxVal*310)}}px">${{esc(t)}}</div>`).join('');
  const blocks = stack.map(i=>`<div class="stack-block">${{esc(i)}} · ${{esc(temps[i] ?? '')}}</div>`).join('');
  return `<div class="stack-world"><div><h3 style="margin:0 0 10px">温度山脉</h3><div class="bars">${{bars}}</div></div><div><h3 style="margin:0 0 10px">等待栈塔</h3><div class="stack-tower">${{blocks || '<span class="token">空栈</span>'}}</div></div></div>`;
}}

function renderGeometryWorld(f) {{
  const s = f.state || {{}};
  let points = [];
  let hull = [];
  if (s.geometry && Array.isArray(s.geometry.points)) {{
    points = s.geometry.points.map((p,i)=>Array.isArray(p)?{{id:String(i),x:p[0],y:p[1],label:`[${{p[0]}},${{p[1]}}]`}}:p);
    hull = Array.isArray(s.geometry.hull) ? s.geometry.hull.map(String) : [];
  }} else if (Array.isArray(s.points)) {{
    points = s.points.map((p,i)=>Array.isArray(p)?{{id:String(i),x:p[0],y:p[1],label:`[${{p[0]}},${{p[1]}}]`}}:p);
  }} else {{
    const objs = f.objects || [];
    points = objs.filter(o=>o.type==='node' && o.meta && Number.isFinite(Number(o.meta.x))).map(o=>({{id:o.id.replace('point:',''),x:Number(o.meta.x),y:Number(o.meta.y),label:o.label||o.id}}));
    hull = objs.filter(o=>o.type==='edge' && o.meta && o.meta.shape==='hull').map(o=>[o.source.replace('point:',''),o.target.replace('point:','')]);
  }}
  const w=860,h=440,pad=44;
  const xs=points.map(p=>Number(p.x)), ys=points.map(p=>Number(p.y));
  const minX=Math.min(...xs,0), maxX=Math.max(...xs,1), minY=Math.min(...ys,0), maxY=Math.max(...ys,1);
  const sx=x=>pad+(Number(x)-minX)*(w-2*pad)/Math.max(1,maxX-minX);
  const sy=y=>h-pad-(Number(y)-minY)*(h-2*pad)/Math.max(1,maxY-minY);
  const by=new Map(points.map(p=>[String(p.id),p]));
  let edges='';
  if (hull.length && Array.isArray(hull[0])) {{
    edges = hull.map(e=>{{ const a=by.get(String(e[0])), b=by.get(String(e[1])); return a&&b?`<line class="g-edge hot" x1="${{sx(a.x)}}" y1="${{sy(a.y)}}" x2="${{sx(b.x)}}" y2="${{sy(b.y)}}"></line>`:''; }}).join('');
  }} else if (hull.length > 1) {{
    edges = hull.map((id,i)=>{{ const a=by.get(String(id)), b=by.get(String(hull[(i+1)%hull.length])); return a&&b?`<line class="g-edge hot" x1="${{sx(a.x)}}" y1="${{sy(a.y)}}" x2="${{sx(b.x)}}" y2="${{sy(b.y)}}"></line>`:''; }}).join('');
  }}
  const active = targetIds(f);
  const nodeSvg = points.map(p=>`<g class="g-node ${{active.has('point:'+p.id)?'hot':''}}" transform="translate(${{sx(p.x)}},${{sy(p.y)}})"><circle r="10"></circle><text x="14" y="-8" font-size="12">${{esc(p.label || p.id)}}</text></g>`).join('');
  return `<div class="geo-world"><svg class="svg-stage" viewBox="0 0 ${{w}} ${{h}}"><line class="g-edge" x1="${{pad}}" y1="${{h-pad}}" x2="${{w-pad}}" y2="${{h-pad}}"></line><line class="g-edge" x1="${{pad}}" y1="${{pad}}" x2="${{pad}}" y2="${{h-pad}}"></line>${{edges}}${{nodeSvg}}</svg></div>`;
}}

function renderFallbackWorld(f) {{
  const active = targetIds(f);
  const objects = (f.objects || []).filter(o => o.type !== 'arrow').slice(0, 32);
  return `<div class="fallback-grid">${{objects.map(o=>`<div class="tile ${{active.has(o.id)?'hot':''}}"><strong>${{esc(o.label || o.id)}}</strong><br><span style="color:var(--muted)">${{esc(typeof o.value === 'object' ? JSON.stringify(o.value) : o.value)}}</span></div>`).join('')}}</div>`;
}}

$('prev').onclick = () => go(stepIndex - 1);
$('next').onclick = () => go(stepIndex + 1);
$('play').onclick = play;
$('range').oninput = e => go(parseInt(e.target.value, 10));
window.addEventListener('keydown', e => {{ if(e.key==='ArrowLeft') go(stepIndex-1); if(e.key==='ArrowRight') go(stepIndex+1); if(e.key===' ') {{ e.preventDefault(); play(); }} }});
boot();
</script>
</body>
</html>
"""


def _escape(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
