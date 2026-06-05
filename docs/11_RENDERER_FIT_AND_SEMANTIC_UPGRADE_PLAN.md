# Renderer Fit 与算法语义升级落地方案

## 1. 文档定位

本文档是 `10_RENDERER_VISUAL_OPTIMIZATION_DESIGN.md` 的后续落地方案，聚焦 2026-06-05 对
`llm_algolab_full_gemini_3_flash_c12_k3_r1_full1` 当前 renderer 重渲截图的人工复核结论。

本轮不要求重新调用 LLM，也不改提示词。优化目标是：

- 修复主舞台漂移、裁剪、显示不完整。
- 让截图首屏自动呈现完整、稳定、可教学的主视图。
- 把 graph/tree/trie/math/string-specialized 等算法族从“状态卡展示”提升为“算法过程展示”。
- 保持现有边界：renderer 只消费 `BuildArtifact` 和 `SceneGraph`，不伪造 trace，不绕过 validation。

主要相关文件：

- `algolab/renderer/export.py`：页面 CSS、前端 runtime、主舞台 fit、各 layout renderer。
- `algolab/renderer/layout_registry.py`：layout 到 renderer 的映射。
- `algolab/compiler/scene_compiler.py`：从 SemanticTrace 编译 SceneGraph 和对象 metadata。
- `algolab/compiler/object_resolver.py`：state 对象到 SceneObject 的基础解析。
- `scripts/audit_renderer_visual_quality.py`：截图和 DOM 层质量审查。
- `tests/browser_smoke.py`、`tests/offline_regression.py`：浏览器和离线回归入口。

## 2. 当前截图结论

复核对象：

- 原始 artifact：`output/aaai/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1`
- 当前重渲截图：`shot/renderer_optimized_llm_algolab_full_gemini_3_flash_c12_k3_r1_full1`
- 样本规模：71 个算法，每个算法 first / middle / last 三帧，共 213 张 PNG。

总体结论：

- 没有发现普遍性的严重硬重叠。
- 有明显的主视图漂移、裁剪和显示不完整风险。
- 当前主要不是“布局完全坏了”，而是“算法语义不够强”：主画布里很多核心结构偏小、偏淡，右侧解释区和浅蓝/浅绿 answer 背景有时抢主视觉，教学效果像在看状态面板，而不是看算法过程。

重点问题：

1. 图、树、Trie 类节点仍偏小，尤其 Tarjan、树 DP、Trie 首帧信息量弱。
2. 二分图匹配和二分图染色不是严格左右分区布局，语义不够强。
3. 快慢指针链表仍偏数组/线性指针表达，环形链表语义不明显。
4. GCD、扩展 GCD 偏状态卡，除法/余数链视觉关系不够强。
5. Manacher、Z Algorithm、TSP 状压已有轨道/矩阵，但中心半径、Z-box、mask 转移不够醒目。
6. 部分 answer 末帧浅蓝/浅绿背景面积偏大，右侧解释区有时仍抢主画布注意力。
7. 堆、回溯、Kruskal 边排序轨道可以进一步强化。

保留项：

- KMP、筛法、Floyd/矩阵 DP、部分网络流和普通滑窗类整体较稳定。
- 这些算法没有明显重叠，语义也比其他类别清楚，下一轮不应优先重写。

## 3. 根因判断

三张用户标注截图暴露的问题是 renderer 自适配策略的问题，不是单纯缺少拖拽。

### 3.1 `fitSceneToCanvas()` 使用了不可靠边界

当前 `algolab/renderer/export.py` 中的 `fitSceneToCanvas()` 位于约 `export.py:685`，核心逻辑是：

```javascript
const contentWidth = Math.max(1, scene.scrollWidth);
const contentHeight = Math.max(1, scene.scrollHeight);
const rawScale = Math.min(availableWidth / contentWidth, availableHeight / contentHeight) * 0.985;
scene.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
```

问题：

- `scrollWidth / scrollHeight` 代表布局盒尺寸，不等于真实可见对象边界。
- SVG 内部存在 `viewBox` 空白时，外部盒子看似完整，关键节点可能只占小角落。
- 多主面板、answer 大背景、semantic anchor、focus 目标会改变内容边界。
- 对象可能有视觉溢出，例如节点描边、标签、浮层、return bubble，`scrollWidth` 不一定覆盖真实视觉边界。

