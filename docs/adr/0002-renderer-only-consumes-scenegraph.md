# ADR-0002: Renderer 只能消费 SceneGraph

## Context

如果 renderer 直接读取 LLM 生成代码、自然语言或自由 HTML，页面会变得不可控，错误过程也可能被前端掩盖。

## Decision

Renderer 只能消费 BuildArtifact 中的 SceneGraph 和 validation report。所有算法语义必须先经过 SemanticTrace、validator 和 Scene Compiler。

## Consequences

好处：

- 页面稳定统一。
- LLM 不能绕过校验发布错误 HTML。
- 可视化绑定错误可以在 SceneGraph 层检查。

代价：

- Renderer 不能为单个题目随意写专用逻辑。
- 新页面能力需要扩展 SceneGraph 表达。
- 某些复杂动画需要先抽象成通用视觉原语。

