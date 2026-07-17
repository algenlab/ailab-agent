# AlgoTutorGen 成果展示站设计规格

## 目标

在仓库内新增一个可独立运行的静态成果展示站，把 AlgoTutorGen 的方法链、Full-200 方法对比、表示保持与非干扰证据、真实浏览器产物和论文入口组织成一条清晰、可核查、可交互的叙事。页面面向算法教育、网页生成与智能体系统方向的研究者和工程师，优先展示真实证据，不引入论文与 `docs/EXPERIMENT_RESULTS.md` 之外的新主张。

## 已冻结的视觉概念

本轮先通过内置 Image Gen 生成了五张协调一致的区段概念图，分别覆盖首屏、方法对比、契约架构、真实产物画廊和论文收束。用户要求代理自主决定并直接完成，因此这些概念按已批准设计处理。

统一视觉方向为 **Contract Observatory / 契约观测站**：

- 背景是接近 `#07101f` 的午夜蓝黑，正文使用偏冷白色。
- 电光青表示通过验证的算法状态链，暖橙表示不完整方法、失败和审计标记，紫色只表示只读教学分支。
- 标题使用大尺度现代无衬线，指标、路径和机器证据使用等宽字体。
- 主要容器采用开放式轨道、横向证据带和媒体舞台，避免默认卡片网格、霓虹网格、漂浮光球与过度发光。
- 动效围绕“状态沿契约链流动”展开：轨道上的移动点、图表宽度变化、画廊切换和滚动进入；所有动效遵守 `prefers-reduced-motion`。

## 信息架构

### 1. 首屏：从可执行语义到可验证导师

- 安静的固定导航：`AlgoTutorGen`、`方法`、`结果`、`产物`、`论文`，以及主操作“浏览产物”。
- 主标题：`从可执行语义到可验证的交互式算法导师`。
- 英文说明：`Contract-guided synthesis from executable specs to trustworthy browser artifacts.`
- 两个操作：滚动到实验结果、滚动到真实产物。
- 右侧把 `Spec → SemanticTrace → SceneGraph → Fixed Runtime` 做成可感知流动的契约链，钻石节点代表 gate。
- `198 / 200 Machine OK` 作为契约链终点，不做成孤立统计卡。
- 底部证据带显示 `200 tasks`、`23 algorithm families`、`646 inputs`。

### 2. 方法对比：统一黑盒浏览器合同

默认展示 `Machine OK`，并允许切换到全部十个结果维度：

- Machine OK
- Load
- Answer
- Interaction
- Correct FB
- Wrong FB
- Hint
- Show
- Log
- Mutation-free

每次选择指标后，五种方法以同一条 0–100% 横向轨道比较，行尾同时给出 `通过数/200` 与百分比。方法和顺序固定为：

1. AlgoTutorGen
2. Direct-BrowserRepair（1-call first-call control）
3. Direct HTML
4. WebGen-Agent
5. Direct + HTMLCure（strict）

主视图下方解释 Machine OK 是九项行为检查的合取，并展示 `+50.0 pp vs Direct HTML`、`101 only AlgoTutorGen passed`、`1 only Direct passed` 和 exact McNemar `p = 4.06e-29`。不得把不同预算的方法解释成通用 agent 排名。

### 3. 方法链与证据：契约逐层存活

- 开放式横向链路：`Problem + Input → LLM executable spec → Sandbox / SemanticTrace → Validation → SceneGraph → Fixed Web Runtime → Interactive HTML`。
- 每个 gate 可聚焦或点击，显示该边界检查的简短说明。
- 紫色教学分支从只读事实进入 overlay sanitizer，再在 release 前合流；视觉上明确教学状态不能回写 canonical algorithmic state。
- 暖橙修复线从失败信号回到 spec 层，不表现为整页 HTML 盲重写。
- 下方三个大证据数字：
  - `55,108 / 55,108` 跨表示帧一致；
  - `2,198 / 2,198` 定义的语义违规被拒绝；
  - `1,561,298 actions` 中观察到 `0` 个教学状态污染反例。
- 附加上下文只使用权威结果：294 artifacts、240 pages、24,000 randomized sequences。

### 4. 真实产物画廊

- 主舞台使用仓库真实截图，不使用 Image Gen 伪造算法界面。
- 画廊条目固定为二分查找、Dijkstra 最短路、不同路径、Trie 前缀匹配。
- 选择条目后，主图、标题、算法族、帧数说明和“打开真实产物”链接同步更新。
- 真实 HTML 在新标签页打开；页面明确提示其为 self-contained browser artifact。
- 画廊用单一大媒体舞台加横向 filmstrip，不使用等宽卡片瀑布流。

### 5. 论文与边界

- 展示论文完整标题：`AlgoTutorGen: Contract-Guided Compositional Synthesis of Verifiable Interactive Algorithm Tutors`。
- 链接到 `docs/EXPERIMENT_RESULTS.md`、`latex/main.pdf`、`latex/supplement.pdf` 和关键架构图。
- 证据 ledger 列出 Full-200、cross-model、held-out 40、representation audit、noninterference stress test。
- 透明列出边界：更多模型调用、长轨迹 HTML/内存膨胀、不声称真人学习效果。
- 页脚重复主要导航与 `Built from executable evidence.`。

