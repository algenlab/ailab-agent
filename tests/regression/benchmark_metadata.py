"""Split regression tests: benchmark metadata."""

from __future__ import annotations

from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.process_validator import validate_process
from tests.benchmark_cases import LEETCODE_STYLE_PROBLEM_OVERRIDES, BenchmarkCase, benchmark_cases

from tests.regression.helpers import *


def test_leetcode_style_problem_overrides_only_replace_problem_descriptions():
    from tests.benchmark_families import array_pointer, dp, expansion, graph, hash_sort_linked_greedy, string, tree_range_math

    raw_cases = (
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
    raw_by_id = {case.id: case for case in raw_cases}

    assert LEETCODE_STYLE_PROBLEM_OVERRIDES
    overridden_count = 0
    for case in benchmark_cases():
        raw = raw_by_id[case.id]
        if case.id in LEETCODE_STYLE_PROBLEM_OVERRIDES:
            overridden_count += 1
            assert case.problem == LEETCODE_STYLE_PROBLEM_OVERRIDES[case.id]
        else:
            assert case.problem == raw.problem
        for field in BenchmarkCase.__dataclass_fields__:
            if field == "problem":
                continue
            assert getattr(case, field) == getattr(raw, field), (case.id, field)

    assert overridden_count == len(LEETCODE_STYLE_PROBLEM_OVERRIDES)

def test_benchmark_cases_are_multi_input_release_ready():
    cases = benchmark_cases()
    assert len(cases) >= 5
    for case in cases:
        assert len(case.samples) >= 2
        for index, sample in enumerate(case.samples):
            request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)
            artifact, errors = _try_materialize(request, spec_for_case(case))
            assert errors == [], (case.id, index, errors)
            assert artifact.validation.release_gate.release_ready, (case.id, index, artifact.validation.release_gate)
            assert len(artifact.variants) == 1
            assert artifact.variants[0].result == sample.expected
            assert artifact.verifier_result == sample.expected
            assert artifact.variants[0].trace is not None
            assert len(artifact.variants[0].trace.events) >= 1
            if case.id in contract_enabled_case_ids():
                assert artifact.correctness_contract is not None
                assert artifact.validation.contract_validation is not None
                assert artifact.validation.contract_validation.release_gate.contract_ready
                assert artifact.validation.contract_test_results
                assert all(item["ok"] for item in artifact.validation.contract_test_results)
            if index == 0:
                scene = artifact.scenes[case.id]
                layouts = {
                    obj.meta.get("layout")
                    for frame in scene.frames
                    for obj in frame.objects
                    if obj.type.value == "container"
                }
                for expected_layout in case.expected_layouts:
                    assert expected_layout in layouts, (case.id, index, expected_layout, layouts)


def test_benchmark_cases_expose_phase10_metadata():
    from scripts.check_family_capabilities import load_family_capabilities

    capabilities_by_label = {
        entry["label"]: entry for entry in load_family_capabilities()["families"]
    }
    valid_gate_layers = {"smoke", "family_core", "expansion", "llm_eval"}
    valid_support_levels = {"strong", "medium_plus", "medium", "basic", "planned"}
    valid_oracle_types = {"closed_form", "independent_reference", "bruteforce", "property"}

    for case in benchmark_cases():
        family_capability = capabilities_by_label[case.family]
        assert case.family_id == family_capability["family_id"], case.id
        assert case.process_profile == family_capability["process_profile"], case.id
        assert case.support_level == family_capability["current_level"], case.id
        assert case.subfamily_id, case.id
        assert case.gate_layer in valid_gate_layers, case.id
        assert case.support_level in valid_support_levels, case.id
        assert case.oracle_type in valid_oracle_types, case.id
        assert isinstance(case.demo_required, bool), case.id


def test_benchmark_cases_expose_phase11_oracle_metadata_and_independent_examples():
    from tests.oracles import oracle_examples

    valid_oracle_types = {"closed_form", "independent_reference", "bruteforce", "property"}
    valid_risks = {"none", "missing_verifier", "verifier_matches_solve"}
    example_families = {example["family_id"] for example in oracle_examples()}

    assert {"dp_1d", "basic_graph", "string_advanced", "sorting", "union_find", "range_structure"} <= example_families
    for example in oracle_examples():
        assert example["oracle_type"] in valid_oracle_types
        assert callable(example["reference"])
        assert example["notes"]

    risky_case_ids = {"tarjan_scc", "articulation_bridges", "bipartite_matching", "edmonds_karp"}
    for case in benchmark_cases():
        assert case.oracle_type in valid_oracle_types, case.id
        assert case.oracle_risk in valid_risks, case.id
        assert case.oracle_notes, case.id
        if not case.verifier_code.strip():
            assert case.oracle_risk == "missing_verifier", case.id
        if case.id in risky_case_ids:
            assert case.oracle_risk == "verifier_matches_solve", case.id
            assert "solve" in case.oracle_notes.lower() or "结构" in case.oracle_notes, case.id
        if case.support_level == "strong" and case.oracle_risk != "none":
            assert case.oracle_reference, case.id


def test_contract_tests_block_bad_solve():
    case = next(item for item in benchmark_cases() if item.id == "two_sum")
    spec = spec_for_case(case)
    spec["variants"][0]["code"] = "def solve(input_data):\n    return [0, 1]"
    sample = case.samples[0]
    request = ProblemInput(problem=case.title, input_data=sample.input_data, expected_result=sample.expected)

    artifact, errors = _try_materialize(request, spec)

    assert errors
    assert not artifact.validation.release_gate.release_ready
    assert artifact.validation.contract_test_results
    assert any(not item["ok"] for item in artifact.validation.contract_test_results)
    assert any("contract test_cases" in error for error in errors)


__all__ = [name for name in globals() if name.startswith("test_")]
