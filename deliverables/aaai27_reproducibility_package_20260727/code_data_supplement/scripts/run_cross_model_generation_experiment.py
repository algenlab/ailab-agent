"""Run AlgoTutorGen and Direct HTML with a second generation model on 50 cases."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import _model_name, api_settings, chat_text_with_metadata
from scripts.run_direct_to_scenegraph_ablation import _manifest_rows, _repo_path, _write_json


DEFAULT_SOURCE_REPORT = ROOT / "output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
DEFAULT_OUTPUT_DIR = ROOT / "output/experiments/algotutorgen_plan_completion_20260713/cross_model_50"
FIXED_PYTHON = "python3"


def candidate_models(*, primary_model: str, configured: str = "") -> list[str]:
    raw = configured or os.environ.get("ALGOLAB_SECOND_MODEL_CANDIDATES", "") or "gemini-3-flash-preview"
    primary = primary_model.strip().lower()
    seen: set[str] = set()
    models: list[str] = []
    for item in raw.split(","):
        model = item.strip()
        key = model.lower()
        if not model or key == primary or key in seen:
            continue
        seen.add(key)
        models.append(model)
    return models


def build_method_commands(
    *,
    python_executable: str,
    case_ids: list[str],
    output_dir: Path,
    concurrency: int = 8,
) -> dict[str, list[str]]:
    case_args = [part for case_id in case_ids for part in ("--case", case_id)]
    return {
        "stage1": [
            python_executable,
            "scripts/run_llm_benchmark.py",
            *case_args,
            "--sample",
            "0",
            "--solutions",
            "2",
            "--max-rounds",
            "2",
            "--max-candidates",
            "2",
            "--timeout-s",
            "2400",
            "--strict-warnings",
            "--no-browser-smoke",
            "--concurrency",
            str(concurrency),
            "--condition",
            "algolab_full",
            "--output-dir",
            str(output_dir / "stage1"),
        ],
        "direct": [
            python_executable,
            "scripts/run_direct_html_baseline.py",
            *case_args,
            "--sample",
            "0",
            "--solutions",
            "1",
            "--max-rounds",
            "2",
            "--timeout-s",
            "2400",
            "--strict-warnings",
            "--no-browser-smoke",
            "--concurrency",
            str(concurrency),
            "--output-dir",
            str(output_dir / "direct"),
        ],
    }


def probe_model(model: str, output_path: Path) -> dict[str, Any]:
    started_at = datetime.now().isoformat(timespec="seconds")
    try:
        response = chat_text_with_metadata(
            "Return a short plain-text readiness response.",
            "Reply exactly READY.",
            model=model,
            kind="cross_model_probe",
        )
        content = str(response.get("content") or "").strip()
        payload = {
            "model": model,
            "ok": bool(content),
            "content": content[:200],
            "model_call": response.get("model_call") or {},
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "endpoint": api_settings().get("base_url"),
        }
    except Exception as exc:
        payload = {
            "model": model,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "endpoint": api_settings().get("base_url"),
        }
    _write_json(output_path, payload)
    return payload


def _report_complete(path: Path, count: int) -> bool:
    if not path.exists():
        return False
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return len(report.get("results") or []) == count


def _run_method(name: str, command: list[str], *, model: str, log_path: Path, count: int) -> dict[str, Any]:
    report_path = Path(command[-1]) / "llm_benchmark_report.json"
    if _report_complete(report_path, count):
        return {"method": name, "status": "reused", "returncode": 0, "report": str(report_path)}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["ALGOLAB_LLM_MODEL"] = model
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    return {
        "method": name,
        "status": "completed" if report_path.exists() else "failed",
        "returncode": completed.returncode,
        "report": str(report_path),
        "log": str(log_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--selection-manifest", type=Path, default=DEFAULT_OUTPUT_DIR.parent / "nondegenerate_ablations/selected_cases_50.json")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--primary-model", default="DeepSeek-V4-Pro")
    parser.add_argument("--candidate-models", default="")
    parser.add_argument("--model", default="", help="跳过候选顺序，直接探测并使用该模型")
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    source_report = _repo_path(args.source_report)
    output_dir = _repo_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source = json.loads(source_report.read_text(encoding="utf-8"))
    selected = _manifest_rows(
        source.get("results") or [],
        _repo_path(args.selection_manifest),
        count=args.count,
        seed=args.seed,
    )
    case_ids = [str(row["case_id"]) for row in selected]
    candidates = [args.model] if args.model else candidate_models(
        primary_model=args.primary_model,
        configured=args.candidate_models,
    )
    probes: list[dict[str, Any]] = []
    selected_model = ""
    for model in candidates:
        probe = probe_model(model, output_dir / "probes" / f"{model.replace('/', '_')}.json")
        probes.append(probe)
        if probe.get("ok"):
            selected_model = model
            break
    if not selected_model:
        _write_json(
            output_dir / "experiment_manifest.json",
            {"kind": "cross_model_generation", "status": "blocked_external", "probes": probes, "case_ids": case_ids},
        )
        print(json.dumps({"status": "blocked_external", "probes": probes}, ensure_ascii=False))
        return 2
    if args.probe_only:
        print(json.dumps({"status": "probe_ok", "model": selected_model}, ensure_ascii=False))
        return 0

    commands = build_method_commands(
        python_executable=FIXED_PYTHON,
        case_ids=case_ids,
        output_dir=output_dir,
        concurrency=args.concurrency,
    )
    runs = []
    for name in ("stage1", "direct"):
        runs.append(
            _run_method(
                name,
                commands[name],
                model=selected_model,
                log_path=output_dir / "logs" / f"{name}.log",
                count=len(case_ids),
            )
        )
    manifest = {
        "kind": "cross_model_generation",
        "status": "generated" if all(Path(run["report"]).exists() for run in runs) else "incomplete",
        "primary_model": args.primary_model,
        "second_model": selected_model,
        "endpoint": api_settings().get("base_url"),
        "case_ids": case_ids,
        "family_count": len({row.get("family_id") for row in selected}),
        "probes": probes,
        "runs": runs,
        "commands": commands,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(output_dir / "experiment_manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "model": selected_model, "runs": runs}, ensure_ascii=False))
    return 0 if manifest["status"] == "generated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
