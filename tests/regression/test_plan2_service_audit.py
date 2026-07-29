from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from scripts.audit_service_composition import (
    FAMILY_TO_MACRO_GROUP,
    analyze_source_lines,
    extract_trace_services,
    macro_group_for_family,
    run_service_audit,
)


def test_extract_trace_services_counts_only_trace_session_factories() -> None:
    tracker_code = '''
def trace(input_data):
    sess = TraceSession("demo", input_data)
    arr = sess.array("nums", input_data["nums"])
    left = sess.pointer("left", on=arr, idx=0)
    with sess.step("scan"):
        arr.highlight(0)
        sess.note("start")
    sess.result(left.idx)
    return sess.to_trace()
'''

    result = extract_trace_services(tracker_code)

    assert result.services == ("array", "pointer")
    assert result.unknown_session_calls == ()


def test_service_audit_cli_can_run_as_a_direct_script() -> None:
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, str(root / "scripts" / "audit_service_composition.py"), "--help"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_extract_trace_services_reports_calls_outside_the_session_catalog() -> None:
    tracker_code = '''
def trace(input_data):
    session = TraceSession("demo", input_data)
    session.canvas("stage")
    session.result(0)
    return session.to_trace()
'''

    result = extract_trace_services(tracker_code)

    assert result.services == ()
    assert result.unknown_session_calls == ("canvas",)


def test_analyze_source_lines_reports_collapse_and_answer_return_alignment() -> None:
    source = '''def solve(input_data):
    value = input_data["value"]
    if value > 0:
        value += 1
        return value
    return 0'''
    events = [
        {"step": 0, "op": "create", "targets": [{"id": "value"}], "code_line": 1},
        {"step": 1, "op": "note", "targets": [], "code_line": 1},
        {
            "step": 2,
            "op": "mark",
            "targets": [{"id": "answer"}],
            "role": "answer",
            "code_line": 5,
        },
    ]

    result = analyze_source_lines(source, events)

    assert result.event_count == 3
    assert result.code_line_one_count == 2
    assert result.code_line_one_ratio == 2 / 3
    assert result.dominant_line == 1
    assert result.dominant_line_ratio == 2 / 3
    assert result.single_line_dominated is True
    assert result.out_of_range_count == 0
    assert result.answer_event_count == 1
    assert result.answer_return_line_match_count == 1
    assert result.answer_return_line_match_rate == 1.0


def test_macro_group_mapping_covers_representative_families() -> None:
    assert macro_group_for_family("dp_core") == "dynamic_programming"
    assert macro_group_for_family("advanced_graph") == "graph_algorithms"
    assert macro_group_for_family("string_advanced") == "strings_hash"
    assert macro_group_for_family("range_structure") == "trees_and_structures"
    assert macro_group_for_family("geometry_sweep") == "math_geometry"
    assert len(FAMILY_TO_MACRO_GROUP) == 23
    assert "unmapped" not in FAMILY_TO_MACRO_GROUP.values()


def test_source_line_diagnostics_separates_missing_invalid_and_out_of_range() -> None:
    source = "def solve(input_data):\n    return 0"
    events = [
        {"step": 0},
        {"step": 1, "code_line": "2"},
        {"step": 2, "code_line": 0},
        {"step": 3, "code_line": 99},
        {"step": 4, "code_line": 2},
    ]

    result = analyze_source_lines(source, events)

    assert result.code_line_missing_count == 1
    assert result.code_line_invalid_count == 2
    assert result.out_of_range_count == 1
    assert result.distinct_valid_code_line_count == 1
    assert result.dominant_line == 2
    assert result.dominant_line_count == 1
    assert result.dominant_line_ratio == 0.2
    assert result.single_line_collapse is False


