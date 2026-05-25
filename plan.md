# Tracer API 与 Trace 粒度策略实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 LLM 自由手写 `events.append({...})` 的 tracker 机制升级为受系统控制的 `Tracer API`，统一管理 trace 格式、逐帧/抽样策略、覆盖率统计和调试对齐能力。

**Architecture:** LLM 仍然生成 `tracker_code`，但 tracker 不直接拼装 trace JSON，而是在算法执行过程中调用系统提供的 `Tracer`。`Tracer` 负责生成标准 `SemanticTrace`、执行粒度策略、统计覆盖率，并为未来 debug mode 提供可对齐的事件序列。

**Tech Stack:** Python 3.10, Pydantic schemas, existing `algolab/runtime/sandbox.py`, `algolab/runtime/executor.py`, `algolab/verification/process_validator.py`, `tests/offline_regression.py`.

---

## 0. 背景和六个价值

当前机制：

```text
LLM 生成 tracker_code
tracker_code 手写 events 列表
trace(input_data) 返回 trace JSON
系统校验 trace JSON
```

主要问题是 LLM 同时负责：

1. 执行算法。
2. 决定记录哪些步骤。
3. 手写 trace schema。
4. 控制逐帧还是抽样。

这导致它可能写出：

```python
if len(events) < 6 or (i == m - 1 and j == n - 1):
    events.append(...)
```

结果是小 DP 表只展示前几帧，然后直接跳到最终格。

Tracer API 要解决的六个问题：

1. **防止跳帧**：小输入必须完整记录，大输入抽样必须由系统策略决定。
2. **统一 trace schema**：LLM 不再手写 event dict，系统统一补 `step/op/targets/deps/state` 等字段。
3. **统一粒度策略**：`full / sampled / strict` 等策略集中配置，而不是散落在 prompt 和 LLM 代码里。
4. **支持调试模式**：标准代码和学生代码用同一套事件接口，后续可以对齐比较第一处分歧。
5. **支持质量指标**：输出真实更新数、记录事件数、覆盖率、抽样率、缺失关键转移。
6. **支持大输入降级**：当事件过多时明确进入 sampled mode，并在 artifact/report 中声明，而不是静默省略。

---

## 1. 目标行为

### 1.1 LLM 生成的 tracker 新形态

目标 tracker 写法：

```python
def trace(input_data):
    tracer = Tracer(input_data, algorithm="不同路径")
    m = input_data["m"]
    n = input_data["n"]
    dp = [[1] * n for _ in range(m)]

    tracer.create("dp", state={"dp": [row[:] for row in dp]}, reason="初始化第一行和第一列。")

    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
            tracer.set(
                f"dp[{i}][{j}]",
                value=dp[i][j],
                deps=[f"dp[{i - 1}][{j}]", f"dp[{i}][{j - 1}]"],
                state={"dp": [row[:] for row in dp], "i": i, "j": j},
                reason="当前位置只能从上方或左侧到达。",
            )

    tracer.result(dp[m - 1][n - 1])
    return tracer.to_trace()
```

禁止新 tracker 手写：

```python
events.append({...})
```

### 1.2 粒度策略

第一版只做三种策略：

```text
full      小输入完整保留所有事件
sampled   大输入保留关键帧，记录被抽样事实
strict    小输入发现关键更新缺失时报错
```

默认策略：

```text
max_events = 80
small input <= 80 semantic updates -> full + strict
large input > 80 semantic updates -> sampled
```

### 1.3 最小支持的 Tracer API

第一版实现这些方法：

```python
Tracer(input_data, algorithm="", pseudocode=None, max_events=80, policy="auto")
tracer.create(target, state=None, value=None, deps=None, role="current", reason="", code_line=1)
tracer.set(target, state=None, value=None, deps=None, role="current", reason="", code_line=1)
tracer.mark(target, state=None, value=None, deps=None, role="current", reason="", code_line=1)
tracer.move(target, state=None, value=None, deps=None, role="current", reason="", code_line=1)
tracer.compare(targets, state=None, value=None, deps=None, role="candidate", reason="", code_line=1)
tracer.push(target, state=None, value=None, deps=None, role="current", reason="", code_line=1)
tracer.pop(target, state=None, value=None, deps=None, role="current", reason="", code_line=1)
tracer.explain(target=None, state=None, value=None, deps=None, role="", reason="", code_line=1)
tracer.expect_updates(name, count)
tracer.result(value)
tracer.to_trace()
```

