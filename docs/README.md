# AlgoLab 文档入口

本文档目录用于同时服务两类读者：

- 人：理解 AlgoLab 是什么、做到哪、下一步往哪走。
- AI：按固定边界写代码，不自由发挥。

## 推荐阅读顺序

每轮开发前先读：

1. [00_PRODUCT_NORTH_STAR.md](00_PRODUCT_NORTH_STAR.md)
2. [01_FINAL_PAGE_SPEC.md](01_FINAL_PAGE_SPEC.md)
3. [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md)
4. [03_AI_CODING_GUIDE.md](03_AI_CODING_GUIDE.md)
5. [07_ROADMAP_AND_TASKS.md](07_ROADMAP_AND_TASKS.md)

涉及 trace、target、SceneGraph 或 renderer 时继续读：

6. [04_TRACE_AND_SCHEMA_CONTRACT.md](04_TRACE_AND_SCHEMA_CONTRACT.md)
7. [05_VISUAL_PRIMITIVES_AND_PATTERNS.md](05_VISUAL_PRIMITIVES_AND_PATTERNS.md)

涉及论文实验、benchmark 或评估时读：

8. [06_EVALUATION_AND_BENCHMARK.md](06_EVALUATION_AND_BENCHMARK.md)
9. [08_AAAI_EXPERIMENT_PLAN.md](08_AAAI_EXPERIMENT_PLAN.md)

## 文档分工

- `00_PRODUCT_NORTH_STAR.md`：产品目标和非目标。
- `01_FINAL_PAGE_SPEC.md`：最终页面模块和交互规格。
- `02_SYSTEM_ARCHITECTURE.md`：系统架构、数据流和模块边界。
- `03_AI_CODING_GUIDE.md`：AI 写代码时必须遵守的硬规则。
- `04_TRACE_AND_SCHEMA_CONTRACT.md`：SemanticTrace、event、target、state 合同。
- `05_VISUAL_PRIMITIVES_AND_PATTERNS.md`：通用视觉原语和页面模式。
- `06_EVALUATION_AND_BENCHMARK.md`：评估指标、baseline、消融和失败分类。
- `07_ROADMAP_AND_TASKS.md`：最终产品设计方案和分阶段可执行任务。
- `08_AAAI_EXPERIMENT_PLAN.md`：P17 收口后的 AAAI 实验冻结、真实浏览器截图、LLM benchmark、baseline / ablation 和论文产物执行计划。

## 子目录

- `adr/`：关键架构决策记录。
- `examples/`：黄金样例页面期望。

## 核心边界

- LLM 不直接生成 HTML/CSS/JS。
- Renderer 只消费 SceneGraph 和 BuildArtifact。
- 新 tracker 优先使用 `TraceSession` DSL；`Tracer` 仅作为历史 benchmark / 旧产物兼容 API。
- 新算法优先复用固定 SemanticOp 和视觉原语。
- 错误产物不能通过放宽校验发布。
