"""Export build artifacts to a single-file Simplified Chinese HTML app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from algolab.schemas.validation import BuildArtifact


def save_html(artifact: BuildArtifact, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(artifact), encoding="utf-8")
    output.with_suffix(".json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return output


def render_html(artifact: BuildArtifact) -> str:
    lab_json = artifact.model_dump_json().replace("</", "<\\/")
    title = _escape(artifact.problem_title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
  --bg:#f6f7fb; --panel:#fff; --ink:#172033; --muted:#657085; --line:#d7deea;
  --blue:#2563eb; --green:#16a34a; --amber:#d97706; --red:#dc2626; --violet:#7c3aed;
  --shadow:0 1px 2px rgba(15,23,42,.08);
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif; color:var(--ink); background:var(--bg); }}
button,input {{ font:inherit; }}
.app {{ min-height:100vh; display:grid; grid-template-rows:auto 1fr; }}
.topbar {{ background:#fff; border-bottom:1px solid var(--line); padding:14px 20px; display:grid; grid-template-columns:minmax(280px,1fr) auto; gap:16px; align-items:center; }}
h1 {{ margin:0; font-size:20px; letter-spacing:0; }}
.subtitle {{ margin:5px 0 0; color:var(--muted); font-size:13px; }}
.badges {{ display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; }}
.badge {{ border:1px solid var(--line); border-radius:999px; padding:4px 9px; background:#fff; color:var(--muted); font-size:12px; }}
.badge.ok {{ color:#166534; border-color:#bbf7d0; background:#f0fdf4; }}
.badge.warn {{ color:#92400e; border-color:#fde68a; background:#fffbeb; }}
.workspace {{ display:grid; grid-template-columns:minmax(260px,320px) minmax(440px,1fr) minmax(300px,380px); gap:14px; padding:14px; min-height:0; }}
.col {{ display:grid; gap:14px; align-content:start; min-width:0; }}
.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); min-width:0; }}
.section {{ padding:14px; }}
.section h2 {{ margin:0 0 10px; color:#374151; font-size:13px; letter-spacing:.04em; text-transform:uppercase; }}
.tabs {{ display:grid; gap:8px; }}
.tab {{ border:1px solid var(--line); border-radius:7px; background:#fff; padding:10px; cursor:pointer; text-align:left; }}
.tab.active {{ border-color:var(--blue); box-shadow:inset 3px 0 0 var(--blue); }}
.tab strong {{ display:block; font-size:14px; }}
.tab span {{ display:block; margin-top:4px; color:var(--muted); font-size:12px; line-height:1.25; }}
pre {{ margin:0; white-space:pre-wrap; overflow:auto; font-size:12px; line-height:1.45; }}
.jsonbox {{ max-height:260px; border:1px solid var(--line); border-radius:6px; padding:10px; background:#fbfdff; }}
.hero {{ min-height:520px; display:grid; grid-template-rows:auto minmax(360px,1fr) auto auto; }}
.step-head {{ padding:14px 16px; border-bottom:1px solid var(--line); display:grid; grid-template-columns:1fr auto; gap:12px; }}
.step-head h2 {{ margin:0; font-size:18px; }}
.step-head p {{ margin:6px 0 0; color:var(--muted); font-size:13px; }}
.pill {{ border-radius:999px; border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8; padding:5px 10px; height:fit-content; font-size:12px; text-transform:uppercase; }}
.canvas {{ padding:18px; overflow:auto; min-height:360px; }}
.controls {{ border-top:1px solid var(--line); padding:12px 14px; display:grid; grid-template-columns:auto auto auto 1fr auto; gap:10px; align-items:center; }}
.controls button {{ border:1px solid var(--line); background:#fff; border-radius:6px; padding:8px 11px; cursor:pointer; }}
.controls .primary {{ border-color:var(--blue); background:var(--blue); color:#fff; }}
.range {{ width:100%; accent-color:var(--blue); }}
.counter {{ color:var(--muted); font-size:13px; min-width:86px; text-align:right; }}
.timeline {{ border-top:1px solid var(--line); display:flex; gap:4px; padding:12px 14px; overflow-x:auto; }}
.tick {{ width:28px; min-width:28px; height:28px; border:1px solid var(--line); border-radius:6px; background:#fff; color:var(--muted); cursor:pointer; font-size:11px; }}
.tick.active {{ background:var(--blue); border-color:var(--blue); color:#fff; }}
.objects {{ display:grid; gap:18px; }}
.view-title {{ margin:0 0 10px; font-size:15px; }}
.array {{ display:flex; flex-wrap:wrap; gap:8px; align-items:flex-end; }}
.array-wrap {{ display:grid; gap:8px; width:fit-content; max-width:100%; }}
.cell {{ position:relative; min-width:42px; min-height:40px; border:1px solid var(--line); border-radius:7px; background:#fff; display:grid; place-items:center; font-weight:650; }}
.cell .idx {{ position:absolute; top:3px; left:5px; color:var(--muted); font-size:10px; font-weight:500; }}
.pointer-row {{ display:grid; gap:8px; }}
.pointer-slot {{ min-width:42px; min-height:24px; display:flex; flex-wrap:wrap; align-items:flex-start; justify-content:center; gap:3px; }}
.pointer-tag {{ border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8; border-radius:999px; padding:2px 7px; font-size:11px; line-height:1.4; font-weight:650; }}
.hot {{ border-color:var(--blue)!important; background:#eff6ff!important; color:#1d4ed8; }}
.dep {{ border-color:var(--amber)!important; background:#fffbeb!important; }}
.answer {{ border-color:var(--green)!important; background:#f0fdf4!important; }}
.conflict {{ border-color:var(--red)!important; background:#fef2f2!important; }}
.matrix {{ display:grid; gap:4px; width:fit-content; max-width:100%; overflow:auto; }}
.mcell {{ width:44px; height:34px; border:1px solid var(--line); border-radius:5px; background:#fff; display:grid; place-items:center; font-size:12px; font-weight:620; }}
.stack {{ width:min(360px,100%); display:flex; flex-direction:column-reverse; gap:6px; }}
.queue {{ max-width:100%; display:flex; flex-wrap:wrap; gap:8px; align-items:center; }}
.stack-item {{ border:1px solid var(--line); border-radius:6px; padding:9px 10px; background:#fff; }}
.mapgrid {{ display:grid; gap:6px; }}
.maprow {{ display:grid; grid-template-columns:minmax(80px,130px) 1fr; gap:8px; align-items:start; border:1px solid var(--line); border-radius:6px; padding:7px 8px; background:#fff; }}
.graph-svg {{ width:100%; min-height:330px; border:1px solid var(--line); border-radius:8px; background:#fbfdff; }}
.edge {{ stroke:#b8c1d1; stroke-width:1.6; }}
.node circle {{ fill:#fff; stroke:#94a3b8; stroke-width:2; }}
.node.hot circle {{ fill:#dbeafe; stroke:var(--blue); stroke-width:3; }}
.node.dep circle {{ fill:#fffbeb; stroke:var(--amber); }}
.node.answer circle {{ fill:#dcfce7; stroke:var(--green); }}
.tree-svg,.geometry-svg {{ width:100%; min-height:330px; border:1px solid var(--line); border-radius:8px; background:#fbfdff; }}
.geo-axis {{ stroke:#e5e7eb; stroke-width:1; }}
.geo-segment {{ stroke:#64748b; stroke-width:2; fill:none; }}
.geo-hull {{ stroke:#16a34a; stroke-width:2.4; fill:none; }}
.geo-sweep {{ stroke:#dc2626; stroke-width:2; stroke-dasharray:6 5; }}
.heap {{ display:grid; gap:10px; justify-items:center; width:fit-content; max-width:100%; }}
.heap-level {{ display:flex; gap:8px; justify-content:center; }}
.arrow-note {{ color:var(--muted); font-size:12px; margin-top:8px; }}
.code {{ max-height:370px; background:#101827; color:#dbeafe; border-radius:7px; overflow:auto; }}
.line {{ display:grid; grid-template-columns:42px 1fr; gap:10px; padding:1px 10px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; line-height:1.55; }}
.lineno {{ color:#7f8ea3; text-align:right; }}
.line.active {{ background:#1d4ed8; color:#fff; }}
.state-grid {{ display:grid; gap:8px; }}
.state-grid {{ max-height:360px; overflow:auto; padding-right:2px; }}
.state-row {{ border:1px solid var(--line); border-radius:6px; padding:8px; background:#fff; }}
.state-row strong {{ display:block; margin-bottom:4px; color:#374151; font-size:12px; }}
.interaction {{ border-left:3px solid var(--violet); background:#f5f3ff; padding:10px; border-radius:6px; }}
.interaction button {{ display:block; width:100%; margin:6px 0; border:1px solid #ddd6fe; background:#fff; border-radius:6px; padding:8px; text-align:left; cursor:pointer; }}
.feedback {{ margin-top:8px; color:#4c1d95; font-size:13px; }}
@media (max-width:1100px) {{ .workspace {{ grid-template-columns:1fr; }} .topbar {{ grid-template-columns:1fr; }} .badges {{ justify-content:flex-start; }} }}
</style>
</head>
<body>
<div class="app">
  <header class="topbar">
    <div><h1 id="title"></h1><p id="subtitle" class="subtitle"></p></div>
    <div id="badges" class="badges"></div>
  </header>
  <main class="workspace">
    <aside class="col">
      <section class="panel section"><h2>解法</h2><div id="tabs" class="tabs"></div></section>
      <section class="panel section"><h2>输入</h2><pre id="input" class="jsonbox"></pre></section>
      <section class="panel section"><h2>输出</h2><pre id="result" class="jsonbox"></pre></section>
    </aside>
    <section class="col">
      <div class="panel hero">
        <div class="step-head">
          <div><h2 id="step-title"></h2><p id="step-desc"></p></div>
          <div id="op" class="pill"></div>
        </div>
        <div id="canvas" class="canvas"></div>
        <div class="controls">
          <button id="prev">上一步</button>
          <button id="play" class="primary">播放</button>
          <button id="next">下一步</button>
          <input id="range" class="range" type="range" min="0" value="0">
          <div id="counter" class="counter"></div>
        </div>
        <div id="timeline" class="timeline"></div>
      </div>
    </section>
    <aside class="col">
      <section class="panel section"><h2>状态</h2><div id="state" class="state-grid"></div></section>
      <section class="panel section"><h2>交互</h2><div id="interaction"></div></section>
      <section class="panel section"><h2>代码</h2><div id="code" class="code"></div></section>
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
const sceneIds = () => Object.keys(ARTIFACT.scenes || {{}});
const variant = () => ARTIFACT.variants[variantIndex];
const scene = () => ARTIFACT.scenes[variant().id];
const frames = () => scene().frames || [];
const frame = () => frames()[stepIndex];

function boot() {{
  $('title').textContent = ARTIFACT.problem_title || '算法可视化实验';
  $('subtitle').textContent = ARTIFACT.input_contract || '由语义轨迹编译生成，页面只渲染 scene graph';
  $('input').textContent = pretty(ARTIFACT.input_data);
  renderBadges();
  renderTabs();
  selectVariant(0);
}}
function renderBadges() {{
  const g = ARTIFACT.validation.release_gate || {{}};
  const items = [['过程', g.process_ready], ['轨迹', g.trace_ready], ['视觉', g.visual_ready], ['发布', g.release_ready]];
  $('badges').innerHTML = items.map(([k,v]) => `<span class="badge ${{v?'ok':'warn'}}">${{k}}：${{v?'通过':'待检查'}}</span>`).join('');
}}
function renderTabs() {{
  $('tabs').innerHTML = ARTIFACT.variants.map((v,i) => `<button class="tab ${{i===variantIndex?'active':''}}" onclick="selectVariant(${{i}})"><strong>${{esc(v.name)}}</strong><span>${{esc(v.time_complexity)}} · ${{esc(v.space_complexity)}}<br>${{esc(v.strategy)}}</span></button>`).join('');
}}
function selectVariant(i) {{
  variantIndex = i; stepIndex = 0; stop();
  renderTabs();
  $('result').textContent = pretty(variant().result);
  $('range').max = Math.max(0, frames().length - 1);
  renderStep();
}}
function go(i) {{
  stepIndex = Math.max(0, Math.min(i, frames().length - 1));
  renderStep();
}}
function renderStep() {{
  const f = frame();
  if (!f) return;
  $('step-title').textContent = f.title;
  $('step-desc').textContent = f.description || '';
  $('op').textContent = f.operation;
  $('counter').textContent = `${{stepIndex + 1}} / ${{frames().length}}`;
  $('range').value = stepIndex;
  renderCanvas(f);
  renderState(f.state || {{}});
  renderInteraction(f.interaction);
  renderCode(variant().code || '', f.code_line || 1);
  renderTimeline();
}}
function markClass(id, marks) {{
  const found = (marks || []).find(m => m.target === id);
  if (!found) return '';
  if (found.role === 'dependency') return 'dep';
  if (found.role === 'answer' || found.role === 'visited') return 'answer';
  if (found.role === 'conflict') return 'conflict';
  return 'hot';
}}
function groupedObjects(f) {{
  const groups = {{}};
  for (const o of f.objects || []) {{
    const parent = o.parent || (o.type === 'node' || o.type === 'edge' ? 'graph' : o.id);
    if (!groups[parent]) groups[parent] = [];
    groups[parent].push(o);
  }}
  return groups;
}}
function renderCanvas(f) {{
  const groups = groupedObjects(f);
  const containers = (f.objects || []).filter(o => o.type === 'container');
  let html = '<div class="objects">';
  if (containers.length) {{
    for (const c of containers) html += renderContainer(c, groups[c.id] || [], f.marks || []);
  }} else {{
    html += renderLooseObjects(f.objects || [], f.marks || []);
  }}
  const arrows = (f.objects || []).filter(o => o.type === 'arrow');
  if (arrows.length) html += `<div class="arrow-note">依赖关系：${{arrows.map(a => esc(a.source + ' → ' + a.target)).join('，')}}</div>`;
  html += '</div>';
  $('canvas').innerHTML = html;
}}
function renderContainer(c, children, marks) {{
  const layout = c.meta && c.meta.layout;
  const cells = children.filter(o => o.type === 'cell');
  if (layout === 'matrix') return renderMatrix(c, cells, marks);
  if (layout === 'array') return renderArray(c, cells, marks);
  if (layout === 'string') return renderString(c, cells, marks);
  if (layout === 'heap') return renderHeap(c, cells, marks);
  if (['queue','deque'].includes(layout)) return renderQueue(c, cells, marks);
  if (layout === 'stack') return renderStack(c, cells, marks);
  if (layout === 'graph') return renderGraph(c, children, marks);
  if (['tree','trie','union_find','recursion_tree'].includes(layout)) return renderTree(c, children, marks, layout);
  if (layout === 'geometry') return renderGeometry(c, children, marks);
  if (layout === 'map') return renderMap(c, children, marks);
  return renderMap(c, children, marks);
}}
function renderArray(c, cells, marks) {{
  cells.sort((a,b)=>(a.index??0)-(b.index??0));
  const pointers = currentPointersFor(c.id);
  const pointerByIndex = new Map();
  for (const p of pointers) {{
    if (!pointerByIndex.has(p.index)) pointerByIndex.set(p.index, []);
    pointerByIndex.get(p.index).push(p);
  }}
  const cellHtml = cells.map(o => `<div class="cell ${{markClass(o.id, marks)}}"><span class="idx">${{o.index}}</span>${{esc(o.value)}}</div>`).join('');
  const pointerHtml = cells.map(o => `<div class="pointer-slot">${{(pointerByIndex.get(o.index) || []).map(p => `<span class="pointer-tag">${{esc(p.label || p.id.replace('pointer:',''))}}</span>`).join('')}}</div>`).join('');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="array-wrap"><div class="array">${{cellHtml}}</div><div class="pointer-row" style="grid-template-columns:repeat(${{Math.max(cells.length,1)}},42px)">${{pointerHtml}}</div></div></div>`;
}}
function renderMatrix(c, cells, marks) {{
  const rows = Math.max(0, ...cells.map(o => o.row ?? 0)) + 1;
  const cols = Math.max(0, ...cells.map(o => o.col ?? 0)) + 1;
  const by = new Map(cells.map(o => [`${{o.row}},${{o.col}}`, o]));
  let body = '';
  for (let r=0; r<rows; r++) for (let col=0; col<cols; col++) {{
    const o = by.get(`${{r}},${{col}}`) || {{id:'', value:''}};
    body += `<div class="mcell ${{markClass(o.id, marks)}}">${{esc(o.value)}}</div>`;
  }}
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="matrix" style="grid-template-columns:repeat(${{Math.max(cols,1)}},44px)">${{body}}</div></div>`;
}}
function renderString(c, cells, marks) {{
  return renderArray(c, cells, marks);
}}
function renderHeap(c, cells, marks) {{
  cells.sort((a,b)=>(a.index??0)-(b.index??0));
  let html = `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="heap">`;
  let idx = 0, level = 0;
  while (idx < cells.length) {{
    const count = Math.pow(2, level);
    const levelCells = cells.slice(idx, idx + count);
    html += `<div class="heap-level">${{levelCells.map(o => `<div class="cell ${{markClass(o.id, marks)}}"><span class="idx">${{o.index}}</span>${{esc(o.value)}}</div>`).join('')}}</div>`;
    idx += count; level += 1;
  }}
  html += '</div></div>';
  return html;
}}
function renderStack(c, cells, marks) {{
  cells.sort((a,b)=>(a.index??0)-(b.index??0));
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="stack">${{cells.map(o => `<div class="stack-item ${{markClass(o.id, marks)}}">${{esc(o.value)}}</div>`).join('')}}</div></div>`;
}}
function renderQueue(c, cells, marks) {{
  cells.sort((a,b)=>(a.index??0)-(b.index??0));
  const body = cells.map((o,i) => `<div class="cell ${{markClass(o.id, marks)}}"><span class="idx">${{i===0?'头':i===cells.length-1?'尾':o.index}}</span>${{esc(o.value)}}</div>`).join('');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="queue">${{body}}</div></div>`;
}}
function renderMap(c, children, marks) {{
  const rows = children.filter(o => o.id !== c.id && o.type !== 'arrow');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="mapgrid">${{rows.map(o => `<div class="maprow ${{markClass(o.id, marks)}}"><strong>${{esc(o.label || o.id)}}</strong><span>${{esc(typeof o.value === 'object' ? JSON.stringify(o.value) : o.value)}}</span></div>`).join('')}}</div></div>`;
}}
function renderGraph(c, children, marks) {{
  const nodes = children.filter(o => o.type === 'node');
  const edges = children.filter(o => o.type === 'edge');
  const w=720,h=340,cx=w/2,cy=h/2,r=Math.min(w,h)*.36;
  const pos={{}};
  nodes.forEach((n,i)=>{{ const a=-Math.PI/2 + 2*Math.PI*i/Math.max(1,nodes.length); pos[n.id]=[cx+r*Math.cos(a),cy+r*Math.sin(a)]; }});
  const edgeSvg = edges.map(e => {{
    const a=pos[e.source], b=pos[e.target]; if(!a||!b) return '';
    return `<line class="edge" x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"></line>`;
  }}).join('');
  const nodeSvg = nodes.map(n => {{
    const p=pos[n.id]; const cls=markClass(n.id, marks);
    return `<g class="node ${{cls}}" transform="translate(${{p[0]}},${{p[1]}})"><circle r="23"></circle><text text-anchor="middle" dominant-baseline="central" font-size="13" font-weight="650">${{esc(n.label || n.id.replace('node:',''))}}</text></g>`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || '图')}}</h3><svg class="graph-svg" viewBox="0 0 ${{w}} ${{h}}">${{edgeSvg}}${{nodeSvg}}</svg></div>`;
}}
function renderTree(c, children, marks, layout) {{
  const nodes = children.filter(o => o.type === 'node');
  const edges = children.filter(o => o.type === 'edge');
  const w=720,h=340;
  const roots = inferRoots(nodes, edges);
  const levels = treeLevels(nodes, edges, roots);
  const pos={{}};
  levels.forEach((levelNodes, depth) => {{
    const y = 48 + depth * Math.max(62, (h - 80) / Math.max(1, levels.length - 1));
    levelNodes.forEach((n, i) => {{
      const x = (i + 1) * w / (levelNodes.length + 1);
      pos[n.id] = [x, y];
    }});
  }});
  nodes.forEach((n, i) => {{ if (!pos[n.id]) pos[n.id]=[(i+1)*w/(nodes.length+1), h-45]; }});
  const edgeSvg = edges.map(e => {{
    const a=pos[e.source], b=pos[e.target]; if(!a||!b) return '';
    return `<line class="edge" x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"></line>`;
  }}).join('');
  const nodeSvg = nodes.map(n => {{
    const p=pos[n.id]; const cls=markClass(n.id, marks);
    return `<g class="node ${{cls}}" transform="translate(${{p[0]}},${{p[1]}})"><circle r="22"></circle><text text-anchor="middle" dominant-baseline="central" font-size="12" font-weight="650">${{esc(n.label || n.id.replace('node:',''))}}</text></g>`;
  }}).join('');
  const label = layout === 'trie' ? 'Trie' : layout === 'union_find' ? '并查集' : layout === 'recursion_tree' ? '递归树' : '树';
  return `<div><h3 class="view-title">${{esc(c.label || label)}}</h3><svg class="tree-svg" viewBox="0 0 ${{w}} ${{h}}">${{edgeSvg}}${{nodeSvg}}</svg></div>`;
}}
function inferRoots(nodes, edges) {{
  const targets = new Set(edges.map(e => e.target));
  const roots = nodes.filter(n => !targets.has(n.id));
  return roots.length ? roots : nodes.slice(0,1);
}}
function treeLevels(nodes, edges, roots) {{
  const bySource = new Map();
  edges.forEach(e => {{ if(!bySource.has(e.source)) bySource.set(e.source, []); bySource.get(e.source).push(e.target); }});
  const nodeById = new Map(nodes.map(n => [n.id, n]));
  const seen = new Set();
  let frontier = roots.map(r => r.id);
  const levels = [];
  while (frontier.length && levels.length < 10) {{
    const levelNodes = frontier.filter(id => nodeById.has(id) && !seen.has(id)).map(id => nodeById.get(id));
    if (!levelNodes.length) break;
    levels.push(levelNodes);
    frontier.forEach(id => seen.add(id));
    frontier = frontier.flatMap(id => bySource.get(id) || []);
  }}
  const rest = nodes.filter(n => !seen.has(n.id));
  if (rest.length) levels.push(rest);
  return levels.length ? levels : [nodes];
}}
function renderGeometry(c, children, marks) {{
  const points = children.filter(o => o.type === 'node' && o.meta && Number.isFinite(Number(o.meta.x)) && Number.isFinite(Number(o.meta.y)));
  const edges = children.filter(o => o.type === 'edge');
  const sweeps = children.filter(o => o.meta && o.meta.layout === 'sweep_line');
  const w=720,h=340,pad=36;
  const xs = points.map(p => Number(p.meta.x)), ys = points.map(p => Number(p.meta.y));
  for (const s of sweeps) {{
    if (s.meta.axis === 'x' && Number.isFinite(Number(s.meta.x))) xs.push(Number(s.meta.x));
    if (s.meta.axis === 'y' && Number.isFinite(Number(s.meta.y))) ys.push(Number(s.meta.y));
  }}
  const minX=Math.min(...xs,0), maxX=Math.max(...xs,1), minY=Math.min(...ys,0), maxY=Math.max(...ys,1);
  const sx=x => pad + (Number(x)-minX) * (w-2*pad) / Math.max(1, maxX-minX);
  const sy=y => h - pad - (Number(y)-minY) * (h-2*pad) / Math.max(1, maxY-minY);
  const byId = new Map(points.map(p => [p.id, p]));
  const edgeSvg = edges.map(e => {{
    const a=byId.get(e.source), b=byId.get(e.target); if(!a||!b) return '';
    const cls = e.meta && e.meta.shape === 'hull' ? 'geo-hull' : 'geo-segment';
    return `<line class="${{cls}}" x1="${{sx(a.meta.x)}}" y1="${{sy(a.meta.y)}}" x2="${{sx(b.meta.x)}}" y2="${{sy(b.meta.y)}}"></line>`;
  }}).join('');
  const sweepSvg = sweeps.map(s => {{
    if (s.meta.axis === 'x') {{
      const x=sx(s.meta.x);
      return `<line class="geo-sweep" x1="${{x}}" y1="${{pad}}" x2="${{x}}" y2="${{h-pad}}"></line><text x="${{x+6}}" y="${{pad+14}}" font-size="12" fill="#dc2626">${{esc(s.label || '扫描线')}}</text>`;
    }}
    const y=sy(s.meta.y);
    return `<line class="geo-sweep" x1="${{pad}}" y1="${{y}}" x2="${{w-pad}}" y2="${{y}}"></line><text x="${{pad+6}}" y="${{y-6}}" font-size="12" fill="#dc2626">${{esc(s.label || '扫描线')}}</text>`;
  }}).join('');
  const pointSvg = points.map(p => {{
    const cls=markClass(p.id, marks); const x=sx(p.meta.x), y=sy(p.meta.y);
    return `<g class="node ${{cls}}" transform="translate(${{x}},${{y}})"><circle r="7"></circle><text x="10" y="-8" font-size="12">${{esc(p.label)}}</text></g>`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || '几何平面')}}</h3><svg class="geometry-svg" viewBox="0 0 ${{w}} ${{h}}"><line class="geo-axis" x1="${{pad}}" y1="${{h-pad}}" x2="${{w-pad}}" y2="${{h-pad}}"></line><line class="geo-axis" x1="${{pad}}" y1="${{pad}}" x2="${{pad}}" y2="${{h-pad}}"></line>${{edgeSvg}}${{sweepSvg}}${{pointSvg}}</svg></div>`;
}}
function renderLooseObjects(objects, marks) {{
  const fake = {{id:'状态', label:'状态', meta:{{layout:'map'}}}};
  return renderMap(fake, objects, marks);
}}
function currentPointersFor(containerId) {{
  const f = frame();
  return (f.objects || []).filter(o => o.type === 'pointer' && (o.parent === containerId || (o.meta && o.meta.array === containerId)) && Number.isInteger(o.index));
}}
function renderTimeline() {{
  $('timeline').innerHTML = frames().map((f,i)=>`<button class="tick ${{i===stepIndex?'active':''}}" onclick="go(${{i}})">${{i+1}}</button>`).join('');
}}
function renderState(state) {{
  const entries = Object.entries(state || {{}});
  $('state').innerHTML = entries.length ? entries.map(([k,v]) => `<div class="state-row"><strong>${{esc(k)}}</strong><pre>${{esc(pretty(v))}}</pre></div>`).join('') : '<p style="color:var(--muted);margin:0;">当前步骤没有状态快照。</p>';
}}
function renderInteraction(interaction) {{
  if (!interaction) {{ $('interaction').innerHTML = '<p style="color:var(--muted);margin:0;">当前步骤没有交互题。</p>'; return; }}
  const opts = Array.isArray(interaction.options) ? interaction.options : [];
  const optHtml = opts.map(o => `<button onclick="checkChoice('${{encodeURIComponent(String(o))}}')">${{esc(o)}}</button>`).join('');
  const inputHtml = interaction.type === 'input' ? '<input id="free-answer" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;"><button onclick="checkInput()">检查</button>' : '';
  $('interaction').innerHTML = `<div class="interaction"><strong>${{esc(interaction.prompt || '思考题')}}</strong>${{optHtml}}${{inputHtml}}<div id="feedback" class="feedback"></div></div>`;
}}
function checkChoice(encoded) {{
  const value = decodeURIComponent(encoded);
  const ans = frame().interaction.answer;
  const ok = Array.isArray(ans) ? ans.map(String).includes(value) : String(ans) === value;
  $('feedback').textContent = (ok ? '正确。' : '再想想。') + (frame().interaction.explanation || '');
}}
function checkInput() {{
  const value = $('free-answer').value.trim();
  const ans = String(frame().interaction.answer ?? '').trim();
  $('feedback').textContent = (value === ans ? '正确。' : `参考答案：${{ans}}。`) + (frame().interaction.explanation || '');
}}
function renderCode(code, active) {{
  const lines = String(code || '').split('\\n');
  $('code').innerHTML = lines.map((line,i)=>`<div class="line ${{i+1===active?'active':''}}"><span class="lineno">${{i+1}}</span><span>${{esc(line) || ' '}}</span></div>`).join('');
}}
function play() {{
  if (timer) return stop();
  $('play').textContent = '暂停';
  timer = setInterval(()=>{{ if(stepIndex >= frames().length-1) return stop(); go(stepIndex+1); }}, 850);
}}
function stop() {{ if(timer) clearInterval(timer); timer=null; $('play').textContent='播放'; }}
$('prev').onclick = () => go(stepIndex-1);
$('next').onclick = () => go(stepIndex+1);
$('play').onclick = play;
$('range').oninput = e => go(parseInt(e.target.value,10));
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
