# 黄金样例：每日温度

## 输入

```json
{"temperatures": [73, 74, 75, 71, 69, 72, 76, 73]}
```

expected output：

```json
[1, 1, 4, 2, 1, 1, 0, 0]
```

## 关键步骤

- 从左到右扫描温度。
- 栈中保存还没找到更高温度的下标。
- 当前温度高于栈顶温度时弹栈并写答案。
- 当前下标入栈。
- 扫描结束后栈中剩余下标答案为 0。

## 视觉重点

- 主原语：`stack`
- 辅助原语：`array`
- 关键对象：`temperatures`、`temperatures[0]`、`temperatures[1]`、`stack`、`answer`、`answer[0]`
- 关键 deps：`temperatures[0]`、`temperatures[1]`
- 当前扫描下标。
- 单调栈内容。
- 被弹出的下标。
- answer 数组更新。

## 教学解释

关键 teaching 字段：`what`、`why`、`formula`、`invariant`。

栈保持温度单调递减。遇到更高温度时，它正好是栈顶那些较低温度等待的下一个更高温度。

## 验收标准

- pop 事件必须说明被当前温度解决。
- answer 更新必须指向原数组下标。
- 栈元素和数组单元必须联动高亮。
