"""Split regression tests: phase13 families."""

from __future__ import annotations

from pathlib import Path
import importlib
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.verification.process_validator import validate_process
from tests.benchmark_cases import benchmark_cases
from scripts.run_llm_benchmark import classify_failure

from tests.regression.helpers import *

def test_phase13_long_files_are_split_without_changing_public_contracts():
    import algolab.verification.process_validator as process_validator
    import tests.benchmark_cases as benchmark_cases_module
    import tests.benchmark_regression as benchmark_regression_module

    expected_modules = (
        "algolab.verification.process_families.common",
        "algolab.verification.process_families.array_pointer",
        "algolab.verification.process_families.dp",
        "algolab.verification.process_families.graph",
        "algolab.verification.process_families.hash_sort_linked_greedy",
        "algolab.verification.process_families.string",
        "algolab.verification.process_families.tree_range_math",
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

    cases = benchmark_cases()
    case_ids = [case.id for case in cases]
    assert len(cases) == 69
    assert sum(len(case.samples) for case in cases) == 250
    assert (
        __import__("hashlib").sha256("\n".join(case_ids).encode()).hexdigest()
        == "1cfc7cf707760629b743538f300102763fa5310cd9daf91fc33394dbbc3291d7"
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
    profiles = {profile.family: profile for profile in __import__("algolab.verification.process_validator", fromlist=["process_validation_registry"]).process_validation_registry()}
    assert "array_pointer" in profiles
    assert profiles["array_pointer"].status == "strong"

    array_pointer_samples = [
        sample
        for case in benchmark_cases()
        if case.process_profile == "array_pointer"
        for sample in case.samples
    ]
    assert len(array_pointer_samples) >= 18

    valid_two_pointer_errors = _process_errors_for(
        _array_contract_trace(
            "Two pointer pair sum trace",
            {"nums": [1, 2, 4, 6, 10], "target": 8},
            [1, 3],
            [
                _family_contract_event(
                    0,
                    "create",
                    ["nums", "pointer:left", "pointer:right"],
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 4, "target": 8, "array_contract": {"submode": "two_pointer"}},
                    reason="初始化左右双指针。",
                ),
                _family_contract_event(
                    1,
                    "compare",
                    ["nums[0]", "nums[4]"],
                    value=11,
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 4, "target": 8, "sum": 11, "array_contract": {"submode": "two_pointer"}},
                    reason="比较左右指针元素之和。",
                ),
                _family_contract_event(
                    2,
                    "move",
                    ["pointer:right"],
                    value=3,
                    deps=["nums[0]", "nums[4]", "target"],
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 3, "target": 8, "array_contract": {"submode": "two_pointer"}},
                    reason="当前和大于 target，右指针左移。",
                ),
                _family_contract_event(
                    3,
                    "compare",
                    ["nums[0]", "nums[3]"],
                    value=7,
                    state={"nums": [1, 2, 4, 6, 10], "left": 0, "right": 3, "target": 8, "sum": 7, "array_contract": {"submode": "two_pointer"}},
                    reason="比较移动后的两数之和。",
                ),
                _family_contract_event(
                    4,
                    "move",
                    ["pointer:left"],
                    value=1,
                    deps=["nums[0]", "nums[3]", "target"],
                    state={"nums": [1, 2, 4, 6, 10], "left": 1, "right": 3, "target": 8, "array_contract": {"submode": "two_pointer"}},
                    reason="当前和小于 target，左指针右移。",
                ),
                _family_contract_event(
                    5,
                    "mark",
                    ["nums[1]", "nums[3]"],
                    value=[1, 3],
                    state={"nums": [1, 2, 4, 6, 10], "left": 1, "right": 3, "target": 8, "sum": 8, "answer": [1, 3], "array_contract": {"submode": "two_pointer"}},
                    role="answer",
                    reason="两数之和等于 target，返回当前指针。",
                ),
            ],
        )
    )
    assert valid_two_pointer_errors == [], valid_two_pointer_errors

    wrong_mid_errors = _process_errors_for(
        _array_contract_trace(
            "Binary search wrong mid array pointer",
            {"nums": [1, 3, 5, 7], "target": 7},
            3,
            [
                _family_contract_event(0, "create", ["nums"], state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "mid": 3, "target": 7}, reason="初始化错误 mid。"),
                _family_contract_event(1, "compare", ["nums[3]", "pointer:mid"], value=3, state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "mid": 3, "target": 7}, reason="比较错误中点。"),
            ],
        )
    )
    assert any("mid" in error and "二分" in error for error in wrong_mid_errors), wrong_mid_errors

    wrong_shrink_errors = _process_errors_for(
        _array_contract_trace(
            "Binary search wrong shrink array pointer",
            {"nums": [1, 3, 5, 7], "target": 7},
            3,
            [
                _family_contract_event(0, "create", ["nums"], state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "target": 7}, reason="初始化。"),
                _family_contract_event(1, "compare", ["nums[1]", "pointer:mid"], value=1, state={"nums": [1, 3, 5, 7], "left": 0, "right": 3, "mid": 1, "target": 7}, reason="比较中点。"),
                _family_contract_event(2, "move", ["pointer:right"], value=0, deps=["nums[1]", "target"], state={"nums": [1, 3, 5, 7], "left": 0, "right": 0, "target": 7}, reason="错误地向左收缩。"),
            ],
        )
    )
    assert any("收缩方向错误" in error for error in wrong_shrink_errors), wrong_shrink_errors

    wrong_prefix_errors = _process_errors_for(
        _array_contract_trace(
            "Prefix sum wrong update",
            {"nums": [2, 4, 6], "query": [1, 2]},
            10,
            [
                _family_contract_event(0, "create", ["nums", "prefix"], state={"nums": [2, 4, 6], "prefix": [0, 0, 0, 0], "array_contract": {"submode": "prefix_sum", "expected_targets": ["prefix[1]", "prefix[2]", "prefix[3]"]}}, reason="初始化前缀数组。"),
                _family_contract_event(1, "set", ["prefix[1]"], value=2, deps=["prefix[0]", "nums[0]"], state={"nums": [2, 4, 6], "prefix": [0, 2, 0, 0], "i": 0, "array_contract": {"submode": "prefix_sum", "expected_targets": ["prefix[1]", "prefix[2]", "prefix[3]"]}}, reason="写入 prefix[1]。"),
                _family_contract_event(2, "set", ["prefix[2]"], value=7, deps=["prefix[1]", "nums[1]"], state={"nums": [2, 4, 6], "prefix": [0, 2, 7, 0], "i": 1, "array_contract": {"submode": "prefix_sum", "expected_targets": ["prefix[1]", "prefix[2]", "prefix[3]"]}}, reason="错误写入 prefix[2]。"),
            ],
        )
    )
    assert any("prefix" in error and "应为" in error for error in wrong_prefix_errors), wrong_prefix_errors

    wrong_diff_errors = _process_errors_for(
        _array_contract_trace(
            "Difference array wrong update",
            {"nums": [1, 1, 1], "updates": [[0, 1, 2]]},
            [3, 3, 1],
            [
                _family_contract_event(0, "create", ["diff"], state={"nums": [1, 1, 1], "diff": [1, 0, 0, 0], "updates": [[0, 1, 2]], "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]}}, reason="初始化差分数组。"),
                _family_contract_event(1, "set", ["diff[0]"], value=3, deps=["diff[0]", "updates[0]"], state={"nums": [1, 1, 1], "diff": [3, 0, 0, 0], "updates": [[0, 1, 2]], "update_index": 0, "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]}}, reason="区间左端加 delta。"),
                _family_contract_event(2, "set", ["diff[2]"], value=0, deps=["diff[2]", "updates[0]"], state={"nums": [1, 1, 1], "diff": [3, 0, 0, 0], "updates": [[0, 1, 2]], "update_index": 0, "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]}}, reason="错误地没有在右端后一位减 delta。"),
            ],
        )
    )
    assert any("diff" in error and "应为" in error for error in wrong_diff_errors), wrong_diff_errors

    valid_diff_trace = _array_contract_trace(
        "Difference array valid update dependency",
        {"nums": [1, 1, 1], "updates": [[0, 1, 2]]},
        [3, 3, 1],
        [
            _family_contract_event(
                0,
                "create",
                ["diff"],
                state={
                    "nums": [1, 1, 1],
                    "diff": [1, 0, 0, 0],
                    "updates": [[0, 1, 2]],
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                reason="初始化差分数组。",
            ),
            _family_contract_event(
                1,
                "set",
                ["diff[0]"],
                value=3,
                deps=["diff[0]", "updates[0]"],
                state={
                    "nums": [1, 1, 1],
                    "diff": [3, 0, 0, 0],
                    "updates": [[0, 1, 2]],
                    "update_index": 0,
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                reason="区间左端差分加 delta。",
            ),
            _family_contract_event(
                2,
                "set",
                ["diff[2]"],
                value=-2,
                deps=["diff[2]", "updates[0]"],
                state={
                    "nums": [1, 1, 1],
                    "diff": [3, 0, -2, 0],
                    "updates": [[0, 1, 2]],
                    "update_index": 0,
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                reason="区间右端后一位差分减 delta。",
            ),
            _family_contract_event(
                3,
                "mark",
                ["diff"],
                value=[3, 3, 1],
                state={
                    "nums": [1, 1, 1],
                    "diff": [3, 0, -2, 0],
                    "updates": [[0, 1, 2]],
                    "answer": [3, 3, 1],
                    "array_contract": {"submode": "difference_array", "expected_targets": ["diff[0]", "diff[2]"]},
                },
                role="answer",
                reason="前缀还原最终数组。",
            ),
        ],
    )
    valid_diff_trace_errors, valid_diff_process_errors, valid_diff_scene_errors = _contract_stack_errors(valid_diff_trace)
    assert valid_diff_trace_errors == []
    assert valid_diff_process_errors == []
    assert valid_diff_scene_errors == []

    window_jump_errors = _process_errors_for(
        _array_contract_trace(
            "Sliding window jump",
            {"nums": [1, 2, 3], "target": 3},
            2,
            [
                _family_contract_event(0, "create", ["nums"], state={"nums": [1, 2, 3], "left": 0, "right": 0, "window_sum": 1, "array_contract": {"submode": "sliding_window"}}, reason="初始化窗口。"),
                _family_contract_event(1, "move", ["pointer:right"], value=2, state={"nums": [1, 2, 3], "left": 0, "right": 2, "window_sum": 6, "array_contract": {"submode": "sliding_window"}}, reason="错误跳过一个窗口位置。"),
            ],
        )
    )
    assert any("窗口" in error and "跳变" in error for error in window_jump_errors), window_jump_errors


def test_phase13_dp_validator_expands_family_core_samples_and_rejects_digit_dp_errors():
    profiles = {profile.family: profile for profile in __import__("algolab.verification.process_validator", fromlist=["process_validation_registry"]).process_validation_registry()}
    assert "dp" in profiles
    assert profiles["dp"].status == "strong"

    dp_cases = [
        case
        for case in benchmark_cases()
        if case.gate_layer == "family_core" and case.process_profile == "dp"
    ]
    dp_samples = [sample for case in dp_cases for sample in case.samples]
    subfamilies = {case.subfamily_id for case in dp_cases}
    assert len(dp_samples) >= 35
    assert {
        "house_robber",
        "unique_paths",
        "knapsack_01",
        "complete_knapsack",
        "bounded_knapsack",
        "lcs",
        "edit_distance",
        "interval_dp",
        "tree_max_independent_set",
        "state_compression",
        "digit_dp",
    } <= subfamilies

    def assert_dp_error(raw_trace: dict, *expected_terms: str) -> None:
        errors = _process_errors_for(raw_trace)
        assert any(all(term in error for term in expected_terms) for error in errors), errors

    house_robber_contract = {
        "containers": ["dp"],
        "answer_position": "dp[2]",
        "expected_targets": ["dp[2]"],
        "subfamily": "house_robber",
    }
    assert_dp_error(
        _dp_contract_trace(
            "打家劫舍 DP 错误转移",
            {"nums": [2, 7, 9]},
            11,
            [
                _dp_contract_event(0, "create", ["dp"], state={"nums": [2, 7, 9], "dp": [2, 7, 0], "i": 1, "formula": "dp[1]=max(nums[0], nums[1])", "dp_contract": house_robber_contract}),
                _dp_contract_event(1, "set", ["dp[2]"], value=99, before=0, deps=["dp[1]", "dp[0]", "nums[2]"], state={"nums": [2, 7, 9], "dp": [2, 7, 99], "i": 2, "formula": "dp[i]=max(dp[i-1], dp[i-2]+nums[i])", "dp_contract": house_robber_contract}),
                _dp_contract_event(2, "mark", ["dp[2]"], value=99, deps=["dp[2]"], role="answer", state={"nums": [2, 7, 9], "dp": [2, 7, 99], "i": 2, "answer": 99, "formula": "answer=dp[2]", "dp_contract": house_robber_contract}),
            ],
        ),
        "打家劫舍",
        "不满足",
    )

    unique_paths_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1][1]",
        "expected_targets": ["dp[1][1]"],
        "subfamily": "unique_paths",
    }
    assert_dp_error(
        _dp_contract_trace(
            "不同路径 DP 错误转移",
            {"m": 2, "n": 2},
            2,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [[1, 1], [1, 0]], "i": 0, "j": 0, "formula": "boundary=1", "dp_contract": unique_paths_contract}),
                _dp_contract_event(1, "set", ["dp[1][1]"], value=3, before=0, deps=["dp[0][1]", "dp[1][0]"], state={"dp": [[1, 1], [1, 3]], "i": 1, "j": 1, "formula": "dp[i][j]=dp[i-1][j]+dp[i][j-1]", "dp_contract": unique_paths_contract}),
                _dp_contract_event(2, "mark", ["dp[1][1]"], value=3, deps=["dp[1][1]"], role="answer", state={"dp": [[1, 1], [1, 3]], "i": 1, "j": 1, "answer": 3, "formula": "answer=dp[1][1]", "dp_contract": unique_paths_contract}),
            ],
        ),
        "不同路径",
        "不满足",
    )

    subset_contract = {
        "containers": ["dp"],
        "answer_position": "dp[11]",
        "expected_targets": ["dp[5]"],
        "subfamily": "knapsack_01",
    }
    assert_dp_error(
        _dp_contract_trace(
            "0-1 背包可达性错误",
            {"nums": [1, 5, 11, 5]},
            True,
            [
                _dp_contract_event(0, "create", ["dp"], state={"nums": [1, 5, 11, 5], "target": 11, "dp": [True] + [False] * 11, "i": -1, "formula": "dp[0]=True", "dp_contract": subset_contract}),
                _dp_contract_event(1, "set", ["dp[5]"], value=True, before=False, deps=["dp[4]", "nums[0]"], state={"nums": [1, 5, 11, 5], "target": 11, "dp": [True, True, False, False, False, True, False, False, False, False, False, False], "i": 0, "capacity_index": 5, "formula": "dp[j]=dp[j] or dp[j-num]", "dp_contract": subset_contract}),
                _dp_contract_event(2, "mark", ["dp[11]"], value=True, deps=["dp[11]"], role="answer", state={"nums": [1, 5, 11, 5], "target": 11, "dp": [True, True, False, False, False, True, False, False, False, False, False, True], "i": 0, "capacity_index": 11, "answer": True, "formula": "answer=dp[target]", "dp_contract": subset_contract}),
            ],
        ),
        "0-1 背包",
        "不满足",
    )

    complete_contract = {
        "containers": ["dp"],
        "answer_position": "dp[3]",
        "expected_targets": ["dp[3]"],
        "subfamily": "complete_knapsack",
    }
    assert_dp_error(
        _dp_contract_trace(
            "完全背包零钱兑换错误",
            {"coins": [2], "amount": 3},
            -1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"coins": [2], "amount": 3, "dp": [0, -1, -1, -1], "i": -1, "formula": "dp[0]=0", "dp_mode": "complete_min", "dp_contract": complete_contract}),
                _dp_contract_event(1, "set", ["dp[3]"], value=1, before=-1, deps=["dp[1]", "coins[0]"], state={"coins": [2], "amount": 3, "dp": [0, -1, 1, 1], "i": 0, "capacity_index": 3, "formula": "dp[j]=min(dp[j], dp[j-coin]+1)", "dp_mode": "complete_min", "dp_contract": complete_contract}),
                _dp_contract_event(2, "mark", ["dp[3]"], value=1, deps=["dp[3]"], role="answer", state={"coins": [2], "amount": 3, "dp": [0, -1, 1, 1], "i": 0, "capacity_index": 3, "answer": 1, "formula": "answer=dp[amount]", "dp_mode": "complete_min", "dp_contract": complete_contract}),
            ],
        ),
        "完全背包",
        "不满足",
    )

    lcs_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1][1]",
        "expected_targets": ["dp[1][1]"],
        "subfamily": "lcs",
    }
    assert_dp_error(
        _dp_contract_trace(
            "LCS 错误转移",
            {"text1": "a", "text2": "a"},
            1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [[0, 0], [0, 0]], "i": 0, "j": 0, "formula": "boundary=0", "dp_contract": lcs_contract}),
                _dp_contract_event(1, "set", ["dp[1][1]"], value=0, before=0, deps=["dp[0][0]", "text1[0]", "text2[0]"], state={"dp": [[0, 0], [0, 0]], "i": 1, "j": 1, "formula": "dp[i][j]=dp[i-1][j-1]+1", "dp_contract": lcs_contract}),
                _dp_contract_event(2, "mark", ["dp[1][1]"], value=0, deps=["dp[1][1]"], role="answer", state={"dp": [[0, 0], [0, 0]], "i": 1, "j": 1, "answer": 0, "formula": "answer=dp[m][n]", "dp_contract": lcs_contract}),
            ],
        ),
        "LCS",
        "不满足",
    )

    edit_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1][1]",
        "expected_targets": ["dp[1][1]"],
        "subfamily": "edit_distance",
    }
    assert_dp_error(
        _dp_contract_trace(
            "编辑距离错误转移",
            {"word1": "a", "word2": "b"},
            1,
            [
                _dp_contract_event(0, "create", ["dp"], state={"dp": [[0, 1], [1, 0]], "i": 0, "j": 0, "formula": "boundary=i or j", "dp_contract": edit_contract}),
                _dp_contract_event(1, "set", ["dp[1][1]"], value=0, before=0, deps=["dp[0][1]", "dp[1][0]", "dp[0][0]"], state={"dp": [[0, 1], [1, 0]], "i": 1, "j": 1, "formula": "dp[i][j]=min(delete, insert, replace)+1", "dp_contract": edit_contract}),
                _dp_contract_event(2, "mark", ["dp[1][1]"], value=0, deps=["dp[1][1]"], role="answer", state={"dp": [[0, 1], [1, 0]], "i": 1, "j": 1, "answer": 0, "formula": "answer=dp[m][n]", "dp_contract": edit_contract}),
            ],
        ),
        "编辑距离",
        "不满足",
    )

    interval_contract = {
        "containers": ["dp"],
        "answer_position": "dp[0][1]",
        "expected_targets": ["dp[0][1]"],
        "subfamily": "interval_dp",
    }
    assert_dp_error(
        _dp_contract_trace(
            "区间 DP 合并石子错误转移",
            {"stones": [1, 2]},
            3,
            [
                _dp_contract_event(0, "create", ["dp"], state={"stones": [1, 2], "dp": [[0, 0], [0, 0]], "i": 0, "j": 0, "formula": "dp[i][i]=0", "dp_mode": "merge_stones", "dp_contract": interval_contract}),
                _dp_contract_event(1, "set", ["dp[0][1]"], value=4, before=0, deps=["dp[0][0]", "dp[1][1]"], state={"stones": [1, 2], "dp": [[0, 4], [0, 0]], "i": 0, "j": 1, "k": 0, "formula": "dp[i][j]=min(dp[i][k]+dp[k+1][j])+sum(i,j)", "dp_mode": "merge_stones", "dp_contract": interval_contract}),
                _dp_contract_event(2, "mark", ["dp[0][1]"], value=4, deps=["dp[0][1]"], role="answer", state={"stones": [1, 2], "dp": [[0, 4], [0, 0]], "i": 0, "j": 1, "answer": 4, "formula": "answer=dp[0][n-1]", "dp_mode": "merge_stones", "dp_contract": interval_contract}),
            ],
        ),
        "区间 DP",
        "不满足",
    )

    tree_contract = {
        "containers": ["dp_take", "dp_skip"],
        "answer_position": "dp_take[1]",
        "expected_targets": ["dp_take[1]"],
        "subfamily": "tree_max_independent_set",
    }
    tree = {"nodes": [{"id": "1", "value": 3}], "edges": []}
    assert_dp_error(
        _dp_contract_trace(
            "树形 DP 错误转移",
            {"tree": tree},
            3,
            [
                _dp_contract_event(0, "create", ["tree"], state={"tree": tree, "current": "1", "dp_take": {}, "dp_skip": {}, "formula": "postorder tree dp", "dp_contract": tree_contract}),
                _dp_contract_event(1, "set", ["dp_take[1]"], value=4, before=None, deps=["node:1", "dp_skip[1]"], state={"tree": tree, "current": "1", "dp_take": {"1": 4}, "dp_skip": {"1": 0}, "formula": "dp_take[u]=weight[u]+sum(dp_skip[child])", "dp_contract": tree_contract}),
                _dp_contract_event(2, "mark", ["dp_take[1]"], value=4, deps=["dp_take[1]"], role="answer", state={"tree": tree, "current": "1", "dp_take": {"1": 4}, "dp_skip": {"1": 0}, "answer": 4, "formula": "answer=max(dp_take[root], dp_skip[root])", "dp_contract": tree_contract}),
            ],
        ),
        "树形 DP",
        "应为",
    )

    bitmask_contract = {
        "containers": ["dp"],
        "answer_position": "dp[3]",
        "expected_targets": ["dp[1]", "dp[3]"],
        "subfamily": "state_compression",
    }
    assert_dp_error(
        _dp_contract_trace(
            "状态压缩 DP 合同缺少依赖",
            {"item_count": 2},
            2,
            [
                _dp_contract_event(0, "create", ["dp"], state={"item_count": 2, "dp": [0, 0, 0, 0], "mask": 0, "formula": "dp[0]=0", "dp_contract": bitmask_contract}),
                _dp_contract_event(1, "set", ["dp[1]"], value=1, before=0, deps=[], state={"item_count": 2, "dp": [0, 1, 0, 0], "mask": 1, "formula": "dp[mask]=popcount(mask)", "dp_contract": bitmask_contract}),
                _dp_contract_event(2, "set", ["dp[3]"], value=2, before=0, deps=["dp[1]"], state={"item_count": 2, "dp": [0, 1, 0, 2], "mask": 3, "formula": "dp[mask]=popcount(mask)", "dp_contract": bitmask_contract}),
                _dp_contract_event(3, "mark", ["dp[3]"], value=2, deps=["dp[3]"], role="answer", state={"item_count": 2, "dp": [0, 1, 0, 2], "mask": 3, "answer": 2, "formula": "answer=dp[(1<<n)-1]", "dp_contract": bitmask_contract}),
            ],
        ),
        "DP contract",
        "deps",
    )

    digit_contract = {
        "containers": ["dp"],
        "answer_position": "dp[1]",
        "expected_targets": ["dp[1]"],
        "subfamily": "digit_dp",
    }
    digit_errors = _process_errors_for(
        _dp_contract_trace(
            "数位 DP 统计不含 7 的数字",
            {"n": 20},
            18,
            [
                _dp_contract_event(
                    0,
                    "create",
                    ["dp"],
                    state={"digits": [2, 0], "dp": [1, 0], "digit": 0, "tight": True, "formula": "dp[0]=1", "dp_contract": digit_contract},
                    reason="初始化数位 DP。",
                ),
                _dp_contract_event(
                    1,
                    "set",
                    ["dp[1]"],
                    value=19,
                    before=0,
                    deps=["dp[0]"],
                    state={"digits": [2, 0], "dp": [1, 19], "digit": 1, "tight": False, "formula": "dp[pos+1]+=dp[pos]*valid_choices", "dp_contract": digit_contract},
                    reason="错误地把数字 7 也计入可选分支。",
                ),
                _dp_contract_event(
                    2,
                    "mark",
                    ["dp[1]"],
                    value=19,
                    deps=["dp[1]"],
                    role="answer",
                    state={"digits": [2, 0], "dp": [1, 19], "digit": 1, "answer": 19, "formula": "answer=dp[1]", "dp_contract": digit_contract},
                    reason="返回错误计数。",
                ),
            ],
        )
    )
    assert any("数位 DP" in error and "应为" in error for error in digit_errors), digit_errors

    bounded_contract = {
        "containers": ["dp"],
        "answer_position": "dp[5]",
        "expected_targets": ["dp[5]"],
        "subfamily": "bounded_knapsack",
    }
    bounded_errors = _process_errors_for(
        _dp_contract_trace(
            "多重背包最大价值",
            {"weights": [2], "values": [3], "counts": [2], "capacity": 5},
            6,
            [
                _dp_contract_event(
                    0,
                    "create",
                    ["dp"],
                    state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 0, 0, 0, 0], "i": -1, "formula": "dp[c]=0", "dp_contract": bounded_contract},
                    reason="初始化多重背包 DP。",
                ),
                _dp_contract_event(
                    1,
                    "set",
                    ["dp[5]"],
                    value=9,
                    before=0,
                    deps=["dp[1]", "weights[0]", "values[0]"],
                    state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 3, 3, 6, 9], "i": 0, "capacity_index": 5, "formula": "dp[c]=max(dp[c], prev[c-k*w]+k*v)", "dp_contract": bounded_contract},
                    reason="错误地使用超过 count 的物品数量。",
                ),
                _dp_contract_event(
                    2,
                    "mark",
                    ["dp[5]"],
                    value=9,
                    deps=["dp[5]"],
                    role="answer",
                    state={"weights": [2], "values": [3], "counts": [2], "capacity": 5, "dp": [0, 0, 3, 3, 6, 9], "i": 0, "capacity_index": 5, "answer": 9, "formula": "answer=dp[capacity]", "dp_contract": bounded_contract},
                    reason="返回错误最大价值。",
                ),
            ],
        )
    )
    assert any("多重背包" in error and "应为" in error for error in bounded_errors), bounded_errors


