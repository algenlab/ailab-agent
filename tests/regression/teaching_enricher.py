"""Regression tests for LLM teaching overlay enrichment."""

from __future__ import annotations

from algolab.compiler.scene_compiler import compile_scene
from algolab.generation.teaching_enricher import (
    apply_teaching_overlay,
    build_trace_digest,
    enrich_scene_teaching,
    select_teaching_events,
)
from algolab.schemas.semantic_trace import SemanticTrace


def _event(step: int, op: str, targets: list[str], state: dict, **kwargs) -> dict:
    return {
        "step": step,
        "op": op,
        "targets": [{"id": target} for target in targets],
        "deps": [{"id": dep} for dep in kwargs.get("deps", [])],
        "role": kwargs.get("role", ""),
        "reason": kwargs.get("reason", f"step {step}"),
        "state": state,
        "value": kwargs.get("value"),
        "before": kwargs.get("before"),
        "after": kwargs.get("after"),
        "code_line": kwargs.get("code_line", 1),
    }


def _trace(events: list[dict]) -> SemanticTrace:
    return SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "Bellman-Ford 单源最短路径",
            "input_data": {"edges": [["A", "B", 4]], "start": "A"},
            "result": {"A": 0, "B": 4},
            "pseudocode": ["初始化距离", "松弛边", "返回答案"],
            "events": [dict(event, step=index) for index, event in enumerate(events)],
        }
    )


def test_apply_teaching_overlay_updates_scene_without_mutating_trace():
    trace = _trace(
        [
            _event(0, "create", ["graph"], {"graph": {"nodes": ["A", "B"], "edges": [["A", "B", 4]]}}),
            _event(1, "set", ["dist[B]"], {"dist": {"A": 0, "B": 4}}, deps=["edge:A->B"], value=4),
            _event(
                2,
                "mark",
                ["answer"],
                {"dist": {"A": 0, "B": 4}, "answer": {"A": 0, "B": 4}},
                role="answer",
                value={"A": 0, "B": 4},
                reason="返回最终答案",
            ),
        ]
    )
    before = trace.model_dump()
    scene = compile_scene(trace)

    warnings = apply_teaching_overlay(
        scene,
        {
            "frames": [
                {
                    "step": 2,
                    "teaching": {
                        "what": "返回从 A 出发到每个节点的最短距离",
                        "why": "所有可达边已经完成松弛，dist 的值就是最终答案。",
                        "hint": "关注 dist 中每个节点的最终值。",
                    },
                    "interaction": {
                        "type": "judge",
                        "prompt": "这一步还会继续修改 dist 吗？",
                        "answer": False,
                        "explanation": "当前帧已经是返回答案阶段。",
                    },
                }
            ]
        },
    )

    assert warnings == []
    assert trace.model_dump() == before
    assert scene.frames[2].teaching["what"] == "返回从 A 出发到每个节点的最短距离"
    assert scene.frames[2].teaching["why"] == "所有可达边已经完成松弛，dist 的值就是最终答案。"
    assert scene.frames[2].interaction["type"] == "judge"
    assert scene.frames[2].operation == "mark"
    assert scene.frames[2].state["answer"] == {"A": 0, "B": 4}


def test_apply_teaching_overlay_ignores_echoed_trace_fields_and_repairs_option_explanations():
    trace = _trace(
        [
            _event(0, "create", ["nums"], {"nums": [1, 2]}),
            _event(1, "mark", ["answer"], {"answer": 3}, role="answer", value=3),
        ]
    )
    scene = compile_scene(trace)

    warnings = apply_teaching_overlay(
        scene,
        {
            "frames": [
                {
                    "step": 1,
                    "op": "mark",
                    "targets": ["answer"],
                    "state": {"answer": 3},
                    "code_line": 4,
                    "teaching": {"what": "返回最终答案", "why": "answer 已记录结果。"},
                    "interaction": {
                        "type": "choice",
                        "prompt": "当前是否已经得到答案？",
                        "options": ["是", "否"],
                        "answer": "是",
                        "option_explanations": ["模型错误地输出了列表"],
                    },
                }
            ]
        },
    )

    assert warnings == []
    assert scene.frames[1].teaching["what"] == "返回最终答案"
    assert scene.frames[1].interaction["option_explanations"] == {}
    assert scene.frames[1].operation == "mark"
    assert scene.frames[1].state == {"answer": 3}


def test_apply_teaching_overlay_maps_choice_answer_index_to_option_text():
    trace = _trace(
        [
            _event(0, "create", ["nums"], {"nums": [1, 2]}),
            _event(1, "mark", ["answer"], {"answer": 3}, role="answer", value=3),
        ]
    )
    scene = compile_scene(trace)

    warnings = apply_teaching_overlay(
        scene,
        {
            "frames": [
                {
                    "step": 1,
                    "teaching": {"what": "返回答案", "why": "answer 已写入。"},
                    "interaction": {
                        "type": "choice",
                        "prompt": "当前是否已经得到答案？",
                        "options": ["否", "是"],
                        "answer": 1,
                        "explanation": "第二个选项对应已经得到答案。",
                    },
                }
            ]
        },
    )

    assert warnings == []
    assert scene.frames[1].interaction["answer"] == "是"


