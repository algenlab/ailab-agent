"""Regression tests for LLM teaching overlay enrichment."""

from __future__ import annotations

from algolab.compiler.scene_compiler import compile_scene
from algolab.generation.teaching_enricher import (
    TEACHING_SYSTEM_PROMPT,
    apply_teaching_overlay,
    build_trace_digest,
    compute_interaction_coverage,
    enrich_scene_teaching,
    select_teaching_events,
    validate_teaching_contract,
)
from algolab.renderer.export import render_html
from algolab.schemas.scene_graph import SceneGraph
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.validation import BuildArtifact, ReleaseGate, ValidationReport


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


def _artifact_for_renderer(scene: SceneGraph, trace: SemanticTrace) -> BuildArtifact:
    return BuildArtifact(
        problem_title="教学检查点测试",
        input_contract="输入 nums，返回 answer",
        input_data=trace.input_data,
        expected_result=trace.result,
        verifier_result=trace.result,
        variants=[
            SolutionVariant(
                id="main",
                name="主解法",
                strategy="跟踪关键变量并预测下一步",
                time_complexity="O(n)",
                space_complexity="O(1)",
                code="def solve(input_data):\n    return input_data.get('answer')",
                tracker_code="def trace(input_data):\n    return {}",
                result=trace.result,
                trace=trace,
            )
        ],
        scenes={"main": scene},
        validation=ValidationReport(
            release_gate=ReleaseGate(
                artifact_ready=True,
                process_ready=True,
                trace_ready=True,
                visual_ready=True,
                release_ready=True,
            )
        ),
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


def test_teaching_prompt_requires_interactions_on_key_learning_frames_without_hard_word_caps():
    assert "关键学习帧" in TEACHING_SYSTEM_PROMPT
    assert "必须优先生成 interaction" in TEACHING_SYSTEM_PROMPT
    assert "不要求每个 frame 都有 interaction" in TEACHING_SYSTEM_PROMPT
    assert "不要为了变短省略关键变量" in TEACHING_SYSTEM_PROMPT
    assert "如果不确定就填 null" not in TEACHING_SYSTEM_PROMPT
    assert "不超过 36 个汉字" not in TEACHING_SYSTEM_PROMPT
    assert "不超过 40 个汉字" not in TEACHING_SYSTEM_PROMPT


def test_teaching_prompt_requires_pedagogical_prediction_contract():
    required_phrases = [
        "预测检查点",
        "学生应该先预测",
        "hint 必须引导学生看 targets/deps/state",
        "common_mistake 不能写成泛泛提醒",
        "wrong_explanation 必须解释为什么错",
        "答案帧也必须优先生成 checkpoint",
        "option_explanations 优先覆盖每个错误选项",
    ]

    for phrase in required_phrases:
        assert phrase in TEACHING_SYSTEM_PROMPT


def test_compute_interaction_coverage_counts_key_learning_frames():
    trace = _trace(
        [
            _event(0, "create", ["nums"], {"nums": [1, 2, 3]}),
            _event(1, "compare", ["mid"], {"mid": 1}, deps=["target"], value="nums[mid] < target"),
            _event(2, "move", ["left"], {"left": 2}, before=0, after=2, reason="目标在右侧"),
            _event(3, "set", ["answer"], {"answer": 2}, before=None, after=2, role="answer", value=2),
        ]
    )
    scene = compile_scene(trace)
    scene.frames[1].interaction = {"type": "choice", "prompt": "下一步移动哪边？", "options": ["左边", "右边"], "answer": "右边"}
    scene.frames[3].interaction = {"type": "judge", "prompt": "当前已经得到答案吗？", "answer": True}

    report = compute_interaction_coverage(trace, scene)

    assert report["total_frames"] == 4
    assert report["interaction_frames"] == 2
    assert report["key_learning_frames"] == 3
    assert report["key_learning_interaction_frames"] == 2
    assert report["key_learning_interaction_rate"] == 2 / 3
    assert report["answer_frame_interaction_present"] is True
    assert report["deps_frame_interaction_rate"] == 1.0
    assert report["missing_key_learning_steps"] == [2]


def test_validate_teaching_contract_flags_missing_teaching_and_incomplete_checkpoint():
    trace = _trace(
        [
            _event(0, "create", ["nums"], {"nums": [1, 2, 3]}),
            _event(1, "compare", ["mid"], {"mid": 1}, deps=["target"], value="nums[mid] < target"),
            _event(2, "set", ["answer"], {"answer": 2}, before=None, after=2, role="answer", value=2),
        ]
    )
    scene = compile_scene(trace)
    scene.frames[1].teaching = {}
    scene.frames[1].interaction = {
        "type": "choice",
        "prompt": "下一步移动哪边？",
        "options": ["左边", "右边"],
        "answer": "中间",
        "explanation": "",
    }

    warnings, checks = validate_teaching_contract(trace, scene)

    assert any("step 1" in warning and "teaching.what/why" in warning for warning in warnings), warnings
    assert any("step 1" in warning and "choice answer 必须来自 options" in warning for warning in warnings), warnings
    assert any("step 1" in warning and "缺少错误反馈" in warning for warning in warnings), warnings
    assert any("answer frame 缺少 prediction checkpoint" in warning for warning in warnings), warnings
    assert any("teaching_contract" in check for check in checks), checks


def test_validate_teaching_contract_accepts_grounded_prediction_checkpoint():
    trace = _trace(
        [
            _event(0, "create", ["nums"], {"nums": [1, 2, 3]}),
            _event(1, "compare", ["mid"], {"mid": 1, "target": 3}, deps=["target"], value="nums[mid] < target"),
            _event(2, "set", ["answer"], {"answer": 2}, before=None, after=2, role="answer", value=2),
        ]
    )
    scene = compile_scene(trace)
    scene.frames[1].teaching = {
        "what": "比较 mid 与 target",
        "why": "mid 处的值小于 target，因此搜索右侧。",
        "invariant": "目标若存在仍在闭区间内。",
        "common_mistake": "不要把 mid 左侧继续保留。",
        "hint": "观察 nums[mid] 和 target 的大小关系。",
    }
    scene.frames[1].interaction = {
        "type": "choice",
        "prompt": "下一步应该保留哪一侧？",
        "options": ["左侧", "右侧"],
        "answer": "右侧",
        "explanation": "nums[mid] 小于 target，左侧和 mid 可以排除。",
        "wrong_explanation": "选择左侧会丢掉可能包含 target 的右半区。",
        "option_explanations": {"左侧": "左侧值更小，不能继续保留。"},
    }
    scene.frames[2].teaching = {
        "what": "返回答案下标",
        "why": "answer 已经写入最终下标。",
        "common_mistake": "不要把数组值当作下标。",
        "hint": "answer 表示位置。",
    }
    scene.frames[2].interaction = {
        "type": "input",
        "prompt": "最终 answer 是多少？",
        "answer": "2",
        "explanation": "当前 state 中 answer=2。",
        "wrong_explanation": "这里要填下标，不是 nums[2] 的值。",
    }

    warnings, checks = validate_teaching_contract(trace, scene)

    assert warnings == []
    assert any("teaching_contract: key_learning_interaction_rate" in check for check in checks), checks


def test_renderer_declares_prediction_checkpoint_hint_and_answer_controls():
    trace = _trace(
        [
            _event(0, "create", ["nums"], {"nums": [1, 2], "answer": None}),
            _event(1, "set", ["answer"], {"answer": 3}, role="answer", value=3),
        ]
    )
    scene = compile_scene(trace)
    scene.frames[1].teaching = {
        "what": "写入最终答案",
        "why": "当前答案已经可以从 state 中直接读出。",
        "hint": "关注 answer 的值。",
        "common_mistake": "不要把数组元素当作返回值。",
    }
    scene.frames[1].interaction = {
        "type": "input",
        "prompt": "当前 answer 应该是多少？",
        "answer": "3",
        "explanation": "state 中 answer=3。",
        "wrong_explanation": "这里问的是 answer，不是 nums 中的某个位置。",
    }

    html = render_html(_artifact_for_renderer(scene, trace))

    assert "预测检查点" in html
    assert "先预测，再查看反馈" in html
    assert "showInteractionHint" in html
    assert "revealInteractionAnswer" in html
    assert "data-learning-checkpoint" in html
    assert "learningLog" in html
    assert "logLearningEvent" in html
    assert "exportLearningLog" in html
    assert "data-learning-log" in html
    assert "recordSkipIfNeeded" in html
    assert "defaultVariantIndex" in html
    assert "variantTeachingLoadScore" in html
    assert "label:'当前步骤'" not in html
    assert "label:'为什么'" not in html


def test_renderer_student_mode_hides_debug_text_from_visible_page():
    from scripts.run_external_eval_methods import visible_html_text

    trace = _trace(
        [
            _event(0, "create", ["nums"], {"nums": [1, 2], "answer": None}),
            _event(1, "set", ["answer"], {"answer": 3}, role="answer", value=3),
        ]
    )
    scene = compile_scene(trace)

    html = render_html(_artifact_for_renderer(scene, trace))
    visible_text = visible_html_text(html)

    assert "student-mode" in html
    assert "debug-host" in html
    assert "DEBUG_DRAWER_HTML" in html
    assert "学习目标" in visible_text
    assert "关键不变量" in visible_text
    assert "主动练习与反馈" in visible_text
    assert "实例任务" in visible_text
    assert "预测检查点" in html
    assert "学习日志会记录" in html
    assert "Debug Drawer" not in visible_text
    assert "raw validation report" not in visible_text
    assert "raw state JSON" not in visible_text
    assert "artifact JSON" not in visible_text
    assert "shader compile failed" not in visible_text


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
