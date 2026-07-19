"""Runtime capability declarations for VisualPlan generation."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


_CAPABILITIES: dict[str, Any] = {
    "schema_version": "runtime-capabilities-v1",
    "render_targets": ["teaching_2d", "spatial_3d", "hybrid_2_5d", "creative"],
    "target_status": {
        "teaching_2d": "stable",
        "creative": "stable",
        "spatial_3d": "stable",
        "hybrid_2_5d": "planned",
    },
    "supported_layouts": [
        "array",
        "matrix",
        "graph",
        "queue",
        "stack",
        "map",
        "tree",
        "heap",
        "trie",
        "union_find",
        "recursion_tree",
        "string",
        "geometry",
        "ml",
        "tensor",
        "batch",
        "parameter",
        "loss_curve",
        "gradient_vector",
        "computational_graph",
        "decision_boundary",
        "training_epoch",
        "prediction",
        "generic",
    ],
    "primitive_3d_support": {
        "node": "planned",
        "edge": "planned",
        "cell_block": "planned",
        "matrix_plane": "planned",
        "pointer_beam": "planned",
        "path_trail": "planned",
        "queue_dock": "planned",
        "stack_tower": "planned",
        "camera_focus": "planned",
    },
    "device_constraints": {
        "max_nodes_3d": 120,
        "max_cells_animated": 400,
        "mobile_prefer_2d": True,
        "single_file_html": True,
        "offline_assets_preferred": True,
    },
    "safety_rules": [
        "VisualPlan cannot include DOM/CSS/JS/Three.js code",
        "unsupported targets must fall back to the same SceneGraph baseline renderer",
        "fallback cannot invent conceptual video content",
    ],
}


def runtime_capabilities() -> dict[str, Any]:
    return deepcopy(_CAPABILITIES)


def capabilities_prompt_context() -> str:
    return json.dumps(runtime_capabilities(), ensure_ascii=False, indent=2)
