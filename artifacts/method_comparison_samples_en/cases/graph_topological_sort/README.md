# Topological Sort

- Case ID: `graph_topological_sort`
- Algorithm family: BFS/DFS Basic Graph
- Difficulty: medium
- Time complexity: `O(V+E)`
- Space complexity: `O(V)`

You are developing a course selection recommendation feature for an academic administration system. Given a course dependency graph (adjacency list), where each course is represented as a string, please return a valid course sequence list such that all prerequisite courses appear before each course.

## Fixed input and expected answer

```json
{
  "expected": [
    "A",
    "B",
    "C",
    "D"
  ],
  "index": 0,
  "input_data": {
    "graph": {
      "A": [
        "B",
        "C"
      ],
      "B": [
        "D"
      ],
      "C": [
        "D"
      ],
      "D": []
    }
  }
}
```

## Nine machine checks

Machine OK means that all nine browser checks pass for the same page.

| Method | Load | Answer | Interaction | Correct feedback | Wrong feedback | Hint | Show answer | Learning log | Mutation-free | Machine OK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AlgoTutorGen / Stage2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Direct HTML | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | FAIL |
| WebGen-Agent | PASS | FAIL | PASS | PASS | PASS | FAIL | PASS | FAIL | PASS | FAIL |
| Direct + HTMLCure (strict) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Direct-BrowserRepair (1 call) | PASS | PASS | PASS | FAIL | PASS | PASS | FAIL | PASS | PASS | FAIL |

## Generated artifacts

### AlgoTutorGen / Stage2

[Open AlgoTutorGen / Stage2 page](algotutorgen_stage2/page.html) · [Machine audit](algotutorgen_stage2/audit.json)

![graph_topological_sort - AlgoTutorGen / Stage2](algotutorgen_stage2/screenshot.png)

### Direct HTML

[Open Direct HTML page](direct_html/page.html) · [Machine audit](direct_html/audit.json)

![graph_topological_sort - Direct HTML](direct_html/screenshot.png)

### WebGen-Agent

[WebGen-Agent source entry](webgen_agent/source/index.html) · [Machine audit](webgen_agent/audit.json)

![graph_topological_sort - WebGen-Agent](webgen_agent/screenshot.png)

### Direct + HTMLCure (strict)

[Open Direct + HTMLCure (strict) page](htmlcure_strict/page.html) · [Machine audit](htmlcure_strict/audit.json)

![graph_topological_sort - Direct + HTMLCure (strict)](htmlcure_strict/screenshot.png)

### Direct-BrowserRepair (1 call)

[Open Direct-BrowserRepair (1 call) page](browser_repair_1call/page.html) · [Machine audit](browser_repair_1call/audit.json)

![graph_topological_sort - Direct-BrowserRepair (1 call)](browser_repair_1call/screenshot.png)
