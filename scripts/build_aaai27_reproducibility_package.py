"""Build the anonymous AAAI-27 Code/Data Supplement."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "deliverables/aaai27_reproducibility_package_20260727"
CODE_DATA_ROOT = PACKAGE_ROOT / "code_data_supplement"
TEXT_SUFFIXES = {
    ".bib", ".cfg", ".csv", ".json", ".jsonl", ".md", ".py", ".sh",
    ".tex", ".txt", ".yaml", ".yml",
}
EXCLUDE_NAMES = {
    "api_settings.json", "api_settings.yaml", "api_settings.yml",
    ".algolab_api_settings.json", ".algolab_api_settings.yaml",
    ".algolab_api_settings.yml",
}
EXCLUDE_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}


def _sanitize_text(text: str) -> str:
    text = text.replace(str(ROOT), ".")
    text = text.replace("/ssd1/liaokunpeng/agent-py310-cu/bin/python3", "python3")
    text = text.replace("/ssd1/liaokunpeng/.tmp", "/tmp")
    text = text.replace("/ssd1/liaokunpeng/.cleanup", "/tmp")
    text = text.replace("liaokunpeng-etal-2026-algogen", "anonymous-etal-2026-algogen")
    text = text.replace("Liaokunpeng", "Anonymous Authors")
    text = text.replace("#!python3", "#!/usr/bin/env python3")
    return text


def _copy_file(source: Path, target: Path, *, sanitize: bool = True) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if sanitize and source.suffix.lower() in TEXT_SUFFIXES:
        try:
            target.write_text(
                _sanitize_text(source.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
            shutil.copymode(source, target)
            return
        except (UnicodeDecodeError, OSError):
            pass
    shutil.copy2(source, target)


def _copy_tree(
    source: Path,
    target: Path,
    *,
    suffixes: set[str] | None = None,
) -> None:
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if any(part in EXCLUDE_PARTS for part in relative.parts):
            continue
        if path.name in EXCLUDE_NAMES:
            continue
        if suffixes is not None and path.suffix.lower() not in suffixes:
            continue
        _copy_file(path, target / relative)


def _copy_relative(
    relative_paths: Iterable[str],
    *,
    destination_root: Path = CODE_DATA_ROOT,
) -> None:
    for relative in relative_paths:
        source = ROOT / relative
        if not source.exists():
            continue
        target = destination_root / relative
        if source.is_dir():
            _copy_tree(source, target)
        else:
            _copy_file(source, target)


def _copy_selected_reports() -> None:
    files = [
        "output/experiments/algotutorgen_full_200_20260706/report/experiment_summary.json",
        "output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json",
        "output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine_rendered_text/interaction_semantic_eval_report.json",
        "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json",
        "output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json",
        "output/experiments/algotutorgen_completion_20260713/statistics/paired_statistics.json",
        "output/experiments/algotutorgen_completion_20260713/statistics/ablation_machine_statistics.json",
        "output/experiments/algotutorgen_completion_20260713/statistics/ablation_paired_statistics.json",
        "output/experiments/algotutorgen_completion_20260713/cross_input_replay/cross_input_replay_report.json",
        "output/experiments/algotutorgen_multimodel_full200_20260713/multimodel_summary.json",
        "output/experiments/algotutorgen_plan_completion_20260713/long_trace_scalability/long_trace_scalability_report.json",
        "output/experiments/algotutorgen_plan_completion_20260713/validator_fault_rerun/gate_fault_injection_report.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/stage1/llm_benchmark_report.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/stage1/family_summary.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/direct/llm_benchmark_report.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/direct/family_summary.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/machine_audit/interaction_semantic_eval_report.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/machine_audit/interaction_semantic_eval_report_strict.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/machine_audit_direct/interaction_semantic_eval_report.json",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/statistics/functional/paired_machine_statistics.csv",
        "output/experiments/algotutorgen_plan_completion_20260713/heldout_40/statistics/functional/paired_machine_statistics.md",
        "output/external_baselines/webgen/audit_all200_sample0/report.json",
        "output/external_baselines/htmlcure_all200_sample0/htmlcure_full200_analysis.json",
        "output/external_baselines/traditional_systems/overlap_study_summary.json",
        "output/experiments/direct_browser_repair_fair_20260723/fair_repair_report.json",
        "output/experiments/direct_browser_repair_fair_20260723/fair_repair_report.md",
        "output/experiments/direct_browser_repair_fair_20260723/frozen_initial_manifest.csv",
        "output/experiments/direct_browser_repair_fair_20260723/per_task_transitions.csv",
        "output/experiments/theory_aligned_20260714/semantic_preservation_report.json",
        "output/experiments/theory_aligned_20260714/semantic_mutation_report.json",
        "output/experiments/theory_aligned_20260714/cross_model_overlay_report.json",
        "output/experiments/theory_aligned_20260714/noninterference_stress_report.json",
        "output/experiments/theory_aligned_20260714/nested_contract_survival_report.json",
        "output/experiments/theory_aligned_20260714/retry_flash/local_vs_global_retry_report.json",
        "output/experiments/theory_aligned_20260714/retry_glm/local_vs_global_retry_report.json",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/atomic/llm_benchmark_report.json",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/atomic/llm_benchmark_report.md",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/decoupled/llm_benchmark_report.json",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/decoupled/llm_benchmark_report.md",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/atomic_service_full200_report.json",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/atomic_service_full200_report.md",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/atomic_service_full200_report.csv",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/machine_audits/atomic/interaction_semantic_eval_report.json",
        "output/experiments/plan3_20260725/atomic_service_manual_claim_full200/machine_audits/decoupled/interaction_semantic_eval_report.json",
        "output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/wrong_self_consistent_solver_audit.json",
        "output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/attempts.jsonl",
        "output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/applicable_mutants.csv",
        "output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/manifest.json",
        "output/experiments/total_token_cost_reliability_20260725/total_token_cost_reliability.json",
        "output/experiments/total_token_cost_reliability_20260725/total_token_cost_reliability.md",
        "output/experiments/total_token_cost_reliability_20260725/per_task_ledger.csv",
        "output/experiments/total_token_cost_reliability_20260725/token_cap_curve.csv",
        "output/experiments/total_token_cost_reliability_20260725/budget_curve.csv",
        "output/experiments/total_token_cost_reliability_20260725/total_token_cost_reliability.png",
        "output/experiments/all_method_auxiliary_eval_20260718/all_method_auxiliary_eval_report.json",
        "output/experiments/all_method_auxiliary_eval_20260718/all_method_auxiliary_eval_report.md",
    ]
    _copy_relative(files)
    mutant_source = ROOT / "output/experiments/plan3_20260725/wrong_self_consistent_solver_audit/mutant_sources"
    _copy_tree(
        mutant_source,
        CODE_DATA_ROOT / mutant_source.relative_to(ROOT),
        suffixes={".py"},
    )


def _write_package_docs() -> None:
    readme = """# AlgoTutorGen AAAI-27 Reproducibility Package

