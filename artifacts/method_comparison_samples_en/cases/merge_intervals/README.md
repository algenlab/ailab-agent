# Merge Intervals

- Case ID: `merge_intervals`
- Algorithm family: Greedy
- Difficulty: medium
- Time complexity: `O(n log n)`
- Space complexity: `O(n)`

The conference center receives multiple venue occupancy requests. Each closed interval [start time, end time] in intervals represents a reservation slot. Since the same room cannot be used simultaneously, all overlapping or contiguous slots need to be merged, returning the final list of non-overlapping occupied intervals sorted by start time.

## Fixed input and expected answer

```json
{
  "expected": [
    [
      1,
      6
    ],
    [
      8,
      10
    ],
    [
      15,
      18
    ]
  ],
  "index": 0,
  "input_data": {
    "intervals": [
      [
        1,
        3
      ],
      [
        2,
        6
      ],
      [
        8,
        10
      ],
      [
        15,
        18
      ]
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
| WebGen-Agent | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct + HTMLCure (strict) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct-BrowserRepair (1 call) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

## Generated artifacts

### AlgoTutorGen / Stage2

[Open AlgoTutorGen / Stage2 page](algotutorgen_stage2/page.html) · [Machine audit](algotutorgen_stage2/audit.json)

![merge_intervals - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[Open Direct HTML page](direct_html/page.html) · [Machine audit](direct_html/audit.json)

![merge_intervals - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent source entry](webgen_agent/source/index.html) · [Machine audit](webgen_agent/audit.json)

![merge_intervals - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[Open Direct + HTMLCure (strict) page](htmlcure_strict/page.html) · [Machine audit](htmlcure_strict/audit.json)

![merge_intervals - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1 call)

[Open Direct-BrowserRepair (1 call) page](browser_repair_1call/page.html) · [Machine audit](browser_repair_1call/audit.json)

![merge_intervals - Direct-BrowserRepair (1 call)](browser_repair_1call/screenshot.png)