结果是 renderer 可能认为主视图已经完整 fit，但截图中实际出现漂移、截断或关键对象贴边。

### 3.2 `.scene-fit` 默认隐藏溢出

当前 CSS 位于约 `export.py:87`：

```css
.scene-fit { position:relative; width:100%; height:100%; overflow:hidden; min-width:0; min-height:300px; }
.scene-fit.scroll-fit { overflow:auto; scrollbar-gutter:stable; }
```

问题：

- 默认 `overflow:hidden` 会把估算错误后的内容直接裁掉。
- 只有进入 `scroll-fit` 时才允许滚动，但进入条件依赖同一个不可靠的 `rawScale`。
- focus 模式在可读性 fallback 时会自动滚动到目标对象，这会牺牲整体视图完整性。

### 3.3 focus 模式误用于多主面板

省份数量这类帧同时有 `isConnected` 矩阵、并查集状态、图视图。当前策略可能因为目标是
`isConnected[0][1]` 而把 focus 放到矩阵单元，导致右侧 graph 只露出一部分。

多主面板时，focus 应只是高亮局部对象，不能改变整张主视图的全局 fit。否则会产生“目标对象可见，但算法主结构不完整”的截图。

### 3.4 answer / semantic 背景参与主舞台布局

`answer` 末帧常出现大面积浅蓝或浅绿背景。它本来是结果提示，但现在会：

- 占用主画布空间。
- 影响 fit 边界计算。
- 抢走图、树、矩阵等主结构的视觉权重。

answer 应是结果 badge、结果条或 supplement 内容，不应作为大块 primary 面板参与主画布 fit。

## 4. 总体修复策略

最稳方案：

```text
自动视觉边界 fit
+ 多主面板默认 contain
+ answer 降级为非主画布
+ 可选拖拽/缩放作为交互兜底
+ 算法族 renderer 分批补强
```

原则：

1. 先修自动 fit，不先加拖动。
2. 截图和切帧时必须自动 reset 到最佳 fit。
3. 拖动只作为用户交互兜底，不能作为截图质量的前提。
4. 同一 phase 内主布局应稳定，新增辅助 state 不能把主图挤成缩略图。
5. 原始 state 是证据，不是默认主视觉。

## 5. 优先级与落地任务

### P0：修复自动 fit 和裁剪

目标：任何 first / middle / last 截图中，主结构都不能因为 fit 误判而被裁掉。

修改点：

- `algolab/renderer/export.py`

新增函数建议：

```javascript
function measureVisualBounds(scene) {
  const candidates = Array.from(scene.querySelectorAll([
    '.primitive-panel',
    'svg',
    '[data-object-id]',
    '.cell',
    '.mcell',
    '.node',
    '.edge-label'
  ].join(',')));
  const sceneRect = scene.getBoundingClientRect();
  const rects = candidates
    .map(node => node.getBoundingClientRect())
    .filter(rect => rect.width > 0 && rect.height > 0);
  if (!rects.length) {
    return { left: 0, top: 0, width: Math.max(1, scene.scrollWidth), height: Math.max(1, scene.scrollHeight) };
  }
  const left = Math.min(...rects.map(rect => rect.left)) - sceneRect.left;
  const top = Math.min(...rects.map(rect => rect.top)) - sceneRect.top;
  const right = Math.max(...rects.map(rect => rect.right)) - sceneRect.left;
  const bottom = Math.max(...rects.map(rect => rect.bottom)) - sceneRect.top;
  return {
    left,
    top,
    width: Math.max(1, right - left),
    height: Math.max(1, bottom - top)
  };
}
```

硬性约束：

