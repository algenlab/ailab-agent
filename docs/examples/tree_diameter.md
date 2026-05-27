# 二叉树直径

## 视觉原语

- 主视图使用 `tree`。
- 递归调用使用 `frame:diameter(<id>)`。
- 每个节点的子树高度放入 `height`，局部直径放入 `diameter`。

## Trace 要点

- state 必须包含 `current`、`call_stack`、`height`、`diameter`、`return_values`。
- 每个节点在子 frame 返回后做子树高度聚合。
- `diameter[u]` 应等于子树已有直径和经过当前节点的两条最高子树路径中的最大值。

## 教学解释

页面应展示当前节点如何从子节点返回的高度中取最大的两个，更新经过当前节点的路径长度，并把当前子树高度返回给父 frame。