def test_phase13_graph_validator_expands_core_shortest_mst_samples_and_rejects_process_errors():
    profiles = {
        profile.family: profile
        for profile in __import__(
            "algolab.verification.process_validator",
            fromlist=["process_validation_registry"],
        ).process_validation_registry()
    }
    assert "bfs" in profiles
    assert profiles["bfs"].status == "strong"
    assert "shortest_path_mst" in profiles
    assert profiles["shortest_path_mst"].status == "strong"

    basic_graph_cases = [
        case
        for case in benchmark_cases()
        if case.gate_layer == "family_core" and case.family_id == "basic_graph"
    ]
    basic_graph_samples = [sample for case in basic_graph_cases for sample in case.samples]
    basic_graph_subfamilies = {case.subfamily_id for case in basic_graph_cases}
    assert len(basic_graph_samples) >= 22
    assert {
        "bfs_shortest_layers",
        "dfs_traversal",
        "connected_components",
        "topological_sort",
        "bipartite_coloring",
    } <= basic_graph_subfamilies

    shortest_mst_cases = [
        case
        for case in benchmark_cases()
        if case.gate_layer == "family_core" and case.family_id == "shortest_path_mst"
    ]
    shortest_mst_samples = [sample for case in shortest_mst_cases for sample in case.samples]
    shortest_mst_subfamilies = {case.subfamily_id for case in shortest_mst_cases}
    assert len(shortest_mst_samples) >= 18
    assert {
        "dijkstra",
        "bellman_ford",
        "floyd_warshall",
        "zero_one_bfs",
        "kruskal_mst",
    } <= shortest_mst_subfamilies

    wrong_dijkstra_relax = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Dijkstra wrong relax",
            {"weighted_graph": {"A": [["B", 2]], "B": []}, "start": "A"},
            {"A": 0, "B": 2},
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["heap"],
                    state={
                        "weighted_graph": {"A": [["B", 2]], "B": []},
                        "heap": [[0, "A"]],
                        "dist": {"A": 0},
                        "parent": {},
                        "graph_contract": {"submode": "dijkstra", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="初始化 Dijkstra 堆。",
                ),
                _graph_contract_event(
                    1,
                    "set",
                    ["dist[B]"],
                    value=3,
                    after=3,
                    deps=["dist[A]", "edge:A->B"],
                    state={
                        "weighted_graph": {"A": [["B", 2]], "B": []},
                        "heap": [[3, "B"]],
                        "dist": {"A": 0, "B": 3},
                        "parent": {"B": "A"},
                        "old_dist": None,
                        "new_dist": 3,
                        "current": "A",
                        "neighbor": "B",
                        "weight": 2,
                        "graph_contract": {"submode": "dijkstra", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="错误松弛 Dijkstra 距离。",
                ),
            ],
        )
    )
    assert any("Dijkstra" in error and "dist[B]" in error for error in wrong_dijkstra_relax), wrong_dijkstra_relax

    wrong_bellman_relax = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Bellman-Ford wrong relax",
            {"edges": [["A", "B", 2]], "start": "A"},
            {"A": 0, "B": 2},
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["dist"],
                    state={
                        "edges": [["A", "B", 2]],
                        "dist": {"A": 0, "B": float("inf")},
                        "round": 0,
                        "graph_contract": {"submode": "bellman_ford", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="初始化 Bellman-Ford 距离。",
                ),
                _graph_contract_event(
                    1,
                    "set",
                    ["dist[B]"],
                    value=5,
                    before=float("inf"),
                    after=5,
                    deps=["dist[A]", "edge:A->B"],
                    state={
                        "edges": [["A", "B", 2]],
                        "dist": {"A": 0, "B": 5},
                        "round": 1,
                        "current_edge": ["A", "B", 2],
                        "old_dist": float("inf"),
                        "new_dist": 5,
                        "graph_contract": {"submode": "bellman_ford", "source": "A", "expected_relax_edges": ["A->B"]},
                    },
                    reason="错误松弛 Bellman-Ford 距离。",
                ),
            ],
        )
    )
    assert any("Bellman-Ford" in error and "dist[B]" in error for error in wrong_bellman_relax), wrong_bellman_relax

    wrong_floyd_phase = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Floyd wrong transition",
            {"dist": [[0, 2, 9], [2, 0, 3], [9, 3, 0]]},
            [[0, 2, 5], [2, 0, 3], [5, 3, 0]],
            [
                _graph_contract_event(
                    0,
                    "set",
                    ["dist[0][2]"],
                    value=6,
                    before=9,
                    after=6,
                    deps=["dist[0][1]", "dist[1][2]"],
                    state={
                        "dist": [[0, 2, 6], [2, 0, 3], [9, 3, 0]],
                        "k": 1,
                        "i": 0,
                        "j": 2,
                        "graph_contract": {"submode": "floyd_warshall", "expected_relax_edges": ["0->2"]},
                    },
                    reason="错误 Floyd 中转松弛。",
                )
            ],
        )
    )
    assert any("Floyd" in error and "dist[0][2]" in error for error in wrong_floyd_phase), wrong_floyd_phase

    wrong_topo_indegree = _process_errors_for(
        _graph_contract_trace(
            "P13.3 topo wrong indegree",
            {"graph": {"A": ["B"], "B": []}},
            ["A", "B"],
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["queue"],
                    state={
                        "graph": {"A": ["B"], "B": []},
                        "queue": ["A"],
                        "indegree": {"A": 0, "B": 1},
                        "topo_order": [],
                        "graph_contract": {"submode": "topological_sort", "expected_nodes": ["A", "B"]},
                    },
                    reason="初始化拓扑入度。",
                ),
                _graph_contract_event(
                    1,
                    "set",
                    ["indegree[B]"],
                    value=1,
                    before=1,
                    after=1,
                    deps=["edge:A->B"],
                    state={
                        "graph": {"A": ["B"], "B": []},
                        "queue": ["B"],
                        "indegree": {"A": 0, "B": 1},
                        "topo_order": ["A"],
                        "current": "A",
                        "graph_contract": {"submode": "topological_sort", "expected_nodes": ["A", "B"]},
                    },
                    reason="错误地没有降低 B 的入度却让它入队。",
                ),
            ],
        )
    )
    assert any("topological_sort" in error and "indegree[B]" in error for error in wrong_topo_indegree), wrong_topo_indegree

    wrong_mst_cycle = _process_errors_for(
        _graph_contract_trace(
            "P13.3 Kruskal wrong selected cycle",
            {"edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]]},
            2,
            [
                _graph_contract_event(
                    0,
                    "create",
                    ["union_find"],
                    state={
                        "edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]],
                        "mst_edges": [["A", "B", 1], ["B", "C", 1], ["A", "C", 1]],
                        "union_find": {"parent": {"A": "A", "B": "A", "C": "A"}},
                        "edge_decision": "selected",
                        "graph_contract": {"submode": "mst", "expected_edges": ["A-B", "B-C"]},
                    },
                    reason="错误地选择了形成环的边。",
                )
            ],
        )
    )
    assert any("MST" in error and "环" in error for error in wrong_mst_cycle), wrong_mst_cycle


def test_phase13_string_validator_expands_core_samples_and_rejects_process_errors():
    profiles = {profile.family: profile for profile in __import__("algolab.verification.process_validator", fromlist=["process_validation_registry"]).process_validation_registry()}
    assert "string" in profiles
    assert profiles["string"].status == "strong"
    assert "_validate_string_sliding_window" in profiles["string"].checks
    assert "_validate_trie_prefix_match" in profiles["string"].checks

    string_cases = [
        case
        for case in benchmark_cases()
        if case.family_id == "string_advanced"
    ]
    string_subfamilies = {case.subfamily_id for case in string_cases}
    assert {
        "kmp",
        "rabin_karp",
        "z_algorithm",
        "manacher",
        "string_sliding_window",
        "trie_prefix_match",
    } <= string_subfamilies
    assert len(string_cases) >= 6
    assert sum(len(case.samples) for case in string_cases) >= 18
    oracle_module = __import__("tests.oracles", fromlist=["string_unique_window_reference", "trie_prefix_count_reference"])
    referenced_cases = {case.id: case for case in string_cases if case.oracle_reference}
    for case in referenced_cases.values():
        _, reference_name = case.oracle_reference.rsplit(".", 1)
        reference = getattr(oracle_module, reference_name)
        for sample in case.samples:
            assert reference(sample.input_data) == sample.expected

    capability = next(
        entry
        for entry in __import__("scripts.check_family_capabilities", fromlist=["load_family_capabilities"]).load_family_capabilities()["families"]
        if entry["family_id"] == "string_advanced"
    )
    assert set(capability["core_subfamilies"]) >= {
        "kmp",
        "rabin_karp",
        "z_algorithm",
        "manacher",
        "string_sliding_window",
        "trie_prefix_match",
    }
    assert capability["benchmark_target"]["min_cases"] >= 6
    assert capability["benchmark_target"]["min_samples"] >= 18

    wrong_prefix_errors = _process_errors_for(
        _family_contract_trace(
            "KMP 字符串匹配",
            {"text": "ababaca", "pattern": "ababaca"},
            0,
            [
                _family_contract_event(
                    0,
                    "create",
                    ["text", "pattern", "pi"],
                    state={"text": "ababaca", "pattern": "ababaca", "i": 0, "j": 0, "pi": [0, 0, 0, 0, 0, 0, 0], "family_contract": {"family": "string", "submode": "kmp", "expected_tables": ["pi"]}},
                    reason="初始化 KMP 前缀表。",
                ),
                _family_contract_event(
                    1,
                    "set",
                    ["pi[5]"],
                    value=4,
                    deps=["pattern[5]", "pi[4]"],
                    state={"text": "ababaca", "pattern": "ababaca", "i": 5, "j": 4, "pi": [0, 0, 1, 2, 3, 4, 0], "fallback_reason": "失配后应该按 pi 回退。", "family_contract": {"family": "string", "submode": "kmp", "expected_tables": ["pi"]}},
                    reason="错误写入 KMP 前缀表。",
                ),
            ],
        )
    )
    assert any("KMP 前缀函数" in error for error in wrong_prefix_errors), wrong_prefix_errors

    wrong_window_errors = _process_errors_for(
        _family_contract_trace(
            "字符串滑动窗口最长无重复子串",
            {"text": "abba"},
            2,
            [
                _family_contract_event(
                    0,
                    "create",
                    ["text", "window_counts"],
                    state={"text": "abba", "pattern": "", "i": 0, "j": 0, "left": 0, "right": -1, "window_counts": {}, "best": 0, "family_contract": {"family": "string", "submode": "string_sliding_window", "expected_tables": ["window_counts"]}},
                    reason="初始化字符串滑动窗口。",
                ),
                _family_contract_event(
                    1,
                    "move",
                    ["pointer:right"],
                    value=0,
                    deps=["text[0]"],
                    state={"text": "abba", "pattern": "", "i": 0, "j": 0, "left": 0, "right": 0, "window_counts": {"a": 1}, "best": 1, "window_reason": "窗口右端纳入 text[0]。", "family_contract": {"family": "string", "submode": "string_sliding_window", "expected_tables": ["window_counts"]}},
                    reason="窗口右端移动。",
                ),
                _family_contract_event(
                    2,
                    "move",
                    ["pointer:right"],
                    value=2,
                    deps=["text[2]"],
                    state={"text": "abba", "pattern": "", "i": 2, "j": 0, "left": 0, "right": 2, "window_counts": {"a": 1, "b": 1}, "best": 3, "window_reason": "错误跳过 text[1]。", "family_contract": {"family": "string", "submode": "string_sliding_window", "expected_tables": ["window_counts"]}},
                    reason="错误窗口移动。",
                ),
            ],
        )
    )
    assert any("字符串滑动窗口" in error and ("跳变" in error or "window_counts" in error) for error in wrong_window_errors), wrong_window_errors

    wrong_trie_errors = _process_errors_for(
        _family_contract_trace(
            "Trie 前缀匹配字符串路径",
            {"words": ["apple", "app"], "prefix": "ap"},
            2,
            [
                _family_contract_event(
                    0,
                    "create",
                    ["trie"],
                    state={"text": "ap", "pattern": "ap", "i": 0, "j": 0, "words": ["apple", "app"], "prefix": "ap", "trie": {"nodes": [{"id": "root", "label": "root", "meta": {"count": 2}}], "edges": []}, "prefix_count": 2, "family_contract": {"family": "string", "submode": "trie_prefix_match", "expected_tables": ["prefix_count"]}},
                    reason="初始化 Trie 前缀匹配。",
                ),
                _family_contract_event(
                    1,
                    "mark",
                    ["node:root_a"],
                    value=2,
                    deps=["text[0]"],
                    role="answer",
                    state={"text": "ap", "pattern": "ap", "i": 0, "j": 0, "words": ["apple", "app"], "prefix": "ap", "trie": {"nodes": [{"id": "root", "label": "root", "meta": {"count": 2}}, {"id": "root_a", "label": "a", "meta": {"count": 2}}], "edges": [["root", "root_a"]]}, "prefix_count": 2, "answer": 2, "family_contract": {"family": "string", "submode": "trie_prefix_match", "expected_tables": ["prefix_count"]}},
                    reason="错误地只走到前缀第一个字符。",
                ),
            ],
        )
    )
    assert any("Trie 前缀匹配" in error for error in wrong_trie_errors), wrong_trie_errors


def test_phase13_tree_backtracking_trie_heap_validator_expands_samples_and_rejects_process_errors():
    profiles = {
        profile.family: profile
        for profile in __import__(
            "algolab.verification.process_validator",
            fromlist=["process_validation_registry"],
        ).process_validation_registry()
    }

    for family in ("tree", "heap", "trie", "backtracking"):
        assert family in profiles
        assert profiles[family].status == "strong"
    assert "_validate_heap_property" in profiles["heap"].checks
    assert "_validate_trie_prefix_count" in profiles["trie"].checks
    assert "_validate_backtracking_tree" in profiles["backtracking"].checks
    assert "_validate_recursion_frame_balance" in profiles["backtracking"].checks
    assert "_validate_recursion_frame_balance" in profiles["tree"].checks

    cases = benchmark_cases()
    tree_samples = sum(
        len(case.samples)
        for case in cases
        if case.family_id in {"tree_bst_lca", "tree_dp"}
    )
    backtracking_cases = [case for case in cases if case.family_id == "backtracking_recursion"]
    heap_cases = [case for case in cases if case.family_id == "heap_topk_huffman"]
    trie_cases = [case for case in cases if case.family_id == "trie"]

    assert tree_samples >= 18
    assert sum(len(case.samples) for case in backtracking_cases) >= 12
    assert sum(len(case.samples) for case in heap_cases) >= 8
    assert sum(len(case.samples) for case in trie_cases) >= 8
    assert {case.process_profile for case in backtracking_cases} == {"backtracking"}
    assert {case.process_profile for case in heap_cases} == {"heap"}
    assert {case.process_profile for case in trie_cases} == {"trie"}
    assert {case.support_level for case in backtracking_cases} == {"medium_plus"}
    assert {case.support_level for case in heap_cases} == {"medium_plus"}
    assert {case.support_level for case in trie_cases} == {"medium_plus"}

    capabilities = {
        entry["family_id"]: entry
        for entry in __import__(
            "scripts.check_family_capabilities",
            fromlist=["load_family_capabilities"],
        ).load_family_capabilities()["families"]
    }
    assert (
        capabilities["tree_bst_lca"]["benchmark_target"]["min_samples"]
        + capabilities["tree_dp"]["benchmark_target"]["min_samples"]
        >= 18
    )
    assert capabilities["backtracking_recursion"]["process_profile"] == "backtracking"
    assert capabilities["backtracking_recursion"]["benchmark_target"]["min_samples"] >= 12
    assert capabilities["heap_topk_huffman"]["process_profile"] == "heap"
    assert capabilities["heap_topk_huffman"]["benchmark_target"]["min_samples"] >= 8
    assert capabilities["trie"]["process_profile"] == "trie"
    assert capabilities["trie"]["benchmark_target"]["min_samples"] >= 8

    wrong_frame_errors = _process_errors_for(
        _family_contract_trace(
            "树递归跳帧",
            {"tree": {"nodes": [{"id": "A"}, {"id": "B"}], "edges": [["A", "B"]]}},
            ["A", "B"],
            [
                _family_contract_event(
                    0,
                    "enter",
                    ["frame:dfs(A)"],
                    deps=["node:A"],
                    state={
                        "tree": {"nodes": [{"id": "A"}, {"id": "B"}], "edges": [["A", "B"]]},
                        "call_stack": ["A"],
                        "family_contract": {"family": "tree", "submode": "inorder_traversal"},
                    },
                    reason="进入 A。",
                ),
                _family_contract_event(
                    1,
                    "exit",
                    ["frame:dfs(B)"],
                    deps=["node:B"],
                    state={
                        "tree": {"nodes": [{"id": "A"}, {"id": "B"}], "edges": [["A", "B"]]},
                        "call_stack": [],
                        "family_contract": {"family": "tree", "submode": "inorder_traversal"},
                    },
                    reason="错误地退出未进入的 B。",
                ),
            ],
        )
    )
    assert any("frame:dfs(B)" in error and "未进入" in error for error in wrong_frame_errors), wrong_frame_errors

    wrong_backtracking_errors = _process_errors_for(
        _family_contract_trace(
            "全排列回溯 used/path 跳变",
            {"nums": [1, 2]},
            [],
            [
                _family_contract_event(
                    0,
                    "create",
                    ["recursion_tree"],
                    state={
                        "nums": [1, 2],
                        "path": [],
                        "used": [False, False],
                        "call_stack": ["root"],
                        "recursion_tree": {"nodes": [{"id": "root", "label": "[]"}], "edges": []},
                        "family_contract": {"family": "backtracking", "submode": "permutations"},
                    },
                    reason="初始化回溯。",
                ),
                _family_contract_event(
                    1,
                    "enter",
                    ["frame:perm(root_0)"],
                    deps=["node:root"],
                    state={
                        "nums": [1, 2],
                        "path": [1, 2],
                        "used": [True, False],
                        "call_stack": ["root", "root_0"],
                        "recursion_tree": {
                            "nodes": [{"id": "root", "label": "[]"}, {"id": "root_0", "label": "[1, 2]"}],
                            "edges": [["root", "root_0"]],
                        },
                        "family_contract": {"family": "backtracking", "submode": "permutations"},
                    },
                    reason="错误地一次跳过两层选择。",
                ),
            ],
        )
    )
    assert any(("回溯" in error or "backtracking" in error) and ("used" in error or "path" in error) for error in wrong_backtracking_errors), wrong_backtracking_errors
    assert any("frame:perm(root_0)" in error and "缺少 exit" in error for error in wrong_backtracking_errors), wrong_backtracking_errors

    wrong_heap_errors = _process_errors_for(
        _family_contract_trace(
            "TopK 小顶堆错误",
            {"nums": [3, 1, 2], "k": 2},
            2,
            [
                _family_contract_event(
                    0,
                    "create",
                    ["heap"],
                    state={
                        "nums": [3, 1, 2],
                        "k": 2,
                        "heap": [3, 1],
                        "heap_type": "min",
                        "family_contract": {"family": "heap", "submode": "topk_min_heap"},
                    },
                    reason="错误的小顶堆状态。",
                )
            ],
        )
    )
    assert any("小顶堆" in error for error in wrong_heap_errors), wrong_heap_errors

    wrong_trie_errors = _process_errors_for(
        _family_contract_trace(
            "Trie 前缀计数错误",
            {"words": ["apple", "app", "bat"], "prefix": "app"},
            2,
            [
                _family_contract_event(
                    0,
                    "mark",
                    ["node:root_a_1_p_2_p_3"],
                    value=3,
                    state={
                        "words": ["apple", "app", "bat"],
                        "prefix": "app",
                        "prefix_count": 3,
                        "answer": 3,
                        "trie": {
                            "nodes": [
                                {"id": "root", "label": "root", "meta": {"count": 3}},
                                {"id": "root_a_1", "label": "a", "meta": {"count": 2}},
                                {"id": "root_a_1_p_2", "label": "p", "meta": {"count": 2}},
                                {"id": "root_a_1_p_2_p_3", "label": "p", "meta": {"count": 3, "terminal": True}},
                            ],
                            "edges": [["root", "root_a_1"], ["root_a_1", "root_a_1_p_2"], ["root_a_1_p_2", "root_a_1_p_2_p_3"]],
                        },
                        "family_contract": {"family": "trie", "submode": "prefix_count"},
                    },
                    role="answer",
                    reason="错误地把 app 前缀计数写成 3。",
                )
            ],
        )
    )
    assert any("Trie" in error and "prefix_count" in error for error in wrong_trie_errors), wrong_trie_errors


def test_process_validator_rejects_missing_key_step_coverage_for_small_traces():
    dp_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "不同路径",
            "input_data": {"m": 2, "n": 2},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "dp"}],
                    "state": {"dp": [[1, 1], [1, 2]]},
                    "reason": "只展示最终 DP 表。",
                    "code_line": 1,
                }
            ],
        }
    )
    bfs_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "BFS 最短层数",
            "input_data": {"graph": {"A": ["B"], "B": []}, "start": "A"},
            "result": {"A": 0, "B": 1},
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "queue"}, {"id": "node:A"}],
                    "state": {"graph": {"A": ["B"], "B": []}, "queue": [], "dist": {"A": 0, "B": 1}},
                    "reason": "只展示 BFS 最终距离。",
                    "code_line": 1,
                }
            ],
        }
    )
    binary_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分查找",
            "input_data": {"nums": [1, 3, 5], "target": 5},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "nums"}],
                    "state": {"nums": [1, 3, 5], "left": 2, "right": 2, "target": 5},
                    "reason": "只展示最终搜索区间。",
                    "code_line": 1,
                }
            ],
        }
    )
    stack_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "每日温度",
            "input_data": {"temperatures": [30, 40]},
            "result": [1, 0],
            "events": [
                {
                    "step": 0,
                    "op": "create",
                    "targets": [{"id": "temperatures"}, {"id": "stack"}, {"id": "answer"}],
                    "state": {
                        "temperatures": [30, 40],
                        "stack": [],
                        "answer": [1, 0],
                        "stack_order": "decreasing",
                    },
                    "reason": "只展示最终答案。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("不同路径小 DP 表缺少逐帧状态转移" in error for error in dp_errors)
    assert any("BFS 小图缺少关键步骤覆盖" in error for error in bfs_errors)
    assert any("二分缺少关键步骤覆盖" in error for error in binary_errors)
    assert any("单调栈缺少关键步骤覆盖" in error for error in stack_errors)
    assert classify_failure("failure_type=coverage_error: BFS 小图缺少关键步骤覆盖：check_edge") == "coverage_error"


def test_process_validator_rejects_bad_string_algorithm_tables():
    rabin_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Rabin-Karp 滚动哈希",
            "input_data": {"text": "abcd", "pattern": "bc"},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "window_hashes[1]"}],
                    "state": {
                        "text": "abcd",
                        "pattern": "bc",
                        "pattern_hash": 99,
                        "window_hashes": [10, 999, 30],
                    },
                    "reason": "错误滚动哈希。",
                    "code_line": 1,
                }
            ],
        }
    )
    z_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Z Algorithm",
            "input_data": {"text": "aabcaabx"},
            "result": [0, 1, 0, 0, 3, 1, 0, 0],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "z[4]"}],
                    "state": {"text": "aabcaabx", "z": [0, 1, 0, 0, 9, 1, 0, 0]},
                    "reason": "错误 Z 值。",
                    "code_line": 1,
                }
            ],
        }
    )
    manacher_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Manacher 回文半径",
            "input_data": {"text": "ababa"},
            "result": 5,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "radius[5]"}],
                    "state": {"text": "#a#b#a#b#a#", "radius": [0, 1, 0, 3, 0, 4, 0, 3, 0, 1, 0]},
                    "reason": "错误回文半径。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("Rabin-Karp" in error for error in rabin_errors), rabin_errors
    assert any("Z Algorithm" in error for error in z_errors), z_errors
    assert any("Manacher" in error for error in manacher_errors), manacher_errors