- 不要把 `.semantic-anchor-band` 放进默认 visual bounds candidates；它可以用于最小可见性检查，但不能驱动整体缩放。
- 不要把大块 answer/result 面板放进默认 visual bounds candidates；answer 只允许以小 badge 或 supplement 形态参与边界。
- 如果需要统计 anchor 或 answer 可见性，单独计算 `anchor_visible`、`answer_badge_visible`，不要混入 `primary_visual_bounds`。
- `visual_bounds` 必须代表算法主结构，例如 graph、tree、matrix、array、string、linked list、math chain，而不是顶部语义提示或结果背景。

`fitSceneToCanvas()` 改为：

- 先清空 transform。
- 调用 `measureVisualBounds(scene)`。
- 用视觉边界宽高算 scale。
- 平移时抵消 `bounds.left/top`，支持负偏移。
- 给 fit 留出 16-24px 安全边距。

示意：

```javascript
const bounds = measureVisualBounds(scene);
const safePad = 18;
const rawScale = Math.min(
  (availableWidth - safePad * 2) / bounds.width,
  (availableHeight - safePad * 2) / bounds.height
) * 0.985;
const scale = scrollFit ? minReadableScale : clampNumber(rawScale, minReadableScale, maxUsefulScale);
const translateX = safePad - bounds.left * scale + Math.max(0, (availableWidth - bounds.width * scale - safePad * 2) / 2);
const translateY = safePad - bounds.top * scale + Math.max(0, (availableHeight - bounds.height * scale - safePad * 2) / 2);
```

验收：

- `Image #1` GCD 不再出现主状态卡贴边或底部被 telemetry/提示压住。
- `Image #2` 连通分量末帧 graph、answer badge、主对象都在可见区域内。
- `Image #3` 省份数量的矩阵和图不互相挤出可视区。
- `main_stage_utilization` 不能再用 `scrollWidth` 估算，应基于视觉 bounds 计算。
- P0 实施后必须重新截图，并亲自查看 GCD、连通分量、省份数量三类截图；自动指标通过但人工截图仍有漂移/裁剪时，P0 不算完成。

### P0：多主面板禁用 focus 裁切

目标：多主面板完整展示优先，focus 只做局部高亮。

修改点：

- `fitModeForFrame(f, primary)`

规则：

```javascript
if ((primary || []).length > 1) return 'contain';
```

并补充：

- `compound-scene` 下不触发 `scrollFocusedTarget()`。
- `focus` 只适用于单一 primary 容器。
- `matrix + graph`、`array + graph`、`tree + stack` 这类组合默认 contain。
- 多 primary 的 `contain` 判断必须放在 `fitModeForFrame()` 最前面，早于 `hasTarget`、matrix、array、string、graph/tree 分支。
- 多 primary 在默认截图态下不能因为 `rawScale < minReadableScale` 退回“只展示局部”的 focus/scroll 行为。
- 如果多 primary 真放不下，应优先压缩 supplement、缩小 answer badge、使用 overview/detail；不能自动滚到某个局部 target。
- 交互态可以允许用户滚动或拖动，但切帧、播放、截图前必须 reset 到完整 visual bounds。

验收：

- 省份数量中 `isConnected` 高亮时，右侧 graph 仍完整可见。
- 连通分量 answer 末帧不因 focus 到 answer 而把图移到边缘。
- `llm_provinces_0`、`llm_graph_connected_components_0`、`llm_tarjan_scc_0` 等样例不得再出现 `primary_count > 1` 且 `fit_mode=focus` 的默认截图态。
- 人工查看重新截图时，多主面板必须同时可见；不能只满足当前 target 可见。

### P0：answer / semantic 背景不参与主画布 fit

目标：answer 结果提示不再抢占主视图。

修改点：

- `renderPrimaryStage()`
- `stageRoleForContainer()`
- `answerStateProxySelectors()`
- answer 相关 CSS。

规则：

- `answer`、`ans`、`result` 默认不作为 primary 容器。
- 如果没有其他 primary，answer 才作为小型 centered badge 展示。
- 有 graph/tree/matrix/array/string 等 primary 时，answer 进入 supplement 或覆盖为小 badge。
- 语义 anchor band 不应成为视觉 bounds 的最大来源；可以参与最小可见性，但不应驱动缩放。
- `answerStateProxySelectors()` 不能用 `.primary-scene [data-stage-role="primary"]` 作为无条件兜底，否则 answer focus 会命中整个主面板。
- 只有当前帧确实没有任何 answer-like 对象、没有其他可点击对象、也没有 primary 主结构时，才允许回退到 primary 面板。
- answer 的 focus 目标应优先命中 answer badge、answer chip 或 supplement 中的 answer 行，而不是整块主舞台。

