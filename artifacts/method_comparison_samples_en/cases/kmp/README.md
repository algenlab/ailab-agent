# KMP String Matching

- Case ID: `kmp`
- Algorithm family: Advanced String Algorithm
- Difficulty: medium
- Time complexity: `O(n+m)`
- Space complexity: `O(m)`

A genetic researcher is aligning a long DNA strand text and needs to quickly find the first occurrence position of the target gene probe pattern. Return -1 if not found, or 0 if pattern is an empty string. You can build a prefix table by analyzing the repetitive structure of the pattern itself, achieving smart jumps during matching and avoiding character-by-character matching from the beginning.

## Fixed input and expected answer

```json
{
  "expected": 2,
  "index": 0,
  "input_data": {
    "pattern": "abc",
    "text": "ababc"
  }
}
```

## Nine machine checks

Machine OK means that all nine browser checks pass for the same page.

| Method | Load | Answer | Interaction | Correct feedback | Wrong feedback | Hint | Show answer | Learning log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL |
| WebGen-Agent | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct + HTMLCure (strict) | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL |
| Direct-BrowserRepair (1 call) | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |

## Generated artifacts

### AlgoTutorGen / Stage2

[Open AlgoTutorGen / Stage2 page](algotutorgen_stage2/page.html) · [Machine audit](algotutorgen_stage2/audit.json)

![kmp - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[Open Direct HTML page](direct_html/page.html) · [Machine audit](direct_html/audit.json)

![kmp - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent source entry](webgen_agent/source/index.html) · [Machine audit](webgen_agent/audit.json)

![kmp - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[Open Direct + HTMLCure (strict) page](htmlcure_strict/page.html) · [Machine audit](htmlcure_strict/audit.json)

![kmp - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1 call)

[Open Direct-BrowserRepair (1 call) page](browser_repair_1call/page.html) · [Machine audit](browser_repair_1call/audit.json)

![kmp - Direct-BrowserRepair (1 call)](browser_repair_1call/screenshot.png)