def test_convex_hull_trace_exposes_scan_phases_and_pop_steps():
    case = next(item for item in benchmark_cases() if item.id == "convex_hull")
    artifact, errors = materialize_case(case, sample_index=0)

    assert errors == []
    trace = artifact.variants[0].trace
    assert trace is not None
    events = trace.events
    states = [event.state for event in events]
    phases = [state.get("phase") for state in states]
    pop_events = [event for event in events if event.op.value == "pop"]
    current_values = [tuple(state.get("current")) for state in states if state.get("current") is not None]
    hull_snapshots = {
        tuple((state.get("geometry") or {}).get("hull") or [])
        for state in states
        if state.get("geometry")
    }
    scene = artifact.scenes[case.id]
    hull_edge_counts = [
        sum(1 for obj in frame.objects if obj.type.value == "edge" and obj.meta.get("shape") == "hull")
        for frame in scene.frames
    ]

    assert "lower" in phases
    assert "upper" in phases
    assert pop_events
    assert any("非左转" in event.reason for event in pop_events)
    assert len(set(current_values)) >= 3
    assert len(hull_snapshots) >= 4
    assert max(hull_edge_counts) > min(hull_edge_counts)


def test_phase7_string_algorithms_have_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "kmp": {"state_keys": {"text", "pattern", "pi"}, "target_prefix": "pi[", "reason_token": "回退"},
        "rabin_karp": {"state_keys": {"text", "pattern", "pattern_hash"}, "target_prefix": "window_hashes[", "reason_token": "哈希"},
        "z_algorithm": {"state_keys": {"text", "z"}, "target_prefix": "z[", "reason_token": "Z"},
        "manacher": {"state_keys": {"text", "radius"}, "target_prefix": "radius[", "reason_token": "半径"},
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert "string" in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        object_ids = {obj.id for frame in scene.frames for obj in frame.objects}
        for key in expectation["state_keys"]:
            assert key in object_ids, (case_id, key, sorted(object_ids)[:20])
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids), (case_id, target_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        assert expectation["reason_token"] in reasons, (case_id, reasons)

    example_names = {
        "string_kmp.md": ["string", "pi", "失配回退"],
        "string_rabin_karp.md": ["string", "pattern_hash", "滚动哈希"],
        "string_z_algorithm.md": ["string", "z", "Z-box"],
        "string_manacher.md": ["string", "radius", "半径扩展"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_tree_recursion_aggregates():
    diameter_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二叉树直径",
            "input_data": {
                "tree": {
                    "nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                    "edges": [["1", "2"], ["1", "3"]],
                }
            },
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "diameter[1]"}],
                    "state": {
                        "tree": {
                            "nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                            "edges": [["1", "2"], ["1", "3"]],
                        },
                        "current": "1",
                        "height": {"1": 2, "2": 1, "3": 1},
                        "diameter": {"1": 9, "2": 0, "3": 0},
                    },
                    "reason": "错误树直径聚合。",
                    "code_line": 1,
                }
            ],
        }
    )
    tree_dp_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树形 DP 最大独立集",
            "input_data": {
                "tree": {
                    "nodes": [{"id": "1", "value": 3}, {"id": "2", "value": 2}, {"id": "3", "value": 1}],
                    "edges": [["1", "2"], ["1", "3"]],
                }
            },
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "dp_take[1]"}],
                    "state": {
                        "tree": {
                            "nodes": [{"id": "1", "value": 3}, {"id": "2", "value": 2}, {"id": "3", "value": 1}],
                            "edges": [["1", "2"], ["1", "3"]],
                        },
                        "current": "1",
                        "dp_take": {"1": 99, "2": 2, "3": 1},
                        "dp_skip": {"1": 3, "2": 0, "3": 0},
                    },
                    "reason": "错误树形 DP 聚合。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("树直径" in error for error in diameter_errors), diameter_errors
    assert any("树形 DP" in error for error in tree_dp_errors), tree_dp_errors


