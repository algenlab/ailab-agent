# 黄金样例：埃氏筛

## 输入

```json
{"n": 20}
```

expected output：

```json
[2, 3, 5, 7, 11, 13, 17, 19]
```

## 视觉原语

- 主视图使用 `array` 展示 `is_prime`。
- 当前质数候选使用普通 symbol：`current`。
- 已标记倍数放入 `multiples`。
- 不使用 `number:` target。

## Trace 要点

- 从质数 `p` 的 `p*p` 开始标记倍数。
- 每次写入 `is_prime[m] = false`。
- deps 绑定 `is_prime[p]`，说明倍数来自当前质数。

## 教学解释

筛法不变量：如果一个数已被更小质数标记，它不是质数；未被标记且到达当前候选时，它就是质数。
