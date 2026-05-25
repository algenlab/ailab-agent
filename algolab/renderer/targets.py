"""Renderer target selection helpers."""

from __future__ import annotations

from algolab.schemas.validation import BuildArtifact


def select_render_target(artifact: BuildArtifact) -> str:
    if artifact.render_report is not None:
        return artifact.render_report.actual_target.value
    return "teaching_2d"