建议新增：

```javascript
function isAnswerLikeContainer(id) {
  return ['answer', 'ans', 'result'].includes(String(id || '')) ||
    String(id || '').startsWith('answer[') ||
    String(id || '').startsWith('result[');
}
```

验收：

- 浅蓝/浅绿 answer 背景面积明显缩小。
- 主图或主矩阵仍是第一视觉焦点。
- answer 仍可点击并在右侧对象详情中查看。
- `answer_primary_area_ratio` 超过 0.35 时 P0 不通过，除非该帧没有其他主结构。
- answer 末帧必须重新截图人工查看；结果可见但主图被遮挡或被挤出时，不算通过。

### P1：加主视图拖动、滚轮缩放和 reset

目标：用户可以手动查看局部，但截图默认不受用户操作污染。

修改点：

- `algolab/renderer/export.py`
- `.scene-fit` CSS。

交互：

- 鼠标拖拽 `.scene-fit` 平移。
- 滚轮缩放，以鼠标位置为中心。
- 双击 reset。
- 可选按钮：`适配视图`、`100%`。

状态约束：

- 切换 step 时 reset 到自动 fit。
- 播放时 reset 到自动 fit。
- 截图脚本开始截图前调用 reset。
- 用户 pan/zoom 状态不要写入 artifact。

实现形态：

```javascript
const VIEW_STATE = { userPan: false, scale: 1, x: 0, y: 0, auto: null };
```

自动 fit 后保存：

```javascript
VIEW_STATE.auto = { scale, x: translateX, y: translateY };
```

拖拽只改 runtime state，不改 SceneGraph。

验收：

- 用户可拖动主视图。
- 双击能恢复完整主视图。
- 切帧后不保留上一帧手动偏移。
- 截图审查仍基于自动 fit。

## 6. 算法族 renderer 分批补强

### P1：图、树、Trie 节点放大与首帧增强

问题：

- Tarjan、树 DP、Trie 首帧信息量弱。
- 节点和边偏小，首帧像“空白中几个点”。

方案：

- graph/tree/trie 的 SVG 主体占满 panel。
- 节点半径从约 22-23 提升到 26-30。
- 增加 `viewBox` 安全边距，避免节点标签贴边。
- Tarjan 节点直接显示 `dfn/low`。
- 树 DP 节点显示 `take/skip` 或局部返回值。
- Trie 首帧显示完整待插入词列表、根节点和将要插入的第一条路径，而不是只有 root。

代码落点：

- `renderGraph()`
- `renderTree()`
- `graphNodeMetricText()`
- 新增 `renderTrie()` 或在 `renderTree(..., layout='trie')` 中分支。

验收：

- Tarjan first/middle/last 节点在 1440x790 截图下可读。
- Trie first 不再只有一个根节点。
- 树 DP first 能看出这是树和 DP，不只是普通小树。

### P1：二分图左右分区布局

问题：

- `bipartite_matching` 和 `graph_bipartite_coloring` 现在仍像普通力导向图。

方案：

- 识别输入或 state 中的 `left/right`。
- 没有 `left/right` 时按 color 或图二染推断左右集合。
- 左集合固定 x=25%，右集合固定 x=75%。
- 匹配边绿色粗线，候选边蓝/橙，冲突或失败边红虚线。

代码落点：

- `renderGraph()`
- 新增 `isBipartiteFrame(f)`、`bipartitePositions(nodes, edges, state)`。

验收：

- 二分图匹配 first/middle/last 都是左右分区。
- 二分图染色同时用空间和颜色表达二部性。

### P1：GCD / 扩展 GCD 算式链

问题：

- 当前 GCD 主视图是 `a/b/说明` 状态卡。
- 扩展 GCD 也偏状态卡，缺少余数链和回代关系。

方案：

- GCD 主画布显示：

