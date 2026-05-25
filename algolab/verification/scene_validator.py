"""Scene graph validation."""

from __future__ import annotations

from algolab.schemas.scene_graph import SceneGraph


VISIBLE_TYPES = {
    "cell",
    "node",
    "edge",
    "label",
    "pointer",
    "callout",
    "tensor",
    "batch",
    "parameter",
    "loss_curve",
    "gradient_vector",
    "decision_boundary",
    "training_epoch",
    "prediction",
}


def validate_scene(scene: SceneGraph) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if scene.schema_version != "scene-graph-v1":
        errors.append("scene schema_version 必须是 scene-graph-v1")
    if not scene.frames:
        errors.append("scene 必须包含至少一个 frame")
        return errors, warnings

    for frame in scene.frames:
        if not frame.objects:
            errors.append(f"第 {frame.step} 帧没有任何 scene object")
            continue
        object_ids = {obj.id for obj in frame.objects}
        visible = [obj for obj in frame.objects if obj.type.value in VISIBLE_TYPES]
        if not visible:
            errors.append(f"第 {frame.step} 帧没有可见对象")
        for mark in frame.marks:
            if mark.target not in object_ids:
                warnings.append(f"第 {frame.step} 帧 mark 指向不存在对象：{mark.target}")
        for obj in frame.objects:
            if obj.type.value in {"arrow", "edge"}:
                if obj.source and obj.source not in object_ids:
                    warnings.append(f"第 {frame.step} 帧 {obj.type.value} source 不在对象集合：{obj.source}")
                if obj.target and obj.target not in object_ids:
                    warnings.append(f"第 {frame.step} 帧 {obj.type.value} target 不在对象集合：{obj.target}")
    return errors, warnings
