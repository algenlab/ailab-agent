# 全排列回溯搜索树

## 视觉原语

- 搜索树使用 `recursion_tree`。
- 每个分支节点使用 `node:<id>`。
- 递归调用使用 `frame:perm(<id>)`。

## Trace 要点

- state 必须包含 `path`、`call_stack`、`return_values`、`recursion_tree`。
- 进入 frame 时添加一个搜索树节点。
- 到达叶子时 mark 当前节点并记录一个排列。
- 返回父节点时说明撤销选择，继续尝试其他分支。

## 教学解释

页面应突出“选择、递归、记录答案、撤销选择”的回溯节奏，并用 frame 与 tree 节点联动展示递归栈和搜索树分支。