def test_phase7_tree_recursion_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "binary_tree_inorder": {"layout": "tree", "state_keys": {"current", "call_stack", "return_values"}, "reason_token": "中序"},
        "lca": {"layout": "tree", "state_keys": {"current", "call_stack", "return_values"}, "reason_token": "最近公共祖先"},
        "tree_diameter": {"layout": "tree", "state_keys": {"current", "call_stack", "height", "diameter"}, "reason_token": "子树高度"},
        "tree_max_independent_set": {"layout": "tree", "state_keys": {"current", "call_stack", "dp_take", "dp_skip"}, "reason_token": "子树聚合"},
        "permutations": {"layout": "recursion_tree", "state_keys": {"path", "call_stack", "return_values"}, "reason_token": "撤销选择"},
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        target_ids = {target.id for event in artifact.variants[0].trace.events for target in event.targets}
        dep_ids = {dep.id for event in artifact.variants[0].trace.events for dep in event.deps}
        assert any(target.startswith("frame:") for target in target_ids), (case_id, target_ids)
        assert any(target.startswith("node:") for target in target_ids), (case_id, target_ids)
        assert any(dep.startswith("frame:") for dep in dep_ids), (case_id, dep_ids)
        assert any(dep.startswith("node:") for dep in dep_ids), (case_id, dep_ids)
        arrow_pairs = {(obj.source, obj.target) for frame in scene.frames for obj in frame.objects if obj.type.value == "arrow"}
        assert any(source.startswith("frame:") and target.startswith("node:") for source, target in arrow_pairs) or any(
            source.startswith("node:") and target.startswith("frame:") for source, target in arrow_pairs
        ), (case_id, arrow_pairs)
        reasons = "\n".join(event.reason or "" for event in artifact.variants[0].trace.events)
        assert expectation["reason_token"] in reasons, (case_id, reasons)

    example_names = {
        "tree_inorder.md": ["tree", "call_stack", "返回值"],
        "tree_lca.md": ["tree", "frame:", "最近公共祖先"],
        "tree_diameter.md": ["tree", "height", "diameter"],
        "tree_dp.md": ["tree", "dp_take", "子树聚合"],
        "recursion_permutations.md": ["recursion_tree", "path", "撤销选择"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_range_structure_tables():
    segment_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "线段树区间和",
            "input_data": {"nums": [2, 1, 4], "query": [0, 2], "update": [1, 3]},
            "result": {"before": 7, "after": 9},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "node:seg_1_0_2"}],
                    "state": {
                        "nums": [2, 1, 4],
                        "query": [0, 2],
                        "segment_tree": {
                            "nodes": [
                                {"id": "seg_1_0_2", "label": "[0,2]=99", "meta": {"l": 0, "r": 2, "sum": 99}},
                                {"id": "seg_2_0_1", "label": "[0,1]=3", "meta": {"l": 0, "r": 1, "sum": 3}},
                                {"id": "seg_3_2_2", "label": "[2,2]=4", "meta": {"l": 2, "r": 2, "sum": 4}},
                            ],
                            "edges": [["seg_1_0_2", "seg_2_0_1"], ["seg_1_0_2", "seg_3_2_2"]],
                        },
                    },
                    "reason": "错误线段树聚合。",
                    "code_line": 1,
                }
            ],
        }
    )
    fenwick_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "树状数组前缀和",
            "input_data": {"nums": [1, 2, 3, 4], "query": [1, 3], "update": [2, 1]},
            "result": {"before": 9, "after": 10},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "bit[2]"}],
                    "state": {"nums": [1, 2, 3, 4], "bit": [0, 1, 99, 3, 10], "query": [1, 3]},
                    "reason": "错误树状数组节点。",
                    "code_line": 1,
                }
            ],
        }
    )
    sparse_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "稀疏表区间最小值",
            "input_data": {"nums": [5, 2, 7, 3], "query": [1, 3]},
            "result": 2,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "st[1][1]"}],
                    "state": {"nums": [5, 2, 7, 3], "st": [[5, 2, 7, 3], [2, 9, 3], [2]], "log": [0, 0, 1, 1, 2], "query": [1, 3]},
                    "reason": "错误稀疏表单元。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("线段树" in error for error in segment_errors), segment_errors
    assert any("树状数组" in error for error in fenwick_errors), fenwick_errors
    assert any("稀疏表" in error for error in sparse_errors), sparse_errors


