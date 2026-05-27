# 二叉树中序遍历

## 视觉原语

- 主视图使用 `tree`，节点使用 `node:<id>`，边使用 `edge:<parent>-><child>`。
- 递归调用使用 `frame:inorder(<id>)`，通过 deps 连接到当前树节点。

## Trace 要点

- state 必须包含 `tree`、`current`、`call_stack`、`return_values`。
- 进入节点时记录递归 frame。
- 左子树返回后 mark 当前 `node:<id>`，说明中序访问时机。
- 退出 frame 时写清当前子树返回值。

## 教学解释

页面应说明中序遍历的顺序是左子树、当前节点、右子树，并让 `frame:` 与 `node:` 的依赖箭头说明递归调用与树节点的绑定。
