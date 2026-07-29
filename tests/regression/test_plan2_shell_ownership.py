import json
import re
import subprocess
from pathlib import Path

import pytest

from algolab.renderer.creative_direct import render_direct_visual_stage_shell_html
from algolab.schemas.validation import BuildArtifact
from scripts.audit_plan2_shell_ownership import (
    PROJECTION_JS,
    _compare_projection_sets,
    build_case_pairs,
    build_fault_payloads,
    canonical_runtime_artifact,
    classify_fault_outcome,
    compare_core_semantic_projection,
    compare_shell_projection,
    semantic_sha256,
    shell_structure_signature,
    summarize_fault_results,
)


ROOT = Path(__file__).resolve().parents[2]


def _two_variant_artifact() -> BuildArtifact:
    def variant(variant_id: str, result: str) -> dict:
        return {
            "id": variant_id,
            "name": f"variant-{variant_id}",
            "strategy": f"strategy-{variant_id}",
            "code": "def solve(input_data):\n    return input_data",
            "tracker_code": "def trace(input_data):\n    return {}",
            "result": result,
        }

    def scene(variant_id: str, frame_count: int) -> dict:
        return {
            "algorithm": f"algorithm-{variant_id}",
            "input_data": {"variant": variant_id},
            "result": variant_id,
            "frames": [
                {
                    "step": index,
                    "title": f"{variant_id}-{index}",
                    "description": f"frame {variant_id}-{index}",
                    "operation": "set",
                    "code_line": index + 1,
                    "state": {"marker": f"{variant_id}-{index}"},
                }
                for index in range(frame_count)
            ],
        }

    return BuildArtifact.model_validate(
        {
            "problem_title": "two variants",
            "input_data": {"value": 1},
            "expected_result": "B",
            "verifier_result": "B",
            "variants": [variant("A", "A"), variant("B", "B")],
            "scenes": {"A": scene("A", 2), "B": scene("B", 3)},
            "validation": {},
        }
    )


def test_plan2_shell_ownership_script_exists() -> None:
    assert (ROOT / "scripts" / "audit_plan2_shell_ownership.py").is_file()


def test_creative_shell_runtime_uses_current_variant_scene_and_frames() -> None:
    html = render_direct_visual_stage_shell_html(
        _two_variant_artifact(),
        """
        <template id="creative-stage-template"><div></div></template>
        <script>function renderCreativeStage(ctx) { return String(ctx.frameIndex); }</script>
        """,
    )
    payload_match = re.search(
        r'id="algolab-artifact"[^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    helpers_match = re.search(
        r"(const variants = .*?const frame = .*?;\n)\s*const verifiedResult",
        html,
        flags=re.DOTALL,
    )
    assert payload_match is not None
    assert helpers_match is not None
    payload = json.loads(payload_match.group(1))
    script = f"""
    const ARTIFACT = {json.dumps(payload)};
    let variantIndex = 1;
    let stepIndex = 2;
    {helpers_match.group(1)}
    process.stdout.write(JSON.stringify({{
      scene: scene().algorithm,
      frameCount: frames().length,
      marker: frame().state.marker
    }}));
    """

    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "scene": "algorithm-B",
        "frameCount": 3,
        "marker": "B-2",
    }


def test_semantic_sha256_ignores_mapping_key_order() -> None:
    assert semantic_sha256({"b": 2, "a": [1, 3]}) == semantic_sha256(
        {"a": [1, 3], "b": 2}
    )


def test_build_case_pairs_requires_the_same_complete_case_set() -> None:
    stage1 = {
        "results": [
            {"case_id": "b", "json": "verified/b.json", "html": "verified/b.html"},
            {"case_id": "a", "json": "verified/a.json", "html": "verified/a.html"},
        ]
    }
    stage2 = {
        "items": [
            {
                "case_id": "a",
                "artifact_repo_path": "creative/a.json",
                "html_repo_path": "creative/a.html",
            },
            {
                "case_id": "b",
                "artifact_repo_path": "creative/b.json",
                "html_repo_path": "creative/b.html",
            },
        ]
    }

    pairs = build_case_pairs(stage1, stage2, expected_cases=2)

    assert [row["case_id"] for row in pairs] == ["a", "b"]
    assert pairs[0]["verified_artifact"] == "verified/a.json"
    assert pairs[0]["creative_html"] == "creative/a.html"

    with pytest.raises(ValueError, match="case set mismatch"):
        build_case_pairs(stage1, {"items": stage2["items"][:1]}, expected_cases=2)