### 1.4 Trace 质量指标

`tracer.to_trace()` 返回的 trace 暂时仍符合现有 `SemanticTrace` schema。质量指标先放进每个 event 的 `state["_trace_meta"]` 或最终 explain 事件的 state 中，避免大改 schema。

建议 meta：

```python
{
    "_trace_meta": {
        "policy": "full",
        "max_events": 80,
        "raw_event_count": 13,
        "emitted_event_count": 13,
        "sampled": False,
        "expected_updates": {"dp": 12},
        "recorded_updates": {"dp": 12},
        "coverage": {"dp": 1.0}
    }
}
```

---

## 2. 文件结构

### 新增文件

- `algolab/runtime/tracer.py`
  - 定义 `Tracer`。
  - 定义 trace 粒度策略。
  - 统一生成 event dict。
  - 统计 raw events、emitted events、coverage。

- `tests/tracer_regression.py`
  - 专门测试 `Tracer` API。
  - 覆盖 full、sampled、strict、coverage、schema 输出。

### 修改文件

- `algolab/runtime/sandbox.py`
  - 把 `Tracer` 注入生成代码可用的 sandbox namespace。

- `algolab/runtime/executor.py`
  - 兼容 `trace(input_data)` 返回 `tracer.to_trace()` 的 dict。
  - 保持旧 tracker 兼容。

- `algolab/generation/prompts/tracker_system.txt`
  - 要求 LLM 使用 `Tracer API`。
  - 禁止新代码直接 `events.append`。
  - 说明小输入逐帧、大输入抽样由系统策略负责。

- `algolab/generation/prompts/repair_system.txt`
  - 如果发现手写 events 或跳帧，要求改为 `Tracer API`。

- `algolab/verification/process_validator.py`
  - 保留现有算法 invariant。
  - 增加通用 trace coverage 检查：如果 `_trace_meta.expected_updates` 存在，coverage 不足时报错。

- `tests/offline_regression.py`
  - 将 Tracer 回归纳入 `run_all()`。
  - 保留现有 sparse unique paths 反例。

- `SYSTEM_OVERVIEW.md`
  - 增加 Tracer API 说明。

- `SYSTEM_FLOW.html`
  - 增加 Tracer API 在流程中的位置。

---

## 3. 实施任务

### Task 1: 新增 Tracer 基础 API

**Files:**

- Create: `algolab/runtime/tracer.py`
- Create: `tests/tracer_regression.py`

- [ ] **Step 1: 写失败测试：Tracer 生成标准 SemanticTrace**

在 `tests/tracer_regression.py` 中加入：

```python
from algolab.runtime.tracer import Tracer
from algolab.schemas.semantic_trace import SemanticTrace


def test_tracer_builds_valid_semantic_trace():
    tracer = Tracer({"m": 2, "n": 2}, algorithm="不同路径", pseudocode=["dp[i][j] = dp[i-1][j] + dp[i][j-1]"])
    tracer.create("dp", state={"dp": [[1, 1], [1, 1]]}, reason="初始化。")
    tracer.set(
        "dp[1][1]",
        value=2,
        deps=["dp[0][1]", "dp[1][0]"],
        state={"dp": [[1, 1], [1, 2]], "i": 1, "j": 1},
        reason="来自上方和左侧。",
        code_line=3,
    )
    tracer.result(2)

    trace = SemanticTrace.model_validate(tracer.to_trace())

    assert trace.algorithm == "不同路径"
    assert trace.input_data == {"m": 2, "n": 2}
    assert trace.result == 2
    assert len(trace.events) == 2
    assert trace.events[1].op.value == "set"
    assert trace.events[1].targets[0].id == "dp[1][1]"
    assert [dep.id for dep in trace.events[1].deps] == ["dp[0][1]", "dp[1][0]"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m tests.tracer_regression
```

Expected:

```text
ModuleNotFoundError: No module named 'algolab.runtime.tracer'
```

- [ ] **Step 3: 实现最小 Tracer**

创建 `algolab/runtime/tracer.py`：

