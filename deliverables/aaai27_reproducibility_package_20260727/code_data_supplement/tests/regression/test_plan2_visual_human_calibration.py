import csv
import json
import stat
from pathlib import Path

import pytest

from scripts.plan2_visual_human_calibration import (
    METHODS,
    VISUAL_METRICS,
    analyze_ratings,
    blind_page_id,
    calibration_status,
    prepare_package,
    select_stratified_cases,
)


ROOT = Path(__file__).resolve().parents[2]


def test_plan2_visual_human_calibration_script_exists() -> None:
    assert (ROOT / "scripts" / "plan2_visual_human_calibration.py").is_file()


def test_blind_page_id_is_stable_method_specific_and_secret_keyed() -> None:
    assert blind_page_id("case-a", "direct_html", secret=b"first-secret") == blind_page_id(
        "case-a", "direct_html", secret=b"first-secret"
    )
    assert blind_page_id("case-a", "direct_html", secret=b"first-secret") != blind_page_id(
        "case-a", "webgen_agent", secret=b"first-secret"
    )
    assert blind_page_id("case-a", "direct_html", secret=b"first-secret") != blind_page_id(
        "case-a", "direct_html", secret=b"second-secret"
    )


def test_case_selection_covers_each_available_family_before_filling() -> None:
    candidates = [
        {"case_id": "a1", "family": "a"},
        {"case_id": "a2", "family": "a"},
        {"case_id": "b1", "family": "b"},
        {"case_id": "b2", "family": "b"},
        {"case_id": "c1", "family": "c"},
    ]

    selected = select_stratified_cases(candidates, count=4, seed=11)

    assert len(selected) == 4
    assert {row["family"] for row in selected} == {"a", "b", "c"}


def test_calibration_status_requires_two_complete_valid_rating_sheets() -> None:
    expected = {"page-a", "page-b"}
    blank = [
        {"blind_id": blind_id, **{metric: "" for metric in VISUAL_METRICS}}
        for blind_id in expected
    ]
    assert calibration_status(blank, blank, expected_ids=expected) == "pending_human_labels"

    complete = [
        {"blind_id": blind_id, **{metric: "4" for metric in VISUAL_METRICS}}
        for blind_id in expected
    ]
    assert calibration_status(complete, complete, expected_ids=expected) == "complete"


def test_analysis_reports_vlm_agreement_preferences_and_inter_rater_metrics() -> None:
    key_rows = []
    reviewer_a = []
    reviewer_b = []
    for case_index, case_id in enumerate(("case-a", "case-b")):
        for method_index, method in enumerate(METHODS):
            blind_id = blind_page_id(case_id, method, secret=b"analysis-test-secret")
            score = 5 if method == "algotutorgen_stage2" else 2 + (method_index % 2)
            vlm_scores = {metric: score for metric in VISUAL_METRICS}
            key_rows.append(
                {
                    "blind_id": blind_id,
                    "case_id": case_id,
                    "family": f"f{case_index}",
                    "method": method,
                    "vlm_scores": vlm_scores,
                }
            )
            reviewer_a.append(
                {"blind_id": blind_id, **{metric: str(score) for metric in VISUAL_METRICS}}
            )
            reviewer_b.append(
                {"blind_id": blind_id, **{metric: str(score) for metric in VISUAL_METRICS}}
            )

    result = analyze_ratings(key_rows, reviewer_a, reviewer_b)

    assert result["status"] == "complete"
    assert result["all_ge_3_agreement"]["agreement_rate"] == 1.0
    assert result["paired_preference"]["direct_html"]["pvcr_preferred"] == 2
    assert result["inter_rater"][VISUAL_METRICS[0]]["exact_agreement"] == 1.0


def test_prepare_package_keeps_private_mapping_outside_public_review_dir(tmp_path) -> None:
    prepared_records = {method: [] for method in METHODS}
    review_root = tmp_path / "reviews"
    for method in METHODS:
        screenshot = tmp_path / "screenshots" / method / "case-a.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_bytes(b"not-a-real-png-but-copyable")
        prepared_records[method].append(
            {
                "case_id": "case-a",
                "family": "array",
                "problem_title": "Example problem",
                "problem_description": "Example description",
                "screenshot": str(screenshot),
            }
        )
        review_path = review_root / method / "case-a.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(
            json.dumps({"scores": {metric: 4 for metric in VISUAL_METRICS}}),
            encoding="utf-8",
        )
    prepared_records_path = tmp_path / "prepared_records.json"
    prepared_records_path.write_text(json.dumps(prepared_records), encoding="utf-8")
    public_dir = tmp_path / "public_review"
    private_key = tmp_path / "private" / "visual_blind_key.json"

    prepare_package(
        prepared_records_path=prepared_records_path,
        review_root=review_root,
        output_dir=public_dir,
        private_key_path=private_key,
        count=1,
        seed=17,
    )

    assert private_key.is_file()
    assert stat.S_IMODE(private_key.stat().st_mode) == 0o600
    assert not (public_dir / "private_blind_key.json").exists()
    with (public_dir / "reviewer_a.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert "method" not in rows[0]
    assert "case_id" not in rows[0]
    readme = (public_dir / "README.md").read_text(encoding="utf-8")
    assert "空白页" in readme
    assert "渲染失败" in readme
    assert "四项均记 1 分" in readme


def test_prepare_package_preserves_existing_key_and_human_scores(tmp_path) -> None:
    prepared_records = {method: [] for method in METHODS}
    review_root = tmp_path / "reviews"
    for method in METHODS:
        screenshot = tmp_path / "screenshots" / method / "case-a.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_bytes(b"copyable")
        prepared_records[method].append(
            {
                "case_id": "case-a",
                "family": "array",
                "problem_title": "Example problem",
                "problem_description": "Example description",
                "screenshot": str(screenshot),
            }
        )
        review_path = review_root / method / "case-a.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(
            json.dumps({"scores": {metric: 4 for metric in VISUAL_METRICS}}),
            encoding="utf-8",
        )
    prepared_records_path = tmp_path / "prepared_records.json"
    prepared_records_path.write_text(json.dumps(prepared_records), encoding="utf-8")
    output_dir = tmp_path / "public_review"
    private_key = tmp_path / "private" / "visual_blind_key.json"
    kwargs = {
        "prepared_records_path": prepared_records_path,
        "review_root": review_root,
        "output_dir": output_dir,
        "private_key_path": private_key,
        "count": 1,
        "seed": 17,
    }
    prepare_package(**kwargs)
    key_before = private_key.read_bytes()
    reviewer_path = output_dir / "reviewer_a.csv"
    with reviewer_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    rows[0][VISUAL_METRICS[0]] = "5"
    rows[0]["notes"] = "human score"
    with reviewer_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    prepare_package(**kwargs)

    assert private_key.read_bytes() == key_before
    with reviewer_path.open(newline="", encoding="utf-8-sig") as handle:
        preserved = list(csv.DictReader(handle))
    assert preserved[0]["notes"] == "human score"

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        prepare_package(**{**kwargs, "seed": 18})
