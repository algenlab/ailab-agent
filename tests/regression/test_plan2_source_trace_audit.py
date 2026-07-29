import csv
import json
from pathlib import Path

import pytest

from scripts import audit_plan2_source_trace as source_trace_audit

from scripts.audit_plan2_source_trace import (
    _write_review_package,
    audit_variant,
    classify_answer_mapping,
    return_line_numbers,
    review_status,
    run_audit,
    select_review_cases,
    select_review_events,
)


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ITEM_FIELDS = {
    "audit_id",
    "case_id",
    "family_id",
    "problem_title",
    "input_data",
    "expected_result",
    "verifier_result",
    "variants",
}
PUBLIC_VARIANT_FIELDS = {
    "variant_id",
    "variant_index",
    "name",
    "strategy",
    "result",
    "source_line_count",
    "source_lines",
    "selected_events",
}
PUBLIC_SOURCE_LINE_FIELDS = {"line_number", "text"}
PUBLIC_CURRENT_EVENT_FIELDS = {
    "event_id",
    "event_index",
    "step",
    "op",
    "role",
    "reason",
    "targets",
    "deps",
    "before",
    "after",
    "value",
    "state",
    "interaction",
    "code_line",
    "source_line",
    "previous_event",
    "next_event",
}
PUBLIC_NEIGHBOR_EVENT_FIELDS = {
    "event_id",
    "event_index",
    "step",
    "op",
    "role",
    "reason",
    "targets",
    "before",
    "after",
    "value",
    "interaction",
    "code_line",
    "source_line",
}
PUBLIC_REVIEW_CSV_FIELDS = [
    "audit_id",
    "event_id",
    "case_id",
    "family_id",
    "variant_id",
    "event_index",
    "step",
    "op",
    "role",
    "reason",
    "code_line",
    "source_line",
    "label",
    "critical_error",
    "notes",
]
PUBLIC_MANIFEST_FIELDS = {
    "kind",
    "status",
    "human_labels_present",
    "reviewers_required",
    "case_count",
    "family_count",
    "variant_count",
    "event_count",
    "allowed_labels",
    "seed",
}


def test_plan2_source_trace_audit_script_exists() -> None:
    assert (ROOT / "scripts" / "audit_plan2_source_trace.py").is_file()


def test_answer_mapping_uses_real_python_return_lines() -> None:
    source = "def solve(data):\n    value = data['x']\n    return value\n"

    assert return_line_numbers(source) == [3]
    assert classify_answer_mapping(3, [3], source_line_count=3) == "exact_return"
    assert classify_answer_mapping(2, [3], source_line_count=3) == "adjacent_return"
    assert classify_answer_mapping(1, [3], source_line_count=3) == "other_source_line"
    assert classify_answer_mapping(9, [3], source_line_count=3) == "out_of_range"
    assert classify_answer_mapping(None, [3], source_line_count=3) == "missing_code_line"


def test_audit_variant_exposes_collapse_out_of_range_and_answer_mapping() -> None:
    variant = {
        "id": "v1",
        "code": "def solve(data):\n    total = data['x']\n    return total\n",
        "trace": {
            "events": [
                {"step": 0, "op": "create", "code_line": 1, "state": {"total": 0}},
                {
                    "step": 1,
                    "op": "set",
                    "code_line": 2,
                    "before": 0,
                    "after": 1,
                    "state": {"total": 1},
                },
                {"step": 2, "op": "enter", "code_line": 2, "state": {"total": 1}},
                {
                    "step": 3,
                    "op": "mark",
                    "role": "answer",
                    "targets": [{"id": "answer"}],
                    "code_line": 3,
                    "state": {"total": 1, "answer": 1},
                },
                {"step": 4, "op": "note", "code_line": 9, "state": {"total": 1}},
            ]
        },
    }

    event_rows, summary = audit_variant(
        case_id="case-a",
        family_id="arrays",
        variant_index=0,
        variant=variant,
        scene={
            "frames": [
                {},
                {},
                {},
                {"interaction": {"type": "input", "prompt": "answer?"}},
                {},
            ]
        },
    )

    assert summary["event_count"] == 5
    assert summary["code_line_1_count"] == 1
    assert summary["out_of_range_count"] == 1
    assert summary["answer_mapping_counts"]["exact_return"] == 1
    assert summary["dominant_line_dominated_80pct"] is False
    assert summary["terminal_source_mapping"] == "out_of_range"
    assert summary["terminal_has_explicit_answer"] is False
    assert next(row for row in event_rows if row["step"] == 3)["interaction"]["type"] == "input"
    assert next(row for row in event_rows if row["step"] == 4)["risk"] == "critical"