```python
"""Structured trace builder used by generated tracker code."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class Tracer:
    def __init__(
        self,
        input_data: Any,
        *,
        algorithm: str = "",
        pseudocode: list[str] | None = None,
        max_events: int = 80,
        policy: str = "auto",
    ) -> None:
        self.input_data = deepcopy(input_data)
        self.algorithm = algorithm or "算法轨迹"
        self.pseudocode = list(pseudocode or [])
        self.max_events = max_events
        self.policy = policy
        self._events: list[dict[str, Any]] = []
        self._result: Any = None
        self._expected_updates: dict[str, int] = {}
        self._recorded_updates: dict[str, int] = {}

    def create(self, target: str, **kwargs: Any) -> None:
        self._add("create", [target], **kwargs)

    def set(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("set", [target], **kwargs)

    def mark(self, target: str, **kwargs: Any) -> None:
        self._add("mark", [target], **kwargs)

    def move(self, target: str, **kwargs: Any) -> None:
        self._add("move", [target], **kwargs)

    def compare(self, targets: list[str], **kwargs: Any) -> None:
        self._add("compare", targets, **kwargs)

    def push(self, target: str, **kwargs: Any) -> None:
        self._add("push", [target], **kwargs)

    def pop(self, target: str, **kwargs: Any) -> None:
        self._add("pop", [target], **kwargs)

    def explain(self, target: str | None = None, **kwargs: Any) -> None:
        self._add("explain", [target] if target else [], **kwargs)

    def expect_updates(self, name: str, count: int) -> None:
        self._expected_updates[str(name)] = int(count)

    def result(self, value: Any) -> None:
        self._result = deepcopy(value)

    def to_trace(self) -> dict[str, Any]:
        return {
            "schema_version": "semantic-trace-v1",
            "algorithm": self.algorithm,
            "input_data": deepcopy(self.input_data),
            "result": deepcopy(self._result),
            "pseudocode": list(self.pseudocode),
            "events": [self._with_step(index, event) for index, event in enumerate(self._events)],
        }

    def _add(
        self,
        op: str,
        targets: list[str],
        *,
        state: dict[str, Any] | None = None,
        value: Any = None,
        deps: list[str] | None = None,
        role: str = "",
        reason: str = "",
        code_line: int = 1,
        before: Any = None,
        after: Any = None,
    ) -> None:
        self._events.append(
            {
                "step": len(self._events),
                "op": op,
                "targets": [{"id": item} for item in targets],
                "value": deepcopy(value),
                "before": deepcopy(before),
                "after": deepcopy(after),
                "deps": [{"id": item} for item in (deps or [])],
                "role": role or "",
                "reason": reason or "",
                "state": deepcopy(state or {}),
                "code_line": int(code_line or 1),
            }
        )

    def _record_update(self, target: str) -> None:
        name = target.split("[", 1)[0]
        self._recorded_updates[name] = self._recorded_updates.get(name, 0) + 1

    def _with_step(self, index: int, event: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(event)
        item["step"] = index
        return item
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python -m tests.tracer_regression
```

Expected:

```text
tracer_regression: PASS
```

文件末尾加入：

```python
def run_all():
    test_tracer_builds_valid_semantic_trace()


if __name__ == "__main__":
    run_all()
    print("tracer_regression: PASS")
```

---

### Task 2: 加入 coverage meta 和 strict 更新检查

**Files:**

- Modify: `algolab/runtime/tracer.py`
- Modify: `tests/tracer_regression.py`

- [ ] **Step 1: 写失败测试：expected updates 不足时报错**

加入：

```python
def test_tracer_strict_mode_rejects_missing_expected_updates():
    tracer = Tracer({"m": 3, "n": 7}, algorithm="不同路径", policy="strict")
    tracer.expect_updates("dp", 12)
    tracer.create("dp", state={"dp": [[1] * 7 for _ in range(3)]})
    tracer.set("dp[1][1]", state={"dp": [[1] * 7 for _ in range(3)]})
    tracer.result(28)

    try:
        tracer.to_trace()
    except ValueError as exc:
        assert "dp expected 12 updates, recorded 1" in str(exc)
    else:
        raise AssertionError("strict tracer should reject missing expected updates")
```

- [ ] **Step 2: 写失败测试：meta 记录覆盖率**

加入：

