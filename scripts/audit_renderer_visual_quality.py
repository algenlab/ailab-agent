"""Audit current renderer visual quality on saved BuildArtifact JSON files.

The script intentionally rerenders every JSON artifact with the current
``save_html`` implementation before opening it in Playwright.  This keeps the
audit tied to the renderer under development instead of stale HTML exported by
an earlier run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.compiler.scene_compiler import compile_scene
from algolab.renderer.export import save_html
from algolab.schemas.validation import BuildArtifact


DEFAULT_ARTIFACT_DIR = ROOT / "output" / "aaai" / "llm_algolab_full_gemini_3_flash_c12_k3_r1_full1"
DEFAULT_VIEWPORT = {"width": 1440, "height": 790}
LOW_UTILIZATION_THRESHOLD = 0.20
MIN_READABLE_SCALE = 1.0
MIN_PRIMARY_VISIBLE_RATIO = 0.96
MAX_ANSWER_PRIMARY_AREA_RATIO = 0.35
MIN_GRAPH_NODE_RADIUS = 14.0


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return text.strip("._") or "item"


def sample_frame_indices(total: int) -> list[dict[str, int | str]]:
    if total <= 0:
        return []
    last = max(0, total - 1)
    middle = total // 2
    return [
        {"label": "first", "index": 0},
        {"label": "middle", "index": middle},
        {"label": "last", "index": last},
    ]


def collect_artifact_paths(artifact_dir: Path, pattern: str) -> list[Path]:
    paths = sorted(artifact_dir.glob(pattern))
    return [path for path in paths if path.is_file() and path.suffix == ".json" and is_build_artifact_json(path)]


def is_build_artifact_json(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and payload.get("schema_version") == "algolab-build-v1"


def rerender_artifacts(artifact_paths: list[Path], html_dir: Path) -> list[dict[str, Any]]:
    html_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, artifact_path in enumerate(artifact_paths, start=1):
        artifact = BuildArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
        artifact, compiler_refresh = refresh_scenes_with_current_compiler(artifact)
        html_path = save_html(artifact, html_dir / f"{artifact_path.stem}.html")
        records.append(
            {
                "case_index": index,
                "case_id": artifact_path.stem,
                "artifact_json": str(artifact_path),
                "html": str(html_path),
                "problem_title": artifact.problem_title,
                "variant_count": len(artifact.variants),
                "rerendered_with_current_compiler": compiler_refresh["rerendered_with_current_compiler"],
                "compiler_scene_count": compiler_refresh["compiler_scene_count"],
                "compiler_scene_errors": compiler_refresh["compiler_scene_errors"],
            }
        )
    return records


def refresh_scenes_with_current_compiler(artifact: BuildArtifact) -> tuple[BuildArtifact, dict[str, Any]]:
    """Rebuild embedded scenes from traces so audits cover the current compiler."""

    refreshed = artifact.model_copy(deep=True)
    compiler_scene_count = 0
    compiler_scene_errors: list[str] = []
    for variant in refreshed.variants:
        if variant.trace is None:
            continue
        try:
            refreshed.scenes[variant.id] = compile_scene(variant.trace)
            compiler_scene_count += 1
        except Exception as exc:  # pragma: no cover - surfaced in audit report for archived bad traces.
            compiler_scene_errors.append(f"{variant.id}: {type(exc).__name__}: {exc}")
    return refreshed, {
        "rerendered_with_current_compiler": compiler_scene_count > 0,
        "compiler_scene_count": compiler_scene_count,
        "compiler_scene_errors": compiler_scene_errors,
    }


def audit_records(
    records: list[dict[str, Any]],
    *,
    output_dir: Path,
    screenshot_dir: Path,
    capture_screenshots: bool,
    wait_ms: int,
) -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    audit_rows: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for record in records:
                audit_rows.extend(
                    audit_one_html(
                        browser,
                        record,
                        screenshot_dir=screenshot_dir,
                        capture_screenshots=capture_screenshots,
                        wait_ms=wait_ms,
                    )
                )
        finally:
            browser.close()
    add_primary_container_stability(audit_rows)
    return audit_rows


def audit_one_html(
    browser: Any,
    record: dict[str, Any],
    *,
    screenshot_dir: Path,
    capture_screenshots: bool,
    wait_ms: int,
) -> list[dict[str, Any]]:
    page = browser.new_page(viewport=DEFAULT_VIEWPORT)
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    rows: list[dict[str, Any]] = []
    html_path = Path(str(record["html"]))
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(wait_ms)
        variant_count = int(page.evaluate("() => (ARTIFACT.variants || []).length"))
        for variant_index in range(variant_count):
            page.evaluate("(i) => selectVariant(i)", variant_index)
            page.wait_for_timeout(wait_ms)
            variant_meta = page.evaluate(
                """() => {
                    const v = variant();
                    const sceneFrames = frames();
                    return {
                        variant_id: String(v && v.id || ''),
                        variant_name: String(v && v.name || ''),
                        frame_count: sceneFrames.length,
                    };
                }"""
            )
            for sample in sample_frame_indices(int(variant_meta["frame_count"])):
                step = int(sample["index"])
                label = str(sample["label"])
                page.evaluate("(i) => go(i)", step)
                page.wait_for_timeout(wait_ms)
                metrics = page.evaluate(AUDIT_JS, {"sampleLabel": label, "step": step})
                screenshot = ""
                if capture_screenshots:
                    screenshot_path = screenshot_dir / (
                        f"{int(record['case_index']):03d}_{safe_name(str(record['case_id']))}_"
                        f"{safe_name(str(variant_meta['variant_id']))}_{label}_"
                        f"step{step + 1:03d}of{int(variant_meta['frame_count']):03d}.png"
                    )
                    page.screenshot(path=str(screenshot_path), full_page=False)
                    screenshot = str(screenshot_path)
                row = {
                    **record,
                    **variant_meta,
                    "sample_label": label,
                    "frame_index": step,
                    "viewport": dict(DEFAULT_VIEWPORT),
                    "screenshot": screenshot,
                    "browser_errors": list(errors),
                    **metrics,
                }
                row["failure_categories"] = classify_failure_categories(row)
                row["ok"] = not row["failure_categories"] and not row["browser_errors"]
                rows.append(row)
    except Exception as exc:
        rows.append(
            {
                **record,
                "sample_label": "page",
                "frame_index": -1,
                "viewport": dict(DEFAULT_VIEWPORT),
                "screenshot": "",
                "browser_errors": [f"{type(exc).__name__}: {exc}", *errors],
                "failure_categories": ["browser_error"],
                "ok": False,
            }
        )
    finally:
        page.close()
    return rows


AUDIT_JS = r"""({sampleLabel, step}) => {
  const bool = value => Boolean(value);
  const text = node => node ? String(node.innerText || node.textContent || '') : '';
  const rectPayload = node => {
    if (!node) return null;
    const r = node.getBoundingClientRect();
    return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height, area:Math.max(0, r.width * r.height) };
  };
  const intersects = (a, b) => a && b && a.right >= b.left - 1 && a.left <= b.right + 1 && a.bottom >= b.top - 1 && a.top <= b.bottom + 1;
  const host = document.querySelector('#canvas');
  const stage = document.querySelector('#canvas .stage-grid');
  const sceneFit = document.querySelector('#canvas .scene-fit');
  const scene = document.querySelector('#canvas .objects');
  const primaryRects = Array.from(document.querySelectorAll('#canvas .primary-scene [data-stage-role="primary"]'))
    .map(rectPayload)
    .filter(Boolean);
  const telemetry = document.querySelector('#visual-quality-telemetry');
  const codeSync = document.querySelector('.code-sync');
  const timeline = document.querySelector('#timeline');
  const f = typeof frames === 'function' ? frames()[step] : null;
  const evidence = f && f.evidence || {};
  const targets = Array.isArray(evidence.targets) ? evidence.targets.map(String) : [];
  const deps = Array.isArray(evidence.deps) ? evidence.deps.map(String) : [];
  const visibleTargets = targets.filter(id => {
    const raw = String(id || '');
    return !isAnswerLikeId(raw) && !raw.startsWith('frame:');
  });
  const targetNode = visibleTargets.map(id => sceneObjectBySemanticIdInAudit(id)).find(Boolean) || null;
  const hostRect = rectPayload(host);
  const sceneFitRect = rectPayload(sceneFit);
  const sceneRect = rectPayload(scene);
  const targetRect = rectPayload(targetNode);
  const visibleRect = sceneFit && sceneFit.classList.contains('scroll-fit') ? sceneFitRect : hostRect;
  const visualBounds = measureAuditVisualBounds(scene);
  const visualBoundsRect = visualBounds && sceneRect ? {
    left: sceneRect.left + visualBounds.left,
    top: sceneRect.top + visualBounds.top,
    right: sceneRect.left + visualBounds.left + visualBounds.width,
    bottom: sceneRect.top + visualBounds.top + visualBounds.height,
    width: visualBounds.width,
    height: visualBounds.height,
    area: visualBounds.width * visualBounds.height,
  } : null;
  const primaryVisibleRatio = visibleAreaRatio(visualBoundsRect, sceneFitRect || hostRect);
  const primaryClipDetected = Boolean(visualBoundsRect && sceneFitRect && (
    visualBoundsRect.left < sceneFitRect.left - 6 ||
    visualBoundsRect.top < sceneFitRect.top - 6 ||
    visualBoundsRect.right > sceneFitRect.right + 6 ||
    visualBoundsRect.bottom > sceneFitRect.bottom + 6
  ));
  const answerPrimaryAreaRatio = answerAreaRatio(sceneFitRect);
  const graphNodeMinRadius = minGraphNodeRadius();
  const svgOccupiedRatio = occupiedSvgRatio();
  const renderedObjects = Array.from(document.querySelectorAll('#canvas [data-object-id], #canvas .semantic-anchor-chip, #canvas .cell, #canvas .mcell, #canvas svg .node, #canvas .primitive-panel, #canvas .gcd-hero'))
    .filter(node => {
      const r = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    });
  const frameCodeLine = Number(f && f.code_line);
  const codeLineValid = Number.isInteger(frameCodeLine)
    && frameCodeLine > 0
    && typeof variant === 'function'
    && frameCodeLine <= String((variant() && variant().code) || '').split('\n').length;
  const lineStatus = codeSync ? String(codeSync.getAttribute('data-code-line-status') || '') : '';
  const dependencyRequired = deps.length > 0 && targets.length > 0;
  const dependencyVisible = !dependencyRequired
    || document.querySelector('#canvas .dependency-flow, #canvas .dependency-edge, #canvas [data-visual-pattern], #canvas .dp-dependency-arrow') !== null;
  const teachingRequired = dependencyRequired || Boolean(evidence.process) || Boolean((evidence.visual_patterns || []).length);
  const teachingRelationVisible = !teachingRequired
    || document.querySelector('#canvas .visual-card, #canvas .dependency-flow, #canvas .edge.hot, #canvas .edge.dep, #canvas .edge.answer, #canvas [data-teaching-relation="teaching_relation_visible"]') !== null;
  const fitScale = Number(scene && scene.dataset.fitScale || 0);
  const fitMode = String(scene && scene.dataset.fitMode || '');
  const utilization = Number(scene && scene.dataset.utilization || 0);
  const primaryScrollable = fitMode === 'pan-scroll' && Boolean(sceneFit && (
    sceneFit.scrollWidth > sceneFit.clientWidth + 2 || sceneFit.scrollHeight > sceneFit.clientHeight + 2
  ));
  const familyRenderer = String(stage && stage.dataset.familyRenderer || telemetry && telemetry.dataset.familyRenderer || '');
  const expectedFamily = expectedFamilyForCase(String((ARTIFACT && ARTIFACT.problem_title) || '') + ' ' + String(location.pathname || ''));
  const semanticAnchorVisible = semanticAnchorVisibility(sceneFitRect);
  const fixedOverlayBlocksPrimary = fixedOverlayBlocksPrimaryContent();
  const unexpectedGeometryRelation = document.querySelector('#canvas .geometry-relation-card') !== null
    && expectedFamily !== 'geometry'
    && familyRenderer !== 'geometry';
  const supportDockClipped = supportDockHiddenClip();
  const svgInternalClipCount = primarySvgInternalClipCount();
  const familyRendererUsed = !expectedFamily || familyRendererMatches(expectedFamily, familyRenderer)
    || document.querySelector(selectorForExpectedFamily(expectedFamily)) !== null;
  const rawInPrimary = document.querySelector('#canvas .primary-scene [data-stage-role="raw"]') !== null;
  const rawStateNotPrimary = !rawInPrimary;
  const overflowX = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
    return {
    sample_label: sampleLabel,
    frame_title: String(f && f.title || ''),
    frame_operation: String(f && f.operation || ''),
    timeline_phase: String(evidence && evidence.timeline && evidence.timeline.phase || ''),
    main_stage_utilization: utilization,
    visual_bounds_left: visualBounds ? visualBounds.left : null,
    visual_bounds_top: visualBounds ? visualBounds.top : null,
    visual_bounds_right: visualBounds ? visualBounds.left + visualBounds.width : null,
    visual_bounds_bottom: visualBounds ? visualBounds.top + visualBounds.height : null,
    primary_visible_ratio: primaryVisibleRatio,
    primary_clip_detected: primaryClipDetected,
    multi_primary_fit_mode: primaryRects.length > 1 ? fitMode : '',
    answer_primary_area_ratio: answerPrimaryAreaRatio,
    graph_node_min_radius: graphNodeMinRadius,
    svg_occupied_ratio: svgOccupiedRatio,
    fit_scale: fitScale,
    fit_mode: fitMode,
    requested_fit_mode: String(scene && scene.dataset.requestedFitMode || ''),
    primary_scrollable: primaryScrollable,
    canvas_has_rendered_objects: renderedObjects.length > 0,
    rendered_object_count: renderedObjects.length,
    active_target_required: visibleTargets.length > 0,
    active_target_id: visibleTargets[0] || '',
    active_target_visible: activeTargetVisibleInAudit(targetNode, targetRect, visibleRect, primaryScrollable),
    readable_scale: fitMode === 'contain' || fitScale >= 1.0 || fitMode === 'scroll' || fitMode === 'focus',
    dependency_required: dependencyRequired,
    dependency_visible: dependencyVisible,
    code_line_status_visible: codeSync !== null && (codeLineValid ? lineStatus === 'ok' : lineStatus === 'warn'),
    code_line_valid: codeLineValid,
    code_line_status: lineStatus,
    no_major_overflow: !overflowX,
    timeline_keyframes_visible: timeline !== null && timeline.querySelectorAll('.tick').length > 0,
    timeline_keyframe_count: timeline ? timeline.querySelectorAll('.tick.keyframe').length : 0,
    raw_state_not_primary: rawStateNotPrimary,
    semantic_anchor_visible: semanticAnchorVisible,
    fixed_overlay_blocks_primary: fixedOverlayBlocksPrimary,
    unexpected_geometry_relation: unexpectedGeometryRelation,
    support_dock_clipped: supportDockClipped,
    svg_internal_clip_count: svgInternalClipCount,
    teaching_relation_visible: teachingRelationVisible,
    teaching_relation_required: teachingRequired,
    family_renderer: familyRenderer,
    expected_family_renderer: expectedFamily,
    family_renderer_used: familyRendererUsed,
    primary_rect: aggregateRects(primaryRects),
    primary_rect_count: primaryRects.length,
    scene_rect: sceneRect,
    host_rect: hostRect,
    target_rect: targetRect,
    telemetry_text: text(telemetry),
  };

  function expectedFamilyForCase(text) {
    const value = text.toLowerCase();
    if (/edmonds|network[_ -]?flow|max[_ -]?flow/.test(value)) return 'network_flow';
    if (/convex|geometry|hull/.test(value)) return 'geometry';
    if (/reverse[_ -]?linked|linked[_ -]?list|cycle/.test(value)) return 'linked_list';
    if (/daily[_ -]?temperatures|monotonic/.test(value)) return 'monotonic_stack';
    if (/kth[_ -]?largest|heap/.test(value)) return 'heap';
    if (/gcd|fast[_ -]?power|lowbit|sieve/.test(value)) return 'math_bit';
    if (/trie/.test(value)) return 'trie';
    if (/kmp|rabin|z[_ -]?algorithm|manacher|string/.test(value)) return 'string_specialized';
    if (/state[_ -]?compression|tsp/.test(value)) return 'bitmask_dp';
    if (/fenwick|sparse[_ -]?table|difference[_ -]?array|prefix[_ -]?sum|segment[_ -]?tree/.test(value)) return 'range_structure';
    if (/digit[_ -]?dp/.test(value)) return 'digit_dp';
    if (/tree[_ -]?max|tree[_ -]?dp/.test(value)) return 'tree_dp';
    if (/kruskal/.test(value)) return 'kruskal';
    if (/graph|dijkstra|bellman|tarjan|bfs|dfs|topological|bipartite|province|floyd/.test(value)) return 'graph';
    return '';
  }
  function familyRendererMatches(expected, actual) {
    if (!expected) return true;
    if (actual === expected) return true;
    if (expected === 'string_specialized' && ['string_specialized','string_list','trie'].includes(actual)) return true;
    if (expected === 'trie' && ['trie','tree','string_specialized'].includes(actual)) return true;
    if (expected === 'graph' && ['graph','dp_matrix'].includes(actual)) return true;
    if (expected === 'kruskal' && ['kruskal','graph'].includes(actual)) return true;
    if (expected === 'bitmask_dp' && ['bitmask_dp','dp_matrix','math_bit'].includes(actual)) return true;
    if (expected === 'range_structure' && ['range_structure','graph','tree','dp_matrix'].includes(actual)) return true;
    if (expected === 'digit_dp' && actual === 'digit_dp') return true;
    if (expected === 'heap' && actual === 'heap') return true;
    if (expected === 'monotonic_stack' && actual === 'monotonic_stack') return true;
    if (expected === 'math_bit' && actual) return true;
    return false;
  }
  function selectorForExpectedFamily(expected) {
    return ({
      network_flow: '.network-flow-pattern, .network-augmenting-path-panel, .flow-bottleneck-label',
      geometry: '.geometry-svg, .geometry-relation-card',
      linked_list: '.linked-list-view, .linked-node',
      monotonic_stack: '.monotonic-stack-panel',
      heap: '.heap-sift-panel, .heap',
      math_bit: '.math-bit-panel, [data-math-kind]',
      bitmask_dp: '.bitmask-transition-panel, [data-visual-pattern="bitmask_transition"]',
      kruskal: '.kruskal-track-panel, [data-visual-pattern="kruskal_edge_order"], .graph-svg',
      string_specialized: '.string-specialized-card, .string-alignment-card, .array-wrap',
      trie: '.tree-svg, .tree-dp-overlay',
      range_structure: '.range-structure-pattern, .fenwick-lowbit-panel, .sparse-table-blocks, .diff-prefix-panel',
      digit_dp: '.digit-dp-card',
      tree_dp: '.tree-dp-overlay, .tree-svg',
      graph: '.graph-svg, .graph-metric-overlay',
    })[expected] || '.__missing_expected_family__';
  }
  function sceneObjectBySemanticIdInAudit(id) {
    const scope = document.querySelector('#canvas');
    if (!scope) return null;
    const direct = sceneObjectByIdInAudit(scope, id);
    if (direct) return direct;
    for (const proxyId of semanticProxyIdsInAudit(id)) {
      const proxy = sceneObjectByIdInAudit(scope, proxyId);
      if (proxy) return proxy;
    }
    if (String(id) === 'answer' || String(id) === 'result') {
      return scope.querySelector(answerStateProxySelectorsInAudit()) || semanticFallbackObjectInAudit(scope, id);
    }
    return semanticFallbackObjectInAudit(scope, id);
  }
  function sceneObjectByIdInAudit(scope, id) {
    return Array.from(scope.querySelectorAll('[data-object-id]')).find(node => node.getAttribute('data-object-id') === String(id));
  }
  function semanticProxyIdsInAudit(id) {
    const raw = String(id || '');
    const proxies = [];
    const edgeMatch = raw.match(/^edge:([^>]+)->(.+)$/);
    if (edgeMatch && edgeMatch[1] && edgeMatch[2]) {
      proxies.push(`edge-label:${edgeMatch[1]}->${edgeMatch[2]}`, `node:${edgeMatch[1]}`, `node:${edgeMatch[2]}`);
    }
    const frameMatch = raw.match(/^frame:[^(]+\(([^()]*)\)$/);
    if (frameMatch && frameMatch[1]) {
      proxies.push(`node:${frameMatch[1]}`, frameMatch[1]);
    }
    const plainNodeMatch = raw.match(/^(?:current|node|vertex)[_:]([A-Za-z0-9_.-]+)$/);
    if (plainNodeMatch && plainNodeMatch[1]) proxies.push(`node:${plainNodeMatch[1]}`);
    return proxies;
  }
  function semanticFallbackObjectInAudit(scope, id) {
    const raw = String(id || '');
    if (!scope) return null;
    if (raw.startsWith('frame:')) {
      const framePhaseMatch = raw.match(/^frame:(?:phase\/)?([^()]+)$/);
      if (framePhaseMatch && framePhaseMatch[1]) {
        const phaseText = framePhaseMatch[1].replace(/_/g, ' ');
        const node = Array.from(scope.querySelectorAll('[data-object-id]')).find(item => String(item.getAttribute('data-object-id') || '').includes(phaseText));
        if (node) return node;
      }
      return scope.querySelector('.primary-scene [data-stage-role="primary"], [data-stage-role="primary"], [data-object-id]');
    }
    const stateProxy = sceneObjectByIdInAudit(scope, raw)
      || sceneObjectByIdInAudit(scope, `pointer:${raw}`)
      || sceneObjectByIdInAudit(scope, `node:${raw}`);
    if (stateProxy) return stateProxy;
    const localCell = localStateCellProxyInAudit(scope, raw);
    if (localCell) return localCell;
    const prefixProxy = Array.from(scope.querySelectorAll('[data-object-id]')).find(item => {
      const objectId = String(item.getAttribute('data-object-id') || '');
      return objectId === raw || objectId.startsWith(`${raw}[`) || objectId.endsWith(`:${raw}`);
    });
    if (prefixProxy) return prefixProxy;
    if (raw === 'answer' || raw === 'result') return scope.querySelector(answerStateProxySelectorsInAudit());
    return null;
  }
  function localStateCellProxyInAudit(scope, raw) {
    const evidence = f && f.evidence || {};
    const eventCell = indexedReferenceCellProxyInAudit(scope, evidence.value);
    if (eventCell) return eventCell;
    const state = f && f.state || {};
    const value = state[raw];
    if (!Number.isInteger(Number(value))) return null;
    const containerId = primaryLinearContainerIdInAudit(f);
    if (!containerId) return null;
    return sceneObjectByIdInAudit(scope, `${containerId}[${Number(value)}]`);
  }
  function indexedReferenceCellProxyInAudit(scope, value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const container = value.on ?? value.container ?? value.array ?? value.source;
    const idx = value.idx ?? value.index ?? value.i;
    if (!container || !Number.isInteger(Number(idx))) return null;
    return sceneObjectByIdInAudit(scope, `${container}[${Number(idx)}]`);
  }
  function primaryLinearContainerIdInAudit(frame) {
    const state = frame && frame.state || {};
    for (const key of ['dp','nums','arr','array','values','temperatures','prices','heights']) {
      const value = state[key];
      if (Array.isArray(value) && value.every(item => !Array.isArray(item) && (item === null || typeof item !== 'object'))) return key;
    }
    const container = (frame && frame.objects || []).find(o => o && o.type === 'container' && o.meta && ['array','string'].includes(o.meta.layout));
    return container ? container.id : '';
  }
  function answerStateProxySelectorsInAudit() {
    return '.answer-badge[data-object-id], .role-answer[data-object-id], .pattern-answer-projection[data-object-id], .answer[data-object-id], [data-object-id="answer"], [data-object-id="ans"], [data-object-id="result"], [data-object-id^="answer["], [data-object-id^="ans["], [data-object-id^="result["], .hot[data-object-id], .node.role-answer, .node.pattern-answer-projection, .node.answer, .node.hot, .cell.answer, .mcell.answer';
  }
  function isAnswerLikeId(raw) {
    const id = String(raw || '');
    return ['answer','ans','result'].includes(id) || id.startsWith('answer[') || id.startsWith('ans[') || id.startsWith('result[');
  }
  function activeTargetVisibleInAudit(node, rect, viewport, scrollable) {
    if (!node) return true;
    if (!node.closest('.primary-scene')) return true;
    if (scrollable) return true;
    return intersects(rect, viewport);
  }
  function measureAuditVisualBounds(scope) {
    if (!scope) return null;
    const selectors = [
      ':scope > .primitive-panel[data-stage-role="primary"]',
      ':scope svg',
      ':scope [data-object-id]',
      ':scope .cell',
      ':scope .mcell',
      ':scope .node',
      ':scope .edge-label',
      ':scope .gcd-hero',
    ];
    const sceneBox = scope.getBoundingClientRect();
    const rects = Array.from(scope.querySelectorAll(selectors.join(','))).filter(node => {
      if (node.closest('.semantic-anchor-band') || node.closest('.answer-badge')) return false;
      const objectId = String(node.getAttribute('data-object-id') || '');
      const panel = node.closest('[data-object-id]');
      const panelId = String(panel && panel.getAttribute('data-object-id') || '');
      if (isAnswerLikeId(objectId) || isAnswerLikeId(panelId)) return false;
      const style = getComputedStyle(node);
      const r = node.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
    }).map(node => node.getBoundingClientRect()).filter(r => r.width > 0 && r.height > 0);
    if (!rects.length) return null;
    const left = Math.min(...rects.map(r => r.left)) - sceneBox.left;
    const top = Math.min(...rects.map(r => r.top)) - sceneBox.top;
    const right = Math.max(...rects.map(r => r.right)) - sceneBox.left;
    const bottom = Math.max(...rects.map(r => r.bottom)) - sceneBox.top;
    return { left, top, width:Math.max(1, right - left), height:Math.max(1, bottom - top) };
  }
  function visibleAreaRatio(rect, viewport) {
    if (!rect || !viewport || !rect.area) return 1;
    const left = Math.max(rect.left, viewport.left);
    const top = Math.max(rect.top, viewport.top);
    const right = Math.min(rect.right, viewport.right);
    const bottom = Math.min(rect.bottom, viewport.bottom);
    const area = Math.max(0, right - left) * Math.max(0, bottom - top);
    return area / Math.max(1, rect.area);
  }
  function answerAreaRatio(viewport) {
    if (!viewport) return 0;
    const nodes = Array.from(document.querySelectorAll('#canvas .primary-scene [data-object-id], #canvas .answer-badge')).filter(node => {
      const id = String(node.getAttribute('data-object-id') || '');
      return node.classList.contains('answer-badge') || isAnswerLikeId(id) || node.classList.contains('answer') || node.classList.contains('role-answer');
    });
    const area = nodes.map(rectPayload).filter(Boolean).reduce((sum, rect) => sum + rect.area, 0);
    return area / Math.max(1, viewport.area || viewport.width * viewport.height);
  }
  function semanticAnchorVisibility(viewport) {
    const anchors = Array.from(document.querySelectorAll('#canvas .semantic-anchor-band'));
    if (!anchors.length || !viewport) return true;
    return anchors.every(anchor => {
      const rect = rectPayload(anchor);
      return Boolean(rect)
        && rect.top >= viewport.top - 2
        && rect.left >= viewport.left - 2
        && rect.right <= viewport.right + 2
        && rect.bottom <= viewport.bottom + 2
        && visibleAreaRatio(rect, viewport) >= 0.98;
    });
  }
  function fixedOverlayBlocksPrimaryContent() {
    const overlays = Array.from(document.querySelectorAll('#canvas .scene-fit > .semantic-anchor-band, #canvas .scene-fit > .answer-badge'))
      .map(rectPayload)
      .filter(Boolean);
    if (!overlays.length) return false;
    const nodes = Array.from(document.querySelectorAll('#canvas .primary-scene svg .node, #canvas .primary-scene svg text, #canvas .primary-scene [data-object-id], #canvas .primary-scene .cell, #canvas .primary-scene .mcell, #canvas .primary-scene .gcd-hero'))
      .filter(node => {
        if (node.closest('.semantic-anchor-band') || node.closest('.answer-badge')) return false;
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
      })
      .map(rectPayload)
      .filter(Boolean);
    return overlays.some(overlay => nodes.some(rect => (
      rect.right > overlay.left + 1 &&
      rect.left < overlay.right - 1 &&
      rect.bottom > overlay.top + 1 &&
      rect.top < overlay.bottom - 1
    )));
  }
  function minGraphNodeRadius() {
    const radii = Array.from(document.querySelectorAll('#canvas .primary-scene .graph-svg .node circle, #canvas .primary-scene .tree-svg .node circle, #canvas .primary-scene .cycle-list-svg circle, #canvas .primary-scene .heap-svg circle')).map(circle => {
      const r = circle.getBoundingClientRect();
      return Math.min(r.width, r.height) / 2;
    }).filter(value => Number.isFinite(value) && value > 0);
    return radii.length ? Math.min(...radii) : null;
  }
  function occupiedSvgRatio() {
    const svgs = Array.from(document.querySelectorAll('#canvas .primary-scene svg'));
    const ratios = svgs.map(svg => {
      const svgRect = rectPayload(svg);
      const objectRects = Array.from(svg.querySelectorAll('.node, .edge, .edge-label, .cycle-node, .cycle-edge, .heap-node, .heap-edge'))
        .map(rectPayload)
        .filter(Boolean);
      const union = aggregateRects(objectRects);
      return svgRect && union ? Math.min(1, union.area / Math.max(1, svgRect.area)) : null;
    }).filter(value => value !== null);
    return ratios.length ? Math.max(...ratios) : null;
  }
  function supportDockHiddenClip() {
    return Array.from(document.querySelectorAll('#canvas .support-dock')).some(dock => {
      const style = getComputedStyle(dock);
      return dock.scrollHeight > dock.clientHeight + 3 && ['hidden','clip'].includes(style.overflowY);
    });
  }
  function primarySvgInternalClipCount() {
    let count = 0;
    for (const svg of document.querySelectorAll('#canvas .primary-scene svg')) {
      const svgRect = svg.getBoundingClientRect();
      if (!svgRect || svgRect.width <= 0 || svgRect.height <= 0) continue;
      for (const node of svg.querySelectorAll('.node, .cycle-node, .heap-node')) {
        const rect = node.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;
        if (
          rect.left < svgRect.left - 1 ||
          rect.top < svgRect.top - 1 ||
          rect.right > svgRect.right + 1 ||
          rect.bottom > svgRect.bottom + 1
        ) count += 1;
      }
    }
    return count;
  }
  function aggregateRects(rects) {
    const clean = (rects || []).filter(Boolean);
    if (!clean.length) return null;
    const left = Math.min(...clean.map(r => r.left));
    const top = Math.min(...clean.map(r => r.top));
    const right = Math.max(...clean.map(r => r.right));
    const bottom = Math.max(...clean.map(r => r.bottom));
    const width = Math.max(0, right - left);
    const height = Math.max(0, bottom - top);
    return { left, top, right, bottom, width, height, area: width * height };
  }
}"""


def classify_failure_categories(row: dict[str, Any]) -> list[str]:
    categories: list[str] = []
    if row.get("browser_errors"):
        categories.append("browser_error")
    if not row.get("canvas_has_rendered_objects"):
        categories.append("empty_stage")
    if float(row.get("main_stage_utilization") or 0.0) < LOW_UTILIZATION_THRESHOLD:
        categories.append("low_main_stage_utilization")
    primary_scrollable = bool(row.get("primary_scrollable"))
    if row.get("primary_clip_detected") and not primary_scrollable:
        categories.append("primary_clip_detected")
    if float(row.get("primary_visible_ratio") or 1.0) < MIN_PRIMARY_VISIBLE_RATIO and not primary_scrollable:
        categories.append("primary_visible_ratio_low")
    if int(row.get("primary_rect_count") or 0) > 1 and row.get("fit_mode") == "focus":
        categories.append("multi_primary_focus")
    if float(row.get("answer_primary_area_ratio") or 0.0) > MAX_ANSWER_PRIMARY_AREA_RATIO and int(row.get("primary_rect_count") or 0) > 1:
        categories.append("answer_steals_primary")
    node_radius = row.get("graph_node_min_radius")
    if node_radius is not None and float(node_radius or 0.0) < MIN_GRAPH_NODE_RADIUS:
        categories.append("graph_node_too_small")
    if not row.get("active_target_visible"):
        categories.append("active_target_not_visible")
    if not row.get("readable_scale"):
        categories.append("below_readable_scale")
    if not row.get("dependency_visible"):
        categories.append("dependency_not_visible")
    if not row.get("code_line_status_visible"):
        categories.append("code_line_status_missing")
    if not row.get("no_major_overflow"):
        categories.append("major_page_overflow")
    if not row.get("timeline_keyframes_visible"):
        categories.append("timeline_missing")
    if not row.get("raw_state_not_primary"):
        categories.append("raw_state_primary")
    if not row.get("semantic_anchor_visible"):
        categories.append("semantic_anchor_clipped")
    if row.get("fixed_overlay_blocks_primary"):
        categories.append("fixed_overlay_blocks_primary")
    if row.get("unexpected_geometry_relation"):
        categories.append("unexpected_geometry_relation")
    if row.get("support_dock_clipped"):
        categories.append("support_dock_clipped")
    if int(row.get("svg_internal_clip_count") or 0) > 0:
        categories.append("svg_internal_clip")
    if not row.get("teaching_relation_visible"):
        categories.append("teaching_relation_missing")
    if not row.get("family_renderer_used"):
        categories.append("family_renderer_missing")
    return categories


def add_primary_container_stability(rows: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[
            (
                str(row.get("case_id") or ""),
                str(row.get("variant_id") or ""),
                str(row.get("timeline_phase") or ""),
                str(row.get("family_renderer") or ""),
                str(row.get("requested_fit_mode") or ""),
            )
        ].append(row)

    for group_rows in groups.values():
        areas = [float((row.get("primary_rect") or {}).get("area") or 0) for row in group_rows]
        positive = [area for area in areas if area > 0]
        if len(positive) < 2:
            stable = True
            ratio = 1.0
        else:
            min_area = min(positive)
            max_area = max(positive)
            ratio = min_area / max_area if max_area else 0.0
            stable = ratio >= 0.70
        for row in group_rows:
            row["primary_container_stable"] = stable
            row["primary_container_area_ratio"] = ratio
            if not stable and "primary_container_unstable" not in row["failure_categories"]:
                row["failure_categories"].append("primary_container_unstable")
            row["ok"] = not row["failure_categories"] and not row.get("browser_errors")


def build_quality_summary(records: list[dict[str, Any]], audit_rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [row for row in audit_rows if not row.get("ok")]
    failure_counter = Counter(category for row in audit_rows for category in row.get("failure_categories", []))
    low_utilization = [row for row in audit_rows if float(row.get("main_stage_utilization") or 0.0) < LOW_UTILIZATION_THRESHOLD]
    family_counter = Counter(str(row.get("family_renderer") or "unknown") for row in audit_rows)
    quality_summary = {
        "artifact_count": len(records),
        "sample_count": len(audit_rows),
        "ok": not failures,
        "passed": len(audit_rows) - len(failures),
        "failed": len(failures),
        "low_utilization_threshold": LOW_UTILIZATION_THRESHOLD,
        "low_utilization_count": len(low_utilization),
        "low_utilization_ratio": len(low_utilization) / max(1, len(audit_rows)),
        "failure_categories": dict(sorted(failure_counter.items())),
        "family_renderer_counts": dict(sorted(family_counter.items())),
    }
    return quality_summary


def write_report(
    *,
    output_dir: Path,
    artifact_dir: Path,
    html_dir: Path,
    screenshot_dir: Path,
    records: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    quality_summary = build_quality_summary(records, audit_rows)
    report = {
        "schema_version": "renderer-visual-quality-audit-v1",
        "created_at": now_iso(),
        "artifact_dir": str(artifact_dir),
        "html_dir": str(html_dir),
        "screenshot_dir": str(screenshot_dir),
        "viewport": dict(DEFAULT_VIEWPORT),
        "thresholds": {
            "main_stage_utilization": LOW_UTILIZATION_THRESHOLD,
            "min_readable_scale": MIN_READABLE_SCALE,
            "primary_visible_ratio": MIN_PRIMARY_VISIBLE_RATIO,
            "answer_primary_area_ratio": MAX_ANSWER_PRIMARY_AREA_RATIO,
            "graph_node_min_radius": MIN_GRAPH_NODE_RADIUS,
        },
        "quality_summary": quality_summary,
        "artifacts": records,
        "samples": audit_rows,
    }
    path = output_dir / "renderer_visual_quality_audit.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--artifact-glob", default="*.json")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    parser.add_argument("--wait-ms", type=int, default=90)
    parser.add_argument("--capture-screenshots", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fail-on-violations", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--max-artifacts", type=int, default=0, help="调试用：只审计前 N 个 artifact，0 表示全量")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_dir = args.artifact_dir.resolve()
    output_dir = args.output_dir or (ROOT / "output" / "renderer_visual_audit" / artifact_dir.name)
    output_dir = output_dir.resolve()
    html_dir = output_dir / "html"
    screenshot_dir = (args.screenshot_dir or (output_dir / "screenshots")).resolve()

    artifact_paths = collect_artifact_paths(artifact_dir, args.artifact_glob)
    if args.max_artifacts and args.max_artifacts > 0:
        artifact_paths = artifact_paths[: args.max_artifacts]
    if not artifact_paths:
        raise SystemExit(f"no BuildArtifact JSON files found in {artifact_dir} with {args.artifact_glob}")

    records = rerender_artifacts(artifact_paths, html_dir)
    audit_rows = audit_records(
        records,
        output_dir=output_dir,
        screenshot_dir=screenshot_dir,
        capture_screenshots=bool(args.capture_screenshots),
        wait_ms=int(args.wait_ms),
    )
    report_path = write_report(
        output_dir=output_dir,
        artifact_dir=artifact_dir,
        html_dir=html_dir,
        screenshot_dir=screenshot_dir,
        records=records,
        audit_rows=audit_rows,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report["quality_summary"]
    print(json.dumps({"report": str(report_path), "quality_summary": summary}, ensure_ascii=False, indent=2))
    if args.fail_on_violations and not summary["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