def test_review_event_selection_keeps_four_distinct_roles() -> None:
    rows = [
        {"event_id": "a", "is_answer": True, "is_state_modification": False, "is_control": False, "risk_score": 1},
        {"event_id": "b", "is_answer": False, "is_state_modification": True, "is_control": False, "risk_score": 2},
        {"event_id": "c", "is_answer": False, "is_state_modification": False, "is_control": True, "risk_score": 3},
        {"event_id": "d", "is_answer": False, "is_state_modification": False, "is_control": False, "risk_score": 10},
        {"event_id": "e", "is_answer": False, "is_state_modification": False, "is_control": False, "risk_score": 0},
    ]

    selected = select_review_events(rows, max_events=4)

    assert {row["event_id"] for row in selected} == {"a", "b", "c", "d"}
    assert {role for row in selected for role in row["selection_roles"]} == {
        "final_answer",
        "state_modification",
        "control_event",
        "highest_risk",
    }


def test_review_case_selection_covers_families_before_filling_remaining_slots() -> None:
    cases = [
        {"case_id": "a1", "family_id": "a", "risk_score": 1},
        {"case_id": "a2", "family_id": "a", "risk_score": 9},
        {"case_id": "b1", "family_id": "b", "risk_score": 2},
        {"case_id": "b2", "family_id": "b", "risk_score": 8},
        {"case_id": "c1", "family_id": "c", "risk_score": 3},
    ]

    selected = select_review_cases(cases, count=4, seed=7)

    assert len(selected) == 4
    assert {row["family_id"] for row in selected} == {"a", "b", "c"}


def test_review_status_never_treats_blank_or_invalid_labels_as_results() -> None:
    expected = {"event-a", "event-b"}
    blank = [{"event_id": event_id, "label": ""} for event_id in sorted(expected)]
    assert review_status(blank, blank, expected_ids=expected) == "pending_human_labels"

    valid_a = [{"event_id": event_id, "label": "exact"} for event_id in sorted(expected)]
    valid_b = [
        {"event_id": "event-a", "label": "semantically_adjacent"},
        {"event_id": "event-b", "label": "exact"},
    ]
    assert review_status(valid_a, valid_b, expected_ids=expected) == "pending_adjudication"

    with pytest.raises(ValueError, match="invalid review label"):
        review_status(
            [{"event_id": "event-a", "label": "looks fine"}],
            valid_b,
            expected_ids=expected,
        )


def test_public_review_items_include_source_and_case_facts_without_automatic_conclusions(
    tmp_path: Path,
) -> None:
    output_dir = _write_synthetic_review_package(tmp_path / "review")
    item_path = next((output_dir / "items").glob("*.json"))
    item = json.loads(item_path.read_text(encoding="utf-8"))

    assert item["problem_title"] == "求和"
    assert item["input_data"] == {"x": 2}
    assert item["expected_result"] == 2
    assert item["verifier_result"] == 2
    variant = item["variants"][0]
    assert variant["result"] == 2
    assert variant["source_lines"] == [
        {"line_number": 1, "text": "def solve(input_data):"},
        {"line_number": 2, "text": "    total = input_data['x']"},
        {"line_number": 3, "text": "    return total"},
    ]
    current = next(event for event in variant["selected_events"] if event["event_id"] == "case-a:v1:2:2")
    assert current["code_line"] == 2
    assert current["source_line"] == "    total = input_data['x']"
    assert current["previous_event"]["event_id"] == "case-a:v1:1:1"
    assert current["next_event"]["event_id"] == "case-a:v1:3:3"
    _assert_public_review_contract(output_dir)


