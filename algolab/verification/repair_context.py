"""Repair context helpers for validation and benchmark failures."""

from __future__ import annotations

import json
import re
from typing import Any

from algolab.schemas.input import ProblemInput
from algolab.verification.process_validator import process_failure_type_for_message


STEP_RE = re.compile(r"第\s*(\d+)\s*(?:步|帧|个事件)")
TARGET_PATTERNS = (
    re.compile(r"(?<![\w.])([A-Za-z_][\w]*(?:\[[^\]\s]+\])+)(?![\w.\[])"),
    re.compile(r"\b([A-Za-z_][\w]*:[^\s，,；;]+)\b"),
    re.compile(r"(?:target|对象|格式|转移|依赖|引用|写入|指向)[^：:]*[：:]\s*([A-Za-z_][\w]*(?:\[\d+\])?(?:\[[^\]]+\])?)"),
)
DEMO_FAILURE_TYPES = {
    "demo_missing_reason",
    "demo_missing_deps",
    "demo_missing_state",
    "demo_state_jump",
    "demo_algorithm_mismatch",
    "demo_key_step_missing",
}
FORBIDDEN_REPAIR_ACTIONS = (
    "不要生成 HTML、CSS、JS 或 renderer 代码。",
    "不要绕过 SemanticTrace、SceneGraph、process validator 或 demo readiness。",
    "不要只改最终答案来掩盖错误过程。",
)
BITMASK_SUBSETS_REPAIR_GUIDANCE: tuple[str, ...] = (
    "位掩码子集固定短模板：用 tracer.create(\"subsets\") 初始化结果容器，state.subsets=[]，state.mask=0。",
    "每个 mask 先用 tracer.set(\"mask\") 写当前掩码，再用 tracer.set(\"subset\") 展示当前子集；subset 事件带 value=current_subset、deps=[\"mask\"]、state。",
    "把累计结果写回 tracer.set(\"subsets\")，value=accumulated_subsets；也可以把 tracer.set(\"subsets\") 的 deps 改为 [\"mask\"]，不要使用 res[i]/result[i] 作为 target/deps。",
    "deps 写 subset 时同一事件 state.subset 必须存在；deps 写 subsets 时同一事件 state.subsets 必须存在，最终 answer state 同时保留 subsets 和 answer。",
    "最终用 tracer.mark(\"answer\")，value=subsets，role=\"answer\"，deps=[\"subsets\"]，state.answer=subsets；不要把 res[1]、result[1] 或 answer[1] 放进 targets。",
)
FAMILY_REPAIR_GUIDANCE: dict[str, tuple[str, ...]] = {
    "dynamic_programming": (
        "保持 dp_contract；初始化、每个关键 set、deps、value、formula 和 answer_position 必须可复核。",
        "小规模 DP 不要抽样跳过关键状态；补齐真实循环中的每个关键转移。",
        "最终答案事件必须 role=answer，并在 targets 或 deps 中引用 dp[answer_position] 对应的真实 target，例如 answer_position=dp[11] 时引用 dp[11]。",
        "每个 set dp 事件都必须提供 state.formula 或 teaching.formula；最终答案若用 set 也写 formula=answer=dp[amount]。",
        "0-1 背包使用 knapsack_01 且 capacity_index 倒序扫描；多重背包使用 bounded_knapsack 并记录 count/数量上限、capacity 和 deps。",
        "subset-sum/0-1 背包初始化必须用 tracer.create(\"dp\") 给出 DP 容器初始状态，state.dp[0]=True 且 state.dp_contract 存在；不要只用 tracer.set(\"dp[0]\") 记录 base case。",
        "subset-sum/0-1 背包每个 dp set 带 i、capacity_index、capacity、old_value、candidate、formula、deps 和 dp_contract.expected_targets。",
        "状态压缩 DP 必须把 ans 作为关键更新：最终 set/mark ans，deps 指向 full_mask 的 dp[full_mask][last]，state 包含 mask/current/next/full_mask/candidate/formula。",
        "状态压缩 TSP 若触发 JSON 截断或空内容，重写为 1 个 variant、6-10 个 events、短 tracker_code：只展示 create dp、base、1-2 个转移、set/mark ans，不要复制长代码。",
        "DP 演示缺少状态转移写入帧时不能只 compare/mark；必须在循环中用 tracer.set 写真实状态。Floyd-Warshall 写 dist[i][j]、deps=[dist[i][k], dist[k][j]]、state.k/i/j/old_dist/new_dist。",
        "树形 DP/树递归若出现 dp_take 或 tree，state 同时保留 tree、current、return_values 或 aggregate；按后序写 dp_take[current] 和 dp_skip[current]。",
        "树形 DP demo 必须显式 tracer.set(\"dp_take[current]\") 和 tracer.set(\"dp_skip[current]\")，不要只在 state 里更新 dp_take/dp_skip；最终 role=answer 引用 max(dp_take[root], dp_skip[root])。",
        "树形 DP 的 mark 必须带 value、deps=[\"dp_take[current]\", \"dp_skip[current]\"] 和 state.answer；不要把 answer_position 写成裸根节点 1，应使用 dp_take[1]、dp_skip[1] 或可渲染 answer target，并让 role=answer 事件引用真实 DP target。",
        "树形 DP 后序完成前不要在 state.dp_take/dp_skip 中写当前父节点的半成品；先完成所有 child 的 dp_take/dp_skip，再 set dp_take[current]，再 set dp_skip[current]。dp_contract.containers 包含 answer、answer_position=\"answer\"，expected_targets 包含 answer；最终必须 tracer.set(\"answer\")，deps=[\"dp_take[root]\", \"dp_skip[root]\"]。",
        "不要把 set dp[0] 写成无 deps 的关键更新；若用 set 记录 base case，写 deps=[\"dp\"]、capacity_index=0、capacity=0、formula=\"dp[0]=True\"。",
        "状态压缩每一个 tracer.set 都必须带 deps，初始化 set 也必须带 deps；base 写 dp[1<<start][start] 时 deps=[\"dp\"]，转移 deps 指向 dp[mask][current] 和 cost/current edge。",
    ),
    "graph": (
        "保持 graph_contract，并按具体 submode 修复；不要把 graph 过程错误只改成最终答案。",
        "图事件必须保留可复核的 frontier、边、状态表和 deps，让 process validator 能检查每一步转移。",
        "BFS/DFS/染色/匹配小图必须显式边检查：先 tracer.compare([\"edge:u->v\"], deps=[\"node:u\", \"node:v\", \"edge:u->v\"], state={...}, reason 含 check_edge/检查边)，再首次访问/relax。",
        "首次访问、染色、匹配或 relax 的 mark/set/push 必须带 deps=[\"node:u\", \"node:v\", \"edge:u->v\"]，state 保留 queue/stack/frontier、visited/color/match/dist。",
        "二分图染色使用 graph_contract submode=bipartite_coloring 和 state.color；不要使用 dist 表示颜色，也不要设置 graph_contract submode=bfs。",
        "BFS first_visit 必须用 tracer.set(\"dist[neighbor]\")，完整写法为 tracer.set(\"dist[neighbor]\", value=dist[current]+1, role=\"visited\", deps=[\"node:current\", \"node:neighbor\", \"edge:current->neighbor\"])，并写 parent[neighbor]=current；不要只写 deps=[\"dist[current]\", \"edge:current->neighbor\"]，不要只 push queue，也不要写 parent[neighbor]=neighbor。",
        "DFS/连通分量/增广路如果使用 graph_contract submode=dfs，必须在 state 保留 stack 或 frame:dfs frontier，并发出 enter/exit frame 事件。",
        "拓扑排序 Kahn 中 indegree[v] 变 0 后入队必须有 reason/action 写 indegree[v]==0/入队，deps 包含 indegree[v] 和 edge:u->v。",
        "拓扑排序初始化 indegree[D] 等于所有入边数量；每条 edge:u->v 只 decrement 一次，只有所有前驱处理完成后才把 v 入队。",
    ),
    "string": (
        "保持 family_contract；按 submode 修复：KMP/Rabin-Karp 记录 text/pattern，Z Algorithm/Manacher 单串不要机械添加 pattern。",
        "字符串滑动窗口是单串 text 算法：family_contract 使用 {\"family\":\"string\",\"submode\":\"string_sliding_window\"}，state 保留 text、left/right、window_counts、best；不要机械添加 pattern。",
        "字符串滑动窗口每个 move/set/answer 事件 targets 或 deps 必须引用 text[i]、pointer:left 或 pointer:right。",
        "字符串滑动窗口遇到重复字符时，必须按 while window_counts[text[right]] > 1 先收缩到无重复再更新 best；每次收缩都 set window_counts 并 move pointer:left。",
        "每个字符串滑动窗口事件的 window_counts 必须等于 text[left:right+1] 的逐字符计数；不要把收缩后的 window_counts 配上收缩前的 left/right。",
        "不要发布含重复字符的 state.window_counts；若需要解释重复，使用 pending_char/pending_count，发布事件 state.window_counts 必须已完成收缩。",
        "如果必须发布重复帧，reason 或 state.phase 必须写 duplicate_before_shrink/重复/收缩，且该重复帧的 window_counts 仍必须与当前 left/right 完全一致。",
        "字符串滑动窗口 answer 事件 deps/targets 引用 text 或 pointer，不能只 mark answer。",
        "记录 pi/z/radius/hash/窗口表项；失配回退、中心扩展或窗口收缩必须写入 state 和 reason，不能只用自然语言。",
        "Z Algorithm 对 text=\"aabcaabx\" 的标准结果是 [0,1,0,0,3,1,0,0]，特别是 z[4]=3；不要在扩展完成前 tracer.set(\"z[4]\") 写半成品。",
        "Z Algorithm 写 z[i] 前必须先完成 while 扩展；样例 i=4 先 compare text[0]/text[4]、text[1]/text[5]、text[2]/text[6]，扩展完成后再 tracer.set(\"z[4]\", value=3)。",
    ),
    "tree": (
        "保持 family_contract；记录 tree、frame:* enter/exit、current、return_values 或 aggregate。",
        "递归返回、LCA/直径/树形 DP 聚合必须用 deps 或 state 说明来自哪个子树。",
        "中序遍历/LCA 等树递归不能只有 path/result；每个 exit frame 写 return_values、return_value、subtree_return 或 aggregate，说明当前子树返回值。",
        "树形 DP 必须按后序计算 dp_take[current] 和 dp_skip[current]：dp_take[current]=weight[current]+sum(dp_skip[child])，dp_skip[current]=sum(max(dp_take[child],dp_skip[child]))，state.current 指向正在写的节点。",
        "树形 DP demo 必须显式 tracer.set(\"dp_take[current]\") 和 tracer.set(\"dp_skip[current]\")，不要只在 state 里更新 dp_take/dp_skip；dp_contract.answer_position=\"answer\" 时最终必须 tracer.set(\"answer\", role=\"answer\")。",
        "expected_nodes 覆盖必须可见：每个节点的 enter/exit/set/mark state.current 指向该节点，并且 targets/deps 尽量包含 node:<id>。",
        "LCA/树递归固定短模板：不要使用 graph_contract submode=dfs；使用 family_contract={\"family\":\"tree\",\"submode\":\"lca\"}，state 保留 tree、current、p、q、return_value 或 aggregate。",
        "LCA 第一帧必须是 initialization/create 阶段：用 tracer.create(\"tree\")，state.phase=\"initialization\"，state 保留 tree、p、q 和 family_contract。",
    ),
    "backtracking": (
        "保持 family_contract；记录 choose、enter、record、undo 以及 path/used 连续变化。",
        "撤销不能跳步；递归树或 frame 必须能解释当前分支和回退原因。",
        "choose 用 push/mark/enter 表达，record 写入 answer target，undo 用 pop/unmark/exit 表达；path/used 必须逐步回滚。",
        "permutation/backtracking 必须在 state 中保留 recursion_tree 或 search_tree；record 事件必须 role=answer，state.answer 包含新记录，deps 指向当前 path。",
        "全排列 record 事件必须 role=\"answer\"，state.answer 包含新记录，deps=[\"path\"]，reason/action 含 record 或 记录。",
        "演示帧必须包含 tracer.enter(\"frame:dfs(...)\") 选择进入帧和 tracer.exit(\"frame:dfs(...)\") 返回/撤销帧；撤销后 path/used 与上一层一致。",
        "frame id 禁止包含空格；不要用 str(path) 生成 frame:dfs([1, 2])，改用 frame:dfs(1_2) 或 frame:dfs(root)。enter 和 exit 必须使用完全相同的 frame id。",
        "每个事件都带 state={\"recursion_tree\": {\"nodes\": [...], \"edges\": [...]}, \"path\": ..., \"used\": ..., \"answer\": ..., \"family_contract\": ...}；不要只给 call_stack/path 而省略 recursion_tree。",
        "backtracking expected_events 只能用 choose、record、undo；不要使用 answer 作为 expected_events，答案帧用 role=answer 且 reason/action 含 record 或 记录。",
        "搜索树只能有一个 root；所有新分支节点都通过 edges 连接到 root 或已有 frame/choice 节点，不要每一层重新创建 root。",
        "Andrew/凸包这类 push-pop 过程若触发回溯 readiness，用 tracer.enter 进入候选/while 检查，用 tracer.exit 表达 pop/撤销完成，最终答案前 path/stack 必须回到已撤销状态。",
        "Andrew/凸包的最终答案帧必须是已清理状态：path/stack 只能等于最终 hull，不能保留 pending/current/candidate；每次 pop 后立刻 tracer.exit 表示撤销完成。",
    ),
    "array_pointer": (
        "保持 array_contract；state.array_contract 必须包含 submode，可用 binary_answer、two_pointer、sliding_window、prefix_sum、difference_array、fast_slow。",
        "二分答案 binary_answer 必须先用 tracer.create 记录 initialization 阶段，state.phase=\"initialization\"，包含 left、right、mid、answer、array_contract。",
        "二分 mid 必须来自当前窗口；compare 事件先记录 nums[mid] / target 的比较 deps，move 事件再更新 left/right，区间不能无比较证据跳变。",
        "修复 demo_state_jump 时，在跳变 step 前插入 compare 事件，compare 的 state 使用移动前的 left/right/mid。",
        "闭区间二分使用 while left <= right；每轮 mid=(left+right)//2，先 compare nums[mid] 与 target，再 move pointer:right 到 right=mid-1 或 move pointer:left 到 left=mid+1；expected_targets 包含 pointer:left、pointer:right、pointer:mid。",
        "闭区间二分 move pointer:left/right 后 state.mid 必须等于新窗口 (left+right)//2；若新区间为空则不要发布 mid 字段，不要把 mid 置为 None。",
        "每次 move pointer:left/right 前必须有 compare 事件作为证据；不要连续发布无比较依据的边界跳变。",
        "每个 pointer:left/right move 必须带 value、deps 或 before/after；value 写新指针位置，before/after 写旧窗口和新窗口，deps 指向上一帧 compare 的 nums[mid] 或 pointer:mid。",
        "demo_state_jump 的硬约束：move 的前一个事件必须是 compare，不要在 compare 和 move 之间插入 explain/set/mark；compare 的 state.left/right/mid 使用移动前窗口，二分答案写出 mid*mid <= n 的 value 或 deps。",
        "滑窗、前缀和差分必须在 expected_targets 中列出小样例关键更新；更新 prefix[i]、diff[i]、pointer:* 或 window target，不能把 nums[i] 当作更新 target；差分最终重建例外，必须 set nums[i] 作为输出数组重建。",
        "差分数组必须先按原数组初始化：diff[0]=nums[0]，diff[i]=nums[i]-nums[i-1]；每条 update=[left,right,delta] 只做 diff[left]+=delta 和 diff[right+1]-=delta，不要把结果数组值写回 diff。",
        "差分数组最终重建必须逐个 tracer.set(\"nums[i]\")，expected_targets 包含 nums[0], nums[1], nums[2]；state 保留 running_sum，deps 指向 diff[i] 或 running_sum，不要只更新 diff。",
        "快慢指针必须记录 slow、fast、下一步来源和终止条件；每次指针移动都要有 deps 或 value 证据。",
    ),
    "data_structure": (
        "保持对应 hash/sorting/heap/trie/linked_list/union_find/range_structure contract 或 state 证据。",
        "push/pop/link/unlink/union/find/build/query 等结构变化必须有 deps、value 或可复原 state；family_contract 不要写成 unsupported。",
        "节点 target 统一使用 node:<id>，不要使用 node_0/node_1 这类普通变量名；deps 中出现的 node:<id> 必须能在结构 state 中解释。",
        "堆 top-k 缺 pop 时补 expected_events=[\"push\",\"pop\"] 和 tracer.pop；并查集补 union_find.parent/rank/size；区间结构使用 range_structure、segment_tree 或 fenwick 证据。",
        "堆 TopK 每个 push/pop state 必须保留 heap_type=\"min\" 和 heap_top=heap[0]；最终答案 target/deps 使用 heap[0]。",
        "禁止生成 node:None 或 edge:None->None；Trie 根节点固定 root，新节点必须有非空 id，edge source/target 必须引用 trie.nodes 中已存在的 node:<id>。",
        "树、Trie、链表和线段树的 state.*.edges 必须使用非空端点；state.segment_tree.edges 可写成 [\"root\", \"left\"] 或 {\"from\": \"root\", \"to\": \"left\"}，from/to/source/target 不能为 None。",
        "结构查询或最终答案 mark 必须带 value=answer、deps 和 state.answer；不能发布没有 value/deps/状态变化的 mark。",
        "每个引用 node:<id> 的事件都必须在同一事件 state.segment_tree.nodes、state.trie.nodes、state.linked_list.nodes 或对应结构 nodes 中包含该 id。",
        "compare 事件必须带 deps 或 value；GCD/数学循环比较时 deps 指向 a/b 或 remainder，value 写比较/终止条件。",
    ),
    "geometry": (
        "保持 geometry / convex_hull 过程语义；Andrew/凸包 不要使用 backtracking family_contract，也不要设置 family_contract family=geometry；不要补 choose/record/undo 来绕过错误。",
        "state.geometry 必须包含 points 和 hull/stack；每个 point:<id> target 都必须能在同一事件 state.geometry.points 中找到。",
        "每个 compare/pop/answer 事件都重复完整 state.geometry.points，不要只在 create 事件写 points；point:0 对应 points[0] 或 id=\"0\" 的点。",
        "不要在 deps 使用 point:；point:p0 只能作为 target/高亮对象。compare 带 value=叉积，deps=[\"geometry\"]，避免 point deps 无法解析。",
        "固定点表写法：geometry_points=[{\"id\":\"p0\",\"x\":0,\"y\":0},...]；point targets 与 state.geometry.points 的 id 对齐，deps 固定用 geometry。",
        "中间候选只放 geometry.stack/current_point/candidate，geometry.hull 只放最终或已验证凸包；最终 hull 顺序必须和 solve/expected answer 一致，不能保留 pending/current/candidate。",
        "最终 role=answer 事件必须带 value=answer、deps 指向 hull 或 point:<id> 列表，并在 state.answer 中同步最终点集。",
        "最终答案 deps 也必须是 [\"geometry\"]；不要在 answer deps 使用 point:。",
    ),
    "unknown": (
        "先修复 schema、target、deps、state、reason 和结果一致性，再考虑算法族细节。",
        "compare 必须带 deps 或 value；不能发布无法说明比较依据的 compare。",
        "jump_game 贪心必须记录 previous_reach、candidate_reach 和 reach，reach=max(previous_reach, i+nums[i])；若 i>previous_reach 才判不可达。",
        "jump_game 中 i > previous_reach 时立即 role=\"answer\" 且 value=False，state.answer=False 后停止 trace；不要继续扫描不可达下标，也不要用不可达下标更新 reach。",
        "jump_game 初始化 create 可以用 i=-1、reach=0 表示尚未扫描；第一个扫描事件若 i=0，必须写 previous_reach=0、candidate_reach=nums[0]、reach=nums[0]。不可达样例中 state.i=2 只能出现在最终 answer=False 帧。",
    ),
}
DATA_STRUCTURE_REPAIR_GUIDANCE_BY_SUBMODE: dict[str, tuple[str, ...]] = {
    "trie_prefix": (
        "submode=trie_prefix：区分插入阶段节点累计 count / prefix_count 与 query prefix count；query 的答案 count 必须来自查询前缀路径终点节点。",
        "Trie repair 必须记录 trie nodes/edges、字符路径、terminal/is_word、prefix_count；不要把插入节点 count 机械当作所有查询的答案 count。",
        "Trie 每个字符路径步骤必须在 state 写 char/current_char，并优先用 char:<word_index>:<char_index> 或 char:prefix:<char_index> 作为 target/deps；如果用 words[i][j] 或 prefix[j]，同一事件 state.words 和 state.prefix 必须存在，同时引用当前 node:<id>。",
        "当错误点是 words[0][0] 或 prefix[0] 不存在时，不要把 words[0][0] 作为 target；改用 char:<word_index>:<char_index> 并在 state.current_char/state.words/state.prefix 中给出可见字符。",
        "Trie 的计数和终止标记应挂在 node:<id> 的 node.meta.count、node.meta.prefix_count、node.meta.pass_count、node.meta.terminal 或 state.prefix_count；不要使用孤立 count[i]、is_end[i] 这类没有容器的 target。",
        "words 包含空串时 root 必须 terminal/is_word=True，并发布 terminal 事件：可用 tracer.mark(\"node:root\")，并带 value=True、deps=[\"node:root\"]，state 中 root.meta.terminal=True。",
        "prefix_count 证据必须是可观测 state：不能只在 reason 写 count；query 前缀终点 node:<id> 的 node.meta.count/node.meta.prefix_count/pass_count 必须等于答案，答案 mark 使用 value=prefix_count、deps=[node:<id>]、state.prefix_count。",
        "Trie 创建新节点必须有显式 create_node 事件：优先 tracer.set(\"node:<id>\", role=\"create_node\", deps=[\"node:<parent>\", \"char:<word_index>:<char_index>\"], state=...)；reason/action 含 create_node/创建新节点，并同步 state.trie.nodes 和 state.trie.edges。",
        "Trie 节点路径必须可由 labels/edges 复原：root 以外 node.label 必须是单个字符，edges 用 [parent_id, child_id]；不要让所有节点 label 为空，否则会被当作根路径并要求 count=len(words)。",
        "prefix 为空时答案来自 root.meta.prefix_count=len(words)，直接 mark root；不要把 root prefix_count 写成 0。",
    ),
    "monotonic_stack": (
        "daily_temperatures/单调栈不要使用 range_structure、segment_tree、fenwick 或 sparse_table family_contract；使用 stack_order=\"decreasing\"、temperatures、stack、answer。",
        "submode=monotonic_stack/daily_temperatures：每次 pop 后必须立刻 set answer[i] 或 result[i] target。",
        "单调栈事件必须保留 temperatures、stack、当前 index/value、pop 原因、answer target、deps 和 value；不要只展示 stack 变化。",
        "tracer.pop 事件本身必须带 deps=[temperatures[popped_index], temperatures[current_index]]；随后 set answer[popped_index] 或 result[popped_index]，value=current_index-popped_index。",
    ),
    "linked_list": (
        "submode=linked_list：记录 current/prev/next 或 pointer:*；每次 link/unlink 必须改变 linked_list edges 或 next/prev，不能只给最终链。",
        "链表节点 target/deps 使用 node:<id> 和 edge:u->v；不要使用 node_0/node_1，若已有 node_0 错误需改为 node:<id> 并在 linked_list.nodes 中保留该 id。",
        "linked_list.nodes 每个节点的 meta.next 或 meta.prev 必须反映当前指针状态；事件 state 顶层也保留 current、prev、next。",
        "不要只在初始化 state 写 linked_list；每个引用 node:0/node:1 的事件都必须重复完整 state.linked_list.nodes，例如包含 {\"id\": \"0\"} 和 {\"id\": \"1\"}，node id 字符串要与 target node:0/node:1 一致。",
        "linked_list.nodes[].meta.next 与 state.linked_list.edges 必须一致：meta.next=\"1\" 时 edges 包含 [\"0\",\"1\"] 或 edge:0->1；反转后 meta.next=\"0\" 时 edges 包含 [\"1\",\"0\"] 或 edge:1->0。",
        "link_change 事件必须显式改变边：用 tracer.unlink(\"edge:current->old_next\") 表示断开旧 next，用 tracer.link(\"edge:current->prev\") 表示 current.next 指向 prev；同时更新 state.linked_list.nodes[].meta.next 和 edges。",
        "尾节点或 prev=None 时不要写 meta.next=\"\"，否则会被校验成 edge:id->；用 JSON null 或省略 next，并且 state.linked_list.edges 不要包含空端点边。",
        "链表反转每个 tracer.set 必须带 value、deps 或 before/after，或者让 state.linked_list/current/prev/next 发生真实变化；不要用空 set 只改 reason。",
        "current/prev/next 指针移动用 tracer.move(\"pointer:current\")、tracer.move(\"pointer:prev\") 或 state 变化表达；link_change 用 tracer.link/tracer.unlink，不要用无证据 set 代替。",
        "链表反转每轮先保存 next_node，再改 current.next；也可称 old_next。link_change 后 prev 必须移动到 old_current；下一轮第一帧 pointer:current 才写 next_node，不要在本轮继续发布旧 current。",
        "不要发布半更新链表状态；事件 state 表示动作后的完整一致状态。如果 meta.next 仍是 old_next，就必须保留 edge:current->old_next；如果移除了 edge:current->old_next，就必须同时把 meta.next 改为 null 或 prev。",
        "每轮 link/unlink/set 处理的 current 必须仍是 old_current；不要在完成 old_current 的 link_change 前把 current 写成 next_node。第一轮必须从 head/current=0 开始；下一轮第一帧 pointer:current 才写 next_node。",
        "tracer.move(\"pointer:current\") 是每轮开始帧，state.current 写本轮 old_current，state.next 写 next_node；每个节点只发布一次 pointer:current move。",
        "两节点扩展样例 values=[1,2]：第一轮 old_current=\"0\" 时保存 next_node=\"1\"；处理完 old_current=\"0\" 后，下一帧 current 必须是 \"1\"，prev=\"0\"，不要在下一轮 pointer:current frame 继续写 current=\"0\"。",
        "三节点样例 values=[1,2,3]：current 帧顺序必须是 \"0\" -> \"1\" -> \"2\"；处理完 old_current=\"1\" 后，下一帧 current 必须是 \"2\"，不要继续写 current=\"1\"。",
    ),
    "heap": (
        "submode=heap/topk：family_contract 使用 {\"family\":\"heap\",\"submode\":\"topk_min_heap\",\"expected_events\":[\"push\",\"pop\"]}。",
        "每个 push/pop state 都保留 heap_type=\"min\" 和 heap_top=heap[0]；最终答案 target/deps 使用 heap[0]。",
        "容量为 k 的小顶堆在 len(heap)>k 时必须 tracer.pop(\"heap\", value=removed, state={\"heap\": ..., \"heap_top\": ...})；不能只记录 push。",
    ),
    "hash_map": (
        "Two Sum 哈希固定短模板：使用 state.hash_contract={\"submode\":\"two_sum\"}，不要设置 family_contract family=hash。",
        "Two Sum 第一帧必须是 initialization/create 阶段：用 tracer.create(\"seen\")，state.phase=\"initialization\"，state.seen={}，state.hash_contract={\"submode\":\"two_sum\"}。",
        "每轮 state 保留 nums、target、i、value、need、seen；检查命中用 deps=[\"seen[need]\",\"nums[i]\"]。",
        "未命中后 set seen[value]，命中后 role=answer，answer 为两个下标。",
    ),
    "union_find": (
        "submode=union_find：family_contract 使用 {\"family\":\"union_find\",\"submode\":\"connected_components\"}，state.union_find 至少包含 parent 以及 rank 或 size。",
        "每次 union 记录 find 到的 root、i/j、parent 更新，target 用 union_find 或 node:<root>，reason 说明是否合并或已连通。",
        "deps 不要写无法渲染的 union_find.parent[0]；deps 改用 node:0、node:1 或 union_find，并在 state.union_find.parent 中保留 parent 映射。",
    ),
    "range_query": (
        "submode=range_query：family_contract 可用 {\"family\":\"range_structure\",\"submode\":\"segment_tree\"} 或 {\"family\":\"data_structure\",\"submode\":\"fenwick_tree\"}，不能停在未支持 family。",
        "segment_tree/fenwick 超时后必须用短模板：1 个 variant、6-10 个 events、tracker_code 少于 80 行，只展示 build、一次 query、一次 update、answer。",
        "submode=range_query：segment tree / sparse table 必须记录 build/query 的节点区间、来源子节点或重叠区间、answer target 和 deps。",
        "Segment tree 若 family_contract.expected_events 包含 update，必须有 reason/action 含 update/更新的 set 事件，更新叶子到根路径上的 sum/value。",
        "Segment tree 查询或答案 mark 必须带 value=answer、deps 指向覆盖区间节点或子节点，state.answer 同步；不能发布没有 value/deps/状态变化的 mark。",
        "Segment tree 的 state.segment_tree.edges 必须是端点非空的边，例如 [\"root\", \"left\"] 或 {\"from\": \"root\", \"to\": \"left\"}；每条 edge 的两个端点都必须出现在 state.segment_tree.nodes。",
        "Segment tree state 使用 segment_tree.nodes[].meta.{l,r,sum/value}；Fenwick state 使用 bit 或 fenwick 并记录 lowbit、update/query 索引。",
        "线段树 update 后必须沿叶子到 root 同步 sum/value；state.segment_tree.nodes[].meta.sum 必须等于当前 state.nums 区间和，不要只更新叶子或 answer，父区间和 root 必须同步。",
        "Sparse table build 必须逐个 set st[k][i]，deps 指向 st[k-1][i] 与 st[k-1][i+2^(k-1)]；query 必须记录两个重叠区间和最终 answer target。",
        "Sparse table 数值必须按 st[0][i]=nums[i]、st[k][i] = min(st[k-1][i], st[k-1][i+2^(k-1)]) 生成完整正确的 st；不要把未计算项写成错误数值。",
        "Sparse table state 必须包含完整正确 st 表；st[0]=nums，st[k][i]=min(st[k-1][i], st[k-1][i+2^(k-1)])。nums=[5,2,7,3,6,1] 时 st[1]=[2,2,3,3,1]，st[2]=[2,2,1]。",
        "Sparse table target/deps 只能引用当前 state.st 中真实存在的单元；不要引用不存在的 st[2][1]。nums=[5,2,7,3,6,1] 时 st[2] 只有 st[2][0]、st[2][1]、st[2][2]；如果 state.st[2] 长度不足 2，就不能把 st[2][1] 放进 target/deps，必须先在 create state 写完整 st。",
        "Sparse table 超时必须用紧凑固定模板：tracker_code 少于 80 行，只保留 create st、query 两个区间、answer；不要逐格展开所有 st build 事件，create state 写完整 st。",
    ),
}
DP_REPAIR_GUIDANCE_BY_SUBMODE: dict[str, tuple[str, ...]] = {
    "knapsack_01": (
        "submode=knapsack_01：0-1 背包 capacity_index 必须倒序扫描，避免同一物品重复使用。",
        "每个 set dp[capacity_index] 事件 state 必须包含 i、capacity_index/capacity、weight/item、old_value、candidate、formula 和 dp_contract。",
        "deps 指向更新前的 dp[capacity_index]、来源 dp[capacity_index-weight] 与 weights[i]/values[i]；最终 role=answer 引用 dp[capacity]。",
        "subset-sum 每个 DP 事件 state 保留 nums、target 和当前 nums[i]；deps=[\"dp[c]\",\"dp[c-weight]\",\"nums[i]\"]，reason/teaching 提到 nums 时 targets/deps/state 必须有 nums 依据。",
    ),
    "bounded_knapsack": (
        "submode=bounded_knapsack：state 必须包含 i、capacity_index/capacity、count 或 quantity/数量上限、candidate 和 formula。",
        "多重背包要说明使用第 i 个物品 t 次，deps 指向 dp[capacity_index-t*weight]、weights[i]、values[i] 和 counts[i]。",
        "关键更新缺 deps 时不要只补 reason；每个 set dp 事件必须能按 state 重算 value。",
        "可以展示同一容量的增量 candidate，但 state 必须写 old_value、take 和 candidate；该物品处理完成后最终 dp[capacity_index] 必须等于最大值，最终答案必须是 dp[capacity]。",
        "所有事件 reason 非空，create/set/compare/mark 都写简短原因，不能用空字符串。",
    ),
    "complete_knapsack": (
        "submode=complete_knapsack：小规模样例必须逐个 set dp[j]；state 包含 item/coin、capacity/j、old_value、candidate、formula、answer_position。",
        "零钱兑换完全背包使用 j 从 coin 到 amount 正序；formula 写 dp[j] = min(dp[j], dp[j-coin] + 1)，candidate=dp[j-coin]+1，old_value 是更新前 dp[j]。",
        "校验按 state.i 使用 coins[:i+1] 重新计算期望；内部 inf=amount+1，unreachable 在展示 state.dp 中可写 -1，但 target dp[j] 必须等于用当前 coins[:i+1] 得到的最少硬币数。",
        "每个 set dp 事件都必须提供 state.formula 或 teaching.formula；最终答案若用 set 也写 formula=answer=dp[amount]，否则用 mark dp[amount] role=answer。",
    ),
    "lcs": (
        "submode=lcs：使用 dp_contract.subfamily=\"lcs\"，二维表 dp[i][j] 表示 text1 前 i 个字符与 text2 前 j 个字符的 LCS 长度。",
        "LCS base row/column 的 0 值只放在 tracer.create(\"dp\") 的 state.dp；不要把 dp[0][j] 或 dp[i][0] 放进 dp_contract.expected_targets，除非真的逐格 tracer.set。",
        "LCS expected_targets 只列真实 tracer.set 的 dp[i][j] 和最终答案 dp[len(text1)][len(text2)]，不要列只由初始化 create 覆盖的 base cell。",
        "LCS 每个 tracer.set(\"dp[i][j]\") 的 state 必须包含 text1、text2、i、j、current、old_value、formula 和 dp_contract。",
        "LCS deps=[\"dp[i-1][j]\", \"dp[i][j-1]\", \"dp[i-1][j-1]\", \"text1[i-1]\", \"text2[j-1]\"]，匹配时 formula 写 dp[i][j]=dp[i-1][j-1]+1，否则写 max(dp[i-1][j], dp[i][j-1])。",
        "LCS 最终答案事件 role=answer，target/deps 引用 dp[len(text1)][len(text2)] 或 answer_position 指向的真实 dp 单元。",
    ),
    "state_compression": (
        "submode=state_compression：记录 mask、last/city、transition source、candidate、dp[mask][last]；deps 指向来源 dp 和边/代价。",
        "状态压缩 DP 每个转移必须写 formula，例如 dp[next_mask][next] = min(dp[next_mask][next], dp[mask][last] + cost[last][next])；expected_targets 中的小规模 dp[mask][last] 不能省略。",
        "TSP 状态压缩 repair 不要输出完整指数级跟踪；短 tracker_code 只保留起点 base、少量转移和最终 ans，避免再次输出 16000 tokens 后截断。",
    ),
    "digit_dp": (
        "submode=digit_dp：记录 pos、tight/limit、started、forbidden digit、memo key、count 转移和 answer_position。",
        "数位 DP repair 必须返回顶层 JSON object，不要把整个 JSON object 当字符串返回；expected_targets 只列实际 set 的 dp 项和 ans。",
        "数位 DP tracker_code 少于 80 行，只保留 create dp、set dp[1]、set dp[2]、set ans 四类关键事件；不要写通用长递归或大枚举，不要使用九进制转换法。",
        "对 n=20 / 不包含数字 7 示例，前缀计数必须是 dp[0]=1、dp[1]=2、dp[2]=18，最终调用 tracer.set(\"ans\")，完整写法为 tracer.set(\"ans\", value=18, deps=[\"dp[2]\"], role=\"answer\")。",
    ),
}
GRAPH_REPAIR_GUIDANCE_BY_SUBMODE: dict[str, tuple[str, ...]] = {
    "bfs": (
        "submode=bfs：记录 queue/frontier、dist/visited、parent；首次访问必须绑定来源 edge:u->v，queue 变化不能跳变。",
        "BFS first_visit 必须用 tracer.set(\"dist[neighbor]\")，完整写法为 tracer.set(\"dist[neighbor]\", value=dist[current]+1, role=\"visited\", deps=[\"node:current\", \"node:neighbor\", \"edge:current->neighbor\"])；state 必须满足 parent[neighbor]=current、dist[neighbor]=dist[current]+1；不要只写 deps=[\"dist[current]\", \"edge:current->neighbor\"]，不要写 parent[neighbor]=neighbor。",
    ),
    "connected_components": (
        "submode=connected_components：state 保留 graph、visited、component、components；不要用只有最终 components 的静态帧。",
        "state.component 只能是当前正在遍历的连通分量；不要把多个 component 合并进 state.component。已完成分量放 state.components；样例 A-B 和 C 必须分成 ['A','B'] 与 ['C']。",
        "state.components 的每个内层列表也必须是一个连通分量；不要发布 [['A','B','C']] 或把孤立点 C 合并进 ['A','B']。",
        "处理样例 A-B + C 时，完成第一块后 state.components=[['A','B']]；开始遍历 C 时重置 state.component=['C']，最终答案才是 components=[['A','B'], ['C']]。",
        "若沿用 DFS contract，必须记录 stack 或 frame:dfs(u) enter/exit frontier，每条递归边 deps 包含 edge:u->v。",
    ),
    "dfs": (
        "submode=dfs：记录 stack 或 frame:dfs(u) enter/exit、visited、parent；每条递归边用 edge:u->v 和 deps 说明来源。",
        "每个 DFS repair 事件 state 至少包含 stack 或 frames；enter/exit target 使用 frame:dfs(u)，不要只保留 visited/components。",
    ),
    "bipartite_matching": (
        "二分图匹配不要设置 graph_contract submode=dfs；若必须设置，则每个事件都要有 stack 或 frame:dfs enter/exit。",
        "不要使用裸 frame:dfs；若使用递归帧，frame id 必须带节点，例如 frame:dfs(L1)。每个 tracer.exit 的 target 必须和之前 tracer.enter 完全相同，不能 exit 未进入的 frame；简单匹配过程建议不用 enter/exit。",
        "增广成功时同步 match[left]=right 和 match[right]=left，state 保留 graph、left_nodes、right_nodes、match、visited、augmenting_path。",
        "重新匹配时旧反向边必须同步清理：样例中若 L1 从 R1 改到 R2，旧 match[R1]=L1 必须清除或改为 match[R1]=L2，不能保留不一致双向 match。",
    ),
    "bipartite_coloring": (
        "submode=bipartite_coloring：记录 color、queue/frontier、冲突检查；每次给 v 染色必须依赖 edge:u->v 和 color[u]。",
        "二分图染色不要使用 dist 表示颜色，也不要设置 graph_contract submode=bfs；state 用 color 字典，graph_contract 固定 submode=bipartite_coloring。",
    ),
    "dijkstra": (
        "submode=dijkstra：记录 heap/frontier 的 pop/push；每条关键 relax 使用 edge:u->v 和 dist[v] target。",
        "Dijkstra relax 事件 state 必须包含 old_dist、new_dist、edge_weight、parent/predecessor，deps 指向 dist[u] 与 edge:u->v。",
        "Dijkstra relax 必须用 tracer.set(\"dist[v]\")，deps=[\"node:u\", \"node:v\", \"edge:u->v\", \"dist[u]\"]；state.current/neighbor、old_dist/new_dist/edge_weight 都必须存在。",
    ),
    "bellman_ford": (
        "submode=bellman_ford：按轮次记录每条 edge:u->v relax；state 包含 iteration、old_dist、new_dist、edge_weight、parent。",
        "Bellman-Ford 固定短模板：state.graph.nodes 和 state.graph.edges 必须存在；每个 relax/check 事件都重复完整 state.graph，确保 node:A、edge:A->B 可见。",
    ),
    "floyd_warshall": (
        "submode=floyd_warshall：逐步记录 k/i/j、dist[i][j]、old_dist、new_dist、via；deps 指向 dist[i][k] 和 dist[k][j]。",
    ),
    "zero_one_bfs": (
        "submode=zero_one_bfs：记录 deque/frontier、0/1 权边、push_front/push_back 原因、old_dist/new_dist 和 parent。",
        "0-1 BFS 每条边先 check_edge/compare edge:u->v；first_visit 或 relax 必须用 tracer.set(\"dist[v]\")，deps=[\"node:u\", \"node:v\", \"edge:u->v\"]，state 保留 dist[u]、old_dist、new_dist、edge_weight 和 parent[v]=u。",
        "0-1 BFS 权重为 0 时 push_front，权重为 1 时 push_back；push_front/push_back 事件也带 deps=[\"node:u\", \"node:v\", \"edge:u->v\"]，reason 写 edge_weight=0/1 的队首/队尾依据。",
    ),
    "topological_sort": (
        "submode=topological_sort：记录 indegree 初值、每条 edge:u->v 使 indegree[v] 递减、indegree 为 0 入队原因和 topo_order。",
        "拓扑排序每次 repair 都必须保持短 tracker_code：6-10 个 events，不要重写成长篇 tracker；按 create graph/indegree、pop queue、decrement indegree、push zero indegree、mark topo_order 的顺序展示。",
        "拓扑排序 trace 结束必须调用 tracer.result(topo_order) 再 return tracer.to_trace()，保证 trace.result 与 solve(input_data) 完全一致。",
        "拓扑排序 repair 若上轮 JSON 为空或截断，重写为 1 个 variant、6-10 个 events、短 tracker_code：create graph/indegree、pop queue、decrement indegree、push zero indegree、mark topo_order。",
    ),
    "mst": (
        "submode=mst/Kruskal：记录 sorted_edges/edge_order、每条边 select/skip 原因、mst_edges。",
        "Kruskal 必须同步 state.union_find，至少包含 union_find.parent 以及 rank 或 size，用 find/union 证据说明是否成环。",
    ),
    "tarjan": (
        "submode=tarjan：记录 dfn、low、stack、on_stack；树边和返祖边都要说明 low 更新来源。",
        "Tarjan 在 low[u]==dfn[u] 时必须记录 component 弹栈事件，state.component 显示本次 SCC 节点。",
        "Tarjan 割点桥固定短模板：DFS 首次访问节点必须 tracer.set(\"dfn[u]\") 再 tracer.set(\"low[u]\")；dfn 写入事件和 low 写入事件必须显式存在。",
        "Tarjan 第一帧必须是 initialization/create 阶段：用 tracer.create(\"graph\")，state.phase=\"initialization\"，并给出 dfn/low/parent/stack/on_stack 初始化。",
        "component 弹栈事件必须有 state.component，并且 component 节点已从 stack 移除；不能让 component 中的节点仍留在 state.stack。",
        "Tarjan 割点桥所有事件 reason 非空；create/set/compare/mark/enter/exit 和 dfn/low/bridge/articulation/component 事件都写简短 reason。",
        "割点/桥最终 answer 事件 target/deps 使用 answer 或 graph，state.articulation 和 state.bridges 保存结果；不要使用 node:articulation 或 node:bridges，也不要把 articulation/bridges 当作图节点或边端点。",
    ),
    "network_flow": (
        "submode=network_flow/Edmonds-Karp：记录 BFS parent、augmenting_path、bottleneck、capacity/cap、flow 和 residual。",
        "每条增广边必须 tracer.set(\"flow[u->v]\", value=new_flow, deps=[\"edge:u->v\", \"cap[u->v]\", \"bottleneck\"], state={\"capacity\": ..., \"flow\": ..., \"augmenting_path\": ..., \"bottleneck\": ...})。",
        "flow 更新的 before/after 只有能与上一帧严格对齐时才保留；不确定时用 value、state.flow 和 reason 表达变化。",
        "每个发布出来的 state.flow 都必须满足中间节点流守恒；对一条增广路径，先计算整条增广路径更新后的 flow，再写入事件 state，不要发布只更新单边的中间状态。",
        "state.flow 只保存原始容量边上的非负流量；反向残量边不要写进 flow，必须放在 residual 或 residual_capacity 中。",
    ),
    "unsupported": (
        "不要使用 directed 这类泛化 graph_contract submode；必须改成 bfs、dfs、dijkstra、topological_sort、mst、tarjan、network_flow 等可校验 submode。",
    ),
}
CATEGORY_REPAIR_GUIDANCE: dict[str, str] = {
    "answer_correctness": "修复 solve、trace.result、verify 和 expected 的一致性；不要只改 trace.result。",
    "trace_schema": "修复 semantic-trace-v1 顶层和事件字段，使用 Tracer(input_data, algorithm=..., pseudocode=...) 生成 op/targets/state/code_line。",
    "trace_step_jump": "补齐缺失中间状态或解释跳变原因，关键过程不能直接从初始化跳到答案。",
    "target_or_deps": "修复 targets/deps，使其指向 state 中可渲染、可解析的真实对象；禁止旧字段 target、裸字符串 targets 和旧式 map target。",
    "process_invariant": "修复算法过程和不变量；指定 step 的 state、deps、value 必须与算法转移一致。",
    "coverage": "补齐关键步骤覆盖；小输入必须记录初始化、主循环、关键转移/访问和答案。",
    "demo_readiness": "补齐 reason、state、deps、阶段和教学证据，让页面能讲清当前步骤。",
    "scene_binding": "修复 state/targets/marks，使 SceneGraph 能绑定可见对象。",
    "execution": "修复 Python 执行错误、超时或死循环，优先用有界标准模板；Tracer 必须以 Tracer(input_data, algorithm=..., pseudocode=...) 初始化。",
    "generation": "返回完整 JSON，保持题目语义和已有正确部分，只修失败原因。",
}


