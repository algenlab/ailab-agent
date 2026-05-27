# 黄金样例：割点和桥

## 输入

```json
{"graph": {"A": ["B"], "B": ["A", "C", "D"], "C": ["B", "D"], "D": ["B", "C", "E"], "E": ["D"]}}
```

expected output：

```json
{"articulation": ["B", "D"], "bridges": [["D", "E"], ["A", "B"]]}
```

## 视觉原语

- 主视图使用 `graph` layout。
- DFS 访问次序和 lowlink 使用 `dfn[A]`、`low[A]`。
- DFS 树父节点保存在 state 的 `parent`，桥和割点保存在 `bridges`、`articulation`。

## Trace 要点

- 每个节点首次访问时写入 `dfn[u]`、`low[u]`。
- 对 DFS 树边 `edge:u->v`，返回后检查 `low[v] > dfn[u]`，满足则标记桥。
- 对非根节点，若存在子节点满足 `low[v] >= dfn[u]`，则标记割点。
- 不使用 range/flow 的冒号式未实现 target。

## 教学解释

桥表示删除这条边会增加连通分量数量；割点表示删除这个点会增加连通分量数量。`low[child]` 能否回到祖先，是判断二者的核心证据。