def test_run_service_audit_writes_the_five_required_outputs(tmp_path) -> None:
    artifact_a = tmp_path / "a.json"
    artifact_a.write_text(
        '''{
  "schema_version": "algolab-build-v1",
  "variants": [{
    "id": "v1",
    "name": "array scan",
    "code": "def solve(input_data):\\n    return input_data['nums'][0]",
    "tracker_code": "def trace(input_data):\\n    sess = TraceSession('scan', input_data)\\n    arr = sess.array('nums', input_data['nums'])\\n    ptr = sess.pointer('ptr', on=arr, idx=0)\\n    sess.result(arr[0])\\n    return sess.to_trace()",
    "trace": {"result": 1, "events": [{"step": 0, "op": "mark", "targets": [{"id": "answer"}], "role": "answer", "code_line": 2}]}
  }]
}''',
        encoding="utf-8",
    )
    artifact_b = tmp_path / "b.json"
    artifact_b.write_text(
        '''{
  "schema_version": "algolab-build-v1",
  "variants": [{
    "id": "v1",
    "name": "graph walk",
    "code": "def solve(input_data):\\n    return 0",
    "tracker_code": "def trace(input_data):\\n    sess = TraceSession('walk', input_data)\\n    graph = sess.graph('g', [0], [])\\n    sess.canvas('bad')\\n    sess.result(0)\\n    return sess.to_trace()",
    "trace": {"result": 0, "events": [{"step": 0, "op": "mark", "targets": [{"id": "answer"}], "role": "answer", "code_line": 2}]}
  }]
}''',
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    report.write_text(
        '''{
  "results": [
    {"case_id": "a", "title": "A", "family": "数组", "family_id": "array_pointer", "sample_index": 0, "ok": true, "json": "'''
        + str(artifact_a)
        + '''"},
    {"case_id": "b", "title": "B", "family": "图", "family_id": "basic_graph", "sample_index": 0, "ok": true, "json": "'''
        + str(artifact_b)
        + '''"}
  ]
}''',
        encoding="utf-8",
    )
    output_dir = tmp_path / "audit"

    summary = run_service_audit(report, output_dir, expected_cases=2)

    assert summary["coverage"]["case_count"] == 2
    assert summary["coverage"]["variant_count"] == 2
    assert summary["service_usage"]["used_service_count"] == 3
    assert summary["service_usage"]["multi_service_cases"] == {
        "numerator": 1,
        "denominator": 2,
        "rate": 0.5,
    }
    assert summary["service_usage"]["outside_catalog_calls"][0]["method"] == "canvas"
    assert summary["source_line"]["canonical_answer_event_return_match"] == {
        "numerator": 2,
        "denominator": 2,
        "rate": 1.0,
    }
    assert summary["reuse"]["by_service"]["array"] == {
        "case_count": 1,
        "variant_count": 1,
        "family_count": 1,
        "families": ["array_pointer"],
        "macro_group_count": 1,
        "macro_groups": ["sequence_search_sort"],
    }
    for name in (
        "service_usage_per_case.csv",
        "service_reuse_matrix.csv",
        "service_cooccurrence.csv",
        "source_line_diagnostics.csv",
        "service_usage_summary.json",
    ):
        assert (output_dir / name).is_file()
    with (output_dir / "service_reuse_matrix.csv").open(encoding="utf-8", newline="") as handle:
        reuse = {row["service"]: row for row in csv.DictReader(handle)}
    assert reuse["array"]["factory_call_site_count"] == "1"
    assert reuse["pointer"]["factory_call_site_count"] == "1"
    assert reuse["graph"]["factory_call_site_count"] == "1"

    partial_report = tmp_path / "partial_report.json"
    partial_report.write_text(
        '''{
  "results": [
    {"case_id": "a", "title": "A", "family": "数组", "family_id": "array_pointer", "sample_index": 0, "ok": true, "json": "'''
        + str(artifact_a)
        + '''"},
    {"case_id": "failed", "title": "Failed", "family": "图", "family_id": "basic_graph", "sample_index": 0, "ok": false}
  ]
}''',
        encoding="utf-8",
    )
    partial = run_service_audit(
        partial_report,
        tmp_path / "partial_audit",
        expected_cases=2,
        require_all_ok=False,
    )
    assert partial["coverage"]["source_case_count"] == 2
    assert partial["coverage"]["case_count"] == 1
    assert partial["coverage"]["skipped_failed_case_ids"] == ["failed"]
