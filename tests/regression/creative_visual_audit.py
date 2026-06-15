"""Regression tests for browser-level Creative Stage audit behavior."""

from __future__ import annotations

from pathlib import Path

from algolab.renderer.creative_direct import render_direct_visual_stage_shell_html
from scripts.audit_creative_visual_renderer import audit_html_path
from tests.fixtures import fixture_artifact


TRANSPARENT_HIGHLIGHT_STAGE = """<style id="creative-stage-style">
.audit-stage { width: 640px; height: 260px; }
.cell { fill: #eef2ff; stroke: #475569; stroke-width: 2; }
.range-highlight { fill: #38bdf8; fill-opacity: 0.22; stroke: #0284c7; stroke-width: 3; pointer-events: none; }
.label { font: 18px sans-serif; fill: #111827; dominant-baseline: middle; text-anchor: middle; }
</style>
<template id="creative-stage-template"></template>
<script>
window.renderCreativeStage = function(ctx) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 640 260');
  svg.setAttribute('class', 'audit-stage');
  for (let i = 0; i < 3; i++) {
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('x', String(80 + i * 120));
    rect.setAttribute('y', '100');
    rect.setAttribute('width', '90');
    rect.setAttribute('height', '48');
    rect.setAttribute('rx', '8');
    rect.setAttribute('class', 'cell');
    rect.setAttribute('data-visual', 'candidate');
    svg.appendChild(rect);
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', String(125 + i * 120));
    label.setAttribute('y', '124');
    label.setAttribute('class', 'label');
    label.setAttribute('data-layout-role', 'label');
    label.textContent = String(i + 1);
    svg.appendChild(label);
  }
  const highlight = document.createElementNS(ns, 'rect');
  highlight.setAttribute('x', '76');
  highlight.setAttribute('y', '96');
  highlight.setAttribute('width', '338');
  highlight.setAttribute('height', '56');
  highlight.setAttribute('rx', '12');
  highlight.setAttribute('class', 'range-highlight');
  highlight.setAttribute('data-visual', 'range-highlight');
  svg.insertBefore(highlight, svg.firstChild);
  ctx.host.appendChild(svg);
};
</script>"""


BACKGROUND_AND_LEGEND_STAGE = """<style id="creative-stage-style">
.audit-stage { width: 640px; height: 300px; }
.bar { fill: #dbeafe; stroke: #2563eb; }
.legend-box { fill: white; stroke: #cbd5e1; }
.label { font: 16px sans-serif; fill: #111827; dominant-baseline: middle; }
</style>
<template id="creative-stage-template"></template>
<script>
window.renderCreativeStage = function(ctx) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 640 300');
  svg.setAttribute('class', 'audit-stage');

  const bg = document.createElementNS(ns, 'rect');
  bg.setAttribute('x', '20');
  bg.setAttribute('y', '40');
  bg.setAttribute('width', '420');
  bg.setAttribute('height', '180');
  bg.setAttribute('fill', '#f8fafc');
  bg.setAttribute('data-visual', 'background');
  svg.appendChild(bg);

  for (let i = 0; i < 3; i++) {
    const bar = document.createElementNS(ns, 'rect');
    bar.setAttribute('x', String(70 + i * 90));
    bar.setAttribute('y', String(170 - i * 30));
    bar.setAttribute('width', '48');
    bar.setAttribute('height', String(50 + i * 30));
    bar.setAttribute('class', 'bar');
    bar.setAttribute('data-visual', 'bar');
    svg.appendChild(bar);
  }

  const legend = document.createElementNS(ns, 'rect');
  legend.setAttribute('x', '470');
  legend.setAttribute('y', '70');
  legend.setAttribute('width', '120');
  legend.setAttribute('height', '84');
  legend.setAttribute('rx', '8');
  legend.setAttribute('class', 'legend-box');
  legend.setAttribute('data-layout-role', 'legend');
  svg.appendChild(legend);

  const swatch = document.createElementNS(ns, 'rect');
  swatch.setAttribute('x', '488');
  swatch.setAttribute('y', '98');
  swatch.setAttribute('width', '14');
  swatch.setAttribute('height', '14');
  swatch.setAttribute('fill', '#2563eb');
  swatch.setAttribute('data-layout-role', 'legend-swatch');
  svg.appendChild(swatch);

  const label = document.createElementNS(ns, 'text');
  label.setAttribute('x', '512');
  label.setAttribute('y', '106');
  label.setAttribute('class', 'label');
  label.setAttribute('data-layout-role', 'legend-label');
  label.textContent = 'active';
  svg.appendChild(label);
  ctx.host.appendChild(svg);
};
</script>"""


