"""Repair a failed LLM Direct Creative HTML page using the verified artifact."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.generation.direct_visual_renderer import build_direct_visual_repair_prompt, repair_direct_visual_html
from algolab.schemas.validation import BuildArtifact


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_failure_report(path: Path | None, *, html_path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        html_stem = html_path.stem if html_path is not None else ""
        for row in data["results"]:
            row_html = str(row.get("html") or "")
            if html_stem and Path(row_html).stem == html_stem:
                return row
        return {"summary": data.get("summary"), "results": data.get("results")}
    return data if isinstance(data, dict) else {"failure_report": data}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-json", type=Path, required=True)
    parser.add_argument("--broken-html", type=Path, default=None)
    parser.add_argument("--raw-output", type=Path, default=None)
    parser.add_argument("--failure-report", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stem", default="")
    parser.add_argument("--problem-description", default="")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument("--llm-max-tokens", type=int, default=24000)
    return parser.parse_args()


def apply_llm_overrides(args: argparse.Namespace) -> None:
    if int(args.timeout_s) > 0:
        os.environ["ALGOLAB_LLM_TIMEOUT_S"] = str(int(args.timeout_s))
    if int(args.llm_max_tokens) > 0:
        os.environ["ALGOLAB_LLM_MAX_TOKENS"] = str(int(args.llm_max_tokens))
    if args.model:
        os.environ["ALGOLAB_LLM_MODEL"] = str(args.model)


def main() -> int:
    args = parse_args()
    apply_llm_overrides(args)
    output_dir = args.output_dir.resolve()
    html_dir = output_dir / "html"
    prompt_dir = output_dir / "prompts"
    raw_dir = output_dir / "raw_llm"
    report_dir = output_dir / "audit"
    for directory in (html_dir, prompt_dir, raw_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    artifact = BuildArtifact.model_validate_json(args.artifact_json.read_text(encoding="utf-8"))
    source_path = args.raw_output or args.broken_html
    if source_path is None:
        raise SystemExit("provide --raw-output or --broken-html")
    broken_html = source_path.read_text(encoding="utf-8")
    failure_report = load_failure_report(args.failure_report, html_path=args.broken_html or args.raw_output)
    stem = args.stem or f"{args.artifact_json.stem}_creative_repair"

    started_at = now_iso()
    prompt = build_direct_visual_repair_prompt(
        artifact,
        broken_html=broken_html,
        failure_report=failure_report,
        problem_description=args.problem_description or artifact.problem_title,
    )
    prompt_path = prompt_dir / f"{stem}_prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    result = repair_direct_visual_html(
        artifact,
        broken_html=broken_html,
        failure_report=failure_report,
        problem_description=args.problem_description or artifact.problem_title,
        model=args.model,
    )
    ended_at = now_iso()

    raw_path = raw_dir / f"{stem}_raw.txt"
    raw_path.write_text(result.raw_output, encoding="utf-8")
    html_path = html_dir / f"{stem}.html"
    if result.creative_ok:
        html_path.write_text(result.html, encoding="utf-8")
        html_path.with_suffix(".json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

    report = {
        "kind": "creative_visual_repair_report",
        "schema_version": "creative-visual-repair-v1",
        "started_at": started_at,
        "ended_at": ended_at,
        "artifact_json": str(args.artifact_json.resolve()),
        "source": str(source_path.resolve()),
        "failure_report": str(args.failure_report.resolve()) if args.failure_report else "",
        "requested_model": args.model or "",
        "timeout_s": args.timeout_s,
        "llm_max_tokens": args.llm_max_tokens,
        "creative_ok": result.creative_ok,
        "html": str(html_path) if result.creative_ok else "",
        "prompt": str(prompt_path),
        "raw_output": str(raw_path),
        "errors": result.errors,
        "warnings": result.warnings,
        "model_calls": result.model_calls,
    }
    report_path = report_dir / f"{stem}_repair_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "creative_ok": result.creative_ok, "html": report["html"]}, ensure_ascii=False, indent=2))
    return 0 if result.creative_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
