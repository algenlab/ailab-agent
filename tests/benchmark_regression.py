"""Compatibility entry point for split benchmark regression tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.regression.helpers import benchmark_coverage_artifact, materialize_case, spec_for_case
from tests.regression.trace_contracts import *
from tests.regression.phase13_families import *
from tests.regression.benchmark_metadata import *
from tests.regression.reports_and_gates import *

def run_all():
    test_phase13_long_files_are_split_without_changing_public_contracts()
    test_phase12_dp_trace_contract_accepts_representative_subfamilies()
    test_phase12_dp_trace_contract_rejects_missing_deps_init_answer_and_key_updates()
    test_phase12_graph_trace_contract_accepts_representative_submodes()
    test_phase12_graph_trace_contract_rejects_submode_process_errors()
    test_phase12_family_trace_contract_accepts_string_tree_backtracking_and_structures()
    test_phase12_family_trace_contract_rejects_missing_process_evidence()
    test_phase13_array_pointer_validator_rejects_process_errors_and_tracks_samples()
    test_phase13_dp_validator_expands_family_core_samples_and_rejects_digit_dp_errors()
    test_phase13_graph_validator_expands_core_shortest_mst_samples_and_rejects_process_errors()
    test_phase13_string_validator_expands_core_samples_and_rejects_process_errors()
    test_phase13_tree_backtracking_trie_heap_validator_expands_samples_and_rejects_process_errors()
    test_phase13_hash_sorting_linked_list_greedy_validator_upgrades_profiles_and_rejects_process_errors()
    test_phase13_math_geometry_range_advanced_graph_validator_upgrades_geometry_and_preserves_profiles()
    test_benchmark_cases_are_multi_input_release_ready()
    test_process_validator_rejects_missing_key_step_coverage_for_small_traces()
    test_process_validator_rejects_bad_string_algorithm_tables()
    test_benchmark_cases_expose_phase10_metadata()
    test_benchmark_cases_expose_phase11_oracle_metadata_and_independent_examples()
    test_convex_hull_trace_exposes_scan_phases_and_pop_steps()
    test_phase7_string_algorithms_have_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_tree_recursion_aggregates()
    test_phase7_tree_recursion_group_has_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_range_structure_tables()
    test_phase7_range_structures_have_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_math_bit_invariants()
    test_phase7_math_bit_group_has_benchmarks_visual_state_and_examples()
    test_process_validator_rejects_bad_phase7_advanced_graph_invariants()
    test_phase7_advanced_graph_group_has_benchmarks_visual_state_and_examples()
    test_contract_tests_block_bad_solve()
    test_llm_benchmark_request_uses_problem_and_expected()
    test_llm_benchmark_sample_selection_and_failure_classification(Path(tempfile.gettempdir()))
    test_llm_benchmark_family_split_selection_and_summary(Path(tempfile.gettempdir()))
    test_phase15_unseen_family_cases_are_independent_and_reported(Path(tempfile.gettempdir()))
    test_benchmark_report_summarizes_process_registry_failure_types(Path(tempfile.gettempdir()))
    test_phase15_family_repair_context_and_prompt_distinguish_failure_categories()
    test_demo_readiness_schema_passes_family_core_and_blocks_missing_demo_evidence()
    test_demo_readiness_phase14_covers_each_strong_process_profile()
    test_demo_readiness_phase14_family_rules_reject_group_specific_gaps()
    test_demo_readiness_phase14_accepts_topological_sort_indegree_edge_deps()
    test_demo_readiness_phase14_does_not_treat_bipartite_graph_as_binary_search()
    test_demo_readiness_phase14_accepts_kruskal_mst_union_find_state()
    test_demo_readiness_phase14_accepts_empty_pattern_string_short_path()
    test_demo_readiness_phase14_accepts_pattern_longer_than_text_short_path()
    test_demo_readiness_failure_types_enter_llm_and_evaluation_reports(Path(tempfile.gettempdir()))
    test_llm_benchmark_phase_timing_helpers()
    test_llm_json_and_spec_normalization_helpers()
    test_existing_benchmark_html_report_helper(Path(tempfile.gettempdir()))
    test_benchmark_html_checker_resolves_required_phase8_cases(Path(tempfile.gettempdir()))
    test_demo_dashboard_selection_defaults_to_curated_showcase()
    test_runtime_capabilities_prompt_context_is_json()

    with tempfile.TemporaryDirectory() as d:
        test_llm_client_reads_local_api_settings_without_committing_key(Path(d))
        test_benchmark_aggregate_artifact(Path(d))
        test_demo_dashboard_writes_bundle_and_index(Path(d))
        test_demo_dashboard_groups_by_family_and_gate_layer(Path(d))
        test_demo_dashboard_exposes_phase14_family_layer_statuses_and_reports(Path(d))
        test_evaluation_manifest_covers_phase10_datasets(Path(d))
        test_evaluation_manifest_exports_phase10_case_metadata_and_summaries(Path(d))
        test_evaluation_report_exports_phase10_metrics_and_core_tables(Path(d))
        test_evaluation_report_summarizes_baseline_ablation_conditions(Path(d))
        test_reproducibility_package_records_environment_commands_samples_and_modes(Path(d))
        test_v1_release_gate_report_records_release_requirements(Path(d))
        test_family_capabilities_registry_covers_existing_benchmark_families(Path(d))
        test_family_release_gate_reports_layered_family_readiness_and_strong_fallback_failures(Path(d))
        test_phase16_degradation_policy_enters_evaluation_reports_and_artifact_debug(Path(d))
        test_phase16_core_family_sample_window_and_gates_are_ready()
        test_phase16_expansion_family_samples_and_dashboard_pages_are_ready(Path(d))
        test_property_benchmark_generates_seeded_robustness_report(Path(d))
        test_boundary_case_registry_reports_family_core_coverage_and_strong_upgrade_gate(Path(d))
    test_creative_renderer_contains_theme_controls_and_stage()


if __name__ == "__main__":
    run_all()
    print("benchmark_regression: PASS")
