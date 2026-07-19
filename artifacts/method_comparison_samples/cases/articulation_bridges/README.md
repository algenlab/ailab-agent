# 割点和桥

- 案例 ID：`articulation_bridges`
- 算法家族：图高级
- 难度：medium
- 时间复杂度：`O(V+E)`
- 空间复杂度：`O(V)`

在一个城市的通信网络中，每个交换站对应一个节点，光纤连接对应无向边。给定邻接表表示的图graph，你需要找出所有割点（关键交换站）和桥（唯一光纤），输出格式为包含articulation（割点列表）和bridges（桥的边列表）的对象。

## 抽样输入

```json
{
  "expected": {
    "articulation": [
      "B",
      "D"
    ],
    "bridges": [
      [
        "D",
        "E"
      ],
      [
        "A",
        "B"
      ]
    ]
  },
  "index": 0,
  "input_data": {
    "graph": {
      "A": [
        "B"
      ],
      "B": [
        "A",
        "C",
        "D"
      ],
      "C": [
        "B",
        "D"
      ],
      "D": [
        "B",
        "C",
        "E"
      ],
      "E": [
        "D"
      ]
    }
  }
}
```

## 九项机器判定

| 方法 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| WebGen-Agent | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct + HTMLCure (strict) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct-BrowserRepair (1-call) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

## 五种方法的真实产物

### AlgoTutorGen / Stage2

[打开 AlgoTutorGen / Stage2 HTML](algotutorgen_stage2/page.html) · [审计摘要](algotutorgen_stage2/audit.json)

- Machine OK：**PASS**
- 教学总分：4.857
- 视觉总分：5.0

![articulation_bridges - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[打开 Direct HTML HTML](direct_html/page.html) · [审计摘要](direct_html/audit.json)

- Machine OK：**PASS**
- 教学总分：5.0
- 视觉总分：5.0

![articulation_bridges - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent 源码入口](webgen_agent/source/index.html) · [package.json](webgen_agent/source/package.json) · [审计摘要](webgen_agent/audit.json)

- Machine OK：**FAIL**
- 教学总分：3.143
- 视觉总分：4.75

![articulation_bridges - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[打开 Direct + HTMLCure (strict) HTML](htmlcure_strict/page.html) · [审计摘要](htmlcure_strict/audit.json)

- Machine OK：**FAIL**
- 教学总分：2.429
- 视觉总分：4.25

![articulation_bridges - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1-call)

[打开 Direct-BrowserRepair (1-call) HTML](browser_repair_1call/page.html) · [审计摘要](browser_repair_1call/audit.json)

- Machine OK：**PASS**
- 教学总分：5.0
- 视觉总分：5.0

![articulation_bridges - Direct-BrowserRepair (1-call)](browser_repair_1call/screenshot.png)
