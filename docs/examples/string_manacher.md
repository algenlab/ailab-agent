# 黄金样例：Manacher 回文半径

## 输入

```json
{"text": "ababa"}
```

expected output：

```json
5
```

## 关键步骤

- 将原字符串转换为带分隔符的 `text`，统一奇偶回文。
- 展示 `radius` 数组、当前 `center` 和最右边界 `right`。
- 当当前位置在最右回文覆盖内时，复用 mirror 半径。
- 向两侧比较字符，执行半径扩展。
- 写入 `radius[i]`，更新最右边界并标记最大半径。

## 视觉重点

- 主原语：`string`
- 辅助原语：`array`
- 关键对象：`text`、`radius`、`radius[5]`、`text[0]`、`text[10]`
- 关键 deps：`radius[mirror]`、`text[left]`、`text[right]`
- 不新增回文专用 target；半径扩展用 `radius[i]`、`center`、`right` 和字符 deps 表达。

## 教学解释

关键 teaching 字段：`what`、`why`、`formula`、`invariant`。

Manacher 维护当前已知最右回文区间。区间内的新中心可以先借用 mirror 位置的半径，再继续向两侧扩展，最大 `radius` 对应最长回文子串长度。

## 验收标准

- `text`、`radius`、`center`、`right` 可见。
- `radius[i]` 写入能被 process validator 复核。
- 半径扩展过程必须解释两侧字符比较。
