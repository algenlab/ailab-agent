"""Case-aware result equivalence helpers.

This module intentionally keeps normalization narrow. Generic JSON equality
stays strict; only known benchmark result shapes get semantic equivalence.
"""

from __future__ import annotations

import json
from numbers import Number
from typing import Any


def to_jsonable(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        if isinstance(value, set):
            return sorted(to_jsonable(v) for v in value)
        if isinstance(value, list):
            return [to_jsonable(v) for v in value]
        if isinstance(value, tuple):
            return [to_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {str(k): to_jsonable(v) for k, v in value.items()}
        return str(value)


def canonical(value: Any) -> str:
    return json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def results_equivalent(
    left: Any,
    right: Any,
    *,
    case_id: str | None = None,
    family_id: str | None = None,
    subfamily_id: str | None = None,
) -> bool:
    if canonical(left) == canonical(right):
        return True

    context = _context_key(case_id=case_id, family_id=family_id, subfamily_id=subfamily_id)
    left_context = _contextual_normal_form(left, context)
    right_context = _contextual_normal_form(right, context)
    if left_context is not None and left_context == right_context:
        return True

    left_graph = _canonical_graph_set_result(left)
    right_graph = _canonical_graph_set_result(right)
    if left_graph is not None and left_graph == right_graph:
        return True

    return _inverse_mapping(left) == right or _inverse_mapping(right) == left


def _context_key(*, case_id: str | None, family_id: str | None, subfamily_id: str | None) -> str:
    return " ".join(str(item or "").lower() for item in (case_id, family_id, subfamily_id))


def _contextual_normal_form(value: Any, context: str) -> Any:
    if _is_subset_context(context):
        return _canonical_subset_collection(value)
    if _is_kruskal_context(context):
        return _canonical_mst_result(value)
    return None


def _is_subset_context(context: str) -> bool:
    return "bitmask_subsets" in context or "subsets" in context or "subset_generation" in context


def _canonical_subset_collection(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    normalized: list[str] = []
    for subset in value:
        if not isinstance(subset, (list, tuple, set)):
            return None
        items = sorted(canonical(item) for item in subset)
        normalized.append(json.dumps(items, ensure_ascii=False, separators=(",", ":")))
    return tuple(sorted(normalized))


def _is_kruskal_context(context: str) -> bool:
    return "kruskal" in context or "mst" in context


def _canonical_mst_result(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Number):
        return {"weight": value, "edges": None}
    if not isinstance(value, dict):
        return None
    weight = _first_present(value, ("weight", "total_weight", "mst_weight", "cost"))
    edges = _first_present(value, ("edges", "mst_edges", "tree_edges"))
    if weight is None and edges is None:
        return None
    normalized_edges = _canonical_edge_collection(edges) if edges is not None else None
    if edges is not None and normalized_edges is None:
        return None
    return {"weight": weight, "edges": normalized_edges}


def _first_present(value: dict[Any, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in value:
            return value[key]
    return None


def _canonical_edge_collection(value: Any) -> tuple[tuple[str, str, str], ...] | None:
    if not isinstance(value, (list, tuple, set)):
        return None
    edges: list[tuple[str, str, str]] = []
    for edge in value:
        normalized = _canonical_edge(edge)
        if normalized is None:
            return None
        edges.append(normalized)
    return tuple(sorted(edges))


def _canonical_edge(edge: Any) -> tuple[str, str, str] | None:
    if isinstance(edge, str):
        for sep in ("->", "-", ","):
            if sep in edge:
                left, right = edge.split(sep, 1)
                u, v = sorted((left.strip(), right.strip()))
                return (u, v, "")
        return None
    if not isinstance(edge, (list, tuple)) or len(edge) < 2:
        return None
    u, v = sorted((str(edge[0]), str(edge[1])))
    weight = canonical(edge[2]) if len(edge) >= 3 else ""
    return (u, v, weight)


def _inverse_mapping(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not value:
        return None
    inverse: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (dict, list, tuple, set)):
            return None
        inverse_key = str(item)
        if inverse_key in inverse:
            return None
        inverse[inverse_key] = str(key)
    return inverse


def _canonical_graph_set_result(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or "articulation" not in value or "bridges" not in value:
        return None
    bridges = []
    for edge in value.get("bridges") or []:
        if not isinstance(edge, (list, tuple)) or len(edge) < 2:
            return None
        bridges.append(tuple(sorted((str(edge[0]), str(edge[1])))))
    return {
        "articulation": sorted(str(item) for item in (value.get("articulation") or [])),
        "bridges": sorted(bridges),
    }
