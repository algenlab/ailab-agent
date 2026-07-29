"""Frozen prompt appendices for single-execution experiment conditions."""

from __future__ import annotations

import hashlib

from algolab.generation.prompt_profiles import load_profiled_prompt


# Atomic is the default production path; decoupled remains available for the
# single-execution ablation. ``separate`` is accepted only as a legacy alias.
EXECUTION_MODES = ("atomic", "decoupled")

_ATOMIC_APPENDIX = r"""
# 单执行实验模式：Atomic

`tracker_code/trace(input_data)` 是本条件的唯一权威执行。它必须在一次函数调用中完成算法计算、通过 TraceSession 服务更新可视化状态，并用 `sess.result(answer)` 提交同一次执行的最终答案。`code/solve(input_data)` 只用于页面展示，不参与本条件的运行或正确性判定。

继续使用现有 TraceSession API；每个服务调用会原子地更新 canonical state 并记录事件。不要直接修改 `sess` 或 DSL 对象的私有属性，不要手写或篡改 `to_trace()` 返回的 events/state/result。
""".strip()

_DECOUPLED_APPENDIX = r"""
# 单执行实验模式：Decoupled

`tracker_code/trace(input_data)` 是本条件的唯一权威执行。`code/solve(input_data)` 只用于页面展示。本条件把 canonical state 更新和事件记录拆成两个调用。

每个会改变 canonical state 的 TraceSession factory、DSL 更新方法或 `sess.result(answer)` 之后，必须在下一次服务调用前立即调用 `sess.record(...)`，由 tracker 显式填写 `op`、`targets`、`before`、`after`。这四个字段缺一不可；禁止空调用或让 runtime 代填。只读 compare/highlight/note 等调用由 runtime 直接记录，不需要 record。不要直接修改私有属性。

调用顺序必须严格交替：每个 factory 后立即 record，再调用下一个 factory。若更新前后值相同（`before == after`），该调用是 no-op，没有 pending transition，此时不要调用 record；只有真实状态变化才记录。

单 transition 示例：
```python
value = sess.scalar("value", initial)
sess.record(op="create", targets=["value"], before=None, after=None)

before = int(value)
new_value = before + 1
value.set(new_value, reason="更新 value")
sess.record(op="set", targets=["value"], before=before, after=new_value)

sess.result(answer)
sess.record(op="mark", targets=["answer"], before=None, after=answer)
return sess.to_trace()
```

`targets` 必须使用 DSL 事件的精确 target id，例如标量是 `value`，数组元素是 `nums[3]`，最终答案是 `answer`。factory 的公开 create event 使用 `before=None, after=None`。若某个 DSL 更新事件本身不公开局部 before/after（例如部分 push/pop/link），也显式填写 `None`；不得省略字段。

常用特殊语义：`PointerObj.move(...)` 的 op 是 `move`；`ArrayObj.swap(i, j)` 只产生一个 op=`set` 的 transition，targets 同时为 `["name[i]", "name[j]"]`，before/after 都是 `{i: value_i, j: value_j}`，不能拆成两次 record。`events=[...]` 只用于一次公开调用确实产生多个内部 transition 的方法。

一次公开 DSL 调用可能产生多个内部 transition，例如 `trie.insert("ab")`。此时必须按运行时顺序一次提交等长 claims：
```python
trie.insert("ab")
sess.record(events=[
    {"op": "create", "targets": ["node:1"], "before": None, "after": None},
    {"op": "create", "targets": ["node:2"], "before": None, "after": None},
    {"op": "set", "targets": ["node:2"], "before": None, "after": None},
])
```

不得漏记、在多次公开服务调用后合并记录、虚构字段，或修改 `to_trace()` 返回内容。claim 与同次执行的 runtime transition 不一致时，该候选会失败。
""".strip()


def normalize_execution_mode(execution_mode: str | None) -> str:
    mode = execution_mode or "atomic"
    if mode == "separate":
        mode = "atomic"
    if mode not in {"atomic", "decoupled"}:
        raise ValueError(f"unknown execution mode: {execution_mode}")
    return mode


def load_execution_prompt(name: str, prompt_profile: str, execution_mode: str) -> str:
    execution_mode = normalize_execution_mode(execution_mode)
    base = load_profiled_prompt(name, prompt_profile)
    if execution_mode == "atomic":
        appendix = _ATOMIC_APPENDIX
    elif execution_mode == "decoupled":
        appendix = _DECOUPLED_APPENDIX
    return f"{base.rstrip()}\n\n{appendix}\n"


def execution_mode_metadata(execution_mode: str, prompt_profile: str) -> dict[str, str]:
    execution_mode = normalize_execution_mode(execution_mode)
    generation = load_execution_prompt("tracker_system.txt", prompt_profile, execution_mode)
    repair = load_execution_prompt("repair_system.txt", prompt_profile, execution_mode)
    return {
        "execution_mode": execution_mode,
        "prompt_profile": prompt_profile,
        "profile_version": "single-execution-pilot-v2",
        "generation_prompt_sha256": hashlib.sha256(generation.encode("utf-8")).hexdigest(),
        "repair_prompt_sha256": hashlib.sha256(repair.encode("utf-8")).hexdigest(),
    }
