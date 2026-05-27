# 黄金样例：二分查找

## 输入

```json
{"nums": [-1, 0, 3, 5, 9, 12], "target": 9}
```

expected output：

```json
4
```

## 关键步骤

- 初始化闭区间 `[left, right]`。
- 计算 `mid`。
- 比较 `nums[mid]` 和 `target`。
- 根据比较结果收缩区间。
- 命中时返回下标，否则区间为空返回 -1。

## 视觉重点

- 主原语：`array`
- 辅助原语：无
- 关键对象：`nums`、`nums[2]`、`nums[4]`、`pointer:left`、`pointer:right`、`pointer:mid`
- 关键 deps：`pointer:left`、`pointer:right`、`nums[2]`、`pointer:mid`
- `left`、`right`、`mid` 指针。
- 当前搜索区间。
- 当前比较值。
- 下一步丢弃的区间。

## 教学解释

关键 teaching 字段：`what`、`why`、`formula`、`invariant`。

数组有序，所以每次比较中点后，可以排除一半不可能包含目标值的区间。

## 验收标准

- 每次 compare 后必须有明确的区间变化或返回结果。
- 未命中样例必须展示区间为空。
- 页面不能在前端重新执行二分。