POINTER_GROUP_STAGE = """<style id="creative-stage-style">
.audit-stage { width: 640px; height: 260px; }
.cell { fill: #eef2ff; stroke: #475569; stroke-width: 2; }
.label { font: 16px sans-serif; fill: #111827; text-anchor: middle; }
</style>
<template id="creative-stage-template"></template>
<script>
window.renderCreativeStage = function(ctx) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 640 260');
  svg.setAttribute('class', 'audit-stage');
  const cell = document.createElementNS(ns, 'rect');
  cell.setAttribute('x', '240');
  cell.setAttribute('y', '120');
  cell.setAttribute('width', '80');
  cell.setAttribute('height', '42');
  cell.setAttribute('class', 'cell');
  cell.setAttribute('data-visual', 'cell');
  svg.appendChild(cell);
  const group = document.createElementNS(ns, 'g');
  group.setAttribute('data-layout-role', 'pointers');
  const line = document.createElementNS(ns, 'line');
  line.setAttribute('x1', '280');
  line.setAttribute('y1', '74');
  line.setAttribute('x2', '280');
  line.setAttribute('y2', '116');
  line.setAttribute('stroke', '#dc2626');
  line.setAttribute('stroke-width', '2');
  line.setAttribute('data-visual', 'pointer-line');
  group.appendChild(line);
  const label = document.createElementNS(ns, 'text');
  label.setAttribute('x', '280');
  label.setAttribute('y', '62');
  label.setAttribute('class', 'label');
  label.setAttribute('data-layout-role', 'label');
  label.textContent = 'left';
  group.appendChild(label);
  svg.appendChild(group);
  ctx.host.appendChild(svg);
};
</script>"""


EDGE_LABEL_STAGE = """<style id="creative-stage-style">
.audit-stage { width: 640px; height: 260px; }
.cell { fill: #f8fafc; stroke: #94a3b8; }
.label { font: 16px sans-serif; fill: #111827; text-anchor: middle; }
</style>
<template id="creative-stage-template"></template>
<script>
window.renderCreativeStage = function(ctx) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 640 260');
  svg.setAttribute('class', 'audit-stage');
  const cell = document.createElementNS(ns, 'rect');
  cell.setAttribute('x', '220');
  cell.setAttribute('y', '92');
  cell.setAttribute('width', '90');
  cell.setAttribute('height', '48');
  cell.setAttribute('class', 'cell');
  cell.setAttribute('data-visual', 'cell');
  svg.appendChild(cell);
  const header = document.createElementNS(ns, 'text');
  header.setAttribute('x', '265');
  header.setAttribute('y', '90');
  header.setAttribute('class', 'label');
  header.setAttribute('data-layout-role', 'label');
  header.textContent = '0';
  svg.appendChild(header);
  ctx.host.appendChild(svg);
};
</script>"""


