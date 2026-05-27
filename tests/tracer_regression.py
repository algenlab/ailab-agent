"""Regression tests for the structured Tracer API."""

from __future__ import annotations

from pathlib import Path

from algolab.runtime.executor import execute_variant
from algolab.runtime.tracer import Tracer
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.semantic_trace import SolutionVariant
from tests.benchmark_cases import UNIQUE_PATHS_CODE, UNIQUE_PATHS_TRACKER


def test_tracer_builds_valid_semantic_trace():
    tracer = Tracer({"m": 2, "n": 2}, algorithm="不同路径", pseudocode=["dp[i][j] = dp[i-1][j] + dp[i][j-1]"])
    tracer.create("dp", state={"dp": [[1, 1], [1, 1]]}, reason="初始化。")
    tracer.set(
        "dp[1][1]",
        value=2,
        deps=["dp[0][1]", "dp[1][0]"],
        state={"dp": [[1, 1], [1, 2]], "i": 1, "j": 1},
        reason="来自上方和左侧。",
        code_line=3,
    )
    tracer.result(2)

    trace = SemanticTrace.model_validate(tracer.to_trace())

    assert trace.algorithm == "不同路径"
    assert trace.input_data == {"m": 2, "n": 2}
    assert trace.result == 2
    assert len(trace.events) == 2
    assert trace.events[1].op.value == "set"
    assert trace.events[1].targets[0].id == "dp[1][1]"
    assert [dep.id for dep in trace.events[1].deps] == ["dp[0][1]", "dp[1][0]"]


def test_tracer_accepts_teaching_payload_for_key_events():
    tracer = Tracer({"nums": [1]}, algorithm="教学字段")
    tracer.set(
        "nums[0]",
        value=1,
        state={"nums": [1]},
        reason="写入当前值。",
        teaching={"what": "写入 nums[0]", "why": "当前值就是答案。"},
        code_line=1,
    )
    tracer.result([1])

    trace = SemanticTrace.model_validate(tracer.to_trace())

    assert trace.events[0].teaching is not None
    assert trace.events[0].teaching.what == "写入 nums[0]"
    assert trace.events[0].teaching.why == "当前值就是答案。"


def test_tracer_strict_mode_rejects_missing_expected_updates():
    tracer = Tracer({"m": 3, "n": 7}, algorithm="不同路径", policy="strict")
    tracer.expect_updates("dp", 12)
    tracer.create("dp", state={"dp": [[1] * 7 for _ in range(3)]})
    tracer.set("dp[1][1]", state={"dp": [[1] * 7 for _ in range(3)]})
    tracer.result(28)

    try:
        tracer.to_trace()
    except ValueError as exc:
        assert "dp expected 12 updates, recorded 1" in str(exc)
    else:
        raise AssertionError("strict tracer should reject missing expected updates")


def test_tracer_attaches_trace_meta_to_last_event_state():
    tracer = Tracer({"nums": [1, 2]}, algorithm="数组", policy="full", max_events=80)
    tracer.expect_updates("nums", 2)
    tracer.set("nums[0]", value=1, state={"nums": [1, 2]})
    tracer.set("nums[1]", value=2, state={"nums": [1, 2]})
    tracer.result([1, 2])

    trace = tracer.to_trace()
    meta = trace["events"][-1]["state"]["_trace_meta"]

    assert meta["policy"] == "full"
    assert meta["max_events"] == 80
    assert meta["raw_event_count"] == 2
    assert meta["emitted_event_count"] == 2
    assert meta["expected_updates"] == {"nums": 2}
    assert meta["recorded_updates"] == {"nums": 2}
    assert meta["coverage"] == {"nums": 1.0}


def test_tracer_auto_policy_samples_when_events_exceed_budget():
    tracer = Tracer({"nums": list(range(20))}, algorithm="长数组", max_events=5, policy="auto")
    for i in range(20):
        tracer.set(f"nums[{i}]", value=i, state={"nums": list(range(20)), "i": i})
    tracer.result(list(range(20)))

    trace = tracer.to_trace()
    meta = trace["events"][-1]["state"]["_trace_meta"]

    assert len(trace["events"]) == 5
    assert meta["sampled"] is True
    assert meta["raw_event_count"] == 20
    assert meta["emitted_event_count"] == 5


def test_tracer_auto_policy_keeps_full_trace_when_expected_updates_fit_budget():
    tracer = Tracer({"m": 5, "n": 11}, algorithm="不同路径", max_events=80, policy="auto")
    m, n = 5, 11
    dp = [[1] * n for _ in range(m)]
    tracer.expect_updates("dp", (m - 1) * (n - 1))
    tracer.create("dp", state={"dp": [row[:] for row in dp]})
    for i in range(1, m):
        for j in range(1, n):
            tracer.compare(
                [f"dp[{i}][{j}]"],
                deps=[f"dp[{i - 1}][{j}]", f"dp[{i}][{j - 1}]"],
                state={"dp": [row[:] for row in dp], "i": i, "j": j},
            )
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
            tracer.set(
                f"dp[{i}][{j}]",
                value=dp[i][j],
                deps=[f"dp[{i - 1}][{j}]", f"dp[{i}][{j - 1}]"],
                state={"dp": [row[:] for row in dp], "i": i, "j": j},
            )
    tracer.result(dp[-1][-1])

    trace = tracer.to_trace()
    meta = trace["events"][-1]["state"]["_trace_meta"]

    assert len(trace["events"]) == 81
    assert meta["sampled"] is False
    assert meta["expected_updates"] == {"dp": 40}
    assert meta["recorded_updates"] == {"dp": 40}


