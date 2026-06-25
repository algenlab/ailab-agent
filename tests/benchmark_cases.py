"""Deterministic real-problem benchmark cases.

These cases exercise the production pipeline without calling the LLM.  Each
case provides executable solve/trace/verifier code and several inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class BenchmarkInput:
    input_data: dict[str, Any]
    expected: Any


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    title: str
    problem: str
    family: str
    input_contract: str
    variant_name: str
    strategy: str
    time_complexity: str
    space_complexity: str
    expected_layouts: tuple[str, ...]
    code: str
    tracker_code: str
    verifier_code: str
    samples: tuple[BenchmarkInput, ...]

    @property
    def family_id(self) -> str:
        return _metadata_for_case(self.id)["family_id"]

    @property
    def subfamily_id(self) -> str:
        return _metadata_for_case(self.id)["subfamily_id"]

    @property
    def gate_layer(self) -> str:
        return _metadata_for_case(self.id)["gate_layer"]

    @property
    def support_level(self) -> str:
        return _metadata_for_case(self.id)["support_level"]

    @property
    def process_profile(self) -> str:
        return _metadata_for_case(self.id)["process_profile"]

    @property
    def oracle_type(self) -> str:
        return _metadata_for_case(self.id)["oracle_type"]

    @property
    def oracle_risk(self) -> str:
        metadata = _metadata_for_case(self.id)
        if metadata.get("oracle_risk"):
            return metadata["oracle_risk"]
        if not self.verifier_code.strip():
            return "missing_verifier"
        if _verifier_matches_solve_structure(self.code, self.verifier_code):
            return "verifier_matches_solve"
        return "none"

    @property
    def oracle_notes(self) -> str:
        metadata = _metadata_for_case(self.id)
        if metadata.get("oracle_notes"):
            return metadata["oracle_notes"]
        if self.oracle_risk == "missing_verifier":
            return "缺少 verifier，不能作为 deterministic answer gate 证据。"
        if self.oracle_risk == "verifier_matches_solve":
            reference = self.oracle_reference or "missing oracle_reference"
            return f"verifier 与 solve 结构过于相同，不能作为 strong family 的唯一答案正确性证据；参考 {reference}。"
        return "Oracle matches the declared oracle_type."

    @property
    def oracle_reference(self) -> str:
        return _metadata_for_case(self.id).get("oracle_reference", "")

    @property
    def demo_required(self) -> bool:
        return bool(_metadata_for_case(self.id)["demo_required"])


BENCHMARK_CASE_METADATA: dict[str, dict[str, Any]] = {
    "house_robber": {
        "family_id": "dp_1d",
        "subfamily_id": "house_robber",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "binary_search": {
        "family_id": "binary_search",
        "subfamily_id": "closed_interval_search",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "binary_search",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "binary_answer_sqrt": {
        "family_id": "array_pointer",
        "subfamily_id": "binary_answer",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "array_pointer",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "two_pointer_pair_sum": {
        "family_id": "array_pointer",
        "subfamily_id": "two_pointer",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "array_pointer",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "sliding_window_min_len": {
        "family_id": "array_pointer",
        "subfamily_id": "sliding_window",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "array_pointer",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "prefix_sum_range": {
        "family_id": "array_pointer",
        "subfamily_id": "prefix_sum",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "array_pointer",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "difference_array_range_add": {
        "family_id": "array_pointer",
        "subfamily_id": "difference_array",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "array_pointer",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "fast_slow_cycle": {
        "family_id": "array_pointer",
        "subfamily_id": "fast_slow",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "array_pointer",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "unique_paths": {
        "family_id": "dp_2d",
        "subfamily_id": "unique_paths",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "closed_form",
        "demo_required": True,
    },
    "knapsack_01_subset_sum": {
        "family_id": "dp_core",
        "subfamily_id": "knapsack_01",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "complete_knapsack_coin_change": {
        "family_id": "dp_core",
        "subfamily_id": "complete_knapsack",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "bounded_knapsack_max_value": {
        "family_id": "dp_core",
        "subfamily_id": "bounded_knapsack",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "lcs_length": {
        "family_id": "dp_core",
        "subfamily_id": "lcs",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "edit_distance": {
        "family_id": "dp_core",
        "subfamily_id": "edit_distance",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "interval_dp_merge_stones": {
        "family_id": "dp_core",
        "subfamily_id": "interval_dp",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "state_compression_tsp": {
        "family_id": "dp_core",
        "subfamily_id": "state_compression",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "digit_dp_no_seven": {
        "family_id": "dp_core",
        "subfamily_id": "digit_dp",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "graph_bfs": {
        "family_id": "basic_graph",
        "subfamily_id": "bfs_shortest_layers",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "bfs",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "graph_dfs_traversal": {
        "family_id": "basic_graph",
        "subfamily_id": "dfs_traversal",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "bfs",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.graph_dfs_reference",
        "demo_required": True,
    },
    "graph_connected_components": {
        "family_id": "basic_graph",
        "subfamily_id": "connected_components",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "bfs",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.connected_components_reference",
        "demo_required": True,
    },
    "graph_topological_sort": {
        "family_id": "basic_graph",
        "subfamily_id": "topological_sort",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "bfs",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.topological_order_property_reference",
        "demo_required": True,
    },
    "graph_bipartite_coloring": {
        "family_id": "basic_graph",
        "subfamily_id": "bipartite_coloring",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "bfs",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.bipartite_coloring_reference",
        "demo_required": True,
    },
    "dijkstra_shortest_path": {
        "family_id": "shortest_path_mst",
        "subfamily_id": "dijkstra",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "shortest_path_mst",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.dijkstra_reference",
        "demo_required": True,
    },
    "bellman_ford_shortest_path": {
        "family_id": "shortest_path_mst",
        "subfamily_id": "bellman_ford",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "shortest_path_mst",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.bellman_ford_reference",
        "demo_required": True,
    },
    "floyd_warshall_all_pairs": {
        "family_id": "shortest_path_mst",
        "subfamily_id": "floyd_warshall",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "shortest_path_mst",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.floyd_warshall_reference",
        "demo_required": True,
    },
    "zero_one_bfs_shortest_path": {
        "family_id": "shortest_path_mst",
        "subfamily_id": "zero_one_bfs",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "shortest_path_mst",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.zero_one_bfs_reference",
        "demo_required": True,
    },
    "kruskal_mst_weight": {
        "family_id": "shortest_path_mst",
        "subfamily_id": "kruskal_mst",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "shortest_path_mst",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.kruskal_mst_reference",
        "demo_required": True,
    },
    "kmp": {
        "family_id": "string_advanced",
        "subfamily_id": "kmp",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "string",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "rabin_karp": {
        "family_id": "string_advanced",
        "subfamily_id": "rabin_karp",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "string",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "z_algorithm": {
        "family_id": "string_advanced",
        "subfamily_id": "z_algorithm",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "string",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "manacher": {
        "family_id": "string_advanced",
        "subfamily_id": "manacher",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "string",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "string_sliding_window_unique": {
        "family_id": "string_advanced",
        "subfamily_id": "string_sliding_window",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "string",
        "oracle_type": "bruteforce",
        "oracle_reference": "tests.oracles.string_unique_window_reference",
        "demo_required": True,
    },
    "trie_prefix_match_string": {
        "family_id": "string_advanced",
        "subfamily_id": "trie_prefix_match",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "string",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.trie_prefix_count_reference",
        "demo_required": True,
    },
    "two_sum": {
        "family_id": "hash_map",
        "subfamily_id": "two_sum",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "hash",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "subarray_sum_equals_k": {
        "family_id": "hash_map",
        "subfamily_id": "prefix_sum_count",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "hash",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "daily_temperatures": {
        "family_id": "monotonic_stack",
        "subfamily_id": "daily_temperatures",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "monotonic_stack",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "insertion_sort": {
        "family_id": "sorting",
        "subfamily_id": "insertion_sort",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "sorting",
        "oracle_type": "property",
        "demo_required": True,
    },
    "reverse_linked_list": {
        "family_id": "linked_list_cache",
        "subfamily_id": "reverse_linked_list",
        "gate_layer": "family_core",
        "support_level": "medium",
        "process_profile": "linked_list",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "jump_game": {
        "family_id": "greedy",
        "subfamily_id": "jump_game",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "greedy",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "merge_intervals": {
        "family_id": "greedy",
        "subfamily_id": "merge_intervals",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "greedy",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "binary_tree_inorder": {
        "family_id": "tree_bst_lca",
        "subfamily_id": "inorder_traversal",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "tree",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.tree_inorder_reference",
        "demo_required": True,
    },
    "lca": {
        "family_id": "tree_bst_lca",
        "subfamily_id": "lca",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "tree",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "tree_diameter": {
        "family_id": "tree_bst_lca",
        "subfamily_id": "tree_diameter",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "tree",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.tree_diameter_reference",
        "demo_required": True,
    },
    "tree_max_independent_set": {
        "family_id": "tree_dp",
        "subfamily_id": "tree_max_independent_set",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "dp",
        "oracle_type": "bruteforce",
        "oracle_reference": "tests.oracles.tree_independent_set_bruteforce",
        "demo_required": True,
    },
    "kth_largest": {
        "family_id": "heap_topk_huffman",
        "subfamily_id": "topk_min_heap",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "heap",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "trie_prefix": {
        "family_id": "trie",
        "subfamily_id": "prefix_count",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "trie",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "provinces": {
        "family_id": "union_find",
        "subfamily_id": "connected_components",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "union_find",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "permutations": {
        "family_id": "backtracking_recursion",
        "subfamily_id": "permutations",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "backtracking",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "convex_hull": {
        "family_id": "geometry_sweep",
        "subfamily_id": "convex_hull",
        "gate_layer": "family_core",
        "support_level": "medium_plus",
        "process_profile": "geometry",
        "oracle_type": "property",
        "demo_required": True,
    },
    "segment_tree_range_sum": {
        "family_id": "range_structure",
        "subfamily_id": "segment_tree",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "range_structure",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "fenwick_tree_prefix_sum": {
        "family_id": "range_structure",
        "subfamily_id": "fenwick_tree",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "range_structure",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.range_sum_after_delta_reference",
        "demo_required": True,
    },
    "sparse_table_range_min": {
        "family_id": "range_structure",
        "subfamily_id": "sparse_table",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "range_structure",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.range_min_direct_reference",
        "demo_required": True,
    },
    "gcd_euclid": {
        "family_id": "math_bit",
        "subfamily_id": "gcd",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "math_bit",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.gcd_reference",
        "demo_required": True,
    },
    "fast_power_mod": {
        "family_id": "math_bit",
        "subfamily_id": "fast_power",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "math_bit",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "sieve_primes": {
        "family_id": "math_bit",
        "subfamily_id": "sieve",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "math_bit",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "combinations_pascal": {
        "family_id": "math_bit",
        "subfamily_id": "combinations",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "math_bit",
        "oracle_type": "closed_form",
        "demo_required": True,
    },
    "bitmask_subsets": {
        "family_id": "math_bit",
        "subfamily_id": "bitmask",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "math_bit",
        "oracle_type": "property",
        "oracle_reference": "tests.oracles.bitmask_subset_property_reference",
        "demo_required": True,
    },
    "lowbit_decomposition": {
        "family_id": "math_bit",
        "subfamily_id": "lowbit",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "math_bit",
        "oracle_type": "property",
        "oracle_reference": "tests.oracles.lowbit_property_reference",
        "demo_required": True,
    },
    "tarjan_scc": {
        "family_id": "advanced_graph",
        "subfamily_id": "tarjan_scc",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "advanced_graph",
        "oracle_type": "independent_reference",
        "oracle_risk": "verifier_matches_solve",
        "oracle_notes": "当前 verifier 由 solve 代码替换函数名生成，结构过于相同；strong 证据必须同时依赖 process validator 和独立 oracle 示例。",
        "oracle_reference": "tests.oracles.advanced_graph_oracle_examples",
        "demo_required": True,
    },
    "articulation_bridges": {
        "family_id": "advanced_graph",
        "subfamily_id": "articulation_bridges",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "advanced_graph",
        "oracle_type": "independent_reference",
        "oracle_risk": "verifier_matches_solve",
        "oracle_notes": "当前 verifier 由 solve 代码替换函数名生成，结构过于相同；strong 证据必须同时依赖 process validator 和独立 oracle 示例。",
        "oracle_reference": "tests.oracles.advanced_graph_oracle_examples",
        "demo_required": True,
    },
    "bipartite_matching": {
        "family_id": "advanced_graph",
        "subfamily_id": "bipartite_matching",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "advanced_graph",
        "oracle_type": "bruteforce",
        "oracle_risk": "verifier_matches_solve",
        "oracle_notes": "当前 verifier 由 solve 代码替换函数名生成，结构过于相同；strong 证据必须同时依赖 process validator 和独立 oracle 示例。",
        "oracle_reference": "tests.oracles.advanced_graph_oracle_examples",
        "demo_required": True,
    },
    "edmonds_karp": {
        "family_id": "advanced_graph",
        "subfamily_id": "edmonds_karp",
        "gate_layer": "family_core",
        "support_level": "strong",
        "process_profile": "advanced_graph",
        "oracle_type": "independent_reference",
        "oracle_risk": "verifier_matches_solve",
        "oracle_notes": "当前 verifier 由 solve 代码替换函数名生成，结构过于相同；strong 证据必须同时依赖 process validator 和独立 oracle 示例。",
        "oracle_reference": "tests.oracles.advanced_graph_oracle_examples",
        "demo_required": True,
    },
    "jump_game_expansion": {
        "family_id": "greedy",
        "subfamily_id": "jump_game",
        "gate_layer": "expansion",
        "support_level": "medium_plus",
        "process_profile": "greedy",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "dijkstra_shortest_path_expansion": {
        "family_id": "shortest_path_mst",
        "subfamily_id": "dijkstra",
        "gate_layer": "expansion",
        "support_level": "strong",
        "process_profile": "shortest_path_mst",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.dijkstra_reference",
        "demo_required": True,
    },
    "kth_largest_expansion": {
        "family_id": "heap_topk_huffman",
        "subfamily_id": "topk_min_heap",
        "gate_layer": "expansion",
        "support_level": "medium_plus",
        "process_profile": "heap",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "trie_prefix_expansion": {
        "family_id": "trie",
        "subfamily_id": "prefix_count",
        "gate_layer": "expansion",
        "support_level": "medium_plus",
        "process_profile": "trie",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "permutations_expansion": {
        "family_id": "backtracking_recursion",
        "subfamily_id": "permutations",
        "gate_layer": "expansion",
        "support_level": "medium_plus",
        "process_profile": "backtracking",
        "oracle_type": "bruteforce",
        "demo_required": True,
    },
    "gcd_euclid_expansion": {
        "family_id": "math_bit",
        "subfamily_id": "gcd",
        "gate_layer": "expansion",
        "support_level": "strong",
        "process_profile": "math_bit",
        "oracle_type": "independent_reference",
        "oracle_reference": "tests.oracles.gcd_reference",
        "demo_required": True,
    },
    "convex_hull_expansion": {
        "family_id": "geometry_sweep",
        "subfamily_id": "convex_hull",
        "gate_layer": "expansion",
        "support_level": "medium_plus",
        "process_profile": "geometry",
        "oracle_type": "property",
        "demo_required": True,
    },
    "reverse_linked_list_expansion": {
        "family_id": "linked_list_cache",
        "subfamily_id": "reverse_linked_list",
        "gate_layer": "expansion",
        "support_level": "medium",
        "process_profile": "linked_list",
        "oracle_type": "independent_reference",
        "demo_required": True,
    },
    "edmonds_karp_expansion": {
        "family_id": "advanced_graph",
        "subfamily_id": "edmonds_karp",
        "gate_layer": "expansion",
        "support_level": "strong",
        "process_profile": "advanced_graph",
        "oracle_type": "independent_reference",
        "oracle_risk": "verifier_matches_solve",
        "oracle_notes": "当前 verifier 由 solve 代码替换函数名生成，结构过于相同；strong 证据必须同时依赖 process validator 和独立 oracle 示例。",
        "oracle_reference": "tests.oracles.advanced_graph_oracle_examples",
        "demo_required": True,
    },
}


def _metadata_for_case(case_id: str) -> dict[str, Any]:
    try:
        return BENCHMARK_CASE_METADATA[case_id]
    except KeyError as exc:
        raise KeyError(f"Benchmark case {case_id!r} is missing Phase 10 metadata") from exc


def _verifier_matches_solve_structure(code: str, verifier_code: str) -> bool:
    def normalize(value: str) -> str:
        return (
            value.replace("def solve(input_data):", "def _oracle(input_data):")
            .replace("def verify(input_data):", "def _oracle(input_data):")
            .strip()
        )

    return bool(code.strip()) and normalize(code) == normalize(verifier_code)


from tests.benchmark_families import array_pointer, dp, expansion, graph, hash_sort_linked_greedy, string, tree_range_math
from tests.benchmark_families.dp import UNIQUE_PATHS_CODE, UNIQUE_PATHS_TRACKER


LEETCODE_STYLE_PROBLEM_OVERRIDES: dict[str, str] = {
    "house_robber": (
        "LeetCode 198 风格：一排房屋沿街排列，nums[i] 表示第 i 间房里的金额。"
        "如果同一晚偷了相邻房屋就会触发警报；返回在不触发警报的前提下能拿到的最高金额。"
    ),
    "binary_search": (
        "LeetCode 704 风格：给定按升序排列且不含重复元素的整数数组 nums，以及目标值 target。"
        "在数组中查找 target，找到则返回它的下标；如果不存在，返回 -1。"
    ),
    "binary_answer_sqrt": (
        "LeetCode 69 风格：给定非负整数 n，计算并返回 n 的算术平方根向下取整后的整数。"
        "不能依赖浮点误差，适合用二分答案不断缩小可行区间。"
    ),
    "two_pointer_pair_sum": (
        "LeetCode 167 风格的本地版本：给定升序数组 nums 和目标值 target，"
        "用左右指针寻找一对元素使和等于 target；返回这对元素的 0-based 下标，不存在则返回空数组。"
    ),
    "sliding_window_min_len": (
        "LeetCode 209 风格：给定正整数数组 nums 和目标值 target，"
        "找出总和至少为 target 的最短连续子数组长度；如果不存在这样的子数组，返回 0。"
    ),
    "unique_paths": (
        "在一座智能仓库里，巡检机器人需要从 m x n 货架网格的左上角充电点出发，"
        "每一步只能向右或向下移动到相邻通道。计算它到达右下角打包站一共有多少条不同路线。"
    ),
    "knapsack_01_subset_sum": (
        "LeetCode 416 风格：给定一个只包含正整数的数组 nums，判断能否把这些数字分成两个子集，"
        "使两个子集的元素和完全相同。"
    ),
    "complete_knapsack_coin_change": (
        "LeetCode 322 风格：给定硬币面额 coins 和目标金额 amount，每种硬币都可以使用任意多次。"
        "返回凑成 amount 所需的最少硬币数；如果无法凑出该金额，返回 -1。"
    ),
    "lcs_length": (
        "LeetCode 1143 风格：给定两个字符串 text1 和 text2，"
        "返回它们最长公共子序列的长度；子序列可以不连续，但相对顺序必须保持不变。"
    ),
    "edit_distance": (
        "LeetCode 72 风格：给定 word1 和 word2，允许插入、删除、替换一个字符。"
        "返回把 word1 转换成 word2 所需的最少操作次数。"
    ),
    "kmp": (
        "LeetCode 28 风格：给定文本 text 和模式串 pattern，返回 pattern 在 text 中第一次出现的起始下标。"
        "如果不存在返回 -1；如果 pattern 为空返回 0。这里希望展示 KMP 前缀表和失配回退过程。"
    ),
    "string_sliding_window_unique": (
        "LeetCode 3 风格：给定字符串 text，返回不含重复字符的最长子串长度。"
        "窗口需要在遇到重复字符时收缩，并持续记录当前最优长度。"
    ),
    "two_sum": (
        "在订单配货系统中，nums[i] 表示第 i 个货位上可直接拣出的商品数量，"
        "订单还缺 target 件同类商品。找到两个不同货位，使它们的数量之和正好为 target，"
        "返回这两个货位的 0-based 下标；本地样例允许不存在答案，此时返回空数组。"
    ),
    "subarray_sum_equals_k": (
        "LeetCode 560 风格：给定整数数组 nums 和整数 k，统计数组中和为 k 的连续子数组个数。"
        "数组中可以有正数、负数和 0，因此适合用前缀和计数。"
    ),
    "reverse_linked_list": (
        "LeetCode 206 风格的本地版本：给定链表节点值序列 values，按顺序构成一条单链表。"
        "用迭代指针逐个反转 next 方向，并返回反转后的节点值序列。"
    ),
    "jump_game": (
        "LeetCode 55 风格：给定非负整数数组 nums，nums[i] 表示从位置 i 最多可以向前跳多少步。"
        "判断从下标 0 出发是否能够到达最后一个下标。"
    ),
    "merge_intervals": (
        "会议中心收到多批场地占用申请，intervals 中每个闭区间表示一个房间在时间轴上的占用窗口。"
        "把所有相互重叠或首尾相接的占用窗口合并，返回按起点排序、互不重叠的最终占用区间列表。"
    ),
    "daily_temperatures": (
        "农业温室有一串未来每日温度预报 temperatures，管理员想知道每一天之后还要等几天才会出现更高温度，"
        "以便安排自动通风和遮阳策略。如果之后都不会升温，则该位置为 0。"
    ),
    "binary_tree_inorder": (
        "LeetCode 94 风格的本地版本：给定一棵二叉树 tree，返回节点 id 的中序遍历序列。"
        "tree 由 nodes 和父子 edges 表示，同一父节点的子节点顺序对应左、右子树。"
    ),
    "lca": (
        "LeetCode 236 风格的本地版本：给定一棵二叉树 tree，以及两个节点 p 和 q。"
        "返回同时作为 p、q 祖先且深度最大的节点 id。tree 使用 nodes 和父子 edges 表示。"
    ),
    "tree_diameter": (
        "LeetCode 543 风格的本地版本：给定一棵二叉树 tree，返回任意两个节点之间最长路径的边数。"
        "路径可以不经过根节点，适合后序计算子树高度并更新直径。"
    ),
    "kth_largest": (
        "LeetCode 215 风格：给定整数数组 nums 和整数 k，返回数组排序后第 k 个最大的元素。"
        "它不是第 k 个不同元素；这里希望用容量为 k 的小顶堆维护候选答案。"
    ),
    "trie_prefix": (
        "Trie 前缀查询风格：给定字符串数组 words 和查询前缀 prefix，"
        "沿 Trie 的字符路径查找 prefix，并返回有多少单词以该前缀开头。"
    ),
    "trie_prefix_match_string": (
        "Trie 前缀查询风格：给定字符串数组 words 和查询前缀 prefix，"
        "逐字符沿 Trie 向下匹配，并统计以 prefix 开头的单词数量。"
    ),
    "provinces": (
        "LeetCode 547 风格：给定城市连通矩阵 isConnected。"
        "如果两个城市直接或间接连通，则它们属于同一个省份；返回省份总数。"
    ),
    "permutations": (
        "LeetCode 46 风格：给定一个不含重复数字的数组 nums，返回它的所有可能排列。"
        "过程需要展示选择一个数字、进入下一层搜索、记录完整排列以及撤销选择。"
    ),
    "bitmask_subsets": (
        "LeetCode 78 风格：给定数组 nums，枚举它的所有子集。"
        "这里使用二进制 mask 表示每个元素是否被选中，并按 mask 从小到大返回子集。"
    ),
    "jump_game_expansion": (
        "LeetCode 55 风格扩展样例：给定非负整数数组 nums，nums[i] 表示从位置 i 最多可以向前跳多少步。"
        "判断从下标 0 出发是否能够到达最后一个下标。"
    ),
    "kth_largest_expansion": (
        "LeetCode 215 风格扩展样例：给定整数数组 nums 和整数 k，返回数组排序后第 k 个最大的元素。"
        "这里继续使用容量为 k 的小顶堆维护候选答案。"
    ),
    "trie_prefix_expansion": (
        "Trie 前缀查询扩展样例：给定字符串数组 words 和查询前缀 prefix，"
        "沿 Trie 的字符路径查找 prefix，并返回有多少单词以该前缀开头。"
    ),
    "permutations_expansion": (
        "LeetCode 46 风格扩展样例：给定一个不含重复数字的数组 nums，返回它的所有可能排列。"
        "过程展示回溯搜索中的选择、记录和撤销。"
    ),
    "reverse_linked_list_expansion": (
        "LeetCode 206 风格扩展样例：给定链表节点值序列 values，按顺序构成一条单链表。"
        "用迭代指针反转链表，并返回反转后的节点值序列。"
    ),
}


def _apply_problem_overrides(cases: tuple[BenchmarkCase, ...]) -> tuple[BenchmarkCase, ...]:
    """Return benchmark cases with only problem descriptions replaced."""

    return tuple(
        replace(case, problem=LEETCODE_STYLE_PROBLEM_OVERRIDES[case.id])
        if case.id in LEETCODE_STYLE_PROBLEM_OVERRIDES
        else case
        for case in cases
    )


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    return _apply_problem_overrides(
        (
            *dp.cases()[:1],
            *array_pointer.cases()[:1],
            *array_pointer.cases()[1:],
            *dp.cases()[1:],
            *graph.cases(),
            *string.cases(),
            *hash_sort_linked_greedy.cases(),
            *tree_range_math.cases(),
            *expansion.cases(),
        )
    )