def test_phase7_range_structures_have_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "segment_tree_range_sum": {
            "layout": "tree",
            "state_keys": {"segment_tree", "nums", "query", "update", "answer"},
            "target_prefix": "node:seg_",
            "reason_tokens": ("查询区间", "更新路径"),
        },
        "fenwick_tree_prefix_sum": {
            "layout": "array",
            "state_keys": {"nums", "bit", "query", "update", "answer"},
            "target_prefix": "bit[",
            "reason_tokens": ("lowbit", "前缀", "更新路径"),
        },
        "sparse_table_range_min": {
            "layout": "matrix",
            "state_keys": {"nums", "st", "log", "query", "answer"},
            "target_prefix": "st[",
            "reason_tokens": ("稀疏表", "重叠区间"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("range:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids | dep_ids), (case_id, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "range_segment_tree.md": ["segment_tree", "node:seg_", "查询区间", "更新路径"],
        "range_fenwick_tree.md": ["bit[", "lowbit", "前缀"],
        "range_sparse_table.md": ["st[", "稀疏表", "重叠区间"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_math_bit_invariants():
    gcd_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "最大公约数 Euclid",
            "input_data": {"a": 48, "b": 18},
            "result": 6,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "remainders[0]"}],
                    "state": {"a": 48, "b": 18, "remainders": [99]},
                    "reason": "错误余数。",
                    "code_line": 1,
                }
            ],
        }
    )
    fast_power_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "快速幂",
            "input_data": {"base": 3, "exponent": 5, "mod": 13},
            "result": 9,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "powers[2]"}],
                    "state": {"base": 3, "exponent": 5, "mod": 13, "bits": [1, 0, 1], "powers": [3, 9, 99]},
                    "reason": "错误快速幂平方表。",
                    "code_line": 1,
                }
            ],
        }
    )
    sieve_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "埃氏筛",
            "input_data": {"n": 10},
            "result": [2, 3, 5, 7],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "is_prime[9]"}],
                    "state": {"n": 10, "is_prime": [False, False, True, True, False, True, False, True, False, True, False]},
                    "reason": "错误筛法倍数标记。",
                    "code_line": 1,
                }
            ],
        }
    )
    combination_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "组合数 Pascal",
            "input_data": {"n": 5, "k": 2},
            "result": 10,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "table[5][2]"}],
                    "state": {"n": 5, "k": 2, "table": [[1, 0, 0], [1, 1, 0], [1, 2, 1], [1, 3, 3], [1, 4, 6], [1, 99, 99]]},
                    "reason": "错误组合数表。",
                    "code_line": 1,
                }
            ],
        }
    )
    bitmask_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "位掩码枚举子集",
            "input_data": {"nums": [1, 2, 3]},
            "result": [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "bits[1]"}],
                    "state": {"nums": [1, 2, 3], "mask": 5, "bits": [1, 1, 1], "subset": [1, 2, 3]},
                    "reason": "错误位掩码位图。",
                    "code_line": 1,
                }
            ],
        }
    )
    lowbit_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "lowbit 分解",
            "input_data": {"n": 12},
            "result": [4, 8],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "lowbits[0]"}],
                    "state": {"n": 12, "remaining": 12, "lowbit": 99, "bits": [0, 0, 1, 1], "lowbits": [99]},
                    "reason": "错误 lowbit。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("最大公约数" in error or "GCD" in error for error in gcd_errors), gcd_errors
    assert any("快速幂" in error for error in fast_power_errors), fast_power_errors
    assert any("筛法" in error for error in sieve_errors), sieve_errors
    assert any("组合数" in error for error in combination_errors), combination_errors
    assert any("位掩码" in error for error in bitmask_errors), bitmask_errors
    assert any("lowbit" in error for error in lowbit_errors), lowbit_errors


