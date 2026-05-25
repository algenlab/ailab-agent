"""Layout registry for the browser runtime."""

from __future__ import annotations

import json


LAYOUT_RENDERERS: dict[str, str] = {
    "array": "array",
    "matrix": "matrix",
    "string": "string",
    "heap": "heap",
    "queue": "queue",
    "deque": "queue",
    "stack": "stack",
    "graph": "graph",
    "tree": "tree",
    "trie": "tree",
    "union_find": "tree",
    "recursion_tree": "tree",
    "geometry": "geometry",
    "ml": "ml",
    "tensor": "ml",
    "batch": "ml",
    "parameter": "ml",
    "loss_curve": "ml",
    "gradient_vector": "ml",
    "computational_graph": "graph",
    "decision_boundary": "ml",
    "training_epoch": "ml",
    "prediction": "ml",
    "map": "map",
    "generic": "map",
}


def layout_registry_json() -> str:
    return json.dumps(LAYOUT_RENDERERS, ensure_ascii=False, sort_keys=True)
