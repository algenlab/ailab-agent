# 插入排序

- 案例 ID：`insertion_sort`
- 算法家族：排序
- 难度：medium
- 时间复杂度：`O(n^2)`
- 空间复杂度：`O(1)`

在音乐播放器应用中，你获得了歌曲喜爱度评分列表 nums，请使用插入排序方法将其升序排列，返回排序后的列表，以便按评分从低到高播放歌曲。

## 抽样输入

```json
{
  "expected": [
    1,
    2,
    3,
    5
  ],
  "index": 0,
  "input_data": {
    "nums": [
      5,
      2,
      3,
      1
    ]
  }
}
```

## 九项机器判定

| 方法 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL |
| WebGen-Agent | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL |
| Direct + HTMLCure (strict) | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL |
| Direct-BrowserRepair (1-call) | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL |

## 五种方法的真实产物

### AlgoTutorGen / Stage2

[打开 AlgoTutorGen / Stage2 HTML](algotutorgen_stage2/page.html) · [审计摘要](algotutorgen_stage2/audit.json)

- Machine OK：**PASS**
- 教学总分：4.857
- 视觉总分：4.75

![insertion_sort - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[打开 Direct HTML HTML](direct_html/page.html) · [审计摘要](direct_html/audit.json)

- Machine OK：**FAIL**
- 教学总分：4.286
- 视觉总分：5.0

![insertion_sort - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent 源码入口](webgen_agent/source/index.html) · [package.json](webgen_agent/source/package.json) · [审计摘要](webgen_agent/audit.json)

- Machine OK：**FAIL**
- 教学总分：4.714
- 视觉总分：4.75

![insertion_sort - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[打开 Direct + HTMLCure (strict) HTML](htmlcure_strict/page.html) · [审计摘要](htmlcure_strict/audit.json)

- Machine OK：**FAIL**
- 教学总分：4.143
- 视觉总分：4.25

![insertion_sort - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1-call)

[打开 Direct-BrowserRepair (1-call) HTML](browser_repair_1call/page.html) · [审计摘要](browser_repair_1call/audit.json)

- Machine OK：**FAIL**
- 教学总分：4.286
- 视觉总分：4.75

![insertion_sort - Direct-BrowserRepair (1-call)](browser_repair_1call/screenshot.png)
