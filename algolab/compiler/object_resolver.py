"""Shared resolution of basic state values into scene objects."""

from __future__ import annotations

from typing import Any

from algolab.schemas.scene_graph import SceneObject, SceneObjectType


SEQUENCE_LAYOUT_KEYS = {"heap", "stack", "queue", "deque"}


def resolve_basic_state_objects(state: dict[str, Any]) -> list[SceneObject]:
    objects: list[SceneObject] = []
    for key, value in state.items():
        objects.extend(resolve_basic_state_value(key, value))
    return objects


def resolve_basic_state_value(key: str, value: Any) -> list[SceneObject]:
    if _is_set_grid(key, value):
        return _set_grid_objects(key, value)
    if _is_matrix(value):
        return _matrix_objects(key, value)
    if key not in SEQUENCE_LAYOUT_KEYS and _is_string_list(value):
        return _string_list_objects(key, value)
    if _is_scalar_list(value):
        return _scalar_list_objects(key, value)
    if isinstance(value, dict):
        return _map_objects(key, value)
    if isinstance(value, (int, float, str, bool)) or value is None:
        return [SceneObject(id=key, type=SceneObjectType.LABEL, label=key, value=value)]
    return []


def known_target_ids(objects: list[SceneObject]) -> set[str]:
    return {obj.id for obj in objects}


def basic_state_target_ids(state: dict[str, Any]) -> set[str]:
    return known_target_ids(resolve_basic_state_objects(state))


def _matrix_objects(key: str, value: list[list[Any]]) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "matrix"})]
    for r, row in enumerate(value):
        objects.append(SceneObject(id=f"{key}[{r}]", type=SceneObjectType.LABEL, label=str(r), parent=key, row=r))
        for c, cell in enumerate(row):
            objects.append(
                SceneObject(
                    id=f"{key}[{r}][{c}]",
                    type=SceneObjectType.CELL,
                    value=cell,
                    parent=key,
                    row=r,
                    col=c,
                )
            )
    return objects


def _string_list_objects(key: str, value: list[str]) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "string_list"})]
    for r, item in enumerate(value):
        objects.append(SceneObject(id=f"{key}[{r}]", type=SceneObjectType.LABEL, label=str(r), value=item, parent=key, row=r))
        for c, char in enumerate(item):
            objects.append(
                SceneObject(
                    id=f"{key}[{r}][{c}]",
                    type=SceneObjectType.CELL,
                    value=char,
                    parent=key,
                    row=r,
                    col=c,
                )
            )
    return objects


def _set_grid_objects(key: str, value: list[list[Any]]) -> list[SceneObject]:
    objects = [
        SceneObject(
            id=key,
            type=SceneObjectType.CONTAINER,
            label=key,
            meta={"layout": "set_grid", "subset_count": len(value)},
        )
    ]
    for r, row in enumerate(value):
        objects.append(
            SceneObject(
                id=f"{key}[{r}]",
                type=SceneObjectType.LABEL,
                label=str(r),
                value="[]" if not row else None,
                parent=key,
                row=r,
            )
        )
        for c, item in enumerate(row):
            objects.append(
                SceneObject(
                    id=f"{key}[{r}][{c}]",
                    type=SceneObjectType.CELL,
                    value=item,
                    parent=key,
                    row=r,
                    col=c,
                )
            )
    return objects


def _scalar_list_objects(key: str, value: list[Any]) -> list[SceneObject]:
    layout = key if key in SEQUENCE_LAYOUT_KEYS else "array"
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": layout})]
    for i, item in enumerate(value):
        objects.append(
            SceneObject(
                id=f"{key}[{i}]",
                type=SceneObjectType.CELL,
                value=item,
                parent=key,
                index=i,
            )
        )
    return objects


def _map_objects(key: str, value: dict[Any, Any]) -> list[SceneObject]:
    objects = [SceneObject(id=key, type=SceneObjectType.CONTAINER, label=key, meta={"layout": "map"})]
    for mk, mv in value.items():
        objects.append(
            SceneObject(
                id=f"{key}[{mk}]",
                type=SceneObjectType.LABEL,
                label=str(mk),
                value=mv,
                parent=key,
            )
        )
    return objects


def _is_scalar_list(value: Any) -> bool:
    return isinstance(value, list) and all(not isinstance(x, (list, dict)) for x in value)


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def _is_set_grid(key: str, value: Any) -> bool:
    if key not in {"answer", "ans", "result", "subsets", "combinations", "permutations", "powerset"}:
        return False
    if not isinstance(value, list) or not value or not all(isinstance(row, list) for row in value):
        return False
    if not all(all(not isinstance(item, (list, dict)) for item in row) for row in value):
        return False
    widths = [len(row) for row in value]
    return 0 in widths or len(set(widths)) > 1


def _is_matrix(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(row, list) for row in value)
