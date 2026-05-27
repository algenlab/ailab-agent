# Trace 与 Schema 合同

## 1. 合同定位

SemanticTrace 是 AlgoLab 的核心中间表示。LLM 只能生成算法语义候选，不能直接生成页面。系统通过执行、校验和编译 SemanticTrace 来生成教学页面。

本文档是 tracker、validator、compiler、renderer 之间的接口合同。

## 2. 顶层 schema

`trace(input_data)` 必须返回 dict，并能通过 `SemanticTrace` 校验：

```json
{
  "schema_version": "semantic-trace-v1",
  "algorithm": "不同路径",
  "input_data": {"m": 3, "n": 7},
  "result": 28,
  "pseudocode": ["dp[i][j] = dp[i-1][j] + dp[i][j-1]"],
  "events": [
    {
      "step": 0,
      "op": "create",
      "targets": [{"id": "dp"}],
      "state": {"dp": [[1, 1, 1], [1, 1, 1]]},
      "reason": "初始化 DP 表。",
      "code_line": 1
    }
  ]
}
```

要求：

- `schema_version` 必须是 `semantic-trace-v1`。
- `input_data` 必须显式存在，并且与本次请求完全一致。
- `events` 不能为空。
- `events[i].step == i`。
- `result` 必须等于 `solve(input_data)` 的返回值。

## 3. Event schema

每个事件字段：

```json
{
  "step": 0,
  "op": "set",
  "targets": [{"id": "dp[1][2]"}],
  "value": 3,
  "before": 1,
  "after": 3,
  "deps": [{"id": "dp[0][2]"}, {"id": "dp[1][1]"}],
  "role": "answer",
  "reason": "写入上方和左侧路径数之和。",
  "state": {"dp": [[1, 1, 1], [1, 2, 3]], "i": 1, "j": 2},
  "code_line": 3
}
```

必须字段：

- `step`
- `op`
- `targets`
- `state`
- `code_line`

推荐字段：

- `value`
- `before`
- `after`
- `deps`
- `role`
- `reason`
- `teaching`
- `interaction`

## 4. 固定 op 集合

当前合法 op：

- `create`
- `set`
- `mark`
- `unmark`
- `move`
- `compare`
- `link`
- `unlink`
- `push`
- `pop`
- `enter`
- `exit`
- `explain`

新增算法通常不需要新增 op。只有现有 op 无法表达新的通用语义动作时，才允许扩展 schema、validator、compiler、renderer 和测试。

## 5. Target id 规范

推荐 target：

```text
数组/表格：nums[0]、dp[1][2]
切片：text[2:5]
哈希表：seen[2]、dist[B]、count[x]
图节点/边：node:A、edge:A->B
指针：pointer:left、pointer:mid
递归帧：frame:dfs(2)
几何点：point:3
字符串字符：text[3]、pattern[2]
容器：stack、queue、heap、tree、trie、frames、points、string
```

禁止在当前实现中直接使用未支持的新前缀 target，例如：

```text
range:1-3
number:n
interval:2-5
flow:A->B
```

这些前缀会被当前 trace validator 视为旧式冒号 target 或普通 symbol，不能稳定进入 SceneGraph。若要把它们变成正式合同，必须同步扩展：

- `algolab/compiler/target_parser.py`
- `algolab/verification/trace_validator.py`
- `algolab/compiler/scene_compiler.py`
- `algolab/renderer/*`
- 对应 regression tests

在完成这些实现前，新算法应优先用已支持的数组、表格、节点、边、指针、frame、point、symbol 和容器 target 表达。

可落地替代表达：

```text
区间：用 nums[2:5]、query[0]、query[1]，或 tree 节点 label/meta 表达覆盖范围。
数字：用 n、mask、bits[0]、factor[2]、table[3][4]。
线段树节点：用 node:seg_1_4 或 node:seg(1,4)，前提是 state 中的 tree / segment_tree nodes 明确包含该 id。
网络流容量：用 cap[A->B]、flow[A->B] 或 edge:A->B + state 中的 capacity/flow map。
```

禁止旧写法：

