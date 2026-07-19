"""Run the no-SceneGraph-compiler ablation as an external experiment."""

from __future__ import annotations

import argparse
import json
import sys
import time
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.solution_generator import generate_solution_spec, parse_variants, repair_solution_spec
from algolab.pipeline import BuildError
from algolab.runtime.executor import canonical, execute_variant, run_verifier
from algolab.schemas.input import ProblemInput
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.verification.demo_readiness import validate_variant_demo_readiness
from algolab.verification.process_validator import validate_process
from algolab.verification.repair_context import repair_failure_types
from algolab.verification.trace_validator import validate_trace
from llm_client import _model_name, clear_model_calls, consume_model_calls
from scripts.baseline_experiment_utils import add_common_args, run_benchmark
from scripts.run_llm_benchmark import (
    BenchmarkCase,
    BenchmarkInput,
    UnseenBenchmarkCase,
    benchmark_condition,
    classify_failure,
    make_request,
    result_metadata,
)


def _try_materialize_trace_only(
    request: ProblemInput,
    spec: dict[str, Any],
) -> tuple[list[SolutionVariant], list[str], list[str], list[str], Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []
    verifier_result = None
    verifier_available = False
    verifier_code = str(spec.get("verifier_code") or "")
    if verifier_code.strip():
        try:
            verifier_result = run_verifier(verifier_code, request.input_data)
            verifier_available = True
            checks.append("独立 verifier 执行通过")
        except Exception as exc:
            errors.append(f"独立 verifier 执行失败：{exc}")

    good_variants: list[SolutionVariant] = []
    for variant in parse_variants(spec):
        try:
            materialized = execute_variant(variant, request.input_data)
            if verifier_available and canonical(materialized.result) != canonical(verifier_result):
                raise ValueError(f"结果 {materialized.result!r} 与 verifier {verifier_result!r} 不一致")
            if request.expected_result is not None and canonical(materialized.result) != canonical(request.expected_result):
                raise ValueError(f"结果 {materialized.result!r} 与 expected {request.expected_result!r} 不一致")
            assert materialized.trace is not None
            trace_errors, trace_warnings = validate_trace(materialized.trace)
            if trace_errors:
                raise ValueError("; ".join(trace_errors))
            warnings.extend(f"{materialized.name}: {warning}" for warning in trace_warnings)
            process_errors, process_warnings = validate_process(materialized.trace)
            if process_errors:
                raise ValueError("; ".join(process_errors))
            warnings.extend(f"{materialized.name}: {warning}" for warning in process_warnings)
            demo_report = validate_variant_demo_readiness(materialized.id, materialized.name, materialized.trace)
            if demo_report.errors:
                raise ValueError("; ".join(demo_report.errors))
            warnings.extend(f"{materialized.name}: {warning}" for warning in demo_report.warnings)
            good_variants.append(materialized)
            checks.append(f"{materialized.name}：solve/trace/process/demo 通过；SceneGraph compiler disabled")
        except Exception as exc:
            errors.append(f"{variant.name} 失败：{exc}")

    if len(good_variants) > 1:
        baseline = good_variants[0].result
        for variant in good_variants[1:]:
            if canonical(variant.result) != canonical(baseline):
                errors.append(f"多解法结果不一致：{good_variants[0].name} vs {variant.name}")
        if not any("多解法结果不一致" in error for error in errors):
            checks.append("多解法交叉结果一致")
    if not good_variants:
        errors.append("scene_error: no trace-only variant available")
    return good_variants, errors, warnings, checks, verifier_result


def build_trace_only_variants(
    request: ProblemInput,
    *,
    max_rounds: int,
    strict_warnings: bool,
    repair_failure_types_out: list[str],
) -> tuple[dict[str, Any], list[SolutionVariant], list[str], list[str], Any]:
    spec = generate_solution_spec(request)
    last_errors: list[str] = []
    for round_idx in range(max_rounds + 1):
        variants, errors, warnings, checks, verifier_result = _try_materialize_trace_only(request, spec)
        if variants and not errors:
            return spec, variants, warnings, checks, verifier_result
        last_errors = errors or []
        if round_idx < max_rounds:
            for failure_type in repair_failure_types(last_errors):
                if failure_type not in repair_failure_types_out:
                    repair_failure_types_out.append(failure_type)
            spec = repair_solution_spec(request, spec, last_errors)
    raise BuildError("没有生成 trace-only HTML 产物：\n" + "\n".join(last_errors))


def render_trace_only_html(
    *,
    title: str,
    input_data: Any,
    expected: Any,
    variants: list[SolutionVariant],
    checks: list[str],
    warnings: list[str],
) -> str:
    variant = variants[0]
    trace = variant.trace
    frames = [event.model_dump() for event in trace.events] if trace else []
    payload = {
        "input": input_data,
        "expected": expected,
        "result": variant.result,
        "variant": {"id": variant.id, "name": variant.name, "strategy": variant.strategy},
        "frames": frames,
        "checks": checks,
        "warnings": warnings,
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} - no SceneGraph compiler</title>
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif; color:#172033; background:#f6f7fb; }}
    main {{ max-width:1080px; margin:0 auto; padding:18px; display:grid; gap:12px; }}
    header, section {{ background:#fff; border:1px solid #d7deea; border-radius:8px; padding:14px; }}
    h1 {{ margin:0; font-size:22px; }}
    .meta {{ color:#657085; font-size:13px; margin-top:6px; }}
    #canvas {{ min-height:260px; white-space:pre-wrap; line-height:1.5; }}
    button {{ border:1px solid #2563eb; background:#2563eb; color:#fff; border-radius:6px; padding:8px 11px; cursor:pointer; }}
    pre {{ margin:0; overflow:auto; white-space:pre-wrap; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1 id="title">{safe_title}</h1>
      <div class="meta">no_scenegraph_compiler ablation：使用 trace-only renderer，未调用 SceneGraph compiler。</div>
      <div id="counter">1 / {max(1, len(frames))}</div>
    </header>
    <section id="canvas"></section>
    <section>
      <button id="next" type="button">下一步</button>
    </section>
  </main>
  <script>
    const PAYLOAD = {payload_json};
    let stepIndex = 0;
    function esc(value) {{
      return String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
    }}
    function render() {{
      const frames = PAYLOAD.frames && PAYLOAD.frames.length ? PAYLOAD.frames : [{{op:'explain', reason:'无 trace frame', state:{{}}}}];
      stepIndex = Math.max(0, Math.min(stepIndex, frames.length - 1));
      const frame = frames[stepIndex];
      document.getElementById('counter').textContent = `${{stepIndex + 1}} / ${{frames.length}}`;
      document.getElementById('canvas').innerHTML = [
        `<h2>${{esc(frame.op || 'step')}}</h2>`,
        `<p>${{esc(frame.reason || '')}}</p>`,
        `<pre>${{esc(JSON.stringify({{targets: frame.targets, deps: frame.deps, value: frame.value, state: frame.state}}, null, 2))}}</pre>`
      ].join('');
    }}
    document.getElementById('next').addEventListener('click', () => {{
      const frames = PAYLOAD.frames && PAYLOAD.frames.length ? PAYLOAD.frames : [{{}}];
      stepIndex = Math.min(stepIndex + 1, frames.length - 1);
      render();
    }});
    render();
  </script>
</body>
</html>
"""


def run_one_no_scenegraph_compiler(
    case: BenchmarkCase | UnseenBenchmarkCase,
    sample: BenchmarkInput,
    sample_index: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started = time.time()
    clear_model_calls()
    request = make_request(case, sample, solutions=args.solutions)
    output_stem = f"no_scenegraph_compiler_{case.id}_{sample_index}"
    output_html = args.output_dir / f"{output_stem}.html"
    metadata = result_metadata(case, sample_index, args)
    repair_types: list[str] = []
    try:
        _spec, variants, warnings, checks, verifier_result = build_trace_only_variants(
            request,
            max_rounds=args.max_rounds,
            strict_warnings=args.strict_warnings,
            repair_failure_types_out=repair_types,
        )
        html = render_trace_only_html(
            title=case.title,
            input_data=sample.input_data,
            expected=sample.expected,
            variants=variants,
            checks=checks,
            warnings=warnings,
        )
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html, encoding="utf-8")
        output_html.with_suffix(".json").write_text(
            json.dumps(
                {
                    "kind": "no_scenegraph_compiler_trace_only_artifact",
                    "case_id": case.id,
                    "sample_index": sample_index,
                    "condition": benchmark_condition(args),
                    "scenegraph_compiler_enabled": False,
                    "variant_count": len(variants),
                    "verifier_result": verifier_result,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        variant_rows = [
            {
                "id": variant.id,
                "name": variant.name,
                "result": variant.result,
                "steps": len(variant.trace.events) if variant.trace else 0,
            }
            for variant in variants
        ]
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "ablation": "no_scenegraph_compiler",
            "process_validator_enabled": True,
            "scenegraph_compiler_enabled": False,
            "trace_only_renderer_enabled": True,
            "ok": True,
            "checks": checks,
            "warnings": warnings,
            "variants": variant_rows,
            "html": str(output_html),
            "json": str(output_html.with_suffix(".json")),
            "duration_s": round(time.time() - started, 3),
            "failure_type": "",
            "repair_failure_types": repair_types,
            "model_calls": consume_model_calls(),
        }
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        return {
            "case_id": case.id,
            "title": case.title,
            "family": case.family,
            **metadata,
            "sample_index": sample_index,
            "input_data": sample.input_data,
            "expected": sample.expected,
            "model": _model_name(),
            "condition": benchmark_condition(args),
            "ablation": "no_scenegraph_compiler",
            "process_validator_enabled": True,
            "scenegraph_compiler_enabled": False,
            "trace_only_renderer_enabled": True,
            "ok": False,
            "error": message,
            "failure_type": classify_failure(message),
            "duration_s": round(time.time() - started, 3),
            "repair_failure_types": repair_types,
            "model_calls": consume_model_calls(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 no_scenegraph_compiler 消融，输出 trace-only HTML")
    add_common_args(parser, condition="no_scenegraph_compiler")
    args = parser.parse_args()
    args.ablation = "no_scenegraph_compiler"
    args.process_validator_enabled = True
    args.scenegraph_compiler_enabled = False
    args.direct_html_baseline = False
    args.trace_only_renderer_enabled = True
    return run_benchmark(args, run_one_no_scenegraph_compiler)


if __name__ == "__main__":
    raise SystemExit(main())
