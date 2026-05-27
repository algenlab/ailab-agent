# 黄金样例：二分图匹配

## 输入

```json
{"graph": {"L1": ["R1", "R2"], "L2": ["R1"], "L3": ["R2"]}, "left": ["L1", "L2", "L3"], "right": ["R1", "R2"]}
```

expected output：

```json
{"L1": "R2", "L2": "R1"}
```

## 视觉原语

- 主视图使用 `graph` layout。
- 左右两侧点保存在 state 的 `left_nodes`、`right_nodes`。
- 匹配关系使用 `match[L1]`、`match[R1]` 这类 map target。

## Trace 要点

- 每轮从一个左侧点出发寻找增广路径。
- 访问右侧点时标记 `node:R1` 并在 `visited` 中记录。
- 增广成功时同时写入左侧和右侧 `match[...]`，保持双向一致。
- deps 应绑定当前边 `edge:L1->R2` 和参与匹配的节点。

## 教学解释

增广路径会交替经过未匹配边和已匹配边。找到一条增广路径后翻转路径上的匹配关系，匹配数增加 1。
