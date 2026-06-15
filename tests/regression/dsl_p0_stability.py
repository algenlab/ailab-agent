"""Regression tests for P0 stability contracts."""

from __future__ import annotations

from algolab.generation import solution_generator
from algolab.generation.repair import build_solution_repair_prompt
from algolab.runtime.executor import execute_variant, results_equivalent
from algolab.runtime.sandbox import SandboxError, run_function
from algolab.schemas.input import ProblemInput
from algolab.schemas.semantic_trace import SemanticTrace, SolutionVariant
from algolab.verification.demo_readiness import validate_variant_demo_readiness
from algolab.verification.repair_context import build_repair_context
from scripts.replay_llm_specs import replay_artifact_file


def test_case_aware_normalizer_accepts_bitmask_subset_order():
    expected = [[], [1], [2], [1, 2]]
    actual = [[2], [1, 2], [], [1]]

    assert not results_equivalent(expected, actual)
    assert results_equivalent(expected, actual, case_id="bitmask_subsets", family_id="math_bit")


def test_case_aware_normalizer_accepts_kruskal_mst_result_shapes():
    expected = {"weight": 6, "edges": [["A", "B", 1], ["B", "C", 5]]}
    actual = {"total_weight": 6, "mst_edges": [["C", "B", 5], ["B", "A", 1]]}

    assert results_equivalent(expected, actual, case_id="kruskal_mst_weight", family_id="shortest_path_mst")


def test_execute_variant_uses_case_aware_trace_result_normalization():
    variant = SolutionVariant(
        id="bitmask",
        name="bitmask",
        strategy="subset order compatibility",
        code="def solve(input_data):\n    return [[], [1], [2], [1, 2]]\n",
        tracker_code=(
            "def trace(input_data):\n"
            "    sess = TraceSession('bitmask', input_data)\n"
            "    sess.result([[2], [1, 2], [], [1]])\n"
            "    return sess.to_trace()\n"
        ),
    )

    executed = execute_variant(variant, {}, case_id="bitmask_subsets", family_id="math_bit")

    assert executed.result == [[], [1], [2], [1, 2]]
    assert executed.trace is not None
    assert executed.trace.result == [[], [1], [2], [1, 2]]


def test_problem_input_carries_benchmark_metadata_without_prompt_leakage_requirements():
    request = ProblemInput(
        problem="返回所有子集。",
        input_data={"nums": [1, 2]},
        expected_result=[[], [1], [2], [1, 2]],
        case_id="bitmask_subsets",
        family_id="math_bit",
        subfamily_id="bitmask",
    )

    assert request.case_id == "bitmask_subsets"
    assert request.family_id == "math_bit"
    assert request.subfamily_id == "bitmask"


def test_trace_session_accepts_deepseek_single_input_argument_alias():
    from algolab.runtime.dsl import TraceSession

    sess = TraceSession({"x": 1})
    sess.result(1)
    trace = sess.to_trace()

    assert trace["algorithm"] == "算法可视化"
    assert trace["input_data"] == {"x": 1}


def test_executor_fills_missing_trace_input_data_from_request():
    variant = SolutionVariant(
        id="v",
        name="missing input trace",
        strategy="compat",
        code="def solve(input_data):\n    return 1\n",
        tracker_code=(
            "def trace(input_data):\n"
            "    sess = TraceSession()\n"
            "    sess.result(1)\n"
            "    return sess.to_trace()\n"
        ),
    )

    executed = execute_variant(variant, {"x": 1})

    assert executed.trace is not None
    assert executed.trace.input_data == {"x": 1}


def test_array_setitem_at_current_length_appends_for_dynamic_path_arrays():
    from algolab.runtime.dsl import TraceSession

    sess = TraceSession("dynamic path", {"nums": [1]})
    path = sess.array("path", [])
    path[0] = 1
    sess.result(path.to_list())
    trace = sess.to_trace()

    assert trace["result"] == [1]
    assert trace["events"][-1]["state"]["path"] == [1]


