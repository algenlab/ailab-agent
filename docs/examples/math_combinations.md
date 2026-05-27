# 黄金样例：组合数

## 输入

```json
{"n": 5, "k": 2}
```

expected output：

```json
10
```

## 视觉原语

- 主视图使用 `matrix` 展示 `table`。
- `table[i][j]` 表示组合数 `C(i,j)`。
- 参数使用普通 symbol：`n`、`k`、`answer`。
- 不使用 `number:` target。

## Trace 要点

- 边界：`table[i][0] = 1`，`table[i][i] = 1`。
- 转移：`table[i][j] = table[i-1][j-1] + table[i-1][j]`。
- deps 必须绑定左上和正上两个格子。

## 教学解释

帕斯卡恒等式把是否选择第 `i` 个元素分成两种情况：选它来自 `C(i-1,j-1)`，不选它来自 `C(i-1,j)`。