This anonymous archive contains the current executable implementation, frozen
benchmark definitions, exact prompt files, representative 23-case method
artifacts, paper-supporting reports, and current LaTeX sources. It does not
contain API credentials.

## Contents

- `code_data_supplement/algolab/`: implementation, runtime, validators, and renderers.
- `code_data_supplement/benchmark/`: 200-task/646-input and held-out definitions.
- `code_data_supplement/scripts/`: generation, audit, and analysis entry points.
- `code_data_supplement/artifacts/method_comparison_samples_en/`: 23 representative cases with artifacts, pages, screenshots, audits, and baseline source.
- `code_data_supplement/output/`: selected frozen reports at the paths used by the paper.
- `code_data_supplement/paper/latex/`: paper, supplement, figures, style, and bibliography sources.
- `supplementary_document.pdf`: current supplement compiled with pdfLaTeX.
- `reproducibility_checklist.pdf`: current checklist compiled with pdfLaTeX.
- `SHA256SUMS`: SHA-256 manifest for this directory.

## Deterministic checks

Run from `code_data_supplement/` with Python 3.10+:

```bash
python3 scripts/run_quality_checks.py
python3 -m pytest tests/regression -q
```

Install the pinned packages in `requirements-browser-smoke.txt`. Live LLM runs
require an externally configured `ALGOLAB_LLM_API_KEY`; credentials are not
part of the archive.

