# 二叉树最近公共祖先

## 视觉原语

- 主视图使用 `tree`。
- 当前递归节点使用 `node:<id>` 标记。
- 每个递归调用使用 `frame:lca(<id>)`，并依赖对应树节点。

## Trace 要点

- state 必须包含 `current`、`call_stack`、`return_values`、`lca`。
- 子树 frame 返回命中节点或 `None`。
- 当左右子树分别命中目标时，当前节点被写入 `return_values` 并标记为最近公共祖先。

## 教学解释

重点解释后序 DFS：目标节点向上返回自己，父节点聚合左右返回值；第一个左右都命中的节点就是最近公共祖先。
