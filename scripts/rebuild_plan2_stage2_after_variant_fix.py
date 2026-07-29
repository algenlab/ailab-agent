"""Rewrap saved Stage2 visual assets after the Creative Shell variant fix."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algolab.renderer.creative_direct import render_direct_visual_stage_shell_html
from algolab.schemas.validation import BuildArtifact


DEFAULT_STAGE2 = (
    ROOT
    / "output/experiments/algotutorgen_full_200_20260706/"
    "stage2_creative_visual_deepseek_v4pro_full200_parallel8_container_20260707"
)


def _resolve_path(value: str | Path, root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        if path.parts[:2] == ("/", "work"):
            return root / path.relative_to("/work")
        return path
    return root / path


def _repo_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rebuild_stage2_pages(
    *,
    manifest_path: Path,
    output_dir: Path,
    root: Path = ROOT,
    expected_cases: int = 200,
) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = _resolve_path(manifest_path, root)
    output_dir = _resolve_path(output_dir, root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = list(manifest.get("items") or [])
    if len(items) != expected_cases:
        raise ValueError(f"expected {expected_cases} cases, found {len(items)}")

    html_dir = output_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    rebuilt_items: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda row: str(row.get("case_id") or "")):
        case_id = str(item.get("case_id") or "")
        if not case_id:
            raise ValueError("manifest item missing case_id")
        artifact_path = _resolve_path(str(item.get("artifact_repo_path") or ""), root)
        report_path = _resolve_path(
            str(item.get("generation_report_repo_path") or ""), root
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        raw_path = _resolve_path(str(report.get("raw_output") or ""), root)
        for required in (artifact_path, report_path, raw_path):
            if not required.is_file():
                raise FileNotFoundError(f"{case_id}: missing {required}")

        artifact = BuildArtifact.model_validate_json(
            artifact_path.read_text(encoding="utf-8")
        )
        raw_output = raw_path.read_text(encoding="utf-8")
        html = render_direct_visual_stage_shell_html(artifact, raw_output)
        html_path = html_dir / f"{case_id}.html"
        html_path.write_text(html, encoding="utf-8")
        rebuilt_items.append(
            {
                **item,
                "html_repo_path": _repo_path(html_path, root),
                "html_host_path": str(html_path),
                "source_html_repo_path": str(item.get("html_repo_path") or ""),
                "raw_output_repo_path": _repo_path(raw_path, root),
                "artifact_sha256": _sha256(artifact_path),
                "raw_output_sha256": _sha256(raw_path),
                "html_sha256": _sha256(html_path),
                "rewrapped_without_api": True,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    rebuilt_manifest = {
        "kind": "plan2_stage2_variant_fix_manifest",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "source_manifest": _repo_path(manifest_path, root),
        "source_manifest_sha256": _sha256(manifest_path),
        "case_count": len(rebuilt_items),
        "api_calls": 0,
        "items": rebuilt_items,
    }
    rebuilt_manifest_path = output_dir / "selected_html_manifest_variant_fix.json"
    rebuilt_manifest_path.write_text(
        json.dumps(rebuilt_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = {
        "kind": "plan2_stage2_variant_fix_rebuild",
        "created_at": rebuilt_manifest["created_at"],
        "case_count": len(rebuilt_items),
        "api_calls": 0,
        "manifest": _repo_path(rebuilt_manifest_path, root),
        "manifest_sha256": _sha256(rebuilt_manifest_path),
        "all_artifacts_present": len(rebuilt_items) == expected_cases,
        "all_raw_outputs_present": len(rebuilt_items) == expected_cases,
        "all_html_present": all(
            _resolve_path(item["html_repo_path"], root).is_file()
            for item in rebuilt_items
        ),
    }
    (output_dir / "rebuild_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_STAGE2 / "selected_html_manifest_final.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output/experiments/plan2_20260722/p0_3_stage2_variant_fix",
    )
    parser.add_argument("--expected-cases", type=int, default=200)
    args = parser.parse_args()
    summary = rebuild_stage2_pages(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        expected_cases=args.expected_cases,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