## Scope

The archive includes the reports needed to inspect the paper's final numbers
and the 23-case qualitative evidence, rather than the 24GB historical output
tree. Missing cited materials are listed in `MISSING_MATERIALS.md`. Remote model
versions, provider responses, browser binaries, and API latency can drift.
"""
    missing = """# Materials Not Available

- `artifacts/method_comparison_samples_en/manifest.json` is present and included.
- `latex/figure-generation/AlgoTutorGen-ssv-pvcr-artifact-showcase-editable.pptx` is absent from the workspace.
- `latex/figure-generation/figure2-system-architecture-ssv-pvcr-editable.pptx` is absent from the workspace.
- `single_execution_trace_audit.json` is cited by `latex/supplement.tex`, but no file with that name exists under `output/`.
- The claimed 1,292-run execution audit is represented by available source validators and aggregate reports, not by the cited single JSON ledger.
"""
    (PACKAGE_ROOT / "README.md").write_text(readme, encoding="utf-8")
    (PACKAGE_ROOT / "MISSING_MATERIALS.md").write_text(missing, encoding="utf-8")


def _copy_pdfs() -> None:
    for source, target_name in (
        (Path("/tmp/aaai-pdftex-anon/supplement.pdf"), "supplementary_document.pdf"),
        (
            Path("/tmp/aaai-pdftex/reproducibility-checklist.pdf"),
            "reproducibility_checklist.pdf",
        ),
    ):
        if source.exists():
            _copy_file(source, PACKAGE_ROOT / target_name, sanitize=False)


def _write_manifest() -> None:
    rows = []
    for path in sorted(PACKAGE_ROOT.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(f"{digest}  {path.relative_to(PACKAGE_ROOT).as_posix()}")
    (PACKAGE_ROOT / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def build() -> Path:
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    archive = PACKAGE_ROOT.with_suffix(".zip")
    if archive.exists():
        archive.unlink()
    CODE_DATA_ROOT.mkdir(parents=True, exist_ok=False)

    _copy_relative([
        "README.md", "SYSTEM_OVERVIEW.md", "architecture.md", "app.py",
        "cli.py", "llm_client.py", ".env.example", "requirements-browser-smoke.txt",
    ])
    _copy_tree(ROOT / "algolab", CODE_DATA_ROOT / "algolab")
    _copy_tree(ROOT / "benchmark", CODE_DATA_ROOT / "benchmark")
    _copy_tree(ROOT / "scripts", CODE_DATA_ROOT / "scripts")
    _copy_relative(["tests/__init__.py", "tests/benchmark_regression.py"])
    _copy_tree(ROOT / "tests/regression", CODE_DATA_ROOT / "tests/regression")
    _copy_relative([
        "docs/EXPERIMENT_RESULTS.md",
        "docs/EXPERIMENT_RESULTS_DETAILED.md",
        "docs/20_ALGOTUTORGEN_PROMPT_APPENDIX.md",
        "docs/32_EXPERT_AUDIT_ALGORITHMIC_TRACE_FIDELITY.md",
        "docs/34_TOTAL_TOKEN_COST_RELIABILITY_EXPERIMENT.md",
        "docs/35_ATOMIC_SERVICE_PILOT_EXPERIMENT.md",
        "docs/36_WRONG_SELF_CONSISTENT_SOLVER_AUDIT.md",
    ])
    _copy_tree(ROOT / "latex", CODE_DATA_ROOT / "paper/latex")
    _copy_tree(
        ROOT / "artifacts/method_comparison_samples_en",
        CODE_DATA_ROOT / "artifacts/method_comparison_samples_en",
    )
    _copy_selected_reports()
    _copy_pdfs()
    _write_package_docs()
    _write_manifest()

    shutil.make_archive(
        str(PACKAGE_ROOT),
        "zip",
        root_dir=PACKAGE_ROOT.parent,
        base_dir=PACKAGE_ROOT.name,
    )
    return PACKAGE_ROOT.with_suffix(".zip")


if __name__ == "__main__":
    print(build())
