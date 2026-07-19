# 快速幂取模

- 案例 ID：`fast_power_mod`
- 算法家族：数学与位运算
- 难度：medium
- 时间复杂度：`O(log exponent)`
- 空间复杂度：`O(log exponent)`

在一个安全验证场景中，给定底数 base、指数 exponent 和模数 mod，你需要计算 base 的 exponent 次幂对 mod 取模的结果。请实现快速幂算法，返回最终模值。

## 抽样输入

```json
{
  "expected": 9,
  "index": 0,
  "input_data": {
    "base": 3,
    "exponent": 5,
    "mod": 13
  }
}
```

## 九项机器判定

| 方法 | Load | Answer | Interaction | Correct FB | Wrong FB | Hint | Show | Log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| WebGen-Agent | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | FAIL |
| Direct + HTMLCure (strict) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct-BrowserRepair (1-call) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

## 五种方法的真实产物

### AlgoTutorGen / Stage2

[打开 AlgoTutorGen / Stage2 HTML](algotutorgen_stage2/page.html) · [审计摘要](algotutorgen_stage2/audit.json)

- Machine OK：**PASS**
- 教学总分：4.857
- 视觉总分：4.75

![fast_power_mod - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[打开 Direct HTML HTML](direct_html/page.html) · [审计摘要](direct_html/audit.json)

- Machine OK：**PASS**
- 教学总分：5.0
- 视觉总分：5.0

![fast_power_mod - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent 源码入口](webgen_agent/source/index.html) · [package.json](webgen_agent/source/package.json) · [审计摘要](webgen_agent/audit.json)

- Machine OK：**FAIL**
- 教学总分：3.857
- 视觉总分：4.75

![fast_power_mod - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[打开 Direct + HTMLCure (strict) HTML](htmlcure_strict/page.html) · [审计摘要](htmlcure_strict/audit.json)

- Machine OK：**FAIL**
- 教学总分：2.857
- 视觉总分：4.75

![fast_power_mod - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1-call)

[打开 Direct-BrowserRepair (1-call) HTML](browser_repair_1call/page.html) · [审计摘要](browser_repair_1call/audit.json)

- Machine OK：**PASS**
- 教学总分：5.0
- 视觉总分：5.0

![fast_power_mod - Direct-BrowserRepair (1-call)](browser_repair_1call/screenshot.png)
