# 黄金样例：lowbit 分解

## 输入

```json
{"n": 12}
```

expected output：

```json
[4, 8]
```

## 视觉原语

- 主视图使用 `array` 展示 `bits` 和 `lowbits`。
- 当前剩余值使用普通 symbol：`remaining`。
- 不使用 `number:` target。

## Trace 要点

- 每轮计算 `lowbit = remaining & -remaining`。
- 写入 `lowbits[i]`。
- 从 `remaining` 中删除这个最低位的 1。

## 教学解释

`lowbit` 提取二进制中最低位的 1 所代表的值。反复删除最低位的 1，可以把整数分解为若干个二进制贡献项。
