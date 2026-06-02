"""Regression tests for R6 LLM failure attribution reports."""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from scripts.analyze_llm_failures import ROOT_CAUSES, analyze_report, classify_failure, main


def _write_sample_report(path: Path) -> None:
    report = {
        "kind": "llm_benchmark_report",
        "total": 6,
        "passed": 1,
        "failed": 5,
        "pass_rate": 1 / 6,
        "failure_summary": {
            "demo_missing_deps": 1,
            "process_invariant": 1,
            "scene_warning": 1,
            "generation": 1,
            "string_contract": 1,
        },
        "model_usage": {
            "usage_available_rate": 0.8,
            "call_count": 10,
            "total_tokens": 12345,
        },
        "browser_smoke": [
            {"html": "ok.html", "ok": True},
            {"html": "bad.html", "ok": False, "errors": ["missing canvas"]},
        ],
        "results": [
            {
                "case_id": "ok_case",
                "family": "Graph",
                "subfamily_id": "bfs",
                "ok": True,
            },
            {
                "case_id": "kmp_prefix_table",
                "family": "String 核心",
                "family_id": "string_core",
                "subfamily_id": "kmp",
                "ok": False,
                "failure_type": "string_contract",
                "error": "String contract overgeneralized: KMP prefix table accepted Rabin-Karp evidence",
            },
            {
                "case_id": "trie_prefix_count",
                "family": "Data Structure",
                "subfamily_id": "trie_prefix",
                "ok": False,
                "failure_type": "demo_missing_deps",
                "error": "failure_type=demo_missing_deps: pop 缺少 deps 和 evidence",
            },
            {
                "case_id": "dijkstra_relaxation",
                "family": "Graph",
                "subfamily_id": "dijkstra",
                "ok": False,
                "failure_type": "process_invariant",
                "error": "第 4 步距离不满足 relax 公式，应为 7",
            },
            {
                "case_id": "weighted_graph_scene",
                "family": "Graph",
                "subfamily_id": "weighted_graph",
                "ok": False,
                "failure_type": "scene_warning",
                "error": "SceneGraph warning: 第 2 帧没有可见对象，edge binding 缺少 node",
            },
            {
                "case_id": "empty_llm_response",
                "family": "DP",
                "subfamily_id": "digit_dp",
                "ok": False,
                "failure_type": "generation",
                "error": "LLMJsonError: 模型返回空内容，无法解析 JSON",
            },
        ],
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def test_r6_classifies_failures_into_fixed_root_cause_enum():
    assert "unknown" in ROOT_CAUSES
    assert classify_failure({"failure_type": "generation", "error": "LLMJsonError: 模型返回空内容"}) == (
        "runtime_api_or_generated_code_error"
    )
    assert classify_failure({"failure_type": "demo_key_step_missing", "error": "缺少关键步骤覆盖"}) == (
        "missing_key_events_or_coverage"
    )
    assert classify_failure({"failure_type": "demo_missing_deps", "error": "缺少 deps"}) == "missing_evidence_or_deps"
    assert classify_failure({"failure_type": "process_invariant", "error": "不满足转移公式，应为 3"}) == (
        "actual_algorithm_state_mismatch"
    )
    assert classify_failure({"failure_type": "scene_warning", "error": "edge binding 缺少 node"}) == (
        "scene_object_binding_warning"
    )
    assert classify_failure({"family_id": "string_core", "failure_type": "process_invariant", "error": "KMP contract overgeneralized"}) == (
        "string_contract_overgeneralized"
    )
    assert classify_failure({"failure_type": "schema_error", "error": "ValidationError: events[0].targets Field required"}) == (
        "legacy_schema_or_target_format"
    )
    assert classify_failure({"failure_type": "validator_acceptance", "error": "validator acceptance bug"}) == (
        "validator_acceptance_bug"
    )


def test_r6_classifies_live_full_report_failure_shapes_without_overgeneralizing_generation():
    assert classify_failure({"failure_type": "generation", "error": "差分数组 失败：Array pointer contract 缺少关键更新：diff[1]"}) == (
        "missing_key_events_or_coverage"
    )
    assert classify_failure({"failure_type": "generation", "error": "第 2 步引用了不存在的索引 target：result[1]"}) == (
        "legacy_schema_or_target_format"
    )
    assert classify_failure({"failure_type": "demo_missing_reason", "error": "failure_type=demo_missing_reason: step 6 缺少 reason"}) == (
        "missing_evidence_or_deps"
    )
    assert classify_failure({"failure_type": "visual_warning", "error": "edge source 不在对象集合：node:A"}) == (
        "scene_object_binding_warning"
    )
    assert classify_failure({"failure_type": "process_invariant", "error": "Family contract 未支持的 family：union_find"}) == (
        "validator_acceptance_bug"
    )
    assert classify_failure({"failure_type": "correctness", "error": "trace 执行失败：TypeError: Tracer._add() got an unexpected keyword argument 'stage'"}) == (
        "runtime_api_or_generated_code_error"
    )
    assert classify_failure({"failure_type": "generation", "error": "快慢指针法 失败：第 2 步窗口指针跳变; 第 7 步窗口指针跳变"}) == (
        "actual_algorithm_state_mismatch"
    )
    assert classify_failure({"family": "字符串高级算法", "family_id": "string_advanced", "subfamily_id": "trie_prefix_match", "failure_type": "process_invariant", "error": "Family contract trie 缺少字符路径证据"}) == (
        "missing_evidence_or_deps"
    )


def test_r6_analyze_report_writes_json_markdown_and_csv_outputs():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        report = root / "llm_benchmark_report.json"
        output_dir = root / "failure_attribution"
        _write_sample_report(report)

        summary = analyze_report(report, output_dir)

        expected = {
            "failure_attribution.json",
            "failure_attribution.md",
            "failure_attribution_by_family.csv",
            "failure_attribution_by_root_cause.csv",
        }
        assert expected == {p.name for p in output_dir.iterdir()}
        assert summary["report_summary"]["total"] == 6
        assert summary["report_summary"]["passed"] == 1
        assert summary["report_summary"]["failed"] == 5
        assert summary["browser_summary"] == {"browser_total": 2, "browser_ok": 1, "browser_failed": 1}

        data = json.loads((output_dir / "failure_attribution.json").read_text(encoding="utf-8"))
        assert data["kind"] == "failure_attribution_report"
        assert data["root_cause_enum"] == list(ROOT_CAUSES)
        assert len(data["failures"]) == 5
        trie = next(item for item in data["failures"] if item["case_id"] == "trie_prefix_count")
        assert trie == {
            "case_id": "trie_prefix_count",
            "family": "Data Structure",
            "subfamily_id": "trie_prefix",
            "failure_type": "demo_missing_deps",
            "root_cause": "missing_evidence_or_deps",
            "error_summary": "failure_type=demo_missing_deps: pop 缺少 deps 和 evidence",
        }

        root_rows = list(csv.DictReader((output_dir / "failure_attribution_by_root_cause.csv").open(encoding="utf-8")))
        by_root = {row["root_cause"]: int(row["count"]) for row in root_rows}
        assert by_root["missing_evidence_or_deps"] == 1
        assert by_root["runtime_api_or_generated_code_error"] == 1
        assert by_root["string_contract_overgeneralized"] == 1

        family_rows = list(csv.DictReader((output_dir / "failure_attribution_by_family.csv").open(encoding="utf-8")))
        graph_row = next(row for row in family_rows if row["family"] == "Graph")
        assert int(graph_row["failed"]) == 2
        assert int(graph_row["actual_algorithm_state_mismatch"]) == 1
        assert int(graph_row["scene_object_binding_warning"]) == 1

        md = (output_dir / "failure_attribution.md").read_text(encoding="utf-8")
        assert "# LLM Failure Attribution" in md
        assert "| case_id | family | subfamily_id | failure_type | root_cause | error_summary |" in md
        assert "trie_prefix_count" in md
        assert "model_usage" in md


def test_r6_cli_accepts_report_and_output_dir_arguments():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        report = root / "llm_benchmark_report.json"
        output_dir = root / "failure_attribution"
        _write_sample_report(report)

        exit_code = main(["--report", str(report), "--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "failure_attribution.json").exists()


def run_all() -> None:
    test_r6_classifies_failures_into_fixed_root_cause_enum()
    test_r6_classifies_live_full_report_failure_shapes_without_overgeneralizing_generation()
    test_r6_analyze_report_writes_json_markdown_and_csv_outputs()
    test_r6_cli_accepts_report_and_output_dir_arguments()


if __name__ == "__main__":
    run_all()
    print("failure_attribution: PASS")
