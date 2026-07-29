# Plan2 P0-3 最小修复设计

## 目标

修复 Creative Shell 在切换到第二个解法后仍读取首个解法 `scene/frames` 的问题；复用已有 Stage2 模型输出，不重新调用 API；将 P0-3 的核心判据从 DOM/文字完全一致改为可验证的语义状态一致，并保留旧结果作为错误审计记录。

## 约束

- 只修改 Creative Shell 内部的当前 variant → scene/frame 选择逻辑，不重构 Stage1/Stage2 外壳。
- 保留顶层 `artifact.scene`、`artifact.frames` 便捷别名，避免破坏已有生成代码。
- 使用现有 200 个最终 `raw_output` 本地重封装 HTML；原始 HTML 和 P0-3 结果不覆盖。
- Playwright 仅在 Docker 中运行。
- P0-2 Full-200 继续使用总并发 16，不重启、不停止、不单侧补跑。

## 实现

Creative Shell 的 `scene()` 先按当前 `variant().id` 查询 `ARTIFACT.scenes`，只有找不到时才使用兼容性回退；`frames()` 始终读取当前 `scene().frames`。回归测试使用两个具有不同帧数和状态哨兵的解法，证明切换后 runtime、timeline、code line 和传给 Creative Stage 的 `ctx.frame/ctx.frames/ctx.scene` 都来自当前解法。

现有 Stage2 生成报告中的最终 `raw_output` 与 artifact 将重新传给 `render_direct_visual_stage_shell_html()`，输出到新的修复目录并生成新的 manifest。P0-3 新审计以 artifact、variant、frame、canonical state、code line、timeline、interaction behavior 和 answer 为主；DOM skeleton 与文字 hash 仅作为诊断。故障注入拆分 sanitizer 拒绝、Verified fallback、generic fallback、外部请求和 shell 完整性，不再把 generic fallback 简写成“逃逸”。

## 验证

1. 回归测试必须先在旧实现上失败，再在最小修复后通过。
2. 修复后的 200 个 artifact 必须继续保持 200/200 字节与语义一致。
3. Docker 全量审计覆盖 200 cases、399 variants、12,709 states。
4. 只重新计算此前为负或口径有歧义的 P0-3 指标；已通过的 artifact pairing 和浏览器无错误事实可复用但仍核对。
5. P0-2 运行期间只做只读监控，完成后按既定协议继续 Machine、服务和配对统计。