def test_demo_missing_state_is_degraded_warning_not_blocking_error():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "state degraded",
            "input_data": {"value": 1},
            "result": 1,
            "pseudocode": [],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "input"}],
                    "state": {"value": 1},
                    "reason": "初始化输入。",
                    "code_line": 1,
                },
                {
                    "step": 1,
                    "op": "set",
                    "targets": [{"id": "dp[0]"}],
                    "deps": [{"id": "input"}],
                    "reason": "根据输入更新状态。",
                    "code_line": 2,
                },
                {
                    "step": 2,
                    "op": "mark",
                    "targets": [{"id": "answer"}],
                    "role": "answer",
                    "state": {"answer": 1},
                    "value": 1,
                    "reason": "得到答案。",
                    "code_line": 3,
                },
            ],
        }
    )

    report = validate_variant_demo_readiness("v", "variant", trace)

    assert report.status == "warn"
    assert report.errors == []
    assert any("demo_missing_state" in warning for warning in report.warnings)


def test_repair_prompt_locks_scope_for_demo_state_and_result_mismatch():
    demo_context = build_repair_context(["variant 失败：failure_type=demo_missing_state: step 3 缺少可复原 state"])
    demo_prompt = build_solution_repair_prompt(
        request_prompt="生成算法轨迹 JSON。",
        previous={"variants": [{"id": "v", "code": "def solve(input_data): return 1", "tracker_code": ""}]},
        errors=["variant 失败：failure_type=demo_missing_state: step 3 缺少可复原 state"],
        repair_context=demo_context,
    )

    mismatch_context = build_repair_context(["variant 失败：solve 结果 1 与 trace 结果 0 不一致"])
    mismatch_prompt = build_solution_repair_prompt(
        request_prompt="生成算法轨迹 JSON。",
        previous={"variants": [{"id": "v", "code": "def solve(input_data): return 1", "tracker_code": ""}]},
        errors=["variant 失败：solve 结果 1 与 trace 结果 0 不一致"],
        repair_context=mismatch_context,
    )

    assert "只补 tracker_code 中缺失的 state/snapshot/step" in demo_prompt
    assert "不要修改 solve_code/code" in demo_prompt
    assert "优先只修改 tracker_code" in mismatch_prompt
    assert "不要重写已正确的 solve_code/code" in mismatch_prompt


def test_sandbox_trace_error_includes_generated_code_location():
    code = (
        "def trace(input_data):\n"
        "    sess = TraceSession('runtime error', input_data)\n"
        "    value = input_data['value']\n"
        "    return 10 / 0\n"
    )

    try:
        run_function(code, "trace", {"value": 1})
    except SandboxError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("trace should fail")

    assert "trace 执行失败" in message
    assert "Generated code traceback" in message
    assert 'File "<algolab_generated_trace>", line 4, in trace' in message
    assert "return 10 / 0" in message


def test_sandbox_allows_next_over_generator_expressions():
    code = (
        "def solve(input_data):\n"
        "    nums = input_data['nums']\n"
        "    return next(x for x in nums if x > 1)\n"
    )

    assert run_function(code, "solve", {"nums": [1, 2, 3]}) == 2


def test_demo_state_repair_preserves_previous_solve_code_even_if_llm_rewrites_it():
    previous_code = "def solve(input_data):\n    return 1\n"
    rewritten_code = "def solve(input_data):\n    return 999\n"

    def fake_chat_json(_system_prompt: str, _user_prompt: str, *, kind: str):
        return {
            "problem_title": "demo state",
            "input_contract": "",
            "verifier_code": "",
            "variants": [
                {
                    "id": "v",
                    "name": "v",
                    "strategy": "",
                    "time_complexity": "",
                    "space_complexity": "",
                    "code": rewritten_code,
                    "tracker_code": "def trace(input_data):\n    return {}\n",
                }
            ],
        }

    request = ProblemInput(problem="常量题", input_data={}, expected_result=1, solution_count=1)
    previous = {
        "problem_title": "demo state",
        "input_contract": "",
        "verifier_code": "",
        "variants": [
            {
                "id": "v",
                "name": "v",
                "strategy": "",
                "time_complexity": "",
                "space_complexity": "",
                "code": previous_code,
                "tracker_code": "def trace(input_data):\n    return {}\n",
            }
        ],
    }
    original = solution_generator._chat_json
    solution_generator._chat_json = fake_chat_json
    try:
        repaired = solution_generator.repair_solution_spec(
            request,
            previous,
            ["variant 失败：failure_type=demo_missing_state: step 3 缺少可复原 state"],
        )
    finally:
        solution_generator._chat_json = original

    assert repaired["variants"][0]["code"] == previous_code


