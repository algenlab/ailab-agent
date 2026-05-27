# 黄金样例：快速幂取模

## 输入

```json
{"base": 3, "exponent": 5, "mod": 13}
```

expected output：

```json
9
```

## 视觉原语

- 主视图使用 `array` 展示指数 `bits` 和平方表 `powers`。
- 当前值使用普通 symbol：`base`、`exponent`、`mod`、`answer`。
- 不使用 `number:` target。

## Trace 要点

- `bits[i]` 表示指数的第 `i` 个二进制位。
- `powers[i]` 表示 `base^(2^i) mod mod`。
- 当前位为 1 时，`answer` 依赖 `powers[i]` 和 `bits[i]`。

## 教学解释

快速幂把指数拆成二进制，平方表负责快速得到每个二进制位的贡献。指数位为 1 的项乘入答案。
