"""Export deterministic component-on/off ablation artifacts from saved BuildArtifact JSON.

This script does not call an LLM. It derives ablation artifacts by removing
optional teaching / interaction fields from an already generated artifact, then
exports JSON and HTML for each variant.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.renderer.export import save_html
from algolab.schemas.validation import BuildArtifact


ALL_VARIANTS = ("full", "no_teaching", "no_interaction", "no_teaching_interaction")


@dataclass(frozen=True)
class AblationVariant:
    name: str
    strip_teaching: bool
    strip_interaction: bool


VARIANTS = {
    "full": AblationVariant("full", strip_teaching=False, strip_interaction=False),
    "no_teaching": AblationVariant("no_teaching", strip_teaching=True, strip_interaction=False),
    "no_interaction": AblationVariant("no_interaction", strip_teaching=False, strip_interaction=True),
    "no_teaching_interaction": AblationVariant(
        "no_teaching_interaction",
        strip_teaching=True,
        strip_interaction=True,
    ),
}


def load_artifact(path: Path) -> BuildArtifact:
    return BuildArtifact.model_validate_json(path.read_text(encoding="utf-8"))


def collect_artifacts(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    paths.extend(args.artifact or [])
    if args.artifact_dir:
        for path in sorted(args.artifact_dir.glob(args.glob)):
            if path.name in {"llm_benchmark_report.json", "family_summary.json"}:
                continue
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if payload.get("schema_version") == "algolab-build-v1":
                paths.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    case_filters = set(args.case or [])
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if case_filters and not any(case_id in path.stem for case_id in case_filters):
            continue
        unique.append(path)
    return unique


def derive_artifact(artifact: BuildArtifact, variant: AblationVariant) -> BuildArtifact:
    derived = artifact.model_copy(deep=True)
    if not (variant.strip_teaching or variant.strip_interaction):
        return derived
    for scene in derived.scenes.values():
        for frame in scene.frames:
            if variant.strip_teaching:
                frame.teaching = None
            if variant.strip_interaction:
                frame.interaction = None
    for solution in derived.variants:
        if solution.trace is None:
            continue
        for event in solution.trace.events:
            if variant.strip_teaching:
                event.teaching = None
            if variant.strip_interaction:
                event.interaction = None
    return derived


def component_counts(artifact: BuildArtifact) -> dict[str, int]:
    scene_frames = [frame for scene in artifact.scenes.values() for frame in scene.frames]
    trace_events = [
        event
        for variant in artifact.variants
        if variant.trace is not None
        for event in variant.trace.events
    ]
    return {
        "scene_frames": len(scene_frames),
        "scene_teaching_frames": sum(1 for frame in scene_frames if frame.teaching),
        "scene_interaction_frames": sum(1 for frame in scene_frames if frame.interaction),
        "trace_events": len(trace_events),
        "trace_teaching_events": sum(1 for event in trace_events if event.teaching),
        "trace_interaction_events": sum(1 for event in trace_events if event.interaction),
    }


def export_variant(
    artifact_path: Path,
    artifact: BuildArtifact,
    variant: AblationVariant,
    output_dir: Path,
    *,
    html: bool,
) -> dict[str, Any]:
    derived = derive_artifact(artifact, variant)
    variant_dir = output_dir / variant.name
    variant_dir.mkdir(parents=True, exist_ok=True)
    stem = artifact_path.stem
    html_path = variant_dir / f"{stem}.html"
    json_path = html_path.with_suffix(".json")
    if html:
        save_html(derived, html_path)
    else:
        json_path.write_text(derived.model_dump_json(indent=2), encoding="utf-8")
        html_path = Path("")
    return {
        "source_artifact": str(artifact_path),
        "variant": variant.name,
        "strip_teaching": variant.strip_teaching,
        "strip_interaction": variant.strip_interaction,
        "json": str(json_path),
        "html": str(html_path) if html_path else "",
        "counts": component_counts(derived),
    }


def write_manifest(rows: list[dict[str, Any]], output_dir: Path, args: argparse.Namespace) -> Path:
    manifest = {
        "kind": "component_ablation_export_manifest",
        "schema_version": "component-ablation-export-v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config": {
            "artifact": [str(path) for path in (args.artifact or [])],
            "artifact_dir": str(args.artifact_dir) if args.artifact_dir else "",
            "glob": args.glob,
            "case": args.case,
            "variants": args.variant,
            "html": args.html,
        },
        "total_exports": len(rows),
        "exports": rows,
    }
    path = output_dir / "component_ablation_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="从已生成 BuildArtifact 导出 teaching/interaction 开关消融产物")
    parser.add_argument("--artifact", action="append", type=Path, default=[], help="指定单个 BuildArtifact JSON，可重复传入")
    parser.add_argument("--artifact-dir", type=Path, default=None, help="批量读取 BuildArtifact JSON 的目录")
    parser.add_argument("--glob", default="*.json", help="配合 --artifact-dir 使用的 glob，默认 *.json")
    parser.add_argument("--case", action="append", default=[], help="只导出 stem 中包含该 case id 的 artifact，可重复传入")
    parser.add_argument("--output-dir", type=Path, default=Path("output/component_ablation_artifacts"), help="输出目录")
    parser.add_argument(
        "--variant",
        action="append",
        choices=ALL_VARIANTS,
        default=[],
        help="要导出的变体；默认导出 full/no_teaching/no_interaction/no_teaching_interaction",
    )
    parser.add_argument("--html", action=argparse.BooleanOptionalAction, default=True, help="是否同时导出 HTML")
    args = parser.parse_args()

    variants = [VARIANTS[name] for name in (args.variant or list(ALL_VARIANTS))]
    artifact_paths = collect_artifacts(args)
    if not artifact_paths:
        raise SystemExit("没有找到 BuildArtifact JSON。请传 --artifact 或 --artifact-dir。")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for artifact_path in artifact_paths:
        artifact = load_artifact(artifact_path)
        for variant in variants:
            rows.append(export_variant(artifact_path, artifact, variant, args.output_dir, html=args.html))

    manifest_path = write_manifest(rows, args.output_dir, args)
    print(f"component_ablation_exports: {len(rows)}")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
