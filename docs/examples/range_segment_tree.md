# 黄金样例：线段树区间和

## 输入

```json
{"nums": [2, 1, 4, 5], "query": [1, 3], "update": [2, 6]}
```

expected output：

```json
{"before": 10, "after": 12}
```

## 视觉原语

- 主视图使用 `segment_tree`，由 tree layout 渲染。
- 每个线段树节点用 `node:seg_<idx>_<l>_<r>` 引用。
- 节点 label/meta 必须写清覆盖区间，例如 `{"l": 1, "r": 3, "sum": 10}`。
- 原数组和输入参数仍用 `nums[i]`、`query[0]`、`query[1]`、`update[0]`、`update[1]`。

## Trace 要点

- 不使用 `range:` target。
- 查询区间完全覆盖某个节点时，标记对应 `node:seg_...`。
- 部分重叠时，用 deps 连接 `query[0]`、`query[1]` 和被访问节点。
- 单点更新必须展示从叶子到根的更新路径，每个回溯节点重新写入 `meta.sum`。

## 教学解释

查询区间由若干互不相交的线段树覆盖节点组成；更新路径只影响包含更新位置的祖先节点。页面应同时解释“查询区间覆盖”和“更新路径回溯”。
