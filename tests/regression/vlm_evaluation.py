"""Regression tests for VLM screenshot evaluation infrastructure."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import llm_client
from scripts.run_vlm_screenshot_eval import build_report, write_report


def _valid_payload(case_id: str = "case_a", condition: str = "deterministic", screenshot: str = "case_a.png") -> dict:
    return {
        "case_id": case_id,
        "condition": condition,
        "screenshot": screenshot,
        "viewport": "desktop",
        "scores": {
            "layout_readability": 5,
            "algorithm_state_visibility": 4,
            "teaching_explanation": 4,
            "interaction_affordance": 3,
            "evidence_alignment": 4,
            "overall_teaching_quality": 4,
        },
        "confidence": 0.8,
        "issues": [
            {
                "severity": "medium",
                "category": "interaction",
                "message": "Formula toggle is visible but secondary.",
            }
        ],
        "suggested_caption": "Clear state transition with visible controls.",
    }


def _write_fixture_files(root: Path) -> tuple[Path, Path, Path, Path]:
    image_a = root / "case_a.png"
    image_b = root / "case_b.png"
    image_a.write_bytes(b"fake-png-a")
    image_b.write_bytes(b"fake-png-b")
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "test-manifest",
                "ok": True,
                "screenshots": [
                    {
                        "kind": "page",
                        "target_id": "case_a",
                        "html": "case_a.html",
                        "viewport": "desktop",
                        "screenshot": str(image_a),
                        "bytes": image_a.stat().st_size,
                        "ok": True,
                        "errors": [],
                    },
                    {
                        "kind": "interaction",
                        "target_id": "case_b",
                        "html": "case_b.html",
                        "viewport": "mobile",
                        "phase": "after_click",
                        "screenshot": str(image_b),
                        "bytes": image_b.stat().st_size,
                        "ok": True,
                        "errors": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    rubric = root / "rubric.json"
    rubric.write_text(
        json.dumps(
            {
                "schema_version": "vlm-screenshot-rubric-v1",
                "rubric_version": "test-rubric",
                "dimensions": [],
            }
        ),
        encoding="utf-8",
    )
    system_prompt = root / "system.txt"
    user_prompt = root / "user.txt"
    system_prompt.write_text("System prompt: visible content only.", encoding="utf-8")
    user_prompt.write_text("Condition {{condition}} case {{case_id}} rubric {{rubric_json}}", encoding="utf-8")
    return manifest, rubric, system_prompt, user_prompt


def _usage_call(content: str) -> dict:
    return {
        "content": content,
        "model_call": {
            "kind": "vlm_eval",
            "model": "fake-vlm",
            "started_at": "2026-05-30T00:00:00",
            "ended_at": "2026-05-30T00:00:01",
            "duration_s": 1.0,
            "usage_available": True,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


def _no_usage_call(content: str) -> dict:
    return {
        "content": content,
        "model_call": {
            "kind": "vlm_eval",
            "model": "fake-vlm",
            "started_at": "2026-05-30T00:00:00",
            "ended_at": "2026-05-30T00:00:01",
            "duration_s": 1.0,
            "usage_available": False,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        },
    }


def test_fake_vlm_legal_json_records_scores_usage_and_versions():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            return _usage_call(json.dumps(_valid_payload()))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
        )

    assert report["prompt_version"]
    assert report["prompt_hash"]
    assert report["rubric_version"] == "test-rubric"
    assert report["rubric_hash"]
    assert report["summary"]["passed"] == 2
    assert report["summary"]["failed"] == 0
    assert report["summary"]["model_usage"]["usage_available"] is True
    assert report["summary"]["model_usage"]["prompt_tokens"] == 20
    assert report["summary"]["model_usage"]["completion_tokens"] == 40
    assert report["summary"]["model_usage"]["total_tokens"] == 60
    assert report["results"][0]["scores"]["layout_readability"] == 5
    assert report["results"][0]["model_call"]["usage_available"] is True
    assert report["results"][0]["model_call"]["prompt_tokens"] == 10


def test_fake_vlm_invalid_json_does_not_stop_batch_and_preserves_fields():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)
        responses = iter(["not json", json.dumps(_valid_payload(case_id="case_b"))])

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            return _usage_call(next(responses))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
        )

    assert report["summary"]["passed"] == 1
    assert report["summary"]["failed"] == 1
    first = report["results"][0]
    second = report["results"][1]
    assert first["ok"] is False
    assert first["failure_type"] == "vlm_eval_error"
    assert first["case_id"] == "case_a"
    assert first["condition"] == "deterministic"
    assert first["viewport"] == "desktop"
    assert first["screenshot"].endswith("case_a.png")
    assert second["ok"] is True
    assert second["case_id"] == "case_b"


def test_fake_vlm_exception_does_not_stop_batch():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)
        calls = {"count": 0}

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            calls["count"] += 1
            if calls["count"] == 1:
                raise Exception("upstream 500")
            return _usage_call(json.dumps(_valid_payload(case_id="case_b")))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
        )

    assert report["summary"]["passed"] == 1
    assert report["summary"]["failed"] == 1
    assert report["summary"]["failure_types"] == {"vlm_eval_error": 1}
    assert report["results"][0]["failure_type"] == "vlm_eval_error"
    assert "upstream 500" in report["results"][0]["error"]
    assert report["results"][1]["ok"] is True


def test_retry_recovers_empty_vlm_response_and_records_each_call():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)
        responses = iter(["", json.dumps(_valid_payload()), json.dumps(_valid_payload(case_id="case_b"))])

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            return _usage_call(next(responses))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
            retries=1,
        )

    assert report["summary"]["passed"] == 2
    assert report["summary"]["failed"] == 0
    assert report["summary"]["model_usage"]["call_count"] == 3
    assert len(report["results"][0]["model_calls"]) == 2


def test_caption_allows_thirty_english_words():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)
        payload = _valid_payload()
        payload["suggested_caption"] = (
            "Clear dashboard view showing algorithm status controls evidence state explanation layout interaction feedback "
            "and readable teaching context for paper review"
        )

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            return _usage_call(json.dumps(payload))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
        )

    assert report["summary"]["passed"] == 2
    assert report["results"][0]["suggested_caption"].startswith("Clear dashboard")


def test_score_range_validation_marks_result_failed():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)
        payload = _valid_payload()
        payload["scores"]["layout_readability"] = 6

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            return _usage_call(json.dumps(payload))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
        )

    assert report["summary"]["passed"] == 0
    assert report["summary"]["failed"] == 2
    assert report["results"][0]["failure_type"] == "vlm_eval_error"
    assert "layout_readability" in report["results"][0]["error"]


def test_usage_unavailable_is_explicit_and_summary_tokens_are_null():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            return _no_usage_call(json.dumps(_valid_payload()))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
        )

    assert report["summary"]["model_usage"]["usage_available"] is False
    assert report["summary"]["model_usage"]["usage_available_rate"] == 0.0
    assert report["summary"]["model_usage"]["prompt_tokens"] is None
    assert report["results"][0]["model_call"]["usage_available"] is False
    assert report["results"][0]["model_call"]["prompt_tokens"] is None


def test_write_report_outputs_json_and_csv_files():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        manifest, rubric, system_prompt, user_prompt = _write_fixture_files(root)

        def fake_judge(_system_prompt, _user_prompt, _image_b64, _model):
            return _usage_call(json.dumps(_valid_payload()))

        report = build_report(
            manifest_path=manifest,
            condition="deterministic",
            rubric_path=rubric,
            system_prompt_path=system_prompt,
            user_prompt_path=user_prompt,
            judge_model="fake-vlm",
            judge_call=fake_judge,
        )
        out = root / "out"
        json_path = write_report(report, out)

        assert json_path.exists()
        assert (out / "vlm_screenshot_scores.csv").exists()
        assert (out / "vlm_screenshot_summary.csv").exists()


def test_vlm_config_uses_dedicated_timeout_default_and_env_override():
    old_timeout = os.environ.get("ALGOLAB_VLM_TIMEOUT_S")
    old_max_tokens = os.environ.get("ALGOLAB_VLM_MAX_TOKENS")
    try:
        os.environ.pop("ALGOLAB_VLM_TIMEOUT_S", None)
        os.environ.pop("ALGOLAB_VLM_MAX_TOKENS", None)
        default_config = llm_client.vlm_config("fake-vlm")
        assert default_config["timeout_s"] == llm_client.VISION_TIMEOUT_S
        assert default_config["timeout_s"] >= 600
        assert default_config["max_tokens"] == llm_client.VISION_MAX_TOKENS
        assert default_config["max_tokens"] >= 4096

        os.environ["ALGOLAB_VLM_TIMEOUT_S"] = "123"
        os.environ["ALGOLAB_VLM_MAX_TOKENS"] = "456"
        override_config = llm_client.vlm_config("fake-vlm")
        assert override_config["timeout_s"] == 123.0
        assert override_config["max_tokens"] == 456
    finally:
        if old_timeout is None:
            os.environ.pop("ALGOLAB_VLM_TIMEOUT_S", None)
        else:
            os.environ["ALGOLAB_VLM_TIMEOUT_S"] = old_timeout
        if old_max_tokens is None:
            os.environ.pop("ALGOLAB_VLM_MAX_TOKENS", None)
        else:
            os.environ["ALGOLAB_VLM_MAX_TOKENS"] = old_max_tokens


def run_all():
    test_fake_vlm_legal_json_records_scores_usage_and_versions()
    test_fake_vlm_invalid_json_does_not_stop_batch_and_preserves_fields()
    test_fake_vlm_exception_does_not_stop_batch()
    test_retry_recovers_empty_vlm_response_and_records_each_call()
    test_caption_allows_thirty_english_words()
    test_score_range_validation_marks_result_failed()
    test_usage_unavailable_is_explicit_and_summary_tokens_are_null()
    test_write_report_outputs_json_and_csv_files()
    test_vlm_config_uses_dedicated_timeout_default_and_env_override()


if __name__ == "__main__":
    run_all()
    print("vlm_evaluation: PASS")
