# 黄金样例：KMP 字符串匹配

## 输入

```json
{"text": "ababc", "pattern": "abc"}
```

expected output：

```json
2
```

## 关键步骤

- 展示 `text`、`pattern` 和 `pi` 前缀表。
- 构建 `pi[i]`，记录每次前缀长度写入。
- 匹配阶段比较 `text[i]` 和 `pattern[j]`。
- 失配回退时用 `pi[j-1]` 移动 `pointer:j`。
- 完整匹配后标记 `text` 中的匹配切片。

## 视觉重点

- 主原语：`string`
- 辅助原语：`array`
- 关键对象：`text`、`pattern`、`pi`、`text[2]`、`pattern[0]`、`pi[2]`
- 关键 deps：`pattern[2]`、`pi[1]`、`text[2:5]`
- 不新增 target 前缀，失配回退用 `pointer:j` 和 `pi[i]` 表达。

## 教学解释

关键 teaching 字段：`what`、`why`、`formula`、`invariant`。

`pi[i]` 表示 `pattern[:i+1]` 的最长相等真前后缀长度。失配时，已经匹配的前缀信息允许 `j` 回退到 `pi[j-1]`，无需移动 `text` 的扫描位置。

## 验收标准

- `text`、`pattern`、`pi` 在页面中可见。
- `pi[i]` 写入能被 process validator 复核。
- 失配回退必须说明来自 `pi[j-1]`。
