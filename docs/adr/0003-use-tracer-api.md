# ADR-0003: 新 tracker 优先使用 Tracer API

## Context

LLM 手写 `events.append({...})` 容易漏字段、跳过关键更新、使用旧 target 格式，也难以统计 coverage 和 sampled mode。

## Decision

所有新 tracker 优先使用系统注入的 `Tracer` API。Tracer 统一生成 step、targets、deps、state、coverage meta 和抽样信息。

## Consequences

好处：

- trace schema 更稳定。
- 小规模样例更容易保证完整逐帧记录。
- `_trace_meta` 能记录 coverage 和 sampled 状态。
- repair prompt 更容易定位问题。

代价：

- 生成 prompt 更复杂。
- 已有手写 tracker 需要逐步迁移。
- Tracer 自身仍需更多可信执行侧标记。