```python
def test_tracer_attaches_trace_meta_to_last_event_state():
    tracer = Tracer({"nums": [1, 2]}, algorithm="数组", policy="full", max_events=80)
    tracer.expect_updates("nums", 2)
    tracer.set("nums[0]", value=1, state={"nums": [1, 2]})
    tracer.set("nums[1]", value=2, state={"nums": [1, 2]})
    tracer.result([1, 2])

    trace = tracer.to_trace()
    meta = trace["events"][-1]["state"]["_trace_meta"]

    assert meta["policy"] == "full"
    assert meta["max_events"] == 80
    assert meta["raw_event_count"] == 2
    assert meta["emitted_event_count"] == 2
    assert meta["expected_updates"] == {"nums": 2}
    assert meta["recorded_updates"] == {"nums": 2}
    assert meta["coverage"] == {"nums": 1.0}
```

- [ ] **Step 3: 运行测试确认失败**

Run:

```bash
python -m tests.tracer_regression
```

Expected:

```text
AssertionError
```

- [ ] **Step 4: 实现 strict 和 meta**

在 `Tracer.to_trace()` 中生成 events 前加入：

```python
self._validate_expected_updates()
events = [self._with_step(index, event) for index, event in enumerate(self._events)]
self._attach_meta(events)
```

新增方法：

```python
def _validate_expected_updates(self) -> None:
    if self.policy not in {"strict", "full", "auto"}:
        return
    for name, expected in self._expected_updates.items():
        recorded = self._recorded_updates.get(name, 0)
        if expected <= self.max_events and recorded < expected:
            raise ValueError(f"{name} expected {expected} updates, recorded {recorded}")


def _attach_meta(self, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    coverage = {}
    for name, expected in self._expected_updates.items():
        recorded = self._recorded_updates.get(name, 0)
        coverage[name] = 1.0 if expected == 0 else round(recorded / expected, 6)
    meta = {
        "policy": self.policy,
        "max_events": self.max_events,
        "raw_event_count": len(self._events),
        "emitted_event_count": len(events),
        "sampled": False,
        "expected_updates": dict(self._expected_updates),
        "recorded_updates": dict(self._recorded_updates),
        "coverage": coverage,
    }
    state = dict(events[-1].get("state") or {})
    state["_trace_meta"] = meta
    events[-1]["state"] = state
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
python -m tests.tracer_regression
```

Expected:

```text
tracer_regression: PASS
```

---

### Task 3: 加入 sampled mode

**Files:**

- Modify: `algolab/runtime/tracer.py`
- Modify: `tests/tracer_regression.py`

- [ ] **Step 1: 写失败测试：大输入进入 sampled mode**

加入：

```python
def test_tracer_auto_policy_samples_when_events_exceed_budget():
    tracer = Tracer({"nums": list(range(20))}, algorithm="长数组", max_events=5, policy="auto")
    for i in range(20):
        tracer.set(f"nums[{i}]", value=i, state={"nums": list(range(20)), "i": i})
    tracer.result(list(range(20)))

    trace = tracer.to_trace()
    meta = trace["events"][-1]["state"]["_trace_meta"]

    assert len(trace["events"]) == 5
    assert meta["sampled"] is True
    assert meta["raw_event_count"] == 20
    assert meta["emitted_event_count"] == 5
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m tests.tracer_regression
```

Expected:

```text
AssertionError: assert 20 == 5
```

- [ ] **Step 3: 实现抽样**

在 `to_trace()` 中从：

```python
events = [self._with_step(index, event) for index, event in enumerate(self._events)]
```

改为：

```python
raw_events = self._events
sampled = self.policy in {"auto", "sampled"} and len(raw_events) > self.max_events
selected = self._sample_events(raw_events, self.max_events) if sampled else raw_events
events = [self._with_step(index, event) for index, event in enumerate(selected)]
self._attach_meta(events, sampled=sampled, raw_event_count=len(raw_events))
```

修改 `_attach_meta` 签名：

```python
def _attach_meta(self, events: list[dict[str, Any]], *, sampled: bool, raw_event_count: int) -> None:
```

新增：

```python
def _sample_events(self, events: list[dict[str, Any]], max_events: int) -> list[dict[str, Any]]:
    if max_events <= 0 or len(events) <= max_events:
        return events
    if max_events == 1:
        return [events[-1]]
    selected_indices = {0, len(events) - 1}
    remaining = max_events - len(selected_indices)
    if remaining > 0:
        span = len(events) - 1
        for k in range(1, remaining + 1):
            selected_indices.add(round(k * span / (remaining + 1)))
    return [events[index] for index in sorted(selected_indices)][:max_events]
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python -m tests.tracer_regression
```

