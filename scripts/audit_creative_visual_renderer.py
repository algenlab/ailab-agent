"""Audit LLM Direct Visual Renderer pages with Playwright."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def collect_html_paths(html_dir: Path, pattern: str) -> list[Path]:
    return sorted(path for path in html_dir.glob(pattern) if path.is_file() and path.suffix.lower() == ".html")


def audit_one_html(
    browser: Any,
    html_path: Path,
    screenshot_dir: Path,
    wait_ms: int,
    *,
    require_result_visible: bool = False,
    require_stage_visual_quality: bool = False,
    stage_audit_max_frames: int = 4,
) -> dict[str, Any]:
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    row: dict[str, Any] = {
        "html": str(html_path),
        "case_id": html_path.stem.replace("_creative_stage", "").replace("_creative", ""),
        "page_load_ok": False,
        "console_error_count": 0,
        "page_error_count": 0,
        "deterministic_shell_present": False,
        "teaching_panel_visible": False,
        "code_panel_visible": False,
        "timeline_visible": False,
        "creative_stage_host_visible": False,
        "visual_non_empty": False,
        "frame_switch_ok": False,
        "range_control_ok": False,
        "uses_trace_data": False,
        "trace_mutation_detected": True,
        "result_visible": False,
        "main_area_not_blank": False,
        "stage_layout_audit_supported": False,
        "stage_visual_quality_ok": False,
        "stage_audited_frame_count": 0,
        "stage_overlap_count": 0,
        "stage_overlap_max": 0,
        "stage_clipped_count": 0,
        "stage_clipped_max": 0,
        "stage_text_occlusion_count": 0,
        "stage_text_occlusion_max": 0,
        "stage_layout_issues": [],
        "screenshot_non_empty": False,
        "screenshot": "",
        "failure_reason": "",
    }
    try:
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(wait_ms)
        row["page_load_ok"] = True
        before_artifact = page.evaluate("() => document.getElementById('algolab-artifact')?.textContent || ''")
        metrics = page.evaluate(AUDIT_JS)
        stage_quality = page.evaluate(
            STAGE_QUALITY_AUDIT_JS,
            {"maxFrames": int(stage_audit_max_frames), "waitMs": int(wait_ms)},
        )
        switch = page.evaluate(SWITCH_JS)
        page.wait_for_timeout(wait_ms)
        after_artifact = page.evaluate("() => document.getElementById('algolab-artifact')?.textContent || ''")
        screenshot_path = screenshot_dir / f"{html_path.stem}.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        row.update(metrics)
        row.update(stage_quality)
        row.update(switch)
        row["trace_mutation_detected"] = before_artifact != after_artifact
        row["console_error_count"] = len(console_errors)
        row["page_error_count"] = len(page_errors)
        row["screenshot"] = str(screenshot_path)
        row["screenshot_non_empty"] = screenshot_path.exists() and screenshot_path.stat().st_size > 2048
    except Exception as exc:
        row["failure_reason"] = f"{type(exc).__name__}: {exc}"
    finally:
        page.close()
    row["console_errors"] = console_errors
    row["page_errors"] = page_errors
    row["creative_ok"] = bool(
        row["page_load_ok"]
        and row["console_error_count"] == 0
        and row["page_error_count"] == 0
        and row["visual_non_empty"]
        and row["frame_switch_ok"]
        and not row["trace_mutation_detected"]
        and row["main_area_not_blank"]
        and row["screenshot_non_empty"]
        and (row["result_visible"] or not require_result_visible)
        and (row["stage_visual_quality_ok"] or not require_stage_visual_quality)
    )
    failures = []
    for key in (
        "page_load_ok",
        "visual_non_empty",
        "frame_switch_ok",
        "main_area_not_blank",
        "screenshot_non_empty",
    ):
        if not row.get(key):
            failures.append(key)
    if require_result_visible and not row.get("result_visible"):
        failures.append("result_visible")
    if require_stage_visual_quality and not row.get("stage_visual_quality_ok"):
        failures.append("stage_visual_quality_ok")
    if row.get("trace_mutation_detected"):
        failures.append("trace_mutation_detected")
    if row.get("console_error_count"):
        failures.append("console_errors")
    if row.get("page_error_count"):
        failures.append("page_errors")
    if row.get("failure_reason"):
        failures.append(str(row["failure_reason"]))
    row["failure_categories"] = failures
    return row


def audit_html_path(
    html_path: Path,
    output_dir: Path,
    *,
    wait_ms: int = 300,
    require_result_visible: bool = False,
    require_stage_visual_quality: bool = False,
    stage_audit_max_frames: int = 4,
) -> dict[str, Any]:
    """Audit one creative HTML file with a fresh Playwright browser.

    This helper is intentionally importable by the generation benchmark so the
    same browser-level layout gate is used for standalone audits and automatic
    repair loops.
    """

    from playwright.sync_api import sync_playwright

    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            return audit_one_html(
                browser,
                html_path,
                screenshot_dir,
                wait_ms,
                require_result_visible=require_result_visible,
                require_stage_visual_quality=require_stage_visual_quality,
                stage_audit_max_frames=stage_audit_max_frames,
            )
        finally:
            browser.close()


AUDIT_JS = r"""() => {
  const text = node => node ? String(node.innerText || node.textContent || '') : '';
  const artifactNode = document.getElementById('algolab-artifact');
  let artifact = {};
  try { artifact = JSON.parse(artifactNode && artifactNode.textContent || '{}'); } catch (_) {}
  const bodyText = text(document.body);
  const stage = document.querySelector('#stage, #canvas, main, [data-creative-stage]');
  const stageText = text(stage);
  const shell = document.querySelector('#app[data-render-target="creative_stage_shell"], .creative-shell');
  const teachingPanel = document.querySelector('#teaching-panel, #teaching');
  const codePanel = document.querySelector('#code-panel, #code');
  const timeline = document.querySelector('#timeline');
  const stageHost = document.querySelector('#creative-stage-host');
  const visualNodes = Array.from(document.querySelectorAll('svg, canvas, #stage *, #canvas *, [data-visual], [data-derived-visual-only]'))
    .filter(node => {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return rect.width > 1 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden';
    });
  const firstVariant = (artifact.variants || [])[0] || {};
  const firstSceneForResult = Object.values(artifact.scenes || {})[0] || {};
  const verifiedResult = firstVariant.result ?? firstSceneForResult.result ?? artifact.verifier_result ?? artifact.expected_result ?? '';
  const resultText = JSON.stringify(verifiedResult);
  const compactBodyText = bodyText.replace(/\s+/g, '');
  const compactResultText = String(resultText).replace(/\s+/g, '');
  const resultVisible = resultText === '""'
    || bodyText.includes(resultText)
    || bodyText.includes(String(verifiedResult ?? ''))
    || (compactResultText && compactBodyText.includes(compactResultText));
  const frames = (() => {
    const scenes = artifact.scenes || {};
    const first = Object.values(scenes)[0] || {};
    return first.frames || [];
  })();
  const frameTokens = frames.slice(0, 3).flatMap(f => [f.title, f.operation, f.description]).filter(Boolean).map(String);
  const usesTrace = frameTokens.some(token => token && bodyText.includes(token.slice(0, Math.min(18, token.length))))
    || /frame|frames|state|evidence|trace|ARTIFACT|algolab-artifact/.test(document.documentElement.innerHTML);
  return {
    deterministic_shell_present: Boolean(shell),
    teaching_panel_visible: Boolean(teachingPanel && text(teachingPanel).trim().length > 0),
    code_panel_visible: Boolean(codePanel && text(codePanel).trim().length > 0),
    timeline_visible: Boolean(timeline && timeline.querySelectorAll('.tick, button').length > 0),
    creative_stage_host_visible: Boolean(stageHost && stageHost.getBoundingClientRect().width > 80 && stageHost.getBoundingClientRect().height > 80),
    visual_non_empty: Boolean((stageText && stageText.trim().length > 0) || visualNodes.length > 0),
    main_area_not_blank: Boolean(stage && stage.getBoundingClientRect().width > 80 && stage.getBoundingClientRect().height > 80 && (stageText.trim().length > 0 || visualNodes.length > 0)),
    uses_trace_data: usesTrace,
    result_visible: resultVisible,
    rendered_node_count: visualNodes.length,
    body_text_chars: bodyText.trim().length,
    artifact_frame_count: frames.length,
  };
}"""


STAGE_QUALITY_AUDIT_JS = r"""async (opts) => {
  const options = opts || {};
  const maxFrames = Number.isFinite(Number(options.maxFrames)) ? Number(options.maxFrames) : 4;
  const waitMs = Math.max(0, Math.min(1200, Number(options.waitMs || 0)));
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const nextPaint = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const round = value => Math.round(Number(value || 0) * 10) / 10;
  const host = document.querySelector('#creative-stage-host') || document.querySelector('#stage');

  function frameCount() {
    try {
      const shell = window.algolabCreativeShell;
      if (shell && typeof shell.frames === 'function') {
        const frames = shell.frames();
        if (Array.isArray(frames)) return frames.length;
      }
      const artifact = JSON.parse(document.getElementById('algolab-artifact')?.textContent || '{}');
      const first = Object.values(artifact.scenes || {})[0] || {};
      return (artifact.frames || first.frames || []).length || 1;
    } catch (_) {
      return 1;
    }
  }

  function currentFrameIndex() {
    const range = document.querySelector('#range');
    const fromRange = range ? Number(range.value) : NaN;
    if (Number.isFinite(fromRange)) return fromRange;
    const fromHost = host ? Number(host.dataset.frameIndex) : NaN;
    return Number.isFinite(fromHost) ? fromHost : 0;
  }

  function sampleIndices(total, limit) {
    const count = Math.max(1, Number(total) || 1);
    if (limit <= 0 || limit >= count) return Array.from({length: count}, (_, index) => index);
    const raw = [0, 1, Math.floor((count - 1) / 2), count - 1].filter(index => index >= 0 && index < count);
    const result = [];
    for (const index of raw) {
      if (!result.includes(index)) result.push(index);
      if (result.length >= limit) return result;
    }
    for (let index = 0; index < count && result.length < limit; index += 1) {
      if (!result.includes(index)) result.push(index);
    }
    return result;
  }

  async function goFrame(index) {
    const shell = window.algolabCreativeShell;
    if (shell && typeof shell.go === 'function') {
      shell.go(index);
    } else {
      const range = document.querySelector('#range');
      if (range) {
        range.value = String(index);
        range.dispatchEvent(new Event('input', { bubbles: true }));
        range.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    await nextPaint();
    if (waitMs) await sleep(waitMs);
    await nextPaint();
  }

  function visible(node) {
    if (!node || !(node instanceof Element)) return false;
    const style = getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity || 1) < 0.05) return false;
    const rect = node.getBoundingClientRect();
    return rect.width >= 3 && rect.height >= 3;
  }

  function directText(node) {
    const text = String(node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim();
    return text;
  }

  function visibleChildCount(node) {
    return Array.from(node.children || []).filter(visible).length;
  }

  function classify(node) {
    const tag = String(node.tagName || '').toLowerCase();
    const cls = String(node.className && node.className.baseVal !== undefined ? node.className.baseVal : node.className || '');
    const dataVisual = String(node.getAttribute('data-visual') || node.getAttribute('data-derived-visual-only') || '');
    const layoutRole = String(node.getAttribute('data-layout-role') || '');
    const text = directText(node);
    const labelLike = /label|caption|legend|tick|axis|value|index|pointer|badge|chip|note|annotation/i.test(`${cls} ${dataVisual} ${layoutRole}`);
    const shapeLike = /node|cell|bar|card|tile|block|box|edge|interval|water|queen|path/i.test(`${cls} ${dataVisual} ${layoutRole}`);
    if (tag === 'text' || tag === 'foreignobject' || labelLike) return { role: 'text', text };
    if (text && visibleChildCount(node) === 0 && ['div', 'span', 'p', 'strong', 'code', 'small'].includes(tag)) {
      return { role: 'text', text };
    }
    if (dataVisual || shapeLike) return { role: 'visual', text };
    return null;
  }

  function box(node, hostRect) {
    const rect = node.getBoundingClientRect();
    return {
      x: round(rect.left - hostRect.left),
      y: round(rect.top - hostRect.top),
      width: round(rect.width),
      height: round(rect.height),
    };
  }

  function label(node, index) {
    const text = directText(node);
    const id = node.getAttribute('data-id') || node.getAttribute('data-visual') || node.id || '';
    const cls = String(node.className && node.className.baseVal !== undefined ? node.className.baseVal : node.className || '');
    const tag = String(node.tagName || '').toLowerCase();
    const suffix = text ? `: ${text.slice(0, 42)}` : (id || cls).slice(0, 42);
    return `${tag || 'node'}#${index}${suffix ? ` ${suffix}` : ''}`;
  }

  function intersection(a, b) {
    const left = Math.max(a.left, b.left);
    const right = Math.min(a.right, b.right);
    const top = Math.max(a.top, b.top);
    const bottom = Math.min(a.bottom, b.bottom);
    const width = right - left;
    const height = bottom - top;
    if (width <= 0 || height <= 0) return null;
    return { left, top, right, bottom, width, height, area: width * height };
  }

  function center(rect) {
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }

  function containsPoint(rect, point, pad = 2) {
    return point.x >= rect.left - pad && point.x <= rect.right + pad && point.y >= rect.top - pad && point.y <= rect.bottom + pad;
  }

  function nearestGroup(node) {
    let current = node;
    while (current && current !== host && current.parentElement) {
      const tag = String(current.tagName || '').toLowerCase();
      if (tag === 'g' || current.hasAttribute('data-visual-group') || current.hasAttribute('data-layout-group')) return current;
      current = current.parentElement;
    }
    return null;
  }

  function shapeKind(node) {
    const tag = String(node && node.tagName || '').toLowerCase();
    const cls = String(node && node.className && node.className.baseVal !== undefined ? node.className.baseVal : node && node.className || '');
    const role = String(node && node.getAttribute && (node.getAttribute('data-visual') || node.getAttribute('data-layout-role') || '') || '');
    return `${tag} ${cls} ${role}`;
  }

  function isConnector(node) {
    return /(^|\s)(line|polyline|path)(\s|$)|edge-line|connector|arrow/i.test(shapeKind(node));
  }

  function isEmbeddedTextInShape(textItem, visualItem) {
    if (!textItem || !visualItem || textItem.role !== 'text') return false;
    const point = center(textItem.rect);
    if (!containsPoint(visualItem.rect, point)) return false;
    if (textItem.area / Math.max(1, visualItem.area) > 0.35) return false;
    const sharedGroup = nearestGroup(textItem.node) && nearestGroup(textItem.node) === nearestGroup(visualItem.node);
    const kind = shapeKind(visualItem.node);
    const containerLike = /rect|circle|ellipse|foreignobject|panel|background|lane|card|tile|node|bar|cell|block|box|interval|water|queen/i.test(kind);
    return Boolean(sharedGroup || containerLike);
  }

  function isAllowedEmbeddedTop(textNode, top) {
    if (!top || !(top instanceof Element)) return false;
    const textRect = textNode.getBoundingClientRect();
    const topRect = top.getBoundingClientRect();
    if (textRect.width < 1 || textRect.height < 1 || topRect.width < 1 || topRect.height < 1) return false;
    if (textRect.width * textRect.height / Math.max(1, topRect.width * topRect.height) > 0.35) return false;
    if (!containsPoint(topRect, center(textRect))) return false;
    const sharedGroup = nearestGroup(textNode) && nearestGroup(textNode) === nearestGroup(top);
    const kind = shapeKind(top);
    const containerLike = /rect|circle|ellipse|foreignobject|panel|background|lane|card|tile|node|bar|cell|block|box|interval|water|queen/i.test(kind);
    return Boolean(sharedGroup || containerLike);
  }

  function isAllowedTop(textNode, top) {
    if (!top) return true;
    if (top === textNode || textNode.contains(top) || top.contains(textNode)) return true;
    if (isAllowedEmbeddedTop(textNode, top)) return true;
    const cls = String(top.className && top.className.baseVal !== undefined ? top.className.baseVal : top.className || '');
    const role = String(top.getAttribute && (top.getAttribute('data-layout-role') || top.getAttribute('data-visual') || '') || '');
    return /background|backdrop|grid|axis|lane|shell/i.test(`${cls} ${role}`);
  }

  function textOccluded(item) {
    if (item.role !== 'text') return null;
    const rect = item.node.getBoundingClientRect();
    const points = [
      [rect.left + rect.width / 2, rect.top + rect.height / 2],
      [rect.left + Math.min(rect.width - 1, Math.max(1, rect.width * 0.25)), rect.top + rect.height / 2],
      [rect.left + Math.min(rect.width - 1, Math.max(1, rect.width * 0.75)), rect.top + rect.height / 2],
    ];
    for (const [x, y] of points) {
      const stack = document.elementsFromPoint(x, y).filter(el => el !== document.documentElement && el !== document.body);
      const top = stack[0];
      if (!isAllowedTop(item.node, top)) {
        return {
          type: 'text_occlusion',
          node: item.name,
          blocked_by: label(top, 0),
          point: { x: round(x), y: round(y) },
          box: item.box,
        };
      }
    }
    return null;
  }

  function auditCurrentFrame(frameIndex) {
    if (!host || !visible(host)) {
      return {
        frame_index: frameIndex,
        overlap_count: 0,
        clipped_count: 0,
        text_occlusion_count: 0,
        issues: [{ type: 'stage_host_missing_or_hidden' }],
      };
    }
    const hostRect = host.getBoundingClientRect();
    const selector = [
      'svg text',
      'svg foreignObject',
      '[data-visual]',
      '[data-derived-visual-only]',
      '[data-layout-role]',
      '.label',
      '.node',
      '.cell',
      '.bar',
      '.card',
      '.tile',
      '.edge-label',
      '.caption',
      '.axis-label',
      '.value-label',
      '.pointer-label',
      '.legend',
      'span',
      'div',
      'p',
      'strong',
      'code',
      'small',
    ].map(part => `#creative-stage-host ${part}`).join(',');
    const nodes = Array.from(document.querySelectorAll(selector))
      .filter(node => node !== host && host.contains(node) && visible(node))
      .map((node, index) => {
        const meta = classify(node);
        if (!meta) return null;
        const rect = node.getBoundingClientRect();
        return {
          node,
          index,
          role: meta.role,
          text: meta.text,
          rect,
          area: rect.width * rect.height,
          box: box(node, hostRect),
          name: label(node, index),
        };
      })
      .filter(Boolean)
      .filter(item => item.area >= 12);

    const issues = [];
    for (const item of nodes) {
      const clipped = item.rect.left < hostRect.left - 3
        || item.rect.top < hostRect.top - 3
        || item.rect.right > hostRect.right + 3
        || item.rect.bottom > hostRect.bottom + 3;
      if (clipped) {
        issues.push({ type: 'clipped', node: item.name, box: item.box });
      }
      const occluded = textOccluded(item);
      if (occluded) issues.push(occluded);
    }

    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const a = nodes[i];
        const b = nodes[j];
        if (a.node.contains(b.node) || b.node.contains(a.node)) continue;
        if (isConnector(a.node) || isConnector(b.node)) continue;
        if (a.role !== 'text' && b.role !== 'text' && !(a.node.hasAttribute('data-visual') && b.node.hasAttribute('data-visual'))) continue;
        const hit = intersection(a.rect, b.rect);
        if (!hit || hit.area < 24) continue;
        const ratio = hit.area / Math.max(1, Math.min(a.area, b.area));
        if (ratio < 0.16) continue;
        if (isEmbeddedTextInShape(a.role === 'text' ? a : b, a.role === 'text' ? b : a)) continue;
        issues.push({
          type: 'overlap',
          a: a.name,
          b: b.name,
          intersection_ratio: round(ratio),
          a_box: a.box,
          b_box: b.box,
        });
      }
    }
    return {
      frame_index: frameIndex,
      candidate_count: nodes.length,
      overlap_count: issues.filter(item => item.type === 'overlap').length,
      clipped_count: issues.filter(item => item.type === 'clipped').length,
      text_occlusion_count: issues.filter(item => item.type === 'text_occlusion').length,
      issues: issues.slice(0, 8),
    };
  }

  try {
    const totalFrames = frameCount();
    const original = currentFrameIndex();
    const indices = sampleIndices(totalFrames, maxFrames);
    const frames = [];
    for (const index of indices) {
      await goFrame(index);
      frames.push(auditCurrentFrame(index));
    }
    await goFrame(original);
    const overlapTotal = frames.reduce((sum, item) => sum + Number(item.overlap_count || 0), 0);
    const clippedTotal = frames.reduce((sum, item) => sum + Number(item.clipped_count || 0), 0);
    const textOcclusionTotal = frames.reduce((sum, item) => sum + Number(item.text_occlusion_count || 0), 0);
    const overlapMax = Math.max(0, ...frames.map(item => Number(item.overlap_count || 0)));
    const clippedMax = Math.max(0, ...frames.map(item => Number(item.clipped_count || 0)));
    const textOcclusionMax = Math.max(0, ...frames.map(item => Number(item.text_occlusion_count || 0)));
    return {
      stage_layout_audit_supported: Boolean(host),
      stage_visual_quality_ok: Boolean(host) && overlapTotal === 0 && clippedTotal === 0 && textOcclusionTotal === 0,
      stage_audited_frame_count: frames.length,
      stage_audited_frames: indices,
      stage_overlap_count: overlapTotal,
      stage_overlap_max: overlapMax,
      stage_clipped_count: clippedTotal,
      stage_clipped_max: clippedMax,
      stage_text_occlusion_count: textOcclusionTotal,
      stage_text_occlusion_max: textOcclusionMax,
      stage_layout_issues: frames.flatMap(item => (item.issues || []).map(issue => ({ frame_index: item.frame_index, ...issue }))).slice(0, 20),
      stage_layout_frame_reports: frames,
    };
  } catch (error) {
    return {
      stage_layout_audit_supported: Boolean(host),
      stage_visual_quality_ok: false,
      stage_audited_frame_count: 0,
      stage_overlap_count: 0,
      stage_overlap_max: 0,
      stage_clipped_count: 0,
      stage_clipped_max: 0,
      stage_text_occlusion_count: 0,
      stage_text_occlusion_max: 0,
      stage_layout_issues: [{ type: 'stage_quality_audit_error', message: String(error && error.message || error) }],
      stage_layout_frame_reports: [],
    };
  }
}"""


SWITCH_JS = r"""() => {
  const beforeCounter = String(document.querySelector('#counter')?.innerText || '');
  const beforeText = String(document.body.innerText || '');
  const next = document.querySelector('#next');
  const range = document.querySelector('#range');
  let rangeOk = false;
  let switched = false;
  if (range && Number(range.max || 0) >= 1) {
    range.value = '1';
    range.dispatchEvent(new Event('input', { bubbles: true }));
    range.dispatchEvent(new Event('change', { bubbles: true }));
    rangeOk = String(range.value) === '1';
  } else if (next) {
    next.click();
  }
  const afterCounter = String(document.querySelector('#counter')?.innerText || '');
  const afterText = String(document.body.innerText || '');
  switched = beforeCounter !== afterCounter || beforeText !== afterText || rangeOk;
  const frameCount = (() => {
    try {
      const artifact = JSON.parse(document.getElementById('algolab-artifact')?.textContent || '{}');
      const first = Object.values(artifact.scenes || {})[0] || {};
      return (first.frames || []).length;
    } catch (_) { return 0; }
  })();
  return {
    frame_switch_ok: frameCount <= 1 || switched,
    range_control_ok: !range || Number(range.max || 0) <= 0 || rangeOk,
  };
}"""


def write_report(
    rows: list[dict[str, Any]],
    output_dir: Path,
    *,
    html_dir: Path,
    require_result_visible: bool,
    require_stage_visual_quality: bool,
    stage_audit_max_frames: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for row in rows if row.get("creative_ok"))
    stage_visual_passed = sum(1 for row in rows if row.get("stage_visual_quality_ok"))
    report = {
        "schema_version": "creative-visual-audit-v1",
        "created_at": now_iso(),
        "html_dir": str(html_dir),
        "mode": "strict_visual_quality" if require_stage_visual_quality else ("strict_result_visible" if require_result_visible else "browser_smoke"),
        "require_result_visible": require_result_visible,
        "require_stage_visual_quality": require_stage_visual_quality,
        "stage_audit_max_frames": stage_audit_max_frames,
        "summary": {
            "total": len(rows),
            "creative_ok": passed,
            "failed": len(rows) - passed,
            "creative_ok_rate": passed / len(rows) if rows else 0.0,
            "stage_visual_quality_ok": stage_visual_passed,
            "stage_visual_quality_ok_rate": stage_visual_passed / len(rows) if rows else 0.0,
            "stage_overlap_total": sum(int(row.get("stage_overlap_count") or 0) for row in rows),
            "stage_clipped_total": sum(int(row.get("stage_clipped_count") or 0) for row in rows),
            "stage_text_occlusion_total": sum(int(row.get("stage_text_occlusion_count") or 0) for row in rows),
        },
        "results": rows,
    }
    json_path = output_dir / "creative_visual_audit.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = output_dir / "creative_visual_audit.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "creative_ok",
                "page_load_ok",
                "console_error_count",
                "page_error_count",
                "visual_non_empty",
                "frame_switch_ok",
                "trace_mutation_detected",
                "result_visible",
                "stage_visual_quality_ok",
                "stage_audited_frame_count",
                "stage_overlap_count",
                "stage_clipped_count",
                "stage_text_occlusion_count",
                "main_area_not_blank",
                "screenshot_non_empty",
                "html",
                "failure_categories",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: ("; ".join(row.get(key, [])) if key == "failure_categories" else row.get(key, ""))
                    for key in writer.fieldnames or []
                }
            )
    md_path = output_dir / "creative_visual_audit.md"
    lines = [
        "# Creative Visual Audit",
        "",
        f"- total: {len(rows)}",
        f"- creative_ok: {passed}",
        f"- stage_visual_quality_ok: {stage_visual_passed}",
        "",
        "| Case | OK | Stage Quality | Overlap | Clipped | Text Occlusion | Failures | HTML |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('case_id', '')} | {row.get('creative_ok', False)} | "
            f"{row.get('stage_visual_quality_ok', False)} | {row.get('stage_overlap_count', 0)} | "
            f"{row.get('stage_clipped_count', 0)} | {row.get('stage_text_occlusion_count', 0)} | "
            f"{'; '.join(row.get('failure_categories') or [])} | {row.get('html', '')} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-dir", type=Path, required=True)
    parser.add_argument("--html-glob", default="*_creative.html")
    parser.add_argument("--output-dir", type=Path, default=Path("output/creative_visual_audit"))
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    parser.add_argument("--wait-ms", type=int, default=300)
    parser.add_argument("--fail-on-violations", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--require-result-visible",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Strict mode: require exact/normalized verified result text to be visible. Default keeps this as a diagnostic only.",
    )
    parser.add_argument(
        "--require-stage-visual-quality",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Strict mode: fail pages with detected Creative Stage overlap, clipping, or text occlusion.",
    )
    parser.add_argument(
        "--stage-audit-max-frames",
        type=int,
        default=4,
        help="How many representative frames to audit for Creative Stage layout quality; 0 audits all frames.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    html_dir = args.html_dir.resolve()
    output_dir = args.output_dir.resolve()
    screenshot_dir = (args.screenshot_dir or (output_dir / "screenshots")).resolve()
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    paths = collect_html_paths(html_dir, args.html_glob)
    if not paths:
        raise SystemExit(f"no creative HTML files found in {html_dir}")
    from playwright.sync_api import sync_playwright

    rows: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for path in paths:
                rows.append(
                    audit_one_html(
                        browser,
                        path,
                        screenshot_dir,
                        int(args.wait_ms),
                        require_result_visible=bool(args.require_result_visible),
                        require_stage_visual_quality=bool(args.require_stage_visual_quality),
                        stage_audit_max_frames=int(args.stage_audit_max_frames),
                    )
                )
        finally:
            browser.close()
    report_path = write_report(
        rows,
        output_dir,
        html_dir=html_dir,
        require_result_visible=bool(args.require_result_visible),
        require_stage_visual_quality=bool(args.require_stage_visual_quality),
        stage_audit_max_frames=int(args.stage_audit_max_frames),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    print(json.dumps({"report": str(report_path), "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if args.fail_on_violations and report["summary"]["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