```text
24 = 4 * 6 + 0
gcd(24, 6) -> gcd(6, 0)
```

- 每轮显示 `a = q * b + r`。
- 余数 `r` 以箭头流入下一轮的 `b`。
- 终止帧突出 `b = 0`，answer 是当前 `a`。
- 扩展 GCD 增加回代链：`gcd = ax + by`。

代码落点：

- `renderMathBitPanel()`
- `renderFormulaSubstitutionPattern()`
- 可新增 `renderGcdChainPattern(f)`。

验收：

- GCD middle 截图第一眼看到公式链，而不是大状态表。
- GCD last 的 answer 是小 badge，不铺满主画布。

### P1：快慢指针环形链表 renderer

问题：

- 现在像数组三格加 `slow/fast` 文本，看不出环。

方案：

- 对 `fast_slow_cycle`、`cycle`、`linked_list` + `slow/fast` 组合启用环形链表视图。
- 节点沿圆或尾接环布局。
- slow/fast 用不同颜色令牌贴在节点上。
- fast 走两步的轨迹用虚线弧。
- 相遇点用绿色或蓝色强高亮。

代码落点：

- `renderLinkedList()`
- 新增 `renderCycleLinkedList()`。

验收：

- 快慢指针 first/middle/last 都能看出链表环。
- middle 帧能看出 slow/fast 速度差。

### P2：Manacher / Z Algorithm / TSP 状压语义增强

Manacher：

- 中心 `center` 用竖线和中心点。
- 半径 `radius` 用回文弧或区间带。
- `mirror` 用虚线映射到当前点。

Z Algorithm：

- Z-box `[l,r]` 必须是第一视觉层级。
- 当前 `i`、复制来源、扩展比较要在同一字符串轨道上。

TSP 状压：

- mask 显示十进制、二进制、已访问城市集合。
- 当前转移显示 `dp[mask][u] + dist[u][v] -> dp[mask|1<<v][v]`。
- 矩阵中来源格和目标格用箭头连接。

代码落点：

- `renderStringSpecializedPattern()`
- `renderDpDependencyWindowPattern()`
- 新增 `renderBitmaskTransitionPattern(f)`。

### P2：堆、回溯、Kruskal 轨道

堆：

- 主视图改为堆树，而不只是数组。
- push/pop 显示上浮/下沉路径。

回溯：

- 主视图显示 path、候选池、递归深度。
- 选择/撤销直接作用在候选元素上。

Kruskal：

- 边排序轨道按权重展示。
- 当前扫描边与图上边同步高亮。
- 接纳/拒绝用绿色/红色状态。
- DSU 分量变化用小组件展示。

## 7. 质量审查与自动/人工验收

### 7.1 新增 DOM 质量指标

在 `scripts/audit_renderer_visual_quality.py` 增加：

- `visual_bounds_left/top/right/bottom`
- `primary_visible_ratio`
- `primary_clip_detected`
- `multi_primary_fit_mode`
- `answer_primary_area_ratio`
- `focus_target_visible`
- `graph_node_min_radius`
- `svg_occupied_ratio`

判定规则：

- primary bounds 超出 `.scene-fit` 可视区 6px 以上，判为 clip。
- 多 primary 且 `fit_mode=focus`，判为 high risk。
- answer-like 面板面积超过主视图 35%，判为 answer stealing focus。
- graph/tree 节点最小显示直径低于 28px，判为 weak readability。
- `llm_provinces_0`、`llm_graph_connected_components_0`、`llm_tarjan_scc_0` 这类多主面板样例如果仍然 `fit_mode=focus`，P0 必须失败。
- 自动审查指标是 P0 的必要项，不是可选项。不能出现 `failure_categories=[]` 但人工截图仍有明显裁剪/漂移的情况。

### 7.2 必查样例

至少覆盖：

- `llm_gcd_euclid_0`
- `llm_gcd_euclid_expansion_0`
- `llm_graph_connected_components_0`
- `llm_provinces_0`
- `llm_bipartite_matching_0`
- `llm_graph_bipartite_coloring_0`
- `llm_fast_slow_cycle_0`
- `llm_tarjan_scc_0`
- `llm_tree_max_independent_set_0`
- `llm_trie_prefix_0`
- `llm_manacher_0`
- `llm_z_algorithm_0`
- `llm_state_compression_tsp_0`
- `llm_kruskal_mst_weight_0`

