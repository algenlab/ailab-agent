# Reverse Linked List

- Case ID: `reverse_linked_list`
- Algorithm family: Linked List and Cache
- Difficulty: medium
- Time complexity: `O(n)`
- Space complexity: `O(1)`

Suppose you are developing a browser where a user visits a series of web pages, and a list `values` records the visited URL IDs. The browser needs to generate a backward history path, i.e., reverse the visit order so that the user can gradually go back from the current page to the earliest visited page. Given the list `values` representing the visited page IDs in order, please implement an algorithm that returns the reversed list, i.e., the backward order.

## Fixed input and expected answer

```json
{
  "expected": [
    3,
    2,
    1
  ],
  "index": 0,
  "input_data": {
    "values": [
      1,
      2,
      3
    ]
  }
}
```

## Nine machine checks

Machine OK means that all nine browser checks pass for the same page.

| Method | Load | Answer | Interaction | Correct feedback | Wrong feedback | Hint | Show answer | Learning log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| WebGen-Agent | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | FAIL | PASS | FAIL |
| Direct + HTMLCure (strict) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct-BrowserRepair (1 call) | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | FAIL |

## Generated artifacts

### AlgoTutorGen / Stage2

[Open AlgoTutorGen / Stage2 page](algotutorgen_stage2/page.html) · [Machine audit](algotutorgen_stage2/audit.json)

![reverse_linked_list - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[Open Direct HTML page](direct_html/page.html) · [Machine audit](direct_html/audit.json)

![reverse_linked_list - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent source entry](webgen_agent/source/index.html) · [Machine audit](webgen_agent/audit.json)

![reverse_linked_list - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[Open Direct + HTMLCure (strict) page](htmlcure_strict/page.html) · [Machine audit](htmlcure_strict/audit.json)

![reverse_linked_list - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1 call)

[Open Direct-BrowserRepair (1 call) page](browser_repair_1call/page.html) · [Machine audit](browser_repair_1call/audit.json)

![reverse_linked_list - Direct-BrowserRepair (1 call)](browser_repair_1call/screenshot.png)