def test_shell_projection_reports_each_owned_dimension_separately() -> None:
    verified = {
        "artifact_hash": "same",
        "variant_id": "v2",
        "frame_index": 3,
        "code_panel": {"source": "x", "active_line": 4},
        "timeline": {"count": 8, "active": 3},
        "explanation": {"description": "step", "teaching": {"what": "why"}},
        "interaction": {"type": "input", "prompt": "p"},
        "feedback": {"correct": True, "wrong": True},
        "answer": 7,
        "learning_log": {"available": True, "records_current_frame": True},
        "canonical_state_hash": "state",
        "runtime_variant_id": "v2",
        "runtime_matches_expected": True,
    }
    creative = dict(verified)
    creative["learning_log"] = {"available": False, "records_current_frame": False}

    result = compare_shell_projection(verified, creative)

    assert result["dimensions"]["canonical_artifact_state"] is True
    assert result["dimensions"]["code_panel"] is True
    assert result["dimensions"]["learning_log"] is False
    assert result["all_dimensions_match"] is False

    stale_creative = dict(verified)
    stale_creative["runtime_matches_expected"] = False
    stale_result = compare_shell_projection(verified, stale_creative)
    assert stale_result["dimensions"]["canonical_artifact_state"] is False


def test_fault_outcomes_distinguish_rejection_verified_fallback_and_escape() -> None:
    assert classify_fault_outcome(["reserved_shell_id"], {}) == "rejected"
    assert (
        classify_fault_outcome(
            [],
            {"verified_view_fallback": True, "external_requests": []},
        )
        == "verified_fallback"
    )
    assert (
        classify_fault_outcome(
            [],
            {
                "verified_view_fallback": False,
                "generic_fallback": True,
                "shell_intact": True,
                "external_requests": [],
            },
        )
        == "generic_fallback"
    )
    assert (
        classify_fault_outcome(
            [],
            {
                "verified_view_fallback": False,
                "generic_fallback": False,
                "shell_intact": True,
                "external_requests": ["https://example.invalid/request"],
            },
        )
        == "external_request_attempted"
    )


def test_fault_payloads_cover_all_five_plan2_injections() -> None:
    payloads = build_fault_payloads()

    assert set(payloads) == {
        "page_level_html",
        "reserved_shell_id",
        "external_url",
        "renderer_exception",
        "invalid_template_script_structure",
    }
    assert all("renderCreativeStage" in payload for payload in payloads.values())


def test_fault_summary_reports_actual_runtime_dispositions() -> None:
    summary = summarize_fault_results(
        [
            {
                "disposition": "rejected",
                "browser_observation": {},
            },
            {
                "disposition": "generic_fallback",
                "browser_observation": {
                    "shell_intact": True,
                    "external_requests": [],
                },
            },
            {
                "disposition": "external_request_attempted",
                "browser_observation": {
                    "shell_intact": True,
                    "external_requests": ["https://example.invalid/request"],
                },
            },
        ]
    )

    assert summary["attempt_count"] == 3
    assert summary["sanitizer_rejected"] == 1
    assert summary["generic_fallback"] == 1
    assert summary["external_request_attempted"] == 1
    assert summary["shell_corruption"] == 0
    assert summary["all_faults_rejected_or_verified_fallback"] is False


def test_shell_structure_signature_ignores_only_creative_host_descendants() -> None:
    left = """
    <main id="app"><section id="stage"><div id="creative-stage-host"><svg><circle/></svg></div></section><pre id="code"></pre></main>
    """
    right = """
    <main id="app"><section id="stage"><div id="creative-stage-host"><canvas></canvas></div></section><pre id="code"></pre></main>
    """
    changed_shell = right.replace('id="code"', 'id="different-code"')

    assert shell_structure_signature(left) == shell_structure_signature(right)
    assert shell_structure_signature(left) != shell_structure_signature(changed_shell)


def test_shell_structure_signature_does_not_hide_generated_asset_containers() -> None:
    base = """
    <main id="app"><div id="creative-stage-host"><svg></svg></div><pre id="code"></pre></main>
    """
    with_generated_assets = base.replace(
        "</main>",
        '<script id="algolab-artifact" type="application/json"></script>'
        '<style id="creative-stage-style"></style>'
        '<template id="creative-stage-template"></template>'
        '<script id="creative-stage-user-script"></script>'
        "</main>",
    )

    assert shell_structure_signature(base) != shell_structure_signature(with_generated_assets)


