from __future__ import annotations


def test_naps_level_prefers_responding_when_feedback_is_semantic() -> None:
    from scripts.run_external_eval_methods import naps_level_from_features

    level = naps_level_from_features(
        {
            "page_load_ok": True,
            "visible_answer_match": True,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": True,
            "input_change_supported": False,
        }
    )

    assert level["level"] == "responding"
    assert level["score"] == 2


def test_naps_level_detects_changing_when_input_rerun_exists() -> None:
    from scripts.run_external_eval_methods import naps_level_from_features

    level = naps_level_from_features(
        {
            "page_load_ok": True,
            "visible_answer_match": True,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": True,
            "input_change_supported": True,
        }
    )

    assert level["level"] == "changing"
    assert level["score"] == 3


def test_trakla2_core_pass_requires_both_feedback_directions() -> None:
    from scripts.run_external_eval_methods import trakla2_style_scores

    passing = trakla2_style_scores(
        {
            "page_load_ok": True,
            "visible_answer_match": True,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": True,
            "show_answer_ok": True,
            "learning_log_ok": True,
            "mutation_free_ok": True,
        }
    )
    failing = trakla2_style_scores(
        {
            "page_load_ok": True,
            "visible_answer_match": True,
            "interaction_reachable": True,
            "correct_feedback_ok": True,
            "wrong_feedback_ok": False,
            "show_answer_ok": True,
            "learning_log_ok": True,
            "mutation_free_ok": True,
        }
    )

    assert passing["core_pass"] is True
    assert passing["score"] == 7
    assert failing["core_pass"] is False
    assert failing["score"] == 6


def test_external_review_normalization_clamps_scores_and_unblinds_winner() -> None:
    from scripts.run_external_eval_methods import normalize_external_review_result

    result = normalize_external_review_result(
        {
            "winner": "B",
            "scores": {
                "A": {
                    "content_quality": 6,
                    "learning_goal_alignment": 5,
                    "feedback_adaptation": 1,
                    "interaction_usability": 4,
                    "presentation_design": 3,
                    "teaching_effectiveness": 5,
                    "ease_of_use": 2,
                },
                "B": {
                    "content_quality": 4,
                    "learning_goal_alignment": 4,
                    "feedback_adaptation": 4,
                    "interaction_usability": 4,
                    "presentation_design": 4,
                    "teaching_effectiveness": 4,
                    "ease_of_use": 0,
                },
            },
            "rationale": "B has better interaction.",
        },
        blind_map={"A": "direct_html", "B": "algolab_full"},
    )

    assert result["winner"] == "algolab_full"
    assert result["conditions"]["direct_html"]["scores"]["content_quality"] == 5
    assert result["conditions"]["algolab_full"]["scores"]["ease_of_use"] == 1


def test_visible_html_text_excludes_scripts_styles_and_debug_blocks() -> None:
    from scripts.run_external_eval_methods import visible_html_text

    html = """
    <html>
      <style>.debug { color: red; }</style>
      <script>const artifact = {"raw": "debug-only"};</script>
      <body>
        <main>二分查找教学内容</main>
        <section id="debug-drawer">raw validation report shader compile failed</section>
      </body>
    </html>
    """

    text = visible_html_text(html)

    assert "二分查找教学内容" in text
    assert "shader compile failed" not in text
    assert "debug-only" not in text


def test_compact_page_evidence_prefers_rendered_browser_text() -> None:
    from scripts.run_external_eval_methods import compact_page_evidence

    evidence = compact_page_evidence(
        {
            "title": "二分查找",
            "rendered_text": "浏览器渲染后的学习目标 checkpoint feedback answer",
            "page_load_ok": True,
            "visible_answer_match": True,
            "interaction_reachable": True,
        }
    )

    assert evidence["text_excerpt"] == "浏览器渲染后的学习目标 checkpoint feedback answer"