def test_review_package_preserves_existing_labels_and_refuses_protocol_changes(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "review"
    _write_synthetic_review_package(output_dir, case_ids=("case-a", "case-b"), seed=17)
    reviewer_path = output_dir / "reviewer_a.csv"
    reviewer_rows = _read_review_csv(reviewer_path)
    reviewer_rows[0]["label"] = "exact"
    reviewer_rows[0]["critical_error"] = "0"
    reviewer_rows[0]["notes"] = "human label"
    _write_review_csv(reviewer_path, reviewer_rows)
    key_before = (output_dir / "private_review_key.json").read_bytes()
    item_hashes_before = {
        path.name: path.read_bytes() for path in (output_dir / "items").glob("*.json")
    }
    sentinel = output_dir / "keep-me.txt"
    sentinel.write_text("keep", encoding="utf-8")

    _write_synthetic_review_package(output_dir, case_ids=("case-a", "case-b"), seed=17)

    assert _read_review_csv(reviewer_path)[0]["notes"] == "human label"
    assert (output_dir / "private_review_key.json").read_bytes() == key_before
    assert {
        path.name: path.read_bytes() for path in (output_dir / "items").glob("*.json")
    } == item_hashes_before
    assert sentinel.read_text(encoding="utf-8") == "keep"

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        _write_synthetic_review_package(output_dir, case_ids=("case-c",), seed=29)


def test_human_review_analysis_reports_ci_critical_error_and_agreement() -> None:
    analyze = getattr(source_trace_audit, "analyze_human_reviews", None)
    assert callable(analyze)
    labels = (
        ("event-a", "exact", "0"),
        ("event-b", "semantically_adjacent", "0"),
        ("event-c", "wrong", "1"),
        ("event-d", "no_source_counterpart", "0"),
    )
    reviewer_a = [
        {"event_id": event_id, "label": label, "critical_error": critical}
        for event_id, label, critical in labels
    ]
    reviewer_b = [dict(row) for row in reviewer_a]

    result = analyze(reviewer_a, reviewer_b, expected_ids={row[0] for row in labels})

    assert result["status"] == "complete"
    assert result["exact_plus_adjacent"]["rate"] == 0.5
    assert len(result["exact_plus_adjacent"]["wilson_ci_95"]) == 2
    assert result["critical_error"]["rate"] == 0.25
    assert result["inter_rater"]["label_exact_agreement"] == 1.0
    assert result["strong_claim_gate"]["passed"] is False


def test_run_audit_carries_real_artifact_source_and_facts_into_blind_review_package(
    tmp_path: Path,
) -> None:
    source = "def solve(input_data):\n    total = input_data['x']\n    return total\n"
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text(
        json.dumps(
            {
                "problem_title": "真实求和题",
                "input_data": {"x": 7},
                "expected_result": 7,
                "verifier_result": 7,
                "variants": [
                    {
                        "id": "v1",
                        "name": "直接返回",
                        "strategy": "读取并返回输入值",
                        "code": source,
                        "result": 7,
                        "trace": {
                            "events": [
                                {
                                    "step": 0,
                                    "op": "create",
                                    "reason": "创建 total",
                                    "targets": [{"id": "total"}],
                                    "code_line": 1,
                                    "state": {"total": 0},
                                },
                                {
                                    "step": 1,
                                    "op": "set",
                                    "reason": "读取 x",
                                    "targets": [{"id": "total"}],
                                    "before": 0,
                                    "after": 7,
                                    "code_line": 2,
                                    "state": {"total": 7},
                                },
                                {
                                    "step": 2,
                                    "op": "mark",
                                    "role": "answer",
                                    "reason": "返回 total",
                                    "targets": [{"id": "answer"}],
                                    "value": 7,
                                    "code_line": 3,
                                    "state": {"total": 7, "answer": 7},
                                },
                            ]
                        },
                    }
                ],
                "scenes": {
                    "v1": {
                        "frames": [
                            {},
                            {"interaction": {"type": "input", "prompt": "x 是多少？"}},
                            {},
                        ]
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "case_id": "case-real",
                        "family_id": "arrays",
                        "title": "报告回退标题",
                        "input_data": {"x": -1},
                        "expected": -1,
                        "json": str(artifact_path),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "audit"

    summary = run_audit(report_path=report_path, output_dir=output_dir, review_count=1, seed=31)

    assert summary["status"] == "automatic_complete_human_pending"
    assert (summary["case_count"], summary["variant_count"], summary["event_count"]) == (1, 1, 3)
    human_dir = output_dir / "human_review"
    item_path = next((human_dir / "items").glob("*.json"))
    item = json.loads(item_path.read_text(encoding="utf-8"))
    assert item["problem_title"] == "真实求和题"
    assert item["input_data"] == {"x": 7}
    assert item["expected_result"] == 7
    assert item["verifier_result"] == 7
    variant = item["variants"][0]
    assert variant["source_lines"] == [
        {"line_number": 1, "text": "def solve(input_data):"},
        {"line_number": 2, "text": "    total = input_data['x']"},
        {"line_number": 3, "text": "    return total"},
    ]
    assert variant["result"] == 7
    current = next(event for event in variant["selected_events"] if event["event_index"] == 1)
    assert current["code_line"] == 2
    assert current["source_line"] == "    total = input_data['x']"
    assert current["interaction"] == {"type": "input", "prompt": "x 是多少？"}
    assert current["previous_event"]["event_id"] == "case-real:v1:0:0"
    assert current["next_event"]["event_id"] == "case-real:v1:2:2"
    auto_events = [
        json.loads(line)
        for line in (output_dir / "source_trace_auto_events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert {"risk", "risk_score", "risk_reasons", "answer_mapping"} <= set(auto_events[-1])
    _assert_public_review_contract(human_dir)


def test_reviewer_csvs_use_distinct_deterministic_orders_with_blank_labels(tmp_path: Path) -> None:
    first = _write_synthetic_review_package(tmp_path / "first")
    second = _write_synthetic_review_package(tmp_path / "second")

    first_a = _read_review_csv(first / "reviewer_a.csv")
    first_b = _read_review_csv(first / "reviewer_b.csv")
    second_a = _read_review_csv(second / "reviewer_a.csv")
    second_b = _read_review_csv(second / "reviewer_b.csv")
    ids_a = [row["event_id"] for row in first_a]
    ids_b = [row["event_id"] for row in first_b]

    assert len(ids_a) == len(ids_b) == 4
    assert set(ids_a) == set(ids_b)
    assert ids_a != ids_b
    assert ids_a == [row["event_id"] for row in second_a]
    assert ids_b == [row["event_id"] for row in second_b]
    assert all(
        row["label"] == row["critical_error"] == row["notes"] == ""
        for row in first_a + first_b
    )


def _write_synthetic_review_package(
    output_dir: Path,
    *,
    case_ids: tuple[str, ...] = ("case-a",),
    seed: int = 17,
) -> Path:
    selected_cases = [
        {
            "case_id": case_id,
            "family_id": "arrays",
            "risk_score": 100,
            "problem_title": "求和",
            "input_data": {"x": index + 2},
            "expected_result": index + 2,
            "verifier_result": index + 2,
        }
        for index, case_id in enumerate(case_ids)
    ]
    source_lines = [
        {"line_number": 1, "text": "def solve(input_data):"},
        {"line_number": 2, "text": "    total = input_data['x']"},
        {"line_number": 3, "text": "    return total"},
    ]
    variant_rows = [
        {
            "case_id": case_id,
            "family_id": "arrays",
            "variant_id": "v1",
            "variant_index": 0,
            "source_line_count": 3,
            "return_lines": [3],
            "risk_score": 100,
            "name": "直接求和",
            "strategy": "读取输入并返回",
            "result": index + 2,
            "source_lines": source_lines,
        }
        for index, case_id in enumerate(case_ids)
    ]
    events_by_case_variant = {
        (case_id, "v1"): [
            _synthetic_event(0, case_id=case_id, op="create", code_line=1, risk_score=40, mutation=True),
            _synthetic_event(1, case_id=case_id, op="compare", code_line=2, risk_score=10, control=True),
            _synthetic_event(2, case_id=case_id, op="set", code_line=2, risk_score=100, mutation=True),
            _synthetic_event(3, case_id=case_id, op="mark", code_line=3, risk_score=70, answer=True),
            _synthetic_event(4, case_id=case_id, op="exit", code_line=3, risk_score=20, control=True),
        ]
        for case_id in case_ids
    }
    _write_review_package(
        output_dir=output_dir,
        selected_cases=selected_cases,
        variant_rows=variant_rows,
        events_by_case_variant=events_by_case_variant,
        seed=seed,
    )
    return output_dir


def _synthetic_event(
    event_index: int,
    *,
    case_id: str = "case-a",
    op: str,
    code_line: int,
    risk_score: int,
    answer: bool = False,
    mutation: bool = False,
    control: bool = False,
) -> dict[str, object]:
    source = {
        1: "def solve(input_data):",
        2: "    total = input_data['x']",
        3: "    return total",
    }
    return {
        "event_id": f"{case_id}:v1:{event_index}:{event_index}",
        "case_id": case_id,
        "family_id": "arrays",
        "variant_id": "v1",
        "variant_index": 0,
        "event_index": event_index,
        "step": event_index,
        "op": op,
        "role": "answer" if answer else "",
        "reason": f"event {event_index}",
        "targets": [{"id": "answer" if answer else "total"}],
        "deps": [],
        "before": event_index - 1,
        "after": event_index,
        "value": event_index,
        "state": {"total": event_index},
        "interaction": None,
        "code_line": code_line,
        "source_line": source[code_line],
        "source_line_count": 3,
        "return_lines": [3],
        "is_answer": answer,
        "is_state_modification": mutation,
        "is_control": control,
        "answer_mapping": "exact_return" if answer else "",
        "risk_score": risk_score,
        "risk": "critical" if risk_score >= 90 else "low",
        "risk_reasons": ["automatic conclusion"],
    }


def _read_review_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_review_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open(encoding="utf-8-sig", newline="", mode="w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _assert_public_review_contract(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "package_manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == PUBLIC_MANIFEST_FIELDS
    assert (output_dir / "README.md").read_text(encoding="utf-8") == _expected_readme(manifest)

    for item_path in (output_dir / "items").glob("*.json"):
        item = json.loads(item_path.read_text(encoding="utf-8"))
        assert set(item) == PUBLIC_ITEM_FIELDS
        for variant in item["variants"]:
            assert set(variant) == PUBLIC_VARIANT_FIELDS
            assert all(set(line) == PUBLIC_SOURCE_LINE_FIELDS for line in variant["source_lines"])
            for event in variant["selected_events"]:
                assert set(event) == PUBLIC_CURRENT_EVENT_FIELDS
                for neighbor_name in ("previous_event", "next_event"):
                    neighbor = event[neighbor_name]
                    if neighbor is not None:
                        assert set(neighbor) == PUBLIC_NEIGHBOR_EVENT_FIELDS

    for reviewer in ("reviewer_a.csv", "reviewer_b.csv"):
        with (output_dir / reviewer).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == PUBLIC_REVIEW_CSV_FIELDS
            assert all(set(row) == set(PUBLIC_REVIEW_CSV_FIELDS) for row in reader)


def _expected_readme(manifest: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Plan-2 Source-to-Trace 双评审包",
            "",
            "- 当前状态：`pending_human_labels`",
            f"- 题目数：{manifest['case_count']}；算法族数：{manifest['family_count']}",
            f"- 待标事件：{manifest['event_count']}（抽中题目的所有 variant，每个 variant 最多 4 个关键事件）",
            "",
            "每个 item 提供题目输入、期望结果、实际结果、带行号的完整 solve 源码，以及待标事件的前后事件摘要。",
            "事件中的 code_line 是当前待评映射行；两份 CSV 已使用不同的确定性随机顺序。",
            "",
            "两位评审者分别填写 reviewer_a.csv 和 reviewer_b.csv。label 只能填写：",
            "`exact`、`semantically_adjacent`、`wrong`、`no_source_counterpart`。",
            "critical_error 填 1/0，表示该映射错误是否会改变算法事实或教学结论。",
            "不得使用模型自动补标签；分歧需人工裁决。",
            "",
        ]
    )
