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
button,input,textarea {{ font:inherit; }}
.app {{ min-height:100vh; display:grid; grid-template-rows:auto 1fr auto; }}
.topbar {{ background:#fff; border-bottom:1px solid var(--line); padding:10px 16px; display:grid; grid-template-columns:minmax(240px,1fr) minmax(260px,420px) auto; gap:12px; align-items:center; }}
.top-title {{ min-width:0; }}
h1 {{ margin:0; font-size:18px; letter-spacing:0; }}
.subtitle {{ margin:5px 0 0; color:var(--muted); font-size:13px; }}
.top-summary {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; min-width:0; }}
.summary-card {{ border:1px solid var(--line); border-radius:7px; background:#fbfdff; padding:7px 9px; min-width:0; }}
.summary-card span {{ display:block; color:var(--muted); font-size:11px; line-height:1.3; }}
.summary-card strong {{ display:block; margin-top:2px; font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.badges {{ display:flex; flex-wrap:wrap; justify-content:flex-end; gap:6px; }}
.badge {{ border:1px solid var(--line); border-radius:999px; padding:3px 8px; background:#fff; color:var(--muted); font-size:11px; }}
.badge.ok {{ color:#166534; border-color:#bbf7d0; background:#f0fdf4; }}
.badge.warn {{ color:#92400e; border-color:#fde68a; background:#fffbeb; }}
.workspace {{ display:grid; grid-template-columns:minmax(220px,260px) minmax(680px,1fr) minmax(300px,340px); gap:10px; padding:10px; min-height:0; align-items:start; }}
.col {{ display:grid; gap:10px; align-content:start; min-width:0; }}
.task-col,.teaching-col {{ align-content:start; padding-right:2px; }}
.task-col {{ max-height:min(560px, calc(100vh - 86px)); }}
.task-col {{ overflow:auto; }}
.teaching-col {{ overflow:visible; }}
.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); min-width:0; }}
.section {{ padding:10px; }}
.section h2 {{ margin:0 0 8px; color:#374151; font-size:12px; letter-spacing:.04em; text-transform:uppercase; }}
.tabs {{ display:grid; gap:6px; max-height:160px; overflow:auto; padding-right:2px; }}
.tab {{ border:1px solid var(--line); border-radius:7px; background:#fff; padding:8px; cursor:pointer; text-align:left; }}
.tab.active {{ border-color:var(--blue); box-shadow:inset 3px 0 0 var(--blue); }}
.tab strong {{ display:block; font-size:14px; }}
.tab span {{ display:block; margin-top:4px; color:var(--muted); font-size:12px; line-height:1.25; }}
.variant-compare {{ display:grid; gap:6px; min-width:0; max-width:100%; max-height:160px; overflow:auto; padding-right:2px; }}
.variant-compare-card {{ border:1px solid var(--line); border-radius:7px; background:#fff; padding:8px; display:grid; gap:6px; min-width:0; max-width:100%; overflow-wrap:anywhere; }}
.variant-compare-card.active {{ border-color:#86efac; background:#f0fdf4; }}
.variant-compare-card > * {{ min-width:0; max-width:100%; }}
.variant-compare-card strong {{ display:block; font-size:13px; color:#172033; }}
.variant-compare-meta {{ display:grid; gap:4px; min-width:0; color:var(--muted); font-size:12px; line-height:1.35; }}
.variant-compare-meta span {{ min-width:0; overflow-wrap:anywhere; }}
.variant-compare-status {{ width:auto; justify-self:start; max-width:100%; min-width:0; border:1px solid #bbf7d0; border-radius:999px; padding:2px 7px; color:#166534; background:#f0fdf4; font-size:11px; overflow-wrap:anywhere; }}
.variant-compare-status.warn {{ border-color:#fde68a; color:#92400e; background:#fffbeb; }}
.variant-compare-card button {{ width:100%; border:1px solid #bfdbfe; border-radius:6px; background:#eff6ff; color:#1d4ed8; padding:6px 8px; cursor:pointer; text-align:center; }}
.variant-compare-card button:focus-visible {{ outline:2px solid #2563eb; outline-offset:2px; }}
pre {{ margin:0; white-space:pre-wrap; overflow:auto; font-size:12px; line-height:1.4; }}
.jsonbox {{ max-height:120px; border:1px solid var(--line); border-radius:6px; padding:8px; background:#fbfdff; }}
.jsonbox.compact {{ max-height:96px; }}
.hero {{ min-height:0; display:grid; grid-template-rows:auto minmax(460px,clamp(460px,64vh,700px)) auto auto; }}
.step-head {{ padding:10px 12px; border-bottom:1px solid var(--line); display:grid; grid-template-columns:1fr auto; gap:10px; }}
.step-head h2 {{ margin:0; font-size:16px; }}
.step-head p {{ margin:4px 0 0; color:var(--muted); font-size:12px; line-height:1.35; max-height:36px; overflow:auto; }}
.pill {{ border-radius:999px; border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8; padding:5px 10px; height:fit-content; font-size:12px; text-transform:uppercase; }}
.canvas {{ padding:12px; overflow:hidden; min-height:0; height:clamp(460px,64vh,700px); }}
.stage-grid {{ height:100%; min-height:0; display:grid; grid-template-rows:minmax(340px,1fr) minmax(96px,168px); gap:8px; }}
.scene-fit {{ position:relative; width:100%; height:100%; overflow:hidden; min-width:0; min-height:300px; cursor:grab; touch-action:none; }}
.scene-fit.dragging {{ cursor:grabbing; }}
.scene-fit.scroll-fit {{ overflow:auto; scrollbar-gutter:stable; }}
.scene-fit.pan-scroll {{ overflow:auto; scrollbar-gutter:stable both-edges; }}
.view-tools {{ position:absolute; top:8px; right:8px; z-index:8; display:flex; gap:5px; pointer-events:auto; }}
.view-tools button {{ border:1px solid #cbd5e1; border-radius:6px; background:rgba(255,255,255,.92); color:#334155; padding:4px 7px; font-size:11px; cursor:pointer; box-shadow:0 1px 2px rgba(15,23,42,.08); }}
.view-tools button:hover {{ border-color:#93c5fd; color:#1d4ed8; background:#eff6ff; }}
.stage-supplement {{ min-height:0; overflow:auto; display:grid; gap:8px; padding-right:2px; }}
.stage-supplement:has(.support-dock) > .visual-quality-telemetry,
.stage-supplement:has(.support-dock) > #dependency-detail {{ display:none; }}
.stage-supplement:has(.visual-card) > #dependency-detail {{ display:none; }}
.spatial-wrap {{ display:grid; gap:6px; min-height:0; }}
.spatial-stage {{ width:100%; height:clamp(240px,34vh,330px); border:1px solid var(--line); border-radius:8px; background:#0b1220; display:block; }}
.spatial-label {{ color:var(--muted); font-size:12px; }}
.spatial-fallback {{ color:#92400e; background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:8px 10px; font-size:12px; }}
.controls {{ border-top:1px solid var(--line); padding:8px 10px; display:grid; grid-template-columns:auto auto auto 1fr auto; gap:8px; align-items:center; }}
.controls button {{ border:1px solid var(--line); background:#fff; border-radius:6px; padding:6px 10px; cursor:pointer; }}
.controls .primary {{ border-color:var(--blue); background:var(--blue); color:#fff; }}
.range {{ width:100%; accent-color:var(--blue); }}
.counter {{ color:var(--muted); font-size:13px; min-width:86px; text-align:right; }}
.timeline {{ border-top:1px solid var(--line); display:flex; gap:6px; padding:8px 10px; overflow-x:auto; }}
.tick {{ position:relative; width:104px; min-width:104px; min-height:42px; border:1px solid var(--line); border-radius:7px; background:#fff; color:var(--muted); cursor:pointer; font-size:11px; text-align:left; padding:6px 7px 6px 12px; display:grid; gap:2px; align-content:center; }}
.tick::before {{ content:''; position:absolute; left:4px; top:8px; bottom:8px; width:3px; border-radius:999px; background:#cbd5e1; }}
.tick.keyframe::before {{ background:var(--amber); }}
.tick.active {{ background:#eff6ff; border-color:var(--blue); color:#1d4ed8; }}
.tick.active::before {{ background:var(--blue); }}
.tick-label {{ color:#172033; font-size:12px; font-weight:700; line-height:1.2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.tick.active .tick-label {{ color:#1d4ed8; }}
.tick-op {{ color:var(--muted); font-size:11px; line-height:1.2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.objects {{ display:grid; gap:10px; width:max-content; max-width:none; min-width:0; transform-origin:top left; }}
.scene-scroll-surface {{ position:relative; width:100%; height:100%; min-width:100%; min-height:100%; }}
.scene-scroll-surface > .objects,
.scene-fit > .objects {{ position:absolute; top:0; left:0; }}
.scene-world {{ will-change:transform; }}
.primary-scene {{ align-items:start; padding-top:56px; }}
.compound-scene {{ width:min(760px,78vw); grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr)); align-items:start; gap:12px; }}
.primitive-panel {{ min-width:0; max-width:100%; overflow:visible; border:1px solid #eef2f7; border-radius:7px; background:#fbfdff; padding:10px; }}
.primary-scene > .primitive-panel {{ min-width:min(560px,74vw); min-height:210px; display:grid; align-content:center; justify-content:center; }}
.primary-scene > .primitive-panel.primitive-graph,
.primary-scene > .primitive-panel.primitive-tree,
.primary-scene > .primitive-panel.primitive-recursion_tree,
.primary-scene > .primitive-panel.primitive-geometry,
.primary-scene > .primitive-panel.primitive-linked_list {{ min-width:min(760px,82vw); min-height:360px; }}
.primary-scene.compound-scene > .primitive-panel {{ min-width:min(360px,42vw); min-height:180px; padding:8px; justify-content:stretch; }}
.primary-scene.compound-scene > .primitive-panel.primitive-graph,
.primary-scene.compound-scene > .primitive-panel.primitive-tree,
.primary-scene.compound-scene > .primitive-panel.primitive-recursion_tree,
.primary-scene.compound-scene > .primitive-panel.primitive-geometry,
.primary-scene.compound-scene > .primitive-panel.primitive-linked_list {{ min-width:min(420px,46vw); min-height:240px; }}
.primary-scene.compound-scene > .primitive-panel.primitive-matrix,
.primary-scene.compound-scene > .primitive-panel.primitive-array,
.primary-scene.compound-scene > .primitive-panel.primitive-string,
.primary-scene.compound-scene > .primitive-panel.primitive-string_list {{ min-width:min(300px,34vw); min-height:170px; }}
.primary-scene.compound-scene .view-title {{ font-size:12px; margin-bottom:6px; }}
.primary-scene.compound-scene .graph-svg,
.primary-scene.compound-scene .tree-svg,
.primary-scene.compound-scene .geometry-svg,
.primary-scene.compound-scene .heap-svg,
.primary-scene.compound-scene .cycle-list-svg {{ height:clamp(190px,28vh,260px); }}
.primary-scene.compound-scene .array-wrap {{ width:100%; }}
.primary-scene.compound-scene .array {{ width:100%; max-width:100%; }}
.primary-scene.compound-scene .cell {{ min-width:38px; min-height:36px; }}
.dock-grid .graph-svg,
.dock-grid .tree-svg,
.dock-grid .geometry-svg,
.dock-grid .heap-svg,
.dock-grid .cycle-list-svg {{ height:96px; }}
.scene-fit > .semantic-anchor-band {{ position:absolute; top:10px; left:10px; z-index:6; }}
.semantic-anchor-band {{ width:min(520px,54vw); max-height:72px; overflow:hidden; border:1px solid #bfdbfe; border-radius:8px; background:rgba(239,246,255,.96); padding:8px 10px; display:flex; flex-wrap:wrap; align-items:center; gap:7px; box-shadow:0 1px 4px rgba(15,23,42,.10); }}
.semantic-anchor-label {{ color:#1e3a8a; font-size:12px; font-weight:800; margin-right:2px; }}
.semantic-anchor-chip {{ border:1px solid #bfdbfe; border-radius:999px; background:#fff; color:#1d4ed8; padding:4px 9px; font-size:12px; font-weight:750; overflow-wrap:anywhere; }}
.semantic-anchor-chip[target-kind="dependency"] {{ border-color:#fcd34d; background:#fffbeb; color:#92400e; }}
.semantic-anchor-chip[target-kind="target"] {{ border-color:#93c5fd; background:#dbeafe; color:#1d4ed8; }}
.support-dock {{ min-height:min(120px,100%); max-height:100%; overflow:auto; border:1px solid #e2e8f0; border-radius:7px; background:#f8fafc; padding:8px; scrollbar-gutter:stable; }}
.support-dock h3,.raw-state-dock h3 {{ margin:0 0 6px; color:#475569; font-size:12px; }}
.dock-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(180px,100%),1fr)); gap:8px; min-width:0; }}
.dock-grid .primitive-panel {{ padding:7px; background:#fff; }}
.dock-grid .view-title {{ font-size:12px; margin-bottom:5px; }}
.raw-state-dock {{ min-height:0; max-height:84px; overflow:hidden; border:1px dashed #cbd5e1; border-radius:7px; background:#fff; padding:7px 8px; }}
.raw-state-dock summary {{ color:#64748b; font-size:12px; }}
.primitive-panel .view-title {{ font-size:13px; margin-bottom:8px; }}
.view-title {{ margin:0 0 10px; font-size:15px; }}
.frame-stage-card {{ width:min(520px,70vw); min-height:168px; display:grid; align-content:center; justify-items:center; gap:10px; border:1px solid #bfdbfe; border-radius:8px; background:#eff6ff; color:#1e3a8a; padding:18px; text-align:center; }}
.primary-scene.compound-scene .frame-stage-card {{ width:100%; min-height:132px; padding:12px; }}
.dock-grid .frame-stage-card {{ width:100%; min-height:56px; padding:8px; gap:4px; }}
.frame-stage-card strong {{ font-size:20px; max-width:100%; overflow-wrap:anywhere; }}
.primary-scene.compound-scene .frame-stage-card strong {{ font-size:16px; line-height:1.25; }}
.dock-grid .frame-stage-card strong {{ font-size:12px; line-height:1.2; }}
.frame-stage-card span {{ font-size:12px; color:#475569; overflow-wrap:anywhere; }}
.answer-badge {{ position:absolute; top:10px; right:10px; z-index:6; max-width:min(320px,42vw); border:1px solid #86efac; border-radius:8px; background:rgba(240,253,244,.96); color:#14532d; padding:8px 10px; box-shadow:0 1px 4px rgba(15,23,42,.12); font-size:12px; line-height:1.35; overflow-wrap:anywhere; }}
.answer-badge strong {{ display:block; margin-bottom:2px; color:#166534; font-size:12px; }}
.array {{ display:flex; flex-wrap:wrap; gap:8px; align-items:flex-end; }}
.array-wrap {{ display:grid; gap:8px; width:fit-content; max-width:100%; }}
.cell {{ position:relative; min-width:42px; min-height:40px; border:1px solid var(--line); border-radius:7px; background:#fff; display:grid; place-items:center; font-weight:650; }}
.primary-scene.compound-scene .array-wrap {{ width:100%; min-width:0; }}
.primary-scene.compound-scene .array {{ width:100%; max-width:100%; min-width:0; }}
.primary-scene.compound-scene .cell {{ min-width:38px; min-height:36px; }}
.cell .idx {{ position:absolute; top:3px; left:5px; color:var(--muted); font-size:10px; font-weight:500; }}
.pointer-row {{ display:grid; gap:8px; }}
.pointer-slot {{ min-width:42px; min-height:24px; display:flex; flex-wrap:wrap; align-items:flex-start; justify-content:center; gap:3px; }}
.primary-scene.compound-scene .pointer-row {{ display:flex; flex-wrap:wrap; width:100%; gap:6px; }}
.primary-scene.compound-scene .pointer-slot {{ width:38px; min-width:38px; min-height:20px; }}
.pointer-tag {{ border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8; border-radius:999px; padding:2px 7px; font-size:11px; line-height:1.4; font-weight:650; }}
.hot {{ border-color:var(--blue)!important; background:#eff6ff!important; color:#1d4ed8; }}
.dep {{ border-color:var(--amber)!important; background:#fffbeb!important; }}
.answer {{ border-color:var(--green)!important; background:#f0fdf4!important; }}
.conflict {{ border-color:var(--red)!important; background:#fef2f2!important; }}
.matrix {{ display:grid; gap:4px; width:fit-content; max-width:none; overflow:visible; }}
.mcell {{ width:44px; height:34px; border:1px solid var(--line); border-radius:5px; background:#fff; display:grid; place-items:center; font-size:12px; font-weight:620; }}
.mcell.pattern-dp-formula-substitution.role-dp-target {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.mcell.pattern-dp-formula-substitution.role-dp-dependency {{ border-color:#f59e0b; background:#fffbeb; }}
.set-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(98px,1fr)); gap:8px; width:min(720px,78vw); max-width:100%; }}
.set-card {{ min-height:52px; border:1px solid var(--line); border-radius:7px; background:#fff; padding:7px; display:grid; grid-template-columns:auto 1fr; gap:6px; align-items:center; }}
.set-card.hot,.set-card.answer {{ border-color:#16a34a; background:#f0fdf4; }}
.set-index {{ min-width:24px; height:24px; border-radius:999px; border:1px solid #cbd5e1; background:#f8fafc; color:#64748b; display:grid; place-items:center; font-size:11px; font-weight:700; }}
.set-values {{ display:flex; flex-wrap:wrap; gap:4px; align-items:center; min-width:0; }}
.set-token {{ min-width:26px; min-height:24px; border:1px solid #bfdbfe; border-radius:6px; background:#eff6ff; color:#1d4ed8; display:grid; place-items:center; padding:2px 6px; font-size:12px; font-weight:700; }}
.set-empty {{ color:#94a3b8; font-size:12px; font-weight:700; }}
.cell.pattern-string-window {{ border-color:#f59e0b; background:#fffbeb; }}
.cell.pattern-string-alignment.role-cursor {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.stack {{ width:min(360px,100%); display:flex; flex-direction:column-reverse; gap:6px; }}
.queue {{ max-width:100%; display:flex; flex-wrap:wrap; gap:8px; align-items:center; }}
.stack-item {{ border:1px solid var(--line); border-radius:6px; padding:9px 10px; background:#fff; }}
.mapgrid {{ display:grid; gap:6px; }}
.maprow {{ display:grid; grid-template-columns:minmax(80px,130px) 1fr; gap:8px; align-items:start; border:1px solid var(--line); border-radius:6px; padding:7px 8px; background:#fff; }}
.graph-svg {{ width:100%; height:clamp(300px,42vh,380px); border:1px solid var(--line); border-radius:8px; background:#fbfdff; }}
.edge {{ stroke:#b8c1d1; stroke-width:1.6; }}
.edge.matching-edge,.edge.accepted-edge {{ stroke:#16a34a; stroke-width:4; }}
.edge.rejected-edge {{ stroke:#dc2626; stroke-width:3; stroke-dasharray:6 5; }}
.node circle {{ fill:#fff; stroke:#94a3b8; stroke-width:2; }}
.node.hot circle {{ fill:#dbeafe; stroke:var(--blue); stroke-width:3; }}
.node.dep circle {{ fill:#fffbeb; stroke:var(--amber); }}
.node.answer circle {{ fill:#dcfce7; stroke:var(--green); }}
.node.role-answer circle,.node.pattern-answer-projection circle {{ fill:#dcfce7; stroke:var(--green); stroke-width:3; }}
.node.pattern-graph-frontier circle {{ stroke:#0f766e; stroke-width:3; }}
.node.pattern-graph-path-highlight circle,.node.pattern-backtracking-choice circle {{ stroke:#16a34a; stroke-width:3; }}
.node.pattern-backtracking-undo circle {{ stroke:#dc2626; stroke-dasharray:4 3; }}
.edge.hot,.edge.dep,.edge.pattern-graph-relax-edge {{ stroke:#f59e0b; stroke-width:3; }}
.edge.answer,.edge.pattern-graph-path-highlight,.edge.pattern-network-flow-augmenting-path {{ stroke:#16a34a; stroke-width:3; }}
.edge.role-answer,.edge.pattern-answer-projection {{ stroke:#16a34a; stroke-width:3.2; }}
.edge.pattern-network-flow-edge-label {{ stroke:#2563eb; stroke-width:2.4; }}
.edge-label {{ fill:#334155; font-size:12px; font-weight:700; paint-order:stroke; stroke:#fff; stroke-width:3px; }}
.flow-bottleneck-label rect {{ fill:#f0fdf4; stroke:#16a34a; stroke-width:1.2; rx:7; }}
.flow-bottleneck-label text {{ fill:#166534; font-size:11px; font-weight:800; paint-order:stroke; stroke:#fff; stroke-width:2px; }}
.return-bubble rect {{ fill:#f0fdf4; stroke:#16a34a; stroke-width:1.2; rx:7; }}
.return-bubble text {{ fill:#166534; font-size:11px; font-weight:700; }}
.tree-svg,.geometry-svg {{ width:100%; height:clamp(300px,42vh,380px); border:1px solid var(--line); border-radius:8px; background:#fbfdff; }}
.geo-axis {{ stroke:#e5e7eb; stroke-width:1; }}
.geo-segment {{ stroke:#64748b; stroke-width:2; fill:none; }}
.geo-hull {{ stroke:#16a34a; stroke-width:2.4; fill:none; }}
.geo-sweep {{ stroke:#dc2626; stroke-width:2; stroke-dasharray:6 5; }}
.geo-candidate-point circle {{ fill:#dbeafe; stroke:#2563eb; stroke-width:3; r:10; }}
.geo-hull-ghost-svg circle {{ fill:#f8fafc; stroke:#94a3b8; stroke-width:2; stroke-dasharray:4 3; opacity:.82; }}
.geo-cross-vector {{ stroke:#dc2626; stroke-width:2.4; marker-end:url(#geo-arrowhead); }}
.geo-cross-label {{ fill:#b91c1c; font-size:12px; font-weight:800; paint-order:stroke; stroke:#fff; stroke-width:3px; }}
.heap {{ display:grid; gap:10px; justify-items:center; width:fit-content; max-width:100%; }}
.heap-level {{ display:flex; gap:8px; justify-content:center; }}
.linked-list-view {{ display:flex; align-items:center; gap:8px; min-width:max-content; padding:8px 2px 16px; }}
.linked-node-wrap {{ display:grid; justify-items:center; gap:5px; }}
.pointer-badges {{ min-height:22px; display:flex; flex-wrap:wrap; gap:4px; justify-content:center; }}
.pointer-badge {{ border:1px solid #bfdbfe; border-radius:999px; background:#eff6ff; color:#1d4ed8; padding:1px 6px; font-size:11px; font-weight:700; }}
.linked-node {{ min-width:54px; min-height:42px; border:1px solid var(--line); border-radius:7px; background:#fff; display:grid; place-items:center; font-weight:700; padding:4px 8px; }}
.linked-arrow {{ color:#64748b; font-size:18px; font-weight:800; }}
.linked-arrow.ghost {{ color:#dc2626; text-decoration:line-through; opacity:.78; }}
.linked-arrow.cycle {{ color:#7c3aed; }}
.cycle-list-svg {{ width:100%; height:clamp(300px,42vh,380px); border:1px solid var(--line); border-radius:8px; background:#fbfdff; }}
.cycle-edge {{ stroke:#64748b; stroke-width:2.2; fill:none; marker-end:url(#cycle-arrowhead); }}
.cycle-edge.cycle {{ stroke:#7c3aed; stroke-width:3; stroke-dasharray:7 5; }}
.cycle-node circle {{ fill:#fff; stroke:#94a3b8; stroke-width:2.4; }}
.cycle-node.hot circle {{ fill:#dbeafe; stroke:#2563eb; stroke-width:3.2; }}
.cycle-token {{ fill:#1d4ed8; font-size:11px; font-weight:800; paint-order:stroke; stroke:#fff; stroke-width:3px; }}
.math-bit-panel {{ border:1px solid #dbeafe; border-radius:7px; background:#eff6ff; padding:9px 10px; display:grid; gap:8px; }}
.math-bit-panel h3 {{ margin:0; color:#1e3a8a; font-size:12px; }}
.math-bit-grid {{ display:grid; gap:7px; }}
.gcd-chain,.fast-power-row {{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; color:#172033; font-size:12px; }}
.math-token {{ border:1px solid #bfdbfe; border-radius:999px; background:#fff; color:#1d4ed8; padding:2px 8px; font-weight:700; }}
.gcd-hero {{ width:min(760px,82vw); min-height:260px; display:grid; align-content:center; gap:14px; border:1px solid #bfdbfe; border-radius:8px; background:#f8fbff; padding:22px; }}
.gcd-formula-line {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:24px; font-weight:800; color:#172033; }}
.gcd-formula-line .remainder {{ border:2px solid #f59e0b; background:#fffbeb; color:#92400e; border-radius:8px; padding:2px 8px; }}
.gcd-transition {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; color:#1e3a8a; font-size:15px; font-weight:750; }}
.gcd-backsub {{ border:1px solid #c7d2fe; border-radius:7px; background:#eef2ff; color:#312e81; padding:8px 10px; font-size:13px; line-height:1.4; }}
.bit-row {{ display:grid; grid-template-columns:64px 1fr; gap:7px; align-items:center; color:#172033; font-size:12px; }}
.bit-cells {{ display:flex; gap:3px; }}
.bit-cell {{ width:22px; height:24px; border:1px solid #cbd5e1; border-radius:5px; background:#fff; display:grid; place-items:center; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; font-weight:700; }}
.bit-cell.on {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.sieve-grid {{ display:flex; flex-wrap:wrap; gap:5px; }}
.sieve-num {{ width:30px; height:28px; border:1px solid #cbd5e1; border-radius:6px; background:#fff; display:grid; place-items:center; font-size:12px; font-weight:700; }}
.sieve-num.prime {{ border-color:#16a34a; background:#f0fdf4; color:#166534; }}
.sieve-num.composite {{ color:#94a3b8; text-decoration:line-through; background:#f8fafc; }}
.dependency-flow {{ display:grid; gap:7px; margin-top:10px; max-width:100%; min-width:0; border:1px solid #fed7aa; border-radius:7px; background:#fff7ed; padding:9px 10px; }}
.dependency-flow h3 {{ margin:0; color:#9a3412; font-size:12px; letter-spacing:0; }}
.dependency-edge {{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; min-width:0; color:#7c2d12; font-size:12px; line-height:1.45; overflow-wrap:anywhere; }}
.dependency-node {{ min-width:0; max-width:100%; border:1px solid var(--line); border-radius:999px; padding:2px 8px; background:#fff; color:#172033; overflow-wrap:anywhere; }}
.dependency-node.dep {{ border-color:#fcd34d; background:#fffbeb; color:#92400e; }}
.dependency-node.target {{ border-color:#86efac; background:#f0fdf4; color:#166534; }}
.dependency-arrow {{ color:#c2410c; font-weight:700; }}
.dependency-detail {{ border:1px solid #c7d2fe; border-radius:7px; background:#eef2ff; color:#312e81; padding:9px 10px; font-size:12px; line-height:1.45; overflow-wrap:anywhere; }}
.dependency-detail strong {{ display:block; margin-bottom:5px; color:#1e1b4b; font-size:12px; }}
.dependency-detail p {{ margin:3px 0; }}
.visual-patterns {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr)); gap:8px; margin-top:10px; min-width:0; }}
.visual-card {{ border:1px solid #dbeafe; border-radius:7px; background:#eff6ff; padding:9px 10px; color:#172033; font-size:12px; line-height:1.45; overflow-wrap:anywhere; }}
.visual-card strong {{ display:block; margin-bottom:5px; color:#1e3a8a; font-size:12px; }}
.visual-card code {{ display:block; margin-top:4px; color:#1e3a8a; white-space:pre-wrap; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; }}
.visual-chip-row {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:5px; }}
.visual-chip {{ border:1px solid #bfdbfe; border-radius:999px; background:#fff; padding:2px 7px; color:#1d4ed8; font-size:11px; }}
.binary-pointer-panel,.digit-dp-card,.monotonic-stack-panel,.heap-sift-panel,.graph-metric-overlay,.tree-dp-overlay,.dp-dependency-window,.string-specialized-card,.fenwick-lowbit-panel,.sparse-table-blocks,.diff-prefix-panel,.geometry-relation-card,.network-augmenting-path-panel {{ background:#f8fafc; border-color:#cbd5e1; }}
.dp-window-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(72px,1fr)); gap:6px; margin-top:6px; }}
.dp-window-cell {{ min-height:38px; border:1px solid #d7deea; border-radius:6px; background:#fff; display:grid; gap:2px; place-items:center; font-size:11px; font-weight:700; }}
.dp-current-cell {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.dp-dependency-arrow {{ display:inline-flex; align-items:center; gap:4px; color:#92400e; font-weight:700; }}
.string-specialized-tracks,.range-hop-row,.sparse-block-row,.diff-impact-row,.augmenting-path-chain,.flow-delta-row {{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin-top:6px; }}
.string-track {{ border:1px solid #bfdbfe; border-radius:7px; background:#fff; padding:5px 7px; display:grid; gap:3px; min-width:110px; }}
.kmp-fallback-arc,.rolling-hash-track,.z-box-band,.manacher-radius-arc {{ border:1px solid #fed7aa; border-radius:999px; background:#fff7ed; color:#9a3412; padding:5px 10px; font-size:12px; font-weight:800; }}
.z-box-band {{ border-color:#fb923c; background:#ffedd5; }}
.manacher-radius-arc {{ border-color:#c084fc; background:#f5f3ff; color:#6d28d9; }}
.fenwick-hop-arrow,.sparse-query-block,.diff-impact-point,.flow-delta-pill {{ border:1px solid #bfdbfe; border-radius:999px; background:#fff; color:#1d4ed8; padding:3px 8px; font-size:11px; font-weight:700; }}
.geometry-relation-row {{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin-top:6px; }}
.cross-turn-badge {{ border:1px solid #fecaca; border-radius:999px; background:#fef2f2; color:#b91c1c; padding:3px 8px; font-size:11px; font-weight:700; }}
.geo-cross-arrow {{ color:#dc2626; font-weight:800; }}
.hull-ghost-point {{ border:1px dashed #94a3b8; border-radius:999px; background:#f8fafc; color:#64748b; padding:3px 8px; font-size:11px; }}
.bottleneck-badge {{ border:1px solid #86efac; border-radius:999px; background:#f0fdf4; color:#166534; padding:3px 8px; font-size:11px; font-weight:700; }}
.graph-node-inline-metrics {{ fill:#475569; font-size:10px; font-weight:700; paint-order:stroke; stroke:#fff; stroke-width:3px; }}
.visual-quality-telemetry {{ display:none; border:1px dashed #cbd5e1; border-radius:7px; background:#fff; color:#64748b; padding:6px 8px; font-size:11px; flex-wrap:wrap; gap:6px; }}
.visual-quality-telemetry .visual-chip {{ color:#475569; border-color:#d7deea; background:#f8fafc; }}
.pointer-track {{ display:grid; grid-template-columns:repeat(var(--slot-count, 8), minmax(30px,1fr)); gap:4px; margin-top:6px; align-items:end; }}
.pointer-slot-cell {{ min-height:46px; border:1px solid #d7deea; border-radius:6px; background:#fff; display:grid; grid-template-rows:1fr auto; place-items:center; font-size:11px; font-weight:700; color:#334155; position:relative; overflow:hidden; }}
.pointer-slot-cell.excluded {{ background:#f1f5f9; color:#94a3b8; }}
.pointer-slot-cell.in-range {{ border-color:#bfdbfe; background:#eff6ff; }}
.search-interval-band {{ grid-column:span var(--slot-count, 8); height:8px; border-radius:999px; background:linear-gradient(90deg,#dcfce7,#dbeafe,#f5f3ff); border:1px solid #bfdbfe; }}
.pointer-marker-row {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:6px; }}
.pointer-marker {{ border:1px solid #bfdbfe; border-radius:999px; background:#fff; padding:2px 7px; font-size:11px; font-weight:700; }}
.marker-low {{ border-color:#86efac; color:#166534; background:#f0fdf4; }}
.marker-mid {{ border-color:#93c5fd; color:#1d4ed8; background:#eff6ff; }}
.marker-high {{ border-color:#c4b5fd; color:#6d28d9; background:#f5f3ff; }}
.digit-dp-state {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(86px,1fr)); gap:6px; margin-top:6px; }}
.digit-dp-pill {{ border:1px solid #bfdbfe; border-radius:7px; background:#fff; padding:6px 7px; display:grid; gap:2px; }}
.digit-dp-pill span {{ color:#64748b; font-size:10px; text-transform:uppercase; }}
.digit-dp-pill strong {{ color:#1e3a8a; font-size:13px; }}
.digit-row {{ display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }}
.digit-cell {{ width:28px; height:28px; border:1px solid #cbd5e1; border-radius:6px; background:#fff; display:grid; place-items:center; font-weight:700; }}
.digit-cell.hot {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.mono-layout {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(92px,150px); gap:8px; align-items:start; }}
.mono-array {{ display:flex; flex-wrap:wrap; gap:5px; }}
.mono-cell {{ min-width:32px; min-height:34px; border:1px solid #d7deea; border-radius:6px; background:#fff; display:grid; place-items:center; font-weight:700; position:relative; }}
.mono-cell.current {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.mono-stack {{ display:grid; gap:4px; align-content:end; }}
.mono-stack-item {{ border:1px solid #fcd34d; border-radius:6px; background:#fffbeb; padding:4px 6px; font-size:11px; color:#92400e; }}
.stack-pop-arrow {{ margin-top:6px; color:#c2410c; font-weight:700; font-size:12px; }}
.heap-sift-row {{ display:flex; flex-wrap:wrap; align-items:center; gap:5px; margin-top:6px; }}
.heap-sift-node {{ min-width:30px; min-height:30px; border:1px solid #cbd5e1; border-radius:999px; background:#fff; display:grid; place-items:center; font-size:12px; font-weight:700; }}
.heap-sift-path {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.heap-svg {{ width:100%; height:clamp(300px,42vh,380px); border:1px solid var(--line); border-radius:8px; background:#fbfdff; }}
.heap-edge {{ stroke:#94a3b8; stroke-width:2; }}
.heap-edge.heap-sift-path {{ stroke:#2563eb; stroke-width:3.2; }}
.heap-node circle {{ fill:#fff; stroke:#94a3b8; stroke-width:2.4; }}
.heap-node.hot circle,.heap-node.heap-sift-path circle {{ fill:#dbeafe; stroke:#2563eb; stroke-width:3.2; }}
.kruskal-edge-track,.backtracking-track,.bitmask-transition-track {{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin-top:6px; }}
.kruskal-edge-pill,.backtracking-pill,.bitmask-pill {{ border:1px solid #cbd5e1; border-radius:999px; background:#fff; color:#334155; padding:4px 8px; font-size:11px; font-weight:750; }}
.kruskal-edge-pill.current {{ border-color:#93c5fd; background:#eff6ff; color:#1d4ed8; }}
.kruskal-edge-pill.accept {{ border-color:#86efac; background:#f0fdf4; color:#166534; }}
.kruskal-edge-pill.reject {{ border-color:#fecaca; background:#fef2f2; color:#991b1b; }}
.graph-metric-grid,.tree-dp-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(92px,1fr)); gap:5px; margin-top:6px; }}
.graph-node-metric,.tree-dp-badge {{ border:1px solid #d7deea; border-radius:7px; background:#fff; padding:5px 6px; font-size:11px; line-height:1.35; }}
.graph-node-metric strong,.tree-dp-badge strong {{ display:block; color:#172033; font-size:12px; margin:0 0 2px; }}
.relax-formula {{ margin-top:6px; border:1px solid #fed7aa; border-radius:7px; background:#fff7ed; color:#9a3412; padding:6px 7px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; overflow-wrap:anywhere; }}
.frontier-dock {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:6px; }}
.frontier-dock .visual-chip {{ border-color:#99f6e4; color:#0f766e; background:#f0fdfa; }}
.string-alignment {{ display:grid; gap:4px; overflow-x:auto; padding-bottom:2px; }}
.string-row {{ display:flex; gap:4px; align-items:center; min-height:28px; }}
.string-row-label {{ width:52px; flex:0 0 52px; color:#475569; font-weight:700; }}
.visual-char {{ width:26px; height:24px; border:1px solid #cbd5e1; border-radius:5px; background:#fff; display:grid; place-items:center; font-weight:700; }}
.visual-char.window {{ border-color:#f59e0b; background:#fffbeb; }}
.visual-char.cursor {{ border-color:#2563eb; background:#dbeafe; color:#1d4ed8; }}
.clickable-object {{ cursor:pointer; }}
.clickable-object:hover {{ outline:2px solid #60a5fa; outline-offset:1px; }}
.code-panel {{ padding:9px; }}
.code-panel h2 {{ margin-bottom:7px; }}
.code {{ background:#101827; color:#dbeafe; border-radius:7px; overflow:visible; }}
.code pre {{ overflow:visible; }}
.code-sync {{ display:flex; align-items:center; gap:8px; padding:5px 9px; border-bottom:1px solid rgba(148,163,184,.25); background:#0f172a; color:#bfdbfe; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; line-height:1.3; }}
.code-sync.ok {{ color:#bbf7d0; }}
.code-sync.warn {{ color:#fde68a; background:#1f2937; }}
.line {{ display:grid; grid-template-columns:42px 1fr; gap:10px; padding:1px 10px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; line-height:1.55; }}
.lineno {{ color:#7f8ea3; text-align:right; }}
.line.active {{ background:#1d4ed8; color:#fff; }}
.line.fallback {{ background:#1f2937; color:#cbd5e1; }}
.line.fallback .lineno {{ color:#fde68a; }}
.state-grid {{ display:grid; gap:6px; overflow:visible; padding-right:2px; }}
.state-row {{ border:1px solid var(--line); border-radius:6px; padding:8px; background:#fff; }}
.state-row strong {{ display:block; margin-bottom:4px; color:#374151; font-size:12px; }}
.state-row code {{ display:block; color:#172033; overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; line-height:1.35; }}
.interaction {{ border-left:3px solid var(--violet); background:#f5f3ff; padding:10px; border-radius:6px; }}
.interaction button {{ display:block; width:100%; margin:6px 0; border:1px solid #ddd6fe; background:#fff; border-radius:6px; padding:8px; text-align:left; cursor:pointer; }}
.feedback {{ margin-top:8px; color:#4c1d95; font-size:13px; }}
.feedback.correct {{ color:#166534; }}
.feedback.wrong {{ color:#991b1b; }}
.feedback-source {{ display:block; margin-top:4px; color:var(--muted); font-size:11px; }}
.teaching {{ display:grid; gap:6px; overflow:visible; padding-right:2px; }}
.teach-row {{ border:1px solid var(--line); border-radius:6px; padding:8px; background:#fff; }}
.teach-row.formula {{ border-color:#bfdbfe; background:#eff6ff; }}
.teach-row.invariant {{ border-color:#bbf7d0; background:#f0fdf4; }}
.teach-row.common_mistake {{ border-color:#fecaca; background:#fef2f2; }}
.teach-row.hint {{ border-color:#ddd6fe; background:#f5f3ff; }}
.teach-row strong {{ display:block; margin-bottom:4px; color:#374151; font-size:12px; }}
.teach-row p {{ margin:0; color:#172033; font-size:13px; line-height:1.45; }}
.teach-row code {{ display:block; color:#1e3a8a; white-space:pre-wrap; overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; line-height:1.45; }}
.formula-expander summary {{ cursor:pointer; display:flex; align-items:center; justify-content:space-between; gap:8px; list-style:none; }}
.formula-expander summary::-webkit-details-marker {{ display:none; }}
.formula-expander summary span {{ border:1px solid #bfdbfe; border-radius:999px; background:#fff; color:#1d4ed8; padding:2px 7px; font-size:11px; }}
.formula-expansion {{ display:grid; gap:5px; margin-top:7px; }}
.formula-expansion-row {{ display:grid; grid-template-columns:minmax(74px,110px) minmax(0,1fr); gap:7px; align-items:start; color:#172033; font-size:12px; line-height:1.4; }}
.formula-expansion-row span:first-child {{ color:#475569; font-weight:700; }}
.formula-expansion-row code {{ color:#1e3a8a; }}
.change-summary {{ border:1px solid #bbf7d0; border-radius:6px; padding:8px; background:#f0fdf4; }}
.change-summary strong {{ display:block; margin-bottom:5px; color:#166534; font-size:12px; }}
.change-row {{ display:grid; gap:3px; padding:5px 0; border-top:1px solid #dcfce7; font-size:12px; line-height:1.4; }}
.change-row:first-of-type {{ border-top:0; padding-top:0; }}
.change-row code {{ overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; color:#14532d; }}
.evidence,.step-evidence {{ display:grid; gap:6px; overflow:visible; padding-right:2px; }}
.evidence-block {{ border:1px solid var(--line); border-radius:6px; padding:7px; background:#fff; min-width:0; }}
.evidence-block strong {{ display:block; margin-bottom:5px; color:#374151; font-size:12px; }}
.evidence-line {{ display:grid; grid-template-columns:minmax(82px,120px) minmax(0,1fr); gap:8px; align-items:start; padding:3px 0; font-size:12px; line-height:1.4; }}
.evidence-line span:first-child {{ color:var(--muted); }}
.evidence-line code,.diff-row code {{ overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; }}
.evidence-list {{ margin:0; padding-left:17px; color:#172033; font-size:12px; line-height:1.45; }}
.evidence-list li {{ margin:3px 0; }}
.status-line {{ display:grid; gap:6px; }}
.status-item {{ display:flex; align-items:center; gap:7px; color:#172033; font-size:12px; line-height:1.4; }}
.status-dot {{ width:8px; height:8px; border-radius:999px; background:#d97706; flex:0 0 auto; }}
.status-item.ok .status-dot {{ background:#16a34a; }}
.status-item.warn .status-dot {{ background:#d97706; }}
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
.debug-drawer {{ border-top:1px solid var(--line); background:#eef2f7; padding:0 10px 10px; }}
.debug-drawer summary {{ list-style:none; display:flex; gap:12px; align-items:baseline; padding:12px 4px; cursor:pointer; color:#172033; }}
.debug-drawer summary::-webkit-details-marker {{ display:none; }}
.debug-drawer summary span {{ font-weight:700; }}
.debug-drawer summary small {{ color:var(--muted); }}
.debug-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
.debug-json {{ max-height:260px; }}
.debug-download {{ display:inline-block; margin:0 0 8px; color:#1d4ed8; font-size:12px; text-decoration:none; }}
.debug-download:hover {{ text-decoration:underline; }}
.compact-details {{ margin-top:8px; }}
.compact-details summary {{ list-style:none; display:flex; align-items:center; justify-content:space-between; gap:8px; cursor:pointer; color:#374151; font-size:12px; font-weight:700; }}
.compact-details summary::-webkit-details-marker {{ display:none; }}
.compact-details summary::after {{ content:'展开'; border:1px solid var(--line); border-radius:999px; padding:1px 6px; color:var(--muted); background:#fff; font-size:11px; font-weight:500; }}
.compact-details[open] summary::after {{ content:'收起'; }}
.compact-details > :not(summary) {{ margin-top:7px; }}
@media (max-width:1100px) {{
  .workspace {{ grid-template-columns:1fr; }}
  .topbar {{ grid-template-columns:1fr; }}
  .badges {{ justify-content:flex-start; }}
  .debug-grid {{ grid-template-columns:1fr; }}
  .task-col {{ max-height:360px; overflow:auto; padding-right:2px; }}
  .teaching-col {{ max-height:none; overflow:visible; padding-right:2px; }}
}}
@media (max-width:560px) {{
  .topbar,.workspace {{ padding:10px; }}
  .top-summary {{ grid-template-columns:1fr; }}
  .hero {{ min-height:0; grid-template-rows:auto minmax(300px,380px) auto auto; }}
  .canvas {{ height:380px; max-height:none; min-height:300px; }}
  .spatial-stage {{ height:280px; }}
  .controls {{ grid-template-columns:repeat(3,1fr); }}
  .controls .range {{ grid-column:1 / -1; }}
  .counter {{ grid-column:1 / -1; text-align:left; min-width:0; }}
  .controls button {{ min-width:0; padding:8px 6px; }}
  .maprow,.evidence-line {{ grid-template-columns:1fr; }}
}}
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
const VIEW_STATE = {{ scale:1, x:0, y:0, userPan:false, auto:null, boundFit:null, drag:null }};
window.SPATIAL_STATE = SPATIAL_STATE;
window.VIEW_STATE = VIEW_STATE;
const $ = id => document.getElementById(id);
const setText = (id, value) => {{ const node = $(id); if (node) node.textContent = value; }};
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const pretty = x => JSON.stringify(x, null, 2);
const sceneIds = () => Object.keys(ARTIFACT.scenes || {{}});
const variant = () => ARTIFACT.variants[variantIndex];
const scene = () => ARTIFACT.scenes[variant().id];
const frames = () => scene().frames || [];
const frame = () => frames()[stepIndex];
const isSpatialTarget = () => RUNTIME_TARGET === 'spatial_3d' || RUNTIME_TARGET === 'hybrid_2_5d';

function boot() {{
  setText('title', ARTIFACT.problem_title || '算法可视化实验');
  setText('subtitle', ARTIFACT.input_contract || '由语义轨迹编译生成，页面只渲染 scene graph');
  setText('debug-artifact', pretty(ARTIFACT));
  const artifactDownload = $('debug-artifact-download');
  if (artifactDownload) artifactDownload.href = `data:application/json;charset=utf-8,${{encodeURIComponent(pretty(ARTIFACT))}}`;
  renderBadges();
  renderEvidence();
  renderTabs();
  renderVariantCompare();
  selectVariant(0);
}}
function renderBadges() {{
  const g = ARTIFACT.validation.release_gate || {{}};
  const items = [
    ['代码执行通过', g.artifact_ready],
    ['轨迹覆盖完整', g.trace_ready],
    ['过程转移通过校验', g.process_ready],
    ['可视化对象绑定正确', g.visual_ready],
  ];
  $('badges').innerHTML = items.map(([k,v]) => `<span class="badge ${{v?'ok':'warn'}}">${{k}}：${{v?'通过':'待检查'}}</span>`).join('');
}}
function renderTabs() {{
  $('tabs').innerHTML = ARTIFACT.variants.map((v,i) => `<button class="tab ${{i===variantIndex?'active':''}}" onclick="selectVariant(${{i}})"><strong>${{esc(v.name)}}</strong><span>${{esc(v.time_complexity)}} · ${{esc(v.space_complexity)}}<br>${{esc(v.strategy)}}</span></button>`).join('');
}}
function renderVariantCompare() {{
  const node = $('variant-compare');
  if (!node) return;
  const variants = ARTIFACT.variants || [];
  if (variants.length < 2) {{
    node.innerHTML = '<p style="color:var(--muted);margin:0;font-size:12px;">当前 artifact 只有一个解法，无需对比。</p>';
    return;
  }}
  const baseline = variants[0] || {{}};
  node.innerHTML = variants.map((v, i) => {{
    const sceneForVariant = ARTIFACT.scenes && ARTIFACT.scenes[v.id] || {{}};
    const sceneFrames = sceneForVariant.frames || [];
    const stepCount = sceneFrames.length;
    const keyStepCount = sceneFrames.filter(isKeyCompareFrame).length || stepCount;
    const consistent = stableJson(v.result) === stableJson(baseline.result);
    return `<article class="variant-compare-card ${{i === variantIndex ? 'active' : ''}}" data-variant-id="${{esc(v.id)}}" data-scene-id="${{esc(v.id)}}" data-step-count="${{stepCount}}" data-key-step-count="${{keyStepCount}}"><strong>${{esc(v.name || v.id)}}</strong><div class="variant-compare-meta"><span>复杂度：${{esc(v.time_complexity || '未标注')}} / ${{esc(v.space_complexity || '未标注')}}</span><span>关键步骤数：${{keyStepCount}} / ${{stepCount}}</span><span>SceneGraph：${{esc(v.id)}}</span></div><span class="variant-compare-status ${{consistent ? '' : 'warn'}}">结果一致性：${{consistent ? '一致' : '不一致'}} · ${{esc(compactValue(v.result))}}</span><button type="button" onclick="selectVariant(${{i}})">查看这个解法</button></article>`;
  }}).join('');
}}
function isKeyCompareFrame(f) {{
  const evidence = f && f.evidence || {{}};
  const timeline = evidence.timeline || {{}};
  if (timeline.keyframe) return true;
  const op = textOrEmpty(evidence.operation || f && f.operation);
  return ['set','mark','move','compare','push','pop','enter','exit'].includes(op);
}}
function selectVariant(i) {{
  variantIndex = i; stepIndex = 0; stop();
  renderTabs();
  renderVariantCompare();
  $('top-result').textContent = compactValue(variant().result);
  $('top-solution').textContent = `${{variant().name || variant().id}} · ${{variant().time_complexity || '复杂度未标注'}}`;
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
  $('step-title').textContent = frameTitle(f);
  $('step-desc').textContent = frameDescription(f);
  $('op').textContent = frameOperation(f);
  $('counter').textContent = `${{stepIndex + 1}} / ${{frames().length}}`;
  $('range').value = stepIndex;
  renderCanvas(f);
  renderState(f.state || {{}});
  renderDebugState(f.state || {{}});
  renderTeaching(f);
  renderStepEvidence(f);
  renderInteraction(f.interaction);
  const code = variant().code || '';
  renderCode(code, codeLineInfo(f, code));
  renderTimeline();
}}
function frameTitle(f) {{
  return textOrEmpty(f && f.title) || frameOperation(f) || `步骤 ${{stepIndex + 1}}`;
}}
function frameDescription(f) {{
  return textOrEmpty(f && f.description);
}}
function frameOperation(f) {{
  return textOrEmpty(f && f.operation) || 'explain';
}}
function frameCodeLine(f) {{
  const value = Number(f && f.code_line);
  return Number.isInteger(value) && value > 0 ? value : 1;
}}
function codeLineInfo(f, code) {{
  const lines = String(code || '').split('\\n');
  const lineCount = Math.max(1, lines.length);
  const raw = Number(f && f.code_line);
  if (Number.isInteger(raw) && raw > 0 && raw <= lineCount) {{
    return {{ active: raw, label: `当前代码行：第 ${{raw}} 行`, status: 'ok', raw }};
  }}
  if (Number.isInteger(raw) && raw > 0) {{
    const active = Math.min(Math.max(raw, 1), lineCount);
    return {{ active, label: `当前代码行：code_line 越界（${{raw}}），已降级到第 ${{active}} 行`, status: 'warn', raw }};
  }}
  return {{ active: 1, label: '当前代码行：缺失或无效 code_line，已降级到第 1 行', status: 'warn', raw: null }};
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
  const classified = classifyStageContainers(f, containers);
  const fitMode = fitModeForFrame(f, classified.primary);
  const familyRenderer = familyRendererForFrame(f, classified);
  let html = `<div class="stage-grid" data-family-renderer="${{esc(familyRenderer)}}" data-visual-quality="${{esc(familyRenderer)}}" data-raw-state-not-primary="${{classified.raw.length ? 'raw_state_not_primary' : 'none'}}" data-teaching-relation="${{dependencyEdges(f).length || (f.evidence && (f.evidence.process || (f.evidence.visual_patterns || []).length)) ? 'teaching_relation_visible' : 'none'}}">`;
  html += `<div class="scene-fit"><div class="view-tools" aria-label="主视图控制"><button type="button" onclick="resetSceneView()">适配</button><button type="button" onclick="zoomSceneToOne()">100%</button></div><div class="scene-scroll-surface"><div class="objects scene-world primary-scene ${{classified.primary.length > 1 ? 'compound-scene' : ''}}" data-primitive-count="${{classified.primary.length}}" data-fit-mode="${{esc(fitMode)}}">`;
  html += renderPrimaryStage(classified.primary, groups, f.marks || [], f.objects || []);
  html += '</div></div></div>';
  html += '<div class="stage-supplement">';
  html += renderMathBitPanel(f);
  html += renderVisualPatternPanel(f);
  html += renderVisualQualityTelemetry(f, classified);
  html += renderDependencyFlow(f);
  html += renderSupportDock(classified.support, groups, f.marks || []);
  html += renderRawStateDock(classified.raw, groups, f.marks || []);
  html += '<div id="dependency-detail" class="dependency-detail">点击当前对象或依赖对象，查看它依赖谁、影响谁。</div>';
  html += '</div>';
  html += '</div>';
  $('canvas').innerHTML = html;
  fitSceneToCanvas();
}}
function familyRendererForFrame(f, classified) {{
  const layouts = new Set((classified && classified.primary || []).map(c => String(c && c.meta && c.meta.layout || 'generic')));
  const state = f && f.state || {{}};
  const familyHint = visualFamilyHint(f);
  if (familyHint) return familyHint;
  const patterns = new Set((f && f.evidence && f.evidence.visual_patterns || []).map(item => String(item && item.pattern || item)).filter(Boolean));
  for (const obj of f && f.objects || []) for (const pattern of objectPatterns(obj)) patterns.add(pattern);
  if (patterns.has('network_flow_augmenting_path') || patterns.has('network_flow_edge_label') || state.augmenting_path) return 'network_flow';
  if (layouts.has('geometry')) return 'geometry';
  if (state.mask !== undefined || state.next_mask !== undefined || state.state_mask !== undefined || state.visited_mask !== undefined) return 'bitmask_dp';
  if (state.sorted_edges || state.mst_edges || state.accepted_edges || state.rejected_edges) return 'kruskal';
  if (patterns.has('range_query_path') || patterns.has('range_update_path') || state.query_path || state.update_path) return 'range_structure';
  if (layouts.has('trie')) return 'trie';
  if (layouts.has('graph')) return 'graph';
  if (layouts.has('tree') || layouts.has('recursion_tree')) return treeDpNodeValues(state).length ? 'tree_dp' : 'tree';
  if (state.tight !== undefined || state.memo_hit !== undefined || state.memo_key !== undefined) return 'digit_dp';
  if (layouts.has('set_grid')) return 'math_bit';
  if (layouts.has('matrix')) return 'dp_matrix';
  if (layouts.has('string') || layouts.has('string_list')) return 'string_specialized';
  if (layouts.has('linked_list')) return 'linked_list';
  if (Array.isArray(state.stack) || Array.isArray(state.monotonic_stack)) return 'monotonic_stack';
  if (Array.isArray(state.heap) || Array.isArray(state.min_heap) || Array.isArray(state.max_heap) || Array.isArray(state.priority_queue)) return 'heap';
  return Array.from(layouts).filter(Boolean).join('+') || 'generic';
}}
function renderVisualQualityTelemetry(f, classified) {{
  const family = familyRendererForFrame(f, classified);
  const primaryCount = classified && classified.primary ? classified.primary.length : 0;
  const supportCount = classified && classified.support ? classified.support.length : 0;
  const rawCount = classified && classified.raw ? classified.raw.length : 0;
  const hasTarget = !!((f && f.evidence && f.evidence.targets || []).length || (f && f.marks || []).some(m => m.role !== 'dependency'));
  const hasRelation = dependencyEdges(f).length || !!(f && f.evidence && (f.evidence.process || (f.evidence.visual_patterns || []).length));
  const chips = [
    visualChip(`family_renderer=${{family}}`),
    visualChip(`primary=${{primaryCount}}`),
    visualChip(`support=${{supportCount}}`),
    visualChip(`raw_dock=${{rawCount}}`),
    visualChip(`active_target=${{hasTarget ? 'visible_or_pending' : 'none'}}`),
    visualChip(`teaching_relation=${{hasRelation ? 'visible' : 'none'}}`),
    visualChip('fit_mode=pending'),
    visualChip('fit_scale=pending'),
    visualChip('utilization=pending'),
  ].join('');
  return `<section id="visual-quality-telemetry" class="visual-quality-telemetry" data-visual-quality="visual_quality" data-family-renderer="${{esc(family)}}">${{chips}}</section>`;
}}
function classifyStageContainers(f, containers) {{
  const rows = (containers || []).map(c => ({{ container:c, role:stageRoleForContainer(f, c) }}));
  let primary = rows.filter(item => item.role === 'primary').map(item => item.container);
  const support = rows.filter(item => item.role === 'support').map(item => item.container);
  const raw = rows.filter(item => item.role === 'raw').map(item => item.container);
  if (primary.length > 1) {{
    const demoted = primary.filter(c => isSecondaryPrimaryContainer(f, c, primary));
    if (demoted.length && primary.length - demoted.length >= 1) {{
      primary = primary.filter(c => !demoted.includes(c));
      support.unshift(...demoted);
    }}
  }}
  if (!primary.length && support.length) primary = [support.shift()];
  if (!primary.length && raw.length) primary = [raw.shift()];
  return {{ primary, support, raw }};
}}
function isSecondaryPrimaryContainer(f, c, allPrimary) {{
  if (!c || !Array.isArray(allPrimary) || allPrimary.length <= 1) return false;
  const id = String(c.id || '');
  const label = String(c.label || '');
  const layout = String(c && c.meta && c.meta.layout || 'generic');
  const hasStructuralPrimary = allPrimary.some(other => {{
    const otherLayout = String(other && other.meta && other.meta.layout || 'generic');
    return other !== c && ['graph','tree','trie','union_find','recursion_tree','linked_list','geometry','computational_graph'].includes(otherLayout);
  }});
  if ((layout === 'frame' || id.startsWith('frame:')) && (hasStructuralPrimary || !containerIsActive(f, c)) && allPrimary.some(other => other !== c)) return true;
  const hasGraphPrimary = allPrimary.some(other => {{
    const otherLayout = String(other && other.meta && other.meta.layout || 'generic');
    return other !== c && (otherLayout === 'graph' || otherLayout === 'computational_graph');
  }});
  const linearAuxLayouts = new Set(['array','string','string_list','queue','deque','stack','heap']);
  if (hasGraphPrimary && linearAuxLayouts.has(layout)) return true;
  if (!isUnionFindLikeContainer(f, c)) return false;
  return allPrimary.some(other => other !== c && !isUnionFindLikeContainer(f, other));
}}
function isUnionFindLikeContainer(f, c) {{
  const id = String(c && c.id || '');
  const label = String(c && c.label || '');
  const text = `${{id}} ${{label}}`.toLowerCase();
  if (text === 'uf uf' || text.includes('并查集') || text.includes('union_find') || text.includes('union-find') || text.includes('disjoint')) return true;
  if (/\\buf\\b/.test(text) || /\\bparent\\b/.test(text) && /\\brank\\b/.test(text)) return true;
  const state = f && f.state || {{}};
  const value = state[id] !== undefined ? state[id] : state[label];
  return Boolean(value && typeof value === 'object' && !Array.isArray(value) && (Array.isArray(value.parent) || Array.isArray(value['parent'])) && (Array.isArray(value.rank) || Array.isArray(value['rank'])));
}}
function stageRoleForContainer(f, c) {{
  const id = String(c && c.id || '');
  const label = String(c && c.label || '');
  const text = `${{id}} ${{label}}`;
  const layout = String(c && c.meta && c.meta.layout || 'generic');
  if (isAnswerLikeContainer(id)) return 'support';
  const active = containerIsActive(f, c);
  if (/递归栈|call[_ -]?stack|recursion[_ -]?stack/i.test(text)) return 'support';
  if (layout === 'frame' || id.startsWith('frame:')) return active ? 'primary' : 'support';
  const renderer = LAYOUT_RENDERERS[layout] || LAYOUT_RENDERERS.generic || 'map';
  const rawIds = new Set(['capacity','cap','capacities','flow','flows','residual','residual_capacity','residuals','memo','cache','call_stack','query_path','update_path','cover_path','nodes','edges','visited','dist','parent']);
  const rawLayouts = new Set(['map','generic']);
  const primaryLayouts = new Set(['graph','tree','recursion_tree','geometry','matrix','set_grid','array','string','string_list','heap','stack','queue','deque','trie','union_find','linked_list','ml','computational_graph']);
  const supportLayouts = new Set(['stack','queue','deque','heap','array','matrix','string','string_list']);
  const isRaw = rawIds.has(id) || rawLayouts.has(renderer) || rawLayouts.has(layout);
  if (active && primaryLayouts.has(layout)) return 'primary';
  if (active && !isRaw) return 'primary';
  if (primaryLayouts.has(layout) && !isRaw) return 'primary';
  if (supportLayouts.has(layout) && !isRaw) return 'support';
  if (isRaw) return 'raw';
  return 'support';
}}
function containerIsActive(f, c) {{
  const id = String(c && c.id || '');
  const evidence = f && f.evidence || {{}};
  const targets = new Set([...(evidence.targets || []), ...((f && f.marks || []).filter(m => m.role !== 'dependency').map(m => m.target))].map(String));
  const deps = new Set([...(evidence.deps || []), ...((f && f.marks || []).filter(m => m.role === 'dependency').map(m => m.target))].map(String));
  return targetTouchesContainer(id, targets) || targetTouchesContainer(id, deps);
}}
function isAnswerLikeContainer(id) {{
  const raw = String(id || '');
  return ['answer','ans','result'].includes(raw)
    || raw.startsWith('answer[')
    || raw.startsWith('ans[')
    || raw.startsWith('result[');
}}
function targetTouchesContainer(containerId, ids) {{
  if (!containerId || !ids) return false;
  for (const id of ids) {{
    if (id === containerId || id.startsWith(`${{containerId}}[`) || id.startsWith(`${{containerId}}:`)) return true;
    if (id.startsWith('pointer:') && containerId && id.endsWith(containerId)) return true;
  }}
  return false;
}}
function renderPrimaryStage(primary, groups, marks, objects) {{
  const f = frame();
  if (!primary.length && isGcdLikeFrame(f)) return renderGcdHero(f);
  const body = primary.length ? primary.map(c => renderPrimitivePanel(c, groups[c.id] || [], marks, 'primary')).join('') : renderLooseObjects(objects || [], marks);
  return body;
}}
function renderSemanticAnchorBand(f) {{
  const evidence = f && f.evidence || {{}};
  const marks = f && f.marks || [];
  const targets = unique([...(Array.isArray(evidence.targets) ? evidence.targets : []), ...marks.filter(m => m.role !== 'dependency').map(m => m.target)]).slice(0, 6);
  const deps = unique([...(Array.isArray(evidence.deps) ? evidence.deps : []), ...marks.filter(m => m.role === 'dependency').map(m => m.target)]).slice(0, 6);
  if (!targets.length && !deps.length) return '';
  const targetChips = targets.map(id => semanticAnchorChip(f, id, 'target')).join('');
  const depChips = deps.map(id => semanticAnchorChip(f, id, 'dependency')).join('');
  return `<section class="semantic-anchor-band" data-stage-role="anchor" data-visual-pattern="semantic_target_anchor" aria-label="当前语义锚点"><span class="semantic-anchor-label">当前对象</span>${{targetChips}}${{depChips ? `<span class="semantic-anchor-label">依赖</span>${{depChips}}` : ''}}</section>`;
}}
function semanticAnchorChip(f, id, kind) {{
  return `<span class="semantic-anchor-chip clickable-object" target-kind="${{esc(kind)}}" ${{clickableAttrs(id)}}>${{dependencyLabel(f, id)}}</span>`;
}}
function renderAnswerBadge(f) {{
  const answer = answerValueForFrame(f);
  const answerTarget = answerTargetForFrame(f);
  if (answer.value === undefined && !answerTarget) return '';
  const label = answer.key || (answerTarget ? String(answerTarget).replace(/\[.*$/, '') : 'answer');
  const value = answer.value === undefined ? '结果更新' : compactValue(answer.value);
  return `<section class="answer-badge clickable-object" data-stage-role="answer-badge" data-answer-like="true" ${{clickableAttrs(answerTarget || label)}}><strong>结果</strong><span>${{esc(label)}} = ${{esc(value)}}</span></section>`;
}}
function answerValueForFrame(f) {{
  const state = f && f.state || {{}};
  for (const key of ['answer','ans','result']) {{
    if (Object.prototype.hasOwnProperty.call(state, key)) return {{ key, value:state[key] }};
  }}
  return {{ key:'', value:undefined }};
}}
function answerTargetForFrame(f) {{
  const evidence = f && f.evidence || {{}};
  const ids = [
    ...(Array.isArray(evidence.targets) ? evidence.targets : []),
    ...((f && f.marks || []).filter(m => m.role === 'answer').map(m => m.target)),
  ].map(String);
  return ids.find(id => isAnswerLikeContainer(id)) || '';
}}
function isGcdLikeFrame(f) {{
  const state = f && f.state || {{}};
  const a = numberOrNull(state.a ?? state.x);
  const b = numberOrNull(state.b ?? state.y);
  const hasGcdHint = hasVisualFamilyPattern(f, 'gcd_state') || hasVisualFamily(f, 'gcd');
  if (hasGcdHint && (a !== null || b !== null)) return true;
  return a !== null && b !== null && (
    state.remainder !== undefined || state.mod !== undefined || state.gcd !== undefined ||
    state.quotient !== undefined || state.q !== undefined || state.x_coeff !== undefined || state.y_coeff !== undefined
  );
}}
function renderGcdHero(f) {{
  const state = f && f.state || {{}};
  const a = numberOrNull(state.a ?? state.x);
  const b = numberOrNull(state.b ?? state.y);
  const aText = a === null ? '?' : String(a);
  const bText = b === null ? '?' : String(b);
  const q = numberOrNull(state.quotient ?? state.q ?? (a !== null && b ? Math.floor(a / b) : null));
  const r = numberOrNull(state.remainder ?? state.mod ?? (a !== null && b ? a % b : null));
  let formulaLine = `<span>a</span><span>=</span><span>${{esc(aText)}}</span>`;
  let next = '等待 b 进入同一条余数链';
  if (a !== null && b !== null && b !== 0) {{
    formulaLine = `<span>${{a}}</span><span>=</span><span>${{q ?? '?'}}</span><span>×</span><span>${{b}}</span><span>+</span><span class="remainder">${{r ?? '?'}}</span>`;
    next = `余数 ${{r ?? '?'}} 传入下一轮：gcd(${{b}}, ${{r ?? '?'}})`;
  }} else if (a !== null && b === 0) {{
    formulaLine = `<span>gcd</span><span>(</span><span>${{a}}</span><span>,</span><span>0</span><span>)</span><span>=</span><span class="remainder">${{a}}</span>`;
    next = `终止：第二个数为 0，答案是 ${{a}}`;
  }} else if (a === null && b !== null) {{
    formulaLine = `<span>b</span><span>=</span><span>${{b}}</span>`;
  }}
  const coeff = state.x_coeff !== undefined || state.y_coeff !== undefined || state.coeff_x !== undefined || state.coeff_y !== undefined
    ? `<div class="gcd-backsub">回代：gcd = ${{esc(compactValue(state.x_coeff ?? state.coeff_x ?? '?'))}}·a + ${{esc(compactValue(state.y_coeff ?? state.coeff_y ?? '?'))}}·b</div>`
    : '';
  const answer = answerValueForFrame(f);
  const answerBadge = answer.value !== undefined ? `<div class="gcd-backsub">结果：${{esc(answer.key || 'answer')}} = ${{esc(compactValue(answer.value))}}</div>` : '';
  return `<section class="gcd-hero" data-stage-role="primary" data-visual-pattern="gcd_chain"><div class="gcd-formula-line">${{formulaLine}}</div><div class="gcd-transition"><span>${{esc(next)}}</span></div>${{coeff}}${{answerBadge}}</section>`;
}}
function renderSupportDock(support, groups, marks) {{
  if (!support.length) return '';
  return `<section class="support-dock" aria-label="辅助状态"><h3>辅助状态</h3><div class="dock-grid">${{support.map(c => renderPrimitivePanel(c, groups[c.id] || [], marks, 'support')).join('')}}</div></section>`;
}}
function renderRawStateDock(raw, groups, marks) {{
  if (!raw.length) return '';
  return `<details class="raw-state-dock"><summary>原始 state 证据（默认不进入主舞台）</summary><div class="dock-grid">${{raw.map(c => renderPrimitivePanel(c, groups[c.id] || [], marks, 'raw')).join('')}}</div></details>`;
}}
function fitModeForFrame(f, primary) {{
  if ((primary || []).length > 1) return 'contain';
  return 'contain';
}}
function fitSceneToCanvas() {{
  const host = $('canvas');
  const fit = host && host.querySelector('.scene-fit');
  const scene = fit && fit.querySelector('.objects');
  const surface = fit && fit.querySelector('.scene-scroll-surface');
  if (!host || !fit || !scene) return;
  bindScenePanZoom(fit, scene);
  fit.classList.remove('scroll-fit', 'pan-scroll');
  fit.scrollLeft = 0;
  fit.scrollTop = 0;
  syncSceneOverlays(fit);
  VIEW_STATE.userPan = false;
  scene.style.transform = 'none';
  scene.style.width = '';
  scene.style.height = '';
  if (surface) {{
    surface.style.width = '';
    surface.style.height = '';
  }}
  const availableWidth = Math.max(1, fit.clientWidth);
  const availableHeight = Math.max(1, fit.clientHeight);
  const bounds = measureVisualBounds(scene);
  const safePad = 18;
  const topSafePad = Math.max(safePad, sceneOverlayBottom(fit) + 10);
  const fitWidth = Math.max(1, availableWidth - safePad * 2);
  const fitHeight = Math.max(1, availableHeight - topSafePad - safePad);
  const rawScale = Math.min(fitWidth / bounds.width, fitHeight / bounds.height) * 0.985;
  const fitMode = scene.dataset.fitMode || 'contain';
  const minReadableScale = 1;
  const maxUsefulScale = 1.85;
  const minContainScale = 0.08;
  const needsReadableFallback = rawScale < minReadableScale;
  const scrollFit = needsReadableFallback;
  const effectiveFitMode = scrollFit ? 'pan-scroll' : 'contain';
  fit.classList.toggle('scroll-fit', scrollFit);
  fit.classList.toggle('pan-scroll', scrollFit);
  const scale = scrollFit ? minReadableScale : clampNumber(rawScale, minContainScale, maxUsefulScale);
  const contentWidth = Math.max(1, Math.ceil(Math.max(scene.scrollWidth, bounds.left + bounds.width, bounds.width)));
  const contentHeight = Math.max(1, Math.ceil(Math.max(scene.scrollHeight, bounds.top + bounds.height, bounds.height)));
  const translateX = scrollFit ? safePad - bounds.left * scale : safePad - bounds.left * scale + Math.max(0, (availableWidth - bounds.width * scale - safePad * 2) / 2);
  let translateY = scrollFit ? topSafePad - bounds.top * scale : topSafePad - bounds.top * scale + Math.max(0, (availableHeight - topSafePad - bounds.height * scale - safePad) / 2);
  applySceneTransform(scene, scale, translateX, translateY);
  const overlayDelta = fixedOverlayClearanceDelta(fit, scene);
  if (overlayDelta > 0) {{
    translateY += overlayDelta;
    applySceneTransform(scene, scale, translateX, translateY);
  }}
  const effectiveTopSafePad = topSafePad + overlayDelta;
  scene.style.width = `${{contentWidth}}px`;
  scene.style.height = `${{contentHeight}}px`;
  const surfaceWidth = scrollFit ? Math.max(availableWidth + 1, Math.ceil(bounds.width * scale + safePad * 2)) : availableWidth;
  const surfaceHeight = scrollFit ? Math.max(availableHeight + 1, Math.ceil(bounds.height * scale + effectiveTopSafePad + safePad)) : availableHeight;
  if (surface) {{
    surface.style.width = `${{surfaceWidth}}px`;
    surface.style.height = `${{surfaceHeight}}px`;
    surface.dataset.scrollWidth = String(surfaceWidth);
    surface.dataset.scrollHeight = String(surfaceHeight);
  }}
  scene.dataset.fitScale = String(scale);
  scene.dataset.fitMode = effectiveFitMode;
  scene.dataset.requestedFitMode = fitMode;
  scene.dataset.cameraMode = effectiveFitMode;
  scene.dataset.visualBoundsLeft = String(bounds.left);
  scene.dataset.visualBoundsTop = String(bounds.top);
  scene.dataset.visualBoundsWidth = String(bounds.width);
  scene.dataset.visualBoundsHeight = String(bounds.height);
  scene.dataset.topSafePad = String(effectiveTopSafePad);
  scene.dataset.overlayClearanceDelta = String(overlayDelta);
  scene.dataset.utilization = String(Math.min(1, (bounds.width * scale * bounds.height * scale) / Math.max(1, availableWidth * availableHeight)));
  VIEW_STATE.auto = {{ scale, x:translateX, y:translateY, bounds, mode:effectiveFitMode, scrollFit, surfaceWidth, surfaceHeight, safePad, topSafePad:effectiveTopSafePad, overlayDelta }};
  updateVisualQualityTelemetry(scene);
  if (scrollFit) requestAnimationFrame(() => scrollFocusedTarget(fit, scene));
}}
function syncSceneOverlays(fit) {{
  if (!fit) return;
  const offset = fit.scrollLeft || fit.scrollTop ? `translate(${{fit.scrollLeft}}px, ${{fit.scrollTop}}px)` : '';
  for (const node of fit.querySelectorAll(':scope > .view-tools, :scope > .semantic-anchor-band, :scope > .answer-badge')) {{
    node.style.transform = offset;
  }}
}}
function sceneOverlayBottom(fit) {{
  if (!fit) return 0;
  const fitRect = fit.getBoundingClientRect();
  const overlays = Array.from(fit.querySelectorAll(':scope > .semantic-anchor-band, :scope > .answer-badge'));
  const bottoms = overlays.map(node => node.getBoundingClientRect()).filter(rect => rect.width > 0 && rect.height > 0).map(rect => rect.bottom - fitRect.top);
  return bottoms.length ? Math.max(...bottoms) : 0;
}}
function fixedOverlayClearanceDelta(fit, scene) {{
  if (!fit || !scene) return 0;
  const overlays = Array.from(fit.querySelectorAll(':scope > .semantic-anchor-band, :scope > .answer-badge'))
    .map(node => node.getBoundingClientRect())
    .filter(rect => rect.width > 0 && rect.height > 0);
  if (!overlays.length) return 0;
  const selectors = [
    '.primary-scene svg .node',
    '.primary-scene svg text',
    '.primary-scene [data-object-id]',
    '.primary-scene .cell',
    '.primary-scene .mcell',
    '.primary-scene .gcd-hero'
  ];
  const contentRects = Array.from(scene.querySelectorAll(selectors.join(','))).filter(node => {{
    if (node.closest('.semantic-anchor-band') || node.closest('.answer-badge')) return false;
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  }}).map(node => node.getBoundingClientRect());
  let delta = 0;
  const gap = 10;
  for (const overlay of overlays) {{
    for (const rect of contentRects) {{
      const horizontalOverlap = rect.right > overlay.left + 1 && rect.left < overlay.right - 1;
      const verticalConflict = rect.top < overlay.bottom + gap && rect.bottom > overlay.top - 1;
      if (horizontalOverlap && verticalConflict) delta = Math.max(delta, overlay.bottom + gap - rect.top);
    }}
  }}
  return Math.ceil(Math.max(0, delta));
}}
function measureVisualBounds(scene) {{
  const selectors = [
    '.primary-scene > .primitive-panel[data-stage-role="primary"]',
    '.primary-scene svg',
    '.primary-scene [data-object-id]',
    '.primary-scene .cell',
    '.primary-scene .mcell',
    '.primary-scene .node',
    '.primary-scene .edge-label',
    '.primary-scene .gcd-hero'
  ];
  const sceneRect = scene.getBoundingClientRect();
  const candidates = Array.from(scene.querySelectorAll(selectors.join(','))).filter(node => {{
    if (node.closest('.semantic-anchor-band')) return false;
    if (node.closest('.answer-badge')) return false;
    const objectId = String(node.getAttribute('data-object-id') || '');
    const panelId = String(node.closest('[data-object-id]') && node.closest('[data-object-id]').getAttribute('data-object-id') || '');
    if (isAnswerLikeContainer(objectId) || isAnswerLikeContainer(panelId)) return false;
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  }});
  const rects = candidates.map(node => node.getBoundingClientRect()).filter(rect => rect.width > 0 && rect.height > 0);
  if (!rects.length) {{
    return {{ left:0, top:0, width:Math.max(1, scene.scrollWidth), height:Math.max(1, scene.scrollHeight) }};
  }}
  const left = Math.min(...rects.map(rect => rect.left)) - sceneRect.left;
  const top = Math.min(...rects.map(rect => rect.top)) - sceneRect.top;
  const right = Math.max(...rects.map(rect => rect.right)) - sceneRect.left;
  const bottom = Math.max(...rects.map(rect => rect.bottom)) - sceneRect.top;
  return {{ left, top, width:Math.max(1, right - left), height:Math.max(1, bottom - top) }};
}}
function applySceneTransform(scene, scale, x, y) {{
  scene.style.transform = `translate(${{x}}px, ${{y}}px) scale(${{scale}})`;
  VIEW_STATE.scale = scale;
  VIEW_STATE.x = x;
  VIEW_STATE.y = y;
  if (scene) {{
    scene.dataset.fitScale = String(scale);
    scene.dataset.panX = String(x);
    scene.dataset.panY = String(y);
    if (VIEW_STATE.auto && VIEW_STATE.auto.scrollFit) syncSceneScrollSurface(scene, scale);
  }}
}}
function syncSceneScrollSurface(scene, scale) {{
  const fit = document.querySelector('#canvas .scene-fit');
  const surface = fit && fit.querySelector('.scene-scroll-surface');
  const auto = VIEW_STATE.auto;
  if (!surface || !auto || !auto.bounds) return;
  const safePad = auto.safePad || 18;
  const topSafePad = auto.topSafePad || safePad;
  const width = Math.max((fit && fit.clientWidth || 0) + 1, Math.ceil(auto.bounds.width * scale + safePad * 2));
  const height = Math.max((fit && fit.clientHeight || 0) + 1, Math.ceil(auto.bounds.height * scale + topSafePad + safePad));
  surface.style.width = `${{width}}px`;
  surface.style.height = `${{height}}px`;
  surface.dataset.scrollWidth = String(width);
  surface.dataset.scrollHeight = String(height);
  if (scene) scene.dataset.cameraMode = auto.scrollFit ? 'pan-scroll' : (auto.mode || 'contain');
}}
function bindScenePanZoom(fit, scene) {{
  if (!fit || !scene || fit.dataset.panZoomBound === 'true') return;
  fit.dataset.panZoomBound = 'true';
  fit.addEventListener('scroll', () => syncSceneOverlays(fit));
  fit.addEventListener('wheel', event => {{
    if (!fit.contains(event.target)) return;
    event.preventDefault();
    const rect = fit.getBoundingClientRect();
    const mx = event.clientX - rect.left;
    const my = event.clientY - rect.top;
    const oldScale = VIEW_STATE.scale || 1;
    const newScale = clampNumber(oldScale * (event.deltaY > 0 ? 0.9 : 1.1), 0.12, 3.2);
    const x = mx - (mx - VIEW_STATE.x) * (newScale / oldScale);
    const y = my - (my - VIEW_STATE.y) * (newScale / oldScale);
    VIEW_STATE.userPan = true;
    applySceneTransform(scene, newScale, x, y);
    updateVisualQualityTelemetry(scene);
  }}, {{ passive:false }});
  fit.addEventListener('pointerdown', event => {{
    if (event.button !== 0 || event.target.closest('.view-tools')) return;
    fit.setPointerCapture(event.pointerId);
    fit.classList.add('dragging');
    VIEW_STATE.drag = {{
      pointerId:event.pointerId,
      startX:event.clientX,
      startY:event.clientY,
      x:VIEW_STATE.x,
      y:VIEW_STATE.y,
      scrollLeft:fit.scrollLeft,
      scrollTop:fit.scrollTop,
      scrollMode:fit.classList.contains('pan-scroll')
    }};
  }});
  fit.addEventListener('pointermove', event => {{
    const drag = VIEW_STATE.drag;
    if (!drag || drag.pointerId !== event.pointerId) return;
    VIEW_STATE.userPan = true;
    if (drag.scrollMode) {{
      fit.scrollLeft = Math.max(0, drag.scrollLeft + drag.startX - event.clientX);
      fit.scrollTop = Math.max(0, drag.scrollTop + drag.startY - event.clientY);
      return;
    }}
    applySceneTransform(scene, VIEW_STATE.scale, drag.x + event.clientX - drag.startX, drag.y + event.clientY - drag.startY);
  }});
  const endDrag = event => {{
    const drag = VIEW_STATE.drag;
    if (!drag || drag.pointerId !== event.pointerId) return;
    VIEW_STATE.drag = null;
    fit.classList.remove('dragging');
  }};
  fit.addEventListener('pointerup', endDrag);
  fit.addEventListener('pointercancel', endDrag);
  fit.addEventListener('dblclick', event => {{
    if (event.target.closest('.view-tools')) return;
    resetSceneView();
  }});
}}
function resetSceneView() {{
  const scene = document.querySelector('#canvas .objects');
  if (!scene || !VIEW_STATE.auto) return fitSceneToCanvas();
  VIEW_STATE.userPan = false;
  applySceneTransform(scene, VIEW_STATE.auto.scale, VIEW_STATE.auto.x, VIEW_STATE.auto.y);
  scene.dataset.fitMode = VIEW_STATE.auto.mode || scene.dataset.fitMode || 'contain';
  const fit = document.querySelector('#canvas .scene-fit');
  if (fit) {{
    fit.classList.toggle('scroll-fit', !!VIEW_STATE.auto.scrollFit);
    fit.classList.toggle('pan-scroll', !!VIEW_STATE.auto.scrollFit);
    fit.scrollLeft = 0;
    fit.scrollTop = 0;
    syncSceneOverlays(fit);
    if (VIEW_STATE.auto.scrollFit) requestAnimationFrame(() => scrollFocusedTarget(fit, scene));
  }}
  updateVisualQualityTelemetry(scene);
}}
function zoomSceneToOne() {{
  const scene = document.querySelector('#canvas .objects');
  const fit = document.querySelector('#canvas .scene-fit');
  if (!scene || !fit) return;
  const auto = VIEW_STATE.auto || {{ x:18, y:18 }};
  VIEW_STATE.userPan = true;
  applySceneTransform(scene, 1, auto.x, auto.y);
  updateVisualQualityTelemetry(scene);
}}
window.resetSceneView = resetSceneView;
function updateVisualQualityTelemetry(scene) {{
  const telemetry = $('visual-quality-telemetry');
  if (!telemetry || !scene) return;
  const family = telemetry.dataset.familyRenderer || '';
  const scale = Number(scene.dataset.fitScale || 0);
  const utilization = Number(scene.dataset.utilization || 0);
  const chips = [
    visualChip(`family_renderer=${{family}}`),
    visualChip(`fit_mode=${{scene.dataset.fitMode || 'unknown'}}`),
    visualChip(`fit_scale=${{scale ? scale.toFixed(2) : 'unknown'}}`),
    visualChip(`utilization=${{utilization ? utilization.toFixed(2) : '0.00'}}`),
    visualChip(`requested=${{scene.dataset.requestedFitMode || 'unknown'}}`),
  ].join('');
  telemetry.innerHTML = chips;
}}
function scrollFocusedTarget(fit, scene) {{
  const focus = focusedSceneObject(scene);
  if (!focus) return;
  const fitRect = fit.getBoundingClientRect();
  const focusRect = focus.getBoundingClientRect();
  const safeTop = fitRect.top + sceneOverlayBottom(fit) + 10;
  const safeLeft = fitRect.left + 8;
  const safeRight = fitRect.right - 8;
  const safeBottom = fitRect.bottom - 8;
  const focusCenterViewportX = focusRect.left + focusRect.width / 2;
  const focusCenterViewportY = focusRect.top + focusRect.height / 2;
  if (
    focusCenterViewportX >= safeLeft && focusCenterViewportX <= safeRight &&
    focusCenterViewportY >= safeTop && focusCenterViewportY <= safeBottom
  ) return;
  const centerX = focusRect.left + focusRect.width / 2 - fitRect.left + fit.scrollLeft;
  const centerY = focusRect.top + focusRect.height / 2 - fitRect.top + fit.scrollTop;
  fit.scrollLeft = Math.max(0, centerX - fit.clientWidth / 2);
  fit.scrollTop = Math.max(0, centerY - fit.clientHeight / 2);
  syncSceneOverlays(fit);
  const overlayDelta = fixedOverlayClearanceDelta(fit, scene);
  if (overlayDelta > 0) {{
    fit.scrollTop = Math.max(0, fit.scrollTop - overlayDelta);
    syncSceneOverlays(fit);
  }}
}}
function focusedSceneObject(scene) {{
  const f = frame();
  const evidence = f && f.evidence || {{}};
  const orderedIds = [
    ...(Array.isArray(evidence.targets) ? evidence.targets : []),
    ...((f && f.marks || []).filter(m => m.role !== 'dependency').map(m => m.target)),
    ...(Array.isArray(evidence.deps) ? evidence.deps : []),
    ...((f && f.marks || []).filter(m => m.role === 'dependency').map(m => m.target)),
  ].filter(Boolean).map(String);
  for (const id of orderedIds) {{
    const direct = sceneObjectBySemanticId(scene, id);
    if (direct) return direct;
  }}
  return scene.querySelector('.hot[data-object-id], .dep[data-object-id], [data-object-id]');
}}
function sceneObjectBySemanticId(scene, id) {{
  const direct = sceneObjectById(scene, id);
  if (direct) return direct;
  const proxies = semanticProxyIds(id);
  for (const proxyId of proxies) {{
    const proxy = sceneObjectById(scene, proxyId);
    if (proxy) return proxy;
  }}
  if (String(id) === 'answer' || String(id) === 'result') {{
    return scene.querySelector(answerStateProxySelectors()) || semanticFallbackObject(scene, id);
  }}
  return semanticFallbackObject(scene, id);
}}
function semanticFallbackObject(scene, id) {{
  const raw = String(id || '');
  if (!scene) return null;
  if (raw.startsWith('frame:')) {{
    const framePhaseMatch = raw.match(/^frame:(?:phase\\/)?([^()]+)$/);
    if (framePhaseMatch && framePhaseMatch[1]) {{
      const phaseText = framePhaseMatch[1].replace(/_/g, ' ');
      const node = Array.from(scene.querySelectorAll('[data-object-id]')).find(item => String(item.getAttribute('data-object-id') || '').includes(phaseText));
      if (node) return node;
    }}
    return scene.querySelector('.primary-scene [data-stage-role="primary"], [data-stage-role="primary"], [data-object-id]');
  }}
  const stateProxy = sceneObjectById(scene, raw)
    || sceneObjectById(scene, `pointer:${{raw}}`)
    || sceneObjectById(scene, `node:${{raw}}`);
  if (stateProxy) return stateProxy;
  const localCell = localStateCellProxy(scene, raw);
  if (localCell) return localCell;
  const prefixProxy = Array.from(scene.querySelectorAll('[data-object-id]')).find(item => {{
    const objectId = String(item.getAttribute('data-object-id') || '');
    return objectId === raw || objectId.startsWith(`${{raw}}[`) || objectId.endsWith(`:${{raw}}`);
  }});
  if (prefixProxy) return prefixProxy;
  if (raw === 'answer' || raw === 'result') return scene.querySelector(answerStateProxySelectors());
  return null;
}}
function localStateCellProxy(scene, raw) {{
  const f = frame();
  const evidence = f && f.evidence || {{}};
  const eventCell = indexedReferenceCellProxy(scene, evidence.value);
  if (eventCell) return eventCell;
  const state = f && f.state || {{}};
  const value = state[raw];
  if (!Number.isInteger(Number(value))) return null;
  const containerId = primaryLinearContainerId(f);
  if (!containerId) return null;
  return sceneObjectById(scene, `${{containerId}}[${{Number(value)}}]`);
}}
function indexedReferenceCellProxy(scene, value) {{
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const container = value.on ?? value.container ?? value.array ?? value.source;
  const idx = value.idx ?? value.index ?? value.i;
  if (!container || !Number.isInteger(Number(idx))) return null;
  return sceneObjectById(scene, `${{container}}[${{Number(idx)}}]`);
}}
function primaryLinearContainerId(f) {{
  const state = f && f.state || {{}};
  for (const key of ['dp','nums','arr','array','values','temperatures','prices','heights']) {{
    const value = state[key];
    if (Array.isArray(value) && value.every(item => !Array.isArray(item) && (item === null || typeof item !== 'object'))) return key;
  }}
  const container = (f && f.objects || []).find(o => o && o.type === 'container' && o.meta && ['array','string'].includes(o.meta.layout));
  return container ? container.id : '';
}}
function answerStateProxySelectors() {{
  return '.answer-badge[data-object-id], .role-answer[data-object-id], .pattern-answer-projection[data-object-id], .answer[data-object-id], [data-object-id="answer"], [data-object-id="ans"], [data-object-id="result"], [data-object-id^="answer["], [data-object-id^="ans["], [data-object-id^="result["], .hot[data-object-id], .node.role-answer, .node.pattern-answer-projection, .node.answer, .node.hot, .cell.answer, .mcell.answer';
}}
function semanticProxyIds(id) {{
  const raw = String(id || '');
  const proxies = [];
  const edgeMatch = raw.match(/^edge:([^>]+)->(.+)$/);
  if (edgeMatch && edgeMatch[1] && edgeMatch[2]) {{
    proxies.push(`edge-label:${{edgeMatch[1]}}->${{edgeMatch[2]}}`, `node:${{edgeMatch[1]}}`, `node:${{edgeMatch[2]}}`);
  }}
  const frameMatch = raw.match(/^frame:[^(]+\\(([^()]*)\\)$/);
  if (frameMatch && frameMatch[1]) {{
    proxies.push(`node:${{frameMatch[1]}}`, frameMatch[1]);
  }}
  const plainNodeMatch = raw.match(/^(?:current|node|vertex)[_:]([A-Za-z0-9_.-]+)$/);
  if (plainNodeMatch && plainNodeMatch[1]) proxies.push(`node:${{plainNodeMatch[1]}}`);
  return proxies;
}}
function sceneObjectById(scene, id) {{
  return Array.from(scene.querySelectorAll('[data-object-id]')).find(node => node.getAttribute('data-object-id') === String(id));
}}
function clampNumber(value, min, max) {{
  return Math.max(min, Math.min(max, Number.isFinite(value) ? value : 1));
}}
function renderPrimitivePanel(c, children, marks, stageRole='primary') {{
  const layout = c.meta && c.meta.layout || 'generic';
  return `<section class="primitive-panel clickable-object ${{primitivePanelClass(c)}} ${{markClass(c.id, marks)}} ${{objectMetaClass(c)}}" ${{clickableAttrs(c.id)}} data-layout="${{esc(layout)}}" data-stage-role="${{esc(stageRole)}}">${{renderContainer(c, children, marks)}}</section>`;
}}
function primitivePanelClass(c) {{
  const layout = c && c.meta && c.meta.layout || 'generic';
  return `primitive-${{String(layout).replace(/[^a-zA-Z0-9_-]/g, '-')}}`;
}}
function renderVisualPatternPanel(f) {{
  const cards = [
    renderFormulaSubstitutionPattern(f),
    renderGraphVisualPattern(f),
    renderStringAlignmentPattern(f),
    renderTreeReturnPattern(f),
    renderBacktrackingPattern(f),
    renderKruskalTrackPattern(f),
    renderRangeStructurePattern(f),
    renderNetworkFlowPattern(f),
    renderDpDependencyWindowPattern(f),
    renderBitmaskTransitionPattern(f),
    renderStringSpecializedPattern(f),
    renderFenwickLowbitPattern(f),
    renderSparseTableBlocksPattern(f),
    renderDiffPrefixPattern(f),
    renderGeometryRelationPattern(f),
    renderNetworkFlowAugmentingPathPattern(f),
    renderBinaryPointerPattern(f),
    renderDigitDpPattern(f),
    renderMonotonicStackPattern(f),
    renderHeapSiftPattern(f),
    renderGraphMetricOverlay(f),
    renderTreeDpOverlay(f),
  ].filter(Boolean);
  if (!cards.length) return '';
  return `<section class="visual-patterns" aria-label="族级视觉模式">${{cards.join('')}}</section>`;
}}
function renderFormulaSubstitutionPattern(f) {{
  const targets = objectsWithPattern(f, 'dp_formula_substitution').filter(o => o.meta && o.meta.pattern_role === 'dp_target');
  const arrows = objectsWithPattern(f, 'dp_dependency_arrow');
  if (!targets.length && !arrows.length) return '';
  const formula = textOrEmpty(f.teaching && f.teaching.formula) || textOrEmpty((targets[0] && targets[0].meta && targets[0].meta.formula) || '');
  const substitution = textOrEmpty((targets[0] && targets[0].meta && targets[0].meta.substitution) || '');
  const chips = targets.map(o => visualChip(o.id)).join('') + arrows.slice(0, 4).map(o => visualChip(`${{o.source}} → ${{o.target}}`)).join('');
  return `<article class="visual-card dp-formula-substitution" data-visual-pattern="dp_formula_substitution"><strong>DP 依赖代入</strong>${{formula ? `<code>${{esc(formula)}}</code>` : ''}}${{substitution ? `<code>${{esc(substitution)}}</code>` : ''}}<div class="visual-chip-row">${{chips}}</div></article>`;
}}
function renderGraphVisualPattern(f) {{
  const frontier = objectsWithPattern(f, 'graph_frontier');
  const relax = objectsWithPattern(f, 'graph_relax_edge');
  const path = objectsWithPattern(f, 'graph_path_highlight');
  if (!frontier.length && !relax.length && !path.length) return '';
  return `<article class="visual-card graph-visual-pattern" data-visual-pattern="graph_relax"><strong>图 frontier / relax / path</strong><div class="visual-chip-row">${{frontier.slice(0, 6).map(o => visualChip(`frontier ${{o.id}}`)).join('')}}${{relax.slice(0, 6).map(o => visualChip(`relax ${{edgeDisplayLabel(o) || o.id}}`)).join('')}}${{path.slice(0, 6).map(o => visualChip(`path ${{o.id}}`)).join('')}}</div></article>`;
}}
function renderStringAlignmentPattern(f) {{
  const rows = objectsWithPattern(f, 'string_alignment').filter(o => o.type === 'container' && o.meta && o.meta.layout === 'string');
  if (rows.length < 2) return '';
  const body = rows.map(row => {{
    const cells = (f.objects || []).filter(o => o.parent === row.id && o.type === 'cell').sort((a,b)=>(a.index??0)-(b.index??0));
    const offset = Math.max(0, Number(row.meta && row.meta.alignment_offset) || 0);
    const spacer = offset ? `<span style="width:${{offset * 30}}px;flex:0 0 ${{offset * 30}}px"></span>` : '';
    return `<div class="string-row" data-row-role="${{esc(row.meta && row.meta.row_role || row.id)}}"><span class="string-row-label">${{esc(row.label || row.id)}}</span>${{spacer}}${{cells.map(cell => `<span class="visual-char ${{objectMetaClass(cell)}} ${{objectPatterns(cell).includes('string_window') ? 'window' : ''}} ${{objectPatterns(cell).includes('string_alignment') ? 'cursor' : ''}}" data-object-id="${{esc(cell.id)}}">${{esc(cell.value)}}</span>`).join('')}}</div>`;
  }}).join('');
  const fallback = objectsWithPattern(f, 'string_fallback_arc').map(o => visualChip(`${{o.source}} ↩ ${{o.target}}`)).join('');
  return `<article class="visual-card string-alignment-card" data-visual-pattern="string_alignment"><strong>字符串双行对齐 / 窗口</strong><div class="string-alignment">${{body}}</div>${{fallback ? `<div class="visual-chip-row">${{fallback}}</div>` : ''}}</article>`;
}}
function renderTreeReturnPattern(f) {{
  const nodes = objectsWithPattern(f, 'tree_return_value').filter(o => o.meta && o.meta.return_value !== undefined);
  if (!nodes.length) return '';
  return `<article class="visual-card tree-return-pattern" data-visual-pattern="tree_return_value"><strong>树递归返回值</strong><div class="visual-chip-row">${{nodes.slice(0, 8).map(o => visualChip(`${{o.id}} = ${{compactValue(o.meta.return_value)}}`)).join('')}}</div></article>`;
}}
function renderBacktrackingPattern(f) {{
  const choices = objectsWithPattern(f, 'backtracking_choice');
  const undo = objectsWithPattern(f, 'backtracking_undo');
  const state = f && f.state || {{}};
  const path = Array.isArray(state.path) ? state.path : Array.isArray(state.current_path) ? state.current_path : Array.isArray(state.partial) ? state.partial : [];
  const candidates = Array.isArray(state.candidates) ? state.candidates : Array.isArray(state.remaining) ? state.remaining : [];
  const depth = state.depth ?? state.level ?? path.length;
  if (!choices.length && !undo.length && !path.length && !candidates.length) return '';
  const track = [
    `<span class="backtracking-pill">depth=${{esc(compactValue(depth))}}</span>`,
    path.length ? `<span class="backtracking-pill">path: ${{esc(path.map(compactValue).join(' → '))}}</span>` : '',
    candidates.length ? `<span class="backtracking-pill">候选: ${{esc(candidates.slice(0, 8).map(compactValue).join(', '))}}</span>` : '',
  ].join('');
  return `<article class="visual-card backtracking-pattern" data-visual-pattern="backtracking_choice"><strong>回溯 path / 候选 / 撤销</strong><div class="backtracking-track">${{track}}</div><div class="visual-chip-row">${{choices.slice(0, 6).map(o => visualChip(`选择 ${{o.id}}`)).join('')}}${{undo.slice(0, 6).map(o => visualChip(`撤销 ${{o.id}}`)).join('')}}</div></article>`;
}}
function renderKruskalTrackPattern(f) {{
  const state = f && f.state || {{}};
  const edges = state.sorted_edges || state.edge_order || state.edges;
  const current = state.current_edge ?? state.edge ?? state.current;
  const accepted = state.accepted_edges || state.mst_edges || state.selected_edges || state.mst;
  const rejected = state.rejected_edges || state.skipped_edges || state.conflict_edges;
  if (!Array.isArray(edges) || !edges.length || (!accepted && !rejected && current === undefined && !hasVisualFamily(f, 'kruskal'))) return '';
  const pills = edges.slice(0, 12).map(edge => {{
    const label = kruskalEdgeLabel(edge);
    const cls = edgeMatchesValue(edge, current) ? 'current' : edgeInListValue(edge, accepted) ? 'accept' : edgeInListValue(edge, rejected) ? 'reject' : '';
    return `<span class="kruskal-edge-pill ${{cls}}">${{esc(label)}}</span>`;
  }}).join('');
  return `<article class="visual-card kruskal-track-panel" data-visual-pattern="kruskal_edge_order"><strong>Kruskal 边排序 / 接纳轨道</strong><div class="kruskal-edge-track">${{pills}}</div></article>`;
}}
function kruskalEdgeLabel(edge) {{
  if (Array.isArray(edge)) return edge.length >= 3 ? `${{edge[0]}}-${{edge[1]}} w=${{edge[2]}}` : edge.join('-');
  if (edge && typeof edge === 'object') return `${{edge.u ?? edge.source ?? edge[0] ?? '?'}}-${{edge.v ?? edge.target ?? edge[1] ?? '?'}}${{edge.w !== undefined || edge.weight !== undefined ? ` w=${{edge.w ?? edge.weight}}` : ''}}`;
  return compactValue(edge);
}}
function edgeInListValue(edge, list) {{
  if (!list) return false;
  const values = Array.isArray(list) ? list : Object.values(list);
  return values.some(item => edgeMatchesValue(edge, item));
}}
function edgeMatchesValue(edge, value) {{
  if (value === undefined || value === null) return false;
  const label = kruskalEdgeLabel(edge);
  if (String(value) === label || String(value) === compactValue(edge)) return true;
  return edgePairMatches(edge, String(value.u ?? value.source ?? value[0] ?? ''), String(value.v ?? value.target ?? value[1] ?? ''));
}}
function renderRangeStructurePattern(f) {{
  const query = objectsWithPattern(f, 'range_query_path');
  const update = objectsWithPattern(f, 'range_update_path');
  const cover = objectsWithPattern(f, 'range_cover_path');
  if (!query.length && !update.length && !cover.length) return '';
  return `<article class="visual-card range-structure-pattern" data-visual-pattern="range_structure"><strong>区间结构 query / update 路径</strong><div class="visual-chip-row">${{query.slice(0, 8).map(o => visualChip(`query ${{o.id}}`)).join('')}}${{update.slice(0, 8).map(o => visualChip(`update ${{o.id}}`)).join('')}}${{cover.slice(0, 8).map(o => visualChip(`cover ${{o.id}}`)).join('')}}</div></article>`;
}}
function renderNetworkFlowPattern(f) {{
  const edges = objectsWithPattern(f, 'network_flow_edge_label').filter(o => o.type === 'edge');
  if (!edges.length) return '';
  return `<article class="visual-card network-flow-pattern" data-visual-pattern="network_flow_edge_label"><strong>网络流 residual / capacity</strong><div class="visual-chip-row">${{edges.slice(0, 8).map(o => visualChip(`${{o.id}} ${{edgeDisplayLabel(o)}}`)).join('')}}</div></article>`;
}}
function renderDpDependencyWindowPattern(f) {{
  const targets = objectsWithPattern(f, 'dp_formula_substitution').filter(o => o.type === 'cell' || o.meta && o.meta.pattern_role === 'dp_target');
  const arrows = objectsWithPattern(f, 'dp_dependency_arrow');
  const evidence = f && f.evidence || {{}};
  const deps = (evidence.deps || []).filter(id => String(id).includes('[')).slice(0, 6);
  const targetIds = (evidence.targets || []).filter(id => String(id).includes('[')).slice(0, 3);
  if (!targets.length && !arrows.length && !deps.length && !targetIds.length) return '';
  const targetCells = (targets.length ? targets.map(o => o.id) : targetIds).slice(0, 4);
  const depCells = arrows.length ? arrows.slice(0, 6).map(o => o.source || o.id) : deps;
  const cells = [
    ...depCells.map(id => `<span class="dp-window-cell">${{esc(id)}}</span>`),
    ...targetCells.map(id => `<span class="dp-window-cell dp-current-cell">${{esc(id)}}</span>`),
  ].join('');
  const arrowRow = depCells.length && targetCells.length
    ? `<div class="visual-chip-row"><span class="dp-dependency-arrow">${{esc(depCells.join(' + '))}} → ${{esc(targetCells.join(', '))}}</span></div>`
    : '';
  const formula = textOrEmpty(f && f.teaching && f.teaching.formula) || graphRelaxFormula(f, f && f.state || {{}});
  return `<article class="visual-card dp-dependency-window" data-visual-pattern="dp_dependency_window"><strong>DP 当前格 / 依赖窗口</strong><div class="dp-window-grid">${{cells}}</div>${{arrowRow}}${{formula ? `<div class="relax-formula">${{esc(formula)}}</div>` : ''}}</article>`;
}}
function renderBitmaskTransitionPattern(f) {{
  const state = f && f.state || {{}};
  const mask = numberOrNull(state.mask ?? state.subset ?? state.state_mask);
  const u = state.u ?? state.current_city ?? state.last ?? state.i;
  const v = state.v ?? state.next_city ?? state.next ?? state.j;
  const hasBitmask = mask !== null || state.next_mask !== undefined || state.new_mask !== undefined || state.visited_mask !== undefined || hasVisualFamily(f, 'state_compression') || hasVisualFamily(f, 'bitmask_dp');
  if (!hasBitmask) return '';
  const nextMask = numberOrNull(state.next_mask ?? state.new_mask ?? (mask !== null && v !== undefined && Number.isInteger(Number(v)) ? (mask | (1 << Number(v))) : null));
  const n = numberOrNull(state.n ?? state.city_count ?? state.num_cities) ?? 4;
  const visited = mask === null ? [] : Array.from({{length:Math.min(16, Math.max(1, n))}}, (_, i) => (mask & (1 << i)) ? i : null).filter(v => v !== null);
  const formula = `dp[${{mask ?? '?'}}][${{compactValue(u ?? '?')}}] + dist[${{compactValue(u ?? '?')}}][${{compactValue(v ?? '?')}}] → dp[${{nextMask ?? '?'}}][${{compactValue(v ?? '?')}}]`;
  return `<article class="visual-card bitmask-transition-panel" data-visual-pattern="bitmask_transition"><strong>状态压缩 mask 转移</strong><div class="bitmask-transition-track"><span class="bitmask-pill">mask=${{esc(compactValue(mask))}}</span><span class="bitmask-pill">bin=${{mask === null ? '?' : mask.toString(2).padStart(Math.min(16, n), '0')}}</span><span class="bitmask-pill">visited={{${{esc(visited.join(', '))}}}}</span><span class="bitmask-pill">${{esc(formula)}}</span></div></article>`;
}}
function renderStringSpecializedPattern(f) {{
  const state = f && f.state || {{}};
  const hasString = typeof state.text === 'string' || typeof state.pattern === 'string' || typeof state.s === 'string';
  const fallback = state.fallback_from !== undefined || state.fallback_to !== undefined || objectsWithPattern(f, 'string_fallback_arc').length;
  const hasHash = state.rolling_hash !== undefined || state.window_hash !== undefined || state.pattern_hash !== undefined;
  const zBox = state.z_box || state.zbox || (state.l !== undefined && state.r !== undefined && (state.z || state.Z));
  const manacher = state.center !== undefined || state.radius !== undefined || state.mirror !== undefined || state.C !== undefined || state.R !== undefined || Array.isArray(state.P) || hasVisualFamilyPattern(f, 'manacher_radius');
  if (!hasString && !fallback && !hasHash && !zBox && !manacher) return '';
  const tracks = [];
  if (hasString) tracks.push(`<span class="string-track"><strong>text/pattern</strong><span>i=${{esc(compactValue(state.i ?? state.idx ?? ''))}} · j=${{esc(compactValue(state.j ?? ''))}}</span></span>`);
  if (fallback) tracks.push(`<span class="kmp-fallback-arc">KMP fallback ${{esc(compactValue(state.fallback_from ?? '?'))}} ↩ ${{esc(compactValue(state.fallback_to ?? '?'))}}</span>`);
  if (hasHash) tracks.push(`<span class="rolling-hash-track">rolling hash ${{esc(compactValue(state.window_hash ?? state.rolling_hash))}} / pattern ${{esc(compactValue(state.pattern_hash))}}</span>`);
  if (zBox) {{
    const box = Array.isArray(zBox) ? zBox : [state.l, state.r];
    tracks.push(`<span class="z-box-band">Z-box [${{esc(compactValue(box[0]))}}, ${{esc(compactValue(box[1]))}}] · i=${{esc(compactValue(state.i ?? state.idx ?? '?'))}}</span>`);
  }}
  if (manacher) {{
    const center = state.center ?? state.C ?? state.c;
    const index = state.i ?? state.idx ?? state.index;
    const radius = state.radius ?? (Array.isArray(state.P) && Number.isInteger(Number(index)) ? state.P[Number(index)] : undefined);
    const mirror = state.mirror ?? (center !== undefined && index !== undefined ? 2 * Number(center) - Number(index) : undefined);
    const right = state.right ?? state.R ?? state.r;
    tracks.push(`<span class="manacher-radius-arc">中心线 center=${{esc(compactValue(center ?? '?'))}} · i=${{esc(compactValue(index ?? '?'))}} · 半径 P[i]=${{esc(compactValue(radius ?? '?'))}} · R=${{esc(compactValue(right ?? '?'))}} · mirror=${{esc(compactValue(mirror ?? '?'))}}</span>`);
  }}
  return `<article class="visual-card string-specialized-card" data-visual-pattern="string_specialized"><strong>字符串专项关系</strong><div class="string-specialized-tracks">${{tracks.join('')}}</div></article>`;
}}
function renderFenwickLowbitPattern(f) {{
  const state = f && f.state || {{}};
  const bit = state.bit || state.fenwick || state.fenwick_tree;
  const index = pointerIndexValue(state, ['idx','index','i','pos']);
  const explicitPath = Array.isArray(state.query_path) ? state.query_path : Array.isArray(state.update_path) ? state.update_path : Array.isArray(state.path) ? state.path : null;
  const lowbit = numberOrNull(state.lowbit ?? (index === null ? null : (index & -index)));
  if (!Array.isArray(bit) && !explicitPath && index === null && !hasVisualFamilyPattern(f, 'fenwick_lowbit')) return '';
  const path = explicitPath || (index !== null && lowbit !== null ? [index, index + lowbit, index - lowbit].filter(n => n > 0) : []);
  const fallbackPath = path.length ? path : [1, 2, 4].filter(n => !Array.isArray(bit) || n < bit.length);
  const arrows = fallbackPath.slice(0, 8).map((value, i) => `<span class="fenwick-hop-arrow">${{esc(compactValue(value))}}${{i < fallbackPath.length - 1 ? ' →' : ''}}</span>`).join('');
  const covers = Array.isArray(bit) ? bit.slice(1, 9).map((value, i) => {{
    const idx = i + 1;
    const width = idx & -idx;
    return visualChip(`bit[${{idx}}] covers [${{idx - width + 1}},${{idx}}]`);
  }}).join('') : primaryLinearValues(f, ['nums','values','arr']).slice(0, 6).map((_, i) => {{
    const idx = i + 1;
    const width = idx & -idx;
    return visualChip(`bit[${{idx}}] covers [${{idx - width + 1}},${{idx}}]`);
  }}).join('');
  return `<article class="visual-card fenwick-lowbit-panel" data-visual-pattern="fenwick_lowbit"><strong>Fenwick lowbit 跳转</strong><div class="range-hop-row">${{arrows || visualChip(`idx=${{compactValue(index)}} lowbit=${{compactValue(lowbit)}}`)}}</div><div class="visual-chip-row">${{covers}}</div></article>`;
}}
function renderSparseTableBlocksPattern(f) {{
  const state = f && f.state || {{}};
  const table = state.st || state.sparse_table || state.sparse;
  const l = pointerIndexValue(state, ['l','left','query_l']);
  const r = pointerIndexValue(state, ['r','right','query_r']);
  const k = pointerIndexValue(state, ['k','level','log']);
  const explicit = state.query_blocks || state.blocks;
  const hasSparse = Array.isArray(table) || Array.isArray(explicit) || (l !== null && r !== null && k !== null);
  if (!hasSparse) return '';
  const blocks = Array.isArray(explicit) ? explicit.slice(0, 2) : [[l, l === null || k === null ? r : l + Math.pow(2, k) - 1], [r === null || k === null ? l : r - Math.pow(2, k) + 1, r]];
  return `<article class="visual-card sparse-table-blocks" data-visual-pattern="sparse_table_blocks"><strong>Sparse Table query blocks</strong><div class="sparse-block-row">${{blocks.map(block => `<span class="sparse-query-block">[${{esc(compactValue(block[0]))}}, ${{esc(compactValue(block[1]))}}]</span>`).join('')}}</div></article>`;
}}
function renderDiffPrefixPattern(f) {{
  const state = f && f.state || {{}};
  const diff = state.diff || state.difference || state.diff_array;
  const prefix = state.prefix || state.prefix_sum || state.prefix_sums;
  const l = pointerIndexValue(state, ['l','left','range_l']);
  const r = pointerIndexValue(state, ['r','right','range_r']);
  const delta = state.delta ?? state.add ?? state.value;
  if (!Array.isArray(diff) && !Array.isArray(prefix) && (l === null || r === null)) return '';
  const impacts = [
    l !== null ? `<span class="diff-impact-point">diff[${{l}}] += ${{esc(compactValue(delta ?? 'x'))}}</span>` : '',
    r !== null ? `<span class="diff-impact-point">diff[${{r + 1}}] -= ${{esc(compactValue(delta ?? 'x'))}}</span>` : '',
    l !== null && r !== null ? `<span class="diff-impact-point">prefix[${{r + 1}}] - prefix[${{l}}]</span>` : '',
  ].filter(Boolean).join('');
  if (!impacts) return '';
  return `<article class="visual-card diff-prefix-panel" data-visual-pattern="diff_prefix"><strong>差分 / 前缀双端依赖</strong><div class="diff-impact-row">${{impacts}}</div></article>`;
}}
function renderGeometryRelationPattern(f) {{
  const state = f && f.state || {{}};
  const geometry = state.geometry || state.points && {{ points:state.points }};
  const points = geometry && Array.isArray(geometry.points) ? geometry.points : [];
  const hull = geometry && Array.isArray(geometry.hull) ? geometry.hull : [];
  const isGeometryFrame = hasVisualFamily(f, 'geometry') || (f && f.objects || []).some(o => o && o.meta && o.meta.layout === 'geometry') || points.length > 0 || hull.length > 0 || state.geometry !== undefined;
  const current = state.current ?? state.candidate;
  const popped = state.popped ?? state.removed ?? state.pop_point;
  const cross = state.cross ?? state.cross_product ?? state.orientation;
  const hasRelationSignal = hasVisualFamilyPattern(f, 'geometry_relation') || cross !== undefined || popped !== undefined || current !== undefined;
  if (!isGeometryFrame || !hasRelationSignal) return '';
  const turn = cross === undefined ? '' : Number(cross) > 0 ? 'left turn' : Number(cross) < 0 ? 'right turn' : 'collinear';
  const row = [
    hull.length ? visualChip(`hull: ${{hull.join('→')}}`) : '',
    current !== undefined ? visualChip(`candidate=${{compactValue(current)}}`) : '',
    cross !== undefined ? `<span class="cross-turn-badge">${{esc(turn)}} · cross=${{esc(compactValue(cross))}}</span>` : '',
    cross !== undefined ? `<span class="geo-cross-arrow">叉积方向 →</span>` : '',
    popped !== undefined ? `<span class="hull-ghost-point">popped ghost ${{esc(compactValue(popped))}}</span>` : '',
  ].filter(Boolean).join('');
  if (!row) return '';
  return `<article class="visual-card geometry-relation-card" data-visual-pattern="geometry_relation"><strong>几何方向 / hull 关系</strong><div class="geometry-relation-row">${{row}}</div></article>`;
}}
function renderNetworkFlowAugmentingPathPattern(f) {{
  const state = f && f.state || {{}};
  const path = Array.isArray(state.augmenting_path) ? state.augmenting_path : Array.isArray(state.path) && objectsWithPattern(f, 'network_flow_augmenting_path').length ? state.path : [];
  const edges = objectsWithPattern(f, 'network_flow_edge_label').filter(o => o.type === 'edge');
  if (!path.length && !edges.length) return '';
  const bottleneck = state.bottleneck ?? state.delta ?? state.augment ?? state.pushed;
  const chain = path.length ? path.map(node => `<span class="flow-delta-pill">${{esc(compactValue(node))}}</span>`).join('<span>→</span>') : edges.slice(0, 4).map(edge => `<span class="flow-delta-pill">${{esc(edge.id)}}</span>`).join('<span>→</span>');
  const deltas = edges.slice(0, 6).map(edge => `<span class="flow-delta-pill">${{esc(edge.id)}} ${{esc(edgeDisplayLabel(edge))}}</span>`).join('');
  return `<article class="visual-card network-augmenting-path-panel" data-visual-pattern="network_flow_augmenting_path"><strong>增广路径 / 瓶颈</strong><div class="augmenting-path-chain">${{chain}}${{bottleneck !== undefined ? `<span class="bottleneck-badge">bottleneck=${{esc(compactValue(bottleneck))}}</span>` : ''}}</div><div class="flow-delta-row">${{deltas}}</div></article>`;
}}
function renderBinaryPointerPattern(f) {{
  const state = f && f.state || {{}};
  const low = pointerIndexValue(state, ['low','lo','left','l']);
  const mid = pointerIndexValue(state, ['mid','middle']);
  const high = pointerIndexValue(state, ['high','hi','right','r']);
  if (low === null && mid === null && high === null) return '';
  const values = primaryLinearValues(f);
  const size = Math.max(values.length, ...[low, mid, high].filter(Number.isFinite).map(x => x + 1), 1);
  const capped = Math.min(size, 32);
  const lowBound = low === null ? 0 : low;
  const highBound = high === null ? capped - 1 : Math.min(high, capped - 1);
  const cells = Array.from({{length:capped}}, (_, i) => {{
    const inRange = i >= lowBound && i <= highBound;
    const value = i < values.length ? values[i] : i;
    const marker = i === low ? 'L' : i === mid ? 'M' : i === high ? 'H' : '';
    return `<span class="pointer-slot-cell ${{inRange ? 'in-range' : 'excluded'}}"><span>${{esc(value)}}</span><small>${{marker || i}}</small></span>`;
  }}).join('');
  const compare = binaryCompareText(f, state, mid);
  const markers = [
    low !== null ? `<span class="pointer-marker marker-low">low=${{low}}</span>` : '',
    mid !== null ? `<span class="pointer-marker marker-mid">mid=${{mid}}</span>` : '',
    high !== null ? `<span class="pointer-marker marker-high">high=${{high}}</span>` : '',
  ].join('');
  return `<article class="visual-card binary-pointer-panel" data-visual-pattern="binary_pointer"><strong>二分 / 指针区间</strong><div class="pointer-track" style="--slot-count:${{capped}}">${{cells}}<span class="search-interval-band"></span></div><div class="pointer-marker-row">${{markers}}</div>${{compare ? `<div class="relax-formula">${{esc(compare)}}</div>` : ''}}</article>`;
}}
function renderDigitDpPattern(f) {{
  const state = digitDpStateForFrame(f);
  const pos = pointerIndexValue(state, ['pos','position','digit_pos','idx']);
  const hasDigitState = pos !== null || ['tight','started','lead','limit','memo_hit','memo_key'].some(key => state[key] !== undefined);
  if (!hasDigitState && !hasVisualFamily(f, 'digit_dp')) return '';
  const digits = digitSequenceForState(state);
  const pills = [
    ['pos', pos ?? 0],
    ['tight', state.tight ?? state.limit],
    ['started', state.started ?? state.lead],
    ['memo', state.memo_hit ?? state.memo_key],
    ['state', state.dp_state ?? state.state_key],
  ].filter(([,value]) => value !== undefined && value !== null && value !== '');
  const digitRow = digits.length ? `<div class="digit-row">${{digits.slice(0, 24).map((digit, index) => `<span class="digit-cell ${{index === pos ? 'hot' : ''}}">${{esc(digit)}}</span>`).join('')}}</div>` : '';
  return `<article class="visual-card digit-dp-card" data-visual-pattern="digit_dp_state"><strong>数位 DP 当前状态</strong>${{digitRow}}<div class="digit-dp-state">${{pills.map(([key,value]) => `<span class="digit-dp-pill"><span>${{esc(key)}}</span><strong>${{esc(compactValue(value))}}</strong></span>`).join('')}}</div></article>`;
}}
function digitDpStateForFrame(f) {{
  const original = f && f.state || {{}};
  const extracted = digitDpStateFromTargets(f) || digitDpStateFromStack(original);
  if (!extracted) return original;
  return Object.assign({{}}, original, extracted);
}}
function digitDpStateFromTargets(f) {{
  const ids = [
    ...((f && f.evidence && Array.isArray(f.evidence.targets)) ? f.evidence.targets : []),
    ...((f && f.evidence && Array.isArray(f.evidence.deps)) ? f.evidence.deps : []),
  ].map(String);
  for (const id of ids) {{
    const parsed = digitDpStateFromCallText(id);
    if (parsed) return parsed;
  }}
  return null;
}}
function digitDpStateFromStack(state) {{
  const stack = state && (state.call_stack || state.recursion_stack || state['递归栈']);
  if (!Array.isArray(stack) || !stack.length) return null;
  for (let i = stack.length - 1; i >= 0; i -= 1) {{
    const parsed = digitDpStateFromCallText(stack[i]);
    if (parsed) return parsed;
  }}
  return null;
}}
function digitDpStateFromCallText(value) {{
  const raw = String(value || '');
  const match = raw.match(/dfs\\(([^()]*)\\)/i) || raw.match(/dp\\(([^()]*)\\)/i);
  if (!match || !match[1]) return null;
  const result = {{}};
  for (const part of match[1].split(',')) {{
    const cleaned = part.trim();
    if (!cleaned) continue;
    const pair = cleaned.split('=');
    if (pair.length >= 2) {{
      const key = pair[0].trim().replace(/^_+/, '');
      result[key] = parseDigitDpScalar(pair.slice(1).join('=').trim());
    }} else if (result.pos === undefined) {{
      result.pos = parseDigitDpScalar(cleaned);
    }}
  }}
  return Object.keys(result).length ? result : null;
}}
function parseDigitDpScalar(value) {{
  const text = String(value || '').trim();
  if (/^-?\\d+$/.test(text)) return Number(text);
  if (/^(true|false)$/i.test(text)) return /^true$/i.test(text);
  return text;
}}
function renderMonotonicStackPattern(f) {{
  const state = f && f.state || {{}};
  const stack = Array.isArray(state.stack) ? state.stack : Array.isArray(state.monotonic_stack) ? state.monotonic_stack : hasVisualFamily(f, 'monotonic_stack') ? [] : null;
  const values = primaryLinearValues(f, ['temperatures','nums','arr','array','prices','heights']);
  if (!stack || !values.length) return '';
  const current = pointerIndexValue(state, ['i','idx','index','current_index']);
  const answer = Array.isArray(state.answer) ? state.answer : Array.isArray(state.ans) ? state.ans : null;
  const cells = values.slice(0, 28).map((value, i) => `<span class="mono-cell ${{i === current ? 'current' : ''}}">${{esc(value)}}<small>${{i}}</small></span>`).join('');
  const stackItems = stack.slice(-8).map(item => `<span class="mono-stack-item">${{esc(compactValue(item))}}</span>`).join('');
  const change = eventChangeRows(f).find(row => String(row.target || '').includes('answer') || String(row.target || '').includes('ans'));
  const arrow = change ? `<div class="stack-pop-arrow">pop → ${{esc(change.target)}}：${{esc(compactValue(change.before))}} → ${{esc(compactValue(change.after))}}</div>` : '';
  const compare = current !== null && stack.length ? `<div class="relax-formula">比较 current=${{current}} 与栈顶 ${{esc(compactValue(stack[stack.length - 1]))}}</div>` : '';
  const answerHint = answer ? `<div class="visual-chip-row">${{visualChip(`answer: ${{compactValue(answer)}}`)}}</div>` : '';
  return `<article class="visual-card monotonic-stack-panel" data-visual-pattern="monotonic_stack"><strong>单调栈扫描</strong><div class="mono-layout"><div class="mono-array">${{cells}}</div><div class="mono-stack">${{stackItems}}</div></div>${{compare}}${{arrow}}${{answerHint}}</article>`;
}}
function renderHeapSiftPattern(f) {{
  const state = f && f.state || {{}};
  const heap = Array.isArray(state.heap) ? state.heap : Array.isArray(state.min_heap) ? state.min_heap : Array.isArray(state.max_heap) ? state.max_heap : null;
  const values = heap && heap.length ? heap : hasVisualFamily(f, 'heap') ? primaryLinearValues(f, ['heap','min_heap','max_heap','nums','values','arr']) : [];
  if (!values || !values.length) return '';
  const path = heapPathForState(state, values.length);
  const capacity = state.k ?? state.capacity ?? state.heap_capacity;
  const evicted = state.evicted ?? state.removed ?? state.popped;
  const row = values.slice(0, 31).map((value, i) => `<span class="heap-sift-node ${{path.includes(i) ? 'heap-sift-path' : ''}}">${{esc(compactValue(value))}}</span>`).join('');
  const chips = [
    capacity !== undefined ? visualChip(`k=${{capacity}}`) : '',
    evicted !== undefined ? visualChip(`淘汰=${{compactValue(evicted)}}`) : '',
    path.length ? visualChip(`sift path=${{path.join('→')}}`) : '',
  ].join('');
  return `<article class="visual-card heap-sift-panel" data-visual-pattern="heap_sift_path"><strong>堆上浮 / 下沉路径</strong><div class="heap-sift-row">${{row}}</div><div class="visual-chip-row">${{chips}}</div></article>`;
}}
function renderGraphMetricOverlay(f) {{
  const state = f && f.state || {{}};
  const metricKeys = ['dist','distance','dfn','low','indegree','color'];
  const metrics = metricKeys.filter(key => state[key] && typeof state[key] === 'object' && !Array.isArray(state[key]));
  const frontier = graphFrontierValues(state);
  const relax = graphRelaxFormula(f, state);
  if (!metrics.length && !frontier.length && !relax) return '';
  const nodeIds = unique(metrics.flatMap(key => Object.keys(state[key] || {{}}))).slice(0, 12);
  const rows = nodeIds.map(node => {{
    const parts = metrics.map(key => state[key][node] !== undefined ? `${{key}}=${{compactValue(state[key][node])}}` : '').filter(Boolean).join(' · ');
    return `<span class="graph-node-metric"><strong>${{esc(node)}}</strong>${{esc(parts)}}</span>`;
  }}).join('');
  const frontierDock = frontier.length ? `<div class="frontier-dock">${{frontier.slice(0, 10).map(value => visualChip(`frontier ${{value}}`)).join('')}}</div>` : '';
  return `<article class="visual-card graph-metric-overlay" data-visual-pattern="graph_metric_overlay"><strong>图节点指标 / frontier</strong><div class="graph-metric-grid">${{rows}}</div>${{frontierDock}}${{relax ? `<div class="relax-formula">${{esc(relax)}}</div>` : ''}}</article>`;
}}
function renderTreeDpOverlay(f) {{
  const state = f && f.state || {{}};
  const nodeValues = treeDpNodeValues(state);
  if (!nodeValues.length) return '';
  const rows = nodeValues.slice(0, 12).map(([node, value]) => {{
    const take = value && typeof value === 'object' ? value.take ?? value.rob ?? value.include : undefined;
    const skip = value && typeof value === 'object' ? value.skip ?? value.not_rob ?? value.exclude : undefined;
    const ret = value && typeof value === 'object' ? value.return_value ?? value.best ?? value.value : value;
    const parts = [
      take !== undefined ? `take=${{compactValue(take)}}` : '',
      skip !== undefined ? `skip=${{compactValue(skip)}}` : '',
      ret !== undefined ? `return=${{compactValue(ret)}}` : '',
    ].filter(Boolean).join(' · ');
    return `<span class="tree-dp-badge"><strong>${{esc(node)}}</strong>${{esc(parts || compactValue(value))}}</span>`;
  }}).join('');
  return `<article class="visual-card tree-dp-overlay" data-visual-pattern="tree_dp_overlay"><strong>树形 DP take / skip / return</strong><div class="tree-dp-grid">${{rows}}</div></article>`;
}}
function renderMathBitPanel(f) {{
  const items = mathBitItems(f);
  if (!items.length) return '';
  return `<section class="math-bit-panel" aria-label="数学和 bit 状态机"><h3>数学 / bit 状态机</h3><div class="math-bit-grid">${{items.join('')}}</div></section>`;
}}
function mathBitItems(frameOrState) {{
  const f = frameOrState && frameOrState.evidence ? frameOrState : null;
  const state = f ? (f.state || {{}}) : (frameOrState || {{}});
  const items = [];
  const a = numberOrNull(state.a ?? state.x);
  const b = numberOrNull(state.b ?? state.y);
  if (a !== null && b !== null && (state.remainder !== undefined || state.mod !== undefined || state.gcd !== undefined)) {{
    const r = numberOrNull(state.remainder ?? state.mod ?? (b ? a % b : 0));
    const q = numberOrNull(state.quotient ?? state.q ?? (b ? Math.floor(a / b) : 0));
    items.push(`<div class="gcd-chain" data-math-kind="gcd"><span class="math-token">${{a}} = ${{q}} × ${{b}} + ${{r}}</span><span>余数流入下一轮</span><span class="math-token">gcd(${{b}}, ${{r}})</span></div>`);
  }}
  if (state.lowbit !== undefined || state.negative_x !== undefined || state.neg_x !== undefined || hasVisualFamilyPattern(f, 'lowbit_state')) {{
    const x = numberOrNull(state.x ?? state.value ?? state.remaining ?? state.n);
    const neg = numberOrNull(state.negative_x ?? state.neg_x ?? (x === null ? null : -x));
    const low = numberOrNull(state.lowbit ?? (x === null ? null : (x & -x)));
    items.push(renderBitRows([['x', x], ['-x', neg], ['x & -x', low]]));
  }}
  if (state.exponent !== undefined || state.exp !== undefined || state.power !== undefined || state.base !== undefined && state.result !== undefined) {{
    const exp = numberOrNull(state.exponent ?? state.exp);
    const bits = exp === null ? '' : exp.toString(2);
    items.push(`<div class="fast-power-row" data-math-kind="fast_power"><span class="math-token">base=${{esc(state.base ?? '')}}</span><span class="math-token">result=${{esc(state.result ?? 1)}}</span>${{bits ? `<span class="math-token">exp₂=${{esc(bits)}}</span>` : ''}}<span>当前位为 1 时乘入 result，否则只平方 base。</span></div>`);
  }}
  const sieve = state.sieve || state.is_prime || state.prime || state.composite;
  if (Array.isArray(sieve)) {{
    items.push(renderSieveGrid(sieve, state.current_prime ?? state.prime_i ?? state.p));
  }}
  return items;
}}
function renderBitRows(rows) {{
  const clean = rows.filter(([,value]) => value !== null && value !== undefined);
  if (!clean.length) return '';
  const width = Math.max(4, ...clean.map(([,value]) => Math.abs(Number(value)).toString(2).length));
  return `<div data-math-kind="lowbit">${{clean.map(([label,value]) => {{
    const bits = unsignedBits(Number(value), width);
    return `<div class="bit-row"><span>${{esc(label)}}</span><span class="bit-cells">${{bits.map(bit => `<span class="bit-cell ${{bit === '1' ? 'on' : ''}}">${{bit}}</span>`).join('')}}</span></div>`;
  }}).join('')}}</div>`;
}}
function unsignedBits(value, width) {{
  const mask = width >= 30 ? value : (value & ((1 << width) - 1));
  return Math.abs(mask).toString(2).padStart(width, '0').slice(-width).split('');
}}
function renderSieveGrid(values, currentPrime) {{
  const current = numberOrNull(currentPrime);
  const cells = values.map((value, index) => {{
    const isPrime = value === true || value === 1 || value === 'prime';
    const cls = isPrime ? 'prime' : 'composite';
    const hot = current !== null && index % current === 0 && index >= current * current ? ' hot' : '';
    return `<span class="sieve-num ${{cls}}${{hot}}">${{index}}</span>`;
  }}).join('');
  return `<div class="sieve-grid" data-math-kind="sieve">${{cells}}</div>`;
}}
function numberOrNull(value) {{
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}}
function pointerIndexValue(state, keys) {{
  for (const key of keys || []) {{
    const n = numberOrNull(state && state[key]);
    if (n !== null && Number.isInteger(n)) return n;
  }}
  return null;
}}
function visualFamilyHint(f) {{
  const evidence = f && f.evidence || {{}};
  return String(evidence.visual_family || '').trim();
}}
function hasVisualFamily(f, family) {{
  return visualFamilyHint(f) === family;
}}
function hasVisualFamilyPattern(f, pattern) {{
  const evidence = f && f.evidence || {{}};
  if (String(evidence.visual_family_pattern || '') === pattern) return true;
  return (evidence.visual_patterns || []).some(item => String(item && item.pattern || item) === pattern);
}}
function primaryLinearValues(f, preferredKeys) {{
  const state = f && f.state || {{}};
  const keys = [...(preferredKeys || []), 'nums','arr','array','values','temperatures','prices','heights','dp'];
  for (const key of keys) {{
    if (Array.isArray(state[key]) && state[key].every(item => !Array.isArray(item) && (item === null || typeof item !== 'object'))) return state[key];
  }}
  const containers = (f && f.objects || []).filter(o => o.type === 'container' && o.meta && ['array','string'].includes(o.meta.layout));
  const container = containers[0];
  if (!container) return [];
  return (f.objects || [])
    .filter(o => o.parent === container.id && o.type === 'cell')
    .sort((a,b)=>(a.index??0)-(b.index??0))
    .map(o => o.value);
}}
function binaryCompareText(f, state, mid) {{
  const teaching = f && f.teaching || {{}};
  if (teaching.formula) return teaching.formula;
  const evidence = f && f.evidence || {{}};
  if (evidence.process && evidence.process.summary) return evidence.process.summary;
  const target = state.target ?? state.target_value ?? state.x ?? state.n;
  if (mid !== null && target !== undefined) return `judge(mid=${{mid}}, target=${{compactValue(target)}})`;
  return '';
}}
function digitSequenceForState(state) {{
  const raw = state.digits ?? state.num_digits ?? state.number ?? state.n ?? state.s;
  if (Array.isArray(raw)) return raw.map(String);
  if (raw === undefined || raw === null || typeof raw === 'object') return [];
  return String(raw).split('');
}}
function heapPathForState(state, heapLength) {{
  const explicit = state.sift_path ?? state.heap_path ?? state.path;
  if (Array.isArray(explicit)) return explicit.map(Number).filter(n => Number.isInteger(n) && n >= 0 && n < heapLength);
  const index = pointerIndexValue(state, ['heap_index','idx','i']);
  if (index === null) return [];
  const path = [];
  let cur = index;
  while (cur >= 0 && path.length < 12) {{
    path.push(cur);
    if (cur === 0) break;
    cur = Math.floor((cur - 1) / 2);
  }}
  return path.reverse();
}}
function graphFrontierValues(state) {{
  for (const key of ['frontier','queue','deque','stack','pq','priority_queue','open_set']) {{
    const value = state[key];
    if (Array.isArray(value)) return value.map(compactValue);
  }}
  return [];
}}
function graphRelaxFormula(f, state) {{
  const teaching = f && f.teaching || {{}};
  if (teaching.formula) return teaching.formula;
  const evidence = f && f.evidence || {{}};
  const edge = (evidence.deps || []).find(id => String(id).startsWith('edge:'));
  const target = (evidence.targets || []).find(id => String(id).startsWith('node:'));
  if (edge && target) return `${{edge}} relaxes ${{target}}`;
  const current = state.current ?? state.u ?? state.node;
  const next = state.next ?? state.v ?? state.neighbor;
  const weight = state.weight ?? state.w;
  if (current !== undefined && next !== undefined) return `dist[${{current}}] + ${{weight ?? 'w'}} < dist[${{next}}]`;
  return '';
}}
function treeDpNodeValues(state) {{
  for (const key of ['tree_dp','dp_tree','node_dp','returns','return_values']) {{
    const value = state[key];
    if (value && typeof value === 'object' && !Array.isArray(value)) return Object.entries(value);
  }}
  const take = state.take ?? state.rob ?? state.include;
  const skip = state.skip ?? state.not_rob ?? state.exclude;
  const node = state.node ?? state.current ?? state.current_node;
  if (node !== undefined && (take !== undefined || skip !== undefined || state.return_value !== undefined)) {{
    return [[String(node), {{ take, skip, return_value:state.return_value ?? state.best }}]];
  }}
  return [];
}}
function objectsWithPattern(f, pattern) {{
  return (f.objects || []).filter(o => objectPatterns(o).includes(pattern));
}}
function objectPatterns(o) {{
  const meta = o && o.meta || {{}};
  const raw = Array.isArray(meta.visual_patterns) ? [...meta.visual_patterns] : (meta.visual_patterns ? [meta.visual_patterns] : []);
  if (meta.visual_pattern) raw.push(meta.visual_pattern);
  return [...new Set(raw.map(String).filter(Boolean))];
}}
function objectMetaClass(o) {{
  const patternClasses = objectPatterns(o).map(value => `pattern-${{cssToken(value)}}`);
  const role = o && o.meta && o.meta.pattern_role ? [`role-${{cssToken(o.meta.pattern_role)}}`] : [];
  return [...patternClasses, ...role].join(' ');
}}
function cssToken(value) {{
  return String(value || '').replace(/_/g, '-').replace(/[^a-zA-Z0-9-]/g, '-').toLowerCase();
}}
function visualChip(value) {{
  return `<span class="visual-chip">${{esc(value)}}</span>`;
}}
function edgeDisplayLabel(edge) {{
  if (!edge) return '';
  const meta = edge.meta || {{}};
  if (edge.label) return String(edge.label);
  if (meta.edge_label) return String(meta.edge_label);
  const parts = [];
  if (meta.flow !== undefined || meta.capacity !== undefined) parts.push(`${{meta.flow ?? 0}}/${{meta.capacity ?? '?'}}`);
  if (meta.residual !== undefined) parts.push(`res ${{meta.residual}}`);
  if (meta.weight !== undefined) parts.push(String(meta.weight));
  return parts.join(' · ');
}}
function renderDependencyFlow(f) {{
  const edges = dependencyEdges(f);
  if (!edges.length) return '';
  return `<div class="dependency-flow" aria-label="依赖关系"><h3>依赖关系</h3>${{edges.map(edge => `<div class="dependency-edge" data-source="${{esc(edge.source)}}" data-target="${{esc(edge.target)}}"><span class="dependency-node dep clickable-object" ${{clickableAttrs(edge.source)}}>${{dependencyLabel(f, edge.source)}}</span><span class="dependency-arrow">→</span><span class="dependency-node target clickable-object" ${{clickableAttrs(edge.target)}}>${{dependencyLabel(f, edge.target)}}</span></div>`).join('')}}</div>`;
}}
function dependencyEdges(f) {{
  const arrows = (f.objects || []).filter(o => o.type === 'arrow' && o.source && o.target);
  if (arrows.length) return arrows.map(o => ({{ source:String(o.source), target:String(o.target) }}));
  const evidence = f.evidence || {{}};
  const deps = Array.isArray(evidence.deps) ? evidence.deps.filter(Boolean) : [];
  const targets = Array.isArray(evidence.targets) ? evidence.targets.filter(Boolean) : [];
  const edges = [];
  for (const dep of deps) for (const target of targets) edges.push({{ source:String(dep), target:String(target) }});
  return edges;
}}
function objectById(f) {{
  return new Map((f.objects || []).map(o => [o.id, o]));
}}
function dependencyLabel(f, id) {{
  const object = objectById(f).get(id);
  if (!object) return esc(id);
  const base = object.label || object.id || id;
  if (object.value === undefined || object.value === null || object.value === '') return esc(base);
  return esc(`${{base}} = ${{compactValue(object.value)}}`);
}}
function clickableAttrs(id) {{
  if (!id) return '';
  return `data-object-id="${{esc(id)}}" onclick="showDependencyDetail('${{encodeURIComponent(id)}}')"`;
}}
function roleForObject(f, id) {{
  const mark = (f.marks || []).find(m => m.target === id);
  return mark && mark.role ? mark.role : '';
}}
function showDependencyDetail(encodedId) {{
  const f = frame();
  const id = canonicalDetailObjectId(decodeURIComponent(encodedId), f);
  const edges = dependencyEdges(f);
  const deps = unique(edges.filter(edge => edge.target === id).map(edge => edge.source));
  const impacts = unique(edges.filter(edge => edge.source === id).map(edge => edge.target));
  const role = roleForObject(f, id);
  const object = objectById(f).get(id);
  const container = objectContainerInfo(f, object);
  const objectId = object && object.id;
  const change = eventChangeRows(f).find(row => row.target === id || objectId && row.target === objectId);
  const detail = $('dependency-detail');
  if (!detail) return;
  const depText = deps.length ? deps.map(x => `${{dependencyLabel(f, x)}} <code>${{esc(x)}}</code>`).join('，') : '无';
  const impactText = impacts.length ? impacts.map(x => `${{dependencyLabel(f, x)}} <code>${{esc(x)}}</code>`).join('，') : '无';
  const roleText = role ? `<p>角色：${{esc(role)}}</p>` : '<p>角色：未标注</p>';
  const valueText = object && object.value !== undefined ? `<p>值：<code>${{esc(compactValue(object.value))}}</code></p>` : '';
  const containerText = container ? `<p>所属容器：<code>${{esc(container.id)}}</code> · layout <code>${{esc(container.layout)}}</code></p>` : '';
  const beforeAfterText = change && (change.before !== undefined || change.after !== undefined)
    ? `<p>before：<code>${{esc(compactValue(change.before))}}</code></p><p>after：<code>${{esc(compactValue(change.after))}}</code></p>`
    : '';
  detail.innerHTML = `<strong>${{dependencyLabel(f, id)}} <code>${{esc(id)}}</code></strong>${{roleText}}${{valueText}}${{containerText}}${{beforeAfterText}}<p>依赖对象：${{depText}}</p><p>影响对象：${{impactText}}</p><p>来源：SceneGraph marks、dependency arrows 和 evidence.deps / evidence.targets。</p>`;
}}
function canonicalDetailObjectId(rawId, f) {{
  const raw = String(rawId || '');
  if (!['answer','ans','result'].includes(raw)) return raw;
  const evidence = f && f.evidence || {{}};
  const candidates = [
    ...(Array.isArray(evidence.targets) ? evidence.targets : []),
    ...((f && f.marks || []).filter(m => m.role === 'answer').map(m => m.target)),
  ].map(String);
  return candidates.find(id => isAnswerLikeContainer(id) && id !== raw) || raw;
}}
function objectContainerInfo(f, object) {{
  if (!object) return null;
  const parent = object.parent || '';
  const container = (f.objects || []).find(o => o.type === 'container' && o.id === parent);
  if (!container) return parent ? {{ id:parent, layout:'unknown' }} : null;
  return {{ id:container.id, layout:container.meta && container.meta.layout || 'generic' }};
}}
function unique(items) {{
  return [...new Set((items || []).filter(Boolean).map(String))];
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
      const a = spatialEndpoint(arrow.source, positions), b = spatialEndpoint(arrow.target, positions);
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
    const flow = document.getElementById('spatial-dependency-flow');
    if (flow) flow.innerHTML = renderDependencyFlow(f);
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
    canvasHost.innerHTML = '<div class="spatial-wrap"><canvas id="spatial-canvas" class="spatial-stage"></canvas><div id="spatial-label" class="spatial-label"></div><div id="spatial-dependency-flow"></div></div>';
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
function spatialEndpoint(id, positions) {{
  if (!id) return null;
  if (positions[id]) return positions[id];
  const raw = String(id);
  if (raw.startsWith('frame:')) {{
    const match = raw.match(/\(([^()]*)\)/);
    const key = match && match[1] ? match[1] : raw.replace(/^frame:[^(]+/, '').replace(/[()]/g, '');
    if (positions[`node:${{key}}`]) return positions[`node:${{key}}`];
    if (positions[key]) return positions[key];
  }}
  return null;
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
  if (renderer === 'set_grid') return renderSetGrid(c, children, marks);
  if (renderer === 'array') return renderArray(c, cells, marks);
  if (renderer === 'string') return renderString(c, cells, marks);
  if (renderer === 'heap') return renderHeap(c, cells, marks);
  if (renderer === 'queue') return renderQueue(c, cells, marks);
  if (renderer === 'stack') return renderStack(c, cells, marks);
  if (renderer === 'graph') return renderGraph(c, children, marks);
  if (renderer === 'tree') return renderTree(c, children, marks, layout);
  if (renderer === 'linked_list') return renderLinkedList(c, children, marks);
  if (renderer === 'geometry') return renderGeometry(c, children, marks);
  if (renderer === 'ml') return renderML(c, children, marks);
  if (layout === 'frame') return renderFrameStage(c);
  if (renderer === 'map') return renderMap(c, children, marks);
  return renderMap(c, children, marks);
}}
function renderFrameStage(c) {{
  return `<div class="frame-stage-card"><strong>${{esc(c.label || c.id.replace(/^frame:/,''))}}</strong><span>阶段切换 / 递归帧</span></div>`;
}}
function renderArray(c, cells, marks) {{
  cells.sort((a,b)=>cellLinearIndex(a)-cellLinearIndex(b));
  const state = frame().state || {{}};
  if (shouldRenderFunctionalCycleArray(c, cells, state)) return renderFunctionalCycleArray(c, cells, marks, state);
  const pointers = currentPointersFor(c.id);
  const pointerByIndex = new Map();
  for (const p of pointers) {{
    if (!pointerByIndex.has(p.index)) pointerByIndex.set(p.index, []);
    pointerByIndex.get(p.index).push(p);
  }}
  const cellHtml = cells.map((o, i) => `<div class="cell clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}><span class="idx">${{esc(cellDisplayIndex(o, i))}}</span>${{esc(o.value)}}</div>`).join('');
  const pointerHtml = cells.map(o => `<div class="pointer-slot">${{(pointerByIndex.get(o.index) || []).map(p => `<span class="pointer-tag clickable-object" ${{clickableAttrs(p.id)}}>${{esc(p.label || p.id.replace('pointer:',''))}}</span>`).join('')}}</div>`).join('');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="array-wrap"><div class="array">${{cellHtml}}</div><div class="pointer-row" style="grid-template-columns:repeat(${{Math.max(cells.length,1)}},42px)">${{pointerHtml}}</div></div></div>`;
}}
function cellLinearIndex(cell) {{
  const index = Number(cell && cell.index);
  if (Number.isInteger(index)) return index;
  const row = Number(cell && cell.row);
  const col = Number(cell && cell.col);
  if (Number.isInteger(row) && Number.isInteger(col)) return row * 1000 + col;
  if (Number.isInteger(row)) return row;
  if (Number.isInteger(col)) return col;
  return 0;
}}
function cellDisplayIndex(cell, fallback) {{
  if (cell && cell.index !== undefined && cell.index !== null) return compactValue(cell.index);
  const row = Number(cell && cell.row);
  const col = Number(cell && cell.col);
  if (Number.isInteger(row) && Number.isInteger(col)) return col === 0 ? String(row) : `${{row}},${{col}}`;
  if (Number.isInteger(row)) return String(row);
  if (Number.isInteger(col)) return String(col);
  return String(fallback);
}}
function shouldRenderFunctionalCycleArray(c, cells, state) {{
  if (!c || !cells || !cells.length || state.slow === undefined || state.fast === undefined) return false;
  const values = cells.map(cell => Number(cell.value));
  return values.every(value => Number.isInteger(value) && value >= 0 && value < cells.length);
}}
function renderFunctionalCycleArray(c, cells, marks, state) {{
  const w=760,h=380,cx=w/2,cy=h/2+8,rx=250,ry=128;
  const pos={{}};
  cells.forEach((cell, i) => {{
    const a=-Math.PI/2 + 2*Math.PI*i/Math.max(1, cells.length);
    pos[i]=[cx+rx*Math.cos(a), cy+ry*Math.sin(a)];
  }});
  const edges = cells.map((cell, i) => {{
    const target = Number(cell.value);
    const a=pos[i], b=pos[target]; if(!a||!b) return '';
    const mx=(a[0]+b[0])/2, my=(a[1]+b[1])/2 - (i === target ? 60 : 34);
    const cls = target <= i ? 'cycle' : '';
    return `<path class="cycle-edge ${{cls}} clickable-object" ${{clickableAttrs(`${{c.id}}[${{i}}]`)}} d="M${{a[0]}},${{a[1]}} Q${{mx}},${{my}} ${{b[0]}},${{b[1]}}"></path>`;
  }}).join('');
  const pointerNames = new Map();
  for (const name of ['slow','fast']) {{
    const idx = Number(state[name]);
    if (!Number.isInteger(idx) || !pos[idx]) continue;
    if (!pointerNames.has(idx)) pointerNames.set(idx, []);
    pointerNames.get(idx).push(name);
  }}
  const nodes = cells.map((cell, i) => {{
    const p=pos[i];
    const tokens=(pointerNames.get(i) || []).map((name, j) => `<text class="cycle-token" x="0" y="${{-46 - j * 15}}" text-anchor="middle">${{esc(name)}}</text>`).join('');
    const cls = `${{markClass(cell.id, marks)}} ${{objectMetaClass(cell)}} ${{pointerNames.has(i) ? 'hot' : ''}}`;
    return `<g class="cycle-node node clickable-object ${{cls}}" ${{clickableAttrs(cell.id)}} transform="translate(${{p[0]}},${{p[1]}})"><circle r="34"></circle><text text-anchor="middle" y="-4" font-size="14" font-weight="800">${{i}}</text><text text-anchor="middle" y="15" font-size="11" fill="#64748b">→ ${{esc(cell.value)}}</text>${{tokens}}</g>`;
  }}).join('');
  const meet = Number(state.slow) === Number(state.fast) ? `<text x="${{cx}}" y="${{h - 26}}" text-anchor="middle" fill="#166534" font-size="13" font-weight="800">slow 与 fast 相遇：${{esc(compactValue(state.slow))}}</text>` : '';
  return `<div><h3 class="view-title">${{esc(c.label || '环形下标链表')}}</h3><svg class="cycle-list-svg" viewBox="0 0 ${{w}} ${{h}}"><defs><marker id="cycle-arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#64748b"></path></marker></defs>${{edges}}${{nodes}}${{meet}}</svg></div>`;
}}
function renderMatrix(c, cells, marks) {{
  const rows = Math.max(0, ...cells.map(o => o.row ?? 0)) + 1;
  const cols = Math.max(0, ...cells.map(o => o.col ?? 0)) + 1;
  const by = new Map(cells.map(o => [`${{o.row}},${{o.col}}`, o]));
  let body = '';
  for (let r=0; r<rows; r++) for (let col=0; col<cols; col++) {{
    const o = by.get(`${{r}},${{col}}`) || {{id:'', value:''}};
    body += `<div class="mcell clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}>${{esc(o.value)}}</div>`;
  }}
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="matrix" style="grid-template-columns:repeat(${{Math.max(cols,1)}},44px)">${{body}}</div></div>`;
}}
function renderSetGrid(c, children, marks) {{
  const rows = new Map();
  for (const o of children || []) {{
    if (!Number.isInteger(Number(o.row))) continue;
    const row = Number(o.row);
    if (!rows.has(row)) rows.set(row, {{ label:null, cells:[] }});
    if (o.type === 'label') rows.get(row).label = o;
    if (o.type === 'cell') rows.get(row).cells.push(o);
  }}
  const cards = Array.from(rows.entries()).sort((a,b)=>a[0]-b[0]).map(([row, entry]) => {{
    const label = entry.label || {{ id:`${{c.id}}[${{row}}]`, value:'[]', label:String(row) }};
    const cells = (entry.cells || []).sort((a,b)=>(a.col??0)-(b.col??0));
    const values = cells.length
      ? cells.map(o => `<span class="set-token clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}>${{esc(o.value)}}</span>`).join('')
      : `<span class="set-empty">${{esc(label.value || '[]')}}</span>`;
    return `<article class="set-card clickable-object ${{markClass(label.id, marks)}} ${{objectMetaClass(label)}}" ${{clickableAttrs(label.id)}} data-set-row="${{row}}"><span class="set-index">${{esc(label.label || row)}}</span><span class="set-values">${{values}}</span></article>`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="set-grid" data-visual-pattern="set_grid">${{cards}}</div></div>`;
}}
function renderString(c, cells, marks) {{
  return renderArray(c, cells, marks);
}}
function renderHeap(c, cells, marks) {{
  cells.sort((a,b)=>(a.index??0)-(b.index??0));
  const w=760,h=380;
  const state = frame().state || {{}};
  const path = heapPathForState(state, Math.max(cells.length, 1));
  const pathEdges = new Set(path.slice(1).map(i => `${{Math.floor((i - 1) / 2)}}-${{i}}`));
  const pos={{}};
  cells.forEach((cell, i) => {{
    const level = Math.floor(Math.log2(i + 1));
    const first = Math.pow(2, level) - 1;
    const indexInLevel = i - first;
    const count = Math.pow(2, level);
    pos[i] = [((indexInLevel + 1) * w) / (count + 1), 52 + level * 78];
  }});
  const edges = cells.slice(1).map((cell, i0) => {{
    const i = i0 + 1;
    const parent = Math.floor((i - 1) / 2);
    const a=pos[parent], b=pos[i]; if(!a||!b) return '';
    const cls = pathEdges.has(`${{parent}}-${{i}}`) ? 'heap-sift-path' : '';
    return `<line class="heap-edge ${{cls}}" x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"></line>`;
  }}).join('');
  const nodes = cells.map((cell, i) => {{
    const p=pos[i];
    const cls = `${{markClass(cell.id, marks)}} ${{objectMetaClass(cell)}} ${{path.includes(i) ? 'heap-sift-path' : ''}}`;
    return `<g class="heap-node clickable-object ${{cls}}" ${{clickableAttrs(cell.id)}} transform="translate(${{p[0]}},${{p[1]}})"><circle r="28"></circle><text text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="750">${{esc(cell.value)}}</text><text y="45" text-anchor="middle" fill="#64748b" font-size="11">${{i}}</text></g>`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><svg class="heap-svg" viewBox="0 0 ${{w}} ${{h}}">${{edges}}${{nodes}}</svg></div>`;
}}
function renderStack(c, cells, marks) {{
  cells.sort((a,b)=>(a.index??0)-(b.index??0));
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="stack">${{cells.map(o => `<div class="stack-item clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}>${{esc(o.value)}}</div>`).join('')}}</div></div>`;
}}
function renderQueue(c, cells, marks) {{
  cells.sort((a,b)=>(a.index??0)-(b.index??0));
  const body = cells.map((o,i) => `<div class="cell clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}><span class="idx">${{i===0?'头':i===cells.length-1?'尾':o.index}}</span>${{esc(o.value)}}</div>`).join('');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="queue">${{body}}</div></div>`;
}}
function renderLinkedList(c, children, marks) {{
  const nodes = children.filter(o => o.type === 'node');
  const edges = children.filter(o => o.type === 'edge');
  const state = frame().state || {{}};
  const outgoing = new Map(edges.map(e => [e.source, e]));
  const incoming = new Set(edges.map(e => e.target));
  let current = nodes.find(n => !incoming.has(n.id)) || nodes[0];
  const ordered = [];
  const seen = new Set();
  while (current && !seen.has(current.id) && ordered.length <= nodes.length) {{
    ordered.push(current);
    seen.add(current.id);
    const edge = outgoing.get(current.id);
    current = edge ? nodes.find(n => n.id === edge.target) : null;
  }}
  for (const node of nodes) if (!seen.has(node.id)) ordered.push(node);
  if (shouldRenderCycleLinkedList(state, ordered, edges)) return renderCycleLinkedList(c, ordered, edges, marks, state);
  const pointers = linkedListPointers(state, ordered);
  const edgeBySource = new Map(edges.map(e => [e.source, e]));
  const body = ordered.map((node, index) => {{
    const badges = (pointers.get(node.id) || []).map(name => `<span class="pointer-badge">${{esc(name)}}</span>`).join('');
    const edge = edgeBySource.get(node.id);
    const arrowCls = edge && edge.meta && edge.meta.old_direction ? 'ghost' : edge && edge.meta && edge.meta.cycle ? 'cycle' : '';
    const arrow = index < ordered.length - 1 ? `<span class="linked-arrow ${{arrowCls}}">${{arrowCls === 'cycle' ? '↻' : '→'}}</span>` : '';
    return `<div class="linked-node-wrap"><div class="pointer-badges">${{badges}}</div><div class="linked-node clickable-object ${{markClass(node.id, marks)}} ${{objectMetaClass(node)}}" ${{clickableAttrs(node.id)}}>${{esc(node.label || node.id.replace('node:',''))}}</div></div>${{arrow}}`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || '链表')}}</h3><div class="linked-list-view">${{body}}</div></div>`;
}}
function shouldRenderCycleLinkedList(state, ordered, edges) {{
  if (!ordered.length) return false;
  if (state && (state.has_cycle === true || state.cycle_entry !== undefined || state.meeting !== undefined)) return true;
  if (state && state.slow !== undefined && state.fast !== undefined) return true;
  const indexById = new Map(ordered.map((node, i) => [node.id, i]));
  return edges.some(edge => edge.meta && edge.meta.cycle || indexById.has(edge.source) && indexById.has(edge.target) && indexById.get(edge.target) <= indexById.get(edge.source));
}}
function renderCycleLinkedList(c, ordered, edges, marks, state) {{
  const w=760,h=380,cx=w/2,cy=h/2+6,rx=250,ry=126;
  const pos={{}};
  ordered.forEach((node, i) => {{
    const a=-Math.PI/2 + 2*Math.PI*i/Math.max(1, ordered.length);
    pos[node.id]=[cx+rx*Math.cos(a),cy+ry*Math.sin(a)];
  }});
  const indexById = new Map(ordered.map((node, i) => [node.id, i]));
  const edgeSvg = edges.map(edge => {{
    const a=pos[edge.source], b=pos[edge.target]; if(!a||!b) return '';
    const cycle = edge.meta && edge.meta.cycle || indexById.get(edge.target) <= indexById.get(edge.source);
    const cls = cycle ? 'cycle' : '';
    if (cycle) {{
      const mx=(a[0]+b[0])/2, my=(a[1]+b[1])/2 - 72;
      return `<path class="cycle-edge ${{cls}} clickable-object" ${{clickableAttrs(edge.id)}} d="M${{a[0]}},${{a[1]}} Q${{mx}},${{my}} ${{b[0]}},${{b[1]}}"></path>`;
    }}
    return `<line class="cycle-edge clickable-object" ${{clickableAttrs(edge.id)}} x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"></line>`;
  }}).join('');
  const pointers = linkedListPointers(state, ordered);
  const nodeSvg = ordered.map(node => {{
    const p=pos[node.id];
    const cls=markClass(node.id, marks);
    const tokens=(pointers.get(node.id) || []).map((name, i) => `<text class="cycle-token" x="0" y="${{-40 - i * 14}}" text-anchor="middle">${{esc(name)}}</text>`).join('');
    return `<g class="cycle-node node clickable-object ${{cls}} ${{objectMetaClass(node)}}" ${{clickableAttrs(node.id)}} transform="translate(${{p[0]}},${{p[1]}})"><circle r="29"></circle><text text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="750">${{esc(node.label || node.id.replace('node:',''))}}</text>${{tokens}}</g>`;
  }}).join('');
  const meet = state.meeting !== undefined ? `<text x="${{cx}}" y="${{h - 24}}" text-anchor="middle" fill="#166534" font-size="13" font-weight="800">相遇点 / 入环证据：${{esc(compactValue(state.meeting ?? state.cycle_entry))}}</text>` : '';
  return `<div><h3 class="view-title">${{esc(c.label || '环形链表')}}</h3><svg class="cycle-list-svg" viewBox="0 0 ${{w}} ${{h}}"><defs><marker id="cycle-arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#64748b"></path></marker></defs>${{edgeSvg}}${{nodeSvg}}${{meet}}</svg></div>`;
}}
function linkedListPointers(state, orderedNodes) {{
  const nodeIds = new Set((orderedNodes || []).map(n => n.id));
  const byPlain = new Map((orderedNodes || []).map(n => [String(n.id).replace(/^node:/, ''), n.id]));
  const result = new Map();
  for (const key of ['head','prev','curr','current','next','slow','fast','tail']) {{
    const raw = state && state[key];
    const id = raw !== undefined && raw !== null ? (nodeIds.has(String(raw)) ? String(raw) : byPlain.get(String(raw)) || `node:${{raw}}`) : '';
    if (!id || !nodeIds.has(id)) continue;
    if (!result.has(id)) result.set(id, []);
    result.get(id).push(key === 'current' ? 'curr' : key);
  }}
  return result;
}}
function renderMap(c, children, marks) {{
  const rows = children.filter(o => o.id !== c.id && o.type !== 'arrow');
  return `<div><h3 class="view-title">${{esc(c.label || c.id)}}</h3><div class="mapgrid">${{rows.map(o => `<div class="maprow clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}><strong>${{esc(o.label || o.id)}}</strong><span>${{esc(typeof o.value === 'object' ? JSON.stringify(o.value) : o.value)}}</span></div>`).join('')}}</div></div>`;
}}
function renderML(c, children, marks) {{
  const rows = children.filter(o => o.id !== c.id && o.type !== 'arrow' && o.type !== 'edge');
  const body = rows.map(o => {{
    if (o.type === 'loss_curve') return `<div class="mlitem clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}><strong>${{esc(o.label || 'loss')}}</strong>${{renderSparkline(o.value)}}</div>`;
    const shape = o.meta && Array.isArray(o.meta.shape) && o.meta.shape.length ? `shape ${{o.meta.shape.join('×')}} · ` : '';
    return `<div class="mlitem clickable-object ${{markClass(o.id, marks)}} ${{objectMetaClass(o)}}" ${{clickableAttrs(o.id)}}><strong>${{esc(o.label || o.id)}}</strong><span>${{esc(shape + compactValue(o.value))}}</span></div>`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || 'ML state')}}</h3><div class="mlgrid">${{body}}</div></div>`;
}}
function compactValue(value) {{
  if (value === null || value === undefined) return '';
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value);
  return text.length > 80 ? text.slice(0, 77) + '...' : text;
}}
function stateValueSummary(value) {{
  if (Array.isArray(value)) {{
    const rows = value.length;
    const cols = Array.isArray(value[0]) ? value[0].length : null;
    const shape = cols !== null ? `${{rows}}×${{cols}}` : `${{rows}} 项`;
    return `${{shape}} · ${{compactValue(value)}}`;
  }}
  if (value && typeof value === 'object') {{
    const keys = Object.keys(value);
    return keys.length ? `${{keys.length}} 字段 · ${{compactValue(value)}}` : '{{}}';
  }}
  return compactValue(value);
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
  let nodes = children.filter(o => o.type === 'node');
  const edges = children.filter(o => o.type === 'edge');
  const nodeIds = new Set(nodes.map(n => n.id));
  for (const edge of edges) {{
    for (const endpoint of [edge.source, edge.target]) {{
      if (!endpoint || nodeIds.has(endpoint)) continue;
      nodeIds.add(endpoint);
      nodes.push({{ id:endpoint, type:'node', parent:c.id, label:String(endpoint).replace(/^node:/, '') }});
    }}
  }}
  const state = frame().state || {{}};
  const bottleneck = state.bottleneck ?? state.delta ?? state.augment ?? state.pushed;
  const w=760,h=380;
  const nodeRadius = nodes.length <= 5 ? 50 : nodes.length <= 10 ? 42 : 36;
  const hasMetricText = nodes.some(n => graphNodeMetricText(frame(), n));
  const pos=graphPositions(c, nodes, edges, state, w, h, nodeRadius, hasMetricText ? 30 : 10);
  const edgeSvg = edges.map(e => {{
    const a=pos[e.source], b=pos[e.target]; if(!a||!b) return '';
    const cls = `${{markClass(e.id, marks)}} ${{objectMetaClass(e)}} ${{graphEdgeSemanticClass(e, state)}}`;
    return `<line class="edge clickable-object ${{cls}}" ${{clickableAttrs(e.id)}} x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"></line>`;
  }}).join('');
  const edgeLabels = edges.map(e => {{
    const a=pos[e.source], b=pos[e.target], label=edgeDisplayLabel(e); if(!a||!b||!label) return '';
    return `<text class="edge-label clickable-object ${{objectMetaClass(e)}}" ${{clickableAttrs(`edge-label:${{e.id.replace(/^edge:/,'')}}`)}} x="${{(a[0]+b[0])/2}}" y="${{(a[1]+b[1])/2 - 6}}" text-anchor="middle">${{esc(label)}}</text>`;
  }}).join('');
  const bottleneckLabels = bottleneck === undefined ? '' : edges.filter(e => objectPatterns(e).includes('network_flow_augmenting_path')).map(e => {{
    const a=pos[e.source], b=pos[e.target]; if(!a||!b) return '';
    const x=(a[0]+b[0])/2, y=(a[1]+b[1])/2 + 18;
    return `<g class="flow-bottleneck-label" transform="translate(${{x}},${{y}})"><rect x="-30" y="-12" width="60" height="22" rx="7"></rect><text text-anchor="middle" y="3">瓶颈 ${{esc(compactValue(bottleneck))}}</text></g>`;
  }}).join('');
  const nodeSvg = nodes.map(n => {{
    const p=pos[n.id]; const cls=`${{markClass(n.id, marks)}} ${{objectMetaClass(n)}}`;
    const metric = graphNodeMetricText(frame(), n);
    const metricText = metric ? `<text class="graph-node-inline-metrics" y="${{nodeRadius + 17}}" text-anchor="middle">${{esc(metric)}}</text>` : '';
    return `<g class="node clickable-object ${{cls}}" ${{clickableAttrs(n.id)}} transform="translate(${{p[0]}},${{p[1]}})"><circle r="${{nodeRadius}}"></circle><text text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="750">${{esc(n.label || n.id.replace('node:',''))}}</text>${{metricText}}</g>`;
  }}).join('');
  return `<div><h3 class="view-title">${{esc(c.label || '图')}}</h3><svg class="graph-svg" viewBox="0 0 ${{w}} ${{h}}">${{edgeSvg}}${{edgeLabels}}${{bottleneckLabels}}${{nodeSvg}}</svg></div>`;
}}
function graphPositions(c, nodes, edges, state, w, h, nodeRadius, bottomExtra) {{
  const partition = bipartitePartitions(nodes, edges, state);
  if (partition) return bipartiteGraphPositions(nodes, partition.left, partition.right, w, h, nodeRadius, bottomExtra);
  const padX = nodeRadius + 26;
  const padTop = nodeRadius + 14;
  const padBottom = nodeRadius + bottomExtra;
  const cx=w/2, cy=padTop + Math.max(1, h - padTop - padBottom) / 2;
  const rx=Math.max(24, w / 2 - padX);
  const ry=Math.max(24, (h - padTop - padBottom) / 2);
  const pos={{}};
  nodes.forEach((n,i)=>{{ const a=-Math.PI/2 + 2*Math.PI*i/Math.max(1,nodes.length); pos[n.id]=[cx+rx*Math.cos(a),cy+ry*Math.sin(a)]; }});
  return pos;
}}
function bipartiteGraphPositions(nodes, leftIds, rightIds, w, h, nodeRadius, bottomExtra) {{
  const nodeByKey = graphNodeKeyMap(nodes);
  const left = unique(leftIds.map(id => nodeByKey.get(String(id)) || nodeByKey.get(`node:${{id}}`) || String(id)).filter(id => nodeByKey.has(id) || nodes.some(n => n.id === id)));
  const right = unique(rightIds.map(id => nodeByKey.get(String(id)) || nodeByKey.get(`node:${{id}}`) || String(id)).filter(id => nodeByKey.has(id) || nodes.some(n => n.id === id)));
  const assigned = new Set([...left, ...right]);
  const leftovers = nodes.map(n => n.id).filter(id => !assigned.has(id));
  leftovers.forEach((id, i) => (left.length <= right.length ? left : right).push(id));
  const pos={{}};
  const place = (ids, x) => {{
    const padTop = nodeRadius + 14;
    const padBottom = nodeRadius + bottomExtra;
    const usable = Math.max(1, h - padTop - padBottom);
    const gap = usable / Math.max(1, ids.length - 1);
    ids.forEach((id, i) => pos[id] = [x, ids.length === 1 ? padTop + usable / 2 : padTop + i * gap]);
  }};
  place(left, w * 0.27);
  place(right, w * 0.73);
  return pos;
}}
function bipartitePartitions(nodes, edges, state) {{
  const direct = directBipartitePartition(state);
  if (direct) return direct;
  const namedPartition = namedBipartitePartition(nodes);
  if (namedPartition) return namedPartition;
  const colorPartition = colorBipartitePartition(nodes, state);
  if (colorPartition) return colorPartition;
  const matchingPartition = matchingBipartitePartition(nodes, state);
  if (matchingPartition) return matchingPartition;
  return null;
}}
function namedBipartitePartition(nodes) {{
  const left = [], right = [];
  for (const node of nodes || []) {{
    const raw = String(node.label || node.id || '').replace(/^node:/, '');
    if (/^(l|left)[_:-]?\\w*/i.test(raw)) left.push(node.id);
    else if (/^(r|right)[_:-]?\\w*/i.test(raw)) right.push(node.id);
  }}
  return left.length && right.length ? {{ left, right }} : null;
}}
function directBipartitePartition(state) {{
  const left = state.left ?? state.Left ?? state.U ?? state.left_set ?? state.left_partition;
  const right = state.right ?? state.Right ?? state.V ?? state.right_set ?? state.right_partition;
  const partition = state.partition || state.partitions || state.bipartition;
  const leftList = Array.isArray(left) ? left : partition && Array.isArray(partition.left) ? partition.left : partition && Array.isArray(partition.L) ? partition.L : null;
  const rightList = Array.isArray(right) ? right : partition && Array.isArray(partition.right) ? partition.right : partition && Array.isArray(partition.R) ? partition.R : null;
  if (leftList && rightList && (leftList.length || rightList.length)) return {{ left:leftList.map(String), right:rightList.map(String) }};
  return null;
}}
function colorBipartitePartition(nodes, state) {{
  const colors = state.color || state.colors || state.colour;
  if (!colors || typeof colors !== 'object' || Array.isArray(colors)) return null;
  const groups = new Map();
  for (const node of nodes) {{
    const candidates = graphNodeKeyCandidates(node);
    const key = candidates.find(id => Object.prototype.hasOwnProperty.call(colors, id));
    if (key === undefined) continue;
    const color = String(colors[key]);
    if (!groups.has(color)) groups.set(color, []);
    groups.get(color).push(node.id);
  }}
  const entries = Array.from(groups.values()).filter(Boolean);
  if (entries.length !== 2) return null;
  return {{ left:entries[0], right:entries[1] }};
}}
function matchingBipartitePartition(nodes, state) {{
  const matching = state.matching || state.matches || state.match || state.pair || state.pairs;
  if (!matching) return null;
  const left = [], right = [];
  if (Array.isArray(matching)) {{
    matching.forEach(item => {{
      if (Array.isArray(item) && item.length >= 2) {{ left.push(String(item[0])); right.push(String(item[1])); }}
      else if (item && typeof item === 'object') {{ left.push(String(item.u ?? item.left ?? item[0] ?? '')); right.push(String(item.v ?? item.right ?? item[1] ?? '')); }}
    }});
  }} else if (typeof matching === 'object') {{
    Object.entries(matching).forEach(([k,v]) => {{ left.push(String(k)); right.push(String(v)); }});
  }}
  if (!left.length && !right.length) return null;
  return {{ left:left.filter(Boolean), right:right.filter(Boolean) }};
}}
function graphNodeKeyMap(nodes) {{
  const map = new Map();
  for (const node of nodes) for (const key of graphNodeKeyCandidates(node)) map.set(key, node.id);
  return map;
}}
function graphNodeKeyCandidates(node) {{
  const raw = String(node && node.id || '');
  const plain = raw.replace(/^node:/, '');
  const label = String(node && node.label || '');
  return unique([raw, plain, label]);
}}
function graphEdgeSemanticClass(edge, state) {{
  const classes = [];
  if (edgeInCollection(edge, state.accepted_edges || state.mst_edges || state.selected_edges)) classes.push('accepted-edge');
  if (edgeInCollection(edge, state.rejected_edges || state.skipped_edges || state.conflict_edges)) classes.push('rejected-edge');
  if (edgeInMatching(edge, state)) classes.push('matching-edge');
  return classes.join(' ');
}}
function edgeInMatching(edge, state) {{
  const matching = state.matching || state.matches || state.match || state.pair || state.pairs;
  if (!matching) return false;
  const u = String(edge.source || '').replace(/^node:/, '');
  const v = String(edge.target || '').replace(/^node:/, '');
  if (Array.isArray(matching)) return matching.some(item => edgePairMatches(item, u, v));
  if (typeof matching === 'object') return Object.entries(matching).some(([a,b]) => edgeEndpointPairMatches(String(a), String(b), u, v));
  return false;
}}
function edgeInCollection(edge, collection) {{
  if (!collection) return false;
  const u = String(edge.source || '').replace(/^node:/, '');
  const v = String(edge.target || '').replace(/^node:/, '');
  const values = Array.isArray(collection) ? collection : Object.values(collection);
  return values.some(item => edgePairMatches(item, u, v) || String(item) === edge.id || String(item) === `${{u}}-${{v}}` || String(item) === `${{u}}->${{v}}`);
}}
function edgePairMatches(item, u, v) {{
  if (Array.isArray(item) && item.length >= 2) return edgeEndpointPairMatches(String(item[0]), String(item[1]), u, v);
  if (item && typeof item === 'object') return edgeEndpointPairMatches(String(item.u ?? item.source ?? item.left ?? ''), String(item.v ?? item.target ?? item.right ?? ''), u, v);
  return false;
}}
function edgeEndpointPairMatches(a, b, u, v) {{
  return (a === u && b === v) || (a === v && b === u);
}}
function graphNodeMetricText(f, node) {{
  const state = f && f.state || {{}};
  const rawId = String(node && node.id || '');
  const plainId = rawId.replace(/^node:/, '');
  const label = String(node && node.label || '');
  const candidates = unique([rawId, plainId, label].filter(Boolean));
  const parts = [];
  for (const key of ['dist','distance','dfn','low','indegree','color']) {{
    const table = state[key];
    if (!table || typeof table !== 'object' || Array.isArray(table)) continue;
    const found = candidates.find(id => Object.prototype.hasOwnProperty.call(table, id));
    if (found === undefined) continue;
    const shortKey = key === 'distance' ? 'dist' : key;
    parts.push(`${{shortKey}}=${{compactValue(table[found])}}`);
  }}
  return parts.slice(0, 3).join(' · ');
}}
function renderTree(c, children, marks, layout) {{
  const nodes = children.filter(o => o.type === 'node');
  const edges = children.filter(o => o.type === 'edge');
  const w=760,h=380;
  const roots = inferRoots(nodes, edges);
  const levels = treeLevels(nodes, edges, roots);
  const pos={{}};
  const hasTreeMetricText = nodes.some(n => treeNodeMetricText(frame(), n, layout));
  const hasReturnBubble = nodes.some(n => n.meta && n.meta.return_value !== undefined);
  const topPad = hasReturnBubble ? 58 : 44;
  const bottomPad = hasTreeMetricText ? 72 : 44;
  const usableHeight = Math.max(1, h - topPad - bottomPad);
  levels.forEach((levelNodes, depth) => {{
    const y = levels.length === 1 ? topPad + usableHeight / 2 : topPad + depth * usableHeight / Math.max(1, levels.length - 1);
    levelNodes.forEach((n, i) => {{
      const x = (i + 1) * w / (levelNodes.length + 1);
      pos[n.id] = [x, y];
    }});
  }});
  nodes.forEach((n, i) => {{ if (!pos[n.id]) pos[n.id]=[(i+1)*w/(nodes.length+1), h-bottomPad]; }});
  const edgeSvg = edges.map(e => {{
    const a=pos[e.source], b=pos[e.target]; if(!a||!b) return '';
    const cls = `${{markClass(e.id, marks)}} ${{objectMetaClass(e)}}`;
    return `<line class="edge clickable-object ${{cls}}" ${{clickableAttrs(e.id)}} x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"></line>`;
  }}).join('');
  const edgeLabels = edges.map(e => {{
    const a=pos[e.source], b=pos[e.target], label=edgeDisplayLabel(e); if(!a||!b||!label) return '';
    return `<text class="edge-label ${{objectMetaClass(e)}}" x="${{(a[0]+b[0])/2}}" y="${{(a[1]+b[1])/2 - 6}}" text-anchor="middle">${{esc(label)}}</text>`;
  }}).join('');
  const nodeSvg = nodes.map(n => {{
    const p=pos[n.id]; const cls=`${{markClass(n.id, marks)}} ${{objectMetaClass(n)}}`;
    const bubble = n.meta && n.meta.return_value !== undefined ? `<g class="return-bubble" transform="translate(17,-34)"><rect x="-4" y="-12" width="${{Math.max(34, String(compactValue(n.meta.return_value)).length * 7 + 10)}}" height="20" rx="7"></rect><text x="3" y="2">${{esc(compactValue(n.meta.return_value))}}</text></g>` : '';
    const metric = treeNodeMetricText(frame(), n, layout);
    const metricText = metric ? `<text class="graph-node-inline-metrics" y="52" text-anchor="middle">${{esc(metric)}}</text>` : '';
    return `<g class="node clickable-object ${{cls}}" ${{clickableAttrs(n.id)}} transform="translate(${{p[0]}},${{p[1]}})"><circle r="34"></circle><text text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="750">${{esc(n.label || n.id.replace('node:',''))}}</text>${{metricText}}${{bubble}}</g>`;
  }}).join('');
  const label = layout === 'trie' ? 'Trie' : layout === 'union_find' ? '并查集' : layout === 'recursion_tree' ? '递归树' : '树';
  return `<div><h3 class="view-title">${{esc(c.label || label)}}</h3><svg class="tree-svg" viewBox="0 0 ${{w}} ${{h}}">${{edgeSvg}}${{edgeLabels}}${{nodeSvg}}</svg></div>`;
}}
function treeNodeMetricText(f, node, layout) {{
  const state = f && f.state || {{}};
  const graphMetric = graphNodeMetricText(f, node);
  if (graphMetric) return graphMetric;
  const rawId = String(node && node.id || '');
  const plainId = rawId.replace(/^node:/, '');
  const dpEntries = treeDpNodeValues(state);
  const found = dpEntries.find(([key]) => String(key) === rawId || String(key) === plainId || `node:${{key}}` === rawId);
  if (found) {{
    const value = found[1];
    if (value && typeof value === 'object') {{
      const take = value.take ?? value.rob ?? value.include;
      const skip = value.skip ?? value.not_rob ?? value.exclude;
      const ret = value.return_value ?? value.best ?? value.value;
      return [take !== undefined ? `take=${{compactValue(take)}}` : '', skip !== undefined ? `skip=${{compactValue(skip)}}` : '', ret !== undefined ? `ret=${{compactValue(ret)}}` : ''].filter(Boolean).slice(0, 2).join(' · ');
    }}
    return `dp=${{compactValue(value)}}`;
  }}
  if (layout === 'trie' && (node.meta && (node.meta.is_word || node.meta.terminal || node.meta.word_end) || /\\*$/.test(String(node.label || '')))) return 'word end';
  return '';
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
  const state = frame().state || {{}};
  const candidate = state.candidate ?? state.current;
  const popped = state.popped ?? state.removed ?? state.pop_point;
  const cross = state.cross ?? state.cross_product ?? state.orientation;
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
  const byAlias = new Map(points.flatMap(p => [[p.id, p], [p.meta && p.meta.alias, p], [String(p.label || ''), p], [`point:${{p.label}}`, p]].filter(item => item[0])));
  const pointLookup = value => byAlias.get(String(value)) || byAlias.get(`point:${{value}}`);
  const edgeSvg = edges.map(e => {{
    const a=byId.get(e.source), b=byId.get(e.target); if(!a||!b) return '';
    const cls = e.meta && e.meta.shape === 'hull' ? 'geo-hull' : 'geo-segment';
    return `<line class="${{cls}} clickable-object" ${{clickableAttrs(e.id)}} x1="${{sx(a.meta.x)}}" y1="${{sy(a.meta.y)}}" x2="${{sx(b.meta.x)}}" y2="${{sy(b.meta.y)}}"></line>`;
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
    const relationCls = pointLookup(candidate) === p ? 'geo-candidate-point' : pointLookup(popped) === p ? 'geo-hull-ghost-svg' : '';
    return `<g class="node clickable-object ${{cls}} ${{relationCls}}" ${{clickableAttrs(p.id)}} transform="translate(${{x}},${{y}})"><circle r="7"></circle><text x="10" y="-8" font-size="12">${{esc(p.label)}}</text></g>`;
  }}).join('');
  const candidatePoint = pointLookup(candidate);
  const poppedPoint = pointLookup(popped);
  const relationSvg = candidatePoint && poppedPoint && cross !== undefined ? (() => {{
    const x1=sx(poppedPoint.meta.x), y1=sy(poppedPoint.meta.y), x2=sx(candidatePoint.meta.x), y2=sy(candidatePoint.meta.y);
    const label = Number(cross) > 0 ? '左转' : Number(cross) < 0 ? '右转' : '共线';
    return `<line class="geo-cross-vector" x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}"></line><text class="geo-cross-label" x="${{(x1+x2)/2+8}}" y="${{(y1+y2)/2-8}}">${{esc(label)}} cross=${{esc(compactValue(cross))}}</text>`;
  }})() : '';
  return `<div><h3 class="view-title">${{esc(c.label || '几何平面')}}</h3><svg class="geometry-svg" viewBox="0 0 ${{w}} ${{h}}"><defs><marker id="geo-arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#dc2626"></path></marker></defs><line class="geo-axis" x1="${{pad}}" y1="${{h-pad}}" x2="${{w-pad}}" y2="${{h-pad}}"></line><line class="geo-axis" x1="${{pad}}" y1="${{pad}}" x2="${{pad}}" y2="${{h-pad}}"></line>${{edgeSvg}}${{sweepSvg}}${{relationSvg}}${{pointSvg}}</svg></div>`;
}}
function renderLooseObjects(objects, marks) {{
  const fake = {{id:'状态', label:'状态', meta:{{layout:'map'}}}};
  return renderPrimitivePanel(fake, objects, marks, 'primary');
}}
function currentPointersFor(containerId) {{
  const f = frame();
  return (f.objects || []).filter(o => o.type === 'pointer' && (o.parent === containerId || (o.meta && o.meta.array === containerId)) && Number.isInteger(o.index));
}}
function renderTimeline() {{
  $('timeline').innerHTML = frames().map((f,i) => {{
    const meta = timelineMeta(f);
    const label = timelineLabel(f, i, meta);
    const op = timelineOperation(f, meta);
    const title = `${{i + 1}} / ${{frames().length}} · ${{label}} · ${{op}}`;
    return `<button class="tick ${{i===stepIndex?'active':''}} ${{meta.keyframe ? 'keyframe' : 'ordinary'}}" data-step="${{i}}" data-phase="${{esc(textOrEmpty(meta.phase) || label)}}" title="${{esc(title)}}" aria-label="${{esc(title)}}" onclick="go(${{i}})"><span class="tick-label">${{esc(label)}}</span><span class="tick-op">${{esc(op)}}</span></button>`;
  }}).join('');
}}
function timelineMeta(f) {{
  const evidence = f && f.evidence || {{}};
  return evidence.timeline || {{}};
}}
function timelineLabel(f, i, meta) {{
  return textOrEmpty(meta.phase) || textOrEmpty(meta.keyframe_label) || fallbackTimelineLabel(f, i);
}}
function timelineOperation(f, meta) {{
  const op = textOrEmpty(meta.operation) || textOrEmpty(f && f.operation);
  const targets = Array.isArray(meta.targets) ? meta.targets.filter(Boolean).slice(0, 2).join(', ') : '';
  return targets ? `${{op || 'step'}} · ${{targets}}` : (op || 'step');
}}
function fallbackTimelineLabel(f, i) {{
  return `${{i + 1}} · ${{frameTitle(f)}}`;
}}
function textOrEmpty(value) {{
  return typeof value === 'string' ? value.trim() : '';
}}
function renderState(state) {{
  const entries = Object.entries(state || {{}});
  $('state').innerHTML = entries.length ? entries.map(([k,v]) => `<div class="state-row"><strong>${{esc(k)}}</strong><code>${{esc(stateValueSummary(v))}}</code></div>`).join('') : '<p style="color:var(--muted);margin:0;">当前步骤没有状态快照。</p>';
}}
function renderDebugState(state) {{
  const node = $('debug-state');
  if (!node) return;
  node.innerHTML = `<div class="state-row"><strong>frame ${{stepIndex + 1}}</strong><pre>${{esc(pretty(state || {{}}))}}</pre></div>`;
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
  const degradations = validation.degradations || [];
  const renderReport = ARTIFACT.render_report || {{}};
  const testPassed = tests.filter(t => t.ok).length;
  const answerRows = [
    ['expected', ARTIFACT.expected_result],
    ['verifier', ARTIFACT.verifier_result],
    ['actual', v.result],
  ].filter(([,value]) => value !== undefined && value !== null);
  const statusItems = [
    ['代码执行通过', gate.artifact_ready],
    ['轨迹覆盖完整', gate.trace_ready],
    ['过程转移通过校验', gate.process_ready],
    ['可视化对象绑定正确', gate.visual_ready],
  ];
  let html = '';
  html += `<div class="evidence-block"><strong>可信度摘要</strong><div class="status-line">${{statusItems.map(([label,ok]) => `<div class="status-item ${{ok ? 'ok' : 'warn'}}"><span class="status-dot"></span><span>${{esc(label)}}：${{ok ? '通过' : '待检查'}}</span></div>`).join('')}}</div></div>`;
  html += `<div class="evidence-block"><strong>答案交叉检查</strong>${{answerRows.length ? answerRows.map(([k,val]) => evidenceLine(k, valueCode(val))).join('') : '<p style="color:var(--muted);margin:0;font-size:12px;">无 expected/verifier 证据。</p>'}}</div>`;
  let debugHtml = '';
  debugHtml += `<div class="evidence-block"><strong>Release gate</strong><div class="chip-row">${{gateChips(gate).join('')}}</div>${{(gate.blocking_reasons || []).length ? `<ul class="evidence-list">${{gate.blocking_reasons.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : ''}}</div>`;
  if (contract) {{
    debugHtml += `<div class="evidence-block"><strong>CorrectnessContract</strong>${{evidenceLine('schema', esc(contract.schema_version || ''))}}${{evidenceLine('oracle', esc(contract.oracle_strategy || ''))}}${{contractGate ? `<div class="chip-row">${{gateChips(contractGate).join('')}}</div>` : ''}}${{contract.process_invariants && contract.process_invariants.length ? `<ul class="evidence-list">${{contract.process_invariants.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : ''}}</div>`;
  }}
  debugHtml += `<div class="evidence-block"><strong>Contract tests</strong>${{tests.length ? evidenceLine('passed', `${{testPassed}}/${{tests.length}}`) + `<ul class="evidence-list">${{tests.slice(0, 6).map(renderContractTest).join('')}}${{tests.length > 6 ? `<li>还有 ${{tests.length - 6}} 条已省略</li>` : ''}}</ul>` : '<p style="color:var(--muted);margin:0;font-size:12px;">当前 artifact 没有 contract 多输入测试。</p>'}}</div>`;
  debugHtml += `<div class="evidence-block"><strong>Pipeline checks</strong>${{checks.length ? `<ul class="evidence-list">${{checks.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : '<p style="color:var(--muted);margin:0;font-size:12px;">无 checks。</p>'}}</div>`;
  if (degradations.length) {{
    debugHtml += `<div class="evidence-block"><strong>Degradation policy</strong><ul class="evidence-list">${{degradations.map(item => `<li><span class="chip warn">${{esc(item.type || 'degraded')}}</span> ${{esc(item.reason || '')}}${{item.source ? ` <code>${{esc(item.source)}}</code>` : ''}}</li>`).join('')}}</ul></div>`;
  }}
  if (warnings.length || errors.length) {{
    debugHtml += `<div class="evidence-block"><strong>Warnings / errors</strong><ul class="evidence-list">${{errors.map(x => `<li>错误：${{esc(x)}}</li>`).join('')}}${{warnings.map(x => `<li>警告：${{esc(x)}}</li>`).join('')}}</ul></div>`;
  }}
  if (renderReport.requested_target || renderReport.actual_target) {{
    debugHtml += `<div class="evidence-block"><strong>Render target</strong>${{evidenceLine('requested', esc(renderReport.requested_target || ''))}}${{evidenceLine('actual', esc(renderReport.actual_target || RUNTIME_TARGET))}}${{renderReport.used_baseline_renderer ? evidenceLine('baseline', 'true') : ''}}</div>`;
  }}
  const evidenceNode = $('evidence');
  if (evidenceNode) evidenceNode.innerHTML = html;
  const debugEvidence = $('debug-evidence');
  if (debugEvidence) debugEvidence.innerHTML = debugHtml;
  setText('debug-validation-json', pretty(validation));
  const debugRelease = $('debug-release');
  if (debugRelease) debugRelease.innerHTML = `<div class="evidence-block"><strong>release gate raw</strong><pre>${{esc(pretty(gate))}}</pre></div>`;
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
function renderProcessEvidence(f) {{
  const process = f && f.evidence && f.evidence.process || null;
  if (!process || !process.summary) return '';
  const checks = Array.isArray(process.checks) ? process.checks : [];
  const checkRows = checks.length ? `<ul class="evidence-list">${{checks.map(item => `<li><strong>${{esc(item.label || '核对')}}</strong>：${{esc(item.text || '')}}</li>`).join('')}}</ul>` : '';
  const status = process.status ? evidenceLine('status', esc(process.status)) : '';
  const kind = process.kind ? evidenceLine('kind', esc(process.kind)) : '';
  return `<div class="evidence-block"><strong>过程校验证据</strong><p style="color:var(--muted);margin:0 0 6px;font-size:12px;">本步过程核对</p>${{status}}${{kind}}${{evidenceLine('summary', esc(process.summary))}}${{checkRows}}</div>`;
}}
function renderStepEvidence(f) {{
  const evidence = f.evidence || {{}};
  const previous = stepIndex > 0 ? frames()[stepIndex - 1] : null;
  const marks = f.marks || [];
  const targets = evidence.targets || marks.filter(m => m.role !== 'dependency').map(m => m.target);
  const deps = evidence.deps || marks.filter(m => m.role === 'dependency').map(m => m.target);
  const changedTargetIds = targetChanges(targets, previous && previous.state || {{}}, f.state || {{}});
  let html = '';
  html += `<div class="evidence-block"><strong>本步语义</strong>${{evidenceLine('operation', esc(evidence.operation || frameOperation(f)))}}${{evidenceLine('code_line', esc(evidence.code_line || frameCodeLine(f)))}}${{evidenceLine('targets', esc((targets || []).join(', ') || '无'))}}${{evidenceLine('deps', esc((deps || []).join(', ') || '无'))}}${{evidence.role ? evidenceLine('role', esc(evidence.role)) : ''}}</div>`;
  html += renderProcessEvidence(f);
  if (evidence.value !== undefined || evidence.before !== undefined || evidence.after !== undefined) {{
    html += `<div class="evidence-block"><strong>事件值</strong>${{evidence.value !== undefined ? evidenceLine('value', valueCode(evidence.value)) : ''}}${{evidence.before !== undefined ? evidenceLine('before', valueCode(evidence.before)) : ''}}${{evidence.after !== undefined ? evidenceLine('after', valueCode(evidence.after)) : ''}}</div>`;
  }}
  const changeRows = eventChangeRows(f);
  html += `<div class="evidence-block"><strong>状态变化摘要</strong>${{changeRows.length ? changeRows.slice(0, 4).map(renderChangeRow).join('') : '<p style="color:var(--muted);margin:0;font-size:12px;">本步没有可观测状态变化。</p>'}}${{changeRows.length > 4 ? `<p style="color:var(--muted);margin:5px 0 0;font-size:12px;">还有 ${{changeRows.length - 4}} 项变化已省略。</p>` : ''}}</div>`;
  html += `<div class="evidence-block"><strong>目标写入核对</strong>${{changedTargetIds.length ? `<ul class="evidence-list">${{changedTargetIds.map(x => `<li>${{esc(x)}}</li>`).join('')}}</ul>` : '<p style="color:var(--muted);margin:0;font-size:12px;">本步目标没有可解析的状态写入，或属于指针/节点移动。</p>'}}</div>`;
  $('step-evidence').innerHTML = html;
}}
function renderChangeSummary(f) {{
  const rows = eventChangeRows(f);
  if (!rows.length) return '';
  return `<div class="change-summary"><strong>状态变化摘要</strong>${{rows.slice(0, 6).map(renderChangeRow).join('')}}${{rows.length > 6 ? `<p style="color:#166534;margin:6px 0 0;font-size:12px;">还有 ${{rows.length - 6}} 项变化已省略。</p>` : ''}}</div>`;
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
  return {{
    target:String(row && row.target !== undefined ? row.target : 'state'),
    before:row && row.before,
    after:row && row.after,
    value:row && row.value,
    kind:row && row.kind || '',
    source:row && row.source || '',
  }};
}}
function pickIndexedValue(value, index, total) {{
  if (Array.isArray(value) && total > 1 && index < value.length) return value[index];
  return value;
}}
function renderChangeRow(row) {{
  const parts = [];
  if (row.before !== undefined || row.after !== undefined) parts.push(`${{compactValue(row.before)}} → ${{compactValue(row.after)}}`);
  if (row.value !== undefined) parts.push(`value=${{compactValue(row.value)}}`);
  const suffix = [row.kind, row.source === 'state_diff' ? 'state diff' : 'event'].filter(Boolean).join(' · ');
  return `<div class="change-row" data-source="${{esc(row.source || '')}}"><span>${{esc(row.target)}}${{suffix ? ` · ${{esc(suffix)}}` : ''}}</span><code>${{esc(parts.join(' · ') || '已变化')}}</code></div>`;
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
function teachingFieldRows(f) {{
  const teaching = f.teaching || {{}};
  return [
    {{ key:'what', label:'当前步骤', value:teaching.what || frameTitle(f), code:false }},
    {{ key:'why', label:'为什么', value:teaching.why || frameDescription(f) || '根据当前状态推进算法步骤。', code:false }},
    {{ key:'formula', label:'公式 / 规则', value:teaching.formula || '', code:true }},
    {{ key:'invariant', label:'不变量', value:teaching.invariant || '', code:false }},
    {{ key:'common_mistake', label:'常见错误', value:teaching.common_mistake || '', code:false }},
    {{ key:'hint', label:'提示', value:teaching.hint || '', code:false }},
  ].filter(row => String(row.value || '').trim());
}}
function renderTeachingField(row, f) {{
  if (row.key === 'formula') return renderFormulaExpansion(f, row);
  const value = esc(row.value);
  const body = row.code ? `<code>${{value}}</code>` : `<p>${{value}}</p>`;
  return `<div class="teach-row ${{esc(row.key)}}"><strong>${{esc(row.label)}}</strong>${{body}}</div>`;
}}
function renderFormulaExpansion(f, row) {{
  const evidence = f && f.evidence || {{}};
  const process = evidence.process || {{}};
  const targets = Array.isArray(evidence.targets) ? evidence.targets.filter(Boolean) : [];
  const deps = Array.isArray(evidence.deps) ? evidence.deps.filter(Boolean) : [];
  const rows = [
    formulaExpansionRow('公式', row.value),
    formulaExpansionRow('代入', formulaSubstitutionForFrame(f)),
    formulaExpansionRow('目标', targets.join(', ')),
    formulaExpansionRow('依赖', deps.join(', ')),
    formulaExpansionRow('事件值', formulaValueSummary(evidence)),
    formulaExpansionRow('过程核对', process.summary || ''),
  ].filter(Boolean);
  const checks = Array.isArray(process.checks) && process.checks.length
    ? `<div class="formula-expansion-row"><span>检查项</span><code>${{esc(process.checks.map(item => [item.label, item.text].filter(Boolean).join('：')).join('；'))}}</code></div>`
    : '';
  return `<details class="teach-row formula formula-expander" data-trace-step="${{esc(f && f.step)}}" data-source="teaching/evidence/SceneGraph"><summary><strong>${{esc(row.label)}}</strong><span>展开</span></summary><code>${{esc(row.value)}}</code><div class="formula-expansion">${{rows.join('')}}${{checks}}<div class="formula-expansion-row"><span>来源</span><code>SceneGraph frame.teaching / frame.evidence / visual object meta，只读当前 trace。</code></div></div></details>`;
}}
function formulaExpansionRow(label, value) {{
  const text = String(value ?? '').trim();
  if (!text) return '';
  return `<div class="formula-expansion-row"><span>${{esc(label)}}</span><code>${{esc(text)}}</code></div>`;
}}
function formulaSubstitutionForFrame(f) {{
  const candidates = objectsWithPattern(f || {{}}, 'dp_formula_substitution')
    .map(o => o.meta && o.meta.substitution)
    .filter(value => String(value ?? '').trim());
  if (candidates.length) return String(candidates[0]);
  const teaching = f && f.teaching || {{}};
  return teaching.substitution || '';
}}
function formulaValueSummary(evidence) {{
  const parts = [];
  if (evidence.before !== undefined) parts.push(`before=${{compactValue(evidence.before)}}`);
  if (evidence.after !== undefined) parts.push(`after=${{compactValue(evidence.after)}}`);
  if (evidence.value !== undefined) parts.push(`value=${{compactValue(evidence.value)}}`);
  return parts.join(' · ');
}}
function teachingRows(f) {{
  const rows = teachingFieldRows(f);
  return rows.length ? rows : [{{ key:'what', label:'当前步骤', value:frameDescription(f) || frameTitle(f) || '继续执行算法步骤。', code:false }}];
}}
function renderTeaching(f) {{
  $('teaching').innerHTML = `<div class="teaching">${{teachingRows(f).map(row => renderTeachingField(row, f)).join('')}}${{renderChangeSummary(f)}}</div>`;
}}
function renderInteraction(interaction) {{
  if (!interaction) {{ $('interaction').innerHTML = '<p style="color:var(--muted);margin:0;">当前步骤没有交互题。</p>'; return; }}
  const opts = Array.isArray(interaction.options) ? interaction.options : [];
  const choiceHtml = interaction.type === 'choice' ? opts.map(o => `<button data-option="${{esc(o)}}" onclick="checkChoice('${{encodeURIComponent(String(o))}}')">${{esc(o)}}</button>`).join('') : '';
  const inputHtml = interaction.type === 'input' ? '<input id="free-answer" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;"><button onclick="checkInput()">检查</button>' : '';
  const judgeHtml = interaction.type === 'judge' ? '<button onclick="checkJudge(true)">正确</button><button onclick="checkJudge(false)">错误</button>' : '';
  $('interaction').innerHTML = `<div class="interaction" data-interaction-type="${{esc(interaction.type || '')}}" data-trace-step="${{frame().step}}"><strong>${{esc(interaction.prompt || '思考题')}}</strong>${{choiceHtml}}${{inputHtml}}${{judgeHtml}}<div id="feedback" class="feedback"></div></div>`;
}}
function checkChoice(encoded) {{
  const value = decodeURIComponent(encoded);
  const ans = frame().interaction.answer;
  const ok = Array.isArray(ans) ? ans.map(String).includes(value) : String(ans) === value;
  setFeedback(ok, ok ? correctFeedback(value) : wrongFeedback(value), value);
}}
function checkInput() {{
  const value = $('free-answer').value.trim();
  const ans = String(frame().interaction.answer ?? '').trim();
  const ok = value === ans;
  setFeedback(ok, ok ? correctFeedback(value) : `参考答案：${{ans}}。${{wrongFeedback(value)}}`, value);
}}
function checkJudge(value) {{
  const ans = frame().interaction.answer;
  const expected = ans === true || String(ans).toLowerCase() === 'true' || String(ans) === '正确';
  setFeedback(value === expected, value === expected ? correctFeedback(value) : wrongFeedback(value), value);
}}
function correctFeedback(value) {{
  const interaction = frame().interaction || {{}};
  const optionText = optionExplanation(interaction, value);
  return optionText || interaction.explanation || '';
}}
function wrongFeedback(value) {{
  const interaction = frame().interaction || {{}};
  const teaching = frame().teaching || {{}};
  return optionExplanation(interaction, value)
    || interaction.wrong_explanation
    || teaching.common_mistake
    || interaction.explanation
    || '这一步没有提供针对该错误选项的解释。';
}}
function optionExplanation(interaction, value) {{
  const explanations = interaction && interaction.option_explanations || {{}};
  const key = String(value);
  if (Object.prototype.hasOwnProperty.call(explanations, key)) return String(explanations[key] || '');
  return '';
}}
function feedbackSource(value, ok) {{
  const interaction = frame().interaction || {{}};
  const teaching = frame().teaching || {{}};
  const explanations = interaction.option_explanations || {{}};
  if (Object.prototype.hasOwnProperty.call(explanations, String(value))) return 'interaction.option_explanations';
  if (!ok && interaction.wrong_explanation) return 'interaction.wrong_explanation';
  if (!ok && teaching.common_mistake) return 'teaching.common_mistake';
  return 'interaction.explanation';
}}
function setFeedback(ok, message, value) {{
  const node = $('feedback');
  if (!node) return;
  const source = feedbackSource(value, ok);
  node.className = `feedback ${{ok ? 'correct' : 'wrong'}}`;
  node.dataset.source = source;
  node.dataset.correct = ok ? 'true' : 'false';
  node.innerHTML = `${{ok ? '正确。' : '错误选项解释：'}}${{esc(message || '')}}<span class="feedback-source">来源：${{esc(source)}}，只读当前 SceneGraph interaction / teaching。</span>`;
}}
function renderCode(code, info) {{
  const lines = String(code || '').split('\\n');
  const active = Number(info && info.active) || 1;
  const status = info && info.status === 'ok' ? 'ok' : 'warn';
  const label = info && info.label ? info.label : `当前代码行：第 ${{active}} 行`;
  const sync = `<div class="code-sync ${{status}}" data-active-line="${{active}}" data-code-line-status="${{status}}"><span>${{esc(label)}}</span></div>`;
  $('code').innerHTML = sync + lines.map((line,i)=>{{
    const lineNo = i + 1;
    const lineActive = status === 'ok' && lineNo === active;
    const fallback = status !== 'ok' && lineNo === active;
    return `<div class="line ${{lineActive ? 'active' : ''}} ${{fallback ? 'fallback' : ''}}"><span class="lineno">${{lineNo}}</span><span>${{esc(line) || ' '}}</span></div>`;
  }}).join('');
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
window.addEventListener('resize', () => {{ if (!isSpatialTarget()) fitSceneToCanvas(); }});
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
