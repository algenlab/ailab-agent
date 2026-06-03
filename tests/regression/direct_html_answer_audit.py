"""Regression tests for direct HTML answer correctness auditing."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts import audit_direct_html_answer as audit


def test_extracts_final_answer_json_list() -> None:
    html = """
    <html><body>
      <main id="canvas">
        <h2>最终答案</h2>
        <div id="answer">输出：[0, 1]</div>
      </main>
    </body></html>
    """

    result = audit.audit_html_answer(html, [0, 1])

    assert result["status"] == "answer_match"
    assert result["extracted_answer"] == [0, 1]
    assert result["extraction_confidence"] == "high"


def test_extracts_final_answer_json_object_and_bool() -> None:
    html = """
    <html><body>
      <section aria-label="result">
        最终输出 JSON：{"ok": true, "path": ["A", "B"]}
      </section>
    </body></html>
    """

    result = audit.audit_html_answer(html, {"ok": True, "path": ["A", "B"]})

    assert result["status"] == "answer_match"
    assert result["extracted_answer"] == {"ok": True, "path": ["A", "B"]}


def test_reports_missing_when_no_answer_region_exists() -> None:
    html = """
    <html><body>
      <main id="canvas">这里有步骤解释，但没有最终答案。</main>
    </body></html>
    """

    result = audit.audit_html_answer(html, 7)

    assert result["status"] == "answer_missing"
    assert result["extracted_answer"] is None


def test_reports_mismatch_when_visible_answer_differs() -> None:
    html = """
    <html><body><p>结果：8</p></body></html>
    """

    result = audit.audit_html_answer(html, 7)

    assert result["status"] == "answer_mismatch"
    assert result["extracted_answer"] == 8


def test_ignores_script_control_values_and_uses_step_strings() -> None:
    html = """
    <html><body>
      <script>
        let updated = false;
        const steps = [
          {desc: "继续处理中间状态"},
          {desc: "算法结束。最终还原的数组为 [3, 3, 1]。"}
        ];
        nextBtn.disabled = true;
      </script>
    </body></html>
    """

    result = audit.audit_html_answer(html, [3, 3, 1])

    assert result["status"] == "answer_match"
    assert result["extracted_answer"] == [3, 3, 1]


def test_ignores_formula_index_brackets_as_answers() -> None:
    html = """
    <html><body>
      <script>
        const step = {desc: `结果: dp[j] = min(dp[j], dp[j - coin] + 1)。`};
      </script>
    </body></html>
    """

    result = audit.audit_html_answer(html, 3)

    assert result["status"] == "answer_missing"


def test_extracts_final_formula_value_after_equals() -> None:
    html = """
    <html><body>
      <script>
        const step = {formula: "最终结果 = dp[4] = 12"};
      </script>
    </body></html>
    """

    result = audit.audit_html_answer(html, 12)

    assert result["status"] == "answer_match"
    assert result["extracted_answer"] == 12


def test_audits_report_success_html_and_summarizes_counts() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        ok_html = root / "ok.html"
        bad_html = root / "bad.html"
        ok_html.write_text("<html><body>最终答案：7</body></html>", encoding="utf-8")
        bad_html.write_text("<html><body>最终答案：8</body></html>", encoding="utf-8")
        report_path = root / "llm_benchmark_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "config": {"benchmark_condition": "direct_html_baseline"},
                    "results": [
                        {"case_id": "ok", "sample_index": 0, "ok": True, "html": str(ok_html), "expected": 7},
                        {"case_id": "bad", "sample_index": 0, "ok": True, "html": str(bad_html), "expected": 7},
                        {"case_id": "browser_fail", "sample_index": 0, "ok": False, "expected": 7},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        summary = audit.audit_report(report_path)

    assert summary["total_results"] == 3
    assert summary["audited_html"] == 2
    assert summary["status_counts"] == {"answer_match": 1, "answer_mismatch": 1}
    assert summary["visible_answer_match_rate"] == 0.5
    assert summary["expected_visible_to_model"] is True


def run_all() -> None:
    test_extracts_final_answer_json_list()
    test_extracts_final_answer_json_object_and_bool()
    test_reports_missing_when_no_answer_region_exists()
    test_reports_mismatch_when_visible_answer_differs()
    test_ignores_script_control_values_and_uses_step_strings()
    test_ignores_formula_index_brackets_as_answers()
    test_extracts_final_formula_value_after_equals()
    test_audits_report_success_html_and_summarizes_counts()


if __name__ == "__main__":
    run_all()
    print("direct_html_answer_audit: PASS")
