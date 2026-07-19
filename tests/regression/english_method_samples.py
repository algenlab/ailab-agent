from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGLISH_CASES = ROOT / "benchmark/english_method_samples.json"
CJK_RE = re.compile(r"[\u3400-\u9fff]")

SELECTED_CASE_IDS = (
    "graph_topological_sort",
    "complete_knapsack_coin_change",
    "trie_prefix",
    "house_robber",
    "binary_search",
    "unique_paths",
    "convex_hull",
    "segment_tree_range_sum",
    "two_sum",
    "permutations",
    "articulation_bridges",
    "kth_largest",
    "kmp",
    "provinces",
    "insertion_sort",
    "fast_power_mod",
    "two_pointer_pair_sum",
    "dijkstra_shortest_path",
    "daily_temperatures",
    "lca",
    "tree_max_independent_set",
    "merge_intervals",
    "reverse_linked_list",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_english_case_subset_preserves_the_fixed_cases_inputs_and_answers() -> None:
    source = _load(ROOT / "benchmark/algo_learn_env_benchmark.json")
    english = _load(ENGLISH_CASES)
    source_by_id = {row["id"]: row for row in source["cases"]}
    english_by_id = {row["id"]: row for row in english["cases"]}

    assert tuple(row["id"] for row in english["cases"]) == SELECTED_CASE_IDS
    assert set(english_by_id) == set(SELECTED_CASE_IDS)
    for case_id in SELECTED_CASE_IDS:
        assert english_by_id[case_id]["samples"] == source_by_id[case_id]["samples"]
        assert english_by_id[case_id]["family_id"] == source_by_id[case_id]["family_id"]
        assert english_by_id[case_id]["subfamily_id"] == source_by_id[case_id]["subfamily_id"]


def test_english_case_subset_has_no_cjk_in_public_text() -> None:
    english = _load(ENGLISH_CASES)
    public_fields = (
        "title",
        "family",
        "problem",
        "strategy",
        "input_contract",
        "variant_name",
        "learning_objectives",
        "required_views",
        "interaction_tasks",
    )
    for case in english["cases"]:
        for field in public_fields:
            text = json.dumps(case.get(field), ensure_ascii=False)
            assert CJK_RE.search(text) is None, (case["id"], field, text)


def test_generation_prompts_expose_a_strict_english_mode() -> None:
    from algolab.generation.language import english_output_requirement
    from scripts.run_direct_html_baseline import _system_prompt

    requirement = english_output_requirement()
    system = _system_prompt(language="en")
    combined = f"{requirement}\n{system}".lower()

    for phrase in ("english only", "user interface", "feedback", "learning log", "code comments"):
        assert phrase in combined
    assert CJK_RE.search(system) is None


def test_webgen_english_instruction_is_cjk_free() -> None:
    from scripts.prepare_external_webgen_baseline import make_instruction

    case = {
        "id": "binary_search",
        "title": "Binary Search",
        "family": "Binary Search",
        "problem": "Find the target index in a sorted array.",
        "strategy": "Maintain a closed search interval.",
    }
    sample = {"input_data": {"nums": [-1, 0, 3, 5, 9, 12], "target": 9}, "expected": 4}
    instruction = make_instruction(case, sample, language="en")

    assert "English only" in instruction
    assert CJK_RE.search(instruction) is None


def test_english_gallery_validator_rejects_cjk_text(tmp_path: Path) -> None:
    from scripts.build_english_method_artifact_gallery import assert_english_only_tree

    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "page.html").write_text("<p>English only</p>", encoding="utf-8")
    assert_english_only_tree(clean)

    (clean / "audit.json").write_text('{"note":"中文"}', encoding="utf-8")
    try:
        assert_english_only_tree(clean)
    except ValueError as exc:
        assert "audit.json" in str(exc)
    else:
        raise AssertionError("CJK text should fail the English-only gate")