def test_phase7_math_bit_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "gcd_euclid": {
            "layout": "array",
            "state_keys": {"a", "b", "remainders", "answer"},
            "target_prefix": "remainders[",
            "reason_tokens": ("最大公约数", "不变量"),
        },
        "fast_power_mod": {
            "layout": "array",
            "state_keys": {"base", "exponent", "mod", "bits", "powers", "answer"},
            "target_prefix": "powers[",
            "reason_tokens": ("快速幂", "指数"),
        },
        "sieve_primes": {
            "layout": "array",
            "state_keys": {"n", "is_prime", "current", "multiples", "answer"},
            "target_prefix": "is_prime[",
            "reason_tokens": ("筛法", "倍数"),
        },
        "combinations_pascal": {
            "layout": "matrix",
            "state_keys": {"n", "k", "table", "answer"},
            "target_prefix": "table[",
            "reason_tokens": ("组合数", "帕斯卡"),
        },
        "bitmask_subsets": {
            "layout": "array",
            "state_keys": {"nums", "mask", "bits", "subset", "answer"},
            "target_prefix": "bits[",
            "reason_tokens": ("位掩码", "子集"),
        },
        "lowbit_decomposition": {
            "layout": "array",
            "state_keys": {"n", "remaining", "bits", "lowbits", "answer"},
            "target_prefix": "lowbits[",
            "reason_tokens": ("lowbit", "最低位"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert expectation["layout"] in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert expectation["layout"] in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("number:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        assert any(target.startswith(expectation["target_prefix"]) for target in target_ids | dep_ids), (case_id, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "math_gcd.md": ["remainders", "最大公约数", "不变量"],
        "math_fast_power.md": ["powers", "bits", "快速幂"],
        "math_sieve.md": ["is_prime", "筛法", "倍数"],
        "math_combinations.md": ["table", "组合数", "帕斯卡"],
        "bitmask_subsets.md": ["bits", "mask", "子集"],
        "bit_lowbit.md": ["lowbits", "lowbit", "最低位"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_process_validator_rejects_bad_phase7_advanced_graph_invariants():
    tarjan_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Tarjan 强连通分量",
            "input_data": {"graph": {"A": ["B"], "B": ["A"]}},
            "result": [["A", "B"]],
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "low[A]"}],
                    "state": {
                        "graph": {"A": ["B"], "B": ["A"]},
                        "dfn": {"A": 1, "B": 2},
                        "low": {"A": 3, "B": 1},
                        "stack": ["A", "B"],
                        "on_stack": {"A": True, "B": True},
                    },
                    "reason": "错误 lowlink。",
                    "code_line": 1,
                }
            ],
        }
    )
    bridge_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "割点和桥 Tarjan",
            "input_data": {"graph": {"A": ["B"], "B": ["A", "C"], "C": ["B"]}},
            "result": {"articulation": ["B"], "bridges": [["A", "B"], ["B", "C"]]},
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "edge:A->B"}],
                    "state": {
                        "graph": {"A": ["B"], "B": ["A", "C"], "C": ["B"]},
                        "dfn": {"A": 1, "B": 2, "C": 3},
                        "low": {"A": 1, "B": 1, "C": 3},
                        "parent": {"A": None, "B": "A", "C": "B"},
                        "bridges": [["A", "B"]],
                        "articulation": [],
                    },
                    "role": "bridge",
                    "reason": "错误桥判定。",
                    "code_line": 1,
                }
            ],
        }
    )
    matching_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "二分图匹配",
            "input_data": {"graph": {"L1": ["R1"], "L2": ["R1"]}, "left": ["L1", "L2"], "right": ["R1"]},
            "result": {"L1": "R1", "L2": "R1"},
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "match[L2]"}],
                    "state": {
                        "graph": {"L1": ["R1"], "L2": ["R1"]},
                        "left_nodes": ["L1", "L2"],
                        "right_nodes": ["R1"],
                        "match": {"L1": "R1", "L2": "R1", "R1": "L2"},
                        "visited": {"R1": True},
                    },
                    "reason": "错误匹配：两个左侧点匹配同一个右侧点。",
                    "code_line": 1,
                }
            ],
        }
    )
    flow_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Edmonds-Karp 最大流",
            "input_data": {"graph": {"S": ["A"], "A": ["T"], "T": []}, "source": "S", "sink": "T"},
            "result": 3,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "flow[S->A]"}],
                    "state": {
                        "graph": {"S": ["A"], "A": ["T"], "T": []},
                        "capacity": {"S->A": 2, "A->T": 2},
                        "flow": {"S->A": 3, "A->T": 1},
                        "queue": ["S"],
                        "parent": {"A": "S", "T": "A"},
                        "bottleneck": 3,
                    },
                    "reason": "错误 flow 超过容量。",
                    "code_line": 1,
                }
            ],
        }
    )

    assert any("Tarjan" in error or "low" in error for error in tarjan_errors), tarjan_errors
    assert any("桥" in error or "bridge" in error.lower() for error in bridge_errors), bridge_errors
    assert any("匹配" in error or "match" in error.lower() for error in matching_errors), matching_errors
    assert any("flow" in error.lower() or "容量" in error for error in flow_errors), flow_errors


