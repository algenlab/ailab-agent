# 黄金样例：树状数组前缀和

## 输入

```json
{"nums": [1, 2, 3, 4, 5], "query": [1, 3], "update": [2, 4]}
```

expected output：

```json
{"before": 9, "after": 13}
```

## 视觉原语

- 主视图使用 `array`，同时展示 `nums` 和 `bit`。
- 树状数组单元使用 `bit[i]` target。
- 查询参数使用 `query[0]`、`query[1]`。
- 更新参数使用 `update[0]`、`update[1]`。

## Trace 要点

- 不使用 `range:` target。
- 前缀和查询沿 `i -= lowbit(i)` 访问 `bit[i]`。
- 区间和由右端前缀减去左端前一位前缀。
- 单点更新沿 `i += lowbit(i)` 更新路径同步每个 `bit[i]`。

## 教学解释

`lowbit(i)` 决定 `bit[i]` 覆盖的前缀块长度。页面应展示前缀查询路径和更新路径，说明为什么只访问这些 `bit[i]`。
