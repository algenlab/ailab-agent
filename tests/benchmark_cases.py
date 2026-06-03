"""Deterministic real-problem benchmark cases.

These cases exercise the production pipeline without calling the LLM.  Each
case provides executable solve/trace/verifier code and several inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
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


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    return (
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
