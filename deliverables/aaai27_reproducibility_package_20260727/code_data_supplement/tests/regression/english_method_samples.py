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


def test_english_gallery_keeps_stage1_and_stage2_as_separate_artifacts() -> None:
    from scripts.build_english_method_artifact_gallery import METHOD_LABELS, METHOD_ORDER, _root_readme

    assert METHOD_ORDER == (
        "algotutorgen_stage1",
        "algotutorgen_stage2",
        "direct_html",
        "webgen_agent",
        "htmlcure_strict",
        "browser_repair_1call",
    )
    assert METHOD_LABELS["algotutorgen_stage1"] == "AlgoTutorGen / Stage1"
    assert METHOD_LABELS["algotutorgen_stage2"] == "AlgoTutorGen / Stage2"
    readme = _root_readme(
        {
            "cases": [
                {
                    "case_id": "binary_search",
                    "title": "Binary Search",
                    "family": "Binary",
                    "methods": {method: {"machine_ok": True} for method in METHOD_ORDER},
                }
            ]
        }
    )
    assert "five comparison methods" in readme
    assert "138 saved artifact views" in readme
    assert "| Family | Case | Stage1 | Stage2 | Direct HTML | WebGen-Agent | HTMLCure | BrowserRepair |" in readme


def test_case_readme_explains_that_stage2_reuses_stage1_machine_checks() -> None:
    from scripts.build_english_method_artifact_gallery import MACHINE_BOOL_KEYS, METHOD_ORDER, _case_readme

    audits = {
        method: {
            "machine_metrics": {key: True for key in MACHINE_BOOL_KEYS},
            "machine_ok": True,
        }
        for method in METHOD_ORDER
    }
    readme = _case_readme(
        {
            "id": "binary_search",
            "title": "Binary Search",
            "family": "Binary",
            "difficulty": "medium",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "problem": "Find a target in a sorted array.",
            "samples": [{"input_data": {"nums": [1, 2, 3], "target": 2}, "expected": 1}],
        },
        audits,
    )

    assert "Stage2 row reuses the checks from its paired Stage1 interaction page" in readme
    assert "not a separate audit of the saved Stage2 visualization page" in readme


def test_stage1_localizer_translates_nested_payload_without_changing_values() -> None:
    from scripts.localize_stage1_artifacts_en import apply_translation_map, collect_cjk_strings

    payload = {
        "title": "二分查找",
        "answer": 4,
        "选项说明": {"相等": "Equal"},
        "steps": [
            {"reason": "高亮 nums[2]", "state": {"left": 0, "right": 5}},
            {"reason": "Found target", "state": {"left": 3, "right": 5}},
        ],
    }
    translated = apply_translation_map(
        payload,
        {
            "二分查找": "Binary Search",
            "高亮 nums[2]": "Highlight nums[2]",
            "选项说明": "Option explanations",
            "相等": "Equal",
        },
    )

    assert translated == {
        "title": "Binary Search",
        "answer": 4,
        "Option explanations": {"Equal": "Equal"},
        "steps": [
            {"reason": "Highlight nums[2]", "state": {"left": 0, "right": 5}},
            {"reason": "Found target", "state": {"left": 3, "right": 5}},
        ],
    }
    assert collect_cjk_strings(payload) == ["二分查找", "相等", "选项说明", "高亮 nums[2]"]


def test_stage1_localizer_replaces_renderer_cjk_runs_and_punctuation() -> None:
    from scripts.localize_stage1_artifacts_en import localize_renderer_text

    source = "const label = `当前代码行：第 ${line} 行`; // 提示"
    translated = localize_renderer_text(
        source,
        {
            "当前代码行": "Current code line",
            "第": "number",
            "行": "line",
            "提示": "Hint",
        },
    )

    assert translated == "const label = `Current code line: number ${line} line`; // Hint"
    json_source = 'const payload = {"note":"compare the “not rob” plan"};'
    assert localize_renderer_text(json_source, {}) == json_source


def test_stage1_localizer_validates_model_translation_batches() -> None:
    from scripts.localize_stage1_artifacts_en import translation_map_from_response

    sources = ["二分查找", "高亮 nums[2]"]
    translations = translation_map_from_response(
        sources,
        {"translations": ["Binary Search", "Highlight nums[2]"]},
    )

    assert translations == {
        "二分查找": "Binary Search",
        "高亮 nums[2]": "Highlight nums[2]",
    }

    try:
        translation_map_from_response(sources, {"translations": ["Binary Search", "高亮 nums[2]"]})
    except ValueError as exc:
        assert "still contains CJK" in str(exc)
    else:
        raise AssertionError("CJK-bearing translations must be rejected")


