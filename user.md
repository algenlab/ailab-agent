  第一档：Prompt 增强，最快见效
  让 LLM 在 teaching enrichment 阶段强制为关键帧输出：

  - 本步学生应该注意什么
  - 当前 invariant
  - 常见错误
  - 一个预测题
  - 正确答案
  - 错误反馈

  这能快速让 demo 变得更像教学页面。缺点是质量不稳定，审稿时容易被问：这些问题是否正确？反馈是否真的对应当前状态？

  第二档：Schema + Validator 增强，适合论文
  保留现有 teaching / interaction 字段，但加硬约束：

  - 每个关键帧必须有 why
  - DP / stack / graph 等关键步骤必须有 invariant 或 formula
  - prediction question 的 answer 必须能从当前 state / result / deps 校验
  - wrong feedback 不能空
  - interaction 必须绑定当前 frame 的 targets/deps/state

  这一步才是论文里能讲的贡献：不是单纯“LLM 写解释”，而是“可验证教学交互层”。

  第三档：Renderer 交互增强，适合产品和学生实验
  前端把 interaction 变成真实学习动作：

  - 预测下一步按钮
  - 输入答案后即时反馈
  - 答错显示 common mistake
  - “为什么依赖这些对象”展开
  - 交互日志记录：在哪帧答错、重看、跳过

  这部分直接服务本科生实验。