OUTLINE_CONNECTOR_STAGE = """<style id="creative-stage-style">
.audit-stage { width: 640px; height: 260px; }
.cell { fill: #f8fafc; stroke: #94a3b8; }
.label { font: 16px sans-serif; fill: #111827; text-anchor: middle; }
</style>
<template id="creative-stage-template"></template>
<script>
window.renderCreativeStage = function(ctx) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 640 260');
  svg.setAttribute('class', 'audit-stage');
  const cell = document.createElementNS(ns, 'rect');
  cell.setAttribute('x', '250');
  cell.setAttribute('y', '110');
  cell.setAttribute('width', '70');
  cell.setAttribute('height', '42');
  cell.setAttribute('class', 'cell');
  cell.setAttribute('data-visual', 'cell');
  svg.appendChild(cell);
  const ring = document.createElementNS(ns, 'circle');
  ring.setAttribute('cx', '285');
  ring.setAttribute('cy', '131');
  ring.setAttribute('r', '42');
  ring.setAttribute('fill', 'none');
  ring.setAttribute('stroke', '#f59e0b');
  ring.setAttribute('stroke-width', '3');
  ring.setAttribute('data-visual', 'true');
  svg.appendChild(ring);
  const label = document.createElementNS(ns, 'text');
  label.setAttribute('x', '285');
  label.setAttribute('y', '76');
  label.setAttribute('class', 'label');
  label.setAttribute('data-layout-role', 'label');
  label.textContent = 'Answer=2';
  svg.appendChild(label);
  const guide = document.createElementNS(ns, 'line');
  guide.setAttribute('x1', '285');
  guide.setAttribute('y1', '68');
  guide.setAttribute('x2', '285');
  guide.setAttribute('y2', '88');
  guide.setAttribute('stroke', '#64748b');
  guide.setAttribute('stroke-width', '2');
  guide.setAttribute('data-visual', 'pointer-line');
  svg.appendChild(guide);
  ctx.host.appendChild(svg);
};
</script>"""


TRANSLUCENT_REGION_STAGE = """<style id="creative-stage-style">
.audit-stage { width: 640px; height: 300px; }
.label { font: 14px sans-serif; fill: #111827; text-anchor: middle; }
</style>
<template id="creative-stage-template"></template>
<script>
window.renderCreativeStage = function(ctx) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 640 300');
  svg.setAttribute('class', 'audit-stage');
  const region = document.createElementNS(ns, 'polygon');
  region.setAttribute('points', '120,220 320,80 520,220');
  region.setAttribute('fill', 'rgba(34, 197, 94, 0.18)');
  region.setAttribute('stroke', '#16a34a');
  region.setAttribute('stroke-width', '2');
  region.setAttribute('data-derived-visual-only', 'true');
  region.setAttribute('class', 'answer-region');
  svg.appendChild(region);
  [[120,220,'0'], [320,80,'1'], [520,220,'2']].forEach(([x, y, text]) => {
    const point = document.createElementNS(ns, 'circle');
    point.setAttribute('cx', String(x));
    point.setAttribute('cy', String(y));
    point.setAttribute('r', '7');
    point.setAttribute('fill', '#334155');
    point.setAttribute('data-visual', 'point');
    svg.appendChild(point);
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', String(x));
    label.setAttribute('y', String(y - 12));
    label.setAttribute('class', 'label');
    label.setAttribute('data-layout-role', 'label');
    label.textContent = text;
    svg.appendChild(label);
  });
  ctx.host.appendChild(svg);
};
</script>"""


UNMARKED_TRANSLUCENT_REGION_STAGE = TRANSLUCENT_REGION_STAGE.replace(
    "  region.setAttribute('data-derived-visual-only', 'true');\n"
    "  region.setAttribute('class', 'answer-region');",
    "  region.setAttribute('class', 'answer-hull');\n"
    "  region.setAttribute('data-visual', 'region');",
)


def test_stage_visual_audit_allows_transparent_highlight_overlay(tmp_path: Path):
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, TRANSPARENT_HIGHLIGHT_STAGE)
    html_path = tmp_path / "highlight_overlay.html"
    html_path.write_text(html, encoding="utf-8")

    row = audit_html_path(
        html_path,
        tmp_path / "audit",
        wait_ms=50,
        require_stage_visual_quality=True,
        stage_audit_max_frames=1,
    )

    assert row["browser_smoke_ok"] is True
    assert row["stage_visual_quality_ok"] is True
    assert row["stage_permitted_overlap_count"] >= 1
    assert row["creative_ok"] is True


def test_stage_visual_audit_ignores_background_and_legend_containers(tmp_path: Path):
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, BACKGROUND_AND_LEGEND_STAGE)
    html_path = tmp_path / "background_legend.html"
    html_path.write_text(html, encoding="utf-8")

    row = audit_html_path(
        html_path,
        tmp_path / "audit_background_legend",
        wait_ms=50,
        require_stage_visual_quality=True,
        stage_audit_max_frames=1,
    )

    assert row["browser_smoke_ok"] is True
    assert row["stage_visual_quality_ok"] is True
    assert row["stage_overlap_count"] == 0
    assert row["creative_ok"] is True


