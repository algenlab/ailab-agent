"""Export build artifacts to a single-file Simplified Chinese HTML app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from algolab.renderer.layout_registry import layout_registry_json
from algolab.renderer.panels import workspace_markup
from algolab.renderer.runtime_shell import document_end, document_start
from algolab.renderer.spatial_runtime import spatial_runtime_script
from algolab.renderer.targets import select_render_target
from algolab.schemas.validation import BuildArtifact


def save_html(artifact: BuildArtifact, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(artifact), encoding="utf-8")
    output.with_suffix(".json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return output


def render_html(artifact: BuildArtifact) -> str:
    lab_json = json.dumps(_public_artifact_payload(artifact.model_dump()), ensure_ascii=False).replace("</", "<\\/")
    title = _escape(artifact.problem_title)
    render_target = select_render_target(artifact)
    return f"""{document_start(title)}
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
.spatial-wrap {{ display:grid; gap:8px; min-height:360px; }}
.spatial-stage {{ width:100%; min-height:330px; border:1px solid var(--line); border-radius:8px; background:#0b1220; display:block; }}
.spatial-label {{ color:var(--muted); font-size:12px; }}
.spatial-fallback {{ color:#92400e; background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:8px 10px; font-size:12px; }}
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
.teaching {{ display:grid; gap:8px; }}
.teach-row {{ border:1px solid var(--line); border-radius:6px; padding:8px; background:#fff; }}
.teach-row strong {{ display:block; margin-bottom:4px; color:#374151; font-size:12px; }}
.teach-row p {{ margin:0; color:#172033; font-size:13px; line-height:1.45; }}
.evidence,.step-evidence {{ display:grid; gap:8px; }}
.evidence-block {{ border:1px solid var(--line); border-radius:6px; padding:8px; background:#fff; min-width:0; }}
.evidence-block strong {{ display:block; margin-bottom:5px; color:#374151; font-size:12px; }}
.evidence-line {{ display:grid; grid-template-columns:minmax(82px,120px) minmax(0,1fr); gap:8px; align-items:start; padding:3px 0; font-size:12px; line-height:1.4; }}
.evidence-line span:first-child {{ color:var(--muted); }}
.evidence-line code,.diff-row code {{ overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; }}
.evidence-list {{ margin:0; padding-left:17px; color:#172033; font-size:12px; line-height:1.45; }}
.evidence-list li {{ margin:3px 0; }}
.chip-row {{ display:flex; flex-wrap:wrap; gap:5px; }}
.chip {{ border:1px solid var(--line); border-radius:999px; padding:2px 7px; color:var(--muted); background:#fff; font-size:11px; }}
.chip.ok {{ color:#166534; border-color:#bbf7d0; background:#f0fdf4; }}
.chip.warn {{ color:#92400e; border-color:#fde68a; background:#fffbeb; }}
.chip.bad {{ color:#991b1b; border-color:#fecaca; background:#fef2f2; }}
.diff-row {{ display:grid; gap:4px; padding:6px 0; border-top:1px solid #eef2f7; font-size:12px; }}
.diff-row:first-child {{ border-top:0; padding-top:0; }}
.diff-kind {{ width:max-content; border-radius:999px; padding:1px 6px; background:#eff6ff; color:#1d4ed8; font-size:11px; }}
.mlgrid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:8px; }}
.mlitem {{ border:1px solid var(--line); border-radius:6px; padding:8px; background:#fbfdff; min-width:0; }}
.mlitem strong {{ display:block; color:#374151; font-size:12px; margin-bottom:5px; }}
.spark {{ width:100%; height:56px; border:1px solid var(--line); border-radius:5px; background:#fff; }}
@media (max-width:1100px) {{ .workspace {{ grid-template-columns:1fr; }} .topbar {{ grid-template-columns:1fr; }} .badges {{ justify-content:flex-start; }} }}
</style>
</head>
{workspace_markup(render_target)}
{spatial_runtime_script()}
<script>
const ARTIFACT = {lab_json};
const RUNTIME_TARGET = {json.dumps(render_target, ensure_ascii=False)};
const LAYOUT_RENDERERS = {layout_registry_json()};
let variantIndex = 0;
let stepIndex = 0;
let timer = null;
const SPATIAL_STATE = {{ renderer:null, scene:null, camera:null, canvas:null, resizeBound:false, fallbackReason:'', primitives:{{}}, layouts:[] }};
window.SPATIAL_STATE = SPATIAL_STATE;
const $ = id => document.getElementById(id);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const pretty = x => JSON.stringify(x, null, 2);
const sceneIds = () => Object.keys(ARTIFACT.scenes || {{}});
const variant = () => ARTIFACT.variants[variantIndex];
const scene = () => ARTIFACT.scenes[variant().id];
const frames = () => scene().frames || [];
const frame = () => frames()[stepIndex];
const isSpatialTarget = () => RUNTIME_TARGET === 'spatial_3d' || RUNTIME_TARGET === 'hybrid_2_5d';

function boot() {{
  $('title').textContent = ARTIFACT.problem_title || '算法可视化实验';
  $('subtitle').textContent = ARTIFACT.input_contract || '由语义轨迹编译生成，页面只渲染 scene graph';
  $('input').textContent = pretty(ARTIFACT.input_data);
  renderBadges();
  renderEvidence();
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
  renderEvidence();
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
  renderTeaching(f);
  renderStepEvidence(f);
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
  if (isSpatialTarget() && renderSpatialCanvas(f)) {{
    return;
  }}
  renderTeachingCanvas(f);
}}
function renderTeachingCanvas(f) {{
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
function renderSpatialCanvas(f) {{
  try {{
    if (!ensureSpatialRuntime()) return false;
    resizeSpatialRenderer();
    const marks = f.marks || [];
    const objects = f.objects || [];
    const drawable = objects.filter(o => ['node','cell','pointer','edge'].includes(o.type));
    const nodes = drawable.filter(o => o.type === 'node' || o.type === 'cell');
    if (!nodes.length) return false;

    const step = f.step || 0;
    const containers = spatialContainers(objects);
    SPATIAL_STATE.primitives = {{}};
    SPATIAL_STATE.layouts = Object.values(containers).map(c => c.layout).filter(Boolean);
    const positions = spatialPositions(nodes, step, containers);
    const scene = SPATIAL_STATE.scene;
    scene.clear();
    SPATIAL_STATE.renderer.setClearColor(spatialClearColor(step), 1);
    updateSpatialCamera(nodes, positions, marks, step);
    drawSpatialPlanes(scene, containers, nodes, positions, marks, step);
    drawSpatialDocks(scene, containers, nodes, positions, marks, step);

    for (const edge of drawable.filter(o => o.type === 'edge')) {{
      const a = positions[edge.source], b = positions[edge.target];
      if (a && b) drawSpatialEdge(scene, a, b, edge, marks, containers[edge.parent]);
    }}
    for (const arrow of objects.filter(o => o.type === 'arrow')) {{
      const a = positions[arrow.source], b = positions[arrow.target];
      if (a && b) drawSpatialPathTrail(scene, a, b, arrow, marks, step);
    }}
    nodes.forEach((o, i) => drawSpatialNode(scene, positions[o.id], o, marks, i, step, containers[o.parent]));
    for (const pointer of drawable.filter(o => o.type === 'pointer')) {{
      const target = positions[pointer.target] || positions[`${{pointer.parent}}[${{pointer.index}}]`];
      if (target) drawSpatialPointer(scene, target, pointer, marks, step);
    }}
    SPATIAL_STATE.renderer.render(scene, SPATIAL_STATE.camera);
    const label = document.getElementById('spatial-label');
    label.textContent = `${{RUNTIME_TARGET}} · Three.js WebGL · step ${{step + 1}} · ${{f.title || f.operation || ''}}`;
    return true;
  }} catch (err) {{
    SPATIAL_STATE.fallbackReason = err && err.message ? err.message : String(err);
    return false;
  }}
}}
function ensureSpatialRuntime() {{
  if (!window.THREE || !window.THREE.WebGLRenderer) {{
    SPATIAL_STATE.fallbackReason = 'Three.js runtime unavailable';
    return false;
  }}
  const canvasHost = $('canvas');
  if (!document.getElementById('spatial-canvas')) {{
    canvasHost.innerHTML = '<div class="spatial-wrap"><canvas id="spatial-canvas" class="spatial-stage"></canvas><div id="spatial-label" class="spatial-label"></div></div>';
  }}
  const canvas = document.getElementById('spatial-canvas');
  if (SPATIAL_STATE.renderer && SPATIAL_STATE.canvas === canvas) return true;
  try {{
    SPATIAL_STATE.canvas = canvas;
    SPATIAL_STATE.scene = new THREE.Scene();
    SPATIAL_STATE.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    SPATIAL_STATE.camera.position.set(0, 0, 7.5);
    SPATIAL_STATE.camera.lookAt(new THREE.Vector3(0, 0, 0));
    SPATIAL_STATE.renderer = new THREE.WebGLRenderer({{ canvas, antialias:true, preserveDrawingBuffer:true }});
    SPATIAL_STATE.renderer.setPixelRatio(window.devicePixelRatio || 1);
    resizeSpatialRenderer();
    if (!SPATIAL_STATE.resizeBound) {{
      window.addEventListener('resize', () => {{
        if (isSpatialTarget() && document.getElementById('spatial-canvas')) renderStep();
      }});
      SPATIAL_STATE.resizeBound = true;
    }}
    return true;
  }} catch (err) {{
    SPATIAL_STATE.renderer = null;
    SPATIAL_STATE.scene = null;
    SPATIAL_STATE.camera = null;
    SPATIAL_STATE.fallbackReason = err && err.message ? err.message : String(err);
    return false;
  }}
}}
function resizeSpatialRenderer() {{
  const canvas = SPATIAL_STATE.canvas;
  const renderer = SPATIAL_STATE.renderer;
  const camera = SPATIAL_STATE.camera;
  if (!canvas || !renderer || !camera) return;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(360, Math.floor(rect.width || canvas.parentElement.clientWidth || 720));
  const height = Math.max(330, Math.floor(rect.height || 330));
  if (canvas.width !== width || canvas.height !== height) {{
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(1, height);
    camera.updateProjectionMatrix();
  }}
}}
function spatialClearColor(step) {{
  const palette = ['#0b1220', '#102033', '#111827', '#172554', '#052e2b'];
  return palette[step % palette.length];
}}
function spatialContainers(objects) {{
  const result = {{}};
  for (const obj of objects || []) {{
    if (obj.type !== 'container') continue;
    result[obj.id] = {{ id: obj.id, label: obj.label || obj.id, layout: obj.meta && obj.meta.layout || 'generic' }};
  }}
  return result;
}}
function spatialPrimitive(name) {{
  SPATIAL_STATE.primitives[name] = (SPATIAL_STATE.primitives[name] || 0) + 1;
}}
function spatialGroup(nodes, containers, layoutName) {{
  return nodes.filter(node => {{
    const layout = containers[node.parent] && containers[node.parent].layout;
    return layout === layoutName;
  }});
}}
function spatialPositions(nodes, step, containers) {{
  const pos = {{}};
  const byParent = new Map();
  nodes.forEach(node => {{
    const parent = node.parent || 'scene';
    if (!byParent.has(parent)) byParent.set(parent, []);
    byParent.get(parent).push(node);
  }});
  const parentIds = Array.from(byParent.keys());
  parentIds.forEach((parent, groupIndex) => {{
    const group = byParent.get(parent);
    const layout = containers[parent] && containers[parent].layout || 'generic';
    const offsetX = parentIds.length === 1 ? 0 : (groupIndex - (parentIds.length - 1) / 2) * 2.35;
    if (layout === 'matrix') return positionMatrixGroup(pos, group, offsetX);
    if (layout === 'queue') return positionLinearGroup(pos, group, offsetX, -1.9, 0.72);
    if (layout === 'stack') return positionStackGroup(pos, group, offsetX);
    if (layout === 'recursion_tree' || layout === 'tree' || layout === 'trie' || layout === 'union_find') return positionTreeGroup(pos, group, offsetX, layout);
    if (layout === 'geometry') return positionGeometryGroup(pos, group, offsetX);
    if (layout === 'array') return positionLinearGroup(pos, group, offsetX, -1.35, 0.62);
    positionOrbitGroup(pos, group, step, offsetX);
  }});
  return pos;
}}
function positionOrbitGroup(pos, group, step, offsetX) {{
  const n = Math.max(group.length, 1);
  group.forEach((node, i) => {{
    const angle = -Math.PI / 2 + 2 * Math.PI * i / n;
    const ring = n > 14 ? 1.95 + (i % 3) * 0.24 : 1.9;
    const wave = Math.sin(step * 0.45 + i * 0.7) * 0.18;
    pos[node.id] = new THREE.Vector3(offsetX + Math.cos(angle) * ring, Math.sin(angle) * 1.35 + wave, Math.sin(angle) * 1.1);
  }});
}}
function positionLinearGroup(pos, group, offsetX, y, spacing) {{
  const sorted = [...group].sort((a,b)=>(a.index??0)-(b.index??0));
  const start = -((sorted.length - 1) * spacing) / 2;
  sorted.forEach((node, i) => {{
    pos[node.id] = new THREE.Vector3(offsetX + start + i * spacing, y, ((i % 2) - 0.5) * 0.18);
  }});
}}
function positionStackGroup(pos, group, offsetX) {{
  const sorted = [...group].sort((a,b)=>(a.index??0)-(b.index??0));
  sorted.forEach((node, i) => {{
    pos[node.id] = new THREE.Vector3(offsetX, -1.75 + i * 0.48, i * 0.08);
  }});
}}
function positionMatrixGroup(pos, group, offsetX) {{
  const rows = Math.max(1, ...group.map(o => (o.row ?? 0) + 1));
  const cols = Math.max(1, ...group.map(o => (o.col ?? 0) + 1));
  group.forEach(node => {{
    const row = node.row ?? 0, col = node.col ?? 0;
    pos[node.id] = new THREE.Vector3(offsetX + (col - (cols - 1) / 2) * 0.55, 1.1 - (row - (rows - 1) / 2) * 0.45, -0.75);
  }});
}}
function positionTreeGroup(pos, group, offsetX, layout) {{
  const sorted = [...group].sort((a,b)=>String(a.id).localeCompare(String(b.id)));
  sorted.forEach((node, i) => {{
    const depth = Math.max(0, String(node.id).split('_').length - 1);
    const levelWidth = Math.max(1, sorted.filter(n => Math.max(0, String(n.id).split('_').length - 1) === depth).length);
    const levelIndex = sorted.filter((n, j) => j <= i && Math.max(0, String(n.id).split('_').length - 1) === depth).length - 1;
    const spread = layout === 'union_find' ? 0.82 : 0.68;
    pos[node.id] = new THREE.Vector3(offsetX + (levelIndex - (levelWidth - 1) / 2) * spread, 1.65 - depth * 0.62, depth * 0.2);
  }});
}}
function positionGeometryGroup(pos, group, offsetX) {{
  const xs = group.map(o => Number(o.meta && o.meta.x)).filter(Number.isFinite);
  const ys = group.map(o => Number(o.meta && o.meta.y)).filter(Number.isFinite);
  const minX = Math.min(...xs, 0), maxX = Math.max(...xs, 1), minY = Math.min(...ys, 0), maxY = Math.max(...ys, 1);
  group.forEach((node, i) => {{
    const x = Number(node.meta && node.meta.x);
    const y = Number(node.meta && node.meta.y);
    if (Number.isFinite(x) && Number.isFinite(y)) {{
      pos[node.id] = new THREE.Vector3(offsetX + (x - minX) / Math.max(1, maxX - minX) * 3 - 1.5, (y - minY) / Math.max(1, maxY - minY) * 2.4 - 1.2, 0.25);
    }} else {{
      pos[node.id] = new THREE.Vector3(offsetX + i * 0.4, 0, 0);
    }}
  }});
}}
function updateSpatialCamera(nodes, positions, marks, step) {{
  spatialPrimitive('camera_focus');
  const camera = SPATIAL_STATE.camera;
  const focusObj = nodes.find(o => markClass(o.id, marks) === 'hot') || nodes.find(o => markClass(o.id, marks)) || nodes[0];
  const focus = positions[focusObj.id] || new THREE.Vector3(0, 0, 0);
  const orbit = step * 0.08;
  camera.position.set(Math.sin(orbit) * 1.3, 0.35 + Math.cos(orbit) * 0.2, 7.2);
  camera.lookAt(focus);
}}
function spatialColor(role, fallback) {{
  if (role === 'answer') return '#22c55e';
  if (role === 'dep') return '#f59e0b';
  if (role === 'hot') return '#60a5fa';
  if (role === 'conflict') return '#ef4444';
  return fallback;
}}
function containerColor(container) {{
  const layout = container && container.layout;
  if (layout === 'matrix') return '#475569';
  if (layout === 'queue') return '#0f766e';
  if (layout === 'stack') return '#7c3aed';
  if (layout === 'geometry') return '#0369a1';
  if (layout === 'recursion_tree' || layout === 'tree' || layout === 'trie' || layout === 'union_find') return '#2563eb';
  return '#334155';
}}
function drawSpatialPlanes(scene, containers, nodes, positions, marks, step) {{
  const matrixCells = spatialGroup(nodes, containers, 'matrix');
  if (matrixCells.length) {{
    spatialPrimitive('matrix_plane');
    const plane = new THREE.Mesh(new THREE.BoxGeometry(3.9, 2.7, 0.08), new THREE.MeshBasicMaterial({{ color:'#1e293b', opacity:0.9 }}));
    plane.position.set(0, 0.95, -1.05);
    scene.add(plane);
  }}
  const geometryPoints = spatialGroup(nodes, containers, 'geometry');
  if (geometryPoints.length) {{
    spatialPrimitive('matrix_plane');
    const plane = new THREE.Mesh(new THREE.BoxGeometry(3.7, 2.7, 0.05), new THREE.MeshBasicMaterial({{ color:'#0f172a', opacity:0.92 }}));
    plane.position.set(0, 0, -0.1);
    scene.add(plane);
  }}
}}
function drawSpatialDocks(scene, containers, nodes, positions, marks, step) {{
  const queueNodes = spatialGroup(nodes, containers, 'queue');
  if (queueNodes.length) {{
    spatialPrimitive('queue_dock');
    const dock = new THREE.Mesh(new THREE.BoxGeometry(Math.max(1.2, queueNodes.length * 0.68), 0.18, 0.28), new THREE.MeshBasicMaterial({{ color:'#0f766e', opacity:0.85 }}));
    dock.position.set(0, -2.25, -0.28);
    scene.add(dock);
  }}
  const stackNodes = spatialGroup(nodes, containers, 'stack');
  if (stackNodes.length) {{
    spatialPrimitive('stack_tower');
    const tower = new THREE.Mesh(new THREE.BoxGeometry(0.78, Math.max(0.5, stackNodes.length * 0.5), 0.2), new THREE.MeshBasicMaterial({{ color:'#7c3aed', opacity:0.82 }}));
    tower.position.set(0, -1.52 + stackNodes.length * 0.24, -0.24);
    scene.add(tower);
  }}
}}
function drawSpatialEdge(scene, a, b, edge, marks, container) {{
  spatialPrimitive('edge');
  const role = markClass(edge.id, marks);
  const geometry = new THREE.BufferGeometry().setFromPoints([a, b]);
  const material = new THREE.LineBasicMaterial({{ color: spatialColor(role, containerColor(container) || '#94a3b8'), opacity: role ? 1 : 0.72 }});
  scene.add(new THREE.Line(geometry, material));
}}
function drawSpatialPathTrail(scene, a, b, arrow, marks, step) {{
  spatialPrimitive('path_trail');
  const middle = new THREE.Vector3((a.x + b.x) / 2, (a.y + b.y) / 2 + 0.14, (a.z + b.z) / 2 + 0.18);
  const material = new THREE.LineBasicMaterial({{ color:'#f97316', opacity:0.92 }});
  scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, middle]), material));
  scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([middle, b]), material));
}}
function drawSpatialNode(scene, p, obj, marks, index, step, container) {{
  if (!p) return;
  const role = markClass(obj.id, marks);
  const lift = Math.sin((step + index) * 0.7) * 0.12;
  const isCell = obj.type === 'cell';
  spatialPrimitive(isCell ? 'cell_block' : 'node');
  const geometry = isCell ? new THREE.BoxGeometry(1.08, 0.64, 0.44) : new THREE.SphereGeometry(0.44, 24, 12);
  const fallback = isCell ? '#cbd5e1' : containerColor(container);
  const material = new THREE.MeshBasicMaterial({{ color: spatialColor(role, fallback), opacity: 0.96 }});
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(p.x, p.y + lift, p.z);
  mesh.userData = {{ id: obj.id, label: obj.label || obj.value }};
  scene.add(mesh);
}}
function drawSpatialPointer(scene, target, pointer, marks, step) {{
  spatialPrimitive('pointer_beam');
  const above = new THREE.Vector3(target.x, target.y + 0.95, target.z + 0.15);
  const geometry = new THREE.BufferGeometry().setFromPoints([above, target]);
  const material = new THREE.LineBasicMaterial({{ color: '#38bdf8', opacity: 1 }});
  scene.add(new THREE.Line(geometry, material));
  const marker = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 8), new THREE.MeshBasicMaterial({{ color: '#38bdf8' }}));
  marker.position.set(above.x, above.y + Math.sin(step * 0.6) * 0.08, above.z);
  scene.add(marker);
}}
function renderContainer(c, children, marks) {{
  const layout = c.meta && c.meta.layout;
  const cells = children.filter(o => o.type === 'cell');
  const renderer = LAYOUT_RENDERERS[layout] || LAYOUT_RENDERERS.generic || 'map';
  if (renderer === 'matrix') return renderMatrix(c, cells, marks);
  if (renderer === 'array') return renderArray(c, cells, marks);
  if (renderer === 'string') return renderString(c, cells, marks);
  if (renderer === 'heap') return renderHeap(c, cells, marks);
  if (renderer === 'queue') return renderQueue(c, cells, marks);
  if (renderer === 'stack') return renderStack(c, cells, marks);
  if (renderer === 'graph') return renderGraph(c, children, marks);
  if (renderer === 'tree') return renderTree(c, children, marks, layout);
  if (renderer === 'geometry') return renderGeometry(c, children, marks);
  if (renderer === 'ml') return renderML(c, children, marks);
  if (renderer === 'map') return renderMap(c, children, marks);
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
function renderML(c, children, marks) {{
  const rows = children.filter(o => o.id !== c.id && o.type !== 'arrow' && o.type !== 'edge');
  const body = rows.map(o => {{
    if (o.type === 'loss_curve') return `<div class="mlitem ${{markClass(o.id, marks)}}"><strong>${{esc(o.label || 'loss')}}</strong>${{renderSparkline(o.value)}}</div>`;
    const shape = o.meta && Array.isArray(o.meta.shape) && o.meta.shape.length ? `shape ${{o.meta.shape.join('×')}} · ` : '';
    return `<div class="mlitem ${{markClass(o.id, marks)}}"><strong>${{esc(o.label || o.id)}}</strong><span>${{esc(shape + compactValue(o.value))}}</span></div>`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || 'ML state')}}</h3><div class="mlgrid">${{body}}</div></div>`;
}}
function compactValue(value) {{
  if (value === null || value === undefined) return '';
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value);
  return text.length > 80 ? text.slice(0, 77) + '...' : text;
}}
function renderSparkline(value) {{
  const values = Array.isArray(value) ? value.map(Number).filter(Number.isFinite) : [];
  if (!values.length) return `<span>${{esc(compactValue(value))}}</span>`;
  const w=140,h=48,p=5,min=Math.min(...values),max=Math.max(...values);
  const pts = values.map((v,i) => {{
    const x = p + i * (w - 2*p) / Math.max(1, values.length - 1);
    const y = h - p - (v - min) * (h - 2*p) / Math.max(1e-9, max - min);
    return `${{x}},${{y}}`;
  }}).join(' ');
  return `<svg class="spark" viewBox="0 0 ${{w}} ${{h}}"><polyline points="${{pts}}" fill="none" stroke="#2563eb" stroke-width="2"></polyline></svg>`;
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
function renderEvidence() {{
  const v = variant() || {{}};
  const validation = ARTIFACT.validation || {{}};
  const gate = validation.release_gate || {{}};
  const contract = ARTIFACT.correctness_contract || null;
  const contractGate = validation.contract_validation && validation.contract_validation.release_gate || null;
  const tests = validation.contract_test_results || [];
  const checks = validation.checks || [];
  const warnings = validation.warnings || [];
  const errors = validation.errors || [];
  const renderReport = ARTIFACT.render_report || {{}};
  const testPassed = tests.filter(t => t.ok).length;
  const answerRows = [
    ['expected', ARTIFACT.expected_result],
    ['verifier', ARTIFACT.verifier_result],
    ['actual', v.result],
  ].filter(([,value]) => value !== undefined && value !== null);
  let html = '';
  html += `<div class="evidence-block"><strong>答案交叉检查</strong>${{answerRows.length ? answerRows.map(([k,val]) => evidenceLine(k, valueCode(val))).join('') : '<p style="color:var(--muted);margin:0;font-size:12px;">无 expected/verifier 证据。</p>'}}</div>`;
  html += `<div class="evidence-block"><strong>Release gate</strong><div class="chip-row">${{gateChips(gate).join('')}}</div>${{(gate.blocking_reasons || []).length ? `<ul class="evidence-list">${{gate.blocking_reasons.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : ''}}</div>`;
  if (contract) {{
    html += `<div class="evidence-block"><strong>CorrectnessContract</strong>${{evidenceLine('schema', esc(contract.schema_version || ''))}}${{evidenceLine('oracle', esc(contract.oracle_strategy || ''))}}${{contractGate ? `<div class="chip-row">${{gateChips(contractGate).join('')}}</div>` : ''}}${{contract.process_invariants && contract.process_invariants.length ? `<ul class="evidence-list">${{contract.process_invariants.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : ''}}</div>`;
  }}
  html += `<div class="evidence-block"><strong>Contract tests</strong>${{tests.length ? evidenceLine('passed', `${{testPassed}}/${{tests.length}}`) + `<ul class="evidence-list">${{tests.slice(0, 6).map(renderContractTest).join('')}}${{tests.length > 6 ? `<li>还有 ${{tests.length - 6}} 条已省略</li>` : ''}}</ul>` : '<p style="color:var(--muted);margin:0;font-size:12px;">当前 artifact 没有 contract 多输入测试。</p>'}}</div>`;
  html += `<div class="evidence-block"><strong>Pipeline checks</strong>${{checks.length ? `<ul class="evidence-list">${{checks.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : '<p style="color:var(--muted);margin:0;font-size:12px;">无 checks。</p>'}}</div>`;
  if (warnings.length || errors.length) {{
    html += `<div class="evidence-block"><strong>Warnings / errors</strong><ul class="evidence-list">${{errors.map(x => `<li>错误：${{esc(x)}}</li>`).join('')}}${{warnings.map(x => `<li>警告：${{esc(x)}}</li>`).join('')}}</ul></div>`;
  }}
  if (renderReport.requested_target || renderReport.actual_target) {{
    html += `<div class="evidence-block"><strong>Render target</strong>${{evidenceLine('requested', esc(renderReport.requested_target || ''))}}${{evidenceLine('actual', esc(renderReport.actual_target || RUNTIME_TARGET))}}${{renderReport.used_baseline_renderer ? evidenceLine('baseline', 'true') : ''}}</div>`;
  }}
  $('evidence').innerHTML = html;
}}
function gateChips(gate) {{
  const keys = ['schema_ready','oracle_ready','expected_consistent','generated_tests_pass','contract_ready','artifact_ready','process_ready','trace_ready','visual_ready','multi_solution_ready','release_ready'];
  return keys.filter(k => gate[k] !== undefined).map(k => `<span class="chip ${{gate[k] ? 'ok' : 'warn'}}">${{esc(k)}}：${{gate[k] ? 'PASS' : 'NO'}}</span>`);
}}
function renderContractTest(item) {{
  const cls = item.ok ? 'ok' : 'bad';
  const actual = item.solve_result !== undefined ? item.solve_result : item.actual;
  const reference = item.oracle_result !== null && item.oracle_result !== undefined ? item.oracle_result : item.expected;
  const bits = [`case ${{item.case_index ?? '?'}}`, item.variant_id || '', item.ok ? 'PASS' : 'FAIL'].filter(Boolean).join(' · ');
  return `<li><span class="chip ${{cls}}">${{esc(bits)}}</span><br><code>actual=${{esc(compactValue(actual))}} · reference=${{esc(compactValue(reference))}}</code>${{item.error ? `<br><code>${{esc(item.error)}}</code>` : ''}}</li>`;
}}
function evidenceLine(label, value) {{
  return `<div class="evidence-line"><span>${{esc(label)}}</span><code>${{value}}</code></div>`;
}}
function valueCode(value) {{
  return esc(compactValue(value));
}}
function renderStepEvidence(f) {{
  const evidence = f.evidence || {{}};
  const previous = stepIndex > 0 ? frames()[stepIndex - 1] : null;
  const diffs = stateDiff(previous && previous.state || {{}}, f.state || {{}});
  const marks = f.marks || [];
  const targets = evidence.targets || marks.filter(m => m.role !== 'dependency').map(m => m.target);
  const deps = evidence.deps || marks.filter(m => m.role === 'dependency').map(m => m.target);
  const changedTargetIds = targetChanges(targets, previous && previous.state || {{}}, f.state || {{}});
  let html = '';
  html += `<div class="evidence-block"><strong>本步语义</strong>${{evidenceLine('operation', esc(evidence.operation || f.operation || ''))}}${{evidenceLine('code_line', esc(evidence.code_line || f.code_line || ''))}}${{evidenceLine('targets', esc((targets || []).join(', ') || '无'))}}${{evidenceLine('deps', esc((deps || []).join(', ') || '无'))}}${{evidence.role ? evidenceLine('role', esc(evidence.role)) : ''}}</div>`;
  if (evidence.value !== undefined || evidence.before !== undefined || evidence.after !== undefined) {{
    html += `<div class="evidence-block"><strong>事件值</strong>${{evidence.value !== undefined ? evidenceLine('value', valueCode(evidence.value)) : ''}}${{evidence.before !== undefined ? evidenceLine('before', valueCode(evidence.before)) : ''}}${{evidence.after !== undefined ? evidenceLine('after', valueCode(evidence.after)) : ''}}</div>`;
  }}
  html += `<div class="evidence-block"><strong>状态变化</strong>${{diffs.length ? diffs.slice(0, 8).map(renderDiff).join('') : '<p style="color:var(--muted);margin:0;font-size:12px;">与上一帧相比没有关键变量变化。</p>'}}${{diffs.length > 8 ? `<p style="color:var(--muted);margin:6px 0 0;font-size:12px;">还有 ${{diffs.length - 8}} 项变化已省略。</p>` : ''}}</div>`;
  html += `<div class="evidence-block"><strong>目标写入核对</strong>${{changedTargetIds.length ? `<ul class="evidence-list">${{changedTargetIds.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : '<p style="color:var(--muted);margin:0;font-size:12px;">本步目标没有可解析的状态写入，或属于指针/节点移动。</p>'}}</div>`;
  $('step-evidence').innerHTML = html;
}}
function stateDiff(prev, next) {{
  const keys = Array.from(new Set([...Object.keys(prev || {{}}), ...Object.keys(next || {{}})])).sort();
  const result = [];
  for (const key of keys) {{
    const before = prev ? prev[key] : undefined;
    const after = next ? next[key] : undefined;
    if (stableJson(before) === stableJson(after)) continue;
    result.push({{ key, before, after, kind: before === undefined ? '新增' : after === undefined ? '删除' : '更新' }});
  }}
  return result;
}}
function renderDiff(diff) {{
  return `<div class="diff-row"><span class="diff-kind">${{esc(diff.kind)}} · ${{esc(diff.key)}}</span><code>${{esc(compactValue(diff.before))}} → ${{esc(compactValue(diff.after))}}</code></div>`;
}}
function targetChanges(targets, prev, next) {{
  return (targets || []).map(id => {{
    const before = resolveStateTarget(prev, id);
    const after = resolveStateTarget(next, id);
    if (!before.exists && !after.exists) return '';
    if (stableJson(before.value) === stableJson(after.value)) return '';
    return `${{id}}: ${{compactValue(before.value)}} → ${{compactValue(after.value)}}`;
  }}).filter(Boolean);
}}
function resolveStateTarget(state, id) {{
  if (!state || !id) return {{ exists:false }};
  if (Object.prototype.hasOwnProperty.call(state, id)) return {{ exists:true, value:state[id] }};
  const parsed = parseIndexedTarget(id);
  if (!parsed) return {{ exists:false }};
  let value = state[parsed.name];
  if (value === undefined) return {{ exists:false }};
  for (const idx of parsed.indices) {{
    if (value === undefined || value === null) return {{ exists:false }};
    value = value[idx];
  }}
  return {{ exists:true, value }};
}}
function parseIndexedTarget(id) {{
  const match = String(id).match(/^([A-Za-z_][\\w]*)((?:\\[[^\\]]+\\])+)$/
  );
  if (!match) return null;
  const indices = Array.from(match[2].matchAll(/\\[([^\\]]+)\\]/g)).map(item => /^-?\\d+$/.test(item[1]) ? Number(item[1]) : item[1]);
  return {{ name:match[1], indices }};
}}
function stableJson(value) {{
  if (value === undefined) return '__undefined__';
  try {{ return JSON.stringify(sortJson(value)); }} catch (_) {{ return String(value); }}
}}
function sortJson(value) {{
  if (Array.isArray(value)) return value.map(sortJson);
  if (value && typeof value === 'object') {{
    return Object.fromEntries(Object.keys(value).sort().map(k => [k, sortJson(value[k])]));
  }}
  return value;
}}
function teachingRows(f) {{
  const teaching = f.teaching || {{}};
  const rows = [
    ['当前步骤', teaching.what || f.title || f.operation],
    ['为什么', teaching.why || f.description || '根据当前状态推进算法步骤。'],
    ['公式', teaching.formula || ''],
    ['不变量', teaching.invariant || ''],
    ['常见错误', teaching.common_mistake || ''],
    ['提示', teaching.hint || ''],
  ].filter(([,value]) => String(value || '').trim());
  return rows.length ? rows : [['当前步骤', f.description || f.title || '继续执行算法步骤。']];
}}
function renderTeaching(f) {{
  $('teaching').innerHTML = `<div class="teaching">${{teachingRows(f).map(([label,value]) => `<div class="teach-row"><strong>${{esc(label)}}</strong><p>${{esc(value)}}</p></div>`).join('')}}</div>`;
}}
function renderInteraction(interaction) {{
  if (!interaction) {{ $('interaction').innerHTML = '<p style="color:var(--muted);margin:0;">当前步骤没有交互题。</p>'; return; }}
  const opts = Array.isArray(interaction.options) ? interaction.options : [];
  const choiceHtml = interaction.type === 'choice' ? opts.map(o => `<button onclick="checkChoice('${{encodeURIComponent(String(o))}}')">${{esc(o)}}</button>`).join('') : '';
  const inputHtml = interaction.type === 'input' ? '<input id="free-answer" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;"><button onclick="checkInput()">检查</button>' : '';
  const judgeHtml = interaction.type === 'judge' ? '<button onclick="checkJudge(true)">正确</button><button onclick="checkJudge(false)">错误</button>' : '';
  $('interaction').innerHTML = `<div class="interaction"><strong>${{esc(interaction.prompt || '思考题')}}</strong>${{choiceHtml}}${{inputHtml}}${{judgeHtml}}<div id="feedback" class="feedback"></div></div>`;
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
function checkJudge(value) {{
  const ans = frame().interaction.answer;
  const expected = ans === true || String(ans).toLowerCase() === 'true' || String(ans) === '正确';
  $('feedback').textContent = (value === expected ? '正确。' : '再想想。') + (frame().interaction.explanation || '');
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
{document_end()}
"""


def _escape(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _public_artifact_payload(payload: Any) -> Any:
    if isinstance(payload, list):
        return [_public_artifact_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {
            key: _public_artifact_payload(value)
            for key, value in payload.items()
            if not str(key).startswith("_")
        }
    return payload