def test_trace_digest_limits_long_trace_but_keeps_answer_and_state_change_frames():
    events = [_event(0, "create", ["nums"], {"nums": [1, 2, 3], "answer": None})]
    for index in range(1, 38):
        state = {"nums": [1, 2, 3], "i": index, "answer": None}
        events.append(_event(index, "compare", ["nums[0]"], state, deps=["nums[1]"]))
    events.append(_event(38, "set", ["answer"], {"answer": 6}, value=6, before=None, after=6))
    events.append(_event(39, "mark", ["answer"], {"answer": 6}, role="answer", value=6))
    trace = _trace(events)

    selected = select_teaching_events(trace, max_frames=8)
    selected_steps = [event.step for event in selected]
    digest = build_trace_digest(trace, problem="求和", code="def solve(input_data): ...", max_frames=8)

    assert len(selected) <= 8
    assert selected_steps[0] == 0
    assert 38 in selected_steps
    assert 39 in selected_steps
    assert len(digest["frames"]) == len(selected)
    assert all("state" in frame and "state_diff" in frame for frame in digest["frames"])
    assert digest["trace_summary"]["total_events"] == 40


def test_trace_digest_default_keeps_small_trace_under_frame_limit():
    events = [_event(0, "create", ["nums"], {"nums": [1, 2, 3], "answer": None})]
    for index in range(1, 12):
        events.append(_event(index, "compare", ["nums[0]"], {"nums": [1, 2, 3], "i": index}))
    events.append(_event(12, "mark", ["answer"], {"answer": 6}, role="answer", value=6))
    trace = _trace(events)

    selected = select_teaching_events(trace)
    digest = build_trace_digest(trace, problem="求和", code="def solve(input_data): ...")

    assert len(selected) == len(trace.events)
    assert digest["trace_summary"]["selected_events"] == list(range(len(trace.events)))
    assert len(digest["frames"]) == len(trace.events)


def test_trace_digest_default_caps_large_trace_at_30_key_frames():
    events = [_event(0, "create", ["nums"], {"nums": [1, 2, 3], "answer": None})]
    for index in range(1, 44):
        state = {"nums": [1, 2, 3], "i": index, "answer": None}
        events.append(_event(index, "compare", ["nums[0]"], state, deps=["nums[1]"]))
    events.append(_event(44, "set", ["answer"], {"answer": 6}, value=6, before=None, after=6))
    events.append(_event(45, "mark", ["answer"], {"answer": 6}, role="answer", value=6))
    trace = _trace(events)

    selected = select_teaching_events(trace)
    selected_steps = [event.step for event in selected]
    digest = build_trace_digest(trace, problem="求和", code="def solve(input_data): ...")

    assert len(selected) == 30
    assert selected_steps[0] == 0
    assert 44 in selected_steps
    assert 45 in selected_steps
    assert digest["trace_summary"]["total_events"] == 46
    assert len(digest["frames"]) == 30


def test_enrich_scene_teaching_default_sends_at_most_30_key_frames_to_llm_first():
    events = [_event(0, "create", ["nums"], {"nums": [1, 2, 3]})]
    for index in range(1, 44):
        events.append(_event(index, "compare", ["nums[0]"], {"nums": [1, 2, 3], "i": index}))
    events.append(_event(44, "mark", ["answer"], {"answer": 6}, role="answer", value=6))
    trace = _trace(events)
    scene = compile_scene(trace)
    selected_counts = []

    def fake_chat(_system_prompt, user_prompt, *, kind):
        import json

        payload = json.loads(user_prompt)
        selected_counts.append(len(payload["frames"]))
        selected_steps = [frame["step"] for frame in payload["frames"]]
        assert 44 in selected_steps
        return {"frames": [{"step": 44, "teaching": {"what": "返回求和结果", "why": "answer 已写入。"}}]}

    warnings = enrich_scene_teaching(scene, trace, chat_fn=fake_chat)

    assert warnings == []
    assert selected_counts == [30]
    assert scene.frames[44].teaching["what"] == "返回求和结果"


def test_enrich_scene_teaching_retries_with_smaller_digest_after_llm_failure():
    events = [_event(0, "create", ["nums"], {"nums": [1, 2, 3]})]
    for index in range(1, 10):
        events.append(_event(index, "compare", ["nums[0]"], {"nums": [1, 2, 3], "i": index}))
    events.append(_event(10, "mark", ["answer"], {"answer": 6}, role="answer", value=6))
    trace = _trace(events)
    scene = compile_scene(trace)
    selected_counts = []

    def fake_chat(_system_prompt, user_prompt, *, kind):
        import json

        payload = json.loads(user_prompt)
        selected_counts.append(len(payload["frames"]))
        if len(selected_counts) == 1:
            raise ValueError("first LLM call failed")
        return {"frames": [{"step": 10, "teaching": {"what": "返回求和结果", "why": "answer 已写入。"}}]}

    warnings = enrich_scene_teaching(scene, trace, max_frames=6, chat_fn=fake_chat)

    assert warnings == []
    assert selected_counts == [6, 3]
    assert scene.frames[10].teaching["what"] == "返回求和结果"
