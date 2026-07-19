from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GALLERY = ROOT / "artifacts/method_comparison_samples"


def test_selection_covers_23_unique_benchmark_families() -> None:
    from scripts.build_method_artifact_gallery import SELECTED_CASES

    assert len(SELECTED_CASES) == 23
    assert len({row["family"] for row in SELECTED_CASES}) == 23
    assert len({row["case_id"] for row in SELECTED_CASES}) == 23


def test_committed_gallery_contains_five_complete_method_artifacts_per_case() -> None:
    from scripts.build_method_artifact_gallery import (
        MACHINE_BOOL_KEYS,
        METHOD_ORDER,
        validate_gallery,
    )

    summary = validate_gallery(GALLERY)

    assert summary == {
        "case_count": 23,
        "family_count": 23,
        "method_artifact_count": 115,
    }

    manifest = json.loads((GALLERY / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["method_order"] == list(METHOD_ORDER)
    assert len(manifest["cases"]) == 23

    for case in manifest["cases"]:
        case_dir = GALLERY / "cases" / case["case_id"]
        assert (case_dir / "README.md").is_file()
        assert (case_dir / "case.json").is_file()

        for method in METHOD_ORDER:
            method_dir = case_dir / method
            screenshot = method_dir / "screenshot.png"
            audit_path = method_dir / "audit.json"
            assert screenshot.stat().st_size > 0
            assert audit_path.is_file()

            audit_text = audit_path.read_text(encoding="utf-8")
            assert "/ssd1/" not in audit_text
            assert "/home/" not in audit_text
            audit = json.loads(audit_text)
            assert set(audit["machine_metrics"]) == set(MACHINE_BOOL_KEYS)
            assert audit["machine_ok"] == all(audit["machine_metrics"].values())

            if method == "webgen_agent":
                assert (method_dir / "source/index.html").is_file()
                assert (method_dir / "source/package.json").is_file()
            else:
                assert (method_dir / "page.html").stat().st_size > 0