def test_stage_visual_audit_ignores_pointer_group_bounding_box(tmp_path: Path):
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, POINTER_GROUP_STAGE)
    html_path = tmp_path / "pointer_group.html"
    html_path.write_text(html, encoding="utf-8")

    row = audit_html_path(
        html_path,
        tmp_path / "audit_pointer_group",
        wait_ms=50,
        require_stage_visual_quality=True,
        stage_audit_max_frames=1,
    )

    assert row["browser_smoke_ok"] is True
    assert row["stage_visual_quality_ok"] is True
    assert row["stage_overlap_count"] == 0
    assert row["creative_ok"] is True


def test_stage_visual_audit_allows_minor_edge_label_overlap(tmp_path: Path):
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, EDGE_LABEL_STAGE)
    html_path = tmp_path / "edge_label.html"
    html_path.write_text(html, encoding="utf-8")

    row = audit_html_path(
        html_path,
        tmp_path / "audit_edge_label",
        wait_ms=50,
        require_stage_visual_quality=True,
        stage_audit_max_frames=1,
    )

    assert row["browser_smoke_ok"] is True
    assert row["stage_visual_quality_ok"] is True
    assert row["stage_overlap_count"] == 0
    assert row["creative_ok"] is True


def test_stage_visual_audit_allows_outline_and_connector_guides(tmp_path: Path):
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, OUTLINE_CONNECTOR_STAGE)
    html_path = tmp_path / "outline_connector.html"
    html_path.write_text(html, encoding="utf-8")

    row = audit_html_path(
        html_path,
        tmp_path / "audit_outline_connector",
        wait_ms=50,
        require_stage_visual_quality=True,
        stage_audit_max_frames=1,
    )

    assert row["browser_smoke_ok"] is True
    assert row["stage_visual_quality_ok"] is True
    assert row["stage_overlap_count"] == 0
    assert row["stage_text_occlusion_count"] == 0
    assert row["creative_ok"] is True


def test_stage_visual_audit_allows_translucent_region_under_marks(tmp_path: Path):
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, TRANSLUCENT_REGION_STAGE)
    html_path = tmp_path / "translucent_region.html"
    html_path.write_text(html, encoding="utf-8")

    row = audit_html_path(
        html_path,
        tmp_path / "audit_translucent_region",
        wait_ms=50,
        require_stage_visual_quality=True,
        stage_audit_max_frames=1,
    )

    assert row["browser_smoke_ok"] is True
    assert row["stage_visual_quality_ok"] is True
    assert row["stage_overlap_count"] == 0
    assert row["creative_ok"] is True


def test_stage_visual_audit_rejects_unmarked_translucent_region(tmp_path: Path):
    artifact = fixture_artifact()
    html = render_direct_visual_stage_shell_html(artifact, UNMARKED_TRANSLUCENT_REGION_STAGE)
    html_path = tmp_path / "unmarked_translucent_region.html"
    html_path.write_text(html, encoding="utf-8")

    row = audit_html_path(
        html_path,
        tmp_path / "audit_unmarked_translucent_region",
        wait_ms=50,
        require_stage_visual_quality=True,
        stage_audit_max_frames=1,
    )

    assert row["browser_smoke_ok"] is True
    assert row["stage_visual_quality_ok"] is False
    assert row["creative_ok"] is False


def run_all() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_stage_visual_audit_allows_transparent_highlight_overlay(tmp_path)
        test_stage_visual_audit_ignores_background_and_legend_containers(tmp_path)
        test_stage_visual_audit_ignores_pointer_group_bounding_box(tmp_path)
        test_stage_visual_audit_allows_minor_edge_label_overlap(tmp_path)
        test_stage_visual_audit_allows_outline_and_connector_guides(tmp_path)
        test_stage_visual_audit_allows_translucent_region_under_marks(tmp_path)
        test_stage_visual_audit_rejects_unmarked_translucent_region(tmp_path)
    print("creative_visual_audit: PASS")


if __name__ == "__main__":
    run_all()
