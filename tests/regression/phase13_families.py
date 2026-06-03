"""DSL-era regression tests for the legacy Phase 13 process layer.

The original Phase 13 suite verified thousands of lines of family-specific
process validators under ``algolab.verification.process_families``.  The DSL
architecture intentionally removed that package: traces now come from executed
DSL code, and correctness is gated by solve/trace/verifier agreement plus
schema/scene validation.  These tests keep the old public test entry points but
assert the new compatibility contract.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.process_validator import (
    ALGORITHM_LEVEL,
    CORE_LEVEL,
    ProcessFamilyRegistration,
    process_failure_type_for_message,
    process_validation_profile_for_family,
    process_validation_profile_for_trace,
    process_validation_registry,
    validate_process,
)
from tests.benchmark_cases import BENCHMARK_CASE_METADATA, benchmark_cases
from tests.regression.helpers import REPO_ROOT


EXPECTED_CASE_COUNT = 71
EXPECTED_SAMPLE_COUNT = 259
EXPECTED_CASE_ORDER_SHA = "cb499d8ce95119cddf3d15e7be76cb73061ff06782343fcff3febfb463c191c2"


def _profiles() -> dict[str, ProcessFamilyRegistration]:
    return {profile.family: profile for profile in process_validation_registry()}


def _benchmark_family_ids() -> set[str]:
    return {metadata["family_id"] for metadata in BENCHMARK_CASE_METADATA.values()}


def _sample_count_for_family(family_id: str) -> int:
    return sum(
        len(case.samples)
        for case in benchmark_cases()
        if BENCHMARK_CASE_METADATA[case.id]["family_id"] == family_id
    )


def _case_ids_for_family(family_id: str) -> set[str]:
    return {
        case.id
        for case in benchmark_cases()
        if BENCHMARK_CASE_METADATA[case.id]["family_id"] == family_id
    }


def _assert_dsl_profiles_cover(family_ids: set[str]) -> None:
    profiles = _profiles()
    missing = family_ids - set(profiles)
    assert missing == set(), missing
    for family_id in family_ids:
        profile = profiles[family_id]
        assert profile.status == "strong", profile
        assert profile.level == ALGORITHM_LEVEL, profile
        assert "DSL-era" in profile.coverage_rule, profile.coverage_rule
        assert profile.failure_type == "process_invariant", profile


def _minimal_trace(algorithm: str = "二维 DP") -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": algorithm,
            "input_data": {"nums": [1]},
            "result": 1,
            "pseudocode": ["execute DSL trace"],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1]},
                    "reason": "创建输入数组。",
                    "code_line": 1,
                }
            ],
        }
    )


def _assert_validate_process_is_dsl_sanity_check() -> None:
    errors, warnings = validate_process(_minimal_trace())
    assert errors == []
    assert warnings == []

    errors, warnings = validate_process("not a trace")  # type: ignore[arg-type]
    assert errors and "SemanticTrace" in errors[0]
    assert warnings == []

    try:
        validate_process(_minimal_trace(), levels=["unknown"])  # type: ignore[list-item]
    except ValueError as exc:
        assert "未知 process invariant 层级" in str(exc)
    else:
        raise AssertionError("validate_process should reject unknown invariant levels")


def test_phase13_long_files_are_split_without_changing_public_contracts():
    import algolab.verification.process_validator as process_validator
    import tests.benchmark_cases as benchmark_cases_module
    import tests.benchmark_regression as benchmark_regression_module

    expected_modules = (
        "algolab.verification.process_validator",
        "algolab.runtime.dsl",
        "algolab.runtime.sandbox",
        "algolab.compiler.object_resolver",
        "tests.benchmark_families.array_pointer",
        "tests.benchmark_families.dp",
        "tests.benchmark_families.graph",
        "tests.benchmark_families.hash_sort_linked_greedy",
        "tests.benchmark_families.string",
        "tests.benchmark_families.tree_range_math",
        "tests.benchmark_families.expansion",
        "tests.regression.trace_contracts",
        "tests.regression.phase13_families",
        "tests.regression.benchmark_metadata",
        "tests.regression.reports_and_gates",
        "tests.tracer_regression",
    )
    for module_name in expected_modules:
        importlib.import_module(module_name)

    assert not (REPO_ROOT / "algolab/verification/process_families").exists()

    cases = benchmark_cases()
    case_ids = [case.id for case in cases]
    assert len(cases) == EXPECTED_CASE_COUNT
    assert sum(len(case.samples) for case in cases) == EXPECTED_SAMPLE_COUNT
    assert (
        __import__("hashlib").sha256("\n".join(case_ids).encode()).hexdigest()
        == EXPECTED_CASE_ORDER_SHA
    )

    assert process_validator.validate_process
    assert process_validator.process_validation_registry
    assert benchmark_cases_module.benchmark_cases
    assert benchmark_cases_module.UNIQUE_PATHS_CODE
    assert benchmark_cases_module.UNIQUE_PATHS_TRACKER
    assert benchmark_regression_module.run_all

    line_limits = {
        "algolab/verification/process_validator.py": 900,
        "tests/benchmark_cases.py": 1200,
        "tests/benchmark_regression.py": 500,
    }
    for relative_path, max_lines in line_limits.items():
        line_count = len((REPO_ROOT / relative_path).read_text(encoding="utf-8").splitlines())
        assert line_count < max_lines, (relative_path, line_count, max_lines)


def test_phase13_array_pointer_validator_rejects_process_errors_and_tracks_samples():
    _assert_dsl_profiles_cover({"array_pointer", "binary_search"})
    assert _sample_count_for_family("array_pointer") >= 18
    assert _case_ids_for_family("array_pointer") >= {
        "sliding_window_min_len",
        "prefix_sum_range",
        "fast_slow_cycle",
    }
    assert process_validation_profile_for_family("数组指针 / 窗口 / 前缀").family == "array_pointer"
    assert process_validation_profile_for_family("二分").family == "binary_search"
    _assert_validate_process_is_dsl_sanity_check()


def test_phase13_dp_validator_expands_family_core_samples_and_rejects_digit_dp_errors():
    _assert_dsl_profiles_cover({"dp_1d", "dp_2d", "dp_core"})
    assert _sample_count_for_family("dp_core") >= 24
    assert _case_ids_for_family("dp_core") >= {
        "complete_knapsack_coin_change",
        "lcs_length",
        "digit_dp_no_seven",
    }
    assert process_validation_profile_for_family("二维 DP").family == "dp_2d"
    assert process_validation_profile_for_family("DP 核心扩展").family == "dp_core"


def test_phase13_graph_validator_expands_core_shortest_mst_samples_and_rejects_process_errors():
    _assert_dsl_profiles_cover({"basic_graph", "shortest_path_mst"})
    assert _sample_count_for_family("basic_graph") >= 15
    assert _sample_count_for_family("shortest_path_mst") >= 18
    assert _case_ids_for_family("shortest_path_mst") >= {
        "dijkstra_shortest_path",
        "bellman_ford_shortest_path",
        "kruskal_mst_weight",
    }
    assert process_validation_profile_for_family("BFS/DFS 基础图").family == "basic_graph"
    assert process_validation_profile_for_family("最短路 / MST").family == "shortest_path_mst"


def test_phase13_string_validator_expands_core_samples_and_rejects_process_errors():
    _assert_dsl_profiles_cover({"string_advanced", "trie"})
    assert _sample_count_for_family("string_advanced") >= 18
    assert _case_ids_for_family("string_advanced") >= {
        "kmp",
        "rabin_karp",
        "manacher",
    }
    assert process_validation_profile_for_family("字符串高级算法").family == "string_advanced"
    assert process_validation_profile_for_family("Trie").family == "trie"


def test_phase13_tree_backtracking_trie_heap_validator_expands_samples_and_rejects_process_errors():
    family_ids = {
        "tree_bst_lca",
        "tree_dp",
        "backtracking_recursion",
        "trie",
        "heap_topk_huffman",
        "union_find",
        "monotonic_stack",
    }
    _assert_dsl_profiles_cover(family_ids)
    assert _case_ids_for_family("tree_bst_lca") >= {
        "binary_tree_inorder",
        "lca",
        "tree_diameter",
    }
    assert _case_ids_for_family("backtracking_recursion") >= {"permutations", "permutations_expansion"}
    assert process_validation_profile_for_family("树 / BST / LCA").family == "tree_bst_lca"
    assert process_validation_profile_for_family("堆 / TopK / Huffman").family == "heap_topk_huffman"
    assert process_validation_profile_for_family("并查集").family == "union_find"


def test_phase13_hash_sorting_linked_list_greedy_validator_upgrades_profiles_and_rejects_process_errors():
    _assert_dsl_profiles_cover({"hash_map", "sorting", "linked_list_cache", "greedy"})
    assert _case_ids_for_family("hash_map") == {"two_sum", "subarray_sum_equals_k"}
    assert "merge_intervals" in _case_ids_for_family("greedy")
    assert _sample_count_for_family("hash_map") >= 8
    assert process_validation_profile_for_family("哈希表 / map").family == "hash_map"
    assert process_validation_profile_for_family("排序").family == "sorting"
    assert process_validation_profile_for_family("链表与缓存").family == "linked_list_cache"
    assert process_validation_profile_for_family("贪心").family == "greedy"


def test_phase13_math_geometry_range_advanced_graph_validator_upgrades_geometry_and_preserves_profiles():
    _assert_dsl_profiles_cover({"math_bit", "geometry_sweep", "range_structure", "advanced_graph"})
    assert _case_ids_for_family("range_structure") >= {
        "fenwick_tree_prefix_sum",
        "segment_tree_range_sum",
        "sparse_table_range_min",
    }
    assert _case_ids_for_family("advanced_graph") >= {
        "tarjan_scc",
        "edmonds_karp",
        "bipartite_matching",
    }
    assert process_validation_profile_for_family("数学与位运算").family == "math_bit"
    assert process_validation_profile_for_family("几何 / 扫描线").family == "geometry_sweep"
    assert process_validation_profile_for_family("图高级").family == "advanced_graph"

    uncovered = process_validation_profile_for_family("未注册算法族")
    assert uncovered.family == "uncovered"
    assert uncovered.status == "fallback"
    assert uncovered.level == CORE_LEVEL

    trace_profile = process_validation_profile_for_trace(_minimal_trace("哈希表 / map"))
    assert trace_profile.family == "hash_map"
    assert process_failure_type_for_message("failure_type=process_invariant: bad step") == "process_invariant"
    assert process_failure_type_for_message("trace coverage too low") == "coverage_error"
    assert process_failure_type_for_message("未注册算法族") == "process_uncovered"


def test_phase13_process_registry_covers_all_benchmark_families():
    _assert_dsl_profiles_cover(_benchmark_family_ids())
