# 黄金样例：Tarjan 强连通分量

## 输入

```json
{"graph": {"A": ["B"], "B": ["C", "D"], "C": ["A"], "D": ["E"], "E": ["D"]}}
```

expected output：

```json
[["E", "D"], ["C", "B", "A"]]
```

## 视觉原语

- 主视图使用 `graph` layout，节点和边分别用 `node:A`、`edge:A->B`。
- `dfn[A]`、`low[A]` 使用 map target 表达，不新增 target 前缀。
- `stack` 展示 Tarjan 当前搜索栈，`on_stack` 作为状态证据。

## Trace 要点

- 首次访问节点时写入 `dfn[u]` 和 `low[u]`。
- DFS 树边返回后用 `low[v]` 更新 `low[u]`。
- 遇到栈内回边时用 `dfn[v]` 更新 `low[u]`。
- 当 `low[u] == dfn[u]` 时，从 `stack` 弹出一个 SCC，并在 state 的 `component` 中展示。

## 教学解释

Tarjan 的关键不变量是：`low[u]` 表示从 `u` 出发沿 DFS 树边和至多一条返祖边能到达的最小 `dfn`。只有当 `low[u] == dfn[u]` 时，`u` 才是当前强连通分量的根。
