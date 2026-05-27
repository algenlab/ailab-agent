# 树形 DP 最大独立集

## 视觉原语

- 主视图使用 `tree`。
- 递归调用使用 `frame:tree_dp(<id>)`。
- DP 状态用 `dp_take` 和 `dp_skip` 两张 map 表示。

## Trace 要点

- state 必须包含 `current`、`call_stack`、`dp_take`、`dp_skip`、`return_values`。
- `dp_take[u]` 表示选择当前节点时的子树最优值。
- `dp_skip[u]` 表示不选择当前节点时的子树最优值。
- 子树聚合必须通过 deps 绑定子 frame 和当前 `node:<id>`。

## 教学解释

页面应解释两种状态的互斥关系：选当前节点时子节点不能选；不选当前节点时每个子节点取选或不选的较大值。
