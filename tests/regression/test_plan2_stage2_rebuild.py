import json
import subprocess
import sys
from pathlib import Path

from scripts.rebuild_plan2_stage2_after_variant_fix import rebuild_stage2_pages


ROOT = Path(__file__).resolve().parents[2]


def _artifact_payload() -> dict:
    return {
        "problem_title": "rebuild test",
        "input_data": {"value": 1},
        "expected_result": 1,
        "verifier_result": 1,
        "variants": [
            {
                "id": "v1",
                "name": "one",
                "strategy": "test",
                "code": "def solve(input_data):\n    return 1",
                "tracker_code": "def trace(input_data):\n    return {}",
                "result": 1,
            }
        ],
        "scenes": {
            "v1": {
                "algorithm": "test",
                "input_data": {"value": 1},
                "result": 1,
                "frames": [
                    {
                        "step": 0,
                        "title": "start",
                        "description": "start",
                        "operation": "set",
                        "state": {"answer": 1},
                    }
                ],
            }
        },
        "validation": {},
    }


def test_rebuild_stage2_pages_uses_saved_raw_output_without_api(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    artifact = root / "inputs" / "case.json"
    raw = root / "saved" / "case_raw.txt"
    report = root / "reports" / "case_report.json"
    manifest = root / "manifest.json"
    output = root / "rebuilt"
    artifact.parent.mkdir(parents=True)
    raw.parent.mkdir(parents=True)
    report.parent.mkdir(parents=True)
    artifact.write_text(json.dumps(_artifact_payload()), encoding="utf-8")
    raw.write_text(
        '<template id="creative-stage-template"><div></div></template>'
        '<script>function renderCreativeStage(ctx){return String(ctx.frameIndex)}</script>',
        encoding="utf-8",
    )
    report.write_text(
        json.dumps({"raw_output": "/work/saved/case_raw.txt"}),
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "case_id": "case",
                        "artifact_repo_path": "inputs/case.json",
                        "html_repo_path": "old/case.html",
                        "generation_report_repo_path": "reports/case_report.json",
                        "selection": "primary",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = rebuild_stage2_pages(
        manifest_path=manifest,
        output_dir=output,
        root=root,
        expected_cases=1,
    )

    assert summary["case_count"] == 1
    assert summary["api_calls"] == 0
    rebuilt_manifest = json.loads((output / "selected_html_manifest_variant_fix.json").read_text())
    rebuilt_html = root / rebuilt_manifest["items"][0]["html_repo_path"]
    assert rebuilt_html.is_file()
    assert "function renderCreativeStage" in rebuilt_html.read_text(encoding="utf-8")
    assert rebuilt_manifest["items"][0]["artifact_repo_path"] == "inputs/case.json"


def test_rebuild_script_can_start_outside_repository(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/rebuild_plan2_stage2_after_variant_fix.py"),
            "--help",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