### 7.3 验证命令

所有 Python 命令使用项目约定解释器：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest tests/offline_regression.py -q
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m pytest tests/browser_smoke.py -q
```

重渲和截图审查使用现有脚本时，同样使用：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/audit_renderer_visual_quality.py \
  --artifact-dir output/aaai/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1 \
  --output-dir output/renderer_visual_audit/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1_current
```

如果网络或浏览器依赖出现代理问题，按根目录 `AGENTS.md` 先清理并设置代理环境变量。

### 7.4 重新截图与人工验收

P0 不能只看测试和 JSON 报告，必须重新截图并人工查看。

硬性流程：

1. 用当前 renderer 重新渲染并重新截图 `llm_algolab_full_gemini_3_flash_c12_k3_r1_full1`。
2. 对必查样例生成 first / middle / last 截图。
3. 生成 contact sheet 或等价总览图，至少包含 P0 风险样例。
4. 人工逐张查看以下对象：
   - `llm_gcd_euclid_0`
   - `llm_gcd_euclid_expansion_0`
   - `llm_graph_connected_components_0`
   - `llm_provinces_0`
   - `llm_tarjan_scc_0`
   - `llm_tree_max_independent_set_0`
   - `llm_trie_prefix_0`
   - `llm_bipartite_matching_0`
   - `llm_graph_bipartite_coloring_0`
5. 人工记录每个样例是否还有：
   - 主图漂移到边缘。
   - 节点、矩阵、链条显示不完整。
   - 多主面板只显示当前 target，另一主结构被裁掉。
   - answer/semantic 背景抢占主画布。
   - 自动审查 PASS 但截图视觉上仍失败。

P0 通过标准：

- 必查样例 first / middle / last 重新截图后，主结构全部可见。
- 多主面板样例中，所有 primary 主结构都可见，而不是只让当前 target 可见。
- answer 末帧仍能看到结果，但结果背景不能遮挡或挤出主结构。
- 人工查看结论必须写入本轮实现记录或 PR 说明。只给出自动报告路径不算通过。
- 如果自动审查和人工截图结论冲突，以人工截图为准，并补审查脚本规则。

## 8. 推荐实施顺序

### 第一阶段：fit 与裁剪

1. 在 `export.py` 中新增视觉 bounds 测量。
2. 用 bounds 替换 `scrollWidth/scrollHeight` fit。
3. 多 primary 默认 `contain`。
4. 禁止 compound scene 自动 `scrollFocusedTarget()`。
5. answer-like 容器默认降级为 supplement 或小 badge。
6. 更新 `audit_renderer_visual_quality.py` 的 clip 检测。
7. 同步更新旧测试中关于 `rawScale < minReadableScale`、`scrollFocusedTarget(fit, scene)`、旧 `fit_mode` 行为的硬编码断言。
8. 跑 GCD、连通分量、省份数量三类截图回归。
9. 生成 P0 风险样例 contact sheet 并人工查看。

完成标准：

- 用户标注三张图的问题消失。
- 自动审查能识别真实 clip，而不是只给 `utilization=1.00`。
- 人工查看重新截图后确认主结构完整，且人工结论写入实现记录。

### 第二阶段：交互兜底

1. 给 `.scene-fit` 加 pan/zoom runtime state。
2. 添加双击 reset 和可选 reset 按钮。
3. 切 step、播放、截图前 reset。
4. 补浏览器 smoke 测试。

完成标准：

- 用户可拖动查看细节。
- 截图不受手动拖动状态影响。

### 第三阶段：高优算法族语义增强

1. GCD / 扩展 GCD 公式链。
2. 二分图左右分区。
3. 快慢指针环形链表。
4. Tarjan / 树 DP / Trie 节点放大和首帧增强。

完成标准：

- 这些算法不再像普通状态卡或普通图。
- 首帧就能看出算法核心结构。

### 第四阶段：专项算法与轨道增强

