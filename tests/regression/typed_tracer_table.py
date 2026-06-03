"""Regression tests for typed Tracer table helpers."""

from __future__ import annotations

from algolab.runtime.tracer import Tracer
from algolab.schemas.semantic_trace import SemanticTrace
from algolab.compiler.scene_compiler import compile_scene
from algolab.verification.scene_validator import validate_scene
from algolab.verification.trace_validator import validate_trace


def test_table_helper_generates_valid_cell_refs_and_state():
    tracer = Tracer({"nums": [5, 2, 7, 3, 6, 1]}, algorithm="typed table")
    table = tracer.table("st", [[5, 2, 7, 3, 6, 1], [2, 2, 3, 3, 1], [2, 2, 1]])

    tracer.create("st", state=table.state(), reason="初始化 sparse table。")
    tracer.mark(table.cell(2, 1), deps=[table.cell(1, 1), table.cell(1, 3)], state=table.state(), reason="查询长度 4 的区间。")
    tracer.result(2)

    trace = SemanticTrace.model_validate(tracer.to_trace())
    errors, _warnings = validate_trace(trace)

    assert table.cell(2, 1) == "st[2][1]"
    assert not errors


def test_table_helper_ragged_state_compiles_scene_cells():
    tracer = Tracer({"nums": [5, 2, 7, 3, 6, 1]}, algorithm="typed table")
    table = tracer.table("st", [[5, 2, 7, 3, 6, 1], [2, 2, 3, 3, 1], [2, 2, 1]])

    tracer.create("st", state=table.state(), reason="初始化 sparse table。")
    tracer.mark(table.cell(2, 1), deps=[table.cell(1, 1), table.cell(1, 3)], state=table.state(), reason="查询长度 4 的区间。")
    tracer.result(2)

    trace = SemanticTrace.model_validate(tracer.to_trace())
    scene = compile_scene(trace)
    _errors, warnings = validate_scene(scene)
    frame_object_ids = [{obj.id for obj in frame.objects} for frame in scene.frames]

    assert any("st[2][1]" in ids for ids in frame_object_ids)
    assert not any("st[2][1]" in warning for warning in warnings)


def test_table_helper_rejects_missing_cell_before_trace_validation():
    tracer = Tracer({"nums": [5, 2, 7, 3, 6, 1]}, algorithm="typed table")
    table = tracer.table("st", [[5, 2, 7, 3, 6, 1], [2, 2, 3, 3, 1], [2]])

    try:
        table.cell(2, 1)
    except ValueError as exc:
        assert "st[2][1]" in str(exc)
        assert "不存在" in str(exc)
        return

    raise AssertionError("table.cell 应在不存在的 cell 上失败")


def run_all() -> None:
    test_table_helper_generates_valid_cell_refs_and_state()
    test_table_helper_ragged_state_compiles_scene_cells()
    test_table_helper_rejects_missing_cell_before_trace_validation()


if __name__ == "__main__":
    run_all()
    print("typed_tracer_table: PASS")
