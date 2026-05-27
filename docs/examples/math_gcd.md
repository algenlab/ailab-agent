# 黄金样例：最大公约数

## 输入

```json
{"a": 48, "b": 18}
```

expected output：

```json
6
```

## 视觉原语

- 主视图使用 `array` 展示 `remainders`。
- 当前数字使用普通 symbol：`a`、`b`、`answer`。
- 不使用 `number:` target。

## Trace 要点

- 每轮写入 `remainders[i] = a % b`。
- deps 使用 `a`、`b`。
- reason 必须说明最大公约数不变量：`gcd(a,b)=gcd(b,a mod b)`。

## 教学解释

Euclid 算法每次用较小问题替换原问题，但最大公约数保持不变。余数为 0 时，当前非零数就是最大公约数。