1. Manacher 中心/半径/镜像。
2. Z Algorithm Z-box。
3. TSP mask 转移。
4. 堆上浮/下沉。
5. 回溯递归深度。
6. Kruskal 边排序轨道。

完成标准：

- 专项算法的核心概念成为第一视觉层级。
- 轨道/矩阵不只是静态状态表。

## 9. 风险与约束

- 不要让拖拽掩盖自动 fit 问题。自动截图必须能独立通过。
- 不要把 answer 从主画布完全删除；应保留结果可见性和对象点击能力。
- 不要为了某个算法硬编码 case id；优先按 layout、state 字段、visual pattern 和 metadata 判定。
- 不要在 renderer 重新计算算法答案。
- 不要扩大 SceneGraph 合同，除非现有 `meta`、`patterns`、`marks` 无法表达。
- 不要让右侧解释区承担主语义；主算法过程必须在中央画布可见。

## 10. 最小可交付定义

第一版最小可交付只做 P0：

- `fitSceneToCanvas()` 使用视觉 bounds。
- 多 primary 禁用 focus 裁切。
- answer-like 面板不再作为大块 primary。
- 审查脚本能检测裁剪。
- 旧离线测试中关于 `rawScale < minReadableScale`、`scrollFocusedTarget(fit, scene)`、旧 `fit_mode` 的硬编码断言已同步改为新策略。

第一版完成后，必须重新截图并亲自查看：

- GCD。
- 无向图连通分量。
- 省份数量。
- 二分图匹配/染色。
- Tarjan。
- Trie。

验收要求：

- 必须基于修改后的 renderer 重新渲染并重新截图，不能复用旧截图。
- 必查样例至少覆盖 first / middle / last 三帧。
- 必须生成 contact sheet 或等价总览图，人工检查主结构是否完整可见。
- 自动审查报告和人工截图判断冲突时，以人工截图为准，并补充审查脚本规则。
- 人工查看结论必须写入实现记录或 PR 说明，只给出测试通过和报告路径不算完成。

如果这些重新截图后的人工结论确认不再漂移、不再显示不完整，再进入拖拽和算法族专用 renderer。

## 11. 本轮执行记录（2026-06-05）

本轮已按本文档方案修改当前 renderer，并使用当前 renderer 重新渲染
`llm_algolab_full_gemini_3_flash_c12_k3_r1_full1`。

最终全量审查报告：

- `output/renderer_visual_audit/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1_final/renderer_visual_quality_audit.json`
- `artifact_count=71`
- `sample_count=213`
- `passed=213`
- `failed=0`
- `failure_categories={}`

最终截图目录：

- `output/renderer_visual_audit/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1_final/screenshots/`

已人工查看的最终截图类别：

- GCD / 扩展 GCD：公式链主视觉完整，未再出现状态卡裁切。
- 省份数量：matrix + graph 同屏完整，semantic anchor 不再遮挡主结构。
- 无向图连通分量：末帧 graph 与 answer badge 同时可见，answer 不抢主画布。
- 二分图匹配：L 集合固定左侧、R 集合固定右侧，匹配/候选边可区分。
- 二分图染色：图结构完整，颜色状态在右侧 state 和主图中均可读。
- Tarjan SCC：图节点、dfn/low 指标、stack 面板可见，无明显重叠。
- 树形 DP：树主结构完整，DP 当前状态可见。
- Trie：中间帧树结构和字符边可见，节点不再过小。
- 快慢指针环检测：数组下标链已渲染为环形有向链，slow/fast 令牌可见。
- Manacher：中心线、`i`、`P[i]`、`R`、`mirror` 专项关系可见。
- Z Algorithm：Z-box、当前字符和 z 数组同屏可见。
- TSP 状压：DP 矩阵完整可见，未出现主视图裁切。
- Kruskal：主图边权、当前边和 DSU 辅助状态同时可见，主图不被辅助面板挤出。
- 01 背包子集：`nums` 与 `dp` 数组换行后完整显示，未再右侧裁切。

本轮验证命令：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile \
  algolab/renderer/export.py \
  scripts/audit_renderer_visual_quality.py \
  tests/offline_regression.py \
  tests/browser_smoke.py

