# Insertion Sort

- Case ID: `insertion_sort`
- Algorithm family: Sorting
- Difficulty: medium
- Time complexity: `O(n^2)`
- Space complexity: `O(1)`

In a music player application, you are given a list of song favorability scores nums. Use the insertion sort method to sort them in ascending order and return the sorted list, so that songs can be played from lowest to highest score.

## Fixed input and expected answer

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

## Nine machine checks

Machine OK means that all nine browser checks pass for the same page.

| Method | Load | Answer | Interaction | Correct feedback | Wrong feedback | Hint | Show answer | Learning log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| WebGen-Agent | PASS | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | FAIL |
| Direct + HTMLCure (strict) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct-BrowserRepair (1 call) | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL |

## Generated artifacts

### AlgoTutorGen / Stage2

[Open AlgoTutorGen / Stage2 page](algotutorgen_stage2/page.html) · [Machine audit](algotutorgen_stage2/audit.json)

![insertion_sort - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[Open Direct HTML page](direct_html/page.html) · [Machine audit](direct_html/audit.json)

![insertion_sort - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent source entry](webgen_agent/source/index.html) · [Machine audit](webgen_agent/audit.json)

![insertion_sort - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[Open Direct + HTMLCure (strict) page](htmlcure_strict/page.html) · [Machine audit](htmlcure_strict/audit.json)

![insertion_sort - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1 call)

[Open Direct-BrowserRepair (1 call) page](browser_repair_1call/page.html) · [Machine audit](browser_repair_1call/audit.json)

![insertion_sort - Direct-BrowserRepair (1 call)](browser_repair_1call/screenshot.png)
