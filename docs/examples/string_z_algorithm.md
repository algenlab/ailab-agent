# 黄金样例：Z Algorithm

## 输入

```json
{"text": "aabcaabx"}
```

expected output：

```json
[0, 1, 0, 0, 3, 1, 0, 0]
```

## 关键步骤

- 展示 `text` 和 `z` 数组。
- 维护当前 Z-box `[l, r]`。
- 当 `i` 落在 Z-box 内时复用镜像位置的值。
- 继续比较 `text[z[i]]` 和 `text[i+z[i]]` 向右扩展。
- 写入最终 `z[i]` 并更新 Z-box。

## 视觉重点

- 主原语：`string`
- 辅助原语：`array`
- 关键对象：`text`、`z`、`z[4]`、`text[0:3]`、`text[4:7]`
- 关键 deps：`z[i-l]`、`text[0:z[i]]`、`text[i:i+z[i]]`
- 不新增区间前缀，Z-box 用 state 中的 `l`、`r` 表达。

## 教学解释

关键 teaching 字段：`what`、`why`、`formula`、`invariant`。

`z[i]` 表示从 `i` 开始的后缀与整串前缀的最长公共前缀长度。Z-box 缓存当前最右匹配区间，盒内位置先复用镜像值，再按需扩展。

## 验收标准

- `text`、`z` 和 Z-box 边界可见。
- `z[i]` 写入能被 process validator 复核。
- 扩展步骤必须解释前缀字符和当前位置字符的比较。
