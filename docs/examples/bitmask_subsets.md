# 黄金样例：位掩码枚举子集

## 输入

```json
{"nums": [1, 2, 3]}
```

expected output：

```json
[[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]]
```

## 视觉原语

- 主视图使用 `array` 展示 `nums` 和 `bits`。
- 当前掩码使用普通 symbol：`mask`。
- 当前子集放入 `subset`。
- 不使用 `number:` target。

## Trace 要点

- `bits[i] = (mask >> i) & 1`。
- `bits[i]` 为 1 时选择 `nums[i]`。
- 每个 mask 生成一个子集并追加到 `answer`。

## 教学解释

位掩码用一个二进制数同时表示多个选择。第 `i` 位为 1 表示选择第 `i` 个元素，为 0 表示不选择。