## 数据锁定

方法指标全部来自 `docs/EXPERIMENT_RESULTS.md`：

| 方法 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AlgoTutorGen | 200 | 200 | 200 | 199 | 198 | 200 | 200 | 200 | 200 | 198 |
| Direct HTML | 188 | 200 | 149 | 120 | 125 | 132 | 133 | 135 | 149 | 98 |
| WebGen-Agent | 194 | 169 | 154 | 74 | 89 | 136 | 148 | 109 | 154 | 45 |
| Direct + HTMLCure（strict） | 75 | 75 | 62 | 52 | 51 | 53 | 53 | 59 | 62 | 40 |
| Direct-BrowserRepair（1-call first-call control） | 186 | 200 | 155 | 128 | 133 | 137 | 138 | 143 | 155 | 106 |

所有页面显示值由同一份 JavaScript 常量生成，避免图表与文案各自维护。

## 设计系统

### 色彩

- `--ink-950: #07101f`：页面底色。
- `--ink-900: #0b1728`：媒体与深层表面。
- `--paper: #f2f7fb`：主要文字。
- `--muted: #91a1b6`：说明文字。
- `--cyan: #34e8d3`：验证成功与主动状态。
- `--cyan-soft: #7eeadf`：辅助流线。
- `--orange: #ff9a62`：审计、失败和对照方法。
- `--violet: #a78bfa`：教学只读分支。
- `--rule: rgba(160, 190, 220, .18)`：分割线。

### 排版

- 中文与正文：`Inter, "Noto Sans SC", "PingFang SC", system-ui, sans-serif`。
- 代码、数字与证据路径：`"IBM Plex Mono", "SFMono-Regular", Consolas, monospace`。
- 首屏标题使用 `clamp(3.2rem, 7.3vw, 7rem)`，正文最大行宽约 38 字符。
- 所有按钮、标签、图表数值显式定义字号、字重与行高，不依赖浏览器默认值。

### 容器与间距

- 页面最大宽度 1440px，桌面水平 gutter 为 32–64px。
- 区段上下间距使用 `clamp(96px, 13vw, 196px)`。
- 圆角只用于浏览器媒体框和交互控件；叙事区段本身保持开放。
- 边框优先使用单像素技术线，阴影只服务于真实截图与聚焦层级。

## 交互与状态

- 导航滚动定位并根据可见区段更新活动状态。
- Hero 契约链在非 reduced-motion 模式下运行连续 trace pulse。
- 方法对比的指标按钮支持鼠标、键盘和移动端横向滚动；切换时条形、数值和解释同步变化。
- Gate 支持 hover、focus 和 click 锁定说明。
- 画廊支持点击条目、左右键和触摸滑动式布局；选择状态具有可见的文字与下划线，不只靠颜色。
- 数字进入视口后从较小值过渡到最终值；reduced-motion 下直接显示最终值。
- 所有外链带可读的 `aria-label`，焦点环清晰可见。

## 响应式策略

- `>= 1100px`：首屏双栏、横向架构链、画廊主图与证据列并排。
- `720–1099px`：首屏改为上下结构，架构链允许横向滚动，画廊证据移到主图下方。
- `< 720px`：导航折叠为紧凑菜单；主标题保持 3 行以内；方法名与值分两列；指标选择横向滚动；证据数字纵向排列；真实截图使用稳定 16:10 视窗并允许内部裁切。
- 320px 宽度不得出现页面级横向溢出。

## 技术方案

- 新增 `showcase/`，使用语义化 HTML、独立 CSS 和原生 JavaScript，不引入构建依赖或外部 CDN。
- 使用复制到 `showcase/assets/` 的真实截图与论文图，保证展示站可单独发布。
- 真实 HTML、PDF 和结果文档链接保留指向仓库权威来源。
- JavaScript 只负责交互增强；关闭 JavaScript 时仍能阅读全部核心结果和打开产物。

## 验收标准

1. 方法数据与 `docs/EXPERIMENT_RESULTS.md` 完全一致。
2. 四个真实产物均可从展示站打开，图片无 404。
3. 指标切换、gate 选择、画廊切换、移动导航和键盘焦点均可用。
4. 桌面 1440×1000 和移动 390×844 均无裁切、重叠和页面级横向滚动。
5. 浏览器控制台无错误；`prefers-reduced-motion` 有明确降级。
6. 通过静态完整性测试、链接/资产检查、`git diff --check` 和浏览器视觉检查。

## 规格自检

- 所有章节内容完整，没有占位内容或尚未选择的设计分支。
- 五个区段、数据源、交互、响应式和验收标准互相一致。
- 范围只新增展示站及其设计/实施文档，不修改 AlgoTutorGen 生成与验证主链。
- 所有定量主张均可回溯到现有结果文档或论文证据账本。