bash scripts/run_browser_smoke_container.sh python -m tests.browser_smoke

bash scripts/run_browser_smoke_container.sh python scripts/audit_renderer_visual_quality.py \
  --artifact-dir output/aaai/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1 \
  --output-dir output/renderer_visual_audit/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1_final \
  --wait-ms 120 \
  --capture-screenshots \
  --fail-on-violations
```

注意：仓库全量 `tests.offline_regression` 已复跑，仍失败在既有非 renderer 断言
`test_tracker_prompt_requires_tracer_api`，失败点是 `assert "tracer.set" in prompt`。本轮以 renderer
相关离线子集、browser smoke 和全量截图审查作为交付验收。

### 11.1 截图复查补修（2026-06-05）

用户复查 `Z Algorithm` 首帧后发现两类问题：

- 主视图顶部“当前对象”锚点被自动 fit 推到裁剪边界，只剩下底部可见。
- 非几何算法也出现“几何方向 / hull 关系”卡片，语义错误。

本次补修：

- 将 `semantic-anchor-band` 和 `answer-badge` 从参与缩放的 `.primary-scene` 中移出，作为 `.scene-fit`
  的固定 overlay；自动 fit 根据 overlay 实际底边预留顶部安全区。
- `renderGeometryRelationPattern()` 只在 geometry family 且存在真实 `geometry_relation`、`cross`、`popped`
  或候选几何点信号时渲染，不再用任意 `current/candidate/evidence.targets` 兜底。
- 审查脚本新增 `semantic_anchor_visible` 和 `unexpected_geometry_relation` 指标，避免自动报告漏掉这两类问题。
- `string_list` 接入字符串 renderer，修复 Rabin-Karp 末帧退化为窄状态表和索引显示 `null` 的问题。
- 图算法中 graph/tree/trie 等结构主视图优先，queue/stack/array/frame 这类辅助状态不再挤小主图。

补修后已重新渲染并重新截图：

- 截图目录：`output/renderer_visual_audit/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1_final/screenshots/`
- 审查报告：`output/renderer_visual_audit/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1_final/renderer_visual_quality_audit.json`
- `artifact_count=71`
- `sample_count=213`
- `passed=213`
- `failed=0`
- `failure_categories={}`

人工复查补修后的关键截图：

- `070_llm_z_algorithm_0_v1_first_step001of060.png`：顶部“当前对象 text”完整显示；未再出现几何/hull 关系卡。
- `070_llm_z_algorithm_0_v1_middle_step031of060.png`：Z-box、text、z 数组和当前对象锚点同屏可见。
- `051_llm_rabin_karp_0_v1_last_step024of024.png`：text/pattern 以字符串轨道显示，索引不再出现 `null`。
- `020_llm_edmonds_karp_expansion_0_v1_middle_step029of056.png`：network graph 稳定作为主视图，queue 状态不再挤小主图。
- `061_llm_tarjan_scc_0_v1_middle_step027of053.png`、`064_llm_trie_prefix_0_v1_middle_step016of031.png`、
  `063_llm_tree_max_independent_set_0_v1_middle_step026of050.png`、`054_llm_segment_tree_range_sum_0_v1_middle_step009of017.png`：
  主结构完整可见，未发现裁切或明显重叠。

新增回归覆盖：

- `test_renderer_keeps_string_anchor_visible_without_geometry_relation`
- `test_renderer_renders_string_list_indices_without_null`

补修后验证：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m py_compile \
  algolab/renderer/export.py \
  algolab/renderer/layout_registry.py \
  scripts/audit_renderer_visual_quality.py \
  tests/offline_regression.py

bash scripts/run_browser_smoke_container.sh python -m tests.browser_smoke

bash scripts/run_browser_smoke_container.sh python scripts/audit_renderer_visual_quality.py \
  --artifact-dir output/aaai/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1 \
  --output-dir output/renderer_visual_audit/llm_algolab_full_gemini_3_flash_c12_k3_r1_full1_final \
  --wait-ms 120 \
  --capture-screenshots \
  --fail-on-violations
```
