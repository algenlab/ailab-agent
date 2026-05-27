# 黄金样例：Edmonds-Karp 最大流

## 输入

```json
{"graph": {"S": ["A", "B"], "A": ["T"], "B": ["T"], "T": []}, "capacity": {"S->A": 2, "S->B": 1, "A->T": 2, "B->T": 1}, "source": "S", "sink": "T"}
```

expected output：

```json
3
```

## 视觉原语

- 主视图使用 `graph` layout 和 `queue`。
- 容量和流量分别使用 `cap[S->A]`、`flow[S->A]` map target。
- 不使用未实现的 flow 冒号式 target。

## Trace 要点

- BFS 在残量网络中寻找从 source 到 sink 的增广路径。
- 每条边的残量由 `capacity - flow` 得出，state 中保留 `capacity`、`flow`、`parent` 和 `bottleneck`。
- 增广时沿路径写入 `flow[...]`，并用 `cap[...]` 作为 deps。
- 终止帧解释残量网络中已无可达汇点。

## 教学解释

Edmonds-Karp 每次选择 BFS 找到的最短增广路径。路径上的最小残量是本轮瓶颈，所有路径边的 `flow` 同步增加该瓶颈值，直到不存在新的增广路径。