def test_phase13_hash_sorting_linked_list_greedy_validator_upgrades_profiles_and_rejects_process_errors():
    profiles = {
        profile.family: profile
        for profile in __import__(
            "algolab.verification.process_validator",
            fromlist=["process_validation_registry"],
        ).process_validation_registry()
    }

    assert profiles["hash"].status == "strong"
    assert profiles["hash"].level == "algorithm"
    assert "_validate_hash_map_process" in profiles["hash"].checks
    for family in ("sorting", "linked_list", "greedy"):
        assert family in profiles
        assert profiles[family].status == "strong"
    assert "_validate_sorting_process" in profiles["sorting"].checks
    assert "_validate_linked_list_process" in profiles["linked_list"].checks
    assert "_validate_greedy_process" in profiles["greedy"].checks

    cases = benchmark_cases()
    hash_cases = [case for case in cases if case.family_id == "hash_map"]
    sorting_cases = [case for case in cases if case.family_id == "sorting"]
    linked_cases = [case for case in cases if case.family_id == "linked_list_cache"]
    greedy_cases = [case for case in cases if case.family_id == "greedy"]

    assert sum(len(case.samples) for case in hash_cases) >= 3
    assert sum(len(case.samples) for case in sorting_cases) >= 3
    assert sum(len(case.samples) for case in linked_cases) >= 3
    assert sum(len(case.samples) for case in greedy_cases) >= 3
    assert {case.process_profile for case in hash_cases} == {"hash"}
    assert {case.process_profile for case in sorting_cases} == {"sorting"}
    assert {case.process_profile for case in linked_cases} == {"linked_list"}
    assert {case.process_profile for case in greedy_cases} == {"greedy"}
    assert {case.support_level for case in hash_cases} == {"medium_plus"}
    assert {case.support_level for case in sorting_cases} == {"medium_plus"}
    assert {case.support_level for case in linked_cases} == {"medium"}
    assert {case.support_level for case in greedy_cases} == {"medium_plus"}

    capabilities = {
        entry["family_id"]: entry
        for entry in __import__(
            "scripts.check_family_capabilities",
            fromlist=["load_family_capabilities"],
        ).load_family_capabilities()["families"]
    }
    assert capabilities["hash_map"]["process_profile"] == "hash"
    assert capabilities["hash_map"]["current_level"] == "medium_plus"
    assert capabilities["hash_map"]["fallback_boundaries"] == []
    assert capabilities["sorting"]["process_profile"] == "sorting"
    assert capabilities["sorting"]["current_level"] == "medium_plus"
    assert capabilities["sorting"]["fallback_boundaries"] == []
    assert capabilities["linked_list_cache"]["process_profile"] == "linked_list"
    assert capabilities["linked_list_cache"]["current_level"] == "medium"
    assert capabilities["greedy"]["process_profile"] == "greedy"
    assert capabilities["greedy"]["current_level"] == "medium_plus"

    wrong_hash_errors = _process_errors_for(
        _family_contract_trace(
            "Two Sum wrong hash hit before write",
            {"nums": [2, 7], "target": 9},
            [0, 1],
            [
                _family_contract_event(
                    0,
                    "create",
                    ["nums", "seen"],
                    state={"nums": [2, 7], "seen": {}, "target": 9, "hash_contract": {"submode": "two_sum"}},
                    reason="初始化哈希表。",
                ),
                _family_contract_event(
                    1,
                    "compare",
                    ["nums[0]"],
                    deps=["seen[7]"],
                    value={"need": 7, "exists": True},
                    state={"nums": [2, 7], "seen": {}, "target": 9, "i": 0, "need": 7, "hash_contract": {"submode": "two_sum"}},
                    reason="错误地声称互补值已经命中。",
                ),
                _family_contract_event(
                    2,
                    "mark",
                    ["nums[0]", "nums[1]"],
                    role="answer",
                    value=[0, 1],
                    deps=["seen[7]"],
                    state={"nums": [2, 7], "seen": {}, "target": 9, "answer": [0, 1], "hash_contract": {"submode": "two_sum"}},
                    reason="错误地使用未写入哈希表的值作为答案依据。",
                ),
            ],
        )
    )
    assert any("哈希" in error and "未写入" in error for error in wrong_hash_errors), wrong_hash_errors

    wrong_sort_errors = _process_errors_for(
        _family_contract_trace(
            "Insertion sort wrong prefix",
            {"nums": [3, 2, 1]},
            [1, 2, 3],
            [
                _family_contract_event(
                    0,
                    "create",
                    ["nums"],
                    state={"nums": [3, 2, 1], "i": 0, "sorting_contract": {"submode": "insertion_sort"}},
                    reason="初始化待排序数组。",
                ),
                _family_contract_event(
                    1,
                    "set",
                    ["nums[1]"],
                    after=3,
                    deps=["nums[0]"],
                    state={"nums": [3, 3, 1], "i": 1, "j": 0, "sorting_contract": {"submode": "insertion_sort"}},
                    reason="左侧元素右移。",
                ),
                _family_contract_event(
                    2,
                    "set",
                    ["nums[0]"],
                    after=2,
                    state={"nums": [2, 3, 1], "i": 1, "j": 0, "sorting_contract": {"submode": "insertion_sort"}},
                    reason="插入当前 key 后前缀有序。",
                ),
                _family_contract_event(
                    3,
                    "set",
                    ["nums[2]"],
                    after=3,
                    deps=["nums[1]"],
                    state={"nums": [2, 3, 3], "i": 2, "j": 1, "sorting_contract": {"submode": "insertion_sort"}},
                    reason="右移较大元素。",
                ),
                _family_contract_event(
                    4,
                    "set",
                    ["nums[1]"],
                    after=1,
                    state={"nums": [2, 1, 3], "i": 2, "j": 1, "sorting_contract": {"submode": "insertion_sort"}},
                    reason="错误地插入到仍未有序的位置。",
                ),
            ],
        )
    )
    assert any("排序" in error and "有序前缀" in error for error in wrong_sort_errors), wrong_sort_errors

    wrong_linked_errors = _process_errors_for(
        _family_contract_trace(
            "Linked list wrong reconnect",
            {"values": [1, 2, 3]},
            [3, 2, 1],
            [
                _family_contract_event(
                    0,
                    "create",
                    ["linked_list"],
                    state={
                        "linked_list": {
                            "nodes": [
                                {"id": "0", "label": "1", "meta": {"next": "1"}},
                                {"id": "1", "label": "2", "meta": {"next": "2"}},
                                {"id": "2", "label": "3", "meta": {"next": None}},
                            ],
                            "edges": [["0", "1"], ["1", "2"]],
                        },
                        "current": "0",
                        "prev": None,
                        "next": "1",
                        "family_contract": {"family": "linked_list", "submode": "reverse", "expected_events": ["move_pointer", "link_change"]},
                    },
                    reason="初始化链表。",
                ),
                _family_contract_event(
                    1,
                    "link",
                    ["edge:2->0"],
                    deps=["node:2", "node:0"],
                    state={
                        "linked_list": {
                            "nodes": [
                                {"id": "0", "label": "1", "meta": {"next": None}},
                                {"id": "1", "label": "2", "meta": {"next": "2"}},
                                {"id": "2", "label": "3", "meta": {"next": "0"}},
                            ],
                            "edges": [["2", "0"], ["1", "2"]],
                        },
                        "current": "2",
                        "prev": "0",
                        "next": None,
                        "family_contract": {"family": "linked_list", "submode": "reverse", "expected_events": ["move_pointer", "link_change"]},
                    },
                    reason="错误地跳过节点 1 直接重连节点 2。",
                ),
            ],
        )
    )
    assert any("链表" in error and "current" in error for error in wrong_linked_errors), wrong_linked_errors

    wrong_greedy_errors = _process_errors_for(
        _family_contract_trace(
            "Jump game wrong greedy reach",
            {"nums": [2, 0, 0]},
            True,
            [
                _family_contract_event(
                    0,
                    "create",
                    ["nums", "reach"],
                    state={"nums": [2, 0, 0], "i": 0, "reach": 0, "greedy_contract": {"submode": "jump_game"}},
                    reason="初始化最远可达位置。",
                ),
                _family_contract_event(
                    1,
                    "set",
                    ["reach"],
                    value=1,
                    deps=["nums[0]", "reach"],
                    state={"nums": [2, 0, 0], "i": 0, "reach": 1, "candidate_reach": 1, "greedy_contract": {"submode": "jump_game"}},
                    reason="错误地少更新最远可达位置。",
                ),
            ],
        )
    )
    assert any("贪心" in error and "reach" in error for error in wrong_greedy_errors), wrong_greedy_errors