def test_trace_execution_repair_locks_to_tracker_code_only():
    prompts: list[str] = []
    previous_code = "def solve(input_data):\n    return 3\n"
    previous_verifier = "def verify(input_data):\n    return 3\n"
    repaired_tracker = (
        "def trace(input_data):\n"
        "    sess = TraceSession('fixed trace', input_data)\n"
        "    sess.result(3)\n"
        "    return sess.to_trace()\n"
    )

    def fake_chat_json(_system_prompt: str, user_prompt: str, *, kind: str):
        prompts.append(user_prompt)
        return {
            "problem_title": "LCS",
            "input_contract": "text1/text2",
            "verifier_code": "def verify(input_data):\n    return 999\n",
            "variants": [
                {
                    "id": "dp",
                    "name": "dp",
                    "strategy": "repair trace",
                    "time_complexity": "O(mn)",
                    "space_complexity": "O(mn)",
                    "code": "def solve(input_data):\n    return 999\n",
                    "tracker_code": repaired_tracker,
                }
            ],
        }

    request = ProblemInput(
        problem="给定 text1 和 text2，返回最长公共子序列长度。",
        input_data={"text1": "abcde", "text2": "ace"},
        expected_result=3,
        strategy_hint="二维动态规划",
        solution_count=1,
    )
    previous = {
        "problem_title": "LCS",
        "input_contract": "text1/text2",
        "verifier_code": previous_verifier,
        "variants": [
            {
                "id": "dp",
                "name": "dp",
                "strategy": "dp",
                "time_complexity": "O(mn)",
                "space_complexity": "O(mn)",
                "code": previous_code,
                "tracker_code": "def trace(input_data):\n    raise TypeError('boom')\n",
            }
        ],
    }
    errors = [
        "二维动态规划 失败：trace 执行失败：TypeError: cannot unpack non-iterable int object\n"
        'Generated code traceback:\n  File "<algolab_generated_trace>", line 31, in trace\n'
        "    value = helper()\n"
    ]
    context = build_repair_context(errors, request=request, previous=previous)
    assert context[0]["repair_scope"] == "tracker_only_execution"

    original = solution_generator._chat_json
    solution_generator._chat_json = fake_chat_json
    try:
        repaired = solution_generator.repair_solution_spec(request, previous, errors)
    finally:
        solution_generator._chat_json = original

    assert "失败发生在 trace/tracker_code 执行阶段" in prompts[0]
    assert "只修 tracker_code" in prompts[0]
    assert repaired["verifier_code"] == previous_verifier
    assert repaired["variants"][0]["code"] == previous_code
    assert repaired["variants"][0]["tracker_code"] == repaired_tracker


def test_result_mismatch_repair_locks_tracker_when_trace_matches_expected():
    request = ProblemInput(
        problem="给定 words 和 prefix，统计 words 中以 prefix 开头的单词数量。prefix 可以为空，空前缀匹配所有 words。",
        input_data={"words": ["", "a", "ab"], "prefix": ""},
        expected_result=3,
        strategy_hint="Trie 前缀计数",
        solution_count=1,
        case_id="trie_prefix_expansion",
        family_id="trie",
        subfamily_id="prefix_count",
    )
    errors = ["Trie 前缀计数 失败：solve 结果 0 与 trace 结果 3 不一致"]
    repair_context = build_repair_context(errors, request=request)
    prompt = build_solution_repair_prompt(
        request_prompt="生成算法轨迹 JSON。",
        previous={"variants": [{"id": "v", "code": "def solve(input_data): return 0", "tracker_code": ""}]},
        errors=errors,
        repair_context=repair_context,
    )

    assert "trace_result 等于 expected_result" in prompt
    assert "只修 solve/code" in prompt
    assert "prefix == \"\"" in prompt
    assert "len(words)" in prompt

    previous_tracker = (
        "def trace(input_data):\n"
        "    sess = TraceSession('trie', input_data)\n"
        "    sess.result(3)\n"
        "    return sess.to_trace()\n"
    )
    rewritten_tracker = (
        "def trace(input_data):\n"
        "    sess = TraceSession('trie', input_data)\n"
        "    sess.result(0)\n"
        "    return sess.to_trace()\n"
    )

    def fake_chat_json(_system_prompt: str, _user_prompt: str, *, kind: str):
        return {
            "problem_title": "trie",
            "input_contract": "",
            "verifier_code": "",
            "variants": [
                {
                    "id": "v",
                    "name": "v",
                    "strategy": "",
                    "time_complexity": "",
                    "space_complexity": "",
                    "code": "def solve(input_data):\n    return 3\n",
                    "tracker_code": rewritten_tracker,
                }
            ],
        }

    previous = {
        "problem_title": "trie",
        "input_contract": "",
        "verifier_code": "",
        "variants": [
            {
                "id": "v",
                "name": "v",
                "strategy": "",
                "time_complexity": "",
                "space_complexity": "",
                "code": "def solve(input_data):\n    return 0\n",
                "tracker_code": previous_tracker,
            }
        ],
    }
    original = solution_generator._chat_json
    solution_generator._chat_json = fake_chat_json
    try:
        repaired = solution_generator.repair_solution_spec(request, previous, errors)
    finally:
        solution_generator._chat_json = original

    assert repaired["variants"][0]["code"] == "def solve(input_data):\n    return 3\n"
    assert repaired["variants"][0]["tracker_code"] == previous_tracker


