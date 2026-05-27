# 黄金样例：Rabin-Karp 字符串匹配

## 输入

```json
{"text": "abcdef", "pattern": "cde"}
```

expected output：

```json
2
```

## 关键步骤

- 展示 `text`、`pattern`、`pattern_hash` 和 `window_hashes`。
- 计算第一个窗口哈希。
- 每次移动窗口时，用移出字符和移入字符滚动哈希。
- 比较 `window_hashes[i]` 和 `pattern_hash`。
- 哈希相等后逐字符确认，避免碰撞误判。

## 视觉重点

- 主原语：`string`
- 辅助原语：`array`
- 关键对象：`text`、`pattern`、`pattern_hash`、`window_hashes`、`window_hashes[2]`
- 关键 deps：`text[0:3]`、`text[1]`、`text[3]`、`pattern`
- 不新增 `hash:` target；哈希值用普通标量和数组状态表达。

## 教学解释

关键 teaching 字段：`what`、`why`、`formula`、`invariant`。

滚动哈希让每个等长窗口可以 O(1) 从上一个窗口更新。哈希相等只是候选匹配，最终仍以字符确认作为正确性依据。

## 验收标准

- `text`、`pattern`、`pattern_hash`、`window_hashes` 可见。
- 每个 `window_hashes[i]` 写入能按固定 base/mod 复核。
- 哈希命中步骤必须解释滚动哈希和字符确认。