def test_phase7_advanced_graph_group_has_benchmarks_visual_state_and_examples():
    cases_by_id = {case.id: case for case in benchmark_cases()}
    required = {
        "tarjan_scc": {
            "state_keys": {"graph", "dfn", "low", "stack", "on_stack", "component"},
            "target_prefixes": ("dfn[", "low[", "node:", "edge:"),
            "reason_tokens": ("Tarjan", "low"),
        },
        "articulation_bridges": {
            "state_keys": {"graph", "dfn", "low", "parent", "bridges", "articulation"},
            "target_prefixes": ("dfn[", "low[", "node:", "edge:"),
            "reason_tokens": ("割点", "桥"),
        },
        "bipartite_matching": {
            "state_keys": {"graph", "match", "visited", "left_nodes", "right_nodes"},
            "target_prefixes": ("match[", "node:", "edge:"),
            "reason_tokens": ("匹配", "增广"),
        },
        "edmonds_karp": {
            "state_keys": {"graph", "capacity", "flow", "queue", "parent", "bottleneck"},
            "target_prefixes": ("cap[", "flow[", "node:", "edge:"),
            "reason_tokens": ("Edmonds-Karp", "残量"),
        },
    }

    assert set(required) <= set(cases_by_id)
    for case_id, expectation in required.items():
        case = cases_by_id[case_id]
        assert "graph" in case.expected_layouts
        artifact, errors = materialize_case(case, sample_index=0)
        assert errors == [], (case_id, errors)
        scene = artifact.scenes[case_id]
        layouts = {
            obj.meta.get("layout")
            for frame in scene.frames
            for obj in frame.objects
            if obj.type.value == "container"
        }
        assert "graph" in layouts, (case_id, layouts)
        states = [frame.state for frame in scene.frames]
        state_keys = {key for state in states for key in state}
        assert expectation["state_keys"] <= state_keys, (case_id, state_keys)
        trace = artifact.variants[0].trace
        assert trace is not None
        target_ids = {target.id for event in trace.events for target in event.targets}
        dep_ids = {dep.id for event in trace.events for dep in event.deps}
        assert not any(item.startswith("flow:") for item in target_ids | dep_ids), (case_id, target_ids | dep_ids)
        for prefix in expectation["target_prefixes"]:
            assert any(item.startswith(prefix) for item in target_ids | dep_ids), (case_id, prefix, target_ids, dep_ids)
        reasons = "\n".join(event.reason or "" for event in trace.events)
        for token in expectation["reason_tokens"]:
            assert token in reasons, (case_id, token, reasons)

    example_names = {
        "graph_tarjan_scc.md": ["dfn", "low", "stack", "Tarjan"],
        "graph_articulation_bridges.md": ["dfn", "low", "桥", "割点"],
        "graph_bipartite_matching.md": ["match[", "增广", "匹配"],
        "graph_edmonds_karp.md": ["capacity", "flow[", "残量"],
    }
    for filename, tokens in example_names.items():
        path = Path("docs/examples") / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (filename, token)


def test_phase13_math_geometry_range_advanced_graph_validator_upgrades_geometry_and_preserves_profiles():
    profiles = {
        profile.family: profile
        for profile in __import__(
            "algolab.verification.process_validator",
            fromlist=["process_validation_registry"],
        ).process_validation_registry()
    }

    assert profiles["range_structure"].status == "strong"
    assert profiles["math_bit"].status == "strong"
    assert profiles["advanced_graph"].status == "strong"
    assert profiles["geometry"].status == "strong"
    assert "_validate_convex_hull" in profiles["geometry"].checks

    cases = benchmark_cases()
    geometry_cases = [case for case in cases if case.family_id == "geometry_sweep"]
    range_cases = [case for case in cases if case.family_id == "range_structure"]
    math_cases = [case for case in cases if case.family_id == "math_bit"]
    advanced_graph_cases = [case for case in cases if case.family_id == "advanced_graph"]

    assert sum(len(case.samples) for case in geometry_cases) >= 2
    assert sum(len(case.samples) for case in range_cases) >= 6
    assert sum(len(case.samples) for case in math_cases) >= 17
    assert sum(len(case.samples) for case in advanced_graph_cases) >= 8
    assert {case.support_level for case in geometry_cases} == {"medium_plus"}
    assert {case.process_profile for case in geometry_cases} == {"geometry"}
    assert {case.process_profile for case in range_cases} == {"range_structure"}
    assert {case.process_profile for case in math_cases} == {"math_bit"}
    assert {case.process_profile for case in advanced_graph_cases} == {"advanced_graph"}

    capabilities = {
        entry["family_id"]: entry
        for entry in __import__(
            "scripts.check_family_capabilities",
            fromlist=["load_family_capabilities"],
        ).load_family_capabilities()["families"]
    }
    assert capabilities["geometry_sweep"]["process_profile"] == "geometry"
    assert capabilities["geometry_sweep"]["current_level"] == "medium_plus"
    assert capabilities["geometry_sweep"]["fallback_boundaries"] == []
    for family_id in ("range_structure", "math_bit", "advanced_graph"):
        assert capabilities[family_id]["current_level"] == "strong"
        assert capabilities[family_id]["fallback_boundaries"] == []

    wrong_hull_errors = _process_errors_for(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "凸包",
            "input_data": {"points": [[0, 0], [1, 0], [0, 1], [1, 1]]},
            "result": [[0, 0], [1, 0], [0, 1], [1, 1]],
            "events": [
                {
                    "step": 0,
                    "op": "mark",
                    "targets": [{"id": "point:0"}, {"id": "point:1"}, {"id": "point:2"}, {"id": "point:3"}],
                    "state": {
                        "geometry": {
                            "points": [
                                {"id": "0", "x": 0, "y": 0},
                                {"id": "1", "x": 1, "y": 0},
                                {"id": "2", "x": 0, "y": 1},
                                {"id": "3", "x": 1, "y": 1},
                            ],
                            "hull": ["0", "1", "2", "3"],
                        },
                        "answer": [[0, 0], [1, 0], [0, 1], [1, 1]],
                    },
                    "role": "answer",
                    "reason": "错误地把自相交顺序作为凸包。",
                    "code_line": 1,
                }
            ],
        }
    )
    assert any("hull" in error or "凸" in error or "转向" in error for error in wrong_hull_errors), wrong_hull_errors


__all__ = [name for name in globals() if name.startswith("test_")]