def test_replay_artifact_file_reexecutes_saved_variant_without_llm(tmp_path):
    artifact_path = tmp_path / "llm_bitmask_subsets_0.json"
    artifact_path.write_text(
        """
{
  "problem_title": "子集",
  "input_data": {"nums": [1, 2]},
  "expected_result": [[], [1], [2], [1, 2]],
  "variants": [
    {
      "id": "bitmask",
      "name": "bitmask",
      "strategy": "bitmask",
      "time_complexity": "O(2^n)",
      "space_complexity": "O(2^n)",
      "code": "def solve(input_data):\\n    return [[], [1], [2], [1, 2]]\\n",
      "tracker_code": "def trace(input_data):\\n    sess = TraceSession('bitmask', input_data)\\n    sess.result([[2], [1, 2], [], [1]])\\n    return sess.to_trace()\\n"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    row = replay_artifact_file(artifact_path, case_id="bitmask_subsets", family_id="math_bit")

    assert row["ok"] is True
    assert row["case_id"] == "bitmask_subsets"
    assert row["variant_count"] == 1
    assert row["errors"] == []


def test_llm_benchmark_spec_snapshot_writer_records_round_specs(tmp_path):
    from scripts.run_llm_benchmark import _write_spec_snapshot

    _write_spec_snapshot(
        tmp_path,
        "llm_trie_prefix_expansion_0",
        "round0_generation_spec",
        {"problem_title": "trie", "variants": []},
    )

    snapshot = tmp_path / "spec_rounds" / "llm_trie_prefix_expansion_0_round0_generation_spec.json"
    assert snapshot.exists()
    assert '"problem_title": "trie"' in snapshot.read_text(encoding="utf-8")


def run_all() -> None:
    test_case_aware_normalizer_accepts_bitmask_subset_order()
    test_case_aware_normalizer_accepts_kruskal_mst_result_shapes()
    test_execute_variant_uses_case_aware_trace_result_normalization()
    test_problem_input_carries_benchmark_metadata_without_prompt_leakage_requirements()
    test_trace_session_accepts_deepseek_single_input_argument_alias()
    test_executor_fills_missing_trace_input_data_from_request()
    test_array_setitem_at_current_length_appends_for_dynamic_path_arrays()
    test_demo_missing_state_is_degraded_warning_not_blocking_error()
    test_repair_prompt_locks_scope_for_demo_state_and_result_mismatch()
    test_sandbox_trace_error_includes_generated_code_location()
    test_sandbox_allows_next_over_generator_expressions()
    test_demo_state_repair_preserves_previous_solve_code_even_if_llm_rewrites_it()
    test_trace_execution_repair_locks_to_tracker_code_only()
    test_result_mismatch_repair_locks_tracker_when_trace_matches_expected()
    import tempfile
    from pathlib import Path

    class _TmpPath:
        def __enter__(self):
            self._tmp = tempfile.TemporaryDirectory()
            return Path(self._tmp.name)

        def __exit__(self, exc_type, exc, tb):
            self._tmp.cleanup()

    with _TmpPath() as tmp_path:
        test_replay_artifact_file_reexecutes_saved_variant_without_llm(tmp_path)
        test_llm_benchmark_spec_snapshot_writer_records_round_specs(tmp_path)


if __name__ == "__main__":
    run_all()
    print("dsl_p0_stability: PASS")
