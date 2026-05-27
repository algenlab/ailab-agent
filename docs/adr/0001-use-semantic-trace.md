# ADR-0001: 使用 SemanticTrace 作为核心中间表示

## Context

LLM 直接生成事件列表或页面时，容易出现跳帧、字段格式错误、状态不可校验和视觉绑定不稳定的问题。

## Decision

AlgoLab 使用 `semantic-trace-v1` 作为算法执行过程的核心中间表示。LLM 生成 `solve(input_data)`、`trace(input_data)` 和 `verify(input_data)`，系统执行后只接受符合 schema 的 SemanticTrace。

## Consequences

好处：

- 算法过程可执行、可校验、可复现。
- validator 可以检查 schema、过程不变量和 target 引用。
- renderer 不需要理解 LLM 代码。

代价：

- tracker prompt 更严格。
- 新视觉形态需要补 compiler 和 renderer 支持。
- 旧格式 trace 不能直接复用。

