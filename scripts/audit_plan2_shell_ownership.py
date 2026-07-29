"""Audit Plan-2 PVCR shell ownership and creative-stage fault containment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import html5lib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OWNED_DIMENSIONS = (
    "code_panel",
    "timeline",
    "explanation",
    "interaction",
    "feedback",
    "answer",
    "learning_log",
    "canonical_artifact_state",
)

CORE_SEMANTIC_DIMENSIONS = (
    "artifact_binding",
    "navigation_binding",
    "canonical_state_binding",
    "answer_binding",
)


PROJECTION_JS = r"""
({maxStates}) => {
  const creativeRuntime = window.algolabCreativeShell || null;
  const artifact = typeof ARTIFACT !== 'undefined'
    ? ARTIFACT
    : creativeRuntime && creativeRuntime.artifact
      ? creativeRuntime.artifact
      : JSON.parse((document.querySelector('#algolab-artifact') || {textContent:'{}'}).textContent || '{}');
  const runtimeSelectVariant = index => {
    if (typeof selectVariant === 'function') return selectVariant(index);
    const button = document.querySelector(`#tabs [data-variant="${index}"]`);
    if (!button) throw new Error(`variant selector unavailable: ${index}`);
    button.click();
  };
  const runtimeGo = index => {
    if (typeof go === 'function') return go(index);
    if (creativeRuntime && typeof creativeRuntime.go === 'function') return creativeRuntime.go(index);
    throw new Error('go runtime unavailable');
  };
  const runtimeFrame = () => {
    if (typeof frame === 'function') return frame();
    if (creativeRuntime && typeof creativeRuntime.frame === 'function') return creativeRuntime.frame();
    return null;
  };
  const runtimeVariantId = () => {
    if (typeof variant === 'function') return String((variant() || {}).id || '');
    const active = document.querySelector('#tabs [data-variant].active');
    const index = Number(active && active.getAttribute('data-variant'));
    return Number.isInteger(index) && artifact.variants && artifact.variants[index]
      ? String(artifact.variants[index].id || '')
      : '';
  };
  const normalize = value => String(value ?? '').replace(/\s+/g, ' ').trim();
  const sortedValue = value => {
    if (Array.isArray(value)) return value.map(sortedValue);
    if (value && typeof value === 'object') {
      const result = {};
      Object.keys(value).sort().forEach(key => { result[key] = sortedValue(value[key]); });
      return result;
    }
    return value;
  };
  const stable = value => JSON.stringify(sortedValue(value));
  const canonicalArtifact = value => {
    const copy = JSON.parse(JSON.stringify(value || {}));
    ['input','variant','scene','frames','result'].forEach(key => { delete copy[key]; });
    const variantIds = new Set((copy.variants || []).map(item => String((item || {}).id || '')));
    if (!variantIds.has('0') && copy.scenes && Object.prototype.hasOwnProperty.call(copy.scenes, '0')) {
      delete copy.scenes['0'];
    }
    return copy;
  };
  const hash = value => {
    const text = stable(value);
    let h = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return (h >>> 0).toString(16).padStart(8, '0');
  };
  const text = id => normalize((document.getElementById(id) || {}).textContent || '');
  const contains = (haystack, needle) => !normalize(needle) || normalize(haystack).includes(normalize(needle));
  const activeLine = () => {
    const node = document.querySelector('#code .line.active .lineno, #code .line.fallback .lineno');
    const value = Number(node && node.textContent);
    return Number.isFinite(value) ? value : null;
  };
  const timelineActive = () => {
    const node = document.querySelector('#timeline [data-step].active');
    const value = Number(node && node.getAttribute('data-step'));
    return Number.isFinite(value) ? value : null;
  };
  const boolAnswer = value => value === true || String(value).toLowerCase() === 'true' || String(value) === '正确';
  const feedbackSnapshot = () => {
    const node = document.getElementById('feedback');
    const content = node ? normalize(node.textContent) : '';
    return {
      correct:String((node && node.dataset.correct) || ''),
      content_hash:hash(content),
    };
  };
  const submitInteraction = (interaction, value) => {
    if (!interaction) return null;
    if (typeof checkAnswer === 'function') {
      checkAnswer(value);
    } else if (interaction.type === 'choice' && typeof checkChoice === 'function') {
      checkChoice(encodeURIComponent(String(value)));
    } else if (interaction.type === 'input' && typeof checkInput === 'function') {
      const input = document.getElementById('free-answer');
      if (input) input.value = String(value);
      checkInput();
    } else if (interaction.type === 'judge' && typeof checkJudge === 'function') {
      checkJudge(Boolean(value));
    } else {
      let control = null;
      if (interaction.type === 'choice') {
        control = Array.from(document.querySelectorAll('#interaction [data-option]')).find(
          node => String(node.getAttribute('data-option')) === String(value)
        );
      } else if (interaction.type === 'input') {
        const input = document.getElementById('free-answer');
        if (input) input.value = String(value);
        control = document.querySelector('#interaction [data-input-check]');
      } else if (interaction.type === 'judge') {
        control = document.querySelector(`#interaction [data-judge="${Boolean(value)}"]`);
      }
      if (!control) return null;
      control.click();
    }
    return feedbackSnapshot();
  };
  const feedbackProjection = interaction => {
    if (!interaction) return {applicable:false, content_hash:hash('')};
    const answer = Array.isArray(interaction.answer) ? interaction.answer[0] : interaction.answer;
    let correct = answer;
    let wrong = `${String(answer ?? '')}__plan2_wrong__`;
    if (interaction.type === 'choice') {
      const options = Array.isArray(interaction.options) ? interaction.options : [];
      wrong = options.find(option => String(option) !== String(answer)) ?? wrong;
    } else if (interaction.type === 'judge') {
      correct = boolAnswer(answer);
      wrong = !correct;
    }
    const correctResult = submitInteraction(interaction, correct);
    const wrongResult = submitInteraction(interaction, wrong);
    return {
      applicable:true,
      node_available:Boolean(document.getElementById('feedback')),
      correct_supported:Boolean(correctResult && correctResult.correct === 'true'),
      wrong_supported:Boolean(wrongResult && wrongResult.correct === 'false'),
      correct_content_hash:correctResult ? correctResult.content_hash : hash(''),
      wrong_content_hash:wrongResult ? wrongResult.content_hash : hash(''),
      content_hash:hash({correct:correctResult, wrong:wrongResult}),
    };
  };
  const rows = [];
  const variants = Array.isArray(artifact.variants) ? artifact.variants : [];
  for (let variantIndexValue = 0; variantIndexValue < variants.length; variantIndexValue += 1) {
    const item = variants[variantIndexValue] || {};
    const expectedScene = (artifact.scenes || {})[item.id] || {frames:[]};
    const expectedFrames = Array.isArray(expectedScene.frames) ? expectedScene.frames : [];
    for (let frameIndexValue = 0; frameIndexValue < expectedFrames.length; frameIndexValue += 1) {
      if (maxStates > 0 && rows.length >= maxStates) break;
      runtimeSelectVariant(variantIndexValue);
      runtimeGo(frameIndexValue);
      const currentRuntimeFrame = runtimeFrame() || {};
      const expectedFrame = expectedFrames[frameIndexValue] || {};
      const interaction = expectedFrame.interaction || null;
      const explanationText = [text('step-title'), text('step-desc'), text('teaching'), text('explanation')].join(' ');
      const interactionNode = document.querySelector('#interaction [data-interaction-type], #interaction .interaction');
      const renderedType = interactionNode
        ? String(interactionNode.getAttribute('data-interaction-type') || '')
        : '';
      const feedback = feedbackProjection(interaction);
      const learningNode = document.querySelector('#learning-log-frame, #learning-log-preview, #learning-log-summary');
      const expectedLine = Number(expectedFrame.code_line || (expectedFrame.evidence || {}).code_line || 1);
      const codeLines = String(item.code || '').split('\n');
      const answerText = text('top-result') || text('result') || text('answer');
      rows.push({
        artifact_hash:hash(canonicalArtifact(artifact)),
        variant_id:String(item.id || variantIndexValue),
        runtime_variant_id:runtimeVariantId(),
        frame_index:frameIndexValue,
        canonical_state_hash:hash(currentRuntimeFrame.state || {}),
        expected_state_hash:hash(expectedFrame.state || {}),
        runtime_matches_expected:stable(currentRuntimeFrame) === stable(expectedFrame),
        code_panel:{
          available:Boolean(document.getElementById('code')),
          content_hash:hash(text('code')),
          source_line_count:codeLines.length,
          rendered_line_count:document.querySelectorAll('#code .line').length,
          expected_active_line:expectedLine,
          rendered_active_line:activeLine(),
        },
        timeline:{
          available:Boolean(document.getElementById('timeline')),
          content_hash:hash(text('timeline')),
          expected_count:expectedFrames.length,
          rendered_count:document.querySelectorAll('#timeline [data-step]').length,
          active:timelineActive(),
        },
        explanation:{
          content_hash:hash(explanationText),
          description_visible:contains(explanationText, expectedFrame.description || ''),
          teaching_what_visible:contains(explanationText, (expectedFrame.teaching || {}).what || ''),
          teaching_why_visible:contains(explanationText, (expectedFrame.teaching || {}).why || ''),
        },
        interaction:interaction ? {
          expected:true,
          rendered:Boolean(interactionNode),
          content_hash:hash(text('interaction')),
          type:String(interaction.type || ''),
          rendered_type:renderedType,
          prompt_visible:contains(text('interaction'), interaction.prompt || ''),
        } : {
          expected:false,
          rendered:Boolean(interactionNode),
          content_hash:hash(text('interaction')),
        },
        feedback:feedback,
        answer:{
          expected_hash:hash(item.result),
          visible:Boolean(answerText),
          content_hash:hash(answerText),
        },
        learning_log:{
          available:Boolean(learningNode),
          records_current_frame:Boolean(learningNode && normalize(learningNode.textContent)),
          content_hash:hash(learningNode ? normalize(learningNode.textContent) : ''),
        },
      });
    }
  }
  return {
    runtime_kind:document.getElementById('creative-stage-host') ? 'creative' : 'verified',
    artifact_hash:hash(canonicalArtifact(artifact)),
    states:rows,
  };
}
"""


FAULT_OBSERVATION_JS = r"""
() => {
  const host = document.getElementById('creative-stage-host');
  const verifiedMarker = host && host.querySelector('.stage-grid, .scene-world, .primary-scene');
  return {
    shell_intact:['app','stage','code','timeline','interaction','state','top-result'].every(id => Boolean(document.getElementById(id))),
    stage_rendered:host ? String(host.dataset.stageRendered || '') : '',
    generic_fallback:Boolean(host && host.querySelector('.fallback-stage')),
    verified_view_fallback:Boolean(verifiedMarker && !(host && host.querySelector('.fallback-stage'))),
    stage_text:host ? String(host.innerText || '').slice(0, 500) : '',
  };
}
"""


def semantic_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_runtime_artifact(value: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value, ensure_ascii=False))
    for key in ("input", "variant", "scene", "frames", "result"):
        result.pop(key, None)
    variant_ids = {
        str(item.get("id") or "")
        for item in result.get("variants") or []
        if isinstance(item, dict)
    }
    scenes = result.get("scenes")
    if isinstance(scenes, dict) and "0" not in variant_ids:
        scenes.pop("0", None)
    return result


def build_case_pairs(
    stage1_report: dict[str, Any],
    stage2_manifest: dict[str, Any],
    *,
    expected_cases: int,
) -> list[dict[str, str]]:
    verified = _index_unique(stage1_report.get("results") or [], source="stage1 report")
    creative = _index_unique(stage2_manifest.get("items") or [], source="stage2 manifest")
    if set(verified) != set(creative) or len(verified) != expected_cases:
        raise ValueError(
            "case set mismatch: "
            f"verified={len(verified)}, creative={len(creative)}, expected={expected_cases}, "
            f"verified_only={sorted(set(verified) - set(creative))[:10]}, "
            f"creative_only={sorted(set(creative) - set(verified))[:10]}"
        )
    return [
        {
            "case_id": case_id,
            "verified_artifact": str(verified[case_id].get("json") or ""),
            "verified_html": str(verified[case_id].get("html") or ""),
            "creative_artifact": str(creative[case_id].get("artifact_repo_path") or ""),
            "creative_html": str(creative[case_id].get("html_repo_path") or ""),
        }
        for case_id in sorted(verified)
    ]


def compare_shell_projection(
    verified: dict[str, Any],
    creative: dict[str, Any],
) -> dict[str, Any]:
    dimensions = {
        "code_panel": verified.get("code_panel") == creative.get("code_panel"),
        "timeline": verified.get("timeline") == creative.get("timeline"),
        "explanation": verified.get("explanation") == creative.get("explanation"),
        "interaction": verified.get("interaction") == creative.get("interaction"),
        "feedback": verified.get("feedback") == creative.get("feedback"),
        "answer": verified.get("answer") == creative.get("answer"),
        "learning_log": verified.get("learning_log") == creative.get("learning_log"),
        "canonical_artifact_state": all(
            verified.get(key) == creative.get(key)
            for key in (
                "artifact_hash",
                "variant_id",
                "runtime_variant_id",
                "frame_index",
                "canonical_state_hash",
            )
        )
        and verified.get("runtime_variant_id") == verified.get("variant_id")
        and creative.get("runtime_variant_id") == creative.get("variant_id")
        and verified.get("runtime_matches_expected") is True
        and creative.get("runtime_matches_expected") is True,
    }
    return {
        "dimensions": dimensions,
        "all_dimensions_match": all(dimensions.values()),
    }


def compare_core_semantic_projection(
    verified: dict[str, Any],
    creative: dict[str, Any],
) -> dict[str, bool]:
    artifact_binding = verified.get("artifact_hash") == creative.get("artifact_hash")
    navigation_binding = (
        verified.get("variant_id") == creative.get("variant_id")
        and verified.get("runtime_variant_id") == verified.get("variant_id")
        and creative.get("runtime_variant_id") == creative.get("variant_id")
        and verified.get("frame_index") == creative.get("frame_index")
    )
    canonical_state_binding = (
        verified.get("canonical_state_hash") == creative.get("canonical_state_hash")
        and verified.get("expected_state_hash") == creative.get("expected_state_hash")
        and verified.get("runtime_matches_expected") is True
        and creative.get("runtime_matches_expected") is True
    )
    answer_binding = (verified.get("answer") or {}).get("expected_hash") == (
        creative.get("answer") or {}
    ).get("expected_hash")
    dimensions = {
        "artifact_binding": artifact_binding,
        "navigation_binding": navigation_binding,
        "canonical_state_binding": canonical_state_binding,
        "answer_binding": answer_binding,
    }
    return {
        **dimensions,
        "all_core_semantics_match": all(dimensions.values()),
    }


def classify_fault_outcome(
    sanitizer_errors: list[str],
    browser_observation: dict[str, Any],
) -> str:
    if sanitizer_errors:
        return "rejected"
    if browser_observation.get("verified_view_fallback") and not browser_observation.get(
        "external_requests"
    ):
        return "verified_fallback"
    if (
        browser_observation.get("generic_fallback")
        and browser_observation.get("shell_intact")
        and not browser_observation.get("external_requests")
    ):
        return "generic_fallback"
    if browser_observation.get("external_requests"):
        return "external_request_attempted"
    if browser_observation.get("shell_intact") is False:
        return "shell_corruption"
    return "accepted_stage_asset"


def summarize_fault_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row.get("disposition") or "unknown") for row in rows)
    rendered = [row for row in rows if row.get("browser_observation")]
    shell_corruption = sum(
        (row.get("browser_observation") or {}).get("shell_intact") is False
        for row in rendered
    )
    external_request_attempted = sum(
        bool((row.get("browser_observation") or {}).get("external_requests"))
        for row in rendered
    )
    strict_dispositions = {"rejected", "verified_fallback"}
    return {
        "attempt_count": len(rows),
        "disposition_counts": dict(sorted(counts.items())),
        "sanitizer_rejected": counts["rejected"],
        "verified_fallback": counts["verified_fallback"],
        "generic_fallback": counts["generic_fallback"],
        "accepted_stage_asset": counts["accepted_stage_asset"],
        "external_request_attempted": external_request_attempted,
        "shell_corruption": shell_corruption,
        "rendered_attempt_count": len(rendered),
        "all_rendered_shells_intact": bool(rendered) and shell_corruption == 0,
        "all_faults_rejected_or_verified_fallback": bool(rows)
        and all(str(row.get("disposition") or "") in strict_dispositions for row in rows),
        "criterion": (
            "Report sanitizer rejection, Verified fallback, generic fallback, accepted stage "
            "assets, external request attempts, and shell corruption separately."
        ),
    }


def build_fault_payloads() -> dict[str, str]:
    return {
        "page_level_html": """<!doctype html><html><body><div>page</div><script>function renderCreativeStage(){return '<div>page-level</div>'}</script></body></html>""",
        "reserved_shell_id": """<template id="creative-stage-template"><div id="timeline"></div></template><script>function renderCreativeStage(){return '<div>reserved</div>'}</script>""",
        "external_url": """<template id="creative-stage-template"><img src="https://example.invalid/escape.png"></template><script>function renderCreativeStage(){fetch('https://example.invalid/escape.json');return '<div>external</div>'}</script>""",
        "renderer_exception": """<template id="creative-stage-template"><div>throws</div></template><script>function renderCreativeStage(){throw new Error('fault injection')}</script>""",
        "invalid_template_script_structure": """<template id="creative-stage-template"><div>first</div></template><template id="creative-stage-template"><div>second</div></template><script>function renderCreativeStage(){return '<div>first script</div>'}</script><script>function renderCreativeStage(){return '<div>second script</div>'}</script>""",
    }


def shell_structure_signature(html: str) -> str:
    document = html5lib.parse(
        html or "",
        treebuilder="etree",
        namespaceHTMLElements=False,
    )
    tokens: list[tuple[Any, ...]] = []

    def visit(element: Any) -> None:
        tag = element.tag
        if not isinstance(tag, str):
            return
        attrs_map = {
            str(name).lower(): str(value or "")
            for name, value in element.attrib.items()
        }
        if attrs_map.get("id") == "creative-stage-host":
            return
        classes = tuple(sorted(filter(None, attrs_map.get("class", "").split())))
        tokens.append(("start", tag.lower(), attrs_map.get("id", ""), classes))
        for child in list(element):
            visit(child)
        tokens.append(("end", tag.lower()))

    visit(document)
    return semantic_sha256(tokens)


def _index_unique(rows: list[dict[str, Any]], *, source: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise ValueError(f"{source} contains a row without case_id")
        if case_id in result:
            raise ValueError(f"{source} contains duplicate case_id: {case_id}")
        result[case_id] = row
    return result


def run_audit(
    *,
    stage1_report_path: Path,
    stage2_manifest_path: Path,
    output_dir: Path,
    expected_cases: int,
    browser_enabled: bool,
    fault_count: int,
    seed: int,
    max_cases: int = 0,
) -> dict[str, Any]:
    stage1_report_path = _repo_path(stage1_report_path)
    stage2_manifest_path = _repo_path(stage2_manifest_path)
    output_dir = _repo_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stage1_report = json.loads(stage1_report_path.read_text(encoding="utf-8"))
    stage2_manifest = json.loads(stage2_manifest_path.read_text(encoding="utf-8"))
    pairs = build_case_pairs(stage1_report, stage2_manifest, expected_cases=expected_cases)
    metadata = {
        str(row.get("case_id") or ""): {
            "family_id": str(row.get("family_id") or "unknown"),
            "subfamily_id": str(row.get("subfamily_id") or ""),
        }
        for row in stage1_report.get("results") or []
    }
    if max_cases > 0:
        pairs = pairs[:max_cases]

    case_results: list[dict[str, Any]] = []
    for pair in pairs:
        verified_artifact_path = _repo_path(Path(pair["verified_artifact"]))
        creative_artifact_path = _repo_path(Path(pair["creative_artifact"]))
        verified_html_path = _repo_path(Path(pair["verified_html"]))
        creative_html_path = _repo_path(Path(pair["creative_html"]))
        required = [
            verified_artifact_path,
            creative_artifact_path,
            verified_html_path,
            creative_html_path,
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"{pair['case_id']}: missing inputs: {missing}")
        verified_bytes = verified_artifact_path.read_bytes()
        creative_bytes = creative_artifact_path.read_bytes()
        verified_artifact = json.loads(verified_bytes)
        creative_artifact = json.loads(creative_bytes)
        verified_html = verified_html_path.read_text(encoding="utf-8")
        creative_html = creative_html_path.read_text(encoding="utf-8")
        verified_signature = shell_structure_signature(verified_html)
        creative_signature = shell_structure_signature(creative_html)
        case_results.append(
            {
                **pair,
                **metadata.get(pair["case_id"], {}),
                "verified_artifact_sha256": hashlib.sha256(verified_bytes).hexdigest(),
                "creative_artifact_sha256": hashlib.sha256(creative_bytes).hexdigest(),
                "artifact_byte_identical": verified_bytes == creative_bytes,
                "artifact_semantic_identical": semantic_sha256(verified_artifact)
                == semantic_sha256(creative_artifact),
                "variant_count": len(verified_artifact.get("variants") or []),
                "frame_count": sum(
                    len((scene or {}).get("frames") or [])
                    for scene in (verified_artifact.get("scenes") or {}).values()
                    if isinstance(scene, dict)
                ),
                "verified_shell_structure_sha256": verified_signature,
                "creative_shell_structure_sha256": creative_signature,
                "shell_structure_identical_outside_creative_host": verified_signature
                == creative_signature,
            }
        )

    runtime_summary: dict[str, Any] = {
        "status": "not_run",
        "case_count": 0,
        "expected_state_count": sum(int(row["frame_count"]) for row in case_results),
        "state_count": 0,
        "all_expected_states_audited": False,
        "all_dimensions_match_states": 0,
        "all_dimensions_match_cases": 0,
        "all_core_semantics_match_states": 0,
        "all_core_semantics_match_cases": 0,
        "dimension_matches": {dimension: 0 for dimension in OWNED_DIMENSIONS},
        "dimension_totals": {dimension: 0 for dimension in OWNED_DIMENSIONS},
        "core_semantic_dimension_matches": {
            dimension: 0 for dimension in CORE_SEMANTIC_DIMENSIONS
        },
        "core_semantic_dimension_totals": {
            dimension: 0 for dimension in CORE_SEMANTIC_DIMENSIONS
        },
        "runtime_expected_state_failures": {"verified": 0, "creative": 0},
    }
    fault_results: list[dict[str, Any]] = []
    if browser_enabled:
        runtime_summary, fault_results = _run_browser_audit(
            case_results=case_results,
            output_dir=output_dir,
            fault_count=fault_count,
            seed=seed,
        )

    fault_summary = summarize_fault_results(fault_results)
    summary = {
        "kind": "plan2_pvcr_shell_ownership_audit",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "status": "complete" if browser_enabled else "static_complete_browser_pending",
        "inputs": {
            "stage1_report": str(stage1_report_path),
            "stage1_report_sha256": _file_sha256(stage1_report_path),
            "stage2_manifest": str(stage2_manifest_path),
            "stage2_manifest_sha256": _file_sha256(stage2_manifest_path),
        },
        "config": {
            "expected_cases": expected_cases,
            "audited_cases": len(case_results),
            "browser_enabled": browser_enabled,
            "fault_artifact_count": min(fault_count, len(case_results)),
            "fault_types": sorted(build_fault_payloads()),
            "seed": seed,
        },
        "artifact_pairing": {
            "case_count": len(case_results),
            "byte_identical": sum(bool(row["artifact_byte_identical"]) for row in case_results),
            "semantic_identical": sum(bool(row["artifact_semantic_identical"]) for row in case_results),
            "variant_count": sum(int(row["variant_count"]) for row in case_results),
            "frame_count": sum(int(row["frame_count"]) for row in case_results),
        },
        "static_shell_projection": {
            "comparison_rule": (
                "Compare the ordered DOM tag/id/class skeleton after excluding only the "
                "creative-stage-host subtree; no other generated container is removed."
            ),
            "identical_cases": sum(
                bool(row["shell_structure_identical_outside_creative_host"])
                for row in case_results
            ),
            "case_count": len(case_results),
        },
        "runtime_shell_projection": runtime_summary,
        "core_semantic_ownership_gate": {
            "all_states_match": bool(
                runtime_summary.get("all_expected_states_audited") is True
                and runtime_summary.get("all_core_semantics_match_states")
                == runtime_summary.get("expected_state_count")
            ),
            "all_cases_match": bool(
                len(case_results) == expected_cases
                and runtime_summary.get("all_core_semantics_match_cases") == expected_cases
            ),
        },
        "fault_injection": fault_summary,
        "ideal_ownership_gate": {
            "shell_projection_200_of_200": bool(
                len(case_results) == expected_cases
                and all(row["shell_structure_identical_outside_creative_host"] for row in case_results)
                and runtime_summary.get("all_expected_states_audited") is True
                and runtime_summary.get("all_dimensions_match_cases") == expected_cases
            ),
            "all_faults_rejected_or_verified_fallback": fault_summary[
                "all_faults_rejected_or_verified_fallback"
            ],
        },
        "claim_boundary": (
            "This audit tests ownership and fault containment. A failure is reported as a failure; "
            "generic Creative Stage fallback is not relabeled as Verified View fallback, and the result "
            "does not claim that PVCR is a security sandbox."
        ),
        "cases": case_results,
        "fault_results": fault_results,
    }
    output_path = output_dir / "shell_ownership_audit.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _run_browser_audit(
    *,
    case_results: list[dict[str, Any]],
    output_dir: Path,
    fault_count: int,
    seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from playwright.sync_api import sync_playwright

    dimension_matches: Counter[str] = Counter()
    dimension_totals: Counter[str] = Counter()
    core_dimension_matches: Counter[str] = Counter()
    core_dimension_totals: Counter[str] = Counter()
    state_count = 0
    all_dimensions_match_states = 0
    all_dimensions_match_cases = 0
    all_core_semantics_match_states = 0
    all_core_semantics_match_cases = 0
    expected_state_failures = Counter()
    expected_state_count = sum(int(row.get("frame_count") or 0) for row in case_results)
    browser_errors: list[dict[str, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=_chromium_executable(),
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            for index, row in enumerate(case_results):
                print(f"SHELL {index + 1}/{len(case_results)} {row['case_id']}", flush=True)
                try:
                    verified = _collect_projection(page, _repo_path(Path(row["verified_html"])))
                    creative = _collect_projection(page, _repo_path(Path(row["creative_html"])))
                    comparisons = _compare_projection_sets(verified, creative)
                    row["runtime_projection"] = comparisons
                    case_all = bool(comparisons["states"]) and all(
                        item["all_dimensions_match"] for item in comparisons["states"]
                    )
                    if case_all:
                        all_dimensions_match_cases += 1
                    case_core_all = bool(comparisons["states"]) and all(
                        item["core_semantics"]["all_core_semantics_match"]
                        for item in comparisons["states"]
                    )
                    if case_core_all:
                        all_core_semantics_match_cases += 1
                    for item in comparisons["states"]:
                        state_count += 1
                        if item["all_dimensions_match"]:
                            all_dimensions_match_states += 1
                        if item["core_semantics"]["all_core_semantics_match"]:
                            all_core_semantics_match_states += 1
                        for dimension, matched in item["dimensions"].items():
                            dimension_totals[dimension] += 1
                            dimension_matches[dimension] += int(matched)
                        for dimension in CORE_SEMANTIC_DIMENSIONS:
                            matched = item["core_semantics"][dimension]
                            core_dimension_totals[dimension] += 1
                            core_dimension_matches[dimension] += int(matched)
                    expected_state_failures["verified"] += sum(
                        not state.get("runtime_matches_expected")
                        for state in verified.get("states") or []
                    )
                    expected_state_failures["creative"] += sum(
                        not state.get("runtime_matches_expected")
                        for state in creative.get("states") or []
                    )
                except Exception as exc:
                    row["runtime_projection"] = {
                        "ok": False,
                        "error": f"{type(exc).__name__}: {exc}",
                        "states": [],
                    }
                    browser_errors.append(
                        {"case_id": str(row["case_id"]), "error": f"{type(exc).__name__}: {exc}"}
                    )
            fault_results = _run_fault_injections(
                page=page,
                case_results=case_results,
                output_dir=output_dir,
                fault_count=fault_count,
                seed=seed,
            )
        finally:
            browser.close()
    return (
        {
            "status": "complete" if not browser_errors else "complete_with_browser_errors",
            "case_count": len(case_results),
            "browser_error_count": len(browser_errors),
            "browser_errors": browser_errors,
            "expected_state_count": expected_state_count,
            "state_count": state_count,
            "all_expected_states_audited": state_count == expected_state_count,
            "all_dimensions_match_states": all_dimensions_match_states,
            "all_dimensions_match_cases": all_dimensions_match_cases,
            "all_core_semantics_match_states": all_core_semantics_match_states,
            "all_core_semantics_match_cases": all_core_semantics_match_cases,
            "dimension_matches": {
                dimension: dimension_matches[dimension] for dimension in OWNED_DIMENSIONS
            },
            "dimension_totals": {
                dimension: dimension_totals[dimension] for dimension in OWNED_DIMENSIONS
            },
            "dimension_totals_match_state_count": all(
                dimension_totals[dimension] == state_count
                for dimension in OWNED_DIMENSIONS
            ),
            "core_semantic_dimension_matches": {
                dimension: core_dimension_matches[dimension]
                for dimension in CORE_SEMANTIC_DIMENSIONS
            },
            "core_semantic_dimension_totals": {
                dimension: core_dimension_totals[dimension]
                for dimension in CORE_SEMANTIC_DIMENSIONS
            },
            "runtime_expected_state_failures": {
                "verified": expected_state_failures["verified"],
                "creative": expected_state_failures["creative"],
            },
        },
        fault_results,
    )


def _collect_projection(page: Any, path: Path) -> dict[str, Any]:
    external_requests: list[str] = []

    def route_request(route: Any) -> None:
        url = str(route.request.url)
        if url.startswith(("file:", "data:", "blob:")):
            route.continue_()
        else:
            external_requests.append(url)
            route.abort()

    page.unroute("**/*")
    page.route("**/*", route_request)
    page.goto(path.as_uri(), wait_until="load", timeout=120_000)
    page.wait_for_function(
        """(
          typeof selectVariant === 'function' && typeof go === 'function' && typeof frame === 'function'
        ) || (
          window.algolabCreativeShell &&
          typeof window.algolabCreativeShell.go === 'function' &&
          typeof window.algolabCreativeShell.frame === 'function'
        )""",
        timeout=30_000,
    )
    result = page.evaluate(PROJECTION_JS, {"maxStates": 0})
    result["external_requests"] = sorted(set(external_requests))
    result["html"] = str(path)
    return result


def _compare_projection_sets(
    verified: dict[str, Any],
    creative: dict[str, Any],
) -> dict[str, Any]:
    verified_states = {
        (str(row.get("variant_id") or ""), int(row.get("frame_index") or 0)): row
        for row in verified.get("states") or []
    }
    creative_states = {
        (str(row.get("variant_id") or ""), int(row.get("frame_index") or 0)): row
        for row in creative.get("states") or []
    }
    keys = sorted(set(verified_states) | set(creative_states))
    rows = []
    for variant_id, frame_index in keys:
        left = verified_states.get((variant_id, frame_index))
        right = creative_states.get((variant_id, frame_index))
        if left is None or right is None:
            core_semantics = {
                dimension: False for dimension in CORE_SEMANTIC_DIMENSIONS
            }
            core_semantics["all_core_semantics_match"] = False
            rows.append(
                {
                    "variant_id": variant_id,
                    "frame_index": frame_index,
                    "dimensions": {dimension: False for dimension in OWNED_DIMENSIONS},
                    "all_dimensions_match": False,
                    "core_semantics": core_semantics,
                    "missing_view": "verified" if left is None else "creative",
                }
            )
            continue
        comparison = compare_shell_projection(left, right)
        core_semantics = compare_core_semantic_projection(left, right)
        rows.append(
            {
                "variant_id": variant_id,
                "frame_index": frame_index,
                **comparison,
                "core_semantics": core_semantics,
                "verified_runtime_matches_expected": bool(left.get("runtime_matches_expected")),
                "creative_runtime_matches_expected": bool(right.get("runtime_matches_expected")),
                "verified": left,
                "creative": right,
            }
        )
    return {
        "ok": bool(rows),
        "verified_state_count": len(verified_states),
        "creative_state_count": len(creative_states),
        "state_key_sets_identical": set(verified_states) == set(creative_states),
        "states": rows,
    }


def _run_fault_injections(
    *,
    page: Any,
    case_results: list[dict[str, Any]],
    output_dir: Path,
    fault_count: int,
    seed: int,
) -> list[dict[str, Any]]:
    from algolab.renderer.creative_direct import (
        CreativeDirectHtmlError,
        render_direct_visual_stage_shell_html,
        sanitize_direct_visual_stage_assets,
    )
    from algolab.schemas.validation import BuildArtifact

    candidates = list(case_results)
    random.Random(seed).shuffle(candidates)
    selected = sorted(candidates[: min(fault_count, len(candidates))], key=lambda row: row["case_id"])
    pages_dir = output_dir / "fault_pages"
    pages_dir.mkdir(exist_ok=True)
    payloads = build_fault_payloads()
    results: list[dict[str, Any]] = []
    for case_index, row in enumerate(selected):
        artifact_path = _repo_path(Path(row["verified_artifact"]))
        artifact = BuildArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
        for fault_name, payload in payloads.items():
            print(
                f"FAULT {case_index + 1}/{len(selected)} {row['case_id']} {fault_name}",
                flush=True,
            )
            sanitizer_errors = sanitize_direct_visual_stage_assets(payload)
            observation: dict[str, Any] = {}
            rendered_path = pages_dir / f"{row['case_id']}__{fault_name}.html"
            if not sanitizer_errors:
                try:
                    rendered = render_direct_visual_stage_shell_html(artifact, payload)
                    rendered_path.write_text(rendered, encoding="utf-8")
                    observation = _observe_fault_page(page, rendered_path)
                except CreativeDirectHtmlError as exc:
                    sanitizer_errors = [str(exc)]
                except Exception as exc:
                    observation = {"browser_error": f"{type(exc).__name__}: {exc}"}
            disposition = classify_fault_outcome(sanitizer_errors, observation)
            results.append(
                {
                    "case_id": row["case_id"],
                    "family_id": row.get("family_id", "unknown"),
                    "fault": fault_name,
                    "sanitizer_errors": sanitizer_errors,
                    "rendered_page": str(rendered_path) if rendered_path.is_file() else "",
                    "browser_observation": observation,
                    "disposition": disposition,
                    "contained": disposition in {"rejected", "verified_fallback"},
                }
            )
    return results


def _observe_fault_page(page: Any, path: Path) -> dict[str, Any]:
    external_requests: list[str] = []

    def route_request(route: Any) -> None:
        url = str(route.request.url)
        if url.startswith(("file:", "data:", "blob:")):
            route.continue_()
        else:
            external_requests.append(url)
            route.abort()

    page.unroute("**/*")
    page.route("**/*", route_request)
    page.goto(path.as_uri(), wait_until="load", timeout=60_000)
    page.wait_for_timeout(100)
    observation = page.evaluate(FAULT_OBSERVATION_JS)
    observation["external_requests"] = sorted(set(external_requests))
    return observation


def _repo_path(path: Path) -> Path:
    if not path.is_absolute():
        return ROOT / path
    if path.exists():
        return path
    host_root = os.environ.get("ALGOLAB_HOST_PROJECT_ROOT", "").strip()
    if host_root:
        try:
            return ROOT / path.relative_to(Path(host_root))
        except ValueError:
            pass
    try:
        return ROOT / path.relative_to("/work")
    except ValueError:
        return path


def _chromium_executable() -> str | None:
    configured = os.environ.get("ALGOLAB_CHROMIUM_EXECUTABLE", "").strip()
    if configured and Path(configured).is_file():
        return configured
    candidates = [
        Path("/ms-playwright/chromium-1223/chrome-linux64/chrome"),
        Path("/ms-playwright/chromium-*/chrome-linux64/chrome"),
    ]
    if candidates[0].is_file():
        return str(candidates[0])
    matches = sorted(Path("/ms-playwright").glob("chromium-*/chrome-linux64/chrome"))
    return str(matches[-1]) if matches else None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage1-report",
        type=Path,
        default=ROOT
        / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json",
    )
    parser.add_argument(
        "--stage2-manifest",
        type=Path,
        default=ROOT
        / "output/experiments/algotutorgen_full_200_20260706/"
        "stage2_creative_visual_deepseek_v4pro_full200_parallel8_container_20260707/"
        "selected_html_manifest_final.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output/experiments/plan2_20260722/p0_3_shell_ownership",
    )
    parser.add_argument("--expected-cases", type=int, default=200)
    parser.add_argument("--fault-count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    summary = run_audit(
        stage1_report_path=args.stage1_report,
        stage2_manifest_path=args.stage2_manifest,
        output_dir=args.output_dir,
        expected_cases=args.expected_cases,
        browser_enabled=not args.no_browser,
        fault_count=args.fault_count,
        seed=args.seed,
        max_cases=args.max_cases,
    )
    print(
        json.dumps(
            {
                "output": str(_repo_path(args.output_dir) / "shell_ownership_audit.json"),
                "artifact_pairing": summary["artifact_pairing"],
                "static_shell_projection": summary["static_shell_projection"],
                "runtime_shell_projection": summary["runtime_shell_projection"],
                "fault_injection": summary["fault_injection"],
                "ideal_ownership_gate": summary["ideal_ownership_gate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
