# Complete Knapsack Coin Change

- Case ID: `complete_knapsack_coin_change`
- Algorithm family: DP Core Extension
- Difficulty: medium
- Time complexity: `O(len(coins) * amount)`
- Space complexity: `O(amount)`

A store cashier needs to give change for amount. There is an unlimited number of coins in the cash register, with denominations given by the array coins. Write a program to calculate the minimum number of coins needed to make up the amount. If it is impossible to make up the amount in any way, return -1.

## Fixed input and expected answer

```json
{
  "expected": 3,
  "index": 0,
  "input_data": {
    "amount": 11,
    "coins": [
      1,
      2,
      5
    ]
  }
}
```

## Nine machine checks

Machine OK means that all nine browser checks pass for the same page.

| Method | Load | Answer | Interaction | Correct feedback | Wrong feedback | Hint | Show answer | Learning log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| WebGen-Agent | PASS | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | FAIL |
| Direct + HTMLCure (strict) | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| Direct-BrowserRepair (1 call) | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL |

## Generated artifacts

### AlgoTutorGen / Stage2

[Open AlgoTutorGen / Stage2 page](algotutorgen_stage2/page.html) · [Machine audit](algotutorgen_stage2/audit.json)

![complete_knapsack_coin_change - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[Open Direct HTML page](direct_html/page.html) · [Machine audit](direct_html/audit.json)

![complete_knapsack_coin_change - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent source entry](webgen_agent/source/index.html) · [Machine audit](webgen_agent/audit.json)

![complete_knapsack_coin_change - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[Open Direct + HTMLCure (strict) page](htmlcure_strict/page.html) · [Machine audit](htmlcure_strict/audit.json)

![complete_knapsack_coin_change - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1 call)

[Open Direct-BrowserRepair (1 call) page](browser_repair_1call/page.html) · [Machine audit](browser_repair_1call/audit.json)

![complete_knapsack_coin_change - Direct-BrowserRepair (1 call)](browser_repair_1call/screenshot.png)