```text
type / target       -> 必须改为 op / targets
seen:2              -> seen[2]
dist:A              -> dist[A]
map:seen            -> seen
seen['2']           -> seen[2]
```

## 6. Deps 规范

`deps` 表示当前操作依赖哪些对象。

必须提供 deps 的情况：

- DP 状态转移。
- 图搜索首次访问节点。
- 哈希表命中 complement。
- 单调栈弹出并写答案。
- 二分根据 mid 收缩区间。
- 树递归从子树返回结果。

示例：

```json
{
  "op": "set",
  "targets": [{"id": "dp[2][3]"}],
  "deps": [{"id": "dp[1][3]"}, {"id": "dp[2][2]"}]
}
```

## 7. State 规范

`state` 是当前帧可视化和过程校验的主要证据。

要求：

- 必须包含重建主视图所需的关键变量。
- DP 应包含完整或必要局部 `dp` 表。
- 图搜索应包含 `graph`、`queue` / frontier、`dist` / visited。
- 数组指针应包含数组、指针、窗口或区间。
- 栈队列应包含容器内容和当前扫描下标。
- 哈希表应包含 map 当前状态。

以下划线开头的 state 字段为内部元信息，编译 SceneGraph 时可隐藏，例如 `_trace_meta`。

## 8. Tracer API 用法

新 tracker 应优先使用 `Tracer`：

```python
def trace(input_data):
    tracer = Tracer(
        input_data,
        algorithm="不同路径",
        pseudocode=["dp[i][j] = dp[i-1][j] + dp[i][j-1]"],
    )
    dp = [[1] * input_data["n"] for _ in range(input_data["m"])]
    tracer.create("dp", state={"dp": [row[:] for row in dp]}, reason="初始化 DP 表。")
    tracer.result(dp[-1][-1])
    return tracer.to_trace()
```

常用方法：

- `create(target, ...)`
- `set(target, ...)`
- `mark(target, ...)`
- `unmark(target, ...)`
- `move(target, ...)`
- `compare(targets, ...)`
- `link(target, ...)`
- `unlink(target, ...)`
- `push(target, ...)`
- `pop(target, ...)`
- `enter(target, ...)`
- `exit(target, ...)`
- `explain(target=None, ...)`
- `expect_updates(name, count)`
- `result(value)`
- `to_trace()`

`unmark`、`link`、`unlink`、`enter`、`exit` 只是在固定 SemanticTrace op 上提供便捷封装，不引入新 op。它们适合表达取消标记、建立 / 删除关系、进入 / 退出递归帧或作用域。新增算法仍应优先复用这些固定 op、已有 target 规范和 state 证据，不要因为便捷方法存在而新增 target 前缀或 renderer 规则。

## 9. 正确示例

DP 转移：

```python
tracer.compare(
    [f"dp[{i}][{j}]"],
    deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
    state={"dp": [row[:] for row in dp], "i": i, "j": j},
    role="candidate",
    reason="当前位置只能从上方或左侧到达。",
    code_line=3,
)
dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
tracer.set(
    f"dp[{i}][{j}]",
    value=dp[i][j],
    deps=[f"dp[{i-1}][{j}]", f"dp[{i}][{j-1}]"],
    state={"dp": [row[:] for row in dp], "i": i, "j": j},
    role="answer",
    reason="写入上方和左侧路径数之和。",
    code_line=3,
)
```

## 10. 错误示例

旧字段：

```json
{"step": 0, "type": "set", "target": "dp[1][2]"}
```

缺少输入：

```json
{"schema_version": "semantic-trace-v1", "algorithm": "二分查找", "events": []}
```

旧 map target：

```json
{"targets": [{"id": "seen:2"}]}
```

自然语言代替状态：

```json
{"op": "explain", "reason": "这里做动态规划", "state": {}}
```

## 11. Repair 原则

校验失败后，repair prompt 应优先修复：

1. schema 字段错误。
2. `input_data` 缺失或不一致。
3. `solve_result != trace.result`。
4. target id 不合法。
5. 关键步骤缺失。
6. DP / BFS / 二分等过程不变量不满足。
7. SceneGraph 无可渲染对象。

禁止通过删除 validator、放宽 release gate 或让 renderer 猜过程来 repair。
