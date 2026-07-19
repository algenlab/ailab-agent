# 全排列

- 案例 ID：`permutations`
- 算法家族：回溯 / 递归
- 难度：medium
- 时间复杂度：`O(n! n)`
- 空间复杂度：`O(n)`

你是一位安全专家，面对一个密码锁，它由一组不重复的数字组成（输入数组 nums）。你需要生成所有可能的开锁数字序列（即 nums 的全排列），以便遍历尝试。请输出所有排列的列表。

## 抽样输入

```json
{
  "expected": [
    [
      1,
      2,
      3
    ],
    [
      1,
      3,
      2
    ],
    [
      2,
      1,
      3
    ],
    [
      2,
      3,
      1
    ],
    [
      3,
      1,
      2
    ],
    [
      3,
      2,
      1
    ]
  ],
  "index": 0,
  "input_data": {
    "nums": [
      1,
      2,
      3
    ]
  }
}
```

## 九项机器判定

| 方法 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | FAIL | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| WebGen-Agent | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | FAIL |
| Direct + HTMLCure (strict) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct-BrowserRepair (1-call) | FAIL | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |

## 五种方法的真实产物

### AlgoTutorGen / Stage2

[打开 AlgoTutorGen / Stage2 HTML](algotutorgen_stage2/page.html) · [审计摘要](algotutorgen_stage2/audit.json)

- Machine OK：**PASS**
- 教学总分：5.0
- 视觉总分：5.0

![permutations - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[打开 Direct HTML HTML](direct_html/page.html) · [审计摘要](direct_html/audit.json)

- Machine OK：**FAIL**
- 教学总分：2.429
- 视觉总分：3.5

![permutations - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent 源码入口](webgen_agent/source/index.html) · [package.json](webgen_agent/source/package.json) · [审计摘要](webgen_agent/audit.json)

- Machine OK：**FAIL**
- 教学总分：4.857
- 视觉总分：4.75

![permutations - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[打开 Direct + HTMLCure (strict) HTML](htmlcure_strict/page.html) · [审计摘要](htmlcure_strict/audit.json)

- Machine OK：**FAIL**
- 教学总分：2.571
- 视觉总分：5.0

![permutations - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1-call)

[打开 Direct-BrowserRepair (1-call) HTML](browser_repair_1call/page.html) · [审计摘要](browser_repair_1call/audit.json)

- Machine OK：**FAIL**
- 教学总分：2.857
- 视觉总分：4.25

![permutations - Direct-BrowserRepair (1-call)](browser_repair_1call/screenshot.png)