def test_stage1_localizer_rejects_algorithm_or_token_mutation() -> None:
    from scripts.localize_stage1_artifacts_en import assert_localization_preserves_semantics

    source = {
        "problem_title": "检查 nums[2]",
        "input_data": {"nums": [1, 2]},
        "expected_result": 3,
        "variants": [
            {
                "id": "v1",
                "code": "def solve(input_data):\n    # 返回总和\n    return sum(input_data['nums'])",
                "tracker_code": "def trace(input_data):\n    note = '创建 nums'\n    return input_data['nums']",
                "result": 3,
            }
        ],
    }
    localized = {
        "problem_title": "Check nums[2]",
        "input_data": {"nums": [1, 2]},
        "expected_result": 3,
        "variants": [
            {
                "id": "v1",
                "code": "def solve(input_data):\n    # Return the sum\n    return sum(input_data['nums'])",
                "tracker_code": "def trace(input_data):\n    note = 'Create nums'\n    return input_data['nums']",
                "result": 3,
            }
        ],
    }
    assert_localization_preserves_semantics(source, localized)

    changed_token = json.loads(json.dumps(localized))
    changed_token["problem_title"] = "Check nums[3]"
    try:
        assert_localization_preserves_semantics(source, changed_token)
    except ValueError as exc:
        assert "protected token" in str(exc)
    else:
        raise AssertionError("numbers embedded in localized text must be preserved")

    changed_logic = json.loads(json.dumps(localized))
    changed_logic["variants"][0]["code"] = (
        "def solve(input_data):\n    # Return the sum plus one\n    return sum(input_data['nums']) + 1"
    )
    try:
        assert_localization_preserves_semantics(source, changed_logic)
    except ValueError as exc:
        assert "Python semantics" in str(exc)
    else:
        raise AssertionError("localized code must not change algorithm logic")


def test_english_screenshot_capture_includes_both_algotutorgen_stages() -> None:
    from scripts.capture_english_method_screenshots import SCREENSHOT_METHODS, merge_screenshot_rows

    assert SCREENSHOT_METHODS == (
        "algotutorgen_stage1",
        "algotutorgen_stage2",
        "direct_html",
        "htmlcure_strict",
        "browser_repair_1call",
    )
    merged = merge_screenshot_rows(
        [
            {"method": "algotutorgen_stage2", "case_id": "case", "ok": True},
            {"method": "algotutorgen_stage1", "case_id": "stale", "ok": False},
        ],
        [{"method": "algotutorgen_stage1", "case_id": "case", "ok": True}],
        selected_methods=("algotutorgen_stage1",),
    )
    assert merged == [
        {"method": "algotutorgen_stage1", "case_id": "case", "ok": True},
        {"method": "algotutorgen_stage2", "case_id": "case", "ok": True},
    ]


def test_interaction_audit_recognizes_english_stage1_controls_and_feedback() -> None:
    from scripts.run_interaction_semantic_eval import (
        ALGOLAB_HINT_LABELS,
        ALGOLAB_SHOW_ANSWER_LABELS,
        _feedback_is_correct,
        _feedback_semantics,
        _feedback_is_wrong,
    )

    assert ALGOLAB_HINT_LABELS == ("提示", "Hint")
    assert ALGOLAB_SHOW_ANSWER_LABELS == ("查看答案", "Show answer", "View answer")
    assert _feedback_is_correct("Correct. The current state matches the answer.")
    assert _feedback_is_wrong("Incorrect option explanation: compare the current pointers.")
    assert _feedback_semantics(
        "Correct. The current state matches the answer.",
        "Incorrect option explanation: compare the current pointers.",
    ) == (True, True)
    assert _feedback_semantics(
        "Incorrect option explanation: compare the current pointers.",
        "Correct. The current state matches the answer.",
    ) == (False, False)


def test_gallery_audit_preserves_machine_diagnostics() -> None:
    from scripts.build_english_method_artifact_gallery import _machine_diagnostics

    diagnostics = _machine_diagnostics(
        {
            "console_page_errors": [
                "missing ) after argument list",
                'navigating to "file:///ssd1/private/output/page.html"',
            ],
            "feedback_preview": {"correct": "", "wrong": "", "log": "loaded"},
        }
    )

    assert diagnostics == {
        "console_page_errors": [
            "missing ) after argument list",
            'navigating to "file://<local-path>"',
        ],
        "feedback_preview": {"correct": "", "wrong": "", "log": "loaded"},
    }