def test_shell_structure_signature_recovers_after_void_tag_inside_creative_host() -> None:
    left = (
        '<main id="app"><div id="creative-stage-host"><img src="left.png"></div>'
        '<pre id="code"></pre></main>'
    )
    right = (
        '<main id="app"><div id="creative-stage-host"><img src="right.png"></div>'
        '<pre id="code"></pre></main>'
    )
    changed_shell = right.replace('id="code"', 'id="different-code"')

    assert shell_structure_signature(left) == shell_structure_signature(right)
    assert shell_structure_signature(left) != shell_structure_signature(changed_shell)


def test_projection_runtime_adapter_supports_iife_creative_shell() -> None:
    assert "window.algolabCreativeShell" in PROJECTION_JS
    assert "runtimeSelectVariant" in PROJECTION_JS
    assert "[data-variant=" in PROJECTION_JS


def test_projection_runtime_visits_every_frame_and_hashes_owned_content() -> None:
    assert "selectedIndices" not in PROJECTION_JS
    assert (
        "for (let frameIndexValue = 0; frameIndexValue < expectedFrames.length; "
        "frameIndexValue += 1)"
    ) in PROJECTION_JS
    for dimension in (
        "code_panel",
        "timeline",
        "explanation",
        "interaction",
        "feedback",
        "answer",
        "learning_log",
    ):
        assert f"{dimension}:" in PROJECTION_JS
    assert PROJECTION_JS.count("content_hash:") >= 7


def test_shell_projection_detects_text_change_when_boolean_checks_still_pass() -> None:
    verified = {
        "artifact_hash": "same",
        "variant_id": "v1",
        "runtime_variant_id": "v1",
        "frame_index": 0,
        "canonical_state_hash": "state",
        "runtime_matches_expected": True,
        "code_panel": {"available": True, "content_hash": "left"},
        "timeline": {"available": True, "content_hash": "same"},
        "explanation": {"description_visible": True, "content_hash": "same"},
        "interaction": {"expected": False, "rendered": False, "content_hash": "same"},
        "feedback": {"applicable": False, "content_hash": "same"},
        "answer": {"visible": True, "content_hash": "same"},
        "learning_log": {"available": True, "content_hash": "same"},
    }
    creative = {
        **verified,
        "code_panel": {"available": True, "content_hash": "right"},
    }

    result = compare_shell_projection(verified, creative)

    assert result["dimensions"]["code_panel"] is False
    assert result["all_dimensions_match"] is False


def test_core_semantic_projection_ignores_shell_text_but_rejects_stale_state() -> None:
    verified = {
        "artifact_hash": "artifact",
        "variant_id": "v2",
        "runtime_variant_id": "v2",
        "frame_index": 4,
        "canonical_state_hash": "state-v2-4",
        "expected_state_hash": "state-v2-4",
        "runtime_matches_expected": True,
        "code_panel": {"content_hash": "verified wording"},
        "answer": {"expected_hash": "answer"},
    }
    creative = {
        **verified,
        "code_panel": {"content_hash": "creative wording"},
    }

    result = compare_core_semantic_projection(verified, creative)

    assert result["artifact_binding"] is True
    assert result["navigation_binding"] is True
    assert result["canonical_state_binding"] is True
    assert result["answer_binding"] is True
    assert result["all_core_semantics_match"] is True

    stale = {**creative, "canonical_state_hash": "state-v1-4"}
    assert compare_core_semantic_projection(verified, stale)[
        "all_core_semantics_match"
    ] is False


def test_projection_set_rows_include_core_semantic_result() -> None:
    state = {
        "artifact_hash": "artifact",
        "variant_id": "v1",
        "runtime_variant_id": "v1",
        "frame_index": 0,
        "canonical_state_hash": "state",
        "expected_state_hash": "state",
        "runtime_matches_expected": True,
        "code_panel": {},
        "timeline": {},
        "explanation": {},
        "interaction": {},
        "feedback": {},
        "answer": {"expected_hash": "answer"},
        "learning_log": {},
    }

    result = _compare_projection_sets(
        {"states": [state]},
        {"states": [{**state, "code_panel": {"content_hash": "different"}}]},
    )

    assert result["states"][0]["core_semantics"]["all_core_semantics_match"] is True


def test_canonical_runtime_artifact_removes_stage2_convenience_aliases() -> None:
    original = {
        "schema_version": "v1",
        "variants": [{"id": "v1"}],
        "scenes": {"v1": {"frames": [{"step": 0}]}},
        "expected_result": 1,
    }
    stage2_runtime = {
        **original,
        "input": {"x": 1},
        "variant": original["variants"][0],
        "scene": original["scenes"]["v1"],
        "frames": original["scenes"]["v1"]["frames"],
        "result": 1,
        "scenes": {**original["scenes"], "0": original["scenes"]["v1"]},
    }

    assert canonical_runtime_artifact(stage2_runtime) == original
