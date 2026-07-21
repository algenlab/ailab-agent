# English Method Artifact Gallery: Stage1 and Stage2

This directory contains English-only artifacts for the same fixed 23 cases and five comparison methods as the original gallery.
AlgoTutorGen contributes both its Stage1 and Stage2 views, so the collection contains 138 saved artifact views in total.
The Stage1 solution, trace, scenes, inputs, and expected answers are reused; only human-readable text is localized into English.

## Methods and AlgoTutorGen stages

| Method | Description | Saved artifact |
| --- | --- | --- |
| AlgoTutorGen / Stage1 | The existing verified Stage1 solution, trace, teaching interactions, and deterministic visualization localized into English without regenerating the solution. | HTML page, structured build JSON, screenshot, and audit |
| AlgoTutorGen / Stage2 | A newly generated English Stage2 visual page built from the verified AlgoTutorGen result; its nine machine checks come from the paired Stage1 interaction page. | HTML page, screenshot, and audit |
| Direct HTML | A model directly generates the complete interactive HTML page. | HTML page, screenshot, and audit |
| WebGen-Agent | WebGen-Agent produces a complete frontend project through its iterative workflow. | source project, screenshot, and audit |
| Direct + HTMLCure (strict) | HTMLCure repairs the independently generated Direct HTML page under its strict setting. | HTML page, screenshot, and audit |
| Direct-BrowserRepair (1 call) | An independent one-call Direct-BrowserRepair budget run with no prior browser-feedback repair call. | HTML page, screenshot, and audit |

## Case index

| Family | Case | Stage1 | Stage2 | Direct HTML | WebGen-Agent | HTMLCure | BrowserRepair |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BFS/DFS Basic Graph | [Topological Sort](cases/graph_topological_sort/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| DP Core Extension | [Complete Knapsack Coin Change](cases/complete_knapsack_coin_change/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Trie | [Trie Prefix Counting](cases/trie_prefix/README.md) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| 1D DP | [House Robber](cases/house_robber/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Binary | [Binary Search](cases/binary_search/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| 2D DP | [Unique Paths](cases/unique_paths/README.md) | PASS | PASS | FAIL | PASS | FAIL | FAIL |
| Geometry / Scanline | [Convex Hull](cases/convex_hull/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Range Structure | [Segment Tree Range Sum](cases/segment_tree_range_sum/README.md) | PASS | PASS | PASS | FAIL | PASS | FAIL |
| Hash Table / map | [Two Sum](cases/two_sum/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Backtracking / Recursion | [Permutations](cases/permutations/README.md) | PASS | PASS | PASS | FAIL | PASS | FAIL |
| Advanced Graph | [Articulation Points and Bridges](cases/articulation_bridges/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Heap / TopK / Huffman | [Kth Largest Element in an Array](cases/kth_largest/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Advanced String Algorithm | [KMP String Matching](cases/kmp/README.md) | PASS | PASS | FAIL | PASS | FAIL | FAIL |
| Union Find | [Number of Provinces](cases/provinces/README.md) | PASS | PASS | PASS | FAIL | PASS | FAIL |
| Sorting | [Insertion Sort](cases/insertion_sort/README.md) | PASS | PASS | PASS | FAIL | FAIL | FAIL |
| Mathematics and Bitwise Operations | [Fast Power Modulo](cases/fast_power_mod/README.md) | PASS | PASS | PASS | FAIL | PASS | FAIL |
| Array Pointer / Window / Prefix | [Two Sum in Sorted Array](cases/two_pointer_pair_sum/README.md) | PASS | PASS | FAIL | PASS | FAIL | FAIL |
| Shortest Path / MST | [Dijkstra Shortest Path](cases/dijkstra_shortest_path/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Stack / Queue / Monotonic Stack | [Daily Temperatures](cases/daily_temperatures/README.md) | PASS | PASS | FAIL | FAIL | FAIL | PASS |
| Tree / BST / LCA | [Binary Tree Lowest Common Ancestor](cases/lca/README.md) | PASS | PASS | FAIL | PASS | FAIL | FAIL |
| Tree DP | [Tree DP Maximum Independent Set](cases/tree_max_independent_set/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
| Greedy | [Merge Intervals](cases/merge_intervals/README.md) | PASS | PASS | FAIL | FAIL | FAIL | PASS |
| Linked List and Cache | [Reverse Linked List](cases/reverse_linked_list/README.md) | PASS | PASS | FAIL | FAIL | FAIL | FAIL |