Expected:

```text
tracer_regression: PASS
```

---

### Task 4: 将 Tracer 注入 sandbox

**Files:**

- Modify: `algolab/runtime/sandbox.py`
- Modify: `tests/offline_regression.py`

- [ ] **Step 1: 写失败测试：generated tracker 可以直接使用 Tracer**

在 `tests/offline_regression.py` 加入：

```python
def test_sandbox_exposes_tracer_to_generated_tracker():
    code = """
def trace(input_data):
    tracer = Tracer(input_data, algorithm="常量")
    tracer.create("answer", state={"answer": 1}, reason="初始化答案。")
    tracer.result(1)
    return tracer.to_trace()
"""
    result = run_function(code, "trace", {"x": 1})
    assert result["algorithm"] == "常量"
    assert result["result"] == 1
    assert result["events"][0]["op"] == "create"
```

并加入 `run_all()` 列表。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python - <<'PY'
from tests.offline_regression import test_sandbox_exposes_tracer_to_generated_tracker
test_sandbox_exposes_tracer_to_generated_tracker()
PY
```

Expected:

```text
SandboxError ... NameError: name 'Tracer' is not defined
```

- [ ] **Step 3: 注入 Tracer**

在 `algolab/runtime/sandbox.py` 的 `build_namespace()` 中导入并加入：

```python
from algolab.runtime.tracer import Tracer
```

namespace 增加：

```python
"Tracer": Tracer,
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python - <<'PY'
from tests.offline_regression import test_sandbox_exposes_tracer_to_generated_tracker
test_sandbox_exposes_tracer_to_generated_tracker()
print("sandbox tracer exposure: PASS")
PY
```

Expected:

```text
sandbox tracer exposure: PASS
```

---

### Task 5: process validator 读取 Tracer coverage meta

**Files:**

- Modify: `algolab/verification/process_validator.py`
- Modify: `tests/offline_regression.py`

- [ ] **Step 1: 写失败测试：coverage 不足会被 process validator 拒绝**

加入：

```python
def test_process_validator_rejects_low_tracer_coverage_meta():
    trace = SemanticTrace.model_validate(
        {
            "schema_version": "semantic-trace-v1",
            "algorithm": "覆盖率不足",
            "input_data": {"x": 1},
            "result": 1,
            "events": [
                {
                    "step": 0,
                    "op": "set",
                    "targets": [{"id": "answer"}],
                    "state": {
                        "answer": 1,
                        "_trace_meta": {
                            "policy": "full",
                            "max_events": 80,
                            "raw_event_count": 1,
                            "emitted_event_count": 1,
                            "sampled": False,
                            "expected_updates": {"dp": 12},
                            "recorded_updates": {"dp": 6},
                            "coverage": {"dp": 0.5},
                        },
                    },
                    "after": 1,
                    "reason": "覆盖率不足。",
                    "code_line": 1,
                }
            ],
        }
    )

    errors, _warnings = validate_process(trace)
    assert any("trace coverage dp 不足" in error for error in errors), errors
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python - <<'PY'
from tests.offline_regression import test_process_validator_rejects_low_tracer_coverage_meta
test_process_validator_rejects_low_tracer_coverage_meta()
PY
```

Expected:

```text
AssertionError: []
```

- [ ] **Step 3: 实现 coverage meta 检查**

在 `_validate_core_invariants()` 中加入：

```python
errors.extend(_validate_trace_meta_coverage(trace))
```

新增函数：

```python
def _validate_trace_meta_coverage(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        meta = (event.state or {}).get("_trace_meta")
        if not isinstance(meta, dict):
            continue
        sampled = meta.get("sampled") is True
        coverage = meta.get("coverage")
        if sampled or not isinstance(coverage, dict):
            continue
        for name, value in coverage.items():
            if isinstance(value, (int, float)) and value < 1.0:
                errors.append(f"第 {event.step} 步 trace coverage {name} 不足：{value}")
    return errors
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python - <<'PY'
from tests.offline_regression import test_process_validator_rejects_low_tracer_coverage_meta
test_process_validator_rejects_low_tracer_coverage_meta()
print("trace coverage meta validation: PASS")
PY
```

Expected:

```text
trace coverage meta validation: PASS
```

---

### Task 6: 更新 prompt，要求新 tracker 使用 Tracer API

**Files:**

- Modify: `algolab/generation/prompts/tracker_system.txt`
- Modify: `algolab/generation/prompts/repair_system.txt`
- Modify: `tests/offline_regression.py`

- [ ] **Step 1: 写 prompt 断言测试**

加入：

```python
def test_tracker_prompt_requires_tracer_api():
    prompt = Path("algolab/generation/prompts/tracker_system.txt").read_text(encoding="utf-8")
    assert "Tracer" in prompt
    assert "tracer.set" in prompt
    assert "不要直接手写 events.append" in prompt


def test_repair_prompt_converts_sparse_trace_to_tracer_api():
    prompt = Path("algolab/generation/prompts/repair_system.txt").read_text(encoding="utf-8")
    assert "Tracer API" in prompt
    assert "events.append" in prompt
    assert "tracer.set" in prompt
```

加入 `run_all()`。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python - <<'PY'
from tests.offline_regression import test_tracker_prompt_requires_tracer_api, test_repair_prompt_converts_sparse_trace_to_tracer_api
test_tracker_prompt_requires_tracer_api()
test_repair_prompt_converts_sparse_trace_to_tracer_api()
PY
```

Expected:

```text
AssertionError
```

- [ ] **Step 3: 修改 tracker prompt**

在 `tracker_system.txt` 的 tracker 要求附近加入：

```text
tracker_code 必须优先使用系统提供的 Tracer API，不要直接手写 events.append。
推荐写法：
tracer = Tracer(input_data, algorithm="算法名称", pseudocode=[...])
tracer.create("dp", state={...}, reason="...")
tracer.set("dp[1][3]", value=..., deps=[...], state={...}, reason="...")
tracer.push("stack", value=..., state={...}, reason="...")
tracer.move("pointer:mid", value=..., state={...}, reason="...")
tracer.result(answer)
return tracer.to_trace()
小输入逐帧、大输入抽样、step 编号、targets/deps 格式和 coverage 由 Tracer 统一管理。
```

- [ ] **Step 4: 修改 repair prompt**

在 `repair_system.txt` 加入：

```text
如果 tracker_code 直接手写 events.append、跳过中间状态、或错误包含“缺少逐帧状态转移 / trace coverage”，必须改写为 Tracer API：使用 tracer.set / tracer.push / tracer.move / tracer.compare 记录真实算法操作，最后 return tracer.to_trace()。
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
python - <<'PY'
from tests.offline_regression import test_tracker_prompt_requires_tracer_api, test_repair_prompt_converts_sparse_trace_to_tracer_api
test_tracker_prompt_requires_tracer_api()
test_repair_prompt_converts_sparse_trace_to_tracer_api()
print("prompt tracer api checks: PASS")
PY
```

Expected:

```text
prompt tracer api checks: PASS
```

---

### Task 7: 用 Tracer API 改造一个确定性 unique_paths case

**Files:**

- Modify: `tests/benchmark_cases.py`
- Test: `tests/benchmark_regression.py`

- [ ] **Step 1: 记录当前 unique_paths benchmark 事件数**

Run:

```bash
python - <<'PY'
from tests.benchmark_cases import UNIQUE_PATHS_TRACKER
from algolab.runtime.sandbox import run_function
trace = run_function(UNIQUE_PATHS_TRACKER, "trace", {"m": 3, "n": 7})
print(len(trace["events"]))
PY
```

Expected:

```text
25
```

- [ ] **Step 2: 将 `UNIQUE_PATHS_TRACKER` 改为 Tracer API**

在 `tests/benchmark_cases.py` 中把 unique paths tracker 改成：

```python
UNIQUE_PATHS_TRACKER = """
def trace(input_data):
    m, n = input_data["m"], input_data["n"]
    tracer = Tracer(input_data, algorithm="不同路径", pseudocode=["dp[i][j] = dp[i-1][j] + dp[i][j-1]"])
    dp = [[1] * n for _ in range(m)]
    tracer.expect_updates("dp", max(0, (m - 1) * (n - 1)))
    tracer.create("dp", state={"dp": [row[:] for row in dp]}, reason="第一行和第一列只有一种路径。", code_line=1)
    for i in range(1, m):
        for j in range(1, n):
            tracer.compare(
                [f"dp[{i}][{j}]"],
                deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
                state={"dp": [row[:] for row in dp], "i": i, "j": j},
                role="candidate",
                reason="当前位置只能从上方或左侧到达。",
                code_line=3,
            )
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
            tracer.set(
                f"dp[{i}][{j}]",
                value=dp[i][j],
                deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
                state={"dp": [row[:] for row in dp], "i": i, "j": j},
                role="answer",
                reason="写入上方和左侧路径数之和。",
                code_line=3,
            )
    tracer.result(dp[m - 1][n - 1])
    return tracer.to_trace()
"""
```

- [ ] **Step 3: 运行 unique_paths benchmark materialization**

Run:

```bash
python - <<'PY'
from tests.benchmark_cases import benchmark_cases
from scripts.build_demo_dashboard import spec_for_case
from algolab.pipeline import _try_materialize
from algolab.schemas.input import ProblemInput
case = next(c for c in benchmark_cases() if c.id == "unique_paths")
sample = case.samples[0]
request = ProblemInput(problem=case.problem, input_data=sample.input_data, expected_result=sample.expected, strategy_hint=case.strategy, solution_count=1)
artifact, errors = _try_materialize(request, spec_for_case(case))
print(errors)
print(artifact.validation.release_gate.release_ready)
print(len(artifact.variants[0].trace.events))
PY
```

Expected:

```text
[]
True
25
```

---

### Task 8: 文档更新

**Files:**

- Modify: `SYSTEM_OVERVIEW.md`
- Modify: `SYSTEM_FLOW.html`

- [ ] **Step 1: 更新 `SYSTEM_OVERVIEW.md`**

加入章节：

```markdown
## Tracer API

新 tracker 应使用系统提供的 `Tracer`，不要直接手写 `events.append({...})`。

作用：

1. 防止跳帧。
2. 统一 trace schema。
3. 统一粒度策略。
4. 支持标准轨迹和学生轨迹对齐。
5. 输出 trace coverage 指标。
6. 大输入时明确进入 sampled mode。
```

- [ ] **Step 2: 更新 `SYSTEM_FLOW.html`**

在主流程的 “LLM 生成 spec” 和 “Sandbox 执行” 之间说明：

```text
tracker_code 调用 Tracer API，系统生成标准 SemanticTrace。
```

- [ ] **Step 3: HTML parse 检查**

Run:

```bash
python - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
HTMLParser().feed(Path("SYSTEM_FLOW.html").read_text(encoding="utf-8"))
print("SYSTEM_FLOW.html parse: OK")
PY
```

Expected:

```text
SYSTEM_FLOW.html parse: OK
```

---

## 4. 最终验证

- [ ] **Step 1: 运行 Tracer 回归**

```bash
python -m tests.tracer_regression
```

Expected:

```text
tracer_regression: PASS
```

- [ ] **Step 2: 运行离线回归**

```bash
python -m tests.offline_regression
```

Expected:

```text
offline_regression: PASS
```

- [ ] **Step 3: 运行 benchmark 回归**

```bash
python -m tests.benchmark_regression
```

Expected:

```text
benchmark_regression: PASS
```

- [ ] **Step 4: 运行全部质量检查**

```bash
python scripts/run_quality_checks.py
```

Expected:

```text
quality_checks: PASS
```

---

## 5. 不在第一版做的事

第一版不做：

- 不要求所有旧 benchmark 一次性迁移到 Tracer API。
- 不删除旧 tracker 兼容。
- 不实现完整 debug mode UI。
- 不做 AST 自动插桩。
- 不引入新的 SemanticTrace schema version。

这些留到后续：

1. 所有 deterministic benchmark 迁移到 Tracer API。
2. LLM benchmark 统计 Tracer 使用率。
3. Debug mode：reference trace vs student trace 第一处分歧。
4. 更细粒度的 sampled mode，例如按阶段抽样、保留关键分支、保留错误传播链。

---

## 6. 自检

本计划覆盖六个价值：

- 防止跳帧：Task 2、Task 3、Task 5、Task 7。
- 统一 trace schema：Task 1、Task 4、Task 6。
- 统一粒度策略：Task 2、Task 3。
- 支持调试模式：Task 1 的统一事件接口和 Task 2 的 coverage meta 为后续 diff 打基础。
- 支持质量指标：Task 2、Task 5、Task 8。
- 支持大输入降级：Task 3、Task 8。

实现时必须保持旧 tracker 兼容，避免一次重构影响现有 pipeline。