def test_tracer_counts_non_set_update_operations_for_expected_updates():
    tracer = Tracer({}, policy="strict")
    tracer.expect_updates("stack", 2)
    tracer.expect_updates("pointer:left", 1)
    tracer.create("stack", state={"stack": []})
    tracer.push("stack", value=1, state={"stack": [1]})
    tracer.pop("stack", value=1, state={"stack": []})
    tracer.move("pointer:left", value=1, state={"left": 1})

    trace = tracer.to_trace()
    meta = trace["events"][-1]["state"]["_trace_meta"]

    assert meta["recorded_updates"] == {"stack": 2, "pointer:left": 1}


def test_tracer_exposes_relationship_and_scope_helpers():
    tracer = Tracer({"graph": {"A": ["B"]}}, algorithm="图 DFS", policy="strict")
    tracer.expect_updates("node:A", 1)
    tracer.expect_updates("edge:A->B", 2)
    tracer.expect_updates("frame:dfs(A)", 2)
    tracer.mark("node:A", state={"graph": {"A": ["B"]}, "visited": {"A": True}}, role="visited")
    tracer.unmark("node:A", state={"graph": {"A": ["B"]}, "visited": {"A": False}}, role="")
    tracer.link(
        "edge:A->B",
        deps=["node:A", "node:B"],
        state={"graph": {"A": ["B"]}, "tree_edges": [["A", "B"]]},
        reason="记录 DFS 树边。",
    )
    tracer.enter("frame:dfs(A)", state={"stack": ["dfs(A)"], "current": "A"}, reason="进入 DFS 帧。")
    tracer.exit("frame:dfs(A)", state={"stack": [], "current": "A"}, reason="退出 DFS 帧。")
    tracer.unlink("edge:A->B", state={"graph": {"A": ["B"]}, "tree_edges": []}, reason="撤销树边。")
    tracer.result(["A", "B"])

    trace = SemanticTrace.model_validate(tracer.to_trace())
    ops = [event.op.value for event in trace.events]
    meta = trace.events[-1].state["_trace_meta"]

    assert ops == ["mark", "unmark", "link", "enter", "exit", "unlink"]
    assert trace.events[2].targets[0].id == "edge:A->B"
    assert [dep.id for dep in trace.events[2].deps] == ["node:A", "node:B"]
    assert trace.events[3].targets[0].id == "frame:dfs(A)"
    assert meta["recorded_updates"] == {"node:A": 2, "edge:A->B": 2, "frame:dfs(A)": 2}
    assert meta["coverage"] == {"node:A": 2.0, "edge:A->B": 1.0, "frame:dfs(A)": 1.0}


def test_tracer_api_docs_and_prompt_include_extended_helpers():
    docs = Path("docs/04_TRACE_AND_SCHEMA_CONTRACT.md").read_text(encoding="utf-8")
    prompt = Path("algolab/generation/prompts/tracker_system.txt").read_text(encoding="utf-8")

    for method in ("unmark", "link", "unlink", "enter", "exit"):
        assert f"`{method}(" in docs
        assert f"tracer.{method}" in prompt
    assert "暂未暴露 `unmark`" not in docs


def test_executor_accepts_full_trace_when_expected_updates_fit_budget():
    variant = SolutionVariant(
        id="unique_paths",
        name="不同路径",
        strategy="动态规划",
        code=UNIQUE_PATHS_CODE,
        tracker_code=UNIQUE_PATHS_TRACKER,
    )

    materialized = execute_variant(variant, {"m": 5, "n": 11})

    assert materialized.trace is not None
    assert len(materialized.trace.events) == 81
    assert materialized.trace.events[-1].state["_trace_meta"]["sampled"] is False
    assert materialized.trace.events[-1].state["_trace_meta"]["coverage"] == {"dp": 1.0}


def run_all():
    test_tracer_builds_valid_semantic_trace()
    test_tracer_accepts_teaching_payload_for_key_events()
    test_tracer_strict_mode_rejects_missing_expected_updates()
    test_tracer_attaches_trace_meta_to_last_event_state()
    test_tracer_auto_policy_samples_when_events_exceed_budget()
    test_tracer_auto_policy_keeps_full_trace_when_expected_updates_fit_budget()
    test_tracer_counts_non_set_update_operations_for_expected_updates()
    test_tracer_exposes_relationship_and_scope_helpers()
    test_tracer_api_docs_and_prompt_include_extended_helpers()
    test_executor_accepts_full_trace_when_expected_updates_fit_budget()


if __name__ == "__main__":
    run_all()
    print("tracer_regression: PASS")