def build_repair_context(
    errors: list[str],
    *,
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    family_hint = infer_repair_family(errors=errors, request=request, previous=previous)
    graph_submode_hint = infer_graph_repair_submode(errors=errors, request=request, previous=previous)
    data_structure_submode_hint = infer_data_structure_repair_submode(errors=errors, request=request, previous=previous)
    dp_submode_hint = infer_dp_repair_submode(errors=errors, request=request, previous=previous)
    return [
        classify_repair_error(
            error,
            family_hint=family_hint,
            graph_submode_hint=graph_submode_hint,
            data_structure_submode_hint=data_structure_submode_hint,
            dp_submode_hint=dp_submode_hint,
        )
        for error in errors
    ]


def classify_repair_error(
    message: str,
    *,
    family_hint: str | None = None,
    graph_submode_hint: str | None = None,
    data_structure_submode_hint: str | None = None,
    dp_submode_hint: str | None = None,
) -> dict[str, Any]:
    failure_type = repair_failure_type(message)
    repair_category = repair_category_for_message(message, failure_type)
    family = family_hint or infer_repair_family(errors=[message])
    graph_submode = _graph_repair_submode_for_text(message) or graph_submode_hint or ""
    data_structure_submode = _data_structure_repair_submode_for_text(message) or data_structure_submode_hint or ""
    dp_submode = _dp_repair_submode_for_text(message) or dp_submode_hint or ""
    family_guidance = list(FAMILY_REPAIR_GUIDANCE.get(family, FAMILY_REPAIR_GUIDANCE["unknown"]))
    if _is_bitmask_subsets_text(message):
        family_guidance.extend(BITMASK_SUBSETS_REPAIR_GUIDANCE)
    if family == "graph":
        family_guidance.extend(GRAPH_REPAIR_GUIDANCE_BY_SUBMODE.get(graph_submode, ()))
    if family == "data_structure":
        family_guidance.extend(DATA_STRUCTURE_REPAIR_GUIDANCE_BY_SUBMODE.get(data_structure_submode, ()))
    if family == "dynamic_programming":
        family_guidance.extend(DP_REPAIR_GUIDANCE_BY_SUBMODE.get(dp_submode, ()))
    return {
        "failure_type": failure_type,
        "repair_category": repair_category,
        "repair_instruction": _repair_instruction_for_message(message, repair_category),
        "family": family,
        "graph_submode": graph_submode if family == "graph" else "",
        "data_structure_submode": data_structure_submode if family == "data_structure" else "",
        "dp_submode": dp_submode if family == "dynamic_programming" else "",
        "family_guidance": family_guidance,
        "forbidden_actions": list(FORBIDDEN_REPAIR_ACTIONS),
        "step": _extract_step(message),
        "target": _extract_target(message),
        "message": message,
    }


def repair_failure_type(message: str) -> str:
    text = message.lower()
    if _is_tracer_api_execution_error(text):
        return "execution_error"
    explicit = _explicit_failure_type(text)
    if explicit:
        return _normalize_failure_type(explicit)
    if _is_pydantic_target_error(text, message):
        return "target_error"
    if _is_pydantic_schema_error(text):
        return "schema_error"
    if any(token in text for token in ("validationerror", "semantictrace", "schema", "field required")):
        return "schema_error"
    if "旧式 map target" in message or "target" in text or "引用了不存在" in message or "deps 未出现在 state" in message:
        return "target_error"
    process_type = process_failure_type_for_message(message)
    if process_type == "coverage_error":
        return "coverage_error"
    if process_type in {"process_invariant", "process_fallback", "process_uncovered"}:
        return "process_error"
    if "scene" in text or "layout" in text or "渲染" in message or "可见对象" in message or "帧" in message:
        return "scene_error"
    if "执行失败" in message or "sandbox" in text or "nameerror" in text or "syntaxerror" in text:
        return "execution_error"
    if "expected" in text or "verifier" in text or "结果" in message:
        return "correctness_error"
    return "generation_error"


def _is_tracer_api_execution_error(text: str) -> bool:
    return any(
        token in text
        for token in (
            "tracer.__init__",
            "missing 1 required positional argument: 'input_data'",
            "object has no attribute 'choose'",
            "has no attribute 'choose'",
            "tracer.compare()",
            "missing 1 required positional argument: 'targets'",
            "tracer.link() takes 2 positional arguments",
            "tracer.to_trace() got an unexpected keyword argument 'result'",
            "tracer._add() got an unexpected keyword argument 'stage'",
            "tracer._add() got an unexpected keyword argument 'action'",
            "tracer._add",
            "unhashable type: 'list'",
        )
    )


def _is_pydantic_schema_error(text: str) -> bool:
    return any(
        token in text
        for token in (
            "validationerror",
            "field required",
            "semantictrace",
            "extra_forbidden",
            "model_type",
        )
    )


def _is_pydantic_target_error(text: str, message: str) -> bool:
    if "targets" in text and ".id" in text and "input should be a valid string" in text:
        return True
    if "input should be a valid dictionary or instance of targetref" in text:
        return True
    if "model_type" in text and ("targetref" in text or "targets" in text):
        return True
    if "extra_forbidden" in text and re.search(r"(?:^|[\s.\[])[\"']?target[\"']?(?:$|[\s.\]])", message, re.IGNORECASE):
        return True
    return False


def _repair_instruction_for_message(message: str, repair_category: str) -> str:
    text = message.lower()
    instruction = CATEGORY_REPAIR_GUIDANCE.get(repair_category, CATEGORY_REPAIR_GUIDANCE["generation"])
    extras: list[str] = []
    if _is_json_generation_failure(text, message):
        extras.append(
            "JSON 解析失败或空内容时必须进入紧凑修复：只返回 1 个 variant、6-10 个 events、短 tracker_code、短 reason、短 pseudocode；不要复制长代码，不要输出 16000 tokens，必要时用 max_events 限制。TSP、拓扑排序等容易写长的 tracker 只保留初始化、少量关键转移和答案帧。"
        )
    if "demo_missing_reason" in text or "缺少 reason" in message:
        extras.append("所有事件 reason 非空，create/set/compare/mark 都写简短原因，不能用空字符串。")
    if ("tarjan" in text or "Tarjan" in message) and ("demo_missing_reason" in text or "缺少 reason" in message):
        extras.append(
            "Tarjan 割点桥所有事件 reason 非空；create/set/compare/mark/enter/exit 和 dfn/low/bridge/articulation/component 事件都写简短 reason。"
        )
    if "timeout" in text or "超过 600 秒" in message or "llm benchmark 超过" in text:
        extras.append(
            "LLM 超时时必须进入紧凑修复：只返回 1 个 variant，tracker_code 少于 80 行，不要写通用长递归或大枚举。数位 DP 只保留 create dp、set dp[1]、set dp[2]、set ans。"
        )
        if "sparse_table" in text or "稀疏表" in message or "st表" in text:
            extras.append(
                "Sparse table 超时必须用紧凑固定模板：tracker_code 少于 80 行，只保留 create st、query 两个区间、answer；不要逐格展开所有 st build 事件，create state 写完整 st。"
            )
    if repair_category == "trace_schema" and _is_pydantic_schema_error(text):
        extras.append(
            "遇到 Pydantic Field required、model_type 或 extra_forbidden 时，整体重写 tracker 为 Tracer API；保留 input_data，事件只用 op/targets。"
        )
    if "targets" in text and ".id" in text and "input should be a valid string" in text:
        extras.append(
            'TargetRef.id 必须是字符串；不要把多个 target 塞进同一个 id，例如不要写 {"id": ["pointer:left", "pointer:right"]}。多 target 事件必须写成 {"id": "pointer:left"}、{"id": "pointer:right"} 两个对象；Tracer API 中 create/set/move/mark/link/push/pop 只传单个字符串，compare 才传字符串列表。'
        )
    if repair_category == "target_or_deps":
        extras.append(
            'targets/deps 由 Tracer 接受字符串 id 后生成 {"id": ...}；不要手写裸字符串 targets/deps、旧字段 target 或旧式 seen:2/dist:A。'
        )
        if "不存在的索引 target" in message or "引用了不存在" in message:
            extras.append(
                "修复不存在的索引 target：输入数组只读时不要把 nums[i] 当作更新 target；不要把 result[i] 当 target，不要把 res[i] 当 target，除非 state 中先创建 result/res/answer 容器并逐步 set。回溯使用 recursion_tree、frame:*、path、used、answer；位掩码子集用 mask/subset/answer 或 subsets 容器。"
            )
            if _is_bitmask_subsets_text(message):
                extras.extend(BITMASK_SUBSETS_REPAIR_GUIDANCE)
            if "words[" in message or "prefix[" in message:
                extras.append(
                    "Trie 字符 target 报不存在时，不要把 words[0][0] 作为 target；优先改用 char:<word_index>:<char_index> 或 char:prefix:<char_index>，并在同一事件 state.current_char、state.words、state.prefix 中给出可见字符。"
                )
        if "map target" in text or re.search(r"\[[\"'][^\"']+[\"']\]", message):
            extras.append("map target 的 key 不写 Python 引号：使用 indegree[A]、dist[B]，不要写 indegree['A'] 或 dist[\"B\"]。")
    if "target 含空格" in message or "frame:dfs([" in message:
        extras.append(
            "frame id 禁止包含空格；不要用 str(path) 生成 frame:dfs([1, 2])，改用 frame:dfs(1_2) 或 frame:dfs(root)。enter 和 exit 必须使用完全相同的 frame id。"
        )
    if "缺少 initialization 阶段" in message and ("深度优先搜索" in message or "LCA" in message or "lca" in text):
        extras.append(
            "LCA 第一帧必须是 initialization/create 阶段：用 tracer.create(\"tree\")，state.phase=\"initialization\"，state 保留 tree、p、q 和 family_contract。"
        )
    if "稀疏表" in message or "ST表" in message or "sparse_table" in text:
        extras.append(
            "Sparse table state 必须包含完整正确 st 表；st[0]=nums，st[k][i]=min(st[k-1][i], st[k-1][i+2^(k-1)])。nums=[5,2,7,3,6,1] 时 st[1]=[2,2,3,3,1]，st[2]=[2,2,1]。"
        )
    if repair_category == "execution":
        extras.append(
            "Tracer 公开 API 中没有 to_trace(result=...)，必须先调用 tracer.result(answer)，最后无参数 return tracer.to_trace()。不要调用 tracer._add，也不要传 stage= 或 action=；阶段/动作信息写入 state['phase']、reason 或 teaching。"
        )
        if "tracer.__init__" in text or "missing 1 required positional argument: 'input_data'" in text:
            extras.append("把 Tracer() 或 Tracer.__init__ 错误改为 Tracer(input_data, algorithm=..., pseudocode=...)。")
        if "tracer.__init__" in text and "unexpected keyword argument" in text:
            extras.append("family_contract、dp_contract、graph_contract、array_contract 不能传给 Tracer.__init__；只能放进每个事件的 state。Tracer 初始化固定写 Tracer(input_data, algorithm=..., pseudocode=...)。")
        if "choose" in text:
            extras.append("不存在 tracer.choose()；回溯选择用 push、mark、enter 表达，撤销用 pop、unmark、exit 表达。")
        if "tracer.compare()" in text or "missing 1 required positional argument: 'targets'" in text:
            extras.append('Tracer.compare 必须写成 tracer.compare(["text[0]", "pattern[0]"], deps=[...], state={...}, reason="...")，第一个参数是 targets 列表。')
        if "tracer.link() takes 2 positional arguments" in text:
            extras.append('Tracer.link 只接受一个 target 位置参数；把来源节点放入 deps，例如 tracer.link("edge:L1->R1", deps=["node:L1", "node:R1"], state={...}, reason="...")。')
        if "unhashable type: 'list'" in text:
            extras.append("不要把 list 当作 dict key 或 set 元素；使用 tuple、索引字符串或可哈希节点 id。")
        if "nameerror" in text and "next" in text:
            extras.append("链表反转中不要使用未定义的 next；Python 内置 next 不是链表变量。先写 nxt = current['next'] / current.next 或 next_node = current['next'] / current.next，再改指针；不要写 current = next，必须让 while 循环每轮 current = next_node 单调推进。")
    if extras:
        return " ".join([instruction, *extras])
    return instruction


def _is_json_generation_failure(text: str, message: str) -> bool:
    return any(
        token in text
        for token in (
            "llmjsonerror",
            "jsondecodeerror",
            "unterminated string",
            "not a valid json",
            "not legal json",
            "顶层输出必须是 json object",
            "actual为 str",
            "truncated",
        )
    ) or any(
        token in message
        for token in (
            "模型返回内容不是合法 JSON",
            "模型返回空内容",
            "不是合法 JSON",
            "顶层输出必须是 JSON object",
            "实际为 str",
            "空内容",
            "截断",
        )
    )


def _is_bitmask_subsets_text(text: str) -> bool:
    value = text.lower().replace("-", "_").replace(" ", "_")
    return any(
        token in value
        for token in (
            "bitmask_subsets",
            "bitmask_subset",
            "subsets",
            "位掩码",
            "二进制掩码",
            "掩码枚举",
            "所有子集",
            "子集枚举",
        )
    )


def repair_failure_types(messages: list[str]) -> list[str]:
    result: list[str] = []
    for message in messages:
        failure_type = repair_failure_type(message)
        if failure_type not in result:
            result.append(failure_type)
    return result


def summarize_repair_failure_types(results: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        for failure_type in item.get("repair_failure_types") or []:
            if not isinstance(failure_type, str) or not failure_type:
                continue
            summary[failure_type] = summary.get(failure_type, 0) + 1
    return summary


def _explicit_failure_type(text: str) -> str:
    marker = "failure_type="
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    value = []
    for char in tail:
        if char.islower() or char == "_":
            value.append(char)
        else:
            break
    return "".join(value)


def _normalize_failure_type(value: str) -> str:
    if value == "process_invariant":
        return "process_error"
    if value in {"coverage_error", "schema_error", "target_error", "process_error", "scene_error"}:
        return value
    if value in DEMO_FAILURE_TYPES:
        return value
    return value or "generation_error"


def repair_category_for_message(message: str, failure_type: str | None = None) -> str:
    text = message.lower()
    failure = failure_type or repair_failure_type(message)
    if failure in DEMO_FAILURE_TYPES or "demo readiness" in text or "演示" in message:
        return "demo_readiness"
    if "跳步" in message or "跳变" in message or "state_jump" in text:
        return "trace_step_jump"
    if failure == "coverage_error":
        return "coverage"
    if failure == "schema_error":
        return "trace_schema"
    if failure == "target_error" or "deps" in text or "依赖" in message:
        return "target_or_deps"
    if failure in {"process_error", "process_invariant"}:
        return "process_invariant"
    if failure == "scene_error":
        return "scene_binding"
    if failure in {"execution_error", "timeout"}:
        return "execution"
    if failure in {"correctness_error", "answer_mismatch", "trace_result_mismatch"}:
        return "answer_correctness"
    if "expected" in text or "verifier" in text or "结果" in message or "trace.result" in text:
        return "answer_correctness"
    return "generation"


def infer_repair_family(
    *,
    errors: list[str],
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    if request is not None:
        parts.extend([request.problem, request.strategy_hint or ""])
    if previous is not None:
        parts.append(json.dumps(previous, ensure_ascii=False))
    parts.extend(errors)
    text = "\n".join(parts).lower()
    if any(token in text for token in ("digit_dp", "数位", "不含 7", "不含7", "不包含数字 7", "不包含数字7", "逐位处理", "forbidden digit")):
        return "dynamic_programming"
    if any(token in text for token in ("convex_hull", "convex hull", "andrew", "凸包", "单调链", "geometry", "叉积", "orientation")):
        return "geometry"
    if any(token in text for token in ("sparse_table", "segment_tree", "range_min", "range_sum", "稀疏表", "线段树")):
        return "data_structure"
    if any(token in text for token in ("trie", "prefix_count", "is_end", "前缀树", "字典树")):
        return "data_structure"
    if any(token in text for token in ("monotonic_stack", "daily_temperatures", "单调栈")):
        return "data_structure"
    if any(token in text for token in ("linked_list", "reverse_linked_list", "链表", "迭代反转", "反转法")):
        return "data_structure"
    if any(token in text for token in ("bipartite_matching", "二分图匹配", "匈牙利", "增广路", "matching", "match[")):
        return "graph"
    if any(token in text for token in ("lca", "最近公共祖先", "后序遍历", "中序遍历", "树递归", "lowest common ancestor")):
        return "tree"
    family_patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("dynamic_programming", ("dp", "动态规划", "不同路径", "背包", "lcs", "编辑距离", "状态压缩", "数位")),
        ("graph", ("graph", "图", "bfs", "dfs", "dijkstra", "bellman", "floyd", "拓扑", "mst", "kruskal", "tarjan", "network_flow", "网络流", "匈牙利", "增广路", "matching")),
        ("string", ("string", "字符串", "kmp", "rabin", "z algorithm", "manacher", "pattern", "text")),
        ("backtracking", ("backtracking", "回溯", "全排列", "permutation", "choose", "undo", "path", "used")),
        ("geometry", ("convex_hull", "convex hull", "andrew", "凸包", "单调链", "geometry", "叉积", "orientation")),
        ("tree", ("tree", "二叉树", "树", "bst", "lca", "frame:dfs", "子树")),
        ("array_pointer", ("array_contract", "二分", "滑动窗口", "双指针", "前缀", "差分", "快慢指针")),
        (
            "data_structure",
            (
                "hash_contract",
                "sorting_contract",
                "heap",
                "trie",
                "linked_list",
                "union_find",
                "monotonic_stack",
                "daily_temperatures",
                "prefix_count",
                "is_end",
                "哈希",
                "堆",
                "链表",
                "迭代反转",
                "反转法",
                "并查集",
                "单调栈",
            ),
        ),
    )
    for family, tokens in family_patterns:
        if any(token in text for token in tokens):
            return family
    return "unknown"


def infer_data_structure_repair_submode(
    *,
    errors: list[str],
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    if request is not None:
        parts.extend([request.problem, request.strategy_hint or ""])
    if previous is not None:
        parts.append(json.dumps(previous, ensure_ascii=False))
    parts.extend(errors)
    return _data_structure_repair_submode_for_text("\n".join(parts))


def _data_structure_repair_submode_for_text(text: str) -> str:
    value = text.lower().replace("-", "_").replace(" ", "_")
    patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("hash_map", ("two_sum", "two sum", "hash_contract", "family：hash", "family:hash", "family=hash", "哈希表", "两数之和")),
        ("trie_prefix", ("trie_prefix", "prefix_count", "prefix count", "trie", "前缀树", "字典树", "is_end", "count[")),
        ("monotonic_stack", ("monotonic_stack", "daily_temperatures", "单调栈", "temperatures")),
        ("heap", ("heap", "topk", "topk_min_heap", "小顶堆", "大顶堆", "kth_largest")),
        ("union_find", ("union_find", "dsu", "并查集", "provinces")),
        ("linked_list", ("linked_list", "reverse_linked_list", "链表", "next/prev", "迭代反转", "反转法")),
        (
            "range_query",
            (
                "data_structure",
                "range_structure",
                "segment_tree",
                "fenwick_tree",
                "fenwick",
                "bit",
                "sparse_table",
                "range_sum",
                "range_min",
                "线段树",
                "树状数组",
                "稀疏表",
                "st表",
            ),
        ),
    )
    for submode, tokens in patterns:
        if any(token in value for token in tokens):
            return submode
    return ""


def infer_dp_repair_submode(
    *,
    errors: list[str],
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    if request is not None:
        parts.extend([request.problem, request.strategy_hint or ""])
    if previous is not None:
        parts.append(json.dumps(previous, ensure_ascii=False))
    parts.extend(errors)
    return _dp_repair_submode_for_text("\n".join(parts))


def _dp_repair_submode_for_text(text: str) -> str:
    value = text.lower().replace("-", "_").replace(" ", "_")
    patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("complete_knapsack", ("complete_knapsack", "coin_change", "完全背包", "零钱兑换")),
        ("bounded_knapsack", ("bounded_knapsack", "多重背包", "数量上限", "counts")),
        ("knapsack_01", ("knapsack_01", "0_1背包", "0-1背包", "01背包", "subset_sum")),
        ("lcs", ("lcs", "lcs_length", "最长公共子序列")),
        ("state_compression", ("state_compression", "tsp", "状态压缩", "mask")),
        ("digit_dp", ("digit_dp", "数位dp", "数位_dp", "no_seven", "不含_7", "不含7", "不包含数字_7", "不包含数字7", "逐位处理", "forbidden_digit")),
    )
    for submode, tokens in patterns:
        if any(token in value for token in tokens):
            return submode
    return ""


def infer_graph_repair_submode(
    *,
    errors: list[str],
    request: ProblemInput | None = None,
    previous: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    if request is not None:
        parts.extend([request.problem, request.strategy_hint or ""])
    if previous is not None:
        parts.append(json.dumps(previous, ensure_ascii=False))
    parts.extend(errors)
    return _graph_repair_submode_for_text("\n".join(parts))


def _graph_repair_submode_for_text(text: str) -> str:
    value = text.lower().replace("-", "_").replace(" ", "_")
    patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("network_flow", ("edmonds_karp", "network_flow", "max_flow", "最大流", "网络流", "augmenting_path", "bottleneck", "capacity", "flow/capacity")),
        ("bipartite_matching", ("bipartite_matching", "二分图匹配", "匈牙利", "最大匹配", "增广路径", "增广路", "match[", "matching")),
        ("connected_components", ("connected_components", "connected_component", "连通分量")),
        ("floyd_warshall", ("floyd_warshall", "floyd", "all_pairs", "全源最短")),
        ("bellman_ford", ("bellman_ford", "bellman",)),
        ("zero_one_bfs", ("zero_one_bfs", "0_1_bfs", "01_bfs")),
        ("dijkstra", ("dijkstra",)),
        ("mst", ("kruskal", "mst", "minimum_spanning", "最小生成树")),
        ("tarjan", ("tarjan", "scc", "strongly_connected", "component 弹栈", "割点", "桥")),
        ("topological_sort", ("topological_sort", "topo", "拓扑", "indegree")),
        ("bipartite_coloring", ("bipartite_coloring", "bipartite", "二分图", "color", "染色")),
        ("dfs", ("graph_dfs", "dfs",)),
        ("bfs", ("graph_bfs", "bfs",)),
        ("unsupported", ("submode：directed", "submode:directed", "submode=directed", "unsupported_submode", "未支持的_submode：directed")),
    )
    for submode, tokens in patterns:
        if any(token in value for token in tokens):
            return submode
    return ""


def _extract_step(message: str) -> int | None:
    match = STEP_RE.search(message)
    return int(match.group(1)) if match else None


def _extract_target(message: str) -> str:
    for pattern in TARGET_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1).strip("。.,，；;")
    return ""
